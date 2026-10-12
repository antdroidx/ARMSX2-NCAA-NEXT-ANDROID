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
assert "versionCode='128116'" in manifest
assert "versionName='0.2.5-RC3'" in manifest
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
        disassembly = subprocess.run([str(tools / 'dexdump'), '-d', str(file)], check=True, capture_output=True, text=True).stdout
        reports[name] = audit(data, disassembly)
assert reports
assert sum(r['settings_constructors'] for r in reports.values()) == 1
(apk.parent / 'extended-apk-verification.json').write_text(json.dumps(reports, indent=2))
print('Extended app label, RC3 version, production status and all DEX invokes verified')
