"""Compile generated atlas-selection and alpha-normalization bodies."""
from pathlib import Path
import subprocess,tempfile

def function(text, signature):
    start=text.index(signature); brace=text.index('{',start); depth=0
    for end in range(brace,len(text)):
        depth+=(text[end]=='{')-(text[end]=='}')
        if depth==0:return text[start:end+1]
    raise AssertionError(signature)
source=Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp').read_text()
selector=function(source,'static bool ShouldNormalizeNCAAAlpha(')
alpha=function(source,'auto normalize_alpha = ')
assert 'ShouldNormalizeNCAAAlpha(name) && rtex.format == GSTexture::Format::Color' in source
assert 'normalize_alpha(mip.data, mip.width, mip.height, mip.pitch)' in source
harness=r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
constexpr u32 PSMT4=20;
struct TextureName { u32 TEX0_PSM=20,TEX0_TW=7,TEX0_TH=7; bool regional=false; bool HasRegion() const { return regional; } };
namespace GSTextureReplacements { std::string s_current_serial="SLUS-21214"; }
// SELECTOR
int main() {
 TextureName atlas;
 assert(ShouldNormalizeNCAAAlpha(atlas));
 atlas.TEX0_TW=atlas.TEX0_TH=8; assert(ShouldNormalizeNCAAAlpha(atlas));
 for (u32 psm: {0u,1u,19u,27u}) { auto body=atlas; body.TEX0_PSM=psm; assert(!ShouldNormalizeNCAAAlpha(body)); }
 for (u32 size: {5u,6u,9u,10u}) { auto other=atlas; other.TEX0_TW=other.TEX0_TH=size; assert(!ShouldNormalizeNCAAAlpha(other)); }
 auto other=atlas; other.TEX0_TH=7; assert(!ShouldNormalizeNCAAAlpha(other));
 other=atlas; other.regional=true; assert(!ShouldNormalizeNCAAAlpha(other));
 GSTextureReplacements::s_current_serial="OTHER"; assert(!ShouldNormalizeNCAAAlpha(atlas));
 // ALPHA
 std::vector<u8> pixels={1,2,3,0,4,5,6,128,7,8,9,255,99,99,99,99};
 assert(normalize_alpha(pixels,3,1,16));
 assert((pixels==std::vector<u8>{1,2,3,0,4,5,6,64,7,8,9,128,99,99,99,99}));
 auto saved=pixels; assert(!normalize_alpha(pixels,4,2,16)); assert(pixels==saved);
 assert(!normalize_alpha(pixels,4,1,12)); assert(pixels==saved);
 std::vector<u8> mip={11,22,33,255}; assert(normalize_alpha(mip,1,1,4));
 assert((mip==std::vector<u8>{11,22,33,128}));
 // Selection prevents an opaque body buffer from being normalized.
 GSTextureReplacements::s_current_serial="SLUS-21214";
 TextureName body; body.TEX0_PSM=19;
 std::vector<u8> opaque={11,22,33,255};
 if(ShouldNormalizeNCAAAlpha(body)) normalize_alpha(opaque,1,1,4);
 assert((opaque==std::vector<u8>{11,22,33,255}));
}
'''.replace('// SELECTOR',selector).replace('// ALPHA',alpha+';')
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'atlas.cpp';exe=Path(tmp)/'atlas';cpp.write_text(harness)
    subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
print('Atlas scope, body opacity, RGB preservation, padding, bounds and mip checks passed')
