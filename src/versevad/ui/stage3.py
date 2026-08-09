"""Final library, corpus, VerseMap, and learning workspaces."""

from __future__ import annotations

import hashlib
import math
import os
import re
from bisect import bisect_left, bisect_right
from pathlib import Path
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st

from versevad.application import (
    PROJECT_ROOT,
    AnalysisRequest,
    ResourceReadiness,
    WorkspaceAnalysis,
    WorkspaceAnalysisError,
    run_workspace_analysis,
)
from versevad.inherited_form import FORM_PROFILES, PROFILE_REGISTRY_VERSION
from versevad.preprocessing import TextPreprocessor
from versevad.reference_corpora import (
    BUILT_IN_CORPUS_ID,
    ReferenceCorpusDescriptor,
    ReferenceCorpusError,
    add_user_reference_files,
    build_reference_corpus_index,
    create_user_reference_corpus,
    delete_user_reference_corpus,
    list_reference_corpora,
    load_corpus_index,
    validate_reference_corpus,
)
from versevad.ui.design import (
    PUBLICATION_CHART_COLORS,
    publication_chart,
    render_dataframe,
    render_empty_state,
    render_workspace_header,
)
from versevad.ui.versemap import render_versemap
from versevad.ui.profile_controls import render_fixed_report_profile_controls
from versevad.versemap import VerseMapConfiguration
from versevad.versemap.profile import FEATURE_BY_ID


def _hosted() -> bool:
    return os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") == "1"


def _render_versemap_fixed_profile_controls(workspace_id: str) -> None:
    render_fixed_report_profile_controls(
        workspace_id,
        profile_name="VerseMap Standard Profile 1.0",
        lexical_scope="Content words only; stopwords removed",
        aggregation_weighting="Token-weighted; repetition retained",
        explanation=(
            "Corpus Browser reads the registered reference index rather than "
            "reaggregating it. These controls are disabled because changing them "
            "would make reference poems methodologically incomparable. Formal and "
            "structural dimensions retain their own documented fixed rules."
        ),
    )


def _corpora(*, indexed_only: bool = False) -> tuple[ReferenceCorpusDescriptor, ...]:
    rows = list_reference_corpora(include_user=not _hosted())
    if indexed_only:
        rows = tuple(item for item in rows if item.index_available)
    return tuple(rows)


def _corpus_selector(
    label: str,
    *,
    key: str,
    indexed_only: bool = False,
) -> ReferenceCorpusDescriptor | None:
    corpora = _corpora(indexed_only=indexed_only)
    if not corpora:
        return None
    by_label = {
        f"{item.display_name} | {item.scope_label}": item for item in corpora
    }
    selected = st.selectbox(label, options=tuple(by_label), key=key)
    return by_label[selected]


def _corpus_summary_frame(
    corpora: Iterable[ReferenceCorpusDescriptor],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Corpus": item.display_name,
                "Scope": item.scope_label,
                "VerseMap Index": "Ready" if item.index_available else "Not built",
                "Poems": item.poem_count,
                "Poets": item.poet_count,
                "Release": item.release_id or "--",
                "Model": item.model_id or "--",
            }
            for item in corpora
        ]
    )


def _issues_frame(result) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Level": issue.level.title(),
                "Code": issue.code.replace("_", " ").title(),
                "Path": issue.path,
                "Message": issue.message,
            }
            for issue in result.issues
        ],
        columns=("Level", "Code", "Path", "Message"),
    )


