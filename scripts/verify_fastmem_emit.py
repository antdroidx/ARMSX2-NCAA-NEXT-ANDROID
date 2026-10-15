"""Execute original ARM64 fastmem emitters in the pinned VIXL simulator."""
from pathlib import Path
import subprocess,tempfile
from patch_conservative_gs import function
repo=Path(__file__).resolve().parents[1];root=Path.cwd()
s=Path('pcsx2/arm64/recVTLB-arm64.cpp').read_text()
fns=['static void vtlbGetLiveRegisterMasks(', 'static void vtlbFastmemRead(', 'static void vtlbFastmemWrite(', 'static void vtlbFastmemRead128(', 'static void vtlbFastmemWrite128(', 'static void vtlbFastmemReadFPR32(']
code=(repo/'tests/fastmem_emit_harness.cpp').read_text().replace('// EMITTERS','\n'.join(function(s,f) for f in fns))
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp);(t/'test.cpp').write_text(code)
 cmake=f'''cmake_minimum_required(VERSION 3.22)
project(FastmemEmission LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
add_subdirectory("{(root/'3rdparty/vixl').as_posix()}" vixl)
target_compile_definitions(vixl PUBLIC VIXL_INCLUDE_SIMULATOR_AARCH64 VIXL_DEBUG)
target_compile_options(vixl PRIVATE -O1 -g0)
add_executable(fastmem-emission test.cpp)
target_compile_options(fastmem-emission PRIVATE -O1 -UNDEBUG)
target_link_libraries(fastmem-emission PRIVATE vixl)
'''
 (t/'CMakeLists.txt').write_text(cmake)
 subprocess.run(['cmake','-S',str(t),'-B',str(t/'build'),'-DCMAKE_BUILD_TYPE=Release'],check=True)
 subprocess.run(['cmake','--build',str(t/'build'),'--parallel','4'],check=True)
 subprocess.run([str(t/'build/fastmem-emission')],check=True,timeout=60)
