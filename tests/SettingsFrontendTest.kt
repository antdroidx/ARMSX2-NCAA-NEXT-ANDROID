package com.armsx2.config

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Exercises the actual patched production class without starting JNI. */
class SettingsFrontendTest {
    @Test fun defaultsAndRoundTrip() {
        val first = Settings.fromJson(JSONObject())
        val second = Settings.fromJson(first.toJson())
        assertEquals(first, second)
        assertEquals(first.hashCode(), second.hashCode())
        assertEquals(0, first.eeCycleRate)
        assertEquals(100, first.audioVolume)
        assertTrue(first.mtvu)
    }

    @Test fun updatesKeepUnrelatedSettings() {
        val initial = Settings.fromJson(JSONObject())
        val changed = initial.withJson {
            put("audioVolume", 47)
            put("memoryCardSlot1Filename", "NEXT.ps2")
        }
        assertEquals(47, changed.audioVolume)
        assertEquals("NEXT.ps2", changed.memoryCardSlot1Filename)
        assertEquals(initial.eeCycleRate, changed.eeCycleRate)
        assertEquals(100, initial.audioVolume)
        assertNotEquals(initial, changed)
        assertEquals(changed, Settings.fromJson(changed.toJson()))
    }

    @Test fun structuredFieldsSurviveUpdates() {
        val initial = Settings.fromJson(JSONObject())
        val hosts = listOf(Dev9HostMapping("next.example", "192.0.2.1", true))
        val params = mapOf("shader.slangp" to mapOf("SHARPNESS" to 0.5f))
        val changed = initial.withJson {
            put("dev9EthHosts", hosts)
            put("shaderChainParams", params)
        }
        assertEquals(hosts, changed.dev9EthHosts)
        assertEquals(params, changed.shaderChainParams)
        assertEquals(changed, Settings.fromJson(changed.toJson()))
    }

    @Test fun unsafeGeneratedMethodsAreAbsent() {
        val constructors = Settings::class.java.declaredConstructors
        assertEquals(1, constructors.size)
        assertEquals(246, constructors.single().parameterCount)
        assertFalse(Settings::class.java.declaredMethods.any { it.name == "copy" + '$' + "default" })
        assertFalse(constructors.any { ctor ->
            ctor.parameterTypes.any { it.name.contains("DefaultConstructorMarker") }
        })
    }
}
