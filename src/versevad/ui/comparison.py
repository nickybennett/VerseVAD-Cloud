"""Streamlit workspace for like-for-like contrastive poem evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from versevad.application import (
    AnalysisRequest,
    LEXICON_SPECS,
    ResourceReadiness,
    TextImportError,
    WorkspaceAnalysisError,
    decode_uploaded_text,
    run_workspace_analysis,
)
from versevad.comparison import PoemComparison, build_poem_comparison, comparison_rows
from versevad.exports.comparison import (
    export_poem_comparison_csv,
    export_poem_comparison_docx,
)
from versevad.models import PhrasePolicy
from versevad.preprocessing import TextPreprocessor
from versevad.ui.dataframes import heterogeneous_display_value
from versevad.ui.design import (
    PUBLICATION_CHART_COLORS,
    publication_chart,
    render_dataframe,
    render_empty_state,
    render_stateful_section_navigation,
    render_workspace_header,
)
from versevad.ui.stopwords import render_stopword_settings


_MODULE_LABELS = {
    "concreteness": "Concreteness",
    "frequency": "Frequency & rarity",
    "aoa": "Age of acquisition",
    "sensorimotor": "Sensorimotor imagery & embodiment",
    "lexical_style": "Lexical diversity & structural measures",
    "poetry_id": "PoetryID",
    "pronunciation": "Pronunciation & syllables",
    "meter": "Meter",
    "phonology": "Rhyme & recurring sound",
    "inherited_form": "Inherited-form comparison",
    "versemap": "VerseMap comparative context",
}
_REPORT_SECTIONS = (
    "Overview",
    "Affective Evidence",
    "Lexical Character, Imagery & Embodiment",
    "Cumulative Lexical Load",
    "Structure & Sound",
    "Comparative Context",
    "Complete Evidence Table",
    "Export & Interpretation",
)


def _safe_filename(value: str) -> str:
    filename = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value.strip()
    ).strip("_")
    return filename or "poem_comparison"


def _apply_uploaded_text(side: str) -> None:
    upload = st.session_state.get(f"compare_{side}_upload")
    if upload is None:
        return
    content = upload.getvalue()
    signature = hashlib.sha256(content).hexdigest()
    if st.session_state.get(f"compare_{side}_upload_signature") == signature:
        return
    try:
        text = decode_uploaded_text(upload.name, content)
    except TextImportError as error:
        st.session_state[f"compare_{side}_upload_error"] = str(error)
        return
    st.session_state[f"compare_{side}_text"] = text
    if not st.session_state.get(f"compare_{side}_title", "").strip():
        st.session_state[f"compare_{side}_title"] = Path(upload.name).stem
    st.session_state[f"compare_{side}_upload_signature"] = signature
    st.session_state.pop(f"compare_{side}_upload_error", None)


def _comparison_frame(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> pd.DataFrame:
    rows = comparison_rows(
        comparison,
        analysis_view=analysis_view,
        weighting=weighting,
    )
    data = pd.DataFrame([asdict(row) for row in rows])
    if data.empty:
        return data
    return data.rename(
        columns={
            "section": "Section",
            "source": "Source",
            "analysis_view": "Analysis View",
            "weighting": "Weighting",
            "metric_id": "Metric ID",
            "metric": "Metric",
            "value_a": "Poem A",
            "value_b": "Poem B",
            "difference_b_minus_a": "B minus A",
            "absolute_difference": "Absolute Difference",
            "unit_or_scale": "Unit or Scale",
            "denominator_a": "Poem A Denominator",
            "denominator_b": "Poem B Denominator",
            "coverage_a": "Poem A Coverage",
            "coverage_b": "Poem B Coverage",
            "note": "Interpretive Note",
        }
    )


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def _arrow_safe_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep heterogeneous analytical values from triggering Arrow coercion."""

    display = frame.copy()
    for column in ("Poem A", "Poem B"):
        if column in display:
            display[column] = display[column].map(
                heterogeneous_display_value
            )
    return display


