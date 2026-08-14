"""Streamlit workspace for like-for-like contrastive poem evaluation."""

from __future__ import annotations

import hashlib
import io
import os
import zipfile
from dataclasses import asdict, dataclass
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
    export_poem_comparison_set_bundle,
    export_poem_comparison_set_selected_csv,
)
from versevad.models import PhrasePolicy
from versevad.module_capabilities import fixed_profile_notice
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.concreteness import ConcretenessConfiguration
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.lexical_semantic.sensorimotor import SensorimotorConfiguration
from versevad.lexical_style import LexicalStyleConfiguration
from versevad.phonology import PhonologicalConfiguration
from versevad.poetry_id import PoetryIDConfiguration
from versevad.preprocessing import TextPreprocessor
from versevad.reference_corpora import (
    ReferenceCorpusDescriptor,
    ReferenceCorpusError,
    list_reference_corpora,
    load_corpus_index,
)
from versevad.prosody import (
    MeterAnalysisMode,
    MeterConfiguration,
    PronunciationConfiguration,
    parse_meter_scholar_revisions,
    parse_pronunciation_overrides,
)
from versevad.ui.dataframes import heterogeneous_display_value
from versevad.ui.design import (
    METER_DEPTH_LABELS,
    METER_MODE_LABELS,
    METER_STYLE_LABELS,
    MODULE_PRESETS,
    PUBLICATION_CHART_COLORS,
    bottom_collapsible_expander,
    publication_chart,
    preset_widget_state,
    render_dataframe,
    render_empty_state,
    render_stateful_section_navigation,
    render_workspace_header,
)
from versevad.ui.profile_management import (
    analysis_profile_options,
    apply_profile_display_defaults,
    consume_pending_profile_selection,
    custom_profile_settings,
    render_custom_profile_manager,
    selected_custom_profile_name,
)
from versevad.ui.profiles import (
    COMPARISON_PROFILE_SETTING_KEYS,
    normalize_profile_settings,
    snapshot_profile_settings,
)
from versevad.ui.stopwords import render_stopword_settings
from versevad.analysis_profiles import (
    LexicalScope,
    display_profile_order,
    primary_display_profile,
)
from versevad.ui.profile_controls import render_report_profile_controls
from versevad.ui.module_scope_overrides import (
    active_override_modules,
    render_override_controls_for_groups,
)
from versevad.report_profile_overrides import (
    CONTENT_WORD_SCOPE_OVERRIDE_MODULES,
    canonical_module_id,
    effective_profiles,
    profile_applies_to_module,
)
from versevad.ui.vad_overview import (
    overview_metric_matches_vad_preference,
    preferred_overview_vad_lexicon_id,
)
from versevad.versemap import VerseMapAnalysisResult


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
        "and midpoint-relative loads without merging lexicons."
    ),
    "Emotion Association, Intensity & Sentiment": (
        "Compare NRC association/intensity evidence and VADER polarity under "
        "their own definitions and denominators."
    ),
    "PoetryID": (
        "Compare PoetryID candidates and distances as descriptive profile "
        "evidence, not declarations of a poem's emotion or identity."
    ),
    "Concreteness": "Compare matched normative concreteness, dispersion, and coverage.",
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


@dataclass(frozen=True)
class _SharedComparisonConfiguration:
    """Validated analytical choices applied identically to every poem."""

    phrase_policy: PhrasePolicy
    minimum_matches: int
    concreteness: ConcretenessConfiguration
    sensorimotor: SensorimotorConfiguration
    frequency: FrequencyConfiguration
    aoa: AoAConfiguration
    lexical_style: LexicalStyleConfiguration
    poetry_id: PoetryIDConfiguration
    pronunciation: PronunciationConfiguration
    meter: MeterConfiguration
    phonology: PhonologicalConfiguration


