"""Compare the pinned and generated upload processors with identical mock workloads."""
from pathlib import Path
import os
import subprocess
import tempfile
from patch_conservative_gs import function
from patch_texture_streaming import STATS

repo = Path(__file__).resolve().parents[1]
reference = (repo / 'tests/texture_streaming_original.cpp').read_text()
source = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp').read_text()
old = function(reference, 'void GSTextureReplacements::ProcessAsyncLoadedTextures()')
new = function(source, 'void GSTextureReplacements::ProcessAsyncLoadedTextures()')
assert 'std::deque<std::pair<TextureName, bool>> s_async_loaded_textures;' in source
assert 's_async_loaded_textures.erase' not in source
assert 's_texture_runtime_stats = {};' in function(source, 'void GSTextureReplacements::ResetReplacementCacheLocked()')
base = '''
MockState state;
MockState* g_texture_cache = &state;
struct Config { bool OsdShowTextureReplacements = false; } GSConfig;
struct Logger { int reports=0; template<class... T> void WriteLnFmt(const char*,T...) { ++reports; } } Console;
namespace GSTextureReplacements {
static CONTAINER<std::pair<TextureName,bool>> s_async_loaded_textures;
static std::unordered_map<TextureName,bool> s_pending_async_load_textures;
static std::unordered_map<TextureName,Replacement> s_replacement_texture_cache;
static std::mutex s_replacement_texture_cache_mutex;
[[maybe_unused]] static size_t s_replacement_texture_cache_bytes=0;
EXTRA
void ProcessAsyncLoadedTextures();
size_t ReplacementTextureBytes(const Replacement& r) { return r.bytes; }
int HashCacheKeyFromTextureName(const TextureName& n) { return static_cast<int>(n.words[0]); }
GSTexture* CreateReplacementTexture(const Replacement& r,bool mipmap) {
    state.events.push_back({0,r.id,mipmap,r.alpha_minmax});
    static GSTexture texture;
    return r.success ? &texture : nullptr;
}
}
FUNCTION
'''
original = 'namespace Original {\n' + base.replace('CONTAINER', 'std::vector').replace('EXTRA', '').replace('FUNCTION', old) + '\n}'
optimized = 'namespace Optimized {\n' + base.replace('CONTAINER', 'std::deque').replace('EXTRA', STATS).replace('FUNCTION', new) + '\n}'
harness = (repo / 'tests/texture_streaming_harness.cpp').read_text().replace('// ORIGINAL_NAMESPACE', original).replace('// OPTIMIZED_NAMESPACE', optimized)
with tempfile.TemporaryDirectory() as temp:
    cpp = Path(temp) / 'streaming.cpp'
    exe = Path(temp) / 'streaming-test'
    cpp.write_text(harness)
    subprocess.run(['g++', '-std=c++20', '-O2', '-fno-exceptions', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=60)
    clang = Path(os.environ['ANDROID_HOME']) / 'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
    subprocess.run([str(clang), '-std=c++20', '-O2', '-fno-exceptions', '-Wall', '-Wextra', '-Werror',
                    '-c', str(cpp), '-o', str(Path(temp) / 'streaming-arm64.o')], check=True)
print('Upload ordering/budget preservation, backlog movement, diagnostics and ARM64 compile passed')
