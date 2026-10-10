# Native RAM allocation probe — first stage only

This APK contains a changed libemucore.so based on the exact official Classic 2.2n 3668 core. It is not another stock-core repackaging. **Guest EE RAM is still 32MiB. This APK does not support NEXT27 extended-memory gameplay.**

The experiment expands the independently allocated recompiler snapshot buffer from 32 to 128MiB and its table capacity from 81 to 273MiB. Paired initialization lengths are changed with the allocations. Four ARM64 instructions change; all other native bytes remain unchanged. This adds up to 288MiB of touched host memory when these paths run. Actual use depends on runtime control flow.

This is an intermediate test of increased native allocation/initialization, before host layout and guest mappings are changed. The existing 32MiB page maps, ROM table offsets and memory protection remain intact. It must not be presented as a completed 128MiB patch. Full NEXT support remains unresolved.

## Installation and test

APK: next-classic-3668-ram-allocation-probe.apk. App label: Classic RAM Allocation Probe. Separate package: com.ncaanext.classic3668.ramprobe. It uses the local diagnostic certificate and does not replace ARMSX2 or stock NetherSX2.

1. Install alongside existing apps. Give it its own copied BIOS, ordinary game files and copied in-game saves/cards. Existing app data is not automatically shared.
2. Start with an ordinary game or a NEXT version known to run with 32MiB. Do not use NEXT27 extended-memory behavior as this probe's pass criterion.
3. Record launch success, renderer, recompiler setting, device/OS and game identity. Run with the EE recompiler enabled so the changed reset path can be exercised.
4. Test game boot, several minutes of gameplay, reset, close, launch again and a second session. Record crashes or low-memory termination, especially after reset.
5. Capture logcat and dumpsys meminfo before game launch, after boot and after reset. Compare with stock Classic 2.2n using the same scene/settings. A larger memory footprint and successful game boot would support the paired allocation changes, but do not prove 128MiB guest access.

The capture helper accepts --variant ramprobe. Provide adb path, serial, scene and notes. It collects existing logs without clearing them, package/device details, memory summary and a screenshot. Export emulator logs/settings through the app when available. No connected ARM64 target was available here, so launch/gameplay remain untested.

## Build and verification

Decode a fresh official 2.2n input to classic-2.2n-decoded using apktool with the workspace framework directory. scripts/build_ram_allocation_probe.py pins its native SHA256 and original opcodes before applying any change. It will refuse to patch a different or already-patched native file.

Build the decoded tree with apktool, align with Android SDK zipalign, sign with the existing local classic-diagnostic.jks key, and preserve signer/badging output in diagnostics/ram-probe-signature.txt and diagnostics/ram-probe-badging.txt. Run scripts/verify_ram_allocation_probe.py to prove the final APK contains exactly the four native changes and the separate app identity. Key and binaries remain local; diagnostic records are committed.

The native diff manifest is diagnostics/ram-allocation-probe.json. Static verification can prove patch integrity and APK signing, not native execution. Signature/package assumptions inherited from Classic may still prevent launch.