_PROFILE_TO_COMPARE_CONFIGURATION_KEYS = {
    key: f"compare_config_{key}"
    for key in COMPARISON_PROFILE_SETTING_KEYS
}
_PROFILE_INCLUDE_TO_MODULE = {
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
_PROFILE_TO_COMPARE_STOPWORD_KEYS = {
    "single_stopword_mode": "compare_stopword_mode",
    "single_protected_stopwords": "compare_protected_stopwords",
    "single_custom_stopword_additions": "compare_custom_stopword_additions",
    "single_custom_stopword_removals": "compare_custom_stopword_removals",
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
    if prefix in {"emotion", "emotion_association", "emotion_intensity", "vader"}:
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
    if prefix in {"lexical_style", "word_length"}:
        return "Structure", "Lexical & Structural Measures"
    if prefix == "versemap":
        return "VerseMap", "VerseMap Comparative Profile"
    return "Evidence & Diagnostics", "Other Shared Evidence"


def _comparison_metric_family(
    metric_id: str,
    metric: str,
    panel: str,
) -> str:
    """Group comparison rows into reader-facing analytical families."""

    identifier = metric_id.casefold()
    label = metric.casefold()
    is_dispersion = (
        "population_sd" in identifier
        or "population_standard_deviation" in identifier
    )
    is_cumulative = any(
        marker in identifier
        for marker in (
            "rating_total",
            "midpoint",
            "cumulative_load",
            "load_per_100",
            ".cumulative",
        )
    )
    if panel == "VAD Profile":
        if is_dispersion:
            return "Within-Poem Dispersion"
        if "poem_mean" in identifier:
            return "Mean-Centered Lexical Volatility"
        if (
            "midpoint" in identifier
            and (
                identifier.endswith("per_observation")
                or identifier.endswith("per_100")
            )
        ):
            return "Midpoint Deviation per Matched Token/Type"
        if is_cumulative:
            return "Cumulative Midpoint Loads"
        return "VAD Means"
    if panel == "Emotion Association, Intensity & Sentiment":
        if identifier.startswith("vader."):
            return "VADER Sentiment"
        if identifier.startswith("emotion_intensity."):
            if is_cumulative:
                return "Cumulative Emotion Intensity Load"
            return (
                "Emotion-Intensity Dispersion"
                if is_dispersion
                else "Emotion Intensity Means"
            )
        return "NRC Emotion and Polarity Associations"
    if panel == "PoetryID":
        return "PoetryID Archetypes"
    if panel == "Concreteness":
        if is_dispersion:
            return "Concreteness Dispersion"
        return "Mean Concreteness"
    if panel == "Sensorimotor Imagery & Embodiment":
        if is_dispersion:
            return "Sensorimotor Dispersion"
        if is_cumulative:
            return "Cumulative Sensorimotor Loads"
        return "Sensorimotor Dimension Means"
    if panel == "Frequency & Rarity":
        if is_dispersion:
            return "Frequency and Rarity Dispersion"
        return (
            "Mean Rarity"
            if identifier.startswith("rarity.")
            else "Mean Frequency"
        )
    if panel == "Acquisition & Readability":
        if "poetic_reading_ease" in identifier:
            return "VerseVAD Poetic Reading Ease"
        if identifier.startswith("readability."):
            return "Traditional Readability"
        if is_dispersion:
            return "Age-of-Acquisition Dispersion"
        return "Mean Age of Acquisition"
    if panel == "Language Profile":
        return "Part-of-Speech Profile"
    if panel == "Lexical & Structural Measures":
        if any(marker in identifier for marker in ("line", "stanza")):
            return "Line and Stanza Structure"
        if "alphabetic_characters" in identifier or "word_length" in identifier:
            return "Word Length"
        return "Lexical Diversity"
    if is_dispersion:
        return "Within-Poem Dispersion"
    if is_cumulative:
        return "Method-Defined Cumulative Load"
    if "coverage" in identifier or "matched" in label:
        return "Coverage and Evidence"
    return "Summary Metrics"


_FAMILY_ORDER = {
    "VAD Profile": (
        "VAD Means",
        "Cumulative Midpoint Loads",
        "Midpoint Deviation per Matched Token/Type",
        "Mean-Centered Lexical Volatility",
        "Within-Poem Dispersion",
    ),
    "Emotion Association, Intensity & Sentiment": (
        "NRC Emotion and Polarity Associations",
        "Emotion Intensity Means",
        "Cumulative Emotion Intensity Load",
        "VADER Sentiment",
        "Emotion-Intensity Dispersion",
    ),
    "PoetryID": ("PoetryID Archetypes",),
    "Concreteness": (
        "Mean Concreteness",
        "Concreteness Dispersion",
    ),
    "Sensorimotor Imagery & Embodiment": (
        "Sensorimotor Dimension Means",
        "Cumulative Sensorimotor Loads",
        "Sensorimotor Dispersion",
    ),
    "Frequency & Rarity": (
        "Mean Frequency",
        "Mean Rarity",
        "Frequency and Rarity Dispersion",
    ),
    "Acquisition & Readability": (
        "VerseVAD Poetic Reading Ease",
        "Traditional Readability",
        "Mean Age of Acquisition",
        "Age-of-Acquisition Dispersion",
    ),
}


def _ordered_metric_families(panel_rows: pd.DataFrame, panel: str) -> tuple[str, ...]:
    """Return stable reader-facing order without discarding uncommon metrics."""

    observed = tuple(dict.fromkeys(panel_rows["Metric Family"].tolist()))
    preferred = _FAMILY_ORDER.get(panel, ())
    return tuple(item for item in preferred if item in observed) + tuple(
        item for item in observed if item not in preferred
    )


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


def _prefer_overview_vad_source(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one fixed-priority VAD source in compact Overview snapshots."""

    if frame.empty or "Metric ID" not in frame:
        return frame
    metric_ids = frame["Metric ID"].fillna("").astype(str)
    vad_lexicon_ids = tuple(
        metric_id.split(".", 2)[1]
        for metric_id in metric_ids
        if metric_id.startswith("vad.") and metric_id.count(".") >= 2
    )
    preferred = preferred_overview_vad_lexicon_id(vad_lexicon_ids)
    if preferred is None:
        return frame
    keep = metric_ids.map(
        lambda metric_id: overview_metric_matches_vad_preference(
            metric_id,
            preferred,
        )
    )
    return frame.loc[keep]


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
    with bottom_collapsible_expander(
        label,
        control_id=f"comparison-legacy-{state_key}",
        expanded=False,
    ):
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
            overview = _prefer_overview_vad_source(
                frame[
                    frame["Metric ID"].str.contains(
                        core_metric_ids,
                        regex=True,
                        na=False,
                    )
                ]
            ).head(14)
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
                    with bottom_collapsible_expander(
                        panel,
                        control_id=(
                            "comparison-legacy-empty-"
                            + section.lower().replace(" ", "-").replace("&", "and")
                            + f"-{panel_index}"
                        ),
                        expanded=False,
                    ):
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
        export_mode_label = st.radio(
            "Export mode",
            options=("Export Current View", "Export Complete Audit"),
            horizontal=True,
            key="comparison_set_export_mode",
        )
        export_mode = (
            "current_view"
            if export_mode_label == "Export Current View"
            else "complete_audit"
        )
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
                "- Method-defined cumulative load preserves repetition and length in the token view; VAD per-100 rows divide midpoint load by matched tokens or types for comparison.\n"
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
        with st.expander("Shared Stopword Resource and Exclusions", expanded=False):
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
    st.session_state.pop("compare_results_pronunciation_overrides", None)
    st.session_state.pop("_pending_compare_pronunciation_overrides", None)
    st.session_state.pop("_compare_reanalyze_requested", None)


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
        poetry_id_source = ""
        if report_panel == "PoetryID":
            poetry_id_source, separator, poetry_id_view = (
                row.analysis_view.partition(":")
            )
            if (
                not separator
                or poetry_id_view != analysis_view
                or row.weighting != weighting
            ):
                continue
        metric_label = {
            "poetry_id.categorical_archetype_id": "Category Fit Archetype",
            "poetry_id.nearest_centroid_archetype_id": (
                "Nearest Centroid Archetype"
            ),
        }.get(row.metric_id, row.metric)
        metric_family = _comparison_metric_family(
            row.metric_id,
            metric_label,
            report_panel,
        )
        record = {
            "Report Section": report_section,
            "Report Panel": report_panel,
            "Metric Family": metric_family,
            "Source": (
                "PoetryID / "
                + next(
                    (
                        spec.display_name
                        for spec in LEXICON_SPECS
                        if spec.lexicon_id == poetry_id_source
                    ),
                    poetry_id_source,
                )
                if poetry_id_source
                else row.source
            ),
            "_PoetryID Source": poetry_id_source,
            "Metric": metric_label,
            "Metric ID": row.metric_id,
            "Analysis View": row.analysis_view.replace("_", " ").title(),
            "Weighting": row.weighting.title(),
            "Unit or Scale": row.unit_or_scale,
            "Equal-Poem Mean": row.numeric_mean,
            "Poem-Level SD": row.numeric_population_standard_deviation,
            "Range (Max − Min)": row.numeric_range,
            "Poems Contributing": row.contributing_poem_count,
            "Category Summary": row.categorical_summary or None,
            "Note": row.note,
        }
        for label, value in zip(labels, row.values, strict=True):
            record[label] = value.value
            record[f"{label} · Coverage"] = value.coverage
            record[f"{label} · Denominator"] = value.denominator
        records.append(record)
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records).drop_duplicates(ignore_index=True)
    poetry_mask = frame["Report Panel"] == "PoetryID"
    poetry_sources = tuple(
        frame.loc[poetry_mask, "_PoetryID Source"].dropna().astype(str)
    )
    preferred_poetry_source = preferred_overview_vad_lexicon_id(
        poetry_sources
    )
    if preferred_poetry_source:
        frame = frame.loc[
            ~poetry_mask
            | (frame["_PoetryID Source"] == preferred_poetry_source)
        ]
    poetry_order = {
        "poetry_id.categorical_archetype_id": 0,
        "poetry_id.nearest_centroid_archetype_id": 1,
    }
    frame["_Dashboard Order"] = frame["Metric ID"].map(poetry_order).fillna(2)
    return frame.sort_values(
        ["Report Section", "Report Panel", "_Dashboard Order", "Metric"],
        kind="stable",
        ignore_index=True,
    )


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
    numeric = numeric.reset_index(drop=True)
    numeric["Chart Label"] = (
        numeric["Metric"].fillna("").astype(str)
        + " — "
        + numeric["Source"].fillna("").astype(str)
    )
    duplicate_labels = numeric["Chart Label"].duplicated(keep=False)
    numeric.loc[duplicate_labels, "Chart Label"] = (
        numeric.loc[duplicate_labels, "Chart Label"]
        + " · "
        + numeric.loc[duplicate_labels, "Unit or Scale"].fillna("").astype(str)
    )
    selected_index = st.selectbox(
        "Metric to chart",
        options=tuple(numeric.index),
        format_func=lambda value: numeric.loc[value, "Chart Label"],
        key=f"{state_key}_chart_metric",
        help=(
            "Choose the actual measure to compare. The axis fits the observed "
            "poem values instead of combining unrelated scales."
        ),
    )
    selected = numeric.loc[selected_index]
    long_rows = []
    for label in poem_labels:
        value = selected[label]
        if pd.notna(value):
            long_rows.append({"Poem": label, "Value": float(value)})
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
                title=selected["Unit or Scale"],
            ),
            y=alt.Y("Poem:N", sort=poem_labels, title=None),
            color=alt.Color(
                "Poem:N",
                scale=alt.Scale(range=list(PUBLICATION_CHART_COLORS)),
                legend=None,
            ),
            tooltip=[
                "Poem:N",
                alt.Tooltip("Value:Q", format=".3f"),
            ],
        )
    )
    chart = publication_chart(
        points.properties(height=max(170, min(440, len(long_frame) * 42)))
    )
    st.altair_chart(chart, width="stretch")
    range_value = selected.get("Range (Max − Min)")
    range_text = (
        f"{float(range_value):.3f}"
        if range_value is not None and pd.notna(range_value)
        else "unavailable"
    )
    st.caption(
        f"Each point is one poem. Observed range (maximum minus minimum): "
        f"{range_text} {selected['Unit or Scale']}."
    )


def _comparison_versemap_summary_frame(
    comparison_set: PoemComparisonSet,
) -> pd.DataFrame:
    """Return only the map position and nearest context used by the dashboard."""

    labels = _comparison_set_labels(comparison_set)
    rows = []
    for label, analysis in zip(labels, comparison_set.analyses, strict=True):
        result = analysis.versemap
        if not isinstance(result, VerseMapAnalysisResult):
            continue
        nearest_poem = result.nearest_poems[0] if result.nearest_poems else None
        nearest_poet = result.nearest_poets[0] if result.nearest_poets else None
        rows.append(
            {
                "Poem": label,
                "PCA Component 1": result.coordinate_1,
                "PCA Component 2": result.coordinate_2,
                "Nearest Reference Poem": (
                    f"{nearest_poem.title} - {nearest_poem.poet_name}"
                    if nearest_poem is not None
                    else None
                ),
                "Nearest Poet Centroid": (
                    nearest_poet.poet_name if nearest_poet is not None else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _comparison_pronunciation_attention_frame(
    comparison_set: PoemComparisonSet,
) -> pd.DataFrame:
    """Collect unresolved or genuinely ambiguous pronunciation types by poem."""

    labels = _comparison_set_labels(comparison_set)
    rows = []
    attention_statuses = {
        "ambiguous_dictionary",
        "source_without_marked_vowel",
        "unmatched",
    }
    for label, analysis in zip(labels, comparison_set.analyses, strict=True):
        result = analysis.pronunciation
        if result is None:
            continue
        seen: set[tuple[str, str]] = set()
        for item in result.token_audit:
            status = str(item.status)
            if not item.eligible or status not in attention_statuses:
                continue
            identity = (item.lookup_form, status)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(
                {
                    "Poem": label,
                    "Word": item.surface_form,
                    "Status": status.replace("_", " ").title(),
                    "Dictionary Candidates": (
                        " | ".join(item.dictionary_candidate_phones)
                        if item.dictionary_candidate_phones
                        else "None"
                    ),
                    "Line": item.line_number,
                }
            )
    return pd.DataFrame(rows)


def _render_comparison_pronunciation_review(
    comparison_set: PoemComparisonSet,
) -> None:
    """Offer safe shared overrides without pretending they are poem-specific."""

    attention = _comparison_pronunciation_attention_frame(comparison_set)
    st.markdown("##### Pronunciation Review")
    if attention.empty:
        st.caption(
            "No unresolved or prosodically ambiguous pronunciation types were "
            "reported across the comparison set."
        )
        return
    st.caption(
        "Review these forms before interpreting syllable, meter, rhyme, or form "
        "differences. A shared override applies to the same spelling in every "
        "poem in this set. If a word needs different readings in different poems, "
        "resolve each poem separately in Single Poem instead."
    )
    render_dataframe(
        attention,
        hide_index=True,
        width="stretch",
        height=min(360, 76 + len(attention) * 35),
    )
    review_key = "compare_results_pronunciation_overrides"
    st.session_state.setdefault(
        review_key,
        st.session_state.get("compare_config_pronunciation_overrides", ""),
    )
    override_text = st.text_area(
        "Shared ARPAbet overrides",
        key=review_key,
        placeholder="word = W ER1 D | selected for this comparison set",
        help=(
            "Use one row per spelling: word = ARPAbet phones | scholarly note. "
            "Dictionary candidates in the table can be copied directly."
        ),
    )
    if st.button(
        "Apply Shared Overrides and Reanalyze",
        key="compare_apply_reviewed_pronunciations",
        type="primary",
    ):
        try:
            parse_pronunciation_overrides(override_text)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["_pending_compare_pronunciation_overrides"] = (
                override_text
            )
            st.session_state["_compare_reanalyze_requested"] = True
            st.rerun()


def _render_comparison_versemap(
    comparison_set: PoemComparisonSet,
) -> None:
    """Render a focused multi-poem map without repeating profile metrics."""

    labels = _comparison_set_labels(comparison_set)
    available = [
        (label, analysis.versemap)
        for label, analysis in zip(labels, comparison_set.analyses, strict=True)
        if isinstance(analysis.versemap, VerseMapAnalysisResult)
    ]
    st.subheader("VerseMap")
    st.caption(fixed_profile_notice("versemap"))
    st.caption(
        "The dashboard shows only the compared poems' PCA positions and nearest "
        "reference context. The Standard Profile dimensions remain available in "
        "the statistical export and in their relevant analytical sections."
    )
    if not available:
        st.info(
            "Enable VerseMap in the shared profile and analyze the poems to "
            "compare them against a reference corpus."
        )
        return
    if len(available) != len(comparison_set.analyses):
        st.warning(
            "VerseMap evidence is unavailable for one or more poems, so only "
            "mapped poems are displayed."
        )

    first_result = available[0][1]
    releases = {result.reference_release_id for _, result in available}
    if len(releases) > 1:
        st.warning(
            "These historical results use different reference releases and "
            "should not be interpreted as one shared map. Reanalyze them under "
            "one reference corpus."
        )
    reference_rows = [
        {
            "Series": (
                "Reference poems"
                if point.point_kind == "reference_poem"
                else "Poet centroids"
            ),
            "Poet": point.poet_name,
            "Title": point.title,
            "PCA Component 1": point.coordinate_1,
            "PCA Component 2": point.coordinate_2,
            "Point Size": 34 if point.point_kind == "reference_poem" else 105,
        }
        for point in first_result.map_points
    ]
    query_rows = [
        {
            "Series": label,
            "Poet": "",
            "Title": label,
            "PCA Component 1": result.coordinate_1,
            "PCA Component 2": result.coordinate_2,
            "Point Size": 230,
        }
        for label, result in available
    ]
    map_frame = pd.DataFrame([*reference_rows, *query_rows]).dropna(
        subset=["PCA Component 1", "PCA Component 2"]
    )
    if not map_frame.empty:
        query_palette = list(PUBLICATION_CHART_COLORS)
        domain = ["Reference poems", "Poet centroids", *[row[0] for row in available]]
        color_range = ["#9AA3AA", "#4E5961"] + [
            query_palette[index % len(query_palette)]
            for index in range(len(available))
        ]
        chart = (
            alt.Chart(map_frame)
            .mark_circle(opacity=0.72, strokeWidth=1.2)
            .encode(
                x=alt.X(
                    "PCA Component 1:Q",
                    title=(
                        "PCA Component 1 "
                        f"({first_result.explained_variance_1:.1%} reference variance)"
                    ),
                ),
                y=alt.Y(
                    "PCA Component 2:Q",
                    title=(
                        "PCA Component 2 "
                        f"({first_result.explained_variance_2:.1%} reference variance)"
                    ),
                ),
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(domain=domain, range=color_range),
                    sort=domain,
                    title=None,
                ),
                size=alt.Size(
                    "Point Size:Q",
                    scale=None,
                    legend=None,
                ),
                tooltip=[
                    "Series:N",
                    "Poet:N",
                    "Title:N",
                    alt.Tooltip("PCA Component 1:Q", format=".3f"),
                    alt.Tooltip("PCA Component 2:Q", format=".3f"),
                ],
            )
            .properties(height=560)
            .interactive()
        )
        st.altair_chart(publication_chart(chart), width="stretch")
        st.caption(
            "The chart is a two-dimensional PCA projection. Nearest neighbors "
            "are calculated in the full registered feature space, so the closest "
            "point on screen is not necessarily the nearest full-profile match."
        )

    summary = _comparison_versemap_summary_frame(comparison_set)
    if not summary.empty:
        render_dataframe(
            summary,
            column_config={
                "PCA Component 1": st.column_config.NumberColumn(format="%.3f"),
                "PCA Component 2": st.column_config.NumberColumn(format="%.3f"),
            },
            hide_index=True,
            width="stretch",
        )


def _render_comparison_set_panel(
    frame: pd.DataFrame,
    *,
    comparison_set: PoemComparisonSet,
    report_section: str,
    panel: str,
    state_key: str,
    poem_labels: list[str],
) -> None:
    panel_rows = frame[
        (frame["Report Section"] == report_section)
        & (frame["Report Panel"] == panel)
    ]
    with bottom_collapsible_expander(
        panel,
        control_id=f"comparison-set-{state_key}",
        expanded=False,
    ):
        st.caption(_PANEL_NOTES.get(panel, "Shared comparison evidence."))
        fixed_modules = {
            "Emotion Association, Intensity & Sentiment": ("vader",),
            "Acquisition & Readability": ("traditional_readability", "vv_pre"),
            "Pronunciation, Syllables & Stress": ("pronunciation",),
            "Candidate Meter & Rhythmic Regularity": ("meter",),
            "Rhyme & Recurring Sound": ("phonology",),
            "Inherited Form Analysis": ("inherited_form",),
            "Lexical & Structural Measures": ("structure",),
            "VerseMap Comparative Profile": ("versemap",),
        }.get(panel, ())
        for module_id in fixed_modules:
            st.caption(fixed_profile_notice(module_id))
        if panel == "Pronunciation, Syllables & Stress":
            _render_comparison_pronunciation_review(comparison_set)
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
        for family in _ordered_metric_families(panel_rows, panel):
            family_rows = panel_rows[panel_rows["Metric Family"] == family]
            st.markdown(f"##### {family}")
            if family == "Within-Poem Dispersion" and panel == "VAD Profile":
                st.caption(
                    "Population SD describes spread around each poem's own VAD "
                    "mean and gives unusually distant ratings more influence by "
                    "squaring departures. Mean absolute deviation below weights "
                    "departures linearly. Both are length-neutral and "
                    "order-insensitive."
                )
            elif "Dispersion" in family:
                st.caption(
                    "These values describe variation among matched observations "
                    "inside each poem. They are not cross-poem uncertainty."
                )
            elif family == "Midpoint Deviation per Matched Token/Type":
                st.caption(
                    "Use these rates—not raw cumulative loads—to compare poems of "
                    "different lengths. Per-observation and per-100 values are the "
                    "same normalized evidence on two display scales."
                )
            elif family == "Mean-Centered Lexical Volatility":
                st.caption(
                    "These length-neutral rates measure dispersion around each "
                    "poem's own VAD mean. Mean absolute deviation weights departures "
                    "linearly; population SD above emphasizes extremes. Neither "
                    "measure preserves lexical order."
                )
            display_columns = [
                "Profile",
                "Source",
                "Metric",
                *poem_labels,
                "Range (Max − Min)",
                "Category Summary",
                "Unit or Scale",
            ]
            render_dataframe(
                _arrow_safe_display_frame(
                    family_rows[display_columns],
                    value_columns=tuple(poem_labels),
                ),
                hide_index=True,
                width="stretch",
                height=min(440, 76 + len(family_rows) * 35),
            )
        with st.expander("Coverage, denominators, and methodological notes"):
            detail_columns = [
                "Profile",
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
    report_section = st.selectbox(
        "Report Section",
        options=_REPORT_SECTIONS,
        key="comparison_set_report_section",
    )
    if report_section != "Export & Help":
        st.session_state["comparison_set_last_analytical_section"] = report_section
    profile_state = render_report_profile_controls("compare_poems")
    override_groups = {
        "Affective Evidence": ("emotion",),
        "Lexical Character, Imagery & Embodiment": (
            "concreteness",
            "sensorimotor",
            "frequency",
            "aoa",
        ),
    }.get(report_section, ())
    if override_groups:
        with st.expander("Module-Specific Scope Overrides", expanded=False):
            render_override_controls_for_groups(
                "compare_poems",
                override_groups,
                profile_state.selection,
            )
    overridden_modules = active_override_modules("compare_poems")
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    frames: list[pd.DataFrame] = []
    configurable_prefixes = (
        "vad.",
        "emotion.",
        "emotion_association.",
        "emotion_intensity.",
        "concreteness.",
        "frequency.",
        "aoa.",
        "sensorimotor.",
        "word_length.",
        "poetry_id.",
    )
    primary_profile = primary_display_profile(profile_state.selection)
    selected_profiles = frozenset(profile_state.selection.profiles)
    for profile in effective_profiles(profile_state.selection, overridden_modules):
        profile_view = view_ids[profile.scope]
        profile_weighting = profile.weighting.value.casefold()
        profile_frame = _comparison_set_frame(
            comparison_set,
            analysis_view=profile_view,
            weighting=profile_weighting,
        )
        if profile_frame.empty:
            continue
        metric_ids = profile_frame["Metric ID"].fillna("").astype(str)
        configurable = metric_ids.str.startswith(configurable_prefixes)
        modules = metric_ids.map(canonical_module_id)
        keep = (~configurable & (profile == primary_profile))
        keep |= configurable & modules.map(
            lambda module_id: (
                profile_applies_to_module(
                    profile,
                    module_id=module_id,
                    selection=profile_state.selection,
                    overridden_modules=overridden_modules,
                )
                if module_id in CONTENT_WORD_SCOPE_OVERRIDE_MODULES
                else profile in selected_profiles
            )
        )
        profile_frame = profile_frame[keep]
        if profile_frame.empty:
            continue
        profile_frame = profile_frame.copy()
        profile_frame["Profile"] = profile.label
        frames.append(profile_frame)
    frame = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame()
    )
    analysis_view = view_ids[primary_profile.scope]
    weighting = primary_profile.weighting.value.casefold()
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
            "Each displayed value uses one shared configuration. Range is the "
            "maximum minus the minimum across available poem values; it is a "
            "descriptive contrast, not a significance test."
        )
        summary_columns = st.columns(4)
        summary_columns[0].metric("Poems", len(comparison_set.analyses))
        summary_columns[1].metric("Shared Metrics", len(frame))
        summary_columns[2].metric(
            "Numeric Metrics",
            int(frame["Range (Max − Min)"].notna().sum()) if not frame.empty else 0,
        )
        summary_columns[3].metric(
            "Categorical Metrics",
            int(frame["Category Summary"].notna().sum()) if not frame.empty else 0,
        )
        metric_ids = frame["Metric ID"].fillna("").astype(str)
        core_mask = frame["Metric Family"].isin(
            {
                "VAD Means",
                "Mean Concreteness",
                "Mean Frequency",
                "Mean Rarity",
                "Mean Age of Acquisition",
                "VerseVAD Poetic Reading Ease",
                "PoetryID Archetypes",
            }
        ) | metric_ids.isin(
            {
                "lexical_style.mattr",
                "lexical_style.hdd",
                "lexical_style.mtld",
            }
        )
        core = _prefer_overview_vad_source(frame[core_mask]).head(36)
        if not core.empty:
            st.markdown("#### Core Comparison Snapshot")
            render_dataframe(
                _arrow_safe_display_frame(
                    core[
                        [
                            "Profile",
                            "Source",
                            "Metric",
                            *poem_labels,
                            "Range (Max − Min)",
                            "Category Summary",
                            "Unit or Scale",
                        ]
                    ],
                    value_columns=tuple(poem_labels),
                ),
                hide_index=True,
                width="stretch",
            )
        dispersion = _prefer_overview_vad_source(
            frame[frame["Metric Family"] == "Within-Poem Dispersion"]
        )
        if not dispersion.empty:
            with bottom_collapsible_expander(
                "Within-Poem Dispersion",
                control_id="comparison-set-overview-dispersion",
                expanded=False,
            ):
                st.caption(
                    "Compare how widely matched observations vary inside each "
                    "poem. These are poem-specific standard deviations, not a "
                    "standard deviation across the compared poems."
                )
                render_dataframe(
                    _arrow_safe_display_frame(
                        dispersion[
                            [
                                "Source",
                                "Metric",
                                *poem_labels,
                                "Range (Max − Min)",
                                "Unit or Scale",
                            ]
                        ],
                        value_columns=tuple(poem_labels),
                    ),
                    hide_index=True,
                    width="stretch",
                    height=min(420, 76 + len(dispersion) * 35),
                )
        return

    if report_section == "VerseMap":
        _render_comparison_versemap(comparison_set)
        return

    if report_section in _PANEL_ORDER:
        st.subheader(report_section)
        for panel in _PANEL_ORDER[report_section]:
            _render_comparison_set_panel(
                frame,
                comparison_set=comparison_set,
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
            "This is the audit layer for the dashboard, not a second results "
            "report. Select a panel to inspect exactly which observations formed "
            "each displayed result, how much eligible evidence was matched, and "
            "which methodological cautions apply. The complete long-form audit "
            "remains available from Export & Help."
        )
        panel_options = tuple(
            dict.fromkeys(frame["Report Panel"].fillna("").tolist())
        )
        selected_panel = st.selectbox(
            "Evidence panel",
            options=panel_options,
            key="comparison_set_diagnostic_panel",
        )
        diagnostic_rows = frame[frame["Report Panel"] == selected_panel]
        detail_columns = [
            "Profile",
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
            diagnostic_rows[detail_columns],
            hide_index=True,
            width="stretch",
            height=min(560, 76 + len(diagnostic_rows) * 35),
        )
        return

    if report_section == "Export & Help":
        from versevad.exports.research_notes import (
            append_research_notes_to_docx,
            research_notes_csv,
        )
        from versevad.ui.research import render_note_export_options

        st.subheader("Export & Help")
        export_mode_label = st.radio(
            "Export mode",
            options=("Export Current View", "Export Complete Audit"),
            horizontal=True,
            key="comparison_set_export_mode_current",
        )
        export_mode = (
            "current_view"
            if export_mode_label == "Export Current View"
            else "complete_audit"
        )
        visible_section = str(
            st.session_state.get(
                "comparison_set_last_analytical_section",
                "Overview",
            )
        )
        if export_mode == "current_view":
            export_sections = tuple(
                section for section in _REPORT_SECTIONS if section != "Export & Help"
            )
            visible_section = st.selectbox(
                "Report section to export",
                options=export_sections,
                index=(
                    export_sections.index(visible_section)
                    if visible_section in export_sections
                    else 0
                ),
                key="comparison_set_export_section",
            )
        selected_notes, include_note_metadata = render_note_export_options(
            "Compare Poems",
            key_prefix="comparison_set_export_notes",
        )
        export_signature = (
            comparison_set.comparison_set_id,
            export_mode,
            visible_section,
            tuple(profile.id for profile in profile_state.selection.profiles),
            tuple(sorted(overridden_modules)),
            tuple(
                (note.note_id, note.updated_at)
                for note in selected_notes
            ),
            include_note_metadata,
        )
        prepared_key = "prepared_comparison_set_exports"
        prepared_exports = st.session_state.get(prepared_key)
        if st.button(
            "Prepare downloads",
            type="primary",
            key="prepare_comparison_set_exports",
        ):
            with st.spinner("Preparing CSV, Word, and reproducibility files..."):
                csv_content = export_poem_comparison_set_selected_csv(
                    comparison_set,
                    selection=profile_state.selection,
                    export_mode=export_mode,
                    visible_section=visible_section,
                    module_scope_overrides=overridden_modules,
                )
                bundle_content = export_poem_comparison_set_bundle(
                    comparison_set,
                    selection=profile_state.selection,
                    export_mode=export_mode,
                    visible_section=visible_section,
                    module_scope_overrides=overridden_modules,
                )
                with zipfile.ZipFile(io.BytesIO(bundle_content)) as archive:
                    docx_content = archive.read(
                        "01_REPORTS/Comparison_Report.docx"
                    )
                    csv_content = archive.read(
                        "03_MASTER_DATA/Master_Metrics.csv"
                    )
                docx_content = append_research_notes_to_docx(
                    docx_content,
                    selected_notes,
                    include_metadata=include_note_metadata,
                )
                prepared_exports = {
                    "signature": export_signature,
                    "csv": csv_content,
                    "report": docx_content,
                    "bundle": bundle_content,
                }
                st.session_state[prepared_key] = prepared_exports
        if not (
            isinstance(prepared_exports, dict)
            and prepared_exports.get("signature") == export_signature
        ):
            st.caption(
                "Downloads are generated on demand so larger comparisons do not "
                "rebuild reports during ordinary interface interactions."
            )
            return
        downloads = st.columns(4 if selected_notes else 3)
        downloads[0].download_button(
            (
                "Download Current-View Metrics CSV"
                if export_mode == "current_view"
                else "Download Master Metrics CSV"
            ),
            data=prepared_exports["csv"],
            file_name="VerseVAD_poem_comparison_set.csv",
            mime="text/csv",
            key="comparison_set_download_csv",
            width="stretch",
        )
        downloads[1].download_button(
            "Download Readable Word Report",
            data=prepared_exports["report"],
            file_name="VerseVAD_poem_comparison_set.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key="comparison_set_download_docx",
            width="stretch",
        )
        downloads[2].download_button(
            (
                "Download Current-View ZIP"
                if export_mode == "current_view"
                else "Download Complete Audit ZIP"
            ),
            data=prepared_exports["bundle"],
            file_name="VerseVAD_poem_comparison_bundle.zip",
            mime="application/zip",
            key="comparison_set_download_bundle",
            width="stretch",
        )
        if selected_notes:
            downloads[3].download_button(
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
                "- Range is maximum minus minimum across available poem values.\n"
                "- Within-poem SD describes dispersion among matched observations inside each poem.\n"
                "- Categorical evidence is summarized by counts rather than numerical averaging.\n"
                "- Read coverage and denominators before interpreting apparent differences."
            )


def _comparison_profile_state(
    profile_name: str,
    *,
    available_lexicons: tuple[str, ...],
    installed_modules: tuple[str, ...],
) -> tuple[list[str], list[str], dict[str, object]]:
    if profile_name in MODULE_PRESETS and profile_name != "Custom":
        settings = preset_widget_state(
            profile_name,
            available_lexicon_ids=available_lexicons,
        )
    else:
        custom_name = selected_custom_profile_name(profile_name)
        settings = dict(custom_profile_settings().get(custom_name or "", {}))
    settings = normalize_profile_settings(settings)
    selected_lexicons = [
        item
        for item in settings.get("selected_lexicons", [])
        if item in available_lexicons
    ]
    selected_modules = [
        module_id
        for include_key, module_id in _PROFILE_INCLUDE_TO_MODULE.items()
        if settings.get(include_key) is True and module_id in installed_modules
    ]
    return selected_lexicons, selected_modules, settings


def _comparison_profile_snapshot() -> dict[str, object]:
    """Map shared comparison controls back to the canonical profile schema."""

    settings: dict[str, object] = {
        "selected_lexicons": list(
            st.session_state.get("compare_lexicons", [])
        )
    }
    selected_modules = set(st.session_state.get("compare_modules", []))
    for include_key, module_id in _PROFILE_INCLUDE_TO_MODULE.items():
        settings[include_key] = module_id in selected_modules
    for profile_key, compare_key in (
        _PROFILE_TO_COMPARE_STOPWORD_KEYS.items()
    ):
        if compare_key in st.session_state:
            settings[profile_key] = st.session_state[compare_key]
    for profile_key, compare_key in (
        _PROFILE_TO_COMPARE_CONFIGURATION_KEYS.items()
    ):
        if compare_key in st.session_state:
            settings[profile_key] = st.session_state[compare_key]
    return snapshot_profile_settings(settings)


def _render_shared_comparison_configuration(
    *,
    selected_lexicons: list[str],
    selected_modules: list[str],
) -> tuple[_SharedComparisonConfiguration, str]:
    """Render and validate the methodology shared by every compared poem."""

    selected = set(selected_modules)
    phrase_options = {
        "Prefer the longest phrase (recommended)": PhrasePolicy.PHRASE_PREFERRED,
        "Use unigrams only": PhrasePolicy.UNIGRAM_ONLY,
        "Count phrases and components (exploratory)": (
            PhrasePolicy.PHRASE_AND_COMPONENT
        ),
    }
    defaults = {
        "concreteness": ConcretenessConfiguration(),
        "sensorimotor": SensorimotorConfiguration(),
        "frequency": FrequencyConfiguration(),
        "aoa": AoAConfiguration(),
        "lexical_style": LexicalStyleConfiguration(),
        "poetry_id": PoetryIDConfiguration(),
        "pronunciation": PronunciationConfiguration(),
        "meter": MeterConfiguration(),
        "phonology": PhonologicalConfiguration(),
    }
    key = lambda name: f"compare_config_{name}"
    configuration_defaults = {
        "phrase_policy_label": next(iter(phrase_options)),
        "minimum_matches": 3,
        "concreteness_abstract_max": defaults["concreteness"].highly_abstract_max,
        "concreteness_concrete_min": defaults["concreteness"].highly_concrete_min,
        "concreteness_coverage_warning": defaults[
            "concreteness"
        ].low_coverage_warning_threshold,
        "concreteness_exclude_proper": defaults[
            "concreteness"
        ].exclude_proper_nouns,
        "concreteness_phrases": defaults[
            "concreteness"
        ].activate_multiword_expressions,
        "sensorimotor_exclude_proper": defaults[
            "sensorimotor"
        ].exclude_proper_nouns,
        "sensorimotor_phrases": defaults["sensorimotor"].include_phrases,
        "sensorimotor_top_terms": defaults["sensorimotor"].top_term_count,
        "frequency_rare_below": defaults["frequency"].rare_below,
        "frequency_uncommon_below": defaults["frequency"].uncommon_below,
        "frequency_moderate_below": defaults[
            "frequency"
        ].moderately_common_below,
        "frequency_very_common_min": defaults["frequency"].very_common_min,
        "frequency_exclude_proper": defaults[
            "frequency"
        ].exclude_proper_nouns,
        "frequency_lemma_fallback": defaults[
            "frequency"
        ].enable_lemma_fallback,
        "frequency_coverage_warning": defaults[
            "frequency"
        ].low_coverage_warning_threshold,
        "aoa_early_max": defaults["aoa"].early_acquired_max,
        "aoa_later_min": defaults["aoa"].later_acquired_min,
        "aoa_coverage_warning": defaults["aoa"].low_coverage_warning_threshold,
        "aoa_exclude_proper": defaults["aoa"].exclude_proper_nouns,
        "aoa_lemma_fallback": defaults["aoa"].enable_lemma_fallback,
        "lexical_style_mattr_window": defaults[
            "lexical_style"
        ].mattr_window_size,
        "lexical_style_hdd_sample": defaults["lexical_style"].hdd_sample_size,
        "lexical_style_mtld_threshold": defaults[
            "lexical_style"
        ].mtld_threshold,
        "lexical_style_short_warning": defaults[
            "lexical_style"
        ].short_text_warning_threshold,
        "poetry_id_min_tokens": defaults["poetry_id"].minimum_matched_tokens,
        "poetry_id_min_types": defaults["poetry_id"].minimum_matched_types,
        "poetry_id_min_token_coverage": defaults[
            "poetry_id"
        ].minimum_token_coverage,
        "poetry_id_min_type_coverage": defaults[
            "poetry_id"
        ].minimum_type_coverage,
        "pronunciation_coverage_warning": defaults[
            "pronunciation"
        ].low_coverage_warning_threshold,
        "pronunciation_minimum_complete_lines": defaults[
            "pronunciation"
        ].minimum_complete_lines,
        "pronunciation_minimum_resolved_tokens": defaults[
            "pronunciation"
        ].minimum_resolved_tokens,
        "pronunciation_overrides": "",
        "meter_analysis_mode": "Compare candidate and performance-aware readings",
        "meter_style_profile": next(iter(METER_STYLE_LABELS)),
        "meter_interpretation_depth": list(METER_DEPTH_LABELS)[1],
        "meter_line_match_threshold": defaults["meter"].line_match_threshold,
        "meter_irregular_threshold": defaults["meter"].irregular_fit_threshold,
        "meter_ambiguity_margin": defaults["meter"].ambiguity_margin_threshold,
        "meter_maximum_variants": defaults["meter"].maximum_line_variants,
        "meter_performance_candidate_limit": defaults[
            "meter"
        ].performance_candidate_limit,
        "meter_realized_alternatives": defaults[
            "meter"
        ].retained_realized_alternatives,
        "meter_allow_visible_elision": defaults[
            "meter"
        ].allow_visible_poetic_elision,
        "meter_scholar_revisions": "",
        "phonological_slant_threshold": defaults[
            "phonology"
        ].slant_rhyme_threshold,
        "phonological_sound_repetitions": defaults[
            "phonology"
        ].minimum_sound_repetitions,
        "phonological_coverage_warning": defaults[
            "phonology"
        ].low_ending_coverage_warning_threshold,
        "phonological_maximum_pairs": defaults[
            "phonology"
        ].maximum_pair_evaluations,
    }
    for setting_name, default_value in configuration_defaults.items():
        st.session_state.setdefault(key(setting_name), default_value)
    with st.expander(
        "Shared Configuration and Methodology",
        expanded=False,
    ):
        st.caption(
            "Every choice below is applied identically to every poem. Disabled "
            "controls belong to modules that are not currently selected."
        )
        general = st.columns(2)
        phrase_label = general[0].selectbox(
            "Phrase policy",
            options=tuple(phrase_options),
            key=key("phrase_policy_label"),
        )
        minimum_matches = general[1].number_input(
            "Minimum evidence before a result is marked non-sparse",
            min_value=1,
            max_value=1000,
            step=1,
            key=key("minimum_matches"),
        )

        st.markdown("##### Concreteness")
        columns = st.columns(3)
        concrete_abstract = columns[0].number_input(
            "Highly abstract at or below",
            1.0,
            4.9,
            step=0.1,
            key=key("concreteness_abstract_max"),
            disabled="concreteness" not in selected,
        )
        concrete_high = columns[1].number_input(
            "Highly concrete at or above",
            1.1,
            5.0,
            step=0.1,
            key=key("concreteness_concrete_min"),
            disabled="concreteness" not in selected,
        )
        concrete_coverage = columns[2].number_input(
            "Coverage caution threshold",
            0.0,
            1.0,
            step=0.05,
            key=key("concreteness_coverage_warning"),
            disabled="concreteness" not in selected,
        )
        policies = st.columns(2)
        concrete_proper = policies[0].checkbox(
            "Exclude model-tagged proper nouns",
            key=key("concreteness_exclude_proper"),
            disabled="concreteness" not in selected,
        )
        concrete_phrases = policies[1].checkbox(
            "Activate exact source expressions",
            key=key("concreteness_phrases"),
            disabled="concreteness" not in selected,
        )

        st.markdown("##### Sensorimotor Imagery and Embodiment")
        columns = st.columns(3)
        sensor_proper = columns[0].checkbox(
            "Exclude proper nouns",
            key=key("sensorimotor_exclude_proper"),
            disabled="sensorimotor" not in selected,
        )
        sensor_phrases = columns[1].checkbox(
            "Activate published multiword concepts",
            key=key("sensorimotor_phrases"),
            disabled="sensorimotor" not in selected,
        )
        sensor_terms = columns[2].number_input(
            "Terms retained in compact rankings",
            3,
            100,
            step=1,
            key=key("sensorimotor_top_terms"),
            disabled="sensorimotor" not in selected,
        )

        st.markdown("##### Frequency and Rarity")
        columns = st.columns(4)
        rare_below = columns[0].number_input(
            "Rare below", 1.0, 7.0, step=0.1,
            key=key("frequency_rare_below"), disabled="frequency" not in selected,
        )
        uncommon_below = columns[1].number_input(
            "Uncommon below", 1.1, 7.2, step=0.1,
            key=key("frequency_uncommon_below"), disabled="frequency" not in selected,
        )
        moderate_below = columns[2].number_input(
            "Moderately common below", 1.2, 7.4,
            step=0.1,
            key=key("frequency_moderate_below"), disabled="frequency" not in selected,
        )
        common_min = columns[3].number_input(
            "Very common at or above", 1.3, 8.0,
            step=0.1,
            key=key("frequency_very_common_min"), disabled="frequency" not in selected,
        )
        columns = st.columns(3)
        frequency_proper = columns[0].checkbox(
            "Exclude proper nouns",
            key=key("frequency_exclude_proper"), disabled="frequency" not in selected,
        )
        frequency_content = False
        frequency_lemma = columns[1].checkbox(
            "Allow lemma fallback",
            key=key("frequency_lemma_fallback"), disabled="frequency" not in selected,
        )
        frequency_coverage = columns[2].number_input(
            "Coverage caution", 0.0, 1.0,
            step=0.05,
            key=key("frequency_coverage_warning"), disabled="frequency" not in selected,
        )

        st.markdown("##### Age of Acquisition")
        columns = st.columns(3)
        aoa_early = columns[0].number_input(
            "Early acquired at or below", 0.0, 24.9,
            step=0.5,
            key=key("aoa_early_max"), disabled="aoa" not in selected,
        )
        aoa_late = columns[1].number_input(
            "Later acquired at or above", 0.1, 25.0,
            step=0.5,
            key=key("aoa_later_min"), disabled="aoa" not in selected,
        )
        aoa_coverage = columns[2].number_input(
            "Coverage caution", 0.0, 1.0,
            step=0.05,
            key=key("aoa_coverage_warning"), disabled="aoa" not in selected,
        )
        columns = st.columns(2)
        aoa_proper = columns[0].checkbox(
            "Exclude proper nouns",
            key=key("aoa_exclude_proper"), disabled="aoa" not in selected,
        )
        aoa_content = False
        aoa_lemma = columns[1].checkbox(
            "Allow lemma fallback",
            key=key("aoa_lemma_fallback"), disabled="aoa" not in selected,
        )

        st.markdown("##### Lexical Diversity and Structure")
        columns = st.columns(4)
        mattr_window = columns[0].number_input(
            "MATTR window", 2, 1000, step=1,
            key=key("lexical_style_mattr_window"), disabled="lexical_style" not in selected,
        )
        hdd_sample = columns[1].number_input(
            "HD-D sample", 2, 1000, step=1,
            key=key("lexical_style_hdd_sample"), disabled="lexical_style" not in selected,
        )
        mtld_threshold = columns[2].number_input(
            "MTLD threshold", 0.01, 0.99, step=0.01,
            key=key("lexical_style_mtld_threshold"), disabled="lexical_style" not in selected,
        )
        short_warning = columns[3].number_input(
            "Short-text caution below", 2, 1000,
            step=1,
            key=key("lexical_style_short_warning"), disabled="lexical_style" not in selected,
        )

        st.markdown("##### PoetryID")
        columns = st.columns(4)
        poetry_tokens = columns[0].number_input(
            "Minimum matched tokens", 1, 1000,
            step=1,
            key=key("poetry_id_min_tokens"), disabled="poetry_id" not in selected,
        )
        poetry_types = columns[1].number_input(
            "Minimum matched types", 1, 1000,
            step=1,
            key=key("poetry_id_min_types"), disabled="poetry_id" not in selected,
        )
        poetry_token_coverage = columns[2].number_input(
            "Minimum token coverage", 0.0, 1.0,
            step=0.05,
            key=key("poetry_id_min_token_coverage"), disabled="poetry_id" not in selected,
        )
        poetry_type_coverage = columns[3].number_input(
            "Minimum type coverage", 0.0, 1.0,
            step=0.05,
            key=key("poetry_id_min_type_coverage"), disabled="poetry_id" not in selected,
        )

        sound_enabled = bool(
            selected & {"pronunciation", "meter", "phonology", "inherited_form"}
        )
        st.markdown("##### Pronunciation, Meter, and Sound")
        columns = st.columns(3)
        pronunciation_coverage = columns[0].number_input(
            "Pronunciation coverage caution", 0.0, 1.0,
            step=0.05,
            key=key("pronunciation_coverage_warning"), disabled=not sound_enabled,
        )
        pronunciation_lines = columns[1].number_input(
            "Minimum complete lines", 1, 1000,
            step=1,
            key=key("pronunciation_minimum_complete_lines"), disabled=not sound_enabled,
        )
        pronunciation_tokens = columns[2].number_input(
            "Minimum resolved tokens", 1, 1000,
            step=1,
            key=key("pronunciation_minimum_resolved_tokens"), disabled=not sound_enabled,
        )
        pronunciation_overrides = st.text_area(
            "Shared poem-specific pronunciation overrides",
            key=key("pronunciation_overrides"),
            disabled=not sound_enabled,
            placeholder="learned = L ER1 N IH0 D | optional note",
            help="These session-only overrides are applied to every compared poem.",
        )
        meter_enabled = bool(selected & {"meter", "inherited_form"})
        meter_interpretation = st.columns(3)
        meter_mode_label = meter_interpretation[0].selectbox(
            "Meter analysis level",
            options=list(METER_MODE_LABELS),
            key=key("meter_analysis_mode"),
            disabled=not meter_enabled,
            help=(
                "Candidate meter preserves the fixed-template layer. The "
                "performance-aware layer adds a transparent contextual reading "
                "without changing lexical stress."
            ),
        )
        meter_analysis_mode = METER_MODE_LABELS[meter_mode_label]
        meter_style_label = meter_interpretation[1].selectbox(
            "Declared interpretation profile",
            options=list(METER_STYLE_LABELS),
            key=key("meter_style_profile"),
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
        )
        meter_depth_label = meter_interpretation[2].selectbox(
            "Interpretation detail",
            options=list(METER_DEPTH_LABELS),
            key=key("meter_interpretation_depth"),
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
        )
        columns = st.columns(4)
        meter_line = columns[0].number_input(
            "Meter line-fit threshold", 0.0, 1.0,
            step=0.05,
            key=key("meter_line_match_threshold"), disabled=not meter_enabled,
        )
        meter_poem = columns[1].number_input(
            "Poem candidate-fit threshold", 0.0, 1.0,
            step=0.05,
            key=key("meter_irregular_threshold"), disabled=not meter_enabled,
        )
        meter_margin = columns[2].number_input(
            "Candidate margin", 0.0, 1.0,
            step=0.01,
            key=key("meter_ambiguity_margin"), disabled=not meter_enabled,
        )
        meter_variants = columns[3].number_input(
            "Maximum stress paths", 1, 4096,
            step=1,
            key=key("meter_maximum_variants"), disabled=not meter_enabled,
        )
        meter_realization = st.columns(3)
        meter_performance_candidate_limit = meter_realization[0].number_input(
            "Realization candidates per line",
            2,
            40,
            step=1,
            key=key("meter_performance_candidate_limit"),
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
        )
        meter_realized_alternatives = meter_realization[1].number_input(
            "Retained realized alternatives",
            1,
            8,
            step=1,
            key=key("meter_realized_alternatives"),
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
        )
        meter_allow_visible_elision = meter_realization[2].checkbox(
            "Recognize visibly marked contractions",
            key=key("meter_allow_visible_elision"),
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
            help=(
                "Only preserved spellings such as o'er may be recognized; "
                "unmarked syllables are never silently removed."
            ),
        )
        meter_scholar_revisions = st.text_area(
            "Shared scholar scansion revisions",
            key=key("meter_scholar_revisions"),
            height=100,
            disabled=(
                not meter_enabled
                or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
            ),
            placeholder=(
                "line 2 = iambic pentameter | "
                "x / x / x / x / x / | reason for the revised reading"
            ),
            help=(
                "Optional. Line numbers are interpreted separately within each "
                "compared poem; use only revisions that apply across the set."
            ),
        )
        columns = st.columns(4)
        slant_threshold = columns[0].number_input(
            "Slant-rhyme threshold", 0.0, 1.0,
            step=0.01,
            key=key("phonological_slant_threshold"), disabled="phonology" not in selected and "inherited_form" not in selected,
        )
        sound_repetitions = columns[1].number_input(
            "Minimum repeated sounds", 2, 20,
            step=1,
            key=key("phonological_sound_repetitions"), disabled="phonology" not in selected and "inherited_form" not in selected,
        )
        ending_coverage = columns[2].number_input(
            "Ending coverage caution", 0.0, 1.0,
            step=0.05,
            key=key("phonological_coverage_warning"), disabled="phonology" not in selected and "inherited_form" not in selected,
        )
        maximum_pairs = columns[3].number_input(
            "Maximum ending pairs", 1, 100000,
            step=100,
            key=key("phonological_maximum_pairs"), disabled="phonology" not in selected and "inherited_form" not in selected,
        )

    vad_sources = tuple(
        lexicon_id
        for lexicon_id in selected_lexicons
        if lexicon_id in {
            "warriner_vad_2013",
            "nrc_vad_v1",
            "nrc_vad_v2_1",
        }
    )
    error = ""
    try:
        configuration = _SharedComparisonConfiguration(
            phrase_policy=phrase_options[phrase_label],
            minimum_matches=int(minimum_matches),
            concreteness=ConcretenessConfiguration(
                highly_abstract_max=float(concrete_abstract),
                highly_concrete_min=float(concrete_high),
                exclude_proper_nouns=bool(concrete_proper),
                activate_multiword_expressions=bool(concrete_phrases),
                minimum_rated_tokens=int(minimum_matches),
                low_coverage_warning_threshold=float(concrete_coverage),
            ),
            sensorimotor=SensorimotorConfiguration(
                include_phrases=bool(sensor_phrases),
                exclude_proper_nouns=bool(sensor_proper),
                minimum_match_requirement=int(minimum_matches),
                top_term_count=int(sensor_terms),
            ),
            frequency=FrequencyConfiguration(
                rare_below=float(rare_below),
                uncommon_below=float(uncommon_below),
                moderately_common_below=float(moderate_below),
                very_common_min=float(common_min),
                exclude_proper_nouns=bool(frequency_proper),
                content_words_only=bool(frequency_content),
                enable_lemma_fallback=bool(frequency_lemma),
                minimum_matched_tokens=int(minimum_matches),
                low_coverage_warning_threshold=float(frequency_coverage),
            ),
            aoa=AoAConfiguration(
                early_acquired_max=float(aoa_early),
                later_acquired_min=float(aoa_late),
                exclude_proper_nouns=bool(aoa_proper),
                content_words_only=bool(aoa_content),
                enable_lemma_fallback=bool(aoa_lemma),
                minimum_matched_tokens=int(minimum_matches),
                low_coverage_warning_threshold=float(aoa_coverage),
            ),
            lexical_style=LexicalStyleConfiguration(
                mattr_window_size=int(mattr_window),
                hdd_sample_size=int(hdd_sample),
                mtld_threshold=float(mtld_threshold),
                short_text_warning_threshold=int(short_warning),
            ),
            poetry_id=PoetryIDConfiguration(
                weighting_modes=("token", "type"),
                analysis_views=(
                    "all_matched",
                    "stopwords_excluded",
                    "content_words",
                ),
                vad_lexicon_ids=vad_sources,
                minimum_matched_tokens=int(poetry_tokens),
                minimum_matched_types=int(poetry_types),
                minimum_token_coverage=float(poetry_token_coverage),
                minimum_type_coverage=float(poetry_type_coverage),
            ),
            pronunciation=PronunciationConfiguration(
                overrides=parse_pronunciation_overrides(pronunciation_overrides),
                low_coverage_warning_threshold=float(pronunciation_coverage),
                minimum_complete_lines=int(pronunciation_lines),
                minimum_resolved_tokens=int(pronunciation_tokens),
            ),
            meter=MeterConfiguration(
                line_match_threshold=float(meter_line),
                irregular_fit_threshold=float(meter_poem),
                ambiguity_margin_threshold=float(meter_margin),
                maximum_line_variants=int(meter_variants),
                analysis_mode=meter_analysis_mode,
                style_profile=METER_STYLE_LABELS[meter_style_label],
                interpretation_depth=METER_DEPTH_LABELS[meter_depth_label],
                performance_candidate_limit=int(
                    meter_performance_candidate_limit
                ),
                retained_realized_alternatives=int(
                    meter_realized_alternatives
                ),
                allow_visible_poetic_elision=bool(
                    meter_allow_visible_elision
                ),
                scholar_revisions=(
                    ()
                    if meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                    else parse_meter_scholar_revisions(
                        meter_scholar_revisions
                    )
                ),
            ),
            phonology=PhonologicalConfiguration(
                slant_rhyme_threshold=float(slant_threshold),
                minimum_sound_repetitions=int(sound_repetitions),
                low_ending_coverage_warning_threshold=float(ending_coverage),
                maximum_pair_evaluations=int(maximum_pairs),
            ),
        )
        if "poetry_id" in selected and not vad_sources:
            raise ValueError("PoetryID requires at least one selected VAD lexicon.")
    except ValueError as exc:
        error = str(exc)
        st.warning(error)
        configuration = _SharedComparisonConfiguration(
            phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
            minimum_matches=3,
            concreteness=defaults["concreteness"],
            sensorimotor=defaults["sensorimotor"],
            frequency=defaults["frequency"],
            aoa=defaults["aoa"],
            lexical_style=defaults["lexical_style"],
            poetry_id=defaults["poetry_id"],
            pronunciation=defaults["pronunciation"],
            meter=defaults["meter"],
            phonology=defaults["phonology"],
        )
    return configuration, error


def render_compare_poems_workspace(
    preprocessor: TextPreprocessor,
    readiness: ResourceReadiness,
) -> None:
    """Render a session-only shared-design comparison of two through ten poems."""

    pending_pronunciation_overrides = st.session_state.pop(
        "_pending_compare_pronunciation_overrides",
        None,
    )
    if pending_pronunciation_overrides is not None:
        st.session_state["compare_config_pronunciation_overrides"] = str(
            pending_pronunciation_overrides
        )
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
        "then inspect focused poem-level evidence side by side.",
        kicker="Multi-poem comparative evaluation for close reading",
        status="Session only",
    )
    st.caption(
        "VerseVAD reports comparable normative evidence. It does not rank "
        "literary quality, identify a poem's emotion, or treat observed ranges "
        "as significance tests."
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
    selected_reference_corpus: ReferenceCorpusDescriptor | None = None

    with st.container(border=True):
        st.subheader("2. Choose One Shared Analysis Profile")
        builtin_profile_names = list(MODULE_PRESETS)
        profile_options = analysis_profile_options(builtin_profile_names)
        consume_pending_profile_selection(
            scope_key="compare_poems",
            selection_state_key="compare_analysis_profile",
            options=profile_options,
        )
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
        elif selected_custom_profile_name(selected_profile) is not None:
            st.caption(
                "A saved custom configuration shared with every analytical "
                "workspace. Apply it, then continue customizing if needed."
            )
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
            for source_key, target_key in (
                _PROFILE_TO_COMPARE_STOPWORD_KEYS.items()
            ):
                if source_key in profile_settings:
                    st.session_state[target_key] = profile_settings[source_key]
            for source_key, target_key in (
                _PROFILE_TO_COMPARE_CONFIGURATION_KEYS.items()
            ):
                if source_key in profile_settings:
                    st.session_state[target_key] = profile_settings[source_key]
            apply_profile_display_defaults(selected_profile, "compare_poems")
            st.session_state.pop("poem_comparison_set", None)
            st.rerun()

        render_custom_profile_manager(
            scope_key="compare_poems",
            selected_profile=selected_profile,
            selection_state_key="compare_analysis_profile",
            current_settings=_comparison_profile_snapshot(),
            builtin_profile_names=builtin_profile_names,
        )

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
        if "versemap" in selected_modules:
            corpora = tuple(
                item
                for item in list_reference_corpora(
                    include_user=(
                        os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") != "1"
                    )
                )
                if item.index_available
            )
            if corpora:
                corpus_by_label = {
                    f"{item.display_name} | {item.scope_label}": item
                    for item in corpora
                }
                selected_corpus_label = st.selectbox(
                    "VerseMap reference corpus",
                    options=tuple(corpus_by_label),
                    key="compare_versemap_reference_corpus",
                    help=(
                        "All poems are projected into this same indexed Standard "
                        "Profile 1.0 reference space. Local user corpora appear "
                        "after they are validated and indexed."
                    ),
                )
                selected_reference_corpus = corpus_by_label[
                    selected_corpus_label
                ]
            else:
                st.warning(
                    "No indexed VerseMap reference corpus is available. Disable "
                    "VerseMap or build an index under Collections > Reference Corpora."
                )
        with st.expander("Shared Stopword Resource and Exclusions", expanded=False):
            stopwords = render_stopword_settings("compare")
        shared_configuration, configuration_error = (
            _render_shared_comparison_configuration(
                selected_lexicons=list(selected_lexicons),
                selected_modules=list(selected_modules),
            )
        )

    with st.container(border=True):
        st.subheader("3. Analyze and Compare")
        analyze = st.button(
            f"Analyze {len(poem_ids)} Poems",
            type="primary",
            width="stretch",
            key="compare_analyze_set",
        )
        analyze = analyze or bool(
            st.session_state.pop("_compare_reanalyze_requested", False)
        )
        if analyze:
            if configuration_error:
                st.error(configuration_error)
                return
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
                        phrase_policy=shared_configuration.phrase_policy,
                        minimum_match_requirement=(
                            shared_configuration.minimum_matches
                        ),
                        stopword_mode=stopwords.mode,
                        protected_stopwords=stopwords.protected_words,
                        custom_stopword_additions=stopwords.custom_additions,
                        custom_stopword_removals=stopwords.custom_removals,
                        include_concreteness="concreteness" in selected,
                        concreteness_configuration=(
                            shared_configuration.concreteness
                        ),
                        include_frequency="frequency" in selected,
                        frequency_configuration=shared_configuration.frequency,
                        include_aoa="aoa" in selected,
                        aoa_configuration=shared_configuration.aoa,
                        include_sensorimotor="sensorimotor" in selected,
                        sensorimotor_configuration=(
                            shared_configuration.sensorimotor
                        ),
                        include_lexical_style="lexical_style" in selected,
                        lexical_style_configuration=(
                            shared_configuration.lexical_style
                        ),
                        include_poetry_id="poetry_id" in selected,
                        poetry_id_configuration=shared_configuration.poetry_id,
                        include_pronunciation=include_pronunciation,
                        pronunciation_configuration=(
                            shared_configuration.pronunciation
                        ),
                        include_meter=include_meter,
                        meter_configuration=shared_configuration.meter,
                        include_phonology=include_phonology,
                        phonological_configuration=(
                            shared_configuration.phonology
                        ),
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
                    versemap_index = (
                        load_corpus_index(selected_reference_corpus)
                        if "versemap" in selected
                        and selected_reference_corpus is not None
                        else None
                    )
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
                                    versemap_index=versemap_index,
                                )
                            )
                        st.session_state["poem_comparison_set"] = (
                            build_poem_comparison_set(analyses)
                        )
                        st.session_state[
                            "compare_results_pronunciation_overrides"
                        ] = st.session_state.get(
                            "compare_config_pronunciation_overrides",
                            "",
                        )
                        status.update(
                            label="Comparison-set analysis complete.",
                            state="complete",
                            expanded=False,
                        )
                except (
                    ValueError,
                    WorkspaceAnalysisError,
                    ReferenceCorpusError,
                ) as error:
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
