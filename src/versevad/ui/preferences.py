"""Local application-level interface preferences.

Preferences are intentionally separate from projects and analysis
configurations. They never participate in result IDs, exports, or cached
analytical state.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path


PREFERENCES_VERSION = 2


class AppearanceMode(StrEnum):
    CLASSIC = "Classic"
    DARK = "Dark"
    LAVENDER = "Lavender"
    OCEAN = "Ocean"
    CRIMSON = "Crimson"
    FOREST = "Forest"


@dataclass(frozen=True)
class UiPreferences:
    version: int = PREFERENCES_VERSION
    appearance: AppearanceMode = AppearanceMode.CLASSIC


_LEGACY_APPEARANCE_MIGRATIONS = {
    "Light": AppearanceMode.CLASSIC,
    "System": AppearanceMode.CLASSIC,
}


def normalize_appearance(value: AppearanceMode | str | object) -> AppearanceMode:
    """Resolve current and legacy appearance values to a supported theme."""

    if isinstance(value, AppearanceMode):
        return value
    if not isinstance(value, str):
        return AppearanceMode.CLASSIC
    migrated = _LEGACY_APPEARANCE_MIGRATIONS.get(value)
    if migrated is not None:
        return migrated
    try:
        return AppearanceMode(value)
    except (TypeError, ValueError):
        return AppearanceMode.CLASSIC


def default_preferences_path() -> Path:
    configured = os.environ.get("VERSEVAD_PREFERENCES_PATH")
    if configured:
        return Path(configured).expanduser()
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "private" / "ui_preferences.json"


def load_preferences(path: Path | str | None = None) -> UiPreferences:
    """Return safe defaults when a local preference file is absent or invalid."""

    preference_path = Path(path) if path is not None else default_preferences_path()
    try:
        payload = json.loads(preference_path.read_text(encoding="utf-8"))
        return UiPreferences(
            version=PREFERENCES_VERSION,
            appearance=normalize_appearance(payload.get("appearance")),
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return UiPreferences()


def save_preferences(
    preferences: UiPreferences,
    path: Path | str | None = None,
) -> Path:
    """Atomically save UI-only preferences outside project databases."""

    preference_path = Path(path) if path is not None else default_preferences_path()
    preference_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = preference_path.with_suffix(preference_path.suffix + ".tmp")
    payload = asdict(preferences)
    payload["appearance"] = preferences.appearance.value
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(preference_path)
    return preference_path


def save_appearance(
    appearance: AppearanceMode | str,
    path: Path | str | None = None,
) -> Path:
    return save_preferences(
        UiPreferences(appearance=normalize_appearance(appearance)),
        path,
    )
