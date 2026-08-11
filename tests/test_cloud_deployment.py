from __future__ import annotations

from pathlib import Path
from types import ModuleType

import streamlit_app

from versevad.deployment import (
    CLOUD_SESSION_STATE_KEY,
    cloud_deployment_enabled,
    cloud_session_database_path,
)


ROOT = Path(__file__).resolve().parents[1]


def test_cloud_entrypoint_and_configuration_are_host_safe() -> None:
    entrypoint = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    configuration = (ROOT / ".streamlit" / "config.toml").read_text(
        encoding="utf-8"
    )

    assert 'os.environ["VERSEVAD_CLOUD_DEPLOYMENT"] = "1"' in entrypoint
    assert "runpy.run_path(" in entrypoint
    assert '"versevad" / "ui" / "app.py"' in entrypoint
    assert "from versevad.ui import app" not in entrypoint
    assert 'address = "127.0.0.1"' not in configuration
    assert "headless = false" not in configuration
    assert "maxUploadSize = 5" in configuration
    assert 'fileWatcherType = "none"' in configuration


def test_cloud_entrypoint_discards_only_an_incompatible_cached_helper(
    monkeypatch,
) -> None:
    stale = ModuleType("versevad.ui.profile_details")
    monkeypatch.setitem(
        streamlit_app.sys.modules,
        "versevad.ui.profile_details",
        stale,
    )
    assert streamlit_app._discard_incompatible_cached_modules()
    assert "versevad.ui.profile_details" not in streamlit_app.sys.modules

    current = ModuleType("versevad.ui.profile_details")
    for symbol in streamlit_app._REQUIRED_PROFILE_DETAIL_SYMBOLS:
        setattr(current, symbol, object())
    monkeypatch.setitem(
        streamlit_app.sys.modules,
        "versevad.ui.profile_details",
        current,
    )
    assert not streamlit_app._discard_incompatible_cached_modules()
    assert streamlit_app.sys.modules["versevad.ui.profile_details"] is current


def test_cloud_mode_accepts_only_explicit_true_values() -> None:
    assert cloud_deployment_enabled({"VERSEVAD_CLOUD_DEPLOYMENT": "1"})
    assert cloud_deployment_enabled({"VERSEVAD_CLOUD_DEPLOYMENT": "TRUE"})
    assert not cloud_deployment_enabled({})
    assert not cloud_deployment_enabled(
        {"VERSEVAD_CLOUD_DEPLOYMENT": "unexpected"}
    )


def test_cloud_database_is_stable_within_and_isolated_between_sessions(
    tmp_path: Path,
) -> None:
    first_session: dict[str, object] = {}
    second_session: dict[str, object] = {}

    first_path = cloud_session_database_path(
        first_session,
        temporary_root=tmp_path,
    )
    repeated_path = cloud_session_database_path(
        first_session,
        temporary_root=tmp_path,
    )
    second_path = cloud_session_database_path(
        second_session,
        temporary_root=tmp_path,
    )

    assert first_path == repeated_path
    assert first_path != second_path
    assert first_path.name == "versevad.sqlite3"
    assert first_path.parent.name == first_session[CLOUD_SESSION_STATE_KEY]
