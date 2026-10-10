#!/usr/bin/env python3
"""Apply opt-in 128107 experiments after JD4029 and logging-only USC patches."""
from pathlib import Path


def edit(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise SystemExit(f"Expected one patch anchor in {path}: {old[:80]}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


def main():
    base = "pcsx2/GS/Renderers/HW/"
    edit(base + "GSTextureReplacements.h", "\tvoid Initialize();", """
	// Immutable between replacement-map reloads; workers are synchronized before updates.
	bool NCAAExperimentEnabled();
	unsigned NCAAExperimentMode(const GSTextureCache::HashCacheKey& key);
	void Initialize();""")
    edit(base + "GSTextureReplacements.cpp", "#include <cinttypes>", "#include <sstream>\n#include <cinttypes>")
    edit(base + "GSTextureReplacements.cpp", "void GSTextureReplacements::Initialize()", r'''
namespace
{
	unsigned s_ncaa_wsu_mode = 0;
	unsigned s_ncaa_usc_mode = 0;
	unsigned s_ncaa_global_mode = 0;
	std::optional<GSTextureCache::HashCacheKey> s_ncaa_wsu_key;

	bool NCAAIsUSC(u64 hash)
	{
		return hash == 0x8be535660878868dULL || hash == 0x0fd2f8fface1b473ULL ||
			hash == 0xb1ab915d19fe1b9aULL || hash == 0x2734ba81529c23b3ULL ||
			hash == 0x3925edba8d75885eULL || hash == 0xf09753a478248cbfULL ||
			hash == 0xb255bb1294f62073ULL || hash == 0xb25b9a4dd3060c61ULL;
	}

	void LoadNCAAExperiment()
	{
		s_ncaa_wsu_mode = s_ncaa_usc_mode = s_ncaa_global_mode = 0;
		s_ncaa_wsu_key.reset();
		if (GSTextureReplacements::s_current_serial != "SLUS-21214")
			return;
		const std::string path = Path::Combine(EmuFolders::Textures, "next128107.txt");
		const auto data = FileSystem::ReadFileToString(path.c_str());
		if (data)
		{
			std::istringstream lines(*data);
			std::string line;
			while (std::getline(lines, line))
			{
				if (!line.empty() && line.back() == '\r') line.pop_back();
				if (line == "global=1") s_ncaa_global_mode = 1;
				else if (line == "global=2") s_ncaa_global_mode = 2;
				else if (line == "global=3") s_ncaa_global_mode = 3;
				else if (line == "global=0") s_ncaa_global_mode = 0;
				else if (line == "wsu=1") s_ncaa_wsu_mode = 1;
				else if (line == "wsu=2") s_ncaa_wsu_mode = 2;
				else if (line == "wsu=3") s_ncaa_wsu_mode = 3;
				else if (line == "wsu=0") s_ncaa_wsu_mode = 0;
				else if (line == "usc=1") s_ncaa_usc_mode = 1;
				else if (line == "usc=2") s_ncaa_usc_mode = 2;
				else if (line == "usc=3") s_ncaa_usc_mode = 3;
				else if (line == "usc=0") s_ncaa_usc_mode = 0;
				else if (line.compare(0, 9, "wsu_file=") == 0)
				{
					// A complete legacy PNG filename, never a guessed team/color match.
					const std::string filename = line.substr(9);
					s_ncaa_wsu_key.reset();
					if (filename.size() > 4 && filename.substr(filename.size() - 4) == ".png")
					{
						const auto name = GSTextureReplacements::ParseReplacementName(filename);
						if (name && !NCAAIsUSC(name->TEX0Hash))
							s_ncaa_wsu_key = GSTextureReplacements::HashCacheKeyFromTextureName(*name);
					}
				}
			}
		}
		Console.WriteLnFmt("NEXT128107 config wsu={} usc={} wsu-key={} control=0 alpha=1 decal=2 no-hw-blend=3",
			s_ncaa_wsu_mode, s_ncaa_usc_mode, s_ncaa_wsu_key.has_value());
	}
}

bool GSTextureReplacements::NCAAExperimentEnabled()
{
	return s_ncaa_global_mode != 0 || s_ncaa_wsu_key.has_value() || s_ncaa_usc_mode != 0;
}

unsigned GSTextureReplacements::NCAAExperimentMode(const GSTextureCache::HashCacheKey& key)
{
	if (s_current_serial != "SLUS-21214") return 0;
	if (s_ncaa_wsu_key && key == *s_ncaa_wsu_key) return s_ncaa_wsu_mode;
	if (NCAAIsUSC(key.TEX0Hash) && key.TEX0.PSM == PSMT4 &&
		key.TEX0.TW == key.TEX0.TH && (key.TEX0.TW == 7 || key.TEX0.TW == 8))
		return s_ncaa_usc_mode;
	return 0;
}

void GSTextureReplacements::Initialize()''')
    edit(base + "GSTextureReplacements.cpp", "\tSyncWorkerThread();\n\tScopedGuard startup_complete_guard", "\tSyncWorkerThread();\n\tLoadNCAAExperiment();\n\tScopedGuard startup_complete_guard")
    edit(base + "GSTextureReplacements.cpp", "\tSetReplacementTextureAlphaMinMax(rtex);", r'''
	const unsigned experiment = NCAAExperimentMode(HashCacheKeyFromTextureName(name));
	if (experiment == 1 || experiment >= 4)
	{
		// Test a PNG/GS alpha-range hypothesis in private decoded CPU buffers only.
		// Do not modify disk images, RGB, hashes, or unrelated replacement textures.
		if (rtex.format == GSTexture::Format::Color)
		{
			const unsigned alpha_max = experiment == 4 ? 128 : experiment == 6 ? 192 : 160;
			auto scale_alpha = [alpha_max](std::vector<u8>& bytes, u32 width, u32 height, u32 pitch)
			{
				if (pitch < static_cast<u64>(width) * 4 || bytes.size() < static_cast<u64>(pitch) * height)
					return false;
				for (u32 y = 0; y < height; y++)
					for (u32 x = 0; x < width; x++)
					{
						u8& alpha = bytes[static_cast<size_t>(y) * pitch + x * 4 + 3];
						alpha = static_cast<u8>((static_cast<unsigned>(alpha) * 128 + 127) / 255);
					}
				return true;
			};
			const bool applied = scale_alpha(rtex.data, rtex.width, rtex.height, rtex.pitch);
			for (auto& mip : rtex.mips) scale_alpha(mip.data, mip.width, mip.height, mip.pitch);
			Console.WriteLnFmt("NEXT128107 alpha file={} applied={} range=0-{}", filename, applied, alpha_max);
		}
		else Console.WriteLnFmt("NEXT128107 alpha skipped compressed file={}", filename);
	}
	SetReplacementTextureAlphaMinMax(rtex);''')
    edit(base + "GSTextureCache.h", "\t\tHashCacheEntry* m_from_hash_cache = nullptr;", "\t\tHashCacheEntry* m_from_hash_cache = nullptr;\n\t\tunsigned m_ncaa_experiment = 0;\n\t\tunsigned m_ncaa_logs = 0;\n\t\tHashCacheKey m_ncaa_key;")
    # Tag original and asynchronously replaced sources without changing their cache key.
    edit(base + "GSTextureCache.cpp", "\tconst GSLocalMemory::psm_t& psm = GSLocalMemory::m_psm[TEX0.PSM];\n\tSource* src = new Source(TEX0, TEXA);", r'''	const GSLocalMemory::psm_t& psm = GSLocalMemory::m_psm[TEX0.PSM];
	Source* src = new Source(TEX0, TEXA);
	if (!dst && GSTextureReplacements::NCAAExperimentEnabled())
	{
		const u32* clut = psm.pal ? static_cast<const u32*>(g_gs_renderer->m_mem.m_clut) : nullptr;
		src->m_ncaa_key = HashCacheKey::Create(TEX0, TEXA, clut, lod, region);
		src->m_ncaa_experiment = GSTextureReplacements::NCAAExperimentMode(src->m_ncaa_key);
	}''')
    edit(base + "GSRendererHW.cpp", "void GSRendererHW::Draw()", r'''static bool NCAAHasControlAlpha(const GSHWDrawConfig& conf)
{
	// DECAL and MODULATE have identical alpha only when TCC ignores texture alpha,
	// or every vertex has neutral GS alpha 128. Otherwise keep the RGB test on control.
	if (!conf.ps.tcc) return true;
	if (!conf.verts || !conf.nverts) return false;
	for (u32 i = 0; i < conf.nverts; i++)
		if ((conf.verts[i].RGBAQ.U32[0] >> 24) != 128) return false;
	return true;
}

void GSRendererHW::Draw()''')
    edit(base + "GSRendererHW.cpp", "\tGSDrawLog::EndDraw(m_conf, static_cast<u8>(m_prim_overlap));", r'''
	// Late draw-only experiments. Complex/multi-pass paths retain the control.
	// Source pixels, GS registers, vertex buffers, and persistent cache state stay intact.
	if (tex && tex->m_ncaa_experiment >= 2 && tex->m_from_hash_cache &&
		tex->m_from_hash_cache->is_replacement)
	{
		const auto control_ps = m_conf.ps;
		const auto control_blend = m_conf.blend;
		const bool simple = !m_conf.alpha_second_pass.enable && !m_conf.blend_multi_pass.enable &&
			!m_conf.ps.IsSWBlending() && !m_conf.ps.blend_hw && !m_conf.ps.blend_mix &&
			!m_conf.ps.IsFeedbackLoopRT() && !m_channel_shuffle && !m_texture_shuffle;
		bool applied = false;
		if (simple && tex->m_ncaa_experiment == 2 && m_conf.ps.tfx == 0 && NCAAHasControlAlpha(m_conf))
		{
			m_conf.ps.tfx = 1; // DECAL: replacement RGB instead of vertex-modulated RGB.
			applied = true;
		}
		else if (simple && tex->m_ncaa_experiment == 3 && m_conf.blend.enable)
		{
			m_conf.blend.enable = false; // Isolate destination-color contribution.
			applied = true;
		}
		if (tex->m_ncaa_logs++ < 128)
			Console.WriteLnFmt("NEXT128107 draw mode={} applied={} hash={:016x} clut={:016x} control-ps={:016x}:{:016x} test-ps={:016x}:{:016x} control-blend={:08x} test-blend={:08x}",
				tex->m_ncaa_experiment, applied, tex->m_ncaa_key.TEX0Hash,
				tex->m_ncaa_key.CLUTHash, control_ps.key_hi, control_ps.key_lo,
				m_conf.ps.key_hi, m_conf.ps.key_lo, control_blend.key, m_conf.blend.key);
	}
	GSDrawLog::EndDraw(m_conf, static_cast<u8>(m_prim_overlap));''')
    # Import into the app's actual texture root through Android's document picker.
    # No Settings constructor/copy changes and no live renderer reload.
    android = "platforms/android/app/src/main/java/com/armsx2/ui/textures/"
    edit(android + "TextureManagerScreen.kt", "    LaunchedEffect(Unit) { viewModel.refresh() }", '''    val experimentPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let(viewModel::importExperimentControls)
    }
    LaunchedEffect(Unit) { viewModel.refresh() }''')
    edit(android + "TextureManagerScreen.kt", '                    RoundAction("↻", str("games.card.refresh"), viewModel::refresh)', '''                    RoundAction("↻", str("games.card.refresh"), viewModel::refresh)
                    RoundAction("🧪", "Import 128107 test controls", { experimentPicker.launch(arrayOf("text/plain")) })
                    RoundAction("0", "Restore 128107 control", viewModel::resetExperimentControls)''')
    edit(android + "TextureManagerViewModel.kt", "    private fun textureRoot(): File", r'''    fun importExperimentControls(uri: Uri) {
        viewModelScope.launch {
            val result = runCatching {
                withContext(Dispatchers.IO) {
                    val text = getApplication<Application>().contentResolver.openInputStream(uri)?.use {
                        val bytes = ByteArray(4097)
                        var count = 0
                        while (count < bytes.size) {
                            val n = it.read(bytes, count, bytes.size - count)
                            if (n <= 0) break
                            count += n
                        }
                        require(count <= 4096) { "Control file must be at most 4 KB." }
                        String(bytes, 0, count, Charsets.UTF_8)
                    } ?: error("Could not read control file.")
                    val valid = Regex("(?:wsu|usc|global)=[0-3]|wsu_file=[0-9a-fA-F]{1,16}(?:-[0-9a-fA-F]{1,16})?-[0-9a-fA-F]{8}\\.png")
                    require(text.lineSequence().all { it.isEmpty() || valid.matches(it) }) {
                        "Use wsu=0..3, usc=0..3, and an exact wsu_file=hash-CLUT-bits.png filename."
                    }
                    textureRoot().mkdirs()
                    File(textureRoot(), "next128107.txt").writeText(text)
                }
            }
            state.value = if (result.isSuccess) state.value.copy(
                message = "128107 controls imported. Fully close and restart this app before testing.", error = null
            ) else state.value.copy(error = result.exceptionOrNull()?.message, message = null)
        }
    }

    fun resetExperimentControls() {
        viewModelScope.launch {
            val result = runCatching {
                withContext(Dispatchers.IO) {
                    textureRoot().mkdirs()
                    File(textureRoot(), "next128107.txt").writeText("wsu=0\nusc=0\n")
                }
            }
            state.value = if (result.isSuccess) state.value.copy(
                message = "Original rendering control restored. Fully close and restart this app.", error = null
            ) else state.value.copy(error = result.exceptionOrNull()?.message, message = null)
        }
    }

    private fun textureRoot(): File''')


if __name__ == "__main__":
    main()
