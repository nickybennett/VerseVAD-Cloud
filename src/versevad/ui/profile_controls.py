"""Shared post-analysis lexical scope and weighting controls."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from versevad.analysis_profiles import (
    DEFAULT_SCOPES,
    DEFAULT_WEIGHTINGS,
    SCOPE_ORDER,
    WEIGHTING_ORDER,
    AggregationWeighting,
    LexicalScope,
    ProfileSelection,
    canonical_scopes,
    canonical_weightings,
    coerce_scope,
    coerce_weighting,
)


@dataclass(frozen=True)
class ReportProfileState:
    selection: ProfileSelection
    active_annotation_scope: LexicalScope


def _keys(workspace_id: str) -> tuple[str, str, str, str]:
    prefix = f"{workspace_id}_report_profiles"
    return (
        f"{prefix}_scopes",
        f"{prefix}_weightings",
        f"{prefix}_annotation_scope",
        f"{prefix}_notice",
    )


def _scope_labels(scopes: tuple[LexicalScope, ...]) -> list[str]:
    return [scope.label for scope in scopes]


def _weighting_labels(weightings: tuple[AggregationWeighting, ...]) -> list[str]:
    return [weighting.label for weighting in weightings]


def _scope_from_label(label: str) -> LexicalScope:
    return next(scope for scope in SCOPE_ORDER if scope.label == label)


def _weighting_from_label(label: str) -> AggregationWeighting:
    return next(weighting for weighting in WEIGHTING_ORDER if weighting.label == label)


def _guard_nonempty(key: str, default_labels: list[str], notice_key: str) -> None:
    if not st.session_state.get(key):
        st.session_state[key] = list(default_labels)
        st.session_state[notice_key] = (
            "At least one option must remain selected; VerseVAD restored the ordinary default."
        )


def render_report_profile_controls(
    workspace_id: str,
    *,
    annotation_active: bool = False,
    initial_scopes: tuple[LexicalScope, ...] = DEFAULT_SCOPES,
    initial_weightings: tuple[AggregationWeighting, ...] = DEFAULT_WEIGHTINGS,
) -> ReportProfileState:
    """Render the sole user-facing authority for compatible report profiles."""

    initial_scopes = canonical_scopes(initial_scopes) or DEFAULT_SCOPES
    initial_weightings = canonical_weightings(initial_weightings) or DEFAULT_WEIGHTINGS
    scope_key, weighting_key, annotation_key, notice_key = _keys(workspace_id)
    scope_default = (
        _scope_labels(initial_scopes) if scope_key not in st.session_state else None
    )
    weighting_default = (
        _weighting_labels(initial_weightings)
        if weighting_key not in st.session_state
        else None
    )
    columns = st.columns(2)
    with columns[0]:
        st.multiselect(
            "Lexical scope",
            options=_scope_labels(SCOPE_ORDER),
            default=scope_default,
            key=scope_key,
            on_change=_guard_nonempty,
            args=(scope_key, _scope_labels(DEFAULT_SCOPES), notice_key),
            help=(
                "Choose one or more eligibility perspectives. Scope changes only "
                "cached report aggregation; it does not rerun the analysis."
            ),
        )
    with columns[1]:
        st.multiselect(
            "Aggregation weighting",
            options=_weighting_labels(WEIGHTING_ORDER),
            default=weighting_default,
            key=weighting_key,
            disabled=annotation_active,
            on_change=_guard_nonempty,
            args=(weighting_key, _weighting_labels(DEFAULT_WEIGHTINGS), notice_key),
            help=(
                "Token weighting retains repetition. Type weighting counts each "
                "documented metric-specific type identity once."
            ),
        )
    notice = st.session_state.pop(notice_key, None)
    if notice:
        st.caption(str(notice))

    scopes = tuple(_scope_from_label(label) for label in st.session_state[scope_key])
    weightings = tuple(
        _weighting_from_label(label) for label in st.session_state[weighting_key]
    )
    if annotation_active:
        st.caption(
            "Weighting applies to aggregate statistics. Interactive Annotation "
            "displays individual token occurrences."
        )
        if st.session_state.get(annotation_key) not in _scope_labels(scopes):
            st.session_state.pop(annotation_key, None)
        annotation_kwargs = (
            {} if annotation_key in st.session_state else {"index": 0}
        )
        st.selectbox(
            "Active annotation scope",
            options=_scope_labels(scopes),
            key=annotation_key,
            help=(
                "The poem remains fully visible. Only highlighting and annotation "
                "eligibility change with this scope."
            ),
            **annotation_kwargs,
        )
    elif st.session_state.get(annotation_key) not in _scope_labels(scopes):
        st.session_state[annotation_key] = _scope_labels(scopes)[0]

    return ReportProfileState(
        selection=ProfileSelection(scopes=scopes, weightings=weightings),
        active_annotation_scope=_scope_from_label(st.session_state[annotation_key]),
    )


def render_fixed_report_profile_controls(
    workspace_id: str,
    *,
    profile_name: str,
    lexical_scope: str,
    aggregation_weighting: str,
    explanation: str,
) -> None:
    """Show the global profile controls as read-only for a fixed methodology."""

    columns = st.columns(2)
    with columns[0]:
        st.multiselect(
            "Lexical scope",
            options=(lexical_scope,),
            default=(lexical_scope,),
            key=f"{workspace_id}_fixed_profile_scope",
            disabled=True,
            help=(
                f"{profile_name} fixes lexical eligibility so every result remains "
                "comparable."
            ),
        )
    with columns[1]:
        st.multiselect(
            "Aggregation weighting",
            options=(aggregation_weighting,),
            default=(aggregation_weighting,),
            key=f"{workspace_id}_fixed_profile_weighting",
            disabled=True,
            help=(
                f"{profile_name} fixes aggregation weighting so every result "
                "remains comparable."
            ),
        )
    st.caption(f"**{profile_name} (fixed):** {explanation}")


def report_profile_state(workspace_id: str) -> ReportProfileState:
    """Read a workspace's selection without rendering widgets."""

    scope_key, weighting_key, annotation_key, _notice_key = _keys(workspace_id)
    scope_labels = [
        label
        for label in st.session_state.get(scope_key, _scope_labels(DEFAULT_SCOPES))
        if label in _scope_labels(SCOPE_ORDER)
    ] or _scope_labels(DEFAULT_SCOPES)
    weighting_labels = [
        label
        for label in st.session_state.get(
            weighting_key,
            _weighting_labels(DEFAULT_WEIGHTINGS),
        )
        if label in _weighting_labels(WEIGHTING_ORDER)
    ] or _weighting_labels(DEFAULT_WEIGHTINGS)
    scopes = tuple(_scope_from_label(label) for label in scope_labels)
    weightings = tuple(
        _weighting_from_label(label) for label in weighting_labels
    )
    active_label = st.session_state.get(annotation_key)
    if active_label not in scope_labels:
        active_label = scope_labels[0]
    return ReportProfileState(
        selection=ProfileSelection(scopes=scopes, weightings=weightings),
        active_annotation_scope=_scope_from_label(active_label),
    )


def clear_report_profile_state(workspace_id: str) -> None:
    for key in _keys(workspace_id):
        st.session_state.pop(key, None)


__all__ = [
    "ReportProfileState",
    "clear_report_profile_state",
    "render_fixed_report_profile_controls",
    "render_report_profile_controls",
    "report_profile_state",
]
