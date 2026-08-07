"""Adapters from completed VerseVAD module results into PoetryID evidence.

These functions never load resources or rematch text. They expose values,
coverage, and provenance already calculated by the shared analysis modules.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

from versevad.analysis.statistics import descriptive_statistics
from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    token_is_in_scope,
)
from versevad.lexical_semantic.aoa import AoAAnalysisResult
from versevad.lexical_semantic.concreteness import ConcretenessAnalysisResult
from versevad.lexical_semantic.frequency import FrequencyAnalysisResult
from versevad.models import (
    DescriptiveStatistics,
    MatchSelection,
    Phase2AnalysisResult,
    VadScores,
    WeightedVadStatistics,
)
from versevad.poetry_id.engine import (
    LexicalEvidence,
    PoetryIDConfiguration,
    VadEvidence,
)
from versevad.profile_aggregation import vad_profile_summaries


def _scores(statistics: WeightedVadStatistics) -> VadScores:
    means = tuple(
        statistics.by_dimension()[name].mean
        for name in ("valence", "arousal", "dominance")
    )
    return VadScores(
        *(math.nan if value is None else float(value) for value in means)
    )


def _dispersion(statistics: WeightedVadStatistics) -> VadScores | None:
    values = tuple(
        statistics.by_dimension()[name].population_standard_deviation
        for name in ("valence", "arousal", "dominance")
    )
    if any(value is None for value in values):
        return None
    return VadScores(*(float(value) for value in values))


def _unmatched_terms(
    result: Phase2AnalysisResult,
    analysis_view: str,
    limit: int = 10,
) -> tuple[str, ...]:
    tokens = {row.token_id: row for row in result.tokens}
    active_stopwords = (
        tuple(result.stopword_policy.active_words)
        if result.stopword_policy is not None
        else ()
    )
    scope = {
        "all_matched": LexicalScope.ALL_LEXICAL,
        "stopwords_excluded": LexicalScope.STOPWORD_EXCLUDED,
        "content_words": LexicalScope.CONTENT_WORDS,
    }[analysis_view]
    counts: Counter[str] = Counter()
    for match in result.matches:
        if match.selection != MatchSelection.UNMATCHED:
            continue
        for token_id in match.token_ids:
            token = tokens.get(token_id)
            if token is None:
                continue
            if not token_is_in_scope(
                token,
                scope,
                active_stopwords=active_stopwords,
            ):
                continue
            counts[token.normalized_form] += 1
    return tuple(
        term for term, _count in sorted(
            counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )[:limit]
    )


def vad_evidence_from_results(
    results: Sequence[Phase2AnalysisResult],
    configuration: PoetryIDConfiguration,
) -> tuple[VadEvidence, ...]:
    """Expose selected, normalized VAD means without recalculating VAD."""

    rows: list[VadEvidence] = []
    for result in results:
        if result.vad_summary is None:
            continue
        if (
            configuration.vad_lexicon_ids
            and result.lexicon_metadata.lexicon_id
            not in configuration.vad_lexicon_ids
        ):
            continue
        profile_dimensions = vad_profile_summaries(result)
        for analysis_view in configuration.analysis_views:
            scope = {
                "all_matched": LexicalScope.ALL_LEXICAL,
                "stopwords_excluded": LexicalScope.STOPWORD_EXCLUDED,
                "content_words": LexicalScope.CONTENT_WORDS,
            }[analysis_view]
            for weighting_mode, weighting in (
                ("token", AggregationWeighting.TOKEN),
                ("type", AggregationWeighting.TYPE),
            ):
                if weighting_mode not in configuration.weighting_modes:
                    continue
                profile = AnalysisProfile(scope, weighting)
                summaries = {
                    dimension: profile_dimensions[dimension][profile]
                    for dimension in ("valence", "arousal", "dominance")
                }
                statistics = WeightedVadStatistics(
                    valence=summaries["valence"].statistics,
                    arousal=summaries["arousal"].statistics,
                    dominance=summaries["dominance"].statistics,
                )
                profile_coverage = summaries["valence"].coverage
                matched_tokens = profile_coverage.matched_token_count
                eligible_tokens = profile_coverage.eligible_token_count
                token_coverage = profile_coverage.token_coverage
                matched_types = profile_coverage.matched_type_count
                eligible_types = profile_coverage.eligible_type_count
                type_coverage = profile_coverage.type_coverage
                scores = _scores(statistics)
                if scores is None:
                    continue
                rows.append(
                    VadEvidence(
                        source_analysis_id=result.analysis_id,
                        source_lexicon_id=(
                            result.lexicon_metadata.lexicon_id
                        ),
                        source_lexicon_name=(
                            result.lexicon_metadata.display_name
                        ),
                        source_lexicon_version=(
                            result.lexicon_metadata.version
                        ),
                        source_adapter_version=(
                            result.lexicon_metadata.adapter_version
                        ),
                        source_sha256=(
                            result.lexicon_validation.source_sha256
                        ),
                        analysis_view=analysis_view,
                        weighting_mode=weighting_mode,
                        scores=scores,
                        dispersion=_dispersion(statistics),
                        matched_token_count=matched_tokens,
                        eligible_token_count=eligible_tokens,
                        token_coverage=token_coverage,
                        matched_type_count=matched_types,
                        eligible_type_count=eligible_types,
                        type_coverage=type_coverage,
                        exclusions=(
                            f"phrase_policy={result.phrase_policy.value}",
                            (
                                "stopword_policy="
                                + (
                                    result.stopword_policy.mode.value
                                    if result.stopword_policy is not None
                                    else "unavailable"
                                )
                            ),
                            (
                                "Unmatched items remain missing; no neutral "
                                "numeric value is substituted."
                            ),
                        ),
                        unmatched_terms=_unmatched_terms(
                            result,
                            analysis_view,
                        ),
                        token_vad_observation_count=(
                            profile_dimensions["valence"][
                                AnalysisProfile(scope, AggregationWeighting.TOKEN)
                            ].statistics.count
                        ),
                        type_vad_observation_count=(
                            profile_dimensions["valence"][
                                AnalysisProfile(scope, AggregationWeighting.TYPE)
                            ].statistics.count
                        ),
                    )
                )
    return tuple(rows)


def _type_statistics(values: Sequence[float]) -> DescriptiveStatistics:
    return descriptive_statistics(values)


def lexical_evidence_from_results(
    *,
    concreteness: ConcretenessAnalysisResult | None = None,
    frequency: FrequencyAnalysisResult | None = None,
    aoa: AoAAnalysisResult | None = None,
) -> tuple[LexicalEvidence, ...]:
    """Expose completed lexical-semantic summaries as secondary evidence."""

    rows: list[LexicalEvidence] = []
    if concreteness is not None:
        summary = concreteness.summary
        rows.append(
            LexicalEvidence(
                dimension_id="concreteness",
                source_module="concreteness",
                configuration_id=(
                    concreteness.configuration.configuration_id
                ),
                unit="source 1-5 mean concreteness rating",
                low_max=(
                    concreteness.configuration.highly_abstract_max
                ),
                high_min=(
                    concreteness.configuration.highly_concrete_min
                ),
                low_label="Predominantly abstract vocabulary",
                moderate_label="Mixed abstract and concrete vocabulary",
                high_label="Highly concrete vocabulary",
                token_statistics=summary.statistics,
                type_statistics=_type_statistics(
                    [row.rating for row in concreteness.term_summaries]
                ),
                token_coverage=summary.token_coverage,
                type_coverage=summary.unique_type_coverage,
            )
        )
    if frequency is not None:
        summary = frequency.summary
        rows.append(
            LexicalEvidence(
                dimension_id="frequency",
                source_module="lexical_frequency",
                configuration_id=frequency.configuration.configuration_id,
                unit="SUBTLEX-US Zipf value",
                low_max=frequency.configuration.uncommon_below,
                high_min=frequency.configuration.moderately_common_below,
                low_label="Relatively uncommon vocabulary",
                moderate_label="Moderate-frequency vocabulary",
                high_label="Common vocabulary",
                token_statistics=summary.statistics,
                type_statistics=_type_statistics(
                    [row.zipf_value for row in frequency.term_summaries]
                ),
                token_coverage=summary.token_coverage,
                type_coverage=summary.unique_type_coverage,
            )
        )
    if aoa is not None:
        summary = aoa.summary
        rows.append(
            LexicalEvidence(
                dimension_id="age_of_acquisition",
                source_module="age_of_acquisition",
                configuration_id=aoa.configuration.configuration_id,
                unit="retrospective normative mean age in years",
                low_max=aoa.configuration.early_acquired_max,
                high_min=aoa.configuration.later_acquired_min,
                low_label="Earlier-acquired vocabulary",
                moderate_label="Mixed age-of-acquisition vocabulary",
                high_label="Later-acquired vocabulary",
                token_statistics=summary.statistics,
                type_statistics=_type_statistics(
                    [row.mean_age for row in aoa.term_summaries]
                ),
                token_coverage=summary.token_coverage,
                type_coverage=summary.unique_type_coverage,
            )
        )
    return tuple(rows)


__all__ = [
    "lexical_evidence_from_results",
    "vad_evidence_from_results",
]
