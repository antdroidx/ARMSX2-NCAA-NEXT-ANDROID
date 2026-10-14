# RC4-test2: texture streaming

The ready-upload queue now uses a deque instead of erasing a prefix from a
vector after every frame. Unprocessed entries remain in place. Preserve the old
16 MiB-per-frame accounting, including letting one oversized texture through,
precache-only behavior, pending-mark removal, upload failure handling, upload
order, and alpha metadata. Existing cache locking and GPU calls are unchanged.

The synthetic differential test runs the actual pinned and generated processors
against 500 deterministic workloads, checking each frame's upload/injection
events, pending state, and remaining queue. Cases include absent cache entries,
missing pending marks, precache-only work, failed uploads, and textures larger
than the frame budget. A 4,096-entry backlog moves 4,095 waiting keys in the old
processor and none in the new processor after one budget-sized upload. ASan and
UBSan check host execution; an Android ARM64 compile checks portability. The
reference processor is checked against the pinned source before patching.

This removes queue bookkeeping work. It does not reduce the number of pixels
rendered or establish an Android FPS improvement. Small queues have little
shifting overhead to remove. Device frame-time and thermal measurements remain
necessary before claiming a speedup.

## Optional diagnostics

The existing Graphics → Texture packs → Texture Pack OSD setting also enables
periodic native-log summaries. Counters cover decoded-cache hits/misses,
successfully decoded inputs submitted to the cache, evictions, successful GPU
uploads, source-buffer bytes uploaded, decoded-cache usage, ready queue size,
and pending requests. Source-buffer bytes include padding and mip data, and are
not a measurement of physical GPU-bus traffic. Misses count lookup requests,
including repeated requests while an asynchronous load is pending.

Summaries begin with `Texture streaming stats:` and appear every 600 hardware
GS VSync calls while enabled, roughly 10 seconds at 60 calls/second. They contain
cumulative counts since cache reset, covering enabled periods. Diagnostics use
the existing cache mutex; the GS thread updates the enabled flag under that
mutex so worker threads do not read the live OSD configuration. Resetting the
cache resets the counters. No per-request logging is added. The setting is off
by default and routine summaries are suppressed when off.

Use the Fold's working settings for comparison: system Vulkan, 3×, precaching
off, async loading on, GS multithreading on, and the existing blending choice.
No user settings are imported or overwritten by the build. The requested fresh
GS-threading default remains Off; saved choices still take precedence.

For diagnosis, enable Texture Pack OSD, play through a texture-heavy transition
for at least 10 seconds, and export the emulator log. Compare matched scenes
and settings with RC4-test1; preserve texture barriers on Auto. Rising evictions
and decoded counts point to turnover worth investigating, rather than proving
that a larger cache is safe or beneficial.

## Built candidate

Signed release APK `0.2.5-RC4-test2` / `128119` passed the production signer,
version/label, Settings bytecode, and all post-R8 DEX invocation checks.
Build source: `6432322ccd924a2b0e16124f19c3e9fa5bc3500c`. Build step: 800 seconds.

[Successful build](https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38520749326).
[Temporary APK artifact](https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38520749326/artifacts/11873598731).
APK SHA256: `97949102370a01758680303813c3df8ce3ef56f89c04499b1e0ce2e0b1158ddb`; verified after download.

Device timing and test2 gameplay validation remain pending. No release was
published and the PR remains a draft.
