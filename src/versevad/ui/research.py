"""Research-library, draft, note, and historical-result interface helpers."""

from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import zipfile
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st

from versevad import __version__
from versevad.application import (
    WorkspaceAnalysis,
    detailed_export_zip,
    scholar_summary_csv,
)
from versevad.comparison import PoemComparisonSet
from versevad.explorer import LexiconExplorerResult
from versevad.exports.comparison import (
    export_poem_comparison_set_csv,
    export_poem_comparison_set_docx,
)
from versevad.exports.lexicon_explorer import export_lexicon_explorer_docx
from versevad.research_library import (
    LibraryItem,
    LibraryRevision,
    ResearchLibraryError,
    ResearchLibraryRepository,
    ResearchNote,
    serialize_value,
    session_research_library_path,
)
from versevad.ui.design import (
    render_dataframe,
    render_empty_state,
    render_workspace_header,
)
from versevad.ui.profile_management import (
    custom_profile_settings,
    selected_custom_profile_name,
)
from versevad.ui.profiles import (
    COMPARISON_PROFILE_SETTING_KEYS,
    PROFILE_WIDGET_KEYS,
)


_RESEARCHABLE_WORKSPACES = {
    "Single Poem",
    "Other Text",
    "Compare Poems",
    "Saved Projects",
    "Personal Corpus",
    "Lexicon Explorer",
    "VerseMap",
}
_SINGLE_TEXT_STATE_KEYS = frozenset(
    {
        "project_name",
        "poem_title",
        "poem_text",
        "text_author",
        "text_year",
        "text_source_notes",
        "pronunciation_overrides",
        "module_preset",
        "one_poem_stopword_mode",
        "one_poem_stopword_mode_label",
        "one_poem_protected_stopwords",
        "one_poem_custom_stopword_additions",
        "one_poem_custom_stopword_removals",
        *PROFILE_WIDGET_KEYS,
    }
)
_COMPARE_STATE_KEYS = frozenset(
    {
        "compare_poem_ids",
        "compare_next_poem_number",
        "compare_analysis_profile",
        "compare_lexicons",
        "compare_modules",
        "compare_stopword_mode",
        "compare_stopword_mode_label",
        "compare_protected_stopwords",
        "compare_custom_stopword_additions",
        "compare_custom_stopword_removals",
        "compare_versemap_reference_corpus",
        "compare_config_pronunciation_overrides",
        "compare_config_meter_scholar_revisions",
        *(f"compare_config_{key}" for key in COMPARISON_PROFILE_SETTING_KEYS),
    }
)
_EXPLORER_STATE_KEYS = frozenset({"explorer_value_display"})
_VERSEMAP_STATE_KEYS = frozenset(
    {
        "standalone_versemap_title",
        "standalone_versemap_author",
        "standalone_versemap_text",
        "standalone_versemap_corpus",
        "standalone_versemap_neighbors",
        "standalone_versemap_shared_weight",
    }
)
_COMPARE_TEXT_KEY = re.compile(
    r"^compare_[A-Za-z0-9-]+_(?:title|text)$"
)
_RESTORABLE_UI_STATE_BY_WORKSPACE = {
    "Single Poem": _SINGLE_TEXT_STATE_KEYS,
    "Other Text": _SINGLE_TEXT_STATE_KEYS,
    "Compare Poems": _COMPARE_STATE_KEYS,
    "Lexicon Explorer": _EXPLORER_STATE_KEYS,
    "VerseMap": _VERSEMAP_STATE_KEYS,
}


@dataclass(frozen=True)
class ActiveResearchContext:
    parent_type: str
    parent_id: str
    workspace_id: str
    title: str
    author: str
    payload: object | None
    text_sha256: str
    profile_name: str
    summary: dict[str, object]
    settings: object
    data_versions: object
    warnings: tuple[str, ...]
    analyzed: bool


@st.cache_resource(show_spinner=False)
def _repository_for_path(path: str) -> ResearchLibraryRepository:
    return ResearchLibraryRepository(Path(path))


def research_repository() -> ResearchLibraryRepository:
    path = session_research_library_path(st.session_state)
    return _repository_for_path(str(path))


def hosted_library_is_ephemeral() -> bool:
    return os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") == "1"


def _session_context_id(workspace: str) -> str:
    key = f"_research_context_id__{workspace}"
    value = st.session_state.get(key)
    if not isinstance(value, str) or not value:
        value = f"context-{uuid4().hex}"
        st.session_state[key] = value
    return value


def _library_item_id(workspace: str) -> str | None:
    value = st.session_state.get(f"_research_library_item__{workspace}")
    return value if isinstance(value, str) and value else None


def _set_library_item_id(workspace: str, item_id: str) -> None:
    st.session_state[f"_research_library_item__{workspace}"] = item_id
    st.session_state[f"_research_context_id__{workspace}"] = item_id


def _discard_stale_library_reference(
    workspace: str,
    item_id: str,
    *,
    state: Any | None = None,
) -> None:
    """Detach a browser reference whose ephemeral or deleted row is gone."""

    target = st.session_state if state is None else state
    item_key = f"_research_library_item__{workspace}"
    context_key = f"_research_context_id__{workspace}"
    if target.get(item_key) == item_id:
        target.pop(item_key, None)
    if target.get(context_key) == item_id:
        target.pop(context_key, None)
    target.pop(f"_research_saved_revision__{workspace}", None)
    historical = target.get("_historical_analysis")
    if (
        isinstance(historical, dict)
        and historical.get("workspace") == workspace
        and historical.get("item_id") == item_id
    ):
        target.pop("_historical_analysis", None)


