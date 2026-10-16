# RC4-test3 core efficiencies

These changes remove work inside existing emulation paths. No new diagnostics
features or user settings are added; current device settings remain authoritative.

## Graphics conversion

Mapped render-target updates previously decoded the same PS2 rectangle once into
CPU scratch memory for alpha tracking, then again directly into mapped upload
memory. When alpha tracking is required, decode once, calculate the same alpha
range, and copy the resulting RGBA32 rows into the upload map. Never read from
mapped GPU memory, which may be write-only. The path without alpha tracking and
the unmapped path remain unchanged.

Tests compare 19,008 output/alpha/stride cases using the generated old/new mapped
blocks and the real GSVector alpha implementation, with a modeled pixel reader.
The PS2 format decoder itself is unchanged. The tracked path makes one conversion
call instead of two. Guard bytes, odd widths, unaligned destinations, padded
strides, channel-write conditions, and alpha-validity conditions are covered.

## Decoded-cache insertion

A synchronous decode can finish after an already-running asynchronous decode
inserted the same key. Previously, insertion could evict other entries, increment
the byte total, and append an LRU node before emplace rejected that duplicate.
Return the existing cached value and touch its LRU position without charging it
again. Preserve the prior rejection of individually oversized textures.

The actual insertion/touch/byte-accounting functions pass duplicate-race,
oversized-input, eviction-order, and 10,000 randomized invariant checks. These
check that byte totals equal resident data, the budget is respected, and each
resident key has exactly one LRU node. This fixes an accounting path; it does
not establish what caused a previously reported memory warning.

## Audio affinity

After Android rejects sched_setaffinity, retry after approximately one second
of output frames instead of every callback; warn once per stream open. Audio
rendering continues on every callback, with no sleep or new mutex. Startup still
checks for a performance-cluster mask, successful pins retain their old latch,
and reopening a stream resets the retry state. Audio samples, mixer, resampling,
channel negotiation, buffering, and latency settings are unchanged.

The production callback/Open bodies pass frame/channel/buffer checks plus
44.1/48/96 kHz failure, eventual success, repeated callbacks, and reopen cases
with mocked Android affinity calls. Benefits apply to rejected-affinity cases;
this is not a general audio-FPS improvement.

## ARM64 VIF

Adapt ARMSX2 commit c8f32ece8b21a3e2ff027b77d60b4952b08083ce, attributed in
patches/vif-copy-rows.inc. Use paired quadword loads/stores for mode-free,
unmasked V4-32 copies with at least 16 rows. Exclude fill operations and odd
skip cycles. Keep small/masked/mode/other-format emitters unchanged.

A runtime disjoint-range check retains single-row load/store ordering for
overlapping buffers. Address rebasing respects the pair instruction's 1008-byte
positive displacement limit. Correct the span passed to the existing VU-memory
wrap/interpreter dispatcher: encoded NUM=0 means 256 rows, including skip gaps.
For CL=4/WL=2 this is 8,160 bytes, rather than the previous 4,064 bytes.
Normalize encoded WL=0 to 256 and saturate spans beyond 65,535 bytes so they
still trigger fallback. Pairing adds an overlap fallback and therefore increases generated
code size; device cache and frame-time effects still need testing.

Generated ARM64 instructions execute in the pinned VIXL simulator: 351 disjoint
cases, 585 overlapping cases, and unchanged fallback-code comparisons passed. An
exhaustive 16,777,216-case CL/WL/NUM check compares the span with the emitter
row walk and checks VU boundary decisions.
The representative contiguous 256-row copy executes 269 instructions instead of
513, including guards/rebasing/return. This is an instruction count for that
copy routine, not a claimed percentage improvement in game FPS. The harness
models unchanged helper emission for excluded modes/formats; it is not a full
PS2 game test.

## Acceptance

Graphics, cache, and audio bodies execute under ASan/UBSan and compile for Android
ARM64. VIF instruction tests use the actual VIXL assembler and simulator. Full
Android builds check integration, signing, Settings bytecode and APK DEX widths.

Device acceptance needs the same settings/game/scene as test2, two warm boots,
texture/alpha/crowd checks, audio on speakers and Bluetooth if used, and gameplay
frame-time comparison. No Android target was connected during implementation.
No measured device FPS gain is claimed. Keep PR #7 in draft until test3 passes
device testing.

## Built candidate

Signed APK 0.2.5-RC4-test3 (128120), source dcfad74df6017225c1f6ac9715ac1b290b10a573:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38777787781

All checks passed, including the exhaustive span checks, Android native build,
Settings declaration audit and 204,077 DEX invokes. Downloaded APK SHA256:
`147a3701ae1f174edc019897e7d0470a98041fb789613f68be12b91734858460`.
Production certificate matches the RC2/RC3/test2 signer.

Artifact (expires October 18, 2026):
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38777787781/artifacts/11996505017

This remains a device-test candidate, not a merged or published release.
