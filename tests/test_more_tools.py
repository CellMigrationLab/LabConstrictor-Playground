"""The tools that cover the file, table, EnabledWhen, PixelSizeOf and Affine features: known answers through the real declarations."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("labconstrictor_tools")
np = pytest.importorskip("numpy")
pytest.importorskip("pandas")

from labconstrictor_tools import ToolError  # noqa: E402
from labconstrictor_tools.decorators import tools_in  # noqa: E402
from labconstrictor_tools.introspection import describe_tools  # noqa: E402

MODULE = "labconstrictor_playground_lc_tools"
DATA = ROOT / "lc_tests" / "fixtures" / "data"


def fn(tool_id):
    return {t.id: t.fn for t in tools_in(MODULE)}[tool_id]


def square(row, col):
    image = np.zeros((32, 32), np.uint8)
    image[row : row + 4, col : col + 4] = 255
    return image


def inputs_of(tool_id):
    __import__(MODULE)
    tool = {t["id"]: t for t in describe_tools(MODULE)["tools"]}[tool_id]
    return {i["name"]: i for i in tool["inputs"]}


def test_look_inside_file_json_and_text(tmp_path):
    result = fn("look_inside_file")(DATA / "settings.json")
    assert result["kind"] == "json" and result["value_name"] == "demo" and result["value_channels"] == 3
    assert fn("look_inside_file")(DATA / "notes.txt")["lines"] == 3
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * 1_000_001)
    with pytest.raises(ToolError) as refused:
        fn("look_inside_file")(big)
    assert refused.value.code == "file_too_large"


def test_summarise_table_known_answer():
    import pandas as pd

    rows, counts = fn("summarise_table")(pd.read_csv(DATA / "measurements.csv"))
    by_name = {r["column"]: r for r in rows}
    assert by_name["length"]["mean"] == 20.0 and by_name["width"]["max"] == 6.0
    assert counts == {"rows": 3, "columns": 4, "numeric_columns": 3}
    with pytest.raises(ToolError):
        fn("summarise_table")(pd.DataFrame({"a": ["x", "y"]}))


def test_enabled_when_is_declared_and_the_disabled_parameter_is_still_accepted():
    declared = inputs_of("count_above_level")
    assert declared["level"]["enabled_when"]["param"] == "mode"
    assert declared["percentile"]["enabled_when"] == {"param": "mode", "equals": ["percentile"]}
    image = square(4, 8)
    count = fn("count_above_level")
    assert count(image, "fixed", 100.0, 5.0)["pixels"] == 16
    assert count(image, "percentile", 12345.0, 99.0)["pixels"] == 16


def test_bright_area_needs_a_pixel_size_and_never_invents_one():
    declared = inputs_of("bright_area")["pixel_size"]
    assert declared["pixel_size_of"] == "image" and declared["nullable"] and not declared["required"] and "default" not in declared
    area = fn("bright_area")
    assert area(square(4, 8), 0.5)["area_um2"] == 4.0
    for bad, code in ((None, "pixel_size_unknown"), (0.0, "invalid_pixel_size"), (-1.0, "invalid_pixel_size")):
        with pytest.raises(ToolError) as refused:
            area(square(4, 8), bad)
        assert refused.value.code == code


def test_align_centres_is_the_translation_between_centres():
    matrix = fn("align_centres")(square(4, 8), square(14, 20))
    assert np.allclose(matrix, [[1, 0, 10], [0, 1, 12], [0, 0, 1]])
    with pytest.raises(ToolError) as refused:
        fn("align_centres")(np.zeros((8, 8)), square(1, 1))
    assert refused.value.code == "no_signal"


def with_nan():
    image = square(4, 8).astype(np.float32)
    image[0, 0] = np.nan
    return image


def test_non_finite_pixels_are_refused_not_silently_dropped():
    calls = (
        ("count_above_level", (with_nan(), "percentile")),
        ("count_above_level", (with_nan(), "fixed", 100.0)),
        ("bright_area", (with_nan(), 0.5)),
        ("align_centres", (with_nan(), square(4, 8))),
        ("align_centres", (square(4, 8), with_nan())),
    )
    for tool_id, args in calls:
        with pytest.raises(ToolError) as refused:
            fn(tool_id)(*args)
        assert refused.value.code == "non_finite_pixels", tool_id
