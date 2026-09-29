"""Repair frontend session ownership against the pinned ARMSX2 source.

Apply after PR #1's patches. No native code is modified or rebuilt.
"""
from pathlib import Path
import shutil

ROOT = Path('platforms/android/app/src/main/java')
OVERLAY = Path(__file__).resolve().parents[1]


def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Expected one source anchor: {old[:100]!r}')
    return text.replace(old, new, 1)


def replace_body(text, signature, body):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    # These targeted blocks contain balanced braces in comments and strings too.
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[:opening + 1] + '\n' + body + '\n        }' + text[end:]


p = ROOT / 'com/armsx2/runtime/MainActivityRuntime.kt'
s = p.read_text(encoding='utf-8')
s = once(s, '''        private val vmLifecycleLock = Any()
        @Volatile private var vmStopInProgress = false
        @Volatile private var vmRestartAfterStop = false
        @Volatile private var vmRunLoopActive = false''', '''        private val vmLifecycleLock = VmCompletionBarrier()
        private val vmStopInProgress get() = vmLifecycleLock.stopping
        @Volatile private var vmRestartAfterStop = false
        private val vmRunLoopActive get() = vmLifecycleLock.running
        private val vmUi = android.os.Handler(android.os.Looper.getMainLooper())

        private fun shutdownTrace(event: String) {
            android.util.Log.i("NCAA_NEXT", "VM_EXIT $event")
            // Separate from the native session log, which CPUThreadShutdown closes.
            synchronized(vmLifecycleLock) {
                runCatching {
                    val ctx = instance?.applicationContext ?: return@runCatching
                    val dir = java.io.File(ctx.getExternalFilesDir(null) ?: ctx.filesDir, "logs")
                    dir.mkdirs()
                    val file = java.io.File(dir, "shutdown.log")
                    if (file.length() > 65536) file.writeText(file.readText().takeLast(32768))
                    file.appendText("${System.currentTimeMillis()} ${Thread.currentThread().name} $event\\n")
                }
            }
        }

        private fun onVmRunReturned() {
            synchronized(vmLifecycleLock) { vmLifecycleLock.runReturned() }
            shutdownTrace("RUN_RETURNED")
            vmUi.post { completeVmSessionIfReady() }
        }

        private fun completeVmSessionIfReady() {
            check(android.os.Looper.myLooper() == android.os.Looper.getMainLooper())
            synchronized(vmLifecycleLock) {
                if (!vmLifecycleLock.takeCompletion()) return
                val restartNow = vmRestartAfterStop
                vmRestartAfterStop = false
                eState.value = EmuState.STOPPED
                WindowImpl.toolbarVisible.value = true
                WindowImpl.showLibrary.value = false
                WindowImpl.overlayVisible.value = false
                WindowImpl.inGameScreen.value = null
                // Keep the launch lock through cleanup: no old-session cleanup may
                // clear the next game's metadata or release its surface/input.
                if (restartNow && instance?.isDestroyed == false) {
                    shutdownTrace("RESTART_READY")
                    start()
                } else {
                    onReturnedToLibrary()
                    shutdownTrace("LIBRARY_READY")
                    finishToLauncherIfRequested()
                }
            }
        }''')
if s.count('vmRunLoopActive = true') != 2:
    raise RuntimeError('Game/BIOS launch ownership changed')
s = s.replace('vmRunLoopActive = true', 'vmLifecycleLock.beginRun()')

# Both game and BIOS finally blocks publish through the same UI completion path.
for _ in range(2):
    anchor = '                    NativeApp.runVMThread(m_szGamefile)\n                } finally {'
    start = s.index(anchor)
    opening = s.index('{', start + len(anchor) - 1)
    depth, end = 1, opening + 1
    while depth:
        depth += (s[end] == '{') - (s[end] == '}')
        end += 1
    s = s[:start] + '''                    // A close during boot may cancel before JNI starts.
                    if (!vmStopInProgress) NativeApp.runVMThread(m_szGamefile)
                } finally {
                    onVmRunReturned()
                }''' + s[end:]

