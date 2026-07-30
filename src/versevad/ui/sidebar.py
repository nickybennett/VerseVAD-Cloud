"""Shared conditional sidebar skeleton for VerseVAD workspaces."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st


def _clean_title(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _comparison_titles() -> tuple[str, ...]:
    poem_ids = st.session_state.get("compare_poem_ids", ())
    if not isinstance(poem_ids, Sequence) or isinstance(poem_ids, str):
        poem_ids = ()
    return tuple(
        _clean_title(
            st.session_state.get(f"compare_{poem_id}_title"),
            f"Poem {position}",
        )
        for position, poem_id in enumerate(poem_ids, start=1)
    )


def _context_heading(workspace: str) -> tuple[str, str]:
    if workspace == "Single Poem":
        return (
            "Current Poem",
            _clean_title(st.session_state.get("poem_title"), "Untitled poem"),
        )
    if workspace == "Other Text":
        return (
            "Current Text",
            _clean_title(st.session_state.get("poem_title"), "Untitled text"),
        )
    if workspace == "Compare Poems":
        titles = _comparison_titles()
        return (
            "Current Comparison Set",
            (
                " · ".join(titles)
                if titles
                else "Two poems ready to configure"
            ),
        )
    if workspace == "Saved Projects":
        return ("Current Collection", "Saved research projects")
    if workspace == "Personal Corpus":
        return ("Current Collection", "Personal Corpus")
    if workspace == "Lexicon Explorer":
        result = st.session_state.get("lexicon_explorer_result")
        return (
            "Current Lookup",
            _clean_title(getattr(result, "query", None), "No active lookup"),
        )
    return ("Current Workspace", workspace)


def render_context_sidebar(workspace: str) -> None:
    """Render stable research controls appropriate to the active workspace."""

    # Imported lazily because the research workspace uses shared design
    # primitives, while the design shell itself imports this sidebar module.
    from versevad.ui.research import (
        autosave_active_draft,
        render_analysis_management_sidebar,
        render_research_notes_sidebar,
    )

    analytical = {
        "Single Poem",
        "Other Text",
        "Compare Poems",
        "Saved Projects",
        "Personal Corpus",
        "Lexicon Explorer",
    }
    if workspace not in analytical:
        return

    heading, context = _context_heading(workspace)
    autosave_active_draft(workspace)
    with st.sidebar:
        library_error = st.session_state.pop("_research_library_error", None)
        if isinstance(library_error, str):
            st.warning(library_error)
        st.markdown(f"### {heading}")
        st.caption(context)

        if workspace != "Lexicon Explorer":
            with st.expander("Analysis Profile", expanded=False):
                profile_key = (
                    "compare_analysis_profile"
                    if workspace == "Compare Poems"
                    else "module_preset"
                )
                st.caption(
                    _clean_title(
                        st.session_state.get(profile_key),
                        "Configure in the workspace",
                    )
                )
                st.caption(
                    "Profiles establish shared analytical defaults and remain "
                    "customizable in the workspace."
                )
            with st.expander("Analysis Settings", expanded=False):
                st.caption(
                    "Text processing, weighting, stopword treatment, enabled "
                    "modules, and advanced settings are shown in context."
                )
            with st.expander("Comparison Resources", expanded=False):
                st.caption(
                    "VerseMap and reference-corpus choices appear here as their "
                    "standalone collection tools are completed."
                )

        with st.expander("Research Notes", expanded=False):
            render_research_notes_sidebar(workspace)
        with st.expander("Analysis Management", expanded=False):
            render_analysis_management_sidebar(workspace)
        with st.expander("Export", expanded=False):
            st.caption(
                "Open the workspace's Export report section after analysis for "
                "available CSV, Word, and audit downloads."
            )


__all__ = ["render_context_sidebar"]
