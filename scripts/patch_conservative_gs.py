"""Avoid redundant GS work without changing emulated values or synchronization."""
from pathlib import Path

EARLY_EXIT = '''
			// The full 8-bit alpha range cannot expand further. Check once per
			// eight rows on large images to keep the opaque-image overhead small.
			if (width >= 64 && (r & 7) == 7 &&
				(minc.minv_u32() >> 24) == 0 && (maxc.maxv_u32() >> 24) == 255)
				return {0, 255};
'''

def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if not depth:
            return text[start:end + 1]
    raise RuntimeError(signature)

def patch_alpha(source):
    old = function(source, 'std::pair<u8, u8> GSGetRGBA8AlphaMinMax(')
    anchor = '\n\t\t\tptr += stride;'
    assert old.count(anchor) == 2 and EARLY_EXIT not in old
    new = old.replace(anchor, EARLY_EXIT + anchor)
    return source.replace(old, new, 1)

if __name__ == '__main__':
    p = Path('pcsx2/GS/GS.cpp')
    p.write_text(patch_alpha(p.read_text()))
    p = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
    s = p.read_text()
    anchor = '\tstd::string filename;\n\tfor (FILESYSTEM_FIND_DATA& fd : files)'
    assert s.count(anchor) == 1
    reserve = '''	// Avoid repeated bucket rebuilds while inserting a large replacement pack.
	s_replacement_texture_filenames.reserve(files.size());
	s_replacement_textures_without_clut_hash.reserve(files.size());

'''
    p.write_text(s.replace(anchor, reserve + anchor, 1))
    print('Reserved filename lookup capacity; added exact alpha-range early exit')
