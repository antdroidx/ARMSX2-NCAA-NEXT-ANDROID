// SPDX-License-Identifier: GPL-3.0
void VifUnpackNEON_Dynarec::CompileRoutine()
{
	const int wl = vB.wl ? vB.wl : 256; //0 is taken as 256 (KH2)
	const int upkNum = vB.upkType & 0xf;
	const u8& vift = nVifT[upkNum];
	const int cycleSize = isFill ? vB.cl : wl;
	const int blockSize = isFill ? wl : vB.cl;
	const int skipSize = blockSize - cycleSize;

	uint vNum = vB.num ? vB.num : 256;
	doMode = (upkNum == 0xf) ? 0 : doMode; // V4_5 has no mode feature.
	UnpkNoOfIterations = 0;
	VIF_LOG("Compiling new block, unpack number %x, mode %x, masking %x, vNum %x", upkNum, doMode, doMask, vNum);

	pxAssume(vCL == 0);

	// Value passed determines # of col regs we need to load
	SetMasks(isFill ? blockSize : cycleSize);

	while (vNum)
	{
		// Determine if reads/processing can be skipped.
		ProcessMasks();

		if (vCL < cycleSize)
		{
			ModUnpack(upkNum, false);
			xUnpack(upkNum);
			xMovDest();
			ModUnpack(upkNum, true);

			dstIndirect = armOffsetMemOperand(dstIndirect, 16);
			srcIndirect = armOffsetMemOperand(srcIndirect, vift);

			vNum--;
			if (++vCL == blockSize)
				vCL = 0;
		}
		else if (isFill)
		{
			xUnpack(upkNum);
			xMovDest();

			// dstIndirect += 16;
			dstIndirect = armOffsetMemOperand(dstIndirect, 16);

			vNum--;
			if (++vCL == blockSize)
				vCL = 0;
		}
		else
		{
			// dstIndirect += (16 * skipSize);
			dstIndirect = armOffsetMemOperand(dstIndirect, 16 * skipSize);
			vCL = 0;
		}
	}

	if (doMode >= 2)
		writeBackRow();

	armAsm->Ret();
}
