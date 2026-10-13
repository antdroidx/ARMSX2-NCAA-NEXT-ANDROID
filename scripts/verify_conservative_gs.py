"""Run generated old/new functions with the real GS SIMD implementation."""
from pathlib import Path
import subprocess
import tempfile
from patch_conservative_gs import EARLY_EXIT, function

root = Path.cwd()
source = (root / 'pcsx2/GS/GS.cpp').read_text()
new = function(source, 'std::pair<u8, u8> GSGetRGBA8AlphaMinMax(')
assert new.count(EARLY_EXIT) == 2
old = new.replace(EARLY_EXIT, '').replace('GSGetRGBA8AlphaMinMax(', 'OriginalAlpha(')
harness = (Path(__file__).resolve().parents[1] / 'tests/gs_alpha_harness.cpp').read_text()
harness = harness.replace('// ORIGINAL', old).replace('// OPTIMIZED', new)
with tempfile.TemporaryDirectory() as tmp:
    cpp = Path(tmp) / 'alpha.cpp'
    exe = Path(tmp) / 'alpha-test'
    cpp.write_text(harness)
    subprocess.run(['g++', '-std=c++20', '-O2', '-msse4.1', '-fno-exceptions',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I', str(root), '-I', str(root / 'pcsx2'), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=60)
    # Compile the same production functions against the actual ARM64 NEON headers.
    import os
    clang = Path(os.environ['ANDROID_HOME']) / 'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
    subprocess.run([str(clang), '-std=c++20', '-O2', '-fno-exceptions', '-I', str(root),
                    '-I', str(root / 'pcsx2'), '-c', str(cpp), '-o', str(Path(tmp) / 'alpha-arm64.o')], check=True)
print('Exact alpha equivalence, guarded reads, and ARM64 SIMD compile passed')
