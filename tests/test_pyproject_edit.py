from __future__ import annotations

import tomllib
from pathlib import Path

from uv_init_tui.pyproject_edit import set_project_scripts


def test_set_project_scripts_creates_section(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    set_project_scripts(pyproject, {"demo": "demo.cli:main"})

    parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert parsed["project"]["scripts"]["demo"] == "demo.cli:main"


def test_set_project_scripts_repairs_invalid_project_shape(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('title = "x"\nproject = "bad-shape"\n', encoding="utf-8")

    set_project_scripts(pyproject, {"tool": "pkg.cli:main"})

    parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert parsed["project"]["scripts"]["tool"] == "pkg.cli:main"


def test_set_project_scripts_noop_on_empty_mapping(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    original = '[project]\nname = "demo"\n'
    pyproject.write_text(original, encoding="utf-8")

    set_project_scripts(pyproject, {})

    assert pyproject.read_text(encoding="utf-8") == original
