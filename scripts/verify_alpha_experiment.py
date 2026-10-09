#!/usr/bin/env python3
"""Compile actual generated selection/alpha bodies and check preserved source guards."""
from pathlib import Path
import subprocess
import tempfile


def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError(signature)


base = Path('pcsx2/GS/Renderers/HW')
source = (base / 'GSTextureReplacements.cpp').read_text()
selector = function(source, 'unsigned GSTextureReplacements::NCAAExperimentMode(')
usc = function(source, 'bool NCAAIsUSC(')
loader = function(source, 'void LoadNCAAExperiment(')
alpha = function(source, 'auto scale_alpha = ')
renderer = (base / 'GSRendererHW.cpp').read_text()
assert '!m_conf.alpha_second_pass.enable && !m_conf.blend_multi_pass.enable' in renderer
assert '!m_conf.ps.IsSWBlending()' in renderer
assert 'tex->m_from_hash_cache->is_replacement' in renderer
assert 'LoadNCAAExperiment();' in source
assert '0x00000007FFF00000ULL' in (base / 'GSTextureCache.cpp').read_text()
assert 'u32 TEX0_TCC : 1; // JD4029 compatibility' in source
assert 'NCAA_NEXT_FOLDER_CARD_MB = 64' in Path('pcsx2/SIO/Memcard/MemoryCardFolder.cpp').read_text()
assert 'u32 ExposedRam = TotalRam;' in Path('pcsx2/Memory.cpp').read_text()
assert 'Ps2MemSize::MainRam' not in Path('pcsx2/arm64/iR5900-arm64.cpp').read_text()

