from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/runtime/MainActivityRuntime.kt")
s = p.read_text()

sig = "    private fun stepResolution(dir: Int) {"
start = s.find(sig)
if start < 0:
    raise SystemExit("stepResolution signature not found")

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
    raise SystemExit("stepResolution body is unbalanced")

replacement = r'''    private fun stepResolution(dir: Int) {
        // NCAA NEXT Android: verifier-safe implementation.
        //
        // Android 17 ART rejects the original method's generated DEX with:
        //   VerifyError in MainActivityRuntime.stepResolution(int)
        //   "Rejecting invocation, expected 0 argument registers..."
        //
        // Keep this method deliberately simple while we isolate the exact
        // Kotlin/D8 construct which produced the invalid invoke instruction.
        var next = upscale.value.toInt() + dir
        if (next < 1) next = 1
        if (next > 8) next = 8
        upscale.value = next.toFloat()
    }'''

s = s[:start] + replacement + s[end:]
p.write_text(s)

data = p.read_text()
for marker in (
    "verifier-safe implementation",
    "upscale.value = next.toFloat()",
):
    if marker not in data:
        raise SystemExit(f"missing stepResolution patch marker: {marker}")

print("Applied verifier-safe stepResolution patch")
