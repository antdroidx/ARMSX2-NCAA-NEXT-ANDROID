# Development log

## 2026-09-29 — M1 source constructor repair

Inspected remote main 9ffe8ead3b965df8916e7ed4b38188254e91157a and
successful Build 16 run 36528955257. The handoff's befc62a commit is not
available in this repository. No source constructor repair was present.

Findings:
- Settings is a 246-field Kotlin data class. Its default constructor adds
  receiver + eight masks + marker: 256 argument words. DEX invoke-range
  encodes only 255. Removing call sites alone leaves an invalid generated
  no-arg constructor in the class.
- The previous audit changed dots to slashes before matching dotted method
  names, making its hazard checks ineffective. It also ignored declarations.
- Build 16 used application ID com.armsx2.ncaanext and versionCode 128014.
- Its successful CI log reports a CACHED KEY certificate SHA-256
  599891bb2245e9c90237c41e7066889cb9c28e11c2f8b5d6af75b10cad3a783f.
  Subsequent APK inspection proved this was NOT the APK's signing certificate.

Repair:
- Convert Settings to a regular class with no primary-constructor defaults.
  fromJson provides explicit defaults; retain verifier-safe JSON updates.
- Generate equals/hashCode for all fields, preserving data-class Float semantics.
- Preserve the crash debugger and display actual process exit diagnostics
  instead of the previous literal "undefined" values.
- Build versionCode 128015, versionName 0.1.9-settings-source-constructor-fix.
- Fail when the existing signing key is missing or has a different certificate.
  No fallback key generation.
- Audit compiled constructor declarations and every packaged DEX. Compare
  ordinary/range invoke word counts to DEX method prototypes.
- Verify signature, manifest, increasing version code, ZIP alignment, crash
  markers, ABI, and exact native-library/resource preservation from Run 6.
- Add Settings JVM regression tests and negative audit tests.

Validation so far: source transformation applied to pinned upstream files;
Python audit regression tests passed. Full Gradle, DEX, APK and device results
must be recorded after execution. No main-menu or 128 MB runtime claim yet.

First repair CI run 36536652192 caught 337 remaining Settings.copy UI calls.
Migrated these compiler-identified sites, with per-file counts that fail on
source drift. Added explicit list/map JSON normalization and a structured-field
regression test. Added an Android API 35 ART smoke test using a separate
app_process harness: the old APK must fail with VerifyError, and the repaired
APK must instantiate/update/round-trip Settings. It does not load ARM JNI or
claim to exercise the Samsung main menu.

Signing remains dependent on the original Actions cache. Missing cache now
fails safely. A durable private backup/secret for that SAME key is still needed;
never publish the keystore as an artifact or generate a replacement silently.

### Actual signing diagnosis

Run 36537937833 passed the build, all four Settings JVM tests, and the compiled
constructor audit. Packaged APK validation then correctly rejected an unexpected
runner-generated debug certificate. Copying the cached key to the conventional
debug.keystore path had not controlled Gradle's actual signer.

Inspection job 109473577980 in run 36588060412 verified Build 16's APK signature:
a7135416c2a58f51d331e5b0b21b2bcdb6983e53b5f6bd19d3f612ac08ec0ef5.
This differs from the cached key. Its matching private key has not been recovered
from the available artifacts. A normal update over Build 16 cannot be promised.
The repaired workflow explicitly configures Gradle's debug signing to the
recoverable NCAA NEXT key (599891bb...), keeps com.armsx2.ncaanext, and rejects
future signer drift. Validation records the one-time Build 16 incompatibility
rather than claiming it passes. Preserve/back up app data before reinstalling.

Run 36588272952 passed compilation, Settings JVM tests, declaration audit,
explicit signing identity, package/version, alignment, native ABI/inventory,
and byte-for-byte core resource checks. DEX inspection exposed a validator
text-decoding issue: dexdump emits modified UTF-8 constants. Decode its display
output with replacement while continuing to inspect original binary DEX data.

## Architecture boundary

This repository is an overlay on ARMSX2-3D
f4904cb5e3b322178e3815683e221f3ab9354d2e. The fast frontend workflow reuses
native libraries from run 36368317970. It does not build or establish a
JDHalfrack v1.7.4029 core. The full native workflow applies targeted texture
hash compatibility and extended-RAM patches to ARMSX2; that does NOT satisfy
the requested exact-core provenance requirement. Do not run that workflow
as the next M1 build. M3 requires a separate architecture review after M1.

## Device acceptance for M1

If the original Build 16 private key is recovered, reassess update signing first.
Otherwise back up app data before the one-time reinstall of validated 0.1.9. Launch
through the splash to the ordinary main menu, open settings, then close
and relaunch. Do not launch NEXT 27 yet. On failure, reopen the app and
copy the crash debugger report; optional adb logcat should include AndroidRuntime
and NCAA_NEXT messages. Installation failures need the exact Android/adb error.


## 2026-09-29 — accepted baseline and game-exit candidate

### Baseline review and merge

