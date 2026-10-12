# Proposed per-game texture replacement modes

This describes the next feature. The runtime selector is not implemented by the
branding change.

Add **Texture replacement method** beside the texture-pack switch in Graphics:

- **Auto (recommended):** Legacy JD4029 for `SLUS-21214`; Current ARMSX2 otherwise.
- **Legacy JD4029:** Override for packs made with the older dumper.
- **Current ARMSX2:** Override for packs made with the current dumper.

Use existing global and per-game settings scopes. Missing values in existing
configurations mean Auto. Changing the method requires restarting the game.
Selecting a method does not automatically enable texture replacements.

## Native implementation

Replace the workflow's unconditional JD4029 patch with a patch retaining both
the pinned upstream and proven legacy algorithms. Resolve Auto using the loaded
game's serial, then pass the effective mode to the GS thread. Do not infer pack
age from alpha values or try both hashes for every draw.

Switch all compatibility behavior together: texture regions, full-texture and
mip hashing, TEX0 key masking, TCC filename parsing, and filename/cache-key
conversion. Current mode ignores the historical TCC bit as upstream does; Legacy
preserves it. Dumps and replacement lookups must use the same mode.

Use the native restart-option mechanism. On a game or effective-mode change,
reload the replacement map and discard pending worker jobs, replacement textures,
hash-cache entries and dumped-texture tracking. Never reuse keys across modes.

Keep NCAA number/logo alpha correction separate and scoped to NCAA legacy mode.
Switching hashes does not itself fix blending. Preserve other games' alpha values.

## Settings and validation

Wire the field through Android JSON persistence, global/per-game merge and diff,
native settings export, reset, and native equality/restart checks. Adding a field
also requires updating the verifier patch's 246-field guard and repeating DEX
validation.

Compare fixed texture-key fixtures against both original implementations:
paletted/non-paletted textures, TCC on/off, regions and mipmaps. Check Auto for
NCAA and another serial, explicit overrides, persistence and switching games in
both directions. Device acceptance needs NCAA NEXT and a current-format pack.

## NCAA defaults

Use the game database for supported NCAA defaults. Review frontend/database
interaction for each setting: not every Android UI option necessarily maps to
YAML. Preserve user overrides. Branding work does not change game defaults.
