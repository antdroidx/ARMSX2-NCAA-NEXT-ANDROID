"""Execute actual emitted A64 instructions in the pinned VIXL simulator."""
from pathlib import Path
import subprocess
import tempfile
from patch_conservative_gs import function

repo=Path(__file__).resolve().parents[1]
root=Path.cwd()
source=Path('pcsx2/arm64/Vif_Dynarec.cpp').read_text()
old=function((repo/'tests/vif_compile_original.inc').read_text(),'void VifUnpackNEON_Dynarec::CompileRoutine()')
new=function(source,'void VifUnpackNEON_Dynarec::CompileRoutine()')
emit=function(source,'void VifUnpackNEON_Dynarec::EmitCopyRows(')
assert 'falling back to interpreter' in source
base=r'''
class VifUnpackNEON_Dynarec {
public:
    const Block& vB;int vCL=0,doMode;bool isFill,doMask;
    int UnpkNoOfIterations=0;
    a64::MacroAssembler* armAsm;
    a64::MemOperand dstIndirect{a64::x0},srcIndirect{a64::x1};
    a64::VRegister destReg{a64::q0},workReg{a64::q1};
    a64::WRegister workGprW{a64::w4};
    using CopyRow=std::pair<s64,s64>;
    VifUnpackNEON_Dynarec(const Block& b,a64::MacroAssembler* a):vB(b),doMode(b.mode),isFill(b.cl<(b.wl?b.wl:256)),doMask((b.upkType>>4)&1),armAsm(a){}
    void SetMasks(int) const {if(doMask||doMode)armAsm->Nop();}
    void ProcessMasks(){}
    void ModUnpack(int,bool){}
    void xUnpack(int){armAsm->Ldr(destReg,srcIndirect);}
    void xMovDest(){armAsm->Str(destReg,dstIndirect);}
    void writeBackRow() const {armAsm->Nop();}
    void EmitCopyRows(const std::vector<CopyRow>&) const;
    void CompileRoutine();
};
'''
code='namespace Original {\n'+base+old+'\n}\nnamespace Optimized {\n'+base+emit+'\n'+new+'\n}\n'
harness=(repo/'tests/vif_pairs_harness.cpp').read_text().replace('// NAMESPACES',code)
harness=harness.replace('// COMPUTE_LENGTH',function(source,'static u16 dVifComputeLength('))
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp);(temp/'test.cpp').write_text(harness)
    cmake=f'''cmake_minimum_required(VERSION 3.22)
project(VifPairChecks LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
add_subdirectory("{(root/'3rdparty/vixl').as_posix()}" vixl)
target_compile_definitions(vixl PUBLIC VIXL_INCLUDE_SIMULATOR_AARCH64 VIXL_DEBUG)
target_compile_options(vixl PRIVATE -O1 -g0)
add_executable(vif-pairs test.cpp)
target_compile_options(vif-pairs PRIVATE -O1 -UNDEBUG)
target_link_libraries(vif-pairs PRIVATE vixl)
'''
    (temp/'CMakeLists.txt').write_text(cmake)
    subprocess.run(['cmake','-S',str(temp),'-B',str(temp/'build'),'-DCMAKE_BUILD_TYPE=Release'],check=True)
    subprocess.run(['cmake','--build',str(temp/'build'),'--parallel','4'],check=True)
    subprocess.run([str(temp/'build/vif-pairs')],check=True,timeout=120)
print('Generated ARM64 VIF code executed successfully; physical-device timing still required')
