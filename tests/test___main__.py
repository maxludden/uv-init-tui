from __future__ import annotations

import runpy

import uv_init_tui.app


def test_main_module_invokes_app_main(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    called: list[bool] = []
    monkeypatch.setattr(uv_init_tui.app, "main", lambda: called.append(True))

    runpy.run_module("uv_init_tui.__main__", run_name="__main__")

    assert called == [True]
