"""Single-poem Streamlit presentation for Experiential Dynamics."""

from __future__ import annotations

from html import escape

import streamlit as st

from versevad.experiential_dynamics import (
    AssessmentTiming,
    DIMENSION_LABELS,
    DIMENSION_ORDER,
    ExperientialDynamicsMeasurements,
    ExperientialDynamicsResult,
    READER_QUESTIONS,
    dimension_explanation,
    score_assessment,
)


def _render_poem(title: str, original_text: str) -> None:
    st.markdown("#### Poem")
    st.caption(title)
    # Keep the poem inside one uninterrupted HTML block. Raw newlines—especially
    # blank or indented lines—can otherwise be reinterpreted by Markdown as
    # paragraphs or code blocks instead of remaining part of the poem.
    poem_html = escape(original_text).replace("\r\n", "\n").replace("\r", "\n")
    poem_html = poem_html.replace("\n", "<br>")
    st.markdown(
        (
            '<div style="border:1px solid var(--secondary-background-color);'
            'border-radius:0.75rem;padding:1.25rem 1.4rem;max-height:76vh;overflow:auto;'
            'position:sticky;top:5.5rem;white-space:pre-wrap;tab-size:4;'
            'overflow-wrap:break-word;font-family:inherit;font-size:1rem;line-height:1.65;'
            f'color:var(--text-color);background:transparent;">{poem_html}</div>'
        ),
        unsafe_allow_html=True,
    )


def render_experiential_assessment(
    *,
    title: str,
    original_text: str,
    measurements: ExperientialDynamicsMeasurements,
    assessment_timing: AssessmentTiming,
    key_prefix: str = "experiential_dynamics",
) -> ExperientialDynamicsResult | None:
    """Render all sixteen items without exposing the fixed measurements."""

    st.subheader("Experiential Dynamics")
    st.write(
        "Respond to the poem as a composed whole. The lexical measurements are "
        "already complete but remain hidden until this assessment is submitted."
    )
    st.caption(
        "Experimental reader-response framework · 16 items · 1-5 response scale"
    )
    poem_column, assessment_column = st.columns((2, 1), gap="large")
    with poem_column:
        _render_poem(title, original_text)
    with assessment_column:
        response_values: dict[str, int] = {}
        with st.form(f"{key_prefix}_form", border=True):
            for dimension in DIMENSION_ORDER:
                st.markdown(f"### {DIMENSION_LABELS[dimension]}")
                for question in (
                    item for item in READER_QUESTIONS if item.dimension == dimension
                ):
                    st.markdown(f"**{question.item_id}. {question.prompt}**")
                    value = st.selectbox(
                        f"Response for {question.item_id}",
                        options=(1, 2, 3, 4, 5),
                        index=None,
                        placeholder="Choose one response",
                        format_func=lambda item, q=question: (
                            f"{item} — {q.options[item - 1]}"
                        ),
                        key=f"experiential_dynamics_response_{question.item_id}",
                        label_visibility="collapsed",
                    )
                    if value is not None:
                        response_values[question.item_id] = int(value)
                if dimension != DIMENSION_ORDER[-1]:
                    st.divider()
            submitted = st.form_submit_button(
                "Submit Assessment and View Analysis",
                type="primary",
                width="stretch",
            )
        if submitted:
            if len(response_values) != len(READER_QUESTIONS):
                st.error("Complete all sixteen questions before submitting.")
                return None
            try:
                return score_assessment(
                    measurements,
                    response_values,
                    assessment_timing=assessment_timing,
                )
            except ValueError as error:
                st.error(str(error))
    return None