def _safe_session_value(value: object) -> bool:
    try:
        return len(serialize_value(value)) <= 200_000
    except (ResearchLibraryError, TypeError, ValueError):
        return False


def _is_restorable_ui_state_key(
    key: str,
    workspace: str | None = None,
) -> bool:
    """Return whether ``key`` is registered as durable analytical state.

    Streamlit action, upload, download, and form-submit widgets forbid replayed
    assignments. An allowlist is deliberately safer than naming every current
    and future transient widget: new controls are excluded until explicitly
    registered as durable state.
    """

    if not key or key.startswith("_"):
        return False
    if workspace == "Compare Poems" and _COMPARE_TEXT_KEY.fullmatch(key):
        return True
    if workspace is not None:
        return key in _RESTORABLE_UI_STATE_BY_WORKSPACE.get(
            workspace,
            frozenset(),
        )
    return (
        any(
            key in keys
            for keys in _RESTORABLE_UI_STATE_BY_WORKSPACE.values()
        )
        or _COMPARE_TEXT_KEY.fullmatch(key) is not None
    )


def _is_nonrestorable_ui_state_key(key: str) -> bool:
    """Return whether a key is not registered for safe historical replay."""

    return not _is_restorable_ui_state_key(key)


def _capture_ui_state(workspace: str) -> dict[str, object]:
    """Capture user-visible controls without transient uploads or result bytes."""

    state: dict[str, object] = {}
    for key, value in st.session_state.items():
        if not _is_restorable_ui_state_key(key, workspace):
            continue
        if _safe_session_value(value):
            state[key] = value
    return state


def _request_settings(analysis: WorkspaceAnalysis) -> dict[str, object]:
    return {
        field.name: getattr(analysis.request, field.name)
        for field in fields(analysis.request)
        if field.name
        not in {
            "original_text",
            "project_name",
            "title",
            "text_id",
            "text_version_id",
        }
    }


def _analysis_versions(analysis: WorkspaceAnalysis) -> dict[str, object]:
    versions: dict[str, object] = {
        "versevad": __version__,
        "scenario_id": analysis.request.scenario_id,
        "scenario_version_id": analysis.request.scenario_version_id,
        "lexicons": tuple(analysis.request.lexicon_ids),
    }
    for field in (
        "concreteness",
        "frequency",
        "aoa",
        "sensorimotor",
        "pronunciation",
        "meter",
        "phonology",
        "lexical_style",
        "poetry_id",
        "inherited_form",
        "versemap",
    ):
        result = getattr(analysis, field)
        if result is None:
            continue
        module_result = getattr(result, "module_result", None)
        versions[field] = {
            "result_id": str(
                getattr(module_result, "result_id", "")
                or getattr(result, "analysis_id", "")
            ),
            "module_version": str(
                getattr(module_result, "module_version", "")
                or getattr(result, "module_version", "")
            ),
        }
    return versions


def _analysis_warnings(analysis: WorkspaceAnalysis) -> tuple[str, ...]:
    warnings: list[str] = []
    for result in (
        *analysis.results,
        analysis.vader_sentiment,
        analysis.readability,
        analysis.concreteness,
        analysis.frequency,
        analysis.aoa,
        analysis.sensorimotor,
        analysis.pronunciation,
        analysis.meter,
        analysis.phonology,
        analysis.lexical_style,
        analysis.poetry_id,
        analysis.inherited_form,
        analysis.versemap,
    ):
        if result is None:
            continue
        for warning in getattr(result, "warnings", ()):
            text = str(getattr(warning, "message", warning)).strip()
            if text and text not in warnings:
                warnings.append(text)
        module_result = getattr(result, "module_result", None)
        for warning in getattr(module_result, "warnings", ()):
            text = str(getattr(warning, "message", warning)).strip()
            if text and text not in warnings:
                warnings.append(text)
    return tuple(warnings)


def _draft_payload(workspace: str) -> dict[str, object] | None:
    if workspace in {"Single Poem", "Other Text"}:
        text = str(st.session_state.get("poem_text", ""))
        if not text.strip():
            return None
        return {
            "kind": "text_draft",
            "workspace_id": workspace,
            "ui_state": _capture_ui_state(workspace),
        }
    if workspace == "Compare Poems":
        poem_ids = tuple(st.session_state.get("compare_poem_ids", ()))
        poems = [
            {
                "poem_id": poem_id,
                "title": str(
                    st.session_state.get(f"compare_{poem_id}_title", "")
                ),
                "text": str(
                    st.session_state.get(f"compare_{poem_id}_text", "")
                ),
            }
            for poem_id in poem_ids
        ]
        if not any(poem["text"].strip() for poem in poems):
            return None
        return {
            "kind": "comparison_draft",
            "workspace_id": workspace,
            "poems": poems,
            "ui_state": _capture_ui_state(workspace),
        }
    if workspace == "VerseMap":
        text = str(st.session_state.get("standalone_versemap_text", ""))
        if not text.strip():
            return None
        return {
            "kind": "versemap_draft",
            "workspace_id": workspace,
            "ui_state": _capture_ui_state(workspace),
        }
    return None


