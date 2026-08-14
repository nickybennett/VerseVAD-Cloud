"""Profile-aware detail views reconstructed from retained token audits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import pandas as pd
import streamlit as st

from versevad.analysis.statistics import descriptive_statistics
from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
    display_profile_order,
    phrase_adjusted_eligible_ids,
    scoped_token_ids,
)
from versevad.application import WorkspaceAnalysis
from versevad.models import (
    DescriptiveStatistics,
    MatchSelection,
    Phase2AnalysisResult,
    TokenRecord,
)
from versevad.ui.profile_tables import primary_profile_metric
from versevad.ui.design import render_dataframe
from versevad.workspace_profiles import WorkspaceProfileMetric


@dataclass(frozen=True)
class ProfileAuditObservation:
    token_ids: tuple[str, ...]
    value: float
    type_identity: str
    source_term: str
    surface_form: str
    line_number: int
    stanza_number: int
    part_of_speech: str
    source_row: object


@dataclass(frozen=True)
class ProfileGroupDetail:
    ordinal: int | str
    label: str
    statistics: DescriptiveStatistics
    observation_count: int


@dataclass(frozen=True)
class ContinuousProfileDetail:
    profile: AnalysisProfile
    metric: WorkspaceProfileMetric
    observations: tuple[ProfileAuditObservation, ...]
    statistics: DescriptiveStatistics
    line_summaries: tuple[ProfileGroupDetail, ...]
    stanza_summaries: tuple[ProfileGroupDetail, ...]
    part_of_speech_summaries: tuple[ProfileGroupDetail, ...]

    @property
    def values(self) -> tuple[float, ...]:
        return tuple(item.value for item in self.observations)

    @property
    def interquartile_range(self) -> float | None:
        if (
            self.statistics.first_quartile is None
            or self.statistics.third_quartile is None
        ):
            return None
        return self.statistics.third_quartile - self.statistics.first_quartile


def representative_contributors(
    detail: ContinuousProfileDetail,
    *,
    limit: int = 3,
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
    """Return deduplicated low/high lexical examples for the active profile."""

    grouped: dict[str, list[ProfileAuditObservation]] = {}
    for observation in detail.observations:
        identity = (observation.surface_form or observation.source_term).casefold()
        grouped.setdefault(identity, []).append(observation)
    records = []
    for observations in grouped.values():
        first = min(observations, key=lambda item: (item.line_number, item.stanza_number))
        records.append(
            {
                "Word / expression": first.surface_form or first.source_term,
                "Source entry": first.source_term,
                "Value": observations[0].value,
                "Occurrences": len(observations),
                "First line": first.line_number,
            }
        )
    ordered = sorted(
        records,
        key=lambda item: (float(item["Value"]), int(item["First line"])),
    )
    return tuple(ordered[:limit]), tuple(reversed(ordered[-limit:]))


def render_representative_contributors(
    detail: ContinuousProfileDetail | None,
    *,
    low_label: str,
    high_label: str,
    limit: int = 3,
) -> None:
    """Render a compact, profile-aligned evidence sample for close reading."""

    if detail is None or not detail.observations:
        return
    lowest, highest = representative_contributors(detail, limit=limit)
    st.markdown("**Representative lexical evidence**")
    columns = st.columns(2)
    for container, label, records in (
        (columns[0], low_label, lowest),
        (columns[1], high_label, highest),
    ):
        with container:
            st.caption(label)
            render_dataframe(
                pd.DataFrame(records),
                hide_index=True,
                width="stretch",
            )
    st.caption(
        f"Examples use **{detail.profile.label}**. Surface forms are deduplicated "
        "for display; Occurrences shows retained repetition. The complete audit "
        "preserves every contributing observation."
    )


def _workspace_tokens(workspace: WorkspaceAnalysis) -> tuple[TokenRecord, ...]:
    if workspace.poem_document is not None:
        return tuple(workspace.poem_document.tokens)
    return tuple(workspace.results[0].tokens) if workspace.results else ()


def _active_stopwords(workspace: WorkspaceAnalysis) -> tuple[str, ...]:
    return next(
        (
            tuple(result.stopword_policy.active_words)
            for result in workspace.results
            if result.stopword_policy is not None
        ),
        (),
    )


def select_detail_profile(
    selection: ProfileSelection,
    *,
    key: str,
) -> AnalysisProfile:
    profiles = display_profile_order(selection)
    if len(profiles) == 1:
        return profiles[0]
    labels = {profile.label: profile for profile in profiles}
    selected = st.selectbox(
        "Detailed profile",
        options=tuple(labels),
        key=key,
        help=(
            "The summary table above can show several profiles together. "
            "Choose which selected profile supplies the detailed distributions, "
            "rankings, and line or stanza summaries below."
        ),
    )
    # Streamlit can transiently return ``None`` (or a stale value no longer in
    # the current options) while restoring widget state during a rerun.  Every
    # caller needs a concrete profile, so use the first canonical enabled
    # profile as the deterministic fallback rather than leaking ``None`` into
    # shared Single Poem, Other Text, or comparison renderers.
    return labels.get(selected, profiles[0])


def _identity(row: object, attributes: Iterable[str]) -> str:
    return next(
        (
            str(getattr(row, attribute))
            for attribute in attributes
            if getattr(row, attribute, None)
        ),
        str(getattr(row, "token_id", "")),
    ).casefold()


def _token_ids(row: object) -> tuple[str, ...]:
    group = tuple(getattr(row, "match_group_token_ids", ()) or ())
    if group:
        return group
    token_id = str(getattr(row, "token_id", ""))
    return (token_id,) if token_id else ()


def _observations(
    *,
    tokens: Sequence[TokenRecord],
    audit_rows: Iterable[object],
    value_attribute: str,
    profile: AnalysisProfile,
    active_stopwords: Iterable[str],
    type_identity_attributes: tuple[str, ...],
) -> tuple[ProfileAuditObservation, ...]:
    candidates: list[ProfileAuditObservation] = []
    seen_groups: set[str] = set()
    for row in audit_rows:
        value = getattr(row, value_attribute, None)
        if not bool(getattr(row, "included", False)) or value is None:
            continue
        token_ids = _token_ids(row)
        group_id = str(
            getattr(row, "match_group_id", None)
            or getattr(row, "token_id", None)
            or "|".join(token_ids)
        )
        if group_id in seen_groups:
            continue
        seen_groups.add(group_id)
        candidates.append(
            ProfileAuditObservation(
                token_ids=token_ids,
                value=float(value),
                type_identity=_identity(row, type_identity_attributes),
                source_term=str(
                    getattr(row, "matched_source_term", None)
                    or getattr(row, "matched_lookup_form", None)
                    or getattr(row, "normalized_surface_type", None)
                    or getattr(row, "normalized_form", None)
                    or getattr(row, "surface_form", "")
                ),
                surface_form=str(getattr(row, "surface_form", "")),
                line_number=int(getattr(row, "line_number", 0) or 0),
                stanza_number=int(getattr(row, "stanza_number", 0) or 0),
                part_of_speech=str(getattr(row, "part_of_speech", "") or "Unknown"),
                source_row=row,
            )
        )

    base_eligible = scoped_token_ids(
        tokens,
        profile.scope,
        active_stopwords=active_stopwords,
    )
    eligible = phrase_adjusted_eligible_ids(
        base_eligible,
        (item.token_ids for item in candidates if len(item.token_ids) > 1),
    )
    scoped = tuple(
        item
        for item in candidates
        if set(item.token_ids).intersection(eligible)
        and (
            len(item.token_ids) == 1
            or set(item.token_ids).issubset(eligible)
        )
    )
    if profile.weighting is AggregationWeighting.TOKEN:
        return scoped
    by_type: dict[str, ProfileAuditObservation] = {}
    for item in scoped:
        by_type.setdefault(item.type_identity, item)
    return tuple(by_type.values())


def _group_details(
    observations: Sequence[ProfileAuditObservation],
    attribute: str,
) -> tuple[ProfileGroupDetail, ...]:
    grouped: dict[int | str, list[float]] = {}
    labels: dict[int | str, str] = {}
    for observation in observations:
        value = getattr(observation, attribute)
        grouped.setdefault(value, []).append(observation.value)
        labels[value] = str(value)
    return tuple(
        ProfileGroupDetail(
            ordinal=value,
            label=labels[value],
            statistics=descriptive_statistics(grouped[value]),
            observation_count=len(grouped[value]),
        )
        for value in sorted(grouped, key=lambda item: (str(type(item)), item))
    )


def continuous_profile_detail(
    workspace: WorkspaceAnalysis,
    selection: ProfileSelection,
    *,
    module_id: str,
    metric_id: str,
    audit_rows: Iterable[object],
    value_attribute: str,
    key: str,
    type_identity_attributes: tuple[str, ...] = (
        "matched_lookup_form",
        "matched_source_term",
        "normalized_form",
    ),
) -> ContinuousProfileDetail | None:
    profile = select_detail_profile(selection, key=key)
    metric = primary_profile_metric(
        workspace,
        ProfileSelection(
            scopes=(profile.scope,),
            weightings=(profile.weighting,),
        ),
        module_id=module_id,
        metric_id=metric_id,
    )
    if metric is None:
        return None
    observations = _observations(
        tokens=_workspace_tokens(workspace),
        audit_rows=audit_rows,
        value_attribute=value_attribute,
        profile=profile,
        active_stopwords=_active_stopwords(workspace),
        type_identity_attributes=type_identity_attributes,
    )
    return ContinuousProfileDetail(
        profile=profile,
        metric=metric,
        observations=observations,
        statistics=descriptive_statistics(item.value for item in observations),
        line_summaries=_group_details(observations, "line_number"),
        stanza_summaries=_group_details(observations, "stanza_number"),
        part_of_speech_summaries=_group_details(observations, "part_of_speech"),
    )


def affect_continuous_profile_detail(
    workspace: WorkspaceAnalysis,
    result: Phase2AnalysisResult,
    *,
    profile: AnalysisProfile | None,
    module_id: str,
    metric_id: str,
    value_getter: Callable[[object], float | None],
    type_identity_suffix: str = "",
) -> ContinuousProfileDetail | None:
    """Reconstruct source-specific continuous affect evidence for one profile."""

    if profile is None:
        return None
    selection = ProfileSelection(
        scopes=(profile.scope,),
        weightings=(profile.weighting,),
    )
    metric = primary_profile_metric(
        workspace,
        selection,
        module_id=module_id,
        metric_id=metric_id,
        source_id=result.lexicon_metadata.lexicon_id,
    )
    if metric is None:
        return None
    tokens = tuple(result.tokens)
    token_map = {token.token_id: token for token in tokens}
    candidates: list[ProfileAuditObservation] = []
    for match in result.matches:
        if (
            match.selection is not MatchSelection.INCLUDED
            or not match.included
        ):
            continue
        value = value_getter(match)
        if value is None:
            continue
        match_tokens = tuple(
            token_map[token_id]
            for token_id in match.token_ids
            if token_id in token_map
        )
        if not match_tokens:
            continue
        surface = " ".join(token.surface_form for token in match_tokens)
        identity = (
            match.matched_lookup_form
            or match.matched_term
            or match.match_id
        ).casefold()
        if type_identity_suffix:
            identity = f"{identity}:{type_identity_suffix.casefold()}"
        first_token = min(match_tokens, key=lambda token: token.token_position)
        candidates.append(
            ProfileAuditObservation(
                token_ids=tuple(match.token_ids),
                value=float(value),
                type_identity=identity,
                source_term=str(match.matched_term or match.matched_lookup_form or surface),
                surface_form=surface,
                line_number=match.line_number,
                stanza_number=match.stanza_number,
                part_of_speech=first_token.part_of_speech or "Unknown",
                source_row=match,
            )
        )
    base_eligible = scoped_token_ids(
        tokens,
        profile.scope,
        active_stopwords=_active_stopwords(workspace),
    )
    eligible = phrase_adjusted_eligible_ids(
        base_eligible,
        (item.token_ids for item in candidates if len(item.token_ids) > 1),
    )
    observations = tuple(
        item
        for item in candidates
        if set(item.token_ids).intersection(eligible)
        and (len(item.token_ids) == 1 or set(item.token_ids).issubset(eligible))
    )
    if profile.weighting is AggregationWeighting.TYPE:
        by_type: dict[str, ProfileAuditObservation] = {}
        for observation in observations:
            by_type.setdefault(observation.type_identity, observation)
        observations = tuple(by_type.values())
    return ContinuousProfileDetail(
        profile=profile,
        metric=metric,
        observations=observations,
        statistics=descriptive_statistics(item.value for item in observations),
        line_summaries=_group_details(observations, "line_number"),
        stanza_summaries=_group_details(observations, "stanza_number"),
        part_of_speech_summaries=_group_details(observations, "part_of_speech"),
    )


def categorical_affect_contributors(
    workspace: WorkspaceAnalysis,
    result: Phase2AnalysisResult,
    *,
    profile: AnalysisProfile | None,
    category: str,
    limit: int = 3,
) -> tuple[dict[str, object], ...]:
    """Return deterministic binary association contributors without fake strength."""

    if profile is None:
        return ()
    detail = affect_continuous_profile_detail(
        workspace,
        result,
        profile=profile,
        module_id="emotion_association",
        metric_id=f"{category}_association",
        value_getter=lambda match: (
            1.0 if category in getattr(match, "associations", ()) else None
        ),
        type_identity_suffix=category,
    )
    if detail is None:
        return ()
    grouped: dict[str, list[ProfileAuditObservation]] = {}
    for observation in detail.observations:
        grouped.setdefault(observation.type_identity, []).append(observation)
    records = []
    for observations in grouped.values():
        first = min(observations, key=lambda item: (item.line_number, item.stanza_number))
        records.append(
            {
                "Word / expression": first.surface_form or first.source_term,
                "Occurrences": len(observations),
                "First line": first.line_number,
            }
        )
    if profile.weighting is AggregationWeighting.TOKEN:
        records.sort(key=lambda item: (-int(item["Occurrences"]), int(item["First line"]), str(item["Word / expression"]).casefold()))
    else:
        records.sort(key=lambda item: (int(item["First line"]), str(item["Word / expression"]).casefold()))
    return tuple(records[:limit])


__all__ = [
    "affect_continuous_profile_detail",
    "categorical_affect_contributors",
    "ContinuousProfileDetail",
    "ProfileAuditObservation",
    "ProfileGroupDetail",
    "continuous_profile_detail",
    "render_representative_contributors",
    "representative_contributors",
    "select_detail_profile",
]
