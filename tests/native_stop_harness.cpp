// Compile with the production JNI shutdown body injected by test_native_stop.py.
#include <atomic>
#include <cassert>
#include <deque>
#include <functional>
#include <mutex>
#include <thread>
#include <iostream>
using JNIEnv = void;
using jclass = void*;
constexpr int ANDROID_LOG_INFO = 0;
void __android_log_print(int, const char*, const char*) {}
enum class VMState { Shutdown, Running, Paused, Stopping };
enum class LimiterModeType { Nominal };
std::mutex s_cpu_thread_mutex;
std::thread::id s_cpu_thread_id;
std::deque<std::function<void()>> s_cpu_thread_queue;
std::atomic<bool> s_stop_requested{false};
namespace VMManager {
VMState state = VMState::Shutdown;
int touches = 0;
bool HasValidVM() { return state == VMState::Running || state == VMState::Paused; }
void SetLimiterMode(LimiterModeType) {
    assert(std::this_thread::get_id() == s_cpu_thread_id);
    assert(HasValidVM());
    ++touches;
}
void SetState(VMState value) {
    assert(std::this_thread::get_id() == s_cpu_thread_id);
    assert(HasValidVM());
    state = value;
    ++touches;
}
}
void shutdown(JNIEnv* env, jclass clazz)
// PRODUCTION_BODY

void request() {
    std::thread control([] { shutdown(nullptr, nullptr); });
    control.join();
}
void drain() {
    while (!s_cpu_thread_queue.empty()) {
        auto fn = std::move(s_cpu_thread_queue.front());
        s_cpu_thread_queue.pop_front();
        fn();
    }
}
int main() {
    // No owner must never execute inline or queue work for the next session.
    request();
    assert(s_cpu_thread_queue.empty() && VMManager::touches == 0);
    s_cpu_thread_id = std::this_thread::get_id();
    for (auto state : {VMState::Running, VMState::Paused}) {
        VMManager::state = state;
        s_stop_requested = false;
        const int before = VMManager::touches;
        request(); request();
        assert(VMManager::touches == before && !s_stop_requested);
        drain();
        assert(VMManager::state == VMState::Stopping && s_stop_requested);
        assert(VMManager::touches == before + 2);
    }
    // Teardown wins the race: final pump must discard a stale stop.
    VMManager::state = VMState::Running;
    request();
    VMManager::state = VMState::Shutdown;
    const int before = VMManager::touches;
    drain();
    assert(VMManager::touches == before && VMManager::state == VMState::Shutdown);
    std::cout << "Native stop ownership: no-owner, running, paused, duplicate, stale passed\n";
}
