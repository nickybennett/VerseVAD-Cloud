"""Streamlit project and corpus workspace backed by local SQLite storage."""

from __future__ import annotations

import json
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
from versevad.deployment import (
    cloud_deployment_enabled,
    cloud_session_database_path,
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
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.models import PhrasePolicy, ReviewAction, ReviewScope, TextDocument
from versevad.normalization import normalize_lookup
from versevad.preprocessing import TextPreprocessor
from versevad.prosody import (
    MeterAnalysisMode,
    MeterConfiguration,
    MeterInterpretationDepth,
    MeterStyleProfile,
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
from versevad.ui.dataframes import heterogeneous_display_value
from versevad.ui.design import (
    MODULE_PRESETS,
    preset_widget_state,
    render_dataframe,
    render_empty_state,
    publication_chart,
    render_stateful_section_navigation,
    render_workspace_header,
)
from versevad.ui.stopwords import render_stopword_settings
from versevad.versemap import VerseMapConfiguration, load_reference_index


def _safe_filename(value: str) -> str:
    stem = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value.strip()
    ).strip("_")
    return stem or "versevad_corpus"


def _records_frame(records) -> pd.DataFrame:
    return pd.DataFrame([asdict(record) for record in records])


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
    metrics = tuple(
        row
        for row in repository.list_latest_module_metrics(project_id)
        if row.module_name == "versemap"
    )
    if not metrics:
        st.info(
            "No completed VerseMap corpus batch is available. In Analyze & Compare, "
            "select VerseMap comparative profile and analyze the corpus."
        )
        return
    try:
        index = load_reference_index(
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

    with st.expander("Corpus VerseMap Space", expanded=False):
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
                    alt.Tooltip("Component 1:Q", format=".4f"),
                    alt.Tooltip("Component 2:Q", format=".4f"),
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

    with st.expander("Nearest Reference Poets", expanded=False):
        st.markdown("#### Project-level pattern")
        render_dataframe(
            pd.DataFrame(project_neighbor_rows),
            column_config={
                "Mean Work-to-Centroid Distance": (
                    st.column_config.NumberColumn(format="%.4f")
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
                "Distance": st.column_config.NumberColumn(format="%.4f"),
                "Shared Evidence Weight": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.1%%"
                ),
                "Profile Weight Available": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.1%%"
                ),
            },
        )

    with st.expander("Methodology and Coverage", expanded=False):
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
        "poetry_id.valence",
        "poetry_id.arousal",
        "poetry_id.dominance",
        "poetry_id.categorical_archetype_id",
        "poetry_id.categorical_archetype_name",
        "poetry_id.nearest_centroid_archetype_id",
        "poetry_id.categorical_centroid_match",
        "poetry_id.centroid_distance",
        "poetry_id.confidence_label",
    }
    nearest_scope_id = f"{scope_id}:{weighting}:1"
    by_work: dict[str, dict[str, object]] = {}
    for row in metrics:
        is_selected_document_metric = (
            row.scope == "document"
            and row.scope_id == scope_id
            and row.weighting == weighting
            and row.metric_id in document_metric_ids
        )
        is_nearest_distance = (
            row.scope == "neighbor"
            and row.scope_id == nearest_scope_id
            and row.weighting == weighting
            and row.metric_id == "poetry_id.neighbor_distance"
        )
        if not (is_selected_document_metric or is_nearest_distance):
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

        match = work_metrics.get("poetry_id.categorical_centroid_match")
        if isinstance(match, bool):
            match_label = "Yes" if match else "No"
        elif str(match).strip().casefold() in {"true", "1", "yes"}:
            match_label = "Yes"
        elif str(match).strip().casefold() in {"false", "0", "no"}:
            match_label = "No"
        else:
            match_label = None

        confidence = work_metrics.get("poetry_id.confidence_label")
        confidence_label = (
            str(confidence).replace("_", " ").title()
            if confidence is not None
            else None
        )
        rows.append(
            {
                "Work": values["title"],
                "Categorical profile": categorical_name,
                "Nearest centroid": nearest_name,
                "Same profile": match_label,
                "Nearest distance": work_metrics.get(
                    "poetry_id.neighbor_distance"
                ),
                "Categorical distance": work_metrics.get(
                    "poetry_id.centroid_distance"
                ),
                "Confidence": confidence_label,
                "Valence": work_metrics.get("poetry_id.valence"),
                "Arousal": work_metrics.get("poetry_id.arousal"),
                "Dominance": work_metrics.get("poetry_id.dominance"),
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
                st.success("Project created in the VerseVAD project database.")
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
    completed_text_ids = {
        row.text_id for row in repository.list_latest_metrics(project_id)
    } | {
        row.text_id
        for row in repository.list_latest_module_results(project_id)
    }
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
            st.success("Metadata saved.")
            st.rerun()
        except (ValueError, json.JSONDecodeError) as error:
            st.error(f"Metadata was not changed: {error}")


def _render_profiles(metrics, total_works: int) -> None:
    profiles = corpus_vad_profiles(metrics, total_works=total_works)
    if not profiles:
        st.info("The latest complete corpus batch has no normalized VAD means to compare.")
        return
    st.subheader("Collection VAD: Report Both Views")
    st.write(
        "The **token-weighted volume profile** pools included matched observations, so "
        "long works contribute more. The **work-weighted volume profile** gives every "
        "eligible work one poem-level score. Their divergence can be an important finding."
    )
    profile_frame = pd.DataFrame(
        [
            {
                "Lexicon": row.lexicon,
                "Analysis view": (
                    "All matched tokens"
                    if row.analysis_view == "all_matched"
                    else "Stopwords excluded"
                ),
                "Dimension": row.dimension.title(),
                "Works included": row.works_included,
                "Works omitted": row.works_omitted,
                "Matched observations": row.matched_observations,
                "Volume coverage": row.volume_coverage,
                "Token-weighted volume mean": row.token_weighted_volume_mean,
                "Pooled lexical-rating SD": (
                    row.pooled_lexical_rating_standard_deviation
                ),
                "Work-weighted volume mean": row.work_weighted_volume_mean,
                "Across-poem mean SD": row.poem_mean_standard_deviation,
                "Poem-mean median": row.poem_mean_median,
                "Lowest poem mean": row.poem_mean_minimum,
                "Highest poem mean": row.poem_mean_maximum,
                "Work minus token": row.work_minus_token_difference,
            }
            for row in profiles
        ]
    )
    render_dataframe(
        profile_frame.style.format(
            {
                "Volume coverage": "{:.1%}",
                "Token-weighted volume mean": "{:.3f}",
                "Pooled lexical-rating SD": "{:.3f}",
                "Work-weighted volume mean": "{:.3f}",
                "Across-poem mean SD": "{:.3f}",
                "Poem-mean median": "{:.3f}",
                "Lowest poem mean": "{:.3f}",
                "Highest poem mean": "{:.3f}",
                "Work minus token": "{:+.3f}",
            },
            na_rep="—",
        ),
        hide_index=True,
        width="stretch",
    )
    chart = profile_frame.melt(
        id_vars=["Lexicon", "Analysis view", "Dimension"],
        value_vars=["Token-weighted volume mean", "Work-weighted volume mean"],
        var_name="Collection view",
        value_name="Normalized mean",
    )
    st.bar_chart(
        chart,
        x="Dimension",
        y="Normalized mean",
        color="Collection view",
        stack=False,
        height=320,
    )
    st.caption(
        "Pooled lexical-rating SD describes the spread of all included matched "
        "token ratings around the token-weighted volume mean. Across-poem mean SD "
        "describes variation among poem-level token means around the work-weighted "
        "mean. Neither is a confidence interval, source-rater uncertainty, or an "
        "emotion declaration. Missing work scores stay omitted rather than receiving "
        "a neutral value."
    )


def _render_corpus_modules(
    repository: ProjectRepository,
    project_id: str,
    metrics,
    coverage,
    warnings,
    results,
    aggregates,
) -> None:
    st.subheader("Additional Module Results")
    st.write(
        "These results were produced by the same reusable modules as the one-poem "
        "workspace. Work-level evidence is preserved; collection summaries never "
        "silently replace missing values or mix incompatible configurations."
    )
    available_modules = sorted({row.module_name for row in metrics})
    selected_module = st.selectbox(
        "Module to inspect",
        options=available_modules,
        format_func=lambda value: value.replace("_", " ").title(),
        key=f"corpus_module_inspect_{project_id}",
    )
    selected = tuple(row for row in metrics if row.module_name == selected_module)
    total_works = len({row.text_id for row in selected})
    profiles = corpus_module_profiles(selected, total_works=total_works)
    if profiles:
        st.markdown("**Compatible collection summaries**")
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Metric": row.metric_id,
                        "Source / view": row.scope_id or "—",
                        "Unit": row.unit,
                        "Weighting": row.weighting or "—",
                        "Works included": row.works_included,
                        "Works omitted": row.works_omitted,
                        "Equal-work mean": row.equal_work_mean,
                        "Observation-weighted mean": (
                            row.observation_weighted_mean
                        ),
                        "Observations": row.total_observations or None,
                        "Configuration": row.configuration_id,
                        "Interpretive note": row.note,
                    }
                    for row in profiles
                ]
            ).style.format(
                {
                    "Equal-work mean": "{:.4f}",
                    "Observation-weighted mean": "{:.4f}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
            height=360,
        )

    categories = corpus_module_category_profiles(selected)
    if categories:
        st.markdown("**Work-level categorical prevalence**")
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
                    for row in categories
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
                    distribution_frame.set_index("Profile")[["Works"]],
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
                    pd.DataFrame(scatter_rows),
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
                    "**Per-poem categorical and nearest-centroid comparison**"
                )
                render_dataframe(
                    pd.DataFrame(comparison_rows).style.format(
                        {
                            "Nearest distance": "{:.4f}",
                            "Categorical distance": "{:.4f}",
                            "Valence": "{:.3f}",
                            "Arousal": "{:.3f}",
                            "Dominance": "{:.3f}",
                        },
                        na_rep="-",
                    ),
                    hide_index=True,
                    width="stretch",
                    height=360,
                )
                st.caption(
                    "The categorical profile comes from the configured low, "
                    "moderate, and high VAD thresholds. The nearest centroid is "
                    "the closest of all 27 continuous VAD centroids under "
                    "Euclidean distance. They may differ near a boundary. "
                    "Confidence is rule-based evidence, not a probability."
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
        with st.expander("Module warnings"):
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Work": row.title,
                            "Severity": row.severity.title(),
                            "Code": row.code,
                            "Message": row.message,
                            "Technical detail": row.technical_detail or "—",
                        }
                        for row in selected_warnings
                    ]
                ),
                hide_index=True,
                width="stretch",
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


