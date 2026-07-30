"""Streamlit presentation for transparent PoetryID evidence."""

from __future__ import annotations

from collections.abc import Iterable

import altair as alt
import pandas as pd
import streamlit as st

from versevad.exports.poetry_id import export_poetry_id_bundle
from versevad.poetry_id import ARCHETYPES, PoetryIDAnalysisResult, VadLevel
from versevad.ui.design import (
    PUBLICATION_CHART_COLORS,
    publication_chart,
    render_dataframe,
)


_LEVEL_ORDER = (VadLevel.LOW, VadLevel.MODERATE, VadLevel.HIGH)
_ANALYSIS_VIEW_LABELS = {
    "all_matched": "All matched tokens (including stopwords)",
    "stopwords_excluded": "Stopwords excluded",
}
_WEIGHTING_LABELS = {
    "token": "Token-weighted",
    "type": "Type-weighted",
}


def _percentage(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _clear_invalid_widget_value(key: str, options: list[str]) -> None:
    if st.session_state.get(key) not in options:
        st.session_state.pop(key, None)


def _map_frame(assignment, dominance: VadLevel) -> pd.DataFrame:
    rank_by_id = {
        row.archetype_id: row.rank for row in assignment.neighbors[:3]
    }
    rows = []
    for arousal in reversed(_LEVEL_ORDER):
        row: dict[str, str] = {"Arousal": arousal.value.title()}
        for valence in _LEVEL_ORDER:
            archetype = next(
                item
                for item in ARCHETYPES
                if item.valence_level == valence
                and item.arousal_level == arousal
                and item.dominance_level == dominance
            )
            markers = []
            if (
                archetype.archetype_id
                == assignment.categorical_archetype.archetype_id
            ):
                markers.append("assigned")
            if archetype.archetype_id in rank_by_id:
                markers.append(f"neighbor #{rank_by_id[archetype.archetype_id]}")
            suffix = f"\n({', '.join(markers)})" if markers else ""
            row[valence.value.title()] = archetype.name.replace("The ", "") + suffix
        rows.append(row)
    return pd.DataFrame(rows).set_index("Arousal")


def _render_vad_scale(result: PoetryIDAnalysisResult, assignment) -> None:
    profile = result.configuration.threshold_profile
    score_rows = []
    threshold_rows = []
    for dimension in ("valence", "arousal", "dominance"):
        band = profile.dimensions[dimension]
        score_rows.append(
            {
                "Dimension": dimension.title(),
                "Score": getattr(assignment.vad, dimension),
                "Level": getattr(assignment, f"{dimension}_level").value,
            }
        )
        threshold_rows.extend(
            (
                {
                    "Dimension": dimension.title(),
                    "Boundary": band.low_max,
                    "Boundary kind": "Low maximum",
                },
                {
                    "Dimension": dimension.title(),
                    "Boundary": band.high_min,
                    "Boundary kind": "High minimum",
                },
            )
        )
    points = (
        alt.Chart(pd.DataFrame(score_rows))
        .mark_point(filled=True, size=150, color=PUBLICATION_CHART_COLORS[0])
        .encode(
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y(
                "Dimension:N",
                sort=["Valence", "Arousal", "Dominance"],
            ),
            tooltip=["Dimension", alt.Tooltip("Score:Q", format=".3f"), "Level"],
        )
    )
    boundaries = (
        alt.Chart(pd.DataFrame(threshold_rows))
        .mark_tick(thickness=2, size=30)
        .encode(
            x=alt.X("Boundary:Q", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y(
                "Dimension:N",
                sort=["Valence", "Arousal", "Dominance"],
            ),
            color=alt.Color(
                "Boundary kind:N",
                scale=alt.Scale(
                    domain=["Low maximum", "High minimum"],
                    range=[
                        PUBLICATION_CHART_COLORS[3],
                        PUBLICATION_CHART_COLORS[2],
                    ],
                ),
            ),
            tooltip=[
                "Dimension",
                "Boundary kind",
                alt.Tooltip("Boundary:Q", format=".3f"),
            ],
        )
    )
    st.altair_chart(
        publication_chart((boundaries + points).properties(height=180)),
        width="stretch",
    )
    st.caption(
        "Dots are the continuous normalized source-specific VAD means. "
        "Ticks show the inclusive low maximum and high minimum; values between "
        "them are moderate."
    )


def render_poetry_id(result: PoetryIDAnalysisResult | None) -> None:
    st.subheader("PoetryID")
    st.write(
        "PoetryID locates matched normative lexical VAD evidence among 27 "
        "documented candidate profiles. It does not identify the poem's "
        "emotion, speaker psychology, authorial intent, or reader response."
    )
    if result is None:
        st.info(
            "Enable PoetryID and select at least one VAD lexicon, then analyze "
            "the text."
        )
        return
    if result.unavailable:
        for item in result.unavailable:
            st.warning(item.message)
    if not result.assignments:
        st.info(
            "No PoetryID assignment is available. Review the selected VAD "
            "source, evidence minimums, and coverage."
        )
        return

    source_ids = _unique(
        item.source_analysis_id for item in result.assignments
    )
    source_labels = {
        item.source_analysis_id: item.source_lexicon_name
        for item in result.assignments
    }
    _clear_invalid_widget_value("poetry_id_source", source_ids)
    source_column, scope_column, weighting_column = st.columns(3)
    with source_column:
        selected_source = st.selectbox(
            "PoetryID VAD source",
            options=source_ids,
            format_func=lambda value: source_labels[value],
            key="poetry_id_source",
            disabled=len(source_ids) == 1,
            help=(
                "Each source-specific normalized VAD result remains separate; "
                "PoetryID does not create a consensus score."
            ),
        )

    source_assignments = [
        item
        for item in result.assignments
        if item.source_analysis_id == selected_source
    ]
    analysis_views = _unique(
        item.analysis_view for item in source_assignments
    )
    _clear_invalid_widget_value("poetry_id_analysis_view", analysis_views)
    with scope_column:
        selected_view = st.selectbox(
            "PoetryID token scope",
            options=analysis_views,
            format_func=lambda value: _ANALYSIS_VIEW_LABELS[value],
            key="poetry_id_analysis_view",
            disabled=len(analysis_views) == 1,
            help=(
                "All matched tokens includes matched stopwords. Stopwords "
                "excluded uses the pinned VerseVAD stopword policy. Unmatched "
                "vocabulary remains missing in both views."
            ),
        )

    scoped_assignments = [
        item
        for item in source_assignments
        if item.analysis_view == selected_view
    ]
    weighting_modes = _unique(
        item.weighting_mode for item in scoped_assignments
    )
    _clear_invalid_widget_value("poetry_id_weighting", weighting_modes)
    with weighting_column:
        selected_weighting = st.selectbox(
            "PoetryID weighting",
            options=weighting_modes,
            format_func=lambda value: _WEIGHTING_LABELS[value],
            key="poetry_id_weighting",
            disabled=len(weighting_modes) == 1,
        )
    assignment = next(
        item
        for item in scoped_assignments
        if item.weighting_mode == selected_weighting
    )

    st.markdown(
        "### Category Fit Archetype: "
        f"{assignment.categorical_archetype.name}"
    )
    st.caption(assignment.categorical_archetype.short_descriptor)
    st.write(assignment.narrative_summary)
    st.markdown(
        "**Nearest Centroid Archetype:** "
        f"{assignment.nearest_centroid_archetype.name}"
    )
    st.caption(
        assignment.nearest_centroid_archetype.short_descriptor
        + " The centroid result is a secondary continuous-distance comparison."
    )
    metrics = st.columns(4)
    metrics[0].metric("Valence", f"{assignment.vad.valence:.3f}")
    metrics[1].metric("Arousal", f"{assignment.vad.arousal:.3f}")
    metrics[2].metric("Dominance", f"{assignment.vad.dominance:.3f}")
    metrics[3].metric(
        "Confidence",
        assignment.confidence.label.replace("_", " ").title(),
    )
    st.caption(
        f"Levels: {assignment.valence_level.value} valence · "
        f"{assignment.arousal_level.value} arousal · "
        f"{assignment.dominance_level.value} dominance. "
        f"Token scope: {_ANALYSIS_VIEW_LABELS[assignment.analysis_view]}. "
        f"Weighting: {_WEIGHTING_LABELS[assignment.weighting_mode]}. "
        f"Threshold profile: {result.configuration.threshold_profile.name}. "
        f"VAD token coverage {_percentage(assignment.coverage.token_coverage)}; "
        f"type coverage {_percentage(assignment.coverage.type_coverage)}."
    )

    if not assignment.categorical_match:
        st.warning(
            "The primary category-fit archetype and secondary nearest "
            "Euclidean centroid differ. The category fit is "
            f"{assignment.categorical_archetype.name}; the nearest centroid is "
            f"{assignment.nearest_centroid_archetype.name}. Both are retained."
        )
    elif assignment.confidence.boundary_dimensions:
        st.warning(assignment.confidence.explanation)
    else:
        st.info(assignment.confidence.explanation)

    st.markdown("**VAD threshold scales**")
    _render_vad_scale(result, assignment)

    st.markdown("**Valence × arousal maps at each dominance level**")
    map_columns = st.columns(3)
    for column, dominance in zip(map_columns, _LEVEL_ORDER, strict=True):
        with column:
            st.caption(f"{dominance.value.title()} dominance")
            render_dataframe(
                _map_frame(assignment, dominance),
                width="stretch",
            )
    st.caption(
        "The assigned categorical cell and the three nearest centroids are "
        "marked. Valence runs low to high from left to right; arousal runs high "
        "to low from top to bottom."
    )

    st.markdown("**Nearest candidate profiles**")
    render_dataframe(
        pd.DataFrame(
            [
                {
                    "Rank": row.rank,
                    "Profile": row.archetype_name,
                    "Distance": row.distance,
                    "Relative affinity": row.affinity,
                }
                for row in assignment.neighbors[:5]
            ]
        ).style.format(
            {
                "Distance": "{:.3f}",
                "Relative affinity": "{:.2%}",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Relative affinities are inverse-distance comparisons normalized across "
        "all 27 centroids. They are not probabilities."
    )
    with st.expander("All 27 centroid distances"):
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Rank": row.rank,
                        "Profile": row.archetype_name,
                        "Distance": row.distance,
                        "Relative affinity": row.affinity,
                    }
                    for row in assignment.neighbors
                ]
            ).style.format(
                {
                    "Distance": "{:.3f}",
                    "Relative affinity": "{:.2%}",
                }
            ),
            hide_index=True,
            width="stretch",
        )

    if result.lexical_character:
        st.markdown("**Secondary lexical character**")
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Dimension": row.dimension_id.replace("_", " ").title(),
                        "Weighting": row.weighting_mode,
                        "Mean": row.statistics.mean,
                        "Median": row.statistics.median,
                        "Coverage": row.coverage,
                        "Unit": row.unit,
                        "Orientation": row.display_label,
                    }
                    for row in result.lexical_character
                ]
            ).style.format(
                {"Mean": "{:.3f}", "Median": "{:.3f}", "Coverage": "{:.1%}"},
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Concreteness, frequency, and age-of-acquisition descriptions are "
            "secondary. They never change the VAD archetype."
        )

    with st.expander("Method, coverage, and downloads"):
        st.write(
            f"Threshold profile: {result.configuration.threshold_profile.name} "
            f"({result.configuration.configuration_id}). Euclidean distance is "
            "calculated over the continuous 0–1 VAD means. Confidence is a "
            "documented rule-based evidence label, not a calibrated probability."
        )
        if assignment.coverage.unmatched_terms:
            st.write(
                "Frequent unmatched normalized terms: "
                + ", ".join(assignment.coverage.unmatched_terms)
            )
        bundle = export_poetry_id_bundle(result)
        for filename, content in bundle.items():
            st.download_button(
                f"Download {filename}",
                data=content,
                file_name=filename,
                mime=(
                    "text/csv"
                    if filename.endswith(".csv")
                    else (
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document"
                    )
                ),
                key=f"download_{filename}",
            )
        st.caption(
            "PoetryID exports CSV chart data and a narrative Word report."
        )

    st.warning(assignment.categorical_archetype.interpretive_caution)


__all__ = ["render_poetry_id"]
