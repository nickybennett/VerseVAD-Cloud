"""Lightweight post-analysis aggregation from immutable lexical evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from versevad.analysis.statistics import descriptive_statistics
from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileCoverage,
    SCOPE_ORDER,
    WEIGHTING_ORDER,
    phrase_adjusted_eligible_ids,
    scoped_token_ids,
    type_identity_for_token,
)
from versevad.models import (
    AffectMatchRecord,
    DescriptiveStatistics,
    MatchSelection,
    Phase2AnalysisResult,
    TokenRecord,
)


AGGREGATION_ENGINE_VERSION = "profile-aggregation-v1"


@dataclass(frozen=True)
class ScalarEvidence:
    """One already-computed resource observation used by report aggregation."""

    token_ids: tuple[str, ...]
    value: float
    type_identity: str
    phrase: bool = False


@dataclass(frozen=True)
class ScalarProfileSummary:
    profile: AnalysisProfile
    statistics: DescriptiveStatistics
    cumulative_value: float | None
    value_per_100_observations: float | None
    above_midpoint_load: float | None
    below_midpoint_load: float | None
    net_midpoint_load: float | None
    absolute_midpoint_load: float | None
    average_deviation_from_mean: float | None
    coverage: ProfileCoverage


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _active_stopwords(result: Phase2AnalysisResult | None) -> tuple[str, ...]:
    policy = getattr(result, "stopword_policy", None)
    return tuple(getattr(policy, "active_words", ()) or ())


def _token_map(tokens: Sequence[TokenRecord]) -> dict[str, TokenRecord]:
    return {token.token_id: token for token in tokens}


def _scope_evidence(
    tokens: Sequence[TokenRecord],
    observations: Sequence[ScalarEvidence],
    scope: LexicalScope,
    *,
    active_stopwords: Iterable[str],
) -> tuple[frozenset[str], tuple[ScalarEvidence, ...]]:
    base = scoped_token_ids(tokens, scope, active_stopwords=active_stopwords)
    phrase_spans = tuple(
        observation.token_ids
        for observation in observations
        if observation.phrase and set(observation.token_ids).intersection(base)
    )
    eligible = phrase_adjusted_eligible_ids(base, phrase_spans)
    included = tuple(
        observation
        for observation in observations
        if set(observation.token_ids).intersection(eligible)
        and (
            not observation.phrase
            or set(observation.token_ids).issubset(eligible)
        )
    )
    return eligible, included


def aggregate_scalar_evidence(
    *,
    tokens: Sequence[TokenRecord],
    observations: Sequence[ScalarEvidence],
    active_stopwords: Iterable[str] = (),
    type_identity_rule: str = "matched_resource_entry",
) -> Mapping[AnalysisProfile, ScalarProfileSummary]:
    """Return all six compatible profiles without performing linguistic work."""

    token_by_id = _token_map(tokens)
    lexical_ids = scoped_token_ids(tokens, LexicalScope.ALL_LEXICAL)
    stopword_ids = lexical_ids.difference(
        scoped_token_ids(
            tokens,
            LexicalScope.STOPWORD_EXCLUDED,
            active_stopwords=active_stopwords,
        )
    )
    content_ids = scoped_token_ids(tokens, LexicalScope.CONTENT_WORDS)
    output: dict[AnalysisProfile, ScalarProfileSummary] = {}

    for scope in SCOPE_ORDER:
        eligible_ids, scoped = _scope_evidence(
            tokens,
            observations,
            scope,
            active_stopwords=active_stopwords,
        )
        matched_ids = frozenset(
            token_id
            for observation in scoped
            for token_id in observation.token_ids
            if token_id in eligible_ids
        )
        eligible_type_ids = {
            type_identity_for_token(token_by_id[token_id], "normalized_surface")
            for token_id in eligible_ids
            if token_id in token_by_id
        }
        # Coverage types use the eligible token identity so numerator and
        # denominator remain commensurable. Aggregation may still use a
        # metric-specific resource-entry identity below.
        matched_type_ids = {
            type_identity_for_token(token_by_id[token_id], "normalized_surface")
            for token_id in matched_ids
            if token_id in token_by_id
        }
        phrase_count = sum(observation.phrase for observation in scoped)
        coverage = ProfileCoverage(
            scope=scope,
            eligible_token_count=len(eligible_ids),
            eligible_type_count=len(eligible_type_ids),
            matched_token_count=len(matched_ids),
            unmatched_token_count=max(0, len(eligible_ids) - len(matched_ids)),
            matched_type_count=len(matched_type_ids),
            unmatched_type_count=max(0, len(eligible_type_ids) - len(matched_type_ids)),
            excluded_stopword_count=(
                len(stopword_ids.difference(eligible_ids))
                if scope is LexicalScope.STOPWORD_EXCLUDED
                else 0
            ),
            excluded_non_content_count=(
                len(lexical_ids.difference(content_ids).difference(eligible_ids))
                if scope is LexicalScope.CONTENT_WORDS
                else 0
            ),
            phrase_match_count=phrase_count,
            token_coverage=_ratio(len(matched_ids), len(eligible_ids)),
            type_coverage=_ratio(len(matched_type_ids), len(eligible_type_ids)),
            type_identity_rule=type_identity_rule,
        )

        for weighting in WEIGHTING_ORDER:
            if weighting is AggregationWeighting.TOKEN:
                # One retained observation represents one occurrence of the
                # matched resource entry. A multiword expression therefore
                # contributes once, not once for every token in its span.
                # Token-level coverage still records every participating
                # token above, preserving exact scope denominators.
                values = tuple(observation.value for observation in scoped)
            else:
                by_type: dict[str, float] = {}
                for observation in scoped:
                    by_type.setdefault(observation.type_identity, observation.value)
                values = tuple(by_type.values())
            total = sum(values) if values else None
            if values:
                mean = sum(values) / len(values)
                above_midpoint = sum(max(value - 0.5, 0.0) for value in values)
                below_midpoint = sum(max(0.5 - value, 0.0) for value in values)
                average_deviation = sum(abs(value - mean) for value in values) / len(values)
            else:
                above_midpoint = None
                below_midpoint = None
                average_deviation = None
            output[AnalysisProfile(scope, weighting)] = ScalarProfileSummary(
                profile=AnalysisProfile(scope, weighting),
                statistics=descriptive_statistics(values),
                cumulative_value=total,
                value_per_100_observations=(
                    total / len(values) * 100 if total is not None and values else None
                ),
                above_midpoint_load=above_midpoint,
                below_midpoint_load=below_midpoint,
                net_midpoint_load=(
                    above_midpoint - below_midpoint
                    if above_midpoint is not None and below_midpoint is not None
                    else None
                ),
                absolute_midpoint_load=(
                    above_midpoint + below_midpoint
                    if above_midpoint is not None and below_midpoint is not None
                    else None
                ),
                average_deviation_from_mean=average_deviation,
                coverage=coverage,
            )
    return output


def _match_type_identity(match: AffectMatchRecord) -> str:
    return str(
        match.matched_lookup_form
        or match.matched_term
        or match.match_id
    ).casefold()


def vad_profile_summaries(
    result: Phase2AnalysisResult,
) -> Mapping[str, Mapping[AnalysisProfile, ScalarProfileSummary]]:
    """Aggregate normalized VAD observations for every compatible profile."""

    dimensions = ("valence", "arousal", "dominance")
    output: dict[str, Mapping[AnalysisProfile, ScalarProfileSummary]] = {}
    for dimension in dimensions:
        observations = tuple(
            ScalarEvidence(
                token_ids=tuple(match.token_ids),
                value=float(getattr(match.normalized_scores, dimension)),
                type_identity=_match_type_identity(match),
                phrase=len(match.token_ids) > 1,
            )
            for match in result.matches
            if match.selection == MatchSelection.INCLUDED
            and match.included
            and match.normalized_scores is not None
        )
        output[dimension] = aggregate_scalar_evidence(
            tokens=result.tokens,
            observations=observations,
            active_stopwords=_active_stopwords(result),
            type_identity_rule="matched_resource_entry",
        )
    return output


def token_audit_scalar_profiles(
    *,
    tokens: Sequence[TokenRecord],
    audit_rows: Iterable[object],
    value_attribute: str,
    type_identity_attributes: tuple[str, ...] = (
        "matched_lookup_form",
        "matched_source_term",
        "normalized_form",
    ),
    active_stopwords: Iterable[str] = (),
    phrase_token_ids_attribute: str = "match_group_token_ids",
    observation_identity_attributes: tuple[str, ...] = (
        "match_group_id",
        "token_id",
    ),
    type_identity_rule: str = "matched_resource_entry",
) -> Mapping[AnalysisProfile, ScalarProfileSummary]:
    """Adapt a retained lexical-module token audit to all six profiles."""

    evidence: list[ScalarEvidence] = []
    seen_observations: set[str] = set()
    for row in audit_rows:
        value = getattr(row, value_attribute, None)
        if not bool(getattr(row, "included", False)) or value is None:
            continue
        token_ids = tuple(getattr(row, phrase_token_ids_attribute, ()) or ())
        if not token_ids:
            token_id = str(getattr(row, "token_id", ""))
            token_ids = (token_id,) if token_id else ()
        observation_identity = next(
            (
                str(getattr(row, attribute))
                for attribute in observation_identity_attributes
                if getattr(row, attribute, None)
            ),
            "|".join(token_ids),
        )
        if observation_identity in seen_observations:
            continue
        seen_observations.add(observation_identity)
        identity = next(
            (
                str(getattr(row, attribute))
                for attribute in type_identity_attributes
                if getattr(row, attribute, None)
            ),
            "|".join(token_ids),
        )
        evidence.append(
            ScalarEvidence(
                token_ids=token_ids,
                value=float(value),
                type_identity=identity.casefold(),
                phrase=len(token_ids) > 1,
            )
        )
    return aggregate_scalar_evidence(
        tokens=tokens,
        observations=tuple(evidence),
        active_stopwords=active_stopwords,
        type_identity_rule=type_identity_rule,
    )


__all__ = [
    "AGGREGATION_ENGINE_VERSION",
    "ScalarEvidence",
    "ScalarProfileSummary",
    "aggregate_scalar_evidence",
    "token_audit_scalar_profiles",
    "vad_profile_summaries",
]
