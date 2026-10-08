"""The feature tour: a small segmentation that uses every control and output of the tools bridge (see `feature_tour` in the tools)."""

from __future__ import annotations

from typing import Any

from labconstrictor_tools import ToolError

DEMO_SIZE = 256


def demo_image(seed: int = 0):
    """A 256 x 256 uint8 image of bright blobs on a dark background: some round, some with a hole (rings), some in two parts."""
    import numpy as np

    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:DEMO_SIZE, :DEMO_SIZE]
    image = np.zeros((DEMO_SIZE, DEMO_SIZE), np.float32)
    for _ in range(14):  # plain blobs
        cy, cx = rng.integers(20, DEMO_SIZE - 20, 2)
        radius = rng.integers(5, 11)
        image[(yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2] = 200 + rng.integers(0, 55)
    for cy, cx in ((60, 60), (190, 120)):  # two rings: a nucleus with a hole
        distance = (yy - cy) ** 2 + (xx - cx) ** 2
        image[distance <= 14**2] = 255
        image[distance <= 6**2] = 0
    image += rng.normal(0, 4, image.shape)
    return np.clip(image, 0, 255).astype(np.uint8)


def segment(image: Any, threshold: float, look_for: str, min_size_px: int, region: Any = None):
    """Label the blobs of a 2D image: pixels above `threshold` (a fraction of the range; below it for dark blobs), objects smaller
    than `min_size_px` removed, and, with a `region`, only the blobs whose centre lies inside it. Returns (labels, table rows)."""
    import numpy as np
    from scipy import ndimage

    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2:
        raise ToolError("bad_input", "The feature tour needs a 2D image; got %d dimensions" % array.ndim)
    low, high = float(array.min()), float(array.max())
    if high == low:
        raise ToolError("no_result", "The image is flat (every pixel has the value %g): there is nothing to find." % low)
    scaled = (array - low) / (high - low)
    mask = scaled <= (1 - threshold) if look_for == "dark" else scaled >= threshold
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, index=np.arange(1, count + 1))
    keep = np.flatnonzero(sizes >= min_size_px) + 1
    centres = ndimage.center_of_mass(mask, labels, keep) if len(keep) else []
    if region is not None:
        from labconstrictor_tools.region import bbox

        bbox(region, array)  # the right size, and not empty
        inside = np.asarray(region) > 0
        keep_inside = [i for i, (cy, cx) in zip(keep, centres) if inside[int(round(cy)), int(round(cx))]]
        centres = [c for i, c in zip(keep, centres) if i in set(keep_inside)]
        keep = np.asarray(keep_inside, dtype=int)
    if len(keep) == 0:
        raise ToolError("no_result", "No blob found (threshold %.2f, at least %d pixels%s): lower the threshold or the minimum size." % (threshold, min_size_px, ", inside the region" if region is not None else ""))
    out = np.zeros(labels.shape, np.int32)
    rows = []
    for new, (old, (cy, cx)) in enumerate(zip(keep, centres), start=1):
        out[labels == old] = new
        rows.append({"label": new, "y": float(cy), "x": float(cx), "area_px": int((labels == old).sum()), "mean_intensity": float(array[labels == old].mean())})
    return out, rows
