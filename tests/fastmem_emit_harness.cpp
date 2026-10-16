#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include "vixl/aarch64/macro-assembler-aarch64.h"
#include "vixl/aarch64/simulator-aarch64.h"
namespace a64=vixl::aarch64;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using uptr=uintptr_t;
a64::MacroAssembler* armAsm;
const auto RFASTMEMBASE=a64::x19;
constexpr int NUM_ARM_GPR_REGS=32,NUM_ARM_NEON_REGS=32,NEON_RESERVED_COP2_CLAMPMAX=25,NEON_RESERVED_COP2_CLAMPMIN=26;
struct Reg {bool inuse=false;};Reg arm64gprs[32],arm64neon[32];
bool clamp_valid=false;bool cop2ClampConstsValid(){return clamp_valid;}
u32 pc=0x2001000;
a64::WRegister armWRegister(int n){return a64::WRegister(n);}a64::XRegister armXRegister(int n){return a64::XRegister(n);}
const u8* armGetCurrentCodePointer(){return armAsm->GetBuffer()->GetStartAddress<const u8*>()+armAsm->GetBuffer()->GetCursorOffset();}
struct Record {uptr code;u32 size,pc,gpr,fpr;u8 addr,data,bits;bool sign,load,neon;}record;
void vtlb_AddLoadStoreInfo(uptr code,u32 size,u32 guest,u32 gpr,u32 fpr,u8 addr,u8 data,u8 bits,bool sign,bool load,bool neon){record={code,size,guest,gpr,fpr,addr,data,bits,sign,load,neon};}
// EMITTERS
int main(){
 a64::Decoder decoder;a64::Simulator simulator(&decoder);
 const std::array<u32,15> addresses{0,16,0x1fffff0,0x2000000,0x3fffff0,0x4000000,0x7fffff0,0x20000000,0x30000000,0x80000000,0x82000000,0xa7fffff0,0xb2000000,0xd7fffff0,0xfffffff0};
 size_t cases=0;
 for(bool clamps:{false,true})for(u32 addr:addresses)for(int bits:{8,16,32,64,128})for(bool sign:{false,true})for(bool load:{false,true}){
  if(sign&&(!load||bits>=64))continue;
  clamp_valid=clamps;u32 expected_gpr=0,expected_fpr=0;
  for(int i=0;i<32;++i){arm64gprs[i].inuse=(i%3==0);arm64neon[i].inuse=(i%5==0);if(arm64gprs[i].inuse)expected_gpr|=1u<<i;if(arm64neon[i].inuse)expected_fpr|=1u<<i;}
  if(clamps)expected_fpr|=(1u<<25)|(1u<<26);
  alignas(16) std::array<u8,16> memory{},data{},out{};
  for(int i=0;i<16;++i){data[i]=static_cast<u8>(0x81+i*7);memory[i]=load?data[i]:0;}
  a64::MacroAssembler masm;armAsm=&masm;
  masm.Mov(a64::x19,a64::x0);
  if(!load){if(bits==128)masm.Ldr(a64::q3,a64::MemOperand(a64::x2));else masm.Ldr(a64::x3,a64::MemOperand(a64::x2));}
  const uptr instruction=reinterpret_cast<uptr>(armGetCurrentCodePointer());
  if(bits==128){if(load)vtlbFastmemRead128(1,3);else vtlbFastmemWrite128(1,3);}
  else {if(load)vtlbFastmemRead(1,3,bits,sign);else vtlbFastmemWrite(1,3,bits);}
  assert(record.code==instruction&&record.size==4&&record.pc==pc&&record.gpr==expected_gpr&&record.fpr==expected_fpr);
  assert(record.addr==1&&record.data==3&&record.bits==bits&&record.load==load&&record.neon==(bits==128));
  if(load){if(bits==128)masm.Str(a64::q3,a64::MemOperand(a64::x2));else masm.Str(a64::x3,a64::MemOperand(a64::x2));}
  masm.Ret();masm.FinalizeCode();simulator.ResetState();
  const uptr base=reinterpret_cast<uptr>(memory.data())-addr;
  simulator.RunFrom<void>(masm.GetBuffer()->GetStartAddress<const a64::Instruction*>(),base,addr,reinterpret_cast<uptr>(load?out.data():data.data()));
  if(load){
   if(bits==128)assert(out==data);
   else {u64 expected=0,actual=0;std::memcpy(&expected,data.data(),bits/8);std::memcpy(&actual,out.data(),8);
    if(sign){if(bits==8)expected=static_cast<int8_t>(expected);if(bits==16)expected=static_cast<int16_t>(expected);if(bits==32)expected=static_cast<int32_t>(expected);}
    assert(actual==expected);
   }
  }else {assert(std::memcmp(memory.data(),data.data(),bits/8)==0);for(int i=bits/8;i<16;++i)assert(memory[i]==0);}
  ++cases;
 }
 // Floating-point loads use S registers and their own backpatch metadata.
 for(u32 addr:addresses){
  u32 input=0xc123abcd,output=0;a64::MacroAssembler masm;armAsm=&masm;
  masm.Mov(a64::x19,a64::x0);vtlbFastmemReadFPR32(1,3);masm.Str(a64::s3,a64::MemOperand(a64::x2));masm.Ret();masm.FinalizeCode();
  assert(record.bits==32&&record.neon&&record.load&&!record.sign);
  simulator.ResetState();simulator.RunFrom<void>(masm.GetBuffer()->GetStartAddress<const a64::Instruction*>(),reinterpret_cast<uptr>(&input)-addr,addr,reinterpret_cast<uptr>(&output));assert(output==input);++cases;
 }
 std::cout<<"Fastmem ARM64 simulator: "<<cases<<" scalar/vector/FPR signed-width, high-bit address and live-register metadata cases passed\n";
}
