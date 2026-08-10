"""Readable tables for canonical post-analysis lexical profiles."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from versevad.analysis_profiles import (
    ProfileSelection,
    display_profile_order,
    primary_display_profile,
)
from versevad.application import WorkspaceAnalysis
from versevad.ui.design import render_dataframe
from versevad.workspace_profiles import workspace_profile_metrics


def selected_profile_metrics(
    workspace: WorkspaceAnalysis,
    selection: ProfileSelection,
    *,
    module_ids: Iterable[str] = (),
):
    allowed = frozenset(module_ids)
    ordered_profiles = display_profile_order(selection)
    profile_rank = {
        profile: index for index, profile in enumerate(ordered_profiles)
    }
    rows = tuple(
        row
        for row in workspace_profile_metrics(workspace)
        if row.profile in profile_rank and (not allowed or row.module_id in allowed)
    )
    return tuple(sorted(rows, key=lambda row: profile_rank[row.profile]))


def primary_profile_metric(
    workspace: WorkspaceAnalysis,
    selection: ProfileSelection,
    *,
    module_id: str,
    metric_id: str | None = None,
    source_id: str | None = None,
):
    """Return the first currently selected row for a dashboard detail."""

    primary = primary_display_profile(selection)
    rows = selected_profile_metrics(
        workspace,
        selection,
        module_ids=(module_id,),
    )
    return next(
        (
            row
            for row in rows
            if row.profile == primary
            and (metric_id is None or row.metric_id == metric_id)
            and (source_id is None or row.source_id == source_id)
        ),
        None,
    )


def _height(length: int, maximum: int = 480) -> int:
    return min(maximum, 76 + 35 * length)


def render_configurable_profile_table(
    workspace: WorkspaceAnalysis,
    selection: ProfileSelection,
    *,
    module_ids: Iterable[str] = (),
    heading: str = "Selected Lexical Profiles",
) -> None:
    rows = selected_profile_metrics(workspace, selection, module_ids=module_ids)
    st.markdown(f"#### {heading}")
    if not rows:
        st.info("No compatible retained lexical evidence is available for this section.")
        return

    records = []
    for row in rows:
        per_100_unit = (
            "per 100 matched tokens"
            if row.profile.weighting.value == "TOKEN"
            else "per 100 matched types"
        )
        records.append(
            {
                "Source": row.source_label,
                "Metric": row.metric_label,
                "Module": row.module_id,
                "Profile": row.profile.label,
                "Primary Value": row.value,
                "Median": row.median,
                "Within-Text SD": row.population_standard_deviation,
                "First Quartile": row.first_quartile,
                "Third Quartile": row.third_quartile,
                "Minimum": row.minimum,
                "Maximum": row.maximum,
                "Cumulative Value": row.cumulative_value,
                "Load per 100 Observations": row.value_per_100_observations,
                "Above-Midpoint Load": row.above_midpoint_load,
                "Below-Midpoint Load": row.below_midpoint_load,
                "Net Midpoint Load": row.net_midpoint_load,
                "Absolute Midpoint Load": row.absolute_midpoint_load,
                "Above-Midpoint Load per 100": (
                    row.above_midpoint_load / row.observation_count * 100
                    if row.above_midpoint_load is not None and row.observation_count
                    else None
                ),
                "Below-Midpoint Load per 100": (
                    row.below_midpoint_load / row.observation_count * 100
                    if row.below_midpoint_load is not None and row.observation_count
                    else None
                ),
                "Net Midpoint Load per 100": (
                    row.net_midpoint_load / row.observation_count * 100
                    if row.net_midpoint_load is not None and row.observation_count
                    else None
                ),
                "Absolute Midpoint Load per 100": (
                    row.absolute_midpoint_load / row.observation_count * 100
                    if row.absolute_midpoint_load is not None and row.observation_count
                    else None
                ),
                "Per-100 Unit": per_100_unit,
                "Mean Absolute Deviation from Poem Mean": row.average_deviation_from_mean,
                "Observations": row.observation_count,
                "Eligible Tokens": row.coverage.eligible_token_count,
                "Matched Tokens": row.coverage.matched_token_count,
                "Unmatched Tokens": row.coverage.unmatched_token_count,
                "Token Coverage": row.coverage.token_coverage,
                "Eligible Types": row.coverage.eligible_type_count,
                "Matched Types": row.coverage.matched_type_count,
                "Unmatched Types": row.coverage.unmatched_type_count,
                "Type Coverage": row.coverage.type_coverage,
                "Excluded Stopwords": row.coverage.excluded_stopword_count,
                "Excluded Non-Content": row.coverage.excluded_non_content_count,
                "Phrase Matches": row.coverage.phrase_match_count,
                "Type Identity": row.coverage.type_identity_rule,
                "Unit": row.unit,
            }
        )
    frame = pd.DataFrame(records)

    primary = frame[
        ["Source", "Metric", "Profile", "Primary Value", "Median", "Observations", "Unit"]
    ]
    render_dataframe(
        primary.style.format(
            {"Primary Value": "{:.3f}", "Median": "{:.3f}"}, na_rep="—"
        ),
        hide_index=True,
        width="stretch",
        height=_height(len(primary)),
    )
    st.caption(
        "Primary Value is the selected-profile mean for continuous lexical metrics "
        "and the documented eligible-evidence proportion for categorical association "
        "metrics. Median is secondary and appears only where it is defined."
    )

    dispersion = frame[
        frame["Within-Text SD"].notna()
        | frame["First Quartile"].notna()
        | frame["Third Quartile"].notna()
    ]
    with st.expander("Within-Text Dispersion", expanded=False):
        if dispersion.empty:
            st.info(
                "No valid continuous dispersion estimate is available. Categorical "
                "associations do not have lexical-rating dispersion, and a single "
                "observation is insufficient to estimate spread."
            )
        else:
            columns = [
                "Source", "Metric", "Profile", "Within-Text SD", "First Quartile",
                "Third Quartile", "Minimum", "Maximum", "Observations", "Unit",
            ]
            render_dataframe(
                dispersion[columns].style.format(
                    {
                        "Within-Text SD": "{:.3f}",
                        "First Quartile": "{:.3f}",
                        "Third Quartile": "{:.3f}",
                        "Minimum": "{:.3f}",
                        "Maximum": "{:.3f}",
                    },
                    na_rep="—",
                ),
                hide_index=True,
                width="stretch",
                height=_height(len(dispersion), 420),
            )
            st.caption(
                "Population SD describes the spread of eligible matched continuous "
                "values within this text and profile; it is not uncertainty in the "
                "mean. Categorical association proportions are intentionally omitted."
            )

    cumulative = frame[frame["Cumulative Value"].notna()]
    vad_loads = frame[frame["Above-Midpoint Load"].notna()]
    if not cumulative.empty or not vad_loads.empty:
        with st.expander("Method-Defined Cumulative and Midpoint Loads", expanded=False):
            intensity = cumulative[cumulative["Module"] == "emotion_intensity"]
            other = cumulative[cumulative["Module"] != "emotion_intensity"]
            if not intensity.empty:
                st.markdown("**Cumulative Emotion Intensity Load**")
                columns = [
                    "Source", "Metric", "Profile", "Cumulative Value",
                    "Observations", "Unit",
                ]
                render_dataframe(
                    intensity[columns].style.format(
                        {"Cumulative Value": "{:.3f}"}, na_rep="—"
                    ),
                    hide_index=True,
                    width="stretch",
                    height=_height(len(intensity), 420),
                )
                st.caption(
                    "This raw sum accumulates supplied continuous word-emotion "
                    "intensity ratings. It is length-sensitive, not an association "
                    "count or a newly invented normalized density."
                )
            if not other.empty:
                st.markdown("**Method-defined cumulative loads**")
                columns = [
                    "Source", "Metric", "Profile", "Cumulative Value",
                    "Load per 100 Observations", "Per-100 Unit", "Observations", "Unit",
                ]
                render_dataframe(
                    other[columns].style.format(
                        {
                            "Cumulative Value": "{:.3f}",
                            "Load per 100 Observations": "{:.3f}",
                        },
                        na_rep="—",
                    ),
                    hide_index=True,
                    width="stretch",
                    height=_height(len(other), 420),
                )
                st.caption(
                    "Only modules with an explicit documented accumulation model "
                    "appear here. Token weighting retains repetition; type weighting "
                    "includes each distinct matched lexical type once."
                )
            if not vad_loads.empty:
                st.markdown("**VAD midpoint-deviation loads**")
                columns = [
                    "Source", "Metric", "Profile", "Above-Midpoint Load",
                    "Below-Midpoint Load", "Net Midpoint Load",
                    "Absolute Midpoint Load", "Above-Midpoint Load per 100",
                    "Below-Midpoint Load per 100", "Net Midpoint Load per 100",
                    "Absolute Midpoint Load per 100", "Per-100 Unit",
                ]
                render_dataframe(
                    vad_loads[columns].style.format(precision=3, na_rep="—"),
                    hide_index=True,
                    width="stretch",
                    height=_height(len(vad_loads), 420),
                )
                st.caption(
                    "Above and below loads sum distance from the normalized 0.5 "
                    "midpoint; net retains direction and absolute combines both sides. "
                    "Per-100 values use the matched token or type denominator named in "
                    "the table. Raw rating totals are intentionally not reported."
                )

    volatility = frame[frame["Mean Absolute Deviation from Poem Mean"].notna()]
    if not volatility.empty:
        with st.expander("Mean-Centered Lexical Volatility", expanded=False):
            columns = [
                "Source", "Metric", "Profile",
                "Mean Absolute Deviation from Poem Mean", "Within-Text SD", "Observations",
            ]
            render_dataframe(
                volatility[columns].style.format(precision=3, na_rep="—"),
                hide_index=True,
                width="stretch",
                height=_height(len(volatility), 420),
            )
            st.caption(
                "Mean absolute deviation is the average absolute distance from this "
                "text's own mean. Population SD squares departures and therefore gives "
                "more influence to large departures."
            )

    with st.expander("Coverage, Exclusions, and Denominators", expanded=False):
        columns = [
            "Source", "Metric", "Profile", "Eligible Tokens", "Matched Tokens",
            "Unmatched Tokens", "Token Coverage", "Eligible Types", "Matched Types",
            "Unmatched Types", "Type Coverage", "Excluded Stopwords",
            "Excluded Non-Content", "Phrase Matches", "Type Identity",
        ]
        coverage = frame[columns]
        render_dataframe(
            coverage.style.format(
                {"Token Coverage": "{:.1%}", "Type Coverage": "{:.1%}"}, na_rep="—"
            ),
            hide_index=True,
            width="stretch",
            height=_height(len(coverage), 500),
        )
        st.caption(
            "Excluded words are outside the selected scope and are not counted as "
            "unmatched. Token weighting counts retained occurrences; type weighting "
            "counts each distinct matched lexical identity once. Complete phrase "
            "matches remain intact."
        )
    st.caption(
        "All rows are reconstructed from completed token and resource evidence. "
        "Changing profiles does not repeat preprocessing or matching."
    )


__all__ = [
    "primary_profile_metric",
    "render_configurable_profile_table",
    "selected_profile_metrics",
]
