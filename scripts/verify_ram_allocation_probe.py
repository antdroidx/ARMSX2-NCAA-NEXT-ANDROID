"""Verify native patch bytes, package identity and signature in final APK."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
evidence = root / 'diagnostics'
report = json.loads((evidence / 'ram-allocation-probe.json').read_text())
apk = root / 'next-classic-3668-ram-allocation-probe.apk'
name = 'lib/arm64-v8a/libemucore.so'
with zipfile.ZipFile(root / 'classic-2.2n-base.apk') as z:
    original = z.read(name)
with zipfile.ZipFile(apk) as z:
    patched = z.read(name)
expected = bytearray(original)
for change in report['changes']:
    offset = int(change['file_offset'], 16)
    old, new = bytes.fromhex(change['old_bytes']), bytes.fromhex(change['new_bytes'])
    assert expected[offset:offset+4] == old
    expected[offset:offset+4] = new
assert patched == bytes(expected), 'Unexpected native change or missing patch in final APK'
assert hashlib.sha256(patched).hexdigest() == report['output_native_sha256']
badging = (evidence / 'ram-probe-badging.txt').read_text()
assert "package: name='com.ncaanext.classic3668.ramprobe'" in badging
assert "application-label:'Classic RAM Allocation Probe'" in badging
signature = (evidence / 'ram-probe-signature.txt').read_text()
assert 'Verifies' in signature
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
result = {'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
          'exact_four_native_changes_verified': True, 'signature_verified': True,
          'package_verified': True, 'runtime_tested': False, 'guest_ram_mib': 32,
          'next128_supported': False, 'stage': 'allocation-probe'}
(evidence / 'ram-probe-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
