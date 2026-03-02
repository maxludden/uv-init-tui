from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from uv_init_tui import config


def _set_config_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / ".config" / "uv-init-tui"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    return config_path


def test_toml_dumps_minimal_escapes_special_chars() -> None:
    raw = {
        "default_directory": 'a"b\\c',
        "default_python": "3.14",
        "default_is_lib": False,
        "common_dependencies": ['x"y', "line\nbreak"],
        "common_dev_deps": ["pytest"],
        "default_dependencies": [],
    }
    dumped = config._toml_dumps_minimal(raw)
    parsed = tomllib.loads(dumped)
    assert parsed["default_directory"] == 'a"b\\c'
    assert parsed["common_dependencies"] == ['x"y', "line\nbreak"]


def test_toml_dumps_minimal_rejects_non_string_list_items() -> None:
    with pytest.raises(TypeError, match="list\\[str\\]"):
        config._toml_dumps_minimal({"bad": [1, "ok"]})


def test_load_and_save_config_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_config_paths(monkeypatch, tmp_path)
    loaded = config.load_config()
    assert config_path.exists()
    assert loaded.default_python == "3.14"

    loaded.default_directory = 'dir/with "quotes"'
    loaded.common_dependencies = ["rich", "httpx"]
    loaded.default_dependencies = ["httpx"]
    config.save_config(loaded)

    reloaded = config.load_config()
    assert reloaded.default_directory == 'dir/with "quotes"'
    assert reloaded.common_dependencies == ["rich", "httpx"]
    assert reloaded.default_dependencies == ["httpx"]


def test_load_config_ignores_unknown_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_config_paths(monkeypatch, tmp_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        'default_directory = "."\n'
        'default_python = "3.14"\n'
        'default_is_lib = false\n'
        'common_dependencies = ["rich"]\n'
        'common_dev_deps = ["pytest"]\n'
        'default_dependencies = []\n'
        'unknown_key = "ignore me"\n',
        encoding="utf-8",
    )

    loaded = config.load_config()
    assert loaded.default_directory == "."
    assert not hasattr(loaded, "unknown_key")
