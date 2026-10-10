"""Verify the built control identity and byte-for-byte native preservation."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
evidence = root / 'diagnostics'
baseline = json.loads((evidence / 'classic-input.json').read_text())
apk = root / 'next-classic-3668-control.apk'
with zipfile.ZipFile(apk) as z:
    libs = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith('lib/') and n.endswith('.so')}
assert libs == baseline['native_sha256'], 'Native libraries changed'
badging = (evidence / 'apk-badging.txt').read_text()
assert "package: name='com.ncaanext.classic3668.diagnostic'" in badging
assert "application-label:'NEXT Classic 3668 Control'" in badging
signature = (evidence / 'apk-signature.txt').read_text()
assert 'Verifies' in signature
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
result = {'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
          'native_preserved': True, 'separate_package_verified': True,
          'signature_verified': True, 'runtime_tested': False,
          'next128_support_verified': False, 'jd4029_hash_verified': False,
          'folder64_support_verified': False}
(evidence / 'control-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
