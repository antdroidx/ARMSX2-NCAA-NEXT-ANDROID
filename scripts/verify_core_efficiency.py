"""Execute patched conversion/cache/audio bodies; compile each for ARM64."""
from pathlib import Path
import os
import subprocess
import tempfile
from patch_conservative_gs import function
from patch_texture_streaming import STATS

root = Path.cwd()
repo = Path(__file__).resolve().parents[1]
cache = Path('pcsx2/GS/Renderers/HW/GSTextureCache.cpp').read_text()
replacement = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp').read_text()
audio = Path('pcsx2/Host/OboeAudioStream.cpp').read_text()
alpha = function(Path('pcsx2/GS/GS.cpp').read_text(), 'std::pair<u8, u8> GSGetRGBA8AlphaMinMax(')
old = function((repo/'tests/gs_mapped_original.inc').read_text(), 'if (mapped)')
new = function(function(cache, 'void GSTextureCache::Target::Update('), 'if (mapped)')
stride = function(Path('common/StringUtil.h').read_text(), 'static inline void StrideMemCpy(')
graphics = (repo/'tests/gs_mapped_harness.cpp').read_text().replace('// STRIDE_COPY', stride).replace('// ALPHA_FUNCTION', alpha).replace('// ORIGINAL', old).replace('// OPTIMIZED', new)
functions = '\n'.join(function(replacement, sig) for sig in [
    'size_t GSTextureReplacements::ReplacementTextureBytes(',
    'void GSTextureReplacements::TouchReplacementCacheLocked(',
    'const GSTextureReplacements::ReplacementTexture* GSTextureReplacements::InsertReplacementCacheLocked('])
insertion = (repo/'tests/cache_insert_harness.cpp').read_text().replace('// STATS', STATS).replace('// FUNCTIONS', functions)

audio_functions = function(audio, 'oboe::DataCallbackResult OboeAudioStream::onAudioReady(')+'\n'+function(audio, 'bool OboeAudioStream::Open()')
assert 'builder.setFramesPerDataCallback(2048)' not in audio_functions, 'Use cpu-audio variant for this candidate'
prelude = r'''
#include <sched.h>
#include <sys/syscall.h>
using u64=uint64_t;
int affinity_calls=0, warning_calls=0, info_calls=0, affinity_result=-1;
u64 performance_mask=0;
long fake_syscall(long request) { assert(request==SYS_gettid);return 42; }
int fake_affinity(pid_t tid,size_t,const cpu_set_t* set) {
    assert(tid==42);
    for(int i=0;i<64;++i) assert(!!CPU_ISSET(i,set)==!!(performance_mask&(u64(1)<<i)));
    ++affinity_calls;return affinity_result;
}
namespace VMManager::Internal { u64 GetPerformanceClusterAffinityMask(){return performance_mask;} }
#define syscall fake_syscall
#define sched_setaffinity fake_affinity
#define INFO_LOG(...) (++info_calls)
#define WARNING_LOG(...) (++warning_calls)
#define __ANDROID__ 1
'''
extra = r'''
    for(int rate:{44100,48000,96000}) {
        OboeAudioStream audio;audio.m_sample_rate=rate;
        oboe::returned_channels=2;assert(audio.Open());
        std::vector<float> data(192*2);
        auto callback=[&] {
            audio.begin=data.data();audio.end=data.data()+data.size();audio.calls=audio.frames_read=0;
            audio.onAudioReady(nullptr,data.data(),192);
            assert(audio.frames_read==192);
        };
        performance_mask=0;affinity_calls=warning_calls=info_calls=0;affinity_result=-1;
        for(int i=0;i<10;++i) callback();assert(affinity_calls==0);
        performance_mask=(u64(1)<<0)|(u64(1)<<2)|(u64(1)<<5);
        for(int i=0;i<1000;++i) callback();
        assert(affinity_calls>=1 && affinity_calls<=1+(1000*192)/rate);
        assert(warning_calls==1 && !audio.m_audio_thread_pinned.load());
        affinity_result=0;
        for(int i=0;i<rate/192+2;++i) callback();
        assert(audio.m_audio_thread_pinned.load() && info_calls==1);
        const int calls=affinity_calls;
        for(int i=0;i<100;++i) callback();assert(affinity_calls==calls);
        assert(audio.Open());assert(audio.m_audio_affinity_retry_frames.load()==0);
        callback();assert(affinity_calls==calls+1 && info_calls==2);
        assert(warning_calls==1);
    }
    std::cout<<"Audio affinity: rejected calls bounded, no per-callback warning, recovery/reopen and sample output passed\n";
'''
audio_test = (repo/'tests/selective_audio_harness.cpp').read_text().replace('// PRODUCTION_FUNCTIONS', prelude+audio_functions)
audio_test = audio_test.replace('    std::cout << "Production Oboe functions:', extra+'\n    std::cout << "Production Oboe functions:')

with tempfile.TemporaryDirectory() as temp:
    clang = Path(os.environ['ANDROID_HOME'])/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
    for name, code in [('graphics',graphics),('cache',insertion),('audio',audio_test)]:
        cpp=Path(temp)/(name+'.cpp');exe=Path(temp)/name;cpp.write_text(code)
        includes=['-I',str(root),'-I',str(root/'pcsx2')]
        subprocess.run(['g++','-std=c++20','-O2','-msse4.1','-fno-exceptions','-fsanitize=address,undefined','-fno-omit-frame-pointer',*includes,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True,timeout=60)
        subprocess.run([str(clang),'-std=c++20','-O2','-fno-exceptions',*includes,'-c',str(cpp),'-o',str(Path(temp)/(name+'-arm64.o'))],check=True)
print('Graphics/cache/audio production-body checks and ARM64 compilation passed')
