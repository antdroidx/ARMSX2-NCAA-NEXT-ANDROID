"""Pass launchers explicitly through Gradle; do not rely on inherited CMake env."""
from pathlib import Path

p = Path('platforms/android/app/build.gradle.kts')
s = p.read_text()
anchor = '                    arguments += "-DANDROID_STL=c++_static"'
if s.count(anchor) != 1:
    raise SystemExit('Gradle CMake anchor changed')
p.write_text(s.replace(anchor, anchor + '''
                    arguments += "-DCMAKE_C_COMPILER_LAUNCHER=ccache"
                    arguments += "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache"''', 1))
