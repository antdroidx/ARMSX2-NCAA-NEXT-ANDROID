"""Apply only paired recompiler allocation/initialization changes.

This stage deliberately leaves guest RAM at 32MiB. It is NOT NEXT128 support.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis-tools'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

root = Path(__file__).resolve().parents[1]
decoded = root / 'classic-2.2n-decoded'
library = decoded / 'lib/arm64-v8a/libemucore.so'
expected = '4e378da548984dc0208ff2240aae003942ae9c5a6eec3a36c838c65ac6a37a63'
data = bytearray(library.read_bytes())
assert hashlib.sha256(data).hexdigest() == expected, 'Require freshly decoded exact 2.2n input'
with library.open('rb') as stream:
    elf = ELFFile(stream)
    text = elf.get_section_by_name('.text')
    text_address, text_offset = text['sh_addr'], text['sh_offset']

# ARM64 MOVZ Wd,#imm16,LSL#16. Keep destination/opcode unchanged.
sites = [
    (0x6e7470, 0x0200, 0x0800, 'Snapshot allocation: 32MiB -> 128MiB'),
    (0x6e7498, 0x0510, 0x1110, 'Table allocation capacity: 81MiB -> 273MiB'),
    (0x6e81b8, 0x00a2, 0x0222, 'Table initialization: 81MiB -> 273MiB'),
    (0x6e81ec, 0x0200, 0x0800, 'Snapshot initialization: 32MiB -> 128MiB'),
]
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
changes = []
for address, old_imm, new_imm, purpose in sites:
    offset = address - text_address + text_offset
    old = struct.unpack_from('<I', data, offset)[0]
    assert old & 0xffe00000 == 0x52a00000, hex(address)
    assert (old >> 5) & 0xffff == old_imm, hex(address)
    new = (old & ~(0xffff << 5)) | (new_imm << 5)
    before = next(md.disasm(struct.pack('<I', old), address))
    after = next(md.disasm(struct.pack('<I', new), address))
    struct.pack_into('<I', data, offset, new)
    changes.append({'address': hex(address), 'file_offset': hex(offset),
                    'old_bytes': struct.pack('<I', old).hex(),
                    'new_bytes': struct.pack('<I', new).hex(),
                    'old_instruction': before.mnemonic + ' ' + before.op_str,
                    'new_instruction': after.mnemonic + ' ' + after.op_str,
                    'purpose': purpose})

# Do not alter table ROM offsets/page maps/protection: the first-stage probe
# must keep the existing retail guest layout internally consistent.
library.write_bytes(data)
android = '{http://schemas.android.com/apk/res/android}'
ET.register_namespace('android', android[1:-1])
manifest = decoded / 'AndroidManifest.xml'
tree = ET.parse(manifest)
node = tree.getroot()
assert node.get('package') == 'xyz.aethersx2.android'
package = 'com.ncaanext.classic3668.ramprobe'
node.set('package', package)
app = node.find('application')
app.set(android + 'label', 'Classic RAM Allocation Probe')
for component in app:
    assert not component.get(android + 'name', '').startswith('.')
    if component.get(android + 'label') == 'NetherSX2 Classic':
        component.set(android + 'label', 'Classic RAM Allocation Probe')
    authority = component.get(android + 'authorities')
    if authority:
        component.set(android + 'authorities', authority.replace('xyz.aethersx2.android', package))
tree.write(manifest, encoding='utf-8', xml_declaration=True)
for path in decoded.glob('smali*/**/*.smali'):
    source = path.read_text(encoding='utf-8')
    updated = source.replace('"xyz.aethersx2.android"', '"' + package + '"')
    if updated != source:
        path.write_text(updated, encoding='utf-8')
report = {'input_native_sha256': expected, 'output_native_sha256': hashlib.sha256(data).hexdigest(),
          'package': package, 'changes': changes, 'guest_ram_mib': 32,
          'snapshot_capacity_mib': 128, 'table_capacity_mib': 273,
          'extra_host_capacity_mib': 288, 'next128_supported': False,
          'runtime_tested': False, 'known_limitations': [
              'Guest RAM mapping remains 32MiB; NEXT27 extended-memory gameplay is not supported.',
              'Signature/package assumptions may prevent launch.',
              'Allocation overhead may cause low-memory termination; no ARM64 device test ran.'
          ]}
(root / 'diagnostics/ram-allocation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