def active_research_context(workspace: str) -> ActiveResearchContext | None:
    if workspace not in _RESEARCHABLE_WORKSPACES:
        return None
    existing_item_id = _library_item_id(workspace)
    parent_id = existing_item_id or _session_context_id(workspace)
    if workspace in {"Single Poem", "Other Text"}:
        analysis = st.session_state.get("workspace")
        if isinstance(analysis, WorkspaceAnalysis):
            payload = {
                "kind": "workspace_analysis",
                "workspace_id": workspace,
                "analysis": analysis,
                "ui_state": _capture_ui_state(workspace),
                "metadata": {
                    "author": str(st.session_state.get("text_author", "")),
                    "year": str(st.session_state.get("text_year", "")),
                    "source_notes": str(
                        st.session_state.get("text_source_notes", "")
                    ),
                },
            }
            return ActiveResearchContext(
                parent_type="analysis",
                parent_id=parent_id,
                workspace_id=workspace,
                title=analysis.request.title,
                author=str(st.session_state.get("text_author", "")),
                payload=payload,
                text_sha256=analysis.document.text_sha256,
                profile_name=str(st.session_state.get("module_preset", "Custom")),
                summary={
                    "title": analysis.request.title,
                    "workspace": workspace,
                    "matched_lexicons": len(analysis.results),
                    "enabled_modules": tuple(
                        name
                        for name in (
                            "concreteness",
                            "frequency",
                            "aoa",
                            "sensorimotor",
                            "pronunciation",
                            "meter",
                            "phonology",
                            "lexical_style",
                            "poetry_id",
                            "inherited_form",
                            "versemap",
                        )
                        if getattr(analysis, name) is not None
                    ),
                },
                settings=_request_settings(analysis),
                data_versions=_analysis_versions(analysis),
                warnings=_analysis_warnings(analysis),
                analyzed=True,
            )
        draft = _draft_payload(workspace)
        if draft is None:
            return None
        text = str(st.session_state.get("poem_text", ""))
        return ActiveResearchContext(
            parent_type="draft",
            parent_id=parent_id,
            workspace_id=workspace,
            title=str(st.session_state.get("poem_title", "")).strip()
            or "Untitled draft",
            author=str(st.session_state.get("text_author", "")),
            payload=draft,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            profile_name=str(st.session_state.get("module_preset", "Custom")),
            summary={"workspace": workspace, "draft": True},
            settings=_capture_ui_state(workspace),
            data_versions={"versevad": __version__},
            warnings=(),
            analyzed=False,
        )
    if workspace == "Compare Poems":
        comparison = st.session_state.get("poem_comparison_set")
        if isinstance(comparison, PoemComparisonSet):
            titles = tuple(
                analysis.request.title for analysis in comparison.analyses
            )
            digest = hashlib.sha256(
                "".join(
                    analysis.document.text_sha256
                    for analysis in comparison.analyses
                ).encode("ascii")
            ).hexdigest()
            return ActiveResearchContext(
                parent_type="comparison",
                parent_id=parent_id,
                workspace_id=workspace,
                title=" · ".join(titles[:3])
                + ("…" if len(titles) > 3 else ""),
                author="",
                payload={
                    "kind": "comparison_set",
                    "workspace_id": workspace,
                    "comparison": comparison,
                    "ui_state": _capture_ui_state(workspace),
                },
                text_sha256=digest,
                profile_name=str(
                    st.session_state.get("compare_analysis_profile", "Custom")
                ),
                summary={
                    "workspace": workspace,
                    "poem_count": len(comparison.analyses),
                    "titles": titles,
                },
                settings={
                    "shared_request": _request_settings(comparison.analyses[0])
                },
                data_versions={
                    "versevad": __version__,
                    "analyses": tuple(
                        _analysis_versions(analysis)
                        for analysis in comparison.analyses
                    ),
                },
                warnings=tuple(
                    dict.fromkeys(
                        warning
                        for analysis in comparison.analyses
                        for warning in _analysis_warnings(analysis)
                    )
                ),
                analyzed=True,
            )
        draft = _draft_payload(workspace)
        if draft is None:
            return None
        return ActiveResearchContext(
            parent_type="draft",
            parent_id=parent_id,
            workspace_id=workspace,
            title="Comparison draft",
            author="",
            payload=draft,
            text_sha256=hashlib.sha256(serialize_value(draft)).hexdigest(),
            profile_name=str(
                st.session_state.get("compare_analysis_profile", "Custom")
            ),
            summary={"workspace": workspace, "draft": True},
            settings=_capture_ui_state(workspace),
            data_versions={"versevad": __version__},
            warnings=(),
            analyzed=False,
        )
    if workspace == "Lexicon Explorer":
        result = st.session_state.get("lexicon_explorer_result")
        if not isinstance(result, LexiconExplorerResult):
            return None
        return ActiveResearchContext(
            parent_type="lexicon_word",
            parent_id=parent_id,
            workspace_id=workspace,
            title=result.query,
            author="",
            payload={
                "kind": "lexicon_lookup",
                "workspace_id": workspace,
                "result": result,
                "ui_state": _capture_ui_state(workspace),
            },
            text_sha256="",
            profile_name="Lexicon Explorer",
            summary={
                "workspace": workspace,
                "query": result.query,
                "normalized_query": result.normalized_query,
                "source_count": len(result.entries),
            },
            settings={"mapped_query": st.session_state.get("mapped_query", "")},
            data_versions={"versevad": __version__},
            warnings=tuple(result.notices),
            analyzed=True,
        )
    if workspace == "VerseMap":
        analysis = st.session_state.get("standalone_versemap_analysis")
        if isinstance(analysis, WorkspaceAnalysis):
            return ActiveResearchContext(
                parent_type="versemap_session",
                parent_id=parent_id,
                workspace_id=workspace,
                title=analysis.request.title,
                author=str(
                    st.session_state.get("standalone_versemap_author", "")
                ),
                payload={
                    "kind": "workspace_analysis",
                    "workspace_id": workspace,
                    "analysis": analysis,
                    "ui_state": _capture_ui_state(workspace),
                    "metadata": {
                        "author": str(
                            st.session_state.get(
                                "standalone_versemap_author", ""
                            )
                        )
                    },
                },
                text_sha256=analysis.document.text_sha256,
                profile_name="VerseMap Standard Profile 1.0",
                summary={
                    "workspace": workspace,
                    "title": analysis.request.title,
                    "reference_release": (
                        analysis.versemap.reference_release_id
                        if analysis.versemap is not None
                        else ""
                    ),
                    "model_id": (
                        analysis.versemap.model_id
                        if analysis.versemap is not None
                        else ""
                    ),
                },
                settings=_request_settings(analysis),
                data_versions=_analysis_versions(analysis),
                warnings=_analysis_warnings(analysis),
                analyzed=True,
            )
        draft = _draft_payload(workspace)
        if draft is None:
            return None
        text = str(st.session_state.get("standalone_versemap_text", ""))
        return ActiveResearchContext(
            parent_type="draft",
            parent_id=parent_id,
            workspace_id=workspace,
            title=str(
                st.session_state.get("standalone_versemap_title", "")
            ).strip()
            or "Untitled VerseMap draft",
            author=str(
                st.session_state.get("standalone_versemap_author", "")
            ),
            payload=draft,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            profile_name="VerseMap Standard Profile 1.0",
            summary={"workspace": workspace, "draft": True},
            settings=_capture_ui_state(workspace),
            data_versions={"versevad": __version__},
            warnings=(),
            analyzed=False,
        )
    # Collection contexts can receive notes even when their own persistence
    # remains in the dedicated project/personal-corpus repositories.
    return ActiveResearchContext(
        parent_type=(
            "project" if workspace == "Saved Projects" else "personal_corpus"
        ),
        parent_id=parent_id,
        workspace_id=workspace,
        title=workspace,
        author="",
        payload=None,
        text_sha256="",
        profile_name="",
        summary={"workspace": workspace},
        settings={},
        data_versions={"versevad": __version__},
        warnings=(),
        analyzed=False,
    )


