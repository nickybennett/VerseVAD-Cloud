from __future__ import annotations

from versevad.metric_capabilities import metric_capabilities


def test_categorical_association_capabilities_are_not_continuous() -> None:
    capability = metric_capabilities("emotion_association")

    assert capability.supports_categorical_rate
    assert not capability.supports_central_tendency
    assert not capability.supports_dispersion
    assert not capability.supports_raw_accumulation
    assert not capability.supports_normalized_accumulation


def test_only_defined_metric_families_expose_accumulation() -> None:
    assert metric_capabilities("emotion_intensity").supports_raw_accumulation
    assert metric_capabilities("sensorimotor").supports_raw_accumulation
    for module_id in ("vad", "concreteness", "frequency", "aoa", "word_length"):
        assert not metric_capabilities(module_id).supports_raw_accumulation


def test_vad_exposes_midpoint_load_without_raw_score_total() -> None:
    capability = metric_capabilities("vad")

    assert capability.supports_midpoint_deviation
    assert not capability.supports_raw_accumulation
    assert not capability.supports_normalized_accumulation
