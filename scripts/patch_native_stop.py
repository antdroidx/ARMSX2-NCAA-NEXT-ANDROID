"""Give the CPU thread exclusive ownership of the Android stop transition."""
from pathlib import Path

SIGNATURE = 'Java_kr_co_iefriends_pcsx2_NativeApp_shutdown(JNIEnv *env, jclass clazz)'
BODY = r'''{
    // Never touch Cpu, the limiter, or the file logger from this caller: the
    // run thread can already be in CPUThreadShutdown and destroying them.
    // Queue under the owner mutex rather than RunOnCPUThread's no-owner inline
    // fallback. The frontend barrier waits for runVMThread to return before
    // releasing the session or starting the next game.
    std::lock_guard lock(s_cpu_thread_mutex);
    if (s_cpu_thread_id == std::thread::id())
    {
        __android_log_print(ANDROID_LOG_INFO, "NCAA_NEXT", "VM_EXIT NATIVE_STOP_NO_OWNER");
        return;
    }
    s_cpu_thread_queue.push_back([]() {
        // A queued stop may reach the final message pump after VM shutdown.
        if (!VMManager::HasValidVM())
        {
            __android_log_print(ANDROID_LOG_INFO, "NCAA_NEXT", "VM_EXIT NATIVE_STOP_STALE");
            return;
        }
        __android_log_print(ANDROID_LOG_INFO, "NCAA_NEXT", "VM_EXIT NATIVE_STOP_CPU");
        VMManager::SetLimiterMode(LimiterModeType::Nominal);
        s_stop_requested.store(true, std::memory_order_release);
        VMManager::SetState(VMState::Stopping);
    });
    __android_log_print(ANDROID_LOG_INFO, "NCAA_NEXT", "VM_EXIT NATIVE_STOP_QUEUED");
}'''


def patch(source):
    if source.count(SIGNATURE) != 1:
        raise RuntimeError('Native shutdown signature changed')
    start = source.index('{', source.index(SIGNATURE))
    end = source.index('\n}\n', start) + 2
    old = source[start:end]
    if 'for (int i = 0; i < 5000; ++i)' not in old:
        raise RuntimeError('Expected pinned polling shutdown implementation')
    return source[:start] + BODY + source[end:]


if __name__ == '__main__':
    path = Path('platforms/android/app/src/main/cpp/native-lib.cpp')
    path.write_text(patch(path.read_text(encoding='utf-8')), encoding='utf-8')
    print('Android stop transition now belongs exclusively to the CPU thread')