Reviewed PR #1 at aeb5e9296eebc546f3f4d7df09d9e5c86cfadae9:
constructor/default/copy repair, 337 call-site migration, structured JSON fields,
crash debugger, explicit signer, declaration and DEX audits, and resource checks.
Run 36592876989 passed both jobs, including Settings JVM tests and API 35 ART
`SETTINGS_ART_SMOKE_OK`. Ten Python audit regression tests also passed locally.
The user reports successful game launch and NCAA NEXT 27 extended-RAM gameplay.
This is user device evidence, not an emulator test performed in this chat.

Merged PR #1 using its exact reviewed head; main merge commit:
`d3b23e8d5f1e41ec947db92a3285c14015d8fe17`.
Created `codex/game-exit-no-intro` from that updated main.
`baseline/known-good.json` pins the accepted APK hash, all 17 native-library
hashes, signer, version, CI run, and commits. A local copy of the accepted artifact
was downloaded before editing. Historical architecture notes below remain relevant:
working NEXT 27 does not establish wholesale JDHalfrack core provenance.

### Reproduction and investigation

User reproduction: during gameplay, press Pause to enter the app menu, then
**Close Game**. No crash report/logcat was available. Consequently, the lifecycle
races below are confirmed source defects, but their responsibility for this
particular device crash is NOT yet confirmed.

Traced the pinned upstream f4904cb5 source across these boundaries:

- `EmulationMenuScreen` calls `MainActivityRuntime.closeGame()` -> `stop()`.
  External-launch preferences may additionally request Activity finish; ordinary
  library-launched Close Game should not destroy the Activity.
- Pause/resume use VMControl while shutdown used a separate VMStop executor.
  A duplicate stop while native was active queued another shutdown. This could
  target teardown twice or run late against a restarted game.
- Game and BIOS run-loop `finally` blocks cleared the stop latch independently
  of the shutdown caller, and both the worker and run-loop could publish STOPPED
  and perform library cleanup. That opens a restart/cleanup race.
- Java `NativeApp.vmSetPaused` rejected stale resume but accepted stale pause
  after STOPPED, allowing a dead session to re-enter PAUSED state.
- `onDestroy` called shutdown again on the UI thread and then killed the process.
  Configuration changes already had an exemption, which is retained.
- JNI shutdown latches stop, changes native state, nudges EE execution, queues
  RequestVMShutdown, then waits up to five seconds for VMState::Shutdown.
  Returning from this JNI call is NOT a join of runVMThread.
- The CPU run loop calls VMManager::Shutdown, which waits for VU/GS, closes SPU2,
  input, devices, disc and memory cards, and closes GS; CPUThreadShutdown then
  waits for savestate writes, joins GS/snapshot work, releases CPU providers and
  SysMemory, and closes native logging. JNI returns only after that path.
- Surface destruction is routed through onNativeSurfaceDestroyed and the
  CPU/GS handoff. Frontend STOPPED must not initiate surface/library transitions
  while the old native run still owns those resources.
- Native shutdown also touches limiter/core state from its JNI caller. Native
  teardown and audio/renderer destruction remain possible independent failure
  sites; no tombstone is available to justify changing the accepted binaries.

### Source repair and diagnostics

Added a tested VmCompletionBarrier used by both game and BIOS paths. It coalesces
stop requests and permits one UI-thread completion only after both JNI run and
shutdown callers return. A native timeout never counts as completed teardown.
Pause/resume/stop now enter through the same Java executor. Closing during boot
waits for an active VM or a cancelled/failed run instead of losing the stop during
Initializing. Existing auto-save behavior is retained. Both stale pause and stale
resume callbacks are rejected while STOPPED. Real Activity destruction requests
the same asynchronous stop rather than a second shutdown/process kill.

Boundary diagnostics go to Android logcat (`NCAA_NEXT`, `VM_EXIT`) and bounded
`logs/shutdown.log`: STOP_REQUEST, STOP_COALESCED, WAIT_BOOT, AUTOSAVE_BEGIN/RETURN,
SHUTDOWN_BEGIN/RETURN, RUN_RETURNED, LIBRARY_READY, RESTART_READY, and exceptions.
The existing crash report now includes this file and a Continue to game library
button. Java exceptions remain visible to the original uncaught-crash handler.

Normal BootSplash startup performs the existing crash check and immediately
forwards to Main. It never creates the intro VideoView or waits on playback.
Intent data, extras, ClipData and URI permissions are retained. Explicit preview
from settings remains available. Android's own launch window remains OS-managed.

### Build and validation plan

Candidate: version 0.1.10-game-exit-no-intro / 128016, package unchanged, pinned
signer unchanged. Fast workflow still reuses Run 6 binaries. In addition to the
existing native/resource comparisons, validation pins native hashes directly to
the device-accepted PR #1 and verifies the exact prior APK hash before checking
update compatibility. The old Build 16 certificate inspection remains separate.
Settings JVM tests, constructor audit, packaged DEX checks, signing, manifest,
ZIP alignment, core resources, and API 35 ART remain required. New JVM tests run
against the actual production barrier, including both completion orders,
duplicate stop, failed boot, repeated sessions, and concurrent returns.

Local pinned-source patch application and lifecycle integration checks passed.
CI/build results and device results are recorded separately below when available.
No physical-device result is claimed by source review or host tests.
See DEVICE_TESTING.md. This PR must stay unmerged until the required device gate
passes. If Close Game still crashes, collect the new boundary log plus Android's
native crash report before choosing a native change.