def _render_section_chart(
    section_frame: pd.DataFrame,
    *,
    state_key: str,
    title_a: str,
    title_b: str,
) -> None:
    if section_frame.empty:
        render_empty_state(
            "No shared evidence is available in this section",
            "Enable the relevant modules and analyze both poems again.",
            "Return to Choose Shared Evidence and run the comparison again.",
        )
        return

    numeric = section_frame.copy()
    numeric["Poem A Numeric"] = numeric["Poem A"].map(_numeric)
    numeric["Poem B Numeric"] = numeric["Poem B"].map(_numeric)
    numeric = numeric[
        numeric["Poem A Numeric"].notna() | numeric["Poem B Numeric"].notna()
    ]
    if not numeric.empty:
        numeric["Chart Group"] = (
            numeric["Source"].fillna("")
            + " · "
            + numeric["Unit or Scale"].fillna("")
        )
        groups = tuple(dict.fromkeys(numeric["Chart Group"].tolist()))
        selected_group = st.selectbox(
            "Chart source and scale",
            options=groups,
            key=f"{state_key}_chart_group",
            help=(
                "VerseVAD charts only one source/scale group at a time. This "
                "prevents visually combining measurements that are not directly "
                "commensurate."
            ),
        )
        chart_rows = numeric[numeric["Chart Group"] == selected_group].head(30)
        long_rows = []
        for _, row in chart_rows.iterrows():
            if pd.notna(row["Poem A Numeric"]):
                long_rows.append(
                    {
                        "Metric": row["Metric"],
                        "Poem": title_a,
                        "Value": row["Poem A Numeric"],
                    }
                )
            if pd.notna(row["Poem B Numeric"]):
                long_rows.append(
                    {
                        "Metric": row["Metric"],
                        "Poem": title_b,
                        "Value": row["Poem B Numeric"],
                    }
                )
        if long_rows:
            chart = (
                alt.Chart(pd.DataFrame(long_rows))
                .mark_bar(cornerRadiusEnd=3)
                .encode(
                    y=alt.Y("Metric:N", title=None, sort=None),
                    x=alt.X("Value:Q", title=selected_group.split(" · ", 1)[-1]),
                    yOffset="Poem:N",
                    color=alt.Color(
                        "Poem:N",
                        scale=alt.Scale(range=PUBLICATION_CHART_COLORS[:2]),
                        legend=alt.Legend(orient="top"),
                    ),
                    tooltip=[
                        alt.Tooltip("Poem:N"),
                        alt.Tooltip("Metric:N"),
                        alt.Tooltip("Value:Q", format=".4f"),
                    ],
                )
                .properties(height=max(220, min(720, len(chart_rows) * 34)))
            )
            st.altair_chart(publication_chart(chart), width="stretch")

    display_columns = (
        "Source",
        "Metric",
        "Poem A",
        "Poem B",
        "B minus A",
        "Unit or Scale",
        "Poem A Denominator",
        "Poem B Denominator",
        "Poem A Coverage",
        "Poem B Coverage",
        "Interpretive Note",
    )
    render_dataframe(
        _arrow_safe_display_frame(section_frame[list(display_columns)]),
        hide_index=True,
        width="stretch",
        height=min(640, max(180, 38 * (len(section_frame) + 1))),
    )


