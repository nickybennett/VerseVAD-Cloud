"""Versioned user-defined analysis-profile persistence and widget snapshots."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping


CUSTOM_PROFILE_VERSION = 1
COMPARISON_PROFILE_SETTING_KEYS = (
    "phrase_policy_label",
    "minimum_matches",
    "concreteness_abstract_max",
    "concreteness_concrete_min",
    "concreteness_exclude_proper",
    "concreteness_phrases",
    "concreteness_coverage_warning",
    "sensorimotor_exclude_proper",
    "sensorimotor_phrases",
    "sensorimotor_top_terms",
    "frequency_rare_below",
    "frequency_uncommon_below",
    "frequency_moderate_below",
    "frequency_very_common_min",
    "frequency_exclude_proper",
    "frequency_content_words_only",
    "frequency_lemma_fallback",
    "frequency_coverage_warning",
    "aoa_early_max",
    "aoa_later_min",
    "aoa_exclude_proper",
    "aoa_content_words_only",
    "aoa_lemma_fallback",
    "aoa_coverage_warning",
    "lexical_style_mattr_window",
    "lexical_style_hdd_sample",
    "lexical_style_mtld_threshold",
    "lexical_style_short_warning",
    "poetry_id_min_tokens",
    "poetry_id_min_types",
    "poetry_id_min_token_coverage",
    "poetry_id_min_type_coverage",
    "pronunciation_coverage_warning",
    "pronunciation_minimum_complete_lines",
    "pronunciation_minimum_resolved_tokens",
    "meter_line_match_threshold",
    "meter_irregular_threshold",
    "meter_ambiguity_margin",
    "meter_maximum_variants",
    "meter_analysis_mode",
    "meter_style_profile",
    "meter_interpretation_depth",
    "meter_performance_candidate_limit",
    "meter_realized_alternatives",
    "meter_allow_visible_elision",
    "phonological_slant_threshold",
    "phonological_sound_repetitions",
    "phonological_coverage_warning",
    "phonological_maximum_pairs",
)
_PROFILE_VALUE_MIGRATIONS = {
    (
        "meter_analysis_mode",
        "Candidate meter only (validated default)",
    ): "Candidate meter only (fixed-template layer)",
}

PROFILE_WIDGET_KEYS = frozenset(
    {
        "selected_lexicons",
        "include_concreteness",
        "include_sensorimotor",
        "include_frequency",
        "include_aoa",
        "include_lexical_style",
        "include_poetry_id",
        "include_pronunciation",
        "include_meter",
        "include_phonology",
        "include_inherited_form",
        "include_versemap",
        "single_stopword_mode",
        "single_protected_stopwords",
        "single_custom_stopword_additions",
        "single_custom_stopword_removals",
        "phrase_policy_label",
        "minimum_matches",
        "concreteness_abstract_max",
        "concreteness_concrete_min",
        "concreteness_exclude_proper",
        "concreteness_phrases",
        "concreteness_coverage_warning",
        "sensorimotor_exclude_proper",
        "sensorimotor_phrases",
        "sensorimotor_top_terms",
        "frequency_rare_below",
        "frequency_uncommon_below",
        "frequency_moderate_below",
        "frequency_very_common_min",
        "frequency_exclude_proper",
        "frequency_content_words_only",
        "frequency_lemma_fallback",
        "frequency_coverage_warning",
        "aoa_early_max",
        "aoa_later_min",
        "aoa_exclude_proper",
        "aoa_content_words_only",
        "aoa_lemma_fallback",
        "aoa_coverage_warning",
        "lexical_style_mattr_window",
        "lexical_style_hdd_sample",
        "lexical_style_mtld_threshold",
        "lexical_style_short_warning",
        "poetry_id_sources",
        "poetry_id_weightings",
        "poetry_id_views",
        "poetry_id_lexical_dimensions",
        "poetry_id_custom_thresholds",
        "poetry_id_valence_low",
        "poetry_id_valence_high",
        "poetry_id_arousal_low",
        "poetry_id_arousal_high",
        "poetry_id_dominance_low",
        "poetry_id_dominance_high",
        "poetry_id_min_tokens",
        "poetry_id_min_types",
        "poetry_id_min_token_coverage",
        "poetry_id_min_type_coverage",
        "pronunciation_coverage_warning",
        "pronunciation_minimum_complete_lines",
        "pronunciation_minimum_resolved_tokens",
        "meter_analysis_mode",
        "meter_style_profile",
        "meter_interpretation_depth",
        "meter_line_match_threshold",
        "meter_irregular_threshold",
        "meter_ambiguity_margin",
        "meter_maximum_variants",
        "meter_performance_candidate_limit",
        "meter_realized_alternatives",
        "meter_allow_visible_elision",
        "phonological_slant_threshold",
        "phonological_sound_repetitions",
        "phonological_coverage_warning",
        "phonological_maximum_pairs",
        "show_all_matched_results",
        "show_stopword_excluded_results",
    }
)


@dataclass(frozen=True)
class CustomAnalysisProfile:
    """One named, user-controlled snapshot of analytical widget settings."""

    name: str
    description: str
    base_profile: str
    settings: Mapping[str, Any]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "base_profile": self.base_profile,
            "settings": dict(self.settings),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def default_custom_profiles_path() -> Path:
    configured = os.environ.get("VERSEVAD_ANALYSIS_PROFILES_PATH")
    if configured:
        return Path(configured).expanduser()
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "private" / "analysis_profiles.json"


def _plain_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _plain_json_value(item) for key, item in value.items()
        }
    raise TypeError(f"Unsupported profile setting value: {type(value)!r}")


def normalize_profile_settings(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate retained widget labels without changing analytical choices."""

    normalized: dict[str, Any] = {}
    for key, value in settings.items():
        if key not in PROFILE_WIDGET_KEYS:
            continue
        plain_value = _plain_json_value(value)
        normalized[key] = (
            _PROFILE_VALUE_MIGRATIONS.get((key, plain_value), plain_value)
            if isinstance(plain_value, str)
            else plain_value
        )
    return normalized


