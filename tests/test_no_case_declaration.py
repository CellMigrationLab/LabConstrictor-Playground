"""Every tool of the Playground has a case in `lc_tests/cases.json` or is declared, with a reason, in `lc_tests/no_case.json`."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("labconstrictor_tools")

from labconstrictor_tools.decorators import tools_in  # noqa: E402

MODULE = "labconstrictor_playground_lc_tools"
NO_CASE = ROOT / "lc_tests" / "no_case.json"
CASES = ROOT / "lc_tests" / "cases.json"


def app_tools() -> set[str]:
    return {t.id for t in tools_in(MODULE)}


def tools_with_case() -> set[str]:
    return {case["tool"] for case in json.loads(CASES.read_text(encoding="utf-8"))}


def declared() -> dict[str, str]:
    return json.loads(NO_CASE.read_text(encoding="utf-8"))


def test_no_case_file_is_an_object_of_reasons() -> None:
    data = declared()
    assert isinstance(data, dict)
    for tool_id, reason in data.items():
        assert isinstance(reason, str) and reason.strip(), f"{tool_id}: the reason must be a non-empty text"


def test_declared_tools_exist_and_have_no_case() -> None:
    data = declared()
    unknown = sorted(set(data) - app_tools())
    assert not unknown, f"declared in no_case.json but not tools of the app: {unknown}"
    stale = sorted(set(data) & tools_with_case())
    assert not stale, f"stale exemption, these tools have a case in cases.json: {stale}"


def test_every_tool_has_a_case_or_is_declared() -> None:
    missing = sorted(app_tools() - tools_with_case() - set(declared()))
    assert not missing, f"tools with no case in cases.json and not in no_case.json: {missing}"
