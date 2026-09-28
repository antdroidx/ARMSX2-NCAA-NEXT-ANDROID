from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/Main.kt")
p.write_text(r'''package com.armsx2

import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.TextView
import androidx.activity.ComponentActivity

class Main : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        android.util.Log.i("NCAA_NEXT", "MAIN_PROBE_ONCREATE_PASSED")

        val probe = TextView(this).apply {
            text = "NCAA NEXT MAIN PROBE\n\nMain activity launched successfully.\nMainActivityRuntime was intentionally NOT loaded.\n\nIf you can read this, the crash is inside MainActivityRuntime initialization/onCreate."
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.BLACK)
            gravity = Gravity.CENTER
            textSize = 20f
            setPadding(48, 48, 48, 48)
        }

        setContentView(probe)
    }
}
''')

data = p.read_text()
for marker in ("MAIN_PROBE_ONCREATE_PASSED", "MainActivityRuntime was intentionally NOT loaded"):
    if marker not in data:
        raise SystemExit(f"missing Main probe marker: {marker}")

print("Applied minimal Main activity probe")
