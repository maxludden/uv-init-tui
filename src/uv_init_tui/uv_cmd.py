"""Helpers for constructing and executing `uv` CLI commands."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from collections.abc import Sequence


class UVError(RuntimeError):
    """Raised when running `uv` fails (non-zero exit, missing binary, etc.)."""


def _run(cmd: Sequence[str], cwd: Path | None = None) -> str:
    """
    Run a command and return combined stdout/stderr.

    Args:
        cmd: Command + args (e.g. ["uv", "init", ...]).
        cwd: Optional working directory.

    Raises:
        UVError: If `uv` is missing or command returns non-zero.
    """
    env = os.environ.copy()
    # Avoid uv environment mismatch warnings/behavior when parent shells export
    # UVIRTUAL_ENV for a different project.
    env.pop("UVIRTUAL_ENV", None)

    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except FileNotFoundError as e:
        if cwd is not None and not cwd.exists():
            raise UVError(f"Working directory does not exist: {cwd}") from e
        if e.filename == "uv" or (cmd and cmd[0] == "uv"):
            raise UVError("`uv` was not found on PATH. Install uv first.") from e
        raise UVError(f"Failed to start command: {' '.join(cmd)}") from e
    except subprocess.TimeoutExpired as e:
        raise UVError(f"Command timed out after 300s: {' '.join(cmd)}") from e

    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise UVError(output.strip() or f"Command failed: {' '.join(cmd)}")
    return output.strip()


def build_uv_init_cmd(
    *,
    name: str,
    description: str,
    is_lib: bool,
    python_version: str,
) -> list[str]:
    """
    Build the argv list for `uv init`.

    Keeping command construction in one place ensures preview text in the TUI
    exactly matches what execution will run.
    """
    cmd: list[str] = ["uv", "init"]

    # `--lib` produces a library-style template (implies package layout).
    if is_lib:
        cmd.append("--lib")

    cmd += ["--description", description]
    cmd += ["--python", python_version]

    # `uv init <name>` creates a folder named <name> in the current directory.
    cmd.append(name)
    return cmd


def build_uv_add_cmd(*, deps: Sequence[str], no_sync: bool = True) -> list[str]:
    """Build the argv list for `uv add`.

    Args:
        deps: Dependencies to add.
        no_sync: If True, skip environment sync/installation and only update
            project metadata/lock data.
    """
    cmd = ["uv", "add"]
    if no_sync:
        cmd.append("--no-sync")
    cmd.extend(deps)
    return cmd


def build_uv_remove_cmd(*, deps: Sequence[str], dev: bool = False) -> list[str]:
    """Build the argv list for `uv remove`."""
    cmd = ["uv", "remove"]
    if dev:
        cmd.append("--dev")
    cmd.extend(deps)
    return cmd


def uv_init(
    *,
    target_dir: Path,
    name: str,
    description: str,
    is_lib: bool,
    python_version: str,
) -> str:
    """
    Initialize a new uv project.

    Behavior:
        Runs `uv init <name>` with cwd=target_dir.
        This creates a new folder at `<target_dir>/<name>`.

    Args:
        target_dir: Directory where the project folder is created.
        name: Project name / folder name.
        description: Project description for `uv init --description`.
        is_lib: If True, pass `--lib`.
        python_version: Value for `--python` (e.g. "3.14").

    Returns:
        Combined output from uv.
    """
    cmd = build_uv_init_cmd(
        name=name,
        description=description,
        is_lib=is_lib,
        python_version=python_version,
    )
    return _run(cmd, cwd=target_dir)


def uv_add(*, project_root: Path, deps: Sequence[str], no_sync: bool = True) -> str:
    """
    Add dependencies to an initialized uv project via `uv add`.

    Args:
        project_root: Directory containing pyproject.toml.
        deps: Dependencies to add (e.g. ["httpx", "pydantic"]).
        no_sync: If True, skip environment sync/installation.
    """
    if not deps:
        return ""
    cmd = build_uv_add_cmd(deps=deps, no_sync=no_sync)
    return _run(cmd, cwd=project_root)


def uv_remove(*, project_root: Path, deps: Sequence[str], dev: bool = False) -> str:
    """
    Remove dependencies from an initialized uv project via `uv remove`.

    Args:
        project_root: Directory containing pyproject.toml.
        deps: Dependencies to remove.
        dev: If True, remove from development dependencies with `--dev`.
    """
    if not deps:
        return ""
    cmd = build_uv_remove_cmd(deps=deps, dev=dev)
    return _run(cmd, cwd=project_root)
