"""Audit all APK DEX invocation widths and verify the Extended label/version."""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from audit_dex import audit

apk = Path(sys.argv[1])
tools = Path(sys.argv[2])
manifest = subprocess.run([str(tools / 'aapt'), 'dump', 'badging', str(apk)], check=True, capture_output=True, text=True).stdout
assert "versionCode='128119'" in manifest
assert "versionName='0.2.5-RC4-test2'" in manifest
assert "application-label:'ARMSX2 Extended'" in manifest
assert 'application-debuggable' not in manifest
reports = {}
with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
    for name in z.namelist():
        if not re.fullmatch(r'classes\d*\.dex', name):
            continue
        data = z.read(name)
        file = Path(tmp) / name
        file.write_bytes(data)
        # dexdump prints modified UTF-8 string literals (including surrogate code
        # units). Instruction offsets/opcodes are ASCII; tolerate those literals.
        disassembly = subprocess.run([str(tools / 'dexdump'), '-d', str(file)], check=True, capture_output=True).stdout.decode('utf-8', errors='replace')
        reports[name] = audit(data, disassembly)
assert reports
# R8 renames Settings in release DEX. Its declarations are audited before R8 by
# audit_settings_bytecode.py; every post-R8 invocation is checked above by width.
(apk.parent / 'extended-apk-verification.json').write_text(json.dumps(reports, indent=2))
print('Extended app label, RC4 test version, production status and all DEX invokes verified')
