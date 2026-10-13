#include "GS/GSVector.h"
#include <cassert>
#include <vector>
#include <random>
#include <iostream>
#include <chrono>
#include <sys/mman.h>
#include <unistd.h>
namespace Common { inline u32 AlignDownPow2(u32 n, u32 a) { return n & ~(a - 1); } }
// ORIGINAL
// OPTIMIZED
int main()
{
    std::mt19937 rng(7319);
    for (u32 w : {0u,1u,2u,3u,4u,7u,63u,64u,65u,127u,128u,257u})
        for (u32 h : {0u,1u,7u,8u,9u,31u})
            for (u32 pad : {0u,1u,16u})
                for (unsigned mode = 0; mode < 6; ++mode)
                {
                    const u32 pitch = w * 4 + pad;
                    std::vector<u8> data(static_cast<size_t>(pitch) * h + 16, 0xcc);
                    for (u32 y = 0; y < h; ++y)
                        for (u32 x = 0; x < w; ++x)
                        {
                            for (unsigned c = 0; c < 3; ++c) data[y*pitch+x*4+c] = rng();
                            data[y*pitch+x*4+3] = mode == 0 ? 0 : mode == 1 ? 255 :
                                mode == 2 ? 128 : mode == 3 ? rng() : mode == 4 ? (x & 1 ? 255 : 0) : 1 + rng() % 254;
                        }
                    const auto before = data;
                    assert(GSGetRGBA8AlphaMinMax(data.data(), w, h, pitch) == OriginalAlpha(data.data(), w, h, pitch));
                    assert(data == before);
                }
    // Put a tightly packed odd-width image immediately before an inaccessible page.
    const size_t page = sysconf(_SC_PAGESIZE);
    auto* memory = static_cast<u8*>(mmap(nullptr, page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    assert(memory != MAP_FAILED);
    assert(mprotect(memory + page, page, PROT_NONE) == 0);
    for (u32 w : {1u,2u,3u,63u,64u,65u,127u})
    {
        u8* p = memory + page - w * 4;
        for (u32 i = 0; i < w * 4; ++i) p[i] = rng();
        assert(GSGetRGBA8AlphaMinMax(p,w,1,w*4) == OriginalAlpha(p,w,1,w*4));
    }
    munmap(memory, page * 2);
    std::cout << "Alpha equivalence: 1,296 cases and guarded tails passed\n";
}
