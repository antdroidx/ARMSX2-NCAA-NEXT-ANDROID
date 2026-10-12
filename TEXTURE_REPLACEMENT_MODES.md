# Per-game texture replacement modes

Implemented in the RC3 test candidate. Device validation is still required.

Add **Texture replacement method** beside the texture-pack switch in Graphics:

- **Auto (recommended):** Legacy JD4029 for `SLUS-21214`; Current ARMSX2 otherwise.
- **Legacy:** Override for packs made with the older JD4029 dumper.
- **Current ARMSX2:** Override for packs made with the current dumper.

Uses existing global and per-game settings scopes. Missing values in existing
configurations mean Auto. Changing the method requires restarting the game.
Selecting a method does not automatically enable texture replacements.

## Native implementation

The workflow's unconditional JD4029 patch is replaced with a patch retaining both
the pinned upstream and proven legacy algorithms. Resolve Auto using the loaded
game's serial on the GS thread. Pack age is not inferred from alpha values and
only the selected hash method runs for each draw.

Switch all compatibility behavior together: texture regions, full-texture and
mip hashing, TEX0 key masking, TCC filename parsing, and filename/cache-key
conversion. Current mode ignores the historical TCC bit as upstream does; Legacy
preserves it. Dumps and replacement lookups must use the same mode.

The native restart-option mechanism defers live method changes to the next boot.
Renderer initialization recreates the map and caches. A serial change waits for
worker jobs to finish, clears GS sources and hash entries, and reloads replacement
textures and dumped-texture tracking. Keys are not reused across modes.

Keep NCAA number/logo alpha correction separate and scoped to NCAA legacy mode.
Switching hashes does not itself fix blending. Preserve other games' alpha values.

## Settings and validation

The field is wired through Android JSON persistence, global/per-game merge and
diff, native export, reset, and equality/restart checks. The verifier patch now
supports the additional field, and the production build audits compiled Settings
and APK DEX invocation widths.

Verification compares generated region/hash/key algorithm bodies with digest
fixtures from both original implementations, and compiles the actual resolver
to check Auto and explicit overrides. It also checks TCC handling, cache reset,
and persistence paths. The alpha harness checks that Current disables the NCAA
correction. Device acceptance needs NCAA NEXT and a current-format pack, including
switching games and explicit overrides in both directions.

## NCAA defaults

Use the game database for supported NCAA defaults. Review frontend/database
interaction for each setting: not every Android UI option necessarily maps to
YAML. Preserve user overrides. Branding work does not change game defaults.
