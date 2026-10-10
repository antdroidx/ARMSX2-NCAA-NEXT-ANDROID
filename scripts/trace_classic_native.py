"""Locate direct ARM64 ADRP/ADD string references for manual native analysis."""
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis-tools'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

root = Path(__file__).resolve().parents[1]
path = root / 'classic-2.2n-decoded/lib/arm64-v8a/libemucore.so'
targets = {0x121bdd: 'EE Main Memory', 0xc9ccf: 'IOP Main Memory',
           0x108396: 'EE ARM64 reset', 0x13a1d9: 'FolderMemoryCard RTTI',
           0x11ea44: 'PrecacheTextureReplacements', 0xeb208: 'LoadTextureReplacements',
           0xcd548: 'Folder card open log', 0xfbac6: 'Folder card superblock file',
           0xff2a6: 'Folder card indexing', 0xf8be3: 'Folder card indexing unfiltered'}
pages = {a & ~4095 for a in targets}
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
report = []
with path.open('rb') as f:
    elf = ELFFile(f)
    section = elf.get_section_by_name('.text')
    code, base = section.data(), section['sh_addr']
    for off in range(0, len(code) - 48, 4):
        word = struct.unpack_from('<I', code, off)[0]
        if word & 0x9f000000 != 0x90000000:
            continue
        immediate = ((word >> 5 & 0x7ffff) << 2) | (word >> 29 & 3)
        if immediate & (1 << 20):
            immediate -= 1 << 21
        address = ((base + off) & ~4095) + (immediate << 12)
        if address not in pages:
            continue
        reg = word & 31
        for distance in range(4, 48, 4):
            following = struct.unpack_from('<I', code, off + distance)[0]
            if following & 0xffc00000 == 0x91000000 and (following >> 5 & 31) == reg:
                target = address + (following >> 10 & 4095)
                if target in targets:
                    start = max(0, off - 64)
                    lines = [f'{i.address:#x}: {i.mnemonic} {i.op_str}'
                             for i in md.disasm(code[start:off + 160], base + start)]
                    report.append({'label': targets[target], 'instruction': hex(base + off),
                                   'context': lines})
                break
out = root / 'diagnostics/classic-native-xrefs.json'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
