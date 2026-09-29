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
