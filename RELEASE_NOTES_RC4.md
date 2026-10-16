## ARMSX2 Extended 0.2.5-RC4

- Cache replacement-texture filenames for faster repeat boots; add manual Refresh texture index.
- Reduce texture-loading bookkeeping, duplicate cache accounting and redundant pixel conversion.
- Add ARM64 VIF copy efficiencies with overlap handling and corrected 256-row skip checks.
- Enable selectable EE fast memory by default with 128 MB mapping/remap and allocation-fallback fixes; preserve saved/per-game Off choices.
- Avoid redundant Vulkan upload transitions and identical aligned fallback copies.
- Reduce repeated audio-affinity retries when Android rejects pinning.
- NCAA 06 / NEXT (SLUS-21214) defaults: mipmapping Off, bilinear PS2, trilinear PS2; preserve existing VU clamp and per-game overrides. Trilinear database selection applies when Auto is selected.
- Restore GS Multi-Threading Off for fresh defaults/presets; preserve saved choices.

Automated native, ARM64 simulator, Android build, signing, Settings bytecode and DEX checks passed for tested candidates. The tester reports working gameplay and faster repeat boots; fast memory reduced reported EE load. No consistent gameplay-speed gain from the latest Vulkan changes was established. Driver choice materially affected reported speed.

Uses the existing Extended package and production certificate for updates over RC2/RC3 and RC4 tests, retaining settings and saves.

Known issue: NCAA NEXT Press Start artwork can appear too dark. If a game regresses with Fastmem enabled, turn it Off and restart the game.