harness = r'''
#include <cassert>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
using u64 = uint64_t; using u32 = uint32_t; using u8 = uint8_t;
constexpr u32 PSMT4 = 20;
struct GSTextureCache {
 struct HashCacheKey {
  u64 TEX0Hash=0, CLUTHash=0;
  struct { u32 PSM=0,TW=0,TH=0,TCC=0; } TEX0;
  u64 TEXA=0; u32 region_width=0,region_height=0;
  bool operator==(const HashCacheKey& b) const {
   return TEX0Hash==b.TEX0Hash && CLUTHash==b.CLUTHash && TEX0.PSM==b.TEX0.PSM &&
    TEX0.TW==b.TEX0.TW && TEX0.TH==b.TEX0.TH && TEX0.TCC==b.TEX0.TCC &&
    TEXA==b.TEXA && region_width==b.region_width && region_height==b.region_height;
  }
 };
};
namespace GSTextureReplacements {
 unsigned NCAAExperimentMode(const GSTextureCache::HashCacheKey&);
 std::string s_current_serial="SLUS-21214";
 struct TextureName { u64 TEX0Hash; };
 std::optional<TextureName> ParseReplacementName(const std::string& name) {
  if (name=="123-456-00001dd4.png") return TextureName{123};
  if (name=="b1ab915d19fe1b9a-456-00001dd4.png") return TextureName{0xb1ab915d19fe1b9aULL};
  return {};
 }
 GSTextureCache::HashCacheKey HashCacheKeyFromTextureName(TextureName name) {
  GSTextureCache::HashCacheKey key; key.TEX0Hash=name.TEX0Hash;
  key.CLUTHash=456; key.TEX0.PSM=PSMT4; key.TEX0.TW=key.TEX0.TH=7;
  return key;
 }
}
namespace EmuFolders { std::string Textures="textures"; }
namespace Path { std::string Combine(const std::string& a,const std::string& b) { return a+"/"+b; } }
std::optional<std::string> fake_file;
namespace FileSystem { std::optional<std::string> ReadFileToString(const char*) { return fake_file; } }
struct ConsoleStub { template<typename... T> void WriteLnFmt(const char*, T...) {} } Console;
unsigned s_ncaa_wsu_mode=0, s_ncaa_usc_mode=0;
std::optional<GSTextureCache::HashCacheKey> s_ncaa_wsu_key;
// USC
// LOADER
// SELECTOR
int main() {
 GSTextureCache::HashCacheKey wsu; wsu.TEX0Hash=123; wsu.CLUTHash=456;
 wsu.TEX0.PSM=PSMT4; wsu.TEX0.TW=wsu.TEX0.TH=7;
 auto usc=wsu; usc.TEX0Hash=0xb1ab915d19fe1b9aULL;
 assert(GSTextureReplacements::NCAAExperimentMode(wsu)==0);
 s_ncaa_wsu_key=wsu;
 for (unsigned w=0;w<=3;w++) for(unsigned u=0;u<=3;u++) {
  s_ncaa_wsu_mode=w; s_ncaa_usc_mode=u;
  assert(GSTextureReplacements::NCAAExperimentMode(wsu)==w);
  assert(GSTextureReplacements::NCAAExperimentMode(usc)==u);
  auto other=wsu; other.CLUTHash++;
  assert(GSTextureReplacements::NCAAExperimentMode(other)==0);
  other=wsu; other.TEX0.TCC++;
  assert(GSTextureReplacements::NCAAExperimentMode(other)==0);
 }
 GSTextureReplacements::s_current_serial="OTHER";
 assert(GSTextureReplacements::NCAAExperimentMode(wsu)==0);
 assert(GSTextureReplacements::NCAAExperimentMode(usc)==0);
 GSTextureReplacements::s_current_serial="SLUS-21214"; usc.TEX0.TH=6;
 assert(GSTextureReplacements::NCAAExperimentMode(usc)==0);
 fake_file="wsu=2\r\nusc=3\r\nwsu_file=123-456-00001dd4.png\r\n";
 LoadNCAAExperiment();
 assert(GSTextureReplacements::NCAAExperimentMode(wsu)==2);
 usc.TEX0.TH=7;
 assert(GSTextureReplacements::NCAAExperimentMode(usc)==3);
 fake_file="wsu=1\nwsu_file=b1ab915d19fe1b9a-456-00001dd4.png\n";
 LoadNCAAExperiment(); assert(!s_ncaa_wsu_key);
 assert(GSTextureReplacements::NCAAExperimentMode(wsu)==0);
 assert(GSTextureReplacements::NCAAExperimentMode(usc)==0);
 fake_file="wsu=9\nusc=invalid\nwsu_file=bad.png\n";
 LoadNCAAExperiment(); assert(!s_ncaa_wsu_key);
 assert(s_ncaa_wsu_mode==0 && s_ncaa_usc_mode==0);
 fake_file.reset(); LoadNCAAExperiment();
 assert(s_ncaa_wsu_mode==0 && s_ncaa_usc_mode==0 && !s_ncaa_wsu_key);
 // ALPHA
 std::vector<u8> pixels={1,2,3,0, 4,5,6,128, 7,8,9,255, 99,99,99,99};
 assert(scale_alpha(pixels,3,1,16));
 assert((pixels==std::vector<u8>{1,2,3,0,4,5,6,64,7,8,9,128,99,99,99,99}));
 auto untouched=pixels;
 assert(!scale_alpha(pixels,4,2,16)); assert(pixels==untouched);
 assert(!scale_alpha(pixels,4,1,12)); assert(pixels==untouched);
 std::vector<u8> mip={11,22,33,255}; assert(scale_alpha(mip,1,1,4));
 assert((mip==std::vector<u8>{11,22,33,128}));
}
'''.replace('// USC', usc).replace('// LOADER', loader).replace('// SELECTOR', selector).replace('// ALPHA', alpha + ';')
with tempfile.TemporaryDirectory() as tmp:
    cpp = Path(tmp) / 'experiment.cpp'
    exe = Path(tmp) / 'experiment'
    cpp.write_text(harness)
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
print('128107: independent selectors, control isolation, alpha/RGB/pitch/mips, and baseline guards passed')
