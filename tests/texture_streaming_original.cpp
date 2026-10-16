// SPDX-License-Identifier: GPL-3.0+
// Pinned upstream upload processor, kept as a differential-test reference.
void GSTextureReplacements::ProcessAsyncLoadedTextures()
{
	// Per-frame GPU upload budget.
	//
	// Every pending texture used to be uploaded in ONE call ("this should be reasonably
	// quick" — true for a handful of BC-compressed textures, false otherwise). Walking into
	// a new area streams a whole batch in at once, and real HD packs are entirely
	// UNCOMPRESSED DDS (God of War 1 HD = 2.97 GB over 2235 files, Persona 3 FES = 5.0 GB),
	// where one 2048x2048 texture is 16 MB. Ten arriving together meant ~160 MB of GPU
	// upload inside a single frame, while holding the cache lock — reported as "FPS drops to
	// 50 and stutters in certain areas" with a pack that runs fine on other emulators.
	//
	// Spreading the uploads costs a frame or two of pop-in, which is imperceptible next to
	// dropping the frame outright. 16 MB bounds the worst case to roughly one uncompressed
	// 2048x2048 texture per frame — the natural granularity here.
	constexpr size_t MAX_UPLOAD_BYTES_PER_FRAME = static_cast<size_t>(16) * 1024 * 1024;

	std::unique_lock<std::mutex> lock(s_replacement_texture_cache_mutex);
	size_t uploaded_bytes = 0;
	size_t idx = 0;
	for (; idx < s_async_loaded_textures.size(); idx++)
	{
		// Checked at the top with a zero start, so a texture larger than the whole budget
		// still goes through on its own frame and can never wedge the queue.
		if (uploaded_bytes >= MAX_UPLOAD_BYTES_PER_FRAME)
			break;

		const auto& [name, mipmap] = s_async_loaded_textures[idx];

		// no longer pending!
		const auto pit = s_pending_async_load_textures.find(name);
		if (pit != s_pending_async_load_textures.end())
		{
			const bool cache_only = pit->second;
			s_pending_async_load_textures.erase(pit);

			// if we were precaching, don't inject into the TC if we didn't actually get requested
			// (costs no upload, so it doesn't draw down the budget)
			if (cache_only)
				continue;
		}

		// we should be in the cache now, lock and loaded
		auto it = s_replacement_texture_cache.find(name);
		if (it == s_replacement_texture_cache.end())
			continue;

		// upload and inject into TC
		GSTexture* tex = CreateReplacementTexture(it->second, mipmap);
		if (tex)
			g_texture_cache->InjectHashCacheTexture(HashCacheKeyFromTextureName(name), tex, it->second.alpha_minmax);

		uploaded_bytes += ReplacementTextureBytes(it->second);
	}

	// Carry whatever we didn't reach into the next frame rather than dropping it.
	if (idx >= s_async_loaded_textures.size())
		s_async_loaded_textures.clear();
	else
		s_async_loaded_textures.erase(s_async_loaded_textures.begin(), s_async_loaded_textures.begin() + idx);
}