def _results_only_bundle(context: ActiveResearchContext) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        payload = context.payload
        kind = payload.get("kind") if isinstance(payload, dict) else ""
        if kind == "workspace_analysis":
            analysis = payload["analysis"]
            audit_bundle = detailed_export_zip(analysis)
            with zipfile.ZipFile(io.BytesIO(audit_bundle)) as complete:
                narrative = complete.read("VerseVAD_analysis_report.docx")
            archive.writestr(
                "VerseVAD_saved_results_summary.csv",
                scholar_summary_csv(analysis),
            )
            archive.writestr("VerseVAD_saved_results_report.docx", narrative)
        elif kind == "comparison_set":
            comparison = payload["comparison"]
            archive.writestr(
                "VerseVAD_comparison_results.csv",
                export_poem_comparison_set_csv(comparison),
            )
            archive.writestr(
                "VerseVAD_comparison_report.docx",
                export_poem_comparison_set_docx(comparison),
            )
        elif kind == "lexicon_lookup":
            archive.writestr(
                "VerseVAD_lexicon_lookup_report.docx",
                export_lexicon_explorer_docx(payload["result"]),
            )
        else:
            raise ResearchLibraryError(
                "This context has no results-only archival report."
            )
    return output.getvalue()


def save_active_context(
    workspace: str,
    *,
    title: str,
    storage_mode: str,
    save_as_new: bool = False,
    project_id: str = "",
) -> tuple[LibraryItem, LibraryRevision]:
    context = active_research_context(workspace)
    if context is None or context.payload is None:
        raise ResearchLibraryError("There is no active analysis to save.")
    if not context.analyzed:
        raise ResearchLibraryError(
            "Complete the analysis before saving it to the library."
        )
    saved_title = " ".join(title.split())
    if not saved_title:
        raise ResearchLibraryError("Enter a title for the saved analysis.")
    if len(saved_title) > 200:
        raise ResearchLibraryError(
            "Saved analysis titles must be 200 characters or fewer."
        )
    existing_item_id = _library_item_id(workspace)
    target_item_id = None if save_as_new else existing_item_id
    original_context_id = context.parent_id
    artifact = (
        _results_only_bundle(context) if storage_mode == "results_only" else None
    )
    item, revision, _ = research_repository().save_revision(
        parent_type=(
            context.parent_type if context.parent_type != "draft" else "analysis"
        ),
        workspace_id=workspace,
        title=saved_title,
        author=context.author,
        status="saved",
        storage_mode=storage_mode,
        software_version=__version__,
        payload=context.payload if storage_mode != "results_only" else None,
        text_sha256=context.text_sha256,
        profile_name=context.profile_name,
        settings=context.settings,
        data_versions=context.data_versions,
        warnings=context.warnings,
        summary=context.summary,
        artifact_bundle=artifact,
        item_id=target_item_id,
        project_id=project_id,
    )
    if target_item_id is None and original_context_id != item.item_id:
        research_repository().reparent_notes(
            old_parent_id=original_context_id,
            new_parent_type=item.parent_type,
            new_parent_id=item.item_id,
            copy=bool(existing_item_id),
        )
    _set_library_item_id(workspace, item.item_id)
    st.session_state[f"_research_saved_revision__{workspace}"] = (
        revision.revision_id
    )
    return item, revision


def release_active_context(workspace: str) -> None:
    """Detach the current workspace without creating or deleting a library item."""

    for key in (
        f"_research_library_item__{workspace}",
        f"_research_context_id__{workspace}",
        f"_research_autosave_signature__{workspace}",
        f"_research_saved_revision__{workspace}",
    ):
        st.session_state.pop(key, None)


