"""Canonical configurable profile rows for completed workspace analyses."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Iterable, Mapping, Sequence

from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileCoverage,
)
from versevad.application import WorkspaceAnalysis
from versevad.models import MatchSelection, Phase2AnalysisResult, TokenRecord
from versevad.metric_capabilities import metric_capabilities
from versevad.profile_aggregation import (
    ScalarEvidence,
    ScalarProfileSummary,
    aggregate_scalar_evidence,
    token_audit_scalar_profiles,
    vad_profile_summaries,
)


WORKSPACE_PROFILE_ROWS_VERSION = "workspace-profile-rows-v4"
_PROFILE_CACHE: OrderedDict[tuple[str, ...], tuple["WorkspaceProfileMetric", ...]] = OrderedDict()
_PROFILE_CACHE_LOCK = RLock()
_PROFILE_CACHE_LIMIT = 16


@dataclass(frozen=True)
class WorkspaceProfileMetric:
    module_id: str
    source_id: str
    source_label: str
    metric_id: str
    metric_label: str
    profile: AnalysisProfile
    value: float | None
    median: float | None
    population_standard_deviation: float | None
    first_quartile: float | None
    third_quartile: float | None
    minimum: float | None
    maximum: float | None
    cumulative_value: float | None
    value_per_100_observations: float | None
    above_midpoint_load: float | None
    below_midpoint_load: float | None
    net_midpoint_load: float | None
    absolute_midpoint_load: float | None
    average_deviation_from_mean: float | None
    observation_count: int
    coverage: ProfileCoverage
    unit: str


def _tokens(workspace: WorkspaceAnalysis) -> tuple[TokenRecord, ...]:
    if workspace.poem_document is not None:
        return tuple(workspace.poem_document.tokens)
    return tuple(workspace.results[0].tokens) if workspace.results else ()


def _active_stopwords(workspace: WorkspaceAnalysis) -> tuple[str, ...]:
    return next(
        (
            tuple(result.stopword_policy.active_words)
            for result in workspace.results
            if result.stopword_policy is not None
        ),
        (),
    )


def _rows_from_summaries(
    *,
    module_id: str,
    source_id: str,
    source_label: str,
    metric_id: str,
    metric_label: str,
    summaries: Mapping[AnalysisProfile, ScalarProfileSummary],
    unit: str,
    include_normalized_midpoint_loads: bool = False,
    coverage_by_profile: Mapping[AnalysisProfile, ScalarProfileSummary] | None = None,
) -> tuple[WorkspaceProfileMetric, ...]:
    capabilities = metric_capabilities(module_id)
    return tuple(
        WorkspaceProfileMetric(
            module_id=module_id,
            source_id=source_id,
            source_label=source_label,
            metric_id=metric_id,
            metric_label=metric_label,
            profile=profile,
            value=summary.statistics.mean,
            median=summary.statistics.median,
            population_standard_deviation=(
                summary.statistics.population_standard_deviation
                if capabilities.supports_dispersion
                else None
            ),
            first_quartile=(
                summary.statistics.first_quartile
                if capabilities.supports_dispersion
                else None
            ),
            third_quartile=(
                summary.statistics.third_quartile
                if capabilities.supports_dispersion
                else None
            ),
            minimum=summary.statistics.minimum,
            maximum=summary.statistics.maximum,
            cumulative_value=(
                summary.cumulative_value
                if capabilities.supports_raw_accumulation
                else None
            ),
            value_per_100_observations=(
                summary.value_per_100_observations
                if capabilities.supports_normalized_accumulation
                else None
            ),
            above_midpoint_load=(
                summary.above_midpoint_load
                if include_normalized_midpoint_loads
                else None
            ),
            below_midpoint_load=(
                summary.below_midpoint_load
                if include_normalized_midpoint_loads
                else None
            ),
            net_midpoint_load=(
                summary.net_midpoint_load
                if include_normalized_midpoint_loads
                else None
            ),
            absolute_midpoint_load=(
                summary.absolute_midpoint_load
                if include_normalized_midpoint_loads
                else None
            ),
            average_deviation_from_mean=summary.average_deviation_from_mean,
            observation_count=summary.statistics.count,
            coverage=(
                coverage_by_profile[profile].coverage
                if coverage_by_profile is not None
                else summary.coverage
            ),
            unit=unit,
        )
        for profile, summary in summaries.items()
    )


def _resource_coverage_summaries(
    result: Phase2AnalysisResult,
) -> Mapping[AnalysisProfile, ScalarProfileSummary]:
    """Return resource-wide coverage independently of any metric category.

    Categorical associations and emotion-intensity pairs are subsets of the
    entries matched by their resource. Their proportions and means are metric
    values, not resource-coverage rates. Building this shared coverage layer
    from every retained match keeps those concepts separate in the UI,
    persistence layer, and schema-v3 exports.
    """

    evidence = tuple(
        ScalarEvidence(
            token_ids=tuple(match.token_ids),
            value=1.0,
            type_identity=(
                match.matched_lookup_form
                or match.matched_term
                or match.match_id
            ).casefold(),
            phrase=len(match.token_ids) > 1,
        )
        for match in result.matches
        if match.selection is MatchSelection.INCLUDED and match.included
    )
    return aggregate_scalar_evidence(
        tokens=result.tokens,
        observations=evidence,
        active_stopwords=_active_stopwords_for_result(result),
        type_identity_rule="matched_resource_entry",
    )


def _active_stopwords_for_result(
    result: Phase2AnalysisResult,
) -> tuple[str, ...]:
    return (
        tuple(result.stopword_policy.active_words)
        if result.stopword_policy is not None
        else ()
    )


def _vad_rows(result: Phase2AnalysisResult) -> tuple[WorkspaceProfileMetric, ...]:
    if result.vad_summary is None:
        return ()
    summaries = vad_profile_summaries(result)
    return tuple(
        row
        for dimension, dimension_summaries in summaries.items()
        for row in _rows_from_summaries(
            module_id="vad",
            source_id=result.lexicon_metadata.lexicon_id,
            source_label=result.lexicon_metadata.display_name,
            metric_id=f"{dimension}_mean",
            metric_label=f"Mean normative {dimension}",
            summaries=dimension_summaries,
            unit="normalized 0-1",
            include_normalized_midpoint_loads=True,
        )
    )


def _affect_category_rows(
    result: Phase2AnalysisResult,
) -> tuple[WorkspaceProfileMetric, ...]:
    categories = sorted(
        {
            category
            for match in result.matches
            if match.selection is MatchSelection.INCLUDED and match.included
            for category in match.associations
        }
    )
    rows: list[WorkspaceProfileMetric] = []
    active_stopwords = _active_stopwords_for_result(result)
    resource_coverage = _resource_coverage_summaries(result)
    for category in categories:
        evidence = tuple(
            ScalarEvidence(
                token_ids=tuple(match.token_ids),
                value=1.0,
                type_identity=(
                    f"{match.matched_lookup_form or match.matched_term or match.match_id}:"
                    f"{category}"
                ).casefold(),
                phrase=len(match.token_ids) > 1,
            )
            for match in result.matches
            if match.selection is MatchSelection.INCLUDED
            and match.included
            and category in match.associations
        )
        summaries = aggregate_scalar_evidence(
            tokens=result.tokens,
            observations=evidence,
            active_stopwords=active_stopwords,
            type_identity_rule="matched_entry_category",
        )
        for profile, summary in summaries.items():
            proportion = (
                summary.coverage.token_coverage
                if profile.weighting is AggregationWeighting.TOKEN
                else summary.coverage.type_coverage
            )
            rows.append(
                WorkspaceProfileMetric(
                    module_id="emotion_association",
                    source_id=result.lexicon_metadata.lexicon_id,
                    source_label=result.lexicon_metadata.display_name,
                    metric_id=f"{category}_association",
                    metric_label=f"{category.title()} association",
                    profile=profile,
                    value=proportion,
                    median=None,
                    population_standard_deviation=None,
                    first_quartile=None,
                    third_quartile=None,
                    minimum=None,
                    maximum=None,
                    cumulative_value=None,
                    value_per_100_observations=None,
                    above_midpoint_load=None,
                    below_midpoint_load=None,
                    net_midpoint_load=None,
                    absolute_midpoint_load=None,
                    average_deviation_from_mean=None,
                    observation_count=summary.statistics.count,
                    coverage=resource_coverage[profile].coverage,
                    unit="proportion of eligible lexical evidence",
                )
            )
    return tuple(rows)


def _affect_intensity_rows(
    result: Phase2AnalysisResult,
) -> tuple[WorkspaceProfileMetric, ...]:
    categories = sorted(
        {
            category
            for match in result.matches
            if match.selection is MatchSelection.INCLUDED and match.included
            for category, _value in match.intensities
        }
    )
    active_stopwords = _active_stopwords_for_result(result)
    resource_coverage = _resource_coverage_summaries(result)
    output: list[WorkspaceProfileMetric] = []
    for category in categories:
        evidence = tuple(
            ScalarEvidence(
                token_ids=tuple(match.token_ids),
                value=float(dict(match.intensities)[category]),
                type_identity=(
                    f"{match.matched_lookup_form or match.matched_term or match.match_id}:"
                    f"{category}"
                ).casefold(),
                phrase=len(match.token_ids) > 1,
            )
            for match in result.matches
            if match.selection is MatchSelection.INCLUDED
            and match.included
            and category in dict(match.intensities)
        )
        output.extend(
            _rows_from_summaries(
                module_id="emotion_intensity",
                source_id=result.lexicon_metadata.lexicon_id,
                source_label=result.lexicon_metadata.display_name,
                metric_id=f"{category}_intensity",
                metric_label=f"Mean {category.title()} intensity",
                summaries=aggregate_scalar_evidence(
                    tokens=result.tokens,
                    observations=evidence,
                    active_stopwords=active_stopwords,
                    type_identity_rule="matched_entry_category",
                ),
                unit="source intensity scale",
                coverage_by_profile=resource_coverage,
            )
        )
    return tuple(output)


def _sensorimotor_rows(
    workspace: WorkspaceAnalysis,
    tokens: Sequence[TokenRecord],
    active_stopwords: Iterable[str],
) -> tuple[WorkspaceProfileMetric, ...]:
    result = workspace.sensorimotor
    if result is None:
        return ()
    dimension_ids = tuple(asdict(result.observations[0].means)) if result.observations else ()
    output: list[WorkspaceProfileMetric] = []
    for dimension in dimension_ids:
        evidence = tuple(
            ScalarEvidence(
                token_ids=tuple(observation.token_ids),
                value=float(getattr(observation.means, dimension)),
                type_identity=observation.matched_lookup_form.casefold(),
                phrase=bool(observation.source_is_multiword),
            )
            for observation in result.observations
        )
        output.extend(
            _rows_from_summaries(
                module_id="sensorimotor",
                source_id=result.resource_status.resource_id,
                source_label=result.resource_status.display_name,
                metric_id=dimension,
                metric_label=dimension.replace("_", " ").title(),
                summaries=aggregate_scalar_evidence(
                    tokens=tokens,
                    observations=evidence,
                    active_stopwords=active_stopwords,
                    type_identity_rule="matched_resource_entry",
                ),
                unit="Lancaster strength rating",
            )
        )
    return tuple(output)


def _workspace_profile_metrics_uncached(
    workspace: WorkspaceAnalysis,
) -> tuple[WorkspaceProfileMetric, ...]:
    """Materialize every compatible profile from one completed analysis."""

    tokens = _tokens(workspace)
    active_stopwords = _active_stopwords(workspace)
    rows: list[WorkspaceProfileMetric] = []
    for result in workspace.results:
        rows.extend(_vad_rows(result))
        rows.extend(_affect_category_rows(result))
        rows.extend(_affect_intensity_rows(result))

    optional_specs = (
        (
            "concreteness",
            workspace.concreteness,
            "rating",
            "Mean concreteness",
            "source 1-5",
        ),
        (
            "frequency",
            workspace.frequency,
            "zipf_value",
            "Mean SUBTLEX Zipf frequency",
            "Zipf",
        ),
        (
            "aoa",
            workspace.aoa,
            "mean_age",
            "Mean age of acquisition",
            "normative age in years",
        ),
    )
    for module_id, result, value_attribute, label, unit in optional_specs:
        if result is None:
            continue
        summaries = token_audit_scalar_profiles(
            tokens=tokens,
            audit_rows=result.token_audit,
            value_attribute=value_attribute,
            active_stopwords=active_stopwords,
        )
        status = result.resource_status
        rows.extend(
            _rows_from_summaries(
                module_id=module_id,
                source_id=status.resource_id,
                source_label=status.display_name,
                metric_id=f"{module_id}_mean",
                metric_label=label,
                summaries=summaries,
                unit=unit,
            )
        )

    rows.extend(_sensorimotor_rows(workspace, tokens, active_stopwords))
    if workspace.lexical_style is not None:
        summaries = token_audit_scalar_profiles(
            tokens=tokens,
            audit_rows=workspace.lexical_style.token_audit,
            value_attribute="alphabetic_character_count",
            type_identity_attributes=("normalized_surface_type",),
            active_stopwords=active_stopwords,
            type_identity_rule="normalized_surface",
        )
        rows.extend(
            _rows_from_summaries(
                module_id="word_length",
                source_id="versevad_lexical_style",
                source_label="VerseVAD lexical style",
                metric_id="mean_word_length",
                metric_label="Mean alphabetic characters per word",
                summaries=summaries,
                unit="alphabetic characters",
            )
        )
    return tuple(rows)


def _cache_key(workspace: WorkspaceAnalysis) -> tuple[str, ...]:
    optional = (
        workspace.concreteness,
        workspace.sensorimotor,
        workspace.frequency,
        workspace.aoa,
        workspace.lexical_style,
    )
    return (
        WORKSPACE_PROFILE_ROWS_VERSION,
        workspace.document.text_version_id,
        *(result.analysis_id for result in workspace.results),
        *(
            item.module_result.result_id if item is not None else ""
            for item in optional
        ),
    )


def workspace_profile_metrics(
    workspace: WorkspaceAnalysis,
) -> tuple[WorkspaceProfileMetric, ...]:
    """Return cached all-profile rows for one immutable completed analysis."""

    key = _cache_key(workspace)
    with _PROFILE_CACHE_LOCK:
        cached = _PROFILE_CACHE.get(key)
        if cached is not None:
            _PROFILE_CACHE.move_to_end(key)
            return cached
    rows = _workspace_profile_metrics_uncached(workspace)
    with _PROFILE_CACHE_LOCK:
        _PROFILE_CACHE[key] = rows
        _PROFILE_CACHE.move_to_end(key)
        while len(_PROFILE_CACHE) > _PROFILE_CACHE_LIMIT:
            _PROFILE_CACHE.popitem(last=False)
    return rows


__all__ = [
    "WORKSPACE_PROFILE_ROWS_VERSION",
    "WorkspaceProfileMetric",
    "workspace_profile_metrics",
]
