"""Organize renderer controls and seed threaded Android defaults."""
from pathlib import Path

ROOT = Path('platforms/android/app/src/main/java/com/armsx2')
p = ROOT / 'ui/settings/RendererTab.kt'
s = p.read_text(encoding='utf-8')

def take(start, end):
    global s
    assert s.count(start) == 1 and s.count(end) == 1
    a, b = s.index(start), s.index(end)
    assert a < b
    block = s[a:b]
    s = s[:a] + s[b:]
    return block

thread = take('            // GS Multi-threading', '            // A value that matches no preset')
thread = thread[thread.index('            ToggleRow('):]
packs = take('            // Texture packs, right under', '            SegmentedRow(\n                label = str("renderer.displayMode.label")')
packs = packs[packs.index('            SettingsDivider()\n') + len('            SettingsDivider()\n'):]
packs = packs.removesuffix('            SettingsDivider()\n')
layout = take('            SegmentedRow(\n                label = str("renderer.displayMode.label")', '        }\n        SettingsDivider()\n        CollapsibleSection(str("renderer.section.texturesFiltering"))')
quality = take('            // Hardware & upscaling compatibility fixes', '            // GPU profile override.')
quality = quality[quality.index('            ToggleRow('):]
quality = quality.removesuffix('            SettingsDivider()\n')
s = s.replace('            // GPU profile override.', '            SettingsDivider()\n            // GPU profile override.', 1)
performance = take('            SegmentedRow(\n                label = str("renderer.texturePreloading.label")', '        }\n        SettingsDivider()\n        CollapsibleSection(str("renderer.section.displayEffects"))')
performance = performance.removesuffix('            SettingsDivider()\n')
anchor = '        CollapsibleSection(str("renderer.section.texturesFiltering")) {'
assert s.count(anchor) == 1
s = s.replace(anchor, '        CollapsibleSection(str("renderer.section.texturesFiltering"), initiallyExpanded = true) {\n' + quality + '\n            SettingsDivider()', 1)
anchor = '        CollapsibleSection(str("renderer.section.displayEffects")) {'
sections = ('        CollapsibleSection("Texture packs") {\n' + packs + '\n        }\n'
            '        SettingsDivider()\n        CollapsibleSection("Renderer performance") {\n' + thread + performance + '\n        }\n'
            '        SettingsDivider()\n        CollapsibleSection("Screen layout") {\n' + layout + '\n        }\n        SettingsDivider()\n')
s = s.replace(anchor, sections + anchor, 1)
p.write_text(s, encoding='utf-8')

p = ROOT / 'config/Settings.kt'
s = p.read_text(encoding='utf-8')
old = 'val gsBackThreadMode: Int = if (com.armsx2.BuildConfig.QUEST_VR) 3 else 0'
assert s.count(old) == 1
s = s.replace(old, 'val gsBackThreadMode: Int = 3')
assert s.count('            mtvu = mtvu,') == 1
s = s.replace('            mtvu = mtvu,', '            mtvu = mtvu,\n            gsBackThreadMode = 3,')
p.write_text(s, encoding='utf-8')

p = ROOT / 'DeviceTier.kt'
s = p.read_text(encoding='utf-8')
a = s.index('    /** MTVU (multi-threaded VU1)')
b = s.index('    /** Total physical RAM', a)
s = s[:a] + '    /** Extended defaults to threaded VU1 on every device; users can override it. */\n    fun mtvuDefault(): Boolean = true\n\n' + s[b:]
p.write_text(s, encoding='utf-8')

p = ROOT / 'ui/settings/PerformanceTab.kt'
s = p.read_text(encoding='utf-8')
assert s.count('mtvu = true,') == 3
s = s.replace('mtvu = true,', 'mtvu = true, gsBackThreadMode = 3,')
s = s.replace('Low-End = every cheap GPU/CPU lever, MTVU gated on core count.', 'Low-End = cheaper GPU/CPU settings with threading enabled.')
p.write_text(s, encoding='utf-8')
print('Grouped renderer controls; GS and VU1 threading enabled in defaults and presets')
