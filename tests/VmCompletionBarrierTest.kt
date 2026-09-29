package com.armsx2.runtime

import org.junit.Assert.*
import org.junit.Test

class VmCompletionBarrierTest {
    @Test fun shutdownReturnIsNotRunLoopCompletion() {
        val gate = VmCompletionBarrier()
        gate.beginRun()
        assertTrue(gate.requestStop())
        gate.stopReturned() // Also models native shutdown's five-second timeout.
        assertFalse(gate.takeCompletion())
        assertTrue(gate.stopping)
        gate.runReturned()
        assertTrue(gate.takeCompletion())
        assertFalse(gate.takeCompletion())
        gate.beginRun()
    }

    @Test fun runReturnDoesNotRaceOutstandingShutdownCaller() {
        val gate = VmCompletionBarrier()
        gate.beginRun()
        assertTrue(gate.requestStop())
        gate.runReturned()
        assertFalse(gate.takeCompletion())
        assertFalse(gate.requestStop())
        try {
            gate.beginRun()
            fail("Must not launch before the shutdown caller returns")
        } catch (_: IllegalStateException) { }
        gate.stopReturned()
        assertTrue(gate.takeCompletion())
        gate.beginRun()
    }

    @Test fun duplicateCloseQueuesOnlyOneShutdown() {
        val gate = VmCompletionBarrier()
        assertFalse(gate.requestStop())
        gate.beginRun()
        assertTrue(gate.requestStop())
        repeat(20) { assertFalse(gate.requestStop()) }
        gate.stopReturned()
        gate.runReturned()
        assertTrue(gate.takeCompletion())
    }

    @Test fun failedBootOrNaturalExitCompletesOnceWithoutShutdownCaller() {
        val gate = VmCompletionBarrier()
        repeat(10) {
            gate.beginRun()
            gate.runReturned()
            assertTrue(gate.stopping)
            assertFalse(gate.requestStop())
            assertTrue(gate.takeCompletion())
            assertFalse(gate.takeCompletion())
        }
    }

    @Test fun concurrentReturnsNeverPublishTwice() {
        repeat(100) {
            val gate = VmCompletionBarrier()
            gate.beginRun()
            assertTrue(gate.requestStop())
            val completed = java.util.concurrent.atomic.AtomicInteger()
            val a = Thread { gate.runReturned(); if (gate.takeCompletion()) completed.incrementAndGet() }
            val b = Thread { gate.stopReturned(); if (gate.takeCompletion()) completed.incrementAndGet() }
            a.start(); b.start(); a.join(); b.join()
            assertEquals(1, completed.get())
            assertFalse(gate.stopping)
        }
    }
}
