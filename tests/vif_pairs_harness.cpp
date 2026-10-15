// SPDX-License-Identifier: GPL-3.0+
#include "vixl/aarch64/macro-assembler-aarch64.h"
#include "vixl/aarch64/simulator-aarch64.h"
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
namespace a64=vixl::aarch64;
using u8=uint8_t; using u32=uint32_t; using s64=int64_t; using uint=unsigned;
#define VIF_LOG(...) ((void)0)
#define pxAssume(x) assert(x)
const u8 nVifT[16]={4,2,1,0,8,4,2,0,12,6,3,0,16,8,4,2};
a64::MemOperand armOffsetMemOperand(const a64::MemOperand& p,s64 delta) {return a64::MemOperand(p.GetBaseRegister(),p.GetOffset()+delta);}
struct Block {int wl,cl,num,upkType=12,mode=0;};
struct Counter: a64::DecoderVisitor {
    size_t count=0;
    void Visit(a64::Metadata*,const a64::Instruction*) override {++count;}
};
struct Runtime {
    a64::Decoder decoder;
    a64::Simulator simulator{&decoder};
    Counter counter;
    Runtime(){decoder.AppendVisitor(&counter);}
    ~Runtime(){decoder.RemoveVisitor(&counter);}
};
// NAMESPACES

struct Code {
    a64::MacroAssembler masm;
    explicit Code(Block block,bool optimized) {
        if(optimized) {Optimized::VifUnpackNEON_Dynarec vif(block,&masm);vif.CompileRoutine();}
        else {Original::VifUnpackNEON_Dynarec vif(block,&masm);vif.CompileRoutine();}
        masm.FinalizeCode();
    }
    size_t run(u8* dst,const u8* src) {
        static Runtime runtime;
        auto& simulator=runtime.simulator; auto& counter=runtime.counter;
        simulator.ResetState();counter.count=0;
        simulator.RunFrom<void>(masm.GetBuffer().GetStartAddress<const a64::Instruction*>(),reinterpret_cast<uintptr_t>(dst),reinterpret_cast<uintptr_t>(src));
        return counter.count;
    }
    bool same_bytes(Code& other) {
        const auto count=masm.GetBuffer().GetCursorOffset();
        return count==other.masm.GetBuffer().GetCursorOffset() && !std::memcmp(masm.GetBuffer().GetStartAddress<const void*>(),other.masm.GetBuffer().GetStartAddress<const void*>(),count);
    }
};
int main() {
    size_t cases=0,overlaps=0;
    for(int cl:{1,2,3,7,16,63,64,65,128,255,256})
    for(int wl:{1,2,3,4,7,16,63,64,65,128,255,256})
    for(int num:{1,2,3,15,16,17,63,64,65,127,128,255,0}) {
        Block block{wl==256?0:wl,cl,num};
        Code old(block,false),now(block,true);
        const int rows=num?num:256;
        const bool eligible=cl>=wl && rows>=16 && wl>=2 && (!(wl&1)||cl==wl);
        if(!eligible) {assert(old.same_bytes(now));continue;}
        const size_t dst_extent=static_cast<size_t>((rows-1)/wl*cl+(rows-1)%wl+1)*16;
        const size_t source=dst_extent+128;
        std::vector<u8> a(source+rows*16+128),b;
        for(size_t i=0;i<a.size();++i) a[i]=static_cast<u8>(i*73+i/17);
        b=a;
        const auto before=old.run(a.data()+4,a.data()+source+4);
        const auto after=now.run(b.data()+4,b.data()+source+4);
        assert(a==b);
        // Pairing must amortize the guard even for short eligible copies.
        assert(after<before);
        ++cases;
        if(rows==16||rows==65||rows==256) for(int delta:{-32,-16,0,16,32}) {
            std::vector<u8> x(dst_extent+rows*16+512),y;
            for(size_t i=0;i<x.size();++i) x[i]=static_cast<u8>(i*11+i/3);
            y=x;
            old.run(x.data()+128+delta,x.data()+128);
            now.run(y.data()+128+delta,y.data()+128);
            assert(x==y);++overlaps;
        }
    }
    // Masks, processing modes, and other formats retain the original emitter.
    for(int type:{0,4,8,12,13,14,15,28}) for(int mode:{0,1,2,3}) {
        Block block{4,4,0,type,mode};Code old(block,false),now(block,true);
        if(type!=12||mode!=0) assert(old.same_bytes(now));
    }
    Block block{4,4,0};Code old(block,false),now(block,true);
    std::vector<u8> x(12288),y=x;
    const auto a=old.run(x.data(),x.data()+8192),b=now.run(y.data(),y.data()+8192);
    assert(x==y && b<a);
    std::cout<<"VIF ARM64 simulator: "<<cases<<" disjoint cases, "<<overlaps<<" overlaps, fallback code equality passed; 256-row executed instructions "<<a<<" -> "<<b<<"\n";
}