@st.fragment
def _render_comparison_results(comparison: PoemComparison) -> None:
    title_a = comparison.first.request.title or "Poem A"
    title_b = comparison.second.request.title or "Poem B"
    controls = st.columns(2)
    scope_label = controls[0].selectbox(
        "Shared token scope",
        options=("All matched tokens", "Stopwords excluded"),
        key="compare_result_scope",
        help=(
            "This display choice is applied to both poems. The underlying run "
            "retains both the all-matched and stopword-excluded views."
        ),
    )
    weighting = controls[1].selectbox(
        "Shared weighting",
        options=("token", "type"),
        format_func=lambda value: f"{value.title()} weighted",
        key="compare_result_weighting",
        help=(
            "Token weighting retains repetition in both poems. Type weighting "
            "gives each distinct matched lexical entry one observation."
        ),
    )
    analysis_view = (
        "stopwords_excluded"
        if scope_label == "Stopwords excluded"
        else "all_matched"
    )
    frame = _comparison_frame(
        comparison,
        analysis_view=analysis_view,
        weighting=weighting,
    )

    selected_section, containers = render_stateful_section_navigation(
        "Report Section",
        _REPORT_SECTIONS,
        state_key="compare_report_section",
        container_key_prefix="compare_report",
        default="Overview",
        help_text="Choose one contrastive report section without rebuilding either analysis.",
        control="dropdown",
    )
    del selected_section

    with containers["Overview"]:
        st.subheader("Contrastive Overview")
        st.info(
            "Every displayed difference is Poem B minus Poem A. Positive means "
            "the recorded value is higher for B; negative means it is lower. "
            "These are descriptive differences, not significance tests or rankings."
        )
        cards = st.columns(4)
        cards[0].metric("Poem A", title_a)
        cards[1].metric("Poem B", title_b)
        cards[2].metric("Shared Metrics", f"{len(frame):,}")
        comparable = (
            int(frame["B minus A"].notna().sum()) if not frame.empty else 0
        )
        cards[3].metric("Numeric Differences", f"{comparable:,}")
        if frame.empty:
            render_empty_state(
                "No directly shared metrics were produced",
                "Select at least one common lexicon or analytical module and analyze again.",
                "Return to Choose Shared Evidence and run the comparison again.",
            )
        else:
            overview = (
                frame[frame["B minus A"].notna()]
                .sort_values("Absolute Difference", ascending=False)
                .head(20)
            )
            st.markdown("#### Largest Recorded Numeric Differences")
            st.caption(
                "This orientation table mixes scales and therefore must not be "
                "read as a ranking of importance. Use the source-specific sections "
                "for interpretation."
            )
            render_dataframe(
                overview[
                    [
                        "Section",
                        "Source",
                        "Metric",
                        "Poem A",
                        "Poem B",
                        "B minus A",
                        "Unit or Scale",
                    ]
                ],
                hide_index=True,
                width="stretch",
                height=min(620, max(180, 38 * (len(overview) + 1))),
            )

    for section in _REPORT_SECTIONS[1:-2]:
        with containers[section]:
            st.subheader(section)
            _render_section_chart(
                frame[frame["Section"] == section] if not frame.empty else frame,
                state_key=f"compare_{section.lower().replace(' ', '_').replace('&', 'and')}",
                title_a=title_a,
                title_b=title_b,
            )

    with containers["Complete Evidence Table"]:
        st.subheader("Complete Shared Evidence")
        st.caption(
            "The table preserves source, scale, method, coverage, denominator, "
            "and missingness. It is the safest starting point for reproducible comparison."
        )
        render_dataframe(
            _arrow_safe_display_frame(frame),
            hide_index=True,
            width="stretch",
            height=700,
        )

    with containers["Export & Interpretation"]:
        st.subheader("Export & Interpretation")
        st.write(
            "Download the complete machine-readable comparison or a narrative "
            "Word report. Both retain the selected shared scope and weighting."
        )
        stem = _safe_filename(f"{title_a}_versus_{title_b}")
        csv_content = export_poem_comparison_csv(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        docx_content = export_poem_comparison_docx(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        downloads = st.columns(2)
        downloads[0].download_button(
            "Download Comparison CSV",
            data=csv_content,
            file_name=f"VerseVAD_{stem}.csv",
            mime="text/csv",
            key="compare_download_csv",
            width="stretch",
        )
        downloads[1].download_button(
            "Download Narrative Word Report",
            data=docx_content,
            file_name=f"VerseVAD_{stem}.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key="compare_download_docx",
            width="stretch",
        )
        with st.expander("How to read a contrastive result", expanded=False):
            st.markdown(
                "- Compare values only within the same source, scale, scope, and weighting.\n"
                "- Read coverage and denominators before interpreting a difference.\n"
                "- Population standard deviation describes lexical dispersion within each poem; it is not uncertainty in the mean.\n"
                "- Cumulative load preserves repetition and length in the token view; the per-100 counterpart supports length-normalized comparison.\n"
                "- A missing value means the evidence was unavailable, not neutral."
            )


def render_compare_poems_workspace(
    preprocessor: TextPreprocessor,
    readiness: ResourceReadiness,
) -> None:
    """Render the non-persistent two-poem comparison workspace."""

    render_workspace_header(
        "Compare Poems",
        "Analyze two poems under one shared configuration, then inspect their "
        "affective, lexical, sensorimotor, structural, and contextual evidence "
        "side by side.",
        kicker="Contrastive evaluation for close reading",
        status="Session only",
    )
    st.caption(
        "VerseVAD reports comparable normative evidence and transparent "
        "descriptive differences. It does not score which poem is better, more "
        "emotional, more poetic, or more meaningful."
    )

    for side, default_title in (("a", "Poem A"), ("b", "Poem B")):
        st.session_state.setdefault(f"compare_{side}_title", default_title)
        st.session_state.setdefault(f"compare_{side}_text", "")

    with st.container(border=True):
        st.subheader("1. Add Two Poems")
        poem_columns = st.columns(2)
        for index, (side, label) in enumerate((("a", "Poem A"), ("b", "Poem B"))):
            with poem_columns[index]:
                st.markdown(f"#### {label}")
                st.file_uploader(
                    "Choose a UTF-8 plain-text file",
                    type=["txt"],
                    key=f"compare_{side}_upload",
                    on_change=_apply_uploaded_text,
                    args=(side,),
                )
                if st.session_state.get(f"compare_{side}_upload_error"):
                    st.error(st.session_state[f"compare_{side}_upload_error"])
                st.text_input(
                    "Title or working label",
                    key=f"compare_{side}_title",
                )
                st.text_area(
                    "Paste the poem exactly as it should be analyzed",
                    key=f"compare_{side}_text",
                    height=310,
                )

    available_lexicons = readiness.available_lexicon_ids
    lexicon_labels = {
        spec.lexicon_id: spec.display_name for spec in LEXICON_SPECS
    }
    default_lexicons = tuple(
        lexicon_id
        for lexicon_id in (
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        )
        if lexicon_id in available_lexicons
    )
    installed_modules = readiness.available_module_ids
    default_modules = tuple(
        module_id
        for module_id in (
            "concreteness",
            "frequency",
            "aoa",
            "sensorimotor",
            "lexical_style",
            "poetry_id",
            "versemap",
        )
        if module_id in installed_modules
    )

    with st.container(border=True):
        st.subheader("2. Choose Shared Evidence")
        selected_lexicons = st.multiselect(
            "Affective lexicons",
            options=available_lexicons,
            default=default_lexicons,
            format_func=lambda value: lexicon_labels.get(value, value),
            key="compare_lexicons",
            help="Every selected source is analyzed independently for both poems.",
        )
        selected_modules = st.multiselect(
            "Additional modules",
            options=installed_modules,
            default=default_modules,
            format_func=lambda value: _MODULE_LABELS.get(value, value),
            key="compare_modules",
            help=(
                "The same module configuration is applied to both poems. "
                "VADER and readability evidence are produced automatically."
            ),
        )
        st.caption(
            "Sensorimotor imagery is included by default when the Lancaster "
            "resource is installed. Sound/form modules may be added when CMUdict "
            "is available."
        )
        with st.expander("Shared stopword sensitivity settings", expanded=False):
            stopwords = render_stopword_settings("compare")

    with st.container(border=True):
        st.subheader("3. Analyze and Compare")
        analyze = st.button(
            "Analyze Both Poems",
            type="primary",
            width="stretch",
            key="compare_analyze",
        )
        if analyze:
            text_a = st.session_state["compare_a_text"]
            text_b = st.session_state["compare_b_text"]
            if not text_a.strip() or not text_b.strip():
                st.error("Add text for both Poem A and Poem B before analyzing.")
            else:
                selected = set(selected_modules)
                include_pronunciation = bool(
                    selected
                    & {"pronunciation", "meter", "phonology", "inherited_form"}
                )
                include_meter = bool(
                    selected & {"meter", "inherited_form"}
                )
                include_phonology = bool(
                    selected & {"phonology", "inherited_form"}
                )

                def request(side: str) -> AnalysisRequest:
                    return AnalysisRequest(
                        project_name="Contrastive evaluation",
                        title=st.session_state[f"compare_{side}_title"].strip()
                        or f"Poem {side.upper()}",
                        original_text=st.session_state[f"compare_{side}_text"],
                        lexicon_ids=tuple(selected_lexicons),
                        phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
                        stopword_mode=stopwords.mode,
                        protected_stopwords=stopwords.protected_words,
                        custom_stopword_additions=stopwords.custom_additions,
                        custom_stopword_removals=stopwords.custom_removals,
                        include_concreteness="concreteness" in selected,
                        include_frequency="frequency" in selected,
                        include_aoa="aoa" in selected,
                        include_sensorimotor="sensorimotor" in selected,
                        include_lexical_style="lexical_style" in selected,
                        include_poetry_id="poetry_id" in selected,
                        include_pronunciation=include_pronunciation,
                        include_meter=include_meter,
                        include_phonology=include_phonology,
                        include_inherited_form="inherited_form" in selected,
                        include_versemap="versemap" in selected,
                        analysis_cache_enabled=st.session_state.get(
                            "analysis_cache_enabled", True
                        ),
                        performance_diagnostics=st.session_state.get(
                            "performance_diagnostics_enabled", True
                        ),
                    )

                try:
                    with st.status(
                        "Analyzing both poems under one shared design…",
                        expanded=True,
                    ) as status:
                        st.write("Preparing Poem A and calculating selected evidence.")
                        first = run_workspace_analysis(
                            request("a"),
                            preprocessor=preprocessor,
                        )
                        st.write("Preparing Poem B with the same configuration.")
                        second = run_workspace_analysis(
                            request("b"),
                            preprocessor=preprocessor,
                        )
                        st.session_state["poem_comparison"] = (
                            build_poem_comparison(first, second)
                        )
                        status.update(
                            label="Contrastive analysis complete.",
                            state="complete",
                            expanded=False,
                        )
                except (ValueError, WorkspaceAnalysisError) as error:
                    st.error(str(error))

    comparison = st.session_state.get("poem_comparison")
    if isinstance(comparison, PoemComparison):
        _render_comparison_results(comparison)


__all__ = ["render_compare_poems_workspace"]
