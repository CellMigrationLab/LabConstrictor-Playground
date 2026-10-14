"""The Tools release that the installers pin and the one the Colab notebook installs must be the same tag."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "app" / "bash_bat_scripts"
NOTEBOOK = ROOT / "notebooks" / "LabConstrictorPlayground" / "LabConstrictorPlayground.ipynb"


def _pin(path: Path, pattern: str) -> str:
    """Return the tag that `pattern` (one capture group) finds in `path`; fail if it is not there exactly once."""
    found = re.findall(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE | re.IGNORECASE)
    assert len(found) == 1, f"{path.name}: expected one LC_TOOLS_PIN, found {found}"
    return found[0]


def test_installers_and_notebook_use_the_same_tools_tag() -> None:
    sh = _pin(SCRIPTS / "post_install.sh", r'^\s*LC_TOOLS_PIN="([^"]+)"')
    bat = _pin(SCRIPTS / "post_install.bat", r'^\s*SET "LC_TOOLS_PIN=([^"]+)"')
    assert sh == bat
    sources = "".join(json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"][2]["source"])
    assert f"LabConstrictor-Tools/archive/refs/tags/{sh}.zip" in sources
    assert "LabConstrictor-Tools/archive/refs/heads" not in sources
