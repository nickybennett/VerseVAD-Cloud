"""Authoritative human-facing labels for exported VerseVAD metrics.

Canonical metric IDs are stable machine identifiers.  This module is a
presentation-only registry: it converts those identities (plus retained legacy
metadata where necessary) into concise labels for readable CSV and Word
reports without changing values, denominators, aggregation, or schema
semantics.
"""

from __future__ import annotations

import re


_EXACT_LABELS = {
    "concreteness.mean": "Mean Concreteness",
    "concreteness.population_sd": "Concreteness SD",
    "frequency.mean_zipf": "Mean Zipf Frequency",
    "frequency.population.standard.deviation": "Frequency SD",
    "aoa.mean_years": "Mean Age of Acquisition",
    "aoa.population.standard.deviation": "AoA SD",
    "readability.vv.pre": "VerseVAD Poetic Reading Ease",
}

_ACRONYMS = {
    "Aoa": "AoA",
    "Hdd": "HD-D",
    "Id": "ID",
    "Mattr": "MATTR",
    "Mtld": "MTLD",
    "Pca": "PCA",
    "Pos": "POS",
    "Sd": "SD",
    "Smog": "SMOG",
    "Ttr": "TTR",
    "Vad": "VAD",
    "Vader": "VADER",
    "Versemap": "VerseMap",
}


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")


def _pretty(value: object) -> str:
    words = re.sub(r"[._]+", " ", str(value or "")).strip().title()
    for source, target in _ACRONYMS.items():
        words = re.sub(rf"\b{re.escape(source)}\b", target, words)
    words = words.replace("Poetry ID", "PoetryID")
    words = words.replace("Flesch Kincaid", "Flesch-Kincaid")
    words = words.replace("Per 100", "per 100")
    return words


def _statistic(metric_id: str, legacy_metric_id: str) -> str:
    raw = _slug(legacy_metric_id or metric_id)
    if raw in {"coverage", "token_coverage"} or raw.endswith("_token_coverage"):
        return "coverage"
    if raw == "type_coverage" or raw.endswith("_type_coverage"):
        return "type_coverage"
    if raw.endswith(("_standard_deviation", "_population_sd", "_sd")):
        return "sd"
    if raw.endswith(("_cumulative", "_cumulative_load")):
        return "cumulative"
    if raw.endswith(("_mean", "_mean_mean", "_mean_years", "_mean_zipf")):
        return "mean"
    return ""


def _dimension_base(dimension: object, category: object) -> str:
    raw = _slug(dimension or category)
    for suffix in ("_association", "_intensity", "_sensorimotor", "_mean"):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
    return _pretty(raw)


def human_metric_label(
    *,
    module_id: object,
    metric_id: object,
    fallback: object = "",
    legacy_metric_id: object = "",
    dimension: object = "",
    category: object = "",
) -> str:
    """Return the single authoritative display label for an exported metric."""

    module = _slug(module_id)
    metric = str(metric_id or "").strip()
    legacy = str(legacy_metric_id or "").strip()
    statistic = _statistic(metric, legacy)
    base = _dimension_base(dimension, category)

    if statistic == "coverage":
        return "Coverage"
    if statistic == "type_coverage":
        return "Type Coverage"

    if module == "concreteness" and (base == "Concreteness" or "concreteness_mean" in _slug(legacy)):
        return "Concreteness SD" if statistic == "sd" else "Mean Concreteness"
    if module == "aoa" and (base == "AoA" or "aoa_mean" in _slug(legacy)):
        return "AoA SD" if statistic == "sd" else "Mean Age of Acquisition"
    if module == "frequency" and (base == "Frequency" or "frequency_mean" in _slug(legacy)):
        return "Frequency SD" if statistic == "sd" else "Mean Zipf Frequency"
    if module == "sensorimotor" and base:
        suffix = {"mean": "Mean", "sd": "SD", "cumulative": "Cumulative"}.get(statistic)
        if suffix:
            return f"{base} {suffix}"
    if module == "emotion_intensity" and base:
        suffix = {"mean": "Mean", "sd": "SD", "cumulative": "Cumulative"}.get(statistic, "Mean")
        return f"{base} Intensity {suffix}"
    if module == "emotion_association" and base:
        suffix = {"sd": " SD", "cumulative": " Cumulative"}.get(statistic, "")
        return f"{base} Association{suffix}"
    if module == "vad" and base:
        suffix = {
            "mean": f"Mean {base}",
            "sd": f"{base} SD",
            "cumulative": f"{base} Cumulative",
        }.get(statistic)
        if suffix:
            return suffix
        raw = _slug(legacy or metric)
        for prefix in ("vad_",):
            raw = raw.removeprefix(prefix)
        return f"{base} {_pretty(raw)}".strip()
    if base == "Mean Word Length" or "word_length_mean_word_length" in _slug(legacy):
        return "Word Length SD" if statistic == "sd" else "Mean Word Length"

    exact = _EXACT_LABELS.get(metric)
    if exact:
        return exact

    display_id = metric
    dotted_module = module.replace("_", ".")
    if display_id.casefold().startswith(dotted_module + "."):
        display_id = display_id[len(dotted_module) + 1 :]
    label = _pretty(display_id)
    if module == "poetry_id" and not label.startswith("PoetryID"):
        label = f"PoetryID {label}"
    elif module == "versemap" and not label.startswith("VerseMap"):
        label = f"VerseMap {label}"
    elif module == "vader" and not label.startswith("VADER"):
        label = f"VADER {label}"
    return label or _pretty(fallback or legacy_metric_id or metric_id)


__all__ = ["human_metric_label"]
