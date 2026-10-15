"""Index the bounded Vulkan sampler domain without hash-table nodes."""
from pathlib import Path
from patch_core_efficiency import replace_once


def patch(root):
    p = root / 'pcsx2/GS/Renderers/Vulkan/GSDeviceVK.h'
    s = p.read_text()
    s = replace_once(s, '\tstd::unordered_map<u32, VkSampler> m_samplers;', '''\t// SamplerSelector::key is u8, including its reserved high bit.
\tstd::array<VkSampler, 256> m_samplers{};
\t// Null creation results are cached too, matching the original map semantics.
\tstd::array<bool, 256> m_sampler_initialized{};''')
    p.write_text(s)
    p = root / 'pcsx2/GS/Renderers/Vulkan/GSDeviceVK.cpp'
    s = p.read_text()
    s = replace_once(s, '''\tconst auto it = m_samplers.find(ss.key);
\tif (it != m_samplers.end())
\t\treturn it->second;''', '''\tif (m_sampler_initialized[ss.key])
\t\treturn m_samplers[ss.key];''')
    s = replace_once(s, '\tm_samplers.emplace(ss.key, sampler);', '\tm_samplers[ss.key] = sampler;\n\tm_sampler_initialized[ss.key] = true;')
    old = '''\tfor (const auto& it : m_samplers)
\t{
\t\tif (it.second != VK_NULL_HANDLE)
\t\t\tvkDestroySampler(m_device, it.second, nullptr);
\t}
\tm_samplers.clear();'''
    new = '''\tfor (const VkSampler sampler : m_samplers)
\t{
\t\tif (sampler != VK_NULL_HANDLE)
\t\t\tvkDestroySampler(m_device, sampler, nullptr);
\t}
\tm_samplers.fill(VK_NULL_HANDLE);
\tm_sampler_initialized.fill(false);'''
    assert s.count(old) == 2
    p.write_text(s.replace(old, new))
    print('Vulkan sampler hash lookups replaced with a bounded 256-slot table')

if __name__ == '__main__':
    patch(Path.cwd())
