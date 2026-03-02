from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shlex import join as shlex_join, quote as shlex_quote

import pytest

from uv_init_tui.app import (
    InitPlan,
    WizardScreen,
    _build_preview_text,
    _format_shell_preview,
    _resolve_project_name,
    _slugify_project_name,
)
from uv_init_tui.config import AppConfig


def test_format_shell_preview_matches_shell_join() -> None:
    cwd = Path("/tmp/my project")
    cmd = ["uv", "init", "--description", 'hello "world"', "demo"]
    preview = _format_shell_preview(cwd=cwd, cmd=cmd)
    assert preview == f"cd {shlex_quote(str(cwd))} && {shlex_join(cmd)}"


def test_build_preview_text_includes_uv_steps_and_script_note() -> None:
    plan = InitPlan(
        target_dir=Path("/tmp/demo"),
        name="demo",
        description="Demo",
        is_lib=False,
        python_version="3.14",
        deps=["httpx"],
        scripts={"demo": "demo.cli:main"},
        overwrite=False,
    )

    preview = _build_preview_text(plan)
    assert "uv init" in preview
    assert "uv add --no-sync httpx" in preview
    assert "Non-uv step: update [project.scripts]" in preview


def test_build_preview_text_mentions_no_uv_add_when_no_deps() -> None:
    plan = InitPlan(
        target_dir=Path("/tmp/demo"),
        name="demo",
        description="Demo",
        is_lib=True,
        python_version="3.14",
        deps=[],
        scripts={},
        overwrite=False,
    )
    preview = _build_preview_text(plan)
    assert "(No `uv add` command; no dependencies selected.)" in preview


def test_resolve_project_name_accepts_valid_name() -> None:
    assert _resolve_project_name("my_project-1.0") == "my_project-1.0"


def test_resolve_project_name_uses_slugified_fallback() -> None:
    assert _slugify_project_name("My Cool App!") == "my-cool-app"
    assert _resolve_project_name("My Cool App!") == "my-cool-app"


def test_resolve_project_name_rejects_unsluggable_name() -> None:
    assert _resolve_project_name("!!!") is None


@dataclass
class _FakeRowKey:
    value: str


@dataclass
class _FakeCellKey:
    row_key: object


class _FakeTable:
    row_count = 1
    cursor_coordinate = (0, 0)

    def coordinate_to_cell_key(self, _coord: tuple[int, int]) -> _FakeCellKey:
        return _FakeCellKey(row_key=_FakeRowKey("tool"))


def test_remove_selected_script_handles_row_key_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    screen = WizardScreen(AppConfig(), enable_scripts=True)
    screen._scripts = {"tool": "pkg.cli:main"}
    table = _FakeTable()
    refreshed: list[bool] = []

    def fake_query_one(selector: str, _expected_type):  # type: ignore[no-untyped-def]
        assert selector == "#scripts_table"
        return table

    monkeypatch.setattr(screen, "query_one", fake_query_one)
    monkeypatch.setattr(screen, "_refresh_scripts_table", lambda: refreshed.append(True))

    screen._remove_selected_script()

    assert screen._scripts == {}
    assert refreshed == [True]
