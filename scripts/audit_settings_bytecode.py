#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

# Scan compiled Kotlin/JVM bytecode for calls which are known to overflow DEX's
# 8-bit invoke/range register-count field for com.armsx2.config.Settings.
#
# Settings has 246 primary-constructor fields. Kotlin's generated copy$default
# and default-argument constructor add receiver/mask/marker registers and reach
# 256 registers. D8 has emitted invoke-range count=0 for these calls, which
# Android 17 ART rejects with VerifyError.

roots = [
    Path("platforms/android/app/build/tmp/kotlin-classes/githubDebug"),
    Path("platforms/android/app/build/intermediates/javac/githubDebug/classes"),
]
class_files = []
for root in roots:
    if root.exists():
        class_files.extend(root.rglob("*.class"))

if not class_files:
    raise SystemExit("No compiled class files found for verifier audit")

hazards = []
for cls in class_files:
    # Settings.class necessarily defines copy$default/default constructor;
    # definitions are harmless. We only care about INVOCATIONS from bytecode.
    try:
        out = subprocess.run(
            ["javap", "-c", "-p", str(cls)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout
    except Exception as exc:
        raise SystemExit(f"javap failed for {cls}: {exc}")

    for line in out.splitlines():
        normalized = line.replace(".", "/")
        if "Method com/armsx2/config/Settings.copy$default:" in normalized:
            hazards.append((str(cls), line.strip()))
        # Calls to the Kotlin synthetic default-argument constructor include
        # DefaultConstructorMarker in the invoked Settings.<init> descriptor.
        if (
            "Method com/armsx2/config/Settings" in normalized
            and '"<init>"' in line
            and "DefaultConstructorMarker" in line
        ):
            hazards.append((str(cls), line.strip()))

if hazards:
    print("ERROR: Settings DEX verifier hazards remain:")
    for cls, line in hazards:
        print(f"  {cls}")
        print(f"    {line}")
    print(f"Total hazardous invocations: {len(hazards)}")
    sys.exit(1)

print(f"Settings verifier audit passed across {len(class_files)} compiled classes")
