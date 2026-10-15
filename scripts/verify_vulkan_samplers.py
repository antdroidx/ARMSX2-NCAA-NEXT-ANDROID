"""Run production sampler lookup/cleanup with mocked Vulkan driver calls."""
from pathlib import Path
import os,re,subprocess,tempfile
from patch_conservative_gs import function
repo=Path(__file__).resolve().parents[1]
source=Path('pcsx2/GS/Renderers/Vulkan/GSDeviceVK.cpp').read_text()
header=Path('pcsx2/GS/Renderers/Vulkan/GSDeviceVK.h').read_text()
old=(repo/'tests/vulkan_sampler_original.inc').read_text()
selector=function(Path('pcsx2/GS/Renderers/Common/GSDevice.h').read_text(),'struct SamplerSelector')+';'
assert 'u8 key;' in selector
get_old=function(old,'VkSampler GSDeviceVK::GetSampler(')
get_new=function(source,'VkSampler GSDeviceVK::GetSampler(')
# The sampler descriptor must be byte-for-byte unchanged.
def descriptor(s):return s[s.index('const VkSamplerCreateInfo ci'):s.index('\n\tVkSampler sampler')]
assert descriptor(get_old)==descriptor(get_new)
constants=set(re.findall(r'\bVK_[A-Z0-9_]+\b',get_old))
values={'VK_NULL_HANDLE':'0','VK_SUCCESS':'0','VK_FALSE':'0','VK_LOD_CLAMP_NONE':'1000.0f'}
for i,c in enumerate(sorted(constants-values.keys()),10):values[c]=str(i)
consts='\n'.join(f'constexpr auto {k}={v};' for k,v in values.items())
# GS enum values used by the unchanged selector helpers.
consts+='\nenum class GS_MIN_FILTER:u8 {Nearest_Mipmap_Nearest=2,Nearest_Mipmap_Linear=3,Linear_Mipmap_Nearest=4,Linear_Mipmap_Linear=5};'
classes=''
for ns,text,storage in [('Original',old,'std::unordered_map<u32,VkSampler> m_samplers;'),('Optimized',source,'std::array<VkSampler,256> m_samplers{};std::array<bool,256> m_sampler_initialized{};')]:
 get=function(text,'VkSampler GSDeviceVK::GetSampler(')
 clear=function(text,'void GSDeviceVK::ClearSamplerCache(')
 cleanup=clear[clear.index('\tfor ('):clear.index('\n\tm_point_sampler')]
 if ns=='Optimized':
  assert text.count(cleanup)==2 # ClearSamplerCache and DestroyResources must both reset.
  assert 'std::array<VkSampler, 256> m_samplers{};' in header
 classes+=f'namespace {ns} {{\nclass GSDeviceVK {{public:\nint m_device;{storage}\nVkSampler m_point_sampler=0,m_linear_sampler=0,m_tfx_sampler=0,m_utility_sampler=0;\nexplicit GSDeviceVK(int d):m_device(d){{}}\nvoid ExecuteCommandBuffer(bool wait){{assert(wait);++envs[m_device].waits;}}\nVkSampler GetSampler(GSHWDrawConfig::SamplerSelector);void ClearSamplerCache();void Shutdown(){{\n{cleanup}\n}}\n}};\n{get}\n{clear}\n}}\n'
code=(repo/'tests/vulkan_sampler_harness.cpp').read_text().replace('// CONSTANTS',consts).replace('// SELECTOR',selector).replace('// NAMESPACES',classes)
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'samplers.cpp';cpp.write_text(code);exe=Path(tmp)/'samplers'
 subprocess.run(['g++','-std=c++20','-O2','-fno-exceptions','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=30)
 clang=Path(os.environ['ANDROID_HOME'])/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
 subprocess.run([str(clang),'-std=c++20','-O2','-fno-exceptions','-c',str(cpp),'-o',str(Path(tmp)/'samplers.o')],check=True)
print('Vulkan sampler differential and ARM64 compile passed; device timing remains unmeasured')
