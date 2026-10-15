// SPDX-License-Identifier: GPL-3.0+
#include "GS/GSVector.h"
#include <cassert>
#include <vector>
#include <random>
#include <iostream>
namespace Common { inline u32 AlignDownPow2(u32 a,u32 b) { return a & ~(b-1); } }
namespace StringUtil { // STRIDE_COPY
}
// ALPHA_FUNCTION
constexpr int PSMCT24=1;
inline int VectorAlign(int n) { return (n+15)&~15; }
struct Rect { int x,y,w,h; int width() const{return w;} int height() const{return h;} };
struct Memory {
    int calls=0;
    void ReadTexture(int,Rect r,u8* dst,int pitch,int) {
        ++calls;
        for(int y=0;y<r.h;++y) for(int x=0;x<r.w;++x) {
            const u32 pixel=static_cast<u32>((r.x+x)*739+(r.y+y)*12917)*198269u;
            std::memcpy(dst+y*pitch+x*4,&pixel,4);
        }
    }
};
struct Renderer { Memory m_mem; };
void original(Renderer* g_gs_renderer, Rect read_r, Rect t_r, u8* scratch,u8* dst,int stride,int psm,int bpp,bool alpha,bool valid,std::pair<u8,u8>& alpha_minmax) {
    const bool mapped=true; const int off=0,TEXA=0;
    auto* s_unswizzle_buffer=scratch;
    struct {u8* bits;int pitch;} m{dst,stride};
    struct {int PSM;} m_TEX0{psm};
    bool m_valid_alpha_high=valid,m_valid_alpha_low=false;
    struct Dirty { struct {struct {bool a;}c;}rgba; };
    Dirty m_dirty[1]{{{{alpha}}}}; const size_t i=0;
    // ORIGINAL
}
void optimized(Renderer* g_gs_renderer, Rect read_r, Rect t_r, u8* scratch,u8* dst,int stride,int psm,int bpp,bool alpha,bool valid,std::pair<u8,u8>& alpha_minmax) {
    const bool mapped=true; const int off=0,TEXA=0;
    auto* s_unswizzle_buffer=scratch;
    struct {u8* bits;int pitch;} m{dst,stride};
    struct {int PSM;} m_TEX0{psm};
    bool m_valid_alpha_high=valid,m_valid_alpha_low=false;
    struct Dirty { struct {struct {bool a;}c;}rgba; };
    Dirty m_dirty[1]{{{{alpha}}}}; const size_t i=0;
    // OPTIMIZED
}
int main() {
    size_t cases=0;
    for(int w:{1,2,3,4,7,16,63,64,65,128,257}) for(int h:{1,2,8,17})
    for(int offset:{0,1,3,16}) for(int pad:{0,3,64}) for(int psm:{0,1,2})
    for(int bpp:{8,16,32}) for(bool alpha:{false,true}) for(bool valid:{false,true}) {
        const int pitch=(w+offset+3)*4+pad;
        const int bytes=pitch*(h+3)+64;
        std::vector<u8> a(bytes,0xda),b=a,scratch(VectorAlign(w*4)*h+64,0xee);
        const Rect read{5,11,w,h},target{offset,1,w,h};
        Renderer ra,rb; std::pair<u8,u8> aa{255,0},ab=aa;
        original(&ra,read,target,scratch.data(),a.data()+1,pitch,psm,bpp,alpha,valid,aa);
        optimized(&rb,read,target,scratch.data(),b.data()+1,pitch,psm,bpp,alpha,valid,ab);
        assert(a==b && aa==ab);
        const bool tracked=(psm!=PSMCT24||valid)&&alpha&&bpp>=16;
        assert(ra.m_mem.calls==(tracked?2:1) && rb.m_mem.calls==1);
        ++cases;
    }
    std::cout<<"Mapped GS update: "<<cases<<" output/alpha/stride cases passed; conversions 2 -> 1 when tracked\n";
}
