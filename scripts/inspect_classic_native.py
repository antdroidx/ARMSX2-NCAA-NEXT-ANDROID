"""Read-only ELF inventory; no offsets or constants are patched."""
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis-tools'))
from elftools.elf.elffile import ELFFile

root = Path(__file__).resolve().parents[1]
path = root / 'classic-clean/lib/arm64-v8a/libemucore.so'
data = path.read_bytes()
pattern = re.compile(r'ExtraMemory|ExposedRam|memSetExtra|memGetExtra|128MB|128 MB|HashTexture|TextureReplacement|FolderMemory|MemoryCard|Recompiler|MainRam|EE RAM|GS RAM|GS memory|memory map|Allocating|32 MB', re.I)
with path.open('rb') as stream:
    elf = ELFFile(stream)
    sections = [{'name': s.name, 'address': hex(s['sh_addr']), 'size': s['sh_size'],
                 'offset': hex(s['sh_offset'])} for s in elf.iter_sections()]
    symbols = []
    counts = {}
    for section in elf.iter_sections():
        if section['sh_type'] in ('SHT_SYMTAB', 'SHT_DYNSYM'):
            counts[section.name] = section.num_symbols()
            for symbol in section.iter_symbols():
                if pattern.search(symbol.name):
                    symbols.append({'name': symbol.name, 'address': hex(symbol['st_value']),
                                    'size': symbol['st_size'], 'table': section.name})
    strings = []
    for match in re.finditer(rb'[\x20-\x7e]{5,}', data):
        value = match.group().decode('ascii')
        if pattern.search(value):
            address = None
            for section in elf.iter_sections():
                if section['sh_offset'] <= match.start() < section['sh_offset'] + section['sh_size']:
                    address = section['sh_addr'] + match.start() - section['sh_offset']
                    break
            strings.append({'offset': hex(match.start()), 'address': hex(address) if address else None,
                            'text': value})
    report = {'sha256': hashlib.sha256(data).hexdigest(), 'machine': elf['e_machine'],
              'symbol_counts': counts, 'sections': sections, 'matching_symbols': symbols,
              'matching_strings': strings, 'changes_applied': False}
out = root / 'diagnostics/classic-native-inventory.json'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'machine': report['machine'], 'symbol_counts': counts,
                  'matching_symbols': symbols, 'matching_strings': strings}, indent=2))
