"""Execute restored production fastmem mapping and fault bookkeeping on POSIX."""
from pathlib import Path
import os,subprocess,tempfile
from patch_conservative_gs import function
repo=Path(__file__).resolve().parents[1]
s=Path('pcsx2/vtlb.cpp').read_text()
assert '#define CHECK_FASTMEM (EmuConfig.Cpu.Recompiler.EnableEE && EmuConfig.Cpu.Recompiler.EnableFastmem)' in Path('pcsx2/Config.h').read_text()
assert 'EnableFastmem = true;' in Path('pcsx2/Pcsx2Config.cpp').read_text()
# Verify all earlier extended-RAM compiler spans survived this independent change.
r=Path('pcsx2/arm64/iR5900-arm64.cpp').read_text()
assert 'Ps2MemSize::MainRam' not in r
for text in ['manual_page[Ps2MemSize::TotalRam / 4096]', 'manual_counter[Ps2MemSize::TotalRam / 4096]', 'recRAMCopy.resize(Ps2MemSize::ExposedRam)', 'recLutEntries = (Ps2MemSize::ExposedRam']:
    assert text in r,text
assert 'm_PageProtectInfo[Ps2MemSize::TotalRam >> __pageshift]' in s
vm=Path('pcsx2/VMManager.cpp').read_text()
assert 'vtlb_FastmemAreaUnavailable() && EmuConfig.Cpu.Recompiler.EnableFastmem' in vm
assert 'if (CHECK_EXTRAMEM)' in Path('pcsx2/R5900.cpp').read_text()
functions=[
 'bool vtlb_FastmemAreaUnavailable(',
 'static u32 vtlb_HostPage(', 'static u32 vtlb_HostAlignOffset(', 'static bool vtlb_IsHostCoalesced(',
 'static bool vtlb_GetMainMemoryOffsetFromPtr(', 'static void vtlb_CreateFastmemMapping(',
 'static void vtlb_RemoveFastmemMapping(', 'static void vtlb_RemoveFastmemMappings()',
 'bool vtlb_GetGuestAddress(', 'bool vtlb_ResolveFastmemMapping(',
 'void vtlb_UpdateFastmemProtection(', 'void vtlb_AddLoadStoreInfo(',
 'bool vtlb_BackpatchLoadStore(', 'bool vtlb_IsFaultingPC(', 'bool vtlb_Core_Alloc(',
 'vtlb_ProtectionMode mmap_GetRamPageInfo(', 'void mmap_MarkCountedRamPage(',
 'static __fi void mmap_ClearCpuBlock(', 'PageFaultHandler::HandlerResult PageFaultHandler::HandlePageFault('
]
code=(repo/'tests/fastmem_mapping_harness.cpp').read_text()
code=code.replace('// BACKPATCH_STRUCT',function(s,'struct LoadstoreBackpatchInfo')+';')
code=code.replace('// PRODUCTION','\n'.join(function(s,f) for f in functions))
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'mapping.cpp';p.write_text(code)
 clang=Path(os.environ['ANDROID_HOME'])/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
 for shift in [12,14]:
  exe=Path(tmp)/('mapping-'+str(shift))
  flags=['-std=c++20','-O2','-D__ANDROID__','-DTEST_PAGE_SHIFT='+str(shift)]
  subprocess.run(['g++',*flags,'-fsanitize=undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True,timeout=60)
  if shift == 12:
   # Prove the test catches the old stale reverse-map bug, not just the new code.
   broken=code.replace('s_fastmem_physical_mapping.equal_range(old_offset)', 's_fastmem_physical_mapping.equal_range(mainmem_offset)')
   assert broken != code
   bad=Path(tmp)/'old-remap.cpp';bad.write_text(broken);bad_exe=Path(tmp)/'old-remap'
   subprocess.run(['g++',*flags,str(bad),'-o',str(bad_exe)],check=True)
   result=subprocess.run([str(bad_exe)],capture_output=True,text=True,timeout=60)
   assert result.returncode != 0 and 'forward==s_fastmem_physical_mapping.size()' in result.stderr
   print('Old reverse-remap implementation correctly rejected by invariant regression check')
  subprocess.run([str(clang),*flags,'-c',str(p),'-o',str(Path(tmp)/('mapping-'+str(shift)+'.o'))],check=True)
print('Production fastmem mapping/fault bookkeeping passed on POSIX and compiled for Android ARM64; ARM64 game backpatch execution still needs device testing')
