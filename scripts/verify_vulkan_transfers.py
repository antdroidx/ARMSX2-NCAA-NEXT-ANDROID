"""Compare production upload/barrier and copy-selection bodies with mocked GPU commands."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
from patch_conservative_gs import function

repo = Path(__file__).resolve().parents[1]
root = Path.cwd()
source = Path('pcsx2/GS/Renderers/Vulkan/GSTextureVK.cpp').read_text()
header = Path('pcsx2/GS/Renderers/Vulkan/GSTextureVK.h').read_text()
dev = Path('pcsx2/GS/Renderers/Vulkan/GSDeviceVK.cpp').read_text()
fixture = json.loads((repo / 'tests/vulkan_transfer_original.json').read_text())

# The only two callers finish ShaderReadOnly; their clears/map/upload code is unchanged.
assert source.count('UpdateFromBuffer(') == 3
for name, signature in [('do_update', 'bool GSTextureVK::DoUpdate('), ('unmap', 'void GSTextureVK::Unmap(')]:
    body = function(source, signature)
    assert hashlib.sha256(body.encode()).hexdigest() == fixture[name + '_sha256']
    assert body.index('UpdateFromBuffer(') < body.index('TransitionToLayout(cmdbuf, Layout::ShaderReadOnly);')

layout = function(header, 'enum class Layout') + ';'
transition = function(source, 'void GSTextureVK::TransitionToLayout(VkCommandBuffer')
subresources = function(source, 'void GSTextureVK::TransitionSubresourcesToLayout(')
vk_layout = function(source, 'static VkImageLayout GetVkImageLayout(')
feedback_access = function(source, 'static VkAccessFlagBits GetFeedbackLoopInputAccessBits(')
classes = ''
for ns, upload in [('Original', fixture['upload']), ('Optimized', function(source, 'void GSTextureVK::UpdateFromBuffer('))]:
    classes += f'''namespace {ns} {{
class GSTextureVK {{public:
{layout}
int m_mipmap_levels=1;Layout m_layout=Layout::Undefined;VkImage m_image={{}};bool rt=true;
bool IsDepthStencil()const{{return false;}}bool IsRenderTargetOrDepthStencil()const{{return rt;}}
void TransitionToLayout(VkCommandBuffer,Layout);
void TransitionSubresourcesToLayout(VkCommandBuffer,int,int,Layout,Layout);
void UpdateFromBuffer(VkCommandBuffer,int,u32,u32,u32,u32,u32,u32,VkBuffer,u32);
}};
{vk_layout}
{feedback_access}
{transition}
{subresources}
{upload}
}}
'''

new_copy = function(function(dev, 'void GSDeviceVK::DoRenderHW('), 'if (config.tex_hazard)')
common_device = Path('pcsx2/GS/Renderers/Common/GSDevice.cpp').read_text()
assert 'FetchSurface(GSTexture::RenderTarget, w, h, 1,' in function(common_device, 'GSTexture* GSDevice::CreateRenderTarget(int w, int h,')
process = function(common_device, 'GSVector4i GSDevice::ProcessCopyArea(')
code = (repo / 'tests/vulkan_transfer_harness.cpp').read_text()
code = code.replace('// TEXTURE_CLASSES', classes).replace('// OLD_COPIES', fixture['copies']).replace('// NEW_COPIES', new_copy)
code = code.replace('// PROCESS_COPY_AREA', process.replace('GSDevice::ProcessCopyArea', 'CopyRunner::ProcessCopyArea'))
with tempfile.TemporaryDirectory() as tmp:
    cpp = Path(tmp) / 'transfers.cpp'
    exe = Path(tmp) / 'transfers'
    cpp.write_text(code)
    includes = ['-I', str(root), '-I', str(root / 'pcsx2'), '-I', str(root / '3rdparty/vulkan/include')]
    subprocess.run(['g++', '-std=c++20', '-O2', '-msse4.1', '-fno-exceptions', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *includes, str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=60)
    clang = Path(os.environ['ANDROID_HOME']) / 'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
    subprocess.run([str(clang), '-std=c++20', '-O2', '-fno-exceptions', *includes, '-c', str(cpp), '-o', str(Path(tmp) / 'transfers.o')], check=True)
print('Production Vulkan upload/barrier/copy differential checks and Android ARM64 compilation passed; real-driver timing/validation pending')
