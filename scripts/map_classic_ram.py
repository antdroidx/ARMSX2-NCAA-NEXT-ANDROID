"""Disassemble target RAM functions and inventory size constants; never patch."""
import bisect
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis-tools'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

root = Path(__file__).resolve().parents[1]
path = root / 'classic-2.2n-decoded/lib/arm64-v8a/libemucore.so'
assert hashlib.sha256(path.read_bytes()).hexdigest() == '4e378da548984dc0208ff2240aae003942ae9c5a6eec3a36c838c65ac6a37a63'
out = root / 'diagnostics/native-ram'
out.mkdir(exist_ok=True)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
with path.open('rb') as stream:
    elf = ELFFile(stream)
    section = elf.get_section_by_name('.text')
    code, base = section.data(), section['sh_addr']
    plt = elf.get_section_by_name('.plt')
    relocations = elf.get_section_by_name('.rela.plt')
    symbols = elf.get_section(relocations['sh_link'])
    imports = {plt['sh_addr'] + 32 + 16 * index:
               symbols.get_symbol(relocation['r_info_sym']).name
               for index, relocation in enumerate(relocations.iter_relocations())}
    fdes = sorted((x['initial_location'], x['address_range'])
                  for x in elf.get_dwarf_info().EH_CFI_entries()
                  if hasattr(x, 'header') and 'initial_location' in x.header)
    starts = [x[0] for x in fdes]
    def function_at(address):
        index = bisect.bisect_right(starts, address) - 1
        if index >= 0:
            start, size = fdes[index]
            if address < start + size:
                return start, size
        return None
    anchors = {'ee-reset': 0x6e819c, 'memory-manager': 0x4c8444,
               'folder-open': 0x48c2f8, 'folder-superblock': 0x48c430}
    functions = {}
    for label, address in anchors.items():
        start, size = function_at(address)
        instructions = list(md.disasm(code[start-base:start-base+size], start))
        def line(i):
            annotation = ''
            if i.mnemonic == 'bl' and i.op_str.startswith('#0x'):
                name = imports.get(int(i.op_str[1:], 16))
                if name:
                    annotation = ' ; import ' + name
            return f'{i.address:#010x} {i.bytes.hex():8} {i.mnemonic:8} {i.op_str}{annotation}'
        (out / (label + '.txt')).write_text('\n'.join(line(i) for i in instructions) + '\n')
        functions[label] = {'start': hex(start), 'size': size,
                            'direct_calls': sorted(set(i.op_str for i in instructions if i.mnemonic == 'bl'))}
    constants = []
    needles = re.compile(r'#0x(?:2000000|1ffffff|8000000|7ffffff|a20000)(?![0-9a-f])')
    # This inventory cannot establish what each occurrence means. Host allocation,
    # guest masks and unrelated graphics constants must be distinguished manually.
    for address, size, mnemonic, operands in md.disasm_lite(code, base):
        if needles.search(operands):
            owner = function_at(address)
            constants.append({'address': hex(address), 'mnemonic': mnemonic, 'operands': operands,
                              'owner': hex(owner[0]) if owner else None})
    report = {'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'functions': functions, 'constant_candidates': constants,
              'imported_call_targets': {hex(k): v for k, v in imports.items()
                                       if k in (0xb483e0, 0xb490f0, 0xb48510, 0xb473b0)},
              'patch_ready': False}
    (out / 'map.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'functions': functions, 'constant_count': len(constants)}, indent=2))
