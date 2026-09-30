#include <cassert>
#include <cstdint>
#include <iostream>
namespace a64 {
struct Register { int index; Register W() const { return *this; } };
constexpr Register w9{9}, pin{19};
}
uint32_t values[32]{};
struct Emitter {
    unsigned count = 0;
    void Mov(a64::Register d, uint32_t value) { values[d.index] = value; ++count; }
    void Add(a64::Register d, a64::Register s, int32_t imm) {
        values[d.index] = values[s.index] + static_cast<uint32_t>(imm); ++count;
    }
    void Ubfiz(a64::Register d, a64::Register s, int lsb, int width) {
        values[d.index] = (values[s.index] & ((1u << width) - 1)) << lsb; ++count;
    }
} emitter, *armAsm = &emitter;
int _Rs_ = 1, _Imm_ = 0;
bool constant = false, pinned = false;
uint32_t guest = 0;
struct { uint32_t UL[4]; } g_cpuConstRegs[32]{};
bool GPR_IS_CONST1(int) { return constant; }
void _eeMoveGPRtoR(a64::Register d, int) { armAsm->Mov(d, guest); }
a64::Register _eeGetGPRSourceReg(a64::Register scratch, int rs) {
    if (pinned) return a64::pin;
    _eeMoveGPRtoR(scratch, rs); return scratch;
}
// PRODUCTION_EE
void wrap(a64::Register gprReg) {
// PRODUCTION_VU1
}
int main() {
    for (uint32_t base : {0u, 1u, 0x1ffffffu, 0x2000000u, 0x7ffffffu, 0x8000000u, 0x7fffffffu, 0x80000000u, 0xffffffffu})
        for (int imm : {-32768, -4096, -1, 0, 1, 4095, 32767})
            for (int mode = 0; mode < 3; ++mode) {
                constant = mode == 0; pinned = mode == 1;
                guest = base; values[19] = base; g_cpuConstRegs[1].UL[0] = base;
                _Imm_ = imm; emitter.count = 0;
                recComputeAddr();
                assert(values[9] == base + static_cast<uint32_t>(imm));
                assert(values[19] == base);
                if (pinned && imm != 0) assert(emitter.count == 1);
            }
    for (uint32_t v = 0; v < 65536; ++v) {
        values[9] = v; emitter.count = 0; wrap(a64::w9);
        assert(values[9] == (v % 1024) * 16 && emitter.count == 1);
    }
    values[9] = 0xffffffff; wrap(a64::w9); assert(values[9] == 16368);
    std::cout << "Production emission functions: address boundaries and all 16-bit VU1 addresses passed (instruction model, not device execution)\n";
}
