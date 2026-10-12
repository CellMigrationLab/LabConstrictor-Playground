"""The Playground rule: every marker, input type, output type and widget the tools bridge offers is used by a tool of the Playground.

The Playground is what testers install to see what each host does with each feature, so a feature of `labconstrictor_tools` that no
Playground tool uses is a feature nobody tests on Windows, macOS or Linux. The catalogue is read from the installed
`labconstrictor_tools` (its public `__all__` and the type tables of `labconstrictor_tools.types`), so when the Tools add a marker, an
input type, an output type or a widget this test fails until a tool of the Playground uses it, or until it is added, with a reason, to
`NOT_IN_THE_PLAYGROUND` below (reviewed in the pull request that does it).
"""

import inspect
import sys
import typing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("labconstrictor_tools")

import labconstrictor_tools  # noqa: E402
from labconstrictor_tools import types as T  # noqa: E402
from labconstrictor_tools.decorators import tools_in  # noqa: E402

MODULE = "labconstrictor_playground_lc_tools"

# Items the Playground intentionally does not exercise, each with the reason. Keep it short; every line is a review decision.
# Keys are catalogue names ("marker Foo", "input Foo", "output Foo", "widget 'foo'").
NOT_IN_THE_PLAYGROUND: dict[str, str] = {}


def catalogue() -> set[str]:
    """Everything the Tools declare: markers, input types, output types and widget names, read from the public API."""
    found = set()
    for name in labconstrictor_tools.__all__:
        item = getattr(labconstrictor_tools, name)
        if not inspect.isclass(item) or item.__module__ != T.__name__ or issubclass(item, BaseException):
            continue  # functions (tool, progress...), ToolError, Cancelled: not part of a declaration
        if item in T.INPUT_TYPES:
            found.add("input " + name)
        elif item in T.OUTPUT_TYPES:
            found.add("output " + name)
        else:
            found.add("marker " + name)
    found |= {"widget %r" % w for w in T.WIDGETS}
    return found


def _walk(annotation, used: set[str]) -> None:
    """Record every type, marker and widget in one (possibly nested Annotated / Optional / tuple) annotation."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        base, *metadata = typing.get_args(annotation)
        _walk(base, used)
        for m in metadata:
            used.add(("marker " + type(m).__name__))
            if isinstance(m, T.Widget):
                used.add("widget %r" % m.value)
        return
    if origin is not None:  # Optional[...], tuple[...], Literal[...]
        for arg in typing.get_args(annotation):
            _walk(arg, used)
        return
    if annotation in T.INPUT_TYPES:
        used.add("input " + annotation.__name__)
    elif annotation in T.OUTPUT_TYPES:
        used.add("output " + annotation.__name__)


def used_by_the_playground() -> dict[str, set[str]]:
    """item -> the ids of the Playground tools that use it, from the real declarations (`@tool` functions of the module)."""
    __import__(MODULE)
    users: dict[str, set[str]] = {}
    for tool in tools_in(MODULE):
        items: set[str] = set()
        signature = inspect.signature(tool.fn, eval_str=True)
        for parameter in signature.parameters.values():
            _walk(parameter.annotation, items)
        if signature.return_annotation is not inspect.Signature.empty:
            _walk(signature.return_annotation, items)
        for item in items:
            users.setdefault(item, set()).add(tool.id)
    return users


def test_the_catalogue_is_read_from_the_tools():
    names = catalogue()
    # a floor, so that a change in how the catalogue is read cannot silently empty the rule
    assert {"marker Group", "marker ApplyTo", "input Image", "output PointsOut", "widget 'slider'"} <= names
    assert len(names) >= 30, sorted(names)


def test_every_marker_and_type_of_the_tools_is_used_by_a_playground_tool():
    users = used_by_the_playground()
    missing = sorted(catalogue() - set(users) - set(NOT_IN_THE_PLAYGROUND))
    assert not missing, (
        "The Playground rule: these features of labconstrictor_tools are used by no Playground tool: %s.\n"
        "Add them to a tool of src/labconstrictor_playground_lc_tools/__init__.py (the feature tour, preferably), or, if they cannot "
        "belong there, list them with the reason in NOT_IN_THE_PLAYGROUND in tests/test_manifest_coverage.py." % ", ".join(missing)
    )


def test_the_allowlist_has_no_stale_or_unexplained_entries():
    users = used_by_the_playground()
    names = catalogue()
    for item, reason in NOT_IN_THE_PLAYGROUND.items():
        assert item in names, "%s is no longer in the Tools: remove it from NOT_IN_THE_PLAYGROUND" % item
        assert item not in users, "%s is now used by %s: remove it from NOT_IN_THE_PLAYGROUND" % (item, sorted(users[item]))
        assert len(reason.split()) >= 3, "%s needs a reason" % item