def _apply_ui_state(ui_state: object, *, workspace: str) -> None:
    if not isinstance(ui_state, dict):
        return
    # Older saves could contain momentary Streamlit widget values. Remove only
    # those legacy payload keys from current state, then replay the registered
    # durable subset. This prevents every future action/upload widget from
    # requiring another name-based exception.
    for legacy_key in ui_state:
        if (
            isinstance(legacy_key, str)
            and not _is_restorable_ui_state_key(legacy_key, workspace)
        ):
            st.session_state.pop(legacy_key, None)
    for key, value in ui_state.items():
        if (
            isinstance(key, str)
            and _is_restorable_ui_state_key(key, workspace)
        ):
            st.session_state[key] = value


def restore_library_revision(
    item: LibraryItem,
    revision: LibraryRevision,
) -> str:
    payload = research_repository().load_payload(revision.revision_id)
    if not isinstance(payload, dict):
        raise ResearchLibraryError("This saved analysis has an unknown payload.")
    kind = payload.get("kind")
    workspace = str(payload.get("workspace_id") or item.workspace_id)
    restored_ui_state = payload.get("ui_state")
    _apply_ui_state(restored_ui_state, workspace=workspace)
    if workspace == "Compare Poems" and isinstance(restored_ui_state, dict):
        restored_profile = str(
            restored_ui_state.get("compare_analysis_profile", "")
        )
        custom_name = selected_custom_profile_name(restored_profile)
        if (
            custom_name is not None
            and custom_name not in custom_profile_settings()
        ):
            st.session_state["compare_analysis_profile"] = "Custom"
            st.session_state[
                "_analysis_profile_notice__compare_poems"
            ] = (
                f'The saved custom profile "{custom_name}" is not available '
                "in this installation or hosted session. Its exact saved "
                "comparison settings were restored as Custom."
            )
    if kind == "workspace_analysis":
        analysis = payload.get("analysis")
        if not isinstance(analysis, WorkspaceAnalysis):
            raise ResearchLibraryError("Saved single-text result is malformed.")
        if workspace == "VerseMap":
            st.session_state["standalone_versemap_analysis"] = analysis
            st.session_state["standalone_versemap_title"] = analysis.request.title
            st.session_state["standalone_versemap_text"] = (
                analysis.request.original_text
            )
        else:
            st.session_state["workspace"] = analysis
            st.session_state["poem_title"] = analysis.request.title
            st.session_state["poem_text"] = analysis.request.original_text
            st.session_state["project_name"] = analysis.request.project_name
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            if workspace == "VerseMap":
                st.session_state["standalone_versemap_author"] = str(
                    metadata.get("author", "")
                )
            else:
                st.session_state["text_author"] = str(metadata.get("author", ""))
                st.session_state["text_year"] = str(metadata.get("year", ""))
                st.session_state["text_source_notes"] = str(
                    metadata.get("source_notes", "")
                )
    elif kind == "comparison_set":
        comparison = payload.get("comparison")
        if not isinstance(comparison, PoemComparisonSet):
            raise ResearchLibraryError("Saved comparison result is malformed.")
        st.session_state["poem_comparison_set"] = comparison
    elif kind == "lexicon_lookup":
        result = payload.get("result")
        if not isinstance(result, LexiconExplorerResult):
            raise ResearchLibraryError("Saved lexicon lookup is malformed.")
        st.session_state["lexicon_explorer_result"] = result
    elif kind == "text_draft":
        pass
    elif kind == "comparison_draft":
        poems = payload.get("poems")
        if isinstance(poems, list):
            poem_ids = []
            for position, poem in enumerate(poems, start=1):
                if not isinstance(poem, dict):
                    continue
                poem_id = str(poem.get("poem_id") or f"restored_{position}")
                poem_ids.append(poem_id)
                st.session_state[f"compare_{poem_id}_title"] = str(
                    poem.get("title", "")
                )
                st.session_state[f"compare_{poem_id}_text"] = str(
                    poem.get("text", "")
                )
            st.session_state["compare_poem_ids"] = poem_ids
    elif kind == "versemap_draft":
        pass
    else:
        raise ResearchLibraryError("This saved analysis has an unknown kind.")
    _set_library_item_id(workspace, item.item_id)
    if item.status == "saved":
        st.session_state["_historical_analysis"] = {
            "workspace": workspace,
            "item_id": item.item_id,
            "revision_id": revision.revision_id,
            "saved_version": revision.software_version,
        }
    else:
        st.session_state.pop("_historical_analysis", None)
    st.session_state["_pending_workspace_switch"] = workspace
    return workspace


def _current_notes(
    context: ActiveResearchContext,
) -> tuple[ResearchNote, ...]:
    repository = research_repository()
    try:
        return repository.list_notes(parent_id=context.parent_id)
    except (OSError, sqlite3.Error) as error:
        raise ResearchLibraryError(
            "VerseVAD could not read the private analysis library at "
            f"{repository.database_path}."
        ) from error


