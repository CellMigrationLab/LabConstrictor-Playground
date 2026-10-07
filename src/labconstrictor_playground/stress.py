"""Things a tool does that a host must survive: big results, many points, slow runs, cancel, a crash, no memory, a hang."""

from __future__ import annotations

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
    import ctypes

    ctypes.string_at(0)


def out_of_memory() -> None:
    """Ask for more memory than any machine has: a MemoryError that the tool does not catch."""
    import numpy as np

    np.empty(10**13, dtype=np.uint8)


def hang(seconds: float) -> float:
    """Ignore Cancel for `seconds` (the host must stop the worker after its grace period)."""
    started = time.monotonic()
    while time.monotonic() - started < seconds:
        time.sleep(0.2)
    return time.monotonic() - started
