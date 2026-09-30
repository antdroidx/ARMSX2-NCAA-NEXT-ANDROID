"""Run the actual generated JNI body with lifecycle/thread ownership assertions."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_stop', ROOT / 'scripts/patch_native_stop.py')
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


class NativeStopTest(unittest.TestCase):
    def test_source_drift_fails_closed(self):
        with self.assertRaises(RuntimeError):
            patcher.patch(patcher.SIGNATURE + ' {\n}\n')

    @unittest.skipUnless(shutil.which('g++'), 'host C++ compiler required; runs in CI')
    def test_production_body(self):
        source = (ROOT / 'tests/native_stop_harness.cpp').read_text().replace('// PRODUCTION_BODY', patcher.BODY)
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / 'stop.cpp'
            exe = Path(temp) / 'stop-test'
            src.write_text(source)
            subprocess.run(['g++', '-std=c++17', '-pthread', '-Wall', '-Wextra', str(src), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
