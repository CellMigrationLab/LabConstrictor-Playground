"""Things a tool does that a host must survive: big results, many points, slow runs, cancel, a crash, no memory (simulated, plus an opt-in bounded real test), a hang."""

from __future__ import annotations

import subprocess
import sys
import time


def big_image(megabytes: int):
    """A 16-bit image of about `megabytes` (the host must show or refuse it, not freeze or crash)."""
    import numpy as np

    pixels = max(1, int(megabytes * 1024 * 1024 / 2))
    side = int(pixels**0.5)
    rng = np.random.default_rng(0)
    return rng.integers(0, 65535, size=(side, side), dtype=np.uint16)


def many_points(count: int):
    """`count` random points (y, x, score)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    return pd.DataFrame({"y": rng.uniform(0, 4000, count), "x": rng.uniform(0, 4000, count), "score": rng.random(count)})


def slow(seconds: float, step, cancelled) -> float:
    """Work for `seconds`, reporting progress every half second and stopping politely when Cancel is pressed. Returns the seconds worked."""
    started = time.monotonic()
    while True:
        done = time.monotonic() - started
        if done >= seconds:
            return done
        step(min(1.0, done / seconds), "working: %.0f of %.0f s" % (done, seconds))
        cancelled()
        time.sleep(0.5)


def crash() -> None:
    """Kill the process the way a native library does: a real segmentation fault (an access violation on Windows), not an exception and not a
    chosen exit code (hosts read the exit code to say what happened, so a made-up one would be misleading)."""
    import faulthandler

    if hasattr(faulthandler, "_sigsegv"):  # a real fault on every platform; ctypes.string_at(0) only raises OSError on Windows
        faulthandler._sigsegv()
    import ctypes

    ctypes.string_at(0)


SIMULATED_MEMORY_MESSAGE = "SIMULATED out of memory (stress test): no memory was requested, this MemoryError is raised on purpose"

REAL_MEMORY_MAX_MB = 512  # the hard ceiling of the opt-in real test, whatever is asked for
_CHUNK_MB = 8

# Runs in a child process, never in the worker: allocate and touch real memory in small chunks up to a cap. On Linux the address space of the
# child is limited to what it already uses plus `limit_mb`, so asking for more than that ends in a genuine MemoryError of the child.
_CHILD = """
import sys
target_mb, limit_mb, chunk_mb = (int(v) for v in sys.argv[1:4])
try:
    import resource
    with open('/proc/self/statm') as f:
        base = int(f.read().split()[0]) * resource.getpagesize()
    cap = base + limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    limited = 'address space limited to %d MB above the start' % limit_mb
except Exception:
    limited = 'no operating-system limit available here (the allocation is only capped at %d MB)' % target_mb
held, done = [], 0
try:
    while done < target_mb:
        held.append(b'\\x01' * (chunk_mb * 1024 * 1024))
        done += chunk_mb
    print('completed', done, limited)
except MemoryError:
    print('memory_error', done, limited)
"""


def real_memory_limit(requested_mb: int) -> int:
    """The size, in MB, the real memory test is allowed to use: at least one chunk, never more than REAL_MEMORY_MAX_MB."""
    return max(_CHUNK_MB, min(int(requested_mb), REAL_MEMORY_MAX_MB))


def real_memory_pressure(target_mb: int = 128, limit_mb: int = 64, timeout: float = 60.0) -> dict:
    """REAL but bounded memory pressure, in a separate child process (the worker is never at risk): the child touches `target_mb` of memory
    (at most REAL_MEMORY_MAX_MB) in small chunks. On Linux its address space is capped at `limit_mb` above its start, so a target above the cap
    ends in a genuine MemoryError of the child; elsewhere the child only allocates up to the target. Returns what happened."""
    target, limit = real_memory_limit(target_mb), real_memory_limit(limit_mb)
    done = subprocess.run([sys.executable, "-I", "-c", _CHILD, str(target), str(limit), str(_CHUNK_MB)], capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        # an operating-system kill (or any other abrupt end): report it, do not pretend it was a MemoryError
        return {"outcome": "child_ended_abruptly (exit code %s)" % done.returncode, "allocated_mb": 0, "detail": done.stderr.strip()[-300:]}
    outcome, allocated, detail = done.stdout.split(" ", 2)
    return {"outcome": outcome, "allocated_mb": int(allocated), "detail": detail.strip()}


def out_of_memory() -> None:
    """SIMULATED, deterministic and safe on every operating system: raise a clearly labelled MemoryError without asking for any memory, so that
    the worker's reporting of an uncaught MemoryError (a FAILED result with the code MemoryError) can be checked. It is not a real exhaustion;
    `real_memory_pressure` is the real, bounded and opt-in counterpart."""
    raise MemoryError(SIMULATED_MEMORY_MESSAGE)


def hang(seconds: float) -> float:
    """Ignore Cancel for `seconds` (the host must stop the worker after its grace period)."""
    started = time.monotonic()
    while time.monotonic() - started < seconds:
        time.sleep(0.2)
    return time.monotonic() - started
