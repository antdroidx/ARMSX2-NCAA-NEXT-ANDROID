"""Check preserved algorithms and compile the actual mode resolver."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import sys

def function(text, signature):
    start = text.index(signature); brace = text.index('{', start); depth = 0
    for end in range(brace, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError(signature)

root = Path(__file__).resolve().parents[1]
fixtures = json.loads((root / 'tests/texture_hash_bodies.json').read_text())
tc = Path('pcsx2/GS/Renderers/HW/GSTextureCache.cpp').read_text()
for signature, expected in fixtures.items():
    generated = function(tc, signature)
    body = generated[generated.index('{') + 1:-1].strip()
    condition = 'if (GSTextureReplacements::UsesLegacyTextureHashing())'
    assert body.startswith(condition)
    if signature.startswith('GSTextureCache::SourceRegion'):
        current = body[len(condition):].strip()
        assert current.startswith('return {};')
        current = current[len('return {};'):].strip()
    else:
        branch = function(body, condition)
        legacy = branch[branch.index('{') + 1:-1].strip()
        if signature.startswith('static void'):
            assert legacy.endswith('return;')
            legacy = legacy[:-len('return;')].strip()
        assert hashlib.sha256(legacy.encode()).hexdigest() == expected['legacy']
        current = body[len(branch):].strip()
    assert hashlib.sha256(current.encode()).hexdigest() == expected['current']

tr = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp').read_text()
for marker in ['UsesLegacyTextureHashing() ? hash.TEX0.TCC : 0',
               'UsesLegacyTextureHashing() ? tn.TEX0_TCC : 0',
               'if (!GSTextureReplacements::UsesLegacyTextureHashing())',
               'SyncWorkerThread();\n\tg_texture_cache->RemoveAll(true, false, true);']:
    assert marker in tr, marker
resolver = function(tr, 'static bool ResolveLegacyTextureHashing(')
harness = '''#include <cassert>
#include <string>
// RESOLVER
int main() {
 assert(ResolveLegacyTextureHashing(0, "SLUS-21214"));
 assert(!ResolveLegacyTextureHashing(0, "OTHER"));
 assert(!ResolveLegacyTextureHashing(0, ""));
 assert(ResolveLegacyTextureHashing(1, "OTHER"));
 assert(ResolveLegacyTextureHashing(1, "SLUS-21214"));
 assert(!ResolveLegacyTextureHashing(2, "SLUS-21214"));
 assert(!ResolveLegacyTextureHashing(2, "OTHER"));
}
'''.replace('// RESOLVER', resolver)
with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
    cpp = Path(tmp) / 'mode.cpp'; exe = Path(tmp) / 'mode'
    cpp.write_text(harness)
    if '--source-only' not in sys.argv:
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=10)
settings = Path('platforms/android/app/src/main/java/com/armsx2/config/Settings.kt').read_text()
for marker in ['val textureReplacementMethod: Int',
               '"TextureReplacementMethod", "int", textureReplacementMethod.toString()',
               'json.optInt("textureReplacementMethod", (0))',
               'overrides.getInt("textureReplacementMethod")',
               'current.textureReplacementMethod != base.textureReplacementMethod']:
    assert marker in settings, marker
native = Path('platforms/android/app/src/main/cpp/native-lib.cpp').read_text()
assert 'TextureReplacementMethod   = saved_texture_method;' in native
print('Both original hash algorithms preserved; TCC, cache reset and persistence checks passed')
print('Resolver execution skipped' if '--source-only' in sys.argv else 'Auto and override resolver execution passed')
