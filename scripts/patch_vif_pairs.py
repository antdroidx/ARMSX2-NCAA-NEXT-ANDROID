"""Backport bounded V4-32 pairing, retaining the scalar path for overlap."""
from pathlib import Path
from patch_conservative_gs import function
from patch_core_efficiency import replace_once

if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    p = Path('pcsx2/arm64/Vif_Dynarec.cpp')
    source = p.read_text()
    signature = 'void VifUnpackNEON_Dynarec::CompileRoutine()'
    old = function(source, signature)
    assert old == function((repo / 'tests/vif_compile_original.inc').read_text(), signature)
    new = replace_once(old, '\twhile (vNum)', '''	// Small packets retain the original path; pairing must amortize its guard.
	const bool straight_copy = upkNum == 0xc && !doMask && !doMode && !isFill && vNum >= 16 && cycleSize >= 2 && ((cycleSize & 1) == 0 || skipSize == 0);
	std::vector<CopyRow> copy_rows;
	if (straight_copy)
		copy_rows.reserve(vNum);

	while (vNum)''')
    anchor = '\t\t\txUnpack(upkNum);\n\t\t\txMovDest();'
    assert new.count(anchor) == 2
    new = new.replace(anchor, '''			if (straight_copy)
				copy_rows.emplace_back(dstIndirect.GetOffset(), srcIndirect.GetOffset());
			else
			{
				xUnpack(upkNum);
				xMovDest();
			}''')
    new = replace_once(new, '\tif (doMode >= 2)', '\tif (straight_copy)\n\t\tEmitCopyRows(copy_rows);\n\n\tif (doMode >= 2)')
    helper = (repo / 'patches/vif-copy-rows.inc').read_text()
    p.write_text(replace_once(source, old, helper + '\n' + new))
    p = Path('pcsx2/arm64/Vif_UnpackNEON.h')
    s = p.read_text()
    s = replace_once(s, '#include "arm64/AsmHelpers.h"', '#include "arm64/AsmHelpers.h"\n#include <utility>\n#include <vector>')
    anchor = '\tvoid CompileRoutine();\n\nprotected:'
    s = replace_once(s, anchor, anchor + '\n\tusing CopyRow = std::pair<s64, s64>;\n\tvoid EmitCopyRows(const std::vector<CopyRow>& rows) const;\n')
    p.write_text(s)
    print('VIF pairing enabled for long, unmasked, mode-free, non-fill copies; overlap fallback preserved')
