# RC4 test candidate

The candidate includes the filename-index cache and GS Multi-Threading default
change from PR #7, plus two small GS changes:

- Reserve filename-map and palette-independent lookup-set capacity before inserting
  replacement pack entries, avoiding repeated bucket rebuilds. Entry insertion
  order, duplicate priority, lookup keys, and load factors are unchanged.
- End RGBA8 alpha-range scanning once both 0 and 255 have been observed. Those are
  the representable endpoints, so later pixels cannot change the result. Check
  once per eight rows for widths of at least 64 pixels. This retains the existing
  SIMD scan, tail handling, and alpha-normalization rules.

The early exit can save work for large images containing both transparent and
opaque pixels. Fully opaque images and images whose range is 0–128 do not qualify;
they incur a small additional check. This is a candidate, not a measured Android
speedup. The broad renderer fallback, emulation timing, EE memory mapping, and
thread synchronization are unchanged.

## Automated checks

Generate old and new production functions from the patched source and execute
them using the real upstream GSVector implementation on x86 SSE4.1. Compare 1,296
cases covering aligned and odd widths, empty inputs, padded rows, zero/full/fixed
and random alpha ranges, and unchanged source data. Place short rows before an
inaccessible page to check tail reads. Run with ASan and UBSan, then compile the
same functions against the actual Android ARM64 NEON headers. Full APK signing,
Settings bytecode, and DEX audits also run in the release build.

Host execution does not prove ARM64 execution or a gameplay FPS improvement.

## Galaxy Fold device check

Install `0.2.5-RC4-test1` over the existing Extended installation. It retains the
package and production certificate. Saved GS threading choices remain in effect;
set GS Multi-Threading to Off explicitly if the old installation has it enabled.

1. Use the same resolution, Vulkan driver, texture pack, matchup, and weather as
   the previous build. Keep Override Texture Barriers on Auto.
2. Boot twice. The first boot builds the index; subsequent boots should log
   `Texture filename index: cache hit`. Compare time to the same opening screen.
3. Check jersey numbers, logos, player skin, gear, crowd, and menus for regressions.
   The previously reported dark Press Start image remains a separate known issue.
4. Compare the same stationary gameplay scene after similar warm-up, ideally
   across several runs. Report emulation speed/FPS rather than Android UI FPS.
5. After changing pack filenames, check automatic refresh; use Refresh texture
   index and restart if a synchronization tool preserved directory timestamps.

Do not merge/release until the candidate APK has passed device testing.
