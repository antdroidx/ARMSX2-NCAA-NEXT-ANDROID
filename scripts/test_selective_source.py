"""Exercise patched production functions with bounded host models, not guest benchmarks."""
from pathlib import Path
import subprocess
import tempfile

OVERLAY = Path(__file__).resolve().parents[1]


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


audio = Path('pcsx2/Host/OboeAudioStream.cpp').read_text()
audio_functions = function(audio, 'oboe::DataCallbackResult OboeAudioStream::onAudioReady(') + '\n' + function(audio, 'bool OboeAudioStream::Open()')
ee = function(Path('pcsx2/arm64/recVTLB-arm64.cpp').read_text(), 'static void recComputeAddr()')
vu = function(Path('pcsx2/arm64/microVU_Misc-arm64.inl').read_text(), '__fi void mVUaddrFix(')
vu = vu[vu.index('if (isVU1)'):vu.index('\n\telse')]
vu = vu[vu.index('{') + 1:vu.rindex('}')]
with tempfile.TemporaryDirectory() as temp:
    for name, replacements in [('audio', {'// PRODUCTION_FUNCTIONS': audio_functions}), ('jit', {'// PRODUCTION_EE': ee, '// PRODUCTION_VU1': vu})]:
        source = (OVERLAY / f'tests/selective_{name}_harness.cpp').read_text()
        for marker, replacement in replacements.items():
            source = source.replace(marker, replacement)
        src = Path(temp) / f'{name}.cpp'
        exe = Path(temp) / name
        src.write_text(source)
        subprocess.run(['g++', '-std=c++17', '-pthread', '-fsanitize=undefined,address', '-fno-omit-frame-pointer', str(src), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=30)
print('Host model checks passed; physical ARM64 gameplay/audio validation still required')
