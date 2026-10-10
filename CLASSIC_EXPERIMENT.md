# Classic 3668 experiment — incomplete native port

This branch contains an isolated Classic **shell control**, not a completed NCAA NEXT native port. No runtime rendering result has been measured. Original ARMSX2 checkout and synced sources were left untouched.

## Inputs and baseline distinction

- Private source project: antdroidx/ARMSX2-NCAA-NEXT-ANDROID.
- Experiment branch: codex/nether-classic-3668, based on refreshed origin/main e148ebc77d31bf3d6b425d4efd49988ff0831166.
- Existing local main remains b719ea9242ed4f0f5d0a8c3dcd0b7c8f88549d04, containing the merged 128105 enhancements. Refreshed remote main contains a different lifecycle branch history. Do not interpret remote main as identical to the validated local 128105 build.
- ARMSX2 core pin: f4904cb5e3b322178e3815683e221f3ab9354d2e.
- Classic patch repository: Trixarian/NetherSX2-classic at 98ddad36d6c367a045b65fd06fdb26ba4c611387.
- Control input: official stable NetherSX2-v2.1-3668.apk. Input APK/native SHA256 identities are recorded in diagnostics/classic-input.json.

Classic provides compiled AetherSX2 emucore and APK patch tools, not a native C++ source tree. Its decomp/Extract.bat, Hackify.bat and Pack.bat reference **4248**, so they cannot safely be applied to 3668. old/scripts/patch-apk.bat uses a 3668 xdelta and updates assets/signing. An archived patch tool is not evidence of native NEXT support.

## Feature comparison

| Requirement | ARMSX2 implementation | Classic feasibility/status |
|---|---|---|
| 128MB EE/NEXT | ARM64 LUT, SMC tracking, snapshot and mapping spans; extra-memory enabled; softmem diagnostic | No equivalent native source available. Allocation, address translation, recompilers and saves must all be verified. A settings toggle alone does not establish support. Unported. |
| JDHalfrack 1.7.4029 hashes | TCC filename/key preservation, legacy full texture hashing, region hashing disabled | Classic texture replacement UI exists, but exact native algorithm cannot be established from shell source. Validate replacement hit/miss against known files. Unported/unverified. |
| 64MB folder cards | Native FolderMemoryCard geometry of 65536 clusters with FAT guards | File-backed 64MB cards and folder cards are different features. No verified Classic folder implementation or geometry patch. Unported. |
| Close/Reset | Kotlin completion barrier plus CPU-owner native stop in local 128105 | Different Java/JNI frontend; ARMSX2 shutdown patch targets kr.co.iefriends.pcsx2, Classic uses xyz.aethersx2.android. Cannot transplant the barrier/native stop by renaming. Test Classic native lifecycle independently. |
| Signing/updates | Stable project certificate and ARMSX2 package/version rules | Control has distinct package com.ncaanext.classic3668.diagnostic and separate diagnostic certificate. Production ARMSX2 certificate/cache not used. Preserve the diagnostic key for updates. |
| GS diagnostics | Editable native texture/cache/shader/blend paths | Preserve stock Classic native library for control. Logcat/screenshot collection available; per-draw native instrumentation unavailable without further native analysis. |
| 4KB/16KB pages | Current ARMSX2 dual-library build | Classic ELF compatibility needs separate verification; repackaging does not repair native page alignment. |

## Control build

Keep APKs, decoded tree and key local; do not commit them. Use Java, Python, Android SDK zipalign/apksigner, and the inspected Classic apktool jar. All build logs are retained locally.

1. Download the exact official input URL recorded above to classic-base.apk.
2. Decode with apktool `d -p framework -o classic-clean classic-base.apk`.
3. Run `python scripts/prepare_classic_diagnostic.py`. It preserves Java/JNI class names, changes manifest application identity/provider authority and explicit app-package strings, and records native hashes.
4. Build with apktool `b -p framework --use-aapt2 -o classic-control-unsigned.apk classic-clean`.
5. Align, sign with a separate persistent diagnostic key, verify signature and package, and compare every packaged native library hash to the input manifest.

Native code may contain hardcoded original-package or signature assumptions. Static APK verification is insufficient to establish launch or gameplay. No device was attached at preparation time. Do not call this a working NEXT 27 build.

## A/B procedure

Use separate app storage and copied in-game saves/cards. Do not share writable cards between concurrently running emulators or use cross-core savestates. Start with a game/scene that does not require unverified extended RAM. NEXT 27 testing is gated on demonstrating 128MB reads/writes/execution above 32MB.

Record exact APK/certificate hashes, device/OS/GPU/driver, resolution, renderer, blending accuracy, download mode, texture pack/PNG hashes, async setting, game/ISO identity, and scene. Copy effective settings/configs from each app's export function. Hold these constant and restart between runs.

Capture WSU logo and menu background, broadcast logo/scoreboard/background, USC away cardinal and home gold controls. For each: replacements off, on with synchronous loading, then async on. Capture Vulkan and OpenGL separately when both are supported. Record replacement misses rather than interpreting missing art as correct blending. Use the same in-game save/camera and preserve original PNGs.

Run scripts/capture_classic_ab.py with explicit adb path, serial, variant, scene and notes while the scene is visible. It saves full existing logcat without clearing it, screenshot, package info, device properties and memory summary. Add app-exported emulator logs/settings to that capture folder. Redact personal device data before sharing logs.

Matching GS-path evidence should include texture/CLUT key and hit/miss, decoded/uploaded RGBA, TCC/TFX, palette selector, alpha bounds, vertex RGBA, ALPHA A/B/C/D/FIX, destination format/alpha, shader permutation and final blend path. Existing investigation-usc contains ARMSX2 trace work. Classic stock logcat may not expose these values: absence is not proof of parity. Preserve GS dumps if exposed and use compatible tools; no draw-level comparison was performed here.

## Remaining blockers

A feature-complete port needs 3668 native source or a separately scoped, verified native binary engineering effort for extended RAM/hash/card/lifecycle changes. The control APK only isolates stock Classic behavior. Connected hardware, licensed local game/BIOS and exact scene inputs are required to complete launch and graphical A/B verification.

Subsequent native inspection is recorded in NATIVE_PORT_FINDINGS.md. Folder-card code was identified in the actual target binary; its capacity remains unverified. A published partial LGPL source/relink package was also inspected, but has not been established as matching 3668.