def _corpus_profile_frames(index) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build corpus summaries and coverage-aware centroid distances."""

    features = tuple(index.features)
    total_weight = sum(item.weight for item in features)
    raw_by_feature = {
        item.feature_id: pd.Series(
            [
                point.value_map.get(item.feature_id)
                for point in index.poems
                if point.value_map.get(item.feature_id) is not None
            ],
            dtype=float,
        )
        for item in features
    }
    summary_rows = []
    for feature in features:
        definition = FEATURE_BY_ID[feature.feature_id]
        series = raw_by_feature[feature.feature_id]
        summary_rows.append(
            {
                "Dimension": definition.label,
                "Group": (
                    definition.group_id.replace("_", " ").title()
                    .replace("Vad", "VAD")
                    .replace("Pos", "POS")
                ),
                "Available Poems": len(series),
                "Corpus Coverage": (
                    len(series) / len(index.poems) if index.poems else None
                ),
                "Corpus Mean": series.mean() if len(series) else None,
                "Population SD": (
                    series.std(ddof=0) if len(series) else None
                ),
                "Median": series.median() if len(series) else None,
                "Minimum": series.min() if len(series) else None,
                "Maximum": series.max() if len(series) else None,
                "Profile Weight": feature.weight,
            }
        )

    rows: list[dict[str, object]] = []
    for point in index.poems:
        values = point.value_map
        weighted_squared_distance = 0.0
        available_weight = 0.0
        for feature in features:
            value = values.get(feature.feature_id)
            if value is None:
                continue
            definition = FEATURE_BY_ID[feature.feature_id]
            transformed = (
                math.log1p(max(float(value), 0.0))
                if definition.transform == "log1p"
                else float(value)
            )
            z_score = (
                (transformed - feature.mean) / feature.population_sd
                if feature.population_sd > 1e-12
                else 0.0
            )
            weighted_squared_distance += feature.weight * z_score**2
            available_weight += feature.weight
        distance = (
            math.sqrt(weighted_squared_distance / available_weight)
            if available_weight
            else None
        )
        row: dict[str, object] = {
            "Poem": point.title,
            "Poet": point.poet_name,
            "Poem ID": point.point_id,
            "Source Path": point.relative_path,
            "Component 1": point.coordinate_1,
            "Component 2": point.coordinate_2,
            "Profile Evidence Weight": (
                available_weight / total_weight if total_weight else None
            ),
            "Centroid Distance": distance,
        }
        row.update(
            {
                FEATURE_BY_ID[feature.feature_id].label: values.get(
                    feature.feature_id
                )
                for feature in features
            }
        )
        rows.append(row)

    distances = sorted(
        float(row["Centroid Distance"])
        for row in rows
        if row["Centroid Distance"] is not None
    )
    count = len(distances)
    for row in rows:
        value = row["Centroid Distance"]
        if value is None or not count:
            row["Characteristicity Percentile"] = None
            row["Distinctiveness Percentile"] = None
            continue
        numeric = float(value)
        lower = bisect_left(distances, numeric)
        equal = bisect_right(distances, numeric) - lower
        distinctiveness = (lower + 0.5 * equal) / count
        row["Distinctiveness Percentile"] = distinctiveness
        row["Characteristicity Percentile"] = 1.0 - distinctiveness
    return pd.DataFrame(summary_rows), pd.DataFrame(rows)


def _render_corpus_versemap(index) -> None:
    poets = tuple(sorted({point.poet_name for point in index.poems}))
    selected_poets = st.multiselect(
        "Poets shown",
        options=poets,
        default=poets,
        key="corpus_browser_map_poets",
    )
    selected_set = set(selected_poets)
    rows = [
        {
            "Kind": "Poem",
            "Poet": point.poet_name,
            "Title": point.title,
            "Component 1": point.coordinate_1,
            "Component 2": point.coordinate_2,
        }
        for point in index.poems
        if point.poet_name in selected_set
    ]
    rows.extend(
        {
            "Kind": "Poet centroid",
            "Poet": point.poet_name,
            "Title": point.poet_name,
            "Component 1": point.coordinate_1,
            "Component 2": point.coordinate_2,
        }
        for point in index.poets
        if point.poet_name in selected_set
    )
    if not rows:
        st.info("Select at least one poet to display the corpus map.")
        return
    frame = pd.DataFrame(rows)
    chart = (
        alt.Chart(frame)
        .mark_circle(strokeWidth=1)
        .encode(
            x=alt.X("Component 1:Q", title="Component 1"),
            y=alt.Y("Component 2:Q", title="Component 2"),
            color=alt.Color("Kind:N", title="Point type"),
            shape=alt.Shape("Kind:N", title="Point type"),
            size=alt.Size(
                "Kind:N",
                scale=alt.Scale(
                    domain=["Poem", "Poet centroid"],
                    range=[55, 180],
                ),
                legend=None,
            ),
            opacity=alt.Opacity(
                "Kind:N",
                scale=alt.Scale(
                    domain=["Poem", "Poet centroid"],
                    range=[0.55, 1.0],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Kind:N"),
                alt.Tooltip("Poet:N"),
                alt.Tooltip("Title:N"),
                alt.Tooltip("Component 1:Q", format=".3f"),
                alt.Tooltip("Component 2:Q", format=".3f"),
            ],
        )
        .properties(height=560)
        .interactive()
    )
    st.altair_chart(publication_chart(chart), width="stretch")
    st.caption(
        "Poems and poet centroids use different point styles. PCA components "
        "compress the full Standard Profile for visualization; analytical "
        "distances and characteristicity use the full weighted feature space."
    )


def render_reference_corpora_workspace() -> None:
    render_workspace_header(
        "Reference Corpora",
        (
            "Create, validate, update, index, or remove comparative corpora. "
            "Use Corpus Browser for read-only inspection and analysis."
        ),
        kicker="Validated comparative collections",
        status="Ready",
    )
    corpora = _corpora()
    section = st.selectbox(
        "Report Section",
        ("Overview", "Create & Maintain", "Validation"),
        key="reference_corpora_section",
    )
    if section == "Overview":
        with st.expander("Available Reference Corpora", expanded=False):
            if corpora:
                render_dataframe(
                    _corpus_summary_frame(corpora),
                    hide_index=True,
                    width="stretch",
                )
            else:
                render_empty_state(
                    "No reference corpus is available",
                    "The built-in VerseMap files could not be found.",
                    "Restore the tracked resources and restart VerseVAD.",
                )
        with st.expander("How Reference Corpora Are Used", expanded=False):
            st.write(
                "A source corpus is a folder of poet subfolders containing UTF-8 "
                "plain-text poems. Validation inventories the texts without "
                "rewriting them. A VerseMap index applies Standard Profile 1.0 "
                "uniformly, then records coverage, the release identity, and the "
                "model identity used for comparison."
            )
            st.info(
                "After an index is built, the corpus appears automatically in "
                "Corpus Browser and in standalone VerseMap. Reference Corpora "
                "does not duplicate it into a Saved Project."
            )
        return

    if section == "Create & Maintain":
        if _hosted():
            st.info(
                "Hosted VerseVAD provides the built-in corpus read-only. Create "
                "or service private reference corpora in the downloadable local "
                "edition, where the files remain on that computer."
            )
            with st.expander("Available Hosted Corpus", expanded=False):
                render_dataframe(
                    _corpus_summary_frame(corpora),
                    hide_index=True,
                    width="stretch",
                )
            return

        with st.expander("Create a Local Reference Corpus", expanded=False):
            name = st.text_input(
                "Corpus name",
                key="new_reference_corpus_name",
                placeholder="Nineteenth-Century Lyric",
            )
            default_poet = st.text_input(
                "Default poet for files without a folder",
                key="new_reference_default_poet",
                placeholder="Unknown or mixed authorship",
            )
            uploads = st.file_uploader(
                "Corpus folder",
                type=["txt"],
                accept_multiple_files="directory",
                key="new_reference_corpus_uploads",
                help=(
                    "Prefer one subfolder per poet. If the browser supplies only "
                    "filenames, VerseVAD uses the default poet entered above."
                ),
            )
            if st.button(
                "Create and Validate Corpus",
                type="primary",
                disabled=not uploads,
                key="create_reference_corpus",
            ):
                try:
                    created = create_user_reference_corpus(
                        name,
                        ((item.name, item.getvalue()) for item in uploads),
                        default_poet=default_poet,
                    )
                    st.success(
                        f"{created.display_name} was created in ignored private "
                        "storage. Build its VerseMap index when ready."
                    )
                    st.rerun()
                except (ReferenceCorpusError, OSError) as error:
                    st.error(str(error))

        local = tuple(item for item in corpora if not item.built_in)
        with st.expander("Update, Index, or Remove a Local Corpus", expanded=False):
            if not local:
                st.caption("No private reference corpus has been created yet.")
                return
            by_name = {item.display_name: item for item in local}
            selected_name = st.selectbox(
                "Local corpus",
                options=tuple(by_name),
                key="maintain_reference_corpus",
            )
            selected = by_name[selected_name]
            st.caption(str(selected.source_root))
            update_poet = st.text_input(
                "Default poet for added top-level files",
                key=f"reference_update_poet_{selected.corpus_id}",
            )
            additions = st.file_uploader(
                "Add or replace UTF-8 poem files",
                type=["txt"],
                accept_multiple_files="directory",
                key=f"reference_update_files_{selected.corpus_id}",
            )
            actions = st.columns(3)
            if actions[0].button(
                "Add / Replace Files",
                disabled=not additions,
                key=f"reference_add_{selected.corpus_id}",
                width="stretch",
            ):
                try:
                    add_user_reference_files(
                        selected,
                        ((item.name, item.getvalue()) for item in additions),
                        default_poet=update_poet,
                    )
                    st.success("Files were validated and added. Rebuild the index.")
                    st.rerun()
                except (ReferenceCorpusError, OSError) as error:
                    st.error(str(error))
            if actions[1].button(
                "Build / Refresh Index",
                key=f"reference_index_{selected.corpus_id}",
                width="stretch",
            ):
                progress = st.progress(0.0, text="Preparing Standard Profile 1.0")

                def report(completed: int, total: int, title: str) -> None:
                    progress.progress(
                        completed / max(total, 1),
                        text=f"{completed:,}/{total:,} | {title}",
                    )

                try:
                    result, profile = build_reference_corpus_index(
                        selected,
                        progress=report,
                    )
                    progress.empty()
                    st.success(
                        f"Index ready: {result.poem_count:,} poems; "
                        f"{profile.analyzed_count:,} analyzed and "
                        f"{profile.reused_count:,} reused."
                    )
                    st.rerun()
                except (ReferenceCorpusError, WorkspaceAnalysisError, OSError) as error:
                    progress.empty()
                    st.error(str(error))
            with actions[2].popover("Delete Corpus", width="stretch"):
                confirmation = st.text_input(
                    "Type the exact corpus name",
                    key=f"reference_delete_confirm_{selected.corpus_id}",
                )
                if st.button(
                    "Delete Permanently",
                    type="primary",
                    disabled=confirmation != selected.display_name,
                    key=f"reference_delete_{selected.corpus_id}",
                ):
                    try:
                        delete_user_reference_corpus(
                            selected,
                            confirmation=confirmation,
                        )
                        st.success("The private reference corpus was deleted.")
                        st.rerun()
                    except (ReferenceCorpusError, OSError) as error:
                        st.error(str(error))
        return

    selected = _corpus_selector(
        "Corpus to validate",
        key="reference_validation_corpus",
    )
    if selected is None:
        st.info("No reference corpus is available.")
        return
    with st.expander("Source Inventory Check", expanded=False):
        if st.button(
            "Run Read-Only Validation",
            key=f"validate_reference_{selected.corpus_id}",
            type="primary",
        ):
            try:
                result = validate_reference_corpus(selected)
                metrics = st.columns(4)
                metrics[0].metric("Poems", result.poem_count)
                metrics[1].metric("Poets", result.poet_count)
                metrics[2].metric("Warnings", len(result.warnings))
                metrics[3].metric("Blocking errors", len(result.errors))
                if result.issues:
                    render_dataframe(
                        _issues_frame(result),
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.success("The source inventory passed without warnings.")
            except (OSError, ValueError) as error:
                st.error(str(error))
    with st.expander("Index Identity", expanded=False):
        if selected.index_available:
            st.code(
                f"Release: {selected.release_id}\nModel: {selected.model_id}",
                language=None,
            )
        else:
            st.warning("This source corpus does not yet have a usable VerseMap index.")


def _load_uploaded_versemap_text() -> None:
    upload = st.session_state.get("standalone_versemap_upload")
    if upload is None:
        return
    payload = upload.getvalue()
    signature = hashlib.sha256(payload).hexdigest()
    if st.session_state.get("_standalone_versemap_upload_signature") == signature:
        return
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        st.session_state["_standalone_versemap_upload_error"] = (
            "The selected file is not valid UTF-8."
        )
        return
    st.session_state["_standalone_versemap_upload_signature"] = signature
    st.session_state["standalone_versemap_text"] = text
    if not str(st.session_state.get("standalone_versemap_title", "")).strip():
        st.session_state["standalone_versemap_title"] = Path(upload.name).stem


def render_standalone_versemap_workspace(
    preprocessor: TextPreprocessor,
    readiness: ResourceReadiness,
) -> None:
    render_workspace_header(
        "VerseMap",
        (
            "Place one poem in a fixed, coverage-aware comparative space and "
            "inspect nearby poems, poet centroids, and contributing dimensions."
        ),
        kicker="Standalone comparative exploration",
        status="Ready",
    )
    corpora = _corpora(indexed_only=True)
    if not corpora:
        render_empty_state(
            "No indexed corpus is available",
            "VerseMap needs at least one validated Standard Profile 1.0 index.",
            "Open Collections > Reference Corpora to inspect or build one.",
        )
        return
    st.file_uploader(
        "Choose a UTF-8 poem file (optional)",
        type=["txt"],
        key="standalone_versemap_upload",
        on_change=_load_uploaded_versemap_text,
    )
    upload_error = st.session_state.pop("_standalone_versemap_upload_error", None)
    if upload_error:
        st.error(upload_error)
    fields = st.columns(2)
    title = fields[0].text_input(
        "Poem title or working label",
        key="standalone_versemap_title",
    )
    author = fields[1].text_input(
        "Author (optional)",
        key="standalone_versemap_author",
    )
    text = st.text_area(
        "Poem text",
        height=330,
        key="standalone_versemap_text",
        placeholder="Paste one poem with its original line and stanza breaks.",
    )
    by_name = {
        f"{item.display_name} | {item.scope_label}": item for item in corpora
    }
    selected_name = st.selectbox(
        "Reference corpus",
        options=tuple(by_name),
        key="standalone_versemap_corpus",
    )
    selected = by_name[selected_name]
    with st.expander("Comparison Settings", expanded=False):
        neighbor_count = st.slider(
            "Nearest results to retain",
            min_value=1,
            max_value=25,
            value=10,
            key="standalone_versemap_neighbors",
        )
        shared_weight = st.slider(
            "Minimum shared evidence weight",
            min_value=0.25,
            max_value=1.0,
            value=0.60,
            step=0.05,
            key="standalone_versemap_shared_weight",
            help=(
                "A neighbor is reported only when the poem and reference point "
                "share at least this proportion of registered feature weight."
            ),
        )
        st.caption(
            "All preprocessing and feature definitions remain fixed by VerseMap "
            "Standard Profile 1.0; these controls change only result retention."
        )
    signature = hashlib.sha256(
        (
            title.strip()
            + "\0"
            + author.strip()
            + "\0"
            + text
            + "\0"
            + selected.corpus_id
            + f"\0{neighbor_count}\0{shared_weight:.3f}"
        ).encode("utf-8")
    ).hexdigest()
    if st.button(
        "Map This Poem",
        type="primary",
        width="stretch",
        disabled=not title.strip() or not text.strip(),
        key="run_standalone_versemap",
    ):
        try:
            index = load_corpus_index(selected)
            with st.spinner("Building the fixed VerseMap profile..."):
                analysis = run_workspace_analysis(
                    AnalysisRequest(
                        project_name="Standalone VerseMap",
                        title=title,
                        original_text=text,
                        lexicon_ids=(),
                        minimum_match_requirement=1,
                        text_id=(
                            "standalone-versemap-"
                            + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
                        ),
                        scenario_id="standalone-versemap-1.0",
                        include_versemap=True,
                        versemap_configuration=VerseMapConfiguration(
                            neighbor_count=neighbor_count,
                            minimum_shared_weight=shared_weight,
                        ),
                        analysis_cache_enabled=bool(
                            st.session_state.get("analysis_cache_enabled", True)
                        ),
                        performance_diagnostics=bool(
                            st.session_state.get(
                                "performance_diagnostics_enabled", True
                            )
                        ),
                    ),
                    preprocessor=preprocessor,
                    versemap_index=index,
                )
            st.session_state["standalone_versemap_analysis"] = analysis
            st.session_state["standalone_versemap_signature"] = signature
            st.success("VerseMap comparison complete.")
        except (ReferenceCorpusError, WorkspaceAnalysisError, OSError) as error:
            st.error(str(error))
    analysis = st.session_state.get("standalone_versemap_analysis")
    if isinstance(analysis, WorkspaceAnalysis):
        if st.session_state.get("standalone_versemap_signature") != signature:
            st.warning(
                "The visible poem, corpus, or comparison settings changed. The "
                "result below is historical until you map the poem again."
            )
        render_versemap(
            analysis.versemap,
            show_poem_neighbors=True,
            export_key="standalone",
            note_workspace="VerseMap",
        )
    else:
        with st.expander("What VerseMap Will Report", expanded=False):
            st.write(
                "The result includes a two-dimensional PCA display, full-space "
                "nearest poems and poet centroids, feature values and z-scores, "
                "coverage and eligible counts, methodology, CSV evidence, and a "
                "narrative Word report."
            )
    if not readiness.versemap.available:
        st.caption(
            "The installation check reports the built-in VerseMap model as "
            "unavailable; a selected local indexed corpus may still be usable."
        )


def _corpus_browser_poem_feature_frame(index, point) -> pd.DataFrame:
    feature_by_id = {item.feature_id: item for item in index.features}
    return pd.DataFrame(
        [
            {
                "Dimension": definition.label,
                "Group": (
                    definition.group_id.replace("_", " ").title()
                    .replace("Vad", "VAD")
                    .replace("Pos", "POS")
                ),
                "Poem Value": point.value_map.get(feature_id),
                "Corpus Mean": feature_by_id[feature_id].raw_mean,
                "Corpus SD": feature_by_id[feature_id].raw_population_sd,
                "Standardized Deviation": (
                    (
                        (
                            math.log1p(
                                max(float(point.value_map[feature_id]), 0.0)
                            )
                            if definition.transform == "log1p"
                            else float(point.value_map[feature_id])
                        )
                        - feature_by_id[feature_id].mean
                    )
                    / feature_by_id[feature_id].population_sd
                    if point.value_map.get(feature_id) is not None
                    and feature_by_id[feature_id].population_sd > 1e-12
                    else None
                ),
            }
            for feature_id, definition in FEATURE_BY_ID.items()
            if feature_id in feature_by_id
        ]
    )


def _corpus_browser_vad_diagnostic_frame(points) -> pd.DataFrame:
    rows = []
    for point in points:
        values = point.browser_diagnostic_map
        for dimension in ("valence", "arousal", "dominance"):
            prefix = f"vad_{dimension}"
            rows.append(
                {
                    "Poem": point.title,
                    "Poet": point.poet_name,
                    "Dimension": dimension.title(),
                    "Above Midpoint per Match": values.get(
                        f"{prefix}_above_midpoint_deviation_per_observation"
                    ),
                    "Below Midpoint per Match": values.get(
                        f"{prefix}_below_midpoint_deviation_per_observation"
                    ),
                    "Total Absolute Midpoint Deviation per Match": values.get(
                        f"{prefix}_absolute_midpoint_deviation_per_observation"
                    ),
                    "Above Midpoint per 100 Matches": (
                        values.get(
                            f"{prefix}_above_midpoint_deviation_per_observation"
                        )
                        * 100
                        if values.get(
                            f"{prefix}_above_midpoint_deviation_per_observation"
                        )
                        is not None
                        else None
                    ),
                    "Below Midpoint per 100 Matches": (
                        values.get(
                            f"{prefix}_below_midpoint_deviation_per_observation"
                        )
                        * 100
                        if values.get(
                            f"{prefix}_below_midpoint_deviation_per_observation"
                        )
                        is not None
                        else None
                    ),
                    "Total Absolute Midpoint Deviation per 100 Matches": (
                        values.get(
                            f"{prefix}_absolute_midpoint_deviation_per_observation"
                        )
                        * 100
                        if values.get(
                            f"{prefix}_absolute_midpoint_deviation_per_observation"
                        )
                        is not None
                        else None
                    ),
                    "Average Deviation from Poem Mean": values.get(
                        f"{prefix}_average_deviation_from_poem_mean"
                    ),
                    "Matched Observations": (
                        point.vad_midpoint_matched_observations
                    ),
                }
            )
    return pd.DataFrame(rows)


def _render_corpus_browser_poem(index, poems_frame, point) -> None:
    point_summary = poems_frame.loc[
        poems_frame["Poem ID"] == point.point_id
    ].iloc[0]
    st.markdown(f"### {point.title}")
    st.caption(f"{point.poet_name} · corpus-relative Standard Profile 1.0")
    profile_metrics = st.columns(4)
    profile_metrics[0].metric(
        "Centroid Distance",
        (
            f"{point_summary['Centroid Distance']:.3f}"
            if pd.notna(point_summary["Centroid Distance"])
            else "Unavailable"
        ),
    )
    profile_metrics[1].metric(
        "Characteristicity",
        (
            f"{point_summary['Characteristicity Percentile']:.1%}"
            if pd.notna(point_summary["Characteristicity Percentile"])
            else "Unavailable"
        ),
    )
    profile_metrics[2].metric(
        "Distinctiveness",
        (
            f"{point_summary['Distinctiveness Percentile']:.1%}"
            if pd.notna(point_summary["Distinctiveness Percentile"])
            else "Unavailable"
        ),
    )
    profile_metrics[3].metric(
        "Profile Evidence",
        (
            f"{point_summary['Profile Evidence Weight']:.1%}"
            if pd.notna(point_summary["Profile Evidence Weight"])
            else "Unavailable"
        ),
    )
    report = st.selectbox(
        "Report Section",
        (
            "Profile Overview",
            "Metric Detail",
            "VAD Load & Volatility",
            "Source Text",
        ),
        key="corpus_browser_poem_report",
    )
    _render_versemap_fixed_profile_controls("corpus_browser_poem")
    feature_frame = _corpus_browser_poem_feature_frame(index, point)
    if report == "Profile Overview":
        overview_rows = []
        for group, rows in feature_frame.groupby("Group", sort=False):
            available = rows.dropna(subset=["Standardized Deviation"])
            if available.empty:
                largest_dimension = "Unavailable"
                largest_deviation = None
            else:
                largest_index = available[
                    "Standardized Deviation"
                ].abs().idxmax()
                largest_dimension = available.loc[largest_index, "Dimension"]
                largest_deviation = available.loc[
                    largest_index, "Standardized Deviation"
                ]
            overview_rows.append(
                {
                    "Profile Area": group,
                    "Available Dimensions": len(available),
                    "Registered Dimensions": len(rows),
                    "Largest Corpus-Relative Departure": largest_dimension,
                    "Departure (SD)": largest_deviation,
                }
            )
        render_dataframe(
            pd.DataFrame(overview_rows).style.format(
                {"Departure (SD)": "{:+.3f}"},
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Largest Corpus-Relative Departure identifies the available dimension "
            "furthest from the selected corpus mean. Departure (SD) is its signed "
            "standardized deviation: positive is above the corpus mean and negative "
            "is below it. Use Metric Detail to inspect every dimension."
        )
        return
    if report == "VAD Load & Volatility":
        diagnostics = _corpus_browser_vad_diagnostic_frame((point,))
        if diagnostics.empty or diagnostics[
            "Average Deviation from Poem Mean"
        ].isna().all():
            st.info(
                "This index predates Corpus Browser VAD diagnostics. Run the "
                "VerseMap reference updater once to add them without changing "
                "Standard Profile 1.0 or the PCA model."
            )
            return
        st.markdown("#### Length-Normalized Midpoint Deviation")
        midpoint_rows = []
        for row in diagnostics.to_dict("records"):
            for measure, per_match, per_100 in (
                (
                    "Above-midpoint deviation",
                    row["Above Midpoint per Match"],
                    row["Above Midpoint per 100 Matches"],
                ),
                (
                    "Below-midpoint deviation",
                    row["Below Midpoint per Match"],
                    row["Below Midpoint per 100 Matches"],
                ),
                (
                    "Total absolute deviation",
                    row["Total Absolute Midpoint Deviation per Match"],
                    row["Total Absolute Midpoint Deviation per 100 Matches"],
                ),
            ):
                midpoint_rows.append(
                    {
                        "Dimension": row["Dimension"],
                        "Measure": measure,
                        "Per Matched Observation": per_match,
                        "Per 100 Matches": per_100,
                    }
                )
        render_dataframe(
            pd.DataFrame(midpoint_rows).style.format(
                {
                    "Per Matched Observation": "{:.3f}",
                    "Per 100 Matches": "{:.3f}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.markdown("#### Mean-Centered Lexical Volatility")
        render_dataframe(
            diagnostics[
                [
                    "Dimension",
                    "Average Deviation from Poem Mean",
                    "Matched Observations",
                ]
            ].style.format(
                {"Average Deviation from Poem Mean": "{:.3f}"},
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Average deviation is mean absolute deviation from the poem's own "
            "VAD mean. Population SD in Profile Overview squares departures and "
            "therefore emphasizes extremes more strongly. Both are length-neutral "
            "and do not preserve lexical order."
        )
        return
    if report == "Metric Detail":
        groups = tuple(dict.fromkeys(feature_frame["Group"].tolist()))
        group = st.selectbox(
            "Profile Area",
            groups,
            key="corpus_browser_poem_group",
        )
        selected = feature_frame.loc[feature_frame["Group"] == group].copy()
        chart_frame = selected.dropna(subset=["Standardized Deviation"])
        if not chart_frame.empty:
            chart_data = chart_frame.rename(
                columns={
                    "Poem Value": "poem_value",
                    "Corpus Mean": "corpus_mean",
                    "Standardized Deviation": "z_score",
                }
            )
            chart = (
                alt.Chart(chart_data)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "z_score:Q",
                        stack=None,
                        scale=alt.Scale(zero=True),
                        title="Standardized deviation from corpus mean",
                    ),
                    y=alt.Y("Dimension:N", sort=None, title=None),
                    color=alt.condition(
                        "datum.z_score >= 0",
                        alt.value(PUBLICATION_CHART_COLORS[0]),
                        alt.value(PUBLICATION_CHART_COLORS[1]),
                    ),
                    tooltip=[
                        "Dimension:N",
                        alt.Tooltip(
                            "poem_value:Q",
                            title="Poem Value",
                            format=".3f",
                        ),
                        alt.Tooltip(
                            "corpus_mean:Q",
                            title="Corpus Mean",
                            format=".3f",
                        ),
                        alt.Tooltip(
                            "z_score:Q",
                            title="Standardized Deviation",
                            format=".3f",
                        ),
                    ],
                )
                .properties(height=max(220, min(560, len(selected) * 34)))
            )
            st.altair_chart(publication_chart(chart), width="stretch")
        render_dataframe(
            selected.style.format(
                {
                    "Poem Value": "{:.3f}",
                    "Corpus Mean": "{:.3f}",
                    "Corpus SD": "{:.3f}",
                    "Standardized Deviation": "{:+.3f}",
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Positive standardized deviations are above the selected corpus "
            "mean; negative values are below it. These are descriptive z-scores."
        )
        return
    if not point.relative_path:
        st.caption("No source path is recorded for this profile.")
        return
    source = (index.source_root / point.relative_path).resolve()
    try:
        source.relative_to(index.source_root.resolve())
        text = source.read_text(encoding="utf-8-sig")
        st.code(text, language=None, wrap_lines=True)
    except (ValueError, OSError, UnicodeError):
        st.warning("The recorded source text could not be opened safely.")


def render_corpus_browser_workspace() -> None:
    render_workspace_header(
        "Corpus Browser",
        (
            "Read corpus contents, identities, distributions, coverage, and "
            "poem-level Standard Profile records without editing source texts."
        ),
        kicker="Read-only collection inspection",
        status="Ready",
    )
    selected = _corpus_selector(
        "Corpus",
        key="corpus_browser_corpus",
        indexed_only=True,
    )
    if selected is None:
        render_empty_state(
            "No indexed corpus is available",
            "Corpus Browser reads finished VerseMap reference indexes.",
            "Open Reference Corpora to validate and index a collection.",
        )
        return
    try:
        index = load_corpus_index(selected)
    except ReferenceCorpusError as error:
        st.error(str(error))
        return
    summary_frame, poems_frame = _corpus_profile_frames(index)
    poem_scope_labels = {
        item.point_id: f"{item.poet_name} · {item.title}"
        for item in index.poems
    }
    scope = st.selectbox(
        "Result Scope",
        ("Whole Corpus", *tuple(poem_scope_labels)),
        format_func=lambda value: (
            value if value == "Whole Corpus" else poem_scope_labels[value]
        ),
        key="corpus_browser_scope",
    )
    if scope != "Whole Corpus":
        point = next(item for item in index.poems if item.point_id == scope)
        _render_corpus_browser_poem(index, poems_frame, point)
        return
    section = st.selectbox(
        "Report Section",
        (
            "Overview",
            "VerseMap",
            "Standard Profile Table",
            "Distributions",
            "VAD Load & Volatility",
        ),
        key="corpus_browser_section",
    )
    _render_versemap_fixed_profile_controls("corpus_browser")
    if section == "Overview":
        metrics = st.columns(4)
        metrics[0].metric("Poems", len(index.poems))
        metrics[1].metric("Poets", len(index.poets))
        metrics[2].metric("Dimensions", len(index.features))
        metrics[3].metric(
            "PCA variance shown",
            f"{index.explained_variance_1 + index.explained_variance_2:.1%}",
        )
        with st.expander("Release and Model Identity", expanded=False):
            st.code(
                f"Profile: {index.profile_id}\n"
                f"Profile build: {index.profile_build_id}\n"
                f"Release: {index.reference_release_id}\n"
                f"Model: {index.model_id}",
                language=None,
            )
        with st.expander(
            "Standard Profile Means, Dispersion, and Coverage",
            expanded=False,
        ):
            render_dataframe(
                summary_frame,
                hide_index=True,
                width="stretch",
                column_config={
                    "Corpus Coverage": st.column_config.ProgressColumn(
                        min_value=0.0, max_value=1.0, format="percent"
                    )
                },
            )
            st.caption(
                "Population SD describes poem-to-poem dispersion within the "
                "selected corpus. Missing values remain missing and reduce the "
                "available-poem count; they are not replaced with a neutral score."
            )
        st.info(
            "Reference Corpora creates and services indexes. Corpus Browser is "
            "the read-only place to inspect their maps, distributions, poem "
            "profiles, and corpus-relative characteristicity."
        )
        return

    if section == "VerseMap":
        _render_corpus_versemap(index)
        return

    if section == "Standard Profile Table":
        query = st.text_input(
            "Filter titles or poets",
            key="corpus_browser_query",
        ).strip().casefold()
        sort_options = (
            "Characteristicity Percentile",
            "Distinctiveness Percentile",
            "Centroid Distance",
            "Poem",
            "Poet",
            *(
                FEATURE_BY_ID[item.feature_id].label
                for item in index.features
            ),
        )
        sort_columns = st.columns([3, 1])
        sort_by = sort_columns[0].selectbox(
            "Sort poems by",
            options=sort_options,
            key="corpus_browser_sort_by",
        )
        ascending = sort_columns[1].checkbox(
            "Ascending",
            value=sort_by in {"Poem", "Poet", "Centroid Distance"},
            key="corpus_browser_sort_ascending",
        )
        filtered = poems_frame
        if query:
            matches = (
                filtered["Poem"].astype(str)
                + " "
                + filtered["Poet"].astype(str)
            ).str.casefold().str.contains(re.escape(query), regex=True)
            filtered = filtered.loc[matches]
        filtered = filtered.sort_values(
            sort_by,
            ascending=ascending,
            na_position="last",
            kind="stable",
        )
        dimension_groups: dict[str, list[str]] = {}
        for feature in index.features:
            definition = FEATURE_BY_ID[feature.feature_id]
            dimension_groups.setdefault(
                definition.group_id.replace("_", " ").title()
                .replace("Vad", "VAD")
                .replace("Pos", "POS"),
                [],
            ).append(definition.label)
        display_group = st.selectbox(
            "Displayed Metric Group",
            ("Corpus Relationship", *tuple(dimension_groups)),
            key="corpus_browser_table_group",
            help=(
                "The screen shows one readable metric family at a time. The CSV "
                "download retains every Standard Profile dimension."
            ),
        )
        display_columns = [
            "Poem",
            "Poet",
            "Centroid Distance",
            "Characteristicity Percentile",
            "Distinctiveness Percentile",
            "Profile Evidence Weight",
        ]
        if display_group != "Corpus Relationship":
            display_columns.extend(dimension_groups[display_group])
        if sort_by in filtered.columns and sort_by not in display_columns:
            display_columns.append(sort_by)
        display_frame = filtered[
            [column for column in display_columns if column in filtered.columns]
        ]
        render_dataframe(
            display_frame,
            hide_index=True,
            width="stretch",
            height=560,
            column_config={
                "Profile Evidence Weight": st.column_config.ProgressColumn(
                    min_value=0.0,
                    max_value=1.0,
                    format="percent",
                ),
                "Characteristicity Percentile": (
                    st.column_config.ProgressColumn(
                        min_value=0.0,
                        max_value=1.0,
                        format="percent",
                    )
                ),
                "Distinctiveness Percentile": (
                    st.column_config.ProgressColumn(
                        min_value=0.0,
                        max_value=1.0,
                        format="percent",
                    )
                ),
            },
        )
        st.download_button(
            "Download Standard Profile Table (CSV)",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected.corpus_id.replace(':', '_')}_standard_profile.csv",
            mime="text/csv",
            key=f"download_corpus_profile_{selected.corpus_id}",
        )
        st.caption(
            "Centroid Distance is a coverage-renormalized, profile-weighted RMS "
            "z-distance from this corpus's own centroid. Characteristicity is "
            "the reverse percentile rank (higher means more corpus-typical); "
            "Distinctiveness is the forward percentile rank (higher means more "
            "unusual). They are descriptive ranks, not probabilities, quality "
            "scores, or authorship claims. The visible table is intentionally "
            "concise; the download contains the complete profile matrix."
        )
        return

    if section == "VAD Load & Volatility":
        diagnostics = _corpus_browser_vad_diagnostic_frame(index.poems)
        if diagnostics.empty or diagnostics[
            "Average Deviation from Poem Mean"
        ].isna().all():
            st.info(
                "This index predates Corpus Browser VAD diagnostics. Run the "
                "VerseMap reference updater once to add them without changing "
                "Standard Profile 1.0 or the PCA model."
            )
            return
        dimension = st.selectbox(
            "VAD dimension",
            ("Valence", "Arousal", "Dominance"),
            key="corpus_browser_vad_diagnostic_dimension",
        )
        selected_diagnostics = diagnostics.loc[
            diagnostics["Dimension"] == dimension
        ].copy()
        sort_by = st.selectbox(
            "Sort by",
            (
                "Average Deviation from Poem Mean",
                "Total Absolute Midpoint Deviation per Match",
                "Above Midpoint per Match",
                "Below Midpoint per Match",
                "Poem",
            ),
            key="corpus_browser_vad_diagnostic_sort",
        )
        selected_diagnostics = selected_diagnostics.sort_values(
            sort_by,
            ascending=sort_by == "Poem",
            na_position="last",
        )
        render_dataframe(
            selected_diagnostics.style.format(
                {
                    column: "{:.3f}"
                    for column in selected_diagnostics.columns
                    if column not in {"Poem", "Poet", "Dimension", "Matched Observations"}
                },
                na_rep="—",
            ),
            hide_index=True,
            width="stretch",
            height=620,
        )
        st.caption(
            "Per-match and per-100 midpoint deviations are the same rates on "
            "different display scales. Average deviation from poem mean is mean "
            "absolute deviation; population SD remains available in the Standard "
            "Profile views and emphasizes extremes more strongly."
        )
        return
    if section == "Distributions":
        feature_labels = {
            FEATURE_BY_ID[item.feature_id].label: item for item in index.features
        }
        label = st.selectbox(
            "Dimension",
            options=tuple(feature_labels),
            key="corpus_browser_feature",
        )
        feature = feature_labels[label]
        values = [
            point.value_map.get(feature.feature_id)
            for point in index.poems
            if point.value_map.get(feature.feature_id) is not None
        ]
        chart_frame = pd.DataFrame({"Value": values})
        if values:
            chart = (
                alt.Chart(chart_frame)
                .mark_bar(color=PUBLICATION_CHART_COLORS[0])
                .encode(
                    x=alt.X("Value:Q", bin=alt.Bin(maxbins=28), title=label),
                    y=alt.Y("count():Q", title="Reference poems"),
                    tooltip=["count():Q"],
                )
                .properties(height=420)
            )
            st.altair_chart(publication_chart(chart), width="stretch")
            metrics = st.columns(4)
            series = pd.Series(values, dtype=float)
            metrics[0].metric("Available poems", len(series))
            metrics[1].metric("Mean", f"{series.mean():.3f}")
            metrics[2].metric("Population SD", f"{series.std(ddof=0):.3f}")
            metrics[3].metric("Median", f"{series.median():.3f}")
        else:
            st.info("This dimension has no available poem values.")
        st.caption(
            f"Registered weight {feature.weight:.3f}; values available for "
            f"{feature.available_reference_count:,} reference poems."
        )
        return

    poem_labels = {
        f"{item.poet_name} | {item.title} | {item.point_id[-8:]}": item
        for item in index.poems
    }
    selected_label = st.selectbox(
        "Poem",
        options=tuple(poem_labels),
        key="corpus_browser_poem",
    )
    point = poem_labels[selected_label]
    st.markdown(f"### {point.title}")
    st.caption(f"{point.poet_name} | {point.point_id}")
    point_summary = poems_frame.loc[
        poems_frame["Poem ID"] == point.point_id
    ].iloc[0]
    profile_metrics = st.columns(4)
    profile_metrics[0].metric(
        "Centroid distance",
        (
            f"{point_summary['Centroid Distance']:.3f}"
            if pd.notna(point_summary["Centroid Distance"])
            else "Unavailable"
        ),
    )
    profile_metrics[1].metric(
        "Characteristicity",
        (
            f"{point_summary['Characteristicity Percentile']:.1%}"
            if pd.notna(point_summary["Characteristicity Percentile"])
            else "Unavailable"
        ),
    )
    profile_metrics[2].metric(
        "Distinctiveness",
        (
            f"{point_summary['Distinctiveness Percentile']:.1%}"
            if pd.notna(point_summary["Distinctiveness Percentile"])
            else "Unavailable"
        ),
    )
    profile_metrics[3].metric(
        "Profile evidence weight",
        (
            f"{point_summary['Profile Evidence Weight']:.1%}"
            if pd.notna(point_summary["Profile Evidence Weight"])
            else "Unavailable"
        ),
    )
    feature_by_id = {item.feature_id: item for item in index.features}
    render_dataframe(
        pd.DataFrame(
            [
                {
                    "Dimension": definition.label,
                    "Group": definition.group_id.replace("_", " ").title(),
                    "Poem Value": point.value_map.get(feature_id),
                    "Corpus Mean": feature_by_id[feature_id].raw_mean,
                    "Corpus SD": feature_by_id[feature_id].raw_population_sd,
                    "Standardized Deviation": (
                        (
                            (
                                math.log1p(
                                    max(
                                        float(point.value_map[feature_id]),
                                        0.0,
                                    )
                                )
                                if definition.transform == "log1p"
                                else float(point.value_map[feature_id])
                            )
                            - feature_by_id[feature_id].mean
                        )
                        / feature_by_id[feature_id].population_sd
                        if point.value_map.get(feature_id) is not None
                        and feature_by_id[feature_id].population_sd > 1e-12
                        else None
                    ),
                }
                for feature_id, definition in FEATURE_BY_ID.items()
                if feature_id in feature_by_id
            ]
        ),
        hide_index=True,
        width="stretch",
        height=560,
    )
    st.caption(
        "Standardized Deviation is the poem's z-score within this corpus for "
        "that dimension. Positive values are above the corpus mean; negative "
        "values are below it. Corpus-relative ranks do not imply literary "
        "quality, influence, or authorship."
    )
    with st.expander("Source Text", expanded=False):
        if not point.relative_path:
            st.caption("No source path is recorded for this profile.")
        else:
            source = (index.source_root / point.relative_path).resolve()
            try:
                source.relative_to(index.source_root.resolve())
                text = source.read_text(encoding="utf-8-sig")
                st.code(text, language=None, wrap_lines=True)
            except (ValueError, OSError, UnicodeError):
                st.warning("The recorded source text could not be opened safely.")


def render_form_library_workspace() -> None:
    render_workspace_header(
        "Form Library",
        (
            "Browse the traditional definitions and weighted evidence rules used "
            "by Inherited Form Analysis."
        ),
        kicker="Educational inherited-form reference",
        status="Ready",
    )
    query = st.text_input("Search forms", key="form_library_search").strip().casefold()
    families = sorted({profile.family for profile in FORM_PROFILES})
    family = st.selectbox(
        "Family",
        options=("All families", *families),
        key="form_library_family",
    )
    modes = ("All assessment modes", "automatic", "partial", "manual")
    mode = st.selectbox(
        "Assessment mode",
        options=modes,
        key="form_library_mode",
    )
    matches = [
        profile
        for profile in FORM_PROFILES
        if (
            not query
            or query
            in " ".join(
                (
                    profile.name,
                    profile.family,
                    profile.tradition,
                    profile.definition,
                )
            ).casefold()
        )
        and (family == "All families" or profile.family == family)
        and (mode == "All assessment modes" or profile.assessment_mode == mode)
    ]
    st.caption(
        f"{len(matches):,} of {len(FORM_PROFILES):,} forms | registry "
        f"{PROFILE_REGISTRY_VERSION}"
    )
    if not matches:
        st.info("No form matches the current filters.")
        return
    profile = st.selectbox(
        "Form",
        options=tuple(matches),
        format_func=lambda item: item.name,
        key="form_library_profile",
    )
    with st.expander("Traditional Definition", expanded=False):
        st.markdown(f"### {profile.name}")
        st.write(profile.definition)
        st.caption(
            f"Family: {profile.family} | Tradition: {profile.tradition} | "
            f"Assessment: {profile.assessment_mode.title()}"
        )
        st.info(profile.tooltip_definition)
    with st.expander("Requirements and Weights", expanded=False):
        total_weight = sum(rule.weight for rule in profile.rules)
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Feature": rule.label,
                        "Role": rule.role.value.title(),
                        "Expected Evidence": rule.expected,
                        "Weight": rule.weight,
                        "Share of Candidate Score": rule.weight / total_weight,
                        "Parameters": "; ".join(
                            f"{key}={value}" for key, value in rule.parameters
                        )
                        or "--",
                    }
                    for rule in profile.rules
                ]
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "Share of Candidate Score": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="percent"
                )
            },
        )
        st.caption(
            "Required, preferred, and optional describe traditional importance. "
            "Weights contribute only when VerseVAD has enough coverage to assess "
            "the feature; Match % and Evidence Coverage % remain distinct."
        )
    with st.expander("Limitations and Sources", expanded=False):
        if profile.limitations:
            for limitation in profile.limitations:
                st.markdown(f"- {limitation}")
        else:
            st.caption("No profile-specific limitation is recorded.")
        st.markdown("#### Sources")
        for source in profile.source_urls:
            st.markdown(f"- [{source}]({source})")


_DOCUMENTATION_SOURCES = (
    (
        "Documentation Index",
        "docs/index.md",
        "Maintained entry point for user, methods, resources, and development guidance.",
    ),
    (
        "User Guide",
        "docs/user-guide.md",
        "Task-oriented operating guide for navigation, analysis, saving, and export.",
    ),
    (
        "Resource Installation",
        "docs/resource-installation.md",
        "Licensed dataset download, naming, and placement instructions.",
    ),
    ("macOS Installation", "docs/macos-installation.md", "First-run and launcher guidance."),
    ("Updating VerseVAD", "docs/updating.md", "Safe GitHub update workflows."),
    (
        "Reference Corpora",
        "docs/versemap-reference-corpus.md",
        "Maintainer and private reference-corpus workflow.",
    ),
    (
        "Analysis Library",
        "docs/research-library.md",
        "Explicit saves, historical revisions, notes, and privacy.",
    ),
    ("Project README", "README.md", "Project overview, installation, and entry points."),
)
_METHODOLOGY_SOURCES = (
    ("Metric Formulas, Denominators, and Limitations", "docs/methodology.md"),
    ("Lexicons and Provenance", "docs/lexicons.md"),
    ("VerseMap Standard Profile 1.0", "docs/versemap-standard-profile.md"),
    ("Inherited Form Registry", "docs/inherited-form-registry-v2.md"),
    ("Data Model", "docs/data-model.md"),
)


@st.cache_data(show_spinner=False)
def _read_markdown(path_value: str, modified_ns: int) -> str:
    del modified_ns
    return Path(path_value).read_text(encoding="utf-8")


def _document_text(relative_path: str) -> tuple[Path, str]:
    path = (PROJECT_ROOT / relative_path).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise OSError("Documentation path escaped the VerseVAD installation.") from error
    return path, _read_markdown(str(path), path.stat().st_mtime_ns)


def _markdown_sections(text: str) -> tuple[tuple[str, str], ...]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    if not matches:
        return (("Document", text),)
    sections: list[tuple[str, str]] = []
    introduction = text[: matches[0].start()].strip()
    if introduction:
        sections.append(("Overview", introduction))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.start() : end].strip()))
    return tuple(sections)


def render_documentation_workspace() -> None:
    render_workspace_header(
        "Documentation",
        (
            "Read the versioned operating guidance packaged with this exact "
            "VerseVAD release."
        ),
        kicker="In-application help and installation guidance",
        status="Ready",
    )
    by_label = {label: (path, description) for label, path, description in _DOCUMENTATION_SOURCES}
    label = st.selectbox(
        "Documentation Section",
        options=tuple(by_label),
        key="documentation_source",
    )
    path_value, description = by_label[label]
    st.caption(description)
    try:
        path, text = _document_text(path_value)
    except OSError as error:
        st.error(str(error))
        return
    with st.expander(label, expanded=False):
        st.markdown(text)
    if label == "User Guide":
        manual = PROJECT_ROOT / "docs" / "VerseVAD_User_Manual.docx"
        if manual.is_file():
            st.download_button(
                "Download Printable Word Manual",
                data=manual.read_bytes(),
                file_name=manual.name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                key="download_in_app_user_manual",
            )
    st.caption(f"Packaged source: {path.relative_to(PROJECT_ROOT).as_posix()}")


def render_methodology_workspace() -> None:
    render_workspace_header(
        "Methodology",
        (
            "Inspect how metrics are calculated, which evidence is eligible, "
            "where data came from, and what each result cannot establish."
        ),
        kicker="Calculations, provenance, and known limitations",
        status="Ready",
    )
    by_label = {label: path for label, path in _METHODOLOGY_SOURCES}
    source_label = st.selectbox(
        "Methodology Source",
        options=tuple(by_label),
        key="methodology_source",
    )
    try:
        path, text = _document_text(by_label[source_label])
    except OSError as error:
        st.error(str(error))
        return
    sections = _markdown_sections(text)
    query = st.text_input(
        "Filter topics",
        key="methodology_search",
        placeholder="Valence, HD-D, inherited form, coverage...",
    ).strip().casefold()
    filtered = [
        (title, body)
        for title, body in sections
        if not query or query in f"{title}\n{body}".casefold()
    ]
    if not filtered:
        st.info("No methodology topic matches that search.")
        return
    by_title = {title: body for title, body in filtered}
    topic = st.selectbox(
        "Topic",
        options=tuple(by_title),
        key="methodology_topic",
    )
    with st.expander(topic, expanded=False):
        st.markdown(by_title[topic])
    st.caption(
        f"{len(filtered):,} matching topics | packaged source: "
        f"{path.relative_to(PROJECT_ROOT).as_posix()}"
    )


__all__ = [
    "render_corpus_browser_workspace",
    "render_documentation_workspace",
    "render_form_library_workspace",
    "render_methodology_workspace",
    "render_reference_corpora_workspace",
    "render_standalone_versemap_workspace",
]