def _render_analysis_tab(
    repository: ProjectRepository,
    project_id: str,
    preprocessor: TextPreprocessor,
    resource_readiness: ResourceReadiness,
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
    preset_choice, preset_action = st.columns([3, 1], vertical_alignment="bottom")
    with preset_choice:
        selected_preset = st.selectbox(
            "Corpus module preset",
            options=list(MODULE_PRESETS),
            index=list(MODULE_PRESETS).index("Custom"),
            key=f"corpus_preset_{project_id}",
            help=(
                "Presets update module selections only after Apply. Advanced "
                "methodology settings remain unchanged."
            ),
        )
    with preset_action:
        apply_preset = st.button(
            "Apply corpus preset",
            width="stretch",
            key=f"apply_corpus_preset_{project_id}",
        )
    st.caption(MODULE_PRESETS[selected_preset].description)
    if apply_preset:
        preset_state = preset_widget_state(
            selected_preset,
            available_lexicon_ids=tuple(lexicon_lookup),
        )
        if not preset_state:
            st.info("Custom keeps the current manual selections unchanged.")
            preset_state = None
        module_key_lookup = {
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
        if preset_state is not None:
            st.session_state[f"analysis_lexicons_{project_id}"] = (
                preset_state.get("selected_lexicons", [])
            )
            st.session_state[f"analysis_modules_{project_id}"] = [
                module_name
                for state_key, module_name in module_key_lookup.items()
                if (
                    preset_state.get(state_key) is True
                    and module_name in module_labels
                )
            ]
            st.rerun()
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
    frequency_content_words_only = False
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
    meter_analysis_mode = MeterAnalysisMode.CANDIDATE
    meter_style_profile = MeterStyleProfile.GENERAL
    meter_interpretation_depth = MeterInterpretationDepth.STANDARD
    meter_performance_candidate_limit = 8
    meter_realized_alternatives = 2
    meter_allow_visible_elision = False
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
        if "frequency" in selected_modules:
            frequency_content_words_only = st.checkbox(
                "Frequency: analyze content words only",
                value=False,
                key=f"corpus_frequency_content_only_{project_id}",
                help=(
                    "Non-default. Retains nouns, verbs, adjectives, and adverbs; "
                    "other parts of speech remain explicitly not eligible."
                ),
            )
        if "aoa" in selected_modules:
            aoa_content_words_only = st.checkbox(
                "Age of acquisition: analyze content words only",
                value=False,
                key=f"corpus_aoa_content_only_{project_id}",
                help=(
                    "Non-default. The Kuperman source contains many source POS "
                    "classes, so this is an actual analysis-scope choice."
                ),
            )
        if (
            "meter" in selected_modules
            or "inherited_form" in selected_modules
        ):
            st.markdown("**Meter batch settings**")
            meter_mode_labels = {
                "Candidate meter only (validated default)": (
                    MeterAnalysisMode.CANDIDATE
                ),
                "Performance-aware realization": (
                    MeterAnalysisMode.PERFORMANCE_AWARE
                ),
                "Compare both layers": MeterAnalysisMode.COMPARE_BOTH,
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
            meter_columns = st.columns(3)
            meter_mode_label = meter_columns[0].selectbox(
                "Meter analysis layer",
                options=list(meter_mode_labels),
                key=f"corpus_meter_mode_{project_id}",
            )
            meter_analysis_mode = meter_mode_labels[meter_mode_label]
            meter_style_label = meter_columns[1].selectbox(
                "Declared interpretation profile",
                options=list(meter_style_labels),
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                key=f"corpus_meter_style_{project_id}",
            )
            meter_style_profile = meter_style_labels[meter_style_label]
            meter_depth_label = meter_columns[2].selectbox(
                "Interpretation detail",
                options=list(meter_depth_labels),
                index=1,
                disabled=(
                    meter_analysis_mode is MeterAnalysisMode.CANDIDATE
                ),
                key=f"corpus_meter_depth_{project_id}",
            )
            meter_interpretation_depth = meter_depth_labels[
                meter_depth_label
            ]
            meter_limit_columns = st.columns(3)
            meter_performance_candidate_limit = int(
                meter_limit_columns[0].number_input(
                    "Realization candidates per line",
                    min_value=2,
                    max_value=40,
                    value=8,
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
                    value=2,
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
            poetry_id_weightings = tuple(
                st.multiselect(
                    "PoetryID weighting views",
                    options=["token", "type"],
                    default=["token", "type"],
                    key=f"corpus_poetry_id_weightings_{project_id}",
                )
            )
            poetry_id_views = tuple(
                st.multiselect(
                    "PoetryID analysis views",
                    options=["all_matched", "stopwords_excluded"],
                    default=["all_matched", "stopwords_excluded"],
                    format_func=lambda value: (
                        "All matched tokens (including stopwords)"
                        if value == "all_matched"
                        else "Stopwords excluded"
                    ),
                    key=f"corpus_poetry_id_views_{project_id}",
                    help=(
                        "Both views remain separate in every work and corpus "
                        "comparison. Unmatched vocabulary remains missing."
                    ),
                )
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
                include_frequency="frequency" in selected_modules,
                frequency_configuration=FrequencyConfiguration(
                    content_words_only=frequency_content_words_only
                ),
                include_aoa="aoa" in selected_modules,
                aoa_configuration=AoAConfiguration(
                    content_words_only=aoa_content_words_only
                ),
                include_sensorimotor="sensorimotor" in selected_modules,
                include_pronunciation="pronunciation" in selected_modules,
                include_meter="meter" in selected_modules,
                meter_configuration=MeterConfiguration(
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

    metrics = repository.list_latest_metrics(project_id)
    module_metrics = repository.list_latest_module_metrics(project_id)
    module_coverage = repository.list_latest_module_coverage(project_id)
    module_warnings = repository.list_latest_module_warnings(project_id)
    module_results = repository.list_latest_module_results(project_id)
    module_aggregates = repository.list_latest_module_aggregates(project_id)
    if not metrics and not module_metrics:
        st.info("No complete corpus batch is available yet.")
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

    st.subheader("Length-Sensitive Cumulative Load by Work")
    st.write(
        "These sums answer a different question from means. They grow with included "
        "matched vocabulary and repetition; they are not estimates of a reader's psychological response."
    )
    cumulative_metric_names = {
        "vad_rating_total",
        "vad_above_midpoint_load",
        "vad_below_midpoint_load",
        "vad_net_midpoint_load",
        "vad_absolute_midpoint_load",
    }
    load_rows = [row for row in metrics if row.metric in cumulative_metric_names]
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
        "VerseVAD project database. Other projects are not affected."
    )
    confirmation = st.text_input(
        f'Type the exact project title to confirm: "{project.title}"',
        key=confirmation_key,
    )

    def delete_confirmed_project() -> None:
        try:
            repository.delete_project(
                project_id,
                confirmation_title=str(
                    st.session_state.get(confirmation_key, "")
                ),
            )
            st.session_state.pop("active_corpus_project", None)
            st.session_state.pop(confirmation_key, None)
            st.session_state.pop("corpus_project_error", None)
            st.session_state["corpus_project_flash"] = (
                f'Project "{project.title}" was deleted from this computer.'
            )
        except (KeyError, ValueError, RuntimeError) as error:
            st.session_state["corpus_project_error"] = (
                f"The project was not deleted: {error}"
            )

    st.button(
        "Delete this project",
        type="primary",
        disabled=confirmation != project.title,
        key=f"delete_project_{project_id}",
        on_click=delete_confirmed_project,
    )


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
        "batch. Notes persist in the project database by project, work, lexicon, "
        "and normalized form. "
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
        st.success("Quality-control note saved. Analysis results were not changed.")
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
        combined.set_index("Part of speech")[["Share of lexical tokens"]],
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
    part_of_speech_rows: tuple[dict[str, object], ...],
) -> None:
    project = repository.get_project(project_id)
    texts = repository.list_texts(project_id)
    metrics = repository.list_latest_metrics(project_id)
    unmatched = repository.list_latest_unmatched(project_id)
    module_metrics = repository.list_latest_module_metrics(project_id)
    module_coverage = repository.list_latest_module_coverage(project_id)
    module_warnings = repository.list_latest_module_warnings(project_id)
    module_results = repository.list_latest_module_results(project_id)
    module_aggregates = repository.list_latest_module_aggregates(project_id)
    st.subheader("CSV and Word Research Bundle")
    st.write(
        "The ZIP includes machine-readable CSV tables plus a narrative Word "
        "report. It retains collection weightings, work-level results, coverage, "
        "unmatched review notes, methodology, and provenance."
    )
    if not metrics and not module_metrics:
        st.info("Complete a corpus analysis before exporting the research bundle.")
        return
    methodology = repository.latest_methodology(project_id)
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
    )
    st.download_button(
        "Download corpus CSV and Word bundle",
        data=export_bundle,
        file_name=f"{_safe_filename(project.title)}_VerseVAD_corpus.zip",
        mime="application/zip",
        type="primary",
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
    """Render the local or session-isolated project branch of the application."""

    cloud_deployment = cloud_deployment_enabled()
    database_path = (
        cloud_session_database_path(st.session_state)
        if cloud_deployment
        else default_database_path()
    )
    repository = ProjectRepository(database_path)
    repository.initialize()
    with st.sidebar:
        if cloud_deployment:
            st.markdown("### Session-Isolated Projects")
            st.warning(
                "Projects are private to this browser session and may be erased "
                "when the session disconnects or the hosted app restarts. Export "
                "anything you need to retain."
            )
        else:
            st.markdown("### Persistent Local Projects")
            st.success("Projects, texts, notes, and results stay on this computer.")
            st.caption(f"Database: {repository.database_path}")
        st.markdown("---")
        st.caption(
            "Corpus results describe lexical evidence. They do not determine a work's emotion or a reader's response."
        )

    render_workspace_header(
        "Project / Corpus",
        "Import a folder as separate works, add metadata, compare complete analysis "
        "batches across affective and optional lexical/prosodic modules, build "
        "versioned review scenarios, and export CSV data with a readable Word report.",
        kicker=(
            "Session-isolated corpus research workspace"
            if cloud_deployment
            else "Private corpus research workspace"
        ),
        status="Session-only" if cloud_deployment else "Persistent",
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
            "scenarios, and exports together "
            + (
                "for this browser session."
                if cloud_deployment
                else "in the local database."
            ),
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
        + (
            "Saves remain isolated to this browser session and are not durable; "
            "completed analysis runs remain immutable while the session is active."
            if cloud_deployment
            else "All saves are local and completed analysis runs remain immutable."
        )
    )
    part_of_speech_rows = _corpus_part_of_speech_rows(
        repository,
        project_id,
        preprocessor,
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
    _, project_containers = render_stateful_section_navigation(
        "Project section",
        project_sections,
        state_key=project_state_key,
        container_key_prefix=project_state_key.replace("-", "_"),
        default="Works & Metadata",
        help_text=(
            "The selected project section is retained when controls, analyses, "
            "or prepared exports refresh the page."
        ),
    )
    texts_tab = project_containers["Works & Metadata"]
    language_tab = project_containers["Language Profile"]
    analysis_tab = project_containers["Analyze & Compare"]
    versemap_tab = project_containers["VerseMap"]
    review_tab = project_containers["Review & Scenarios"]
    export_tab = project_containers["Export"]
    settings_tab = project_containers["Project Settings"]

    with texts_tab:
        _render_texts_tab(repository, project_id)
    with language_tab:
        _render_part_of_speech_tab(repository, project_id, preprocessor)
    with analysis_tab:
        _render_analysis_tab(
            repository,
            project_id,
            preprocessor,
            resource_readiness,
        )
    with versemap_tab:
        _render_versemap_tab(repository, project_id)
    with review_tab:
        _render_review_tab(repository, project_id)
    with export_tab:
        _render_export_tab(repository, project_id, part_of_speech_rows)
    with settings_tab:
        _render_project_settings_tab(repository, project_id)
