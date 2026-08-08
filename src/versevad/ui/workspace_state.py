"""Explicit workspace ownership for mutable Streamlit session state."""

from __future__ import annotations

from copy import deepcopy
from typing import MutableMapping

from versevad.ui.profiles import PROFILE_WIDGET_KEYS


WORKSPACE_STATE_VERSION = "workspace-state-v1"
_VAULT_KEY = "_versevad_workspace_state"
_ACTIVE_KEY = "_versevad_active_workspace_state"

# Single Poem and Other Text intentionally share an implementation but not
# mutable user data. These are the implementation's unprefixed widget/result
# keys; report-profile keys are already workspace-prefixed.
_TEXT_WORKSPACE_KEYS = frozenset(PROFILE_WIDGET_KEYS).union(
    {
        "project_name",
        "poem_title",
        "poem_author",
        "poem_text",
        "text_author",
        "text_year",
        "text_source_notes",
        "upload_signature",
        "workspace",
        "analysis_request_hash",
        "prepared_workspace_exports",
        "loaded_evidence_signature",
        "lexical_trajectory_source",
        "lexical_trajectory_view",
        "interpretation_lexicon",
        "pronunciation_overrides",
        "meter_scholar_revisions",
        "module_preset",
        "_applied_analysis_profile",
        "_pending_pronunciation_overrides",
        "_apply_pronunciation_resolutions",
        "_pronunciation_resolution_count",
        "_pronunciation_resolution_error",
    }
)

# Streamlit upload widgets are transient browser controls: their values may be
# read while the widget exists, but must never be assigned through
# ``st.session_state``.  Keep them under workspace ownership for transition and
# clear operations without placing them in the restorable workspace vault.
_TEXT_WORKSPACE_TRANSIENT_KEYS = frozenset({"uploaded_poem"})

_WORKSPACE_PREFIXES = {
    "Single Poem": ("single_poem_report_profiles_", "one_poem_"),
    "Other Text": ("other_text_report_profiles_",),
    "Compare Poems": ("compare_",),
    "Lexicon Explorer": ("explorer_", "lexicon_explorer_"),
    "VerseMap": ("standalone_versemap_",),
    "Personal Corpus": ("personal_corpus_",),
    "Saved Projects": (
        "corpus_",
        "analysis_texts_",
        "analysis_lexicons_",
        "analysis_modules_",
    ),
    "Corpus Browser": ("corpus_browser_",),
    "Reference Corpora": ("reference_corpora_",),
}
_WORKSPACE_EXACT_KEYS = {
    "Compare Poems": frozenset({"poem_comparison", "poem_comparison_set"}),
    "Lexicon Explorer": frozenset({"lexicon_explorer_result"}),
    "VerseMap": frozenset({"standalone_versemap_result"}),
}


def _owned_keys(workspace_id: str) -> frozenset[str]:
    if workspace_id in {"Single Poem", "Other Text"}:
        return _TEXT_WORKSPACE_KEYS
    return frozenset()


def _transient_keys(workspace_id: str) -> frozenset[str]:
    if workspace_id in {"Single Poem", "Other Text"}:
        return _TEXT_WORKSPACE_TRANSIENT_KEYS
    return frozenset()


def workspace_owned_session_keys(
    session_state: MutableMapping[str, object],
    workspace_id: str,
) -> frozenset[str]:
    """Return current temporary keys owned by one workspace."""

    keys = set(_owned_keys(workspace_id))
    keys.update(_transient_keys(workspace_id))
    keys.update(_WORKSPACE_EXACT_KEYS.get(workspace_id, ()))
    prefixes = _WORKSPACE_PREFIXES.get(workspace_id, ())
    keys.update(
        key
        for key in session_state
        if isinstance(key, str) and key.startswith(prefixes)
    )
    return frozenset(keys)


def workspace_has_session_work(
    session_state: MutableMapping[str, object],
    workspace_id: str,
) -> bool:
    def contains_meaningful_work(values: object) -> bool:
        if not isinstance(values, MutableMapping):
            return False
        if workspace_id in {"Single Poem", "Other Text"}:
            return any(
                values.get(key) not in (None, "", (), [], {})
                for key in ("poem_text", "poem_title", "workspace")
            )
        if workspace_id == "Compare Poems":
            return any(
                value not in (None, "", (), [], {})
                for key, value in values.items()
                if key in _WORKSPACE_EXACT_KEYS[workspace_id]
                or (isinstance(key, str) and key.startswith("compare_poem_") and key.endswith("_text"))
            )
        return bool(values)

    vault = session_state.get(_VAULT_KEY)
    if isinstance(vault, dict) and contains_meaningful_work(vault.get(workspace_id)):
        return True
    if session_state.get(_ACTIVE_KEY) != workspace_id:
        return False
    return contains_meaningful_work(
        {
            key: session_state.get(key)
            for key in workspace_owned_session_keys(session_state, workspace_id)
        }
    )


def adopt_current_state_for_workspace(
    session_state: MutableMapping[str, object],
    workspace_id: str,
) -> None:
    """Mark newly loaded state as the target workspace's live replacement."""

    vault = session_state.setdefault(_VAULT_KEY, {})
    if isinstance(vault, dict):
        vault.pop(workspace_id, None)
    session_state[_ACTIVE_KEY] = workspace_id


def activate_workspace_state(
    session_state: MutableMapping[str, object],
    workspace_id: str,
) -> None:
    """Snapshot the old owner and restore only the new owner's mutable keys."""

    previous = session_state.get(_ACTIVE_KEY)
    if previous == workspace_id:
        return
    vault = session_state.setdefault(_VAULT_KEY, {})
    if not isinstance(vault, dict):
        vault = {}
        session_state[_VAULT_KEY] = vault
    if isinstance(previous, str):
        previous_keys = _owned_keys(previous)
        if previous_keys:
            vault[previous] = {
                key: deepcopy(session_state[key])
                for key in previous_keys
                if key in session_state
            }
    transition_keys = (
        _owned_keys(str(previous or ""))
        .union(_owned_keys(workspace_id))
        .union(_transient_keys(str(previous or "")))
        .union(_transient_keys(workspace_id))
    )
    for key in transition_keys:
        session_state.pop(key, None)
    restored = vault.get(workspace_id, {})
    if isinstance(restored, dict):
        for key, value in restored.items():
            # The ownership check also protects already-open sessions whose
            # vault was populated by an older VerseVAD version that captured a
            # file-uploader value.
            if key in _owned_keys(workspace_id):
                session_state[key] = deepcopy(value)
    session_state[_ACTIVE_KEY] = workspace_id


def clear_workspace_state(
    session_state: MutableMapping[str, object],
    workspace_id: str,
) -> None:
    """Clear only one workspace's owned state and its saved snapshot."""

    vault = session_state.get(_VAULT_KEY)
    if isinstance(vault, dict):
        vault.pop(workspace_id, None)
    if session_state.get(_ACTIVE_KEY) == workspace_id:
        for key in workspace_owned_session_keys(session_state, workspace_id):
            session_state.pop(key, None)


__all__ = [
    "WORKSPACE_STATE_VERSION",
    "activate_workspace_state",
    "adopt_current_state_for_workspace",
    "clear_workspace_state",
    "workspace_has_session_work",
    "workspace_owned_session_keys",
]
