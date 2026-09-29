from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/runtime/MainActivityRuntime.kt")
s = p.read_text()

old = '''                    resolved = resolved.copy(
                        memoryCardSlot1Filename = "$serial.ps2",
                        memoryCardSlot1Enabled = true,
                    )
'''
new = '''                    // NCAA NEXT / Android verifier fix:
                    // Settings has >255 constructor fields. Kotlin's generated copy$default
                    // cannot be represented by a DEX invoke-range argument-count byte and
                    // produces invalid bytecode on Android 17. Update through JSON instead.
                    resolved = com.armsx2.config.Settings.fromJson(
                        resolved.toJson().apply {
                            put("memoryCardSlot1Filename", "$serial.ps2")
                            put("memoryCardSlot1Enabled", true)
                        },
                    )
'''
if old not in s:
    raise SystemExit("memory-card Settings.copy block not found")
s = s.replace(old, new, 1)

old = '''            com.armsx2.config.ConfigStore.save(
                if (serial != null) com.armsx2.config.SettingsScope.Game
                else com.armsx2.config.SettingsScope.Global,
                serial,
                resolved.copy(upscaleFloat = nf),
            )
'''
new = '''            val updated = com.armsx2.config.Settings.fromJson(
                resolved.toJson().apply { put("upscaleFloat", nf.toDouble()) },
            )
            com.armsx2.config.ConfigStore.save(
                if (serial != null) com.armsx2.config.SettingsScope.Game
                else com.armsx2.config.SettingsScope.Global,
                serial,
                updated,
            )
'''
if old not in s:
    raise SystemExit("resolution Settings.copy block not found")
s = s.replace(old, new, 1)

p.write_text(s)

data = p.read_text()
if "resolved.copy(" in data:
    raise SystemExit("MainActivityRuntime still contains resolved.copy(")
for marker in (
    "Settings has >255 constructor fields",
    'put("memoryCardSlot1Filename"',
    'put("upscaleFloat"',
):
    if marker not in data:
        raise SystemExit(f"missing verifier-fix marker: {marker}")

print("Eliminated MainActivityRuntime Settings.copy$default verifier hazards")