# JNI control calls now share one queue. Already queued pauses finish before stop;
# subsequent pause/resume requests observe the stop latch and do not enter JNI.
s = once(s, '''        private val vmStopControl = Executors.newSingleThreadExecutor { r ->
            Thread(r, "VMStop")
        }
''', '')
s = replace_body(s, '        fun stop(saveAutosave: Boolean = false, restartAfterStop: Boolean = false)', '''            fastForwardToggleActive = false
            slowDownToggleActive = false
            gyroActive.value = true
            val shouldStop = synchronized(vmLifecycleLock) {
                vmRestartAfterStop = restartAfterStop
                vmLifecycleLock.requestStop()
            }
            if (!shouldStop) {
                shutdownTrace("STOP_COALESCED running=$vmRunLoopActive stopping=$vmStopInProgress")
                return
            }
            shutdownTrace("STOP_REQUEST restart=$restartAfterStop")
            WindowImpl.overlayVisible.value = false
            WindowImpl.showLibrary.value = false
            WindowImpl.inGameScreen.value = null
            stopAutoProgressiveScanHold()
            val doAutosave = saveAutosave || (!restartAfterStop &&
                runCatching { prefs.getBoolean("autoSaveOnExit", false) }.getOrDefault(false))
            vmControl.execute {
                try {
                    // shutdown() ignores Initializing. A close during startup must
                    // wait for an active VM or the cancelled/failed run to return.
                    var waited = 0
                    while (vmRunLoopActive && !NativeApp.hasActiveVM()) {
                        Thread.sleep(10)
                        waited += 10
                        if (waited % 5000 == 0) shutdownTrace("WAIT_BOOT ms=$waited")
                    }
                    if (vmRunLoopActive) {
                        if (doAutosave) {
                            shutdownTrace("AUTOSAVE_BEGIN")
                            val saved = NativeApp.saveAutosaveState()
                            shutdownTrace("AUTOSAVE_RETURN success=$saved")
                        }
                        shutdownTrace("SHUTDOWN_BEGIN")
                        NativeApp.shutdown()
                        shutdownTrace("SHUTDOWN_RETURN running=$vmRunLoopActive")
                    }
                } catch (error: Throwable) {
                    shutdownTrace("SHUTDOWN_EXCEPTION ${error.javaClass.name}: ${error.message}")
                    throw error // Preserve the application's uncaught-crash diagnostics.
                } finally {
                    synchronized(vmLifecycleLock) { vmLifecycleLock.stopReturned() }
                    vmUi.post { completeVmSessionIfReady() }
                }
            }''')

# Real activity destruction must not race another shutdown or kill the process
# while the VM is still flushing memory cards. Configuration recreation is retained.
s = once(s, '''        NativeApp.shutdown()
        super.onDestroy()

        val appPid = Process.myPid()
        Process.killProcess(appPid)''', '''        shutdownTrace("ACTIVITY_DESTROY finishing=$isFinishing running=$vmRunLoopActive")
        stop()
        super.onDestroy()
        // The session completion barrier owns teardown, including a close already
        // in progress. Never kill the process to stand in for joining the VM.''')
p.write_text(s, encoding='utf-8')
shutil.copyfile(OVERLAY / 'frontend/VmCompletionBarrier.kt', p.with_name('VmCompletionBarrier.kt'))

p = ROOT / 'kr/co/iefriends/pcsx2/NativeApp.java'
s = p.read_text(encoding='utf-8')
s = once(s, 'if (!paused && MainActivityRuntime.eState.getValue() == EmuState.STOPPED)',
         'if (MainActivityRuntime.eState.getValue() == EmuState.STOPPED)')
p.write_text(s, encoding='utf-8')
print('Applied VM completion barrier, serialized controls, and exit breadcrumbs; native source untouched')
