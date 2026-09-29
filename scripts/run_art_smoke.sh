#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
adb devices
adb logcat -c
trap 'adb logcat -d > out/art-logcat.txt || true' EXIT
adb push work/art-smoke.jar /data/local/tmp/art-smoke.jar
adb push out/ARMSX2-NCAA-NEXT-ANDROID-RUNTIME-PROBE-fast-debug.apk /data/local/tmp/frontend.apk
# Dynamic code loading on recent Android requires read-only files.
adb shell chmod 444 /data/local/tmp/art-smoke.jar /data/local/tmp/frontend.apk
adb shell 'CLASSPATH=/data/local/tmp/art-smoke.jar:/data/local/tmp/frontend.apk app_process /system/bin SettingsArtSmoke' 2>&1 | tee out/art-smoke.log
grep -q 'SETTINGS_ART_SMOKE_OK' out/art-smoke.log