def render_experiential_result(
    result: ExperientialDynamicsResult,
    measurements: ExperientialDynamicsMeasurements,
) -> None:
    st.subheader("Experiential Dynamics")
    st.caption(
        "Experimental comparison of fixed lexical measurements with a structured "
        "reader assessment; it does not identify the cause of a difference."
    )
    st.markdown(f"### Dynamic Signature: {result.dynamic_signature}")
    st.markdown(f"**{result.compact_code}**")
    st.caption(
        f"Assessment timing: {result.assessment_timing.label} · "
        f"Agreement tolerance: ±{result.configuration.agreement_tolerance:.2f}"
    )

    for component in result.dimensions:
        with st.container(border=True):
            st.markdown(
                f"#### {DIMENSION_LABELS[component.dimension]}: "
                f"{component.relationship_label}"
            )
            columns = st.columns(4)
            columns[0].metric("Measured (0-1)", f"{component.measured_normalized:.3f}")
            columns[1].metric("Experienced (0-1)", f"{component.experienced_normalized:.3f}")
            columns[2].metric("Dynamic Gap", f"{component.dynamic_gap:+.3f}")
            columns[3].metric(
                "Response SD",
                f"{component.response_population_standard_deviation:.3f}",
            )
            st.write(dimension_explanation(component))
            if component.dimension == "concreteness":
                st.caption(
                    f"Measured source mean: {component.measured_source_value:.3f} "
                    "on the Brysbaert 1-5 scale; normalized here as (mean - 1) / 4."
                )
            else:
                st.caption(
                    "Measured value: NRC VAD Lexicon v2.1 normalized 0-1 mean. "
                    f"Experienced raw composite: {component.experienced_raw_mean:.3f}/5."
                )

    with st.expander("Assessment Responses and Methodology", expanded=False):
        st.write(
            "Consider whether sound, rhythm, repetition, syntax, imagery, narrative "
            "situation, or structure may contribute to a measured/experienced gap. "
            "These possibilities are interpretive prompts, not computed causes."
        )
        st.table(
            [
                {
                    "Item": response.item_id,
                    "Dimension": DIMENSION_LABELS[response.dimension],
                    "Response": response.numeric_value,
                    "Selected description": response.option_label,
                }
                for response in result.responses
            ]
        )
        st.caption(
            f"Methodology {result.configuration.methodology_version} · "
            f"Questionnaire {result.configuration.questionnaire_version} · "
            f"{result.configuration.profile.label} · fixed NRC VAD v2.1 and "
            "Brysbaert concreteness resources."
        )
        coverage_rows = []
        for item in measurements.dimensions:
            coverage = item.coverage
            coverage_rows.append(
                {
                    "Dimension": DIMENSION_LABELS[item.dimension],
                    "Resource": item.source_label,
                    "Matched": (
                        coverage.matched_token_count if coverage is not None else None
                    ),
                    "Eligible": (
                        coverage.eligible_token_count if coverage is not None else None
                    ),
                    "Token coverage": (
                        coverage.token_coverage if coverage is not None else None
                    ),
                }
            )
        st.table(coverage_rows)


def render_experiential_panel(
    *,
    title: str,
    original_text: str,
    measurements: ExperientialDynamicsMeasurements | None,
    result: ExperientialDynamicsResult | None,
) -> ExperientialDynamicsResult | None:
    """Render the post-analysis entry point or one completed result."""

    if result is not None and measurements is not None:
        render_experiential_result(result, measurements)
        return None
    if measurements is None or not measurements.available:
        reason = (
            measurements.unavailable_reason
            if measurements is not None
            else "This analysis predates Experiential Dynamics measurements."
        )
        st.info(
            "Experiential Dynamics is unavailable for this result. " + reason
        )
        return None
    st.subheader("Experiential Dynamics")
    st.write(
        "Optionally compare fixed lexical V/A/D/concreteness measurements with "
        "your structured impression of the poem as a whole. Because the report "
        "has already been exposed, this record will be labelled Post-analysis."
    )
    if not st.session_state.get("experiential_dynamics_post_assessment_open", False):
        if st.button(
            "Complete Experiential Dynamics Assessment",
            key="experiential_dynamics_open_post_assessment",
        ):
            st.session_state["experiential_dynamics_post_assessment_open"] = True
            st.rerun()
        return None
    return render_experiential_assessment(
        title=title,
        original_text=original_text,
        measurements=measurements,
        assessment_timing=AssessmentTiming.POST_ANALYSIS,
        key_prefix="experiential_dynamics_post",
    )


__all__ = [
    "render_experiential_assessment",
    "render_experiential_panel",
    "render_experiential_result",
]
