"""The playground package and its tools: checks, test data, stress functions, and the light import of the declarations."""

import json
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
        ["check_everything", "feature_tour", "list_devices", "make_test_data", "run_on_device", "stress_big_image", "stress_crash", "stress_hang", "stress_many_points", "stress_out_of_memory", "stress_slow"]
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
    with pytest.raises(MemoryError):
        stress.out_of_memory()
    seen = []
    assert stress.slow(0.6, lambda f, m: seen.append(f), lambda: None) >= 0.6 and seen


def test_slow_stops_when_cancel_raises():
    class Stop(Exception):
        pass

    def cancelled():
        raise Stop()

    with pytest.raises(Stop):
        stress.slow(5, lambda f, m: None, cancelled)
