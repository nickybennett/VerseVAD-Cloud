"""Deployment-environment helpers that do not depend on Streamlit internals."""

from __future__ import annotations

import os
import secrets
import tempfile
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any


CLOUD_DEPLOYMENT_ENVIRONMENT_VARIABLE = "VERSEVAD_CLOUD_DEPLOYMENT"
CLOUD_SESSION_STATE_KEY = "_versevad_cloud_session_id"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def cloud_deployment_enabled(
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the private Community Cloud entrypoint enabled cloud mode."""

    source = os.environ if environment is None else environment
    return (
        source.get(CLOUD_DEPLOYMENT_ENVIRONMENT_VARIABLE, "").strip().casefold()
        in _TRUE_VALUES
    )


def cloud_session_database_path(
    session_state: MutableMapping[str, Any],
    *,
    temporary_root: Path | None = None,
) -> Path:
    """Return a stable, unguessable database path for one browser session."""

    session_identifier = session_state.get(CLOUD_SESSION_STATE_KEY)
    if not isinstance(session_identifier, str) or len(session_identifier) != 32:
        session_identifier = secrets.token_hex(16)
        session_state[CLOUD_SESSION_STATE_KEY] = session_identifier
    root = (
        Path(tempfile.gettempdir())
        if temporary_root is None
        else Path(temporary_root)
    )
    return (
        root
        / "versevad-cloud-sessions"
        / session_identifier
        / "versevad.sqlite3"
    )
