#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <random>
#include <set>
#include <unordered_map>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using VkSampler=uint64_t;using VkResult=int;using VkSamplerAddressMode=int;
#define __fi inline
#define LOG_VULKAN_ERROR(...) ((void)0)
// CONSTANTS
struct VkSamplerCreateInfo {
 int type;const void* next;int flags,mag,min,mip,u,v,w;float bias;int anisoEnable;float aniso;int compareEnable,compare;float minLod,maxLod;int border,unnormalized;
 bool operator==(const VkSamplerCreateInfo&) const=default;
};
struct GSHWDrawConfig { // SELECTOR
};
struct Env {
 unsigned calls=0,waits=0;std::vector<VkSamplerCreateInfo> infos;std::set<VkSampler> live;
};
Env envs[2];
VkResult vkCreateSampler(int device,const VkSamplerCreateInfo* ci,const void*,VkSampler* out) {
 auto& e=envs[device];++e.calls;e.infos.push_back(*ci);
 if(e.calls%11==0){*out=0;return -1;}
 *out=100+e.calls;assert(e.live.insert(*out).second);return 0;
}
void vkDestroySampler(int device,VkSampler sampler,const void*) {assert(envs[device].live.erase(sampler)==1);}
// NAMESPACES
int main(){
 Original::GSDeviceVK old(0);Optimized::GSDeviceVK now(1);
 std::mt19937 rng(52641);size_t requests=0;
 auto get=[&](u8 key){
  assert(old.GetSampler(key)==now.GetSampler(key));
  assert(envs[0].calls==envs[1].calls && envs[0].infos==envs[1].infos && envs[0].live==envs[1].live);++requests;
 };
 // Every bit pattern, including the reserved bit, and repeated failures.
 for(unsigned k=0;k<256;++k){get(k);get(k);}
 assert(envs[0].calls==256);
 for(unsigned i=0;i<10000;++i){
  if(i%97==0){old.ClearSamplerCache();now.ClearSamplerCache();assert(envs[0].waits==envs[1].waits);}
  get(static_cast<u8>(rng()));
 }
 old.ClearSamplerCache();now.ClearSamplerCache();
 assert(old.m_point_sampler==now.m_point_sampler && old.m_linear_sampler==now.m_linear_sampler);
 assert(old.m_tfx_sampler==now.m_tfx_sampler && old.m_utility_sampler==now.m_utility_sampler);
 old.Shutdown();now.Shutdown();assert(envs[0].live.empty() && envs[1].live.empty());
 for(unsigned k=0;k<256;++k)get(k);
 old.Shutdown();now.Shutdown();assert(envs[0].live.empty() && envs[1].live.empty());
 std::cout<<"Vulkan sampler: "<<requests<<" differential requests, all 256 keys, failed creates, cache clear and shutdown passed\n";
}
