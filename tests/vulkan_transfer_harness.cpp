// Production upload, transition and rectangle selection code; mocked Vulkan commands.
#include "GS/GSVector.h"
#include <vulkan/vulkan_core.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <functional>
#include <iostream>
#include <random>
#include <vector>
#undef pxAssertMsg
#define pxAssertMsg(x,...) assert(x)
#define GL_INS(...) ((void)0)
namespace GSPerfMon {constexpr int Barriers=0,BarriersROV=1;}
struct Perf {void Put(int,int){}}g_perfmon;
struct GSDeviceVK {
 struct FeatureSet {bool stencil_buffer=false;}features;
 bool feedback=false;
 static GSDeviceVK* GetInstance();
 bool UseFeedbackLoopLayout()const{return feedback;}
 const FeatureSet& Features()const{return features;}
 bool DeferredDrawsWouldObserve(const void*)const{return false;}
};
GSDeviceVK device;GSDeviceVK* g_gs_device=&device;
GSDeviceVK* GSDeviceVK::GetInstance(){return &device;}
std::function<void(VkPipelineStageFlags,VkPipelineStageFlags,const VkImageMemoryBarrier&)> barrier_hook;
std::function<void(VkImageLayout,const VkBufferImageCopy&)> copy_hook;
VKAPI_ATTR void VKAPI_CALL vkCmdPipelineBarrier(VkCommandBuffer,VkPipelineStageFlags src,VkPipelineStageFlags dst,VkDependencyFlags,u32 memory_count,const VkMemoryBarrier*,u32 buffer_count,const VkBufferMemoryBarrier*,u32 image_count,const VkImageMemoryBarrier* images){
 assert(memory_count==0&&buffer_count==0&&image_count==1);barrier_hook(src,dst,*images);
}
VKAPI_ATTR void VKAPI_CALL vkCmdCopyBufferToImage(VkCommandBuffer,VkBuffer,VkImage,VkImageLayout layout,u32 count,const VkBufferImageCopy* regions){assert(count==1);copy_hook(layout,*regions);}
// TEXTURE_CLASSES
struct Event {
 VkPipelineStageFlags src,dst;VkAccessFlags src_access,dst_access;VkImageLayout before,after;u32 first,count;
 bool operator==(const Event&)const=default;
};
struct Result {std::vector<Event> events;std::vector<std::vector<u32>> pixels;std::vector<VkImageLayout> layouts;int final_layout;size_t prefix;};
template<class Texture>Result upload(int initial,int levels,int level,int variant,bool rt){
 Texture texture;texture.m_mipmap_levels=levels;texture.m_layout=static_cast<typename Texture::Layout>(initial);texture.rt=rt;
 Result result;result.layouts.assign(levels,GetVkImageLayout(texture.m_layout));
 for(int l=0;l<levels;++l){int size=64>>l;result.pixels.emplace_back(size*size);for(int i=0;i<size*size;++i)result.pixels.back()[i]=static_cast<u32>(i*9871+l*729193);}
 const u32 size=64>>level,width=variant==0?size:std::min(7u,size-2),height=variant==0?size:std::min(5u,size-2),x=variant==0?0:1,y=x;
 const u32 row_length=width+variant*3,offset=16;
 std::vector<u32> buffer(offset/4+row_length*height);
 for(size_t i=0;i<buffer.size();++i)buffer[i]=static_cast<u32>(i*198269u+variant*193);
 bool copied=false;
 barrier_hook=[&](auto src,auto dst,const VkImageMemoryBarrier& b){
  assert(b.subresourceRange.aspectMask==VK_IMAGE_ASPECT_COLOR_BIT);
  const u32 first=b.subresourceRange.baseMipLevel,count=b.subresourceRange.levelCount;
  assert(first+count<=static_cast<u32>(levels));
  for(u32 l=first;l<first+count;++l){assert(result.layouts[l]==b.oldLayout);result.layouts[l]=b.newLayout;}
  result.events.push_back({src,dst,b.srcAccessMask,b.dstAccessMask,b.oldLayout,b.newLayout,first,count});
 };
 copy_hook=[&](auto layout,const VkBufferImageCopy& b){
  assert(!copied&&layout==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);copied=true;result.prefix=result.events.size();
  assert(b.imageSubresource.mipLevel==static_cast<u32>(level)&&b.imageSubresource.aspectMask==VK_IMAGE_ASPECT_COLOR_BIT);
  assert(result.layouts[level]==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
  assert(b.bufferOffset==offset&&b.bufferRowLength==row_length&&b.imageOffset.x==static_cast<int>(x)&&b.imageOffset.y==static_cast<int>(y));
  assert(b.imageExtent.width==width&&b.imageExtent.height==height&&b.imageExtent.depth==1);
  for(u32 row=0;row<height;++row)std::copy_n(buffer.data()+offset/4+row*row_length,width,result.pixels[level].data()+(y+row)*size+x);
 };
 // Both real callers pre-transition Undefined images, then finish ShaderReadOnly.
 if(texture.m_layout==Texture::Layout::Undefined)texture.TransitionToLayout({},Texture::Layout::TransferDst);
 texture.UpdateFromBuffer({},level,x,y,width,height,height,row_length,{},offset);
 texture.TransitionToLayout({},Texture::Layout::ShaderReadOnly);
 assert(copied);result.final_layout=static_cast<int>(texture.m_layout);return result;
}
struct CopyImage {std::vector<u32> pixels;CopyImage():pixels(64*64,0x71a254ffu){}};
struct CopyConfig {bool tex_hazard;GSVector4i drawarea,samplearea;};
struct CopyRunner {
 unsigned calls=0,pixels=0;
 GSVector4i ProcessCopyArea(const GSVector4i&,const GSVector4i&);
 void DoCopyRect(CopyImage* src,CopyImage* dst,const GSVector4i& rect,u32 x,u32 y){
  if(rect.rempty())return;
  assert(x==static_cast<u32>(rect.x)&&y==static_cast<u32>(rect.y));++calls;pixels+=rect.width()*rect.height();
  for(int row=rect.y;row<rect.w;++row)std::copy_n(src->pixels.data()+row*64+rect.x,rect.width(),dst->pixels.data()+row*64+rect.x);
 }
 void Old(CopyConfig& config,CopyImage* draw_rt,CopyImage* draw_rt_clone){GSVector2i rtsize(64,64); // OLD_COPIES
 }
 void New(CopyConfig& config,CopyImage* draw_rt,CopyImage* draw_rt_clone){GSVector2i rtsize(64,64); // NEW_COPIES
 }
};
// PROCESS_COPY_AREA
int main(){
 size_t uploads=0,saved=0;
 for(int layout=0;layout<static_cast<int>(Original::GSTextureVK::Layout::Count);++layout)
 for(bool feedback:{false,true})for(bool rt:{false,true})for(int levels:{1,2,4})for(int level=0;level<levels;++level)for(int variant:{0,1,2}){
  device.feedback=feedback;
  auto old=upload<Original::GSTextureVK>(layout,levels,level,variant,rt),now=upload<Optimized::GSTextureVK>(layout,levels,level,variant,rt);
  assert(old.pixels==now.pixels&&old.layouts==now.layouts&&old.final_layout==now.final_layout);
  assert(now.events.size()<=old.events.size());
  if(levels>1)assert(old.events==now.events);
  else {
   assert(old.prefix==now.prefix&&std::equal(old.events.begin(),old.events.begin()+old.prefix,now.events.begin()));
   // The transfer write must still become visible to fragment shader reads.
   assert(!now.events.empty());const auto& last=now.events.back();
   assert(last.src&VK_PIPELINE_STAGE_TRANSFER_BIT);assert(last.src_access&VK_ACCESS_TRANSFER_WRITE_BIT);
   assert(last.dst&VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);assert(last.dst_access&VK_ACCESS_SHADER_READ_BIT);
  }
  saved+=old.events.size()-now.events.size();++uploads;
 }
 auto a=upload<Original::GSTextureVK>(2,1,0,1,true),b=upload<Optimized::GSTextureVK>(2,1,0,1,true);
 assert(a.events.size()==3&&b.events.size()==2);
 std::mt19937 rng(196274);size_t copy_cases=0,duplicate_cases=0;
 auto check=[&](CopyConfig config){
  CopyImage src,old,now;for(size_t i=0;i<src.pixels.size();++i)src.pixels[i]=static_cast<u32>(i*198269u);
  CopyRunner before,after;before.Old(config,&src,&old);after.New(config,&src,&now);
  assert(old.pixels==now.pixels&&after.calls<=before.calls&&after.pixels<=before.pixels);
  duplicate_cases+=after.calls<before.calls;++copy_cases;
 };
 // Deliberately different rectangles which align to the same four-pixel tile.
 for(int tile_y=0;tile_y<64;tile_y+=4)for(int tile_x=0;tile_x<64;tile_x+=4)
  check({true,GSVector4i(tile_x+1,tile_y+1,tile_x+2,tile_y+2),GSVector4i(tile_x+2,tile_y+2,tile_x+3,tile_y+3)});
 for(int i=0;i<5000;++i){
  auto rect=[&](){int x=rng()%64,y=rng()%64;return GSVector4i(x,y,x+rng()%(65-x),y+rng()%(65-y));};
  check({true,rect(),rect()});
 }
 assert(duplicate_cases>=256&&saved>0);
 std::cout<<"Vulkan transfers: "<<uploads<<" upload/layout/pixel cases; "<<saved<<" synthetic barriers eliminated; representative RT upload 3 -> 2; "<<copy_cases<<" copy cases, "<<duplicate_cases<<" duplicate cases skipped; multi-mip sequences unchanged\n";
}
