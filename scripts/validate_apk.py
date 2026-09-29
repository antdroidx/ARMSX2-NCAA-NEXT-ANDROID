#!/usr/bin/env python3
"""Validate the signed artifact and compare update/native identity to prior APKs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from audit_dex import audit, SETTINGS

EXPECTED_CERT = "599891bb2245e9c90237c41e7066889cb9c28e11c2f8b5d6af75b10cad3a783f"
BUILD16_CERT = "a7135416c2a58f51d331e5b0b21b2bcdb6983e53b5f6bd19d3f612ac08ec0ef5"
PACKAGE = "com.armsx2.ncaanext"


def run(*args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True).stdout


def identity(apk, tools, expected_cert=EXPECTED_CERT):
    signing = run(tools / "apksigner", "verify", "--verbose", "--print-certs", apk)
    certs = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)", signing)
    if certs != [expected_cert]:
        raise ValueError(f"Signing identity differs from pinned certificate {expected_cert}: {certs}")
    manifest = run(tools / "aapt", "dump", "badging", apk)
    m = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", manifest)
    if not m or m[1] != PACKAGE:
        raise ValueError("Unexpected application ID or missing manifest metadata")
    if "launchable-activity:" not in manifest:
        raise ValueError("Launcher activity missing")
    return {"package": m[1], "version_code": int(m[2]), "version_name": m[3], "certificate_sha256": certs[0]}


def native_inventory(apk):
    with zipfile.ZipFile(apk) as z:
        return {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
                if n.startswith("lib/") and n.endswith(".so")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("apk", type=Path)
    p.add_argument("--previous", type=Path, required=True)
    p.add_argument("--native-base", type=Path, required=True)
    p.add_argument("--build-tools", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    report = identity(a.apk, a.build_tools)
    previous = identity(a.previous, a.build_tools)
    if report["version_code"] != 128016 or report["version_code"] <= previous["version_code"]:
        raise ValueError("New APK must be versionCode 128016 and upgrade the previous build")
    if report["version_name"] != "0.1.10-game-exit-no-intro":
        raise ValueError("Unexpected version name")
    run(a.build_tools / "zipalign", "-c", "-P", "16", "4", a.apk)
    baseline = json.loads(Path(__file__).resolve().parents[1].joinpath("baseline/known-good.json").read_text())
    if hashlib.sha256(a.previous.read_bytes()).hexdigest() != baseline["apk_sha256"]:
        raise ValueError("Previous APK differs from accepted PR 1 artifact")
    native = native_inventory(a.apk)
    if native != baseline["native_sha256"]:
        raise ValueError("Native libraries differ from accepted NEXT 27 baseline")
    if native != native_inventory(a.native_base):
        raise ValueError("Native library inventory/content changed from Run 6")
    if {n.split("/")[1] for n in native} != {"arm64-v8a"}:
        raise ValueError("Unexpected ABI inventory")
    for name in ("emucore_4k", "emucore_16k", "c++_shared", "shaderc_shared", "SPIRV-Tools-shared", "librashader_capi"):
        if f"lib/arm64-v8a/lib{name}.so" not in native:
            raise ValueError(f"Required native library missing: {name}")
    report["native_sha256"] = native
    report["dex"] = {}
    with zipfile.ZipFile(a.apk) as z, zipfile.ZipFile(a.native_base) as base, tempfile.TemporaryDirectory() as td:
        if z.testzip():
            raise ValueError("APK ZIP CRC failure")
        resources = {n for n in base.namelist() if n.startswith("assets/resources/") and not n.endswith("/")}
        if not resources or not resources.issubset(z.namelist()):
            raise ValueError("Expected core resources missing")
        for n in resources:
            if z.read(n) != base.read(n):
                raise ValueError(f"Core resource differs from native baseline: {n}")
        dex_names = [n for n in z.namelist() if re.fullmatch(r"classes(\d+)?\.dex", n)]
        if not dex_names:
            raise ValueError("No DEX files")
        all_dex = []
        definitions = 0
        for name in dex_names:
            data = z.read(name)
            all_dex.append(data)
            target = Path(td) / name
            target.write_bytes(data)
            result = subprocess.run([str(a.build_tools / "dexdump"), "-d", str(target)],
                                    check=True, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
            # dexdump prints DEX modified UTF-8 string constants verbatim.
            # Replace non-UTF-8 display bytes only; audit() reads actual method
            # prototypes/counts from the original binary, not displayed strings.
            if re.search(r"\b(ERROR|invalid|failed)\b", result.stderr, re.I):
                raise ValueError(f"dexdump diagnostics for {name}: {result.stderr}")
            report["dex"][name] = audit(data, result.stdout)
            definitions += result.stdout.count("Class descriptor  : 'Lcom/armsx2/config/Settings;'")
        if definitions != 1 or not any(d["settings_constructors"] for d in report["dex"].values()):
            raise ValueError("Expected exactly one Settings class definition")
        for marker in (b"NCAA NEXT CRASH DEBUGGER", b"DIAG_CRASH_REPORT_SHOWN", b"DIAG_FIRST_LAUNCH", b"STARTUP_INTRO_BYPASSED", b"LIBRARY_READY", b"SHUTDOWN_BEGIN"):
            if not any(marker in d for d in all_dex):
                raise ValueError(f"Crash instrumentation missing: {marker!r}")
        report["core_resource_count"] = len(resources)
    report["apk_sha256"] = hashlib.sha256(a.apk.read_bytes()).hexdigest()
    report["previous_apk"] = previous
    report["update_compatible_with_baseline"] = report["certificate_sha256"] == previous["certificate_sha256"]
    report["baseline_commit"] = baseline["pr_head"]
    report["runtime_status"] = "Device acceptance pending: launch, NEXT 27 extended RAM, Close Game, relaunch; ART is a separate CI gate"
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
