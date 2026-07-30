"""Final library, corpus, VerseMap, and learning workspaces."""

from __future__ import annotations

import hashlib
import os
import re
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
from versevad.versemap import VerseMapConfiguration
from versevad.versemap.profile import FEATURE_BY_ID


def _hosted() -> bool:
    return os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") == "1"


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


def render_reference_corpora_workspace() -> None:
    render_workspace_header(
        "Reference Corpora",
        (
            "Inspect the built-in public-domain collection and, in local "
            "installations, create and maintain private corpora for Corpus "
            "Browser and VerseMap."
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
                "Corpus Browser is read-only. Standalone VerseMap can use any "
                "listed corpus whose index is marked Ready."
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
    section = st.selectbox(
        "Report Section",
        ("Overview", "Contents", "Distributions", "Poem Profiles"),
        key="corpus_browser_section",
    )
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
        with st.expander("Coverage by Registered Dimension", expanded=False):
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Dimension": FEATURE_BY_ID[item.feature_id].label,
                            "Group": FEATURE_BY_ID[item.feature_id].group_id.replace(
                                "_", " "
                            ).title(),
                            "Available Poems": item.available_reference_count,
                            "Corpus Coverage": (
                                item.available_reference_count / len(index.poems)
                                if index.poems
                                else None
                            ),
                            "Reference Mean": item.raw_mean,
                            "Reference SD": item.raw_population_sd,
                            "Weight": item.weight,
                        }
                        for item in index.features
                    ]
                ),
                hide_index=True,
                width="stretch",
                column_config={
                    "Corpus Coverage": st.column_config.ProgressColumn(
                        min_value=0.0, max_value=1.0, format="percent"
                    )
                },
            )
        return
    if section == "Contents":
        query = st.text_input(
            "Filter titles or poets",
            key="corpus_browser_query",
        ).strip().casefold()
        rows = [
            {
                "Poem": item.title,
                "Poet": item.poet_name,
                "Poem ID": item.point_id,
                "Source Path": item.relative_path,
            }
            for item in index.poems
            if not query
            or query in f"{item.title} {item.poet_name}".casefold()
        ]
        render_dataframe(
            pd.DataFrame(rows, columns=("Poem", "Poet", "Poem ID", "Source Path")),
            hide_index=True,
            width="stretch",
            height=560,
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
    feature_by_id = {item.feature_id: item for item in index.features}
    render_dataframe(
        pd.DataFrame(
            [
                {
                    "Dimension": definition.label,
                    "Group": definition.group_id.replace("_", " ").title(),
                    "Poem Value": point.value_map.get(feature_id),
                    "Reference Mean": feature_by_id[feature_id].raw_mean,
                    "Reference SD": feature_by_id[feature_id].raw_population_sd,
                }
                for feature_id, definition in FEATURE_BY_ID.items()
                if feature_id in feature_by_id
            ]
        ),
        hide_index=True,
        width="stretch",
        height=560,
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
    ("User Guide", "docs/user-guide.md", "Workspace-by-workspace operating guide."),
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
        "Saved analyses, drafts, revisions, notes, and privacy.",
    ),
    ("Project README", "README.md", "Project overview, installation, and entry points."),
)
_METHODOLOGY_SOURCES = (
    ("All Metrics and Limitations", "docs/methodology.md"),
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
