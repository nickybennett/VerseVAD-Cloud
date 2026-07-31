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
from versevad.comparison import (
    PoemComparison,
    PoemComparisonSet,
    build_poem_comparison,
    build_poem_comparison_set,
    comparison_rows,
    comparison_set_rows,
)
from versevad.exports.comparison import (
    export_poem_comparison_csv,
    export_poem_comparison_docx,
    export_poem_comparison_set_csv,
    export_poem_comparison_set_docx,
)
from versevad.models import PhrasePolicy
from versevad.preprocessing import TextPreprocessor
from versevad.ui.dataframes import heterogeneous_display_value
from versevad.ui.design import (
    MODULE_PRESETS,
    PUBLICATION_CHART_COLORS,
    publication_chart,
    preset_widget_state,
    render_dataframe,
    render_empty_state,
    render_stateful_section_navigation,
    render_workspace_header,
)
from versevad.ui.profiles import load_custom_profiles
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
    "Sound & Form",
    "Structure",
    "VerseMap",
    "Evidence & Diagnostics",
    "Export & Help",
)
_PANEL_ORDER = {
    "Affective Evidence": (
        "VAD Profile",
        "Emotion Association, Intensity & Sentiment",
        "PoetryID",
    ),
    "Lexical Character, Imagery & Embodiment": (
        "Concreteness",
        "Sensorimotor Imagery & Embodiment",
        "Frequency & Rarity",
        "Acquisition & Readability",
    ),
    "Sound & Form": (
        "Pronunciation, Syllables & Stress",
        "Candidate Meter & Rhythmic Regularity",
        "Rhyme & Recurring Sound",
        "Inherited Form Analysis",
    ),
    "Structure": (
        "Language Profile",
        "Lexical & Structural Measures",
    ),
    "VerseMap": ("VerseMap Comparative Profile",),
}
_PANEL_NOTES = {
    "VAD Profile": (
        "Compare source-specific VAD means, within-poem lexical dispersion, "
        "and cumulative lexical loads without merging lexicons."
    ),
    "Emotion Association, Intensity & Sentiment": (
        "Compare NRC association/intensity evidence and VADER polarity under "
        "their own definitions and denominators."
    ),
    "PoetryID": (
        "Compare PoetryID candidates and distances as descriptive profile "
        "evidence, not declarations of a poem's emotion or identity."
    ),
    "Concreteness": "Compare matched normative concreteness and its lexical load.",
    "Sensorimotor Imagery & Embodiment": (
        "Compare Lancaster perceptual-modality and action-effector evidence."
    ),
    "Frequency & Rarity": (
        "Compare SUBTLEX-US Zipf frequency and the inverse rarity orientation."
    ),
    "Acquisition & Readability": (
        "Compare normative AoA separately from prose-oriented readability formulas."
    ),
    "Pronunciation, Syllables & Stress": (
        "Compare only pronunciation-supported document summaries; unresolved "
        "words can reduce the available evidence."
    ),
    "Candidate Meter & Rhythmic Regularity": (
        "Compare nearest configured metrical candidates and rhythmic evidence, "
        "not definitive scansions."
    ),
    "Rhyme & Recurring Sound": (
        "Compare pronunciation-supported rhyme and recurring-sound evidence."
    ),
    "Inherited Form Analysis": (
        "Compare potential inherited-form matches, consistency, and evidence coverage."
    ),
    "Language Profile": "Compare model-assigned part-of-speech proportions.",
    "Lexical & Structural Measures": (
        "Compare lexical diversity, word length, and preserved line/stanza structure."
    ),
    "VerseMap Comparative Profile": (
        "Compare the two Standard Profile 1.0 records; VerseMap itself retains "
        "its fixed reference-corpus design."
    ),
}


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


