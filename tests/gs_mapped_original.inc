// SPDX-License-Identifier: GPL-3.0+
		if (mapped)
		{
			if (((m_TEX0.PSM & 0xf) != PSMCT24 || m_valid_alpha_high || m_valid_alpha_low) && m_dirty[i].rgba.c.a && bpp >= 16)
			{
				// TODO: Only read once in 32bit and copy to the mapped texture. Bit out of scope of this PR and not a huge impact.
				const int pitch = VectorAlign(read_r.width() * sizeof(u32));
				g_gs_renderer->m_mem.ReadTexture(off, read_r, s_unswizzle_buffer, pitch, TEXA);

				std::pair<u8, u8> new_alpha_minmax = GSGetRGBA8AlphaMinMax(s_unswizzle_buffer, read_r.width(), read_r.height(), pitch);
				alpha_minmax.first = std::min(alpha_minmax.first, new_alpha_minmax.first);
				alpha_minmax.second = std::max(alpha_minmax.second, new_alpha_minmax.second);
			}

			g_gs_renderer->m_mem.ReadTexture(
				off, read_r, m.bits + t_r.y * static_cast<u32>(m.pitch) + (t_r.x * sizeof(u32)), m.pitch, TEXA);
		}
