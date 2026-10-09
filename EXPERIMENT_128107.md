# NCAA NEXT experimental APK 128107

This build tests hypotheses; it does not establish a root cause or claim a fix.
Package: `com.armsx2.ncaanext.alphaexperiment`, label: **NCAA NEXT Alpha 128107**.
It can coexist with validated 128105 and the USC diagnostic app. No main workflow,
source PNG, JD4029 hash algorithm, EE RAM geometry, or memory-card geometry changes.
The experimental app has separate settings/storage; configure its BIOS/game and
texture folder as usual. Avoid simultaneously opening the same memory card in two apps.

## Controls

Create `next128107.txt` in the configured **textures root folder** (the directory
containing `SLUS-21214`, not the replacements folder). With no file, both tests
use the original renderer. Fully stop and restart the experimental app after each
edit so decoded replacement and source caches are rebuilt. Do not change the file
mid-game. Only NCAA Football 06 serial `SLUS-21214` is eligible.

Example control file:

```text
wsu=0
usc=0
wsu_file=EXACT-WSU-REPLACEMENT-FILENAME.png
```

Replace the placeholder with the actual complete legacy filename including hash,
CLUT hash (if present), encoded texture bits and `.png`. No WSU hash is inferred
from color, dimensions, or unrelated USC files. A missing/unmatched WSU selector
leaves its rendering unchanged. WSU selectors matching known USC hashes are rejected.
USC is restricted to the eight existing diagnostic number-atlas hashes and
128/256 square PSMT4 atlases. Only replacement-backed draws are modified.

Each team has an independent mode:

| Mode | Test |
| --- | --- |
| 0 | Original rendering control. |
| 1 | Rescale decoded RGBA8 replacement alpha from 0–255 to 0–128, preserving RGB and disk PNGs. Includes supplied mip levels and recalculates alpha bounds. Compressed textures are logged and skipped. |
| 2 | On simple MODULATE draws, use DECAL RGB to isolate vertex color modulation. Texture alpha selection remains unchanged. |
| 3 | On simple draws with hardware blending enabled, disable that blending to isolate destination color contribution. A draw with no hardware blending is logged as unapplied. |

Modes 2 and 3 leave multipass, software/mixed blending, feedback, and shuffle
draws on control. They are diagnostic probes and may look worse. They do not
rewrite GS registers, vertex buffers or replacement cache pixels. Mode 1 changes
only the matching private decoded replacement buffers for that app session.

## Compare independently

1. Use `wsu=0`, `usc=0`; capture the WSU logo over crimson and the gray stripe,
   and USC jersey numbers under consistent lighting/camera.
2. Keep `usc=0`; compare WSU modes 1, 2, and 3 one at a time, restarting each time.
3. Restore `wsu=0`; compare USC modes 1, 2, and 3 one at a time.
4. Restore both to 0 and confirm the control returns. Remove the file to disable all tests.

Collect `emulog.txt` and screenshots for each comparison. `NEXT128107 config`
records requested modes and whether a WSU key parsed. `NEXT128107 alpha` records
applied/skipped decoded alpha changes. `NEXT128107 draw` records full texture and
CLUT hashes, whether a draw test applied, and control/test shader and blend keys.
The existing `USC-DIAG` rows describe the original final configuration before the
late draw experiment; use `NEXT128107 draw` for the actual changed configuration.
No applied row means no demonstrated test of that draw; do not interpret it as a fix.

The artifact includes APK manifest, signing verification, build commit/version,
SHA-256, this guide, and compiler cache details. CI verifies build integrity;
on-device WSU/USC visual correctness still requires the comparisons above.
