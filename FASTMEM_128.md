# Experimental selectable EE fast memory with 128 MB RAM

RC4-test5, versionCode 128122, is built with workflow input
`experimental_fastmem=true`. The normal workflow default remains false; the
existing soft-memory candidate is not silently replaced. No public release or
merge is performed.

Restore CHECK_FASTMEM to the EE recompiler and existing EnableFastmem setting.
Restore the native default true (the Android frontend already defaults true).
Explicit saved/per-game false values still win. The existing Fastmem switch can
be used to compare against soft memory; restart the game for a clean comparison.

Keep all prior 128 MB recompiler LUT, snapshot, SMC array and mirror extensions.
The shared allocation and protection tables already cover TotalRam; they did
not need another RAM-size rewrite. The prior forced soft-memory path was a
diagnostic restriction, not proof that every fast-memory path is broken.

Changes before restoring the setting:

- Android reservation failure falls back to soft memory and retains the existing
  settings-reload guard, rather than aborting startup or using a null base.
- Keep the 4 GB *virtual address reservation* when fast memory is disabled in
  settings, so a later enable can work. It does not allocate 4 GB of physical RAM.
  A process-wide environment opt-out still releases it and latches unavailable.
- A virtual page remapped from physical A to B removes A's reverse entry. The
  original code searched B's reverse list, leaving stale protection aliases.
- Reject absent/uninitialized reservations in guest-address lookup. Reuse its
  subtraction-based bounds check for resolve/backpatch entry points.

Tests use actual production allocation/mapping/protection/fault-bookkeeping
functions with POSIX shared mappings, mocked core services and physical lookup.
They check 32/128 MB page spans, eight sampled mirror ranges, high-address
resolution, remap consistency, failed mappings, allocation failure, settings-off
reservation retention and environment opt-out. Protected shared aliases are
checked with child processes that must fault; production SMC fault handling must
invalidate the block and allow the subsequent write. MMIO checks validate
backpatch metadata and fallback decisions with a mocked thunk emitter. Both 4 KB
and 16 KB host-page policies are exercised on a 4 KB Linux host and compile for
Android ARM64; this is not a real 16 KB Android-device result.

A separate VIXL simulator executes the original ARM64 fast-memory load/store
emitters for 8/16/32/64/128-bit accesses, signed loads, FPR loads, high-bit guest
addresses, and captured live-register metadata. The production backpatch thunk,
full allocator and hardware exception delivery still require Android gameplay
testing; these tests do not establish game compatibility or a speed gain.

Device acceptance: keep the same driver and game settings as test4, check that
Fastmem is On, restart, and compare the same CPU-vs-CPU play with frame limiting
off. Also check NCAA NEXT boot, graphics, several plays, save/load, repeated
close/relaunch, and any other games used regularly. If a regression appears,
switch Fastmem Off and restart before comparing again. Do not merge/release
until physical-device acceptance passes.

## Initial validation

Source/native validation passed at bdee5f6:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38816141992

40,960 page-span checks per modeled host-page policy, alias/protection/remap and
fault-bookkeeping cases passed; both harnesses compile for Android ARM64. VIXL
executed 405 memory-access and metadata cases. Existing regression checks passed.
The subsequent full build at c7a8509 also runs the new negative remap regression:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38816622077

No physical-device fast-memory result yet. The latest user-supplied INI requested
EnableFastmem=true, so this experiment should honor that existing choice.
