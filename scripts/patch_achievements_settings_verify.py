from pathlib import Path

p = Path("platforms/android/app/src/main/java/com/armsx2/ui/achievements/AchievementsViewModel.kt")
s = p.read_text()

replacements = {
'''        saveRa { it.copy(achievementsHardcore = target) }
''':
'''        saveRa { it.put("achievementsHardcore", target) }
''',
'''        saveRa {
            when (key) {
                "notifications" -> it.copy(achievementsNotifications = enabled)
                "leaderboardNotifications" -> it.copy(achievementsLeaderboardNotifications = enabled)
                "overlays" -> it.copy(achievementsOverlays = enabled)
                "lbOverlays" -> it.copy(achievementsLbOverlays = enabled)
                "soundEffects" -> it.copy(achievementsSoundEffects = enabled)
                "encoreMode" -> it.copy(achievementsEncoreMode = enabled)
                "spectatorMode" -> it.copy(achievementsSpectatorMode = enabled)
                "unofficialTestMode" -> it.copy(achievementsUnofficialTestMode = enabled)
                else -> it
            }
        }
''':
'''        saveRa { json ->
            when (key) {
                "notifications" -> json.put("achievementsNotifications", enabled)
                "leaderboardNotifications" -> json.put("achievementsLeaderboardNotifications", enabled)
                "overlays" -> json.put("achievementsOverlays", enabled)
                "lbOverlays" -> json.put("achievementsLbOverlays", enabled)
                "soundEffects" -> json.put("achievementsSoundEffects", enabled)
                "encoreMode" -> json.put("achievementsEncoreMode", enabled)
                "spectatorMode" -> json.put("achievementsSpectatorMode", enabled)
                "unofficialTestMode" -> json.put("achievementsUnofficialTestMode", enabled)
            }
        }
''',
'''        saveRa {
            when (key) {
                "notificationsDuration" -> it.copy(achievementsNotificationsDuration = value)
                "leaderboardsDuration" -> it.copy(achievementsLeaderboardsDuration = value)
                "notificationPosition" -> it.copy(achievementsNotificationPosition = value)
                "overlayPosition" -> it.copy(achievementsOverlayPosition = value)
                "notificationScale" -> it.copy(achievementsNotificationScale = value)
                else -> it
            }
        }
''':
'''        saveRa { json ->
            when (key) {
                "notificationsDuration" -> json.put("achievementsNotificationsDuration", value)
                "leaderboardsDuration" -> json.put("achievementsLeaderboardsDuration", value)
                "notificationPosition" -> json.put("achievementsNotificationPosition", value)
                "overlayPosition" -> json.put("achievementsOverlayPosition", value)
                "notificationScale" -> json.put("achievementsNotificationScale", value)
            }
        }
''',
'''        saveRa { it.copy(achievementsEnabled = enabled) }
''':
'''        saveRa { it.put("achievementsEnabled", enabled) }
''',
'''    private fun saveRa(change: (Settings) -> Settings) {
        val serial = scopeSerial()
        val previous = ConfigStore.resolveForGame(serial)
        val updated = change(previous)
        if (updated == previous) return
        ConfigStore.save(if (serial != null) SettingsScope.Game else SettingsScope.Global, serial, updated, previous)
        applySaved(serial)
    }
''':
'''    private fun saveRa(change: (JSONObject) -> Unit) {
        val serial = scopeSerial()
        val previous = ConfigStore.resolveForGame(serial)

        // NCAA NEXT / Android 17 verifier fix:
        // Settings is a very large data class. Kotlin's generated copy$default helper
        // requires more argument registers than DEX can safely encode, and ART 17
        // rejects every lambda which invokes it. Mutate the JSON representation and
        // reconstruct Settings instead, so no Settings.copy/copy$default call is emitted.
        val json = previous.toJson()
        change(json)
        val updated = Settings.fromJson(json)

        if (updated == previous) return
        ConfigStore.save(if (serial != null) SettingsScope.Game else SettingsScope.Global, serial, updated, previous)
        applySaved(serial)
    }
'''
}

for old, new in replacements.items():
    if old not in s:
        raise SystemExit("Expected AchievementsViewModel verifier block not found:\n" + old[:120])
    s = s.replace(old, new, 1)

p.write_text(s)

data = p.read_text()
bad_patterns = (
    "saveRa { it.copy(",
    "-> it.copy(achievements",
    "private fun saveRa(change: (Settings) -> Settings)",
)
for pattern in bad_patterns:
    if pattern in data:
        raise SystemExit(f"AchievementsViewModel still contains verifier hazard: {pattern}")

for marker in (
    "Android 17 verifier fix",
    'json.put("achievementsNotifications"',
    'it.put("achievementsEnabled"',
):
    if marker not in data:
        raise SystemExit(f"Missing Achievements verifier-fix marker: {marker}")

print("Eliminated AchievementsViewModel Settings.copy$default verifier hazards")
