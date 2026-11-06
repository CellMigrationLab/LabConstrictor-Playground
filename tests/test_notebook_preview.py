"""The notebook's "Make test data" cell shows its preview as a PNG image, whatever matplotlib's backend is (#34).

With the non-interactive Agg backend, plt.show() only warned "FigureCanvasAgg is non-interactive" and showed no figure (macOS,
round alpha.4). The cell is run here under Agg with the widgets and IPython's display stubbed: pressing the button must display one
PNG image and raise no warning.
"""

import json
import warnings
from pathlib import Path

import matplotlib

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "LabConstrictorPlayground" / "LabConstrictorPlayground.ipynb"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class _Widget:
    def __init__(self, *args, value=None, **kwargs):
        self.value = value
        self.handlers = []

    def on_click(self, handler):
        self.handlers.append(handler)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Widgets:
    Text = Dropdown = Button = Output = VBox = Layout = _Widget


class _Image:
    def __init__(self, data=None, filename=None):
        self.data = data


def _make_test_data_cell() -> str:
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    found = [
        "".join(c["source"])
        for c in cells
        if c["cell_type"] == "code" and "".join(c["source"]).startswith("# @title Make test data")
    ]
    assert len(found) == 1, "expected one Make test data cell"
    return found[0]


def test_no_cell_relies_on_plt_show() -> None:
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    assert not [c for c in cells if c["cell_type"] == "code" and "plt.show(" in "".join(c["source"])]


def test_make_test_data_preview_is_an_image_under_agg(tmp_path: Path) -> None:
    from labconstrictor_playground import make_test_data

    matplotlib.use("Agg")
    shown = []
    namespace = {
        "widgets": _Widgets,
        "Image": _Image,
        "display": shown.append,
        "clear_output": lambda wait=False: None,
        "make_test_data": make_test_data,
    }
    exec(compile(_make_test_data_cell(), "Make test data", "exec"), namespace)
    namespace["folder"].value = str(tmp_path)
    namespace["kind"].value = "all"
    shown.clear()  # the form itself
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # the Agg "cannot be shown" warning fails the test
        for handler in namespace["make"].handlers:
            handler(None)
    images = [s for s in shown if isinstance(s, _Image)]
    assert len(images) == 1, shown
    assert images[0].data.startswith(PNG_SIGNATURE)
