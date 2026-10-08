"""LabConstrictor Playground tools for Napari, Fiji, QuPath and the command line.

This module only *declares* the tools: it imports `labconstrictor_tools` and the standard library at the top, and numpy, PyTorch and the
checks inside the functions, so that listing the tools stays instant (`import torch` alone takes seconds).

    labconstrictor-tools check --module labconstrictor_playground_lc_tools
    labconstrictor-tools test  --module labconstrictor_playground_lc_tools --cases lc_tests/cases.json
"""

from pathlib import Path
from typing import Annotated, Literal, Optional

from labconstrictor_tools import (
    Advanced,
    ApplyTo,
    Axes,
    ChoicesFrom,
    ClearAfterRun,
    Collapsed,
    Description,
    FileOut,
    Folder,
    Group,
    Image,
    ImageOut,
    Label,
    Labels,
    LabelsOut,
    Max,
    MessageOut,
    Min,
    Name,
    PickChannel,
    PointsOut,
    RegionOf,
    Replace,
    Scalars,
    ShapesOut,
    TableOut,
    ToolError,
    Unit,
    Widget,
    check_cancel,
    progress,
    tool,
)

REPORTS = "LabConstrictorPlayground" + "/reports"  # inside the user's home folder


# ------------------------------------------------------------------------------------------------ checks
@tool("Check everything")
def check_everything(
    run_benchmark: Annotated[bool, Group("Checks"), Label("Run the speed test"), Description("Times a small convolution and matrix product on the CPU and on every GPU found, and checks that they agree")] = True,
    check_internet: Annotated[bool, Group("Checks"), Description("Also try to reach pypi.org, huggingface.co and github.com (needed to download models and packages)")] = False,
) -> tuple[
    Annotated[MessageOut, Name("readout")],
    Annotated[TableOut, Name("details")],
    Annotated[FileOut, Name("report")],
]:
    """Tests the machine, the worker and the GPU libraries; every failure comes with what to do. Attach report.json to an issue."""
    from labconstrictor_playground import checks as c

    progress(0.1, "looking at the machine and the GPU tools")
    found = c.check_everything(benchmark=run_benchmark, network=check_internet)
    progress(0.8, "writing the report")
    files = c.write_report(found, Path.home() / REPORTS)
    from labconstrictor_tools import diagnostics

    text = diagnostics.summary(found) + "\n\nReport saved in %s (attach report.json to an issue)." % files["json"].parent
    return text, diagnostics.rows(found), files["json"]


@tool("List the devices")
def list_devices() -> Scalars:
    """The devices a PyTorch tool can use here (cpu, cuda:0, mps). The `choices` feed the device dropdown of other tools."""
    from labconstrictor_tools import diagnostics

    names = diagnostics.torch_devices() or ["cpu"]
    return {"choices": names, "devices": ", ".join(names), "pytorch": "installed" if diagnostics.torch_devices() else "not installed"}


@tool("Run a small test on a device")
def run_on_device(
    device: Annotated[str, Group("Test"), ChoicesFrom("list_devices"), Description("cpu, a GPU (cuda:0, ...) or Apple's mps")] = "cpu",
    size: Annotated[int, Group("Test"), Min(64), Max(4096), Description("Side of the square test image")] = 1024,
    repeats: Annotated[int, Group("Test"), Min(1), Max(200), Advanced()] = 10,
) -> tuple[Annotated[MessageOut, Name("result")], Scalars]:
    """Runs the same convolution and matrix product on the chosen device and reports the time (shows the device dropdown and real GPU use)."""
    from labconstrictor_tools import diagnostics

    if device not in (diagnostics.torch_devices() or ["cpu"]):
        raise ToolError("unknown_device", "'%s' is not available here: %s." % (device, ", ".join(diagnostics.torch_devices() or ["cpu (PyTorch is not installed)"])))
    try:
        import torch
    except ImportError as error:
        raise ToolError("no_pytorch", "PyTorch is not installed in this application, so there is only the CPU test of 'Check everything'.") from error
    import time

    generator = torch.Generator().manual_seed(0)
    image = torch.rand(1, 1, size, size, generator=generator).to(device)
    kernel = torch.rand(8, 1, 5, 5, generator=generator).to(device)
    matrix = torch.rand(size, size, generator=generator).to(device)

    def work():
        return torch.nn.functional.conv2d(image, kernel, padding=2).sum() + (matrix @ matrix).sum()

    work()
    started = time.perf_counter()
    for index in range(repeats):
        check_cancel()
        progress((index + 1) / repeats, "run %d of %d on %s" % (index + 1, repeats, device))
        value = work()
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    seconds = (time.perf_counter() - started) / repeats
    return "**%s**: %.1f ms per run (%dx%d)" % (device, seconds * 1000, size, size), {"device": device, "ms_per_run": round(seconds * 1000, 2), "result": round(float(value.cpu()), 3)}


# ------------------------------------------------------------------------------------------------ test data
@tool("Make test data")
def make_test_data(
    folder: Annotated[Folder, Group("Data"), Description("An existing folder to write the files into")],
    kind: Annotated[Literal["all", "three_channels", "rgb", "labels", "timelapse", "points"], Group("Data")] = "all",
    size: Annotated[int, Group("Data"), Min(32), Max(4096), Description("Side of the images in pixels")] = 256,
) -> tuple[Annotated[MessageOut, Name("files")], Scalars]:
    """Writes small test files (a 3-channel image whose channels have the means 10, 20 and 30, an RGB image, labels, a time-lapse, points)."""
    from labconstrictor_playground import make_test_data as make

    written = make(folder, kind, size)
    names = "\n".join("- %s: %s" % (name, path) for name, path in written.items())
    return "Wrote %d file(s) into %s:\n%s" % (len(written), folder, names), {"folder": str(folder), "files": ", ".join(p.name for p in written.values())}


