"""Fail closed if the pinned-source lifecycle integration drifts before compilation."""
from pathlib import Path

root = Path('platforms/android/app/src/main/java')
runtime = (root / 'com/armsx2/runtime/MainActivityRuntime.kt').read_text(encoding='utf-8')
native = (root / 'kr/co/iefriends/pcsx2/NativeApp.java').read_text(encoding='utf-8')
boot = (root / 'com/armsx2/BootSplashActivity.kt').read_text(encoding='utf-8')
assert runtime.count('NativeApp.shutdown()') == 1, 'Shutdown must have one owner'
assert runtime.count('onVmRunReturned()') == 3, 'Both game and BIOS must join completion'
assert runtime.count('vmLifecycleLock.beginRun()') == 2
assert runtime.count('eState.value = EmuState.STOPPED') == 1, 'Only UI completion publishes STOPPED'
assert 'vmStopControl' not in runtime
assert 'Process.killProcess' not in runtime
assert 'if (!paused && MainActivityRuntime.eState.getValue() == EmuState.STOPPED)' not in native
create = boot[boot.index('override fun onCreate'):boot.index('private fun showNcaNextCrashReportIfPresent')]
assert create.index('showNcaNextCrashReportIfPresent()') < create.index('if (!preview)')
assert create.index('STARTUP_INTRO_BYPASSED') < create.index('setContentView(R.layout.activity_boot_splash)')
assert 'bootLogoEnabled' not in create
assert 'source.clipData?.let(launch::setClipData)' in boot
assert 'FLAG_GRANT_PERSISTABLE_URI_PERMISSION' in boot
print('Lifecycle integration and no-intro source checks passed')
