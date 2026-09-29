from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/BootSplashActivity.kt")
s = p.read_text()

old = """        super.onCreate(savedInstanceState)
        applyImmersiveUi()
"""
new = """        super.onCreate(savedInstanceState)

        // NCAA NEXT self-debugger: on the first launch of each diagnostic build,
        // clear stale crash files from older versions. If this same build crashed
        // on its previous launch, show that crash log instead of entering Main.
        if (showNcaNextCrashReportIfPresent()) return

        applyImmersiveUi()
"""
if old not in s:
    raise SystemExit("BootSplash onCreate anchor not found")
s = s.replace(old, new, 1)

insert_anchor = """    override fun onDestroy() {
"""
helper = r'''    private fun showNcaNextCrashReportIfPresent(): Boolean {
        val diagPrefs = getSharedPreferences("NCAA_NEXT_DIAG", MODE_PRIVATE)
        val versionCode = runCatching {
            if (android.os.Build.VERSION.SDK_INT >= 28) {
                packageManager.getPackageInfo(packageName, 0).longVersionCode
            } else {
                @Suppress("DEPRECATION")
                packageManager.getPackageInfo(packageName, 0).versionCode.toLong()
            }
        }.getOrDefault(-1L)

        val logDir = java.io.File(getExternalFilesDir(null) ?: filesDir, "logs").apply { mkdirs() }
        val seenVersion = diagPrefs.getLong("diagnosticVersion", Long.MIN_VALUE)

        if (seenVersion != versionCode) {
            // First launch of this APK version: remove only old Java crash reports.
            // session.log is left intact because it can contain useful native breadcrumbs.
            logDir.listFiles { f -> f.isFile && f.name.startsWith("crash-") && f.name.endsWith(".txt") }
                ?.forEach { runCatching { it.delete() } }
            diagPrefs.edit().putLong("diagnosticVersion", versionCode).apply()
            android.util.Log.i("NCAA_NEXT", "DIAG_FIRST_LAUNCH version=$versionCode")
            return false
        }

        val latestCrash = logDir
            .listFiles { f -> f.isFile && f.name.startsWith("crash-") && f.name.endsWith(".txt") }
            ?.maxByOrNull { it.lastModified() }

        val report = buildString {
            appendLine("NCAA NEXT CRASH DEBUGGER")
            appendLine()
            if (latestCrash != null) {
                appendLine("Java/Kotlin crash log captured:")
                appendLine(latestCrash.name)
                appendLine()
                appendLine(runCatching { latestCrash.readText() }.getOrElse { "Could not read crash file: $it" })
            } else {
                appendLine("No Java/Kotlin crash file was captured.")
                appendLine("The previous process may have terminated natively or before the uncaught-exception handler could write.")
                if (android.os.Build.VERSION.SDK_INT >= 30) {
                    runCatching {
                        val am = getSystemService(android.app.ActivityManager::class.java)
                        val exit = am.getHistoricalProcessExitReasons(packageName, 0, 5).firstOrNull()
                        if (exit != null) {
                            appendLine()
                            appendLine("Last Android process exit:")
                            appendLine("reason=undefined")
                            appendLine("status=undefined")
                            appendLine("importance=undefined")
                            appendLine("timestamp=undefined")
                            appendLine("description=undefined")
                        }
                    }
                }
                val session = java.io.File(logDir, "session.log")
                if (session.isFile) {
                    appendLine()
                    appendLine("--- session.log tail ---")
                    val text = runCatching { session.readText() }.getOrDefault("")
                    appendLine(text.takeLast(12000))
                }
            }
        }

        // Only intercept the launch when there is evidence of a previous failure.
        val hasCrash = latestCrash != null
        val hasInterestingExit = if (android.os.Build.VERSION.SDK_INT >= 30) {
            runCatching {
                val am = getSystemService(android.app.ActivityManager::class.java)
                val exit = am.getHistoricalProcessExitReasons(packageName, 0, 3).firstOrNull()
                exit != null && (
                    exit.reason == android.app.ApplicationExitInfo.REASON_CRASH ||
                    exit.reason == android.app.ApplicationExitInfo.REASON_CRASH_NATIVE ||
                    exit.reason == android.app.ApplicationExitInfo.REASON_ANR
                )
            }.getOrDefault(false)
        } else false

        if (!hasCrash && !hasInterestingExit) return false

        val textView = android.widget.TextView(this).apply {
            text = report
            setTextColor(android.graphics.Color.WHITE)
            setBackgroundColor(android.graphics.Color.BLACK)
            textSize = 12f
            setPadding(32, 32, 32, 32)
            setTextIsSelectable(true)
        }
        val scroll = android.widget.ScrollView(this).apply {
            setBackgroundColor(android.graphics.Color.BLACK)
            addView(textView)
        }
        setContentView(scroll)
        rootView = scroll
        android.util.Log.i("NCAA_NEXT", "DIAG_CRASH_REPORT_SHOWN")
        return true
    }

'''
if insert_anchor not in s:
    raise SystemExit("BootSplash helper insertion anchor not found")
s = s.replace(insert_anchor, helper + insert_anchor, 1)

p.write_text(s)

for marker in ("NCAA NEXT CRASH DEBUGGER", "DIAG_CRASH_REPORT_SHOWN", "REASON_CRASH_NATIVE"):
    if marker not in p.read_text():
        raise SystemExit(f"missing crash debugger marker: {marker}")

print("Applied on-device crash report debugger")

