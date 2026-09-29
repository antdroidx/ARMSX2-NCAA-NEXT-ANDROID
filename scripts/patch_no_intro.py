"""Bypass startup video after the crash check; retain explicit settings preview."""
from pathlib import Path

p = Path('platforms/android/app/src/main/java/com/armsx2/BootSplashActivity.kt')
s = p.read_text(encoding='utf-8')
old = '''        val prefs = getSharedPreferences("ARMSX2", MODE_PRIVATE)
        val bootLogoEnabled = prefs.getBoolean("ui.bootLogo", true)
        if (!preview && (!bootLogoEnabled || playedThisProcess)) {'''
assert s.count(old) == 1, 'Splash source changed'
s = s.replace(old, '''        // NCAA NEXT: no video, codec, or artificial delay on normal startup.
        // Keep this launcher as the crash-report gate and intent/URI-grant forwarder.
        if (!preview) {
            android.util.Log.i("NCAA_NEXT", "STARTUP_INTRO_BYPASSED")''', 1)

# Keep every captured crash accessible, with a way back to the frontend.
old = '''        setContentView(scroll)
        rootView = scroll'''
new = '''        val shutdown = java.io.File(logDir, "shutdown.log")
        if (shutdown.isFile) textView.append("\\n--- shutdown.log tail ---\\n" +
            runCatching { shutdown.readText().takeLast(16000) }.getOrDefault("unreadable"))
        val content = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setBackgroundColor(android.graphics.Color.BLACK)
            addView(android.widget.Button(this@BootSplashActivity).apply {
                text = "Continue to game library"
                setOnClickListener { launchMainAndFinish() }
            })
            addView(scroll, android.widget.LinearLayout.LayoutParams(-1, 0, 1f))
        }
        setContentView(content)
        rootView = content'''
assert s.count(old) == 1, 'Apply PR #1 crash debugger first'
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Normal startup intro bypassed; crash debugger and intent forwarding retained')
