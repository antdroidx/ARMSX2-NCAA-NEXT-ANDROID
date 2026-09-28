from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/runtime/MainActivityRuntime.kt")
s = p.read_text()

old = """override fun onCreate(savedInstanceState: Bundle?) {
        applyEdgeToEdge()
        super.onCreate(savedInstanceState)
"""
new = """override fun onCreate(savedInstanceState: Bundle?) {
        applyEdgeToEdge()
        super.onCreate(savedInstanceState)

        // NCAA NEXT fast startup bisect. Reaching this point proves that
        // MainActivityRuntime class/property initialization and ComponentActivity
        // onCreate completed. Stop before the normal ARMSX2 startup body.
        android.util.Log.i("NCAA_NEXT", "RUNTIME_EARLY_ONCREATE_PASSED")
        val runtimeProbe = android.widget.TextView(this).apply {
            text = "NCAA NEXT RUNTIME PROBE\\n\\nMainActivityRuntime loaded successfully.\\nBase onCreate completed.\\nNormal runtime initialization was intentionally skipped.\\n\\nIf you can read this, the crash is later inside MainActivityRuntime.onCreate."
            setTextColor(android.graphics.Color.WHITE)
            setBackgroundColor(android.graphics.Color.BLACK)
            gravity = android.view.Gravity.CENTER
            textSize = 20f
            setPadding(48, 48, 48, 48)
        }
        setContentView(runtimeProbe)
        return
"""
if old not in s:
    raise SystemExit("MainActivityRuntime onCreate prologue not found")
s = s.replace(old, new, 1)
p.write_text(s)

data = p.read_text()
for marker in (
    "RUNTIME_EARLY_ONCREATE_PASSED",
    "Normal runtime initialization was intentionally skipped",
):
    if marker not in data:
        raise SystemExit(f"missing runtime probe marker: {marker}")

print("Applied early MainActivityRuntime onCreate probe")
