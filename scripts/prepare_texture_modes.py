"""Generate the dual-mode patch from the reviewed legacy patch and pristine source."""
from pathlib import Path
import runpy

def func(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[start:end + 1]
    raise RuntimeError(signature)

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Expected one anchor: {old[:100]}')
    return text.replace(old, new, 1)

tcpath = Path('pcsx2/GS/Renderers/HW/GSTextureCache.cpp')
original = tcpath.read_text()
runpy.run_path(str(Path(__file__).with_name('patch_jd4029_legacy.py')))
legacy = tcpath.read_text()
region = 'GSTextureCache::SourceRegion GSTextureCache::SourceRegion::Create('
old = func(original, region)
original = original.replace(old, old.replace('{', '{\n\tif (GSTextureReplacements::UsesLegacyTextureHashing())\n\t\treturn {};', 1), 1)
for signature in ['static void HashTextureLevel(', 'GSTextureCache::HashCacheKey GSTextureCache::HashCacheKey::Create(']:
    current_function = func(original, signature)
    legacy_function = func(legacy, signature)
    legacy_body = legacy_function[legacy_function.index('{') + 1:-1]
    if signature.startswith('static void'):
        legacy_body += '\n\treturn;\n'
    branch = '\n\tif (GSTextureReplacements::UsesLegacyTextureHashing())\n\t{' + legacy_body + '\n\t}\n'
    original = original.replace(current_function, current_function.replace('{', '{' + branch, 1), 1)
tcpath.write_text(original)

header = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.h')
header.write_text(replace_once(header.read_text(), '\tvoid Initialize();', '\tbool UsesLegacyTextureHashing();\n\tvoid Initialize();'))
path = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
s = path.read_text()
s = replace_once(s, '(void)TEX0_TCC;', 'if (!GSTextureReplacements::UsesLegacyTextureHashing())\n\t\tTEX0_TCC = 0;')
s = replace_once(s, 'name.TEX0_TCC = hash.TEX0.TCC;', 'name.TEX0_TCC = GSTextureReplacements::UsesLegacyTextureHashing() ? hash.TEX0.TCC : 0;')
s = replace_once(s, 'key.TEX0.TCC = tn.TEX0_TCC;', 'key.TEX0.TCC = GSTextureReplacements::UsesLegacyTextureHashing() ? tn.TEX0_TCC : 0;')
resolver = '''static bool ResolveLegacyTextureHashing(int method, const std::string& serial)
{
    return method == 1 || (method != 2 && serial == "SLUS-21214");
}

bool GSTextureReplacements::UsesLegacyTextureHashing()
{
    return ResolveLegacyTextureHashing(GSConfig.TextureReplacementMethod, s_current_serial);
}

'''
s = replace_once(s, 'void GSTextureReplacements::Initialize()', resolver + 'void GSTextureReplacements::Initialize()')
# Finish old worker jobs before changing serial, then drop GS sources and hash keys.
s = replace_once(s, '\ts_current_serial = std::move(new_serial);', '\tSyncWorkerThread();\n\tg_texture_cache->RemoveAll(true, false, true);\n\ts_current_serial = std::move(new_serial);')
path.write_text(s)

config = Path('pcsx2/Config.h')
s = config.read_text()
s = replace_once(s, '\t\ts8 OverrideTextureBarriers = -1;', '\t\ts32 TextureReplacementMethod = 0; // 0 Auto, 1 Legacy JD4029, 2 Current\n\t\ts8 OverrideTextureBarriers = -1;')
config.write_text(s)
config = Path('pcsx2/Pcsx2Config.cpp')
s = config.read_text()
s = replace_once(s, '\t\tOpEqu(UserHackOverrides) &&', '\t\tOpEqu(UserHackOverrides) &&\n\t\tOpEqu(TextureReplacementMethod) &&')
s = replace_once(s, '\t\t"OverrideTextureBarriers",', '\t\t"OverrideTextureBarriers",\n\t\t"TextureReplacementMethod",')
s = replace_once(s, '\t\t   OpEqu(OverrideTextureBarriers) &&', '\t\t   OpEqu(OverrideTextureBarriers) &&\n\t\t   OpEqu(TextureReplacementMethod) &&')
s = replace_once(s, '\tSettingsWrapBitBool(LoadTextureReplacements);', '\tSettingsWrapEntry(TextureReplacementMethod);\n\tif (TextureReplacementMethod < 0 || TextureReplacementMethod > 2) TextureReplacementMethod = 0;\n\tSettingsWrapBitBool(LoadTextureReplacements);')
config.write_text(s)

native = Path('platforms/android/app/src/main/cpp/native-lib.cpp')
s = native.read_text()
anchor = '        EmuConfig.GS.OverrideTextureBarriers    = saved_tex_barriers;'
# Snapshot this field wherever the existing live-apply code snapshots restart options.
line = next(line for line in s.splitlines() if 'saved_tex_barriers' in line and '=' in line and 'EmuConfig.GS.' in line and not line.strip().startswith('EmuConfig.'))
s = replace_once(s, line, line + '\n        const auto saved_texture_method = EmuConfig.GS.TextureReplacementMethod;')
s = replace_once(s, anchor, anchor + '\n        EmuConfig.GS.TextureReplacementMethod   = saved_texture_method;')
native.write_text(s)
print('Applied Auto/Legacy/Current hashing and restart-safe native config')
