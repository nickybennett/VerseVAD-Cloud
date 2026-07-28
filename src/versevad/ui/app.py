"""VerseVAD local one-text, corpus, and lexicon-exploration interface."""

from __future__ import annotations

import hashlib
import io
import importlib
import os
import sys
import zipfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import versevad.application as _application_services
import versevad.adapters.nrc_vad as _nrc_vad_services
import versevad.db.repository as _repository_services
import versevad.prosody.pronunciation as _pronunciation_services
import versevad.ui.design as _design_services
import versevad.ui.preferences as _preference_services

# The local source may be updated while a Streamlit server is still open.
# Streamlit reruns this page but Python normally retains already imported
# service modules, which can momentarily pair a new interface with an older
# application API or adapter policy. Reload only when a required revision is
# absent so an already-open local session activates NRC VAD v1 phrases too.
_application_was_reloaded = (
    not all(
        hasattr(_application_services, name)
        for name in (
            "VAD_DEFINITIONS",
            "vad_cumulative_views",
            "vad_contributor_views",
            "vad_sensitivity_views",
            "part_of_speech_views",
            "detailed_part_of_speech_views",
            "vad_part_of_speech_views",
            "lexical_trajectory_views",
            "RESOURCE_ROOT",
            "FrequencyConfiguration",
            "AoAConfiguration",
            "PronunciationConfiguration",
            "MeterConfiguration",
            "PhonologicalConfiguration",
            "LexicalStyleConfiguration",
            "PoetryIDConfiguration",
            "InheritedFormConfiguration",
            "installed_resource_readiness",
        )
    )
    or getattr(_nrc_vad_services.NrcVadV1Adapter, "adapter_version", "") != "0.3.0"
    or not _nrc_vad_services.NrcVadV1Adapter.configuration.phrase_support
    or getattr(_repository_services, "SCHEMA_VERSION", 0) < 3
    or (
        getattr(_pronunciation_services.PronunciationModule, "version", "")
        != "1.2.0"
    )
)
if _application_was_reloaded:
    # Reload the framework-independent dependency graph in type-definition
    # order. This is used only after updates to an already-running local
    # Streamlit process; a normal launch imports each module once.
    for _module_name in (
        "versevad.models",
        "versevad.preprocessing",
        "versevad.stopwords",
        "versevad.analysis.statistics",
        "versevad.adapters.base",
        "versevad.adapters.warriner",
        "versevad.adapters.nrc_vad",
        "versevad.adapters.nrc_emotion",
        "versevad.adapters.nrc_intensity",
        "versevad.adapters.concreteness",
        "versevad.adapters.subtlex_us",
        "versevad.adapters.kuperman_aoa",
        "versevad.adapters.cmudict",
        "versevad.adapters",
        "versevad.analysis.phase2",
        "versevad.lexical_semantic.concreteness",
        "versevad.lexical_semantic.frequency",
        "versevad.lexical_semantic.aoa",
        "versevad.lexical_semantic.sentiment",
        "versevad.lexical_semantic.readability",
        "versevad.prosody.pronunciation",
        "versevad.prosody.meter",
        "versevad.prosody",
        "versevad.phonology.rhyme",
        "versevad.phonology",
        "versevad.lexical_style.profile",
        "versevad.lexical_style",
        "versevad.poetry_id.archetypes",
        "versevad.poetry_id.engine",
        "versevad.poetry_id.integration",
        "versevad.poetry_id",
        "versevad.inherited_form.profiles",
        "versevad.inherited_form.engine",
        "versevad.inherited_form",
        "versevad.exports.concreteness",
        "versevad.exports.frequency",
        "versevad.exports.aoa",
        "versevad.exports.pronunciation",
        "versevad.exports.meter",
        "versevad.exports.phonology",
        "versevad.exports.lexical_style",
        "versevad.exports.poetry_id",
        "versevad.exports.inherited_form",
        "versevad.exports.sentiment",
        "versevad.exports.readability",
        "versevad.ui.poetry_id",
        "versevad.ui.inherited_form",
    ):
        _module = importlib.import_module(_module_name)
        importlib.reload(_module)
    importlib.reload(_application_services)
    for _module_name in (
        "versevad.db.repository",
        "versevad.db",
        "versevad.corpus",
        "versevad.ui.corpus",
    ):
        if _module_name in sys.modules:
            importlib.reload(sys.modules[_module_name])

from versevad import __version__
from versevad.application import (
    AnalysisRequest,
    LEXICON_SPECS,
    PROJECT_ROOT,
    RESOURCE_DOWNLOAD_PAGES,
    ResourceReadiness,
    TextImportError,
    VAD_DEFINITIONS,
    WorkspaceAnalysisError,
    coverage_views,
    csv_reading_guide,
    decode_uploaded_text,
    detailed_export_zip,
    detailed_part_of_speech_views,
    emotion_association_views,
    emotion_intensity_views,
    installed_resource_readiness,
    lexical_trajectory_views,
    match_views,
    overview_notes,
    part_of_speech_views,
    run_workspace_analysis,
    scholar_summary_csv,
    sentiment_association_views,
    unmatched_views,
    vad_contributor_views,
    vad_cumulative_views,
    vad_interpretation_views,
    vad_part_of_speech_views,
    vad_sensitivity_views,
    vad_views,
)
from versevad.diagnostics import run_self_test
from versevad.lexical_semantic.concreteness import (
    ConcretenessConfiguration,
)
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.frequency import (
    FrequencyConfiguration,
)
from versevad.lexical_style import LexicalStyleConfiguration
from versevad.inherited_form import InheritedFormConfiguration
from versevad.models import PhrasePolicy
from versevad.preprocessing import SpacyEnglishPreprocessor
from versevad.prosody.pronunciation import (
    PronunciationConfiguration,
    PronunciationStatus,
    parse_pronunciation_overrides,
    upsert_pronunciation_override_text,
)
from versevad.prosody.audio import (
    PronunciationAudioError,
    normalize_arpabet_phones,
    synthesize_arpabet_wav,
)
from versevad.prosody.g2p import (
    G2PPredictionError,
    predict_arpabet,
)
from versevad.prosody.meter import (
    MeterAnalysisMode,
    MeterConfiguration,
    MeterInterpretationDepth,
    MeterStyleProfile,
    parse_meter_scholar_revisions,
)
from versevad.phonology import PhonologicalConfiguration
from versevad.poetry_id import (
    SUPPORTED_VAD_LEXICON_IDS,
    PoetryIDConfiguration,
    ThresholdBand,
    ThresholdProfile,
)
from versevad.ui.poetry_id import render_poetry_id
from versevad.ui.inherited_form import render_inherited_form
from versevad.ui.stopwords import render_stopword_settings
from versevad.ui.design import (
    MODULE_PRESETS,
    PUBLICATION_CHART_COLORS,
    collapse_control_html,
    publication_chart,
    preset_widget_state,
    render_app_shell,
    render_dataframe,
    render_empty_state,
    render_section_intro,
    render_stateful_section_navigation,
    render_workspace_header,
)


