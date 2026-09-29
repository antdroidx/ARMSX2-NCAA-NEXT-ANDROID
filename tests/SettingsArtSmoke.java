import java.lang.reflect.Method;

/**
 * Runs with app_process and the APK on its classpath, without loading ARM JNI.
 * Reflection keeps this harness independent of the app and Android SDK at compile time.
 */
public final class SettingsArtSmoke {
    public static void main(String[] args) throws Exception {
        Class<?> settings = Class.forName("com.armsx2.config.Settings");
        Object companion = settings.getField("Companion").get(null);
        Class<?> json = Class.forName("org.json.JSONObject");
        Method fromJson = companion.getClass().getMethod("fromJson", json);
        Object defaults = fromJson.invoke(companion, json.getConstructor().newInstance());
        Object roundTrip = fromJson.invoke(companion, settings.getMethod("toJson").invoke(defaults));
        if (!defaults.equals(roundTrip) || defaults.hashCode() != roundTrip.hashCode()) {
            throw new AssertionError("Settings JSON round-trip/equality failed");
        }
        Object changed = fromJson.invoke(companion,
                json.getConstructor(String.class).newInstance("{\"audioVolume\":47}"));
        if (!settings.getMethod("getAudioVolume").invoke(changed).equals(47)
                || defaults.equals(changed)) {
            throw new AssertionError("Settings update failed");
        }
        if (settings.getDeclaredConstructors().length != 1
                || settings.getDeclaredConstructors()[0].getParameterTypes().length != 246) {
            throw new AssertionError("Unsafe or unexpected Settings constructors");
        }
        System.out.println("SETTINGS_ART_SMOKE_OK: class verified, defaults/update/round-trip passed");
    }
}
