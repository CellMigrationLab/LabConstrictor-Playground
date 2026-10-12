"""Timing of asynchronous devices: GPU work is queued, so the clock is only meaningful after the queue has drained."""

from __future__ import annotations

import time
from typing import Any, Callable


def synchronize(torch: Any, device: str) -> None:
    """Wait until the work queued on `device` has finished (CUDA and Apple MPS are asynchronous; the CPU is not)."""
    name = str(device)
    if name.startswith("cuda"):
        torch.cuda.synchronize()
    elif name.startswith("mps"):
        torch.mps.synchronize()


def time_device(torch: Any, device: str, work: Callable[[], Any], repeats: int, each: Callable[[int], None] | None = None) -> tuple[float, Any]:
    """Seconds per call of `work` on `device` and the last value: warm up, synchronize, start the clock, run, synchronize, stop it.

    `each(index)` runs before every timed call (progress and Cancel); it must stay cheap.
    """
    work()  # warm-up (kernels are compiled on first use)
    synchronize(torch, device)  # the warm-up must not leak into the timed section
    started = time.perf_counter()
    value = None
    for index in range(repeats):
        if each is not None:
            each(index)
        value = work()
    synchronize(torch, device)  # the timed calls must have completed, not only been queued
    return (time.perf_counter() - started) / repeats, value
