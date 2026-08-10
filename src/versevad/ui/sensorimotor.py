"""Streamlit presentation for Lancaster sensorimotor evidence."""

from __future__ import annotations

from dataclasses import asdict

import altair as alt
import pandas as pd
import streamlit as st

from versevad.lexical_semantic.sensorimotor import (
    DIMENSION_BY_ID,
    SensorimotorAnalysisResult,
)
from versevad.ui.design import (
    PUBLICATION_CHART_COLORS,
    publication_chart,
    render_dataframe,
)


def _decimal(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _percentage(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


@st.fragment
def render_sensorimotor(
    result: SensorimotorAnalysisResult | None,
    *,
    state_key_prefix: str,
    analysis_view: str = "Stopwords excluded",
    weighting: str = "token",
) -> None:
    """Render one completed result without rerunning the full report page."""

    if result is None:
        st.info(
            "Sensorimotor Imagery & Embodiment was not selected for this result. "
            "Enable the Lancaster profile under Choose Evidence, then analyze again."
        )
        return

    st.subheader("Sensorimotor Imagery & Embodiment")
    st.caption(
        "Lancaster ratings describe context-free normative associations between "
        "lexical concepts and six perceptual modalities or five bodily action "
        "effectors. They expose possibilities for close reading; they do not "
        "declare what the poem depicts, what its author intended, or what a reader feels."
    )
    st.caption(
        f"Detailed evidence follows the global {analysis_view} / "
        f"{weighting.title()}-weighted profile. Change it with the controls "
        "beneath Report Section."
    )
    profile = result.profile(analysis_view, weighting)
    per_100_label = (
        "Load per 100 matched tokens"
        if weighting == "token"
        else "Load per 100 matched types"
    )

    cards = st.columns(5)
    cards[0].metric(
        "Coverage",
        _percentage(profile.token_coverage),
        help=(
            f"{profile.matched_token_count} matched of "
            f"{profile.eligible_token_count} eligible token occurrences."
        ),
    )
    cards[1].metric(
        "Matched Observations",
        f"{profile.matched_observation_count:,}",
        help=(
            "A published multiword expression is one observation but all of its "
            "component tokens remain represented in token coverage."
        ),
    )
    cards[2].metric(
        "Overall Strength",
        _decimal(profile.overall_sensorimotor_strength.mean),
        help=(
            "Mean of the source's published Minkowski-3 composite across all "
            "eleven sensorimotor dimensions."
        ),
    )
    cards[3].metric(
        "Exclusivity",
        _decimal(profile.sensorimotor_exclusivity.mean),
        help=(
            "Mean source exclusivity. Higher values indicate concepts whose "
            "ratings are concentrated more strongly in fewer dimensions."
        ),
    )
    cards[4].metric(
        "Dominant-Profile Diversity",
        _decimal(profile.dominant_category_diversity),
        help=(
            "Normalized Shannon diversity from 0 to 1 across the concepts' "
            "strongest dimensions. Higher values indicate a more even spread."
        ),
    )

    with st.expander("What the Eleven Dimensions Mean", expanded=False):
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Dimension": dimension.label,
                        "Family": dimension.family.title(),
                        "Definition": dimension.definition,
                    }
                    for dimension in DIMENSION_BY_ID.values()
                ]
            ),
            hide_index=True,
            width="stretch",
            height=430,
        )
        st.caption(
            "Perceptual modalities: auditory, gustatory, haptic, interoceptive, "
            "olfactory, and visual. Action effectors: foot/leg, hand/arm, head, "
            "mouth/throat, and torso."
        )

    dimensions = pd.DataFrame(
        [
            {
                "Dimension": row.label,
                "Family": row.family.title(),
                "Mean": row.statistics.mean,
                "Population SD": row.statistics.population_standard_deviation,
                "Cumulative load": row.cumulative_load,
                per_100_label: row.load_per_100_observations,
                "Definition": DIMENSION_BY_ID[row.dimension_id].definition,
            }
            for row in profile.dimensions
        ]
    )
    st.markdown("#### Dimension Profile")
    chart = (
        alt.Chart(dimensions)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("Dimension:N", sort="-x", title=None),
            x=alt.X("Mean:Q", title="Mean normative strength (source 0–5)", scale=alt.Scale(domain=[0, 5])),
            color=alt.Color(
                "Family:N",
                scale=alt.Scale(
                    range=PUBLICATION_CHART_COLORS[:2],
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("Dimension:N"),
                alt.Tooltip("Family:N"),
                alt.Tooltip("Mean:Q", format=".3f"),
                alt.Tooltip("Population SD:Q", format=".3f"),
                alt.Tooltip("Cumulative load:Q", format=".3f"),
                alt.Tooltip(f"{per_100_label}:Q", format=".3f"),
                alt.Tooltip("Definition:N"),
            ],
        )
        .properties(height=390)
    )
    st.altair_chart(publication_chart(chart), width="stretch")
    render_dataframe(
        dimensions,
        hide_index=True,
        width="stretch",
        height=430,
        column_config={
            "Mean": st.column_config.NumberColumn(format="%.3f"),
            "Population SD": st.column_config.NumberColumn(format="%.3f"),
            "Cumulative load": st.column_config.NumberColumn(format="%.3f"),
            per_100_label: st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.caption(
        "Token weighting counts every matched occurrence, so repetition contributes; "
        "type weighting counts each distinct matched resource entry once. The per-100 "
        "value uses the matched token or matched type denominator named in the table. "
        "Population SD describes dispersion across matched source means."
    )

    st.markdown("#### Dominant Dimensions")
    dominance = pd.DataFrame(
        [
            {
                "Dimension": row.label,
                "Family": row.family.title(),
                "Count": row.count,
                "Proportion": row.proportion,
            }
            for row in profile.dominant_categories
        ]
    )
    dominance_chart = (
        alt.Chart(dominance)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("Dimension:N", sort="-x", title=None),
            x=alt.X("Proportion:Q", title="Share of matched observations", axis=alt.Axis(format="%")),
            color=alt.Color(
                "Family:N",
                scale=alt.Scale(range=PUBLICATION_CHART_COLORS[:2]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Dimension:N"),
                alt.Tooltip("Family:N"),
                alt.Tooltip("Count:Q", format=","),
                alt.Tooltip("Proportion:Q", format=".1%"),
            ],
        )
        .properties(height=390)
    )
    st.altair_chart(publication_chart(dominance_chart), width="stretch")
    st.caption(
        "The dominant dimension is the largest source rating for each concept. "
        "It is a compact orientation, not a claim that secondary dimensions are absent."
    )

    with st.expander("Trajectory by Line or Stanza", expanded=False):
        structural_controls = st.columns(2)
        scope = structural_controls[0].selectbox(
            "Structure",
            options=("line", "stanza"),
            format_func=str.title,
            key=f"{state_key_prefix}_structure_scope",
        )
        default_dimensions = [
            row.dimension_id
            for row in sorted(
                profile.dimensions,
                key=lambda item: (
                    item.statistics.mean is None,
                    -(item.statistics.mean or 0.0),
                ),
            )[:3]
        ]
        selected_dimensions = structural_controls[1].multiselect(
            "Dimensions to overlay",
            options=tuple(DIMENSION_BY_ID),
            default=default_dimensions,
            format_func=lambda item: DIMENSION_BY_ID[item].label,
            key=f"{state_key_prefix}_structure_dimensions",
            help="Choose a small set for a readable trajectory.",
        )
        summaries = [
            row
            for row in result.structural_summaries
            if row.analysis_view == analysis_view and row.scope == scope
        ]
        structural_rows = []
        for row in summaries:
            means = dict(row.dimension_means)
            for dimension_id in selected_dimensions:
                structural_rows.append(
                    {
                        "Ordinal": row.ordinal,
                        "Source text": row.source_text,
                        "Dimension": DIMENSION_BY_ID[dimension_id].label,
                        "Mean": means.get(dimension_id),
                        "Coverage": row.token_coverage,
                        "Matched observations": row.matched_observation_count,
                    }
                )
        structural_frame = pd.DataFrame(structural_rows)
        if structural_frame.empty or not selected_dimensions:
            st.info("Choose at least one dimension with available structural evidence.")
        else:
            trajectory = (
                alt.Chart(structural_frame)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Ordinal:Q", title=scope.title()),
                    y=alt.Y("Mean:Q", title="Mean normative strength", scale=alt.Scale(domain=[0, 5])),
                    color=alt.Color("Dimension:N"),
                    tooltip=[
                        alt.Tooltip("Ordinal:Q", format="d"),
                        alt.Tooltip("Source text:N"),
                        alt.Tooltip("Dimension:N"),
                        alt.Tooltip("Mean:Q", format=".3f"),
                        alt.Tooltip("Coverage:Q", format=".1%"),
                        alt.Tooltip("Matched observations:Q", format=","),
                    ],
                )
                .properties(height=390)
            )
            st.altair_chart(publication_chart(trajectory), width="stretch")

    with st.expander("Matched Concepts and Unmatched Vocabulary", expanded=False):
        term_rows = []
        for term in result.term_summaries:
            row = {
                "Source concept": term.source_term,
                "Occurrences": term.observation_count,
                "Dominant dimension": term.dominant_sensorimotor,
                "Overall strength": term.minkowski3_sensorimotor_strength,
                "Exclusivity": term.sensorimotor_exclusivity,
                "Observed forms": " | ".join(term.surface_forms),
                "POS": " | ".join(term.part_of_speech_tags),
            }
            row.update(
                {
                    dimension.label: getattr(
                        term.means,
                        dimension.dimension_id,
                    )
                    for dimension in DIMENSION_BY_ID.values()
                }
            )
            term_rows.append(row)
        render_dataframe(
            pd.DataFrame(term_rows),
            hide_index=True,
            width="stretch",
            height=460,
        )
        st.caption(
            f"{len(result.unmatched_tokens):,} eligible token occurrence(s) had no "
            "accepted source entry. These remain missing, not zero."
        )
        if result.unmatched_tokens:
            render_dataframe(
                pd.DataFrame([asdict(row) for row in result.unmatched_tokens]),
                hide_index=True,
                width="stretch",
                height=320,
            )

    with st.expander("Warnings, Method, and Provenance", expanded=False):
        for warning in result.module_result.warnings:
            st.info(warning.message)
        provenance = result.module_result.provenance
        st.markdown(
            f"**Module:** `{result.module_result.module_name}` "
            f"{result.module_result.module_version}  \n"
            f"**Configuration:** `{provenance.configuration_id}`  \n"
            f"**Lookup policy:** {provenance.lookup_policy}  \n"
            f"**Inclusion policy:** {provenance.inclusion_policy}"
        )
        st.code(
            result.resource_status.source_sha256,
            language=None,
        )
        st.caption(
            f"{result.resource_status.display_name} · "
            f"{result.configuration.scenario_id}"
        )
