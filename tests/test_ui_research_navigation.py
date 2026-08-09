from __future__ import annotations

import pytest

import versevad.ui.navigation as navigation
import versevad.ui.research as research


@pytest.mark.parametrize(
    "workspace",
    [
        "Single Poem",
        "Other Text",
        "Compare Poems",
        "Lexicon Explorer",
        "VerseMap",
        "Saved Projects",
        "Personal Corpus",
    ],
)
def test_open_library_revision_navigates_to_restored_workspace(
    monkeypatch,
    workspace: str,
) -> None:
    restored: list[tuple[object, object]] = []
    navigated: list[str] = []
    item = object()
    revision = object()

    def restore(saved_item: object, saved_revision: object) -> str:
        restored.append((saved_item, saved_revision))
        return workspace

    monkeypatch.setattr(research, "restore_library_revision", restore)
    monkeypatch.setattr(navigation, "switch_to_workspace", navigated.append)

    research.open_library_revision(item, revision)

    assert restored == [(item, revision)]
    assert navigated == [workspace]
