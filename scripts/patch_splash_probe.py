from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/BootSplashActivity.kt")
s = p.read_text()

start = s.find("    private fun launchMainAndFinish() {")
if start < 0:
    raise SystemExit("launchMainAndFinish not found")
brace = s.find("{", start)
depth = 0
end = None
for i in range(brace, len(s)):
    if s[i] == "{":
        depth += 1
    elif s[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end is None:
    raise SystemExit("launchMainAndFinish function is unbalanced")

replacement = r'''    private fun launchMainAndFinish() {
        if (launchedMain) return
        launchedMain = true
        rootView?.removeCallbacks(timeoutRunnable)

        if (preview) {
            finish()
            return
        }

        // NCAA NEXT startup probe:
        // Deliberately DO NOT instantiate or launch Main. If this screen stays
        // visible after the intro animation, BootSplashActivity is healthy and
        // the crash is downstream in Main/class initialization/onCreate.
        val probe = android.widget.TextView(this).apply {
            text = "NCAA NEXT STARTUP PROBE\n\nSplash completed successfully.\nMain activity was intentionally NOT launched.\n\nIf you can read this, the crash is inside Main/startup initialization."
            setTextColor(android.graphics.Color.WHITE)
            setBackgroundColor(android.graphics.Color.BLACK)
            gravity = android.view.Gravity.CENTER
            textSize = 20f
            setPadding(48, 48, 48, 48)
        }
        setContentView(probe)
        rootView = probe
        android.util.Log.i("NCAA_NEXT", "STARTUP_PROBE_SPLASH_PASSED")
    }'''

s = s[:start] + replacement + s[end:]
p.write_text(s)

data = p.read_text()
for marker in (
    "STARTUP_PROBE_SPLASH_PASSED",
    "Main activity was intentionally NOT launched",
):
    if marker not in data:
        raise SystemExit(f"missing splash probe marker: {marker}")

print("Applied splash-to-Main isolation probe")