def snapshot_profile_settings(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the analytical, non-text subset of current widget state."""

    snapshot: dict[str, Any] = {}
    for key in sorted(PROFILE_WIDGET_KEYS):
        if key not in state:
            continue
        try:
            snapshot[key] = normalize_profile_settings(
                {key: state[key]}
            )[key]
        except TypeError:
            continue
    return snapshot


def apply_profile_settings(
    target: MutableMapping[str, Any],
    settings: Mapping[str, Any],
) -> None:
    """Apply a validated profile snapshot without touching supplied text."""

    for key, value in normalize_profile_settings(settings).items():
        target[key] = value


def _profile_from_payload(
    name: str,
    payload: Mapping[str, Any],
) -> CustomAnalysisProfile | None:
    settings = payload.get("settings")
    if not isinstance(settings, Mapping):
        return None
    created_at = str(payload.get("created_at") or "")
    updated_at = str(payload.get("updated_at") or created_at)
    return CustomAnalysisProfile(
        name=name,
        description=str(payload.get("description") or ""),
        base_profile=str(payload.get("base_profile") or "Custom"),
        settings=normalize_profile_settings(settings),
        created_at=created_at,
        updated_at=updated_at,
    )


def load_custom_profiles(
    path: Path | str | None = None,
) -> dict[str, CustomAnalysisProfile]:
    profile_path = Path(path) if path is not None else default_custom_profiles_path()
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    profiles_payload = payload.get("profiles")
    if not isinstance(profiles_payload, Mapping):
        return {}
    profiles: dict[str, CustomAnalysisProfile] = {}
    for name, item in profiles_payload.items():
        if not isinstance(name, str) or not isinstance(item, Mapping):
            continue
        profile = _profile_from_payload(name, item)
        if profile is not None:
            profiles[name] = profile
    return dict(sorted(profiles.items(), key=lambda item: item[0].casefold()))


def _write_profiles(
    profiles: Mapping[str, CustomAnalysisProfile],
    profile_path: Path,
) -> Path:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = profile_path.with_suffix(profile_path.suffix + ".tmp")
    payload = {
        "version": CUSTOM_PROFILE_VERSION,
        "profiles": {
            name: profile.to_dict()
            for name, profile in sorted(
                profiles.items(), key=lambda item: item[0].casefold()
            )
        },
    }
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(profile_path)
    return profile_path


def save_custom_profile(
    name: str,
    settings: Mapping[str, Any],
    *,
    description: str = "",
    base_profile: str = "Custom",
    path: Path | str | None = None,
) -> CustomAnalysisProfile:
    clean_name = " ".join(name.split())
    if not clean_name:
        raise ValueError("Enter a name for the custom analysis profile.")
    if len(clean_name) > 80:
        raise ValueError("Custom analysis profile names must be 80 characters or fewer.")
    profile_path = Path(path) if path is not None else default_custom_profiles_path()
    profiles = load_custom_profiles(profile_path)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    existing = profiles.get(clean_name)
    profile = CustomAnalysisProfile(
        name=clean_name,
        description=description.strip(),
        base_profile=base_profile,
        settings=snapshot_profile_settings(settings),
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    profiles[clean_name] = profile
    _write_profiles(profiles, profile_path)
    return profile


def update_custom_profile(
    existing_name: str,
    name: str,
    settings: Mapping[str, Any],
    *,
    description: str = "",
    base_profile: str = "Custom",
    path: Path | str | None = None,
) -> CustomAnalysisProfile:
    """Update or rename one saved profile while preserving its creation time."""

    clean_existing_name = " ".join(existing_name.split())
    clean_name = " ".join(name.split())
    if not clean_name:
        raise ValueError("Enter a name for the custom analysis profile.")
    if len(clean_name) > 80:
        raise ValueError("Custom analysis profile names must be 80 characters or fewer.")
    profile_path = Path(path) if path is not None else default_custom_profiles_path()
    profiles = load_custom_profiles(profile_path)
    existing = profiles.get(clean_existing_name)
    if existing is None:
        raise ValueError("The selected custom analysis profile no longer exists.")
    if clean_name != clean_existing_name and clean_name in profiles:
        raise ValueError(
            "Another custom analysis profile already uses that name."
        )
    now = datetime.now(UTC).isoformat(timespec="seconds")
    updated = CustomAnalysisProfile(
        name=clean_name,
        description=description.strip(),
        base_profile=base_profile,
        settings=snapshot_profile_settings(settings),
        created_at=existing.created_at,
        updated_at=now,
    )
    del profiles[clean_existing_name]
    profiles[clean_name] = updated
    _write_profiles(profiles, profile_path)
    return updated


def delete_custom_profile(
    name: str,
    *,
    path: Path | str | None = None,
) -> bool:
    profile_path = Path(path) if path is not None else default_custom_profiles_path()
    profiles = load_custom_profiles(profile_path)
    if name not in profiles:
        return False
    del profiles[name]
    _write_profiles(profiles, profile_path)
    return True


__all__ = [
    "COMPARISON_PROFILE_SETTING_KEYS",
    "CUSTOM_PROFILE_VERSION",
    "PROFILE_WIDGET_KEYS",
    "CustomAnalysisProfile",
    "apply_profile_settings",
    "default_custom_profiles_path",
    "delete_custom_profile",
    "load_custom_profiles",
    "normalize_profile_settings",
    "save_custom_profile",
    "snapshot_profile_settings",
    "update_custom_profile",
]
