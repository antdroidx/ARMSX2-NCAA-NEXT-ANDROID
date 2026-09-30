# Build results - Close/Reset crash and selective enhancements

Branch: `codex/memcard-hash-upstream-audit`

## Crash-only APK

- Commit: `dce8551fb1738c2b88b2e6dfdc14b7cf5775dc5b`
- GitHub Actions run: `36678427511`
- Artifact: `ARMSX2-NCAA-NEXT-ANDROID-test-apk`
- APK: `ARMSX2-NCAA-NEXT-ANDROID-FAST4K-debug.apk`
- Package: `com.armsx2.ncaanext`
- Version: `128103 / 0.2.3-next128-mc64-stopcpu`
- APK SHA-256: `7c1bd476c7bdf94b6a9b65f1bdfda7ad2775d74271c7196bf632821500144128`
- Signing certificate SHA-256: `599891bb2245e9c90237c41e7066889cb9c28e11c2f8b5d6af75b10cad3a783f`
- CI result: passed
- Local APK verification: passed

This build keeps the existing frontend guard from `9777887` and changes native
Close/Reset handling so the JNI caller queues the stop request onto the CPU-owner
thread. It no longer touches VMManager/Cpu teardown state from the Android UI or
Kotlin coroutine caller thread after requesting shutdown.

## CPU/audio enhancement APK

- Commit: `2587c5fae66b564905f0506e4a245915b57e6976`
- GitHub Actions run: `36681909330`
- Artifact: `ARMSX2-NCAA-NEXT-ANDROID-cpu-audio-test-apk`
- APK: `ARMSX2-NCAA-NEXT-ANDROID-CPU-AUDIO-4K-debug.apk`
- Package: `com.armsx2.ncaanext`
- Version: `128105 / 0.2.5-next128-mc64-cpu-audio`
- APK SHA-256: `9d740eee02eae1e7a6e203cf796dea5c8362fbd5592d488b82b41ee4be527569`
- Signing certificate SHA-256: `599891bb2245e9c90237c41e7066889cb9c28e11c2f8b5d6af75b10cad3a783f`
- CI result: passed
- Local APK verification: passed

This build includes the crash fix plus the selected upstream EE/VU/VIF and Oboe
audio patches described in `SELECTIVE_AUDIT.md`. It does not re-enable EE
fastmem and does not change GS texture dumping, replacement or hash behavior.

## Build/cache timing

- Earlier fast 4K run `36664846673`: Gradle build `27m48s`; cache path was wrong,
  so no compiler cache was saved.
- Guard-only run `36677497087`: job `39m56s`, build step about `38m36s`.
- Crash-only run `36678427511`: job `38m09s`, Gradle build `36m42s`; ccache was
  wired correctly but cold. Cacheable calls `1369 / 2110`; hits `23 / 1369`
  (`1.68%`); saved about `210 MB` under key
  `ccache-v2-Linux-armsx2-f4904cb5-4k-36678427511`.
- CPU/audio run `36681909330`: job `22m22s`, Gradle build `20m46s`; restored the
  `210 MB` cache from run `36678427511`. Cacheable calls `1369 / 2110`; hits
  `1142 / 1369` (`83.42%`).

CI verifies build success, package identity, signing identity and host-side source
properties only. Close/Reset behavior and any emulation-speed gain still require
physical-device testing with the same game/settings scene.
