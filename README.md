# ARMSX2 NCAA NEXT Android

Android ARMSX2 test/build project for NCAA Football 06 NEXT, focused on:

- 128 MB EE RAM support for NCAA NEXT 27
- Android ARM64 compatibility
- JDHalfrack PCSX2 v1.7.4029 texture-replacement hash compatibility
- 4 KB and 16 KB Android page-size support
- Reproducible GitHub Actions APK builds

## Current status

### Working
- ARMSX2 Android source base compiles on GitHub Actions.
- 128 MB ARM64 patches compile.
- JDHalfrack 1.7.4029 texture-hash compatibility patches compile.
- Both 4 KB and 16 KB emucore variants compile.
- Universal APK packaging with both native cores is supported.
- APK installs successfully.

### Current blocker
The app exits/crashes immediately after the animated boot splash hands off to the main activity.

This happens before a game is launched, so the next investigation is focused on Android/native startup initialization rather than NCAA NEXT game execution.

## Build history migrated from NCAANext-TuningApp

- Build 41: wholesale JD4029 desktop-core overlay onto Android scaffold. Failed with widespread PCSX2 generation/ABI mismatches. This approach is retired.
- Build 42: switched to coherent ARMSX2 Android core + targeted JD4029 texture hash patch. Patch script failed before compilation due a whitespace-sensitive edit.
- Build 43: patch fixed; APK compiled successfully. Installed, but crashed immediately after the intro splash.
- Build 44: added universal 4K + 16K native cores. Both cores compiled; final APK signing step failed because the runner had no debug keystore.
- Build 45: signing flow fixed. Universal APK installs but still crashes immediately after the intro splash.

## Architecture

Base source:
- SgtBilko76/ARMSX2-3D
- pinned source commit used by current workflow: f4904cb5e3b322178e3815683e221f3ab9354d2e

128 MB patch:
- Extends ARM64 recompiler RAM/LUT/snapshot spans from retail MainRam to ExposedRam/TotalRam.
- Forces extra-memory mode on for NCAA NEXT testing.
- Uses softmem for the current diagnostic configuration.

JD4029 texture compatibility:
- Restores the old JD4029 texture key mask including TEX0.TCC.
- Disables newer region texture hashing for replacement-key generation.
- Restores JD4029-era full-texture HashTextureLevel behavior.
- Preserves legacy TCC bit in replacement texture filenames.

## Next debugging step

The splash activity hands off to Main, and Main touches NativeApp very early. NativeApp's static initializer loads the native emucore library. The next build should isolate that boundary by deferring nonessential NativeApp accesses until after the main Compose UI is alive, while adding explicit startup markers/crash diagnostics.

