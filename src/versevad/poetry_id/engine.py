"""Deterministic PoetryID classification over completed VAD evidence."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from typing import Mapping, Sequence

from versevad import __version__
from versevad.core.modules import (
    ModuleCoverage,
    ModuleInput,
    ModuleMetric,
    ModuleProvenance,
    ModuleResult,
    ModuleWarning,
    ResultLayer,
    WarningSeverity,
)
from versevad.core.resources import ResourceProvenance
from versevad.models import DescriptiveStatistics, VadScores
from versevad.poetry_id.archetypes import (
    ARCHETYPES,
    PoetryArchetype,
    VadLevel,
    resolve_archetype,
)


POETRY_ID_MODULE_NAME = "poetry_id"
POETRY_ID_MODULE_VERSION = "1.0.0"
SUPPORTED_VAD_LEXICON_IDS = frozenset(
    {"warriner_vad_2013", "nrc_vad_v1", "nrc_vad_v2_1"}
)
_DIMENSIONS = ("valence", "arousal", "dominance")
_SUPPORTED_WEIGHTINGS = frozenset({"token", "type"})
_SUPPORTED_VIEWS = frozenset(
    {"all_matched", "stopwords_excluded", "content_words"}
)


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


@dataclass(frozen=True)
class ThresholdBand:
    low_max: float
    high_min: float
    low_centroid: float | None = None
    moderate_centroid: float | None = None
    high_centroid: float | None = None

    def __post_init__(self) -> None:
        low_max = _number(self.low_max, "low_max")
        high_min = _number(self.high_min, "high_min")
        if not 0 <= low_max <= 1 or not 0 <= high_min <= 1:
            raise ValueError("Threshold values must be on the normalized 0 to 1 scale.")
        if low_max >= high_min:
            raise ValueError("low_max must be below high_min.")
        centroids = (
            low_max / 2 if self.low_centroid is None else _number(
                self.low_centroid, "low centroid"
            ),
            (low_max + high_min) / 2
            if self.moderate_centroid is None
            else _number(self.moderate_centroid, "moderate centroid"),
            (high_min + 1) / 2
            if self.high_centroid is None
            else _number(self.high_centroid, "high centroid"),
        )
        if not 0 <= centroids[0] <= low_max:
            raise ValueError("The low centroid must fall inside the low range.")
        if not low_max <= centroids[1] <= high_min:
            raise ValueError(
                "The moderate centroid must fall inside the moderate range."
            )
        if not high_min <= centroids[2] <= 1:
            raise ValueError("The high centroid must fall inside the high range.")
        object.__setattr__(self, "low_max", low_max)
        object.__setattr__(self, "high_min", high_min)
        object.__setattr__(self, "low_centroid", centroids[0])
        object.__setattr__(self, "moderate_centroid", centroids[1])
        object.__setattr__(self, "high_centroid", centroids[2])

    def centroid(self, level: VadLevel) -> float:
        value = {
            VadLevel.LOW: self.low_centroid,
            VadLevel.MODERATE: self.moderate_centroid,
            VadLevel.HIGH: self.high_centroid,
        }[level]
        assert value is not None
        return value


@dataclass(frozen=True)
class ThresholdProfile:
    profile_id: str
    name: str
    method: str
    dimensions: Mapping[str, ThresholdBand]
    configuration_version: str
    built_in: bool
    normalization_basis: str = "VerseVAD normalized VAD scale, 0 to 1"

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.name.strip():
            raise ValueError("A threshold profile requires an ID and name.")
        if self.method != "fixed":
            raise ValueError(
                "PoetryID Version 1 supports fixed and custom-fixed thresholds only."
            )
        if set(self.dimensions) != set(_DIMENSIONS):
            raise ValueError(
                "Threshold profiles must define valence, arousal, and dominance."
            )
        if not all(
            isinstance(self.dimensions[name], ThresholdBand)
            for name in _DIMENSIONS
        ):
            raise ValueError("Every threshold dimension must be a ThresholdBand.")
        if not self.configuration_version.strip():
            raise ValueError("A threshold profile requires a configuration version.")
        object.__setattr__(
            self,
            "dimensions",
            {name: self.dimensions[name] for name in _DIMENSIONS},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "method": self.method,
            "dimensions": {
                name: asdict(self.dimensions[name]) for name in _DIMENSIONS
            },
            "configuration_version": self.configuration_version,
            "built_in": self.built_in,
            "normalization_basis": self.normalization_basis,
        }

    @classmethod
    def from_dict(cls, values: Mapping[str, object]) -> ThresholdProfile:
        raw_dimensions = values.get("dimensions")
        if not isinstance(raw_dimensions, Mapping):
            raise ValueError("Threshold profile dimensions are missing.")
        return cls(
            profile_id=str(values.get("profile_id", "")),
            name=str(values.get("name", "")),
            method=str(values.get("method", "")),
            dimensions={
                str(name): ThresholdBand(**dict(band))
                for name, band in raw_dimensions.items()
                if isinstance(band, Mapping)
            },
            configuration_version=str(
                values.get("configuration_version", "")
            ),
            built_in=bool(values.get("built_in", False)),
            normalization_basis=str(
                values.get(
                    "normalization_basis",
                    "VerseVAD normalized VAD scale, 0 to 1",
                )
            ),
        )


DEFAULT_THRESHOLD_PROFILE = ThresholdProfile(
    profile_id="default_fixed",
    name="Default Fixed Thresholds",
    method="fixed",
    dimensions={
        name: ThresholdBand(low_max=0.4, high_min=0.6)
        for name in _DIMENSIONS
    },
    configuration_version="poetry-id-thresholds-v1",
    built_in=True,
)


@dataclass(frozen=True)
class PoetryIDConfiguration:
    threshold_profile: ThresholdProfile = DEFAULT_THRESHOLD_PROFILE
    weighting_modes: tuple[str, ...] = ("token", "type")
    analysis_views: tuple[str, ...] = (
        "all_matched",
        "stopwords_excluded",
        "content_words",
    )
    vad_lexicon_ids: tuple[str, ...] = ()
    requested_lexical_dimensions: tuple[str, ...] = ()
    minimum_matched_tokens: int = 5
    minimum_matched_types: int = 3
    minimum_token_coverage: float = 0.2
    minimum_type_coverage: float = 0.2
    low_coverage_caution_threshold: float = 0.5
    high_coverage_threshold: float = 0.8
    boundary_sensitivity_distance: float = 0.03
    high_confidence_boundary_distance: float = 0.08
    high_confidence_neighbor_margin: float = 0.08
    high_confidence_centroid_distance: float = 0.2
    distance_metric: str = "euclidean"
    affinity_epsilon: float = 1e-9
    scenario_id: str = "poetry-id-v1"

    def __post_init__(self) -> None:
        if not self.weighting_modes or not set(self.weighting_modes) <= (
            _SUPPORTED_WEIGHTINGS
        ):
            raise ValueError("PoetryID weighting modes must be token and/or type.")
        if len(set(self.weighting_modes)) != len(self.weighting_modes):
            raise ValueError("PoetryID weighting modes cannot be duplicated.")
        if not self.analysis_views or not set(self.analysis_views) <= (
            _SUPPORTED_VIEWS
        ):
            raise ValueError(
                "PoetryID views must be all_matched, stopwords_excluded, and/or "
                "content_words."
            )
        if len(set(self.analysis_views)) != len(self.analysis_views):
            raise ValueError("PoetryID analysis views cannot be duplicated.")
        if len(set(self.vad_lexicon_ids)) != len(self.vad_lexicon_ids):
            raise ValueError("PoetryID VAD source IDs cannot be duplicated.")
        if len(set(self.requested_lexical_dimensions)) != len(
            self.requested_lexical_dimensions
        ):
            raise ValueError(
                "PoetryID lexical-character dimensions cannot be duplicated."
            )
        if self.minimum_matched_tokens < 1 or self.minimum_matched_types < 1:
            raise ValueError("PoetryID minimum evidence counts must be at least 1.")
        proportions = (
            self.minimum_token_coverage,
            self.minimum_type_coverage,
            self.low_coverage_caution_threshold,
            self.high_coverage_threshold,
            self.boundary_sensitivity_distance,
            self.high_confidence_boundary_distance,
            self.high_confidence_neighbor_margin,
            self.high_confidence_centroid_distance,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= float(value) <= 1
            for value in proportions
        ):
            raise ValueError(
                "PoetryID evidence and confidence thresholds must be between 0 and 1."
            )
        if self.low_coverage_caution_threshold > self.high_coverage_threshold:
            raise ValueError(
                "The low-coverage caution threshold cannot exceed the high threshold."
            )
        if self.distance_metric != "euclidean":
            raise ValueError("PoetryID Version 1 supports Euclidean distance only.")
        if (
            isinstance(self.affinity_epsilon, bool)
            or not isinstance(self.affinity_epsilon, (int, float))
            or not math.isfinite(float(self.affinity_epsilon))
            or self.affinity_epsilon <= 0
        ):
            raise ValueError("Affinity epsilon must be a positive finite number.")
        if not self.scenario_id.strip():
            raise ValueError("PoetryID requires a stable scenario ID.")

    def to_dict(self) -> dict[str, object]:
        return {
            "threshold_profile": self.threshold_profile.to_dict(),
            "weighting_modes": list(self.weighting_modes),
            "analysis_views": list(self.analysis_views),
            "vad_lexicon_ids": list(self.vad_lexicon_ids),
            "requested_lexical_dimensions": list(
                self.requested_lexical_dimensions
            ),
            "minimum_matched_tokens": self.minimum_matched_tokens,
            "minimum_matched_types": self.minimum_matched_types,
            "minimum_token_coverage": self.minimum_token_coverage,
            "minimum_type_coverage": self.minimum_type_coverage,
            "low_coverage_caution_threshold": (
                self.low_coverage_caution_threshold
            ),
            "high_coverage_threshold": self.high_coverage_threshold,
            "boundary_sensitivity_distance": (
                self.boundary_sensitivity_distance
            ),
            "high_confidence_boundary_distance": (
                self.high_confidence_boundary_distance
            ),
            "high_confidence_neighbor_margin": (
                self.high_confidence_neighbor_margin
            ),
            "high_confidence_centroid_distance": (
                self.high_confidence_centroid_distance
            ),
            "distance_metric": self.distance_metric,
            "affinity_epsilon": self.affinity_epsilon,
            "scenario_id": self.scenario_id,
        }

    @classmethod
    def from_dict(cls, values: Mapping[str, object]) -> PoetryIDConfiguration:
        payload = dict(values)
        profile = payload.pop("threshold_profile", None)
        if not isinstance(profile, Mapping):
            raise ValueError("PoetryID configuration is missing its threshold profile.")
        for field in (
            "weighting_modes",
            "analysis_views",
            "vad_lexicon_ids",
            "requested_lexical_dimensions",
        ):
            if field in payload:
                payload[field] = tuple(payload[field])
        return cls(
            threshold_profile=ThresholdProfile.from_dict(profile),
            **payload,
        )

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"poetry-id-config-v1:{digest}"


@dataclass(frozen=True)
class VadEvidence:
    source_analysis_id: str
    source_lexicon_id: str
    source_lexicon_name: str
    source_lexicon_version: str
    source_adapter_version: str
    source_sha256: str
    analysis_view: str
    weighting_mode: str
    scores: VadScores
    dispersion: VadScores | None
    matched_token_count: int
    eligible_token_count: int
    token_coverage: float | None
    matched_type_count: int
    eligible_type_count: int
    type_coverage: float | None
    exclusions: tuple[str, ...] = ()
    unmatched_terms: tuple[str, ...] = ()
    token_vad_observation_count: int | None = None
    type_vad_observation_count: int | None = None

    def __post_init__(self) -> None:
        if self.weighting_mode not in _SUPPORTED_WEIGHTINGS:
            raise ValueError("Unsupported PoetryID VAD weighting mode.")
        if self.analysis_view not in _SUPPORTED_VIEWS:
            raise ValueError("Unsupported PoetryID VAD analysis view.")
        if not all(
            (
                self.source_analysis_id.strip(),
                self.source_lexicon_id.strip(),
                self.source_lexicon_name.strip(),
                self.source_lexicon_version.strip(),
                self.source_adapter_version.strip(),
            )
        ):
            raise ValueError("VAD evidence is missing source identity.")
        if len(self.source_sha256) != 64:
            raise ValueError("VAD evidence requires a source SHA-256.")
        if any(
            character not in "0123456789abcdefABCDEF"
            for character in self.source_sha256
        ):
            raise ValueError("VAD evidence requires a hexadecimal source SHA-256.")
        counts = (
            self.matched_token_count,
            self.eligible_token_count,
            self.matched_type_count,
            self.eligible_type_count,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in counts
        ):
            raise ValueError("VAD evidence counts must be non-negative integers.")
        for label, value in (
            ("token coverage", self.token_coverage),
            ("type coverage", self.type_coverage),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0 <= float(value) <= 1
            ):
                raise ValueError(f"VAD evidence {label} must be between 0 and 1.")


@dataclass(frozen=True)
class LexicalEvidence:
    dimension_id: str
    source_module: str
    configuration_id: str
    unit: str
    low_max: float
    high_min: float
    low_label: str
    moderate_label: str
    high_label: str
    token_statistics: DescriptiveStatistics | None
    type_statistics: DescriptiveStatistics | None
    token_coverage: float | None
    type_coverage: float | None

    def __post_init__(self) -> None:
        low_max = _number(self.low_max, "lexical-character low_max")
        high_min = _number(self.high_min, "lexical-character high_min")
        if low_max >= high_min:
            raise ValueError(
                "A lexical-character low_max must be below high_min."
            )
        if not all(
            (
                self.dimension_id.strip(),
                self.source_module.strip(),
                self.configuration_id.strip(),
                self.unit.strip(),
                self.low_label.strip(),
                self.moderate_label.strip(),
                self.high_label.strip(),
            )
        ):
            raise ValueError("Lexical-character evidence is incomplete.")


@dataclass(frozen=True)
class PoetryIDCoverage:
    matched_token_count: int
    eligible_token_count: int
    token_coverage: float | None
    matched_type_count: int
    eligible_type_count: int
    type_coverage: float | None
    unmatched_terms: tuple[str, ...]
    exclusions: tuple[str, ...]
    weighted_vad_observation_count: int


@dataclass(frozen=True)
class ArchetypeNeighbor:
    rank: int
    archetype_id: str
    archetype_name: str
    distance: float
    affinity: float


@dataclass(frozen=True)
class ConfidenceAssessment:
    label: str
    centroid_distance: float
    neighbor_margin: float
    boundary_proximity: tuple[tuple[str, float], ...]
    boundary_dimensions: tuple[str, ...]
    coverage_assessment: str
    explanation: str


@dataclass(frozen=True)
class LexicalCharacterResult:
    dimension_id: str
    source_module: str
    configuration_id: str
    weighting_mode: str
    statistics: DescriptiveStatistics
    coverage: float | None
    unit: str
    level: VadLevel
    display_label: str
    low_max: float
    high_min: float


@dataclass(frozen=True)
class PoetryIDAssignment:
    source_analysis_id: str
    source_lexicon_id: str
    source_lexicon_name: str
    source_lexicon_version: str
    source_adapter_version: str
    analysis_view: str
    weighting_mode: str
    vad: VadScores
    dispersion: VadScores | None
    valence_level: VadLevel
    arousal_level: VadLevel
    dominance_level: VadLevel
    categorical_archetype: PoetryArchetype
    nearest_centroid_archetype: PoetryArchetype
    categorical_match: bool
    centroid_distance: float
    neighbors: tuple[ArchetypeNeighbor, ...]
    confidence: ConfidenceAssessment
    coverage: PoetryIDCoverage
    narrative_summary: str


@dataclass(frozen=True)
class PoetryIDUnavailable:
    source_lexicon_id: str
    source_lexicon_name: str
    analysis_view: str
    weighting_mode: str
    reason: str
    message: str


@dataclass(frozen=True)
class PoetryIDAnalysisResult:
    module_result: ModuleResult
    configuration: PoetryIDConfiguration
    status: str
    assignments: tuple[PoetryIDAssignment, ...]
    unavailable: tuple[PoetryIDUnavailable, ...]
    lexical_character: tuple[LexicalCharacterResult, ...]

    def __post_init__(self) -> None:
        if self.status not in {"complete", "partial", "unavailable"}:
            raise ValueError("Unsupported PoetryID result status.")
        if self.status == "unavailable" and self.assignments:
            raise ValueError("An unavailable PoetryID result cannot carry assignments.")


def classify_level(score: float, band: ThresholdBand) -> VadLevel:
    value = _number(score, "VAD score")
    if not 0 <= value <= 1:
        raise ValueError("VAD scores must be on the normalized 0 to 1 scale.")
    if value <= band.low_max:
        return VadLevel.LOW
    if value >= band.high_min:
        return VadLevel.HIGH
    return VadLevel.MODERATE


def _centroid(
    archetype: PoetryArchetype,
    profile: ThresholdProfile,
) -> VadScores:
    return VadScores(
        profile.dimensions["valence"].centroid(archetype.valence_level),
        profile.dimensions["arousal"].centroid(archetype.arousal_level),
        profile.dimensions["dominance"].centroid(archetype.dominance_level),
    )


def _distance(first: VadScores, second: VadScores) -> float:
    return math.sqrt(
        (first.valence - second.valence) ** 2
        + (first.arousal - second.arousal) ** 2
        + (first.dominance - second.dominance) ** 2
    )


def _coverage_assessment(
    coverage: float | None,
    configuration: PoetryIDConfiguration,
) -> str:
    if coverage is None:
        return "unavailable"
    if coverage >= configuration.high_coverage_threshold:
        return "high"
    if coverage >= configuration.low_coverage_caution_threshold:
        return "moderate"
    return "low"


def _narrative(
    assignment: PoetryIDAssignment | None,
    *,
    profile: ThresholdProfile,
    lexical: Sequence[LexicalCharacterResult],
) -> str:
    assert assignment is not None
    neighbors = assignment.neighbors[1:3]
    neighbor_text = " and ".join(row.archetype_name for row in neighbors)
    lexical_rows = [
        row
        for row in lexical
        if row.weighting_mode == assignment.weighting_mode
    ]
    lexical_text = ""
    if lexical_rows:
        labels = ", ".join(row.display_label.casefold() for row in lexical_rows)
        lexical_text = f" Its lexical character shows {labels}."
    return (
        f"Under {profile.name}, the {assignment.weighting_mode}-weighted "
        f"lexical VAD profile is nearest categorically to "
        f"{assignment.categorical_archetype.name}: "
        f"{assignment.valence_level.value} valence, "
        f"{assignment.arousal_level.value} arousal, and "
        f"{assignment.dominance_level.value} dominance. "
        f"{assignment.categorical_archetype.summary} "
        f"The next-nearest centroid profiles are {neighbor_text}."
        f"{lexical_text} This classification summarizes matched normative "
        "lexical patterns and should be interpreted alongside coverage, form, "
        "context, and close reading."
    )


class PoetryIDEngine:
    name = POETRY_ID_MODULE_NAME
    version = POETRY_ID_MODULE_VERSION

    @staticmethod
    def validate_resources() -> tuple:
        return ()

    def analyze(
        self,
        module_input: ModuleInput,
        vad_evidence: Sequence[VadEvidence],
        configuration: PoetryIDConfiguration = PoetryIDConfiguration(),
        *,
        lexical_evidence: Sequence[LexicalEvidence] = (),
    ) -> PoetryIDAnalysisResult:
        selected = [
            row
            for row in vad_evidence
            if row.weighting_mode in configuration.weighting_modes
            and row.analysis_view in configuration.analysis_views
            and (
                not configuration.vad_lexicon_ids
                or row.source_lexicon_id in configuration.vad_lexicon_ids
            )
        ]
        warnings: list[ModuleWarning] = []
        unavailable: list[PoetryIDUnavailable] = []
        assignments: list[PoetryIDAssignment] = []

        lexical_results = self._lexical_character(
            lexical_evidence,
            configuration,
            warnings,
        )
        for evidence in selected:
            outcome = self._assignment(evidence, configuration)
            if isinstance(outcome, PoetryIDUnavailable):
                unavailable.append(outcome)
                warnings.append(
                    ModuleWarning(
                        code=f"poetry_id_{outcome.reason}",
                        message=outcome.message,
                    )
                )
                continue
            assignment, assignment_warnings = outcome
            assignment = replace(
                assignment,
                narrative_summary=_narrative(
                    assignment,
                    profile=configuration.threshold_profile,
                    lexical=lexical_results,
                ),
            )
            assignments.append(assignment)
            warnings.extend(assignment_warnings)

        if not selected:
            unavailable.append(
                PoetryIDUnavailable(
                    source_lexicon_id="",
                    source_lexicon_name="",
                    analysis_view="",
                    weighting_mode="",
                    reason="vad_result_missing",
                    message="PoetryID requires a completed normalized VAD analysis.",
                )
            )
            warnings.append(
                ModuleWarning(
                    code="poetry_id_vad_result_missing",
                    message=(
                        "PoetryID requires a completed normalized VAD analysis."
                    ),
                    severity=WarningSeverity.ERROR,
                )
            )

        status = (
            "unavailable"
            if not assignments
            else "partial"
            if unavailable
            or any(
                warning.code == "poetry_id_lexical_dimension_unavailable"
                for warning in warnings
            )
            else "complete"
        )
        module_result = self._module_result(
            module_input,
            configuration,
            assignments,
            unavailable,
            lexical_results,
            warnings,
            selected,
            status,
        )
        return PoetryIDAnalysisResult(
            module_result=module_result,
            configuration=configuration,
            status=status,
            assignments=tuple(assignments),
            unavailable=tuple(unavailable),
            lexical_character=tuple(lexical_results),
        )

    def _assignment(
        self,
        evidence: VadEvidence,
        configuration: PoetryIDConfiguration,
    ) -> (
        tuple[PoetryIDAssignment, tuple[ModuleWarning, ...]]
        | PoetryIDUnavailable
    ):
        values = tuple(
            getattr(evidence.scores, dimension) for dimension in _DIMENSIONS
        )
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 1
            for value in values
        ):
            return PoetryIDUnavailable(
                evidence.source_lexicon_id,
                evidence.source_lexicon_name,
                evidence.analysis_view,
                evidence.weighting_mode,
                "invalid_vad_values",
                "PoetryID received missing or invalid normalized VAD means.",
            )
        if evidence.weighting_mode == "token":
            count = (
                evidence.token_vad_observation_count
                if evidence.token_vad_observation_count is not None
                else evidence.matched_token_count
            )
            minimum = configuration.minimum_matched_tokens
            coverage = evidence.token_coverage
            minimum_coverage = configuration.minimum_token_coverage
            count_reason = "insufficient_matched_tokens"
            count_message = (
                f"PoetryID requires at least {minimum} matched token "
                "observations for the token-weighted profile."
            )
        else:
            count = (
                evidence.type_vad_observation_count
                if evidence.type_vad_observation_count is not None
                else evidence.matched_type_count
            )
            minimum = configuration.minimum_matched_types
            coverage = evidence.type_coverage
            minimum_coverage = configuration.minimum_type_coverage
            count_reason = "insufficient_matched_types"
            count_message = (
                f"PoetryID requires at least {minimum} matched types for the "
                "type-weighted profile."
            )
        if count < minimum:
            return PoetryIDUnavailable(
                evidence.source_lexicon_id,
                evidence.source_lexicon_name,
                evidence.analysis_view,
                evidence.weighting_mode,
                count_reason,
                count_message,
            )
        if coverage is None or coverage < minimum_coverage:
            return PoetryIDUnavailable(
                evidence.source_lexicon_id,
                evidence.source_lexicon_name,
                evidence.analysis_view,
                evidence.weighting_mode,
                "insufficient_vad_coverage",
                (
                    "PoetryID is unavailable because VAD coverage is below the "
                    f"configured {minimum_coverage:.0%} minimum."
                ),
            )

        profile = configuration.threshold_profile
        levels = tuple(
            classify_level(
                getattr(evidence.scores, dimension),
                profile.dimensions[dimension],
            )
            for dimension in _DIMENSIONS
        )
        categorical = resolve_archetype(*levels)
        distances = [
            (archetype, _distance(evidence.scores, _centroid(archetype, profile)))
            for archetype in ARCHETYPES
        ]
        distances.sort(key=lambda row: (row[1], row[0].archetype_id))
        similarities = [
            1 / (distance + configuration.affinity_epsilon)
            for _archetype, distance in distances
        ]
        similarity_total = sum(similarities)
        neighbors = tuple(
            ArchetypeNeighbor(
                rank=index,
                archetype_id=archetype.archetype_id,
                archetype_name=archetype.name,
                distance=distance,
                affinity=similarity / similarity_total,
            )
            for index, ((archetype, distance), similarity) in enumerate(
                zip(distances, similarities, strict=True),
                start=1,
            )
        )
        nearest = distances[0][0]
        categorical_distance = next(
            distance
            for archetype, distance in distances
            if archetype.archetype_id == categorical.archetype_id
        )
        margin = distances[1][1] - distances[0][1]
        boundary = tuple(
            (
                dimension,
                min(
                    abs(
                        getattr(evidence.scores, dimension)
                        - profile.dimensions[dimension].low_max
                    ),
                    abs(
                        getattr(evidence.scores, dimension)
                        - profile.dimensions[dimension].high_min
                    ),
                ),
            )
            for dimension in _DIMENSIONS
        )
        boundary_dimensions = tuple(
            dimension
            for dimension, proximity in boundary
            if proximity <= configuration.boundary_sensitivity_distance
        )
        coverage_label = _coverage_assessment(coverage, configuration)
        categorical_match = nearest.archetype_id == categorical.archetype_id
        if boundary_dimensions or not categorical_match:
            confidence_label = "boundary_sensitive"
        elif coverage_label == "low":
            confidence_label = "low_confidence"
        elif (
            categorical_distance
            <= configuration.high_confidence_centroid_distance
            and margin >= configuration.high_confidence_neighbor_margin
            and min(value for _dimension, value in boundary)
            >= configuration.high_confidence_boundary_distance
            and coverage_label == "high"
        ):
            confidence_label = "high_confidence"
        else:
            confidence_label = "moderate_confidence"
        explanation_parts = []
        if boundary_dimensions:
            explanation_parts.append(
                "The result is close to the "
                + ", ".join(boundary_dimensions)
                + " threshold boundary."
            )
        if not categorical_match:
            explanation_parts.append(
                f"The categorical profile differs from the nearest centroid, "
                f"{nearest.name}; both are retained."
            )
        if coverage_label == "low":
            explanation_parts.append(
                "VAD coverage is low enough to require added caution."
            )
        if not explanation_parts:
            explanation_parts.append(
                f"The next-nearest centroid is {neighbors[1].archetype_name}; "
                f"the distance margin is {margin:.3f}."
            )
        confidence = ConfidenceAssessment(
            label=confidence_label,
            centroid_distance=categorical_distance,
            neighbor_margin=margin,
            boundary_proximity=boundary,
            boundary_dimensions=boundary_dimensions,
            coverage_assessment=coverage_label,
            explanation=" ".join(explanation_parts),
        )
        assignment = PoetryIDAssignment(
            source_analysis_id=evidence.source_analysis_id,
            source_lexicon_id=evidence.source_lexicon_id,
            source_lexicon_name=evidence.source_lexicon_name,
            source_lexicon_version=evidence.source_lexicon_version,
            source_adapter_version=evidence.source_adapter_version,
            analysis_view=evidence.analysis_view,
            weighting_mode=evidence.weighting_mode,
            vad=evidence.scores,
            dispersion=evidence.dispersion,
            valence_level=levels[0],
            arousal_level=levels[1],
            dominance_level=levels[2],
            categorical_archetype=categorical,
            nearest_centroid_archetype=nearest,
            categorical_match=categorical_match,
            centroid_distance=categorical_distance,
            neighbors=neighbors,
            confidence=confidence,
            coverage=PoetryIDCoverage(
                evidence.matched_token_count,
                evidence.eligible_token_count,
                evidence.token_coverage,
                evidence.matched_type_count,
                evidence.eligible_type_count,
                evidence.type_coverage,
                evidence.unmatched_terms,
                evidence.exclusions,
                count,
            ),
            narrative_summary="",
        )
        outcome_warnings = []
        if boundary_dimensions:
            outcome_warnings.append(
                ModuleWarning(
                    code="poetry_id_boundary_sensitive",
                    message=confidence.explanation,
                )
            )
        if not categorical_match:
            outcome_warnings.append(
                ModuleWarning(
                    code="poetry_id_categorical_centroid_discrepancy",
                    message=(
                        "The categorical and nearest-centroid profiles differ. "
                        "Both results are retained."
                    ),
                )
            )
        if coverage_label == "low":
            outcome_warnings.append(
                ModuleWarning(
                    code="poetry_id_low_evidentiary_coverage",
                    message=(
                        "PoetryID was generated with low VAD coverage and "
                        "requires cautious interpretation."
                    ),
                )
            )
        return assignment, tuple(outcome_warnings)

    @staticmethod
    def _lexical_character(
        evidence: Sequence[LexicalEvidence],
        configuration: PoetryIDConfiguration,
        warnings: list[ModuleWarning],
    ) -> list[LexicalCharacterResult]:
        by_dimension = {row.dimension_id: row for row in evidence}
        rows = []
        for dimension in configuration.requested_lexical_dimensions:
            item = by_dimension.get(dimension)
            if item is None:
                warnings.append(
                    ModuleWarning(
                        code="poetry_id_lexical_dimension_unavailable",
                        message=(
                            f"{dimension.replace('_', ' ').title()} evidence "
                            "was unavailable. The VAD archetype is unchanged."
                        ),
                        severity=WarningSeverity.INFORMATION,
                    )
                )
                continue
            for weighting, statistics, coverage in (
                ("token", item.token_statistics, item.token_coverage),
                ("type", item.type_statistics, item.type_coverage),
            ):
                if statistics is None or statistics.mean is None:
                    continue
                if statistics.mean <= item.low_max:
                    level = VadLevel.LOW
                elif statistics.mean >= item.high_min:
                    level = VadLevel.HIGH
                else:
                    level = VadLevel.MODERATE
                label = {
                    VadLevel.LOW: item.low_label,
                    VadLevel.MODERATE: item.moderate_label,
                    VadLevel.HIGH: item.high_label,
                }[level]
                rows.append(
                    LexicalCharacterResult(
                        dimension_id=item.dimension_id,
                        source_module=item.source_module,
                        configuration_id=item.configuration_id,
                        weighting_mode=weighting,
                        statistics=statistics,
                        coverage=coverage,
                        unit=item.unit,
                        level=level,
                        display_label=label,
                        low_max=item.low_max,
                        high_min=item.high_min,
                    )
                )
        return rows

    @staticmethod
    def _module_result(
        module_input: ModuleInput,
        configuration: PoetryIDConfiguration,
        assignments: Sequence[PoetryIDAssignment],
        unavailable: Sequence[PoetryIDUnavailable],
        lexical: Sequence[LexicalCharacterResult],
        warnings: Sequence[ModuleWarning],
        selected_evidence: Sequence[VadEvidence],
        status: str,
    ) -> ModuleResult:
        metrics = [
            ModuleMetric(
                metric_id="poetry_id.result_status",
                value=status,
                layer=ResultLayer.INTERPRETATION,
                unit="status label",
                denominator="selected VAD sources, views, and weightings",
                note="Unavailable and partial states remain explicit.",
            )
        ]
        for row in assignments:
            scope_id = f"{row.source_lexicon_id}:{row.analysis_view}"
            common = {
                "scope": "document",
                "scope_id": scope_id,
                "weighting": row.weighting_mode,
            }
            metrics.extend(
                (
                    ModuleMetric(
                        "poetry_id.source_vad_result_id",
                        row.source_analysis_id,
                        ResultLayer.DIRECT_OBSERVATION,
                        unit="stable result ID",
                        denominator="completed source-specific VAD analysis",
                        **common,
                    ),
                    *(
                        ModuleMetric(
                            f"poetry_id.{dimension}",
                            getattr(row.vad, dimension),
                            ResultLayer.DIRECT_OBSERVATION,
                            unit="normalized 0-1",
                            denominator=(
                                f"{row.coverage.weighted_vad_observation_count} "
                                f"{row.weighting_mode}-weighted normalized VAD "
                                "observations"
                            ),
                            **common,
                        )
                        for dimension in _DIMENSIONS
                    ),
                    ModuleMetric(
                        "poetry_id.categorical_archetype_id",
                        row.categorical_archetype.archetype_id,
                        ResultLayer.INTERPRETATION,
                        unit="canonical profile ID",
                        denominator="three classified VAD levels",
                        note="Nearest candidate profile under the selected thresholds.",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.categorical_archetype_name",
                        row.categorical_archetype.name,
                        ResultLayer.INTERPRETATION,
                        unit="display label",
                        denominator="three classified VAD levels",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.nearest_centroid_archetype_id",
                        row.nearest_centroid_archetype.archetype_id,
                        ResultLayer.COMPUTED_SUMMARY,
                        unit="canonical profile ID",
                        denominator="Euclidean distance across all 27 centroids",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.categorical_centroid_match",
                        row.categorical_match,
                        ResultLayer.COMPUTED_SUMMARY,
                        unit="boolean",
                        denominator="categorical and nearest-centroid assignments",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.centroid_distance",
                        row.centroid_distance,
                        ResultLayer.COMPUTED_SUMMARY,
                        unit="normalized Euclidean distance",
                        denominator="assigned categorical centroid",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.neighbor_margin",
                        row.confidence.neighbor_margin,
                        ResultLayer.COMPUTED_SUMMARY,
                        unit="normalized Euclidean distance",
                        denominator="nearest minus second-nearest centroid distance",
                        **common,
                    ),
                    ModuleMetric(
                        "poetry_id.confidence_label",
                        row.confidence.label,
                        ResultLayer.INTERPRETATION,
                        unit="rule-based evidence label",
                        denominator="documented boundary, distance, margin, and coverage rules",
                        note="This label is not a probability.",
                        **common,
                    ),
                )
            )
            for neighbor in row.neighbors[:3]:
                metrics.extend(
                    (
                        ModuleMetric(
                            "poetry_id.neighbor_archetype_id",
                            neighbor.archetype_id,
                            ResultLayer.COMPUTED_SUMMARY,
                            scope="neighbor",
                            scope_id=f"{scope_id}:{row.weighting_mode}:{neighbor.rank}",
                            unit="canonical profile ID",
                            weighting=row.weighting_mode,
                            denominator=f"rank {neighbor.rank} of 27 centroids",
                        ),
                        ModuleMetric(
                            "poetry_id.neighbor_distance",
                            neighbor.distance,
                            ResultLayer.COMPUTED_SUMMARY,
                            scope="neighbor",
                            scope_id=f"{scope_id}:{row.weighting_mode}:{neighbor.rank}",
                            unit="normalized Euclidean distance",
                            weighting=row.weighting_mode,
                            denominator=f"rank {neighbor.rank} of 27 centroids",
                        ),
                        ModuleMetric(
                            "poetry_id.neighbor_affinity",
                            neighbor.affinity,
                            ResultLayer.COMPUTED_SUMMARY,
                            scope="neighbor",
                            scope_id=f"{scope_id}:{row.weighting_mode}:{neighbor.rank}",
                            unit="relative affinity",
                            weighting=row.weighting_mode,
                            denominator="inverse-distance similarity normalized across all 27 profiles",
                            note="Relative affinity is not a probability.",
                        ),
                    )
                )
        for row in lexical:
            metrics.extend(
                (
                    ModuleMetric(
                        f"poetry_id.lexical_character.{row.dimension_id}.mean",
                        row.statistics.mean,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope="lexical_character",
                        scope_id=row.dimension_id,
                        unit=row.unit,
                        weighting=row.weighting_mode,
                        denominator=f"{row.statistics.count} included observations",
                    ),
                    ModuleMetric(
                        f"poetry_id.lexical_character.{row.dimension_id}.median",
                        row.statistics.median,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope="lexical_character",
                        scope_id=row.dimension_id,
                        unit=row.unit,
                        weighting=row.weighting_mode,
                        denominator=f"{row.statistics.count} included observations",
                    ),
                    ModuleMetric(
                        f"poetry_id.lexical_character.{row.dimension_id}.level",
                        row.level.value,
                        ResultLayer.INTERPRETATION,
                        scope="lexical_character",
                        scope_id=row.dimension_id,
                        unit="orientation level",
                        weighting=row.weighting_mode,
                        denominator=(
                            f"low <= {row.low_max:g}; high >= {row.high_min:g}"
                        ),
                    ),
                )
            )

        coverage_rows = []
        seen_coverage = set()
        for row in selected_evidence:
            scope_id = f"{row.source_lexicon_id}:{row.analysis_view}"
            if scope_id in seen_coverage:
                continue
            seen_coverage.add(scope_id)
            coverage_rows.extend(
                (
                    ModuleCoverage.from_counts(
                        coverage_id="poetry_id.vad_token_coverage",
                        eligible_count=row.eligible_token_count,
                        matched_count=row.matched_token_count,
                        unit="eligible lexical token positions",
                        scope_id=scope_id,
                        unmatched_items=row.unmatched_terms,
                        note="Inherited unchanged from the source-specific VAD result.",
                    ),
                    ModuleCoverage.from_counts(
                        coverage_id="poetry_id.vad_type_coverage",
                        eligible_count=row.eligible_type_count,
                        matched_count=row.matched_type_count,
                        unit="eligible normalized lexical types",
                        scope_id=scope_id,
                        unmatched_items=row.unmatched_terms,
                        note="Inherited unchanged from the source-specific VAD result.",
                    ),
                )
            )

        source_by_id = {}
        for row in selected_evidence:
            source_by_id.setdefault(
                row.source_lexicon_id,
                ResourceProvenance(
                    resource_id=row.source_lexicon_id,
                    display_name=row.source_lexicon_name,
                    version=row.source_lexicon_version,
                    source_sha256=row.source_sha256,
                    adapter_version=row.source_adapter_version,
                ),
            )
        dependency_signature = "|".join(
            sorted(
                f"{row.source_analysis_id}:{row.analysis_view}:{row.weighting_mode}"
                for row in selected_evidence
            )
        )
        result_signature = "|".join(
            (
                module_input.document.text_version_id,
                configuration.configuration_id,
                dependency_signature,
                status,
            )
        )
        return ModuleResult(
            result_id="poetry-id-result-v1:"
            + hashlib.sha256(result_signature.encode("utf-8")).hexdigest()[:24],
            module_name=POETRY_ID_MODULE_NAME,
            module_version=POETRY_ID_MODULE_VERSION,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=tuple(metrics),
            coverage=tuple(coverage_rows),
            warnings=tuple(warnings),
            provenance=ModuleProvenance(
                software_version=__version__,
                source_text_sha256=module_input.document.text_sha256,
                preprocessing_recipe=module_input.preprocessing.recipe_id,
                pipeline_name=module_input.preprocessing.pipeline_name,
                pipeline_version=module_input.preprocessing.pipeline_version,
                configuration_id=configuration.configuration_id,
                scenario_id=configuration.scenario_id,
                lookup_policy=(
                    "Consumes completed source-specific normalized VAD means; "
                    "does not load or match a lexicon independently."
                ),
                inclusion_policy=(
                    f"weightings={','.join(configuration.weighting_modes)}; "
                    f"views={','.join(configuration.analysis_views)}; "
                    f"minimum_tokens={configuration.minimum_matched_tokens}; "
                    f"minimum_types={configuration.minimum_matched_types}; "
                    f"threshold_profile={configuration.threshold_profile.profile_id}"
                ),
                resources=tuple(source_by_id.values()),
            ),
        )


__all__ = [
    "DEFAULT_THRESHOLD_PROFILE",
    "LexicalCharacterResult",
    "LexicalEvidence",
    "POETRY_ID_MODULE_NAME",
    "POETRY_ID_MODULE_VERSION",
    "PoetryIDAnalysisResult",
    "PoetryIDAssignment",
    "PoetryIDConfiguration",
    "PoetryIDEngine",
    "PoetryIDUnavailable",
    "SUPPORTED_VAD_LEXICON_IDS",
    "ThresholdBand",
    "ThresholdProfile",
    "VadEvidence",
    "classify_level",
]
