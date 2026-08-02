"""Shared custom-analysis-profile controls for every analytical workspace."""

from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping, Sequence

import streamlit as st

from versevad.ui.profiles import (
    delete_custom_profile,
    load_custom_profiles,
    save_custom_profile,
    snapshot_profile_settings,
    update_custom_profile,
)


CUSTOM_PROFILE_LABEL_PREFIX = "Custom \u00b7 "
_SESSION_PROFILE_SETTINGS_KEY = "_session_custom_profiles"
_SESSION_PROFILE_METADATA_KEY = "_session_custom_profile_metadata"


def _hosted() -> bool:
    return os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") == "1"


def custom_profile_label(name: str) -> str:
    return f"{CUSTOM_PROFILE_LABEL_PREFIX}{name}"


def selected_custom_profile_name(label: object) -> str | None:
    if not isinstance(label, str) or not label.startswith(
        CUSTOM_PROFILE_LABEL_PREFIX
    ):
        return None
    name = label.removeprefix(CUSTOM_PROFILE_LABEL_PREFIX).strip()
    return name or None


def custom_profile_settings(
    state: MutableMapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the one shared profile registry for the current installation."""

    session_state = st.session_state if state is None else state
    if _hosted():
        session_state.setdefault(_SESSION_PROFILE_SETTINGS_KEY, {})
        return {
            name: dict(settings)
            for name, settings in session_state[
                _SESSION_PROFILE_SETTINGS_KEY
            ].items()
            if isinstance(name, str) and isinstance(settings, Mapping)
        }
    return {
        name: dict(profile.settings)
        for name, profile in load_custom_profiles().items()
    }


def analysis_profile_options(
    builtin_profile_names: Sequence[str],
    state: MutableMapping[str, Any] | None = None,
) -> list[str]:
    return [
        name for name in builtin_profile_names if name != "Custom"
    ] + [
        custom_profile_label(name)
        for name in sorted(
            custom_profile_settings(state),
            key=str.casefold,
        )
    ] + ["Custom"]


def consume_pending_profile_selection(
    *,
    scope_key: str,
    selection_state_key: str,
    options: Sequence[str],
) -> None:
    pending = st.session_state.pop(
        f"_pending_analysis_profile_selection__{scope_key}",
        None,
    )
    if pending in options:
        st.session_state[selection_state_key] = pending


def _profile_description(name: str | None) -> str:
    if not name:
        return ""
    if _hosted():
        metadata = st.session_state.get(_SESSION_PROFILE_METADATA_KEY, {})
        item = metadata.get(name, {}) if isinstance(metadata, Mapping) else {}
        return str(item.get("description") or "") if isinstance(item, Mapping) else ""
    profile = load_custom_profiles().get(name)
    return profile.description if profile is not None else ""


def _save_hosted_profile(
    *,
    name: str,
    settings: Mapping[str, Any],
    description: str,
    base_profile: str,
    existing_name: str | None = None,
) -> str:
    clean_name = " ".join(name.split())
    if not clean_name:
        raise ValueError("Enter a name for the custom analysis profile.")
    if len(clean_name) > 80:
        raise ValueError("Custom analysis profile names must be 80 characters or fewer.")
    profiles = st.session_state.setdefault(_SESSION_PROFILE_SETTINGS_KEY, {})
    metadata = st.session_state.setdefault(_SESSION_PROFILE_METADATA_KEY, {})
    if not isinstance(profiles, dict) or not isinstance(metadata, dict):
        raise TypeError("Hosted custom-profile storage is unavailable.")
    if existing_name is None and clean_name in profiles:
        raise ValueError(
            "A custom analysis profile already uses that name. Select it and "
            "use Update Selected instead."
        )
    if (
        existing_name is not None
        and clean_name != existing_name
        and clean_name in profiles
    ):
        raise ValueError(
            "Another custom analysis profile already uses that name."
        )
    if existing_name is not None:
        profiles.pop(existing_name, None)
        metadata.pop(existing_name, None)
    profiles[clean_name] = snapshot_profile_settings(settings)
    metadata[clean_name] = {
        "description": description.strip(),
        "base_profile": base_profile,
    }
    return clean_name


def _delete_profile(name: str) -> None:
    if _hosted():
        profiles = st.session_state.setdefault(_SESSION_PROFILE_SETTINGS_KEY, {})
        metadata = st.session_state.setdefault(_SESSION_PROFILE_METADATA_KEY, {})
        if isinstance(profiles, dict):
            profiles.pop(name, None)
        if isinstance(metadata, dict):
            metadata.pop(name, None)
        return
    delete_custom_profile(name)


def _queue_result(scope_key: str, *, selection: str, notice: str) -> None:
    st.session_state[
        f"_pending_analysis_profile_selection__{scope_key}"
    ] = selection
    st.session_state[f"_analysis_profile_notice__{scope_key}"] = notice
    st.rerun()


def render_custom_profile_manager(
    *,
    scope_key: str,
    selected_profile: str,
    selection_state_key: str,
    current_settings: Mapping[str, Any],
    builtin_profile_names: Sequence[str],
) -> None:
    """Render consistent add, update/rename, and delete controls."""

    notice = st.session_state.pop(
        f"_analysis_profile_notice__{scope_key}",
        None,
    )
    if notice:
        st.success(str(notice))
    selected_name = selected_custom_profile_name(selected_profile)
    name_key = f"custom_profile_name__{scope_key}"
    description_key = f"custom_profile_description__{scope_key}"
    tracked_selection_key = f"_managed_custom_profile__{scope_key}"
    if (
        st.session_state.get(tracked_selection_key) != selected_name
        or name_key not in st.session_state
        or description_key not in st.session_state
    ):
        st.session_state[name_key] = selected_name or ""
        st.session_state[description_key] = _profile_description(selected_name)
        st.session_state[tracked_selection_key] = selected_name

    with st.expander("Manage Custom Analysis Profiles", expanded=False):
        st.caption(
            "Profiles contain analytical settings only. They never contain "
            "poem text, metadata, pronunciation overrides, results, or exports."
        )
        profile_name = st.text_input("Custom profile name", key=name_key)
        profile_description = st.text_input(
            "Description (optional)",
            key=description_key,
        )
        add_column, update_column, delete_column = st.columns(3)
        add_profile = add_column.button(
            "Add as New",
            key=f"add_custom_profile__{scope_key}",
            width="stretch",
        )
        update_profile = update_column.button(
            "Update Selected",
            key=f"update_custom_profile__{scope_key}",
            width="stretch",
            disabled=selected_name is None,
        )
        delete_profile = delete_column.button(
            "Delete Selected",
            key=f"delete_custom_profile__{scope_key}",
            width="stretch",
            disabled=selected_name is None,
        )
        existing_settings = custom_profile_settings()
        builtin_names = set(builtin_profile_names)

        if add_profile:
            clean_name = " ".join(profile_name.split())
            if clean_name in builtin_names:
                st.error("Choose a name that is not one of the built-in profiles.")
            elif clean_name in existing_settings:
                st.error(
                    "A custom analysis profile already uses that name. Select "
                    "it and use Update Selected instead."
                )
            else:
                try:
                    if _hosted():
                        saved_name = _save_hosted_profile(
                            name=profile_name,
                            settings=current_settings,
                            description=profile_description,
                            base_profile=selected_profile,
                        )
                    else:
                        saved_name = save_custom_profile(
                            profile_name,
                            current_settings,
                            description=profile_description,
                            base_profile=selected_profile,
                        ).name
                    _queue_result(
                        scope_key,
                        selection=custom_profile_label(saved_name),
                        notice=(
                            "Custom analysis profile added for this hosted session."
                            if _hosted()
                            else "Custom analysis profile added locally."
                        ),
                    )
                except (OSError, TypeError, ValueError) as error:
                    st.error(str(error))

        if update_profile and selected_name is not None:
            clean_name = " ".join(profile_name.split())
            if clean_name in builtin_names:
                st.error("Choose a name that is not one of the built-in profiles.")
            else:
                try:
                    if _hosted():
                        saved_name = _save_hosted_profile(
                            existing_name=selected_name,
                            name=profile_name,
                            settings=current_settings,
                            description=profile_description,
                            base_profile=selected_profile,
                        )
                    else:
                        saved_name = update_custom_profile(
                            selected_name,
                            profile_name,
                            current_settings,
                            description=profile_description,
                            base_profile=selected_profile,
                        ).name
                    _queue_result(
                        scope_key,
                        selection=custom_profile_label(saved_name),
                        notice=(
                            "Custom analysis profile updated for this hosted session."
                            if _hosted()
                            else "Custom analysis profile updated locally."
                        ),
                    )
                except (OSError, TypeError, ValueError) as error:
                    st.error(str(error))

        if delete_profile and selected_name is not None:
            try:
                _delete_profile(selected_name)
                _queue_result(
                    scope_key,
                    selection="Custom",
                    notice="Custom analysis profile deleted.",
                )
            except (OSError, TypeError, ValueError) as error:
                st.error(str(error))

        st.caption(
            "Hosted custom profiles last only for the current session."
            if _hosted()
            else "Custom profiles persist locally and are shared by every analytical workspace."
        )


__all__ = [
    "CUSTOM_PROFILE_LABEL_PREFIX",
    "analysis_profile_options",
    "consume_pending_profile_selection",
    "custom_profile_label",
    "custom_profile_settings",
    "render_custom_profile_manager",
    "selected_custom_profile_name",
]