def _report_location(
    metric_id: str,
) -> tuple[str, str]:
    prefix = metric_id.split(".", 1)[0]
    if prefix == "vad":
        return "Affective Evidence", "VAD Profile"
    if prefix in {"emotion", "emotion_intensity", "vader"}:
        return (
            "Affective Evidence",
            "Emotion Association, Intensity & Sentiment",
        )
    if prefix == "poetry_id":
        return "Affective Evidence", "PoetryID"
    if prefix == "concreteness":
        return "Lexical Character, Imagery & Embodiment", "Concreteness"
    if prefix == "sensorimotor":
        return (
            "Lexical Character, Imagery & Embodiment",
            "Sensorimotor Imagery & Embodiment",
        )
    if prefix in {"frequency", "rarity"}:
        return "Lexical Character, Imagery & Embodiment", "Frequency & Rarity"
    if prefix in {"aoa", "readability"}:
        return (
            "Lexical Character, Imagery & Embodiment",
            "Acquisition & Readability",
        )
    if prefix == "pronunciation":
        return "Sound & Form", "Pronunciation, Syllables & Stress"
    if prefix == "meter":
        return "Sound & Form", "Candidate Meter & Rhythmic Regularity"
    if prefix == "phonology":
        return "Sound & Form", "Rhyme & Recurring Sound"
    if prefix == "inherited_form":
        return "Sound & Form", "Inherited Form Analysis"
    if prefix == "pos":
        return "Structure", "Language Profile"
    if prefix == "lexical_style":
        return "Structure", "Lexical & Structural Measures"
    if prefix == "versemap":
        return "VerseMap", "VerseMap Comparative Profile"
    return "Evidence & Diagnostics", "Other Shared Evidence"


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
    frame = data.rename(
        columns={
            "section": "Section",
            "source": "Source",
            "analysis_view": "Analysis View",
            "weighting": "Weighting",
            "metric_id": "Metric ID",
            "metric": "Metric",
            "value_a": "Poem A",
            "value_b": "Poem B",
            "difference_b_minus_a": "B − A Difference",
            "absolute_difference": "Absolute Difference",
            "unit_or_scale": "Unit or Scale",
            "denominator_a": "Poem A Denominator",
            "denominator_b": "Poem B Denominator",
            "coverage_a": "Poem A Coverage",
            "coverage_b": "Poem B Coverage",
            "note": "Interpretive Note",
        }
    )
    locations = frame["Metric ID"].map(_report_location)
    frame.insert(
        0,
        "Report Section",
        [location[0] for location in locations],
    )
    frame.insert(
        1,
        "Report Panel",
        [location[1] for location in locations],
    )
    return frame


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def _arrow_safe_display_frame(
    frame: pd.DataFrame,
    *,
    value_columns: tuple[str, ...] = ("Poem A", "Poem B"),
) -> pd.DataFrame:
    """Keep heterogeneous analytical values from triggering Arrow coercion."""

    display = frame.copy()
    for column in value_columns:
        if column in display:
            display[column] = display[column].map(
                heterogeneous_display_value
            )
    return display


def _numeric_chart_frame(panel_frame: pd.DataFrame) -> pd.DataFrame:
    numeric = panel_frame.copy()
    numeric["Poem A Numeric"] = numeric["Poem A"].map(_numeric)
    numeric["Poem B Numeric"] = numeric["Poem B"].map(_numeric)
    numeric = numeric[
        numeric["Poem A Numeric"].notna() | numeric["Poem B Numeric"].notna()
    ]
    if numeric.empty:
        return numeric
    numeric["Chart Group"] = (
        numeric["Source"].fillna("")
        + " · "
        + numeric["Unit or Scale"].fillna("")
    )
    duplicate_metrics = numeric["Metric"].duplicated(keep=False)
    numeric["Chart Metric"] = numeric["Metric"]
    numeric.loc[duplicate_metrics, "Chart Metric"] = (
        numeric.loc[duplicate_metrics, "Metric"]
        + " · "
        + numeric.loc[duplicate_metrics, "Analysis View"]
    )
    return numeric


def _chart_domain(values: list[float]) -> list[float]:
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum
    padding = (
        span * 0.12
        if span > 0
        else max(abs(maximum) * 0.08, 0.05)
    )
    return [minimum - padding, maximum + padding]


