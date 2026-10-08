"""The feature tour: the demo image, the segmentation (bright / dark, size, region) and the refusals."""

import numpy as np
import pytest

pytest.importorskip("scipy")
from labconstrictor_tools import ToolError  # noqa: E402

from labconstrictor_playground.tour import demo_image, segment  # noqa: E402


def test_the_demo_image_is_reproducible_and_has_blobs():
    image = demo_image()
    assert image.shape == (256, 256) and image.dtype == np.uint8
    assert np.array_equal(image, demo_image())
    _, rows = segment(image, 0.5, "bright", 20)
    assert len(rows) == 16 and all(r["area_px"] >= 20 for r in rows)


def test_dark_blobs_and_minimum_size():
    image = demo_image()
    _, dark = segment(image, 0.5, "dark", 20)
    assert len(dark) == 3  # the background pieces
    _, big = segment(image, 0.5, "bright", 200)
    assert 0 < len(big) < 16


def test_a_region_keeps_the_blobs_whose_centre_is_inside():
    image = demo_image()
    region = np.zeros(image.shape, int)
    region[:128] = 1
    labels, rows = segment(image, 0.5, "bright", 20, region)
    assert len(rows) == 11 and all(r["y"] < 128 for r in rows)
    assert sorted(set(labels.flat)) == list(range(0, 12))  # relabelled 1..N, 0 outside


def test_refusals_are_readable():
    image = demo_image()
    with pytest.raises(ToolError, match="No blob found"):
        segment(image, 1.0, "bright", 500)
    with pytest.raises(ToolError, match="flat"):
        segment(np.full((20, 20), 7, np.uint8), 0.5, "bright", 1)
    with pytest.raises(ToolError, match="2D"):
        segment(np.zeros((3, 20, 20)), 0.5, "bright", 1)
    with pytest.raises(ToolError, match="empty"):
        segment(image, 0.5, "bright", 20, np.zeros(image.shape, int))
    with pytest.raises(ToolError, match="size of the image"):
        segment(image, 0.5, "bright", 20, np.ones((10, 10), int))