# ------------------------------------------------------------------------------------------------ the feature tour
@tool("Feature tour")
def feature_tour(
    image: Annotated[
        Optional[Image], Axes("YX"), PickChannel(), Group("Image"),
        Description("A 2D image (pick its channel in the host). Leave it unset to use a built-in demo image with round blobs, rings (a hole) and blobs in two parts"),
    ] = None,
    region: Annotated[
        Optional[Labels], Axes("YX"), RegionOf("image"), Group("Image"),
        Description("Only keep the blobs whose centre is inside this region: the host fills it from the selection (a Shapes layer, a ROI, annotations)"),
    ] = None,
    look_for: Annotated[Literal["bright", "dark"], Widget("radio"), Group("Segmentation"), Description("Blobs brighter or darker than the background")] = "bright",
    threshold: Annotated[float, Min(0), Max(1), Widget("slider"), Group("Segmentation"), Description("Fraction of the intensity range that separates blobs from background")] = 0.5,
    min_size_px: Annotated[int, Min(1), Max(500), Widget("slider"), Unit("px"), Label("Minimum size"), Group("Segmentation"), Description("Blobs with fewer pixels are removed")] = 20,
    side_note: Annotated[
        Optional[str], Group("Extras"), Collapsed(), ClearAfterRun(),
        Description("A free text shown in the summary. This group starts folded, and the box empties itself after a run"),
    ] = None,
) -> tuple[
    Annotated[LabelsOut, Name("blobs"), ApplyTo("image"), Replace()],
    Annotated[ShapesOut, Name("outlines"), ApplyTo("image"), Replace()],
    Annotated[PointsOut, Name("centres"), ApplyTo("image"), Replace()],
    Annotated[TableOut, Name("measurements"), Replace()],
    Annotated[MessageOut, Name("summary")],
]:
    """Label the blobs of an image and return them in every form a host can show: labels, outlines, points, a table and a message."""
    import pandas as pd
    from labconstrictor_playground.tour import demo_image, segment
    from labconstrictor_tools.shapes import labels_to_shapes

    progress(0.1, "preparing the image" if image is not None else "making the demo image")
    source = image if image is not None else demo_image()
    check_cancel()
    labels, rows = segment(source, threshold, look_for, min_size_px, region)
    progress(0.7, "outlining %d blob(s)" % len(rows))
    table = pd.DataFrame(rows)
    text = "Found **%d** blob(s)%s." % (len(rows), " inside the region" if region is not None else "")
    if image is None:
        text += " (the built-in demo image)"
    if side_note:
        text += "\n\n> " + side_note.replace("\n", " ")
    return labels, labels_to_shapes(labels), table[["y", "x", "label", "area_px"]], table, text


# ------------------------------------------------------------------------------------------------ stress (what a host must survive)
@tool("Stress: a big image")
def stress_big_image(
    megabytes: Annotated[int, Min(1), Max(2000), Description("About how large the result image is")] = 200,
) -> Annotated[ImageOut, Name("big"), Replace()]:
    """Returns a large 16-bit image: the host must show it or say clearly that it is too big, never freeze."""
    from labconstrictor_playground import stress

    progress(0.2, "making the image")
    return stress.big_image(megabytes)


@tool("Stress: many points")
def stress_many_points(
    count: Annotated[int, Min(1), Max(2_000_000), Description("Number of points")] = 200_000,
) -> Annotated[PointsOut, Name("points"), Replace()]:
    """Returns many points (y, x, score): layers and tables with that many rows must stay usable."""
    from labconstrictor_playground import stress

    return stress.many_points(count)


@tool("Stress: slow run with progress")
def stress_slow(
    seconds: Annotated[float, Min(1), Max(600), Description("How long to work; press Cancel to stop earlier")] = 20.0,
) -> Scalars:
    """Works for a while, reporting progress, and stops when Cancel is pressed (the progress bar and Cancel must respond)."""
    from labconstrictor_playground import stress

    worked = stress.slow(seconds, progress, check_cancel)
    return {"worked_seconds": round(worked, 1)}


@tool("Stress: crash the worker")
def stress_crash() -> Scalars:
    """Kills the worker with a real segmentation fault (what a native library does when it fails): the host must say so and recover."""
    from labconstrictor_playground import stress

    progress(0.5, "about to crash on purpose (a real segmentation fault)")
    stress.crash()
    return {}


@tool("Stress: out of memory")
def stress_out_of_memory() -> Scalars:
    """Asks for far more memory than exists: the host must show a clear failure, and the worker must stay usable."""
    from labconstrictor_playground import stress

    progress(0.5, "asking for 10 TB on purpose")
    stress.out_of_memory()
    return {}


@tool("Stress: a tool that ignores Cancel")
def stress_hang(
    seconds: Annotated[float, Min(1), Max(600), Description("How long it ignores everything")] = 60.0,
) -> Scalars:
    """Ignores Cancel for a while: the host must stop the worker after its grace period and leave no process behind."""
    from labconstrictor_playground import stress

    progress(0.1, "ignoring Cancel for %.0f s" % seconds)
    return {"ignored_seconds": round(stress.hang(seconds), 1)}
