Renderer settings organization
===============================

The renderer menu now groups settings in this order:

1. Renderer, driver, shader cache and resolution.
2. Texture filtering (expanded initially): mipmapping, trilinear, anisotropic and bilinear filtering.
3. Texture packs: replacement method, pack management, loading, importing and dumping.
4. Renderer performance: GS multithreading, texture preloading and hardware download mode.
5. Screen layout: aspect ratios, orientation, positioning and deinterlacing.
6. Display effects, overlay artwork and advanced blending controls.

GS multithreading defaults to Pipelined (3), and MTVU defaults to enabled on every device, including first-run device defaults. Optimal, Fast and Low-End presets all enable both. Software renderer threads retain the existing default of four extra threads. Existing saved global and per-game values remain authoritative; users can still disable threading for compatibility. GS changes require a game restart.

Validation: applied the complete frontend patch sequence to the pinned upstream source, including the 247-field Settings verifier repair. Checked that every existing translated renderer label remains present and that mipmapping/trilinear controls precede effects. APK compilation and on-device menu validation remain pending; no Actions build is triggered automatically.
