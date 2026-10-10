# Native port investigation — October 10, 2026

No native changes applied; no new APK produced in this investigation. Existing control remains stock Classic emucore. This report records native evidence rather than claiming a completed port.

## Exact native input

Official Classic 2.1 / 3668 libemucore.so SHA256:
e0cb61cb15bbb14f04faed8b1587def75558c15b0e5a43c5313f5406d5810deb.

ELF machine: AArch64. Only .dynsym is present (2706 entries); no full .symtab. Publicly exported memory-card JNI methods remain named, but CPU/texture-cache implementation functions are not exposed under their source names. Complete section/symbol/string inventory is in diagnostics/classic-native-inventory.json.

## Concrete findings

1. The native binary contains no ASCII ExtraMemory, ExposedRam or memSetExtraMemMode string in the inspected inventory. This does not prove the absence of every possible extended-memory path, but it does mean the modern PCSX2 ExtraMemory option cannot be assumed to exist or be activated by adding an INI key.
2. The string EE/iR5900-ARM64 Recompiler Reset has a direct ADRP/ADD reference at virtual address 0x6e819c. Nearby instructions load w2=0x02000000 (32MiB) at 0x6e81ec and call 0xb490f0 at 0x6e81f0. This is consistent with a fixed 32MiB clear in the reset path. The complete object/argument semantics still require tracing; this is not an approved patch site.
3. The same path uses a fixed count 0xa20000 at 0x6e81b8 in a pointer-fill loop. Changing a clear length alone cannot extend all lookup tables, snapshot buffers and page/alias tracking safely. The surrounding disassembly is preserved in diagnostics/classic-native-xrefs.json.
4. EE Main Memory is referenced at 0x4c8444 in native memory-manager setup. That code also establishes multiple fixed offsets (64MiB, 96MiB, 104MiB, 112MiB, 128MiB, 176MiB and 256MiB nearby). These are host layout offsets, not proof of exposed guest RAM. Expanding a region blindly could overlap another native allocation.
5. FolderMemoryCard and FolderMemoryCardAggregator RTTI names, a folder-card parse-error string and memory-card JNI methods exist. The earlier wording that no folder implementation was available meant no verified source/geometry patch; the binary DOES contain folder-card code. Its guest capacity/FAT geometry is still unverified.
6. Native texture replacement load/async/precache setting strings and texture-cache/replacement type names exist. Settings-reader references are preserved at 0x4ab2e8 and 0x4ab390. Exact TCC filename bits and hashing behavior still need function identification and known-input comparison; no JD4029 compatibility change has been applied.

String-reference scanning only locates direct nearby ADRP/ADD candidates. It is not a complete control/data-flow analysis and does not cover indirect pointers or every compiler addressing pattern.

## Published LGPL source route checked

Inspected https://github.com/Trixarian/AetherSX2 at commit 1d1f795dfc70e38da67724c7298779260f513889.
Its README explicitly describes a partial release with non-LGPL components supplied for relinking. It includes Memory.cpp, MemoryTypes.h, folder-card source and a 5,439,328-byte libAetherSX2.a archive. This is useful reference material, but not established as the matching 3668 core:

- Source MemoryTypes.h defines fixed 32MiB MainRam and places Scratch/ROM buffers directly after it in EEVM_MemoryAllocMess.
- Source GS tree has Common/DX11/HW/Null/OpenGL/SW directories; Vulkan implementation symbols live in the binary archive.
- No GSTextureReplacements source is present in this snapshot, while the actual 3668 library has native texture-replacement type names.
- The archive contains EE/iR5900-32 Recompiler Reset; the actual target contains EE/iR5900-ARM64 Recompiler Reset.

Therefore relinking that archive with a changed MainRam constant is not a verified 3668 port: its compiled ARM CPU/graphics components would retain their own layout/size assumptions. No build of this mismatched source was presented as Classic 3668.

## Required work before a native candidate

Identify and trace target allocation/commit, guest physical and virtual RAM mapping, ARM64 lookup-table allocation and fill, aliases, snapshots, manual SMC/page counters, generated-code address masks and DMA/BIOS memory-size paths. Identify serialized memory lengths and cross-version save behavior. All must agree before testing 128MiB. Modern ARMSX2 source edits cannot be applied to stripped binary addresses without this mapping.

For hash compatibility, identify texture key mask/serialization/parser and raw-block hash functions; prove known source GS texture/CLUT inputs produce the JD4029 filename. For folder cards, trace creation/open geometry and FAT bounds. For Close/Reset, trace Classic's own run-thread ownership and JNI lifecycle before adding the ARMSX2-style barrier.

Hardware validation must exercise independent writes/reads above 32MiB, absence of low-memory aliasing, execution in extended RAM, DMA and restart/reset. No connected target, BIOS/game assets or runtime trace was available; none of these tests passed or ran here.

## Current boundary

The native investigation established specific places to continue analysis, but not a coherent patch. A matching 3668 native source/relink package would materially shorten the work. Otherwise a full native reverse-engineering and runtime-validation effort remains necessary. No unverified constant substitution or fabricated NEXT support was shipped.

Reproduce inventory with Python packages pyelftools==0.33 and capstone==5.0.9 installed into analysis-tools/, then run scripts/inspect_classic_native.py and scripts/trace_classic_native.py. These scripts are read-only for the native input and write evidence JSON files only.
