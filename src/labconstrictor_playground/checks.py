"""The checks of this application: the shared probes of labconstrictor-tools plus what only this app knows (what the installer did)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from labconstrictor_tools import diagnostics
from labconstrictor_tools.diagnostics import FAIL, INFO, OK, WARN, Check

INSTALL_LOG = "menuinst_debug.log"


def install_log_probe(prefix: str | Path | None = None) -> list[Check]:
    """What the installer decided about PyTorch (CPU or GPU requirements, and whether it had to fall back), from the install log."""
    log = Path(prefix or sys.prefix) / INSTALL_LOG
    if not log.is_file():
        return [Check("install", "install log", INFO, "no install log at %s (a source checkout or a manual install)" % log)]
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        return [Check("install", "install log", WARN, "cannot read %s: %s" % (log, error))]
    wanted = ("GPU requirements", "CPU requirements", "falling back", "Falling back", "NVIDIA GPU", "macOS detected")
    kept = [line.strip() for line in lines if any(word in line for word in wanted)]
    checks = [Check("install", "install log", INFO, "; ".join(kept[-4:]) if kept else "no requirement choice recorded in %s" % log)]
    if any("alling back" in line for line in kept):
        checks.append(
            Check(
                "install", "GPU requirements", WARN, "the GPU build of PyTorch could not be installed, the CPU build was used instead",
                "Check the install log for the pip error (often the network, a proxy or a missing driver), then reinstall: GPU runs need the CUDA build.",
            )
        )
    return checks


def check_everything(*, benchmark: bool = True, network: bool = False) -> list[Check]:
    return diagnostics.run_checks(benchmark=benchmark, network=network, extra=[install_log_probe])


def benchmark_figure(checks: list[Check], path: Path) -> Path | None:
    """A bar chart of the benchmark (milliseconds per device); None when there is nothing to draw or no matplotlib."""
    times = diagnostics.benchmark_timings(checks)
    if not times:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure
    except ImportError:
        return None
    figure = Figure(figsize=(max(3.5, 1.4 * len(times)), 3.2))
    axes = figure.subplots()
    axes.bar(list(times), list(times.values()), color=["#1f4e79" if k == "cpu" else "#2e8b57" for k in times])
    axes.set_ylabel("milliseconds per run (lower is faster)")
    axes.set_title("Same convolution and matrix product on each device")
    for index, value in enumerate(times.values()):
        axes.text(index, value, "%.1f" % value, ha="center", va="bottom", fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=130)
    return path


def write_report(checks: list[Check], folder: str | Path) -> dict[str, Path]:
    """report.json (attach it to an issue), summary.txt and, when there is a benchmark, benchmark.png, in a time-stamped folder."""
    folder = Path(folder) / time.strftime("check_%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    files = {"json": folder / "report.json", "summary": folder / "summary.txt"}
    files["json"].write_text(diagnostics.as_json(checks), encoding="utf-8")
    files["summary"].write_text(diagnostics.summary(checks), encoding="utf-8")
    figure = benchmark_figure(checks, folder / "benchmark.png")
    if figure is not None:
        files["figure"] = figure
    return files
