from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, cast

from tomlkit import dumps, parse, table


def set_project_scripts(pyproject_path: Path, scripts: Mapping[str, str]) -> None:
    """
    Ensure [project.scripts] exists and set keys to given values.

    This modifies the *generated project's* pyproject.toml.

    Why tomlkit:
        - Preserves formatting, comments, and ordering more gracefully
          than a dumb string replace.
        - Avoids the "oops, I broke TOML" class of bugs.

    Args:
        pyproject_path: Path to pyproject.toml.
        scripts: Mapping of script name -> entry point ("module:callable").
    """
    if not scripts:
        return

    text = pyproject_path.read_text(encoding="utf-8")
    doc = parse(text)

    # Repair missing or invalid shapes so assignment below is always safe.
    project_obj = doc.get("project")
    if not isinstance(project_obj, MutableMapping):
        doc["project"] = table()
        project_obj = doc["project"]
    project = cast(MutableMapping[str, Any], project_obj)

    if (
        "scripts" not in project
        or project["scripts"] is None
        or not isinstance(project["scripts"], MutableMapping)
    ):
        project["scripts"] = table()

    scripts_tbl = cast(MutableMapping[str, Any], project["scripts"])

    for name, entry in scripts.items():
        scripts_tbl[name] = entry

    pyproject_path.write_text(dumps(doc), encoding="utf-8")