def render_research_notes_sidebar(workspace: str) -> None:
    context = active_research_context(workspace)
    if context is None:
        st.caption("Load text or a result before attaching research notes.")
        return
    try:
        notes = _current_notes(context)
    except ResearchLibraryError as error:
        st.warning(str(error))
        return
    st.caption(f"Notes for this {context.parent_type.replace('_', ' ')}: {len(notes)}")
    with st.form(f"sidebar_note_form__{workspace}", clear_on_submit=True):
        title = st.text_input("Note title", placeholder="Interpretive question")
        anchor_type = st.selectbox(
            "Attach to",
            options=[
                "Analysis",
                "Report section",
                "Metric",
                "Chart",
                "Line of text",
                "Word or phrase",
                "Rhyme or form candidate",
            ],
        )
        anchor_label = st.text_input(
            "Anchored result or passage",
            placeholder="Concreteness → distribution → low-concreteness words",
        )
        body = st.text_area("Research note", height=120)
        tags = st.text_input("Tags", placeholder="imagery, revision, teaching")
        include = st.checkbox("Mark as available for note-inclusive exports")
        submitted = st.form_submit_button("Add note")
    if submitted:
        try:
            research_repository().save_note(
                parent_type=context.parent_type,
                parent_id=context.parent_id,
                analysis_id=(
                    context.parent_id
                    if context.parent_type
                    in {"analysis", "comparison", "draft"}
                    else ""
                ),
                title=title,
                body=body,
                tags=tuple(part.strip() for part in tags.split(",")),
                module=(
                    anchor_label.split("→", 1)[0].strip()
                    if anchor_label
                    else ""
                ),
                metric=anchor_label,
                anchor_type=anchor_type.lower().replace(" ", "_"),
                anchor_label=anchor_label,
                include_in_export=include,
            )
            st.success("Research note saved.")
            st.rerun()
        except ResearchLibraryError as error:
            st.error(str(error))
    for note in notes[:3]:
        st.markdown(f"**{note.title}**")
        if note.anchor_label:
            st.caption(f"Attached to: {note.anchor_label}")
        st.caption(note.body[:180] + ("…" if len(note.body) > 180 else ""))
    if len(notes) > 3:
        st.caption(f"{len(notes) - 3} more in the Analysis Library notebook.")
    if st.button(
        "Open notebook",
        key=f"open_research_notebook__{workspace}",
        width="stretch",
    ):
        st.session_state["_analysis_library_section"] = "Notebook"
        st.session_state["_analysis_library_selected_item"] = context.parent_id
        from versevad.ui.navigation import switch_to_workspace

        switch_to_workspace("Analysis Library")


def render_analysis_management_sidebar(workspace: str) -> None:
    context = active_research_context(workspace)
    if context is None or context.payload is None:
        st.caption("Complete an analysis before saving it.")
    else:
        current_id = _library_item_id(workspace)
        current_status = ""
        if current_id:
            current_item = research_repository().find_item(current_id)
            if current_item is None:
                _discard_stale_library_reference(workspace, current_id)
            else:
                current_status = current_item.status
        if current_status == "saved":
            st.success("This analysis is in the library.")
        if context.analyzed:
            saved_title = st.text_input(
                "Saved analysis title",
                key=f"research_save_title__{workspace}",
                placeholder=context.title or "Enter a descriptive title",
                help=(
                    "Required. VerseVAD saves only when you use one of the "
                    "explicit save buttons below."
                ),
            )
            storage_label = st.selectbox(
                "Save privacy",
                options=[
                    "Full analysis and source text",
                    "Results only — do not retain source text",
                ],
                key=f"research_storage_mode__{workspace}",
                help=(
                    "Results-only storage retains a summary CSV and narrative "
                    "Word report but cannot reopen the original text."
                ),
            )
            storage_mode = (
                "full"
                if storage_label == "Full analysis and source text"
                else "results_only"
            )
            project_link = st.text_input(
                "Optional project identifier",
                key=f"research_project_link__{workspace}",
                help="Records a project association without moving or duplicating the project.",
            )
            save_columns = st.columns(2)
            if save_columns[0].button(
                "Save analysis",
                key=f"save_analysis__{workspace}",
                type="primary",
                width="stretch",
                disabled=not saved_title.strip(),
            ):
                try:
                    _, revision = save_active_context(
                        workspace,
                        title=saved_title,
                        storage_mode=storage_mode,
                        project_id=project_link,
                    )
                    st.success(f"Saved revision {revision.revision_number}.")
                    st.rerun()
                except ResearchLibraryError as error:
                    st.error(str(error))
            if save_columns[1].button(
                "Save as new",
                key=f"save_as_new_analysis__{workspace}",
                width="stretch",
                disabled=not saved_title.strip(),
            ):
                try:
                    save_active_context(
                        workspace,
                        title=saved_title,
                        storage_mode=storage_mode,
                        save_as_new=True,
                        project_id=project_link,
                    )
                    st.success("Saved as a separate analysis.")
                    st.rerun()
                except ResearchLibraryError as error:
                    st.error(str(error))
        else:
            st.caption(
                "Unsaved work remains only in the current session. Complete the "
                "analysis, enter a title, and save it explicitly to retain it."
            )
    if st.button(
        "Open Analysis Library",
        key=f"open_analysis_library__{workspace}",
        width="stretch",
    ):
        from versevad.ui.navigation import switch_to_workspace

        switch_to_workspace("Analysis Library")


def render_historical_analysis_notice(workspace: str) -> None:
    historical = st.session_state.get("_historical_analysis")
    if not isinstance(historical, dict) or historical.get("workspace") != workspace:
        return
    saved_version = str(historical.get("saved_version", "unknown"))
    notice = st.empty()
    with notice.container():
        if saved_version == __version__:
            st.info(
                "Viewing an immutable saved result from the current VerseVAD "
                f"version ({saved_version}). It has not been recalculated "
                "since it was saved."
            )
        else:
            st.info(
                "Viewing an immutable saved result from VerseVAD "
                f"{saved_version}. It has not been recalculated under VerseVAD "
                f"{__version__}."
            )
        columns = st.columns(2)
        continue_historical = columns[0].button(
            "Continue viewing historical result",
            key=f"continue_historical__{workspace}",
            width="stretch",
        )
        prepare_reanalysis = columns[1].button(
            "Prepare reanalysis with current version",
            key=f"prepare_reanalysis__{workspace}",
            width="stretch",
        )

    # A button interaction has already started a Streamlit rerun. Continue the
    # current render after changing only the required state; an additional
    # st.rerun() could discard the just-restored result before it is displayed.
    if continue_historical:
        _continue_historical_result(workspace)
        notice.empty()
    elif prepare_reanalysis:
        _prepare_historical_reanalysis(workspace)
        notice.empty()
        st.success(
            "Historical inputs and settings are restored. Use the workspace's "
            "Analyze or Search action when ready. The saved historical revision "
            "remains unchanged in the Analysis Library."
        )


