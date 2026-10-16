"""Exercise the production cache header, including stale and hostile indexes."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TextureIndexTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'host C++ compiler required; runs in CI')
    def test_production_cache(self):
        for standard in ('c++17', 'c++20'):
            with self.subTest(standard=standard), tempfile.TemporaryDirectory() as temp:
                exe = Path(temp) / 'index-test'
                subprocess.run(['g++', f'-std={standard}', '-fno-exceptions', '-Wall', '-Wextra', '-Werror',
                                '-I', str(ROOT / 'patches'), str(ROOT / 'tests/texture_index_harness.cpp'),
                                '-o', str(exe)], check=True)
                subprocess.run([str(exe), temp], check=True, timeout=20)

if __name__ == '__main__':
    unittest.main()
