"""Resolve exported host-memory pointers used by Classic's memory constructor."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis-tools'))
from elftools.elf.elffile import ELFFile

root = Path(__file__).resolve().parents[1]
path = root / 'classic-2.2n-decoded/lib/arm64-v8a/libemucore.so'
expected = '4e378da548984dc0208ff2240aae003942ae9c5a6eec3a36c838c65ac6a37a63'
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
targets = {0xb83070, 0xb83078, 0xb83080, 0xb83088, 0xb83090,
           0xb83098, 0xb830a0, 0xb830a8, 0xb830b0, 0xb830b8}
report = []
with path.open('rb') as stream:
    elf = ELFFile(stream)
    for section in elf.iter_sections():
        if section['sh_type'] != 'SHT_RELA':
            continue
        symbols = elf.get_section(section['sh_link'])
        for relocation in section.iter_relocations():
            if relocation['r_offset'] in targets and relocation['r_info_sym']:
                symbol = symbols.get_symbol(relocation['r_info_sym'])
                report.append({'got_address': hex(relocation['r_offset']),
                               'name': symbol.name, 'symbol_address': hex(symbol['st_value']),
                               'symbol_size': symbol['st_size']})
assert len(report) == len(targets)
out = root / 'diagnostics/native-ram/exported-memory-globals.json'
out.write_text(json.dumps({'input_sha256': expected, 'globals': report}, indent=2) + '\n')
print(json.dumps(report, indent=2))
