package com.armsx2.runtime

/** Both JNI calls must return before the frontend may release the session.
 * shutdown() returning (including its timeout) is not a join of runVMThread().
 * Synchronize on this object when combining it with frontend restart state.
 */
internal class VmCompletionBarrier {
    @Volatile var running = false
        private set
    @Volatile var stopping = false
        private set
    private var stopCallerActive = false
    private var completionPending = false

    @Synchronized fun beginRun() {
        check(!running && !stopping) { "Previous VM has not finished" }
        running = true
    }

    /** False means a duplicate request or no session; never enqueue a second shutdown. */
    @Synchronized fun requestStop(): Boolean {
        if (stopping || !running) return false
        stopping = true
        stopCallerActive = true
        return true
    }

    @Synchronized fun runReturned() {
        check(running)
        running = false
        stopping = true
        completionPending = true
    }

    @Synchronized fun stopReturned() {
        check(stopCallerActive)
        stopCallerActive = false
    }

    /** Called only by the UI completion path. Keeps launches blocked until then. */
    @Synchronized fun takeCompletion(): Boolean {
        if (!completionPending || running || stopCallerActive) return false
        completionPending = false
        stopping = false
        return true
    }
}
