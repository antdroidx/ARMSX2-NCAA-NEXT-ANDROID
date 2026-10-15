# NCAA filtering defaults and Vulkan sampler lookup

For SLUS-21214, append these hardware defaults in the generated GameIndex.yaml:

```yaml
gsHWFixes:
  mipmap: 0
  bilinearFiltering: 2
  trilinearFiltering: 1
```

The existing `vuClampMode: 3` is retained. No other serial changes. The upstream
mobile overlay has no SLUS-21214 entry that could replace this hardware-fix list.
Add the missing bilinear database key at the end of GSHWFixId to preserve existing
numeric IDs. Wire the INI `filter` key into normal per-game precedence and show
its name/value in the existing database settings panel. Per-game overrides win;
trilinear keeps upstream's rule that the database applies only while Auto is
selected. These runtime defaults do not rewrite exported settings or force menu
selections. With mipmapping Off, trilinear mip filtering has no mip levels to use.

Replace Vulkan's sampler unordered_map with a 256-slot handle table and a
separate initialized table, matching the full u8 key space. The separate validity
flag retains cached failed creation results. Keep descriptors and GPU operations
unchanged. Both cache clearing and resource destruction destroy live handles and
reset both tables. This uses bounded storage (about 2.3 KiB on ARM64) and removes
hashing, bucket/node lookups and per-entry host allocations. It does not reduce
GPU shading cost and no device speed improvement is measured.

Validation parses the YAML, reconstructs its original checksum after removing
only the new NCAA defaults, checks schema IDs/override wiring, and executes the
actual three filtering switch cases. Sampler differential tests use production
lookup/clear bodies and descriptor/selector code with mocked Vulkan driver calls,
covering all 256 keys, failed creates, cache clears, shutdown and reuse. They
run under ASan/UBSan and compile for Android ARM64. Full app compilation/device
acceptance is separate.

## Further performance opportunity

The build workflow still forces `CHECK_FASTMEM` false and defaults
`EnableFastmem` false. That routes EE load/store emission through VTLB soft memory,
including when a settings file requests fast memory. This was introduced during
128 MB extended-memory debugging. It is a plausible contributor to the Classic
performance gap, not a measured explanation. Restoring fast memory requires
validating the 128 MB mappings, mirrors, fault/backpatch handling and extended
address loads/stores; simply removing the guard could reintroduce the original
RAM bug. This change leaves that path alone.

## Validation result

Source/native CI passed at 9ff995e:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38791048092

YAML parsing, unchanged-entry checksum, schema/override checks and executable
filter cases passed. All 10,768 sampler differential requests passed, including
all 256 keys and failure/cleanup paths, under ASan/UBSan; Android ARM64 compilation
passed. Existing graphics, audio, cache and VIF regressions also passed. No APK
was built for this follow-up, to avoid another full Actions build before the next
device-test candidate is requested.

## RC4-test4 APK

Built 0.2.5-RC4-test4 (128121), source 9e8ff0d:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38793057081

Full Android build, preset/sampler/core tests, production signing, Settings
bytecode and 204,082 DEX invoke checks passed. Downloaded checksum verified:
`eb980787e681eb8be0f79f9eb5b7ded6c129eb2c7111a6291cd4f0fe8a84c785`.
Certificate matches test3 and the existing RC2/RC3 production signer.

Test artifact (expires October 18, 2026):
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38793057081/artifacts/12000843911

Device testing is pending; no merge or public release performed.
