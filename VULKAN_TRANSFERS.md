# RC4-test6 Vulkan transfer efficiencies

Keep the test5 experimental fast-memory setting when building this candidate;
the intended comparison changes only these two Vulkan transfer paths.

## Single-level uploads

UpdateFromBuffer has two callers, DoUpdate and Unmap. Both finish by transitioning
the image to ShaderReadOnly. Previously an image last used as ColorAttachment
went ColorAttachment -> TransferDst -> ColorAttachment -> ShaderReadOnly.
For single-level images, use the existing whole-image TransitionToLayout helper
to track TransferDst directly, so the final caller transition goes straight to
ShaderReadOnly. This removes the restore round trip, while retaining the existing
source/destination stage/access masks and the ROV transition workaround. Multi-mip
images keep their prior subresource restore behavior exactly. Caller clear, upload
allocation, row pitch, pixel conversion and mip-generation handling do not change.

## Identical snapped fallback copies

The fallback used when texture barriers are unavailable can select two source
rectangles before alignment. Distinct one-pixel regions at (1,1) and (2,2) select
two copies, but both align to (0,0)-(4,4). Skip the second only when the two aligned
rectangles are exactly equal. No draw or write occurs between them; source,
destination and destination offsets match. Do not merge other overlapping regions,
change feedback requirements, or alter the paths where texture barriers work.

## Validation and limits

Execute the actual old/new upload function, unchanged production image-layout
mapping, transition/barrier functions and copy-area alignment code in a host
harness using real Vulkan types and mocked command recording. Compare complete
RGBA32 output buffers, untouched pixels/mips, final Vulkan layouts and tracked
layout. ROV upload cases use single-level targets, matching CreateRenderTarget;
the legacy ROV workaround is not exercised on non-base mips. Assert identical pre-copy dependency sequences, transfer-write visibility
to fragment-shader reads, unchanged multi-mip command sequences and no barrier
count increases. Differential rectangle workloads compare output and copy count.
Run under ASan/UBSan and compile for Android ARM64. Source hashes check the two
caller bodies remain unchanged.

These are command/pixel model tests, not GPU execution or Vulkan validation-layer
results. Compressed upload descriptors remain unchanged; no compressed decoder is
modified. Driver behavior, frequency of these paths in NCAA, and device speed gains
remain unmeasured. OpenGL code is unchanged; similar speed at 93% GPU usage there
means the device bottleneck is still uncertain. A thread or shared-resource stall,
driver scheduling, or clocks can matter even when no individual counter is 100%.

Device test: compare the same scene/driver/resolution/settings against test5 using
Vulkan, checking boot and gameplay textures, numbers/logos, translucent gear,
shadows, menus and several plays. Leave Fastmem at the same setting for the
comparison. Keep the PR in draft until compatibility and performance acceptance.

## Source validation result

Passed at be1869f:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38822619499

1,188 upload/layout/pixel comparisons passed; 156 barriers were eliminated across
that synthetic workload. Representative single-level ColorAttachment upload:
3 -> 2 barriers. All 5,256 rectangle cases matched, including 256 identical
aligned-copy cases which avoided their second copy. Multi-mip command sequences
were unchanged. ASan/UBSan and Android ARM64 compilation passed, along with all
existing core and experimental fast-memory regressions.

Signed test6 build (128123, experimentalFastmem=true) at be1869f:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38822995484

Physical-device results remain pending. The synthetic counts are not measured
in-game bandwidth or frame-rate improvements.

## Signed APK result

RC4-test6 (128123), source be1869f, experimentalFastmem=true:
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38822995484

Full Android build, all source/native regression checks, production certificate,
Settings and 204082 DEX invoke audits passed. Downloaded SHA256 verified:
`90efdd98e74201966b473e0f1b653f2c97a091d17a705f93c24ef482caa143ba`.
The certificate matches test5 and the existing RC2/RC3 production signer.

Artifact (expires October 18, 2026):
https://github.com/antdroidx/ARMSX2-NCAA-NEXT-ANDROID/actions/runs/38822995484/artifacts/12014268989

Physical-device/driver validation and performance comparison remain pending.
No merge or public release performed.
