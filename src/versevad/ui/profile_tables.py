"""Readable tables for canonical post-analysis lexical profiles."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from versevad.analysis_profiles import ProfileSelection
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
    profiles = frozenset(selection.profiles)
    return tuple(
        row
        for row in workspace_profile_metrics(workspace)
        if row.profile in profiles and (not allowed or row.module_id in allowed)
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
    frame = pd.DataFrame(
        [
            {
                "Source": row.source_label,
                "Metric": row.metric_label,
                "Profile": row.profile.label,
                "Value": row.value,
                "Within-Text SD": row.population_standard_deviation,
                "Cumulative Lexical Load": row.cumulative_value,
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
                "Mean Absolute Deviation from Poem Mean": (
                    row.average_deviation_from_mean
                ),
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
            for row in rows
        ]
    )
    primary = frame[["Source", "Metric", "Profile", "Value", "Observations", "Unit"]]
    render_dataframe(
        primary.style.format({"Value": "{:.3f}"}, na_rep="—"),
        hide_index=True,
        width="stretch",
        height=_height(len(primary)),
    )
    with st.expander("Within-Text Dispersion", expanded=False):
        dispersion = frame[
            ["Source", "Metric", "Profile", "Within-Text SD", "Observations", "Unit"]
        ]
        render_dataframe(
            dispersion.style.format({"Within-Text SD": "{:.3f}"}, na_rep="—"),
            hide_index=True,
            width="stretch",
            height=_height(len(dispersion), 420),
        )
        st.caption(
            "Population standard deviation describes the spread of eligible matched "
            "values within this text and profile; it is not uncertainty in the mean."
        )
    with st.expander("Cumulative Lexical Load", expanded=False):
        cumulative = frame[
            [
                "Source",
                "Metric",
                "Profile",
                "Cumulative Lexical Load",
                "Observations",
                "Unit",
            ]
        ]
        render_dataframe(
            cumulative.style.format(
                {"Cumulative Lexical Load": "{:.3f}"}, na_rep="—"
            ),
            hide_index=True,
            width="stretch",
            height=_height(len(cumulative), 420),
        )
        st.caption(
            "Raw cumulative loads sum the included observations. They retain length "
            "and, for token-weighted profiles, repetition."
        )
        vad_loads = frame[frame["Above-Midpoint Load"].notna()][
            [
                "Source",
                "Metric",
                "Profile",
                "Above-Midpoint Load",
                "Below-Midpoint Load",
                "Net Midpoint Load",
                "Absolute Midpoint Load",
                "Above-Midpoint Load per 100",
                "Below-Midpoint Load per 100",
                "Net Midpoint Load per 100",
                "Absolute Midpoint Load per 100",
            ]
        ]
        if not vad_loads.empty:
            st.markdown("**VAD midpoint-deviation loads**")
            render_dataframe(
                vad_loads.style.format(precision=3, na_rep="—"),
                hide_index=True,
                width="stretch",
                height=_height(len(vad_loads), 420),
            )
            st.caption(
                "Above and below loads sum distance from the normalized 0.5 "
                "midpoint; net retains direction and absolute combines both sides."
            )
    with st.expander("Mean-Centered Lexical Volatility", expanded=False):
        volatility = frame[frame["Mean Absolute Deviation from Poem Mean"].notna()][
            [
                "Source",
                "Metric",
                "Profile",
                "Mean Absolute Deviation from Poem Mean",
                "Within-Text SD",
                "Observations",
            ]
        ]
        render_dataframe(
            volatility.style.format(precision=3, na_rep="—"),
            hide_index=True,
            width="stretch",
            height=_height(len(volatility), 420),
        )
        st.caption(
            "Mean absolute deviation is the average absolute distance from this "
            "text's own mean. Population SD is the root-mean-square distance and "
            "therefore gives more influence to large departures."
        )
    with st.expander("Coverage, Exclusions, and Denominators", expanded=False):
        coverage = frame[
            [
                "Source",
                "Metric",
                "Profile",
                "Eligible Tokens",
                "Matched Tokens",
                "Unmatched Tokens",
                "Token Coverage",
                "Eligible Types",
                "Matched Types",
                "Unmatched Types",
                "Type Coverage",
                "Excluded Stopwords",
                "Excluded Non-Content",
                "Phrase Matches",
                "Type Identity",
            ]
        ]
        render_dataframe(
            coverage.style.format(
                {"Token Coverage": "{:.1%}", "Type Coverage": "{:.1%}"},
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
            height=_height(len(coverage), 500),
        )
        st.caption(
            "Excluded words are outside the selected scope and are not counted as "
            "unmatched. Complete phrase matches remain intact."
        )
    st.caption(
        "All rows are reconstructed from completed token and resource evidence. "
        "Changing profiles does not repeat preprocessing or matching."
    )


__all__ = ["render_configurable_profile_table", "selected_profile_metrics"]
