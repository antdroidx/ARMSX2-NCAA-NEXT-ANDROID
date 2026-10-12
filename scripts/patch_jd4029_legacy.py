from pathlib import Path

def replace_function(src, signature, replacement):
    start = src.find(signature)
    if start < 0:
        raise SystemExit(f"Missing function signature: {signature}")
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit(f"Missing opening brace: {signature}")
    depth = 0
    end = None
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Unbalanced function: {signature}")
    return src[:start] + replacement + src[end:]

tc_path = Path("pcsx2/GS/Renderers/HW/GSTextureCache.cpp")
tc = tc_path.read_text()

tc = replace_function(
    tc,
    "GSTextureCache::SourceRegion GSTextureCache::SourceRegion::Create(GIFRegTEX0 TEX0, GIFRegCLAMP CLAMP)",
    r'''GSTextureCache::SourceRegion GSTextureCache::SourceRegion::Create(GIFRegTEX0 TEX0, GIFRegCLAMP CLAMP)
{
    // JDHalfrack 1.7.4029 predates region-texture hashing. Disable the
    // newer region optimization so replacement keys describe the full texture.
    (void)TEX0;
    (void)CLAMP;
    return {};
}''')

tc = replace_function(
    tc,
    "static void HashTextureLevel(const GIFRegTEX0& TEX0, const GIFRegTEXA& TEXA, GSTextureCache::SourceRegion region, BlockHashState& hash_st, u8* temp)",
    r'''static void HashTextureLevel(const GIFRegTEX0& TEX0, const GIFRegTEXA& TEXA, GSTextureCache::SourceRegion region, BlockHashState& hash_st, u8* temp)
{
    // Exact JDHalfrack v1.7.4029 hashing behavior, adapted only for the
    // modern SourceRegion argument and GS_BLOCK_SIZE constant.
    (void)region;
    const GSLocalMemory::psm_t& psm = GSLocalMemory::m_psm[TEX0.PSM];
    const GSVector2i& bs = psm.bs;
    const int tw = 1 << TEX0.TW;
    const int th = 1 << TEX0.TH;

    const GSVector4i rect(0, 0, tw, th);
    const GSVector4i block_rect(rect.ralign<Align_Outside>(bs));
    GSLocalMemory& mem = g_gs_renderer->m_mem;
    const GSOffset off = mem.GetOffset(TEX0.TBP0, TEX0.TBW, TEX0.PSM);

    if (tw < bs.x || th < bs.y || psm.fmsk != 0xFFFFFFFFu)
    {
        const u32 pitch = Common::AlignUpPow2(static_cast<u32>(block_rect.z), 32);
        const u32 row_size = static_cast<u32>(tw);
        const GSLocalMemory::readTexture rtx = psm.rtxP;

        rtx(mem, off, block_rect, temp, pitch, TEXA);

        u8* ptr = temp;
        if (pitch == row_size)
        {
            BlockHashAccumulate(hash_st, ptr, pitch * static_cast<u32>(th));
        }
        else
        {
            for (int y = 0; y < th; y++, ptr += pitch)
                BlockHashAccumulate(hash_st, ptr, row_size);
        }
    }
    else
    {
        // 1.7.4029 intentionally resets here before hashing raw GS blocks.
        BlockHashReset(hash_st);

        GSOffset::BNHelper bn = off.bnMulti(block_rect.left, block_rect.top);
        const int right = block_rect.right >> off.blockShiftX();
        const int bottom = block_rect.bottom >> off.blockShiftY();
        const int xAdd = (1 << off.blockShiftX()) * (psm.bpp / 8);

        for (; bn.blkY() < bottom; bn.nextBlockY())
        {
            for (int x = 0; bn.blkX() < right; bn.nextBlockX(), x += xAdd)
            {
                BlockHashAccumulate(hash_st, mem.BlockPtr(bn.value()));
            }
        }
    }
}''')

