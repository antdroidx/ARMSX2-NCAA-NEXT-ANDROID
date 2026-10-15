// SPDX-License-Identifier: GPL-3.0+
#include <cassert>
#include <cstdint>
#include <vector>
#include <list>
#include <unordered_map>
#include <random>
#include <iostream>
using u8=uint8_t; using u64=uint64_t; using u32=uint32_t; using TextureName=int;
struct Logger { template<class...T> void WarningFmt(T...){} } Console;
namespace fmt { template<class...T> int format(T...){return 0;} }
#define TRANSLATE_FS(a,b) b
#define ICON_FA_CIRCLE_EXCLAMATION ""
namespace Host { constexpr int OSD_WARNING_DURATION=1; template<class...T> void AddIconOSDMessage(T...){} }
namespace GSTextureReplacements {
struct ReplacementTexture { std::vector<u8> data; struct MipData{std::vector<u8> data;};std::vector<MipData> mips; };
std::unordered_map<int,ReplacementTexture> s_replacement_texture_cache;
std::list<int> s_replacement_texture_lru;
std::unordered_map<int,std::list<int>::iterator> s_replacement_texture_lru_map;
size_t s_replacement_texture_cache_bytes=0;
bool s_replacement_cache_budget_hit=false;
// STATS
size_t GetReplacementCacheBudget(){return 64;}
void TouchReplacementCacheLocked(const TextureName& name);
size_t ReplacementTextureBytes(const ReplacementTexture& tex);
const ReplacementTexture* InsertReplacementCacheLocked(const TextureName&,ReplacementTexture&);
}
// FUNCTIONS
void check() {
    using namespace GSTextureReplacements;
    size_t sum=0; std::unordered_map<int,int> seen;
    for(const auto& p:s_replacement_texture_cache) sum+=ReplacementTextureBytes(p.second);
    for(int key:s_replacement_texture_lru) { assert(++seen[key]==1);assert(s_replacement_texture_cache.count(key));assert(*s_replacement_texture_lru_map.at(key)==key); }
    assert(sum==s_replacement_texture_cache_bytes && sum<=64);
    assert(seen.size()==s_replacement_texture_cache.size() && seen.size()==s_replacement_texture_lru_map.size());
}
int main() {
    using namespace GSTextureReplacements;
    ReplacementTexture a{{1,2,3},{}};a.data.resize(32,1);
    ReplacementTexture b; b.data.resize(32,2);
    auto* first=InsertReplacementCacheLocked(1,a);InsertReplacementCacheLocked(2,b);check();
    ReplacementTexture duplicate;duplicate.data.resize(48,3);
    assert(InsertReplacementCacheLocked(1,duplicate)==first);
    assert(duplicate.data.size()==48 && first->data[0]==1 && s_replacement_texture_cache.count(2));check();
    ReplacementTexture c;c.data.resize(32,4);InsertReplacementCacheLocked(3,c);
    assert(s_replacement_texture_cache.count(1) && !s_replacement_texture_cache.count(2));check();
    ReplacementTexture oversized;oversized.data.resize(128,9);
    assert(!InsertReplacementCacheLocked(1,oversized) && oversized.data.size()==128);check();
    std::mt19937 rng(735);
    for(int i=0;i<10000;++i) {
        ReplacementTexture t;t.data.resize(rng()%81,static_cast<u8>(i));
        t.mips.push_back({std::vector<u8>(rng()%9)});
        const int key=rng()%9; auto before=s_replacement_texture_cache.find(key);
        const bool existed=before!=s_replacement_texture_cache.end();
        const auto data=existed?before->second.data:std::vector<u8>{};
        auto* result=InsertReplacementCacheLocked(key,t);
        if(result && existed) assert(result->data==data);
        check();
    }
    std::cout<<"Cache insertion: duplicate race, eviction order, oversize and 10,000 invariant checks passed\n";
}
