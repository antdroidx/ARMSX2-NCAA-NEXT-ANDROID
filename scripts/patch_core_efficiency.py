"""Remove duplicate texture work and bound rejected audio affinity retries."""
from pathlib import Path
from patch_conservative_gs import function

GRAPHICS_OLD = '''			}

			g_gs_renderer->m_mem.ReadTexture(
				off, read_r, m.bits + t_r.y * static_cast<u32>(m.pitch) + (t_r.x * sizeof(u32)), m.pitch, TEXA);'''
GRAPHICS_NEW = '''				// Reuse the RGBA32 conversion already needed for alpha tracking.
				// The GPU map may be write-only; read only from the CPU scratch buffer.
				StringUtil::StrideMemCpy(
					m.bits + t_r.y * static_cast<u32>(m.pitch) + (t_r.x * sizeof(u32)), m.pitch,
					s_unswizzle_buffer, pitch, static_cast<size_t>(read_r.width()) * sizeof(u32), read_r.height());
			}
			else
			{
				g_gs_renderer->m_mem.ReadTexture(
					off, read_r, m.bits + t_r.y * static_cast<u32>(m.pitch) + (t_r.x * sizeof(u32)), m.pitch, TEXA);
			}'''

DEDUP = '''	// A sync decode can finish after an outstanding async decode inserted
	// this same key. Keep the existing value, as emplace did, but do not
	// evict other entries, charge its bytes twice, or append a duplicate LRU node.
	const auto existing = s_replacement_texture_cache.find(name);
	if (existing != s_replacement_texture_cache.end())
	{
		TouchReplacementCacheLocked(name);
		return &existing->second;
	}

'''

def replace_once(s, old, new):
    assert s.count(old) == 1, old[:100]
    return s.replace(old, new, 1)

if __name__ == '__main__':
    p = Path('pcsx2/GS/Renderers/HW/GSTextureCache.cpp')
    s = p.read_text()
    s = replace_once(s, '#include "common/SmallString.h"', '#include "common/SmallString.h"\n#include "common/StringUtil.h"')
    s = replace_once(s, '\t\t\t\t// TODO: Only read once in 32bit and copy to the mapped texture. Bit out of scope of this PR and not a huge impact.\n', '')
    p.write_text(replace_once(s, GRAPHICS_OLD, GRAPHICS_NEW))

    p = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
    s = p.read_text()
    old = function(s, 'const GSTextureReplacements::ReplacementTexture* GSTextureReplacements::InsertReplacementCacheLocked(')
    new = replace_once(old, '\twhile ((s_replacement_texture_cache_bytes + incoming)', DEDUP + '\twhile ((s_replacement_texture_cache_bytes + incoming)')
    p.write_text(replace_once(s, old, new))

    p = Path('pcsx2/Host/OboeAudioStream.cpp')
    s = p.read_text()
    s = replace_once(s, '\t\tstd::atomic<bool> m_audio_thread_pinned{false};',
        '\t\tstd::atomic<bool> m_audio_thread_pinned{false};\n\t\tstd::atomic<u32> m_audio_affinity_retry_frames{0};\n\t\tstd::atomic<bool> m_audio_affinity_warned{false};')
    anchor = '\t\tconst u64 perf_mask = VMManager::Internal::GetPerformanceClusterAffinityMask();'
    s = replace_once(s, anchor, '''		// Back off for roughly one second of output after a rejected syscall.
		// Continue rendering every callback; do not sleep or wait on this thread.
		const u32 retry = m_audio_affinity_retry_frames.load(std::memory_order_relaxed);
		const u32 elapsed = p_numFrames > 0 ? static_cast<u32>(p_numFrames) : 0;
		if (retry != 0)
			m_audio_affinity_retry_frames.store(retry > elapsed ? retry - elapsed : 0, std::memory_order_relaxed);
		const u64 perf_mask = retry > elapsed ? 0 : VMManager::Internal::GetPerformanceClusterAffinityMask();''')
    old = '\t\t\t\tWARNING_LOG("(Oboe) sched_setaffinity tid={} failed (errno {}) — will retry next callback", tid, errno);'
    new = '''				m_audio_affinity_retry_frames.store(static_cast<u32>(m_sample_rate), std::memory_order_relaxed);
				if (!m_audio_affinity_warned.exchange(true, std::memory_order_relaxed))
					WARNING_LOG("(Oboe) sched_setaffinity tid={} failed (errno {}) — backing off retries", tid, errno);'''
    s = replace_once(s, old, new)
    s = replace_once(s, '\tm_audio_thread_pinned.store(false, std::memory_order_release);',
        '\tm_audio_affinity_retry_frames.store(0, std::memory_order_relaxed);\n\tm_audio_affinity_warned.store(false, std::memory_order_relaxed);\n\tm_audio_thread_pinned.store(false, std::memory_order_release);')
    p.write_text(s)
    print('Single GS conversion, duplicate cache protection, and bounded affinity retries applied')
