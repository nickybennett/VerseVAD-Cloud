"""Transparent comparison of fixed lexical measurements and reader response.

Experiential Dynamics is deliberately independent of Streamlit.  It compares a
fixed, already-computed lexical profile with a sixteen-item reader assessment;
it never performs lexical lookup itself.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping, Sequence

from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileCoverage,
)
from versevad.lexical_semantic.concreteness import ConcretenessAnalysisResult
from versevad.models import Phase2AnalysisResult
from versevad.profile_aggregation import (
    token_audit_scalar_profiles,
    vad_profile_summaries,
)


EXPERIENTIAL_DYNAMICS_METHOD_VERSION = "experiential-dynamics-1.0"
EXPERIENTIAL_DYNAMICS_QUESTIONNAIRE_VERSION = "reader-response-16-v1"
EXPERIENTIAL_DYNAMICS_VAD_SOURCE_ID = "nrc_vad_v2_1"
EXPERIENTIAL_DYNAMICS_VAD_SOURCE_VERSION = "2.1 (March 2025)"
EXPERIENTIAL_DYNAMICS_CONCRETENESS_SOURCE_ID = "brysbaert-concreteness-2014"
EXPERIENTIAL_DYNAMICS_CONCRETENESS_SOURCE_VERSION = (
    "2014 supplementary workbook; 39,954 rated stimuli"
)


class AssessmentTiming(StrEnum):
    PRE_ANALYSIS = "pre_analysis"
    POST_ANALYSIS = "post_analysis"

    @property
    def label(self) -> str:
        return {
            self.PRE_ANALYSIS: "Pre-analysis",
            self.POST_ANALYSIS: "Post-analysis",
        }[self]


class DynamicRelationship(StrEnum):
    LOWER = "experienced_lower"
    AGREEMENT = "agreement"
    HIGHER = "experienced_higher"


@dataclass(frozen=True)
class ExperientialDynamicsConfiguration:
    methodology_version: str = EXPERIENTIAL_DYNAMICS_METHOD_VERSION
    questionnaire_version: str = EXPERIENTIAL_DYNAMICS_QUESTIONNAIRE_VERSION
    vad_source_id: str = EXPERIENTIAL_DYNAMICS_VAD_SOURCE_ID
    vad_source_version: str = EXPERIENTIAL_DYNAMICS_VAD_SOURCE_VERSION
    concreteness_source_id: str = EXPERIENTIAL_DYNAMICS_CONCRETENESS_SOURCE_ID
    concreteness_source_version: str = (
        EXPERIENTIAL_DYNAMICS_CONCRETENESS_SOURCE_VERSION
    )
    lexical_scope: LexicalScope = LexicalScope.STOPWORD_EXCLUDED
    weighting: AggregationWeighting = AggregationWeighting.TOKEN
    agreement_tolerance: float = 0.10

    def __post_init__(self) -> None:
        if not 0 <= self.agreement_tolerance <= 1:
            raise ValueError("Agreement tolerance must be on the normalized 0-1 scale.")
        if self.weighting is not AggregationWeighting.TOKEN:
            raise ValueError("Experiential Dynamics requires token weighting.")

    @property
    def profile(self) -> AnalysisProfile:
        return AnalysisProfile(self.lexical_scope, self.weighting)

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            {
                **asdict(self),
                "lexical_scope": self.lexical_scope.value,
                "weighting": self.weighting.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "experiential-dynamics-config:" + hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:16]


EXPERIENTIAL_DYNAMICS_CONFIGURATION = ExperientialDynamicsConfiguration()


@dataclass(frozen=True)
class ReaderQuestion:
    item_id: str
    dimension: str
    prompt: str
    options: tuple[str, str, str, str, str]


READER_QUESTIONS = (
    ReaderQuestion(
        "V1", "valence",
        "Overall, how would you characterize the poem's emotional atmosphere?",
        ("Strongly negative", "Somewhat negative", "Mixed or neutral", "Somewhat positive", "Strongly positive"),
    ),
    ReaderQuestion(
        "V2", "valence",
        "How does the poem frame its central situation, subject, or emotional world?",
        ("Deeply distressing or painful", "More distressing than affirming", "Mixed, balanced, or neutral", "More affirming than distressing", "Strongly affirming or sustaining"),
    ),
    ReaderQuestion(
        "V3", "valence",
        "Across the poem as a whole, which emotional direction feels more dominant?",
        ("Strongly toward loss, threat, pain, or aversion", "Somewhat toward loss, threat, pain, or aversion", "Neither direction clearly dominates", "Somewhat toward pleasure, hope, comfort, or attraction", "Strongly toward pleasure, hope, comfort, or attraction"),
    ),
    ReaderQuestion(
        "V4", "valence",
        "What is the poem's overall emotional residue by the end?",
        ("Strongly negative", "Somewhat negative", "Mixed or neutral", "Somewhat positive", "Strongly positive"),
    ),
    ReaderQuestion(
        "A1", "arousal",
        "How would you characterize the poem's overall level of activation or intensity?",
        ("Very subdued or calm", "Somewhat subdued", "Moderate or mixed", "Somewhat activated or intense", "Highly activated or intense"),
    ),
    ReaderQuestion(
        "A2", "arousal",
        "How much tension or pressure does the poem create as a whole?",
        ("Very little", "Relatively little", "Moderate or variable", "Considerable", "Very strong"),
    ),
    ReaderQuestion(
        "A3", "arousal",
        "How does the poem's movement or pacing feel?",
        ("Very still, slow, or unhurried", "Mostly restrained or unhurried", "Moderate or variable", "Mostly urgent, driving, or propulsive", "Highly urgent, driving, or propulsive"),
    ),
    ReaderQuestion(
        "A4", "arousal",
        "How much energetic force does the poem seem to carry?",
        ("Very low", "Low", "Moderate", "High", "Very high"),
    ),
    ReaderQuestion(
        "D1", "dominance",
        "How much agency or control does the poem's central speaker, subject, or consciousness seem to possess?",
        ("Very little; strongly powerless or constrained", "Limited", "Mixed or moderate", "Considerable", "Very strong; highly agentic or controlling"),
    ),
    ReaderQuestion(
        "D2", "dominance",
        "In the poem's central situation, does the speaker or subject mainly undergo events or exert influence over them?",
        ("Almost entirely undergoes or is acted upon", "More acted upon than acting", "Mixed or balanced", "More acting upon than being acted upon", "Strongly directs, controls, or determines events"),
    ),
    ReaderQuestion(
        "D3", "dominance",
        "How constrained versus free does the poem's central consciousness or subject feel?",
        ("Strongly trapped, constrained, or overpowered", "Somewhat constrained", "Mixed or moderate", "Somewhat free or self-directing", "Strongly free, self-directing, or empowered"),
    ),
    ReaderQuestion(
        "D4", "dominance",
        "Taken as a whole, how much mastery or command is present in the poem's experienced environment?",
        ("Very little; helplessness or external control dominates", "Limited", "Mixed or moderate", "Considerable", "Very strong; mastery or command dominates"),
    ),
    ReaderQuestion(
        "C1", "concreteness",
        "How tangible or physically instantiated does the poem feel overall?",
        ("Highly abstract or diffuse", "Mostly abstract", "Mixed or moderate", "Mostly tangible or concrete", "Highly tangible or concrete"),
    ),
    ReaderQuestion(
        "C2", "concreteness",
        "How strongly does the poem evoke sensory experience?",
        ("Very weakly", "Weakly", "Moderately", "Strongly", "Very strongly"),
    ),
    ReaderQuestion(
        "C3", "concreteness",
        "How clearly can you picture or spatially imagine the poem's central scenes, objects, bodies, or environment?",
        ("Hardly at all", "With limited clarity", "Moderately", "Clearly", "Very vividly"),
    ),
    ReaderQuestion(
        "C4", "concreteness",
        "How much of the poem's effect seems grounded in perceptible images, objects, actions, or sensations rather than primarily abstract statement?",
        ("Almost entirely abstract or conceptual", "More abstract than perceptible", "Mixed or balanced", "More perceptible than abstract", "Strongly grounded in perceptible imagery or sensation"),
    ),
)

DIMENSION_ORDER = ("valence", "arousal", "dominance", "concreteness")
DIMENSION_LABELS = {
    "valence": "Valence",
    "arousal": "Arousal",
    "dominance": "Dominance",
    "concreteness": "Concreteness",
}
RELATIONSHIP_LABELS = {
    "valence": {
        DynamicRelationship.LOWER: "Darkened",
        DynamicRelationship.AGREEMENT: "Valence-Matched",
        DynamicRelationship.HIGHER: "Brightened",
    },
    "arousal": {
        DynamicRelationship.LOWER: "Subdued",
        DynamicRelationship.AGREEMENT: "Arousal-Matched",
        DynamicRelationship.HIGHER: "Charged",
    },
    "dominance": {
        DynamicRelationship.LOWER: "Constrained",
        DynamicRelationship.AGREEMENT: "Dominance-Matched",
        DynamicRelationship.HIGHER: "Empowered",
    },
    "concreteness": {
        DynamicRelationship.LOWER: "Dissolved",
        DynamicRelationship.AGREEMENT: "Concreteness-Matched",
        DynamicRelationship.HIGHER: "Evoked",
    },
}
RELATIONSHIP_CODES = {
    DynamicRelationship.LOWER: "down",
    DynamicRelationship.AGREEMENT: "equal",
    DynamicRelationship.HIGHER: "up",
}
RELATIONSHIP_SYMBOLS = {
    DynamicRelationship.LOWER: "↓",
    DynamicRelationship.AGREEMENT: "=",
    DynamicRelationship.HIGHER: "↑",
}


@dataclass(frozen=True)
class MeasuredDimension:
    dimension: str
    normalized_value: float | None
    source_value: float | None
    source_unit: str
    source_id: str
    source_label: str
    source_version: str
    source_sha256: str
    coverage: ProfileCoverage | None


@dataclass(frozen=True)
class ExperientialDynamicsMeasurements:
    text_version_id: str
    configuration: ExperientialDynamicsConfiguration
    dimensions: tuple[MeasuredDimension, ...]
    unavailable_reason: str = ""

    @property
    def available(self) -> bool:
        return (
            not self.unavailable_reason
            and len(self.dimensions) == 4
            and all(item.normalized_value is not None for item in self.dimensions)
        )

    def dimension(self, dimension: str) -> MeasuredDimension:
        return next(item for item in self.dimensions if item.dimension == dimension)


@dataclass(frozen=True)
class ReaderResponse:
    item_id: str
    dimension: str
    numeric_value: int
    option_label: str
    prompt: str


@dataclass(frozen=True)
class DynamicDimensionResult:
    dimension: str
    measured_normalized: float
    measured_source_value: float
    experienced_raw_mean: float
    experienced_normalized: float
    response_population_standard_deviation: float
    dynamic_gap: float
    relationship: DynamicRelationship
    relationship_label: str
    compact_symbol: str


@dataclass(frozen=True)
class ExperientialDynamicsResult:
    assessment_id: str
    text_version_id: str
    configuration: ExperientialDynamicsConfiguration
    assessment_timing: AssessmentTiming
    submitted_at: str
    responses: tuple[ReaderResponse, ...]
    dimensions: tuple[DynamicDimensionResult, ...]
    dynamic_signature: str
    compact_code: str


def unavailable_measurements(
    text_version_id: str,
    reason: str,
    *,
    configuration: ExperientialDynamicsConfiguration = EXPERIENTIAL_DYNAMICS_CONFIGURATION,
) -> ExperientialDynamicsMeasurements:
    return ExperientialDynamicsMeasurements(
        text_version_id=text_version_id,
        configuration=configuration,
        dimensions=(),
        unavailable_reason=reason.strip(),
    )


def build_measurements(
    vad_result: Phase2AnalysisResult,
    concreteness_result: ConcretenessAnalysisResult,
    *,
    configuration: ExperientialDynamicsConfiguration = EXPERIENTIAL_DYNAMICS_CONFIGURATION,
) -> ExperientialDynamicsMeasurements:
    """Extract the fixed four-dimensional profile from completed evidence."""

    if vad_result.lexicon_metadata.lexicon_id != configuration.vad_source_id:
        raise ValueError("Experiential Dynamics requires NRC VAD Lexicon v2.1.")
    if vad_result.lexicon_metadata.version != configuration.vad_source_version:
        raise ValueError(
            "Experiential Dynamics requires the documented NRC VAD v2.1 version."
        )
    if (
        concreteness_result.resource_status.resource_id
        != configuration.concreteness_source_id
        or concreteness_result.resource_status.version
        != configuration.concreteness_source_version
    ):
        raise ValueError(
            "Experiential Dynamics requires the documented Brysbaert "
            "concreteness resource."
        )
    if (
        vad_result.document.text_version_id
        != concreteness_result.module_result.text_version_id
    ):
        raise ValueError("Experiential Dynamics inputs must describe the same text version.")

    profile = configuration.profile
    vad_summaries = vad_profile_summaries(vad_result)
    active_stopwords = tuple(
        getattr(getattr(vad_result, "stopword_policy", None), "active_words", ()) or ()
    )
    concreteness_summaries = token_audit_scalar_profiles(
        tokens=vad_result.tokens,
        audit_rows=concreteness_result.token_audit,
        value_attribute="rating",
        active_stopwords=active_stopwords,
    )
    dimensions: list[MeasuredDimension] = []
    for dimension in DIMENSION_ORDER[:3]:
        summary = vad_summaries[dimension][profile]
        dimensions.append(
            MeasuredDimension(
                dimension=dimension,
                normalized_value=summary.statistics.mean,
                source_value=summary.statistics.mean,
                source_unit="normalized 0-1",
                source_id=vad_result.lexicon_metadata.lexicon_id,
                source_label=vad_result.lexicon_metadata.display_name,
                source_version=vad_result.lexicon_metadata.version,
                source_sha256=vad_result.lexicon_validation.source_sha256,
                coverage=summary.coverage,
            )
        )
    concreteness_summary = concreteness_summaries[profile]
    source_mean = concreteness_summary.statistics.mean
    dimensions.append(
        MeasuredDimension(
            dimension="concreteness",
            normalized_value=(
                (source_mean - 1.0) / 4.0 if source_mean is not None else None
            ),
            source_value=source_mean,
            source_unit="source 1-5",
            source_id=concreteness_result.resource_status.resource_id,
            source_label=concreteness_result.resource_status.display_name,
            source_version=concreteness_result.resource_status.version,
            source_sha256=concreteness_result.resource_status.source_sha256,
            coverage=concreteness_summary.coverage,
        )
    )
    missing = [item.dimension for item in dimensions if item.normalized_value is None]
    return ExperientialDynamicsMeasurements(
        text_version_id=vad_result.document.text_version_id,
        configuration=configuration,
        dimensions=tuple(dimensions),
        unavailable_reason=(
            "Insufficient matched evidence for: " + ", ".join(missing)
            if missing
            else ""
        ),
    )


def classify_dynamic_gap(
    dynamic_gap: float,
    *,
    tolerance: float = EXPERIENTIAL_DYNAMICS_CONFIGURATION.agreement_tolerance,
) -> DynamicRelationship:
    if dynamic_gap < -tolerance:
        return DynamicRelationship.LOWER
    if dynamic_gap > tolerance:
        return DynamicRelationship.HIGHER
    return DynamicRelationship.AGREEMENT


def build_dynamic_signature(
    relationships: Mapping[str, DynamicRelationship],
) -> tuple[str, str]:
    """Return the formal four-part label and compact code in fixed order."""

    ordered = tuple(
        (dimension, DynamicRelationship(relationships[dimension]))
        for dimension in DIMENSION_ORDER
    )
    signature = " · ".join(
        RELATIONSHIP_LABELS[dimension][relationship]
        for dimension, relationship in ordered
    )
    compact = " ".join(
        f"{dimension[0].upper()}{RELATIONSHIP_SYMBOLS[relationship]}"
        for dimension, relationship in ordered
    )
    return signature, compact


def score_assessment(
    measurements: ExperientialDynamicsMeasurements,
    response_values: Mapping[str, int],
    *,
    assessment_timing: AssessmentTiming | str,
    submitted_at: str | None = None,
) -> ExperientialDynamicsResult:
    """Score one immutable reader assessment against fixed measurements."""

    if not measurements.available:
        raise ValueError(
            measurements.unavailable_reason
            or "Experiential Dynamics measurements are unavailable."
        )
    expected = {question.item_id for question in READER_QUESTIONS}
    supplied = set(response_values)
    if supplied != expected:
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unexpected " + ", ".join(extra))
        raise ValueError("Complete all sixteen reader-response items (" + "; ".join(detail) + ").")
    invalid = {
        item_id: value
        for item_id, value in response_values.items()
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5
    }
    if invalid:
        raise ValueError("Every reader-response value must be an integer from 1 to 5.")

    timing = AssessmentTiming(assessment_timing)
    responses = tuple(
        ReaderResponse(
            item_id=question.item_id,
            dimension=question.dimension,
            numeric_value=int(response_values[question.item_id]),
            option_label=question.options[int(response_values[question.item_id]) - 1],
            prompt=question.prompt,
        )
        for question in READER_QUESTIONS
    )
    results: list[DynamicDimensionResult] = []
    for dimension in DIMENSION_ORDER:
        values = [
            response.numeric_value
            for response in responses
            if response.dimension == dimension
        ]
        raw_mean = statistics.fmean(values)
        experienced = (raw_mean - 1.0) / 4.0
        measured = measurements.dimension(dimension)
        if measured.normalized_value is None or measured.source_value is None:
            raise ValueError(f"Measured {dimension} is unavailable.")
        gap = experienced - measured.normalized_value
        relationship = classify_dynamic_gap(
            gap,
            tolerance=measurements.configuration.agreement_tolerance,
        )
        results.append(
            DynamicDimensionResult(
                dimension=dimension,
                measured_normalized=measured.normalized_value,
                measured_source_value=measured.source_value,
                experienced_raw_mean=raw_mean,
                experienced_normalized=experienced,
                response_population_standard_deviation=statistics.pstdev(values),
                dynamic_gap=gap,
                relationship=relationship,
                relationship_label=RELATIONSHIP_LABELS[dimension][relationship],
                compact_symbol=RELATIONSHIP_SYMBOLS[relationship],
            )
        )
    submitted = submitted_at or datetime.now(UTC).isoformat(timespec="seconds")
    response_payload = "|".join(
        f"{item_id}:{response_values[item_id]}" for item_id in sorted(expected)
    )
    assessment_id = hashlib.sha256(
        (
            measurements.text_version_id
            + "|"
            + timing.value
            + "|"
            + submitted
            + "|"
            + response_payload
            + "|"
            + measurements.configuration.configuration_id
        ).encode("utf-8")
    ).hexdigest()
    result_tuple = tuple(results)
    signature, compact = build_dynamic_signature(
        {item.dimension: item.relationship for item in result_tuple}
    )
    return ExperientialDynamicsResult(
        assessment_id=assessment_id,
        text_version_id=measurements.text_version_id,
        configuration=measurements.configuration,
        assessment_timing=timing,
        submitted_at=submitted,
        responses=responses,
        dimensions=result_tuple,
        dynamic_signature=signature,
        compact_code=compact,
    )


def dimension_explanation(result: DynamicDimensionResult) -> str:
    label = DIMENSION_LABELS[result.dimension].lower()
    if result.relationship is DynamicRelationship.LOWER:
        return f"Experienced {label} is lower than measured lexical {label}."
    if result.relationship is DynamicRelationship.HIGHER:
        return f"Experienced {label} exceeds measured lexical {label}."
    return f"Experienced and measured lexical {label} agree within the tolerance."


__all__ = [
    "AssessmentTiming",
    "DIMENSION_LABELS",
    "DIMENSION_ORDER",
    "DynamicDimensionResult",
    "DynamicRelationship",
    "EXPERIENTIAL_DYNAMICS_CONFIGURATION",
    "EXPERIENTIAL_DYNAMICS_METHOD_VERSION",
    "ExperientialDynamicsConfiguration",
    "ExperientialDynamicsMeasurements",
    "ExperientialDynamicsResult",
    "MeasuredDimension",
    "READER_QUESTIONS",
    "ReaderQuestion",
    "ReaderResponse",
    "build_dynamic_signature",
    "build_measurements",
    "classify_dynamic_gap",
    "dimension_explanation",
    "score_assessment",
    "unavailable_measurements",
]
