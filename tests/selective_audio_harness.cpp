#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <vector>
using u32 = uint32_t;
using SampleType = float;
struct Logger {
    template<class... T> void WriteLn(T...) {}
    template<class... T> void Error(T...) {}
} Console;
namespace oboe {
enum class DataCallbackResult { Continue };
enum class Result { OK, Error };
namespace Direction { constexpr int Output = 0; }
namespace AudioApi { constexpr int OpenSLES = 0; }
namespace SharingMode { constexpr int Shared = 0; }
namespace AudioFormat { constexpr int Float = 0; }
constexpr int kUnspecified = 0;
int requested_channels = 0, returned_channels = 0, closed = 0, fixed_callback = 0;
bool fail_open = false;
struct AudioStream {
    int getChannelCount() { return returned_channels; }
    void close() { ++closed; }
};
struct AudioStreamBuilder {
    void setDirection(int) {}
    void setPerformanceMode(int) {}
    void setAudioApi(int) {}
    void setSharingMode(int) {}
    void setFormat(int) {}
    void setSampleRate(int) {}
    void setChannelCount(int n) { requested_channels = n; }
    void setDeviceId(int) {}
    void setBufferCapacityInFrames(int) {}
    void setFramesPerDataCallback(int n) { fixed_callback = n; }
    void setDataCallback(void*) {}
    void setErrorCallback(void*) {}
    Result openStream(std::shared_ptr<AudioStream>& stream) {
        if (fail_open) return Result::Error;
        stream = std::make_shared<AudioStream>();
        return Result::OK;
    }
};
}
struct OboeAudioStream {
    std::recursive_mutex m_lock;
    std::atomic<bool> m_audio_thread_pinned{false};
    struct { bool android_use_opensles = false; } m_parameters;
    int m_perf_mode = 0, m_sample_rate = 48000;
    u32 m_output_channels = 2;
    std::shared_ptr<oboe::AudioStream> m_stream;
    u32 frames_read = 0, calls = 0;
    SampleType *begin = nullptr, *end = nullptr;
    void ReadFrames(SampleType* out, u32 frames) {
        assert(frames > 0 && frames <= 2048);
        assert(out == begin + frames_read * m_output_channels);
        assert(out + frames * m_output_channels <= end);
        std::fill(out, out + frames * m_output_channels, 1.0f);
        frames_read += frames;
        ++calls;
    }
    bool Open();
    oboe::DataCallbackResult onAudioReady(oboe::AudioStream*, void*, int32_t);
};
// PRODUCTION_FUNCTIONS
int main() {
    for (u32 channels : {1u, 2u, 3u, 4u, 6u, 8u}) {
        OboeAudioStream audio;
        audio.m_output_channels = channels;
        oboe::returned_channels = channels;
        assert(audio.Open());
        assert(oboe::requested_channels == static_cast<int>(channels));
        assert(oboe::fixed_callback == 0);
        oboe::returned_channels = channels + 1;
        const int old_closed = oboe::closed;
        assert(!audio.Open() && !audio.m_stream && oboe::closed == old_closed + 1);
        oboe::fail_open = true;
        assert(!audio.Open());
        oboe::fail_open = false;
        for (int frames : {0, 1, 96, 192, 256, 1024, 2048, 2049, 4096, 8193}) {
            std::vector<float> buffer(frames * channels + 2, -7.0f);
            audio.begin = buffer.data() + 1;
            audio.end = audio.begin + frames * channels;
            audio.calls = audio.frames_read = 0;
            audio.onAudioReady(nullptr, audio.begin, frames);
            assert(audio.frames_read == static_cast<u32>(frames));
            assert(buffer.front() == -7.0f && buffer.back() == -7.0f);
            assert(std::all_of(audio.begin, audio.end, [](float f) { return f == 1.0f; }));
        }
        audio.calls = 0;
        audio.onAudioReady(nullptr, nullptr, 8193);
        assert(audio.calls == 0);
    }
    std::cout << "Production Oboe functions: channel negotiation, rejection, burst boundaries, null output passed\n";
}