tc = replace_function(
    tc,
    "GSTextureCache::HashCacheKey GSTextureCache::HashCacheKey::Create(const GIFRegTEX0& TEX0, const GIFRegTEXA& TEXA, const u32* clut, const GSVector2i* lod, SourceRegion region)",
    r'''GSTextureCache::HashCacheKey GSTextureCache::HashCacheKey::Create(const GIFRegTEX0& TEX0, const GIFRegTEXA& TEXA, const u32* clut, const GSVector2i* lod, SourceRegion region)
{
    const GSLocalMemory::psm_t& psm = GSLocalMemory::m_psm[TEX0.PSM];
    (void)region;

    HashCacheKey ret;
    // JD4029 includes TEX0.TCC in the serialized texture key.
    ret.TEX0.U64 = TEX0.U64 & 0x00000007FFF00000ULL;
    ret.TEXA.U64 = (psm.pal == 0 && psm.fmt > 0) ? (TEXA.U64 & 0x000000FF000080FFULL) : 0;
    ret.CLUTHash = clut ? GSTextureCache::PaletteKeyHash{}({clut, psm.pal}) : 0;
    ret.region_width = 0;
    ret.region_height = 0;

    BlockHashState hash_st;
    BlockHashReset(hash_st);

    HashTextureLevel(TEX0, TEXA, {}, hash_st, s_unswizzle_buffer);

    if (lod)
    {
        const int basemip = lod->x;
        const int nmips = lod->y - lod->x + 1;
        for (int i = 1; i < nmips; i++)
        {
            const GIFRegTEX0 MIP_TEX0{g_gs_renderer->GetTex0Layer(basemip + i)};
            HashTextureLevel(MIP_TEX0, TEXA, {}, hash_st, s_unswizzle_buffer);
        }
    }

    ret.TEX0Hash = FinishBlockHash(hash_st);
    return ret;
}''')

tc_path.write_text(tc)

tr_path = Path("pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp")
tr = tr_path.read_text()

old = "u32 unused0 : 1; // was TCC"
if old not in tr:
    raise SystemExit("TextureName legacy bit field not found")
tr = tr.replace(old, "u32 TEX0_TCC : 1; // JD4029 compatibility", 1)

# After renaming unused0 -> TEX0_TCC above, preserve the bit when parsing
# legacy JD4029 replacement filenames instead of clearing it.
old = "unused0 = 0;"
if old in tr:
    tr = tr.replace(old, "(void)TEX0_TCC;", 1)
elif "(void)TEX0_TCC;" not in tr:
    raise SystemExit("RemoveUnusedBits assignment not found")

old = "name.TEX0_TH = hash.TEX0.TH;\n"
if old not in tr:
    raise SystemExit("CreateTextureName TH assignment not found")
tr = tr.replace(old, old + "\tname.TEX0_TCC = hash.TEX0.TCC;\n", 1)

old = "key.TEX0.TH = tn.TEX0_TH;\n"
if old not in tr:
    raise SystemExit("HashCacheKeyFromTextureName TH assignment not found")
tr = tr.replace(old, old + "\tkey.TEX0.TCC = tn.TEX0_TCC;\n", 1)

tr_path.write_text(tr)

# Guardrails: fail before compiling if any compatibility marker is missing.
checks = {
    tc_path: [
        "0x00000007FFF00000ULL",
        "const GSLocalMemory::readTexture rtx = psm.rtxP;",
        "return {};",
    ],
    tr_path: [
        "u32 TEX0_TCC : 1; // JD4029 compatibility",
        "name.TEX0_TCC = hash.TEX0.TCC;",
        "key.TEX0.TCC = tn.TEX0_TCC;",
    ],
}
for path, needles in checks.items():
    data = path.read_text()
    for needle in needles:
        if needle not in data:
            raise SystemExit(f"Missing JD4029 compatibility marker in {path}: {needle}")

print("Applied JDHalfrack v1.7.4029 texture-hash compatibility")
