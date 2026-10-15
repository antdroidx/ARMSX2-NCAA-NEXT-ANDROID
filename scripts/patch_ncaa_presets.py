"""Add NCAA filtering defaults and a claimable bilinear database key."""
from pathlib import Path
import re
from patch_core_efficiency import replace_once
from patch_conservative_gs import function


def patch(root):
    p = root / 'pcsx2/GameDatabase.h'
    s = p.read_text()
    # Append, so existing hardware-fix IDs and override bits retain their values.
    s = replace_once(s, '\t\tMoveHandler,\n\n\t\tCount', '\t\tMoveHandler,\n\t\tBilinearFiltering,\n\n\t\tCount')
    p.write_text(s)
    p = root / 'pcsx2/GameDatabase.cpp'
    s = p.read_text()
    s = replace_once(s, '\t"moveHandler",\n};', '\t"moveHandler",\n\t"bilinearFiltering",\n};')
    old = function(s, 'bool GameDatabaseSchema::isUserHackHWFix(')
    s = replace_once(s, old, replace_once(old, '\t\tcase GSHWFixId::TrilinearFiltering:', '\t\tcase GSHWFixId::BilinearFiltering:\n\t\tcase GSHWFixId::TrilinearFiltering:'))
    old = function(s, 'bool GameDatabaseSchema::GameEntry::configMatchesHWFix(')
    s = replace_once(s, old, replace_once(old, '\t\tcase GSHWFixId::TrilinearFiltering:', '\t\tcase GSHWFixId::BilinearFiltering:\n\t\t\treturn static_cast<int>(config.TextureFiltering) == value;\n\n\t\tcase GSHWFixId::TrilinearFiltering:'))
    old = function(s, 'void GameDatabaseSchema::GameEntry::applyGSHardwareFixes(')
    s = replace_once(s, old, replace_once(old, '\t\t\tcase GSHWFixId::TrilinearFiltering:', '''\t\t\tcase GSHWFixId::BilinearFiltering:
            {
                if (value >= static_cast<int>(BiFiltering::Nearest) &&
                    value <= static_cast<int>(BiFiltering::Forced_But_Sprite))
                    config.TextureFiltering = static_cast<BiFiltering>(value);
            }
            break;

\t\t\tcase GSHWFixId::TrilinearFiltering:'''))
    p.write_text(s)
    p = root / 'pcsx2/PerGameOverrides.cpp'
    s = p.read_text()
    anchor = '\t\t{"TriFilter", GSHWFixId::TrilinearFiltering, GSUserHackOverride::MaxCount},'
    p.write_text(replace_once(s, anchor, anchor + '\n\t\t{"filter", GSHWFixId::BilinearFiltering, GSUserHackOverride::MaxCount},'))
    p = root / 'platforms/android/app/src/main/java/com/armsx2/ui/settings/GameDbSection.kt'
    s = p.read_text()
    s = replace_once(s, '        "trilinearFiltering" -> "renderer.trilinear.label"', '        "bilinearFiltering" -> "renderer.textureFiltering.label"\n        "trilinearFiltering" -> "renderer.trilinear.label"')
    s = replace_once(s, '        "trilinearFiltering" -> pick(off, "PS2", str("fixes.opt.forced"))', '        "bilinearFiltering" -> pick("Nearest", "Forced", "PS2", "Sprite")\n        "trilinearFiltering" -> pick(off, "PS2", str("fixes.opt.forced"))')
    p.write_text(s)
    p = root / 'bin/resources/GameIndex.yaml'
    s = p.read_text()
    match = re.search(r'^SLUS-21214:\n.*?(?=^\S|\Z)', s, re.M | re.S)
    assert match and 'gsHWFixes:' not in match[0]
    addition = '''  # Extended defaults requested by antdroidx, 2026-10-15.
  # Existing VU clamp fix retained. Per-game filtering overrides take precedence.
  # Based on user-tested NCAA NEXT settings; this database wiring is source-tested.
  gsHWFixes:
    mipmap: 0 # Off.
    bilinearFiltering: 2 # PS2.
    trilinearFiltering: 1 # PS2 (when the user's selection is Auto).
'''
    p.write_text(s[:match.end()] + addition + s[match.end():])
    print('NCAA defaults: mipmapping Off, bilinear PS2, trilinear PS2; existing fixes retained')

if __name__ == '__main__':
    patch(Path.cwd())
