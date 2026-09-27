from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/runtime/MainActivityRuntime.kt")
s = p.read_text()

old = """        // Restore the saved rumble master toggle into the native gate (NativeApp.onPadRumble).
        NativeApp.sRumbleEnabled = ControllerMappings.rumbleEnabled()
        // Push the saved haptic strength + achievement-sound volume into their native gates before
        // any rumble or unlock sound can fire (both default to 1.0 = as authored until set here).
        ControllerMappings.syncHapticIntensity()
        ControllerMappings.syncRumbleFallback()
"""
new = """        // NCAA NEXT diagnostic: do not touch NativeApp during Main.onCreate.
        // NativeApp's static initializer loads the emucore .so; doing that before the
        // first Compose frame made a native-load problem look like a splash-screen crash.
        println("NEXT_STARTUP_MAIN_NO_NATIVE")
"""
if old not in s:
    raise SystemExit("startup rumble/native block not found")
s = s.replace(old, new, 1)

old = """        // ADPF CPU clock hint (experimental, default OFF): re-assert the saved state to native
        // before any game runs. Referencing NativeApp also loads the native lib (static init).
        runCatching { kr.co.iefriends.pcsx2.NativeApp.setAdpfEnabled(prefs.getBoolean("ui.adpf", false)) }
"""
new = """        // NCAA NEXT diagnostic: defer ADPF until emucore initialization so Main can
        // render without loading the native library at splash handoff.
"""
if old not in s:
    raise SystemExit("startup ADPF block not found")
s = s.replace(old, new, 1)

old = """        if (setupComplete.value) {
            kickoffEmucoreInit()
        }
        // else: setContent's LaunchedEffect(setupComplete.value) below
        // calls kickoffEmucoreInit when the wizard finishes.
"""
new = """        // NCAA NEXT diagnostic: always let Compose render first. The existing
        // LaunchedEffect(setupComplete.value) below starts emucore after first composition.
        // This also covers returning users whose setup is already complete.
"""
if old not in s:
    raise SystemExit("eager kickoff block not found")
s = s.replace(old, new, 1)

old = """        runCatching {
            val gl = com.armsx2.GpuInfo.glStrings()
            kr.co.iefriends.pcsx2.NativeApp.setAutoRendererGpuStrings(gl.vendor, gl.renderer, gl.version)
        }

"""
new = """        // NCAA NEXT diagnostic: no NativeApp references on the pre-init path.
        // GPU auto-renderer hints are pushed immediately after initializeOnce below.

"""
if old not in s:
    raise SystemExit("pre-init GPU native block not found")
s = s.replace(old, new, 1)

old = """        invoke {
            NativeApp.initializeOnce(applicationContext)
            nativeReady.value = true

"""
new = """        invoke {
            println("NEXT_STARTUP_BEFORE_NATIVE_INIT")
            NativeApp.initializeOnce(applicationContext)
            println("NEXT_STARTUP_AFTER_NATIVE_INIT")

            // Native gates which upstream touched during Main.onCreate are safe here:
            // the emucore library has now been loaded and the base settings layer exists.
            NativeApp.sRumbleEnabled = ControllerMappings.rumbleEnabled()
            ControllerMappings.syncHapticIntensity()
            ControllerMappings.syncRumbleFallback()
            runCatching { NativeApp.setAdpfEnabled(prefs.getBoolean("ui.adpf", false)) }
            runCatching {
                val gl = com.armsx2.GpuInfo.glStrings()
                NativeApp.setAutoRendererGpuStrings(gl.vendor, gl.renderer, gl.version)
            }

            nativeReady.value = true

"""
if old not in s:
    raise SystemExit("native initialize block not found")
s = s.replace(old, new, 1)

p.write_text(s)

for marker in (
    "NEXT_STARTUP_MAIN_NO_NATIVE",
    "NEXT_STARTUP_BEFORE_NATIVE_INIT",
    "NEXT_STARTUP_AFTER_NATIVE_INIT",
    "always let Compose render first",
):
    if marker not in p.read_text():
        raise SystemExit(f"missing startup diagnostic marker: {marker}")

print("Applied startup native-load isolation patch")
