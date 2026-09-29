#!/usr/bin/env python3
"""Fail closed on unsafe Settings declarations, including unused constructors."""
from pathlib import Path
import re
import subprocess
import sys


def hazards(output):
    findings = []
    for line in output.splitlines():
        # Inspect declarations as well as calls. Preserve javap's owner/method dot.
        if "copy$default" in line or "DefaultConstructorMarker" in line:
            findings.append(line.strip())
        if re.search(r"public com\.armsx2\.config\.Settings\(\);", line):
            findings.append(line.strip())
    return findings


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("platforms/android/app/build")
    classes = list(root.rglob("com/armsx2/config/Settings.class"))
    if not classes:
        raise SystemExit("Settings.class missing: cannot audit compiled constructor")
    for cls in classes:
        result = subprocess.run(["javap", "-c", "-p", str(cls)],
                                check=True, capture_output=True, text=True)
        if "public com.armsx2.config.Settings(" not in result.stdout:
            raise SystemExit(f"Settings constructor not found in javap output: {cls}")
        errors = hazards(result.stdout)
        if errors:
            raise SystemExit(f"Unsafe Settings bytecode in {cls}:\n" + "\n".join(errors))
    print(f"Settings declaration audit passed ({len(classes)} compiled copies)")


if __name__ == "__main__":
    main()

