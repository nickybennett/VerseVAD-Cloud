"""Shared Streamlit controls for reproducible stopword-sensitivity settings."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from versevad.models import StopwordMode, StopwordPolicy
from versevad.stopwords import (
    DEFAULT_PROTECTED_WORDS,
    build_stopword_policy,
    normalize_word_list,
)


@dataclass(frozen=True)
class StopwordUiSettings:
    mode: StopwordMode
    protected_words: tuple[str, ...]
    custom_additions: tuple[str, ...]
    custom_removals: tuple[str, ...]
    policy: StopwordPolicy


def _split_words(value: str) -> tuple[str, ...]:
    return normalize_word_list(
        part
        for line in value.splitlines()
        for part in line.replace(",", " ").split()
    )


def render_stopword_settings(key_prefix: str) -> StopwordUiSettings:
    """Render controls and return the exact policy to record with the run."""

    mode_key = f"{key_prefix}_stopword_mode"
    mode_label_key = f"{key_prefix}_stopword_mode_label"
    protected_key = f"{key_prefix}_protected_stopwords"
    additions_key = f"{key_prefix}_custom_stopword_additions"
    removals_key = f"{key_prefix}_custom_stopword_removals"
    mode_labels = {
        "Include all matched words": StopwordMode.ALL_MATCHED,
        "Exclude standard stopwords": StopwordMode.STANDARD,
        "Use custom stopword list": StopwordMode.CUSTOM,
    }
    st.session_state.setdefault(mode_key, StopwordMode.STANDARD.value)
    current_mode = StopwordMode(st.session_state[mode_key])
    st.session_state.setdefault(
        mode_label_key,
        next(
            label
            for label, mode in mode_labels.items()
            if mode == current_mode
        ),
    )
    st.session_state.setdefault(
        protected_key,
        "\n".join(DEFAULT_PROTECTED_WORDS),
    )
    st.session_state.setdefault(additions_key, "")
    st.session_state.setdefault(removals_key, "")

    if st.button(
        "Restore default stopword settings",
        key=f"{key_prefix}_restore_stopwords",
    ):
        st.session_state[mode_key] = StopwordMode.STANDARD.value
        st.session_state[mode_label_key] = "Exclude standard stopwords"
        st.session_state[protected_key] = "\n".join(DEFAULT_PROTECTED_WORDS)
        st.session_state[additions_key] = ""
        st.session_state[removals_key] = ""
        st.rerun()

    selected_label = st.selectbox(
        "Secondary-view policy",
        options=list(mode_labels),
        key=mode_label_key,
        help=(
            "The complete all-matched analysis is always preserved. This setting "
            "controls only the parallel sensitivity view."
        ),
    )
    selected_mode = mode_labels[selected_label]
    st.session_state[mode_key] = selected_mode.value

    protected_text = st.text_area(
        "Protected words retained in both views",
        key=protected_key,
        height=145,
        help=(
            "One word per line. Protected words override both the standard and "
            "custom stopword lists."
        ),
    )
    imported = st.file_uploader(
        "Import custom stopwords (.txt)",
        type=["txt"],
        key=f"{key_prefix}_import_stopwords",
        help="Use one word per line. Imported words become custom additions.",
    )
    if st.button(
        "Apply imported list",
        disabled=imported is None,
        key=f"{key_prefix}_apply_imported_stopwords",
    ):
        assert imported is not None
        try:
            imported_text = imported.getvalue().decode("utf-8-sig")
            imported_words = _split_words(imported_text)
            st.session_state[additions_key] = "\n".join(imported_words)
            st.session_state[mode_key] = StopwordMode.CUSTOM.value
            st.session_state[mode_label_key] = "Use custom stopword list"
            st.rerun()
        except (UnicodeDecodeError, ValueError) as error:
            st.error(f"The custom stopword file was not applied: {error}")

    additions_text = st.text_area(
        "Custom additions",
        key=additions_key,
        height=110,
        help="One word per line. These are used when custom mode is selected.",
    )
    removals_text = st.text_area(
        "Custom removals from the standard list",
        key=removals_key,
        height=110,
        help=(
            "One word per line. Removed words remain visible in the audit trail "
            "but are retained in the filtered aggregate."
        ),
    )
    protected = _split_words(protected_text)
    additions = _split_words(additions_text)
    removals = _split_words(removals_text)
    policy = build_stopword_policy(
        mode=selected_mode,
        protected_words=protected,
        custom_additions=additions,
        custom_removals=removals,
    )
    st.caption(
        f"Source: {policy.source} · library {policy.library_version} · "
        f"{policy.standard_word_count:,} standard entries · "
        f"{len(policy.active_words):,} active exclusions"
    )
    with st.expander("View and export the active stopword list"):
        st.write(
            f"List version: `{policy.list_version}`  \n"
            f"Active-list SHA-256: `{policy.active_list_sha256}`"
        )
        st.code("\n".join(policy.active_words) or "(no active exclusions)")
        st.download_button(
            "Export active stopword list",
            data=(
                "\ufeffstopword\n"
                + "".join(f"{word}\n" for word in policy.active_words)
            ).encode("utf-8"),
            file_name="VerseVAD_active_stopwords.csv",
            mime="text/csv",
            key=f"{key_prefix}_export_stopwords",
        )
    return StopwordUiSettings(
        mode=selected_mode,
        protected_words=protected,
        custom_additions=additions,
        custom_removals=removals,
        policy=policy,
    )
