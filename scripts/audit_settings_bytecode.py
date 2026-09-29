#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import zipfile

# Scan compiled Kotlin/JVM bytecode for calls which are known to overflow DEX's
# 8-bit invoke/range register-count field for com.armsx2.config.Settings.
#
# Settings has 246 primary-constructor fields. Kotlin's generated copy$default
# and default-argument constructor add receiver/mask/marker registers and reach
# 256 registers. D8 can emit invoke-range count=0 for these calls, which
# Android 17 ART rejects with VerifyError.

build_root = Path("platforms/android/app/build")
if not build_root.exists():
    raise SystemExit(f"Build output directory not found: {build_root}")

hazards = []
scanned = 0
seen = set()

def inspect_javap(label: str, out: str):
    global scanned
    scanned += 1
    for line in out.splitlines():
        normalized = line.replace(".", "/")
        if "Method com/armsx2/config/Settings.copy$default:" in normalized:
            hazards.append((label, line.strip()))
        if (
            'Method com/armsx2/config/Settings."<init>":' in normalized
            and "DefaultConstructorMarker" in line
        ):
            hazards.append((label, line.strip()))

# Gradle/Kotlin output layout changes between plugin versions. Discover .class
# files anywhere under app/build instead of relying on one hard-coded directory.
for cls in build_root.rglob("*.class"):
    p = str(cls)
    if "com/armsx2/" not in p.replace("\\", "/"):
        continue
    key = ("class", p)
    if key in seen:
        continue
    seen.add(key)
    out = subprocess.run(
        ["javap", "-c", "-p", p],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout
    inspect_javap(p, out)

# Some AGP/Kotlin versions package compiled classes directly into intermediate
# jars. Scan those too so the audit survives build-layout changes.
for jar in build_root.rglob("*.jar"):
    try:
        with zipfile.ZipFile(jar) as zf:
            entries = [
                n for n in zf.namelist()
                if n.startswith("com/armsx2/") and n.endswith(".class")
            ]
    except zipfile.BadZipFile:
        continue

    for entry in entries:
        class_name = entry[:-6].replace("/", ".")
        key = (str(jar), class_name)
        if key in seen:
            continue
        seen.add(key)
        out = subprocess.run(
            ["javap", "-c", "-p", "-classpath", str(jar), class_name],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout
        inspect_javap(f"{jar}!/{entry}", out)

if scanned == 0:
    # Print discovery info so a future AGP layout change is diagnosable from CI
    # without another device test.
    print("No com.armsx2 compiled classes found. Build outputs discovered:")
    for p in sorted(build_root.rglob("*")):
        if p.is_file() and p.suffix in {".jar", ".class", ".dex"}:
            print(f"  {p}")
    raise SystemExit("No compiled com.armsx2 classes found for verifier audit")

if hazards:
    print("ERROR: Settings DEX verifier hazards remain:")
    for label, line in hazards:
        print(f"  {label}")
        print(f"    {line}")
    print(f"Total hazardous invocations: {len(hazards)}")
    sys.exit(1)

print(f"Settings verifier audit passed across {scanned} compiled com.armsx2 classes")
