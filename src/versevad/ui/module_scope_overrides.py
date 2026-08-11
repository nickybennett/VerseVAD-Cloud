"""Streamlit controls for documented module-specific scope exceptions."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from versevad.analysis_profiles import ProfileSelection
from versevad.report_profile_overrides import (
    CONTENT_WORD_SCOPE_OVERRIDE_LABEL,
    CONTENT_WORD_SCOPE_OVERRIDE_TITLES,
    content_word_selection,
    modules_for_groups,
)


def _safe(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)


def _keys(workspace_id: str, group: str) -> tuple[str, str]:
    prefix = f"{_safe(workspace_id)}_content_scope_override_{_safe(group)}"
    return f"{prefix}_stored", f"{prefix}_widget"


def _persist_override(stored_key: str, widget_key: str) -> None:
    st.session_state[stored_key] = bool(st.session_state.get(widget_key, False))


def render_content_word_scope_override(
    workspace_id: str,
    group: str,
    selection: ProfileSelection,
) -> ProfileSelection:
    """Render one durable checkbox and return the effective module selection."""

    if group not in CONTENT_WORD_SCOPE_OVERRIDE_TITLES:
        raise ValueError(f"Unsupported content-word override group: {group}")
    stored_key, widget_key = _keys(workspace_id, group)
    if stored_key not in st.session_state:
        st.session_state[stored_key] = False
    if widget_key not in st.session_state:
        st.session_state[widget_key] = bool(st.session_state[stored_key])
    st.checkbox(
        CONTENT_WORD_SCOPE_OVERRIDE_LABEL,
        key=widget_key,
        on_change=_persist_override,
        args=(stored_key, widget_key),
        help=(
            "Use already-calculated content-word evidence for this module only. "
            "The global lexical scope remains unchanged; the module continues to "
            "inherit the globally selected token/type weighting."
        ),
    )
    active = bool(st.session_state.get(stored_key, False))
    if active:
        st.caption(
            "This section is using content words only and inherits the global "
            "aggregation weighting. Other report sections keep the global scope."
        )
    return content_word_selection(selection) if active else selection


def active_override_groups(workspace_id: str) -> frozenset[str]:
    return frozenset(
        group
        for group in CONTENT_WORD_SCOPE_OVERRIDE_TITLES
        if bool(st.session_state.get(_keys(workspace_id, group)[0], False))
    )


def active_override_modules(workspace_id: str) -> frozenset[str]:
    return modules_for_groups(active_override_groups(workspace_id))


def render_override_controls_for_groups(
    workspace_id: str,
    groups: Iterable[str],
    selection: ProfileSelection,
) -> frozenset[str]:
    """Render named exception controls and return every active module id."""

    for group in groups:
        st.markdown(f"**{CONTENT_WORD_SCOPE_OVERRIDE_TITLES[group]}**")
        render_content_word_scope_override(workspace_id, group, selection)
    return active_override_modules(workspace_id)


__all__ = [
    "active_override_groups",
    "active_override_modules",
    "render_content_word_scope_override",
    "render_override_controls_for_groups",
]
