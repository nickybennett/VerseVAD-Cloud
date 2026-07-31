"""Shared source preference for compact VAD overview displays."""

from __future__ import annotations

from collections.abc import Iterable


VAD_OVERVIEW_SOURCE_PRIORITY = (
    "nrc_vad_v2_1",
    "nrc_vad_v1",
    "warriner_vad_2013",
)


def preferred_overview_vad_lexicon_id(
    available_lexicon_ids: Iterable[str],
) -> str | None:
    """Return the fixed Overview source preference without merging sources."""

    available = tuple(dict.fromkeys(available_lexicon_ids))
    available_set = set(available)
    for lexicon_id in VAD_OVERVIEW_SOURCE_PRIORITY:
        if lexicon_id in available_set:
            return lexicon_id
    return available[0] if available else None


def overview_metric_matches_vad_preference(
    metric_id: str,
    preferred_lexicon_id: str | None,
) -> bool:
    """Keep non-VAD rows and only the preferred source's VAD rows."""

    if not metric_id.startswith("vad.") or preferred_lexicon_id is None:
        return True
    return metric_id.startswith(f"vad.{preferred_lexicon_id}.")


__all__ = [
    "VAD_OVERVIEW_SOURCE_PRIORITY",
    "overview_metric_matches_vad_preference",
    "preferred_overview_vad_lexicon_id",
]
