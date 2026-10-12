"""Add a persisted/scoped Android texture-method setting before verifier repair."""
from pathlib import Path
import re

p = Path('platforms/android/app/src/main/java/com/armsx2/config/Settings.kt')
s = p.read_text()
lines = []
count = 0
for line in s.splitlines(keepends=True):
    lines.append(line)
    if re.search(r'\bloadTextureReplacements\b', line):
        addition = line.replace('loadTextureReplacements', 'textureReplacementMethod')
        addition = addition.replace('LoadTextureReplacements', 'TextureReplacementMethod')
        addition = addition.replace('Boolean', 'Int').replace('boolAt(', 'intAt(')
        addition = addition.replace('optBoolean(', 'optInt(').replace('getBoolean(', 'getInt(')
        addition = addition.replace('= false,', '= 0,').replace('"bool"', '"int"')
        lines.append(addition)
        count += 1
if count != 8:
    raise RuntimeError(f'Unexpected pristine Settings shape: {count} texture entries')
p.write_text(''.join(lines))
p = Path('platforms/android/app/src/main/java/com/armsx2/ui/settings/RendererTab.kt')
s = p.read_text()
anchor = '            TextureManagerRow()'
block = '''            SegmentedGridRow(
                label = "Texture replacement method",
                options = listOf("Auto", "Legacy", "Current ARMSX2"),
                selectedIndex = s.textureReplacementMethod.coerceIn(0, 2),
                columns = 3,
                description = "Auto uses Legacy for NCAA 06/NEXT and Current for other games. Changes take effect after restarting the game.",
                onChange = { index -> apply(s.withJson { put("textureReplacementMethod", index) }) },
            )
            SettingsDivider()
'''
assert s.count(anchor) == 1
p.write_text(s.replace(anchor, block + anchor, 1))
p = Path('platforms/android/app/src/main/java/com/armsx2/ui/settingshub/SettingsResetFields.kt')
s = p.read_text()
assert s.count('"loadTextureReplacements",') == 1
p.write_text(s.replace('"loadTextureReplacements",', '"loadTextureReplacements", "textureReplacementMethod",', 1))
print('Added scoped Auto/Legacy/Current Android selector and persistence')
