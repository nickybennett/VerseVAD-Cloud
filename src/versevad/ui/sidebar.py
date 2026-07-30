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
    if workspace == "VerseMap":
        return (
            "Current VerseMap Session",
            _clean_title(
                st.session_state.get("standalone_versemap_title"),
                "No poem mapped yet",
            ),
        )
    if workspace == "Reference Corpora":
        return ("Current Collection Tool", "Reference Corpora")
    if workspace == "Corpus Browser":
        return ("Current Collection Tool", "Read-only Corpus Browser")
    if workspace == "Form Library":
        return ("Current Reference", "Inherited Form Library")
    if workspace in {"Documentation", "Methodology"}:
        return ("Current Learning Workspace", workspace)
    return ("Current Workspace", workspace)


_WORKSPACE_DESCRIPTIONS = {
    "Reference Corpora": (
        "Inspect the built-in public-domain collection and manage private local "
        "reference corpora when persistent storage is available."
    ),
    "VerseMap": (
        "Compare one fixed Standard Profile 1.0 record with an indexed "
        "reference corpus."
    ),
    "Form Library": (
        "Browse the definitions, requirements, weights, limitations, and "
        "sources used by Inherited Form Analysis."
    ),
    "Corpus Browser": (
        "Inspect indexed corpus contents, coverage, distributions, and poem "
        "profiles without modifying source files."
    ),
    "Documentation": (
        "Read the operating, installation, updating, and research-library "
        "guidance packaged with this release."
    ),
    "Methodology": (
        "Search calculations, data provenance, evidence rules, and known "
        "limitations for VerseVAD metrics."
    ),
}

_RELATED_WORKSPACES = {
    "Single Poem": ("Compare Poems", "VerseMap", "Analysis Library"),
    "Other Text": ("Single Poem", "Lexicon Explorer", "Analysis Library"),
    "Compare Poems": ("Single Poem", "VerseMap", "Analysis Library"),
    "Saved Projects": ("Corpus Browser", "VerseMap", "Analysis Library"),
    "Personal Corpus": ("Single Poem", "VerseMap", "Corpus Browser"),
    "Lexicon Explorer": ("Single Poem", "Methodology", "Documentation"),
    "Analysis Library": ("Single Poem", "Compare Poems", "Saved Projects"),
    "Reference Corpora": ("Corpus Browser", "VerseMap", "Documentation"),
    "VerseMap": ("Reference Corpora", "Corpus Browser", "Analysis Library"),
    "Form Library": ("Single Poem", "Methodology", "Documentation"),
    "Corpus Browser": ("Reference Corpora", "VerseMap", "Form Library"),
    "Documentation": ("Methodology", "Single Poem", "Reference Corpora"),
    "Methodology": ("Documentation", "Lexicon Explorer", "Form Library"),
}


def _render_quick_navigation(workspace: str) -> None:
    from versevad.ui.navigation import switch_to_workspace

    st.caption("Move directly to a related workspace.")
    for target in _RELATED_WORKSPACES.get(
        workspace,
        ("Single Poem", "Analysis Library", "Documentation"),
    ):
        if st.button(
            target,
            key=f"sidebar_quick_nav__{workspace}__{target}",
            width="stretch",
        ):
            switch_to_workspace(target)


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
        "Analysis Library",
        "VerseMap",
    }

    heading, context = _context_heading(workspace)
    if workspace in analytical:
        autosave_active_draft(workspace)
    with st.sidebar:
        library_error = st.session_state.pop("_research_library_error", None)
        if isinstance(library_error, str):
            st.warning(library_error)
        st.markdown(f"### {heading}")
        st.caption(context)

        if workspace not in analytical:
            with st.expander("About This Workspace", expanded=False):
                st.caption(
                    _WORKSPACE_DESCRIPTIONS.get(
                        workspace,
                        "Use the top navigation to choose a VerseVAD workspace.",
                    )
                )
            with st.expander("Quick Navigation", expanded=False):
                _render_quick_navigation(workspace)
            with st.expander("Data & Privacy", expanded=False):
                if workspace in {"Reference Corpora", "Corpus Browser"}:
                    st.caption(
                        "Built-in reference texts are read-only. Private corpora "
                        "in local installations remain in ignored project storage."
                    )
                else:
                    st.caption(
                        "This reference workspace does not change analytical "
                        "results or upload text to an external service."
                    )
            return

        if workspace not in {"Lexicon Explorer", "Analysis Library"}:
            with st.expander("Analysis Profile", expanded=False):
                if workspace == "VerseMap":
                    st.caption("VerseMap Standard Profile 1.0")
                    st.caption(
                        "This comparison profile is fixed so user and reference "
                        "poems remain directly comparable."
                    )
                else:
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
                        "Profiles establish shared analytical defaults and "
                        "remain customizable in the workspace."
                    )
            with st.expander("Analysis Settings", expanded=False):
                if workspace == "VerseMap":
                    st.caption(
                        "Choose the indexed corpus and result-retention settings "
                        "in the workspace. Preprocessing and feature definitions "
                        "remain fixed."
                    )
                else:
                    st.caption(
                        "Text processing, weighting, stopword treatment, enabled "
                        "modules, and advanced settings are shown in context."
                    )
            with st.expander("Comparison Resources", expanded=False):
                if workspace == "VerseMap":
                    st.caption(
                        _clean_title(
                            st.session_state.get("standalone_versemap_corpus"),
                            "Choose a reference corpus in the workspace.",
                        )
                    )
                else:
                    st.caption(
                        "Use Reference Corpora to inspect available collections, "
                        "then open VerseMap or Corpus Browser for comparison."
                    )

        if workspace != "Analysis Library":
            with st.expander("Research Notes", expanded=False):
                render_research_notes_sidebar(workspace)
            with st.expander("Analysis Management", expanded=False):
                render_analysis_management_sidebar(workspace)
            with st.expander("Export", expanded=False):
                st.caption(
                    "Open the workspace's Export report section after analysis "
                    "for available CSV, Word, and audit downloads."
                )
        with st.expander("Quick Navigation", expanded=False):
            _render_quick_navigation(workspace)


__all__ = ["render_context_sidebar"]
