"""Semantic reporting capabilities for profile-aware lexical metrics.

The registry prevents presentation and export layers from inferring statistical
operations merely because a numeric field happens to exist.  Calculations stay
in their owning modules; this module only declares which summaries are
meaningful to expose to readers.
"""

from __future__ import annotations

from dataclasses import dataclass


METRIC_CAPABILITY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class MetricCapabilities:
    measurement_kind: str
    supports_dispersion: bool
    supports_raw_accumulation: bool
    supports_normalized_accumulation: bool
    supports_midpoint_deviation: bool
    denominator_kind: str
    supports_central_tendency: bool = True
    supports_categorical_rate: bool = False
    supports_token_weighting: bool = True
    supports_type_weighting: bool = True
    supports_lexical_contributors: bool = True
    supports_structural_breakdown: bool = True
    supports_visualization: bool = True
    primary_caution: str = ""


_DEFAULT_CONTINUOUS = MetricCapabilities(
    measurement_kind="continuous",
    supports_dispersion=True,
    supports_raw_accumulation=False,
    supports_normalized_accumulation=False,
    supports_midpoint_deviation=False,
    denominator_kind="matched lexical observations",
)


METRIC_CAPABILITIES: dict[str, MetricCapabilities] = {
    "vad": MetricCapabilities(
        measurement_kind="continuous",
        supports_dispersion=True,
        supports_raw_accumulation=False,
        supports_normalized_accumulation=False,
        supports_midpoint_deviation=True,
        denominator_kind="matched lexical observations",
        primary_caution=(
            "Normative lexical ratings are evidence about matched vocabulary, "
            "not declarations of a poem's or reader's emotion."
        ),
    ),
    "emotion_association": MetricCapabilities(
        measurement_kind="categorical_association",
        supports_dispersion=False,
        supports_raw_accumulation=False,
        supports_normalized_accumulation=False,
        supports_midpoint_deviation=False,
        denominator_kind="eligible lexical tokens or types",
        supports_central_tendency=False,
        supports_categorical_rate=True,
        primary_caution=(
            "Categories overlap; association proportions need not sum to 100%. "
            "Binary membership has no within-text score dispersion."
        ),
    ),
    "emotion_intensity": MetricCapabilities(
        measurement_kind="continuous_intensity",
        supports_dispersion=True,
        supports_raw_accumulation=True,
        supports_normalized_accumulation=False,
        supports_midpoint_deviation=False,
        denominator_kind="matched word-emotion intensity observations",
        primary_caution=(
            "Intensity is summarized only among word-category pairs for which "
            "the source supplies a rating."
        ),
    ),
    "sensorimotor": MetricCapabilities(
        measurement_kind="continuous",
        supports_dispersion=True,
        supports_raw_accumulation=True,
        supports_normalized_accumulation=True,
        supports_midpoint_deviation=False,
        denominator_kind="matched Lancaster observations",
        primary_caution=(
            "Sensorimotor norms describe lexical affordances, not imagery "
            "guaranteed by the poem or experienced by every reader."
        ),
    ),
    "concreteness": _DEFAULT_CONTINUOUS,
    "frequency": _DEFAULT_CONTINUOUS,
    "aoa": _DEFAULT_CONTINUOUS,
    "word_length": _DEFAULT_CONTINUOUS,
}


def metric_capabilities(module_id: str) -> MetricCapabilities:
    """Return the declared semantics for one profile-aware module."""

    return METRIC_CAPABILITIES.get(module_id, _DEFAULT_CONTINUOUS)


__all__ = [
    "METRIC_CAPABILITIES",
    "METRIC_CAPABILITY_SCHEMA_VERSION",
    "MetricCapabilities",
    "metric_capabilities",
]
