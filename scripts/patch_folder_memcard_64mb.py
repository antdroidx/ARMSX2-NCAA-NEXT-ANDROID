#!/usr/bin/env python3
from pathlib import Path

path = Path("pcsx2/SIO/Memcard/MemoryCardFolder.cpp")
src = path.read_text()

old = """void FolderMemoryCard::Open(const bool enableFiltering, std::string filter)
{
	Open(EmuConfig.FullpathToMcd(m_slot), EmuConfig.Mcd[m_slot], 0, enableFiltering, std::move(filter), false);
}"""
new = """void FolderMemoryCard::Open(const bool enableFiltering, std::string filter)
{
	// NCAA NEXT Android: folder-backed cards stay as folders on host storage, but
	// advertise 64 MiB of PS2 card geometry to the guest. 64 MiB is the largest
	// size supported by this implementation's single 256-entry indirect FAT:
	// 64 MiB / 1024-byte clusters = 65536 clusters, requiring exactly 256 FAT
	// clusters. No .ps2 image is created.
	static constexpr u32 NCAA_NEXT_FOLDER_CARD_MB = 64;
	static constexpr u32 NCAA_NEXT_FOLDER_CARD_CLUSTERS =
		(NCAA_NEXT_FOLDER_CARD_MB * 1024u * 1024u) / FolderMemoryCard::ClusterSize;
	static_assert(NCAA_NEXT_FOLDER_CARD_CLUSTERS == 65536u);

	Open(EmuConfig.FullpathToMcd(m_slot), EmuConfig.Mcd[m_slot],
		NCAA_NEXT_FOLDER_CARD_CLUSTERS, enableFiltering, std::move(filter), false);
}"""

if old not in src:
    raise SystemExit("FolderMemoryCard::Open baseline block not found; refusing blind patch")
src = src.replace(old, new, 1)
path.write_text(src)

# Guardrails for the static FAT layout. A larger size would overflow the current
# one-indirect-cluster design, so fail the build if upstream layout changes.
hdr = Path("pcsx2/SIO/Memcard/MemoryCardFolder.h").read_text()
for marker in [
    "static const int IndirectFatClusterCount = 1;",
    "u32 data[IndirectFatClusterCount][ClusterSize / 4][ClusterSize / 4];",
    "static const int ClusterSize = PageSize * 2;",
]:
    if marker not in hdr:
        raise SystemExit(f"Folder-card layout changed; review 64 MiB patch: {marker}")

print("Applied NCAA NEXT 64 MiB folder-memory-card geometry")
