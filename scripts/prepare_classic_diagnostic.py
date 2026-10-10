"""Prepare an isolated Classic shell control. Does not port native NEXT features."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parents[1]
decoded = root / 'classic-clean'
package = 'com.ncaanext.classic3668.diagnostic'
android = '{http://schemas.android.com/apk/res/android}'
ET.register_namespace('android', android[1:-1])
manifest = decoded / 'AndroidManifest.xml'
tree = ET.parse(manifest)
node = tree.getroot()
original = node.attrib['package']
assert original in ('xyz.aethersx2.android', package)
node.set('package', package)
app = node.find('application')
app.set(android + 'label', 'NEXT Classic 3668 Control')
for item in app:
    if item.get(android + 'label') == 'NetherSX2 Classic':
        item.set(android + 'label', 'NEXT Classic 3668 Control')
    authority = item.get(android + 'authorities')
    if authority:
        item.set(android + 'authorities', authority.replace('xyz.aethersx2.android', package))
    name = item.get(android + 'name', '')
    assert not name.startswith('.'), 'Qualify component names before changing package'
tree.write(manifest, encoding='utf-8', xml_declaration=True)

# Keep original Java/JNI class names: renaming them would break native bindings.
# Adjust explicit app package strings (intents, FileProvider, storage), not class descriptors.
changed = []
for path in decoded.glob('smali*/**/*.smali'):
    value = path.read_text(encoding='utf-8')
    updated = value.replace('"xyz.aethersx2.android"', '"' + package + '"')
    updated = updated.replace('"xyz.aethersx2.android.androidx-startup"', '"' + package + '.androidx-startup"')
    if updated != value:
        path.write_text(updated, encoding='utf-8')
        changed.append(str(path.relative_to(decoded)))

native = {}
with zipfile.ZipFile(root / 'classic-base.apk') as apk:
    for name in apk.namelist():
        if name.startswith('lib/') and name.endswith('.so'):
            data = apk.read(name)
            assert (decoded / name).read_bytes() == data, name
            native[name] = hashlib.sha256(data).hexdigest()
evidence = root / 'diagnostics'
evidence.mkdir(exist_ok=True)
(evidence / 'classic-input.json').write_text(json.dumps({
    'url': 'https://github.com/Trixarian/NetherSX2-classic/releases/download/2.1/NetherSX2-v2.1-3668.apk',
    'apk_sha256': hashlib.sha256((root / 'classic-base.apk').read_bytes()).hexdigest(),
    'application_id': package, 'native_sha256': native,
    'changed_smali': changed, 'native_next_features_ported': False,
    'runtime_validated': False,
}, indent=2) + '\n')
print('Prepared isolated shell control; native features remain unported.')
