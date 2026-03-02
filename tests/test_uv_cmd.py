from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from uv_init_tui import uv_cmd


def test_build_uv_init_cmd_includes_flags() -> None:
    cmd = uv_cmd.build_uv_init_cmd(
        name="demo",
        description="Demo app",
        is_lib=True,
        python_version="3.14",
    )
    assert cmd == ["uv", "init", "--lib", "--description", "Demo app", "--python", "3.14", "demo"]


def test_build_uv_remove_cmd_includes_dev_flag_when_requested() -> None:
    cmd = uv_cmd.build_uv_remove_cmd(deps=["pytest"], dev=True)
    assert cmd == ["uv", "remove", "--dev", "pytest"]


def test_build_uv_add_cmd_uses_no_sync_by_default() -> None:
    cmd = uv_cmd.build_uv_add_cmd(deps=["rich"])
    assert cmd == ["uv", "add", "--no-sync", "rich"]


def test_run_success_combines_stdout_and_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        assert args[0] == ["uv", "version"]
        assert kwargs["cwd"] == str(tmp_path)
        assert kwargs["timeout"] == 300
        assert "UVIRTUAL_ENV" not in kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="warn\n")

    monkeypatch.setattr(uv_cmd.subprocess, "run", fake_run)
    assert uv_cmd._run(["uv", "version"], cwd=tmp_path) == "ok\nwarn"


def test_run_raises_on_non_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(returncode=2, stdout="", stderr="failed")

    monkeypatch.setattr(uv_cmd.subprocess, "run", fake_run)
    with pytest.raises(uv_cmd.UVError, match="failed"):
        uv_cmd._run(["uv", "init", "demo"])


def test_run_raises_on_missing_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("uv not found")

    monkeypatch.setattr(uv_cmd.subprocess, "run", fake_run)
    with pytest.raises(uv_cmd.UVError, match="not found on PATH"):
        uv_cmd._run(["uv", "init"])


def test_run_raises_on_missing_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    def fake_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("No such file or directory")

    monkeypatch.setattr(uv_cmd.subprocess, "run", fake_run)
    with pytest.raises(uv_cmd.UVError, match="Working directory does not exist"):
        uv_cmd._run(["uv", "init"], cwd=missing)


def test_uv_init_calls_run_with_expected_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, object] = {}

    def fake_run(cmd, cwd=None):  # type: ignore[no-untyped-def]
        called["cmd"] = list(cmd)
        called["cwd"] = cwd
        return "done"

    monkeypatch.setattr(uv_cmd, "_run", fake_run)
    result = uv_cmd.uv_init(
        target_dir=tmp_path,
        name="demo",
        description="Demo app",
        is_lib=False,
        python_version="3.14",
    )
    assert result == "done"
    assert called["cmd"] == ["uv", "init", "--description", "Demo app", "--python", "3.14", "demo"]
    assert called["cwd"] == tmp_path


def test_uv_add_and_remove_return_empty_for_no_deps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def should_not_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("_run should not be called when deps is empty")

    monkeypatch.setattr(uv_cmd, "_run", should_not_run)
    assert uv_cmd.uv_add(project_root=tmp_path, deps=[]) == ""
    assert uv_cmd.uv_remove(project_root=tmp_path, deps=[]) == ""


def test_uv_add_passes_no_sync_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, object] = {}

    def fake_run(cmd, cwd=None):  # type: ignore[no-untyped-def]
        called["cmd"] = list(cmd)
        called["cwd"] = cwd
        return "ok"

    monkeypatch.setattr(uv_cmd, "_run", fake_run)
    assert uv_cmd.uv_add(project_root=tmp_path, deps=["httpx"]) == "ok"
    assert called["cmd"] == ["uv", "add", "--no-sync", "httpx"]
    assert called["cwd"] == tmp_path
