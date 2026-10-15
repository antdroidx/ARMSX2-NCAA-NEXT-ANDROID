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
