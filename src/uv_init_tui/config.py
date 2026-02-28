from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


CONFIG_DIR: Path = Path.home() / ".config" / "uv-init-tui"
CONFIG_PATH: Path = CONFIG_DIR / "config.toml"


@dataclass
class AppConfig:
    """
    User-editable configuration for uv-init-tui.

    Stored at: ~/.config/uv-init-tui/config.toml

    Note:
        We keep this schema intentionally simple (strings/bools/list[str])
        so it’s easy to read and hand-edit.
    """

    default_directory: str = "."
    default_python: str = "3.14"
    default_is_lib: bool = False

    # Shown in the dependency picker (SelectionList)
    common_dependencies: list[str] = field(
        default_factory=lambda: [
            "rich",
            "rich-gradient",
            "textual",
            "typer",
            "httpx",
            "requests",
            "pydantic",
            "python-dotenv",
            "pytest",
            "ruff",
            "mypy",
            "loguru",
            "ty"
        ]
    )

    common_dev_deps: list[str] = field(
         default_factory=lambda: [
             "mypy",
             "ruff",
             "pytest",
             "ty"
         ]
    )

    # Pre-selected dependencies in the picker
    default_dependencies: list[str] = field(default_factory=list)


def _toml_dumps_minimal(data: dict[str, Any]) -> str:
    """
    Minimal TOML serializer for our config schema.

    We only support:
      - str
      - bool
      - list[str]

    This avoids pulling in a TOML writing dependency for config,
    and keeps the file human-friendly.
    """
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, list):
            items = ", ".join(f'"{item}"' for item in value)
            lines.append(f"{key} = [{items}]")
        else:
            raise TypeError(f"Unsupported config type for {key}: {type(value)}")
    lines.append("")
    return "\n".join(lines)


def ensure_config_exists() -> None:
    """
    Ensure config directory + config file exist.
    If missing, write a default config.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        cfg = AppConfig()
        CONFIG_PATH.write_text(_toml_dumps_minimal(asdict(cfg)), encoding="utf-8")


def load_config() -> AppConfig:
    """
    Load the TOML config from disk (creating defaults if needed).

    Raises:
        RuntimeError: if tomllib is unavailable (Python < 3.11).
    """
    ensure_config_exists()
    if tomllib is None:
        raise RuntimeError("tomllib not available (need Python 3.11+).")

    raw_text = CONFIG_PATH.read_text(encoding="utf-8")
    data = tomllib.loads(raw_text)

    cfg = AppConfig()
    # Only apply known keys; ignore unknown keys for forward compatibility.
    for key, value in data.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg


def save_config(cfg: AppConfig) -> None:
    """Persist the given config to disk."""
    ensure_config_exists()
    CONFIG_PATH.write_text(_toml_dumps_minimal(asdict(cfg)), encoding="utf-8")
