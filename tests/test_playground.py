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


def _child_env():
    """The current environment (PATH, SystemRoot, ...) with the local `src` first on PYTHONPATH, joined with the platform separator."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def test_child_environment_keeps_the_parent_environment_and_puts_src_first(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(["elsewhere", "other"]))
    monkeypatch.setenv("PLAYGROUND_MARKER", "kept")
    env = _child_env()
    assert env["PYTHONPATH"].split(os.pathsep) == [str(ROOT / "src"), "elsewhere", "other"]
    assert env["PLAYGROUND_MARKER"] == "kept" and env.get("PATH") == os.environ.get("PATH")
    monkeypatch.delenv("PYTHONPATH")
    assert _child_env()["PYTHONPATH"] == str(ROOT / "src")


def test_the_declarations_stay_light_and_are_valid():
    code = (
        "import sys, labconstrictor_playground_lc_tools\n"
        "heavy = [m for m in ('torch', 'numpy', 'pandas', 'scipy', 'matplotlib', 'tifffile') if m in sys.modules]\n"
        "assert not heavy, heavy\n"
        "from labconstrictor_tools.introspection import describe_tools\n"
        "ids = sorted(t['id'] for t in describe_tools('labconstrictor_playground_lc_tools')['tools'])\n"
        "print(' '.join(ids))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=_child_env())
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == sorted(
        ["align_centres", "bright_area", "check_everything", "count_above_level", "feature_tour", "list_devices", "look_inside_file", "make_test_data", "run_on_device", "stress_big_image", "stress_crash", "stress_hang", "stress_many_points", "stress_out_of_memory", "stress_real_memory", "stress_slow", "summarise_table"]
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


def test_two_reports_in_the_same_second_are_both_kept(tmp_path, monkeypatch):
    from labconstrictor_tools.diagnostics import Check

    monkeypatch.setattr(checks.time, "strftime", lambda fmt: "check_20260101_120000")  # a frozen clock
    drawn = []

    def figure(found, path):
        if not any(c.layer == "benchmark" for c in found):
            return None
        path.write_bytes(b"png")
        drawn.append(path)
        return path

    monkeypatch.setattr(checks, "benchmark_figure", figure)
    first = [Check("machine", "RAM", "ok", "first run"), Check("benchmark", "cpu", "info", "1.0 ms")]
    second = [Check("machine", "RAM", "warn", "second run")]
    one = checks.write_report(first, tmp_path)
    two = checks.write_report(second, tmp_path)
    assert one["json"].parent != two["json"].parent
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 2
    assert all(p.parent.name.startswith("check_20260101_120000") for p in (one["json"], two["json"]))
    assert json.loads(one["json"].read_text(encoding="utf-8"))["checks"][0]["detail"] == "first run"
    assert json.loads(two["json"].read_text(encoding="utf-8"))["checks"][0]["detail"] == "second run"
    assert "figure" in one and drawn == [one["figure"]]
    assert "figure" not in two and not (two["json"].parent / "benchmark.png").exists()


def test_a_taken_report_folder_is_never_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(checks.time, "strftime", lambda fmt: "check_20260101_120000")
    suffixes = iter(["aaaaaaaa", "aaaaaaaa", "bbbbbbbb"])
    monkeypatch.setattr(checks.uuid, "uuid4", lambda: type("U", (), {"hex": next(suffixes) + "0" * 24})())
    first = checks.new_report_folder(tmp_path)
    (first / "report.json").write_text("keep me", encoding="utf-8")
    second = checks.new_report_folder(tmp_path)  # the same suffix is drawn once more: it must retry
    assert first.name.endswith("aaaaaaaa") and second.name.endswith("bbbbbbbb")
    assert (first / "report.json").read_text(encoding="utf-8") == "keep me" and not list(second.iterdir())


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
