# Native port investigation — October 10, 2026

The analysis below preceded native implementation. A subsequent first-stage native allocation probe is described in RAM_ALLOCATION_PROBE.md: four allocation/initialization instructions changed and an APK was built. Guest EE RAM remains 32MiB; the full 128MiB port is incomplete. The earlier control still contains stock Classic emucore.

## User-supplied 2.2n target

Downloaded https://github.com/Trixarian/NetherSX2-classic/releases/download/2.2n/NetherSX2-v2.2n-3668.apk and decoded it separately. APK SHA256 is 8b502b31ce797d5a162bc6b9300b5f02351b0b6b290b8dc1390b8dfb826673ab. Native SHA256 is 4e378da548984dc0208ff2240aae003942ae9c5a6eec3a36c838c65ac6a37a63.

Both versions' native files are 12,094,744 bytes. They differ at only 45 byte positions, grouped into three version-label strings in .rodata at offsets 0xcdcba, 0xdac5e and 0xff022. Every executable ELF section is byte-for-byte identical. All remaining file bytes are identical as well. Therefore the earlier native instruction addresses also apply to this exact 2.2n input; the newer APK does not provide a different native RAM implementation. Android code/assets may differ and were not claimed identical.

Use 2.2n as the selected native patch base going forward. The deliverable must include substantive libemucore.so changes and verified NEXT behavior; another relabeled APK would not satisfy the request. Input, byte-range comparison and complete section comparison are saved in diagnostics/classic-2.2n-input.json, classic-native-version-diff.json and classic-native-section-diff.json. No native patch has yet been produced.

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

### Further RAM and folder tracing

Used ELF unwind FDEs to recover containing function ranges: reset-related routine 0x6e70c0..0x6e8440, memory-manager constructor 0x4c81d0..0x4c8638, and folder-open routine beginning 0x48bfc0. Full instructions and raw bytes are retained under diagnostics/native-ram/. These labels describe the analysis anchors, not recovered source-level function names.

PLT relocation lookup resolves 0xb483e0=posix_memalign, 0xb490f0=memset, 0xb48510=mprotect and 0xb473b0=fread. This narrows previously tentative call semantics:

- 0x6e7470 supplies a 32MiB allocation length in w2 to posix_memalign. Result is stored at 0x28a58d0.
- 0x6e7498 supplies an 81MiB allocation length (0x5100000) to posix_memalign. Result is stored at 0x28a58d8.
- 0x6e7d98, 0x6e7d9c and 0x6e7da8 form offsets of 64MiB, 72MiB and 80MiB from the second allocation. This is consistent with 8-byte recompiler entries per 4-byte guest instruction followed by ROM tables.
- 0x6e81b8 loads 0xa20000 and uses a vector pointer-fill loop covering 81MiB. 0x6e81ec supplies 32MiB to memset. These independently constrain allocation and initialization sizes.
- 0x6e8260 supplies a 32MiB length to mprotect; 0x6e8280 passes 32MiB to another internal memory-protection routine. Their callers and shared page-tracking data still need complete analysis.

With the apparent table layout, expanding guest EE RAM from 32 to 128MiB would increase the table allocation from 81 to 273MiB and move its following ROM tables by 192MiB. That calculation alone does not establish the complete native patch: host RAM commit/layout, every alias and access check, generated code, snapshots, manual tracking and DMA must agree.

In folder-open code, 0x48c498 loads 0x2000 as the size argument to fread while reading _pcsx2_superblock. Other nearby 0x2000 constants are memset lengths for fixed buffers. They are NOT 8MiB card-capacity constants and must not be widened to force 64MiB cards. This illustrates why a global binary constant substitution cannot implement the requested features.

The read-only map script also inventories 1043 exact occurrences of selected memory-size/mask constants across the native text section. These include unrelated functions and are candidates for classification, not patch sites. No bulk substitution was applied.

ADB check again returned an empty connected-device list. A verified working native APK cannot be established here without a test target and the incomplete native mapping cannot yet support a coherent patch. The earlier control APK remains unchanged.

### Host-pointer relocation resolution

Resolved the actual ELF dynamic relocations used by the memory-manager constructor. GOT slots 0xb83070..0xb830b8 identify EEmem, IOPmem, VUmem, EErec, IOPrec, VIF0rec, VIF1rec, mVU0rec, mVU1rec and bumpAllocator. The exported EEmem pointer is stored at native address 0x2605d80; IOPmem at 0x2605d88. The constructor's 64MiB offset really is the start of IOP host memory, not an arbitrary unused allocation. These names are relocation-backed evidence, not guessed labels. Full resolution is in diagnostics/native-ram/exported-memory-globals.json.

This makes a blanket MainRam expansion particularly unsafe: the native host-region layout, guest mapping, embedded non-RAM offsets and all consumers of these pointers must be coordinated. The existing binary patch investigation has not reconstructed those consumers fully. No native constant edit or 128MB APK has been emitted.

The native investigation established specific places to continue analysis, but not a coherent patch. A matching 3668 native source/relink package would materially shorten the work. Otherwise a full native reverse-engineering and runtime-validation effort remains necessary. No unverified constant substitution or fabricated NEXT support was shipped.

Reproduce inventory with Python packages pyelftools==0.33 and capstone==5.0.9 installed into analysis-tools/, then run scripts/inspect_classic_native.py and scripts/trace_classic_native.py. These scripts are read-only for the native input and write evidence JSON files only.
