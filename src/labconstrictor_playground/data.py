"""Test data every host can open: a few small files made from a seed, so that a result can be compared across machines."""

from __future__ import annotations

from pathlib import Path

KINDS = ("three_channels", "rgb", "labels", "timelapse", "points", "all")


def _blobs(shape, count, radius, rng):
    import numpy as np

    yy, xx = np.mgrid[: shape[0], : shape[1]]
    image = np.zeros(shape, np.float32)
    centres = []
    for _ in range(count):
        cy, cx = rng.uniform(radius, shape[0] - radius), rng.uniform(radius, shape[1] - radius)
        image += np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * (radius / 2) ** 2)))
        centres.append((cy, cx))
    return image, centres


def make_test_data(folder: str | Path, kind: str = "all", size: int = 256, seed: int = 0) -> dict[str, Path]:
    """Write the test files into `folder` (made if needed) and return {name: path}. Existing files are replaced."""
    import numpy as np
    import tifffile

    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    if not 32 <= size <= 4096:
        raise ValueError("size must be between 32 and 4096 pixels")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    out: dict[str, Path] = {}
    wanted = KINDS[:-1] if kind == "all" else (kind,)
    radius = max(6, size // 16)
    blobs, centres = _blobs((size, size), 12, radius, rng)
    if "three_channels" in wanted:
        # channel k has a different mean (10, 20, 30 plus the nuclei in channel 1): a tool that gets the wrong channel is caught
        stack = np.zeros((3, size, size), np.uint16)
        stack[0] = 10 + 200 * blobs
        stack[1] = 20
        stack[2] = 30
        out["three_channels"] = folder / "three_channels.tif"
        tifffile.imwrite(out["three_channels"], stack, imagej=True, metadata={"axes": "CYX"})
    if "rgb" in wanted:
        colour = np.zeros((size, size, 3), np.uint8)
        colour[..., 0], colour[..., 1], colour[..., 2] = 10, 20, 30
        colour[..., 0] = np.clip(10 + 200 * blobs, 0, 255)
        out["rgb"] = folder / "rgb.tif"
        tifffile.imwrite(out["rgb"], colour, photometric="rgb")
    if "labels" in wanted:
        from scipy.ndimage import label

        labels, count = label(blobs > 0.35)
        out["labels"] = folder / "labels.tif"
        tifffile.imwrite(out["labels"], labels.astype(np.uint16))
    if "timelapse" in wanted:
        frames = np.stack([_blobs((size, size), 1, radius, np.random.default_rng(seed + t))[0] for t in range(8)])
        out["timelapse"] = folder / "timelapse.tif"
        tifffile.imwrite(out["timelapse"], (255 * frames).astype(np.uint8), imagej=True, metadata={"axes": "TYX"})
    if "points" in wanted:
        out["points"] = folder / "points.csv"
        with open(out["points"], "w", encoding="utf-8", newline="") as handle:
            handle.write("y,x,label\n")
            for index, (cy, cx) in enumerate(centres):
                handle.write("%.2f,%.2f,%d\n" % (cy, cx, index + 1))
    return out
