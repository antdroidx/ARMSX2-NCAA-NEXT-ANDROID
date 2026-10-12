#!/usr/bin/env python3
"""Normalize alpha only for small NCAA NEXT number/logo atlas keys."""
from pathlib import Path

p = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
s = p.read_text()
anchor = 'void GSTextureReplacements::Initialize()'
helper = r'''static bool ShouldNormalizeNCAAAlpha(const TextureName& name)
{
    return GSTextureReplacements::UsesLegacyTextureHashing() &&
        GSTextureReplacements::s_current_serial == "SLUS-21214" &&
        name.TEX0_PSM == PSMT4 && name.TEX0_TW == name.TEX0_TH &&
        (name.TEX0_TW == 7 || name.TEX0_TW == 8) && !name.HasRegion();
}

'''
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor, 1)
anchor = '\tSetReplacementTextureAlphaMinMax(rtex);'
block = r'''
    if (ShouldNormalizeNCAAAlpha(name) && rtex.format == GSTexture::Format::Color)
    {
        auto normalize_alpha = [](std::vector<u8>& bytes, u32 width, u32 height, u32 pitch)
        {
            if (pitch < static_cast<u64>(width) * 4 || bytes.size() < static_cast<u64>(pitch) * height)
                return false;
            for (u32 y = 0; y < height; y++)
                for (u32 x = 0; x < width; x++)
                {
                    u8& alpha = bytes[static_cast<size_t>(y) * pitch + x * 4 + 3];
                    alpha = static_cast<u8>((static_cast<unsigned>(alpha) * 128 + 127) / 255);
                }
            return true;
        };
        normalize_alpha(rtex.data, rtex.width, rtex.height, rtex.pitch);
        for (auto& mip : rtex.mips)
            normalize_alpha(mip.data, mip.width, mip.height, mip.pitch);
    }
    SetReplacementTextureAlphaMinMax(rtex);'''
assert s.count(anchor) == 1
p.write_text(s.replace(anchor, block, 1))
print('Applied scoped NCAA NEXT atlas alpha normalization')
