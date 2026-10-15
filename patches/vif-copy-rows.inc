// SPDX-License-Identifier: GPL-3.0
// Adapted from ARMSX2 commit c8f32ece8b21a3e2ff027b77d60b4952b08083ce
// Brian Degenhardt; overlap guard added for this fork.
void VifUnpackNEON_Dynarec::EmitCopyRows(const std::vector<CopyRow>& rows) const
{
	constexpr s64 pair_reach = 1008;

	const a64::Register dst_base = dstIndirect.GetBaseRegister();
	const a64::Register src_base = srcIndirect.GetBaseRegister();

    // Paired loads read the next row before the first store. Preserve the
    // single-row ordering for overlapping buffers, including forward overlap.
    a64::Label paired, done;
    const a64::Register end = workGprW.X();
    armAsm->Add(end, src_base, rows.back().second + 16);
    armAsm->Cmp(dst_base, end);
    armAsm->B(&paired, a64::hs);
    armAsm->Add(end, dst_base, rows.back().first + 16);
    armAsm->Cmp(src_base, end);
    armAsm->B(&paired, a64::hs);
    for (const auto& row : rows)
    {
        armAsm->Ldr(destReg, a64::MemOperand(src_base, row.second));
        armAsm->Str(destReg, a64::MemOperand(dst_base, row.first));
    }
    armAsm->B(&done);
    armAsm->Bind(&paired);

	s64 dst_bias = 0;
	s64 src_bias = 0;

	for (size_t i = 0; i < rows.size();)
	{
		const bool paired = (i + 1) < rows.size() &&
							rows[i + 1].first == rows[i].first + 16 &&
							rows[i + 1].second == rows[i].second + 16;

		if (paired)
		{
			if ((rows[i].first - dst_bias) > pair_reach)
			{
				armAsm->Add(dst_base, dst_base, rows[i].first - dst_bias);
				dst_bias = rows[i].first;
			}
			if ((rows[i].second - src_bias) > pair_reach)
			{
				armAsm->Add(src_base, src_base, rows[i].second - src_bias);
				src_bias = rows[i].second;
			}

			armAsm->Ldp(destReg, workReg, a64::MemOperand(src_base, rows[i].second - src_bias));
			armAsm->Stp(destReg, workReg, a64::MemOperand(dst_base, rows[i].first - dst_bias));
			i += 2;
		}
		else
		{
			armAsm->Ldr(destReg, a64::MemOperand(src_base, rows[i].second - src_bias));
			armAsm->Str(destReg, a64::MemOperand(dst_base, rows[i].first - dst_bias));
			i += 1;
		}
	}
    armAsm->Bind(&done);
}