def _continue_historical_result(
    workspace: str,
    *,
    state: Any | None = None,
) -> bool:
    """Dismiss the notice without changing the restored immutable result."""

    target = st.session_state if state is None else state
    historical = target.get("_historical_analysis")
    if not isinstance(historical, dict) or historical.get("workspace") != workspace:
        return False
    target.pop("_historical_analysis", None)
    return True


def _prepare_historical_reanalysis(
    workspace: str,
    *,
    state: Any | None = None,
) -> bool:
    """Clear only computed output while retaining restored inputs/settings."""

    target = st.session_state if state is None else state
    historical = target.get("_historical_analysis")
    if not isinstance(historical, dict) or historical.get("workspace") != workspace:
        return False
    if workspace in {"Single Poem", "Other Text"}:
        target.pop("workspace", None)
    elif workspace == "Compare Poems":
        target.pop("poem_comparison_set", None)
    elif workspace == "Lexicon Explorer":
        target.pop("lexicon_explorer_result", None)
    elif workspace == "VerseMap":
        target.pop("standalone_versemap_analysis", None)
        target.pop("standalone_versemap_signature", None)
    target.pop("_historical_analysis", None)
    return True


def _item_label(item: LibraryItem) -> str:
    return (
        f"{item.title} · {item.workspace_id} · Saved · "
        f"{item.updated_at[:10]}"
    )


def _render_item_notebook(item: LibraryItem) -> None:
    notes = research_repository().list_notes(parent_id=item.item_id)
    st.subheader("Research Notes")
    if not notes:
        st.caption("No notes are attached to this item.")
        return
    for note in notes:
        with st.expander(note.title, expanded=False):
            if note.anchor_label:
                st.caption(f"Attached to: {note.anchor_label}")
            st.write(note.body)
            if note.tags:
                st.caption("Tags: " + ", ".join(note.tags))
            st.caption(
                f"Created {note.created_at} · Updated {note.updated_at} · "
                + (
                    "eligible for note-inclusive exports"
                    if note.include_in_export
                    else "private by default in exports"
                )
            )
            with st.form(f"edit_note__{note.note_id}"):
                edit_title = st.text_input("Title", value=note.title)
                edit_body = st.text_area("Body", value=note.body, height=140)
                edit_tags = st.text_input("Tags", value=", ".join(note.tags))
                edit_include = st.checkbox(
                    "Mark as available for note-inclusive exports",
                    value=note.include_in_export,
                )
                if st.form_submit_button("Save note changes"):
                    research_repository().save_note(
                        note_id=note.note_id,
                        parent_type=note.parent_type,
                        parent_id=note.parent_id,
                        analysis_id=note.analysis_id,
                        project_id=note.project_id,
                        module=note.module,
                        metric=note.metric,
                        anchor_type=note.anchor_type,
                        anchor_label=note.anchor_label,
                        title=edit_title,
                        body=edit_body,
                        tags=tuple(
                            part.strip() for part in edit_tags.split(",")
                        ),
                        include_in_export=edit_include,
                    )
                    st.rerun()
            if st.button(
                "Delete note",
                key=f"delete_note__{note.note_id}",
            ):
                research_repository().delete_note(note.note_id)
                st.rerun()


