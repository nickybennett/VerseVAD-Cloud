from __future__ import annotations

import csv
import io
import itertools

import pytest

from versevad.analysis_profiles import AggregationWeighting, LexicalScope
from versevad.experiential_dynamics import (
    AssessmentTiming,
    DIMENSION_ORDER,
    DynamicRelationship,
    EXPERIENTIAL_DYNAMICS_CONFIGURATION,
    ExperientialDynamicsMeasurements,
    MeasuredDimension,
    READER_QUESTIONS,
    build_dynamic_signature,
    classify_dynamic_gap,
    score_assessment,
)
from versevad.exports.experiential_dynamics import (
    export_experiential_dynamics_bundle,
)
from versevad.research_library import deserialize_value, serialize_value


def _measurements(value: float = 0.5) -> ExperientialDynamicsMeasurements:
    return ExperientialDynamicsMeasurements(
        text_version_id="text-version-1",
        configuration=EXPERIENTIAL_DYNAMICS_CONFIGURATION,
        dimensions=tuple(
            MeasuredDimension(
                dimension=dimension,
                normalized_value=value,
                source_value=(3.0 if dimension == "concreteness" else value),
                source_unit=(
                    "source 1-5"
                    if dimension == "concreteness"
                    else "normalized 0-1"
                ),
                source_id=(
                    "brysbaert-concreteness-2014"
                    if dimension == "concreteness"
                    else "nrc_vad_v2_1"
                ),
                source_label="Test resource",
                source_version="test",
                source_sha256="abc123",
                coverage=None,
            )
            for dimension in DIMENSION_ORDER
        ),
    )


def test_configuration_is_fixed_and_versioned() -> None:
    configuration = EXPERIENTIAL_DYNAMICS_CONFIGURATION
    assert configuration.vad_source_id == "nrc_vad_v2_1"
    assert configuration.concreteness_source_id == "brysbaert-concreteness-2014"
    assert configuration.lexical_scope is LexicalScope.STOPWORD_EXCLUDED
    assert configuration.weighting is AggregationWeighting.TOKEN
    assert configuration.agreement_tolerance == pytest.approx(0.10)
    assert configuration.configuration_id.startswith("experiential-dynamics-config:")


@pytest.mark.parametrize(
    ("gap", "expected"),
    (
        (-0.100001, DynamicRelationship.LOWER),
        (-0.10, DynamicRelationship.AGREEMENT),
        (0.0, DynamicRelationship.AGREEMENT),
        (0.10, DynamicRelationship.AGREEMENT),
        (0.100001, DynamicRelationship.HIGHER),
    ),
)
def test_agreement_tolerance_is_inclusive(
    gap: float,
    expected: DynamicRelationship,
) -> None:
    assert classify_dynamic_gap(gap) is expected


def test_all_81_dynamic_signatures_are_distinct() -> None:
    relationships = tuple(DynamicRelationship)
    signatures = {
        build_dynamic_signature(dict(zip(DIMENSION_ORDER, combination)))[0]
        for combination in itertools.product(relationships, repeat=4)
    }
    assert len(signatures) == 81


def test_assessment_scoring_normalizes_responses_and_retains_dispersion() -> None:
    values_by_dimension = {
        "valence": 1,
        "arousal": 5,
        "dominance": 3,
        "concreteness": 4,
    }
    responses = {
        question.item_id: values_by_dimension[question.dimension]
        for question in READER_QUESTIONS
    }
    result = score_assessment(
        _measurements(),
        responses,
        assessment_timing=AssessmentTiming.PRE_ANALYSIS,
        submitted_at="2026-08-13T12:00:00+00:00",
    )
    by_dimension = {item.dimension: item for item in result.dimensions}
    assert by_dimension["valence"].experienced_normalized == pytest.approx(0.0)
    assert by_dimension["valence"].dynamic_gap == pytest.approx(-0.5)
    assert by_dimension["arousal"].experienced_normalized == pytest.approx(1.0)
    assert by_dimension["dominance"].relationship is DynamicRelationship.AGREEMENT
    assert by_dimension["concreteness"].experienced_raw_mean == pytest.approx(4.0)
    assert all(
        item.response_population_standard_deviation == pytest.approx(0.0)
        for item in result.dimensions
    )
    assert result.assessment_timing is AssessmentTiming.PRE_ANALYSIS
    assert len(result.responses) == 16
    assert result.dynamic_signature == (
        "Darkened · Charged · Dominance-Matched · Evoked"
    )
    assert result.compact_code == "V↓ A↑ D= C↑"


def test_export_retains_dimension_and_item_level_audit_data() -> None:
    responses = {question.item_id: 3 for question in READER_QUESTIONS}
    measurements = _measurements()
    result = score_assessment(
        measurements,
        responses,
        assessment_timing=AssessmentTiming.POST_ANALYSIS,
        submitted_at="2026-08-13T12:00:00+00:00",
    )
    files = export_experiential_dynamics_bundle(result, measurements)
    assert set(files) == {
        "experiential_dynamics_summary.csv",
        "experiential_dynamics_responses.csv",
    }
    summary = list(
        csv.DictReader(
            io.StringIO(files["experiential_dynamics_summary.csv"].decode("utf-8-sig"))
        )
    )
    item_rows = list(
        csv.DictReader(
            io.StringIO(files["experiential_dynamics_responses.csv"].decode("utf-8-sig"))
        )
    )
    assert len(summary) == 4
    assert len(item_rows) == 16
    assert summary[0]["fixed_scope"] == "STOPWORD_EXCLUDED"
    assert summary[0]["fixed_weighting"] == "TOKEN"
    assert summary[0]["fixed_profile_label"] == (
        "Stopword-excluded · Token-weighted"
    )
    assert summary[0]["assessment_timing"] == "post_analysis"
    assert {row["item_id"] for row in item_rows} == {
        question.item_id for question in READER_QUESTIONS
    }


def test_completed_assessment_round_trips_through_saved_analysis_serializer() -> None:
    responses = {question.item_id: 3 for question in READER_QUESTIONS}
    result = score_assessment(
        _measurements(),
        responses,
        assessment_timing=AssessmentTiming.PRE_ANALYSIS,
        submitted_at="2026-08-13T12:00:00+00:00",
    )
    restored = deserialize_value(serialize_value(result))
    assert restored == result
    assert restored.assessment_timing is AssessmentTiming.PRE_ANALYSIS
