# ARMSX2 NCAA NEXT Android

Android ARMSX2 test/build project for NCAA Football 06 NEXT, focused on:

- 128 MB EE RAM support for NCAA NEXT 27
- Android ARM64 compatibility
- JDHalfrack PCSX2 v1.7.4029 texture-replacement hash compatibility
- 4 KB and 16 KB Android page-size support
- Reproducible GitHub Actions APK builds

## Current status

PR #1 is merged into main as the known-good frontend baseline (128015 / 0.1.9).
The user confirmed successful gameplay including NCAA NEXT 27 extended RAM.
Closing a game from the app pause menu still crashes in that baseline.

The `codex/game-exit-no-intro` branch contains a frontend lifecycle repair candidate
and immediate startup without the intro video (128016 / 0.1.10). It preserves
all accepted native libraries byte-for-byte. Device testing is still required;
this is not yet a confirmed fix for the reported crash.

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for diagnosis and validation evidence,
[DEVICE_TESTING.md](DEVICE_TESTING.md) for acceptance steps, and
[baseline/known-good.json](baseline/known-good.json) for the accepted artifact identity.

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

## Development gate

Use the Fast ARMSX2 Runtime Probe workflow for this branch. Do not merge the
crash/splash PR until device testing confirms normal game launch, NCAA NEXT 27
extended RAM, Close Game back to the library, and app relaunch. The workflow's
x86 Android ART test verifies Settings; it does not run the ARM64 emulator core.
