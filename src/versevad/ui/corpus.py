"""Streamlit project and corpus workspace backed by local SQLite storage."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict

import altair as alt
import pandas as pd
import streamlit as st

from versevad.application import (
    LEXICON_SPECS,
    RESOURCE_ROOT,
    ResourceReadiness,
    TextImportError,
    WorkspaceAnalysisError,
    detailed_part_of_speech_views_for_tokens,
    load_lexicon,
    part_of_speech_views_for_tokens,
)
from versevad.exports.corpus_csv import build_corpus_export_bundle
from versevad.corpus import (
    CorpusAnalysisConfiguration,
    analyze_corpus,
    corpus_module_category_profiles,
    corpus_module_profiles,
    corpus_scenario_deltas,
    corpus_vad_profiles,
    corpus_vad_work_comparisons,
    decode_corpus_files,
)
from versevad.db import SCHEMA_VERSION, ProjectRepository, default_database_path
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.concreteness import ConcretenessConfiguration
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.lexical_semantic.sensorimotor import SensorimotorConfiguration
from versevad.models import PhrasePolicy, ReviewAction, ReviewScope, TextDocument
from versevad.module_capabilities import fixed_profile_notice
from versevad.normalization import normalize_lookup
from versevad.preprocessing import TextPreprocessor
from versevad.prosody import (
    MeterAnalysisMode,
    MeterConfiguration,
    MeterInterpretationDepth,
    MeterStyleProfile,
    parse_meter_scholar_revisions,
)
from versevad.poetry_id import (
    ARCHETYPE_BY_ID,
    SUPPORTED_VAD_LEXICON_IDS,
    PoetryIDConfiguration,
    ThresholdBand,
    ThresholdProfile,
    VadLevel,
)
from versevad.inherited_form import InheritedFormConfiguration
from versevad.ui.dataframes import (
    heterogeneous_display_value,
    rounded_display_data,
)
from versevad.ui.design import (
    METER_DEPTH_LABELS,
    METER_MODE_LABELS,
    METER_STYLE_LABELS,
    MODULE_PRESETS,
    bottom_collapsible_expander,
    preset_widget_state,
    render_dataframe,
    render_empty_state,
    publication_chart,
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
    normalize_profile_settings,
    snapshot_profile_settings,
)
from versevad.ui.stopwords import render_stopword_settings
from versevad.analysis_profiles import LexicalScope, ProfileSelection
from versevad.ui.profile_controls import (
    render_report_profile_controls,
    report_profile_state,
)
from versevad.ui.module_scope_overrides import (
    active_override_modules,
    render_content_word_scope_override,
)
from versevad.report_profile_overrides import (
    corpus_metric_module_id,
    selection_for_module,
)
from versevad.versemap import (
    MODEL_FILENAME,
    POET_PROFILE_FILENAME,
    PROFILE_FILENAME,
    VerseMapConfiguration,
    load_reference_index,
)


_CORPUS_PROFILE_INCLUDE_TO_MODULE = {
    "include_concreteness": "concreteness",
    "include_frequency": "frequency",
    "include_aoa": "aoa",
    "include_sensorimotor": "sensorimotor",
    "include_pronunciation": "pronunciation",
    "include_meter": "meter",
    "include_phonology": "phonology",
    "include_lexical_style": "lexical_style",
    "include_poetry_id": "poetry_id",
    "include_inherited_form": "inherited_form",
    "include_versemap": "versemap",
}

_VAD_LOAD_METRICS = {
    "vad_rating_total",
    "vad_above_midpoint_load",
    "vad_below_midpoint_load",
    "vad_net_midpoint_load",
    "vad_absolute_midpoint_load",
    "vad_above_midpoint_load_per_observation",
    "vad_below_midpoint_load_per_observation",
    "vad_net_midpoint_load_per_observation",
    "vad_absolute_midpoint_load_per_observation",
    "vad_above_midpoint_load_per_100_observations",
    "vad_below_midpoint_load_per_100_observations",
    "vad_net_midpoint_load_per_100_observations",
    "vad_absolute_midpoint_load_per_100_observations",
}
_VAD_VOLATILITY_METRICS = {"vad_average_deviation_from_poem_mean"}


def _corpus_profile_setting_keys(project_id: str) -> dict[str, str]:
    prefix = f"corpus_{project_id}"
    return {
        "phrase_policy_label": f"corpus_policy_{project_id}",
        "minimum_matches": f"corpus_minimum_{project_id}",
        "concreteness_exclude_proper": (
            f"corpus_concreteness_exclude_proper_{project_id}"
        ),
        "sensorimotor_exclude_proper": (
            f"corpus_sensorimotor_exclude_proper_{project_id}"
        ),
        "frequency_exclude_proper": (
            f"corpus_frequency_exclude_proper_{project_id}"
        ),
        "aoa_exclude_proper": f"corpus_aoa_exclude_proper_{project_id}",
        "poetry_id_sources": f"corpus_poetry_id_sources_{project_id}",
        "poetry_id_lexical_dimensions": (
            f"corpus_poetry_id_character_{project_id}"
        ),
        "poetry_id_custom_thresholds": (
            f"corpus_poetry_id_custom_{project_id}"
        ),
        "poetry_id_valence_low": f"corpus_poetry_id_valence_low_{project_id}",
        "poetry_id_valence_high": f"corpus_poetry_id_valence_high_{project_id}",
        "poetry_id_arousal_low": f"corpus_poetry_id_arousal_low_{project_id}",
        "poetry_id_arousal_high": f"corpus_poetry_id_arousal_high_{project_id}",
        "poetry_id_dominance_low": f"corpus_poetry_id_dominance_low_{project_id}",
        "poetry_id_dominance_high": (
            f"corpus_poetry_id_dominance_high_{project_id}"
        ),
        "meter_analysis_mode": f"corpus_meter_mode_{project_id}",
        "meter_style_profile": f"corpus_meter_style_{project_id}",
        "meter_interpretation_depth": f"corpus_meter_depth_{project_id}",
        "meter_line_match_threshold": (
            f"corpus_meter_line_threshold_{project_id}"
        ),
        "meter_irregular_threshold": f"corpus_meter_poem_threshold_{project_id}",
        "meter_ambiguity_margin": f"corpus_meter_margin_{project_id}",
        "meter_maximum_variants": f"corpus_meter_variants_{project_id}",
        "meter_performance_candidate_limit": (
            f"corpus_meter_candidate_limit_{project_id}"
        ),
        "meter_realized_alternatives": (
            f"corpus_meter_alternatives_{project_id}"
        ),
        "meter_allow_visible_elision": f"corpus_meter_elision_{project_id}",
        "single_stopword_mode": f"{prefix}_stopword_mode",
        "single_protected_stopwords": f"{prefix}_protected_stopwords",
        "single_custom_stopword_additions": (
            f"{prefix}_custom_stopword_additions"
        ),
        "single_custom_stopword_removals": (
            f"{prefix}_custom_stopword_removals"
        ),
    }


def _corpus_profile_snapshot(project_id: str) -> dict[str, object]:
    settings: dict[str, object] = {
        "selected_lexicons": list(
            st.session_state.get(f"analysis_lexicons_{project_id}", [])
        )
    }
    selected_modules = set(
        st.session_state.get(f"analysis_modules_{project_id}", [])
    )
    for include_key, module_id in _CORPUS_PROFILE_INCLUDE_TO_MODULE.items():
        settings[include_key] = module_id in selected_modules
    for profile_key, corpus_key in _corpus_profile_setting_keys(
        project_id
    ).items():
        if corpus_key in st.session_state:
            settings[profile_key] = st.session_state[corpus_key]
    return snapshot_profile_settings(settings)


def _safe_filename(value: str) -> str:
    stem = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value.strip()
    ).strip("_")
    return stem or "versevad_corpus"


def _records_frame(records) -> pd.DataFrame:
    return pd.DataFrame([asdict(record) for record in records])


@st.cache_resource(show_spinner=False)
def _project_repository_for_path(path: str) -> ProjectRepository:
    """Initialize each database schema once while keeping connections short-lived."""

    repository = ProjectRepository(path)
    repository.initialize()
    return repository


@st.cache_resource(show_spinner=False)
def _reference_index_for_signature(
    root_text: str,
    file_signature: tuple[tuple[str, int, int], ...],
):
    """Reuse one immutable VerseMap index until one source file changes."""

    del file_signature
    return load_reference_index(root_text)


def _cached_reference_index(source_root):
    """Load a current reference index without reparsing three CSVs per rerun."""

    signature_rows = []
    for filename in (
        MODEL_FILENAME,
        PROFILE_FILENAME,
        POET_PROFILE_FILENAME,
    ):
        source_stat = (source_root / filename).stat()
        signature_rows.append(
            (filename, source_stat.st_size, source_stat.st_mtime_ns)
        )
    return _reference_index_for_signature(
        str(source_root),
        tuple(signature_rows),
    )


def _render_versemap_tab(
    repository: ProjectRepository,
    project_id: str,
) -> None:
    st.subheader("VerseMap")
    st.write(
        "Compare the project works with reference poet centroids under the pinned "
        "VerseMap Standard Profile 1.0. Distances are descriptive and are not "
        "authorship, influence, quality, or meaning claims."
    )
    metrics = repository.list_latest_module_metrics(
        project_id,
        module_names=("versemap",),
    )
    if not metrics:
        st.info(
            "No completed VerseMap corpus batch is available. In Analyze & Compare, "
            "select VerseMap comparative profile and analyze the corpus."
        )
        return
    try:
        index = _cached_reference_index(
            RESOURCE_ROOT / "VerseMap_Reference_Corpus"
        )
    except (OSError, ValueError) as error:
        st.error(f"The versioned VerseMap reference index could not be loaded: {error}")
        return

    by_work: dict[str, dict[str, object]] = {}
    for row in metrics:
        work = by_work.setdefault(
            row.text_id,
            {
                "text_id": row.text_id,
                "title": row.title,
                "author": row.author,
                "coordinate_1": None,
                "coordinate_2": None,
                "coverage": None,
                "poet_neighbors": {},
                "features": {},
            },
        )
        if row.metric_id == "versemap.coordinate_1":
            work["coordinate_1"] = row.value
        elif row.metric_id == "versemap.coordinate_2":
            work["coordinate_2"] = row.value
        elif row.metric_id == "versemap.evidence_weight_coverage":
            work["coverage"] = row.value
        elif (
            row.scope == "poet_neighbor"
            and row.metric_id in {
                "versemap.neighbor_name",
                "versemap.neighbor_distance",
                "versemap.neighbor_shared_weight",
            }
        ):
            values = work["poet_neighbors"].setdefault(row.scope_id, {})
            values[row.metric_id] = row.value
        elif row.metric_id.startswith("versemap.") and row.scope == "document":
            work["features"][row.metric_id.removeprefix("versemap.")] = row.value

    complete_works = [
        row
        for row in by_work.values()
        if row["coordinate_1"] is not None and row["coordinate_2"] is not None
    ]
    if not complete_works:
        st.warning("The completed batch contains no projectable VerseMap coordinates.")
        return
    centroid_x = sum(float(row["coordinate_1"]) for row in complete_works) / len(
        complete_works
    )
    centroid_y = sum(float(row["coordinate_2"]) for row in complete_works) / len(
        complete_works
    )

    nearest_rows = []
    poet_distances: dict[str, list[float]] = {}
    for work in complete_works:
        ranked = []
        for scope_id, values in work["poet_neighbors"].items():
            if (
                "versemap.neighbor_name" not in values
                or "versemap.neighbor_distance" not in values
            ):
                continue
            rank = int(scope_id.rsplit(":", 1)[-1])
            ranked.append((rank, values))
            poet_distances.setdefault(
                str(values["versemap.neighbor_name"]), []
            ).append(float(values["versemap.neighbor_distance"]))
        ranked.sort(key=lambda item: item[0])
        if ranked:
            _, values = ranked[0]
            nearest_rows.append(
                {
                    "Work": work["title"],
                    "Author Metadata": work["author"] or "Not recorded",
                    "Nearest Reference Poet": values["versemap.neighbor_name"],
                    "Distance": values["versemap.neighbor_distance"],
                    "Shared Evidence Weight": values.get(
                        "versemap.neighbor_shared_weight"
                    ),
                    "Profile Weight Available": work["coverage"],
                }
            )
    project_neighbor_rows = sorted(
        (
            {
                "Rank": 0,
                "Reference Poet": poet,
                "Mean Work-to-Centroid Distance": sum(values) / len(values),
                "Works Compared": len(values),
            }
            for poet, values in poet_distances.items()
        ),
        key=lambda row: row["Mean Work-to-Centroid Distance"],
    )
    for rank, row in enumerate(project_neighbor_rows, start=1):
        row["Rank"] = rank

    summary_columns = st.columns(4)
    summary_columns[0].metric("Mapped project works", f"{len(complete_works):,}")
    summary_columns[1].metric("Reference poets", f"{len(index.poets):,}")
    summary_columns[2].metric(
        "Mean profile weight",
        (
            f"{sum(float(row['coverage']) for row in complete_works if row['coverage'] is not None) / max(sum(row['coverage'] is not None for row in complete_works), 1):.1%}"
        ),
    )
    summary_columns[3].metric(
        "Nearest project-level poet",
        (
            project_neighbor_rows[0]["Reference Poet"]
            if project_neighbor_rows
            else "Insufficient evidence"
        ),
    )

    with bottom_collapsible_expander(
        "Corpus VerseMap Space",
        control_id=f"corpus-versemap-space-{project_id}",
        expanded=False,
    ):
        map_rows = [
            {
                "Kind": "Reference poet centroid",
                "Poet": item.poet_name,
                "Title": item.poet_name,
                "Component 1": item.coordinate_1,
                "Component 2": item.coordinate_2,
                "Poem count": item.poem_count,
            }
            for item in index.poets
        ]
        map_rows.extend(
            {
                "Kind": "Project work",
                "Poet": row["author"] or "",
                "Title": row["title"],
                "Component 1": row["coordinate_1"],
                "Component 2": row["coordinate_2"],
                "Poem count": 1,
            }
            for row in complete_works
        )
        map_rows.append(
            {
                "Kind": "Project centroid",
                "Poet": "",
                "Title": "Project centroid",
                "Component 1": centroid_x,
                "Component 2": centroid_y,
                "Poem count": len(complete_works),
            }
        )
        frame = pd.DataFrame(map_rows).dropna(
            subset=["Component 1", "Component 2"]
        )
        chart = (
            alt.Chart(frame)
            .mark_circle(opacity=0.72)
            .encode(
                x=alt.X(
                    "Component 1:Q",
                    title=(
                        "Component 1 "
                        f"({index.explained_variance_1:.1%} reference variance)"
                    ),
                ),
                y=alt.Y(
                    "Component 2:Q",
                    title=(
                        "Component 2 "
                        f"({index.explained_variance_2:.1%} reference variance)"
                    ),
                ),
                color=alt.Color(
                    "Kind:N",
                    scale=alt.Scale(
                        domain=[
                            "Reference poet centroid",
                            "Project work",
                            "Project centroid",
                        ],
                        range=["#705d8f", "#326b78", "#9f4528"],
                    ),
                ),
                size=alt.Size(
                    "Kind:N",
                    sort=[
                        "Reference poet centroid",
                        "Project work",
                        "Project centroid",
                    ],
                    scale=alt.Scale(
                        domain=[
                            "Reference poet centroid",
                            "Project work",
                            "Project centroid",
                        ],
                        range=[150, 75, 260],
                    ),
                    legend=None,
                ),
                tooltip=[
                    "Kind",
                    "Poet",
                    "Title",
                    "Poem count",
                    alt.Tooltip("Component 1:Q", format=".3f"),
                    alt.Tooltip("Component 2:Q", format=".3f"),
                ],
            )
            .properties(height=560)
            .interactive()
        )
        st.altair_chart(publication_chart(chart), width="stretch")
        st.caption(
            "The project centroid is the mean map position of its completed works. "
            "The nearest-poet tables below use full-space standardized distances, "
            "not only this two-dimensional display."
        )

    with bottom_collapsible_expander(
        "Nearest Reference Poets",
        control_id=f"corpus-versemap-neighbors-{project_id}",
        expanded=False,
    ):
        st.markdown("#### Project-level pattern")
        render_dataframe(
            pd.DataFrame(project_neighbor_rows),
            column_config={
                "Mean Work-to-Centroid Distance": (
                    st.column_config.NumberColumn(format="%.3f")
                )
            },
        )
        st.caption(
            "Project ranking averages each work's full-space distance to a reference "
            "poet centroid. It does not collapse the project into a fictional single poem."
        )
        st.markdown("#### Work-by-work")
        render_dataframe(
            pd.DataFrame(nearest_rows),
            column_config={
                "Distance": st.column_config.NumberColumn(format="%.3f"),
                "Shared Evidence Weight": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="percent"
                ),
                "Profile Weight Available": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="percent"
                ),
            },
        )

    with bottom_collapsible_expander(
        "Methodology and Coverage",
        control_id=f"corpus-versemap-methodology-{project_id}",
        expanded=False,
    ):
        st.markdown(
            f"**{index.profile_id}** | {index.profile_build_id} | "
            f"{index.reference_release_id} | {index.model_id}"
        )
        st.write(
            "Every project work is analyzed independently under the same pinned "
            "profile as the reference poems. Repeated content-word occurrences are "
            "retained, stopwords are removed for lexical measures, and missing "
            "evidence remains missing. All corpus exports retain the VerseMap "
            "module metrics, coverage, warnings, and per-work CSV/Word artifacts."
        )


def _poetry_id_work_comparison_rows(
    metrics,
    selected_group: tuple[str, str],
) -> tuple[dict[str, object], ...]:
    """Build one readable categorical/centroid comparison row per work."""

    scope_id, weighting = selected_group
    document_metric_ids = {
        "poetry_id.categorical_archetype_id",
        "poetry_id.categorical_archetype_name",
        "poetry_id.nearest_centroid_archetype_id",
    }
    by_work: dict[str, dict[str, object]] = {}
    for row in metrics:
        is_selected_document_metric = (
            row.scope == "document"
            and row.scope_id == scope_id
            and row.weighting == weighting
            and row.metric_id in document_metric_ids
        )
        if not is_selected_document_metric:
            continue
        values = by_work.setdefault(
            row.text_id,
            {
                "text_id": row.text_id,
                "title": row.title,
                "metrics": {},
            },
        )
        values["metrics"][row.metric_id] = row.value

    rows = []
    for values in sorted(
        by_work.values(),
        key=lambda item: (str(item["title"]).casefold(), str(item["text_id"])),
    ):
        work_metrics = values["metrics"]
        categorical_id = work_metrics.get(
            "poetry_id.categorical_archetype_id"
        )
        categorical_name = work_metrics.get(
            "poetry_id.categorical_archetype_name"
        )
        if not categorical_name and isinstance(categorical_id, str):
            archetype = ARCHETYPE_BY_ID.get(categorical_id)
            categorical_name = archetype.name if archetype else categorical_id

        nearest_id = work_metrics.get(
            "poetry_id.nearest_centroid_archetype_id"
        )
        nearest_name = None
        if isinstance(nearest_id, str):
            archetype = ARCHETYPE_BY_ID.get(nearest_id)
            nearest_name = archetype.name if archetype else nearest_id

        rows.append(
            {
                "Work": values["title"],
                "Category Fit Archetype": categorical_name,
                "Nearest Centroid Archetype": nearest_name,
            }
        )
    return tuple(rows)


def _inherited_form_work_comparison_rows(
    metrics,
) -> tuple[dict[str, object], ...]:
    """Build one inherited-form candidate row per analyzed work."""

    metric_ids = {
        "inherited_form.result_status",
        "inherited_form.best_candidate_name",
        "inherited_form.best_consistency",
        "inherited_form.best_evidence_coverage",
        "inherited_form.confidence_label",
        "inherited_form.classification",
        "inherited_form.nearest_alternative_name",
        "inherited_form.candidate_margin",
    }
    by_work: dict[str, dict[str, object]] = {}
    for row in metrics:
        if (
            row.module_name != "inherited_form"
            or row.scope != "document"
            or row.metric_id not in metric_ids
        ):
            continue
        values = by_work.setdefault(row.text_id, {"Work": row.title})
        values[row.metric_id] = row.value
    return tuple(
        {
            "Work": values["Work"],
            "Potential match": values.get(
                "inherited_form.best_candidate_name"
            ),
            "Classification": values.get(
                "inherited_form.classification"
            ),
            "Consistency": values.get(
                "inherited_form.best_consistency"
            ),
            "Evidence coverage": values.get(
                "inherited_form.best_evidence_coverage"
            ),
            "Confidence": str(
                values.get("inherited_form.confidence_label", "")
            ).title() or None,
            "Nearest alternative": values.get(
                "inherited_form.nearest_alternative_name"
            ),
            "Candidate margin": values.get(
                "inherited_form.candidate_margin"
            ),
            "Status": str(
                values.get("inherited_form.result_status", "")
            ).replace("_", " ").title(),
        }
        for values in sorted(
            by_work.values(),
            key=lambda item: str(item["Work"]).casefold(),
        )
    )


def _corpus_part_of_speech_rows(
    repository: ProjectRepository,
    project_id: str,
    preprocessor: TextPreprocessor,
) -> tuple[dict[str, object], ...]:
    texts = repository.list_texts(project_id)
    metadata = preprocessor.metadata
    signature = (
        "versevad-pos-profile-v2",
        project_id,
        metadata.recipe_id,
        metadata.pipeline_name,
        metadata.pipeline_version,
        tuple(
            (
                text.text_id,
                text.text_version_id,
                text.title,
                text.collection,
            )
            for text in texts
        ),
    )
    cache_key = f"corpus_pos_profile_{project_id}"
    cached = st.session_state.get(cache_key)
    if cached and cached["signature"] == signature:
        return cached["rows"]

    rows: list[dict[str, object]] = []
    all_tokens = []
    for text in texts:
        document = TextDocument(
            text_id=text.text_id,
            title=text.title,
            original_text=text.original_text,
            text_sha256=text.text_sha256,
            text_version_id=text.text_version_id,
        )
        tokens = preprocessor.process(document)
        all_tokens.extend(tokens)
        for profile_level, views in (
            ("Broad Categories", part_of_speech_views_for_tokens(tokens)),
            (
                "Detailed Model Tags",
                detailed_part_of_speech_views_for_tokens(tokens),
            ),
        ):
            for view in views:
                rows.append(
                    {
                        "Scope": "Work",
                        "Profile Level": profile_level,
                        "Work": text.title,
                        "Collection": text.collection,
                        "Source POS tag(s)": view.tag,
                        "Part of speech": view.category,
                        "Token count": view.token_count,
                        "Share of lexical tokens": view.share_of_lexical_tokens,
                        "Unique normalized types": view.unique_type_count,
                        "Examples": view.example_forms,
                        "Lexical-token denominator": view.lexical_token_denominator,
                        "Model": (
                            f"{metadata.pipeline_name} {metadata.pipeline_version}"
                        ),
                    }
                )
    for profile_level, views in (
        ("Broad Categories", part_of_speech_views_for_tokens(all_tokens)),
        (
            "Detailed Model Tags",
            detailed_part_of_speech_views_for_tokens(all_tokens),
        ),
    ):
        for view in views:
            rows.append(
                {
                    "Scope": "All Works Combined",
                    "Profile Level": profile_level,
                    "Work": "All Works Combined",
                    "Collection": "",
                    "Source POS tag(s)": view.tag,
                    "Part of speech": view.category,
                    "Token count": view.token_count,
                    "Share of lexical tokens": view.share_of_lexical_tokens,
                    "Unique normalized types": view.unique_type_count,
                    "Examples": view.example_forms,
                    "Lexical-token denominator": view.lexical_token_denominator,
                    "Model": (
                        f"{metadata.pipeline_name} {metadata.pipeline_version}"
                    ),
                }
            )
    materialized = tuple(rows)
    st.session_state[cache_key] = {"signature": signature, "rows": materialized}
    return materialized


def _create_project(repository: ProjectRepository, *, expanded: bool) -> None:
    with st.expander("Create a research project", expanded=expanded):
        with st.form("create_corpus_project", clear_on_submit=True):
            title = st.text_input("Project title", key="new_project_title")
            researcher = st.text_input("Researcher (optional)", key="new_project_researcher")
            description = st.text_area(
                "Project description (optional)",
                key="new_project_description",
                height=90,
            )
            create = st.form_submit_button("Create project", type="primary")
        if create:
            try:
                repository.create_project(
                    title,
                    researcher=researcher,
                    description=description,
                )
                st.success("Project created in the local VerseVAD database.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _render_texts_tab(repository: ProjectRepository, project_id: str) -> None:
    st.subheader("Import a Folder of Works")
    st.write(
        "Choose a folder containing UTF-8 `.txt` files. Each file becomes one work; "
        "subfolder paths are retained. Re-importing a changed file creates a new "
        "preserved text version rather than overwriting the old one."
    )
    uploads = st.file_uploader(
        "Corpus folder",
        type=["txt"],
        accept_multiple_files="directory",
        help="The browser passes these files only to the VerseVAD process on this computer.",
        key=f"corpus_folder_{project_id}",
    )
    st.markdown(
        '<div aria-hidden="true" style="height:0.4rem"></div>',
        unsafe_allow_html=True,
    )
    if st.button(
        "Import selected folder",
        type="primary",
        disabled=not uploads,
        key=f"import_corpus_{project_id}",
    ):
        try:
            decoded = decode_corpus_files(
                (upload.name, upload.getvalue()) for upload in uploads
            )
            records = repository.import_texts(project_id, decoded.files)
            st.success(
                f"Imported {len(decoded.files):,} files. This project now contains "
                f"{len(records):,} active works."
            )
            st.rerun()
        except (TextImportError, ValueError) as error:
            st.error(str(error))

    st.markdown(
        '<div aria-hidden="true" style="height:0.4rem"></div>',
        unsafe_allow_html=True,
    )
    texts = repository.list_texts(project_id)
    if not texts:
        st.info("No works have been imported into this project yet.")
        return
    st.subheader(f"Works in This Project ({len(texts):,})")
    filter_columns = st.columns(3)
    search_text = filter_columns[0].text_input(
        "Search works",
        key=f"work_search_{project_id}",
        placeholder="Title, author, collection, or date",
    )
    author_filter = filter_columns[1].selectbox(
        "Author",
        options=["All authors", *sorted({text.author for text in texts if text.author})],
        key=f"work_author_filter_{project_id}",
    )
    collection_filter = filter_columns[2].selectbox(
        "Collection",
        options=[
            "All collections",
            *sorted({text.collection for text in texts if text.collection}),
        ],
        key=f"work_collection_filter_{project_id}",
    )
    query = search_text.strip().casefold()
    filtered_texts = [
        text
        for text in texts
        if (
            not query
            or query
            in " ".join(
                (
                    text.title,
                    text.author,
                    text.collection,
                    text.date_label,
                )
            ).casefold()
        )
        and (author_filter == "All authors" or text.author == author_filter)
        and (
            collection_filter == "All collections"
            or text.collection == collection_filter
        )
    ]
    completed_batches = repository.list_completed_batches(project_id)
    completed_text_ids = (
        set(completed_batches[0].text_ids) if completed_batches else set()
    )
    warning_text_ids = {
        row.text_id
        for row in repository.list_latest_module_warnings(project_id)
    }
    summary = pd.DataFrame(
        [
            {
                "Title": text.title,
                "Author": text.author,
                "Collection": text.collection,
                "Date": text.date_label,
                "Genre": text.genre,
                "Analysis status": (
                    "Complete with warnings"
                    if text.text_id in warning_text_ids
                    else (
                        "Complete"
                        if text.text_id in completed_text_ids
                        else "Not run"
                    )
                ),
                "Source path": text.relative_path,
                "Version": text.text_version_id,
            }
            for text in filtered_texts
        ]
    )
    if summary.empty:
        st.info("No works match the current search and filters.")
    else:
        render_dataframe(summary, hide_index=True, width="stretch", height=300)
    st.caption(
        f"Showing {len(filtered_texts):,} of {len(texts):,} works. "
        "Select column headers to sort."
    )

    st.subheader("Edit One Work's Metadata")
    selected_id = st.selectbox(
        "Work",
        options=[text.text_id for text in texts],
        format_func=lambda text_id: next(text.title for text in texts if text.text_id == text_id),
        key=f"metadata_text_{project_id}",
    )
    selected = next(text for text in texts if text.text_id == selected_id)
    with st.form(f"metadata_form_{selected.text_id}"):
        left, right = st.columns(2)
        title = left.text_input("Title", value=selected.title)
        author = right.text_input("Author", value=selected.author)
        collection = left.text_input("Collection or volume", value=selected.collection)
        date_label = right.text_input("Date or date range", value=selected.date_label)
        genre = left.text_input("Genre or work type", value=selected.genre)
        notes = st.text_area("Research notes", value=selected.notes, height=90)
        custom_json = st.text_area(
            "Custom metadata (JSON object)",
            value=json.dumps(dict(selected.custom_metadata), ensure_ascii=False, indent=2),
            height=100,
            help='For extensible fields such as {"sequence": 3, "section": "Part I"}.',
        )
        save = st.form_submit_button("Save metadata")
    if save:
        try:
            custom = json.loads(custom_json or "{}")
            if not isinstance(custom, dict):
                raise ValueError("Custom metadata must be a JSON object enclosed in braces.")
            repository.update_text_metadata(
                selected.text_id,
                title=title,
                author=author,
                collection=collection,
                date_label=date_label,
                genre=genre,
                notes=notes,
                custom_metadata=custom,
            )
            st.success("Metadata saved locally.")
            st.rerun()
        except (ValueError, json.JSONDecodeError) as error:
            st.error(f"Metadata was not changed: {error}")


def _render_profiles(
    metrics,
    total_works: int,
    *,
    profile_selection: ProfileSelection | None = None,
) -> None:
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    analysis_views = (
        tuple(view_ids[scope] for scope in profile_selection.scopes)
        if profile_selection is not None
        else None
    )
    weightings = (
        tuple(weighting.value.casefold() for weighting in profile_selection.weightings)
        if profile_selection is not None
        else ("token",)
    )
    profiles = corpus_vad_profiles(
        metrics,
        total_works=total_works,
        analysis_views=analysis_views,
        weightings=weightings,
    )
    if not profiles:
        st.info("The latest complete corpus batch has no normalized VAD means to compare.")
        return
    st.subheader("Collection VAD: Report Both Views")
    st.write(
        "The **pooled-observation volume profile** lets works with more included matched "
        "observations contribute more. The **equal-work volume profile** gives every "
        "eligible work one poem-level score. Both use the lexical scope and within-poem "
        "token/type weighting selected above; their divergence can be an important finding."
    )
    scope_labels = {
        "all_matched": "All lexical tokens",
        "stopwords_excluded": "Stopword-excluded",
        "content_words": "Content words only",
    }
    profile_frame = pd.DataFrame(
        [
            {
                "Lexicon": row.lexicon,
                "Profile": (
                    f"{scope_labels.get(row.analysis_view, row.analysis_view)} · "
                    f"{row.weighting.title()}-weighted"
                ),
                "Dimension": row.dimension.title(),
                "Works included": row.works_included,
                "Works omitted": row.works_omitted,
                "Matched observations": row.matched_observations,
                "Volume coverage": row.volume_coverage,
                "Pooled-observation volume mean": row.token_weighted_volume_mean,
                "Pooled lexical-rating SD": (
                    row.pooled_lexical_rating_standard_deviation
                ),
                "Equal-work volume mean": row.work_weighted_volume_mean,
                "Across-poem mean SD": row.poem_mean_standard_deviation,
                "Poem-mean median": row.poem_mean_median,
                "Lowest poem mean": row.poem_mean_minimum,
                "Highest poem mean": row.poem_mean_maximum,
                "Equal-work minus pooled": row.work_minus_token_difference,
            }
            for row in profiles
        ]
    )
    render_dataframe(
        profile_frame.style.format(
            {
                "Volume coverage": "{:.1%}",
                "Pooled-observation volume mean": "{:.3f}",
                "Pooled lexical-rating SD": "{:.3f}",
                "Equal-work volume mean": "{:.3f}",
                "Across-poem mean SD": "{:.3f}",
                "Poem-mean median": "{:.3f}",
                "Lowest poem mean": "{:.3f}",
                "Highest poem mean": "{:.3f}",
                "Equal-work minus pooled": "{:+.3f}",
            },
            na_rep="—",
        ),
        hide_index=True,
        width="stretch",
    )
    chart = profile_frame.melt(
        id_vars=["Lexicon", "Profile", "Dimension"],
        value_vars=["Pooled-observation volume mean", "Equal-work volume mean"],
        var_name="Collection view",
        value_name="Normalized mean",
    )
    chart["Metric profile"] = chart["Dimension"] + " · " + chart["Profile"]
    comparison_chart = (
        alt.Chart(rounded_display_data(chart))
        .mark_bar()
        .encode(
            x=alt.X(
                "Normalized mean:Q",
                scale=alt.Scale(domain=[0.0, 1.0]),
                title="Normalized mean",
            ),
            y=alt.Y(
                "Metric profile:N",
                title=None,
                axis=alt.Axis(labelLimit=360),
            ),
            yOffset=alt.YOffset("Collection view:N"),
            color=alt.Color(
                "Collection view:N",
                legend=alt.Legend(
                    title=None,
                    orient="top",
                    direction="horizontal",
                    columns=2,
                    labelLimit=260,
                    symbolType="square",
                ),
            ),
            tooltip=[
                "Lexicon:N",
                "Profile:N",
                "Dimension:N",
                "Collection view:N",
                alt.Tooltip("Normalized mean:Q", format=".3f"),
            ],
        )
        .properties(height=max(220, 52 * profile_frame["Profile"].nunique() * 3))
    )
    st.altair_chart(publication_chart(comparison_chart), width="stretch")
    st.caption(
        "Pooled lexical-rating SD describes the spread of all included matched "
        "ratings around the pooled-observation mean. Across-poem mean SD "
        "describes variation among compatible poem-level means around the equal-work "
        "mean. Neither is a confidence interval, source-rater uncertainty, or an "
        "emotion declaration. Missing work scores stay omitted rather than receiving "
        "a neutral value."
    )
    _render_scope_token_counts(metrics)


def _render_scope_token_counts(metrics) -> None:
    """Show the eligible token pool behind each corpus lexical scope."""

    scope_labels = {
        "all_matched": "All lexical tokens",
        "stopwords_excluded": "Stopword-excluded",
        "content_words": "Content words only",
    }
    counts: dict[tuple[str, str], dict[str, object]] = {}
    for row in metrics:
        if (
            row.weighting != "token"
            or row.analysis_view not in scope_labels
            or row.lexical_tokens < 0
        ):
            continue
        key = (row.text_id, row.analysis_view)
        current = counts.get(key)
        if current is None or int(row.lexical_tokens) > int(current["Eligible tokens"]):
            counts[key] = {
                "Poem": row.title,
                "Scope": scope_labels[row.analysis_view],
                "Eligible tokens": int(row.lexical_tokens),
            }
    if not counts:
        return

    poem_rows: dict[str, dict[str, object]] = {}
    for (text_id, _analysis_view), item in counts.items():
        row = poem_rows.setdefault(text_id, {"Poem": item["Poem"]})
        row[str(item["Scope"])] = item["Eligible tokens"]
    ordered_scopes = tuple(scope_labels.values())
    poem_frame = pd.DataFrame(
        sorted(poem_rows.values(), key=lambda item: str(item["Poem"]).casefold()),
        columns=("Poem", *ordered_scopes),
    )
    whole_rows = []
    for scope in ordered_scopes:
        values = poem_frame[scope].dropna() if scope in poem_frame else pd.Series(dtype=float)
        whole_rows.append(
            {
                "Scope": scope,
                "Poems represented": int(values.count()),
                "Eligible tokens in corpus": int(values.sum()),
            }
        )

    with bottom_collapsible_expander(
        "Eligible Token Counts by Lexical Scope",
        control_id="corpus-scope-token-counts",
        expanded=False,
    ):
        st.write(
            "These are lexical token occurrences eligible under each scope before "
            "resource matching. The pooled-observation profile uses only matched "
            "observations drawn from the applicable scope; the equal-work profile "
            "uses one poem-level mean per eligible poem."
        )
        render_dataframe(
            pd.DataFrame(whole_rows),
            hide_index=True,
            width="stretch",
        )
        st.markdown("##### Counts by Poem")
        render_dataframe(
            poem_frame,
            hide_index=True,
            width="stretch",
            height=min(420, 76 + len(poem_frame) * 35),
        )


_WHOLE_CORPUS_SCOPE = "__whole_corpus__"
_CORPUS_REPORT_MODULES = {
    "Lexical Character, Imagery & Embodiment": (
        "concreteness",
        "frequency",
        "lexical_frequency",
        "aoa",
        "age_of_acquisition",
        "readability",
        "sensorimotor",
        "sensorimotor_imagery_and_embodiment",
    ),
    "Sound & Form": (
        "pronunciation",
        "pronunciation_prosody_foundation",
        "meter",
        "candidate_meter_and_rhythmic_regularity",
        "phonology",
        "rhyme_and_phonological_patterns",
        "inherited_form",
    ),
    "Structure": ("lexical_style",),
    "PoetryID": ("poetry_id",),
    "VerseMap": ("versemap",),
}
_CORPUS_MODULE_LABELS = {
    "concreteness": "Concreteness",
    "frequency": "Frequency & Rarity",
    "lexical_frequency": "Frequency & Rarity",
    "aoa": "Acquisition & Readability",
    "age_of_acquisition": "Age of Acquisition",
    "readability": "Readability",
    "sensorimotor": "Sensorimotor Imagery & Embodiment",
    "sensorimotor_imagery_and_embodiment": (
        "Sensorimotor Imagery & Embodiment"
    ),
    "pronunciation": "Pronunciation, Syllables & Stress",
    "pronunciation_prosody_foundation": (
        "Pronunciation, Syllables & Stress"
    ),
    "meter": "Candidate Meter & Rhythmic Regularity",
    "candidate_meter_and_rhythmic_regularity": (
        "Candidate Meter & Rhythmic Regularity"
    ),
    "phonology": "Rhyme & Recurring Sound",
    "rhyme_and_phonological_patterns": "Rhyme & Recurring Sound",
    "inherited_form": "Inherited Form Analysis",
    "lexical_style": "Lexical & Structural Measures",
    "poetry_id": "PoetryID",
    "versemap": "VerseMap",
}


def _humanize_metric(value: str) -> str:
    return (
        value.rsplit(".", 1)[-1]
        .replace("_", " ")
        .replace("vad", "VAD")
        .replace("hdd", "HD-D")
        .replace("mattr", "MATTR")
        .replace("mtld", "MTLD")
        .strip()
        .title()
        .replace("Vad", "VAD")
        .replace("Hd-D", "HD-D")
        .replace("Mattr", "MATTR")
        .replace("Mtld", "MTLD")
    )


def _render_canonical_corpus_module_profiles(
    rows,
    *,
    module_id: str,
    profile_selection: ProfileSelection,
    overridden_modules: frozenset[str],
    selected_text_id: str | None,
) -> bool:
    """Render retained scope-aware rows for one configurable lexical module."""

    effective = selection_for_module(
        profile_selection,
        module_id,
        overridden_modules,
    )
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    views = {view_ids[scope] for scope in effective.scopes}
    weightings = {
        weighting.value.casefold() for weighting in effective.weightings
    }
    selected = tuple(
        row
        for row in rows
        if corpus_metric_module_id(row.metric) == module_id
        and row.analysis_view in views
        and row.weighting in weightings
        and (selected_text_id is None or row.text_id == selected_text_id)
    )
    if not selected:
        return False
    scope_labels = {
        "all_matched": "All lexical tokens",
        "stopwords_excluded": "Stopword-excluded",
        "content_words": "Content words only",
    }
    frame = pd.DataFrame(
        [
            {
                "Poem": row.title,
                "Source": row.lexicon,
                "Metric": _humanize_metric(row.metric),
                "Dimension": (row.dimension or row.category or "â€”").title(),
                "Profile": (
                    f"{scope_labels[row.analysis_view]} Â· "
                    f"{row.weighting.title()}-weighted"
                ),
                "Value": row.value,
                "Matched Observations": row.observations,
                "Coverage": row.coverage,
            }
            for row in selected
        ]
    )
    st.markdown("#### Selected Scope-Aware Profiles")
    if selected_text_id is None:
        grouped = (
            frame.groupby(
                ["Source", "Metric", "Dimension", "Profile"],
                dropna=False,
                as_index=False,
            )
            .agg(
                **{
                    "Equal-Work Mean": ("Value", "mean"),
                    "Poem-Level SD": ("Value", lambda values: values.std(ddof=0)),
                    "Works Included": ("Value", "count"),
                    "Mean Coverage": ("Coverage", "mean"),
                }
            )
        )
        render_dataframe(
            grouped.style.format(
                {
                    "Equal-Work Mean": "{:.3f}",
                    "Poem-Level SD": "{:.3f}",
                    "Mean Coverage": "{:.1%}",
                },
                na_rep="â€”",
            ),
            hide_index=True,
            width="stretch",
            height=min(460, 76 + len(grouped) * 35),
        )
        st.caption(
            "Equal-work means give each included poem one poem-level value; "
            "Poem-Level SD describes variation among those poem values."
        )
    else:
        render_dataframe(
            frame.drop(columns=("Poem",)).style.format(
                {"Value": "{:.3f}", "Coverage": "{:.1%}"},
                na_rep="â€”",
            ),
            hide_index=True,
            width="stretch",
            height=min(460, 76 + len(frame) * 35),
        )
    return True


def _corpus_metric_family(metric_id: str) -> str:
    """Return a compact reader-facing family for a corpus metric."""

    identifier = metric_id.casefold()
    if "population_sd" in identifier or "population_standard_deviation" in identifier:
        return "Within-Poem Dispersion"
    if any(
        marker in identifier
        for marker in (
            "rating_total",
            "midpoint",
            "cumulative_load",
            "load_per_100",
        )
    ):
        return "Cumulative Lexical Load"
    if identifier.startswith("readability.poetic_reading_ease"):
        return "VerseVAD Poetic Reading Ease"
    if identifier.startswith("readability."):
        return "Traditional Readability"
    if identifier.startswith("sensorimotor."):
        return "Sensorimotor Profile"
    if identifier.startswith("poetry_id."):
        return "PoetryID"
    if identifier.startswith("lexical_style."):
        if "line" in identifier or "stanza" in identifier:
            return "Line and Stanza Structure"
        if "alphabetic_characters" in identifier or "word_length" in identifier:
            return "Word Length"
        return "Lexical Diversity"
    if identifier.startswith("frequency.") or identifier.startswith("rarity."):
        return "Frequency and Rarity"
    if identifier.startswith("aoa."):
        return "Age of Acquisition"
    if identifier.startswith("concreteness."):
        return "Concreteness"
    if identifier.startswith("pronunciation."):
        return "Pronunciation and Syllables"
    if identifier.startswith("meter."):
        return "Meter and Rhythm"
    if identifier.startswith("phonology."):
        return "Rhyme and Recurring Sound"
    if identifier.startswith("inherited_form."):
        return "Inherited Form"
    return "Summary Metrics"


def _render_corpus_affective_report(
    metrics,
    *,
    selected_text_id: str | None,
    state_prefix: str,
    profile_selection: ProfileSelection,
) -> None:
    selected_metrics = tuple(
        row
        for row in metrics
        if selected_text_id is None or row.text_id == selected_text_id
    )
    comparisons = corpus_vad_work_comparisons(selected_metrics)
    if not comparisons:
        st.info("No normalized VAD means are available for this selection.")
        return
    if selected_text_id is None:
        _render_profiles(
            selected_metrics,
            len({row.text_id for row in selected_metrics}),
            profile_selection=profile_selection,
        )
        st.markdown("#### Poem-Level Comparison")

    lexicons = sorted({row.lexicon for row in comparisons})
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    views = {view_ids[scope] for scope in profile_selection.scopes}
    weightings = {
        weighting.value.casefold() for weighting in profile_selection.weightings
    }
    lexicon = st.selectbox(
        "Lexicon",
        options=lexicons,
        key=f"{state_prefix}_affective_lexicon",
    )
    chosen = tuple(
        row
        for row in comparisons
        if row.lexicon == lexicon
        and row.analysis_view in views
        and row.weighting in weightings
    )
    scope_labels = {
        "all_matched": "All lexical tokens",
        "stopwords_excluded": "Stopword-excluded",
        "content_words": "Content words only",
    }
    long_frame = pd.DataFrame(
        [
            {
                "Poem": row.title,
                "Profile": (
                    f"{scope_labels[row.analysis_view]} · "
                    f"{row.weighting.title()}-weighted"
                ),
                "Dimension": row.dimension.title(),
                "Mean": row.mean,
                "Within-Poem SD": row.population_standard_deviation,
                "Matched Observations": row.observations,
                "Coverage": row.coverage,
            }
            for row in chosen
        ]
    )
    if long_frame.empty:
        st.info("No compatible VAD rows are available for this configuration.")
        return

    if selected_text_id is not None and len(profile_selection.profiles) == 1:
        cards = st.columns(3)
        for column, dimension in zip(
            cards,
            ("Valence", "Arousal", "Dominance"),
            strict=True,
        ):
            values = long_frame.loc[
                long_frame["Dimension"] == dimension,
                "Mean",
            ]
            column.metric(
                f"{dimension} Mean",
                f"{values.iloc[0]:.3f}" if not values.empty else "Unavailable",
            )
        chart = (
            alt.Chart(long_frame)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Mean:Q",
                    scale=alt.Scale(domain=[0.0, 1.0]),
                    title="Normalized lexical rating",
                ),
                y=alt.Y("Dimension:N", sort=("Valence", "Arousal", "Dominance")),
                color=alt.Color(
                    "Dimension:N",
                    scale=alt.Scale(
                        range=["#a7503a", "#457889", "#75638f"]
                    ),
                    legend=None,
                ),
                tooltip=[
                    "Dimension:N",
                    alt.Tooltip("Mean:Q", format=".3f"),
                    alt.Tooltip("Within-Poem SD:Q", format=".3f"),
                    alt.Tooltip("Coverage:Q", format=".1%"),
                ],
            )
            .properties(height=220)
        )
    else:
        chart = (
            alt.Chart(long_frame)
            .mark_circle(size=80, opacity=0.78)
            .encode(
                x=alt.X(
                    "Mean:Q",
                    scale=alt.Scale(zero=False),
                    title="Normalized poem-level mean",
                ),
                y=alt.Y(
                    "Dimension:N",
                    sort=("Valence", "Arousal", "Dominance"),
                    title=None,
                ),
                color=alt.Color("Poem:N"),
                shape=alt.Shape("Profile:N"),
                tooltip=[
                    "Poem:N",
                    "Profile:N",
                    "Dimension:N",
                    alt.Tooltip("Mean:Q", format=".3f"),
                    alt.Tooltip("Within-Poem SD:Q", format=".3f"),
                    alt.Tooltip("Coverage:Q", format=".1%"),
                ],
            )
            .properties(height=250)
        )
    st.altair_chart(publication_chart(chart), width="stretch")

    summary = (
        long_frame.pivot_table(
            index=["Poem", "Profile"],
            columns="Dimension",
            values=["Mean", "Within-Poem SD"],
            aggfunc="first",
        )
        .sort_index(axis=1, level=1)
    )
    summary.columns = [
        f"{dimension} {measure.replace('Within-Poem ', '')}"
        for measure, dimension in summary.columns
    ]
    summary = summary.reset_index()
    render_dataframe(
        summary.style.format(
            {
                column: "{:.3f}"
                for column in summary.columns
                if column not in {"Poem", "Profile"}
            },
            na_rep="—",
        ),
        hide_index=True,
        width="stretch",
        height=min(420, 76 + len(summary) * 35),
    )
    st.caption(
        "Each row identifies its source, scope, and weighting profile. "
        "Within-poem SD describes dispersion among matched lexical ratings; it "
        "is not uncertainty or variation among poems."
    )

    loads = tuple(
        row
        for row in selected_metrics
        if row.metric in _VAD_LOAD_METRICS
        and row.lexicon == lexicon
        and row.analysis_view in views
        and row.weighting in weightings
    )
    if loads:
        with bottom_collapsible_expander(
            "Cumulative and Length-Normalized Lexical Load",
            control_id=f"{state_prefix}-cumulative-load",
            expanded=False,
        ):
            dimensions = sorted({row.dimension.title() for row in loads})
            measures = sorted({row.metric for row in loads})
            load_controls = st.columns(2)
            dimension = load_controls[0].selectbox(
                "Dimension",
                options=dimensions,
                key=f"{state_prefix}_load_dimension",
            )
            measure = load_controls[1].selectbox(
                "Measure",
                options=measures,
                format_func=_humanize_metric,
                key=f"{state_prefix}_load_measure",
            )
            load_frame = pd.DataFrame(
                [
                    {
                        "Poem": row.title,
                        "Profile": (
                            f"{scope_labels[row.analysis_view]} · "
                            f"{row.weighting.title()}-weighted"
                        ),
                        "Value": row.value,
                        "Matched Observations": row.observations,
                        "Coverage": row.coverage,
                    }
                    for row in loads
                    if row.dimension.title() == dimension
                    and row.metric == measure
                ]
            )
            render_dataframe(
                load_frame.style.format(
                    {"Value": "{:.3f}", "Coverage": "{:.1%}"},
                    na_rep="—",
                ),
                hide_index=True,
                width="stretch",
                height=min(360, 76 + len(load_frame) * 35),
            )
            st.caption(
                "Raw cumulative loads remain length- and repetition-sensitive. "
                "Per-observation and per-100 midpoint deviations are normalized "
                "for comparison across differently sized poems. The complete set "
                "of measures remains available in the export."
            )

    volatility = tuple(
        row
        for row in selected_metrics
        if row.metric in _VAD_VOLATILITY_METRICS
        and row.lexicon == lexicon
        and row.analysis_view in views
        and row.weighting in weightings
    )
    if volatility:
        with bottom_collapsible_expander(
            "Mean-Centered Lexical Volatility",
            control_id=f"{state_prefix}-mean-centered-volatility",
            expanded=False,
        ):
            dimensions = sorted({row.dimension.title() for row in volatility})
            dimension = st.selectbox(
                "Dimension",
                options=dimensions,
                key=f"{state_prefix}_volatility_dimension",
            )
            volatility_frame = pd.DataFrame(
                [
                    {
                        "Poem": row.title,
                        "Profile": (
                            f"{scope_labels[row.analysis_view]} · "
                            f"{row.weighting.title()}-weighted"
                        ),
                        "Average Deviation from Poem Mean": row.value,
                        "Matched Observations": row.observations,
                        "Coverage": row.coverage,
                    }
                    for row in volatility
                    if row.dimension.title() == dimension
                ]
            )
            render_dataframe(
                volatility_frame.style.format(
                    {
                        "Average Deviation from Poem Mean": "{:.3f}",
                        "Coverage": "{:.1%}",
                    },
                    na_rep="—",
                ),
                hide_index=True,
                width="stretch",
                height=min(360, 76 + len(volatility_frame) * 35),
            )
            st.caption(
                "This is mean absolute deviation from each poem's own VAD mean. "
                "Unlike population SD, it weights departures linearly rather than "
                "squaring them. Both are length-neutral and order-insensitive."
            )


def _render_poem_module_summary(
    rows,
    *,
    module_name: str,
    state_prefix: str,
) -> None:
    document_rows = tuple(row for row in rows if row.scope == "document")
    if not document_rows:
        st.info(
            "This module has no poem-level summary for the selected poem. "
            "Line-, stanza-, and token-level audit evidence remains in exports."
        )
        return

    contexts = sorted({row.scope_id or "Document Summary" for row in document_rows})
    context = st.selectbox(
        "Source or analysis context",
        options=contexts,
        key=f"{state_prefix}_{module_name}_context",
    )
    selected = tuple(
        row
        for row in document_rows
        if (row.scope_id or "Document Summary") == context
    )
    frame = pd.DataFrame(
        [
            {
                "Metric Family": _corpus_metric_family(row.metric_id),
                "Metric": _humanize_metric(row.metric_id),
                "Value": heterogeneous_display_value(row.value),
                "Unit or Scale": row.unit or "—",
                "Weighting": _humanize_metric(row.weighting) if row.weighting else "—",
                "Observations": row.observation_count,
                "Interpretive Note": row.note or "—",
            }
            for row in selected
        ]
    )
    metric_families = tuple(
        dict.fromkeys(frame["Metric Family"].tolist())
    )
    selected_family = st.selectbox(
        "Metric family",
        options=metric_families,
        key=f"{state_prefix}_{module_name}_poem_metric_family",
        help=(
            "Show one readable family at a time. Line-, stanza-, token-, and "
            "complete audit records remain in exports."
        ),
    )
    visible = frame[frame["Metric Family"] == selected_family]
    render_dataframe(
        visible[
            [
                "Metric",
                "Value",
                "Unit or Scale",
                "Weighting",
                "Observations",
            ]
        ],
        hide_index=True,
        width="stretch",
        height=min(440, 76 + len(visible) * 35),
    )
    with bottom_collapsible_expander(
        "Interpretive and Methodological Notes",
        control_id=f"{state_prefix}-{module_name}-interpretive-notes",
        expanded=False,
    ):
        render_dataframe(
            visible[["Metric", "Interpretive Note"]],
            hide_index=True,
            width="stretch",
            height=min(360, 76 + len(visible) * 35),
        )
    st.caption(
        "This view intentionally shows poem-level summaries only. Complete line, "
        "stanza, token, configuration, and audit records remain downloadable."
    )


def _render_corpus_modules(
    repository: ProjectRepository,
    project_id: str,
    metrics,
    coverage,
    warnings,
    results,
    aggregates,
    *,
    allowed_modules: tuple[str, ...] | None = None,
    selected_module_override: str | None = None,
    selected_text_id: str | None = None,
    state_prefix: str = "corpus_results",
) -> None:
    filtered_metrics = tuple(
        row
        for row in metrics
        if (allowed_modules is None or row.module_name in allowed_modules)
        and (selected_text_id is None or row.text_id == selected_text_id)
    )
    available_modules = sorted({row.module_name for row in filtered_metrics})
    if not available_modules:
        st.info("No compatible module results are available for this selection.")
        return
    selected_module = selected_module_override
    if selected_module is None:
        selected_module = st.selectbox(
            "Analysis",
            options=available_modules,
            format_func=lambda value: _CORPUS_MODULE_LABELS.get(
                value,
                value.replace("_", " ").title(),
            ),
            key=f"{state_prefix}_module_{project_id}",
        )
    selected = tuple(
        row for row in filtered_metrics if row.module_name == selected_module
    )
    if selected_text_id is not None:
        _render_poem_module_summary(
            selected,
            module_name=selected_module,
            state_prefix=state_prefix,
        )
        return

    st.write(
        "Whole-corpus summaries give every compatible poem one vote unless an "
        "observation-weighted mean is explicitly shown. Missing evidence remains "
        "missing and the full audit rows stay in exports."
    )
    total_works = len({row.text_id for row in selected})
    profiles = corpus_module_profiles(selected, total_works=total_works)
    if profiles:
        st.markdown("**Compatible Collection Summaries**")
        profile_frame = pd.DataFrame(
            [
                {
                    "Metric Family": _corpus_metric_family(row.metric_id),
                    "Metric": _humanize_metric(row.metric_id),
                    "Source / View": row.scope_id or "—",
                    "Unit": row.unit,
                    "Weighting": (
                        _humanize_metric(row.weighting)
                        if row.weighting
                        else "—"
                    ),
                    "Works Included": row.works_included,
                    "Works Omitted": row.works_omitted,
                    "Equal-Work Mean": row.equal_work_mean,
                    "Observation-Weighted Mean": (
                        row.observation_weighted_mean
                    ),
                    "Observations": row.total_observations or None,
                    "Methodological Note": row.note,
                }
                for row in profiles
            ]
        )
        profile_families = tuple(
            dict.fromkeys(profile_frame["Metric Family"].tolist())
        )
        selected_family = st.selectbox(
            "Metric family",
            options=profile_families,
            key=f"{state_prefix}_{selected_module}_profile_family",
            help=(
                "Show one readable metric family at a time. The corpus export "
                "retains every compatible summary."
            ),
        )
        visible_profiles = profile_frame[
            profile_frame["Metric Family"] == selected_family
        ]
        render_dataframe(
            visible_profiles[
                [
                    "Metric",
                    "Source / View",
                    "Unit",
                    "Weighting",
                    "Works Included",
                    "Works Omitted",
                    "Equal-Work Mean",
                    "Observation-Weighted Mean",
                    "Observations",
                ]
            ].style.format(
                {
                    "Equal-Work Mean": "{:.3f}",
                    "Observation-Weighted Mean": "{:.3f}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
            height=min(420, 76 + len(visible_profiles) * 35),
        )
        with bottom_collapsible_expander(
            "Methodological Notes",
            control_id=f"{state_prefix}-{selected_module}-methodological-notes",
            expanded=False,
        ):
            render_dataframe(
                visible_profiles[
                    ["Metric", "Source / View", "Methodological Note"]
                ],
                hide_index=True,
                width="stretch",
                height=min(360, 76 + len(visible_profiles) * 35),
            )

    categories = corpus_module_category_profiles(selected)
    if categories:
        st.markdown("**Work-Level Categorical Prevalence**")
        category_metric_ids = tuple(
            dict.fromkeys(row.metric_id for row in categories)
        )
        selected_category_metric = st.selectbox(
            "Categorical measure",
            options=category_metric_ids,
            format_func=_humanize_metric,
            key=f"{state_prefix}_{selected_module}_category_metric",
        )
        visible_categories = tuple(
            row
            for row in categories
            if row.metric_id == selected_category_metric
        )
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Metric": row.metric_id,
                        "Source / view": row.scope_id or "—",
                        "Weighting": row.weighting or "—",
                        "Category": row.category,
                        "Works with category": row.works_with_category,
                        "Eligible works": row.works_included,
                        "Prevalence": row.prevalence,
                        "Configuration": row.configuration_id,
                        "Note": row.note,
                    }
                    for row in visible_categories
                ]
            ).style.format({"Prevalence": "{:.1%}"}),
            hide_index=True,
            width="stretch",
        )

    if selected_module == "poetry_id":
        archetype_metrics = tuple(
            row
            for row in selected
            if row.metric_id == "poetry_id.categorical_archetype_id"
            and isinstance(row.value, str)
        )
        if archetype_metrics:
            st.markdown("**PoetryID corpus distribution**")
            compatible_groups = sorted(
                {
                    (row.scope_id, row.weighting)
                    for row in archetype_metrics
                }
            )
            selected_group = st.selectbox(
                "Compatible source, view, and weighting",
                options=compatible_groups,
                format_func=lambda item: (
                    f"{item[0].replace(':', ' · ')} · "
                    f"{item[1]} weighted"
                ),
                key=f"corpus_poetry_id_group_{project_id}",
            )
            group_rows = tuple(
                row
                for row in archetype_metrics
                if (row.scope_id, row.weighting) == selected_group
            )
            counts: dict[str, int] = {}
            for row in group_rows:
                archetype_id = str(row.value)
                counts[archetype_id] = counts.get(archetype_id, 0) + 1
            distribution_rows = [
                {
                    "Profile": ARCHETYPE_BY_ID[archetype_id].name,
                    "Works": count,
                    "Prevalence": count / len(group_rows),
                }
                for archetype_id, count in sorted(
                    counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
                if archetype_id in ARCHETYPE_BY_ID
            ]
            if distribution_rows:
                distribution_frame = pd.DataFrame(distribution_rows)
                st.bar_chart(
                    rounded_display_data(
                        distribution_frame.set_index("Profile")[["Works"]]
                    ),
                    height=260,
                )
                render_dataframe(
                    distribution_frame.style.format(
                        {"Prevalence": "{:.1%}"}
                    ),
                    hide_index=True,
                    width="stretch",
                )

            map_columns = st.columns(3)
            levels = (VadLevel.LOW, VadLevel.MODERATE, VadLevel.HIGH)
            for column, dominance in zip(
                map_columns,
                levels,
                strict=True,
            ):
                map_rows = []
                for arousal in reversed(levels):
                    map_row = {"Arousal": arousal.value.title()}
                    for valence in levels:
                        archetype = next(
                            item
                            for item in ARCHETYPE_BY_ID.values()
                            if item.valence_level == valence
                            and item.arousal_level == arousal
                            and item.dominance_level == dominance
                        )
                        count = counts.get(archetype.archetype_id, 0)
                        map_row[valence.value.title()] = (
                            f"{archetype.name.replace('The ', '')}: {count}"
                        )
                    map_rows.append(map_row)
                with column:
                    st.caption(f"{dominance.value.title()} dominance")
                    render_dataframe(
                        pd.DataFrame(map_rows).set_index("Arousal"),
                        width="stretch",
                    )

            numeric_by_work: dict[
                tuple[str, str, str],
                dict[str, object],
            ] = {}
            for row in selected:
                if (
                    row.scope_id,
                    row.weighting,
                ) != selected_group:
                    continue
                if row.metric_id not in {
                    "poetry_id.valence",
                    "poetry_id.arousal",
                    "poetry_id.dominance",
                    "poetry_id.categorical_archetype_name",
                }:
                    continue
                key = (row.text_id, row.scope_id, row.weighting)
                values = numeric_by_work.setdefault(
                    key,
                    {"Work": row.title},
                )
                values[row.metric_id.rsplit(".", 1)[-1].replace(
                    "categorical_archetype_name", "Profile"
                ).title()] = row.value
            scatter_rows = [
                row
                for row in numeric_by_work.values()
                if {"Valence", "Arousal", "Dominance"} <= set(row)
            ]
            if scatter_rows:
                st.markdown("**Continuous work-level VAD positions**")
                st.scatter_chart(
                    rounded_display_data(pd.DataFrame(scatter_rows)),
                    x="Valence",
                    y="Arousal",
                    size="Dominance",
                    color=(
                        "Profile"
                        if all("Profile" in row for row in scatter_rows)
                        else None
                    ),
                    height=380,
                )
                render_dataframe(
                    pd.DataFrame(scatter_rows),
                    hide_index=True,
                    width="stretch",
                )

            comparison_rows = _poetry_id_work_comparison_rows(
                selected,
                selected_group,
            )
            if comparison_rows:
                st.markdown(
                    "**Per-poem PoetryID archetypes**"
                )
                render_dataframe(
                    pd.DataFrame(comparison_rows),
                    hide_index=True,
                    width="stretch",
                    height=360,
                )
                st.caption(
                    "Category Fit is the primary threshold-based archetype. "
                    "Nearest Centroid is the secondary continuous-distance "
                    "candidate. Either is descriptive lexical evidence, not a "
                    "declaration of the poem's emotion or identity."
                )

            by_work_scope: dict[
                tuple[str, str],
                dict[str, str],
            ] = {}
            for row in archetype_metrics:
                by_work_scope.setdefault(
                    (row.text_id, row.scope_id),
                    {},
                )[row.weighting] = str(row.value)
            disagreements = [
                {
                    "Work": next(
                        row.title
                        for row in archetype_metrics
                        if row.text_id == text_id
                    ),
                    "Source / view": scope_id,
                    "Token profile": values["token"],
                    "Type profile": values["type"],
                }
                for (text_id, scope_id), values in by_work_scope.items()
                if (
                    "token" in values
                    and "type" in values
                    and values["token"] != values["type"]
                )
            ]
            if disagreements:
                st.markdown("**Token/type sensitivity**")
                render_dataframe(
                    pd.DataFrame(disagreements),
                    hide_index=True,
                    width="stretch",
                )
            st.caption(
                "Every distribution is filtered to one compatible VAD source, "
                "analysis view, weighting, threshold configuration, and completed "
                "batch. These are lexical-evidence distributions, not a "
                "corpus-wide emotional identity. Underlying chart values remain "
                "available in the corpus workbook and each work's CSV bundle."
            )

    if selected_module == "inherited_form":
        comparison_rows = _inherited_form_work_comparison_rows(selected)
        if comparison_rows:
            st.markdown(
                "**Per-poem inherited-form candidate comparison**"
            )
            render_dataframe(
                pd.DataFrame(comparison_rows).style.format(
                    {
                        "Consistency": "{:.1%}",
                        "Evidence coverage": "{:.1%}",
                        "Candidate margin": "{:.1%}",
                    },
                    na_rep="—",
                ),
                hide_index=True,
                width="stretch",
                height=360,
            )
            st.caption(
                "Potential matches compare each poem with the same comprehensive, "
                "versioned registry. Consistency measures agreement with "
                "available weighted evidence; coverage reports how much profile "
                "evidence was available. Confidence is not a probability. The "
                "stored profile CSV and Word report include each traditional "
                "definition, source links, and the poem's feature-level evidence."
            )

    pooled = tuple(
        row for row in aggregates if row.module_name == selected_module
    )
    if pooled:
        st.markdown("**Separately calculated collection aggregates**")
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Metric": row.metric_id,
                        "Method": row.aggregation_method,
                        "Value": heterogeneous_display_value(row.value),
                        "Unit": row.unit,
                        "Works included": row.works_included,
                        "Works omitted": row.works_omitted,
                        "Observations": row.observation_count,
                        "Note": row.note,
                    }
                    for row in pooled
                ]
            ),
            hide_index=True,
            width="stretch",
        )

    st.caption(
        "Detailed work, line, stanza, token, denominator, and warning records "
        "are intentionally omitted from this report view. They remain available "
        "in the corpus and per-work audit exports."
    )
    artifact_results = [
        row for row in results if row.module_name == selected_module
    ]
    if artifact_results:
        with st.expander("Download a Work's Module Audit Bundle"):
            chosen = st.selectbox(
                "Work",
                options=artifact_results,
                format_func=lambda row: row.title,
                key=(
                    f"{state_prefix}_artifact_{project_id}_{selected_module}"
                ),
            )
            try:
                archive = repository.build_module_artifact_zip(
                    chosen.run_id,
                    chosen.module_name,
                )
            except ValueError:
                st.info("This module did not produce separate audit files.")
            else:
                st.download_button(
                    "Download Module Audit ZIP",
                    data=archive,
                    file_name=(
                        f"{_safe_filename(chosen.title)}_"
                        f"{_safe_filename(chosen.module_name)}.zip"
                    ),
                    mime="application/zip",
                    key=(
                        f"{state_prefix}_download_{project_id}_"
                        f"{chosen.run_id}_{chosen.module_name}"
                    ),
                )
    return

    st.markdown("**Work, line, and stanza results**")
    scopes = sorted({row.scope for row in selected})
    selected_scopes = st.multiselect(
        "Result scopes",
        options=scopes,
        default=scopes,
        key=f"corpus_module_scopes_{project_id}_{selected_module}",
    )
    shown = [row for row in selected if row.scope in selected_scopes]
    render_dataframe(
        pd.DataFrame(
            [
                {
                    "Work": row.title,
                    "Collection": row.collection or "—",
                    "Author": row.author or "—",
                    "Date": row.date_label or "—",
                    "Genre": row.genre or "—",
                    "Scope": row.scope,
                    "Scope ID": row.scope_id or "—",
                    "Metric": row.metric_id,
                    "Value": heterogeneous_display_value(row.value),
                    "Unit": row.unit or "—",
                    "Weighting": row.weighting or "—",
                    "Denominator": row.denominator or "—",
                    "Observations": row.observation_count,
                    "Note": row.note or "—",
                }
                for row in shown
            ]
        ),
        hide_index=True,
        width="stretch",
        height=440,
    )

    selected_coverage = [
        row for row in coverage if row.module_name == selected_module
    ]
    if selected_coverage:
        with st.expander("Coverage and unmatched evidence"):
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Work": row.title,
                            "Coverage measure": row.coverage_id,
                            "Scope": row.scope,
                            "Eligible": row.eligible_count,
                            "Matched": row.matched_count,
                            "Unmatched": row.unmatched_count,
                            "Coverage": row.coverage_rate,
                            "Unit": row.unit,
                            "Unmatched items": ", ".join(
                                row.unmatched_items
                            ),
                            "Note": row.note,
                        }
                        for row in selected_coverage
                    ]
                ).style.format({"Coverage": "{:.1%}"}, na_rep="—"),
                hide_index=True,
                width="stretch",
            )

    selected_warnings = [
        row for row in warnings if row.module_name == selected_module
    ]
    if selected_warnings:
        st.markdown("#### Module Warnings")
        _render_corpus_warning_records(
            selected_warnings,
            summarize_shared=selected_text_id is None,
            control_id=f"{state_prefix}-{selected_module}-module-warnings",
        )

    artifact_results = [
        row for row in results if row.module_name == selected_module
    ]
    if artifact_results:
        with st.expander("Download a work's module audit bundle"):
            chosen = st.selectbox(
                "Work",
                options=artifact_results,
                format_func=lambda row: row.title,
                key=f"corpus_module_artifact_{project_id}_{selected_module}",
            )
            try:
                archive = repository.build_module_artifact_zip(
                    chosen.run_id,
                    chosen.module_name,
                )
            except ValueError:
                st.info("This module did not produce separate audit files.")
            else:
                st.download_button(
                    "Download module audit ZIP",
                    data=archive,
                    file_name=(
                        f"{_safe_filename(chosen.title)}_"
                        f"{_safe_filename(chosen.module_name)}.zip"
                    ),
                    mime="application/zip",
                    key=(
                        f"download_module_artifact_{project_id}_"
                        f"{chosen.run_id}_{chosen.module_name}"
                    ),
                )


def _render_corpus_warning_records(
    warnings,
    *,
    summarize_shared: bool,
    control_id: str,
) -> None:
    """Consolidate shared warnings while preserving poem-level audit detail."""

    detail_rows = [
        {
            "Poem": row.title,
            "Severity": row.severity.title(),
            "Code": row.code,
            "Message": row.message,
            "Technical Detail": row.technical_detail or "—",
        }
        for row in warnings
    ]
    if not summarize_shared:
        render_dataframe(
            pd.DataFrame(detail_rows),
            hide_index=True,
            width="stretch",
            height=min(380, 76 + len(detail_rows) * 35),
        )
        return

    grouped: dict[tuple[str, str, str, str], set[str]] = {}
    for row in warnings:
        grouped.setdefault(
            (
                row.severity.title(),
                row.code,
                row.message,
                row.technical_detail or "—",
            ),
            set(),
        ).add(row.title)
    summary_rows = []
    for (severity, code, message, technical_detail), titles in grouped.items():
        ordered_titles = sorted(titles, key=str.casefold)
        examples = ", ".join(ordered_titles[:3])
        if len(ordered_titles) > 3:
            examples += f" (+{len(ordered_titles) - 3} more)"
        summary_rows.append(
            {
                "Severity": severity,
                "Code": code,
                "Warning": message,
                "Affected Poems": len(ordered_titles),
                "Examples": examples,
                "Technical Detail": technical_detail,
            }
        )
    summary_rows.sort(
        key=lambda row: (
            str(row["Severity"]),
            str(row["Code"]),
            str(row["Warning"]),
        )
    )
    st.caption(
        f"{len(detail_rows):,} poem-level warning record(s) consolidated into "
        f"{len(summary_rows):,} distinct warning pattern(s)."
    )
    render_dataframe(
        pd.DataFrame(summary_rows),
        hide_index=True,
        width="stretch",
        height=min(360, 76 + len(summary_rows) * 35),
    )
    with bottom_collapsible_expander(
        "Poem-by-Poem Warning Records",
        control_id=control_id,
        expanded=False,
    ):
        render_dataframe(
            pd.DataFrame(detail_rows),
            hide_index=True,
            width="stretch",
            height=420,
        )


def _render_corpus_diagnostics(
    coverage,
    warnings,
    *,
    selected_text_id: str | None,
    state_prefix: str,
    selected_module_override: str | None = None,
) -> None:
    selected_coverage = tuple(
        row
        for row in coverage
        if selected_text_id is None or row.text_id == selected_text_id
    )
    selected_warnings = tuple(
        row
        for row in warnings
        if selected_text_id is None or row.text_id == selected_text_id
    )
    module_names = sorted(
        {row.module_name for row in selected_coverage}
        | {row.module_name for row in selected_warnings}
    )
    if not module_names:
        st.info("No coverage or warning records are available for this selection.")
        return
    module_name = selected_module_override
    if module_name is None:
        module_name = st.selectbox(
            "Analysis",
            options=module_names,
            format_func=lambda value: _CORPUS_MODULE_LABELS.get(
                value,
                value.replace("_", " ").title(),
            ),
            key=f"{state_prefix}_diagnostic_module",
        )
    module_coverage = tuple(
        row for row in selected_coverage if row.module_name == module_name
    )
    module_warnings = tuple(
        row for row in selected_warnings if row.module_name == module_name
    )
    if module_coverage:
        coverage_frame = pd.DataFrame(
            [
                {
                    "Poem": row.title,
                    "Measure": _humanize_metric(row.coverage_id),
                    "Scope": row.scope.replace("_", " ").title(),
                    "Eligible": row.eligible_count,
                    "Matched": row.matched_count,
                    "Unmatched": row.unmatched_count,
                    "Coverage": row.coverage_rate,
                    "Note": row.note or "—",
                }
                for row in module_coverage
                if row.scope == "document"
            ]
        )
        if coverage_frame.empty:
            st.info(
                "No poem-level coverage summary is available. Detailed coverage "
                "records remain in the export."
            )
        else:
            render_dataframe(
                coverage_frame.style.format(
                    {"Coverage": "{:.1%}"},
                    na_rep="—",
                ),
                hide_index=True,
                width="stretch",
                height=min(440, 76 + len(coverage_frame) * 35),
            )
    if module_warnings:
        st.markdown("#### Warnings")
        _render_corpus_warning_records(
            module_warnings,
            summarize_shared=selected_text_id is None,
            control_id=f"{state_prefix}-{module_name}-warnings",
        )
    elif not module_coverage:
        st.success("No warnings were recorded for this analysis.")
    st.caption(
        "Token- and item-level unmatched evidence remains available in the "
        "statistical and full-audit exports."
    )


@st.fragment
def _render_completed_corpus_results(
    repository: ProjectRepository,
    project_id: str,
    texts,
    latest_batch,
) -> None:
    st.divider()
    st.subheader("Completed Analysis Results")
    st.write(
        "Choose the whole corpus or one poem, then choose a familiar report "
        "family. The interface shows concise summaries and charts; complete "
        "statistical and audit records remain available from Export."
    )
    analyzed_text_ids = set(latest_batch.text_ids)
    scope_options = (
        (_WHOLE_CORPUS_SCOPE, "Whole Corpus"),
        *(
            (text.text_id, text.title)
            for text in texts
            if text.text_id in analyzed_text_ids
        ),
    )
    scope_labels = dict(scope_options)
    reports = []
    if latest_batch.lexicon_ids:
        reports.append("Affective Evidence")
    recorded_modules = set(latest_batch.module_names)
    for family, family_modules in _CORPUS_REPORT_MODULES.items():
        if recorded_modules.intersection(family_modules):
            reports.append(family)
    if recorded_modules:
        reports.append("Evidence & Diagnostics")
    reports = tuple(reports)
    if not reports:
        st.info("The completed batch contains no reportable results.")
        return
    controls = st.columns(2)
    scope_id = controls[0].selectbox(
        "Result Scope",
        options=tuple(scope_labels),
        format_func=lambda value: scope_labels[value],
        key=f"corpus_result_scope_{project_id}",
    )
    report_family = controls[1].selectbox(
        "Analysis Report",
        options=reports,
        key=f"corpus_result_family_{project_id}",
    )
    profile_state = render_report_profile_controls(
        f"corpus_{project_id}",
    )
    selected_text_id = (
        None if scope_id == _WHOLE_CORPUS_SCOPE else scope_id
    )
    if selected_text_id is None:
        st.caption(
            "Whole Corpus uses compatible collection summaries and equal-poem "
            "comparisons. It never treats the corpus as one concatenated poem."
        )
    else:
        selected_text = next(
            text for text in texts if text.text_id == selected_text_id
        )
        st.markdown(f"### {selected_text.title}")
        st.caption(
            f"{selected_text.author or 'Author not recorded'} · "
            "latest complete compatible corpus batch"
        )

    state_prefix = f"corpus_result_{project_id}_{scope_id}"
    if report_family == "Affective Evidence":
        render_content_word_scope_override(
            f"corpus_{project_id}",
            "emotion",
            profile_state.selection,
        )
        overridden_modules = active_override_modules(f"corpus_{project_id}")
        view_ids = {
            LexicalScope.ALL_LEXICAL: "all_matched",
            LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
            LexicalScope.CONTENT_WORDS: "content_words",
        }
        metrics = repository.list_latest_metrics(
            project_id,
            text_id=selected_text_id,
            analysis_views=tuple(
                view_ids[scope] for scope in profile_state.selection.scopes
            ),
            weightings=tuple(
                weighting.value.casefold()
                for weighting in profile_state.selection.weightings
            ),
            metrics=(
                "vad_mean",
                "vad_standard_deviation",
                *_VAD_LOAD_METRICS,
                *_VAD_VOLATILITY_METRICS,
            ),
        )
        _render_corpus_affective_report(
            metrics,
            selected_text_id=selected_text_id,
            state_prefix=state_prefix,
            profile_selection=profile_state.selection,
        )
        all_profile_metrics = repository.list_latest_metrics(
            project_id,
            text_id=selected_text_id,
        )
        for emotion_module in ("emotion_association", "emotion_intensity"):
            _render_canonical_corpus_module_profiles(
                all_profile_metrics,
                module_id=emotion_module,
                profile_selection=profile_state.selection,
                overridden_modules=overridden_modules,
                selected_text_id=selected_text_id,
            )
        return
    if report_family == "Evidence & Diagnostics":
        diagnostic_modules = tuple(
            module_name
            for module_name in latest_batch.module_names
            if module_name in _CORPUS_MODULE_LABELS
        )
        if not diagnostic_modules:
            st.info("No coverage or warning records are available for this batch.")
            return
        diagnostic_module = st.selectbox(
            "Analysis",
            options=diagnostic_modules,
            format_func=lambda value: _CORPUS_MODULE_LABELS.get(
                value, value.replace("_", " ").title()
            ),
            key=f"{state_prefix}_diagnostic_module",
        )
        module_coverage = repository.list_latest_module_coverage(
            project_id,
            text_id=selected_text_id,
            module_names=(diagnostic_module,),
            scopes=("document",),
        )
        module_warnings = repository.list_latest_module_warnings(
            project_id,
            text_id=selected_text_id,
            module_names=(diagnostic_module,),
        )
        _render_corpus_diagnostics(
            module_coverage,
            module_warnings,
            selected_text_id=selected_text_id,
            state_prefix=state_prefix,
            selected_module_override=diagnostic_module,
        )
        return
    if report_family == "VerseMap" and selected_text_id is None:
        st.caption(fixed_profile_notice("versemap"))
        _render_versemap_tab(repository, project_id)
        return
    fixed_modules = {
        "Sound & Form": ("pronunciation", "meter", "phonology", "inherited_form"),
        "Structure": ("structure",),
        "VerseMap": ("versemap",),
    }.get(report_family, ())
    for module_id in fixed_modules:
        st.caption(fixed_profile_notice(module_id))
    available_modules = tuple(
        module_name
        for module_name in latest_batch.module_names
        if module_name in _CORPUS_REPORT_MODULES[report_family]
    )
    if not available_modules:
        st.info("No compatible module results are available for this selection.")
        return
    selected_module = st.selectbox(
        "Analysis",
        options=available_modules,
        format_func=lambda value: _CORPUS_MODULE_LABELS.get(
            value, value.replace("_", " ").title()
        ),
        key=f"{state_prefix}_module_{project_id}",
    )
    override_group_by_module = {
        "concreteness": "concreteness",
        "frequency": "frequency",
        "lexical_frequency": "frequency",
        "aoa": "aoa",
        "age_of_acquisition": "aoa",
        "sensorimotor": "sensorimotor",
        "sensorimotor_imagery_and_embodiment": "sensorimotor",
    }
    override_group = override_group_by_module.get(selected_module)
    canonical_module_id = (
        {
            "lexical_frequency": "frequency",
            "age_of_acquisition": "aoa",
            "sensorimotor_imagery_and_embodiment": "sensorimotor",
        }.get(selected_module, selected_module)
        if override_group
        else ""
    )
    if override_group:
        render_content_word_scope_override(
            f"corpus_{project_id}",
            override_group,
            profile_state.selection,
        )
    overridden_modules = active_override_modules(f"corpus_{project_id}")
    module_metrics = repository.list_latest_module_metrics(
        project_id,
        text_id=selected_text_id,
        module_names=(selected_module,),
        scopes=("document",),
    )
    module_results = repository.list_latest_module_results(
        project_id,
        text_id=selected_text_id,
        module_names=(selected_module,),
    )
    module_aggregates = tuple(
        row
        for row in repository.list_latest_module_aggregates(project_id)
        if row.module_name == selected_module
    )
    scope_aware_rendered = False
    if canonical_module_id:
        scope_aware_rendered = _render_canonical_corpus_module_profiles(
            repository.list_latest_metrics(project_id, text_id=selected_text_id),
            module_id=canonical_module_id,
            profile_selection=profile_state.selection,
            overridden_modules=overridden_modules,
            selected_text_id=selected_text_id,
        )
    if scope_aware_rendered:
        module_metrics = tuple(
            row
            for row in module_metrics
            if corpus_metric_module_id(row.metric_id) != canonical_module_id
        )
        module_aggregates = tuple(
            row
            for row in module_aggregates
            if corpus_metric_module_id(row.metric_id) != canonical_module_id
        )
        if not module_metrics and not module_aggregates:
            return
        st.markdown("#### Additional Fixed or Structural Module Detail")
    _render_corpus_modules(
        repository,
        project_id,
        module_metrics,
        (),
        (),
        module_results,
        module_aggregates,
        allowed_modules=_CORPUS_REPORT_MODULES[report_family],
        selected_module_override=selected_module,
        selected_text_id=selected_text_id,
        state_prefix=state_prefix,
    )


def _render_analysis_tab(
    repository: ProjectRepository,
    project_id: str,
    preprocessor: TextPreprocessor,
    resource_readiness: ResourceReadiness,
    *,
    show_completed_results: bool = True,
) -> None:
    texts = repository.list_texts(project_id)
    if not texts:
        st.info("Import a folder of `.txt` works before running corpus analysis.")
        return
    st.subheader("Corpus Analysis Configuration")
    st.write(
        "VerseVAD analyzes one work at a time, preserving separate work-level results. "
        "The comparison dashboard updates only after every selected work finishes."
    )
    text_ids = st.multiselect(
        "Works to analyze",
        options=[text.text_id for text in texts],
        default=[text.text_id for text in texts],
        format_func=lambda text_id: next(text.title for text in texts if text.text_id == text_id),
        key=f"analysis_texts_{project_id}",
    )
    lexicon_lookup = {
        spec.lexicon_id: spec
        for spec in LEXICON_SPECS
        if spec.lexicon_id in resource_readiness.available_lexicon_ids
    }
    all_module_labels = {
        "concreteness": "Concreteness",
        "frequency": "SUBTLEX-US frequency and rarity",
        "aoa": "Age of acquisition",
        "sensorimotor": "Sensorimotor imagery and embodiment",
        "pronunciation": "Pronunciation and lexical stress",
        "meter": "Candidate meter and rhythmic regularity",
        "phonology": "Rhyme and phonological patterns",
        "lexical_style": (
            "Lexical diversity, word length, and structural word counts"
        ),
        "poetry_id": "PoetryID lexical-affective profiles",
        "inherited_form": "Inherited Form Analysis (comprehensive profile registry)",
        "versemap": "VerseMap comparative profile",
    }
    module_labels = {
        module_id: label
        for module_id, label in all_module_labels.items()
        if module_id in resource_readiness.available_module_ids
    }
    unavailable_module_labels = tuple(
        label
        for module_id, label in all_module_labels.items()
        if module_id not in resource_readiness.available_module_ids
    )
    if not lexicon_lookup or unavailable_module_labels:
        with st.expander("Unavailable analysis sources", expanded=False):
            if not lexicon_lookup:
                st.info(
                    "No validated affective lexicon is installed. Resource-free "
                    "lexical style remains available."
                )
            if unavailable_module_labels:
                st.write(
                    "Install the corresponding local resource before using: "
                    + ", ".join(unavailable_module_labels)
                    + "."
                )
            st.caption(
                "See docs/resource-installation.md for official download pages, "
                "exact filenames, and supported checksums."
            )
    available_custom_profiles = custom_profile_settings()
    builtin_profile_names = list(MODULE_PRESETS)
    profile_options = analysis_profile_options(builtin_profile_names)
    corpus_profile_state_key = f"corpus_preset_{project_id}"
    consume_pending_profile_selection(
        scope_key=f"corpus_{project_id}",
        selection_state_key=corpus_profile_state_key,
        options=profile_options,
    )
    if st.session_state.get(corpus_profile_state_key) not in profile_options:
        st.session_state[corpus_profile_state_key] = "Custom"
    preset_choice, preset_action = st.columns([3, 1], vertical_alignment="bottom")
    with preset_choice:
        selected_preset = st.selectbox(
            "Corpus analysis profile",
            options=profile_options,
            key=corpus_profile_state_key,
            help=(
                "Built-in and saved custom profiles update shared evidence "
                "selections after Apply / Restore."
            ),
        )
    with preset_action:
        apply_preset = st.button(
            "Apply / Restore",
            width="stretch",
            key=f"apply_corpus_preset_{project_id}",
        )
    if selected_preset in MODULE_PRESETS:
        st.caption(MODULE_PRESETS[selected_preset].description)
    elif selected_custom_profile_name(selected_preset) is not None:
        st.caption(
            "A saved custom configuration. Unsupported or unavailable corpus "
            "modules remain disabled."
        )
    if apply_preset:
        custom_name = selected_custom_profile_name(selected_preset)
        if custom_name is not None:
            preset_state = available_custom_profiles.get(custom_name, {})
        else:
            preset_state = preset_widget_state(
                selected_preset,
                available_lexicon_ids=tuple(lexicon_lookup),
            )
        if not preset_state:
            st.info("Custom keeps the current manual selections unchanged.")
            preset_state = None
        elif preset_state is not None:
            preset_state = normalize_profile_settings(preset_state)
        if preset_state is not None:
            st.session_state[f"analysis_lexicons_{project_id}"] = (
                preset_state.get("selected_lexicons", [])
            )
            st.session_state[f"analysis_modules_{project_id}"] = [
                module_name
                for state_key, module_name in (
                    _CORPUS_PROFILE_INCLUDE_TO_MODULE.items()
                )
                if (
                    preset_state.get(state_key) is True
                    and module_name in module_labels
                )
            ]
            for source_key, target_key in _corpus_profile_setting_keys(
                project_id
            ).items():
                if source_key in preset_state:
                    st.session_state[target_key] = preset_state[source_key]
            apply_profile_display_defaults(
                selected_preset,
                f"corpus_{project_id}",
            )
            st.rerun()
    render_custom_profile_manager(
        scope_key=f"corpus_{project_id}",
        selected_profile=selected_preset,
        selection_state_key=corpus_profile_state_key,
        current_settings=_corpus_profile_snapshot(project_id),
        builtin_profile_names=builtin_profile_names,
    )
    lexicon_state_key = f"analysis_lexicons_{project_id}"
    module_state_key = f"analysis_modules_{project_id}"
    if lexicon_state_key not in st.session_state:
        st.session_state[lexicon_state_key] = list(lexicon_lookup)
    else:
        available_lexicon_state = [
            lexicon_id
            for lexicon_id in st.session_state[lexicon_state_key]
            if lexicon_id in lexicon_lookup
        ]
        if available_lexicon_state != st.session_state[lexicon_state_key]:
            st.session_state[lexicon_state_key] = available_lexicon_state
    if module_state_key not in st.session_state:
        st.session_state[module_state_key] = []
    else:
        available_module_state = [
            module_id
            for module_id in st.session_state[module_state_key]
            if module_id in module_labels
        ]
        if available_module_state != st.session_state[module_state_key]:
            st.session_state[module_state_key] = available_module_state
    lexicon_ids = st.multiselect(
        "Lexicons",
        options=list(lexicon_lookup),
        format_func=lambda lexicon_id: lexicon_lookup[lexicon_id].display_name,
        key=lexicon_state_key,
    )
    selected_modules = st.multiselect(
        "Additional analysis modules",
        options=list(module_labels),
        format_func=lambda name: module_labels[name],
        key=module_state_key,
        help=(
            "These call the same tested modules used in the one-poem workspace. "
            "They are optional because pronunciation, meter, and rhyme can add "
            "substantial processing time to a large corpus."
        ),
    )
    scenarios = repository.list_review_scenarios(project_id)
    scenario_by_version = {
        scenario.scenario_version_id: scenario for scenario in scenarios
    }
    scenario_version_id = st.selectbox(
        "Review scenario",
        options=["", *scenario_by_version],
        format_func=lambda value: (
            "Unreviewed baseline — no review decisions"
            if not value
            else (
                f"{scenario_by_version[value].name} "
                f"(version {scenario_by_version[value].version_number}, "
                f"{scenario_by_version[value].decision_count} decision revisions)"
            )
        ),
        key=f"analysis_scenario_{project_id}",
        help=(
            "A scenario applies only its pinned decision revisions. Running it creates "
            "new immutable analyses; it never changes the baseline batch."
        ),
    )
    concreteness_exclude_proper_nouns = False
    sensorimotor_exclude_proper_nouns = False
    frequency_exclude_proper_nouns = False
    frequency_content_words_only = False
    aoa_exclude_proper_nouns = False
    aoa_content_words_only = False
    poetry_id_sources: tuple[str, ...] = ()
    poetry_id_weightings: tuple[str, ...] = ("token", "type")
    poetry_id_views: tuple[str, ...] = (
        "all_matched",
        "stopwords_excluded",
    )
    poetry_id_lexical_dimensions: tuple[str, ...] = ()
    poetry_id_threshold_profile = PoetryIDConfiguration().threshold_profile
    poetry_id_configuration_error = ""
    meter_defaults = MeterConfiguration(
        analysis_mode=MeterAnalysisMode.COMPARE_BOTH
    )
    meter_analysis_mode = MeterAnalysisMode.COMPARE_BOTH
    meter_style_profile = MeterStyleProfile.GENERAL
    meter_interpretation_depth = MeterInterpretationDepth.STANDARD
    meter_line_match_threshold = meter_defaults.line_match_threshold
    meter_irregular_threshold = meter_defaults.irregular_fit_threshold
    meter_ambiguity_margin = meter_defaults.ambiguity_margin_threshold
    meter_maximum_variants = meter_defaults.maximum_line_variants
    meter_performance_candidate_limit = (
        meter_defaults.performance_candidate_limit
    )
    meter_realized_alternatives = (
        meter_defaults.retained_realized_alternatives
    )
    meter_allow_visible_elision = False
    meter_scholar_revisions_text = ""
    with st.expander("Advanced batch methodology"):
        policies = {
            "Prefer the longest phrase (recommended)": PhrasePolicy.PHRASE_PREFERRED,
            "Use unigrams only": PhrasePolicy.UNIGRAM_ONLY,
            "Count phrases and components (exploratory)": PhrasePolicy.PHRASE_AND_COMPONENT,
        }
        policy_label = st.selectbox(
            "Phrase policy",
            options=list(policies),
            key=f"corpus_policy_{project_id}",
        )
        minimum = st.number_input(
            "Minimum matched observations before a VAD result is marked non-sparse",
            min_value=1,
            max_value=100,
            value=3,
            key=f"corpus_minimum_{project_id}",
        )
        st.markdown("**Proper-noun eligibility**")
        proper_noun_columns = st.columns(4)
        concreteness_exclude_proper_nouns = proper_noun_columns[0].checkbox(
            "Concreteness: exclude proper nouns",
            value=False,
            key=f"corpus_concreteness_exclude_proper_{project_id}",
            disabled="concreteness" not in selected_modules,
        )
        sensorimotor_exclude_proper_nouns = proper_noun_columns[1].checkbox(
            "Sensorimotor: exclude proper nouns",
            value=False,
            key=f"corpus_sensorimotor_exclude_proper_{project_id}",
            disabled="sensorimotor" not in selected_modules,
        )
        frequency_exclude_proper_nouns = proper_noun_columns[2].checkbox(
            "Frequency: exclude proper nouns",
            value=False,
            key=f"corpus_frequency_exclude_proper_{project_id}",
            disabled="frequency" not in selected_modules,
        )
        aoa_exclude_proper_nouns = proper_noun_columns[3].checkbox(
            "AoA: exclude proper nouns",
            value=False,
            key=f"corpus_aoa_exclude_proper_{project_id}",
            disabled="aoa" not in selected_modules,
        )
        if (
            "meter" in selected_modules
            or "inherited_form" in selected_modules
        ):
            st.markdown("**Meter batch settings**")
            meter_columns = st.columns(3)
            meter_mode_label = meter_columns[0].selectbox(
                "Meter analysis level",
                options=list(METER_MODE_LABELS),
                index=(
                    0
                    if f"corpus_meter_mode_{project_id}" in st.session_state
                    else list(METER_MODE_LABELS).index(
                        "Compare candidate and performance-aware readings"
                    )
                ),
                key=f"corpus_meter_mode_{project_id}",
            )
            meter_analysis_mode = METER_MODE_LABELS[meter_mode_label]
            meter_style_label = meter_columns[1].selectbox(
                "Declared interpretation profile",
                options=list(METER_STYLE_LABELS),
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                key=f"corpus_meter_style_{project_id}",
            )
            meter_style_profile = METER_STYLE_LABELS[meter_style_label]
            meter_depth_label = meter_columns[2].selectbox(
                "Interpretation detail",
                options=list(METER_DEPTH_LABELS),
                index=1,
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                key=f"corpus_meter_depth_{project_id}",
            )
            meter_interpretation_depth = METER_DEPTH_LABELS[
                meter_depth_label
            ]
            meter_threshold_columns = st.columns(4)
            meter_line_match_threshold = meter_threshold_columns[0].number_input(
                "Meter line-fit threshold",
                0.0,
                1.0,
                meter_defaults.line_match_threshold,
                0.05,
                key=f"corpus_meter_line_threshold_{project_id}",
            )
            meter_irregular_threshold = meter_threshold_columns[1].number_input(
                "Poem candidate-fit threshold",
                0.0,
                1.0,
                meter_defaults.irregular_fit_threshold,
                0.05,
                key=f"corpus_meter_poem_threshold_{project_id}",
            )
            meter_ambiguity_margin = meter_threshold_columns[2].number_input(
                "Candidate margin threshold",
                0.0,
                1.0,
                meter_defaults.ambiguity_margin_threshold,
                0.01,
                key=f"corpus_meter_margin_{project_id}",
            )
            meter_maximum_variants = int(
                meter_threshold_columns[3].number_input(
                    "Maximum stress paths per line",
                    1,
                    4096,
                    meter_defaults.maximum_line_variants,
                    1,
                    key=f"corpus_meter_variants_{project_id}",
                )
            )
            meter_limit_columns = st.columns(3)
            meter_performance_candidate_limit = int(
                meter_limit_columns[0].number_input(
                    "Realization candidates per line",
                    min_value=2,
                    max_value=40,
                    value=meter_defaults.performance_candidate_limit,
                    step=1,
                    disabled=(
                        meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                    ),
                    key=f"corpus_meter_candidate_limit_{project_id}",
                )
            )
            meter_realized_alternatives = int(
                meter_limit_columns[1].number_input(
                    "Retained realized alternatives",
                    min_value=1,
                    max_value=8,
                    value=meter_defaults.retained_realized_alternatives,
                    step=1,
                    disabled=(
                        meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                    ),
                    key=f"corpus_meter_alternatives_{project_id}",
                )
            )
            meter_allow_visible_elision = meter_limit_columns[2].checkbox(
                "Recognize visibly marked contractions",
                value=False,
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                key=f"corpus_meter_elision_{project_id}",
            )
            meter_scholar_revisions_text = st.text_area(
                "Scholar scansion revisions",
                value="",
                key=f"corpus_meter_scholar_revisions_{project_id}",
                height=100,
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                placeholder=(
                    "line 2 = iambic pentameter | "
                    "x / x / x / x / x / | reason for the revised reading"
                ),
                help=(
                    "Optional. The same line-number revisions are applied "
                    "separately to every selected work; use only when they are "
                    "meaningful across the batch."
                ),
            )
            st.caption(
                "Every work uses the same declared profile and exact configuration. "
                "Source lexical stress remains unchanged. When Inherited Form "
                "Analysis is selected, these meter results become one transparent "
                "evidence layer in the form ranking."
            )
        if "inherited_form" in selected_modules:
            st.markdown("**Inherited-form batch settings**")
            st.caption(
                "All ten version-1 profiles will be ranked for every work. "
                "Pronunciation, meter, and graded rhyme run automatically; "
                "missing dependent evidence lowers coverage rather than becoming "
                "a failed feature. Traditional definitions and source links are "
                "included in each stored CSV and Word export."
            )
        if "poetry_id" in selected_modules:
            st.markdown("**PoetryID batch settings**")
            eligible_sources = [
                lexicon_id
                for lexicon_id in lexicon_ids
                if lexicon_id in SUPPORTED_VAD_LEXICON_IDS
            ]
            poetry_id_sources = tuple(
                st.multiselect(
                    "PoetryID VAD sources",
                    options=eligible_sources,
                    default=eligible_sources,
                    format_func=lambda lexicon_id: lexicon_lookup[
                        lexicon_id
                    ].display_name,
                    key=f"corpus_poetry_id_sources_{project_id}",
                    help=(
                        "Every source remains separate; no consensus VAD "
                        "profile is calculated."
                    ),
                )
            )
            poetry_id_weightings = ("token", "type")
            poetry_id_views = (
                "all_matched",
                "stopwords_excluded",
                "content_words",
            )
            character_options = [
                dimension
                for dimension, module_name in (
                    ("concreteness", "concreteness"),
                    ("frequency", "frequency"),
                    ("age_of_acquisition", "aoa"),
                )
                if module_name in selected_modules
            ]
            poetry_id_lexical_dimensions = tuple(
                st.multiselect(
                    "Secondary PoetryID lexical character",
                    options=character_options,
                    default=character_options,
                    format_func=lambda value: value.replace(
                        "_", " "
                    ).title(),
                    key=f"corpus_poetry_id_character_{project_id}",
                )
            )
            custom_thresholds = st.checkbox(
                "Use custom fixed VAD thresholds for this batch",
                value=False,
                key=f"corpus_poetry_id_custom_{project_id}",
            )
            threshold_values = {}
            threshold_columns = st.columns(3)
            for column, dimension in zip(
                threshold_columns,
                ("valence", "arousal", "dominance"),
                strict=True,
            ):
                with column:
                    low_max = st.number_input(
                        f"{dimension.title()} low maximum",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.4,
                        step=0.01,
                        disabled=not custom_thresholds,
                        key=(
                            f"corpus_poetry_id_{dimension}_low_"
                            f"{project_id}"
                        ),
                    )
                    high_min = st.number_input(
                        f"{dimension.title()} high minimum",
                        min_value=0.01,
                        max_value=1.0,
                        value=0.6,
                        step=0.01,
                        disabled=not custom_thresholds,
                        key=(
                            f"corpus_poetry_id_{dimension}_high_"
                            f"{project_id}"
                        ),
                    )
                    threshold_values[dimension] = (
                        float(low_max),
                        float(high_min),
                    )
            if custom_thresholds:
                try:
                    poetry_id_threshold_profile = ThresholdProfile(
                        profile_id="custom_fixed_corpus_ui",
                        name="Custom Fixed Corpus Thresholds",
                        method="fixed",
                        dimensions={
                            dimension: ThresholdBand(low_max, high_min)
                            for dimension, (
                                low_max,
                                high_min,
                            ) in threshold_values.items()
                        },
                        configuration_version=(
                            "poetry-id-custom-fixed-corpus-v1"
                        ),
                        built_in=False,
                    )
                except ValueError as error:
                    poetry_id_configuration_error = str(error)
                    st.warning(poetry_id_configuration_error)
    with st.expander("Stopword settings"):
        st.info(
            "Stopword exclusion changes only the secondary VAD view. Matching, "
            "the complete analysis, and the token audit remain intact."
        )
        stopword_settings = render_stopword_settings(f"corpus_{project_id}")
    run = st.button(
        "Analyze Corpus",
        type="primary",
        disabled=(
            not text_ids
            or (not lexicon_ids and not selected_modules)
            or (
                "poetry_id" in selected_modules
                and (
                    not poetry_id_sources
                    or not poetry_id_weightings
                    or not poetry_id_views
                    or bool(poetry_id_configuration_error)
                )
            )
        ),
        key=f"analyze_corpus_{project_id}",
    )
    if run:
        progress_bar = st.progress(0.0, text="Preparing corpus batch…")

        def update_progress(completed: int, total: int, title: str) -> None:
            progress_bar.progress(
                completed / total if total else 0.0,
                text=f"{completed:,}/{total:,} complete — {title}",
            )

        try:
            module_configuration = CorpusAnalysisConfiguration(
                include_concreteness="concreteness" in selected_modules,
                concreteness_configuration=ConcretenessConfiguration(
                    exclude_proper_nouns=(
                        concreteness_exclude_proper_nouns
                    )
                ),
                include_frequency="frequency" in selected_modules,
                frequency_configuration=FrequencyConfiguration(
                    exclude_proper_nouns=frequency_exclude_proper_nouns,
                    content_words_only=frequency_content_words_only
                ),
                include_aoa="aoa" in selected_modules,
                aoa_configuration=AoAConfiguration(
                    exclude_proper_nouns=aoa_exclude_proper_nouns,
                    content_words_only=aoa_content_words_only
                ),
                include_sensorimotor="sensorimotor" in selected_modules,
                sensorimotor_configuration=SensorimotorConfiguration(
                    exclude_proper_nouns=(
                        sensorimotor_exclude_proper_nouns
                    )
                ),
                include_pronunciation="pronunciation" in selected_modules,
                include_meter="meter" in selected_modules,
                meter_configuration=MeterConfiguration(
                    line_match_threshold=float(meter_line_match_threshold),
                    irregular_fit_threshold=float(meter_irregular_threshold),
                    ambiguity_margin_threshold=float(meter_ambiguity_margin),
                    maximum_line_variants=int(meter_maximum_variants),
                    analysis_mode=meter_analysis_mode,
                    style_profile=meter_style_profile,
                    interpretation_depth=meter_interpretation_depth,
                    performance_candidate_limit=(
                        meter_performance_candidate_limit
                    ),
                    retained_realized_alternatives=(
                        meter_realized_alternatives
                    ),
                    allow_visible_poetic_elision=(
                        meter_allow_visible_elision
                    ),
                    scholar_revisions=(
                        ()
                        if meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                        else parse_meter_scholar_revisions(
                            meter_scholar_revisions_text
                        )
                    ),
                ),
                include_phonology="phonology" in selected_modules,
                include_lexical_style="lexical_style" in selected_modules,
                include_poetry_id="poetry_id" in selected_modules,
                poetry_id_configuration=PoetryIDConfiguration(
                    threshold_profile=poetry_id_threshold_profile,
                    weighting_modes=poetry_id_weightings,
                    analysis_views=poetry_id_views,
                    vad_lexicon_ids=poetry_id_sources,
                    requested_lexical_dimensions=(
                        poetry_id_lexical_dimensions
                    ),
                ),
                include_inherited_form=(
                    "inherited_form" in selected_modules
                ),
                inherited_form_configuration=(
                    InheritedFormConfiguration()
                ),
                include_versemap="versemap" in selected_modules,
                versemap_configuration=VerseMapConfiguration(),
                analysis_cache_enabled=st.session_state.get(
                    "analysis_cache_enabled",
                    True,
                ),
                performance_diagnostics=st.session_state.get(
                    "performance_diagnostics_enabled",
                    True,
                ),
            )
            batch = analyze_corpus(
                repository,
                project_id,
                lexicon_ids=tuple(lexicon_ids),
                text_ids=tuple(text_ids),
                phrase_policy=policies[policy_label],
                minimum_match_requirement=int(minimum),
                stopword_mode=stopword_settings.mode,
                protected_stopwords=stopword_settings.protected_words,
                custom_stopword_additions=stopword_settings.custom_additions,
                custom_stopword_removals=stopword_settings.custom_removals,
                scenario_version_id=scenario_version_id,
                preprocessor=preprocessor,
                progress=update_progress,
                module_configuration=module_configuration,
            )
            progress_bar.progress(1.0, text="Corpus analysis complete")
            st.success(
                f"Completed immutable {'reviewed' if scenario_version_id else 'baseline'} "
                f"batch {batch.batch_id}. Comparisons now use this internally consistent run."
            )
            st.rerun()
        except Exception as error:
            st.error(
                "The corpus batch did not complete, so it was not published to the comparison dashboard. "
                f"Technical detail: {error}"
            )

    if not show_completed_results:
        return

    completed_batches = repository.list_completed_batches(project_id)
    if not completed_batches:
        st.info("No complete corpus batch is available yet.")
        return
    _render_completed_corpus_results(
        repository,
        project_id,
        texts,
        completed_batches[0],
    )
    _render_batch_comparison(repository, project_id)
    return
    if module_metrics:
        st.divider()
        _render_corpus_modules(
            repository,
            project_id,
            module_metrics,
            module_coverage,
            module_warnings,
            module_results,
            module_aggregates,
        )
    if not metrics:
        return
    st.divider()
    st.subheader("Filter the Completed Comparison Batch")
    collections = sorted({row.collection or "(unassigned)" for row in metrics})
    authors = sorted({row.author or "(unassigned)" for row in metrics})
    genres = sorted({row.genre or "(unassigned)" for row in metrics})
    filter_columns = st.columns(3)
    selected_collections = filter_columns[0].multiselect(
        "Collections",
        options=collections,
        default=collections,
        key=f"filter_collections_{project_id}",
    )
    selected_authors = filter_columns[1].multiselect(
        "Authors",
        options=authors,
        default=authors,
        key=f"filter_authors_{project_id}",
    )
    selected_genres = filter_columns[2].multiselect(
        "Genres",
        options=genres,
        default=genres,
        key=f"filter_genres_{project_id}",
    )
    metrics = tuple(
        row
        for row in metrics
        if (row.collection or "(unassigned)") in selected_collections
        and (row.author or "(unassigned)") in selected_authors
        and (row.genre or "(unassigned)") in selected_genres
    )
    if not metrics:
        st.info("No completed work matches these metadata filters.")
        return
    view_labels = {
        "all_matched": "All matched tokens",
        "stopwords_excluded": "Stopwords excluded",
    }
    available_views = [
        view
        for view in ("all_matched", "stopwords_excluded")
        if any(row.analysis_view == view for row in metrics)
    ]
    selected_views = st.multiselect(
        "Affective result views",
        options=available_views,
        default=available_views,
        format_func=lambda value: view_labels[value],
        key=f"comparison_analysis_views_{project_id}",
        help="Keep both selected to compare full and stopword-excluded results together.",
    )
    metrics = tuple(row for row in metrics if row.analysis_view in selected_views)
    if not metrics:
        st.info("Select at least one affective result view.")
        return
    _render_profiles(metrics, len({row.text_id for row in metrics}))

    st.subheader("Compare Individual Works")
    vad = corpus_vad_work_comparisons(metrics)
    if vad:
        selected_lexicon = st.selectbox(
            "Comparison lexicon",
            options=sorted({row.lexicon for row in vad}),
            key=f"comparison_lexicon_{project_id}",
        )
        selected_weighting = st.radio(
            "Within-work weighting",
            options=["token", "type"],
            format_func=lambda value: (
                "Token-weighted — repetitions count"
                if value == "token"
                else "Type-weighted — each matched entry counts once"
            ),
            horizontal=True,
            key=f"comparison_weighting_{project_id}",
        )
        chosen = tuple(
            row
            for row in vad
            if row.lexicon == selected_lexicon and row.weighting == selected_weighting
        )
        work_rows: dict[tuple[str, str], dict[str, object]] = {}
        for row in chosen:
            key = (row.text_id, row.analysis_view)
            values = work_rows.setdefault(
                key,
                {
                    "Work": row.title,
                    "Collection": row.collection,
                    "Analysis view": view_labels[row.analysis_view],
                    "Matched observations": row.observations,
                    "Coverage": row.coverage,
                },
            )
            dimension = row.dimension.title()
            values[f"{dimension} mean"] = row.mean
            values[f"{dimension} SD"] = row.population_standard_deviation
        comparison_columns = [
            "Work",
            "Collection",
            "Analysis view",
            "Valence mean",
            "Valence SD",
            "Arousal mean",
            "Arousal SD",
            "Dominance mean",
            "Dominance SD",
            "Matched observations",
            "Coverage",
        ]
        comparison_rows = sorted(
            work_rows.values(),
            key=lambda row: (
                str(row["Work"]).casefold(),
                str(row["Analysis view"]),
            ),
        )
        comparison_frame = pd.DataFrame(
            comparison_rows,
            columns=comparison_columns,
        )
        render_dataframe(
            comparison_frame.style.format(
                {
                    "Valence mean": "{:.3f}",
                    "Valence SD": "{:.3f}",
                    "Arousal mean": "{:.3f}",
                    "Arousal SD": "{:.3f}",
                    "Dominance mean": "{:.3f}",
                    "Dominance SD": "{:.3f}",
                    "Coverage": "{:.1%}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Each SD is the population standard deviation of included matched "
            "lexical ratings within that poem, source, view, dimension, and "
            "weighting. It is descriptive spread, not a confidence interval or "
            "variability among poems."
        )
        if {"all_matched", "stopwords_excluded"}.issubset(
            {row.analysis_view for row in chosen}
        ):
            work_frame = pd.DataFrame(
                [
                    {
                        "Work": row.title,
                        "Collection": row.collection,
                        "Analysis view": view_labels[row.analysis_view],
                        "Dimension": row.dimension.title(),
                        "Mean": row.mean,
                    }
                    for row in chosen
                ]
            )
            sensitivity = (
                work_frame.pivot_table(
                    index=["Work", "Collection", "Dimension"],
                    columns="Analysis view",
                    values="Mean",
                    aggfunc="first",
                )
                .reset_index()
            )
            if {
                "All matched tokens",
                "Stopwords excluded",
            }.issubset(sensitivity.columns):
                sensitivity["Difference"] = (
                    sensitivity["Stopwords excluded"]
                    - sensitivity["All matched tokens"]
                )
                st.markdown("**Stopword sensitivity by work**")
                render_dataframe(
                    sensitivity.style.format(
                        {
                            "All matched tokens": "{:.3f}",
                            "Stopwords excluded": "{:.3f}",
                            "Difference": "{:+.3f}",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

    st.subheader("Cumulative and Length-Normalized Load by Work")
    st.write(
        "Raw sums grow with included matched vocabulary and repetition. "
        "Per-observation and per-100 rows divide by matched tokens or types for comparable rates; "
        "none estimates a reader's psychological response."
    )
    load_rows = [row for row in metrics if row.metric in _VAD_LOAD_METRICS]
    if load_rows:
        load_frame = pd.DataFrame(
            [
                {
                    "Work": row.title,
                    "Collection": row.collection,
                    "Lexicon": row.lexicon,
                    "Analysis view": view_labels[row.analysis_view],
                    "Dimension": row.dimension.title(),
                    "Measure": row.metric.replace("vad_", "").replace("_", " ").title(),
                    "Value": row.value,
                    "Matched observations": row.observations,
                    "Coverage": row.coverage,
                }
                for row in load_rows
            ]
        )
        render_dataframe(
            load_frame.style.format({"Value": "{:.3f}", "Coverage": "{:.1%}"}),
            hide_index=True,
            width="stretch",
            height=380,
        )
    volatility_rows = [
        row for row in metrics if row.metric in _VAD_VOLATILITY_METRICS
    ]
    if volatility_rows:
        st.subheader("Mean-Centered Lexical Volatility by Work")
        volatility_frame = pd.DataFrame(
            [
                {
                    "Work": row.title,
                    "Collection": row.collection,
                    "Lexicon": row.lexicon,
                    "Analysis view": view_labels[row.analysis_view],
                    "Dimension": row.dimension.title(),
                    "Average Deviation from Poem Mean": row.value,
                    "Matched observations": row.observations,
                    "Coverage": row.coverage,
                }
                for row in volatility_rows
            ]
        )
        render_dataframe(
            volatility_frame.style.format(
                {
                    "Average Deviation from Poem Mean": "{:.3f}",
                    "Coverage": "{:.1%}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
            height=380,
        )
        st.caption(
            "Mean absolute deviation weights departures from each poem's own VAD "
            "mean linearly. Population SD emphasizes unusually large departures."
        )
    _render_batch_comparison(repository, project_id)


def _render_batch_comparison(
    repository: ProjectRepository,
    project_id: str,
) -> None:
    batches = repository.list_completed_batches(project_id)
    if len(batches) < 2:
        return
    st.divider()
    st.subheader("Compare Two Immutable Analysis Batches")
    st.write(
        "Use this to compare an untouched baseline with a reviewed scenario, or "
        "two different scenario versions. Only like-for-like metrics are subtracted."
    )
    if not st.toggle(
        "Load batch comparison",
        value=False,
        key=f"load_batch_comparison_{project_id}",
        help=(
            "Batch comparison can load many stored rows. Leave this off while "
            "moving between ordinary report sections."
        ),
    ):
        st.caption(
            "Turn this on only when you want to compare two immutable analysis batches."
        )
        return

    def label(batch_id: str) -> str:
        batch = next(item for item in batches if item.batch_id == batch_id)
        if batch.scenario_version_id:
            try:
                scenario = repository.get_review_scenario_version(
                    batch.scenario_version_id
                )
                scenario_label = f"{scenario.name} v{scenario.version_number}"
            except KeyError:
                scenario_label = batch.scenario_version_id
        else:
            scenario_label = "Unreviewed baseline"
        completed = (batch.completed_at or batch.created_at)[:19]
        return f"{scenario_label} — {completed} — {batch.batch_id}"

    batch_ids = [batch.batch_id for batch in batches]
    defaults = (
        next(
            (
                index
                for index, batch in enumerate(batches)
                if not batch.scenario_version_id
            ),
            min(1, len(batches) - 1),
        ),
        next(
            (
                index
                for index, batch in enumerate(batches)
                if batch.scenario_version_id
            ),
            0,
        ),
    )
    columns = st.columns(2)
    baseline_id = columns[0].selectbox(
        "Reference batch",
        options=batch_ids,
        index=defaults[0],
        format_func=label,
        key=f"scenario_reference_batch_{project_id}",
    )
    reviewed_id = columns[1].selectbox(
        "Comparison batch",
        options=batch_ids,
        index=defaults[1],
        format_func=label,
        key=f"scenario_comparison_batch_{project_id}",
    )
    if baseline_id == reviewed_id:
        st.info("Choose two different batches to calculate changes.")
        return
    deltas = corpus_scenario_deltas(
        repository.list_metrics_for_batch(project_id, baseline_id),
        repository.list_metrics_for_batch(project_id, reviewed_id),
    )
    primary = [
        row
        for row in deltas
        if (
            row.metric == "coverage"
            or (row.metric == "vad_mean" and row.scale == "normalized_0_1")
        )
    ]
    if not primary:
        st.info(
            "These batches have no directly compatible coverage or normalized VAD means."
        )
        return
    frame = pd.DataFrame(
        [
            {
                "Work": row.title,
                "Lexicon": row.lexicon,
                "Analysis view": (
                    "All matched tokens"
                    if row.analysis_view == "all_matched"
                    else "Stopwords excluded"
                ),
                "Measure": (
                    "Coverage"
                    if row.metric == "coverage"
                    else f"{row.dimension.title()} mean ({row.weighting})"
                ),
                "Reference": row.baseline_value,
                "Comparison": row.reviewed_value,
                "Difference": row.difference,
            }
            for row in primary
        ]
    )
    render_dataframe(
        frame.style.format(
            {
                "Reference": "{:.3f}",
                "Comparison": "{:.3f}",
                "Difference": "{:+.3f}",
            }
        ),
        hide_index=True,
        width="stretch",
        height=380,
    )
    st.caption(
        "A difference is descriptive sensitivity to the recorded review decisions; "
        "it is not evidence that either scenario is universally correct."
    )


def _render_project_settings_tab(
    repository: ProjectRepository,
    project_id: str,
) -> None:
    project = repository.get_project(project_id)
    confirmation_key = f"delete_project_confirmation_{project_id}"
    st.subheader("Project Settings")
    st.warning(
        "Deleting this project permanently removes only this project's imported "
        "texts, preserved versions, completed analyses, corpus batches, and "
        "quality-control notes, review decisions, and scenario history from the "
        "local VerseVAD database. Other projects are not affected."
    )
    confirmation = st.text_input(
        f'Type the exact project title to confirm: "{project.title}"',
        key=confirmation_key,
    )

    def delete_confirmed_project() -> None:
        st.session_state["_pending_corpus_project_delete"] = (
            project_id,
            project.title,
            str(st.session_state.get(confirmation_key, "")),
        )

    st.button(
        "Delete this project",
        type="primary",
        disabled=confirmation != project.title,
        key=f"delete_project_{project_id}",
        on_click=delete_confirmed_project,
    )


def _clear_deleted_project_state(project_id: str) -> None:
    """Remove only session state owned by a successfully deleted project."""

    for key, value in tuple(st.session_state.items()):
        if key == "active_corpus_project" and value == project_id:
            st.session_state.pop(key, None)
        elif project_id in str(key):
            st.session_state.pop(key, None)


def _render_review_tab(
    repository: ProjectRepository,
    project_id: str,
) -> None:
    st.subheader("Review Decisions and Named Scenarios")
    st.write(
        "The baseline always remains untouched. A scenario is a versioned set of "
        "explicit flags, exclusions, and mappings. Every change creates a new "
        "scenario version, and every rerun creates new immutable analysis records."
    )
    st.info(
        "**Flag** records a concern without changing scores. **Exclude** removes a "
        "published candidate only from that scenario's aggregates. **Map** connects "
        "an otherwise unmatched token to one exact published entry; VerseVAD never "
        "chooses the target automatically."
    )
    with st.expander("Create a named review scenario"):
        with st.form(f"create_review_scenario_{project_id}", clear_on_submit=True):
            name = st.text_input(
                "Scenario name",
                placeholder="Example: Conservative reviewed analysis",
            )
            description = st.text_area(
                "Purpose and methodological boundary",
                placeholder=(
                    "Example: Includes only mappings verified against the selected edition."
                ),
                height=90,
            )
            create = st.form_submit_button("Create review scenario", type="primary")
        if create:
            try:
                repository.create_review_scenario(
                    project_id,
                    name,
                    description=description,
                )
                st.success("Review scenario created with an empty version 1.")
                st.rerun()
            except (KeyError, ValueError) as error:
                st.error(f"The scenario was not created: {error}")

    scenarios = repository.list_review_scenarios(project_id)
    if not scenarios:
        st.caption(
            "Create a scenario to turn quality-control observations into reversible "
            "analysis decisions. Unmatched notes remain available below."
        )
        with st.expander("Documentation-only unmatched notes"):
            _render_qc_tab(repository, project_id)
        return
    scenario_id = st.selectbox(
        "Scenario to edit",
        options=[scenario.scenario_id for scenario in scenarios],
        format_func=lambda value: next(
            (
                f"{scenario.name} — version {scenario.version_number}"
                for scenario in scenarios
                if scenario.scenario_id == value
            ),
            value,
        ),
        key=f"review_scenario_{project_id}",
    )
    scenario = repository.get_review_scenario(scenario_id)
    st.caption(
        f"Current immutable snapshot: version {scenario.version_number} · "
        f"{scenario.decision_count} pinned decision revision(s). "
        f"{scenario.description or 'No description recorded.'}"
    )

    decisions = repository.list_review_decisions(scenario.scenario_version_id)
    if decisions:
        st.markdown("**Pinned decisions in this version**")
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "State": decision.state,
                        "Action": decision.action,
                        "Scope": decision.scope,
                        "Lexicon": decision.lexicon_id,
                        "Source": decision.source_form,
                        "Mapping target": decision.mapping_target,
                        "Risk": decision.risk_category,
                        "Revision": decision.revision_number,
                        "Rationale": decision.rationale,
                    }
                    for decision in decisions
                ]
            ),
            hide_index=True,
            width="stretch",
            height=260,
        )
        selected_decision_id = st.selectbox(
            "Decision to revoke or restore",
            options=[decision.decision_id for decision in decisions],
            format_func=lambda value: next(
                (
                    f"{decision.action}: {decision.source_form} "
                    f"({decision.scope}, {decision.state})"
                    for decision in decisions
                    if decision.decision_id == value
                ),
                value,
            ),
            key=f"review_decision_state_{project_id}_{scenario_id}",
        )
        selected_decision = next(
            decision
            for decision in decisions
            if decision.decision_id == selected_decision_id
        )
        with st.form(
            f"toggle_review_decision_{project_id}_{scenario_id}_{selected_decision_id}"
        ):
            change_rationale = st.text_area(
                (
                    "Why restore this decision?"
                    if selected_decision.state == "revoked"
                    else "Why revoke this decision?"
                ),
                height=80,
            )
            toggle = st.form_submit_button(
                (
                    "Restore as a new revision"
                    if selected_decision.state == "revoked"
                    else "Revoke as a new revision"
                )
            )
        if toggle:
            try:
                repository.set_review_decision_state(
                    scenario_id,
                    selected_decision_id,
                    active=selected_decision.state == "revoked",
                    rationale=change_rationale,
                )
                st.success(
                    "A new decision revision and scenario version were recorded."
                )
                st.rerun()
            except (KeyError, ValueError) as error:
                st.error(f"The decision was not changed: {error}")
    else:
        st.info("This scenario version has no decisions yet.")

    st.divider()
    st.markdown("**Semantic-risk and quality-control queue**")
    st.write(
        "Suggested items include unmatched tokens, lemma and possessive fallbacks, "
        "multiword phrases, source collisions, prior mappings, and exclusions. "
        "These are review prompts—not claims that a match is wrong."
    )
    include_exact = st.checkbox(
        "Also show ordinary exact matches for optional contextual review",
        key=f"review_include_exact_{project_id}",
    )
    candidates = repository.list_review_candidates(
        project_id,
        include_exact=include_exact,
    )
    if candidates:
        categories = sorted({candidate.risk_category for candidate in candidates})
        selected_categories = st.multiselect(
            "Candidate types",
            options=categories,
            default=categories,
            format_func=lambda value: value.replace("_", " ").title(),
            key=f"review_categories_{project_id}",
        )
        search = st.text_input(
            "Search word, context, work, or lexicon",
            key=f"review_candidate_search_{project_id}",
        ).casefold()
        filtered = [
            candidate
            for candidate in candidates
            if candidate.risk_category in selected_categories
            and (
                not search
                or search
                in " ".join(
                    (
                        candidate.surface_form,
                        candidate.normalized_form,
                        candidate.matched_term,
                        candidate.text_title,
                        candidate.lexicon,
                        candidate.context,
                    )
                ).casefold()
            )
        ]
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Work": candidate.text_title,
                        "Lexicon": candidate.lexicon,
                        "Line": candidate.line_number,
                        "Surface": candidate.surface_form,
                        "Matched entry": candidate.matched_term,
                        "Method": candidate.method,
                        "Status": candidate.selection,
                        "Review prompt": candidate.risk_category.replace("_", " "),
                        "Context": candidate.context,
                    }
                    for candidate in filtered
                ]
            ),
            hide_index=True,
            width="stretch",
            height=340,
        )
        if filtered:
            candidate_index = st.selectbox(
                "Occurrence to review",
                options=range(len(filtered)),
                format_func=lambda index: (
                    f"{filtered[index].surface_form} — {filtered[index].text_title}, "
                    f"line {filtered[index].line_number} — {filtered[index].lexicon}"
                ),
                key=f"review_candidate_{project_id}_{scenario_id}",
            )
            selected = filtered[candidate_index]
            possible_actions = (
                [ReviewAction.FLAG, ReviewAction.MAP]
                if selected.selection == "unmatched"
                else [ReviewAction.FLAG, ReviewAction.EXCLUDE]
            )
            action_labels = {
                ReviewAction.FLAG: "Flag only — record concern; do not change results",
                ReviewAction.EXCLUDE: "Exclude — omit this match under the scenario",
                ReviewAction.MAP: "Map — use one exact published lexicon entry",
            }
            scope_labels = {
                ReviewScope.OCCURRENCE: "This occurrence only",
                ReviewScope.WORK: "Every occurrence of this form in this work",
                ReviewScope.PROJECT: "Every occurrence of this form in this project",
                ReviewScope.GLOBAL: (
                    "Every eligible work evaluated with this scenario"
                ),
            }
            with st.form(
                f"add_review_decision_{project_id}_{scenario_id}_{selected.match_id}"
            ):
                action = st.selectbox(
                    "Decision",
                    options=possible_actions,
                    format_func=lambda value: action_labels[value],
                )
                scope = st.selectbox(
                    "Scope",
                    options=list(ReviewScope),
                    format_func=lambda value: scope_labels[value],
                )
                mapping_target = st.text_input(
                    "Exact published mapping target",
                    help=(
                        "Required only for Map. The target must exist exactly in this "
                        "lexicon; similarity suggestions are never applied automatically."
                    ),
                )
                rationale = st.text_area(
                    "Scholarly rationale",
                    placeholder=(
                        "Record the edition, contextual reading, or other evidence "
                        "supporting this decision."
                    ),
                    height=100,
                )
                add = st.form_submit_button(
                    "Add decision and create a new scenario version",
                    type="primary",
                )
            if add:
                try:
                    if action == ReviewAction.MAP:
                        lexicon = load_lexicon(selected.lexicon_id)
                        entry, conflict = lexicon.resolve(
                            normalize_lookup(mapping_target),
                            mapping_target.strip(),
                        )
                        if conflict:
                            raise ValueError(
                                "That target has a capitalization collision in the "
                                "source lexicon. Enter an exact source form or choose another target."
                            )
                        if entry is None:
                            raise ValueError(
                                f"{mapping_target!r} is not an exact published entry "
                                f"in {selected.lexicon}."
                            )
                    repository.create_review_decision(
                        scenario_id,
                        action=action,
                        scope=scope,
                        lexicon_id=selected.lexicon_id,
                        source_form=selected.normalized_form,
                        mapping_target=mapping_target,
                        text_id=selected.text_id,
                        text_version_id=selected.text_version_id,
                        token_position=selected.token_position,
                        risk_category=selected.risk_category,
                        rationale=rationale,
                    )
                    st.success(
                        "Decision saved as a new immutable revision and scenario version."
                    )
                    st.rerun()
                except (KeyError, ValueError, WorkspaceAnalysisError) as error:
                    st.error(f"The review decision was not added: {error}")
        else:
            st.info("No candidates match the current filters.")
    else:
        st.info(
            "Run a complete corpus batch first. Its occurrence-level audit will "
            "populate the review queue."
        )

    versions = repository.list_review_scenario_versions(scenario_id)
    if len(versions) > 1:
        with st.expander("Version history and rollback"):
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Version": version.version_number,
                            "Pinned revisions": version.decision_count,
                            "Created": version.created_at,
                            "Change": version.change_note,
                        }
                        for version in versions
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            older = [
                version
                for version in versions
                if version.scenario_version_id != scenario.scenario_version_id
            ]
            with st.form(f"restore_scenario_version_{project_id}_{scenario_id}"):
                source_version_id = st.selectbox(
                    "Historical version to restore",
                    options=[version.scenario_version_id for version in older],
                    format_func=lambda value: next(
                        f"Version {version.version_number} — {version.change_note}"
                        for version in older
                        if version.scenario_version_id == value
                    ),
                )
                restore_reason = st.text_area(
                    "Why restore this version?",
                    height=80,
                )
                restore = st.form_submit_button(
                    "Restore as a new version",
                )
            if restore:
                try:
                    repository.restore_review_scenario_version(
                        scenario_id,
                        source_version_id,
                        rationale=restore_reason,
                    )
                    st.success(
                        "The historical decision set was copied into a new immutable version."
                    )
                    st.rerun()
                except (KeyError, ValueError) as error:
                    st.error(f"The scenario was not restored: {error}")

    with st.expander("Documentation-only unmatched notes"):
        _render_qc_tab(repository, project_id)


def _render_qc_tab(repository: ProjectRepository, project_id: str) -> None:
    rows = repository.list_latest_unmatched(project_id)
    st.subheader("Unmatched-Vocabulary Quality Control")
    st.write(
        "These observations did not match a selected lexicon in the latest complete "
        "batch. Notes persist locally by project, work, lexicon, and normalized form. "
        "They document review; they do not alter an analysis score."
    )
    if not rows:
        st.info("No unmatched observations are available from a complete corpus batch.")
        return
    statuses = ["All", "unreviewed", "reviewed", "needs mapping", "accepted gap"]
    status_filter = st.selectbox(
        "Review status",
        options=statuses,
        key=f"qc_status_{project_id}",
    )
    search = st.text_input(
        "Search word, work, lexicon, lemma, or note",
        key=f"qc_search_{project_id}",
    ).casefold()
    filtered = [
        row
        for row in rows
        if (status_filter == "All" or row.status == status_filter)
        and (
            not search
            or search
            in " ".join(
                (
                    row.display_form,
                    row.normalized_form,
                    row.text_title,
                    row.lexicon,
                    row.proposed_lemma,
                    row.note,
                )
            ).casefold()
        )
    ]
    frame = pd.DataFrame(
        [
            {
                "Work": row.text_title,
                "Lexicon": row.lexicon,
                "Surface": row.display_form,
                "Normalized": row.normalized_form,
                "Frequency": row.frequency,
                "POS": row.pos,
                "Proposed lemma": row.proposed_lemma,
                "Status": row.status,
                "Research note": row.note,
                "Example": row.example_context,
            }
            for row in filtered
        ]
    )
    render_dataframe(frame, hide_index=True, width="stretch", height=340)
    if not filtered:
        return
    selected_index = st.selectbox(
        "Item to review",
        options=range(len(filtered)),
        format_func=lambda index: (
            f"{filtered[index].display_form} — {filtered[index].text_title} — "
            f"{filtered[index].lexicon}"
        ),
        key=f"qc_item_{project_id}",
    )
    selected = filtered[selected_index]
    with st.form(f"qc_note_{selected.text_id}_{selected.lexicon_id}_{selected.normalized_form}"):
        status = st.selectbox(
            "Status",
            options=["unreviewed", "reviewed", "needs mapping", "accepted gap"],
            index=["unreviewed", "reviewed", "needs mapping", "accepted gap"].index(
                selected.status
            ),
        )
        note = st.text_area("Research note", value=selected.note, height=100)
        mapping = st.text_input(
            "Possible mapping (documentation only)",
            value=selected.proposed_mapping,
        )
        save = st.form_submit_button("Save quality-control note")
    if save:
        repository.upsert_unmatched_note(
            project_id=project_id,
            text_id=selected.text_id,
            lexicon_id=selected.lexicon_id,
            normalized_form=selected.normalized_form,
            display_form=selected.display_form,
            status=status,
            note=note,
            proposed_mapping=mapping,
        )
        st.success("Quality-control note saved locally. Analysis results were not changed.")
        st.rerun()


def _render_part_of_speech_tab(
    repository: ProjectRepository,
    project_id: str,
    preprocessor: TextPreprocessor,
) -> None:
    st.subheader("Part-of-Speech Profile")
    st.write(
        "Counts and shares use every eligible lexical token in the current preserved "
        "version of each work, independent of affective-lexicon matches. The combined "
        "profile pools token occurrences across all works, so longer works contribute "
        "more to that specific view. Noun combines source NOUN and PROPN tags; "
        "Verb combines source VERB and AUX tags."
    )
    rows = _corpus_part_of_speech_rows(repository, project_id, preprocessor)
    if not rows:
        st.info("Import at least one work to build a part-of-speech profile.")
        return
    frame = pd.DataFrame(rows)
    combined = frame[
        (frame["Scope"] == "All Works Combined")
        & (frame["Profile Level"] == "Broad Categories")
    ].copy()
    st.markdown("**All Works Combined**")
    st.bar_chart(
        rounded_display_data(
            combined.set_index("Part of speech")[
                ["Share of lexical tokens"]
            ]
        ),
        height=320,
    )
    render_dataframe(
        combined[
            [
                "Source POS tag(s)",
                "Part of speech",
                "Token count",
                "Share of lexical tokens",
                "Unique normalized types",
                "Examples",
                "Lexical-token denominator",
            ]
        ].style.format(
            {"Share of lexical tokens": lambda value: f"{value:.1%}"}
        ),
        hide_index=True,
        width="stretch",
    )
    detailed_combined = frame[
        (frame["Scope"] == "All Works Combined")
        & (frame["Profile Level"] == "Detailed Model Tags")
    ].copy()
    st.markdown("**Detailed Combined Model-Tag Breakdown**")
    render_dataframe(
        detailed_combined[
            [
                "Source POS tag(s)",
                "Part of speech",
                "Token count",
                "Share of lexical tokens",
                "Unique normalized types",
                "Examples",
                "Lexical-token denominator",
            ]
        ].style.format(
            {"Share of lexical tokens": lambda value: f"{value:.1%}"}
        ),
        hide_index=True,
        width="stretch",
    )
    work_rows = frame[
        (frame["Scope"] == "Work")
        & (frame["Profile Level"] == "Broad Categories")
    ].copy()
    if not work_rows.empty:
        st.markdown("**Work-by-Work Comparison**")
        render_dataframe(
            work_rows[
                [
                    "Work",
                    "Collection",
                    "Part of speech",
                    "Source POS tag(s)",
                    "Token count",
                    "Share of lexical tokens",
                    "Unique normalized types",
                    "Examples",
                    "Lexical-token denominator",
                ]
            ].style.format(
                {"Share of lexical tokens": lambda value: f"{value:.1%}"}
            ),
            hide_index=True,
            width="stretch",
            height=420,
        )
        with st.expander("Detailed Work-by-Work Model Tags"):
            detailed_work_rows = frame[
                (frame["Scope"] == "Work")
                & (frame["Profile Level"] == "Detailed Model Tags")
            ].copy()
            render_dataframe(
                detailed_work_rows[
                    [
                        "Work",
                        "Collection",
                        "Part of speech",
                        "Source POS tag(s)",
                        "Token count",
                        "Share of lexical tokens",
                        "Unique normalized types",
                        "Examples",
                        "Lexical-token denominator",
                    ]
                ].style.format(
                    {"Share of lexical tokens": lambda value: f"{value:.1%}"}
                ),
                hide_index=True,
                width="stretch",
                height=420,
            )
    st.warning(
        "These grammatical labels are generated by the installed English model. "
        "Poetic syntax, fragments, archaic forms, and ambiguity can produce uncertain "
        "assignments. Counts are descriptive and are not affective-lexicon results."
    )


def _render_export_tab(
    repository: ProjectRepository,
    project_id: str,
    preprocessor: TextPreprocessor,
    *,
    profile_workspace_id: str | None = None,
) -> None:
    project = repository.get_project(project_id)
    st.subheader("Research Export & Downloads")
    st.write(
        "The ZIP includes machine-readable CSV tables plus a comprehensive Word "
        "report. It retains collection weightings, work-level results, coverage, "
        "unmatched review notes, methodology, and provenance."
    )
    if not repository.list_completed_batches(project_id):
        st.info("Complete a corpus analysis before exporting the research bundle.")
        return
    export_mode_label = st.radio(
        "Export mode",
        options=("Export Current View", "Export Complete Audit"),
        horizontal=True,
        key=f"corpus_export_mode_{project_id}",
    )
    export_mode = (
        "current_view"
        if export_mode_label == "Export Current View"
        else "complete_audit"
    )
    if export_mode == "complete_audit":
        st.info(
            "The Complete Audit ZIP includes every compatible lexical scope and "
            "weighting, all calculated module tables, coverage and warning records, "
            "unmatched/QC data, methodology and provenance, plus the readable Word report."
        )
    else:
        st.caption(
            "Current View limits compatible lexical results to the selected profiles "
            "and the chosen report family while retaining the supporting methodology."
        )
    visible_section = str(
        st.session_state.get(
            f"corpus_result_family_{project_id}",
            "Overview",
        )
    )
    if export_mode == "current_view":
        visible_section = st.selectbox(
            "Report section to export",
            options=(
                "Overview",
                "Affective Evidence",
                "Lexical Character, Imagery & Embodiment",
                "Sound & Form",
                "Structure",
                "VerseMap",
                "Evidence & Diagnostics",
            ),
            index=(
                (
                    "Overview",
                    "Affective Evidence",
                    "Lexical Character, Imagery & Embodiment",
                    "Sound & Form",
                    "Structure",
                    "VerseMap",
                    "Evidence & Diagnostics",
                ).index(visible_section)
                if visible_section in {
                    "Overview", "Affective Evidence",
                    "Lexical Character, Imagery & Embodiment", "Sound & Form",
                    "Structure", "VerseMap", "Evidence & Diagnostics",
                }
                else 0
            ),
            key=f"corpus_export_section_{project_id}",
        )
    profile_workspace_id = profile_workspace_id or f"corpus_{project_id}"
    profile_state = report_profile_state(profile_workspace_id)
    module_scope_overrides = active_override_modules(profile_workspace_id)
    prepared_key = f"prepared_corpus_export_{project_id}"
    signature = (
        export_mode,
        visible_section,
        tuple(profile.id for profile in profile_state.selection.profiles),
        tuple(sorted(module_scope_overrides)),
        project.updated_at,
    )
    prepare_label = (
        "Prepare Complete Audit ZIP"
        if export_mode == "complete_audit"
        else "Prepare Current View ZIP"
    )
    if st.button(
        prepare_label,
        type="primary",
        key=f"prepare_corpus_export_{project_id}",
    ):
        texts = repository.list_texts(project_id)
        metrics = repository.list_latest_metrics(project_id)
        unmatched = repository.list_latest_unmatched(project_id)
        module_metrics = repository.list_latest_module_metrics(project_id)
        module_coverage = repository.list_latest_module_coverage(project_id)
        module_warnings = repository.list_latest_module_warnings(project_id)
        module_results = repository.list_latest_module_results(project_id)
        module_aggregates = repository.list_latest_module_aggregates(project_id)
        part_of_speech_rows = _corpus_part_of_speech_rows(
            repository,
            project_id,
            preprocessor,
        )
        methodology = repository.latest_methodology(project_id)
        with st.spinner("Preparing CSV, Word, and reproducibility files..."):
            export_bundle = build_corpus_export_bundle(
                project,
                texts,
                metrics,
                unmatched,
                methodology=methodology,
                review_decisions=tuple(methodology.get("review_decisions", ())),
                part_of_speech_rows=part_of_speech_rows,
                module_metrics=module_metrics,
                module_coverage=module_coverage,
                module_warnings=module_warnings,
                module_results=module_results,
                module_aggregates=module_aggregates,
                profile_selection=profile_state.selection,
                export_mode=export_mode,
                report_section=visible_section,
                active_preset=str(
                    st.session_state.get(f"corpus_preset_{project_id}", "Custom")
                ),
                module_scope_overrides=module_scope_overrides,
            )
        with zipfile.ZipFile(io.BytesIO(export_bundle)) as archive:
            report = archive.read("01_REPORTS/Corpus_Report.docx")
            metrics_csv = archive.read("03_MASTER_DATA/Master_Metrics.csv")
        st.session_state[prepared_key] = {
            "signature": signature,
            "bundle": export_bundle,
            "report": report,
            "metrics": metrics_csv,
        }
    prepared = st.session_state.get(prepared_key)
    if isinstance(prepared, dict) and prepared.get("signature") == signature:
        download_label = (
            "Download Complete Audit ZIP"
            if export_mode == "complete_audit"
            else "Download Current View ZIP"
        )
        metrics_column, report_column, bundle_column = st.columns(3)
        metrics_column.download_button(
            (
                "Download Current-View Metrics CSV"
                if export_mode == "current_view"
                else "Download Master Metrics CSV"
            ),
            data=prepared["metrics"],
            file_name=f"{_safe_filename(project.title)}_VerseVAD_metrics.csv",
            mime="text/csv",
            width="stretch",
            key=f"download_corpus_metrics_{project_id}",
        )
        report_column.download_button(
            "Download Readable Word Report",
            data=prepared["report"],
            file_name=f"{_safe_filename(project.title)}_VerseVAD_report.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            width="stretch",
            key=f"download_corpus_report_{project_id}",
        )
        bundle_column.download_button(
            download_label,
            data=prepared["bundle"],
            file_name=(
                f"{_safe_filename(project.title)}_VerseVAD_"
                f"{'complete_audit' if export_mode == 'complete_audit' else 'current_view'}.zip"
            ),
            mime="application/zip",
            type="primary",
            width="stretch",
            key=f"download_corpus_{project_id}",
        )
    st.caption(
        "The bundle does not duplicate the full literary texts; it records "
        "text/version IDs, source paths, and SHA-256 hashes."
    )


def render_corpus_workspace(
    preprocessor: TextPreprocessor,
    resource_readiness: ResourceReadiness,
) -> None:
    """Render the persistent local-project branch of the Streamlit application."""

    repository = _project_repository_for_path(str(default_database_path()))
    pending_delete = st.session_state.pop(
        "_pending_corpus_project_delete",
        None,
    )
    if isinstance(pending_delete, tuple) and len(pending_delete) == 3:
        pending_id, pending_title, confirmation_title = pending_delete
        deleted = False
        try:
            repository.delete_project(
                str(pending_id),
                confirmation_title=str(confirmation_title),
            )
        except KeyError:
            if any(
                item.project_id == str(pending_id)
                for item in repository.list_projects()
            ):
                st.session_state["corpus_project_error"] = (
                    "The project could not be deleted because its saved record "
                    "could not be resolved."
                )
            else:
                deleted = True
                st.session_state["corpus_project_flash"] = (
                    f'Project "{pending_title}" was deleted from this computer.'
                )
        except (ValueError, RuntimeError) as error:
            st.session_state["corpus_project_error"] = (
                f"The project was not deleted: {error}"
            )
        else:
            deleted = True
            st.session_state["corpus_project_flash"] = (
                f'Project "{pending_title}" was deleted from this computer.'
            )
        if deleted:
            _clear_deleted_project_state(str(pending_id))
    with st.sidebar:
        st.markdown("### Saved Projects")
        st.success("Projects, texts, notes, and results stay on this computer.")
        st.caption(f"Database: {repository.database_path}")
        st.markdown("---")
        st.caption(
            "Corpus results describe lexical evidence. They do not determine a work's emotion or a reader's response."
        )

    render_workspace_header(
        "Saved Projects",
        "Import a folder as separate works, add metadata, compare complete analysis "
        "batches across affective and optional lexical/prosodic modules, build "
        "versioned review scenarios, and export CSV data with a readable Word report.",
        kicker="Private corpus research workspace",
        status="Persistent",
    )
    project_flash = st.session_state.pop("corpus_project_flash", None)
    if project_flash:
        st.success(project_flash)
    project_error = st.session_state.pop("corpus_project_error", None)
    if project_error:
        st.error(project_error)
    projects = repository.list_projects()
    _create_project(repository, expanded=not projects)
    if not projects:
        render_empty_state(
            "No research project yet",
            "Projects keep texts, metadata, immutable analysis runs, review "
            "scenarios, and exports together in the local database.",
            "Use Create a research project above to begin.",
        )
        return
    project_ids = [project.project_id for project in projects]
    if st.session_state.get("active_corpus_project") not in project_ids:
        st.session_state.pop("active_corpus_project", None)
    project_id = st.selectbox(
        "Active project",
        options=project_ids,
        format_func=lambda item: next(
            project.title for project in projects if project.project_id == item
        ),
        key="active_corpus_project",
    )
    project = repository.get_project(project_id)
    texts = repository.list_texts(project_id)
    project_columns = st.columns(4)
    project_columns[0].metric("Works", len(texts))
    project_columns[1].metric("Schema", SCHEMA_VERSION)
    project_columns[2].metric(
        "Researcher",
        project.researcher or "Not recorded",
    )
    project_columns[3].metric(
        "Last modified",
        project.updated_at[:10],
    )
    st.caption(
        f"{project.title} · {project.description or 'No project description.'} "
        "All saves are local and completed analysis runs remain immutable."
    )
    project_sections = (
        "Works & Metadata",
        "Language Profile",
        "Analyze & Compare",
        "VerseMap",
        "Review & Scenarios",
        "Export",
        "Project Settings",
    )
    project_state_key = f"corpus_project_section_{project_id}"
    active_project_section, project_containers = render_stateful_section_navigation(
        "Project section",
        project_sections,
        state_key=project_state_key,
        container_key_prefix=project_state_key.replace("-", "_"),
        default="Works & Metadata",
        help_text=(
            "The selected project section is retained when controls, analyses, "
            "or prepared exports refresh the page."
        ),
        control="dropdown",
    )
    active_container = project_containers[active_project_section]
    with active_container:
        if active_project_section == "Works & Metadata":
            _render_texts_tab(repository, project_id)
        elif active_project_section == "Language Profile":
            _render_part_of_speech_tab(repository, project_id, preprocessor)
        elif active_project_section == "Analyze & Compare":
            _render_analysis_tab(
                repository,
                project_id,
                preprocessor,
                resource_readiness,
            )
        elif active_project_section == "VerseMap":
            _render_versemap_tab(repository, project_id)
        elif active_project_section == "Review & Scenarios":
            _render_review_tab(repository, project_id)
        elif active_project_section == "Export":
            _render_export_tab(repository, project_id, preprocessor)
        elif active_project_section == "Project Settings":
            _render_project_settings_tab(repository, project_id)
        else:
            raise RuntimeError(
                f"Unknown corpus project section: {active_project_section!r}"
            )
