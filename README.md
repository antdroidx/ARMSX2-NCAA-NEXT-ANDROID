# ARMSX2 Extended

An Android ARM64 build based on ARMSX2, with 128 MB EE RAM support for NCAA NEXT,
Legacy/Current texture replacement methods, per-game settings and purple branding.

## 0.2.5-RC4

RC4 follows the tested RC4-test6 candidate. See [release notes](RELEASE_NOTES_RC4.md)
for changes and compatibility information. The new version code is 128124, above
test6 (128123). The existing Extended package and production certificate allow
updates over RC2/RC3 and RC4 tests without removing settings or saves.

### Changes

- Persistent texture filename index for faster repeat boots, with manual refresh.
- Reduced texture-cache, upload-queue and pixel-conversion overhead.
- ARM64 VIF copy efficiencies and corrected skip-range handling.
- Optional selectable EE fast memory with 128 MB mapping and fallback fixes.
- Fewer redundant Vulkan upload transitions and identical fallback copies.
- Bounded retry work for rejected Android audio-affinity requests.
- NCAA 06 / NEXT (SLUS-21214) defaults: mipmapping Off, bilinear PS2, trilinear PS2,
  retaining the existing VU clamp fix and per-game overrides.
- GS Multi-Threading Off for fresh defaults/presets; saved choices are preserved.

### Performance and known issues

Testers report working gameplay and faster repeat boots. Fast memory reduced
reported EE load; no consistent FPS gain from the latest Vulkan changes was
established. Device, driver, game and settings affect results. OpenGL code was
unchanged by the latest Vulkan efficiencies.

The NCAA NEXT Press Start artwork can still appear too dark. If Fastmem causes
problems in a game, turn it Off and restart the game.

## Build and validation

Run **Full ARMSX2 NCAA NEXT Native Build** with `enhancements=cpu-audio`.
`experimental_fastmem` selects the tested fast-memory variant and remains opt-in
in the workflow until the public default is confirmed. Saved/per-game Off choices
are respected when the feature is enabled. Use `validate_only=true` for source
and native checks without compiling an APK. Signing uses encrypted repository
secrets; signing material is not included in the source or release downloads.

Pinned upstream: SgtBilko76/ARMSX2-3D at
`f4904cb5e3b322178e3815683e221f3ab9354d2e`. The workflow applies Extended changes
to that source, including complete 128 MB recompiler LUT/snapshot/mirror spans.

Tests include production-body differential checks, ASan/UBSan, ARM64 compilation,
VIXL instruction simulation, Android builds, signing, Settings bytecode and DEX
audits. Host/simulator checks do not replace physical-device gameplay testing.

Implementation notes: [core efficiencies](CORE_EFFICIENCY.md),
[fast memory](FASTMEM_128.md), [Vulkan transfers](VULKAN_TRANSFERS.md),
[NCAA filtering](NCAA_FILTERING_AND_SAMPLERS.md), [texture streaming](TEXTURE_STREAMING.md),
and [versioning](VERSIONING.md). Earlier investigation records remain in
[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).
