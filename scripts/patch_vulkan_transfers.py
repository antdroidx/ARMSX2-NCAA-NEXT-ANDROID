"""Avoid a bounded upload layout round trip and identical fallback copies."""
from pathlib import Path
from patch_conservative_gs import function
from patch_core_efficiency import replace_once


def patch(root):
    p = root / 'pcsx2/GS/Renderers/Vulkan/GSTextureVK.cpp'
    s = p.read_text()
    old = function(s, 'void GSTextureVK::UpdateFromBuffer(')
    new = replace_once(old, '\tif (old_layout == Layout::Undefined)', '''\t// Both callers immediately transition to ShaderReadOnly after the upload.
\t// For a single-level image, track TransferDst directly rather than restoring
\t// the previous layout just to transition away from it again. Keep the
\t// per-mip restore path unchanged for images with multiple levels.
\tif (m_mipmap_levels == 1)
\t\tTransitionToLayout(cmdbuf, Layout::TransferDst);
\telse if (old_layout == Layout::Undefined)''')
    new = replace_once(new, '\tif (old_layout != Layout::TransferDst && old_layout != Layout::Undefined)',
                      '\tif (m_mipmap_levels != 1 && old_layout != Layout::TransferDst && old_layout != Layout::Undefined)')
    p.write_text(replace_once(s, old, new))

    p = root / 'pcsx2/GS/Renderers/Vulkan/GSDeviceVK.cpp'
    s = p.read_text()
    old = '\t\t\t\t\tDoCopyRect(draw_rt, draw_rt_clone, snapped_samplearea, snapped_samplearea.left, snapped_samplearea.top);'
    new = '''\t\t\t\t\t// Alignment can turn distinct source regions into the same copy.
\t\t\t\t\t// There is no intervening draw/write, so that second copy adds no data.
\t\t\t\t\tif (!snapped_samplearea.eq(snapped_drawarea))
\t\t\t\t\t\tDoCopyRect(draw_rt, draw_rt_clone, snapped_samplearea, snapped_samplearea.left, snapped_samplearea.top);'''
    p.write_text(replace_once(s, old, new))
    print('Vulkan: single-level upload round trip removed; identical snapped fallback copies deduplicated')


if __name__ == '__main__':
    patch(Path.cwd())
