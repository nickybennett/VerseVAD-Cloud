from __future__ import annotations

from pathlib import Path

from versevad.ui.design import stylesheet_for


ROOT = Path(__file__).parents[1]


def test_macos_helpers_are_project_local_locked_and_private() -> None:
    setup = (ROOT / "setup_macos.command").read_text(encoding="utf-8")
    launcher = (ROOT / "start_versevad.command").read_text(encoding="utf-8")
    diagnostics = (ROOT / "diagnose_macos.command").read_text(encoding="utf-8")

    for helper in (setup, launcher, diagnostics):
        assert helper.startswith("#!/bin/bash\n")
        assert "\r\n" not in helper
        assert '$(dirname -- "$0")' in helper
        assert "UV_PYTHON_INSTALL_DIR" in helper
        assert "UV_PYTHON_PREFERENCE=only-managed" in helper
        assert "ANEW VAD Study" not in helper

    assert "UV_UNMANAGED_INSTALL" in setup
    assert 'UV_VERSION="0.11.30"' in setup
    assert "uv/$UV_VERSION/install.sh" in setup
    assert "sync --locked --python 3.12" in setup
    assert "--runtime-only" in setup
    assert 'rm -rf -- "$VIRTUAL_ENVIRONMENT"' in setup
    assert "Refusing to rebuild an environment outside" in setup

    assert "127.0.0.1" in launcher
    assert "--offline" in launcher
    assert "gatherUsageStats false" in launcher
    assert "--server.headless false" in launcher
    assert "versevad-diagnose" in diagnostics

    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "cp312-cp312-macosx_11_0_arm64.whl" in lock
    assert "cp312-cp312-macosx_10_13_x86_64.whl" in lock
    assert (
        "espeakng_loader-0.2.4-py3-none-macosx_11_0_arm64.whl"
        in lock
    )
    assert (
        "espeakng_loader-0.2.4-py3-none-macosx_10_12_x86_64.whl"
        in lock
    )
    assert "espeakng_loader-0.2.4-py3-none-win_amd64.whl" in lock


def test_browser_styles_include_safari_and_narrow_layout_safeguards() -> None:
    css = stylesheet_for("Classic")

    for required in (
        "-webkit-text-size-adjust: 100%",
        "-webkit-overflow-scrolling: touch",
        "position: -webkit-sticky",
        "@media (max-width: 520px)",
        "overflow-x: clip",
        "font-size: 16px",
        "flex-wrap: wrap",
        "white-space: normal",
        '[aria-label="Project section"]',
        '[data-testid="stSidebarCollapseButton"]',
        '[data-testid="stSidebarCollapsedControl"]',
    ):
        assert required in css
