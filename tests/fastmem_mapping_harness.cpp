// Production mapping/fault functions with POSIX shared mappings and mocked core services.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
using u8=uint8_t;using u32=uint32_t;using uptr=uintptr_t;using uint=unsigned;
#define pxAssert(x) assert(x)
#define pxAssertMsg(x,...) assert(x)
#define __fi inline
#define FASTMEM_LOG(...) ((void)0)
#define CHECK_FASTMEM (EmuConfig.Cpu.Recompiler.EnableEE && EmuConfig.Cpu.Recompiler.EnableFastmem)
#define CHECK_EEREC (EmuConfig.Cpu.Recompiler.EnableEE)
constexpr u32 VTLB_PAGE_SIZE=4096,VTLB_PAGE_BITS=12,VTLB_PAGE_MASK=4095;
constexpr u32 __pageshift=TEST_PAGE_SHIFT,__pagesize=1u<<__pageshift,__pagemask=__pagesize-1;
constexpr size_t FASTMEM_AREA_SIZE=0x100000000ULL,VTLB_VMAP_ITEMS=FASTMEM_AREA_SIZE/VTLB_PAGE_SIZE;
constexpr u32 FASTMEM_PAGE_COUNT=VTLB_VMAP_ITEMS,NO_FASTMEM_MAPPING=0xffffffffu;
constexpr int Color_StrongGreen=0;
struct Config {struct {struct {bool EnableEE=true,EnableFastmem=true;}Recompiler;}Cpu;}EmuConfig;
struct Log {template<class...T>void Write(T...){ }template<class...T>void WriteLn(T...){ }template<class...T>void Warning(T...){ }template<class...T>void Error(T...){ }}Console,DevCon,eeRecPerfLog;
struct Error {std::string GetDescription()const{return "mock";}};
namespace Host {template<class...T>void ReportErrorAsync(T...){}}
struct PageProtectionMode {bool read=false,write=false;PageProtectionMode& Read(){read=true;return *this;}PageProtectionMode& Write(bool w=true){write=w;return *this;}};
PageProtectionMode PageAccess_ReadWrite(){return PageProtectionMode().Read().Write();}
PageProtectionMode PageAccess_ReadOnly(){return PageProtectionMode().Read();}
int native_prot(PageProtectionMode p){return (p.read?PROT_READ:0)|(p.write?PROT_WRITE:0);}
namespace HostSys {void MemProtect(void* ptr,size_t size,PageProtectionMode p){assert(mprotect(ptr,size,native_prot(p))==0);}}
namespace Ps2MemSize {constexpr u32 TotalRam=128u<<20;u32 ExposedRam=TotalRam;}
struct EEVM_MemoryAllocMess {u8 Main[Ps2MemSize::TotalRam];u8 Rom[65536];u8 ZeroRead[4096];};
struct IopVM_MemoryAllocMess {u8 Main[65536];u8 P[4096];};
EEVM_MemoryAllocMess* eeMem=nullptr;IopVM_MemoryAllocMess* iopMem=nullptr;
namespace HostMemoryMap {constexpr u32 EEmemOffset=0,IOPmemOffset=0x10000000,VUmemOffset=0x10010000,VUmemSize=32768;constexpr size_t VTLBVirtualMapSize=VTLB_VMAP_ITEMS;}
bool fail_reservation=false,fail_next_map=false,code_memory=true;
int backing_fd=-1;std::vector<u8> fake_vmap(VTLB_VMAP_ITEMS),vu(32768);
namespace SysMemory {
bool IsAllocated(){return true;}bool HasCodeMemory(){return code_memory;}
void* GetVTLBVirtualMap(){return fake_vmap.data();}int GetDataFileHandle(){return backing_fd;}
void* GetDataPtr(size_t){return eeMem;}void* GetVUMem(){return vu.data();}void* GetVUMemEnd(){return vu.data()+vu.size();}
}
struct VTLBVirtual {u8 unused;};
struct MapData {VTLBVirtual* vmap=nullptr;uptr fastmem_base=0;}vtlbdata;
class SharedMemoryMappingArea {
 void* ptr;
 explicit SharedMemoryMappingArea(void* p):ptr(p){}
public:
 static std::unique_ptr<SharedMemoryMappingArea>Create(size_t n){
  if(fail_reservation)return {};
  auto p=mmap(nullptr,n,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE,-1,0);
  assert(p!=MAP_FAILED);return std::unique_ptr<SharedMemoryMappingArea>(new SharedMemoryMappingArea(p));
 }
 ~SharedMemoryMappingArea(){assert(munmap(ptr,FASTMEM_AREA_SIZE)==0);}
 void* BasePointer(){return ptr;}void* OffsetPointer(u32 offset){return static_cast<u8*>(ptr)+offset;}
 void* PagePointer(u32 page){return static_cast<u8*>(ptr)+size_t(page)*__pagesize;}
 bool Map(int fd,u32 offset,void* dst,size_t n,PageProtectionMode mode){
  if(fail_next_map){fail_next_map=false;return false;}
  return mmap(dst,n,native_prot(mode),MAP_SHARED|MAP_FIXED,fd,offset)!=MAP_FAILED;
 }
 bool Unmap(void* dst,size_t n){return mmap(dst,n,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=MAP_FAILED;}
};
// BACKPATCH_STRUCT
static std::unique_ptr<SharedMemoryMappingArea> s_fastmem_area;
static std::vector<u32> s_fastmem_virtual_mapping;
static std::unordered_multimap<u32,u32> s_fastmem_physical_mapping;
static std::unordered_map<uptr,LoadstoreBackpatchInfo> s_fastmem_backpatch_info;
static std::vector<u32> s_fastmem_faulting_pcs;
static bool s_fastmem_area_unavailable=false;
enum vtlb_ProtectionMode {ProtMode_NotRequired,ProtMode_Write,ProtMode_Manual};
struct PageInfo {u32 ReverseRamMap=0;vtlb_ProtectionMode Mode=ProtMode_NotRequired;};
static PageInfo m_PageProtectInfo[Ps2MemSize::TotalRam>>__pageshift];
void* PSM(u32 address){const u32 p=address&0x1fffffffu;return p<Ps2MemSize::ExposedRam?eeMem->Main+p:nullptr;}
struct CpuService {std::vector<std::pair<u32,u32>> cleared;void Clear(u32 pc,u32 n){cleared.emplace_back(pc,n);}}cpu;
CpuService* Cpu=&cpu;
struct BackpatchRecord {unsigned calls=0;uptr code=0;u32 guest=0;u8 bits=0,addr_reg=0,data_reg=0;bool load=false,fpr=false;}backpatch;
void vtlb_DynBackpatchLoadStore(uptr code,u32,u32,u32 guest,u32,u32,u8 addr,u8 data,u8 bits,bool,bool load,bool fpr){backpatch={backpatch.calls+1,code,guest,bits,addr,data,load,fpr};}
namespace PageFaultHandler {enum class HandlerResult{ContinueExecution,ExecuteNextHandler};bool Install(Error*){return true;}HandlerResult HandlePageFault(void*,void*,bool);}
constexpr bool vtlb_MismatchedHostPageSize(){return __pagesize!=VTLB_PAGE_SIZE;}
bool vtlb_IsHostAligned(u32 address){return (address&__pagemask)==0;}
bool vtlb_GetGuestAddress(uptr,u32*);
vtlb_ProtectionMode mmap_GetRamPageInfo(u32);
bool vtlb_GetMainMemoryOffset(u32,u32*,u32*,PageProtectionMode*);
// PRODUCTION
bool vtlb_GetMainMemoryOffset(u32 p,u32* off,u32* size,PageProtectionMode* prot){
 auto ptr=PSM(p);return ptr&&vtlb_GetMainMemoryOffsetFromPtr(reinterpret_cast<uptr>(ptr),off,size,prot);
}
void invariant(){
 size_t forward=0;
 for(size_t i=0;i<s_fastmem_virtual_mapping.size();++i){
  u32 off=s_fastmem_virtual_mapping[i];if(off==NO_FASTMEM_MAPPING)continue;++forward;
  auto range=s_fastmem_physical_mapping.equal_range(off);unsigned count=0;
  for(auto it=range.first;it!=range.second;++it)count+=it->second==i*VTLB_PAGE_SIZE;
  assert(count==1);
 }
 assert(forward==s_fastmem_physical_mapping.size());
}
void map_host_page(u32 va,u32 pa){
 for(u32 n=0;n<__pagesize;n+=4096){u32 off,size;PageProtectionMode p;
  assert(vtlb_GetMainMemoryOffset(pa+n,&off,&size,&p));vtlb_CreateFastmemMapping(va+n,off,p);
 }
}
bool write_faults(volatile u8* p){
 const pid_t child=fork();assert(child>=0);
 if(child==0){signal(SIGSEGV,SIG_DFL);*p=17;_exit(0);}
 int status=0;assert(waitpid(child,&status,0)==child);return WIFSIGNALED(status)&&WTERMSIG(status)==SIGSEGV;
}
int main(){
 char path[]="/tmp/armsx2-fastmem-XXXXXX";backing_fd=mkstemp(path);assert(backing_fd>=0);unlink(path);
 assert(ftruncate(backing_fd,0x10100000)==0);
 eeMem=static_cast<EEVM_MemoryAllocMess*>(mmap(nullptr,sizeof(*eeMem),PROT_READ|PROT_WRITE,MAP_SHARED,backing_fd,0));assert(eeMem!=MAP_FAILED);
 iopMem=static_cast<IopVM_MemoryAllocMess*>(mmap(nullptr,sizeof(*iopMem),PROT_READ|PROT_WRITE,MAP_SHARED,backing_fd,HostMemoryMap::IOPmemOffset));assert(iopMem!=MAP_FAILED);
 // Reservation failure and no executable memory must never emit against a null base.
 fail_reservation=true;assert(vtlb_Core_Alloc());assert(!EmuConfig.Cpu.Recompiler.EnableFastmem&&vtlb_FastmemAreaUnavailable());
 u32 guest=99;assert(!vtlb_GetGuestAddress(0x1000,&guest));
 fail_reservation=false;s_fastmem_area_unavailable=false;vtlbdata.vmap=nullptr;
 code_memory=false;assert(vtlb_Core_Alloc());assert(!vtlbdata.fastmem_base&&!EmuConfig.Cpu.Recompiler.EnableFastmem);
 // A deliberately disabled INI keeps its choice, but retains VA for a later enable.
 code_memory=true;vtlbdata.vmap=nullptr;assert(vtlb_Core_Alloc());
 assert(s_fastmem_area&&!EmuConfig.Cpu.Recompiler.EnableFastmem&&!vtlb_FastmemAreaUnavailable());
 EmuConfig.Cpu.Recompiler.EnableFastmem=true;
 size_t span_pages=0;
 for(u32 exposed:{32u<<20,128u<<20}){
  Ps2MemSize::ExposedRam=exposed;
  for(u32 p=0;p<exposed;p+=4096){u32 off,size;PageProtectionMode prot;
   assert(vtlb_GetMainMemoryOffset(p,&off,&size,&prot)&&off==p&&size>=4096&&prot.write);++span_pages;
  }
  assert(!PSM(exposed));
 }
 Ps2MemSize::ExposedRam=128u<<20;
 const std::array<u32,8> mirrors{0,0x20000000,0x30000000,0x80000000,0xa0000000,0xb0000000,0xc0000000,0xd0000000};
 const std::array<u32,7> offsets{0,0x1ffc000,0x2000000,0x3ffc000,0x4000000,0x6000000,0x7ffc000};
 for(u32 p:offsets){
  for(u32 mirror:mirrors)map_host_page(mirror+p,p);
  for(u32 mirror:mirrors){
   auto alias=reinterpret_cast<u8*>(vtlbdata.fastmem_base+mirror+p);alias[31]=static_cast<u8>(mirror>>24);
   assert(eeMem->Main[p+31]==static_cast<u8>(mirror>>24));
   uptr resolved=reinterpret_cast<uptr>(alias+31);assert(vtlb_ResolveFastmemMapping(&resolved));assert(resolved==reinterpret_cast<uptr>(eeMem->Main+p+31));
   u32 g=0;assert(vtlb_GetGuestAddress(reinterpret_cast<uptr>(alias+31),&g)&&g==mirror+p+31);
  }
 }
 invariant();
 // A virtual-page remap must remove its old reverse record, not another page's.
 const u32 va=0x44000000,old_pa=0x2100000,new_pa=0x4100000;
 map_host_page(va,old_pa);map_host_page(va,new_pa);invariant();
 assert(s_fastmem_physical_mapping.count(old_pa)==0);
 auto alias=reinterpret_cast<u8*>(vtlbdata.fastmem_base+va);alias[5]=83;assert(eeMem->Main[new_pa+5]==83);
 vtlb_UpdateFastmemProtection(old_pa,__pagesize,PageAccess_ReadOnly());alias[5]=84; // no stale protection of the new page
 vtlb_UpdateFastmemProtection(new_pa,__pagesize,PageAccess_ReadOnly());assert(write_faults(alias));
 vtlb_UpdateFastmemProtection(new_pa,__pagesize,PageAccess_ReadWrite());alias[5]=85;
 // Protect code above 32MB. Its aliases must fault until the CPU block is invalidated.
 const u32 code_pa=0x6000000;
 mmap_MarkCountedRamPage(code_pa);assert(mmap_GetRamPageInfo(code_pa)==ProtMode_Write);
 auto code_alias=reinterpret_cast<u8*>(vtlbdata.fastmem_base+0xa0000000+code_pa);
 assert(write_faults(code_alias));
 assert(PageFaultHandler::HandlePageFault(nullptr,code_alias,true)==PageFaultHandler::HandlerResult::ContinueExecution);
 assert(mmap_GetRamPageInfo(code_pa)==ProtMode_Manual);*code_alias=99;
 assert(!cpu.cleared.empty()&&cpu.cleared.back()==std::pair(code_pa,__pagesize));
 // Handler-backed MMIO routes through the registered backpatch metadata, all widths.
 const u32 mmio=0x10000000;
 for(u8 bits:{8,16,32,64,128})for(bool load:{false,true}){
  const uptr pc=0x123400+bits+(load?256:0);
  vtlb_AddLoadStoreInfo(pc,4,0x2001000,0x123,0x456,9,3,bits,true,load,bits==128);
  const unsigned calls=backpatch.calls;
  assert(PageFaultHandler::HandlePageFault(reinterpret_cast<void*>(pc),reinterpret_cast<void*>(vtlbdata.fastmem_base+mmio),!load)==PageFaultHandler::HandlerResult::ContinueExecution);
  assert(backpatch.calls==calls+1&&backpatch.guest==mmio&&backpatch.bits==bits&&backpatch.load==load&&backpatch.addr_reg==9&&backpatch.data_reg==3);
  assert(vtlb_IsFaultingPC(0x2001000));assert(!vtlb_BackpatchLoadStore(pc,vtlbdata.fastmem_base+mmio));
 }
 uptr unknown=vtlbdata.fastmem_base+mmio;assert(!vtlb_ResolveFastmemMapping(&unknown));
 assert(!vtlb_GetGuestAddress(vtlbdata.fastmem_base-1,&guest));
 assert(vtlb_GetGuestAddress(vtlbdata.fastmem_base+0xffffffffu,&guest)&&guest==0xffffffffu);
 assert(!vtlb_GetGuestAddress(vtlbdata.fastmem_base+FASTMEM_AREA_SIZE,&guest));
 vtlb_RemoveFastmemMappings();invariant();assert(s_fastmem_physical_mapping.empty());
 // Failed replacement must not leave the original reverse map behind either.
 map_host_page(va,old_pa);fail_next_map=true;map_host_page(va,new_pa);invariant();
 vtlb_RemoveFastmemMappings();s_fastmem_virtual_mapping.clear();s_fastmem_area.reset();vtlbdata.fastmem_base=0;vtlbdata.vmap=nullptr;
 assert(!vtlb_ResolveFastmemMapping(&unknown));
 EmuConfig.Cpu.Recompiler.EnableFastmem=true;setenv("iPSX2_FORCE_NO_FASTMEM","1",1);assert(vtlb_Core_Alloc());
 assert(!s_fastmem_area&&!EmuConfig.Cpu.Recompiler.EnableFastmem&&s_fastmem_area_unavailable);unsetenv("iPSX2_FORCE_NO_FASTMEM");
 assert(munmap(eeMem,sizeof(*eeMem))==0);assert(munmap(iopMem,sizeof(*iopMem))==0);close(backing_fd);
 std::cout<<"Fastmem POSIX: "<<span_pages<<" RAM pages; 8 mirrors, 32-128MB boundaries, SMC protection/fault handling, MMIO metadata, remap invariants, reservation/toggle/failure paths passed (host page "<<__pagesize<<")\n";
}