st.set_page_config(
    page_title="VerseVAD",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit reruns this page when a dependency changes but retains already
# imported dependency modules. Use an explicit revision marker for Explorer
# compatibility fixes so an open local session reloads both the service and UI
# modules exactly once, then retains normal session state on later interactions.
_DEVELOPMENT_HOT_RELOAD = os.environ.get("VERSEVAD_DEV_HOT_RELOAD") == "1"
_EXPLORER_RUNTIME_REVISION = "2026-07-24-explorer-4"
_explorer_was_reloaded = (
    _DEVELOPMENT_HOT_RELOAD
    and st.session_state.get("_explorer_runtime_revision")
    != _EXPLORER_RUNTIME_REVISION
)
if _explorer_was_reloaded:
    import versevad.explorer as _explorer_services
    import versevad.ui.explorer as _explorer_ui_services

    importlib.reload(_explorer_services)
    importlib.reload(_explorer_ui_services)
    st.session_state["_explorer_runtime_revision"] = _EXPLORER_RUNTIME_REVISION

# Keep an already-open development server aligned with the current corpus
# CSV/DOCX exporter and corpus page.
_CORPUS_RUNTIME_REVISION = "2026-07-25-csv-docx-1"
import versevad.exports.corpus_csv as _corpus_export_services

_corpus_was_reloaded = (
    getattr(_corpus_export_services, "CORPUS_EXPORT_API_VERSION", 0) < 1
    or (
        _DEVELOPMENT_HOT_RELOAD
        and st.session_state.get("_corpus_runtime_revision")
        != _CORPUS_RUNTIME_REVISION
    )
)
if _corpus_was_reloaded:
    importlib.reload(_corpus_export_services)
    if "versevad.ui.corpus" in sys.modules:
        importlib.reload(sys.modules["versevad.ui.corpus"])
    st.session_state["_corpus_runtime_revision"] = _CORPUS_RUNTIME_REVISION

# Stage 13 centralizes the shell and appearance tokens. Reload the presentation
# modules once in an already-open local server so theme and workspace changes
# do not require the scholar to restart VerseVAD manually.
_DESIGN_RUNTIME_REVISION = "2026-07-28-design-7"
_design_was_reloaded = (
    _DEVELOPMENT_HOT_RELOAD
    and st.session_state.get("_design_runtime_revision")
    != _DESIGN_RUNTIME_REVISION
)
if _design_was_reloaded:
    importlib.reload(_design_services)
    import versevad.ui.poetry_id as _poetry_id_ui_services
    import versevad.ui.inherited_form as _inherited_form_ui_services

    importlib.reload(_poetry_id_ui_services)
    importlib.reload(_inherited_form_ui_services)
    for _module_name in ("versevad.ui.corpus", "versevad.ui.explorer"):
        if _module_name in sys.modules:
            importlib.reload(sys.modules[_module_name])
    MODULE_PRESETS = _design_services.MODULE_PRESETS
    PUBLICATION_CHART_COLORS = _design_services.PUBLICATION_CHART_COLORS
    collapse_control_html = _design_services.collapse_control_html
    publication_chart = _design_services.publication_chart
    preset_widget_state = _design_services.preset_widget_state
    render_app_shell = _design_services.render_app_shell
    render_dataframe = _design_services.render_dataframe
    render_empty_state = _design_services.render_empty_state
    render_section_intro = _design_services.render_section_intro
    render_stateful_section_navigation = (
        _design_services.render_stateful_section_navigation
    )
    render_workspace_header = _design_services.render_workspace_header
    render_poetry_id = _poetry_id_ui_services.render_poetry_id
    render_inherited_form = _inherited_form_ui_services.render_inherited_form
    st.session_state["_design_runtime_revision"] = _DESIGN_RUNTIME_REVISION

if _application_was_reloaded:
    st.session_state.pop("workspace", None)
if _application_was_reloaded or _explorer_was_reloaded:
    st.session_state.pop("lexicon_explorer_result", None)


@st.cache_resource(show_spinner=False)
def _preprocessor() -> SpacyEnglishPreprocessor:
    return SpacyEnglishPreprocessor()


def _percentage(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _decimal(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _clear_current_text() -> None:
    """Clear widget state before the text-area widget is recreated."""

    st.session_state["poem_text"] = ""
    st.session_state.pop("upload_signature", None)


def _frame(rows, rename: dict[str, str] | None = None) -> pd.DataFrame:
    data = pd.DataFrame([asdict(row) for row in rows])
    return data.rename(columns=rename or {})


def _stateful_expander(label: str, *, state_key: str):
    """Return a default-collapsed expander with a stable analytical label."""

    del state_key
    return st.expander(label, expanded=False)


def _render_bottom_collapse_button(label: str, *, state_key: str) -> None:
    st.html(
        collapse_control_html(label, state_key),
        width="stretch",
        unsafe_allow_javascript=True,
    )


def _bottom_collapsible_expander(
    label: str,
    *,
    state_key: str,
    collapse_label: str,
):
    """Create a report expander with a compact collapse action at its end."""

    expander = _stateful_expander(label, state_key=state_key)

    @contextmanager
    def _contents():
        with expander:
            yield
            _render_bottom_collapse_button(
                collapse_label,
                state_key=state_key,
            )

    return _contents()


def _queue_pronunciation_resolutions(
    selections: tuple[tuple[str, str, str, str, str], ...],
) -> bool:
    """Copy selected candidates into the editable session overrides."""

    try:
        override_text = st.session_state.get("pronunciation_overrides", "")
        prepared: list[tuple[str, str, str]] = []
        for (
            surface_form,
            state_key,
            source_kind,
            provisional_phones,
            source_label,
        ) in selections:
            phones_text = st.session_state.get(state_key)
            if not phones_text:
                continue
            normalized_phones = normalize_arpabet_phones(str(phones_text))
            if source_kind == "g2p":
                predicted_phones = (
                    normalize_arpabet_phones(provisional_phones)
                    if provisional_phones
                    else ""
                )
                if predicted_phones and normalized_phones == predicted_phones:
                    note = (
                        "User approved this provisional G2P prediction in "
                        f"Words Needing Attention; source: {source_label}."
                    )
                else:
                    note = (
                        "User edited and approved this session pronunciation "
                        "in Words Needing Attention"
                        + (
                            f"; provisional source: {source_label}."
                            if source_label
                            else "."
                        )
                    )
            else:
                note = (
                    "User selected this retained CMUdict candidate in "
                    "Words Needing Attention."
                )
            prepared.append((surface_form, normalized_phones, note))
        if not prepared:
            raise ValueError(
                "Select or approve at least one pronunciation candidate."
            )
        for surface_form, phones_text, note in prepared:
            override_text = upsert_pronunciation_override_text(
                override_text,
                term=surface_form,
                phones_text=phones_text,
                note=note,
            )
        # The editable Advanced methodology textarea owns
        # ``pronunciation_overrides``. A result fragment runs after that widget
        # was instantiated, so Streamlit forbids writing its key here. Stage
        # the serialized value under a non-widget key; the ensuing full rerun
        # copies it into the widget state before recreating the textarea.
        st.session_state["_pending_pronunciation_overrides"] = override_text
        st.session_state["_apply_pronunciation_resolutions"] = True
        st.session_state["_pronunciation_resolution_count"] = len(prepared)
        st.session_state.pop("_pronunciation_resolution_error", None)
        return True
    except (PronunciationAudioError, ValueError) as error:
        st.session_state["_pronunciation_resolution_error"] = str(error)
        return False


def _render_pronunciation_attention_contents(pronunciation) -> None:
    """Render auditable ambiguity resolution without rerunning the whole page."""

    unresolved = [
        item
        for item in pronunciation.token_audit
        if item.eligible and not item.resolved
    ]
    st.markdown("#### Review Summary")
    if not unresolved:
        st.success(
            "Every eligible observed word form has resolved dictionary "
            "syllable and lexical-stress evidence."
        )
        return

    render_dataframe(
        pd.DataFrame(
            [
                {
                    "Surface": item.surface_form,
                    "Line": item.line_number,
                    "Status": item.status.value.replace("_", " "),
                    "Candidate phones": " | ".join(
                        item.dictionary_candidate_phones
                    ),
                    "Candidate stresses": " | ".join(
                        item.dictionary_candidate_stresses
                    ),
                    "Candidate syllables": " | ".join(
                        str(value)
                        for value in item.dictionary_candidate_syllable_counts
                    ),
                    "Why": item.reason,
                }
                for item in unresolved
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    ambiguous_by_form = {}
    unmatched_by_form = {}
    for item in unresolved:
        if item.status is PronunciationStatus.AMBIGUOUS_DICTIONARY:
            ambiguous_by_form.setdefault(item.normalized_form, item)
        elif item.status is PronunciationStatus.UNMATCHED:
            unmatched_by_form.setdefault(item.normalized_form, item)

    selections: list[tuple[str, str, str, str, str]] = []
    if ambiguous_by_form:
        st.markdown("#### Resolve Dictionary Ambiguities for This Session")
        st.caption(
            "Choose only when the poem's context supports one retained CMUdict "
            "candidate. Applying choices updates the session override field and "
            "reanalyzes pronunciation, meter, sound, and inherited-form evidence."
        )
        for normalized_form, item in ambiguous_by_form.items():
            line_numbers = sorted(
                {
                    row.line_number
                    for row in unresolved
                    if row.normalized_form == normalized_form
                }
            )
            with st.container(border=True):
                st.markdown(
                    f"**{item.surface_form}** · "
                    f"line{'s' if len(line_numbers) != 1 else ''} "
                    + ", ".join(str(value) for value in line_numbers)
                )
                options = tuple(item.dictionary_candidate_phones)
                state_key = (
                    "pronunciation_resolution_"
                    + hashlib.sha256(
                        (
                            pronunciation.module_result.result_id
                            + "|"
                            + normalized_form
                        ).encode("utf-8")
                    ).hexdigest()[:16]
                )
                selected = st.selectbox(
                    f"Pronunciation for {item.surface_form}",
                    options=options,
                    index=None,
                    placeholder="Select a CMUdict candidate",
                    key=state_key,
                    format_func=lambda phones: phones,
                )
                selections.append(
                    (item.surface_form, state_key, "dictionary", "", "CMUdict")
                )
                for candidate_index, phones_text in enumerate(options):
                    stress = item.dictionary_candidate_stresses[
                        candidate_index
                    ]
                    syllables = item.dictionary_candidate_syllable_counts[
                        candidate_index
                    ]
                    phone_column, detail_column, audio_column = st.columns(
                        [5, 2, 1]
                    )
                    phone_column.code(phones_text, language=None)
                    detail_column.caption(
                        f"{syllables} syllable"
                        f"{'s' if syllables != 1 else ''} · stress {stress}"
                    )
                    play = audio_column.button(
                        "Hear",
                        icon=":material/volume_up:",
                        help=(
                            "Play a local synthetic preview of this exact "
                            "ARPAbet candidate."
                        ),
                        key=f"{state_key}_audio_{candidate_index}",
                        type="tertiary",
                    )
                    if play:
                        try:
                            st.audio(
                                synthesize_arpabet_wav(phones_text),
                                format="audio/wav",
                                autoplay=True,
                                width="stretch",
                            )
                        except PronunciationAudioError as error:
                            st.warning(str(error))
                if selected:
                    st.success(
                        "Selected for the next session analysis: "
                        f"`{selected}`"
                    )

    show_out_of_dictionary = (
        st.toggle(
            "Show Out-of-Dictionary Words",
            value=False,
            key=(
                "show_out_of_dictionary_"
                + pronunciation.module_result.result_id
            ),
            help=(
                "Reveal provisional G2P candidates and session approval "
                "controls for words absent from CMUdict."
            ),
        )
        if unmatched_by_form
        else False
    )
    if unmatched_by_form and show_out_of_dictionary:
        st.markdown("#### Out-of-Dictionary Words")
        st.warning(
            "These words remain **unmatched**. The displayed G2P pronunciation "
            "is provisional—not confirmed evidence—and does not affect any "
            "result unless you explicitly approve or edit it."
        )
        st.caption(
            "Leave explicitly unresolved is the default. Approving or editing "
            "creates a reversible session-only pronunciation override and "
            "reanalyzes pronunciation, meter, sound, and inherited-form evidence."
        )
        for normalized_form, item in unmatched_by_form.items():
            line_numbers = sorted(
                {
                    row.line_number
                    for row in unresolved
                    if row.normalized_form == normalized_form
                }
            )
            state_seed = hashlib.sha256(
                (
                    pronunciation.module_result.result_id
                    + "|g2p|"
                    + normalized_form
                ).encode("utf-8")
            ).hexdigest()[:16]
            phones_key = f"pronunciation_g2p_phones_{state_seed}"
            decision_key = f"pronunciation_g2p_decision_{state_seed}"
            prediction_phones = ""
            prediction_label = ""
            prediction_ipa = ""
            prediction_error = ""
            try:
                prediction = predict_arpabet(item.surface_form)
                prediction_phones = prediction.phones_text
                prediction_label = prediction.source_label
                prediction_ipa = prediction.ipa_text
            except G2PPredictionError as error:
                prediction_error = str(error)

            st.session_state.setdefault(phones_key, prediction_phones)
            st.session_state.setdefault(
                decision_key,
                "Leave explicitly unresolved",
            )
            with st.container(border=True):
                st.markdown(
                    f"**{item.surface_form}** · "
                    f"line{'s' if len(line_numbers) != 1 else ''} "
                    + ", ".join(str(value) for value in line_numbers)
                )
                st.markdown(
                    "**Status: unmatched** · "
                    "**Prediction: provisional—not confirmed**"
                )
                if prediction_error:
                    st.warning(
                        prediction_error
                        + " You can still enter a reviewed ARPAbet sequence "
                        "manually below or leave the word unresolved."
                    )
                else:
                    st.caption(
                        f"Prediction source: {prediction_label}. "
                        f"Intermediate IPA: `{prediction_ipa}`"
                    )
                edited_phones = st.text_input(
                    f"Provisional ARPAbet for {item.surface_form} (editable)",
                    key=phones_key,
                    placeholder="Enter spaced CMUdict-style ARPAbet phones",
                    help=(
                        "Editing this field alone does not resolve the word. "
                        "Choose the approval option and apply before it becomes "
                        "a session pronunciation override."
                    ),
                )
                decision = st.radio(
                    f"Decision for {item.surface_form}",
                    options=(
                        "Leave explicitly unresolved",
                        "Approve or edit for this session",
                    ),
                    key=decision_key,
                    horizontal=True,
                    help=(
                        "No prediction is used unless you explicitly choose "
                        "the approval option and apply it."
                    ),
                )
                audio_column, explanation_column = st.columns([1, 5])
                play = audio_column.button(
                    "Hear",
                    icon=":material/volume_up:",
                    help=(
                        "Play a local synthetic preview of the currently "
                        "displayed editable ARPAbet."
                    ),
                    key=f"{phones_key}_audio",
                    type="tertiary",
                    disabled=not bool(edited_phones.strip()),
                )
                explanation_column.caption(
                    "The preview follows the editable field; hearing it does "
                    "not approve it."
                )
                if play:
                    try:
                        st.audio(
                            synthesize_arpabet_wav(edited_phones),
                            format="audio/wav",
                            autoplay=True,
                            width="stretch",
                        )
                    except PronunciationAudioError as error:
                        st.warning(str(error))
                if decision == "Approve or edit for this session":
                    selections.append(
                        (
                            item.surface_form,
                            phones_key,
                            "g2p",
                            prediction_phones,
                            prediction_label,
                        )
                    )
                    st.info(
                        "Pending approval for the next session analysis. "
                        "Use the Apply button below to confirm."
                    )

    if ambiguous_by_form or unmatched_by_form:
        apply_clicked = st.button(
            "Apply Approved Pronunciations and Reanalyze",
            type="primary",
            icon=":material/check_circle:",
            width="stretch",
            disabled=not any(
                st.session_state.get(state_key)
                for _, state_key, _, _, _ in selections
            ),
            key=(
                "apply_pronunciation_resolutions_"
                + pronunciation.module_result.result_id
            ),
        )
        if apply_clicked and _queue_pronunciation_resolutions(
            tuple(selections)
        ):
            # Ordinary fragment widgets rerun only this panel. The analysis
            # request lives in the full app, so promote a successful apply to
            # one app-scoped rerun after the state write. Streamlit explicitly
            # treats st.rerun() inside an on_click callback as a no-op.
            st.rerun(scope="app")

    if st.session_state.get("_pronunciation_resolution_error"):
        st.error(st.session_state["_pronunciation_resolution_error"])

    st.info(
        "Dictionary choices and explicitly approved or edited G2P candidates "
        "become poem-specific ARPAbet overrides in Advanced methodology "
        "settings. Unapproved predictions remain unmatched and unresolved. "
        "Approved choices apply to every exact occurrence of that observed "
        "form in this temporary session."
    )
    st.caption(
        "The speaker plays an offline eSpeak NG synthetic preview derived from "
        "the displayed ARPAbet sequence. It is an orientation aid—not a "
        "recording, dialect authority, or claim about performance."
    )


@st.fragment
def _render_pronunciation_attention(pronunciation) -> None:
    """Render pronunciation review in a compact, default-collapsed panel."""

    with st.expander("Words Needing Attention", expanded=False):
        _render_pronunciation_attention_contents(pronunciation)


def _display_self_test() -> None:
    with st.spinner("Checking the model, formulas, and five local lexicons…"):
        checks = run_self_test()
    st.session_state["self_test_checks"] = checks


def _render_resource_setup_notice(readiness: ResourceReadiness) -> None:
    unavailable = readiness.unavailable
    if not unavailable:
        return
    affected_lexicons = tuple(
        status
        for status in readiness.affective_lexicons
        if not status.available
    )
    affected_modules: list[str] = []
    if not readiness.concreteness.available:
        affected_modules.append("concreteness")
    if not readiness.frequency.available:
        affected_modules.append("frequency")
    if not readiness.aoa.available:
        affected_modules.append("Age of Acquisition")
    if not readiness.pronunciation_available:
        affected_modules.extend(("pronunciation", "meter", "rhyme/sound"))
    consequences: list[str] = []
    if affected_lexicons:
        consequences.append(
            f"{len(affected_lexicons)} affective source"
            f"{'s are' if len(affected_lexicons) != 1 else ' is'} unavailable"
        )
    if affected_modules:
        consequences.append(
            "the affected optional modules are disabled"
        )
    st.warning(
        f"Resource setup needs attention: {len(unavailable)} of "
        f"{len(readiness.all_statuses)} required runtime files are missing or "
        f"unsupported. {'; '.join(consequences).capitalize()}. "
        "Other installed analyses remain usable."
    )
    with st.expander("Resource setup details"):
        st.write(
            "VerseVAD never downloads research data automatically. Download each "
            "source under its own terms, keep its original contents unchanged, "
            "and place it at the exact destination below."
        )
        for status in unavailable:
            try:
                configured_path = status.configured_path.relative_to(PROJECT_ROOT)
            except ValueError:
                configured_path = status.configured_path
            source_page = RESOURCE_DOWNLOAD_PAGES.get(status.resource_id)
            st.markdown(
                f"**{status.display_name}** — "
                f"`{status.state.value.replace('_', ' ')}`"
            )
            st.code(str(configured_path), language=None)
            if source_page:
                st.markdown(f"[Open the official source/download page]({source_page})")
            if status.source_sha256:
                st.caption(
                    "The file exists, but its SHA-256 does not match the edition "
                    "VerseVAD has validated. It was not changed or analyzed."
                )
        st.caption(
            "Complete filenames, supported SHA-256 values, source terms, and "
            "installation steps: docs/resource-installation.md"
        )


workspace_page, _appearance_mode = render_app_shell()
resource_readiness = installed_resource_readiness()
_render_resource_setup_notice(resource_readiness)
if workspace_page == "Project / Corpus":
    from versevad.ui.corpus import render_corpus_workspace

    render_corpus_workspace(_preprocessor(), resource_readiness)
if workspace_page == "Lexicon Explorer":
    from versevad.ui.explorer import render_lexicon_explorer

    render_lexicon_explorer(_preprocessor())


if workspace_page in {"Single Poem", "Other Text"}:
    is_other_text = workspace_page == "Other Text"
    st.session_state.setdefault("project_name", "")
    if not st.session_state.get("_workspace_name_blank_default_migrated"):
        if st.session_state["project_name"] == "Temporary private workspace":
            st.session_state["project_name"] = ""
        st.session_state["_workspace_name_blank_default_migrated"] = True
    st.session_state.setdefault("poem_title", "")
    st.session_state.setdefault("poem_text", "")
    st.session_state.setdefault("text_author", "")
    st.session_state.setdefault("text_year", "")
    st.session_state.setdefault("text_source_notes", "")
    st.session_state.setdefault("pronunciation_overrides", "")
    pending_pronunciation_overrides = st.session_state.pop(
        "_pending_pronunciation_overrides",
        None,
    )
    if pending_pronunciation_overrides is not None:
        st.session_state["pronunciation_overrides"] = str(
            pending_pronunciation_overrides
        )
    st.session_state.setdefault("workspace", None)

    with st.sidebar:
        st.markdown("### Local Session")
        st.caption(f"{workspace_page} · VerseVAD {__version__}")
        st.success("Private by design: analysis stays on this computer.")
        st.info(
            "Single-text results last only while the app is open. Download them "
            "before closing, or use Project / Corpus for persistent local work."
        )
        st.markdown("### Installation Check")
        if st.button("Run self-test", width="stretch", key="run_self_test"):
            _display_self_test()
        if "self_test_checks" in st.session_state:
            checks = st.session_state["self_test_checks"]
            passed = sum(check.passed for check in checks)
            st.caption(f"{passed}/{len(checks)} checks passed")
            with st.expander("Self-test details", expanded=passed != len(checks)):
                for check in checks:
                    st.markdown(
                        f"**{'PASS' if check.passed else 'FAIL'} — {check.check}**  \n"
                        f"{check.detail}"
                    )
        st.markdown("---")
        st.caption(
            "VerseVAD describes lexical evidence. It does not determine the emotion "
            "of a text, speaker, author, or reader."
        )

    render_workspace_header(
        "Other Text" if is_other_text else "Single Poem",
        (
            "Paste or import prose or another non-poetic text, choose the evidence "
            "to inspect, and receive the same auditable report structure."
            if is_other_text
            else "Paste or import one poem, choose the lexical and formal evidence "
            "to inspect, and receive a readable report with its full audit trail."
        ),
        kicker="Local literary text analysis",
        status="Session only",
    )

    with st.container(border=True):
        st.subheader("1. Add the Text" if is_other_text else "1. Add a Poem")
        uploaded = st.file_uploader(
            "Choose a UTF-8 plain-text file",
            type=["txt"],
            help="The browser reads this file locally into the app. VerseVAD does not upload it to a cloud service.",
            key="uploaded_poem",
        )
        if uploaded is not None:
            content = uploaded.getvalue()
            upload_signature = hashlib.sha256(content).hexdigest()
            if st.session_state.get("upload_signature") != upload_signature:
                try:
                    st.session_state["poem_text"] = decode_uploaded_text(uploaded.name, content)
                    if not st.session_state.get("poem_title", "").strip():
                        st.session_state["poem_title"] = Path(uploaded.name).stem
                    st.session_state["upload_signature"] = upload_signature
                    st.rerun()
                except TextImportError as error:
                    st.error(str(error))

        left, right = st.columns([1, 1])
        with left:
            st.text_input(
                "Workspace name",
                key="project_name",
                help=(
                    "Optional. Leave blank or add a temporary session label; "
                    "this does not create a persistent project."
                ),
            )
        with right:
            st.text_input(
                (
                    "Text title or working label"
                    if is_other_text
                    else "Poem title or working label"
                ),
                key="poem_title",
            )
        st.text_area(
            (
                "Paste the text exactly as you want it analyzed"
                if is_other_text
                else "Paste the poem exactly as you want it analyzed"
            ),
            key="poem_text",
            height=260,
            placeholder=(
                "Paste text here, preserving paragraph and line breaks…"
                if is_other_text
                else "Paste a poem here, preserving its line and stanza breaks…"
            ),
            help="VerseVAD keeps this original string unchanged and creates a separate processing representation.",
        )
        text = st.session_state.get("poem_text", "")
        line_count = len(text.splitlines()) if text else 0
        stanza_count = (
            len(
                [
                    part
                    for part in text.replace("\r\n", "\n").split("\n\n")
                    if part.strip()
                ]
            )
            if text
            else 0
        )
        st.caption(
            f"{len(text.split()):,} whitespace-separated words · "
            f"{line_count:,} physical lines · {stanza_count:,} text blocks. "
            "Analysis uses the shared linguistic tokenizer, not these live estimates."
        )
        with st.popover("Clear text"):
            st.warning(
                "This clears the current session text. Completed results remain "
                "visible but will be marked stale."
            )
            st.button(
                "Confirm clear text",
                disabled=not bool(text),
                key="confirm_clear_text",
                on_click=_clear_current_text,
            )
        with st.expander("Optional bibliographic metadata"):
            metadata_columns = st.columns([2, 1])
            with metadata_columns[0]:
                st.text_input("Author or creator", key="text_author")
            with metadata_columns[1]:
                st.text_input("Date or year", key="text_year")
            st.text_area(
                "Source or edition notes",
                key="text_source_notes",
                height=90,
            )

    with st.container(border=True):
        st.subheader("2. Choose Evidence")
        spec_by_id = {
            spec.lexicon_id: spec
            for spec in LEXICON_SPECS
            if spec.lexicon_id in resource_readiness.available_lexicon_ids
        }
        concreteness_status = resource_readiness.concreteness
        frequency_status = resource_readiness.frequency
        aoa_status = resource_readiness.aoa
        pronunciation_statuses = resource_readiness.pronunciation
        pronunciation_available = resource_readiness.pronunciation_available
        unavailable_modules = {
            "include_concreteness": not concreteness_status.available,
            "include_frequency": not frequency_status.available,
            "include_aoa": not aoa_status.available,
            "include_pronunciation": not pronunciation_available,
            "include_meter": not pronunciation_available,
            "include_phonology": not pronunciation_available,
            "include_inherited_form": not pronunciation_available,
        }
        for module_key in (
            "include_concreteness",
            "include_frequency",
            "include_aoa",
            "include_pronunciation",
            "include_meter",
            "include_phonology",
            "include_lexical_style",
            "include_poetry_id",
            "include_inherited_form",
        ):
            if unavailable_modules.get(module_key, False):
                st.session_state[module_key] = False
            else:
                st.session_state.setdefault(module_key, False)
        if "selected_lexicons" not in st.session_state:
            st.session_state["selected_lexicons"] = list(spec_by_id)
        else:
            selected_available_lexicons = [
                lexicon_id
                for lexicon_id in st.session_state["selected_lexicons"]
                if lexicon_id in spec_by_id
            ]
            if (
                selected_available_lexicons
                != st.session_state["selected_lexicons"]
            ):
                st.session_state["selected_lexicons"] = (
                    selected_available_lexicons
                )

        preset_choice, preset_action = st.columns([3, 1], vertical_alignment="bottom")
        with preset_choice:
            selected_preset = st.selectbox(
                "Module preset",
                options=list(MODULE_PRESETS),
                index=list(MODULE_PRESETS).index("Custom"),
                key="module_preset",
                help=(
                    "A preset changes module selections only. It never overwrites "
                    "advanced thresholds, filters, or pronunciation decisions."
                ),
            )
        with preset_action:
            apply_preset = st.button(
                "Apply preset",
                width="stretch",
                key="apply_module_preset",
            )
        st.caption(MODULE_PRESETS[selected_preset].description)
        if apply_preset:
            preset_state = preset_widget_state(
                selected_preset,
                available_lexicon_ids=tuple(spec_by_id),
            )
            if not preset_state:
                st.info("Custom keeps the current manual selections unchanged.")
            for key, value in preset_state.items():
                st.session_state[key] = (
                    False if unavailable_modules.get(key, False) else value
                )
            if preset_state:
                st.rerun()

        st.markdown("#### Core Analysis")
        st.caption(
            "Affective sources stay separate. Repeated words contribute according "
            "to each module's visible weighting and view."
        )
        selected_lexicons = st.multiselect(
            "Lexicons",
            options=list(spec_by_id),
            format_func=lambda lexicon_id: spec_by_id[lexicon_id].display_name,
            help="Each source is analyzed independently. VerseVAD never creates a default consensus score.",
            key="selected_lexicons",
        )
        if not spec_by_id:
            st.info(
                "No validated affective lexicon is installed. You can still run "
                "resource-free lexical-style analysis or any installed optional "
                "module."
            )
        if selected_lexicons:
            with st.expander("What each selected lexicon contributes"):
                for lexicon_id in selected_lexicons:
                    spec = spec_by_id[lexicon_id]
                    st.markdown(f"**{spec.display_name}:** {spec.short_description}")

        st.subheader("Additional Optional Models")
        st.caption(
            "Enable only the lexical-character, structural, PoetryID, sound, "
            "and inherited-form models needed for this analysis."
        )
        with _stateful_expander(
            "Choose Additional Optional Models",
            state_key="additional_optional_models",
        ):
            st.markdown("#### Lexical Character")
            include_concreteness = st.checkbox(
                "Concreteness profile (Brysbaert et al. ratings)",
                disabled=not concreteness_status.available,
                key="include_concreteness",
                help=(
                    "Measures matched normative lexical concreteness on the source "
                    "1-5 scale. The module is independent of the affective lexicons."
                ),
            )
            if concreteness_status.available:
                st.caption(
                    "Available locally. The source workbook is read in place, its "
                    "SHA-256 is recorded, and it is not added to source control."
                )
            else:
                st.info(concreteness_status.message)

            include_frequency = st.checkbox(
                "Frequency & rarity profile (SUBTLEX-US Zipf)",
                disabled=not frequency_status.available,
                key="include_frequency",
                help=(
                    "Describes corpus-relative word-form frequency using the "
                    "official local SUBTLEX-US Zipf workbook. No wordfreq fallback "
                    "is used."
                ),
            )
            if frequency_status.available:
                st.caption(
                    "Available locally. Zipf values come from the pinned official "
                    "SUBTLEX-US workbook, read in place with its SHA-256 recorded."
                )
            else:
                st.info(frequency_status.message)

            include_aoa = st.checkbox(
                "Age of Acquisition profile (Kuperman et al. ratings)",
                disabled=not aoa_status.available,
                key="include_aoa",
                help=(
                    "Optional retrospective normative lexical ratings in years. "
                    "This is not word difficulty, grade level, or a diagnostic "
                    "measure."
                ),
            )
            if aoa_status.available:
                st.caption(
                    "Available locally. VerseVAD reads the official erratum "
                    "supplement in place and records its SHA-256."
                )
            else:
                st.info(aoa_status.message)

            st.markdown("#### Structural and Lexical Measures")
            include_lexical_style = st.checkbox(
                "Lexical diversity, word length & structural word counts",
                key="include_lexical_style",
                help=(
                    "Reports normalized observed surface-form diversity, "
                    "alphabetic-character word lengths, and lexical-token counts "
                    "for each preserved physical line and stanza."
                ),
            )
            st.caption(
                "Optional and off by default. This module needs no external dataset "
                "and reuses the shared poetry-preserving processing record."
            )

            st.markdown("#### PoetryID")
            st.caption(
                "PoetryID requires completed VAD evidence and reuses it without "
                "rematching or recalculating the text."
            )
            available_poetry_id_sources = [
                lexicon_id
                for lexicon_id in selected_lexicons
                if lexicon_id in SUPPORTED_VAD_LEXICON_IDS
            ]
            if not available_poetry_id_sources:
                st.session_state["include_poetry_id"] = False
            include_poetry_id = st.checkbox(
                "PoetryID lexical-affective profile",
                disabled=not available_poetry_id_sources,
                key="include_poetry_id",
                help=(
                    "Classifies completed normalized VAD evidence against a "
                    "transparent 27-profile grid. It does not rerun VAD or declare "
                    "the poem's emotion."
                ),
            )
            if not available_poetry_id_sources:
                st.info(
                    "Select Warriner VAD, NRC VAD v1, or NRC VAD v2.1 to enable "
                    "PoetryID."
                )
            poetry_id_sources = st.multiselect(
                "PoetryID VAD sources",
                options=available_poetry_id_sources,
                default=available_poetry_id_sources,
                format_func=lambda lexicon_id: spec_by_id[lexicon_id].display_name,
                disabled=not include_poetry_id,
                key="poetry_id_sources",
                help=(
                    "Every source remains a separate result. PoetryID never creates "
                    "a consensus VAD score."
                ),
            )
            poetry_id_weightings = st.multiselect(
                "PoetryID weighting views",
                options=["token", "type"],
                default=["token", "type"],
                disabled=not include_poetry_id,
                key="poetry_id_weightings",
            )
            poetry_id_views = st.multiselect(
                "PoetryID analysis views",
                options=["all_matched", "stopwords_excluded"],
                default=["all_matched", "stopwords_excluded"],
                format_func=lambda value: (
                    "All matched tokens (including stopwords)"
                    if value == "all_matched"
                    else "Stopwords excluded"
                ),
                disabled=not include_poetry_id,
                key="poetry_id_views",
                help=(
                    "Both views are kept separate. All matched tokens includes "
                    "matched stopwords; unmatched vocabulary remains missing in "
                    "both views and is never assigned a neutral value."
                ),
            )
            available_character_dimensions = []
            if include_concreteness:
                available_character_dimensions.append("concreteness")
            if include_frequency:
                available_character_dimensions.append("frequency")
            if include_aoa:
                available_character_dimensions.append("age_of_acquisition")
            poetry_id_lexical_dimensions = st.multiselect(
                "Secondary PoetryID lexical character",
                options=available_character_dimensions,
                default=available_character_dimensions,
                format_func=lambda value: value.replace("_", " ").title(),
                disabled=not include_poetry_id,
                key="poetry_id_lexical_dimensions",
                help=(
                    "Uses completed module summaries only. These descriptors never "
                    "change the VAD archetype."
                ),
            )

            st.markdown("#### Sound and Form")
            if is_other_text:
                st.info(
                    "Pronunciation, meter, and rhyme remain available for close reading "
                    "of prose, but meter and rhyme should be treated as experimental "
                    "outside lineated poetry."
                )
            include_pronunciation = st.checkbox(
                "Pronunciation & prosody foundation (CMUdict)",
                disabled=not pronunciation_available,
                key="include_pronunciation",
                help=(
                    "Optional exact observed-form dictionary pronunciations, "
                    "syllable counts, and lexical stress. This Stage 5 module does "
                    "not classify meter, rhyme, or performed scansion."
                ),
            )
            if pronunciation_available:
                st.caption(
                    "Available locally. VerseVAD reads the pinned official CMUdict "
                    "files in place, records all three SHA-256 checksums, and retains "
                    "every pronunciation alternative."
                )
            else:
                for status in pronunciation_statuses:
                    if not status.available:
                        st.info(status.message)

            include_meter = st.checkbox(
                "Meter & rhythmic regularity",
                disabled=not pronunciation_available,
                key="include_meter",
                help=(
                    "Stage 6 compares retained lexical-stress evidence against "
                    "iambic, trochaic, anapestic, dactylic, and amphibrachic "
                    "templates from monometer through octameter."
                ),
            )
            if pronunciation_available:
                st.caption(
                    "Optional and off by default. Meter analysis automatically runs "
                    "the pronunciation foundation, retains dictionary alternatives, "
                    "and reports nearest candidates rather than definitive scansion."
                )

            include_phonology = st.checkbox(
                "Rhyme & phonological patterns",
                disabled=not pronunciation_available,
                key="include_phonology",
                help=(
                    "Stage 7 derives end-rhyme groups and schemes, perfect, identical, "
                    "masculine, feminine, multisyllabic, graded slant, eye, and "
                    "internal-rhyme evidence plus alliteration, assonance, consonance, "
                    "refrains, and coverage."
                ),
            )
            if pronunciation_available:
                st.caption(
                    "Optional and off by default. Stage 7 automatically runs the "
                    "pronunciation foundation. Dictionary, spelling, and repeated-text "
                    "evidence remain separately labeled."
                )

            include_inherited_form = st.checkbox(
                "Inherited Form Analysis (comprehensive profile registry)",
                disabled=not pronunciation_available,
                key="include_inherited_form",
                help=(
                    "Ranks source-backed inherited-form profiles using line, "
                    "stanza, meter, graded rhyme, refrain, syllable, end-word, "
                    "and other observable evidence. Profiles with defining "
                    "contextual requirements remain manually inspectable but "
                    "cannot become automatic suggestions."
                ),
            )
            if pronunciation_available:
                st.caption(
                    "Optional and off by default. This automatically reuses the "
                    "pronunciation, performance-aware meter, and graded rhyme "
                    "modules. Its candidate tooltip explains the traditional "
                    "definition and the poem's agreements and departures."
                )
            _render_bottom_collapse_button(
                "Additional Optional Models",
                state_key="additional_optional_models",
            )

    with st.container(border=True):
        st.subheader("3. Analysis Configuration and Methodology")
        st.caption(
            "Fine-tune thresholds, matching policies, and evidence handling. "
            "Defaults are suitable for an initial analysis."
        )
        with _stateful_expander(
            "Show Configuration Controls",
            state_key="analysis_configuration",
        ):
            policy_labels = {
                "Prefer the longest phrase (recommended)": PhrasePolicy.PHRASE_PREFERRED,
                "Use unigrams only": PhrasePolicy.UNIGRAM_ONLY,
                "Count phrases and components (exploratory)": PhrasePolicy.PHRASE_AND_COMPONENT,
            }
            policy_label = st.selectbox(
                "Phrase policy",
                options=list(policy_labels),
                index=0,
                help="Warriner and NRC VAD v2.1 activate exact multiword expressions.",
                key="phrase_policy_label",
            )
            minimum_matches = st.number_input(
                "Minimum included matches before a VAD result is considered non-sparse",
                min_value=1,
                max_value=100,
                value=3,
                step=1,
                key="minimum_matches",
            )
            st.caption(
                "This threshold marks a result as sparse; it does not invent values or remove the audit trail."
            )
            st.markdown("**Concreteness settings**")
            concreteness_columns = st.columns(2)
            highly_abstract_max = concreteness_columns[0].number_input(
                "Highly abstract band: rating at or below",
                min_value=1.0,
                max_value=4.9,
                value=2.0,
                step=0.1,
                key="concreteness_abstract_max",
                disabled=not include_concreteness,
            )
            highly_concrete_min = concreteness_columns[1].number_input(
                "Highly concrete band: rating at or above",
                min_value=1.1,
                max_value=5.0,
                value=4.0,
                step=0.1,
                key="concreteness_concrete_min",
                disabled=not include_concreteness,
            )
            concreteness_policy_columns = st.columns(2)
            exclude_concreteness_proper_nouns = concreteness_policy_columns[
                0
            ].checkbox(
                "Exclude model-tagged proper nouns",
                value=True,
                key="concreteness_exclude_proper",
                disabled=not include_concreteness,
            )
            activate_concreteness_phrases = concreteness_policy_columns[
                1
            ].checkbox(
                "Activate exact two-word source expressions",
                value=True,
                key="concreteness_phrases",
                disabled=not include_concreteness,
            )
            concreteness_warning_threshold = st.number_input(
                "Concreteness rated-token coverage caution threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                key="concreteness_coverage_warning",
                disabled=not include_concreteness,
            )
            st.caption(
                "The extreme bands and coverage caution are configurable "
                "VerseVAD orientation aids, not categories or validity cutoffs "
                "defined by the source paper."
            )
            st.markdown("**Frequency & rarity settings**")
            frequency_threshold_columns = st.columns(4)
            rare_below = frequency_threshold_columns[0].number_input(
                "Rare: Zipf below",
                min_value=1.0,
                max_value=7.0,
                value=3.0,
                step=0.1,
                key="frequency_rare_below",
                disabled=not include_frequency,
            )
            uncommon_below = frequency_threshold_columns[1].number_input(
                "Uncommon: below",
                min_value=1.1,
                max_value=7.2,
                value=4.0,
                step=0.1,
                key="frequency_uncommon_below",
                disabled=not include_frequency,
            )
            moderately_common_below = frequency_threshold_columns[
                2
            ].number_input(
                "Moderately common: below",
                min_value=1.2,
                max_value=7.4,
                value=5.0,
                step=0.1,
                key="frequency_moderate_below",
                disabled=not include_frequency,
            )
            very_common_min = frequency_threshold_columns[3].number_input(
                "Very common: at or above",
                min_value=1.3,
                max_value=8.0,
                value=6.0,
                step=0.1,
                key="frequency_very_common_min",
                disabled=not include_frequency,
            )
            frequency_policy_columns = st.columns(3)
            exclude_frequency_proper_nouns = frequency_policy_columns[
                0
            ].checkbox(
                "Exclude frequency proper nouns",
                value=True,
                key="frequency_exclude_proper",
                disabled=not include_frequency,
            )
            frequency_content_words_only = frequency_policy_columns[
                1
            ].checkbox(
                "Content words only",
                value=False,
                key="frequency_content_words_only",
                disabled=not include_frequency,
                help=(
                    "Optional and off by default. Limits eligible tokens to "
                    "model-tagged NOUN, VERB, ADJ, and ADV; excludes determiners, "
                    "prepositions, conjunctions, pronouns, auxiliaries, and "
                    "punctuation."
                ),
            )
            enable_frequency_lemma_fallback = frequency_policy_columns[
                2
            ].checkbox(
                "Allow explicit lemma fallback",
                value=True,
                key="frequency_lemma_fallback",
                disabled=not include_frequency,
            )
            frequency_warning_threshold = st.number_input(
                "Frequency matched-token coverage caution threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                key="frequency_coverage_warning",
                disabled=not include_frequency,
            )
            st.caption(
                "Median Zipf is primary. Each one-point increase represents "
                "roughly ten times greater corpus frequency. The configurable "
                "bands are orientation aids rather than universal categories."
            )
            st.markdown("**Age of Acquisition settings**")
            aoa_threshold_columns = st.columns(2)
            early_acquired_max = aoa_threshold_columns[0].number_input(
                "Early-acquired band: source mean age at or below",
                min_value=0.0,
                max_value=24.9,
                value=5.0,
                step=0.5,
                key="aoa_early_max",
                disabled=not include_aoa,
            )
            later_acquired_min = aoa_threshold_columns[1].number_input(
                "Later-acquired band: source mean age at or above",
                min_value=0.1,
                max_value=25.0,
                value=12.0,
                step=0.5,
                key="aoa_later_min",
                disabled=not include_aoa,
            )
            aoa_policy_columns = st.columns(3)
            exclude_aoa_proper_nouns = aoa_policy_columns[0].checkbox(
                "Exclude AoA proper nouns",
                value=True,
                key="aoa_exclude_proper",
                disabled=not include_aoa,
            )
            aoa_content_words_only = aoa_policy_columns[1].checkbox(
                "AoA content words only",
                value=False,
                key="aoa_content_words_only",
                disabled=not include_aoa,
                help=(
                    "Optional and off by default. Uses the poem occurrence's "
                    "model tag and retains only NOUN, VERB, ADJ, and ADV. The "
                    "paper's source-sampling rule does not make this contextual "
                    "filter redundant."
                ),
            )
            enable_aoa_lemma_fallback = aoa_policy_columns[2].checkbox(
                "Allow AoA lemma fallback",
                value=True,
                key="aoa_lemma_fallback",
                disabled=not include_aoa,
            )
            aoa_warning_threshold = st.number_input(
                "AoA matched-token coverage caution threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                key="aoa_coverage_warning",
                disabled=not include_aoa,
            )
            st.caption(
                "The early/later bands are configurable VerseVAD orientation "
                "aids, not source-paper categories. Age-of-acquisition results "
                "are retrospective normative lexical evidence and are not "
                "diagnostic of cognitive impairment or decline."
            )
            st.markdown("**Lexical diversity and word-count settings**")
            lexical_style_columns = st.columns(4)
            lexical_style_mattr_window = lexical_style_columns[0].number_input(
                "MATTR window size",
                min_value=2,
                max_value=1000,
                value=50,
                step=1,
                key="lexical_style_mattr_window",
                disabled=not include_lexical_style,
            )
            lexical_style_hdd_sample = lexical_style_columns[1].number_input(
                "HD-D sample size",
                min_value=2,
                max_value=1000,
                value=42,
                step=1,
                key="lexical_style_hdd_sample",
                disabled=not include_lexical_style,
            )
            lexical_style_mtld_threshold = lexical_style_columns[2].number_input(
                "MTLD TTR threshold",
                min_value=0.01,
                max_value=0.99,
                value=0.72,
                step=0.01,
                key="lexical_style_mtld_threshold",
                disabled=not include_lexical_style,
            )
            lexical_style_short_warning = lexical_style_columns[3].number_input(
                "Short-text caution below",
                min_value=2,
                max_value=1000,
                value=50,
                step=1,
                key="lexical_style_short_warning",
                disabled=not include_lexical_style,
            )
            st.caption(
                "MATTR and HD-D remain missing when the poem is shorter than "
                "their configured denominators. Compare texts only when these "
                "parameters and the lexical-token policy match."
            )
            st.markdown("**PoetryID settings**")
            poetry_id_custom_thresholds = st.checkbox(
                "Use custom fixed VAD thresholds",
                value=False,
                disabled=not include_poetry_id,
                key="poetry_id_custom_thresholds",
                help=(
                    "Off uses the documented 0.40/0.60 fixed boundaries. "
                    "Corpus-relative tertiles and z scores are not implemented "
                    "until a defensible reference-corpus rule is specified."
                ),
            )
            poetry_threshold_columns = st.columns(3)
            poetry_id_threshold_values = {}
            for column, dimension in zip(
                poetry_threshold_columns,
                ("valence", "arousal", "dominance"),
                strict=True,
            ):
                with column:
                    st.caption(dimension.title())
                    low_max = st.number_input(
                        "Low maximum",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.4,
                        step=0.01,
                        key=f"poetry_id_{dimension}_low",
                        disabled=(
                            not include_poetry_id
                            or not poetry_id_custom_thresholds
                        ),
                    )
                    high_min = st.number_input(
                        "High minimum",
                        min_value=0.01,
                        max_value=1.0,
                        value=0.6,
                        step=0.01,
                        key=f"poetry_id_{dimension}_high",
                        disabled=(
                            not include_poetry_id
                            or not poetry_id_custom_thresholds
                        ),
                    )
                    poetry_id_threshold_values[dimension] = (
                        float(low_max),
                        float(high_min),
                    )
            poetry_id_evidence_columns = st.columns(4)
            poetry_id_min_tokens = poetry_id_evidence_columns[0].number_input(
                "Minimum matched tokens",
                min_value=1,
                max_value=1000,
                value=5,
                key="poetry_id_min_tokens",
                disabled=not include_poetry_id,
            )
            poetry_id_min_types = poetry_id_evidence_columns[1].number_input(
                "Minimum matched types",
                min_value=1,
                max_value=1000,
                value=3,
                key="poetry_id_min_types",
                disabled=not include_poetry_id,
            )
            poetry_id_min_token_coverage = poetry_id_evidence_columns[
                2
            ].number_input(
                "Minimum token coverage",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.05,
                key="poetry_id_min_token_coverage",
                disabled=not include_poetry_id,
            )
            poetry_id_min_type_coverage = poetry_id_evidence_columns[
                3
            ].number_input(
                "Minimum type coverage",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.05,
                key="poetry_id_min_type_coverage",
                disabled=not include_poetry_id,
            )
            st.caption(
                "Categorical boundaries, all 27 centroid distances, relative "
                "affinities, boundary sensitivity, coverage, and the exact "
                "configuration are retained. Affinities are not probabilities."
            )
            st.markdown("**Pronunciation & prosody-foundation settings**")
            pronunciation_overrides_text = st.text_area(
                "Poem-specific pronunciation overrides",
                key="pronunciation_overrides",
                disabled=not (
                    include_pronunciation or include_meter or include_phonology
                ),
                height=120,
                placeholder=(
                    "permit = P ER0 M IH1 T | verb reading in this line\n"
                    "fire = F AY1 ER0 | two-syllable reading"
                ),
                help=(
                    "One observed word form per line: word = uppercase ARPAbet "
                    "phones | brief scholarly note. Overrides apply only to this "
                    "analysis and remain distinct from dictionary candidates."
                ),
            )
            pronunciation_columns = st.columns(3)
            pronunciation_warning_threshold = pronunciation_columns[
                0
            ].number_input(
                "Pronunciation coverage caution threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.8,
                step=0.05,
                key="pronunciation_coverage_warning",
                disabled=not (
                    include_pronunciation or include_meter or include_phonology
                ),
            )
            pronunciation_minimum_complete_lines = pronunciation_columns[
                1
            ].number_input(
                "Minimum complete lines",
                min_value=1,
                max_value=100,
                value=2,
                step=1,
                key="pronunciation_minimum_complete_lines",
                disabled=not (
                    include_pronunciation or include_meter or include_phonology
                ),
            )
            pronunciation_minimum_resolved_tokens = pronunciation_columns[
                2
            ].number_input(
                "Minimum resolved tokens",
                min_value=1,
                max_value=1000,
                value=3,
                step=1,
                key="pronunciation_minimum_resolved_tokens",
                disabled=not (
                    include_pronunciation or include_meter or include_phonology
                ),
            )
            st.caption(
                "Analysis uses exact observed forms only: no lemma or "
                "possessive-base fallback. Out-of-dictionary G2P candidates "
                "are review-only and remain unmatched unless explicitly "
                "approved or edited into a session override. Multiple "
                "dictionary candidates resolve automatically only when "
                "syllable count and lexical stress agree."
            )
            st.markdown("**Meter and rhythmic-regularity settings**")
            meter_mode_labels = {
                "Candidate meter only (validated default)": (
                    MeterAnalysisMode.CANDIDATE
                ),
                "Performance-aware realization": (
                    MeterAnalysisMode.PERFORMANCE_AWARE
                ),
                "Compare candidate and performance-aware readings": (
                    MeterAnalysisMode.COMPARE_BOTH
                ),
            }
            meter_style_labels = {
                "General English Verse": MeterStyleProfile.GENERAL,
                "Traditional Accentual-Syllabic Verse": (
                    MeterStyleProfile.TRADITIONAL
                ),
                "Romantic / Victorian Verse": (
                    MeterStyleProfile.ROMANTIC_VICTORIAN
                ),
                "Modernist Verse": MeterStyleProfile.MODERNIST,
                "Contemporary Formal Verse": (
                    MeterStyleProfile.CONTEMPORARY_FORMAL
                ),
                "Free Verse / Cadential": (
                    MeterStyleProfile.FREE_VERSE_CADENTIAL
                ),
                "Custom visible weights": MeterStyleProfile.CUSTOM,
            }
            meter_depth_labels = {
                "Summary": MeterInterpretationDepth.SUMMARY,
                "Standard": MeterInterpretationDepth.STANDARD,
                "Detailed": MeterInterpretationDepth.DETAILED,
            }
            meter_interpretation_columns = st.columns(3)
            meter_analysis_mode_label = meter_interpretation_columns[
                0
            ].selectbox(
                "Meter analysis layer",
                options=list(meter_mode_labels),
                key="meter_analysis_mode",
                disabled=not include_meter,
                help=(
                    "Candidate meter preserves the validated fixed-template "
                    "method. Performance-aware mode adds an inspectable, "
                    "profile-dependent realization without changing lexical stress."
                ),
            )
            meter_analysis_mode = meter_mode_labels[meter_analysis_mode_label]
            meter_style_profile_label = meter_interpretation_columns[
                1
            ].selectbox(
                "Declared interpretation profile",
                options=list(meter_style_labels),
                key="meter_style_profile",
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                help=(
                    "A broad reading profile changes only explicit realization "
                    "weights. VerseVAD never infers a period, movement, or author."
                ),
            )
            meter_interpretation_depth_label = meter_interpretation_columns[
                2
            ].selectbox(
                "Interpretation detail",
                options=list(meter_depth_labels),
                index=1,
                key="meter_interpretation_depth",
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
            )
            meter_columns = st.columns(4)
            meter_line_match_threshold = meter_columns[0].number_input(
                "Meter line-fit threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.75,
                step=0.05,
                key="meter_line_match_threshold",
                disabled=not include_meter,
            )
            meter_irregular_threshold = meter_columns[1].number_input(
                "Poem candidate-fit threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.65,
                step=0.05,
                key="meter_irregular_threshold",
                disabled=not include_meter,
            )
            meter_ambiguity_margin = meter_columns[2].number_input(
                "Candidate margin threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.03,
                step=0.01,
                key="meter_ambiguity_margin",
                disabled=not include_meter,
            )
            meter_maximum_variants = meter_columns[3].number_input(
                "Maximum stress paths per line",
                min_value=1,
                max_value=4096,
                value=256,
                step=1,
                key="meter_maximum_variants",
                disabled=not include_meter,
            )
            meter_realization_columns = st.columns(3)
            meter_performance_candidate_limit = meter_realization_columns[
                0
            ].number_input(
                "Realization candidates per line",
                min_value=2,
                max_value=40,
                value=8,
                step=1,
                key="meter_performance_candidate_limit",
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                help="Bounds contextual reranking while retaining fixed-layer evidence.",
            )
            meter_realized_alternatives = meter_realization_columns[
                1
            ].number_input(
                "Retained realized alternatives",
                min_value=1,
                max_value=8,
                value=2,
                step=1,
                key="meter_realized_alternatives",
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
            )
            meter_allow_visible_elision = meter_realization_columns[
                2
            ].checkbox(
                "Recognize visibly marked contractions",
                value=False,
                key="meter_allow_visible_elision",
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                help=(
                    "Off by default. Only preserved spellings such as o'er may "
                    "be labeled; unmarked syllables are never silently removed."
                ),
            )
            meter_scholar_revisions_text = st.text_area(
                "Scholar scansion revisions",
                value="",
                key="meter_scholar_revisions",
                height=100,
                disabled=(
                    not include_meter
                    or meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                placeholder=(
                    "line 2 = iambic pentameter | "
                    "x / x / x / x / x / | reason for the revised reading"
                ),
                help=(
                    "Optional. One line per revision. Automatic and revised "
                    "readings remain separate in the interface and export."
                ),
            )
            st.caption(
                "The fixed grid remains 40 candidates: five recurring stress "
                "patterns by one through eight feet. Optional realization "
                "separately reports promotion, demotion, phrasing, substitutions, "
                "alternatives, and confidence."
            )
            st.markdown("**Rhyme and phonological-pattern settings**")
            phonological_columns = st.columns(4)
            phonological_slant_threshold = phonological_columns[0].number_input(
                "Slant-rhyme threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.68,
                step=0.01,
                key="phonological_slant_threshold",
                disabled=not include_phonology,
            )
            phonological_sound_repetitions = phonological_columns[1].number_input(
                "Minimum repeated sounds",
                min_value=2,
                max_value=20,
                value=2,
                step=1,
                key="phonological_sound_repetitions",
                disabled=not include_phonology,
            )
            phonological_coverage_warning = phonological_columns[2].number_input(
                "Ending-coverage caution threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.70,
                step=0.05,
                key="phonological_coverage_warning",
                disabled=not include_phonology,
            )
            phonological_maximum_pairs = phonological_columns[3].number_input(
                "Maximum ending-pair comparisons",
                min_value=1,
                max_value=100000,
                value=10000,
                step=100,
                key="phonological_maximum_pairs",
                disabled=not include_phonology,
            )
            st.caption(
                "The slant score combines stressed vowel, final consonants, "
                "rhyme-part edit similarity, stress alignment, and syllable "
                "similarity. It is a configurable heuristic, not a probability."
            )
            st.markdown("**Stopword reporting**")
            reporting_columns = st.columns(2)
            show_all_matched = reporting_columns[0].checkbox(
                "Show all-token results",
                value=True,
                key="show_all_matched_results",
            )
            show_stopword_excluded = reporting_columns[1].checkbox(
                "Show stopword-excluded results",
                value=True,
                key="show_stopword_excluded_results",
            )
            st.caption(
                "Stopword exclusion removes common grammatical words from the secondary "
                "analysis only. The complete analysis and token audit remain available."
            )
            with st.expander("Stopword settings"):
                stopword_settings = render_stopword_settings("one_poem")
            _render_bottom_collapse_button(
                "Analysis Configuration and Methodology",
                state_key="analysis_configuration",
            )

        analyze_clicked = st.button(
            "Analyze Text" if is_other_text else "Analyze Poem",
            type="primary",
            width="stretch",
            key="analyze_text",
        )

    concreteness_configuration_error = ""
    try:
        concreteness_configuration = ConcretenessConfiguration(
            highly_abstract_max=float(highly_abstract_max),
            highly_concrete_min=float(highly_concrete_min),
            exclude_proper_nouns=exclude_concreteness_proper_nouns,
            activate_multiword_expressions=activate_concreteness_phrases,
            minimum_rated_tokens=int(minimum_matches),
            low_coverage_warning_threshold=float(
                concreteness_warning_threshold
            ),
        )
    except ValueError as error:
        concreteness_configuration_error = str(error)
        concreteness_configuration = ConcretenessConfiguration()
        if include_concreteness:
            st.warning(concreteness_configuration_error)

    frequency_configuration_error = ""
    try:
        frequency_configuration = FrequencyConfiguration(
            rare_below=float(rare_below),
            uncommon_below=float(uncommon_below),
            moderately_common_below=float(moderately_common_below),
            very_common_min=float(very_common_min),
            exclude_proper_nouns=exclude_frequency_proper_nouns,
            content_words_only=frequency_content_words_only,
            enable_lemma_fallback=enable_frequency_lemma_fallback,
            minimum_matched_tokens=int(minimum_matches),
            low_coverage_warning_threshold=float(frequency_warning_threshold),
        )
    except ValueError as error:
        frequency_configuration_error = str(error)
        frequency_configuration = FrequencyConfiguration()
        if include_frequency:
            st.warning(frequency_configuration_error)

    aoa_configuration_error = ""
    try:
        aoa_configuration = AoAConfiguration(
            early_acquired_max=float(early_acquired_max),
            later_acquired_min=float(later_acquired_min),
            exclude_proper_nouns=exclude_aoa_proper_nouns,
            content_words_only=aoa_content_words_only,
            enable_lemma_fallback=enable_aoa_lemma_fallback,
            minimum_matched_tokens=int(minimum_matches),
            low_coverage_warning_threshold=float(aoa_warning_threshold),
        )
    except ValueError as error:
        aoa_configuration_error = str(error)
        aoa_configuration = AoAConfiguration()
        if include_aoa:
            st.warning(aoa_configuration_error)

    lexical_style_configuration_error = ""
    try:
        lexical_style_configuration = LexicalStyleConfiguration(
            mattr_window_size=int(lexical_style_mattr_window),
            hdd_sample_size=int(lexical_style_hdd_sample),
            mtld_threshold=float(lexical_style_mtld_threshold),
            short_text_warning_threshold=int(lexical_style_short_warning),
        )
    except ValueError as error:
        lexical_style_configuration_error = str(error)
        lexical_style_configuration = LexicalStyleConfiguration()
        if include_lexical_style:
            st.warning(lexical_style_configuration_error)

    poetry_id_configuration_error = ""
    try:
        if include_poetry_id and not poetry_id_sources:
            raise ValueError("Select at least one VAD source for PoetryID.")
        threshold_profile = PoetryIDConfiguration().threshold_profile
        if poetry_id_custom_thresholds:
            threshold_profile = ThresholdProfile(
                profile_id="custom_fixed_ui",
                name="Custom Fixed Thresholds",
                method="fixed",
                dimensions={
                    dimension: ThresholdBand(low_max, high_min)
                    for dimension, (
                        low_max,
                        high_min,
                    ) in poetry_id_threshold_values.items()
                },
                configuration_version="poetry-id-custom-fixed-v1",
                built_in=False,
            )
        poetry_id_configuration = PoetryIDConfiguration(
            threshold_profile=threshold_profile,
            weighting_modes=tuple(poetry_id_weightings),
            analysis_views=tuple(poetry_id_views),
            vad_lexicon_ids=tuple(poetry_id_sources),
            requested_lexical_dimensions=tuple(
                poetry_id_lexical_dimensions
            ),
            minimum_matched_tokens=int(poetry_id_min_tokens),
            minimum_matched_types=int(poetry_id_min_types),
            minimum_token_coverage=float(
                poetry_id_min_token_coverage
            ),
            minimum_type_coverage=float(poetry_id_min_type_coverage),
        )
    except ValueError as error:
        poetry_id_configuration_error = str(error)
        poetry_id_configuration = PoetryIDConfiguration()
        if include_poetry_id:
            st.warning(poetry_id_configuration_error)

    inherited_form_configuration = InheritedFormConfiguration()

    pronunciation_configuration_error = ""
    try:
        pronunciation_configuration = PronunciationConfiguration(
            overrides=parse_pronunciation_overrides(
                pronunciation_overrides_text
            ),
            low_coverage_warning_threshold=float(
                pronunciation_warning_threshold
            ),
            minimum_complete_lines=int(
                pronunciation_minimum_complete_lines
            ),
            minimum_resolved_tokens=int(
                pronunciation_minimum_resolved_tokens
            ),
        )
    except ValueError as error:
        pronunciation_configuration_error = str(error)
        pronunciation_configuration = PronunciationConfiguration()
        if (
            include_pronunciation
            or include_meter
            or include_phonology
            or include_inherited_form
        ):
            st.warning(pronunciation_configuration_error)

    meter_configuration_error = ""
    try:
        meter_configuration = MeterConfiguration(
            line_match_threshold=float(meter_line_match_threshold),
            irregular_fit_threshold=float(meter_irregular_threshold),
            ambiguity_margin_threshold=float(meter_ambiguity_margin),
            maximum_line_variants=int(meter_maximum_variants),
            analysis_mode=meter_analysis_mode,
            style_profile=meter_style_labels[meter_style_profile_label],
            interpretation_depth=meter_depth_labels[
                meter_interpretation_depth_label
            ],
            performance_candidate_limit=int(
                meter_performance_candidate_limit
            ),
            retained_realized_alternatives=int(
                meter_realized_alternatives
            ),
            allow_visible_poetic_elision=meter_allow_visible_elision,
            scholar_revisions=(
                ()
                if meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                else parse_meter_scholar_revisions(
                    meter_scholar_revisions_text
                )
            ),
        )
    except ValueError as error:
        meter_configuration_error = str(error)
        meter_configuration = MeterConfiguration()
        if include_meter or include_inherited_form:
            st.warning(meter_configuration_error)

    phonological_configuration_error = ""
    try:
        phonological_configuration = PhonologicalConfiguration(
            slant_rhyme_threshold=float(phonological_slant_threshold),
            minimum_sound_repetitions=int(phonological_sound_repetitions),
            low_ending_coverage_warning_threshold=float(
                phonological_coverage_warning
            ),
            maximum_pair_evaluations=int(phonological_maximum_pairs),
        )
    except ValueError as error:
        phonological_configuration_error = str(error)
        phonological_configuration = PhonologicalConfiguration()
        if include_phonology or include_inherited_form:
            st.warning(phonological_configuration_error)

    automatic_pronunciation_update = bool(
        st.session_state.pop("_apply_pronunciation_resolutions", False)
    )
    analyze_clicked = analyze_clicked or automatic_pronunciation_update

    if analyze_clicked:
        try:
            if concreteness_configuration_error:
                raise ValueError(concreteness_configuration_error)
            if frequency_configuration_error:
                raise ValueError(frequency_configuration_error)
            if aoa_configuration_error:
                raise ValueError(aoa_configuration_error)
            if lexical_style_configuration_error:
                raise ValueError(lexical_style_configuration_error)
            if poetry_id_configuration_error:
                raise ValueError(poetry_id_configuration_error)
            if pronunciation_configuration_error:
                raise ValueError(pronunciation_configuration_error)
            if meter_configuration_error:
                raise ValueError(meter_configuration_error)
            if phonological_configuration_error:
                raise ValueError(phonological_configuration_error)
            request = AnalysisRequest(
                project_name=st.session_state["project_name"],
                title=st.session_state["poem_title"],
                original_text=st.session_state["poem_text"],
                lexicon_ids=tuple(selected_lexicons),
                phrase_policy=policy_labels[policy_label],
                minimum_match_requirement=int(minimum_matches),
                stopword_mode=stopword_settings.mode,
                protected_stopwords=stopword_settings.protected_words,
                custom_stopword_additions=stopword_settings.custom_additions,
                custom_stopword_removals=stopword_settings.custom_removals,
                include_concreteness=include_concreteness,
                concreteness_configuration=concreteness_configuration,
                include_frequency=include_frequency,
                frequency_configuration=frequency_configuration,
                include_aoa=include_aoa,
                aoa_configuration=aoa_configuration,
                include_lexical_style=include_lexical_style,
                lexical_style_configuration=lexical_style_configuration,
                include_poetry_id=include_poetry_id,
                poetry_id_configuration=poetry_id_configuration,
                include_inherited_form=include_inherited_form,
                inherited_form_configuration=(
                    inherited_form_configuration
                ),
                include_pronunciation=include_pronunciation,
                pronunciation_configuration=pronunciation_configuration,
                include_meter=include_meter,
                meter_configuration=meter_configuration,
                include_phonology=include_phonology,
                phonological_configuration=phonological_configuration,
                analysis_cache_enabled=st.session_state.get(
                    "analysis_cache_enabled",
                    True,
                ),
                performance_diagnostics=st.session_state.get(
                    "performance_diagnostics_enabled",
                    True,
                ),
            )
            with st.status(
                (
                    "Updating pronunciation and dependent evidence locally…"
                    if automatic_pronunciation_update
                    else "Analyzing locally…"
                ),
                expanded=True,
            ) as analysis_status:
                st.write("Preparing one shared linguistic representation.")
                st.write(
                    "Calculating offline VADER polarity and transparent readability "
                    "formula evidence."
                )
                if selected_lexicons:
                    st.write("Analyzing selected affective lexicons independently.")
                if (
                    include_pronunciation
                    or include_meter
                    or include_phonology
                    or include_inherited_form
                ):
                    st.write(
                        "Analyzing pronunciation and selected sound/form evidence."
                    )
                if include_poetry_id:
                    st.write("Generating PoetryID from the completed VAD result.")
                if include_inherited_form:
                    st.write(
                        "Ranking the inherited-form registry from completed "
                        "sound and structural evidence."
                    )
                st.session_state["workspace"] = run_workspace_analysis(
                    request, preprocessor=_preprocessor()
                )
                analysis_status.update(
                    label="Analysis complete",
                    state="complete",
                    expanded=False,
                )
            if automatic_pronunciation_update:
                applied_count = st.session_state.pop(
                    "_pronunciation_resolution_count",
                    0,
                )
                st.success(
                    f"{applied_count} pronunciation choice(s) applied; "
                    "readability, pronunciation, meter, sound, and inherited-form "
                    "evidence are updated."
                )
            else:
                st.success(
                    "Analysis complete. Start with Overview; use Evidence & "
                    "Diagnostics when you want to inspect why."
                )
        except (TextImportError, WorkspaceAnalysisError, ValueError) as error:
            st.error(str(error))
        except Exception as error:  # pragma: no cover - defensive UI boundary
            st.error(
                "VerseVAD could not complete this analysis. No source lexicon or original "
                "file was changed. Copy the technical detail below if you report the problem."
            )
            st.code(f"{type(error).__name__}: {error}")

    workspace = st.session_state.get("workspace")
    if workspace is None:
        render_empty_state(
            "No analysis yet",
            (
                "Your text and module choices are ready when you are. VerseVAD "
                "will keep the original text unchanged and build one auditable "
                "processing representation."
            ),
            (
                "Optionally choose a preset or modules, then select Analyze Text."
                if is_other_text
                else "Optionally choose a preset or modules, then select Analyze Poem."
            ),
        )
        st.stop()

    if (
        st.session_state["poem_text"] != workspace.request.original_text
        or tuple(selected_lexicons) != workspace.request.lexicon_ids
        or include_concreteness != workspace.request.include_concreteness
        or include_frequency != workspace.request.include_frequency
        or include_aoa != workspace.request.include_aoa
        or include_pronunciation != workspace.request.include_pronunciation
        or include_meter != workspace.request.include_meter
        or include_phonology != workspace.request.include_phonology
        or include_lexical_style != workspace.request.include_lexical_style
        or include_poetry_id != workspace.request.include_poetry_id
        or include_inherited_form
        != workspace.request.include_inherited_form
        or (
            include_concreteness
            and concreteness_configuration
            != workspace.request.concreteness_configuration
        )
        or (
            include_frequency
            and frequency_configuration
            != workspace.request.frequency_configuration
        )
        or (
            include_aoa
            and aoa_configuration != workspace.request.aoa_configuration
        )
        or (
            include_lexical_style
            and lexical_style_configuration
            != workspace.request.lexical_style_configuration
        )
        or (
            include_poetry_id
            and poetry_id_configuration
            != workspace.request.poetry_id_configuration
        )
        or (
            (
                include_pronunciation
                or include_meter
                or include_phonology
                or include_inherited_form
            )
            and pronunciation_configuration
            != workspace.request.pronunciation_configuration
        )
        or (
            (include_meter or include_inherited_form)
            and meter_configuration != workspace.request.meter_configuration
        )
        or (
            (include_phonology or include_inherited_form)
            and phonological_configuration
            != workspace.request.phonological_configuration
        )
    ):
        st.warning(
            "The text, lexicon selection, or optional-module settings have "
            "changed since this result was calculated. "
            f"Click {'Analyze Text' if is_other_text else 'Analyze Poem'} again "
            "before using the results."
        )

    st.divider()
    render_section_intro(
        workspace.document.title,
        "Current completed result. Use the report-family navigation below to move "
        "between overview, detailed evidence, diagnostics, and exports.",
    )
    st.caption(
        f"Text version {workspace.document.text_version_id} · "
        f"Phrase policy: {workspace.request.phrase_policy.value.replace('_', ' ')}"
    )
    bibliographic_details = [
        value
        for value in (
            st.session_state.get("text_author", "").strip(),
            st.session_state.get("text_year", "").strip(),
            st.session_state.get("text_source_notes", "").strip(),
        )
        if value
    ]
    if bibliographic_details:
        st.caption("Bibliographic notes · " + " · ".join(bibliographic_details))

    report_sections = (
        "Overview",
        "Affective Evidence",
        "Lexical Character",
        "Sound & Form",
        "Structure",
        "Evidence & Diagnostics",
        "Export & Help",
    )
    report_state_key = (
        "other_text_report_section"
        if is_other_text
        else "single_poem_report_section"
    )
    _, report_containers = render_stateful_section_navigation(
        "Report section",
        report_sections,
        state_key=report_state_key,
        container_key_prefix=report_state_key,
        default="Overview",
        control="dropdown",
        help_text=(
            "The selected report family is retained when a view, weighting, "
            "lexicon, or prepared export causes the page to refresh."
        ),
    )
    overview_tab = report_containers["Overview"]
    affective_tab = report_containers["Affective Evidence"]
    lexical_tab = report_containers["Lexical Character"]
    sound_tab = report_containers["Sound & Form"]
    structure_tab = report_containers["Structure"]
    evidence_diagnostics_tab = report_containers["Evidence & Diagnostics"]
    export_help_tab = report_containers["Export & Help"]

    def _section_label(label: str, available: bool) -> str:
        return f"{label} · {'Complete' if available else 'Not selected'}"

    with affective_tab:
        vad_tab = _bottom_collapsible_expander(
            _section_label("VAD", bool(workspace.results)),
            state_key=f"{report_state_key}_vad",
            collapse_label="VAD",
        )
        emotion_tab = _bottom_collapsible_expander(
            _section_label(
                "Emotion Association, Intensity & Sentiment",
                workspace.vader_sentiment is not None,
            ),
            state_key=f"{report_state_key}_emotion",
            collapse_label="Emotion Association, Intensity & Sentiment",
        )
        trajectory_tab = _bottom_collapsible_expander(
            _section_label(
                "Lexical Trajectory",
                any(result.vad_summary is not None for result in workspace.results),
            ),
            state_key=f"{report_state_key}_lexical_trajectory",
            collapse_label="Lexical Trajectory",
        )
        poetry_id_tab = _bottom_collapsible_expander(
            _section_label("PoetryID", workspace.poetry_id is not None),
            state_key=f"{report_state_key}_poetry_id",
            collapse_label="PoetryID",
        )
    with lexical_tab:
        concreteness_tab = _bottom_collapsible_expander(
            _section_label("Concreteness", workspace.concreteness is not None),
            state_key=f"{report_state_key}_concreteness",
            collapse_label="Concreteness",
        )
        frequency_tab = _bottom_collapsible_expander(
            _section_label("Frequency & Rarity", workspace.frequency is not None),
            state_key=f"{report_state_key}_frequency",
            collapse_label="Frequency & Rarity",
        )
        aoa_tab = _bottom_collapsible_expander(
            _section_label(
                "Acquisition & Readability",
                workspace.readability is not None,
            ),
            state_key=f"{report_state_key}_acquisition",
            collapse_label="Acquisition & Readability",
        )
    with sound_tab:
        pronunciation_tab = _bottom_collapsible_expander(
            _section_label(
                "Pronunciation, Syllables & Stress",
                workspace.pronunciation is not None,
            ),
            state_key=f"{report_state_key}_pronunciation",
            collapse_label="Pronunciation, Syllables & Stress",
        )
        meter_tab = _bottom_collapsible_expander(
            _section_label("Meter & Rhythm", workspace.meter is not None),
            state_key=f"{report_state_key}_meter",
            collapse_label="Meter & Rhythm",
        )
        phonology_tab = _bottom_collapsible_expander(
            _section_label("Rhyme & Recurring Sound", workspace.phonology is not None),
            state_key=f"{report_state_key}_phonology",
            collapse_label="Rhyme & Recurring Sound",
        )
        inherited_form_tab = _bottom_collapsible_expander(
            _section_label(
                "Inherited Form Analysis",
                workspace.inherited_form is not None,
            ),
            state_key=f"{report_state_key}_inherited_form",
            collapse_label="Inherited Form Analysis",
        )
    with structure_tab:
        language_tab = _bottom_collapsible_expander(
            _section_label("Language Profile", workspace.poem_document is not None),
            state_key=f"{report_state_key}_language",
            collapse_label="Language Profile",
        )
        lexical_style_tab = _bottom_collapsible_expander(
            _section_label(
                "Lexical & Structural Measures",
                workspace.lexical_style is not None,
            ),
            state_key=f"{report_state_key}_lexical_structure",
            collapse_label="Lexical & Structural Measures",
        )
    with evidence_diagnostics_tab:
        evidence_tab = _bottom_collapsible_expander(
            "Token Evidence, Coverage & Diagnostics · Complete",
            state_key=f"{report_state_key}_evidence",
            collapse_label="Token Evidence, Coverage & Diagnostics",
        )
    with export_help_tab:
        download_tab = _bottom_collapsible_expander(
            "Export Report & Data",
            state_key=f"{report_state_key}_exports",
            collapse_label="Export Report & Data",
        )
        help_tab = _bottom_collapsible_expander(
            "Methodology & How to Read",
            state_key=f"{report_state_key}_help",
            collapse_label="Methodology & How to Read",
        )

    with trajectory_tab:
        vad_sources = [
            result
            for result in workspace.results
            if result.vad_summary is not None
        ]
        if not vad_sources:
            st.info(
                "Select at least one VAD lexicon and analyze again to build a "
                "line-level lexical trajectory."
            )
        else:
            st.subheader("Lexical Trajectory")
            st.write(
                "Each line shows token-weighted mean normative VAD evidence for "
                "one selected lexicon. Concreteness is overlaid when that optional "
                "module was enabled. Blank or unmatched physical lines remain gaps."
            )
            source_ids = [
                result.lexicon_metadata.lexicon_id for result in vad_sources
            ]
            if st.session_state.get("lexical_trajectory_source") not in source_ids:
                st.session_state["lexical_trajectory_source"] = source_ids[0]
            trajectory_controls = st.columns(2)
            trajectory_source = trajectory_controls[0].selectbox(
                "Trajectory VAD source",
                options=source_ids,
                format_func=lambda value: next(
                    result.lexicon_metadata.display_name
                    for result in vad_sources
                    if result.lexicon_metadata.lexicon_id == value
                ),
                key="lexical_trajectory_source",
                help=(
                    "Sources remain separate. Changing this display choice retains "
                    "the Affective Evidence report section."
                ),
            )
            selected_result = next(
                result
                for result in vad_sources
                if result.lexicon_metadata.lexicon_id == trajectory_source
            )
            trajectory_view_options = ["All matched tokens"]
            if selected_result.stopword_coverage is not None:
                trajectory_view_options.append("Stopwords excluded")
            current_trajectory_view = st.session_state.get(
                "lexical_trajectory_view"
            )
            if current_trajectory_view not in trajectory_view_options:
                st.session_state["lexical_trajectory_view"] = (
                    trajectory_view_options[0]
                )
            trajectory_view = trajectory_controls[1].selectbox(
                "Trajectory token scope",
                options=trajectory_view_options,
                key="lexical_trajectory_view",
                help=(
                    "The full and stopword-excluded views remain distinct; changing "
                    "this display choice does not rerun the poem analysis."
                ),
            )
            trajectory = lexical_trajectory_views(
                workspace,
                lexicon_id=trajectory_source,
                analysis_view=trajectory_view,
            )
            trajectory_frame = pd.DataFrame(
                [
                    {
                        "Line": row.line_number,
                        "Text": row.source_text,
                        "Valence": row.valence_mean,
                        "Arousal": row.arousal_mean,
                        "Dominance": row.dominance_mean,
                        "Concreteness": row.concreteness_mean_normalized,
                        "Concreteness (source 1-5)": (
                            row.concreteness_mean_source_scale
                        ),
                        "VAD matches": row.vad_matched_observations,
                        "Concreteness matches": row.concreteness_matched_tokens,
                    }
                    for row in trajectory
                ]
            )
            chart_columns = ["Valence", "Arousal", "Dominance"]
            if workspace.concreteness is not None:
                chart_columns.append("Concreteness")
            chart_long = trajectory_frame.melt(
                id_vars=["Line", "Text"],
                value_vars=chart_columns,
                var_name="Measure",
                value_name="Mean",
            )
            trajectory_chart = (
                alt.Chart(chart_long)
                .mark_line(point=True, strokeWidth=2.4)
                .encode(
                    x=alt.X(
                        "Line:Q",
                        title="Physical line",
                        axis=alt.Axis(tickMinStep=1),
                    ),
                    y=alt.Y(
                        "Mean:Q",
                        title="Mean rating (normalized 0-1)",
                        scale=alt.Scale(domain=[0, 1]),
                    ),
                    color=alt.Color(
                        "Measure:N",
                        scale=alt.Scale(
                            domain=[
                                "Valence",
                                "Arousal",
                                "Dominance",
                                "Concreteness",
                            ],
                            range=[
                                "#c64e52",
                                "#d88b1f",
                                "#3778b8",
                                "#3f8b5b",
                            ],
                        ),
                        legend=alt.Legend(title=None, orient="top"),
                    ),
                    tooltip=[
                        alt.Tooltip("Line:Q", format=".0f"),
                        "Text:N",
                        "Measure:N",
                        alt.Tooltip("Mean:Q", format=".3f"),
                    ],
                )
                .properties(height=360)
            )
            st.altair_chart(
                trajectory_chart,
                width="stretch",
                theme="streamlit",
            )
            if workspace.concreteness is None:
                st.info(
                    "Concreteness was not enabled for this analysis, so this graph "
                    "shows the three VAD trajectories. Enable Concreteness to add "
                    "the fourth line."
                )
            else:
                st.caption(
                    "Concreteness is linearly rescaled from its source 1-5 range "
                    "to 0-1 for this overlay only: (rating - 1) / 4. The original "
                    "line means remain in the table and CSV export."
                )
            render_dataframe(
                trajectory_frame,
                hide_index=True,
                width="stretch",
                height=360,
            )
            st.caption(
                "Means use only matched observations on each physical line. "
                "Missing evidence is not entered as zero and adjacent points may "
                "therefore be separated by gaps."
            )

    with poetry_id_tab:
        render_poetry_id(workspace.poetry_id)

    with inherited_form_tab:
        render_inherited_form(workspace.inherited_form)

    with overview_tab:
        coverage = coverage_views(workspace)
        metrics = st.columns(4)
        lexical_tokens = (
            workspace.poem_document.coverage.lexical_token_count
            if workspace.poem_document is not None
            else (coverage[0].lexical_tokens if coverage else 0)
        )
        metrics[0].metric("Lexical tokens", f"{lexical_tokens:,}")
        metrics[1].metric("Lexicons analyzed", len(workspace.results))
        metrics[2].metric("Lines preserved", len(workspace.document.original_text.splitlines()))
        metrics[3].metric("Text checksum", workspace.document.text_sha256[:10] + "…")

        st.markdown("### Report at a Glance")
        affective_summary, lexical_summary, sound_summary, structure_summary = (
            st.columns(4)
        )
        primary_vad = next(
            (
                row
                for row in vad_views(workspace)
                if row.analysis_view == "All matched tokens"
            ),
            None,
        )
        primary_poetry_id = (
            next(
                (
                    row
                    for row in workspace.poetry_id.assignments
                    if row.analysis_view == "all_matched"
                    and row.weighting_mode == "token"
                ),
                None,
            )
            if workspace.poetry_id is not None
            else None
        )
        with affective_summary:
            st.markdown("#### Affective Evidence")
            if primary_vad is not None:
                st.write(
                    f"V {_decimal(primary_vad.normalized_valence)} · "
                    f"A {_decimal(primary_vad.normalized_arousal)} · "
                    f"D {_decimal(primary_vad.normalized_dominance)}"
                )
                st.caption(primary_vad.lexicon)
            else:
                st.write("Not selected")
            if primary_poetry_id is not None:
                st.write(
                    "**Nearest PoetryID profile:** "
                    f"{primary_poetry_id.nearest_centroid_archetype.name}"
                )
            st.caption("Open Affective Evidence for sources, weighting, and details.")
        with lexical_summary:
            st.markdown("#### Lexical Character")
            if workspace.concreteness is not None:
                st.write(
                    "Concreteness: "
                    f"{_decimal(workspace.concreteness.summary.statistics.mean)}"
                )
            if workspace.frequency is not None:
                st.write(
                    "Median Zipf: "
                    f"{_decimal(workspace.frequency.summary.statistics.median)}"
                )
            if workspace.aoa is not None:
                st.write(
                    "Mean AoA: "
                    f"{_decimal(workspace.aoa.summary.statistics.mean)} years"
                )
            if all(
                result is None
                for result in (
                    workspace.concreteness,
                    workspace.frequency,
                    workspace.aoa,
                )
            ):
                st.write("Not selected")
            st.caption("Open Lexical Character for distributions and coverage.")
        with sound_summary:
            st.markdown("#### Sound & Form")
            if workspace.meter is not None:
                st.write(
                    "**Nearest meter candidate:** "
                    f"{workspace.meter.summary.closest_candidate_label}"
                )
            if workspace.phonology is not None:
                st.write(
                    "**Rhyme scheme:** "
                    f"{workspace.phonology.summary.whole_poem_rhyme_scheme or '—'}"
                )
            if workspace.meter is None and workspace.phonology is None:
                st.write("Not selected")
            st.caption("Open Sound & Form for line-level and pronunciation evidence.")
        with structure_summary:
            st.markdown("#### Structure")
            st.write(f"{lexical_tokens:,} lexical tokens")
            st.write(
                f"{len(workspace.document.original_text.splitlines()):,} "
                "physical lines"
            )
            if workspace.lexical_style is not None:
                st.write("Lexical diversity and word-count profiles complete")
            st.caption("Open Structure for language and line/stanza measures.")

        st.markdown(
            '<div class="versevad-callout"><strong>Begin here:</strong> Coverage is the '
            "share of eligible vocabulary that found an entry in each lexicon. "
            "Every aggregate below is based only on matched evidence.</div>",
            unsafe_allow_html=True,
        )
        if coverage:
            coverage_frame = _frame(
                coverage,
                {
                    "lexicon": "Lexicon",
                    "matched_tokens": "Matched tokens",
                    "lexical_tokens": "Lexical tokens",
                    "coverage": "Coverage",
                    "matched_types": "Matched types",
                    "total_types": "Total types",
                    "exact_matches": "Exact",
                    "lemma_matches": "Lemma",
                    "phrase_matches": "Phrases",
                    "note": "Reading note",
                },
            )
            coverage_frame["Coverage"] = coverage_frame["Coverage"].map(
                _percentage
            )
            render_dataframe(
                coverage_frame[
                    [
                        "Lexicon",
                        "Matched tokens",
                        "Lexical tokens",
                        "Coverage",
                        "Exact",
                        "Lemma",
                        "Phrases",
                        "Reading note",
                    ]
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info(
                "No affective lexicon was selected for this result. Optional "
                "module coverage is reported separately below."
            )
        if workspace.frequency is not None:
            frequency_summary = workspace.frequency.summary
            st.markdown("**SUBTLEX-US frequency coverage**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Resource": workspace.frequency.resource_status.display_name,
                            "Scope": frequency_summary.scope_label,
                            "Matched tokens": frequency_summary.matched_token_count,
                            "Eligible tokens": frequency_summary.eligible_token_count,
                            "Matched-token coverage": frequency_summary.token_coverage,
                            "Matched unique words": (
                                frequency_summary.matched_unique_type_count
                            ),
                            "Eligible unique words": (
                                frequency_summary.eligible_unique_type_count
                            ),
                            "Unique-word coverage": (
                                frequency_summary.unique_type_coverage
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Matched-token coverage": lambda value: _percentage(value),
                        "Unique-word coverage": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if workspace.concreteness is not None:
            concrete_summary = workspace.concreteness.summary
            st.markdown("**Concreteness coverage**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Resource": (
                                workspace.concreteness.resource_status.display_name
                            ),
                            "Rated tokens": concrete_summary.rated_token_count,
                            "Eligible tokens": concrete_summary.eligible_token_count,
                            "Rated-token coverage": (
                                concrete_summary.token_coverage
                            ),
                            "Rated unique words": (
                                concrete_summary.rated_unique_type_count
                            ),
                            "Eligible unique words": (
                                concrete_summary.eligible_unique_type_count
                            ),
                            "Unique-word coverage": (
                                concrete_summary.unique_type_coverage
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Rated-token coverage": lambda value: _percentage(value),
                        "Unique-word coverage": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if workspace.aoa is not None:
            aoa_summary = workspace.aoa.summary
            st.markdown("**Age-of-acquisition coverage**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Resource": workspace.aoa.resource_status.display_name,
                            "Scope": aoa_summary.scope_label,
                            "Matched tokens": aoa_summary.matched_token_count,
                            "Eligible tokens": aoa_summary.eligible_token_count,
                            "Matched-token coverage": aoa_summary.token_coverage,
                            "Matched unique words": (
                                aoa_summary.matched_unique_type_count
                            ),
                            "Eligible unique words": (
                                aoa_summary.eligible_unique_type_count
                            ),
                            "Unique-word coverage": (
                                aoa_summary.unique_type_coverage
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Matched-token coverage": lambda value: _percentage(value),
                        "Unique-word coverage": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if workspace.pronunciation is not None:
            pronunciation_summary = workspace.pronunciation.summary
            st.markdown("**Pronunciation and prosody-foundation coverage**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Resource": "Pinned official CMUdict",
                            "Resolved tokens": (
                                pronunciation_summary.resolved_token_count
                            ),
                            "Eligible tokens": (
                                pronunciation_summary.eligible_token_count
                            ),
                            "Resolved-token coverage": (
                                pronunciation_summary.token_coverage
                            ),
                            "Resolved unique words": (
                                pronunciation_summary.resolved_unique_type_count
                            ),
                            "Eligible unique words": (
                                pronunciation_summary.eligible_unique_type_count
                            ),
                            "Unique-word coverage": (
                                pronunciation_summary.unique_type_coverage
                            ),
                            "Complete lines": (
                                pronunciation_summary.complete_line_count
                            ),
                            "Eligible lines": (
                                pronunciation_summary.eligible_line_count
                            ),
                            "Complete-line coverage": (
                                pronunciation_summary.complete_line_coverage
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Resolved-token coverage": lambda value: _percentage(
                            value
                        ),
                        "Unique-word coverage": lambda value: _percentage(value),
                        "Complete-line coverage": lambda value: _percentage(
                            value
                        ),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if show_stopword_excluded:
            filtered_coverage = [
                {
                    "Lexicon": result.lexicon_metadata.display_name,
                    "Matched non-stopword tokens": result.stopword_coverage.matched_token_count,
                    "Eligible non-stopword tokens": result.stopword_coverage.eligible_token_count,
                    "Content-focused coverage": result.stopword_coverage.lexical_token_coverage,
                    "Excluded matched observations": (
                        result.stopword_coverage.excluded_matched_observation_count
                    ),
                    "Excluded matched types": (
                        result.stopword_coverage.excluded_matched_type_count
                    ),
                }
                for result in workspace.results
                if result.stopword_coverage is not None
            ]
            if filtered_coverage:
                st.markdown("**Stopwords-excluded coverage**")
                render_dataframe(
                    pd.DataFrame(filtered_coverage).style.format(
                        {
                            "Content-focused coverage": lambda value: _percentage(
                                value
                            ),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Content-focused coverage uses eligible non-stopword tokens as "
                    "its denominator, so intentional exclusions do not appear as "
                    "failed matches."
                )
            policy = next(
                (
                    result.stopword_policy
                    for result in workspace.results
                    if result.stopword_policy is not None
                ),
                None,
            )
            if policy is not None:
                with st.expander("Stopword methodology used for this analysis"):
                    excluded_tokens = max(
                        (
                            result.stopword_coverage.excluded_matched_token_count
                            for result in workspace.results
                            if result.stopword_coverage is not None
                        ),
                        default=0,
                    )
                    st.write(
                        f"Source: **{policy.source}** · library "
                        f"**{policy.library_version}** · active exclusions "
                        f"**{len(policy.active_words):,}** · excluded matched tokens "
                        f"in the current text (maximum across selected lexicons): "
                        f"**{excluded_tokens:,}**"
                    )
                    st.write(
                        "**Protected words:** "
                        + ", ".join(policy.protected_words)
                    )
                    st.write(
                        "**Custom additions:** "
                        + (", ".join(policy.custom_additions) or "none")
                    )
                    st.write(
                        "**Custom removals:** "
                        + (", ".join(policy.custom_removals) or "none")
                    )
        st.caption(
            "The 60% and 80% coverage bands are orientation aids, not universal scholarly cutoffs."
        )
        st.subheader("How to Frame This Result")
        for note in overview_notes(workspace):
            st.markdown(f"- {note}")
        warnings = [
            (result.lexicon_metadata.display_name, warning)
            for result in workspace.results
            for warning in result.warnings
        ]
        if workspace.concreteness is not None:
            warnings.extend(
                (
                    "Concreteness",
                    warning.message,
                )
                for warning in workspace.concreteness.module_result.warnings
            )
        if workspace.frequency is not None:
            warnings.extend(
                (
                    "Frequency",
                    warning.message,
                )
                for warning in workspace.frequency.module_result.warnings
            )
        if workspace.aoa is not None:
            warnings.extend(
                (
                    "Age of Acquisition",
                    warning.message,
                )
                for warning in workspace.aoa.module_result.warnings
            )
        if workspace.pronunciation is not None:
            warnings.extend(
                (
                    "Pronunciation & Prosody",
                    warning.message,
                )
                for warning in workspace.pronunciation.module_result.warnings
            )
        if workspace.meter is not None:
            warnings.extend(
                ("Meter & Rhythm", warning.message)
                for warning in workspace.meter.module_result.warnings
            )
        if workspace.phonology is not None:
            warnings.extend(
                ("Rhyme & Sound", warning.message)
                for warning in workspace.phonology.module_result.warnings
            )
        if workspace.lexical_style is not None:
            warnings.extend(
                ("Lexical Style", warning.message)
                for warning in workspace.lexical_style.module_result.warnings
            )
        if warnings:
            with st.expander(f"Warnings and cautions ({len(warnings)})"):
                for lexicon, warning in warnings:
                    st.warning(f"{lexicon}: {warning}")

    with language_tab:
        poem_document = workspace.poem_document
        if poem_document is not None:
            st.subheader("Shared Processing Record")
            st.write(
                "This is the reusable structural and linguistic representation "
                "created once for the text and shared by the selected analyses. "
                "The original text remains unchanged; normalized lookup forms and "
                "model annotations are stored separately."
            )
            structure_columns = st.columns(5)
            structure_columns[0].metric("Stanzas", len(poem_document.stanzas))
            structure_columns[1].metric("Physical lines", len(poem_document.lines))
            structure_columns[2].metric(
                "Model sentences", poem_document.coverage.sentence_count
            )
            structure_columns[3].metric(
                "Tokens", poem_document.coverage.total_token_count
            )
            structure_columns[4].metric(
                "Lexical tokens", poem_document.coverage.lexical_token_count
            )
            st.write(
                f"**Processing recipe:** `{poem_document.configuration.recipe_id}` "
                f"| **configuration:** "
                f"`{poem_document.configuration.configuration_id}` "
                f"| **pipeline:** `{poem_document.preprocessing.pipeline_name}` "
                f"{poem_document.preprocessing.pipeline_version} "
                f"| **dependency coverage:** "
                f"{_percentage(poem_document.coverage.dependency_annotation_rate)} "
                f"| **NER:** "
                f"{'enabled' if poem_document.configuration.enable_ner else 'disabled'}"
            )
            if not poem_document.coverage.model_vocabulary_available:
                st.info(
                    "Model-vocabulary OOV reporting is unavailable because the "
                    "installed small English model has no static vectors. This does "
                    "not affect named-resource coverage: each lexicon or later "
                    "research dataset reports its own unmatched terms separately."
                )
            with st.expander(
                f"Processing warnings and cautions ({len(poem_document.warnings)})"
            ):
                for warning in poem_document.warnings:
                    if warning.severity.value == "information":
                        st.info(warning.message)
                    else:
                        st.warning(warning.message)

        st.subheader("Part-of-Speech Profile")
        st.write(
            "This is a grammatical profile of all eligible lexical token occurrences, "
            "independent of affective-lexicon coverage. The count is the number of "
            "occurrences assigned to a category; the share divides that count by all "
            "eligible lexical tokens in this text. The displayed Noun category combines "
            "the model's common-noun (NOUN) and proper-noun (PROPN) tags; Verb "
            "combines main-verb (VERB) and auxiliary/copular (AUX) tags."
        )
        pos_rows = part_of_speech_views(workspace)
        if pos_rows:
            pos_frame = _frame(
                pos_rows,
                {
                    "tag": "Source POS tag(s)",
                    "category": "Part of speech",
                    "token_count": "Token count",
                    "share_of_lexical_tokens": "Share of lexical tokens",
                    "unique_type_count": "Unique normalized types",
                    "example_forms": "Examples",
                    "lexical_token_denominator": "Lexical-token denominator",
                },
            )
            st.bar_chart(
                pos_frame.set_index("Part of speech")[["Share of lexical tokens"]],
                height=320,
            )
            render_dataframe(
                pos_frame.style.format(
                    {"Share of lexical tokens": lambda value: _percentage(value)}
                ),
                hide_index=True,
                width="stretch",
            )
            vad_pos_rows = vad_part_of_speech_views(workspace)
            if vad_pos_rows:
                st.subheader("VAD Means by Part of Speech")
                st.write(
                    "These source-separated rows add matched normative VAD "
                    "evidence to the grammatical profile. Token-weighted means "
                    "count every included match occurrence; type-weighted means "
                    "count each distinct matched lexicon entry once within its "
                    "lexicon, analysis view, and part-of-speech group."
                )
                vad_pos_frame = _frame(
                    vad_pos_rows,
                    {
                        "lexicon": "Lexicon",
                        "analysis_view": "Analysis view",
                        "tag": "Source POS tag(s)",
                        "category": "Part of speech",
                        "matched_observations": "Matched observations",
                        "matched_types": "Distinct matched types",
                        "matched_token_occurrences": "Covered token occurrences",
                        "eligible_token_occurrences": "Eligible token occurrences",
                        "lexical_coverage": "Lexical-token coverage",
                        "token_weighted_valence": "Token-weighted valence",
                        "token_weighted_arousal": "Token-weighted arousal",
                        "token_weighted_dominance": "Token-weighted dominance",
                        "type_weighted_valence": "Type-weighted valence",
                        "type_weighted_arousal": "Type-weighted arousal",
                        "type_weighted_dominance": "Type-weighted dominance",
                        "phrase_observations": "Published phrase observations",
                        "is_sparse": "Sparse",
                    },
                )[
                    [
                        "Lexicon",
                        "Analysis view",
                        "Part of speech",
                        "Source POS tag(s)",
                        "Matched observations",
                        "Distinct matched types",
                        "Covered token occurrences",
                        "Eligible token occurrences",
                        "Lexical-token coverage",
                        "Token-weighted valence",
                        "Token-weighted arousal",
                        "Token-weighted dominance",
                        "Type-weighted valence",
                        "Type-weighted arousal",
                        "Type-weighted dominance",
                        "Published phrase observations",
                        "Sparse",
                    ]
                ]
                mean_columns = {
                    "Token-weighted valence",
                    "Token-weighted arousal",
                    "Token-weighted dominance",
                    "Type-weighted valence",
                    "Type-weighted arousal",
                    "Type-weighted dominance",
                }
                render_dataframe(
                    vad_pos_frame.style.format(
                        {
                            "Lexical-token coverage": (
                                lambda value: (
                                    "not available"
                                    if pd.isna(value)
                                    else _percentage(float(value))
                                )
                            ),
                            **{
                                column: (
                                    lambda value: (
                                        "not available"
                                        if pd.isna(value)
                                        else _decimal(float(value))
                                    )
                                )
                                for column in mean_columns
                            },
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Means use each lexicon's independently normalized 0-1 "
                    "ratings. Unmatched evidence remains missing, never neutral. "
                    "An accepted multiword entry contributes one observation; "
                    "phrases spanning more than one broad POS stay in the "
                    "Mixed-POS Phrase row, whose token-coverage denominator is "
                    "not defined. Sparse marks fewer matches than the configured "
                    "minimum."
                )
            st.subheader("Detailed Model-Tag Breakdown")
            st.write(
                "This second table preserves the installed model's Universal "
                "Dependencies distinctions. Use it to audit how the broad Noun and "
                "Verb rows were composed."
            )
            detailed_pos_frame = _frame(
                detailed_part_of_speech_views(workspace),
                {
                    "tag": "Universal POS tag",
                    "category": "Detailed category",
                    "token_count": "Token count",
                    "share_of_lexical_tokens": "Share of lexical tokens",
                    "unique_type_count": "Unique normalized types",
                    "example_forms": "Examples",
                    "lexical_token_denominator": "Lexical-token denominator",
                },
            )
            render_dataframe(
                detailed_pos_frame.style.format(
                    {"Share of lexical tokens": lambda value: _percentage(value)}
                ),
                hide_index=True,
                width="stretch",
            )
            st.warning(
                "Part-of-speech labels are generated by the installed English model. "
                "Poetic syntax, archaic forms, fragments, and deliberate ambiguity can "
                "produce uncertain labels; inspect the token-level Evidence table when "
                "a distinction matters."
            )
        else:
            st.info("This text contains no eligible lexical tokens to profile.")

    with lexical_style_tab:
        lexical_style = workspace.lexical_style
        if lexical_style is None:
            st.info(
                "Lexical Style was not selected for this result. Enable "
                "Lexical diversity, word length & structural word counts under "
                "Choose Evidence, then run the analysis again."
            )
        else:
            summary = lexical_style.summary
            configuration = lexical_style.configuration
            st.subheader("Lexical Diversity")
            st.write(
                "These measures use normalized observed surface forms. Lemmas "
                "remain visible in the audit but never silently replace the "
                "word forms present in the poem."
            )
            diversity_columns = st.columns(5)
            diversity_columns[0].metric(
                "Lexical tokens",
                f"{summary.lexical_token_count:,}",
            )
            diversity_columns[1].metric(
                "Surface types",
                f"{summary.normalized_surface_type_count:,}",
            )
            diversity_columns[2].metric(
                f"MATTR ({configuration.mattr_window_size})",
                _decimal(summary.mattr),
            )
            diversity_columns[3].metric(
                f"HD-D ({configuration.hdd_sample_size})",
                _decimal(summary.hdd),
            )
            diversity_columns[4].metric(
                f"MTLD ({configuration.mtld_threshold:g})",
                _decimal(summary.mtld),
            )
            st.caption(
                "MATTR averages overlapping fixed-window type-token ratios. "
                "HD-D estimates the expected distinct-type proportion in a "
                "without-replacement sample. MTLD reports the mean forward/reverse "
                "token-sequence length that maintains the configured TTR threshold. "
                "A missing value means the configured calculation was unavailable."
            )
            st.warning(
                "Lexical diversity is a configured textual descriptor, not a "
                "measure of literary quality, vocabulary knowledge, intelligence, "
                "or reader ability. Compare only matching configurations and "
                "word-unit policies."
            )

            st.subheader("Word Length")
            word_length_columns = st.columns(4)
            word_length_columns[0].metric(
                "Mean letters",
                _decimal(summary.mean_alphabetic_characters_per_token),
            )
            word_length_columns[1].metric(
                "Median letters",
                _decimal(summary.median_alphabetic_characters_per_token),
            )
            word_length_columns[2].metric(
                "Minimum",
                _decimal(summary.minimum_alphabetic_characters),
            )
            word_length_columns[3].metric(
                "Maximum",
                _decimal(summary.maximum_alphabetic_characters),
            )
            st.caption(
                "Word length counts Unicode alphabetic characters in each "
                "included lexical-token surface. It does not count punctuation "
                "marks, bytes, or syllables."
            )
            length_frame = _frame(
                lexical_style.word_length_distribution,
                {
                    "alphabetic_character_count": "Alphabetic characters",
                    "token_count": "Token count",
                    "token_proportion": "Token proportion",
                },
            )
            if not length_frame.empty:
                st.bar_chart(
                    length_frame.set_index("Alphabetic characters")[["Token count"]],
                    height=260,
                )
                render_dataframe(
                    length_frame.style.format(
                        {"Token proportion": lambda value: _percentage(value)}
                    ),
                    hide_index=True,
                    width="stretch",
                )

            st.subheader("Structural Count Summary")
            st.write(
                "These averages summarize the poem's nonblank physical lines "
                "and stanzas using the same lexical-token counts shown in the "
                "detailed tables below."
            )
            structural_mean_columns = st.columns(3)
            structural_mean_columns[0].metric(
                "Average words per nonblank line",
                _decimal(summary.nonblank_line_word_count_statistics.mean),
            )
            structural_mean_columns[1].metric(
                "Average words per stanza",
                _decimal(summary.stanza_word_count_statistics.mean),
            )
            structural_mean_columns[2].metric(
                "Average nonblank lines per stanza",
                _decimal(summary.stanza_line_count_statistics.mean),
            )
            structural_sd_columns = st.columns(3)
            structural_sd_columns[0].metric(
                "SD words per nonblank line",
                _decimal(
                    summary.nonblank_line_word_count_statistics
                    .population_standard_deviation
                ),
            )
            structural_sd_columns[1].metric(
                "SD words per stanza",
                _decimal(
                    summary.stanza_word_count_statistics
                    .population_standard_deviation
                ),
            )
            structural_sd_columns[2].metric(
                "SD nonblank lines per stanza",
                _decimal(
                    summary.stanza_line_count_statistics
                    .population_standard_deviation
                ),
            )
            st.caption(
                "SD is the population standard deviation across all observed "
                "units in this poem. Blank stanza-separator lines are excluded "
                "from the line denominator; stanza line counts likewise count "
                "nonblank physical lines."
            )

            st.subheader("Words by Physical Line")
            st.write(
                "Every preserved physical line remains visible. Blank stanza "
                "separators therefore appear with word count zero."
            )
            line_frame = _frame(
                lexical_style.line_summaries,
                {
                    "ordinal": "Line",
                    "source_text": "Source text",
                    "is_blank": "Blank separator",
                    "word_count": "Word count (lexical tokens)",
                    "normalized_surface_type_count": "Surface types",
                    "surface_type_token_ratio": "Line TTR",
                    "mean_alphabetic_characters_per_token": "Mean letters",
                    "median_alphabetic_characters_per_token": "Median letters",
                },
            )
            render_dataframe(
                line_frame.style.format(
                    {
                        "Line TTR": lambda value: _decimal(value),
                        "Mean letters": lambda value: _decimal(value),
                        "Median letters": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
                height=360,
            )

            st.subheader("Words by Stanza")
            stanza_frame = _frame(
                lexical_style.stanza_summaries,
                {
                    "ordinal": "Stanza",
                    "line_count": "Nonblank lines",
                    "word_count": "Word count (lexical tokens)",
                    "normalized_surface_type_count": "Surface types",
                    "surface_type_token_ratio": "Stanza TTR",
                    "mean_alphabetic_characters_per_token": "Mean letters",
                    "median_alphabetic_characters_per_token": "Median letters",
                },
            )
            render_dataframe(
                stanza_frame.style.format(
                    {
                        "Stanza TTR": lambda value: _decimal(value),
                        "Mean letters": lambda value: _decimal(value),
                        "Median letters": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            with st.expander(
                "Lexical-style methodology, coverage, and warnings"
            ):
                st.write(
                    f"Configuration: `{configuration.configuration_id}` · "
                    f"Scenario: `{configuration.scenario_id}`"
                )
                for coverage in lexical_style.module_result.coverage:
                    st.write(
                        f"**{coverage.coverage_id}:** "
                        f"{coverage.matched_count}/{coverage.eligible_count} "
                        f"({_percentage(coverage.coverage_rate)}) — {coverage.note}"
                    )
                for warning in lexical_style.module_result.warnings:
                    if warning.severity.value == "information":
                        st.info(warning.message)
                    else:
                        st.warning(warning.message)

    with concreteness_tab:
        concreteness = workspace.concreteness
        if concreteness is None:
            st.info(
                "Concreteness was not selected for this result. Enable the "
                "optional Concreteness profile under Choose Evidence, then run "
                "the analysis again."
            )
            if not concreteness_status.available:
                st.warning(concreteness_status.message)
        else:
            summary = concreteness.summary
            st.subheader("Normative Lexical Concreteness")
            st.write(
                "These values summarize matched Brysbaert, Warriner, and "
                "Kuperman ratings. On the source scale, 1 is very abstract "
                "(language-based) and 5 is very concrete (experience-based). "
                "They describe normative lexical evidence, not the poem's "
                "quality, imagery success, readability, intelligence, or "
                "comprehensibility."
            )
            headline = st.columns(6)
            headline[0].metric("Mean", _decimal(summary.statistics.mean))
            headline[1].metric("Median", _decimal(summary.statistics.median))
            headline[2].metric(
                "Population SD",
                _decimal(summary.statistics.population_standard_deviation),
            )
            headline[3].metric(
                "IQR",
                _decimal(summary.interquartile_range),
            )
            headline[4].metric(
                "Rated-token coverage",
                _percentage(summary.token_coverage),
            )
            headline[5].metric(
                "Unique-word coverage",
                _percentage(summary.unique_type_coverage),
            )
            st.caption(
                f"{summary.rated_token_count:,} of "
                f"{summary.eligible_token_count:,} eligible token occurrences "
                f"and {summary.rated_unique_type_count:,} of "
                f"{summary.eligible_unique_type_count:,} unique normalized "
                "surface types were rated. Unmatched values remain missing."
            )

            band_columns = st.columns(2)
            band_columns[0].metric(
                f"Rating >= {summary.highly_concrete_min:g}",
                _percentage(summary.highly_concrete_proportion),
                help=(
                    "Configurable VerseVAD orientation band among rated token "
                    "occurrences; not a category defined by the source paper."
                ),
            )
            band_columns[1].metric(
                f"Rating <= {summary.highly_abstract_max:g}",
                _percentage(summary.highly_abstract_proportion),
                help=(
                    "Configurable VerseVAD orientation band among rated token "
                    "occurrences; not a category defined by the source paper."
                ),
            )
            st.caption(
                "The extreme bands are configurable display aids. Values between "
                "them remain part of the full continuous 1-5 distribution."
            )

            if concreteness.module_result.warnings:
                with st.expander(
                    "Concreteness warnings and method notices "
                    f"({len(concreteness.module_result.warnings)})"
                ):
                    for warning in concreteness.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            rated_lines = [
                group
                for group in concreteness.line_summaries
                if group.statistics.mean is not None
            ]
            st.subheader("Physical-Line Profile")
            if rated_lines:
                line_frame = pd.DataFrame(
                    [
                        {
                            "Line": group.ordinal,
                            "Mean normative concreteness": group.statistics.mean,
                            "Median": group.statistics.median,
                            "Rated tokens": group.rated_token_count,
                            "Eligible tokens": group.eligible_token_count,
                            "Coverage": group.token_coverage,
                            "Text": group.source_text,
                        }
                        for group in rated_lines
                    ]
                )
                st.line_chart(
                    line_frame.set_index("Line")[
                        ["Mean normative concreteness"]
                    ],
                    height=280,
                )
                render_dataframe(
                    line_frame.style.format(
                        {
                            "Mean normative concreteness": lambda value: _decimal(
                                value
                            ),
                            "Median": lambda value: _decimal(value),
                            "Coverage": lambda value: _percentage(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No physical line contains a rated eligible token.")

            st.subheader("Stanza Profile")
            stanza_frame = pd.DataFrame(
                [
                    {
                        "Stanza": group.ordinal,
                        "Mean": group.statistics.mean,
                        "Median": group.statistics.median,
                        "Population SD": (
                            group.statistics.population_standard_deviation
                        ),
                        "Rated tokens": group.rated_token_count,
                        "Eligible tokens": group.eligible_token_count,
                        "Coverage": group.token_coverage,
                    }
                    for group in concreteness.stanza_summaries
                ]
            )
            if not stanza_frame.empty:
                render_dataframe(
                    stanza_frame.style.format(
                        {
                            "Mean": lambda value: _decimal(value),
                            "Median": lambda value: _decimal(value),
                            "Population SD": lambda value: _decimal(value),
                            "Coverage": lambda value: _percentage(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No stanza units were available.")

            st.subheader("Concreteness by Model Part of Speech")
            pos_frame = pd.DataFrame(
                [
                    {
                        "Universal POS tag": group.label,
                        "Mean": group.statistics.mean,
                        "Median": group.statistics.median,
                        "Rated tokens": group.rated_token_count,
                        "Eligible tokens": group.eligible_token_count,
                        "Coverage": group.token_coverage,
                    }
                    for group in concreteness.part_of_speech_summaries
                ]
            )
            if not pos_frame.empty:
                render_dataframe(
                    pos_frame.style.format(
                        {
                            "Mean": lambda value: _decimal(value),
                            "Median": lambda value: _decimal(value),
                            "Coverage": lambda value: _percentage(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Part-of-speech tags come from the installed English model "
                    "and may be uncertain for poetic syntax, fragments, names, "
                    "archaic language, and deliberate ambiguity."
                )

            st.subheader("Matched Term Extremes")
            concrete_column, abstract_column = st.columns(2)
            with concrete_column:
                st.markdown("**Highest source ratings**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Term": term.source_term,
                                "Rating": term.rating,
                                "Rated token occurrences": (
                                    term.rated_token_occurrences
                                ),
                            }
                            for term in concreteness.most_concrete_terms
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            with abstract_column:
                st.markdown("**Lowest source ratings**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Term": term.source_term,
                                "Rating": term.rating,
                                "Rated token occurrences": (
                                    term.rated_token_occurrences
                                ),
                            }
                            for term in concreteness.most_abstract_terms
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            st.caption(
                "These are rankings among matched source entries, not claims "
                "about contextual meaning or the poem as a whole."
            )

            with st.expander(
                f"Concreteness token audit ({len(concreteness.token_audit):,} rows)"
            ):
                audit_frame = _frame(
                    concreteness.token_audit,
                    {
                        "surface_form": "Surface",
                        "normalized_form": "Normalized surface",
                        "lemma": "Model lemma",
                        "part_of_speech": "POS",
                        "line_number": "Line",
                        "stanza_number": "Stanza",
                        "eligible": "Eligible",
                        "included": "Rated",
                        "match_method": "Method",
                        "matched_source_term": "Source entry",
                        "rating": "Rating",
                        "source_rating_standard_deviation": "Source rating SD",
                        "source_percent_known": "Source percent known",
                        "match_group_id": "Match group",
                        "reason": "Why",
                    },
                )
                render_dataframe(
                    audit_frame[
                        [
                            "Surface",
                            "Normalized surface",
                            "Model lemma",
                            "POS",
                            "Line",
                            "Stanza",
                            "Eligible",
                            "Rated",
                            "Method",
                            "Source entry",
                            "Rating",
                            "Source rating SD",
                            "Source percent known",
                            "Match group",
                            "Why",
                        ]
                    ],
                    hide_index=True,
                    width="stretch",
                    height=420,
                )
            with st.expander("Concreteness resource and calculation provenance"):
                provenance = concreteness.module_result.provenance
                resource = provenance.resources[0]
                st.write(
                    f"**Resource:** {resource.display_name}  \n"
                    f"**Version:** {resource.version}  \n"
                    f"**SHA-256:** `{resource.source_sha256}`  \n"
                    f"**Adapter:** {resource.adapter_version}  \n"
                    f"**Module:** {concreteness.module_result.module_name} "
                    f"{concreteness.module_result.module_version}  \n"
                    f"**Configuration:** "
                    f"`{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
                st.write(f"**Citation:** {resource.citation}")
                st.caption(resource.license_notice)

    with frequency_tab:
        frequency = workspace.frequency
        if frequency is None:
            st.subheader("SUBTLEX-US Lexical Frequency & Rarity")
            st.info(
                "Frequency & rarity was not selected for this result. Enable "
                "the optional SUBTLEX-US Zipf module above and analyze again."
            )
            if not frequency_status.available:
                st.warning(frequency_status.message)
        else:
            summary = frequency.summary
            statistics = summary.statistics
            st.subheader("SUBTLEX-US Lexical Frequency & Rarity")
            st.markdown(
                '<div class="versevad-callout"><strong>Primary reading:</strong> '
                "Median Zipf describes the central corpus-relative frequency "
                "among matched eligible token occurrences. The scale is "
                "logarithmic: one Zipf point is roughly a tenfold frequency "
                "difference. It does not measure difficulty, sophistication, "
                "accessibility, or literary quality.</div>",
                unsafe_allow_html=True,
            )
            metric_columns = st.columns(5)
            metric_columns[0].metric(
                "Median Zipf (primary)", _decimal(statistics.median)
            )
            metric_columns[1].metric("Mean Zipf", _decimal(statistics.mean))
            metric_columns[2].metric(
                "Interquartile range", _decimal(summary.interquartile_range)
            )
            metric_columns[3].metric(
                "Matched-token coverage", _percentage(summary.token_coverage)
            )
            metric_columns[4].metric(
                "Unique-word coverage",
                _percentage(summary.unique_type_coverage),
            )
            st.caption(
                f"Active scope: **{summary.scope_label}**. "
                f"{summary.matched_token_count:,} of "
                f"{summary.eligible_token_count:,} eligible token occurrences "
                "matched. Unmatched words remain missing rather than Zipf zero."
            )

            st.markdown("**Configured Zipf distribution**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Band": band.label,
                            "Lower bound": band.lower_bound,
                            "Upper bound": band.upper_bound,
                            "Matched tokens": band.token_count,
                            "Proportion": band.proportion,
                        }
                        for band in summary.bands
                    ]
                ).style.format(
                    {
                        "Lower bound": lambda value: (
                            "" if pd.isna(value) else f"{value:.2f}"
                        ),
                        "Upper bound": lambda value: (
                            "" if pd.isna(value) else f"{value:.2f}"
                        ),
                        "Proportion": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Default orientation: rare <3, uncommon 3-<4, moderately "
                "common 4-<5, common 5-<6, and very common >=6. These "
                "configurable labels are not universal linguistic categories."
            )

            if frequency.module_result.warnings:
                with st.expander(
                    "Frequency warnings and methodology notes "
                    f"({len(frequency.module_result.warnings)})"
                ):
                    for warning in frequency.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            st.markdown("**Physical-line summaries**")
            line_rows = [
                {
                    "Line": group.ordinal,
                    "Text": group.source_text,
                    "Eligible tokens": group.eligible_token_count,
                    "Matched tokens": group.matched_token_count,
                    "Coverage": group.token_coverage,
                    "Median Zipf": group.statistics.median,
                    "Mean Zipf": group.statistics.mean,
                }
                for group in frequency.line_summaries
            ]
            render_dataframe(
                pd.DataFrame(
                    line_rows,
                    columns=[
                        "Line",
                        "Text",
                        "Eligible tokens",
                        "Matched tokens",
                        "Coverage",
                        "Median Zipf",
                        "Mean Zipf",
                    ],
                ).style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Median Zipf": lambda value: _decimal(value),
                        "Mean Zipf": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            with st.expander("Stanza and part-of-speech summaries"):
                stanza_rows = [
                    {
                        "Stanza": group.ordinal,
                        "Text": group.source_text,
                        "Eligible tokens": group.eligible_token_count,
                        "Matched tokens": group.matched_token_count,
                        "Coverage": group.token_coverage,
                        "Median Zipf": group.statistics.median,
                        "Mean Zipf": group.statistics.mean,
                    }
                    for group in frequency.stanza_summaries
                ]
                st.markdown("**Stanzas**")
                render_dataframe(
                    pd.DataFrame(
                        stanza_rows,
                        columns=[
                            "Stanza",
                            "Text",
                            "Eligible tokens",
                            "Matched tokens",
                            "Coverage",
                            "Median Zipf",
                            "Mean Zipf",
                        ],
                    ).style.format(
                        {
                            "Coverage": lambda value: _percentage(value),
                            "Median Zipf": lambda value: _decimal(value),
                            "Mean Zipf": lambda value: _decimal(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                pos_rows = [
                    {
                        "POS": group.label,
                        "Eligible tokens": group.eligible_token_count,
                        "Matched tokens": group.matched_token_count,
                        "Coverage": group.token_coverage,
                        "Median Zipf": group.statistics.median,
                        "Mean Zipf": group.statistics.mean,
                    }
                    for group in frequency.part_of_speech_summaries
                ]
                st.markdown("**Part of speech**")
                render_dataframe(
                    pd.DataFrame(
                        pos_rows,
                        columns=[
                            "POS",
                            "Eligible tokens",
                            "Matched tokens",
                            "Coverage",
                            "Median Zipf",
                            "Mean Zipf",
                        ],
                    ).style.format(
                        {
                            "Coverage": lambda value: _percentage(value),
                            "Median Zipf": lambda value: _decimal(value),
                            "Mean Zipf": lambda value: _decimal(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "POS labels are model-generated. When Content words only "
                    "is active, only NOUN, VERB, ADJ, and ADV are eligible."
                )

            low_column, high_column = st.columns(2)
            with low_column:
                st.markdown("**Lowest-frequency represented terms**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Term": term.source_term,
                                "Zipf": term.zipf_value,
                                "Token occurrences": (
                                    term.matched_token_occurrences
                                ),
                                "Frequency per million": (
                                    term.frequency_per_million
                                ),
                            }
                            for term in frequency.lowest_frequency_terms
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            with high_column:
                st.markdown("**Highest-frequency represented terms**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Term": term.source_term,
                                "Zipf": term.zipf_value,
                                "Token occurrences": (
                                    term.matched_token_occurrences
                                ),
                                "Frequency per million": (
                                    term.frequency_per_million
                                ),
                            }
                            for term in frequency.highest_frequency_terms
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
            with st.expander(
                f"Rare-word tail ({len(frequency.rare_word_tail):,} represented terms)"
            ):
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Term": term.source_term,
                                "Zipf": term.zipf_value,
                                "Token occurrences": (
                                    term.matched_token_occurrences
                                ),
                                "Model POS in poem": " | ".join(
                                    term.part_of_speech_tags
                                ),
                            }
                            for term in frequency.rare_word_tail
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )

            with st.expander(
                f"Frequency token audit ({len(frequency.token_audit):,} rows)"
            ):
                audit_frame = _frame(
                    frequency.token_audit,
                    {
                        "surface_form": "Surface",
                        "normalized_form": "Normalized surface",
                        "lemma": "Model lemma",
                        "part_of_speech": "POS",
                        "line_number": "Line",
                        "stanza_number": "Stanza",
                        "eligible": "Eligible",
                        "included": "Matched",
                        "match_method": "Method",
                        "matched_source_term": "Source entry",
                        "zipf_value": "Zipf",
                        "frequency_count": "Corpus count",
                        "contextual_diversity_count": "Film count",
                        "reason": "Why",
                    },
                )
                render_dataframe(
                    audit_frame[
                        [
                            "Surface",
                            "Normalized surface",
                            "Model lemma",
                            "POS",
                            "Line",
                            "Stanza",
                            "Eligible",
                            "Matched",
                            "Method",
                            "Source entry",
                            "Zipf",
                            "Corpus count",
                            "Film count",
                            "Why",
                        ]
                    ],
                    hide_index=True,
                    width="stretch",
                    height=420,
                )
            with st.expander("Frequency resource and calculation provenance"):
                provenance = frequency.module_result.provenance
                resource = provenance.resources[0]
                st.write(
                    f"**Resource:** {resource.display_name}  \n"
                    f"**Version:** {resource.version}  \n"
                    f"**SHA-256:** `{resource.source_sha256}`  \n"
                    f"**Adapter:** {resource.adapter_version}  \n"
                    f"**Module:** {frequency.module_result.module_name} "
                    f"{frequency.module_result.module_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
                st.write(f"**Citation:** {resource.citation}")
                st.caption(resource.license_notice)

    with aoa_tab:
        readability = workspace.readability
        if readability is not None:
            readability_summary = readability.summary
            st.subheader("Readability and Grade-Formula Evidence")
            st.write(
                "These familiar English formulas combine sentence length, word "
                "length, and estimated syllables. They were designed for prose, "
                "so VerseVAD presents them as orientation evidence rather than a "
                "judgment of literary quality, reader ability, or required grade."
            )
            readability_columns = st.columns(3)
            readability_columns[0].metric(
                "Flesch Reading Ease",
                _decimal(readability_summary.flesch_reading_ease),
            )
            readability_columns[1].metric(
                "Flesch-Kincaid Grade",
                _decimal(readability_summary.flesch_kincaid_grade),
            )
            readability_columns[2].metric(
                "Gunning Fog Index",
                _decimal(readability_summary.gunning_fog_index),
            )
            readability_columns = st.columns(3)
            readability_columns[0].metric(
                "Automated Readability Index",
                _decimal(readability_summary.automated_readability_index),
            )
            readability_columns[1].metric(
                "Coleman-Liau Index",
                _decimal(readability_summary.coleman_liau_index),
            )
            readability_columns[2].metric(
                "SMOG Index",
                _decimal(readability_summary.smog_index),
            )
            st.caption(
                f"Denominators: {readability_summary.word_count:,} shared-processing "
                f"lexical tokens; {readability_summary.sentence_count:,} sentence(s) "
                f"using {readability_summary.sentence_count_method}; "
                f"{readability_summary.syllable_count:,} estimated syllables. "
                f"Dictionary/override syllable coverage: "
                f"{_percentage(readability_summary.pronunciation_coverage)}. "
                f"SMOG remains missing below "
                f"{readability.configuration.smog_minimum_sentences} sentences."
            )
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Mean words per sentence": (
                                readability_summary.mean_words_per_sentence
                            ),
                            "Mean syllables per word": (
                                readability_summary.mean_syllables_per_word
                            ),
                            "Mean alphabetic characters per word": (
                                readability_summary.mean_characters_per_word
                            ),
                            "Polysyllabic words": (
                                readability_summary.polysyllabic_word_count
                            ),
                            "Dictionary/override words": (
                                readability_summary.dictionary_or_override_word_count
                            ),
                            "Heuristic words": (
                                readability_summary.heuristic_word_count
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Mean words per sentence": lambda value: _decimal(value),
                        "Mean syllables per word": lambda value: _decimal(value),
                        "Mean alphabetic characters per word": lambda value: (
                            _decimal(value)
                        ),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            heuristic_rows = [
                item
                for item in readability.word_audit
                if item.syllable_method.startswith("orthographic heuristic")
            ]
            if heuristic_rows:
                with st.expander(
                    "Pronunciation Estimates Needing Attention "
                    f"({len(heuristic_rows):,})",
                    expanded=False,
                ):
                    st.warning(
                        "These out-of-dictionary occurrences use an explicit "
                        "orthographic estimate for formula completeness; the estimate "
                        "is not a confirmed pronunciation. Resolve the observed word "
                        "in Sound & Form > Words Needing Attention, then reanalyze to "
                        "apply that session override here as well."
                    )
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Word": item.surface_form,
                                    "Line": item.line_number,
                                    "Estimated syllables": item.syllable_count,
                                    "Method": item.syllable_method,
                                }
                                for item in heuristic_rows
                            ]
                        ),
                        hide_index=True,
                        width="stretch",
                    )
            with st.expander("Readability Formula Cautions and Provenance"):
                for warning in readability.module_result.warnings:
                    if warning.severity.value == "information":
                        st.info(warning.message)
                    else:
                        st.warning(warning.message)
                provenance = readability.module_result.provenance
                st.write(
                    f"**Module:** {readability.module_result.module_name} "
                    f"{readability.module_result.module_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
            st.divider()

        aoa = workspace.aoa
        if aoa is None:
            st.subheader("Normative Lexical Age of Acquisition")
            st.info(
                "Age of Acquisition was not selected for this result. Enable "
                "the optional Kuperman profile under Choose Evidence, then "
                "analyze again."
            )
            if not aoa_status.available:
                st.warning(aoa_status.message)
        else:
            summary = aoa.summary
            stats = summary.statistics
            st.subheader("Normative Lexical Age of Acquisition")
            st.write(
                "Kuperman ratings are retrospective estimates, in years, of "
                "when respondents believed they learned each word. The poem "
                "summary aggregates matched source means; it is not grade level, "
                "word difficulty, intelligence, or familiarity."
            )
            st.warning(
                "Age-of-acquisition results describe lexical patterns and are "
                "not diagnostic of cognitive impairment or decline."
            )
            metric_columns = st.columns(5)
            metric_columns[0].metric(
                "Mean normative AoA",
                _decimal(stats.mean),
            )
            metric_columns[1].metric(
                "Median normative AoA",
                _decimal(stats.median),
            )
            metric_columns[2].metric(
                "Matched-token coverage",
                _percentage(summary.token_coverage),
            )
            early_band = next(
                band
                for band in summary.bands
                if band.band_id == "early_acquired"
            )
            later_band = next(
                band
                for band in summary.bands
                if band.band_id == "later_acquired"
            )
            metric_columns[3].metric(
                "Early-band share",
                _percentage(early_band.proportion),
            )
            metric_columns[4].metric(
                "Later-band share",
                _percentage(later_band.proportion),
            )
            st.caption(
                f"Scope: {summary.scope_label}. Values are token-weighted over "
                f"{summary.matched_token_count:,} matched occurrences. "
                f"Early means <= {aoa.configuration.early_acquired_max:g}; "
                f"later means >= {aoa.configuration.later_acquired_min:g}. "
                "These bands are configurable orientation aids."
            )

            st.markdown("**Distribution and source-response evidence**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Mean": stats.mean,
                            "Median": stats.median,
                            "Population SD": stats.population_standard_deviation,
                            "Q1": stats.first_quartile,
                            "Q3": stats.third_quartile,
                            "IQR": summary.interquartile_range,
                            "Minimum": stats.minimum,
                            "Maximum": stats.maximum,
                            "Minimum source numeric responses": (
                                summary.minimum_source_numeric_responses
                            ),
                            "Low-response tokens (<5)": (
                                summary.low_response_token_count
                            ),
                        }
                    ]
                ).style.format(
                    {
                        "Mean": lambda value: _decimal(value),
                        "Median": lambda value: _decimal(value),
                        "Population SD": lambda value: _decimal(value),
                        "Q1": lambda value: _decimal(value),
                        "Q3": lambda value: _decimal(value),
                        "IQR": lambda value: _decimal(value),
                        "Minimum": lambda value: _decimal(value),
                        "Maximum": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Population SD above describes variation among the poem's "
                "matched source means. Each source term's own Rating.SD and "
                "response count are separate evidence in the term and audit tables."
            )
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Band": band.label,
                            "Lower": band.lower_bound,
                            "Upper": band.upper_bound,
                            "Matched tokens": band.token_count,
                            "Proportion": band.proportion,
                        }
                        for band in summary.bands
                    ]
                ).style.format(
                    {"Proportion": lambda value: _percentage(value)}
                ),
                hide_index=True,
                width="stretch",
            )

            if aoa.relationships:
                st.markdown("**Relationships with other enabled modules**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Other measure": item.other_metric,
                                "Paired surface types": item.pair_count,
                                "Spearman rho": item.coefficient,
                                "Weighting": item.weighting,
                                "Note": item.note,
                            }
                            for item in aoa.relationships
                        ]
                    ).style.format(
                        {"Spearman rho": lambda value: _decimal(value)}
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "These are descriptive type-level associations only. A "
                    "missing coefficient means too few paired types or no rank "
                    "variation; no causal inference is made."
                )

            if aoa.module_result.warnings:
                with st.expander(
                    "Age-of-acquisition warnings and methodology notes "
                    f"({len(aoa.module_result.warnings)})"
                ):
                    for warning in aoa.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            st.markdown("**Physical-line summaries**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Line": group.ordinal,
                            "Text": group.source_text,
                            "Eligible tokens": group.eligible_token_count,
                            "Matched tokens": group.matched_token_count,
                            "Coverage": group.token_coverage,
                            "Mean normative AoA": group.statistics.mean,
                            "Median normative AoA": group.statistics.median,
                        }
                        for group in aoa.line_summaries
                    ]
                ).style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Mean normative AoA": lambda value: _decimal(value),
                        "Median normative AoA": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            with st.expander("Stanza and part-of-speech summaries"):
                for heading, groups, first_column in (
                    ("Stanzas", aoa.stanza_summaries, "Stanza"),
                    (
                        "Model part of speech",
                        aoa.part_of_speech_summaries,
                        "POS",
                    ),
                ):
                    st.markdown(f"**{heading}**")
                    rows = [
                        {
                            first_column: (
                                group.ordinal
                                if first_column == "Stanza"
                                else group.label
                            ),
                            "Text": (
                                group.source_text
                                if first_column == "Stanza"
                                else ""
                            ),
                            "Eligible tokens": group.eligible_token_count,
                            "Matched tokens": group.matched_token_count,
                            "Coverage": group.token_coverage,
                            "Mean normative AoA": group.statistics.mean,
                            "Median normative AoA": group.statistics.median,
                        }
                        for group in groups
                    ]
                    render_dataframe(
                        pd.DataFrame(rows).style.format(
                            {
                                "Coverage": lambda value: _percentage(value),
                                "Mean normative AoA": lambda value: _decimal(
                                    value
                                ),
                                "Median normative AoA": lambda value: _decimal(
                                    value
                                ),
                            }
                        ),
                        hide_index=True,
                        width="stretch",
                    )
                st.caption(
                    "POS labels are model-generated. The optional content-word "
                    "scope uses the poem occurrence's contextual tag, not the "
                    "paper's source-selection label."
                )

            early_column, late_column = st.columns(2)
            for column, heading, terms in (
                (
                    early_column,
                    "Earliest-acquired represented terms",
                    aoa.earliest_acquired_terms,
                ),
                (
                    late_column,
                    "Latest-acquired represented terms",
                    aoa.latest_acquired_terms,
                ),
            ):
                with column:
                    st.markdown(f"**{heading}**")
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Term": term.source_term,
                                    "Mean age": term.mean_age,
                                    "Source SD": (
                                        term.source_rating_standard_deviation
                                    ),
                                    "Numeric responses": (
                                        term.source_numeric_response_count
                                    ),
                                    "Token occurrences": (
                                        term.matched_token_occurrences
                                    ),
                                }
                                for term in terms
                            ]
                        ),
                        hide_index=True,
                        width="stretch",
                    )

            with st.expander(
                f"Age-of-acquisition token audit ({len(aoa.token_audit):,} rows)"
            ):
                audit_frame = _frame(
                    aoa.token_audit,
                    {
                        "surface_form": "Surface",
                        "normalized_form": "Normalized surface",
                        "lemma": "Model lemma",
                        "part_of_speech": "POS",
                        "line_number": "Line",
                        "stanza_number": "Stanza",
                        "eligible": "Eligible",
                        "included": "Matched",
                        "match_method": "Method",
                        "matched_source_term": "Source entry",
                        "mean_age": "Mean age",
                        "source_rating_standard_deviation": "Source SD",
                        "source_numeric_response_count": "Numeric responses",
                        "source_numeric_response_proportion": (
                            "Numeric-response proportion"
                        ),
                        "reason": "Why",
                    },
                )
                render_dataframe(
                    audit_frame[
                        [
                            "Surface",
                            "Normalized surface",
                            "Model lemma",
                            "POS",
                            "Line",
                            "Stanza",
                            "Eligible",
                            "Matched",
                            "Method",
                            "Source entry",
                            "Mean age",
                            "Source SD",
                            "Numeric responses",
                            "Numeric-response proportion",
                            "Why",
                        ]
                    ],
                    hide_index=True,
                    width="stretch",
                    height=420,
                )
            with st.expander(
                "Age-of-acquisition resource and calculation provenance"
            ):
                provenance = aoa.module_result.provenance
                resource = provenance.resources[0]
                st.write(
                    f"**Resource:** {resource.display_name}  \n"
                    f"**Version:** {resource.version}  \n"
                    f"**SHA-256:** `{resource.source_sha256}`  \n"
                    f"**Adapter:** {resource.adapter_version}  \n"
                    f"**Module:** {aoa.module_result.module_name} "
                    f"{aoa.module_result.module_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
                st.write(f"**Citation:** {resource.citation}")
                st.caption(resource.license_notice)

    with pronunciation_tab:
        pronunciation = workspace.pronunciation
        if pronunciation is None:
            st.info(
                "Select Pronunciation & prosody foundation, then analyze again "
                "to see dictionary syllable and lexical-stress evidence."
            )
        else:
            st.subheader("Dictionary Pronunciation, Syllables & Lexical Stress")
            st.warning(
                "CMUdict supplies North American dictionary pronunciations. "
                "Dialect, historical pronunciation, poetic elision, and "
                "performance may differ. These results do not classify meter, "
                "rhyme, or performed scansion."
            )
            summary = pronunciation.summary
            metric_columns = st.columns(5)
            metric_columns[0].metric(
                "Resolved coverage",
                _percentage(summary.token_coverage),
                help=(
                    f"{summary.resolved_token_count} of "
                    f"{summary.eligible_token_count} eligible lexical tokens"
                ),
            )
            metric_columns[1].metric(
                "Mean syllables / word",
                _decimal(summary.syllables_per_resolved_word.mean),
                help=(
                    f"Based on {summary.resolved_token_count} resolved token "
                    "occurrences."
                ),
            )
            metric_columns[2].metric(
                "Median syllables / line",
                _decimal(summary.syllables_per_complete_line.median),
                help=(
                    f"Based on {summary.complete_line_count} complete physical "
                    "lines; incomplete lines remain missing."
                ),
            )
            metric_columns[3].metric(
                "Lexical stress density",
                _percentage(summary.stress_density),
                help=(
                    "Primary and secondary lexical stress among resolved "
                    "dictionary syllables; not metrical stress."
                ),
            )
            metric_columns[4].metric(
                "Complete lines",
                (
                    f"{summary.complete_line_count}/"
                    f"{summary.eligible_line_count}"
                ),
                help=(
                    "Every eligible word must resolve before VerseVAD reports a "
                    "line total or stress sequence."
                ),
            )
            st.caption(
                f"Exact observed-form lookup. {summary.ambiguous_token_count:,} "
                "token occurrence(s) have materially different dictionary "
                f"alternatives; {summary.unmatched_token_count:,} are outside "
                "the pinned dictionary; neither receives a fabricated value."
            )

            if pronunciation.module_result.warnings:
                with st.expander(
                    "Pronunciation warnings and methodology notes "
                    f"({len(pronunciation.module_result.warnings)})"
                ):
                    for warning in pronunciation.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            st.markdown("**Physical-line syllable and lexical-stress evidence**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Line": line.line_number,
                            "Stanza": line.stanza_number,
                            "Text": line.source_text,
                            "Eligible tokens": line.eligible_token_count,
                            "Resolved tokens": line.resolved_token_count,
                            "Coverage": line.resolution_coverage,
                            "Complete": line.is_complete,
                            "Syllables": line.syllable_count,
                            "Lexical stress by word": (
                                line.lexical_stress_sequence
                            ),
                            "Stress density": line.stress_density,
                        }
                        for line in pronunciation.line_summaries
                    ]
                ).style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Stress density": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Stress digits follow CMUdict/ARPAbet: 0 = unstressed, "
                "1 = primary lexical stress, 2 = secondary lexical stress. "
                "A vertical bar separates words."
            )

            _render_pronunciation_attention(pronunciation)

            with st.expander(
                f"Pronunciation token audit ({len(pronunciation.token_audit):,} rows)"
            ):
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Surface": item.surface_form,
                                "Normalized surface": item.normalized_form,
                                "POS": item.part_of_speech,
                                "Line": item.line_number,
                                "Eligible": item.eligible,
                                "Resolved": item.resolved,
                                "Status": item.status.value,
                                "Candidates": item.dictionary_candidate_count,
                                "Candidate phones": " | ".join(
                                    item.dictionary_candidate_phones
                                ),
                                "Candidate stress": " | ".join(
                                    item.dictionary_candidate_stresses
                                ),
                                "Candidate syllables": " | ".join(
                                    str(value)
                                    for value in (
                                        item.dictionary_candidate_syllable_counts
                                    )
                                ),
                                "Resolved phones": item.resolved_phones,
                                "Resolved stress": (
                                    item.resolved_stress_pattern
                                ),
                                "Resolved syllables": (
                                    item.resolved_syllable_count
                                ),
                                "Resolution label": item.confidence_label,
                                "Override note": item.override_note,
                                "Why": item.reason,
                            }
                            for item in pronunciation.token_audit
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                    height=440,
                )

            with st.expander("Pronunciation resource and calculation provenance"):
                provenance = pronunciation.module_result.provenance
                for resource in provenance.resources:
                    st.write(
                        f"**{resource.display_name}:** {resource.version}  \n"
                        f"SHA-256: `{resource.source_sha256}`  \n"
                        f"Adapter: {resource.adapter_version}"
                    )
                st.write(
                    f"**Official repository commit:** "
                    f"`{pronunciation.resource_statuses[0].version}`  \n"
                    f"**Pronouncing package:** "
                    f"{pronunciation.pronouncing_package_version}  \n"
                    f"**cmudict package:** "
                    f"{pronunciation.cmudict_package_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )

    with meter_tab:
        meter = workspace.meter
        if meter is None:
            st.info(
                "Select Meter & rhythmic regularity, then analyze again to "
                "compare the 40 fixed pattern-by-foot-count templates."
            )
        else:
            st.subheader("Candidate Meter & Rhythmic Regularity")
            st.warning(
                "This module reports nearest configured candidates from "
                "dictionary lexical-stress evidence. It does not establish a "
                "definitive meter, correct scansion, performed rhythm, dialect, "
                "or authorial intention."
            )
            summary = meter.summary
            meter_metrics = st.columns(6)
            meter_metrics[0].metric(
                "Nearest candidate",
                summary.closest_candidate_label or "Insufficient evidence",
                help=summary.closest_candidate_kind,
            )
            meter_metrics[1].metric(
                "Mean fit",
                _percentage(summary.whole_poem_mean_fit),
                help="Configured alignment similarity; not a probability.",
            )
            meter_metrics[2].metric(
                "Matching lines",
                (
                    f"{summary.matching_line_count}/"
                    f"{summary.analyzable_line_count}"
                ),
                help=(
                    "Lines at or above the configured "
                    f"{meter.configuration.line_match_threshold:g} fit threshold."
                ),
            )
            meter_metrics[3].metric(
                "Line coverage",
                _percentage(summary.line_coverage),
                help=(
                    f"{summary.analyzable_line_count} of "
                    f"{summary.eligible_line_count} eligible physical lines."
                ),
            )
            meter_metrics[4].metric(
                "Candidate confidence",
                summary.candidate_confidence,
                help=summary.confidence_explanation,
            )
            meter_metrics[5].metric(
                "Rhythmic variability",
                _decimal(summary.rhythmic_variability),
                help=(
                    "Population standard deviation of selected-candidate line "
                    "fits; missing when fewer than two lines are analyzable."
                ),
            )
            st.caption(
                f"Assessment: {summary.assessment.value.replace('_', ' ')}. "
                f"Nearest alternative: "
                f"{summary.alternative_candidate_label or 'none available'}. "
                f"Candidate margin: {_decimal(summary.candidate_margin)}."
            )

            performance_meter = meter.performance_aware
            if performance_meter is not None:
                st.divider()
                st.subheader("Performance-Aware Realization")
                st.warning(
                    "This optional layer models plausible relationships among "
                    "lexical stress, rhythmic expectation, phrasing, recurrence, "
                    "and the declared profile. It does not recover one mandatory "
                    "performance or the poet's intention."
                )
                performance_summary = performance_meter.poem_summary
                performance_metrics = st.columns(6)
                performance_metrics[0].metric(
                    "Rhythmic organization",
                    performance_summary.rhythmic_organization.value.replace(
                        "_",
                        " ",
                    ).title(),
                )
                performance_metrics[1].metric(
                    "Primary realized candidate",
                    (
                        performance_summary.primary_meter
                        or "Insufficient evidence"
                    ),
                )
                performance_metrics[2].metric(
                    "Mean realized score",
                    _percentage(performance_summary.mean_realized_score),
                    help="Inspectable configured component score; not a probability.",
                )
                performance_metrics[3].metric(
                    "Line coverage",
                    _percentage(performance_summary.line_coverage),
                )
                performance_metrics[4].metric(
                    "Primary-candidate share",
                    _percentage(
                        performance_summary.primary_meter_line_proportion
                    ),
                )
                performance_metrics[5].metric(
                    "Rule-based confidence",
                    performance_summary.confidence.value.replace(
                        "_",
                        " ",
                    ).title(),
                    help=performance_summary.confidence_explanation,
                )
                st.caption(
                    f"Declared profile: "
                    f"{performance_meter.style_profile.label} "
                    f"(v{performance_meter.style_profile.version}). "
                    f"Secondary candidate: "
                    f"{performance_summary.secondary_meter or 'none retained'}. "
                    "The profile is selected by the scholar, never inferred."
                )
                if performance_summary.generic_composite_pattern:
                    st.info(performance_summary.generic_composite_pattern)

                st.markdown("**Stanza-level recurrence**")
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Stanza": item.stanza_number,
                                "Lines": ", ".join(
                                    str(value)
                                    for value in item.line_numbers
                                ),
                                "Primary candidate": item.primary_candidate,
                                "Alternate candidate": (
                                    item.alternate_candidate
                                ),
                                "Analyzable lines": item.analyzable_lines,
                                "Mean realized score": (
                                    item.mean_realized_score
                                ),
                                "Regularity": item.regularity,
                                "Line-position sequence": " | ".join(
                                    item.line_position_pattern
                                ),
                                "Exceptions": ", ".join(
                                    str(value) for value in item.exceptions
                                ),
                            }
                            for item in performance_meter.stanza_summaries
                        ]
                    ).style.format(
                        {
                            "Mean realized score": (
                                lambda value: _percentage(value)
                            ),
                            "Regularity": lambda value: _percentage(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

                if (
                    meter.configuration.interpretation_depth
                    is not MeterInterpretationDepth.SUMMARY
                ):
                    st.markdown("**Line-level realized readings**")
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Line": line.line_number,
                                    "Stanza": line.stanza_number,
                                    "Text": line.source_text,
                                    "Raw lexical stress": (
                                        line.raw_lexical_stress
                                    ),
                                    "Fixed-layer candidate": (
                                        line.candidate_meter
                                    ),
                                    "Realized candidate": (
                                        line.primary_realization.candidate_label
                                        if line.primary_realization
                                        else ""
                                    ),
                                    "Candidate template": (
                                        line.primary_realization.candidate_template
                                        if line.primary_realization
                                        else ""
                                    ),
                                    "Realized scansion": (
                                        line.primary_realization.realized_display
                                        if line.primary_realization
                                        else ""
                                    ),
                                    "Overall score": (
                                        line.primary_realization.scores.overall
                                        if line.primary_realization
                                        else None
                                    ),
                                    "Confidence": line.confidence.value.replace(
                                        "_",
                                        " ",
                                    ),
                                    "Margin": line.score_margin,
                                    "Substitutions": (
                                        " | ".join(
                                            item.label
                                            for item in (
                                                line.primary_realization.substitutions
                                            )
                                        )
                                        if line.primary_realization
                                        else ""
                                    ),
                                    "Why": line.explanation,
                                }
                                for line in performance_meter.line_results
                            ]
                        ).style.format(
                            {
                                "Overall score": (
                                    lambda value: _percentage(value)
                                ),
                                "Margin": lambda value: _decimal(value),
                            }
                        ),
                        hide_index=True,
                        width="stretch",
                        height=420,
                    )
                    st.caption(
                        "Scansion notation: x weak; / strong; ^ proposed "
                        "promotion; v proposed demotion; 2 secondary-stress "
                        "flexibility; || punctuation-supported caesura; | foot "
                        "boundary. Raw lexical stress remains separate."
                    )

                    trajectory_rows = [
                        {
                            "Line": item.line_number,
                            "Stanza": item.stanza_number,
                            "Realized score": item.realized_score,
                            "Syllables": item.syllable_count,
                            "Beats": item.realized_beats,
                            "Substitutions": item.substitution_count,
                        }
                        for item in performance_meter.trajectory
                    ]
                    if trajectory_rows:
                        with st.expander("Rhythmic trajectory"):
                            trajectory_frame = pd.DataFrame(trajectory_rows)
                            st.line_chart(
                                trajectory_frame.set_index("Line")[
                                    ["Realized score"]
                                ],
                                height=240,
                            )
                            render_dataframe(
                                trajectory_frame,
                                hide_index=True,
                                width="stretch",
                            )

                if (
                    meter.configuration.interpretation_depth
                    is MeterInterpretationDepth.DETAILED
                ):
                    with st.expander(
                        "Alternate readings and component scores",
                        expanded=False,
                    ):
                        detailed_rows = []
                        for line in performance_meter.line_results:
                            readings = (
                                (line.primary_realization,)
                                + line.alternate_realizations
                                if line.primary_realization is not None
                                else ()
                            )
                            for rank, reading in enumerate(
                                readings,
                                start=1,
                            ):
                                detailed_rows.append(
                                    {
                                        "Line": line.line_number,
                                        "Rank": rank,
                                        "Role": (
                                            "Primary"
                                            if rank == 1
                                            else "Alternate"
                                        ),
                                        "Candidate": reading.candidate_label,
                                        "Overall": reading.scores.overall,
                                        "Fixed fit": (
                                            reading.scores.candidate_fit
                                        ),
                                        "Context": (
                                            reading.scores.contextual_fit
                                        ),
                                        "Phrase": reading.scores.phrase_fit,
                                        "Ending": (
                                            reading.scores.line_ending_fit
                                        ),
                                        "Poem recurrence": (
                                            reading.scores.poem_consistency
                                        ),
                                        "Stanza recurrence": (
                                            reading.scores.stanza_consistency
                                        ),
                                        "Style compatibility": (
                                            reading.scores.style_compatibility
                                        ),
                                        "Pronunciation path": " | ".join(
                                            reading.selected_pronunciation_path
                                        ),
                                    }
                                )
                        render_dataframe(
                            pd.DataFrame(detailed_rows),
                            hide_index=True,
                            width="stretch",
                            height=440,
                        )

                if performance_meter.scholar_revisions:
                    st.markdown("**Scholar revisions (kept separate)**")
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Line": item.line_number,
                                    "Text": item.source_text,
                                    "Applied to existing line": (
                                        item.applied_to_existing_line
                                    ),
                                    "Automatic candidate": (
                                        item.automatic_candidate
                                    ),
                                    "Automatic scansion": (
                                        item.automatic_scansion
                                    ),
                                    "Scholar candidate": (
                                        item.revised_candidate
                                    ),
                                    "Scholar scansion": (
                                        item.revised_scansion
                                    ),
                                    "Scholar note": item.note,
                                }
                                for item in (
                                    performance_meter.scholar_revisions
                                )
                            ]
                        ),
                        hide_index=True,
                        width="stretch",
                    )
                    st.caption(
                        "Scholar revisions do not overwrite the automatic "
                        "reading or source lexical stress."
                    )

                with st.expander("Performance-aware safeguards"):
                    for method_note in performance_meter.methodology:
                        st.write(f"- {method_note}")
                    for warning in performance_meter.warnings:
                        st.info(warning)

            st.markdown("**Physical-line candidate evidence**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Line": line.line_number,
                            "Stanza": line.stanza_number,
                            "Text": line.source_text,
                            "Status": line.status.value.replace("_", " "),
                            "Closest fixed template": (
                                line.closest_candidate.label
                                if line.closest_candidate
                                else ""
                            ),
                            "Closest fit": (
                                line.closest_candidate.fit_score
                                if line.closest_candidate
                                else None
                            ),
                            "Selected lexical stress": (
                                line.closest_candidate.selected_stress_sequence
                                if line.closest_candidate
                                else ""
                            ),
                            "Aligned observed": (
                                line.closest_candidate.aligned_observed
                                if line.closest_candidate
                                else ""
                            ),
                            "Aligned template": (
                                line.closest_candidate.aligned_template
                                if line.closest_candidate
                                else ""
                            ),
                            "Substitutions": (
                                line.closest_candidate.substitution_count
                                if line.closest_candidate
                                else None
                            ),
                            "Initial inversion": (
                                line.closest_candidate.initial_inversion_count
                                if line.closest_candidate
                                else None
                            ),
                            "Extra syllables": (
                                line.closest_candidate.extra_syllable_count
                                if line.closest_candidate
                                else None
                            ),
                            "Omitted syllables": (
                                line.closest_candidate.omitted_syllable_count
                                if line.closest_candidate
                                else None
                            ),
                            "Why": line.reason,
                        }
                        for line in meter.line_results
                    ]
                ).style.format(
                    {
                        "Closest fit": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Stress digits use CMUdict notation: 0 unstressed, 1 primary, "
                "2 secondary."
            )

            with st.expander("All 40 fixed candidates"):
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Rank": item.rank,
                                "Pattern": item.pattern.value,
                                "Feet": item.foot_count,
                                "Foot-count name": item.foot_count_name,
                                "Candidate": item.label,
                                "Mean fit": item.mean_fit,
                                "Median fit": item.median_fit,
                                "Fit variability": item.fit_variability,
                                "Matching lines": item.matching_line_count,
                                "Matching proportion": (
                                    item.matching_line_proportion
                                ),
                            }
                            for item in meter.candidate_summaries
                        ]
                    ).style.format(
                        {
                            "Mean fit": lambda value: _percentage(value),
                            "Median fit": lambda value: _percentage(value),
                            "Fit variability": lambda value: _decimal(value),
                            "Matching proportion": (
                                lambda value: _percentage(value)
                            ),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                    height=440,
                )

            if meter.module_result.warnings:
                with st.expander(
                    "Meter warnings and methodology notes "
                    f"({len(meter.module_result.warnings)})"
                ):
                    for warning in meter.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            with st.expander("Meter calculation provenance"):
                provenance = meter.module_result.provenance
                st.write(
                    f"**Module:** {meter.module_result.module_name} "
                    f"{meter.module_result.module_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Scenario:** `{provenance.scenario_id}`  \n"
                    f"**Pronunciation configuration:** "
                    f"`{meter.pronunciation_configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
                st.write(
                    "**Primary foot patterns:** iambic 01; trochaic 10; "
                    "anapestic 001; dactylic 100; amphibrachic 010.  \n"
                    "**Foot counts:** monometer through octameter.  \n"
                    "**Local deviations:** spondaic and pyrrhic substitutions, "
                    "initial inversion, feminine ending, catalexis, and extra "
                    "or omitted syllables."
                )

    with phonology_tab:
        phonology = workspace.phonology
        if phonology is None:
            st.info(
                "Select Rhyme & phonological patterns, then analyze again to "
                "inspect end rhyme, internal rhyme, and recurring sound evidence."
            )
        else:
            st.subheader("Rhyme & Recurring Phonological Patterns")
            st.warning(
                "These are dictionary- and spelling-based textual observations. "
                "They do not establish a performed rhyme, dialect, reading, "
                "sound effect, or authorial intention."
            )
            summary = phonology.summary
            rhyme_metrics = st.columns(6)
            rhyme_metrics[0].metric(
                "Whole-poem scheme",
                summary.whole_poem_rhyme_scheme or "No eligible endings",
                help="Perfect/identical groups only; x = unrhymed, ? = unresolved.",
            )
            rhyme_metrics[1].metric(
                "Ending coverage",
                _percentage(summary.ending_coverage),
                help=(
                    f"{summary.analyzable_ending_count} of "
                    f"{summary.eligible_line_count} eligible endings."
                ),
            )
            rhyme_metrics[2].metric(
                "Rhyme density",
                _percentage(summary.rhyme_density),
                help="Analyzable endings participating in an exact within-stanza pair.",
            )
            rhyme_metrics[3].metric(
                "Perfect / identical",
                (
                    f"{summary.perfect_rhyme_pair_count} / "
                    f"{summary.identical_rhyme_pair_count}"
                ),
            )
            rhyme_metrics[4].metric(
                "Slant / eye",
                (
                    f"{summary.slant_rhyme_pair_count} / "
                    f"{summary.eye_rhyme_pair_count}"
                ),
                help="Graded phonetic slant and spelling-based eye rhyme remain separate.",
            )
            rhyme_metrics[5].metric(
                "Internal pairs",
                summary.internal_rhyme_pair_count,
            )
            st.caption(
                f"Stanza schemes: {summary.stanza_scheme_sequence or 'none'}. "
                f"Refrain lines: {summary.refrain_line_count}. "
                "Masculine, feminine, and multisyllabic labels appear in the "
                "pair evidence below."
            )

            st.markdown("**Stanza-level end-rhyme summary**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Stanza": item.stanza_number,
                            "Eligible endings": item.eligible_line_count,
                            "Analyzable endings": item.analyzable_ending_count,
                            "Coverage": item.ending_coverage,
                            "Scheme": item.rhyme_scheme,
                            "Exact pairs": (
                                item.perfect_or_identical_pair_count
                            ),
                            "Slant pairs": item.slant_pair_count,
                            "Rhymed lines": item.rhymed_line_count,
                            "Rhyme density": item.rhyme_density,
                        }
                        for item in phonology.stanza_summaries
                    ]
                ).style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Rhyme density": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )

            st.markdown("**Physical-line ending and sound evidence**")
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Line": line.line_number,
                            "Stanza": line.stanza_number,
                            "Text": line.source_text,
                            "Status": line.status.value.replace("_", " "),
                            "Ending": line.ending_surface_form,
                            "Candidate phones": " | ".join(
                                line.ending_candidate_phones
                            ),
                            "Rhyme parts": " | ".join(line.ending_rhyme_parts),
                            "Poem label": line.poem_scheme_label,
                            "Stanza label": line.stanza_scheme_label,
                            "Ending shape": line.ending_shape,
                            "Refrain": line.is_refrain,
                            "Initial repeats": " ".join(
                                line.repeated_initial_consonants
                            ),
                            "Stressed-vowel repeats": " ".join(
                                line.repeated_stressed_vowels
                            ),
                            "Consonant repeats": " ".join(
                                line.repeated_consonants
                            ),
                            "Alliteration density": line.alliteration_density,
                            "Assonance density": line.assonance_density,
                            "Consonance density": line.consonance_density,
                            "Why": line.reason,
                        }
                        for line in phonology.line_results
                    ]
                ).style.format(
                    {
                        "Alliteration density": lambda value: _percentage(value),
                        "Assonance density": lambda value: _percentage(value),
                        "Consonance density": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
                height=440,
            )

            st.markdown("**Within-stanza ending-pair evidence**")
            if phonology.pair_results:
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Stanza": pair.stanza_number,
                                "Lines": (
                                    f"{pair.first_line_number}–"
                                    f"{pair.second_line_number}"
                                ),
                                "Words": (
                                    f"{pair.first_word} / {pair.second_word}"
                                ),
                                "Relationship": pair.relationship.replace("_", " "),
                                "Types": ", ".join(pair.rhyme_types),
                                "Conservative slant score": pair.similarity_score,
                                "Maximum score": pair.maximum_similarity_score,
                                "Stressed vowel": pair.stressed_vowel_similarity,
                                "Final consonants": pair.final_consonant_similarity,
                                "Rhyme-part edit": pair.phoneme_edit_similarity,
                                "Stress alignment": pair.stress_alignment_similarity,
                                "Syllable similarity": pair.syllable_count_similarity,
                                "Eye rhyme": pair.is_eye_rhyme,
                                "Orthographic rime": pair.orthographic_rime,
                                "Evidence label": pair.confidence_label,
                                "Note": pair.note,
                            }
                            for pair in phonology.pair_results
                        ]
                    ).style.format(
                        {
                            "Conservative slant score": lambda value: _decimal(value),
                            "Maximum score": lambda value: _decimal(value),
                            "Stressed vowel": lambda value: _decimal(value),
                            "Final consonants": lambda value: _decimal(value),
                            "Rhyme-part edit": lambda value: _decimal(value),
                            "Stress alignment": lambda value: _decimal(value),
                            "Syllable similarity": lambda value: _decimal(value),
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                    height=440,
                )
            else:
                st.info("No within-stanza ending pairs were available.")

            sound_columns = st.columns(3)
            sound_columns[0].metric(
                "Alliteration density",
                _percentage(summary.alliteration_density),
                help="Repeated initial consonant phonemes within physical lines.",
            )
            sound_columns[1].metric(
                "Assonance density",
                _percentage(summary.assonance_density),
                help="Repeated stressed-vowel phonemes within physical lines.",
            )
            sound_columns[2].metric(
                "Consonance density",
                _percentage(summary.consonance_density),
                help="Repeated consonant phoneme occurrences within physical lines.",
            )
            if phonology.sound_families:
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Category": item.category.replace("_", " "),
                                "Sound": item.sound,
                                "Occurrences": item.occurrence_count,
                                "Lines": item.line_count,
                                "Category share": item.share_of_category_occurrences,
                            }
                            for item in phonology.sound_families
                        ]
                    ).style.format(
                        {"Category share": lambda value: _percentage(value)}
                    ),
                    hide_index=True,
                    width="stretch",
                )

            if phonology.module_result.warnings:
                with st.expander(
                    "Rhyme and sound warnings "
                    f"({len(phonology.module_result.warnings)})"
                ):
                    for warning in phonology.module_result.warnings:
                        if warning.severity.value == "information":
                            st.info(warning.message)
                        else:
                            st.warning(warning.message)

            with st.expander("Rhyme and sound calculation provenance"):
                provenance = phonology.module_result.provenance
                st.write(
                    f"**Module:** {phonology.module_result.module_name} "
                    f"{phonology.module_result.module_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Pronunciation configuration:** "
                    f"`{phonology.pronunciation_configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )

    with vad_tab:
        visible_vad_views = set()
        if show_all_matched:
            visible_vad_views.add("All matched tokens")
        if show_stopword_excluded:
            visible_vad_views.add("Stopwords excluded")
        vad = [
            row
            for row in vad_views(workspace)
            if row.analysis_view in visible_vad_views
        ]
        if not vad:
            if not visible_vad_views:
                st.info("Enable at least one stopword-reporting view in the settings above.")
            else:
                st.info("No VAD lexicon was selected. Choose Warriner or either NRC VAD source to see this view.")
        else:
            st.subheader("Parallel Normalized VAD Views")
            st.write(
                "These means use a derived 0–1 scale so the three VAD sources can be "
                "placed side by side. Higher values mean higher normative ratings on "
                "that dimension among matched observations—not more emotion in the poem."
            )
            vad_frame = _frame(
                vad,
                {
                    "lexicon": "Lexicon",
                    "analysis_view": "Analysis view",
                    "matched_observations": "Matched observations",
                    "matched_types": "Matched types",
                    "eligible_tokens": "Eligible tokens",
                    "lexical_coverage": "Coverage",
                    "normalized_valence": "Valence",
                    "normalized_arousal": "Arousal",
                    "normalized_dominance": "Dominance",
                    "type_valence": "Type valence",
                    "type_arousal": "Type arousal",
                    "type_dominance": "Type dominance",
                    "original_scale": "Original scale",
                    "normalization_formula": "Formula",
                },
            )
            render_dataframe(
                vad_frame[
                    [
                        "Lexicon",
                        "Analysis view",
                        "Matched observations",
                        "Matched types",
                        "Eligible tokens",
                        "Coverage",
                        "Valence",
                        "Arousal",
                        "Dominance",
                    ]
                ].style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Valence": lambda value: _decimal(value),
                        "Arousal": lambda value: _decimal(value),
                        "Dominance": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            dimension_order = ["Valence", "Arousal", "Dominance"]
            vad_frame["Lexicon and view"] = (
                vad_frame["Lexicon"] + " · " + vad_frame["Analysis view"]
            )
            lexicon_order = vad_frame["Lexicon and view"].tolist()
            chart_data = vad_frame[
                ["Lexicon", "Analysis view", "Lexicon and view", *dimension_order]
            ].melt(
                id_vars=["Lexicon", "Analysis view", "Lexicon and view"],
                var_name="Dimension",
                value_name="Normalized mean",
            )
            chart = (
                alt.Chart(chart_data)
                .mark_bar(size=12)
                .encode(
                    x=alt.X(
                        "Normalized mean:Q",
                        scale=alt.Scale(domain=[0, 1]),
                        title="Derived normalized mean (0–1)",
                    ),
                    y=alt.Y("Lexicon and view:N", sort=lexicon_order, title=None),
                    yOffset=alt.YOffset("Dimension:N", sort=dimension_order),
                    color=alt.Color(
                        "Dimension:N",
                        sort=dimension_order,
                        scale=alt.Scale(
                            range=[
                                PUBLICATION_CHART_COLORS[0],
                                PUBLICATION_CHART_COLORS[1],
                                PUBLICATION_CHART_COLORS[2],
                            ]
                        ),
                        title=None,
                    ),
                    tooltip=[
                        alt.Tooltip("Lexicon:N"),
                        alt.Tooltip("Analysis view:N"),
                        alt.Tooltip("Dimension:N"),
                        alt.Tooltip("Normalized mean:Q", format=".3f"),
                    ],
                )
                .properties(height=max(210, 80 * len(vad)))
            )
            st.altair_chart(publication_chart(chart), width="stretch")
            st.caption(
                "All three dimensions are normative lexical ratings. They do not identify "
                "the poem's emotion or predict an individual reader's response."
            )
            st.subheader("What Valence, Arousal, and Dominance Mean")
            definition_columns = st.columns(3)
            for column, dimension in zip(
                definition_columns,
                ("valence", "arousal", "dominance"),
                strict=True,
            ):
                with column:
                    st.markdown(f"**{dimension.title()}**")
                    st.write(VAD_DEFINITIONS[dimension])

            interpretations = [
                row
                for row in vad_interpretation_views(workspace)
                if row.analysis_view in visible_vad_views
            ]
            interpretation_lexicon = st.selectbox(
                "Explain results from",
                options=list(dict.fromkeys(row.lexicon for row in vad)),
                key="interpretation_lexicon",
            )
            for explanation in interpretations:
                if explanation.lexicon == interpretation_lexicon:
                    st.markdown(
                        f"**{explanation.analysis_view} · "
                        f"{explanation.dimension.title()}:** {explanation.explanation}"
                    )

            dispersion_rows = []
            for result in workspace.results:
                summary = result.vad_summary
                if summary is None:
                    continue
                groups = (
                    (
                        "All matched tokens",
                        "Token-weighted",
                        summary.token_weighted_normalized,
                    ),
                    (
                        "All matched tokens",
                        "Type-weighted",
                        summary.type_weighted_normalized,
                    ),
                    (
                        "Stopwords excluded",
                        "Token-weighted",
                        summary.stopword_excluded_token_weighted_normalized,
                    ),
                    (
                        "Stopwords excluded",
                        "Type-weighted",
                        summary.stopword_excluded_type_weighted_normalized,
                    ),
                )
                for analysis_view, weighting, group in groups:
                    if group is None or analysis_view not in visible_vad_views:
                        continue
                    for dimension, statistics in group.by_dimension().items():
                        dispersion_rows.append(
                            {
                                "Lexicon": result.lexicon_metadata.display_name,
                                "Analysis view": analysis_view,
                                "Weighting": weighting,
                                "Dimension": dimension.title(),
                                "Count": statistics.count,
                                "Population standard deviation": (
                                    statistics.population_standard_deviation
                                ),
                            }
                        )
            st.subheader("Dispersion of Matched Ratings")
            st.write(
                "Population standard deviation describes how widely the matched "
                "lexicon ratings vary around their mean. It is not the source "
                "lexicon's rater-level uncertainty."
            )
            render_dataframe(
                pd.DataFrame(dispersion_rows).style.format(
                    {"Population standard deviation": lambda value: _decimal(value)}
                ),
                hide_index=True,
                width="stretch",
            )

            st.subheader("Repetition-Sensitive and Vocabulary-Sensitive Means")
            st.write(
                "Token-weighted means count every included occurrence, so repetition matters. "
                "Type-weighted means count each distinct matched lexicon entry once, so they "
                "describe the breadth of the matched vocabulary. Both use the same 0–1 display scale."
            )
            weighting_details = []
            for row in vad:
                weighting_details.extend(
                    (
                        {
                            "Lexicon": row.lexicon,
                            "Analysis view": row.analysis_view,
                            "Weighting": "Token-weighted",
                            "Valence": row.normalized_valence,
                            "Arousal": row.normalized_arousal,
                            "Dominance": row.normalized_dominance,
                        },
                        {
                            "Lexicon": row.lexicon,
                            "Analysis view": row.analysis_view,
                            "Weighting": "Type-weighted",
                            "Valence": row.type_valence,
                            "Arousal": row.type_arousal,
                            "Dominance": row.type_dominance,
                        },
                    )
                )
            render_dataframe(
                pd.DataFrame(weighting_details).style.format(
                    {dimension: lambda value: _decimal(value) for dimension in dimension_order}
                ),
                hide_index=True,
                width="stretch",
            )

            st.subheader("Stopword Sensitivity")
            st.write(
                "Stopword sensitivity is the stopword-excluded mean minus the "
                "all-matched mean. A large absolute difference indicates that common "
                "grammatical words materially influence the aggregate; it does not "
                "make either view more accurate."
            )
            sensitivity_frame = _frame(
                vad_sensitivity_views(workspace),
                {
                    "lexicon": "Lexicon",
                    "weighting": "Weighting",
                    "dimension": "Dimension",
                    "all_matched_mean": "All matched tokens",
                    "stopwords_excluded_mean": "Stopwords excluded",
                    "difference": "Difference",
                },
            )
            sensitivity_frame["Dimension"] = sensitivity_frame["Dimension"].str.title()
            render_dataframe(
                sensitivity_frame.style.format(
                    {
                        "All matched tokens": lambda value: _decimal(value),
                        "Stopwords excluded": lambda value: _decimal(value),
                        "Difference": lambda value: (
                            "—" if pd.isna(value) else f"{value:+.3f}"
                        ),
                    }
                ),
                hide_index=True,
                width="stretch",
            )

            st.subheader("Cumulative Normative Lexical Load")
            st.write(
                "These token totals are deliberately sensitive to length and repetition. "
                "The absolute midpoint load sums each matched rating's distance from 0.5; "
                "above and below loads preserve direction, while net load lets them offset. "
                "This reports encountered lexical evidence—not a measured load on a reader."
            )
            cumulative = [
                row
                for row in vad_cumulative_views(workspace)
                if row.analysis_view in visible_vad_views
            ]
            cumulative_frame = _frame(
                cumulative,
                {
                    "lexicon": "Lexicon",
                    "analysis_view": "Analysis view",
                    "dimension": "Dimension",
                    "matched_observations": "Matched observations",
                    "lexical_coverage": "Coverage",
                    "rating_total": "Rating total",
                    "above_midpoint_deviation": "Above-midpoint load",
                    "below_midpoint_deviation": "Below-midpoint load",
                    "net_midpoint_deviation": "Net midpoint load",
                    "absolute_midpoint_deviation": "Absolute midpoint load",
                },
            )
            cumulative_frame["Dimension"] = cumulative_frame["Dimension"].str.title()
            render_dataframe(
                cumulative_frame[
                    [
                        "Lexicon",
                        "Analysis view",
                        "Dimension",
                        "Matched observations",
                        "Coverage",
                        "Rating total",
                        "Above-midpoint load",
                        "Below-midpoint load",
                        "Net midpoint load",
                        "Absolute midpoint load",
                    ]
                ].style.format(
                    {
                        "Coverage": lambda value: _percentage(value),
                        "Rating total": "{:.3f}",
                        "Above-midpoint load": "{:.3f}",
                        "Below-midpoint load": "{:.3f}",
                        "Net midpoint load": "{:.3f}",
                        "Absolute midpoint load": "{:.3f}",
                    }
                ),
                hide_index=True,
                width="stretch",
            )

            st.subheader("Top Contributors to Each Mean")
            st.write(
                "Signed contribution is frequency × (normalized rating − 0.5). "
                "This midpoint-centered calculation shows how repetition and distance "
                "from the midpoint combine. For arousal and dominance, read the sign "
                "as weighted deviation rather than positive or negative emotion."
            )
            contributor_view = st.selectbox(
                "Contributor analysis view",
                options=sorted(visible_vad_views),
                key="contributor_analysis_view",
            )
            contributor_dimension = st.selectbox(
                "Contributor dimension",
                options=["valence", "arousal", "dominance"],
                format_func=str.title,
                key="contributor_dimension",
            )
            contributors = [
                row
                for row in vad_contributor_views(workspace)
                if row.dimension == contributor_dimension
                and row.analysis_view == contributor_view
            ]
            contributor_frame = _frame(
                contributors,
                {
                    "lexicon": "Lexicon",
                    "analysis_view": "Analysis view",
                    "term": "Matched entry",
                    "surface_forms": "Surface forms",
                    "observations": "Occurrences",
                    "normalized_rating": "Normalized rating",
                    "midpoint_deviation_per_occurrence": "Deviation per occurrence",
                    "signed_contribution": "Signed contribution",
                    "absolute_contribution": "Absolute contribution",
                    "direction": "Direction",
                    "stopword_status": "Stopword status",
                    "example_surface": "Example surface",
                    "example_line": "Line",
                    "match_method": "Method",
                },
            )
            if contributor_frame.empty:
                st.info("No contributor ranking is available for this dimension.")
            else:
                render_dataframe(
                    contributor_frame[
                        [
                            "Lexicon",
                            "Analysis view",
                            "Matched entry",
                            "Surface forms",
                            "Occurrences",
                            "Normalized rating",
                            "Deviation per occurrence",
                            "Signed contribution",
                            "Absolute contribution",
                            "Direction",
                            "Stopword status",
                            "Example surface",
                            "Line",
                            "Method",
                        ]
                    ].style.format(
                        {
                            "Normalized rating": "{:.3f}",
                            "Deviation per occurrence": "{:+.3f}",
                            "Signed contribution": "{:+.3f}",
                            "Absolute contribution": "{:.3f}",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

            with st.expander("Original source scales and normalization formulas"):
                st.markdown(
                    "**Normalization formulas:** Warriner `(x − 1) / 8`; NRC VAD v1 "
                    "identity; NRC VAD v2.1 `(x + 1) / 2`. Original values are never overwritten."
                )
                details = []
                result_by_id = {
                    result.lexicon_metadata.lexicon_id: result for result in workspace.results
                }
                for row in vad:
                    result = result_by_id[row.lexicon_id]
                    summary = result.vad_summary
                    assert summary is not None
                    original = (
                        summary.token_weighted_original
                        if row.analysis_view == "All matched tokens"
                        else summary.stopword_excluded_token_weighted_original
                    )
                    if original is None:
                        continue
                    details.append(
                        {
                            "Lexicon": row.lexicon,
                            "Analysis view": row.analysis_view,
                            "Original scale": row.original_scale,
                            "Source valence mean": original.valence.mean,
                            "Source arousal mean": original.arousal.mean,
                            "Source dominance mean": original.dominance.mean,
                            "Formula": row.normalization_formula,
                        }
                    )
                render_dataframe(details, hide_index=True, width="stretch")

    with emotion_tab:
        associations = emotion_association_views(workspace)
        sentiments = sentiment_association_views(workspace)
        intensities = emotion_intensity_views(workspace)
        if not associations and not sentiments and not intensities:
            st.info(
                "NRC Emotion or NRC Emotion Intensity was not selected. "
                "The resource-free VADER polarity evidence remains available below."
            )
        vader = workspace.vader_sentiment
        if vader is not None:
            st.subheader("VADER Rule-Based Sentiment")
            st.write(
                "VADER reports raw positive, neutral, and negative lexical-polarity "
                "proportions plus a rule-adjusted compound score from -1 to +1. "
                "Its conventional threshold label is descriptive polarity evidence, "
                "not a declaration of the poem's emotion."
            )
            score = vader.document_score
            vader_columns = st.columns(4)
            vader_columns[0].metric(
                "Positive proportion",
                _percentage(score.positive_proportion),
            )
            vader_columns[1].metric(
                "Neutral proportion",
                _percentage(score.neutral_proportion),
            )
            vader_columns[2].metric(
                "Negative proportion",
                _percentage(score.negative_proportion),
            )
            vader_columns[3].metric(
                "Compound score",
                f"{score.compound_score:+.3f}",
            )
            st.caption(
                f"Conventional threshold label: {score.threshold_label.title()} "
                f"(positive >= {vader.configuration.positive_minimum:+.2f}; "
                f"negative <= {vader.configuration.negative_maximum:+.2f}). "
                "The three proportions are raw lexical-category ratios; compound "
                "also applies VADER's negation, intensity, punctuation, casing, "
                "and contrast rules."
            )
            st.subheader(
                "Sentence-Level VADER Scores "
                f"({len(vader.sentence_scores):,})"
            )
            st.caption(
                "Each model-segmented sentence is scored separately and shown "
                "below. VADER scores the complete preserved text directly for "
                "the document compound; it does not average these sentence "
                "compound scores to produce that value."
            )
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Sentence": item.ordinal,
                            "Lines": " | ".join(
                                str(value) for value in item.line_numbers
                            ),
                            "Text": item.source_text,
                            "Positive": item.score.positive_proportion,
                            "Neutral": item.score.neutral_proportion,
                            "Negative": item.score.negative_proportion,
                            "Compound": item.score.compound_score,
                            "Threshold label": (
                                item.score.threshold_label.title()
                            ),
                        }
                        for item in vader.sentence_scores
                    ]
                ).style.format(
                    {
                        "Positive": lambda value: _percentage(value),
                        "Neutral": lambda value: _percentage(value),
                        "Negative": lambda value: _percentage(value),
                        "Compound": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
                height=320,
            )
            with st.expander("VADER Cautions, Method, and Citation"):
                for warning in vader.module_result.warnings:
                    if warning.severity.value == "information":
                        st.info(warning.message)
                    else:
                        st.warning(warning.message)
                st.write(f"**Citation:** {vader.citation}")
                provenance = vader.module_result.provenance
                st.write(
                    f"**Package:** vaderSentiment {vader.package_version}  \n"
                    f"**Configuration:** `{provenance.configuration_id}`  \n"
                    f"**Lookup policy:** {provenance.lookup_policy}  \n"
                    f"**Inclusion policy:** {provenance.inclusion_policy}"
                )
            if associations or sentiments or intensities:
                st.divider()
        if associations:
            st.subheader("Eight Emotion Associations")
            st.write(
                "This counts vocabulary associated with anger, anticipation, disgust, "
                "fear, joy, sadness, surprise, and trust in NRC Emotion. One token may "
                "belong to several categories, so rates do not sum to 100%."
            )
            association_frame = _frame(
                associations,
                {
                    "category": "Category",
                    "token_count": "Token count",
                    "unique_types": "Unique types",
                    "rate_per_lexical_token": "Rate per lexical token",
                    "rate_among_emotion_bearing_tokens": "Rate among emotion-bearing tokens",
                    "top_terms": "Top contributors",
                },
            )
            st.bar_chart(
                association_frame.set_index("Category")[["Rate per lexical token"]],
                height=300,
            )
            render_dataframe(
                association_frame.style.format(
                    {
                        "Rate per lexical token": lambda value: _percentage(value),
                        "Rate among emotion-bearing tokens": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if sentiments:
            st.subheader("Positive and Negative Sentiment Associations")
            st.write(
                "Positive and negative are broad sentiment labels, so VerseVAD reports "
                "them separately from the eight emotion categories. One token may have "
                "more than one source association, and these rates need not sum to 100%."
            )
            sentiment_frame = _frame(
                sentiments,
                {
                    "category": "Sentiment",
                    "token_count": "Token count",
                    "unique_types": "Unique types",
                    "rate_per_lexical_token": "Rate per lexical token",
                    "rate_among_emotion_bearing_tokens": "Rate among association-bearing tokens",
                    "top_terms": "Top contributors",
                },
            )
            st.bar_chart(
                sentiment_frame.set_index("Sentiment")[["Rate per lexical token"]],
                height=220,
            )
            render_dataframe(
                sentiment_frame.style.format(
                    {
                        "Rate per lexical token": lambda value: _percentage(value),
                        "Rate among association-bearing tokens": lambda value: _percentage(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if intensities:
            st.subheader("Emotion Intensity Among Supplied Matches")
            st.write(
                "Prevalence asks how often category-scored vocabulary occurs. Mean "
                "intensity asks how strong the supplied ratings are only among those matches."
            )
            intensity_frame = _frame(
                intensities,
                {
                    "category": "Category",
                    "token_count": "Matched occurrences",
                    "distinct_pairs": "Distinct word-category pairs",
                    "prevalence_per_lexical_token": "Prevalence per lexical token",
                    "mean_matched_intensity": "Mean matched intensity",
                    "median_matched_intensity": "Median",
                    "maximum_matched_intensity": "Maximum",
                    "top_terms": "Top contributors",
                },
            )
            render_dataframe(
                intensity_frame.style.format(
                    {
                        "Prevalence per lexical token": lambda value: _percentage(value),
                        "Mean matched intensity": lambda value: _decimal(value),
                        "Median": lambda value: _decimal(value),
                        "Maximum": lambda value: _decimal(value),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption("A missing word-category pair remains missing; VerseVAD does not enter a zero.")

    with evidence_tab:
        st.subheader("Match Evidence")
        st.write(
            "Use this table when you want to know exactly which surface form, lemma, "
            "phrase, or source entry contributed—or why it was suppressed."
        )
        if workspace.performance is not None:
            with st.expander("Performance and cache diagnostics"):
                performance = workspace.performance
                st.metric(
                    "Analysis wall time",
                    f"{performance.total_ms:,.1f} ms",
                )
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Operation": item.module,
                                "Status": item.status,
                                "Cache": item.cache_status,
                                "Cache reason": item.cache_reason,
                                "Processing ms": item.processing_ms,
                                "Total ms": item.total_ms,
                            }
                            for item in performance.operations
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Cache": item.name,
                                "Entries": item.entry_count,
                                "Maximum entries": item.max_entries,
                                "Approximate shallow bytes": (
                                    item.approximate_size_bytes
                                ),
                                "Hits": item.hits,
                                "Misses": item.misses,
                                "Evictions": item.evictions,
                                "Discarded invalid entries": (
                                    item.corruptions
                                ),
                            }
                            for item in performance.caches
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(performance.note)
        evidence_signature = (
            workspace.document.text_version_id
            + "|"
            + "|".join(result.analysis_id for result in workspace.results)
        )
        evidence_is_loaded = (
            st.session_state.get("loaded_evidence_signature")
            == evidence_signature
        )
        if st.button(
            (
                "Refresh match evidence"
                if evidence_is_loaded
                else "Load match evidence"
            ),
            key="load_match_evidence",
            help=(
                "Builds large match and unmatched tables only when requested, "
                "then retains them for unchanged results."
            ),
        ):
            st.session_state["loaded_evidence_signature"] = evidence_signature
            evidence_is_loaded = True
        if not evidence_is_loaded:
            st.info(
                "Detailed match and unmatched tables are deferred so hidden "
                "report tabs remain responsive. Load them when you need the "
                "token-level audit."
            )
        all_matches = (
            match_views(workspace) if evidence_is_loaded else ()
        )
        lexicon_filter = st.selectbox(
            "Filter by lexicon",
            options=["All lexicons", *sorted({row.lexicon for row in all_matches})],
            key="evidence_lexicon_filter",
        )
        status_options = sorted({row.status for row in all_matches})
        status_filter = st.multiselect(
            "Match status",
            options=status_options,
            default=["included"] if "included" in status_options else [],
            key="evidence_status_filter",
        )
        stopword_filter = st.multiselect(
            "Stopword status",
            options=sorted({row.stopword_status for row in all_matches}),
            default=sorted({row.stopword_status for row in all_matches}),
            key="evidence_stopword_filter",
        )
        only_excluded_stopwords = st.checkbox(
            "Show only matched observations excluded from the stopword-filtered view",
            value=False,
            key="evidence_only_excluded_stopwords",
        )
        search = st.text_input(
            "Search surface form, matched term, lemma, or context",
            key="evidence_search",
        ).casefold()
        filtered = [
            row
            for row in all_matches
            if (lexicon_filter == "All lexicons" or row.lexicon == lexicon_filter)
            and row.status in status_filter
            and row.stopword_status in stopword_filter
            and (
                not only_excluded_stopwords
                or (row.included_in_full and not row.included_in_filtered)
            )
            and (
                not search
                or search
                in " ".join((row.surface, row.matched_term, row.lemma, row.context)).casefold()
            )
        ]
        match_frame = _frame(
            filtered,
            {
                "lexicon": "Lexicon",
                "surface": "Text surface",
                "normalized": "Normalized form",
                "line": "Line",
                "stanza": "Stanza",
                "pos": "POS",
                "lemma": "Lemma",
                "matched_term": "Matched entry",
                "method": "Method",
                "status": "Status",
                "value": "Source evidence",
                "context": "Line context",
                "explanation": "Why",
                "stopword_status": "Stopword status",
                "included_in_full": "Included in full",
                "included_in_filtered": "Included in filtered",
                "stopword_exclusion_reason": "Stopword decision",
            },
        )
        render_dataframe(match_frame, hide_index=True, width="stretch", height=420)
        st.caption(f"Showing {len(filtered):,} of {len(all_matches):,} audit records.")

        st.subheader("Unmatched Vocabulary")
        unmatched = (
            unmatched_views(workspace) if evidence_is_loaded else ()
        )
        if unmatched:
            unmatched_frame = _frame(
                unmatched,
                {
                    "lexicon": "Lexicon",
                    "surface": "Surface form",
                    "frequency": "Occurrences",
                    "pos": "POS",
                    "proposed_lemma": "Model lemma",
                    "example_line": "Example line",
                    "example_context": "Example context",
                },
            )
            render_dataframe(unmatched_frame, hide_index=True, width="stretch", height=320)
            st.caption(
                "A model lemma is proposed processing evidence, not an approved historical or scholarly mapping."
            )
        elif workspace.results and evidence_is_loaded:
            st.success("Every lexical token matched each selected lexicon under this policy.")
        elif evidence_is_loaded:
            st.info(
                "No affective lexicon was selected. Optional-module matching is "
                "available in the Concreteness, Frequency & Rarity, or Age of "
                "Acquisition tabs, or in the Pronunciation & Prosody and "
                "Meter & Rhythm or Rhyme & Sound audits and downloads."
            )

    with download_tab:
        st.subheader("Readable First, Audit Trail Second")
        st.write(
            "The compact summary is meant to be opened first. The ZIP adds every "
            "detailed table needed to inspect or reproduce the result."
        )
        safe_stem = "".join(
            character if character.isalnum() or character in {"-", "_"} else "_"
            for character in workspace.document.title.strip()
        ).strip("_") or "versevad_analysis"
        export_signature = hashlib.sha256(
            (
                workspace.document.text_version_id
                + workspace.comparison.comparison_id
                + "|".join(
                    result.analysis_id for result in workspace.results
                )
                + "|".join(
                    (
                        (
                            workspace.vader_sentiment.module_result.result_id
                            if workspace.vader_sentiment
                            else ""
                        ),
                        (
                            workspace.readability.module_result.result_id
                            if workspace.readability
                            else ""
                        ),
                        (
                            workspace.concreteness.module_result.result_id
                            if workspace.concreteness
                            else ""
                        ),
                        (
                            workspace.frequency.module_result.result_id
                            if workspace.frequency
                            else ""
                        ),
                        (
                            workspace.aoa.module_result.result_id
                            if workspace.aoa
                            else ""
                        ),
                        (
                            workspace.pronunciation.module_result.result_id
                            if workspace.pronunciation
                            else ""
                        ),
                        (
                            workspace.meter.module_result.result_id
                            if workspace.meter
                            else ""
                        ),
                        (
                            workspace.phonology.module_result.result_id
                            if workspace.phonology
                            else ""
                        ),
                        (
                            workspace.lexical_style.module_result.result_id
                            if workspace.lexical_style
                            else ""
                        ),
                        (
                            workspace.poetry_id.module_result.result_id
                            if workspace.poetry_id
                            else ""
                        ),
                        (
                            workspace.inherited_form.module_result.result_id
                            if workspace.inherited_form
                            else ""
                        ),
                    )
                )
            ).encode("utf-8")
        ).hexdigest()
        prepared_exports = st.session_state.get("prepared_workspace_exports")
        if st.button(
            "Prepare downloads",
            type="primary",
            key="prepare_workspace_exports",
            help=(
                "Builds export bytes only when requested. Repeated preparation "
                "of the unchanged analysis uses the bounded export cache."
            ),
        ):
            with st.spinner("Preparing complete local exports..."):
                audit_bundle = detailed_export_zip(
                    workspace,
                    use_cache=st.session_state.get(
                        "analysis_cache_enabled",
                        True,
                    ),
                )
                with zipfile.ZipFile(io.BytesIO(audit_bundle)) as archive:
                    narrative_report = archive.read(
                        "VerseVAD_analysis_report.docx"
                    )
                prepared_exports = {
                    "signature": export_signature,
                    "summary": scholar_summary_csv(workspace),
                    "guide": csv_reading_guide(),
                    "report": narrative_report,
                    "bundle": audit_bundle,
                }
                st.session_state["prepared_workspace_exports"] = (
                    prepared_exports
                )
        if (
            prepared_exports
            and prepared_exports.get("signature") == export_signature
        ):
            column1, column2, column3, column4 = st.columns(4)
            column1.download_button(
                "Download readable summary",
                data=prepared_exports["summary"],
                file_name=f"{safe_stem}_scholar_summary.csv",
                mime="text/csv",
                width="stretch",
                key="download_summary",
            )
            column2.download_button(
                "Download CSV reading guide",
                data=prepared_exports["guide"],
                file_name="VerseVAD_CSV_reading_guide.csv",
                mime="text/csv",
                width="stretch",
                key="download_guide",
            )
            column3.download_button(
                "Download narrative report",
                data=prepared_exports["report"],
                file_name=f"{safe_stem}_VerseVAD_report.docx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                width="stretch",
                key="download_narrative_report",
            )
            column4.download_button(
                "Download full audit bundle",
                data=prepared_exports["bundle"],
                file_name=f"{safe_stem}_VerseVAD_audit.zip",
                mime="application/zip",
                width="stretch",
                key="download_bundle",
            )
        else:
            st.caption(
                "Downloads are generated on demand so hidden tabs do not rebuild "
                "large audit bundles during ordinary interface interactions."
            )
        st.info(
            "The full bundle contains the narrative Word report, readable CSV "
            "summary and guide, shared processing CSVs, and complete module CSV "
            "audit tables. Each selected optional module also includes its own "
            "narrative Word report. ZIP is used only to keep the related CSV and "
            "DOCX files together; VerseVAD no longer generates JSON, TXT, or XLSX "
            "analysis exports."
        )

    with help_tab:
        st.subheader("A Practical Reading Order")
        st.markdown(
            """
            1. **Coverage:** Is enough vocabulary represented to make the aggregate useful?
            2. **Concreteness:** Read the source 1-5 distribution with both coverage denominators and configured bands.
            3. **Frequency:** Read median SUBTLEX-US Zipf with its named corpus and matched coverage.
            4. **Age of Acquisition:** Read source means in years, response evidence, configured bands, and the non-diagnostic warning.
            5. **Lexical Style:** Check token/type denominators and parameters before reading MATTR, HD-D, MTLD, word lengths, and structural word counts.
            6. **Pronunciation & Prosody:** Read exact observed-form coverage, unresolved alternatives, complete-line syllables, and lexical stress; do not treat this as meter or performed scansion.
            7. **Meter & Rhythm:** Read the nearest fixed template with fit, coverage, alternatives, and deviations; treat it as candidate evidence, not definitive scansion.
            8. **Rhyme & Sound:** Read the exact-rhyme scheme with ending coverage, then inspect separately labeled slant, eye, internal-rhyme, refrain, and recurring-sound evidence.
            9. **Normalized VAD:** Compare source-specific 0–1 means, keeping coverage beside them.
            10. **Emotion associations:** Read category rates as overlapping lexical associations.
            11. **Emotion intensity:** Keep prevalence separate from mean intensity among matches.
            12. **Evidence:** Inspect the terms, lemmas, phrases, and suppressions producing a pattern.
            13. **Manifest:** Use this only when you need provenance or reproducibility details.
            """
        )
        st.info(
            "When Frequency & Rarity is selected, read median SUBTLEX-US Zipf "
            "after coverage and concreteness, then inspect configured bands and "
            "the rare-word audit before moving to VAD."
        )
        st.subheader("What the Main Terms Mean")
        definitions = [
            ("Coverage", "The share of eligible lexical tokens that found a source entry."),
            ("Token-weighted", "Every matched occurrence contributes, including repetitions."),
            ("Type-weighted", "Each distinct matched lexicon entry contributes once."),
            ("Work-weighted corpus", "Each eligible work contributes one work-level mean regardless of length."),
            ("Cumulative lexical load", "A length-sensitive sum of matched normative ratings or midpoint deviations."),
            ("Normalized VAD", "A derived 0-1 version used for legitimate side-by-side VAD comparison."),
            ("Normative lexical concreteness", "A matched source rating from 1 (very abstract or language-based) to 5 (very concrete or experience-based)."),
            ("Rated-token coverage", "The share of eligible lexical token occurrences assigned a source rating; missing tokens stay missing."),
            ("Rated unique-word coverage", "The share of unique normalized observed surface forms assigned a source rating."),
            ("SUBTLEX-US Zipf frequency", "A logarithmic, corpus-relative word-form frequency value; one point is roughly a tenfold frequency difference."),
            ("Matched frequency coverage", "The share of eligible token occurrences or observed surface types that found a SUBTLEX-US entry; unmatched values stay missing."),
            ("Normative lexical AoA", "A matched retrospective source mean, in years, for when respondents believed they learned a word; it is not grade level or difficulty."),
            ("AoA source SD", "Variation among source respondents for one word, kept distinct from variation among the poem's matched normative means."),
            ("Content words only", "An optional frequency or AoA scope limited to model-tagged NOUN, VERB, ADJ, and ADV; it is off by default."),
            ("MATTR", "The mean surface-form type-token ratio across every overlapping fixed-length token window."),
            ("HD-D", "The expected proportion of distinct surface types in a configured without-replacement token sample."),
            ("MTLD", "The mean forward/reverse token-sequence length that maintains a configured type-token-ratio threshold."),
            ("Lexical-style word unit", "One shared-preprocessing lexical token; punctuation and numeric tokens are excluded."),
            ("Alphabetic word length", "The number of Unicode alphabetic characters in one included lexical-token surface."),
            ("Dictionary pronunciation coverage", "The share of eligible lexical token occurrences whose exact observed form has one CMUdict pronunciation, prosodically agreeing alternatives, or an explicit poem-specific scholar override."),
            ("Lexical stress digits", "CMUdict/ARPAbet marks 0 for unstressed, 1 for primary lexical stress, and 2 for secondary lexical stress; this is not a metrical scansion."),
            ("Complete pronunciation line", "A physical line in which every eligible lexical token has resolved syllable and lexical-stress evidence; incomplete line totals remain missing."),
            ("Scholar pronunciation override", "A poem-specific, reversible ARPAbet pronunciation plus a required note, kept distinct from every dictionary candidate."),
            ("Association", "A binary category link; it is not an intensity or contextual interpretation."),
            ("Intensity", "A source rating for a supplied word-category pair; missing pairs stay missing."),
            ("Suppressed component", "A visible unigram candidate not counted because a preferred phrase was selected."),
            ("Lemma fallback", "A model-proposed base form used only after exact matching fails."),
        ]
        render_dataframe(
            pd.DataFrame(definitions, columns=["Term", "Meaning"]),
            hide_index=True,
            width="stretch",
        )
        st.warning(
            "Lexicon matching does not resolve negation, irony, metaphor, voice, "
            "historical sense, authorial intention, or reader response."
        )