def render_analysis_library_workspace() -> None:
    render_workspace_header(
        "Analysis Library",
        "Retrieve explicitly saved results and manage contextual or "
        "result-anchored research notes.",
        kicker="Persistent research retrieval",
        status=(
            "Hosted session only"
            if hosted_library_is_ephemeral()
            else "Stored locally"
        ),
    )
    if hosted_library_is_ephemeral():
        st.warning(
            "In the hosted app, this library lasts only for the current isolated "
            "browser session. Download important work before the session ends."
        )
    else:
        st.success(
            "Saved analyses and notes remain on this computer and are "
            "excluded from the public source repository."
        )
    try:
        repository = research_repository()
    except ResearchLibraryError as error:
        st.error(str(error))
        return
    section = st.selectbox(
        "Library Section",
        options=["Saved Analyses", "Notebook"],
        key="_analysis_library_section",
    )
    items = repository.list_items(status="saved")
    if section == "Notebook":
        saved_ids = {item.item_id for item in items}
        all_notes = tuple(
            note
            for note in research_repository().list_notes()
            if note.parent_id in saved_ids
        )
        if not all_notes:
            render_empty_state(
                "No research notes yet",
                "Notes created from an analysis remain attached to that object.",
                "Open Research Notes in an analytical workspace to add one.",
            )
            return
        frame = pd.DataFrame(
            [
                {
                    "Title": note.title,
                    "Context": note.parent_type.replace("_", " ").title(),
                    "Anchor": note.anchor_label or "Analysis level",
                    "Tags": ", ".join(note.tags),
                    "Updated": note.updated_at,
                    "Export eligible": note.include_in_export,
                }
                for note in all_notes
            ]
        )
        render_dataframe(frame, hide_index=True, width="stretch")
        item_by_id = {item.item_id: item for item in items}
        selectable = [
            item_by_id[note.parent_id]
            for note in all_notes
            if note.parent_id in item_by_id
        ]
        if selectable:
            labels = {_item_label(item): item for item in selectable}
            selected = labels[
                st.selectbox("Open an attached notebook", options=list(labels))
            ]
            _render_item_notebook(selected)
        return
    if not items:
        render_empty_state(
            "No saved analyses yet",
            "Saved analyses preserve historical results without silently "
            "recalculating them.",
            "Use Analysis Management in a workspace to save a result.",
        )
        return
    labels = {_item_label(item): item for item in items}
    selected_item = labels[
        st.selectbox("Saved analysis", options=list(labels))
    ]
    revisions = research_repository().list_revisions(selected_item.item_id)
    revision_labels = {
        (
            f"Revision {revision.revision_number} · "
            f"{revision.created_at[:19]} · "
            f"{revision.storage_mode.replace('_', ' ')}"
        ): revision
        for revision in revisions
    }
    selected_revision = revision_labels[
        st.selectbox("Historical revision", options=list(revision_labels))
    ]
    summary_columns = st.columns(4)
    summary_columns[0].metric("Workspace", selected_item.workspace_id)
    summary_columns[1].metric("Revision", selected_revision.revision_number)
    summary_columns[2].metric("Saved with", selected_revision.software_version)
    summary_columns[3].metric(
        "Storage", selected_revision.storage_mode.replace("_", " ").title()
    )
    st.caption(
        f"Created {selected_item.created_at} · Updated {selected_item.updated_at}"
    )
    if selected_revision.warnings:
        with st.expander("Saved warnings", expanded=False):
            for warning in selected_revision.warnings:
                st.write(f"- {warning}")
    open_columns = st.columns(2)
    if selected_revision.storage_mode != "results_only":
        if open_columns[0].button(
            "Open historical result",
            type="primary",
            width="stretch",
        ):
            try:
                restore_library_revision(selected_item, selected_revision)
                from versevad.ui.navigation import switch_to_workspace

                switch_to_workspace(selected_item.workspace_id)
            except ResearchLibraryError as error:
                st.error(str(error))
    elif selected_revision.artifact_bundle:
        open_columns[0].download_button(
            "Download retained reports",
            data=selected_revision.artifact_bundle,
            file_name="VerseVAD_saved_results.zip",
            mime="application/zip",
            width="stretch",
        )
        st.info(
            "This privacy-preserving revision does not retain source text and "
            "cannot be reopened as a live analysis."
        )
    with open_columns[1].popover("Delete from library", width="stretch"):
        with st.form(f"delete_library_form__{selected_item.item_id}"):
            confirmation = st.checkbox(
                f"Permanently delete this saved item: {selected_item.title}",
            )
            delete_submitted = st.form_submit_button(
                "Delete permanently",
                type="primary",
            )
        if delete_submitted:
            if not confirmation:
                st.warning(
                    "Select the confirmation checkbox before permanently "
                    "deleting this saved analysis."
                )
            else:
                try:
                    research_repository().delete_item(selected_item.item_id)
                except ResearchLibraryError as error:
                    st.error(str(error))
                else:
                    st.rerun()
    _render_item_notebook(selected_item)


def notes_for_active_context(workspace: str) -> tuple[ResearchNote, ...]:
    context = active_research_context(workspace)
    return () if context is None else _current_notes(context)


def render_note_export_options(
    workspace: str,
    *,
    key_prefix: str,
) -> tuple[tuple[ResearchNote, ...], bool]:
    """Render an explicit, default-off note selection for compact exports."""

    try:
        available_notes = notes_for_active_context(workspace)
    except ResearchLibraryError as error:
        st.caption(
            "Research-note export options are unavailable because the private "
            f"analysis library could not be opened. {error}"
        )
        return (), False
    mode = st.selectbox(
        "Include research notes",
        options=[
            "Exclude notes",
            "All notes for this analysis",
            "Analysis-level notes only",
            "Selected notes",
        ],
        key=f"{key_prefix}__mode",
        help=(
            "Research notes are excluded by default so private interpretive "
            "comments are not shared accidentally."
        ),
    )
    selected: tuple[ResearchNote, ...] = ()
    if mode == "All notes for this analysis":
        selected = available_notes
    elif mode == "Analysis-level notes only":
        selected = tuple(
            note for note in available_notes if note.anchor_type == "analysis"
        )
    elif mode == "Selected notes":
        labels = {
            (
                f"{note.title} · {note.anchor_label or 'Analysis level'} · "
                f"{note.note_id[-8:]}"
            ): note
            for note in available_notes
        }
        choices = st.multiselect(
            "Notes to include",
            options=list(labels),
            key=f"{key_prefix}__selected",
        )
        selected = tuple(labels[choice] for choice in choices)
    include_metadata = st.checkbox(
        "Include note dates, tags, IDs, and anchored references",
        value=False,
        disabled=not selected,
        key=f"{key_prefix}__metadata",
    )
    if not available_notes:
        st.caption("No research notes are attached to this result.")
    return selected, include_metadata


__all__ = [
    "active_research_context",
    "hosted_library_is_ephemeral",
    "notes_for_active_context",
    "render_note_export_options",
    "render_analysis_library_workspace",
    "render_analysis_management_sidebar",
    "render_historical_analysis_notice",
    "render_research_notes_sidebar",
    "release_active_context",
    "research_repository",
    "restore_library_revision",
    "save_active_context",
]
