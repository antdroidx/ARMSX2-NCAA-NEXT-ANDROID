# Close/Reset and selective ARM64 audit, 2026-09-30

## Baseline and evidence

Source stays pinned at SgtBilko76/ARMSX2-3D `f4904cb5e3b322178e3815683e221f3ab9354d2e`.
The requested overlay branch started at `9777887aa3d95395bc857442a3c5befd8b8fea7e`.
The two device screenshots show Android exit reason 5/status 6, no Java crash,
and STOP_REQUEST -> SHUTDOWN_BEGIN -> RUN_RETURNED without SHUTDOWN_RETURN.
They do not include a native stack. RUN_RETURNED is a frontend finally marker,
not proof that every teardown action was safe.

The active-VM recheck in 9777887 is retained. It cannot make the subsequent JNI
shutdown call atomic with native teardown. Pinned JNI shutdown latches stop on
VMControl, then changes limiter/state, accesses Cpu, queues another stop, and
polls/logs while the run thread can destroy CPU providers and close the logger.
The new JNI implementation only queues under the CPU-owner mutex. The CPU task
rechecks VM validity, resets the limiter, latches stop, and changes state. An
already-ended session is ignored. There is no foreign-thread Cpu dereference,
state mutation, polling, or core logger use in this JNI call. The existing
frontend barrier still requires the run caller to return before library/restart.

This removes a concrete race; physical-device confirmation is still required.
It relies on the normal CPU message pump (each vsync and while paused). It is
not a watchdog for an unrelated core deadlock. No process-kill workaround added.

## Upstreams inspected

- [ARMSX2 master](https://github.com/ARMSX2/ARMSX2/commit/ae93e16a0cc4bad8d4679312e921b158b70a8131), fetched 2026-09-30.
- [PCSX2 master](https://github.com/PCSX2/pcsx2/commit/94d86c891b1621c0b252e4fc2e155bf90274dcc0), fetched 2026-09-30.
- The local fork remains pinned; upstream histories were fetched only for comparison.
  Some changes have equivalent cherry-picked ancestors with different IDs, so
  decisions use source differences rather than commit-list membership alone.

## Selected, optional backports

| Area | Upstream commit | Exact change | Expected effect |
|---|---|---|---|
| EE | [426adcd244](https://github.com/ARMSX2/ARMSX2/commit/426adcd2441706b62b68c4868d67df1b347b18b9) | Read the resident base register directly for nonzero address-offset addition | Removes a move when the base is resident; retains softmem and 128 MB handling |
| VU1 | [4bce28f6ba](https://github.com/ARMSX2/ARMSX2/commit/4bce28f6baeac8488da59d4604f9e859a4ded3a2) | UBFIZ replaces AND then LSL for address wrapping | One fewer emitted instruction; same 10-bit quadword address |
| VIF | [e1bbcfc414](https://github.com/PCSX2/pcsx2/commit/e1bbcfc4143c08351fd34e1dad2daa31f538df4b) | Pass the actual packet size to MTVU instead of rounding with `(size + 4) & ~3` | Prevents source over-read; correctness fix, not a claimed FPS gain |
| Oboe | [cdc8180b02](https://github.com/ARMSX2/ARMSX2/commit/cdc8180b02799e6c8f85aabaa7ed9fb66c8bc4e1) | Request the actual output channel count; reject a mismatch | Prevents expanded-channel writes into an undersized mono callback buffer |
| Oboe | [ae766e068c](https://github.com/ARMSX2/ARMSX2/commit/ae766e068c9a6bb0c8f536ba2aff1795915a22f0) | Remove fixed 2048-frame callback size; bound individual reads to 2048 frames | Avoids unnecessary block adaptation and bounds stack use; may reduce route-specific dropouts |

Patch files retain upstream attribution and apply cleanly to the pinned source.
Only four source files are touched by these optional patches. GS, texture names,
dump/replacement/hash code, memory-card geometry, RAM exposure, fastmem settings,
signing, and frontend code are outside them. No mixer/timestretch/latency settings
or CPU-affinity defaults are changed.

## Deferred after review

- IOP `cbcc148004`: SUBS plus B.LE removes a compare, but subtraction's V flag
  makes it differ from comparing the wrapped result with zero when signed
  overflow occurs. Require cycle-range proof and PS1/PS2 timeslice differential
  tests before adopting. Example: 0x80000000 - 1 wraps to 0x7fffffff; old and new
  signed branch predicates differ. This is a boundary concern, not a claim that
  normal gameplay reaches it.
- VIF `c8f32ece8b`: pair loads/stores for unmasked V4-32 need differential coverage
  of fill/skip cycles, 256-row packets, pairing reach, and destination wrapping.
- EE `f895f5a481`: call/return ring field narrowing changes packed register layout
  and warrants overflow/underflow, reset and savestate testing.
- Larger VU clamp/model/register-allocation chains and dispatcher changes are
  interdependent and not suitable for a blind cherry-pick.
- PCSX2's audio tree is not a drop-in Android upgrade: the pinned fork already
  carries ARM64 NEON mixer code and Android Oboe lifecycle handling. Preserve it.
- EE fastmem remains forced off. No GS changes or wholesale core upgrade.

## Test scope

The stop harness executes the actual generated JNI body with mocked core calls
and real host threads, checking no-owner, active, paused, duplicate and stale
requests. It does not reproduce the device's native crash.

Optional tests extract the patched EE/VU emission functions into a host
instruction model, checking positive/negative offsets, wrap boundaries including
32/128 MB, register preservation, and all 65,536 VI values. They do not execute
ARM64 machine code. Oboe's patched Open and callback functions execute against
mocked device negotiation and guarded buffers for 1/2/3/4/6/8 channels and
0..8193-frame boundary cases, with ASan/UBSan in CI. Device routing, underruns,
gameplay correctness and speed still require hardware testing.

## Builds and acceptance order

1. `128103 / 0.2.3-next128-mc64-stopcpu`: crash-only candidate, first to test.
2. Optional `128104`: CPU/VIF only, available via workflow input `cpu`.
3. `128105 / 0.2.5-next128-mc64-cpu-audio`: optional backports plus crash fix.

Install 128103 first and complete repeated Close/Reset/relaunch before installing
128105. Android normally prevents downgrading to the lower versionCode, so keep
this order. All variants use the same package and pinned signer.

Compare the same gameplay scene, settings, renderer, resolution and thermal
state. Record emulation speed/frame time, audio dropouts, and repeated
Close/Reset results. Use several warm runs; report median and range. Do not
attribute compilation speed to emulation FPS or infer FPS from instruction count.

## Cache repair

Build 12's log ends with `Path Validation Error` and no saved cache. The new
workflow uses an absolute workspace cache directory, explicit CMake launchers,
a unique save key per run with a shared restore prefix, and uploads statistics.
The old fixed key would also stop an exact-hit cache from refreshing. The first
corrected build is cold; later builds must show actual hits and a saved cache
before reuse can be claimed. Results are recorded separately after completion.
