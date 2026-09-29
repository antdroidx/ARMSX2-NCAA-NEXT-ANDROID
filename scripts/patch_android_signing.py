"""Point Gradle at the exact restored key instead of its implicit debug path."""
from pathlib import Path

p = Path('platforms/android/app/build.gradle.kts')
s = p.read_text()
anchor = '    signingConfigs {\n'
if s.count(anchor) != 1:
    raise SystemExit('Expected exactly one Android signingConfigs block')
explicit = '''        getByName("debug") {
            storeFile = file(System.getProperty("user.home") + "/.android/ncaa-next-debug.jks")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
'''
p.write_text(s.replace(anchor, anchor + explicit, 1))
print('Bound Gradle debug signing to the pinned NCAA NEXT development key')
