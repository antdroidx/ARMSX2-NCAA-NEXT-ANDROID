#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
adb devices
adb logcat -c
trap 'adb logcat -d > out/art-logcat.txt || true' EXIT
adb push work/art-smoke.jar /data/local/tmp/art-smoke.jar
adb push "$(find previous -name '*.apk' -print -quit)" /data/local/tmp/build16.apk
adb push out/ARMSX2-NCAA-NEXT-ANDROID-RUNTIME-PROBE-fast-debug.apk /data/local/tmp/frontend.apk
# Dynamic code loading on recent Android requires read-only files.
adb shell chmod 444 /data/local/tmp/art-smoke.jar /data/local/tmp/build16.apk /data/local/tmp/frontend.apk
set +e
adb shell 'CLASSPATH=/data/local/tmp/art-smoke.jar:/data/local/tmp/build16.apk app_process /system/bin SettingsArtSmoke' > out/art-build16-negative.log 2>&1
baseline_status=$?
set -e
cat out/art-build16-negative.log
if [[ "$baseline_status" -eq 0 ]] || ! grep -q 'VerifyError' out/art-build16-negative.log; then
  echo "Build 16 did not reproduce the expected verifier failure; inspect the smoke harness."
  exit 1
fi
adb shell 'CLASSPATH=/data/local/tmp/art-smoke.jar:/data/local/tmp/frontend.apk app_process /system/bin SettingsArtSmoke' 2>&1 | tee out/art-smoke.log
grep -q 'SETTINGS_ART_SMOKE_OK' out/art-smoke.log
