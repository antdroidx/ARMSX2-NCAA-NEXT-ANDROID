#!/usr/bin/env python3
"""Apply Extended launcher branding to the pinned upstream Android source."""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

res = Path('platforms/android/app/src/main/res')
assets = Path(__file__).resolve().parents[1] / 'branding'
icon = assets / 'savetowerforeground-purple.png'
if not icon.is_file():
    raise SystemExit(f'Missing Extended icon: {icon}')
changed = 0
for strings in res.glob('values*/strings.xml'):
    tree = ET.parse(strings)
    for node in tree.getroot().findall('string'):
        if node.get('name') == 'app_name':
            node.text = 'ARMSX2 Extended'
            changed += 1
        elif node.get('name') == 'app_name_nightly':
            node.text = 'ARMSX2 Extended Nightly'
    tree.write(strings, encoding='utf-8', xml_declaration=True)
if changed == 0:
    raise SystemExit('Missing upstream app_name resource')
shutil.copy2(icon, res / 'drawable/savetowerforeground.png')
background = res / 'drawable/ic_launcher_background.xml'
text = background.read_text()
for old, new in [('#061021', '#100621'), ('#0B1D38', '#210B38'), ('#102B50', '#371050')]:
    if old not in text and new not in text:
        raise SystemExit(f'Unexpected launcher background: missing {old}')
    text = text.replace(old, new)
background.write_text(text)
print('Applied ARMSX2 Extended label and purple launcher artwork')
