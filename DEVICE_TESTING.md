# Device acceptance — do not merge before this passes

Current crash-only candidate: `com.armsx2.ncaanext`, versionCode `128103`,
versionName `0.2.3-next128-mc64-stopcpu`. Install as an update over the working
4K/128 MB/64 MB build (`128102`); the pinned signer matches. Back up saves before
testing. Historical runtime-probe Build 16 used a different signer and is not
the update baseline. Record the device, Android version, renderer, APK hash,
whether launched from the library or an external frontend, and autosave setting.

## Required gate

1. Cold-launch the app. The normal frontend should appear without the intro
   video or artificial delay. Android may still show its own launch window.
   Open Settings, return, and verify saved paths/settings remain intact.
2. Launch a game from the app library and play. Confirm controls, graphics,
   audio and memory-card saves work.
3. Launch NCAA NEXT 27 and reach actual gameplay that exercises extended RAM.
   Compare against the accepted baseline, not just the title screen.
4. During gameplay, press Pause -> app menu -> **Close Game**. Expect the same
   app to return to its game library, without exiting, freezing, or restarting.
5. Immediately launch the game again. Repeat steps 3–4 at least five times.
   Try tapping Close Game twice quickly. No duplicate shutdown or stale pause
   should affect the next session.
   Also repeat **Reset Game** five times: it must return to a newly running game
   without exiting Android, showing the intro, or losing memory-card progress.
6. Exit the app normally, relaunch, and run/close another game. Repeat after
   background/foreground and screen off/on while the pause menu is open.

Also test autosave on/off (and reload saved progress), Reset Game, BIOS close,
close during startup, renderer-specific Vulkan/OpenGL behavior where supported,
and rotation/DeX if used. An external frontend may intentionally regain focus
when its existing exit-to-launcher setting is enabled; record that separately.

## If it fails

Do not clear app data. Relaunch and copy the selectable crash report, including
the new shutdown.log tail. Use **Continue to game library** to leave the report.
Files remain in the app's external files `logs` directory (`crash-*.txt`,
`session.log`, `shutdown.log`). Native crashes may have no Java crash file.

Optional ADB capture (start before reproducing; stop with Ctrl+C afterwards):

```sh
adb logcat -v threadtime > game-exit-logcat.txt
adb pull /sdcard/Android/data/com.armsx2.ncaanext/files/logs game-exit-logs
adb bugreport game-exit-bugreport.zip
```

Review a bugreport before sharing: it can contain unrelated device information.
If external files are inaccessible, use the in-app report/log export.

Interpretation: SHUTDOWN_RETURN alone is not success. RUN_RETURNED and then
LIBRARY_READY establish that both Java/JNI callers finished and the frontend
published the library. A last SHUTDOWN_BEGIN with a native crash needs a native
stack/tombstone; a long WAIT_BOOT means startup has not reached an active VM.
Full logcat is useful because SIGSEGV/SIGABRT/ANR details may use other tags.
The new asynchronous native stop normally returns SHUTDOWN_RETURN before
RUN_RETURNED. This is expected: the frontend barrier still waits for both.
Logcat additionally contains NATIVE_STOP_QUEUED and NATIVE_STOP_CPU (or
NATIVE_STOP_STALE / NATIVE_STOP_NO_OWNER when a request is no longer needed).

## Optional enhancement comparison

After 128103 passes, compare `128105 / 0.2.5-next128-mc64-cpu-audio` against it.
Do not install 128105 first: normal Android updates cannot downgrade versionCode.
Keep scene, camera, renderer, resolution, settings and temperature comparable.
Record several warm runs of emulation speed/frame time and audio dropouts.
Check speaker, wired/USB and Bluetooth output as available; exercise pause,
resume and route reconnection. Recheck Close/Reset and saved progress.
The workflow also exposes a CPU/VIF-only 128104 variant for finer isolation;
test it before 128105 if using it. No FPS improvement is claimed before measurement.
See SELECTIVE_AUDIT.md for the selected/deferred commits and host-test limits.

## Sign-off record

- APK SHA-256 / CI run:
- Device / Android / renderer:
- Library launch and Settings:
- NEXT 27 gameplay and extended RAM:
- Pause -> Close Game (including repeated cycles):
- Saves / autosave / reset:
- App exit and relaunch:
- Background/foreground / rotation:
- Remaining failures, with logs:

All four primary outcomes—launch, NEXT 27, game exit, and relaunch—must be
confirmed on a physical device before merging. Passing CI alone is insufficient.
