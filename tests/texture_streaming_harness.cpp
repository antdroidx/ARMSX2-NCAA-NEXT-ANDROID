// SPDX-License-Identifier: GPL-3.0+
#include <array>
#include <cassert>
#include <cstdint>
#include <deque>
#include <iostream>
#include <mutex>
#include <random>
#include <unordered_map>
#include <vector>
using u64 = uint64_t;
using u32 = uint32_t;
inline size_t key_moves = 0;
struct TextureName {
    std::array<u64, 4> words{};
    TextureName(int n = 0) { words[0] = n; }
    TextureName(const TextureName&) = default;
    TextureName& operator=(const TextureName&) = default;
    TextureName(TextureName&& other) noexcept : words(other.words) { ++key_moves; }
    TextureName& operator=(TextureName&& other) noexcept { words = other.words; ++key_moves; return *this; }
    bool operator==(const TextureName&) const = default;
};
namespace std { template<> struct hash<TextureName> {
    size_t operator()(const TextureName& n) const { return n.words[0]; }
}; }
struct Replacement { size_t bytes; bool success; std::pair<int,int> alpha_minmax{0,128}; int id=-1; };
struct GSTexture {};
struct Event {
    int operation, id; bool mipmap; std::pair<int,int> alpha{};
    bool operator==(const Event&) const = default;
};
struct MockState {
    std::vector<Event> events;
    void InjectHashCacheTexture(int id, GSTexture*, std::pair<int,int> alpha) { events.push_back({1,id,false,alpha}); }
};
// ORIGINAL_NAMESPACE
// OPTIMIZED_NAMESPACE

template<class A, class B> bool same_queue(const A& a, const B& b) {
    if (a.size() != b.size()) return false;
    for (size_t i=0; i<a.size(); ++i) if (a[i] != b[i]) return false;
    return true;
}
int main() {
    namespace A = Original::GSTextureReplacements;
    namespace B = Optimized::GSTextureReplacements;
    std::mt19937 random(924);
    constexpr size_t MiB = 1024*1024;
    const size_t sizes[] = {0,64,MiB/2,8*MiB,16*MiB,20*MiB,32*MiB};
    for (int scenario=0; scenario<500; ++scenario) {
        A::s_async_loaded_textures.clear(); B::s_async_loaded_textures.clear();
        A::s_pending_async_load_textures.clear(); B::s_pending_async_load_textures.clear();
        A::s_replacement_texture_cache.clear(); B::s_replacement_texture_cache.clear();
        Original::state.events.clear(); Optimized::state.events.clear();
        for (int i=0, count=random()%150; i<count; ++i) {
            const TextureName name(i);
            const bool mipmap = random()%2;
            A::s_async_loaded_textures.emplace_back(name,mipmap);
            B::s_async_loaded_textures.emplace_back(name,mipmap);
            if (random()%4) {
                const Replacement texture{sizes[random()%7], random()%5 != 0, {0,128}, i};
                A::s_replacement_texture_cache.emplace(name,texture);
                B::s_replacement_texture_cache.emplace(name,texture);
            }
            const int pending = random()%3;
            if (pending) {
                A::s_pending_async_load_textures.emplace(name,pending==2);
                B::s_pending_async_load_textures.emplace(name,pending==2);
            }
        }
        int frames=0;
        do {
            assert(++frames < 200);
            A::ProcessAsyncLoadedTextures(); B::ProcessAsyncLoadedTextures();
            assert(Original::state.events == Optimized::state.events);
            assert(A::s_pending_async_load_textures == B::s_pending_async_load_textures);
            assert(same_queue(A::s_async_loaded_textures,B::s_async_loaded_textures));
        } while (!A::s_async_loaded_textures.empty());
    }
    // A backlog of 4,096 one-budget textures consumes one entry per frame.
    A::s_async_loaded_textures.clear(); B::s_async_loaded_textures.clear();
    for (int i=0; i<4096; ++i) {
        const TextureName name(10000+i);
        A::s_async_loaded_textures.emplace_back(name,false);
        B::s_async_loaded_textures.emplace_back(name,false);
        A::s_replacement_texture_cache.emplace(name,Replacement{16*MiB,true,{0,128},10000+i});
        B::s_replacement_texture_cache.emplace(name,Replacement{16*MiB,true,{0,128},10000+i});
    }
    key_moves=0; A::ProcessAsyncLoadedTextures(); const size_t old_moves=key_moves;
    key_moves=0; B::ProcessAsyncLoadedTextures(); const size_t new_moves=key_moves;
    assert(old_moves == 4095 && new_moves == 0);
    assert(same_queue(A::s_async_loaded_textures,B::s_async_loaded_textures));
    B::s_async_loaded_textures.clear();
    B::s_texture_runtime_stats = {};
    Optimized::GSConfig.OsdShowTextureReplacements=false;
    for (int i=0; i<600; ++i) B::ProcessAsyncLoadedTextures();
    assert(B::s_texture_runtime_stats.frames == 0 && Optimized::Console.reports == 0);
    Optimized::GSConfig.OsdShowTextureReplacements=true;
    for (int i=0; i<600; ++i) B::ProcessAsyncLoadedTextures();
    assert(B::s_texture_runtime_stats.frames == 0 && Optimized::Console.reports == 1);
    std::cout << "Streaming differential: 500 scenarios passed; backlog moves " << old_moves << " -> " << new_moves << "; opt-in diagnostics passed\n";
}
