"""Consume ready textures without shifting the backlog; opt-in cache diagnostics."""
from pathlib import Path
from patch_conservative_gs import function

STATS = '''
	// All accesses are under s_replacement_texture_cache_mutex. Counters are
	// opt-in through the existing texture-replacement OSD setting.
	struct TextureRuntimeStats
	{
		u64 hits = 0, misses = 0, decoded = 0, evicted = 0;
		u64 uploads = 0, upload_bytes = 0;
		u32 frames = 0;
	};
	static TextureRuntimeStats s_texture_runtime_stats;
	static bool s_texture_runtime_stats_enabled = false;
'''
REPORT = '''
	// Read GSConfig only on the GS thread; worker counters use this locked flag.
	s_texture_runtime_stats_enabled = GSConfig.OsdShowTextureReplacements;
	if (s_texture_runtime_stats_enabled && ++s_texture_runtime_stats.frames >= 600)
	{
		s_texture_runtime_stats.frames = 0;
		Console.WriteLnFmt("Texture streaming stats: decoded-cache hits={} misses={} decoded={} evicted={} "
			"uploads={} uploaded-source-MiB={} cache-MiB={} ready={} pending={}",
			s_texture_runtime_stats.hits, s_texture_runtime_stats.misses,
			s_texture_runtime_stats.decoded, s_texture_runtime_stats.evicted,
			s_texture_runtime_stats.uploads, s_texture_runtime_stats.upload_bytes / 1048576,
			s_replacement_texture_cache_bytes / 1048576,
			s_async_loaded_textures.size(), s_pending_async_load_textures.size());
	}
'''

def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)

def optimize_queue(body):
    body = replace_once(body, '\tsize_t idx = 0;\n\tfor (; idx < s_async_loaded_textures.size(); idx++)',
                        '\twhile (!s_async_loaded_textures.empty())')
    body = replace_once(body, '\t\tconst auto& [name, mipmap] = s_async_loaded_textures[idx];',
                        '\t\t// Copy the key before removing its queue node.\n\t\tconst auto [name, mipmap] = s_async_loaded_textures.front();\n\t\ts_async_loaded_textures.pop_front();')
    tail = '''
	// Carry whatever we didn't reach into the next frame rather than dropping it.
	if (idx >= s_async_loaded_textures.size())
		s_async_loaded_textures.clear();
	else
		s_async_loaded_textures.erase(s_async_loaded_textures.begin(), s_async_loaded_textures.begin() + idx);'''
    return replace_once(body, tail, '\n\t// Unprocessed entries stay queued for the next frame.')

def patch(source):
    source = replace_once(source,
        '\tstatic std::vector<std::pair<TextureName, bool>> s_async_loaded_textures;',
        '\tstatic std::deque<std::pair<TextureName, bool>> s_async_loaded_textures;' + STATS)
    old = function(source, 'void GSTextureReplacements::ProcessAsyncLoadedTextures()')
    reference = (Path(__file__).resolve().parents[1] / 'tests/texture_streaming_original.cpp').read_text()
    assert old == function(reference, 'void GSTextureReplacements::ProcessAsyncLoadedTextures()'), 'Upload processor drift'
    new = optimize_queue(old)
    anchor = '\tstd::unique_lock<std::mutex> lock(s_replacement_texture_cache_mutex);'
    new = replace_once(new, anchor, anchor + REPORT)
    source = replace_once(source, old, new)

    old = function(source, 'void GSTextureReplacements::ResetReplacementCacheLocked()')
    source = replace_once(source, old, old.replace('{', '{\n\ts_texture_runtime_stats = {};\n\ts_texture_runtime_stats_enabled = false;', 1))

    old = function(source, 'GSTexture* GSTextureReplacements::LookupReplacementTexture(')
    new = replace_once(old, '\t\t\tTouchReplacementCacheLocked(name);',
        '\t\t\tif (s_texture_runtime_stats_enabled)\n\t\t\t\t++s_texture_runtime_stats.hits;\n\t\t\tTouchReplacementCacheLocked(name);')
    anchor = '\t\t\treturn CreateReplacementTexture(it->second, mipmap);\n\t\t}'
    new = replace_once(new, anchor, anchor + '\n\t\tif (s_texture_runtime_stats_enabled)\n\t\t\t++s_texture_runtime_stats.misses;')
    source = replace_once(source, old, new)

    old = function(source, 'const GSTextureReplacements::ReplacementTexture* GSTextureReplacements::InsertReplacementCacheLocked(')
    new = replace_once(old, '\tconst size_t incoming = ReplacementTextureBytes(tex);',
        '\tif (s_texture_runtime_stats_enabled)\n\t\t++s_texture_runtime_stats.decoded;\n\tconst size_t incoming = ReplacementTextureBytes(tex);')
    new = replace_once(new, '\t\t\ts_replacement_texture_cache.erase(vit);',
        '\t\t\ts_replacement_texture_cache.erase(vit);\n\t\t\tif (s_texture_runtime_stats_enabled)\n\t\t\t\t++s_texture_runtime_stats.evicted;')
    source = replace_once(source, old, new)

    old = function(source, 'GSTexture* GSTextureReplacements::CreateReplacementTexture(')
    new = replace_once(old, '\treturn tex;', '''	if (s_texture_runtime_stats_enabled)
	{
		++s_texture_runtime_stats.uploads;
		s_texture_runtime_stats.upload_bytes += ReplacementTextureBytes(rtex);
	}
	return tex;''')
    return replace_once(source, old, new)

if __name__ == '__main__':
    path = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
    path.write_text(patch(path.read_text()))
    print('Deque upload queue and opt-in texture cache diagnostics applied')
