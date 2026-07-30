from __future__ import annotations

from dataclasses import dataclass

import pytest

from versevad import __version__
from versevad.application import AnalysisRequest, WorkspaceAnalysis, run_workspace_analysis
from versevad.research_library import (
    LIBRARY_SCHEMA_VERSION,
    ResearchLibraryError,
    ResearchLibraryRepository,
    deserialize_value,
    serialize_value,
)


def _workspace(preprocessor) -> WorkspaceAnalysis:
    return run_workspace_analysis(
        AnalysisRequest(
            project_name="",
            title="A Small Test",
            original_text="Cold stars turn.\nThe quiet river answers.",
            lexicon_ids=(),
            include_lexical_style=True,
            analysis_cache_enabled=False,
            performance_diagnostics=False,
        ),
        preprocessor=preprocessor,
    )


def test_workspace_round_trips_through_restricted_json(preprocessor) -> None:
    workspace = _workspace(preprocessor)

    restored = deserialize_value(serialize_value(workspace))

    assert isinstance(restored, WorkspaceAnalysis)
    assert restored == workspace
    assert restored.request.original_text == workspace.request.original_text
    assert serialize_value(restored) == serialize_value(workspace)


def test_serializer_rejects_non_versevad_dataclasses() -> None:
    @dataclass(frozen=True)
    class Untrusted:
        value: str

    with pytest.raises(ResearchLibraryError, match="outside VerseVAD"):
        serialize_value(Untrusted("no"))


def test_library_keeps_immutable_revisions_and_recovers_drafts(
    tmp_path,
    preprocessor,
) -> None:
    repository = ResearchLibraryRepository(tmp_path / "analysis_library.sqlite3")
    workspace = _workspace(preprocessor)

    item, first, created = repository.save_revision(
        parent_type="analysis",
        workspace_id="Single Poem",
        title=workspace.request.title,
        software_version=__version__,
        payload=workspace,
        storage_mode="full",
        text_sha256=workspace.document.text_sha256,
        profile_name="Computational Close Reading",
        settings={"weighting": "token", "stopwords": "excluded"},
        data_versions={"schema": LIBRARY_SCHEMA_VERSION},
        warnings=(),
        summary={"title": workspace.request.title},
    )
    _, second, second_created = repository.save_revision(
        parent_type="analysis",
        workspace_id="Single Poem",
        title=workspace.request.title,
        software_version=__version__,
        payload=workspace,
        storage_mode="full",
        text_sha256=workspace.document.text_sha256,
        item_id=item.item_id,
    )

    assert created is True
    assert second_created is True
    assert first.revision_number == 1
    assert second.revision_number == 2
    assert repository.load_payload(first.revision_id) == workspace
    assert repository.load_payload(second.revision_id) == workspace

    draft, draft_revision, draft_created = repository.save_revision(
        parent_type="draft",
        workspace_id="Single Poem",
        title="Recover me",
        software_version=__version__,
        payload={"text": "unfinished", "title": "Recover me"},
        storage_mode="draft",
        status="draft",
        deduplicate=True,
    )
    _, repeated_revision, repeated_created = repository.save_revision(
        parent_type="draft",
        workspace_id="Single Poem",
        title="Recover me",
        software_version=__version__,
        payload={"text": "unfinished", "title": "Recover me"},
        storage_mode="draft",
        status="draft",
        item_id=draft.item_id,
        deduplicate=True,
    )

    assert draft_created is True
    assert repeated_created is False
    assert repeated_revision.revision_id == draft_revision.revision_id
    assert repository.list_items(status="draft") == (draft,)


def test_context_notes_update_and_follow_promoted_draft(tmp_path) -> None:
    repository = ResearchLibraryRepository(tmp_path / "analysis_library.sqlite3")
    draft, _, _ = repository.save_revision(
        parent_type="draft",
        workspace_id="Single Poem",
        title="Draft",
        software_version=__version__,
        payload={"text": "A line"},
        storage_mode="draft",
        status="draft",
    )
    note = repository.save_note(
        parent_type="draft",
        parent_id=draft.item_id,
        title="Valence question",
        body="Does the low mean conceal a high-valence refrain?",
        tags=("close reading", "valence", "valence"),
        module="Affective Evidence",
        metric="Valence",
        anchor_type="metric",
        anchor_label="Valence → token-weighted mean",
        include_in_export=True,
    )
    edited = repository.save_note(
        note_id=note.note_id,
        parent_type="draft",
        parent_id=draft.item_id,
        title=note.title,
        body=note.body + " Revisit the repeated word.",
        tags=note.tags,
        module=note.module,
        metric=note.metric,
        anchor_type=note.anchor_type,
        anchor_label=note.anchor_label,
        include_in_export=True,
    )

    assert edited.created_at == note.created_at
    assert edited.body.endswith("repeated word.")
    assert edited.tags == ("close reading", "valence")

    repository.promote_draft(draft.item_id)
    promoted_notes = repository.list_notes(
        parent_type="analysis",
        parent_id=draft.item_id,
    )
    assert len(promoted_notes) == 1
    assert promoted_notes[0].note_id == edited.note_id
    assert promoted_notes[0].parent_type == "analysis"
    assert promoted_notes[0].body == edited.body


def test_results_only_revision_has_no_restorable_payload(tmp_path) -> None:
    repository = ResearchLibraryRepository(tmp_path / "analysis_library.sqlite3")
    _, revision, _ = repository.save_revision(
        parent_type="analysis",
        workspace_id="Single Poem",
        title="Private source",
        software_version=__version__,
        payload=None,
        storage_mode="results_only",
        text_sha256="abc",
        summary={"valence": 0.5},
        artifact_bundle=b"report",
    )

    with pytest.raises(ResearchLibraryError, match="results-only"):
        repository.load_payload(revision.revision_id)
