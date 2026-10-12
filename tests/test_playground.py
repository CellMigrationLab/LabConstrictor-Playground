"""The playground package and its tools: checks, test data, stress functions, and the light import of the declarations."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("labconstrictor_tools")

import numpy as np  # noqa: E402

from labconstrictor_playground import checks, data, stress  # noqa: E402


def test_the_declarations_stay_light_and_are_valid():
    code = (
        "import sys, labconstrictor_playground_lc_tools\n"
        "heavy = [m for m in ('torch', 'numpy', 'pandas', 'scipy', 'matplotlib', 'tifffile') if m in sys.modules]\n"
        "assert not heavy, heavy\n"
        "from labconstrictor_tools.introspection import describe_tools\n"
        "ids = sorted(t['id'] for t in describe_tools('labconstrictor_playground_lc_tools')['tools'])\n"
        "print(' '.join(ids))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src") + ":" + ":".join(sys.path)})
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == sorted(
        ["check_everything", "feature_tour", "list_devices", "make_test_data", "run_on_device", "stress_big_image", "stress_crash", "stress_hang", "stress_many_points", "stress_out_of_memory", "stress_real_memory", "stress_slow"]
    )


def test_check_everything_without_pytorch_is_clean_information(monkeypatch):
    from labconstrictor_tools import diagnostics

    monkeypatch.setattr(diagnostics, "_torch_module", lambda: None)
    found = checks.check_everything(benchmark=True)
    assert not [c for c in found if c.status == diagnostics.FAIL and c.layer != "install"], [c for c in found if c.status == "fail"]
    assert any(c.name == "PyTorch" for c in found) or any(c.layer == "gpu libraries" for c in found)


def test_report_files_are_written_and_json_parses(tmp_path):
    found = checks.check_everything(benchmark=False)
    files = checks.write_report(found, tmp_path)
    report = json.loads(files["json"].read_text(encoding="utf-8"))
    assert len(report["checks"]) == len(found)
    assert "checks:" in files["summary"].read_text(encoding="utf-8")


def test_install_log_records_a_fallback_as_a_warning(tmp_path):
    (tmp_path / "menuinst_debug.log").write_text(
        "NVIDIA GPU detected, installing GPU requirements from x\nWARNING: installing the GPU requirements failed; falling back to the CPU requirements from y\n", encoding="utf-8"
    )
    found = checks.install_log_probe(tmp_path)
    assert any(c.name == "GPU requirements" and c.status == "warn" for c in found)


def test_install_log_missing_is_information(tmp_path):
    assert [c.status for c in checks.install_log_probe(tmp_path)] == ["info"]


def test_test_data_has_the_documented_channel_means(tmp_path):
    import tifffile

    written = data.make_test_data(tmp_path, "all", size=64)
    assert set(written) == {"three_channels", "rgb", "labels", "timelapse", "points"}
    three = tifffile.imread(written["three_channels"])
    assert three.shape == (3, 64, 64) and three[1].mean() == 20 and three[2].mean() == 30
    rgb = tifffile.imread(written["rgb"])
    assert rgb.shape == (64, 64, 3) and rgb[..., 1].mean() == 20 and rgb[..., 2].mean() == 30
    labels = tifffile.imread(written["labels"])
    assert labels.max() >= 1 and labels.dtype == np.uint16
    assert tifffile.imread(written["timelapse"]).shape == (8, 64, 64)
    assert written["points"].read_text().splitlines()[0] == "y,x,label"


def test_test_data_is_reproducible_and_checks_its_arguments(tmp_path):
    a = data.make_test_data(tmp_path / "a", "labels", size=64)["labels"].read_bytes()
    b = data.make_test_data(tmp_path / "b", "labels", size=64)["labels"].read_bytes()
    assert a == b
    with pytest.raises(ValueError):
        data.make_test_data(tmp_path, "nonsense")
    with pytest.raises(ValueError):
        data.make_test_data(tmp_path, "labels", size=8)


def test_stress_functions():
    assert stress.big_image(2).dtype == np.uint16
    assert abs(stress.big_image(2).nbytes - 2 * 1024 * 1024) < 4096
    frame = stress.many_points(1000)
    assert list(frame.columns) == ["y", "x", "score"] and len(frame) == 1000
    seen = []
    assert stress.slow(0.6, lambda f, m: seen.append(f), lambda: None) >= 0.6 and seen


def test_slow_stops_when_cancel_raises():
    class Stop(Exception):
        pass

    def cancelled():
        raise Stop()

    with pytest.raises(Stop):
        stress.slow(5, lambda f, m: None, cancelled)


class _FakeTorch:
    """Records every synchronize call and every unit of work, in order, so the order around the timer can be asserted."""

    def __init__(self, events):
        self.cuda = type("cuda", (), {"synchronize": staticmethod(lambda: events.append("sync:cuda"))})
        self.mps = type("mps", (), {"synchronize": staticmethod(lambda: events.append("sync:mps"))})


def test_mps_is_synchronized_after_warm_up_and_before_stopping_the_clock(monkeypatch):
    from labconstrictor_playground import timing

    events = []
    clock = iter([100.0, 102.0])
    monkeypatch.setattr(timing.time, "perf_counter", lambda: events.append("clock") or next(clock))
    seconds, value = timing.time_device(_FakeTorch(events), "mps", lambda: events.append("work") or "v", 2)
    assert events == ["work", "sync:mps", "clock", "work", "work", "sync:mps", "clock"]
    assert seconds == 1.0 and value == "v"


def test_cuda_is_synchronized_at_both_boundaries_and_the_cpu_is_not():
    from labconstrictor_playground import timing

    events = []
    timing.time_device(_FakeTorch(events), "cuda:0", lambda: None, 1)
    assert events == ["sync:cuda", "sync:cuda"]
    events.clear()
    timing.time_device(_FakeTorch(events), "cpu", lambda: None, 1)
    assert events == []



def test_simulated_out_of_memory_is_deterministic_labelled_and_allocates_nothing(monkeypatch):
    import tracemalloc

    monkeypatch.setattr(np, "empty", lambda *a, **k: pytest.fail("the simulated case must not allocate through numpy"))
    tracemalloc.start()
    try:
        for _ in range(2):  # the same every time
            with pytest.raises(MemoryError, match="SIMULATED") as caught:
                stress.out_of_memory()
            assert str(caught.value) == stress.SIMULATED_MEMORY_MESSAGE
        assert tracemalloc.get_traced_memory()[1] < 1024 * 1024
    finally:
        tracemalloc.stop()


def test_the_declared_simulated_tool_reports_a_memory_error():
    import labconstrictor_playground_lc_tools as tools

    run = getattr(tools.stress_out_of_memory, "__wrapped__", tools.stress_out_of_memory)
    with pytest.raises(MemoryError, match="SIMULATED"):
        run()


def test_the_real_memory_test_is_bounded_before_anything_runs():
    assert stress.real_memory_limit(10**9) == stress.REAL_MEMORY_MAX_MB <= 512
    assert stress.real_memory_limit(-5) == 8


def test_real_memory_pressure_uses_a_bounded_child_process(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["timeout"] = cmd, kwargs["timeout"]
        return subprocess.CompletedProcess(cmd, 0, stdout="memory_error 16 address space limited\n", stderr="")

    monkeypatch.setattr(stress.subprocess, "run", fake_run)
    result = stress.real_memory_pressure(10**9, 10**9, timeout=5)
    assert result == {"outcome": "memory_error", "allocated_mb": 16, "detail": "address space limited"}
    assert seen["cmd"][0] == sys.executable and seen["cmd"][-3:-1] == [str(stress.REAL_MEMORY_MAX_MB)] * 2 and seen["timeout"] == 5
    monkeypatch.setattr(stress.subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, -9, stdout="", stderr="Killed"))
    assert stress.real_memory_pressure()["outcome"].startswith("child_ended_abruptly")


@pytest.mark.skipif(os.environ.get("PLAYGROUND_REAL_MEMORY_TEST") != "1", reason="opt-in: set PLAYGROUND_REAL_MEMORY_TEST=1 (really uses up to 64 MB in a child process)")
def test_real_memory_pressure_for_real_opt_in():
    result = stress.real_memory_pressure(target_mb=64, limit_mb=32, timeout=60)
    assert result["outcome"] in {"memory_error", "completed"}, result
    assert 0 <= result["allocated_mb"] <= 64