def _render_scale_aware_chart(
    panel_frame: pd.DataFrame,
    *,
    state_key: str,
    title_a: str,
    title_b: str,
) -> None:
    numeric = _numeric_chart_frame(panel_frame)
    if numeric.empty:
        st.caption(
            "This subsection contains categorical or unavailable evidence, so "
            "its side-by-side table is more informative than a numeric chart."
        )
        return

    groups = tuple(dict.fromkeys(numeric["Chart Group"].tolist()))
    if len(groups) > 1:
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
    else:
        selected_group = groups[0]
        st.caption(f"Chart scale: {selected_group}")

    chart_rows = numeric[numeric["Chart Group"] == selected_group].head(16)
    visualization = st.segmented_control(
        "Visualization",
        options=("Side-by-Side Values", "B − A Difference"),
        default="Side-by-Side Values",
        key=f"{state_key}_visualization",
        help=(
            "The values view uses an automatically fitted scale and has no zero "
            "bar baseline. The difference view is centered on zero."
        ),
    )
    if visualization == "B − A Difference":
        differences = chart_rows[
            chart_rows["Poem A Numeric"].notna()
            & chart_rows["Poem B Numeric"].notna()
        ].copy()
        differences["Difference"] = (
            differences["Poem B Numeric"]
            - differences["Poem A Numeric"]
        )
        if differences.empty:
            st.caption("No paired numeric values are available for this chart group.")
            return
        maximum = max(
            float(differences["Difference"].abs().max()),
            0.001,
        )
        domain = [-maximum * 1.12, maximum * 1.12]
        zero_rule = (
            alt.Chart(pd.DataFrame({"zero": [0.0]}))
            .mark_rule(color="#777777", strokeWidth=1)
            .encode(x=alt.X("zero:Q", scale=alt.Scale(domain=domain)))
        )
        bars = (
            alt.Chart(differences)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                y=alt.Y("Chart Metric:N", title=None, sort=None),
                x=alt.X(
                    "Difference:Q",
                    title="B − A difference",
                    scale=alt.Scale(domain=domain, nice=True),
                ),
                color=alt.condition(
                    alt.datum.Difference >= 0,
                    alt.value(PUBLICATION_CHART_COLORS[1]),
                    alt.value(PUBLICATION_CHART_COLORS[0]),
                ),
                tooltip=[
                    alt.Tooltip("Chart Metric:N", title="Metric"),
                    alt.Tooltip("Difference:Q", title="B − A", format=".3f"),
                    alt.Tooltip("Poem A Numeric:Q", title=title_a, format=".3f"),
                    alt.Tooltip("Poem B Numeric:Q", title=title_b, format=".3f"),
                ],
            )
        )
        chart = (zero_rule + bars).properties(
            height=max(220, min(600, len(differences) * 34))
        )
    else:
        long_rows = []
        connector_rows = []
        for _, row in chart_rows.iterrows():
            value_a = row["Poem A Numeric"]
            value_b = row["Poem B Numeric"]
            if pd.notna(value_a):
                long_rows.append(
                    {
                        "Metric": row["Chart Metric"],
                        "Poem": title_a,
                        "Value": value_a,
                    }
                )
            if pd.notna(value_b):
                long_rows.append(
                    {
                        "Metric": row["Chart Metric"],
                        "Poem": title_b,
                        "Value": value_b,
                    }
                )
            if pd.notna(value_a) and pd.notna(value_b):
                connector_rows.append(
                    {
                        "Metric": row["Chart Metric"],
                        "Poem A": value_a,
                        "Poem B": value_b,
                    }
                )
        values = [float(row["Value"]) for row in long_rows]
        domain = _chart_domain(values)
        points = (
            alt.Chart(pd.DataFrame(long_rows))
            .mark_point(filled=True, size=115)
            .encode(
                y=alt.Y("Metric:N", title=None, sort=None),
                x=alt.X(
                    "Value:Q",
                    title=selected_group.split(" · ", 1)[-1],
                    scale=alt.Scale(domain=domain, zero=False, nice=True),
                ),
                color=alt.Color(
                    "Poem:N",
                    scale=alt.Scale(range=PUBLICATION_CHART_COLORS[:2]),
                    legend=alt.Legend(orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("Poem:N"),
                    alt.Tooltip("Metric:N"),
                    alt.Tooltip("Value:Q", format=".3f"),
                ],
            )
        )
        if connector_rows:
            connectors = (
                alt.Chart(pd.DataFrame(connector_rows))
                .mark_rule(color="#8b8b8b", opacity=0.5)
                .encode(
                    y=alt.Y("Metric:N", title=None, sort=None),
                    x=alt.X(
                        "Poem A:Q",
                        scale=alt.Scale(domain=domain, zero=False, nice=True),
                    ),
                    x2="Poem B:Q",
                )
            )
            chart = connectors + points
        else:
            chart = points
        chart = chart.properties(
            height=max(220, min(600, len(chart_rows) * 34))
        )
    st.altair_chart(publication_chart(chart), width="stretch")


def _render_comparison_panel(
    label: str,
    panel_frame: pd.DataFrame,
    *,
    state_key: str,
    title_a: str,
    title_b: str,
) -> None:
    with st.expander(label, expanded=False):
        st.caption(_PANEL_NOTES.get(label, "Shared comparison evidence."))
        _render_scale_aware_chart(
            panel_frame,
            state_key=state_key,
            title_a=title_a,
            title_b=title_b,
        )

        display_columns = (
            "Source",
            "Metric",
            "Poem A",
            "Poem B",
            "B − A Difference",
            "Unit or Scale",
            "Poem A Denominator",
            "Poem B Denominator",
            "Poem A Coverage",
            "Poem B Coverage",
            "Interpretive Note",
        )
        render_dataframe(
            _arrow_safe_display_frame(panel_frame[list(display_columns)]),
            hide_index=True,
            width="stretch",
            height=min(560, max(180, 38 * (len(panel_frame) + 1))),
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
            int(frame["B − A Difference"].notna().sum())
            if not frame.empty
            else 0
        )
        cards[3].metric("Numeric Differences", f"{comparable:,}")
        if frame.empty:
            render_empty_state(
                "No directly shared metrics were produced",
                "Select at least one common lexicon or analytical module and analyze again.",
                "Return to Choose Shared Evidence and run the comparison again.",
            )
        else:
            core_metric_ids = (
                r"^vad\..*\.mean$|^concreteness\.mean$|^rarity\.mean$|"
                r"^aoa\.mean$|^lexical_style\..*statistics\.mean$|"
                r"^lexical_style\.mean_alphabetic_characters_per_token$"
            )
            overview = frame[
                frame["Metric ID"].str.contains(
                    core_metric_ids,
                    regex=True,
                    na=False,
                )
            ].head(14)
            st.markdown("#### Core Comparison Snapshot")
            st.caption(
                "A compact orientation only. Open the matching report subsection "
                "for its chart, dispersion, cumulative load, coverage, and cautions."
            )
            render_dataframe(
                _arrow_safe_display_frame(
                    overview[
                        [
                            "Source",
                            "Metric",
                            "Poem A",
                            "Poem B",
                            "B − A Difference",
                            "Unit or Scale",
                        ]
                    ]
                ),
                hide_index=True,
                width="stretch",
                height=min(620, max(180, 38 * (len(overview) + 1))),
            )
            with st.expander("Shared Analysis Design", expanded=False):
                st.write(
                    f"Token scope: **{scope_label}**  \n"
                    f"Weighting: **{weighting.title()} weighted**  \n"
                    f"Comparison ID: `{comparison.comparison_id}`"
                )
                st.caption(
                    "Both poems were analyzed with the same sources, matching "
                    "policy, stopword policy, and enabled-module configurations."
                )

    for section, panel_order in _PANEL_ORDER.items():
        with containers[section]:
            st.subheader(section)
            section_frame = (
                frame[frame["Report Section"] == section]
                if not frame.empty
                else frame
            )
            for panel_index, panel in enumerate(panel_order):
                panel_frame = (
                    section_frame[section_frame["Report Panel"] == panel]
                    if not section_frame.empty
                    else section_frame
                )
                if panel_frame.empty:
                    with st.expander(panel, expanded=False):
                        st.info(
                            "No shared result is available for this subsection. "
                            "Enable its required sources/modules and analyze both "
                            "poems again."
                        )
                    continue
                _render_comparison_panel(
                    panel,
                    panel_frame,
                    state_key=(
                        f"compare_{section.lower().replace(' ', '_').replace('&', 'and')}"
                        f"_{panel_index}"
                    ),
                    title_a=title_a,
                    title_b=title_b,
                )

    with containers["Evidence & Diagnostics"]:
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

    with containers["Export & Help"]:
        st.subheader("Export & Help")
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


def _render_legacy_binary_comparison_workspace(
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


def _comparison_set_poem_ids() -> list[str]:
    poem_ids = st.session_state.setdefault(
        "compare_poem_ids",
        ["poem_1", "poem_2"],
    )
    if not isinstance(poem_ids, list) or not 2 <= len(poem_ids) <= 10:
        poem_ids = ["poem_1", "poem_2"]
        st.session_state["compare_poem_ids"] = poem_ids
    st.session_state.setdefault("compare_next_poem_number", len(poem_ids) + 1)
    for position, poem_id in enumerate(poem_ids, start=1):
        st.session_state.setdefault(
            f"compare_{poem_id}_title",
            f"Poem {position}",
        )
        st.session_state.setdefault(f"compare_{poem_id}_text", "")
    return poem_ids


def _add_comparison_poem() -> None:
    poem_ids = list(st.session_state.get("compare_poem_ids", []))
    if len(poem_ids) >= 10:
        return
    next_number = int(st.session_state.get("compare_next_poem_number", 3))
    poem_id = f"poem_{next_number}"
    st.session_state["compare_next_poem_number"] = next_number + 1
    poem_ids.append(poem_id)
    st.session_state["compare_poem_ids"] = poem_ids
    st.session_state[f"compare_{poem_id}_title"] = f"Poem {len(poem_ids)}"
    st.session_state[f"compare_{poem_id}_text"] = ""
    st.session_state.pop("poem_comparison_set", None)


def _remove_comparison_poem(poem_id: str) -> None:
    poem_ids = list(st.session_state.get("compare_poem_ids", []))
    if len(poem_ids) <= 2 or poem_id not in poem_ids:
        return
    poem_ids.remove(poem_id)
    st.session_state["compare_poem_ids"] = poem_ids
    for suffix in ("title", "text", "upload", "upload_error"):
        st.session_state.pop(f"compare_{poem_id}_{suffix}", None)
    st.session_state.pop("poem_comparison_set", None)


def _clear_comparison_set() -> None:
    for poem_id in list(st.session_state.get("compare_poem_ids", [])):
        st.session_state[f"compare_{poem_id}_text"] = ""
        st.session_state[f"compare_{poem_id}_title"] = ""
        st.session_state.pop(f"compare_{poem_id}_upload", None)
        st.session_state.pop(f"compare_{poem_id}_upload_error", None)
    st.session_state.pop("poem_comparison_set", None)


def _comparison_set_labels(comparison_set: PoemComparisonSet) -> list[str]:
    bases = [
        analysis.request.title.strip() or f"Poem {position}"
        for position, analysis in enumerate(
            comparison_set.analyses,
            start=1,
        )
    ]
    totals: dict[str, int] = {}
    for base in bases:
        totals[base] = totals.get(base, 0) + 1
    seen: dict[str, int] = {}
    labels = []
    for base in bases:
        seen[base] = seen.get(base, 0) + 1
        labels.append(
            f"{base} ({seen[base]})" if totals[base] > 1 else base
        )
    return labels


def _comparison_set_frame(
    comparison_set: PoemComparisonSet,
    *,
    analysis_view: str,
    weighting: str,
) -> pd.DataFrame:
    labels = _comparison_set_labels(comparison_set)
    records = []
    for row in comparison_set_rows(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
    ):
        report_section, report_panel = _report_location(row.metric_id)
        if report_panel == "PoetryID" and row.metric_id not in {
            "poetry_id.categorical_archetype_id",
            "poetry_id.nearest_centroid_archetype_id",
        }:
            continue
        metric_label = {
            "poetry_id.categorical_archetype_id": "Category Fit Archetype",
            "poetry_id.nearest_centroid_archetype_id": (
                "Nearest Centroid Archetype"
            ),
        }.get(row.metric_id, row.metric)
        record = {
            "Report Section": report_section,
            "Report Panel": report_panel,
            "Source": row.source,
            "Metric": metric_label,
            "Metric ID": row.metric_id,
            "Analysis View": row.analysis_view.replace("_", " ").title(),
            "Weighting": row.weighting.title(),
            "Unit or Scale": row.unit_or_scale,
            "Equal-Poem Mean": row.numeric_mean,
            "Poem-Level SD": row.numeric_population_standard_deviation,
            "Poems Contributing": row.contributing_poem_count,
            "Category Summary": row.categorical_summary or None,
            "Note": row.note,
        }
        for label, value in zip(labels, row.values, strict=True):
            record[label] = value.value
            record[f"{label} · Coverage"] = value.coverage
            record[f"{label} · Denominator"] = value.denominator
        records.append(record)
    return pd.DataFrame(records)


def _render_comparison_set_chart(
    frame: pd.DataFrame,
    *,
    state_key: str,
    poem_labels: list[str],
) -> None:
    numeric = frame.copy()
    for label in poem_labels:
        numeric[label] = pd.to_numeric(numeric[label], errors="coerce")
    numeric = numeric.dropna(subset=poem_labels, how="all")
    if numeric.empty:
        return
    numeric["Chart Group"] = (
        numeric["Source"].fillna("").astype(str)
        + " · "
        + numeric["Unit or Scale"].fillna("").astype(str)
    )
    groups = list(dict.fromkeys(numeric["Chart Group"].tolist()))
    selected_group = st.selectbox(
        "Chart source and scale",
        options=groups,
        key=f"{state_key}_chart_group",
        help=(
            "Only metrics sharing one source and unit are drawn together. "
            "Axes fit the observed poem values instead of forcing a zero baseline."
        ),
    )
    selected = numeric[numeric["Chart Group"] == selected_group].head(16)
    long_rows = []
    for _, row in selected.iterrows():
        for label in poem_labels:
            value = row[label]
            if pd.notna(value):
                long_rows.append(
                    {
                        "Metric": row["Metric"],
                        "Poem": label,
                        "Value": float(value),
                        "Mean": row["Equal-Poem Mean"],
                    }
                )
    if not long_rows:
        return
    long_frame = pd.DataFrame(long_rows)
    lower, upper = _chart_domain(long_frame["Value"].tolist())
    points = (
        alt.Chart(long_frame)
        .mark_circle(size=95, opacity=0.88)
        .encode(
            x=alt.X(
                "Value:Q",
                scale=alt.Scale(domain=[lower, upper], zero=False),
                title=selected.iloc[0]["Unit or Scale"],
            ),
            y=alt.Y("Metric:N", sort=None, title=None),
            color=alt.Color(
                "Poem:N",
                scale=alt.Scale(range=list(PUBLICATION_CHART_COLORS)),
            ),
            tooltip=[
                "Poem:N",
                "Metric:N",
                alt.Tooltip("Value:Q", format=".3f"),
            ],
        )
    )
    means = (
        alt.Chart(
            long_frame[["Metric", "Mean"]]
            .dropna()
            .drop_duplicates()
        )
        .mark_point(
            shape="diamond",
            size=120,
            filled=True,
            color="#17242d",
        )
        .encode(
            x=alt.X("Mean:Q"),
            y=alt.Y("Metric:N", sort=None),
            tooltip=[
                "Metric:N",
                alt.Tooltip("Mean:Q", title="Equal-poem mean", format=".3f"),
            ],
        )
    )
    chart = publication_chart(
        (points + means).properties(
            height=max(220, min(620, len(selected) * 35))
        )
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "Colored circles are individual poems. Black diamonds are equal-poem "
        "means. Means omit missing evidence and never pool tokens across poems."
    )


def _render_comparison_set_panel(
    frame: pd.DataFrame,
    *,
    report_section: str,
    panel: str,
    state_key: str,
    poem_labels: list[str],
) -> None:
    panel_rows = frame[
        (frame["Report Section"] == report_section)
        & (frame["Report Panel"] == panel)
    ]
    with st.expander(panel, expanded=False):
        st.caption(_PANEL_NOTES.get(panel, "Shared comparison evidence."))
        if panel_rows.empty:
            st.info(
                "No compatible evidence is available for this comparison set "
                "under the selected shared configuration."
            )
            return
        _render_comparison_set_chart(
            panel_rows,
            state_key=state_key,
            poem_labels=poem_labels,
        )
        display_columns = [
            "Source",
            "Metric",
            *poem_labels,
            "Equal-Poem Mean",
            "Poem-Level SD",
            "Poems Contributing",
            "Category Summary",
            "Unit or Scale",
        ]
        render_dataframe(
            _arrow_safe_display_frame(
                panel_rows[display_columns],
                value_columns=tuple(poem_labels),
            ),
            hide_index=True,
            width="stretch",
            height=min(500, 76 + len(panel_rows) * 35),
        )
        with st.expander("Coverage, denominators, and methodological notes"):
            detail_columns = [
                "Source",
                "Metric",
                *[
                    item
                    for label in poem_labels
                    for item in (
                        f"{label} · Coverage",
                        f"{label} · Denominator",
                    )
                ],
                "Note",
            ]
            render_dataframe(
                panel_rows[detail_columns],
                hide_index=True,
                width="stretch",
                height=min(420, 76 + len(panel_rows) * 35),
            )


def _render_comparison_set_results(
    comparison_set: PoemComparisonSet,
) -> None:
    view_columns = st.columns(2)
    analysis_view_label = view_columns[0].selectbox(
        "Shared token scope",
        options=("All matched tokens", "Stopwords excluded"),
        key="comparison_set_analysis_view",
    )
    weighting_label = view_columns[1].selectbox(
        "Shared weighting",
        options=("Token weighted", "Type weighted"),
        key="comparison_set_weighting",
    )
    report_section = st.selectbox(
        "Report Section",
        options=_REPORT_SECTIONS,
        key="comparison_set_report_section",
    )
    analysis_view = (
        "stopwords_excluded"
        if analysis_view_label == "Stopwords excluded"
        else "all_matched"
    )
    weighting = "type" if weighting_label == "Type weighted" else "token"
    frame = _comparison_set_frame(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
    )
    poem_labels = _comparison_set_labels(comparison_set)
    if frame.empty:
        st.info(
            "No compatible comparison metrics were produced for the enabled "
            "modules and shared token scope."
        )
        return

    if report_section == "Overview":
        st.subheader("Comparison Set Overview")
        st.info(
            "Each displayed value uses one shared configuration. Equal-poem "
            "means give every poem one vote and omit unavailable evidence; "
            "they are descriptive summaries, not significance tests."
        )
        summary_columns = st.columns(4)
        summary_columns[0].metric("Poems", len(comparison_set.analyses))
        summary_columns[1].metric("Shared Metrics", len(frame))
        summary_columns[2].metric(
            "Numeric Metrics",
            int(frame["Equal-Poem Mean"].notna().sum()) if not frame.empty else 0,
        )
        summary_columns[3].metric(
            "Categorical Metrics",
            int(frame["Category Summary"].notna().sum()) if not frame.empty else 0,
        )
        core = frame[
            frame["Metric ID"].str.contains(
                "vad\\.|concreteness.*mean|frequency.*rarity|"
                "lexical_style.*mean|poetry_id\\.categorical",
                regex=True,
                na=False,
            )
        ].head(18)
        if not core.empty:
            st.markdown("#### Core Comparison Snapshot")
            render_dataframe(
                _arrow_safe_display_frame(
                    core[
                        [
                            "Source",
                            "Metric",
                            *poem_labels,
                            "Equal-Poem Mean",
                            "Poem-Level SD",
                            "Category Summary",
                            "Unit or Scale",
                        ]
                    ],
                    value_columns=tuple(poem_labels),
                ),
                hide_index=True,
                width="stretch",
            )
        return

    if report_section in _PANEL_ORDER:
        st.subheader(report_section)
        for panel in _PANEL_ORDER[report_section]:
            _render_comparison_set_panel(
                frame,
                report_section=report_section,
                panel=panel,
                state_key=(
                    "comparison_set_"
                    + panel.lower().replace(" ", "_").replace("&", "and")
                ),
                poem_labels=poem_labels,
            )
        return

    if report_section == "Evidence & Diagnostics":
        st.subheader("Evidence & Diagnostics")
        st.caption(
            "Complete shared metric evidence with per-poem denominators, "
            "coverage, and cautions."
        )
        render_dataframe(
            _arrow_safe_display_frame(
                frame,
                value_columns=tuple(poem_labels),
            ),
            hide_index=True,
            width="stretch",
            height=620,
        )
        return

    if report_section == "Export & Help":
        from versevad.exports.research_notes import (
            append_research_notes_to_docx,
            research_notes_csv,
        )
        from versevad.ui.research import render_note_export_options

        st.subheader("Export & Help")
        selected_notes, include_note_metadata = render_note_export_options(
            "Compare Poems",
            key_prefix="comparison_set_export_notes",
        )
        csv_content = export_poem_comparison_set_csv(
            comparison_set,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        docx_content = export_poem_comparison_set_docx(
            comparison_set,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        docx_content = append_research_notes_to_docx(
            docx_content,
            selected_notes,
            include_metadata=include_note_metadata,
        )
        downloads = st.columns(3 if selected_notes else 2)
        downloads[0].download_button(
            "Download Comparison-Set CSV",
            data=csv_content,
            file_name="VerseVAD_poem_comparison_set.csv",
            mime="text/csv",
            key="comparison_set_download_csv",
            width="stretch",
        )
        downloads[1].download_button(
            "Download Narrative Word Report",
            data=docx_content,
            file_name="VerseVAD_poem_comparison_set.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key="comparison_set_download_docx",
            width="stretch",
        )
        if selected_notes:
            downloads[2].download_button(
                "Download Research Notes CSV",
                data=research_notes_csv(
                    selected_notes,
                    include_metadata=include_note_metadata,
                ),
                file_name="VerseVAD_poem_comparison_notes.csv",
                mime="text/csv",
                key="comparison_set_download_notes_csv",
                width="stretch",
            )
        with st.expander("How to read a comparison set", expanded=False):
            st.markdown(
                "- Compare values only within the same source, scale, scope, and weighting.\n"
                "- Equal-poem means do not pool tokens and omit unavailable results.\n"
                "- Poem-level SD describes dispersion among poem values, not uncertainty or significance.\n"
                "- Categorical evidence is summarized by counts rather than numerical averaging.\n"
                "- Read coverage and denominators before interpreting apparent differences."
            )


def _comparison_profile_state(
    profile_name: str,
    *,
    available_lexicons: tuple[str, ...],
    installed_modules: tuple[str, ...],
) -> tuple[list[str], list[str], dict[str, object]]:
    include_to_module = {
        "include_concreteness": "concreteness",
        "include_frequency": "frequency",
        "include_aoa": "aoa",
        "include_sensorimotor": "sensorimotor",
        "include_lexical_style": "lexical_style",
        "include_poetry_id": "poetry_id",
        "include_pronunciation": "pronunciation",
        "include_meter": "meter",
        "include_phonology": "phonology",
        "include_inherited_form": "inherited_form",
        "include_versemap": "versemap",
    }
    if profile_name in MODULE_PRESETS and profile_name != "Custom":
        settings = preset_widget_state(
            profile_name,
            available_lexicon_ids=available_lexicons,
        )
    else:
        custom_name = profile_name.removeprefix("Custom · ")
        session_profiles = st.session_state.get("_session_custom_profiles", {})
        if custom_name in session_profiles:
            settings = dict(session_profiles[custom_name])
        else:
            settings = dict(load_custom_profiles()[custom_name].settings)
    selected_lexicons = [
        item
        for item in settings.get("selected_lexicons", [])
        if item in available_lexicons
    ]
    selected_modules = [
        module_id
        for include_key, module_id in include_to_module.items()
        if settings.get(include_key) is True and module_id in installed_modules
    ]
    return selected_lexicons, selected_modules, settings


def render_compare_poems_workspace(
    preprocessor: TextPreprocessor,
    readiness: ResourceReadiness,
) -> None:
    """Render a session-only shared-design comparison of two through ten poems."""

    poem_ids = _comparison_set_poem_ids()
    with st.sidebar:
        st.metric("Poems", len(poem_ids))
        st.button(
            "Clear Comparison Workspace",
            key="compare_sidebar_clear",
            width="stretch",
            on_click=_clear_comparison_set,
        )

    render_workspace_header(
        "Compare Poems",
        "Analyze between two and ten poems under one shared configuration, "
        "then inspect poem-level evidence and equal-poem summaries side by side.",
        kicker="Multi-poem comparative evaluation for close reading",
        status="Session only",
    )
    st.caption(
        "VerseVAD reports comparable normative evidence. It does not rank "
        "literary quality, identify a poem's emotion, or treat set means as "
        "significance tests."
    )

    with st.container(border=True):
        st.subheader(f"1. Add Poems ({len(poem_ids)} of 10)")
        for start in range(0, len(poem_ids), 2):
            columns = st.columns(2)
            for offset, poem_id in enumerate(poem_ids[start : start + 2]):
                position = start + offset + 1
                with columns[offset]:
                    with st.container(border=True):
                        heading_columns = st.columns(
                            [4, 1],
                            vertical_alignment="center",
                        )
                        heading_columns[0].markdown(f"#### Poem {position}")
                        heading_columns[1].button(
                            "Remove",
                            key=f"compare_remove_{poem_id}",
                            disabled=len(poem_ids) <= 2,
                            on_click=_remove_comparison_poem,
                            args=(poem_id,),
                            help="Remove this poem from the comparison set.",
                        )
                        st.file_uploader(
                            "Choose a UTF-8 plain-text file",
                            type=["txt"],
                            key=f"compare_{poem_id}_upload",
                            on_change=_apply_uploaded_text,
                            args=(poem_id,),
                        )
                        if st.session_state.get(
                            f"compare_{poem_id}_upload_error"
                        ):
                            st.error(
                                st.session_state[
                                    f"compare_{poem_id}_upload_error"
                                ]
                            )
                        st.text_input(
                            "Title or working label",
                            key=f"compare_{poem_id}_title",
                        )
                        st.text_area(
                            "Paste the poem exactly as it should be analyzed",
                            key=f"compare_{poem_id}_text",
                            height=250,
                        )
        st.button(
            "Add Another Poem",
            icon=":material/add:",
            key="compare_add_poem",
            disabled=len(poem_ids) >= 10,
            on_click=_add_comparison_poem,
            width="stretch",
        )

    available_lexicons = tuple(readiness.available_lexicon_ids)
    lexicon_labels = {
        spec.lexicon_id: spec.display_name for spec in LEXICON_SPECS
    }
    installed_modules = tuple(readiness.available_module_ids)
    default_lexicons = [
        lexicon_id
        for lexicon_id in (
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        )
        if lexicon_id in available_lexicons
    ]
    default_modules = [
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
    ]
    st.session_state.setdefault("compare_lexicons", default_lexicons)
    st.session_state.setdefault("compare_modules", default_modules)

    with st.container(border=True):
        st.subheader("2. Choose One Shared Analysis Profile")
        custom_names = set(load_custom_profiles())
        custom_names.update(
            name
            for name in st.session_state.get(
                "_session_custom_profiles",
                {},
            )
            if isinstance(name, str)
        )
        profile_options = [
            name for name in MODULE_PRESETS if name != "Custom"
        ] + [f"Custom · {name}" for name in sorted(custom_names)] + ["Custom"]
        if st.session_state.get("compare_analysis_profile") not in profile_options:
            st.session_state["compare_analysis_profile"] = "Custom"
        profile_columns = st.columns([3, 1], vertical_alignment="bottom")
        selected_profile = profile_columns[0].selectbox(
            "Analysis profile",
            options=profile_options,
            key="compare_analysis_profile",
            help=(
                "Apply a built-in or saved profile, then continue customizing "
                "the shared evidence below."
            ),
        )
        apply_profile = profile_columns[1].button(
            "Apply / Restore",
            key="compare_apply_profile",
            width="stretch",
            disabled=selected_profile == "Custom",
        )
        if selected_profile in MODULE_PRESETS:
            st.caption(MODULE_PRESETS[selected_profile].description)
        if apply_profile:
            selected_lexicons, selected_modules, profile_settings = (
                _comparison_profile_state(
                    selected_profile,
                    available_lexicons=available_lexicons,
                    installed_modules=installed_modules,
                )
            )
            st.session_state["compare_lexicons"] = selected_lexicons
            st.session_state["compare_modules"] = selected_modules
            stopword_key_map = {
                "single_stopword_mode": "compare_stopword_mode",
                "single_protected_stopwords": "compare_protected_stopwords",
                "single_custom_stopword_additions": (
                    "compare_custom_stopword_additions"
                ),
                "single_custom_stopword_removals": (
                    "compare_custom_stopword_removals"
                ),
            }
            for source_key, target_key in stopword_key_map.items():
                if source_key in profile_settings:
                    st.session_state[target_key] = profile_settings[source_key]
            st.session_state.pop("poem_comparison_set", None)
            st.rerun()

        selected_lexicons = st.multiselect(
            "Affective lexicons",
            options=available_lexicons,
            format_func=lambda value: lexicon_labels.get(value, value),
            key="compare_lexicons",
            help="Every selected source is analyzed independently for every poem.",
        )
        selected_modules = st.multiselect(
            "Additional modules",
            options=installed_modules,
            format_func=lambda value: _MODULE_LABELS.get(value, value),
            key="compare_modules",
            help=(
                "The same module configuration is applied to every poem. "
                "VADER and readability evidence are produced automatically."
            ),
        )
        with st.expander("Shared stopword sensitivity settings", expanded=False):
            stopwords = render_stopword_settings("compare")

    with st.container(border=True):
        st.subheader("3. Analyze and Compare")
        analyze = st.button(
            f"Analyze {len(poem_ids)} Poems",
            type="primary",
            width="stretch",
            key="compare_analyze_set",
        )
        if analyze:
            empty_positions = [
                position
                for position, poem_id in enumerate(poem_ids, start=1)
                if not st.session_state[f"compare_{poem_id}_text"].strip()
            ]
            if empty_positions:
                st.error(
                    "Add text for every poem before analyzing. Empty positions: "
                    + ", ".join(str(position) for position in empty_positions)
                    + "."
                )
            else:
                selected = set(selected_modules)
                include_pronunciation = bool(
                    selected
                    & {"pronunciation", "meter", "phonology", "inherited_form"}
                )
                include_meter = bool(selected & {"meter", "inherited_form"})
                include_phonology = bool(
                    selected & {"phonology", "inherited_form"}
                )

                def request(poem_id: str, position: int) -> AnalysisRequest:
                    return AnalysisRequest(
                        project_name="Multi-poem comparative evaluation",
                        title=st.session_state[
                            f"compare_{poem_id}_title"
                        ].strip()
                        or f"Poem {position}",
                        original_text=st.session_state[
                            f"compare_{poem_id}_text"
                        ],
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
                            "analysis_cache_enabled",
                            True,
                        ),
                        performance_diagnostics=st.session_state.get(
                            "performance_diagnostics_enabled",
                            True,
                        ),
                    )

                try:
                    analyses = []
                    with st.status(
                        f"Analyzing {len(poem_ids)} poems under one shared design…",
                        expanded=True,
                    ) as status:
                        for position, poem_id in enumerate(poem_ids, start=1):
                            title = (
                                st.session_state[
                                    f"compare_{poem_id}_title"
                                ].strip()
                                or f"Poem {position}"
                            )
                            st.write(
                                f"Preparing {position} of {len(poem_ids)}: {title}"
                            )
                            analyses.append(
                                run_workspace_analysis(
                                    request(poem_id, position),
                                    preprocessor=preprocessor,
                                )
                            )
                        st.session_state["poem_comparison_set"] = (
                            build_poem_comparison_set(analyses)
                        )
                        status.update(
                            label="Comparison-set analysis complete.",
                            state="complete",
                            expanded=False,
                        )
                except (ValueError, WorkspaceAnalysisError) as error:
                    st.error(str(error))

    comparison_set = st.session_state.get("poem_comparison_set")
    if isinstance(comparison_set, PoemComparisonSet):
        _render_comparison_set_results(comparison_set)


__all__ = [
    "_REPORT_SECTIONS",
    "_chart_domain",
    "_report_location",
    "render_compare_poems_workspace",
]
