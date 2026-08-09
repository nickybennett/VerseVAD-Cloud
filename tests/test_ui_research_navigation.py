from __future__ import annotations

from types import SimpleNamespace

import pytest

import versevad.ui.navigation as navigation
import versevad.ui.research as research


def test_registered_workspace_switch_does_not_call_rerun(monkeypatch) -> None:
    state = {
        "_pending_workspace_switch": "Single Poem",
        "_versevad_workspace_pages": {"Single Poem": "single-poem-page"},
    }
    switched: list[object] = []
    fake_streamlit = SimpleNamespace(
        session_state=state,
        switch_page=switched.append,
        rerun=lambda: pytest.fail(
            "A registered page switch must not call st.rerun()."
        ),
    )
    monkeypatch.setattr(navigation, "st", fake_streamlit)

    navigation.switch_to_workspace("Single Poem")

    assert switched == ["single-poem-page"]
    assert "_pending_workspace_switch" not in state


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
