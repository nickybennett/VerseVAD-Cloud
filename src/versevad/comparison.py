"""Like-for-like comparison of two completed VerseVAD workspaces."""

from __future__ import annotations

import hashlib
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from numbers import Real
from typing import TYPE_CHECKING, Iterable, Sequence

from versevad.stopwords import build_stopword_policy
from versevad.metric_capabilities import metric_capabilities

if TYPE_CHECKING:
    from versevad.application import WorkspaceAnalysis


@dataclass(frozen=True)
class PoemComparison:
    comparison_id: str
    first: WorkspaceAnalysis
    second: WorkspaceAnalysis


@dataclass(frozen=True)
class PoemComparisonRow:
    section: str
    source: str
    analysis_view: str
    weighting: str
    metric_id: str
    metric: str
    value_a: float | int | str | None
    value_b: float | int | str | None
    difference_b_minus_a: float | None
    absolute_difference: float | None
    unit_or_scale: str
    denominator_a: str
    denominator_b: str
    coverage_a: float | None
    coverage_b: float | None
    note: str


@dataclass(frozen=True)
class PoemComparisonSet:
    """Two to ten immutable analyses sharing one analytical configuration."""

    comparison_set_id: str
    analyses: tuple[WorkspaceAnalysis, ...]


@dataclass(frozen=True)
class PoemComparisonSetValue:
    """One poem's contribution to a comparison-set metric."""

    poem_id: str
    title: str
    value: float | int | str | None
    denominator: str
    coverage: float | None


@dataclass(frozen=True)
class PoemComparisonSetRow:
    """One like-for-like metric across every poem in a comparison set."""

    section: str
    source: str
    analysis_view: str
    weighting: str
    metric_id: str
    metric: str
    values: tuple[PoemComparisonSetValue, ...]
    numeric_mean: float | None
    numeric_population_standard_deviation: float | None
    contributing_poem_count: int
    categorical_summary: str
    unit_or_scale: str
    note: str
    numeric_range: float | None = None


def build_poem_comparison(
    first: WorkspaceAnalysis,
    second: WorkspaceAnalysis,
) -> PoemComparison:
    """Validate a shared design and retain both immutable analyses."""

    request_a = first.request
    request_b = second.request
    shared_fields = (
        "lexicon_ids",
        "phrase_policy",
        "minimum_match_requirement",
        "stopword_mode",
        "protected_stopwords",
        "custom_stopword_additions",
        "custom_stopword_removals",
        "include_concreteness",
        "concreteness_configuration",
        "include_frequency",
        "frequency_configuration",
        "include_aoa",
        "aoa_configuration",
        "include_sensorimotor",
        "sensorimotor_configuration",
        "include_pronunciation",
        "pronunciation_configuration",
        "include_meter",
        "meter_configuration",
        "include_phonology",
        "phonological_configuration",
        "include_lexical_style",
        "lexical_style_configuration",
        "include_poetry_id",
        "poetry_id_configuration",
        "include_inherited_form",
        "inherited_form_configuration",
        "include_versemap",
        "versemap_configuration",
    )
    incompatible = tuple(
        field
        for field in shared_fields
        if getattr(request_a, field) != getattr(request_b, field)
    )
    if incompatible:
        raise ValueError(
            "Poem comparison requires one shared configuration. Incompatible "
            "fields: " + ", ".join(incompatible)
        )
    signature = "|".join(
        (
            first.document.text_version_id,
            second.document.text_version_id,
            repr(tuple((field, getattr(request_a, field)) for field in shared_fields)),
        )
    )
    return PoemComparison(
        comparison_id="poem-comparison-v1:"
        + hashlib.sha256(signature.encode("utf-8")).hexdigest(),
        first=first,
        second=second,
    )


def build_poem_comparison_set(
    analyses: Sequence[WorkspaceAnalysis],
) -> PoemComparisonSet:
    """Validate and retain a shared-design set of two through ten poems."""

    retained = tuple(analyses)
    if not 2 <= len(retained) <= 10:
        raise ValueError("A poem comparison set requires between 2 and 10 poems.")
    anchor = retained[0]
    comparison_ids = [
        build_poem_comparison(anchor, analysis).comparison_id
        for analysis in retained
    ]
    signature = "|".join(("poem-comparison-set-v1", *comparison_ids))
    return PoemComparisonSet(
        comparison_set_id="poem-comparison-set-v1:"
        + hashlib.sha256(signature.encode("utf-8")).hexdigest(),
        analyses=retained,
    )


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _row(
    *,
    section: str,
    source: str,
    analysis_view: str,
    weighting: str,
    metric_id: str,
    metric: str,
    value_a: float | int | str | None,
    value_b: float | int | str | None,
    unit_or_scale: str,
    denominator_a: str,
    denominator_b: str,
    coverage_a: float | None = None,
    coverage_b: float | None = None,
    note: str = "",
) -> PoemComparisonRow:
    numeric_a = _numeric(value_a)
    numeric_b = _numeric(value_b)
    difference = (
        numeric_b - numeric_a
        if numeric_a is not None and numeric_b is not None
        else None
    )
    return PoemComparisonRow(
        section=section,
        source=source,
        analysis_view=analysis_view,
        weighting=weighting,
        metric_id=metric_id,
        metric=metric,
        value_a=value_a,
        value_b=value_b,
        difference_b_minus_a=difference,
        absolute_difference=abs(difference) if difference is not None else None,
        unit_or_scale=unit_or_scale,
        denominator_a=denominator_a,
        denominator_b=denominator_b,
        coverage_a=coverage_a,
        coverage_b=coverage_b,
        note=note,
    )


def _vad_group(result, analysis_view: str, weighting: str):
    summary = result.vad_summary
    if summary is None:
        return None
    prefix = "stopword_excluded_" if analysis_view == "stopwords_excluded" else ""
    return getattr(summary, f"{prefix}{weighting}_weighted_normalized")


def _vad_coverage(result, analysis_view: str) -> float | None:
    if analysis_view == "stopwords_excluded":
        coverage = result.stopword_coverage
        return coverage.lexical_token_coverage if coverage is not None else None
    return result.coverage.lexical_token_coverage


def _selected_vad_matches(result, analysis_view: str, weighting: str):
    from versevad.analysis_profiles import (
        LexicalScope,
        phrase_adjusted_eligible_ids,
        scoped_token_ids,
    )

    if analysis_view == "content_words":
        base_ids = scoped_token_ids(result.tokens, LexicalScope.CONTENT_WORDS)
        eligible_ids = phrase_adjusted_eligible_ids(
            base_ids,
            (
                match.token_ids
                for match in result.matches
                if match.included and len(match.token_ids) > 1
            ),
        )
    else:
        eligible_ids = None
    selected = [
        match
        for match in result.matches
        if match.included
        and match.normalized_scores is not None
        and (
            analysis_view == "all_matched"
            or (analysis_view == "stopwords_excluded" and match.included_in_stopword_view)
            or (
                analysis_view == "content_words"
                and eligible_ids is not None
                and set(match.token_ids).issubset(eligible_ids)
            )
        )
    ]
    if weighting == "type":
        unique = {}
        for match in selected:
            unique.setdefault(match.matched_lookup_form or match.match_id, match)
        selected = list(unique.values())
    return tuple(selected)


def _vad_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    first_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.first.results
        if result.vad_summary is not None
    }
    second_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.second.results
        if result.vad_summary is not None
    }
    rows = []
    for lexicon_id in sorted(set(first_by_id) & set(second_by_id)):
        first = first_by_id[lexicon_id]
        second = second_by_id[lexicon_id]
        source = first.lexicon_metadata.display_name
        matches_a = _selected_vad_matches(first, analysis_view, weighting)
        matches_b = _selected_vad_matches(second, analysis_view, weighting)
        from versevad.analysis_profiles import (
            AggregationWeighting,
            AnalysisProfile,
            LexicalScope,
        )
        from versevad.profile_aggregation import vad_profile_summaries

        scope = {
            "all_matched": LexicalScope.ALL_LEXICAL,
            "stopwords_excluded": LexicalScope.STOPWORD_EXCLUDED,
            "content_words": LexicalScope.CONTENT_WORDS,
        }[analysis_view]
        profile = AnalysisProfile(
            scope,
            AggregationWeighting.TYPE
            if weighting == "type"
            else AggregationWeighting.TOKEN,
        )
        summaries_a = vad_profile_summaries(first)
        summaries_b = vad_profile_summaries(second)
        denominator_kind = "tokens" if weighting == "token" else "types"
        for dimension in ("valence", "arousal", "dominance"):
            summary_a = summaries_a[dimension][profile]
            summary_b = summaries_b[dimension][profile]
            stats_a = summary_a.statistics
            stats_b = summary_b.statistics
            if weighting == "token":
                denominator_a = (
                    f"{summary_a.coverage.matched_token_count} of "
                    f"{summary_a.coverage.eligible_token_count} eligible tokens; "
                    f"{summary_a.coverage.matched_token_count} matched tokens"
                )
                denominator_b = (
                    f"{summary_b.coverage.matched_token_count} of "
                    f"{summary_b.coverage.eligible_token_count} eligible tokens; "
                    f"{summary_b.coverage.matched_token_count} matched tokens"
                )
            else:
                denominator_a = (
                    f"{summary_a.coverage.matched_type_count} of "
                    f"{summary_a.coverage.eligible_type_count} eligible types; "
                    f"{summary_a.coverage.matched_type_count} matched types"
                )
                denominator_b = (
                    f"{summary_b.coverage.matched_type_count} of "
                    f"{summary_b.coverage.eligible_type_count} eligible types; "
                    f"{summary_b.coverage.matched_type_count} matched types"
                )
            coverage_a = (
                summary_a.coverage.token_coverage
                if weighting == "token"
                else summary_a.coverage.type_coverage
            )
            coverage_b = (
                summary_b.coverage.token_coverage
                if weighting == "token"
                else summary_b.coverage.type_coverage
            )
            rows.extend(
                (
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=f"vad.{lexicon_id}.{dimension}.mean",
                        metric=f"Mean normative {dimension}",
                        value_a=stats_a.mean,
                        value_b=stats_b.mean,
                        unit_or_scale="derived normalized 0–1",
                        denominator_a=denominator_a,
                        denominator_b=denominator_b,
                        coverage_a=coverage_a,
                        coverage_b=coverage_b,
                        note=(
                            "The shared endpoint transformation supports direct "
                            "within-source comparison; it does not merge lexicons."
                        ),
                    ),
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=f"vad.{lexicon_id}.{dimension}.population_sd",
                        metric=f"{dimension.title()} population standard deviation",
                        value_a=stats_a.population_standard_deviation,
                        value_b=stats_b.population_standard_deviation,
                        unit_or_scale="derived normalized-scale points",
                        denominator_a=denominator_a,
                        denominator_b=denominator_b,
                        coverage_a=coverage_a,
                        coverage_b=coverage_b,
                        note="Within-poem lexical dispersion, not uncertainty in the mean.",
                    ),
                )
            )
            values_a = [
                float(getattr(match.normalized_scores, dimension))
                for match in matches_a
            ]
            values_b = [
                float(getattr(match.normalized_scores, dimension))
                for match in matches_b
            ]
            cumulative_a = _cumulative_values(values_a)
            cumulative_b = _cumulative_values(values_b)
            for key, label in (
                ("above_midpoint", "Above-midpoint load"),
                ("below_midpoint", "Below-midpoint load"),
                ("net_midpoint", "Net midpoint load"),
                ("absolute_midpoint", "Absolute midpoint load"),
                (
                    "above_midpoint_per_observation",
                    f"Above-midpoint deviation per matched {denominator_kind[:-1]}",
                ),
                (
                    "below_midpoint_per_observation",
                    f"Below-midpoint deviation per matched {denominator_kind[:-1]}",
                ),
                (
                    "net_midpoint_per_observation",
                    f"Net midpoint deviation per matched {denominator_kind[:-1]}",
                ),
                (
                    "absolute_midpoint_per_observation",
                    f"Absolute midpoint deviation per matched {denominator_kind[:-1]}",
                ),
                (
                    "above_midpoint_per_100",
                    f"Above-midpoint deviation per 100 matched {denominator_kind}",
                ),
                (
                    "below_midpoint_per_100",
                    f"Below-midpoint deviation per 100 matched {denominator_kind}",
                ),
                (
                    "net_midpoint_per_100",
                    f"Net midpoint deviation per 100 matched {denominator_kind}",
                ),
                (
                    "absolute_midpoint_per_100",
                    f"Absolute midpoint deviation per 100 matched {denominator_kind}",
                ),
                (
                    "average_deviation_from_poem_mean",
                    "Average deviation from poem mean",
                ),
            ):
                rows.append(
                    _row(
                        section="Cumulative Lexical Load",
                        source=source,
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=f"vad.{lexicon_id}.{dimension}.{key}",
                        metric=f"{dimension.title()} — {label}",
                        value_a=cumulative_a.get(key),
                        value_b=cumulative_b.get(key),
                        unit_or_scale=(
                            "mean absolute deviation on derived normalized 0-1 scale"
                            if "poem_mean" in key
                            else f"deviation points per 100 matched {denominator_kind}"
                            if key.endswith("per_100")
                            and "midpoint" in key
                            else (
                                    "mean deviation per matched observation"
                                if key.endswith("per_observation")
                                else (
                                    f"summed normalized ratings per 100 matched {denominator_kind}"
                                    if key.endswith("per_100")
                                    else "summed normalized ratings"
                                )
                            )
                        ),
                        denominator_a=denominator_a,
                        denominator_b=denominator_b,
                        coverage_a=coverage_a,
                        coverage_b=coverage_b,
                        note=(
                            (
                                "Length-neutral dispersion around each poem's "
                                "own lexical mean; token or line order is not retained."
                            )
                            if "poem_mean" in key
                            else (
                                "Raw loads retain length and repetition in the token "
                                "view; per-observation and per-100 deviations support "
                                "comparison across differently sized poems."
                            )
                        ),
                    )
                )
    return rows


def _cumulative_values(values: Iterable[float]) -> dict[str, float | None]:
    numbers = tuple(values)
    if not numbers:
        return {
            "rating_total": None,
            "above_midpoint": None,
            "below_midpoint": None,
            "net_midpoint": None,
            "absolute_midpoint": None,
            "rating_total_per_100": None,
            "above_midpoint_per_observation": None,
            "below_midpoint_per_observation": None,
            "net_midpoint_per_observation": None,
            "absolute_midpoint_per_observation": None,
            "above_midpoint_per_100": None,
            "below_midpoint_per_100": None,
            "net_midpoint_per_100": None,
            "absolute_midpoint_per_100": None,
            "average_deviation_from_poem_mean": None,
        }
    above = sum(max(value - 0.5, 0.0) for value in numbers)
    below = sum(max(0.5 - value, 0.0) for value in numbers)
    total = sum(numbers)
    count = len(numbers)
    net = above - below
    absolute = above + below
    poem_mean = statistics.fmean(numbers)
    average_mean_deviation = statistics.fmean(
        abs(value - poem_mean) for value in numbers
    )
    return {
        "rating_total": total,
        "above_midpoint": above,
        "below_midpoint": below,
        "net_midpoint": net,
        "absolute_midpoint": absolute,
        "rating_total_per_100": total / count * 100,
        "above_midpoint_per_observation": above / count,
        "below_midpoint_per_observation": below / count,
        "net_midpoint_per_observation": net / count,
        "absolute_midpoint_per_observation": absolute / count,
        "above_midpoint_per_100": above / count * 100,
        "below_midpoint_per_100": below / count * 100,
        "net_midpoint_per_100": net / count * 100,
        "absolute_midpoint_per_100": absolute / count * 100,
        "average_deviation_from_poem_mean": average_mean_deviation,
    }


def _descriptive_rows(
    *,
    section: str,
    source: str,
    metric_prefix: str,
    label: str,
    values_a: tuple[float, ...],
    values_b: tuple[float, ...],
    analysis_view: str,
    weighting: str,
    unit: str,
    coverage_a: float | None,
    coverage_b: float | None,
    note: str,
) -> list[PoemComparisonRow]:
    mean_a = statistics.fmean(values_a) if values_a else None
    mean_b = statistics.fmean(values_b) if values_b else None
    sd_a = statistics.pstdev(values_a) if len(values_a) > 1 else None
    sd_b = statistics.pstdev(values_b) if len(values_b) > 1 else None
    sum_a = sum(values_a) if values_a else None
    sum_b = sum(values_b) if values_b else None
    denominator_a = f"{len(values_a)} matched {weighting}-weighted observations"
    denominator_b = f"{len(values_b)} matched {weighting}-weighted observations"
    return [
        _row(
            section=section,
            source=source,
            analysis_view=analysis_view,
            weighting=weighting,
            metric_id=f"{metric_prefix}.mean",
            metric=f"Mean {label}",
            value_a=mean_a,
            value_b=mean_b,
            unit_or_scale=unit,
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=coverage_a,
            coverage_b=coverage_b,
            note=note,
        ),
        _row(
            section=section,
            source=source,
            analysis_view=analysis_view,
            weighting=weighting,
            metric_id=f"{metric_prefix}.population_sd",
            metric=f"{label.title()} population standard deviation",
            value_a=sd_a,
            value_b=sd_b,
            unit_or_scale=f"{unit} points",
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=coverage_a,
            coverage_b=coverage_b,
            note="Within-poem dispersion across the retained lexical observations.",
        ),
        _row(
            section="Cumulative Lexical Load",
            source=source,
            analysis_view=analysis_view,
            weighting=weighting,
            metric_id=f"{metric_prefix}.cumulative_load",
            metric=f"{label.title()} cumulative load",
            value_a=sum_a,
            value_b=sum_b,
            unit_or_scale=f"summed {unit}",
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=coverage_a,
            coverage_b=coverage_b,
            note="Length- and repetition-sensitive in the token-weighted view.",
        ),
        _row(
            section="Cumulative Lexical Load",
            source=source,
            analysis_view=analysis_view,
            weighting=weighting,
            metric_id=f"{metric_prefix}.load_per_100",
            metric=f"{label.title()} load per 100 observations",
            value_a=(sum_a / len(values_a) * 100 if values_a else None),
            value_b=(sum_b / len(values_b) * 100 if values_b else None),
            unit_or_scale=f"summed {unit} per 100 observations",
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=coverage_a,
            coverage_b=coverage_b,
            note="Length-normalized counterpart to cumulative load.",
        ),
    ]


def _filtered_audit_values(
    workspace: WorkspaceAnalysis,
    result,
    value_attribute: str,
    *,
    analysis_view: str,
    weighting: str,
) -> tuple[tuple[float, ...], float | None]:
    rows = tuple(result.token_audit)
    policy = build_stopword_policy(
        mode=workspace.request.stopword_mode,
        protected_words=workspace.request.protected_stopwords,
        custom_additions=workspace.request.custom_stopword_additions,
        custom_removals=workspace.request.custom_stopword_removals,
    )
    published_phrase_ids = {
        row.token_id
        for row in rows
        if row.included and getattr(row, "source_is_multiword", False)
    }
    eligible = [
        row
        for row in rows
        if row.eligible
        and (
            analysis_view == "all_matched"
            or row.token_id in published_phrase_ids
            or (
                row.normalized_form not in policy.active_words
                and row.normalized_lemma not in policy.active_words
            )
        )
    ]
    included = [
        row
        for row in eligible
        if row.included and getattr(row, value_attribute) is not None
    ]
    if weighting == "type":
        unique = {}
        for row in included:
            unique.setdefault(
                row.matched_lookup_form or row.normalized_form,
                row,
            )
        included = list(unique.values())
    values = tuple(float(getattr(row, value_attribute)) for row in included)
    return values, len(included) / len(eligible) if eligible else None


def _lexical_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    rows: list[PoemComparisonRow] = []
    module_specs = (
        (
            "concreteness",
            "rating",
            "Normative concreteness",
            "source 1–5",
            "Concreteness",
            "Context-free normative concreteness among matched concepts.",
        ),
        (
            "frequency",
            "zipf_value",
            "SUBTLEX-US Zipf frequency",
            "Zipf",
            "Frequency & Rarity",
            "Higher Zipf values indicate more frequent vocabulary in SUBTLEX-US.",
        ),
        (
            "aoa",
            "mean_age",
            "Normative age of acquisition",
            "source years",
            "Age of Acquisition",
            "Retrospective lexical norms, not reader age or grade level.",
        ),
    )
    for attribute, value_attribute, label, unit, source, note in module_specs:
        result_a = getattr(comparison.first, attribute)
        result_b = getattr(comparison.second, attribute)
        if result_a is None or result_b is None:
            continue
        values_a, coverage_a = _filtered_audit_values(
            comparison.first,
            result_a,
            value_attribute,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        values_b, coverage_b = _filtered_audit_values(
            comparison.second,
            result_b,
            value_attribute,
            analysis_view=analysis_view,
            weighting=weighting,
        )
        rows.extend(
            _descriptive_rows(
                section="Lexical Character, Imagery & Embodiment",
                source=source,
                metric_prefix=attribute,
                label=label,
                values_a=values_a,
                values_b=values_b,
                analysis_view=analysis_view,
                weighting=weighting,
                unit=unit,
                coverage_a=coverage_a,
                coverage_b=coverage_b,
                note=note,
            )
        )
        if attribute == "frequency":
            rarity_a = tuple(7.0 - value for value in values_a)
            rarity_b = tuple(7.0 - value for value in values_b)
            rows.extend(
                _descriptive_rows(
                    section="Lexical Character, Imagery & Embodiment",
                    source=source,
                    metric_prefix="rarity",
                    label="lexical rarity orientation",
                    values_a=rarity_a,
                    values_b=rarity_b,
                    analysis_view=analysis_view,
                    weighting=weighting,
                    unit="7 minus SUBTLEX-US Zipf",
                    coverage_a=coverage_a,
                    coverage_b=coverage_b,
                    note="Higher values indicate rarer matched vocabulary.",
                )[:2]
            )
    sensor_a = comparison.first.sensorimotor
    sensor_b = comparison.second.sensorimotor
    if sensor_a is not None and sensor_b is not None:
        view_label = (
            "Stopwords excluded"
            if analysis_view == "stopwords_excluded"
            else "All matched tokens"
        )
        profile_a = sensor_a.profile(view_label, weighting)
        profile_b = sensor_b.profile(view_label, weighting)
        dimensions_b = {
            row.dimension_id: row for row in profile_b.dimensions
        }
        denominator_a = (
            f"{profile_a.matched_observation_count} matched "
            f"{weighting}-weighted observations"
        )
        denominator_b = (
            f"{profile_b.matched_observation_count} matched "
            f"{weighting}-weighted observations"
        )
        for dimension_a in profile_a.dimensions:
            dimension_b = dimensions_b[dimension_a.dimension_id]
            for suffix, label, value_a, value_b, unit, note in (
                (
                    "mean",
                    f"Mean normative {dimension_a.label}",
                    dimension_a.statistics.mean,
                    dimension_b.statistics.mean,
                    "source 0–5",
                    "Context-free normative sensorimotor association strength.",
                ),
                (
                    "population_sd",
                    f"{dimension_a.label} population standard deviation",
                    dimension_a.statistics.population_standard_deviation,
                    dimension_b.statistics.population_standard_deviation,
                    "source-scale points",
                    "Within-poem dispersion across matched source means.",
                ),
                (
                    "cumulative_load",
                    f"{dimension_a.label} cumulative load",
                    dimension_a.cumulative_load,
                    dimension_b.cumulative_load,
                    "summed source ratings",
                    "Length- and repetition-sensitive in the token view.",
                ),
                (
                    "load_per_100",
                    f"{dimension_a.label} load per 100 observations",
                    dimension_a.load_per_100_observations,
                    dimension_b.load_per_100_observations,
                    "summed ratings per 100 observations",
                    "Length-normalized cumulative load.",
                ),
            ):
                rows.append(
                    _row(
                        section=(
                            "Cumulative Lexical Load"
                            if "load" in suffix
                            else "Lexical Character, Imagery & Embodiment"
                        ),
                        source="Lancaster Sensorimotor Norms",
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=(
                            f"sensorimotor.{dimension_a.dimension_id}.{suffix}"
                        ),
                        metric=label,
                        value_a=value_a,
                        value_b=value_b,
                        unit_or_scale=unit,
                        denominator_a=denominator_a,
                        denominator_b=denominator_b,
                        coverage_a=profile_a.token_coverage,
                        coverage_b=profile_b.token_coverage,
                        note=note,
                    )
                )
    return rows


def _method_fixed_rows(comparison: PoemComparison) -> list[PoemComparisonRow]:
    from versevad.application import part_of_speech_views

    rows: list[PoemComparisonRow] = []
    vader_a = comparison.first.vader_sentiment
    vader_b = comparison.second.vader_sentiment
    if vader_a is not None and vader_b is not None:
        for field, label, unit in (
            ("positive_proportion", "VADER positive proportion", "proportion"),
            ("neutral_proportion", "VADER neutral proportion", "proportion"),
            ("negative_proportion", "VADER negative proportion", "proportion"),
            ("compound_score", "VADER compound score", "normalized −1 to 1"),
            ("threshold_label", "VADER conventional threshold label", "category"),
        ):
            rows.append(
                _row(
                    section="Affective Evidence",
                    source="VADER",
                    analysis_view="complete preserved text",
                    weighting="method fixed",
                    metric_id=f"vader.{field}",
                    metric=label,
                    value_a=getattr(vader_a.document_score, field),
                    value_b=getattr(vader_b.document_score, field),
                    unit_or_scale=unit,
                    denominator_a="complete preserved text",
                    denominator_b="complete preserved text",
                    note="Rule-based polarity evidence, not the poem's emotion.",
                )
            )
    readability_a = comparison.first.readability
    readability_b = comparison.second.readability
    if readability_a is not None and readability_b is not None:
        poetic_a = getattr(readability_a, "poetic_reading_ease", None)
        poetic_b = getattr(readability_b, "poetic_reading_ease", None)
        if poetic_a is not None and poetic_b is not None:
            rows.extend(
                (
                    _row(
                        section="Lexical Character, Imagery & Embodiment",
                        source="VerseVAD Poetic Reading Ease (Experimental)",
                        analysis_view=poetic_a.profile_id,
                        weighting="fixed positive weighted composite",
                        metric_id="readability.poetic_reading_ease.score",
                        metric="VV-PRE score",
                        value_a=poetic_a.score,
                        value_b=poetic_b.score,
                        unit_or_scale="0-100; higher means more accessible",
                        denominator_a="all four declared components",
                        denominator_b="all four declared components",
                        note=(
                            "Fixed token-weighted content-word profile for "
                            "Frequency, AoA, and Word Complexity; all lexical "
                            "words for line length. Surface-level linguistic "
                            "accessibility, not thematic or interpretive complexity."
                        ),
                    ),
                    _row(
                        section="Lexical Character, Imagery & Embodiment",
                        source="VerseVAD Poetic Reading Ease (Experimental)",
                        analysis_view=poetic_a.profile_id,
                        weighting="fixed interpretation bands",
                        metric_id="readability.poetic_reading_ease.band",
                        metric="VV-PRE interpretation band",
                        value_a=poetic_a.interpretation_band,
                        value_b=poetic_b.interpretation_band,
                        unit_or_scale="declared experimental band",
                        denominator_a="VV-PRE score",
                        denominator_b="VV-PRE score",
                        note="Band boundaries are fixed and documented.",
                    ),
                    _row(
                        section="Lexical Character, Imagery & Embodiment",
                        source="VerseVAD Poetic Reading Ease (Experimental)",
                        analysis_view=poetic_a.profile_id,
                        weighting="fixed evidence-sufficiency rules",
                        metric_id=(
                            "readability.poetic_reading_ease.evidence_confidence"
                        ),
                        metric="VV-PRE evidence confidence",
                        value_a=getattr(poetic_a, "evidence_confidence", None),
                        value_b=getattr(poetic_b, "evidence_confidence", None),
                        unit_or_scale="High, Moderate, or Limited",
                        denominator_a=(
                            "minimum component coverage and lexical match count"
                        ),
                        denominator_b=(
                            "minimum component coverage and lexical match count"
                        ),
                        note=(
                            "Evidence sufficiency qualifies interpretation and "
                            "does not alter either numerical score."
                        ),
                    ),
                    _row(
                        section="Lexical Character, Imagery & Embodiment",
                        source="VerseVAD Poetic Reading Ease (Experimental)",
                        analysis_view=poetic_a.profile_id,
                        weighting="method fixed",
                        metric_id=(
                            "readability.poetic_reading_ease."
                            "minimum_component_coverage"
                        ),
                        metric="VV-PRE minimum component coverage",
                        value_a=getattr(
                            poetic_a,
                            "minimum_component_coverage",
                            None,
                        ),
                        value_b=getattr(
                            poetic_b,
                            "minimum_component_coverage",
                            None,
                        ),
                        unit_or_scale="proportion",
                        denominator_a="four VV-PRE components",
                        denominator_b="four VV-PRE components",
                        note="Lowest component coverage used by the confidence rule.",
                    ),
                )
            )
            components_b = {
                component.component_id: component
                for component in poetic_b.components
            }
            for component_a in poetic_a.components:
                component_b = components_b.get(component_a.component_id)
                if component_b is None:
                    continue
                rows.append(
                    _row(
                        section="Lexical Character, Imagery & Embodiment",
                        source="VerseVAD Poetic Reading Ease (Experimental)",
                        analysis_view=poetic_a.profile_id,
                        weighting=f"fixed {component_a.weight:.0%} component",
                        metric_id=(
                            "readability.poetic_reading_ease."
                            f"{component_a.component_id}.ease_score"
                        ),
                        metric=f"{component_a.label} ease score",
                        value_a=component_a.ease_score,
                        value_b=component_b.ease_score,
                        unit_or_scale="normalized 0-100 ease score",
                        denominator_a=(
                            f"{component_a.matched_count} of "
                            f"{component_a.eligible_count} observations"
                        ),
                        denominator_b=(
                            f"{component_b.matched_count} of "
                            f"{component_b.eligible_count} observations"
                        ),
                        coverage_a=component_a.coverage,
                        coverage_b=component_b.coverage,
                        note=(
                            f"Easy anchor {component_a.easy_anchor:g}; difficult "
                            f"anchor {component_a.difficult_anchor:g}; scope: "
                            f"{component_a.scope_label}."
                        ),
                    )
                )
        for field, label, unit in (
            ("flesch_reading_ease", "Flesch Reading Ease", "formula score"),
            ("flesch_kincaid_grade", "Flesch-Kincaid Grade", "US grade orientation"),
            ("gunning_fog_index", "Gunning Fog Index", "grade orientation"),
            ("automated_readability_index", "Automated Readability Index", "grade orientation"),
            ("coleman_liau_index", "Coleman-Liau Index", "grade orientation"),
            ("smog_index", "SMOG Index", "grade orientation"),
            ("mean_words_per_sentence", "Mean words per sentence", "words"),
            ("mean_syllables_per_word", "Mean syllables per word", "syllables"),
        ):
            rows.append(
                _row(
                    section="Lexical Character, Imagery & Embodiment",
                    source="Readability formulas",
                    analysis_view="complete preserved text",
                    weighting="method fixed",
                    metric_id=f"readability.{field}",
                    metric=label,
                    value_a=getattr(readability_a.summary, field),
                    value_b=getattr(readability_b.summary, field),
                    unit_or_scale=unit,
                    denominator_a=f"{readability_a.summary.word_count} words",
                    denominator_b=f"{readability_b.summary.word_count} words",
                    coverage_a=readability_a.summary.pronunciation_coverage,
                    coverage_b=readability_b.summary.pronunciation_coverage,
                    note="Prose-oriented orientation evidence, not literary quality.",
                )
            )
    style_a = comparison.first.lexical_style
    style_b = comparison.second.lexical_style
    if style_a is not None and style_b is not None:
        fields = (
            ("lexical_token_count", "Lexical token count", "tokens"),
            ("normalized_surface_type_count", "Normalized surface type count", "types"),
            ("surface_type_token_ratio", "Surface type-token ratio", "proportion"),
            ("mattr", "MATTR", "mean fixed-window TTR"),
            ("hdd", "HD-D", "expected distinct-type proportion"),
            ("mtld", "MTLD", "mean lexical-token factor length"),
            ("mean_alphabetic_characters_per_token", "Mean word length", "alphabetic characters"),
            (
                "population_standard_deviation_alphabetic_characters",
                "Word-length population standard deviation",
                "alphabetic characters",
            ),
        )
        for field, label, unit in fields:
            rows.append(
                _row(
                    section="Structure & Sound",
                    source="Lexical & Structural Measures",
                    analysis_view="shared preprocessing",
                    weighting="method fixed",
                    metric_id=f"lexical_style.{field}",
                    metric=label,
                    value_a=getattr(style_a.summary, field),
                    value_b=getattr(style_b.summary, field),
                    unit_or_scale=unit,
                    denominator_a=f"{style_a.summary.lexical_token_count} lexical tokens",
                    denominator_b=f"{style_b.summary.lexical_token_count} lexical tokens",
                    note="Diversity values are comparable only under the shared configuration.",
                )
            )
        for name, label in (
            ("nonblank_line_word_count_statistics", "Words per nonblank line"),
            ("stanza_word_count_statistics", "Words per stanza"),
            ("stanza_line_count_statistics", "Nonblank lines per stanza"),
        ):
            stats_a = getattr(style_a.summary, name)
            stats_b = getattr(style_b.summary, name)
            for suffix, metric_label in (
                ("mean", f"Mean {label.lower()}"),
                ("population_standard_deviation", f"{label} population standard deviation"),
            ):
                rows.append(
                    _row(
                        section="Structure & Sound",
                        source="Lexical & Structural Measures",
                        analysis_view="preserved structure",
                        weighting="method fixed",
                        metric_id=f"lexical_style.{name}.{suffix}",
                        metric=metric_label,
                        value_a=getattr(stats_a, suffix),
                        value_b=getattr(stats_b, suffix),
                        unit_or_scale="count",
                        denominator_a=f"{stats_a.count} structural units",
                        denominator_b=f"{stats_b.count} structural units",
                        note="Population dispersion across preserved structural units.",
                    )
                )
    pos_a = {row.tag: row for row in part_of_speech_views(comparison.first)}
    pos_b = {row.tag: row for row in part_of_speech_views(comparison.second)}
    for tag in sorted(set(pos_a) | set(pos_b)):
        first = pos_a.get(tag)
        second = pos_b.get(tag)
        label = first.category if first is not None else second.category
        rows.append(
            _row(
                section="Structure & Sound",
                source="Shared linguistic model",
                analysis_view="all eligible lexical tokens",
                weighting="token",
                metric_id=f"pos.{tag}.proportion",
                metric=f"{label} proportion",
                value_a=first.share_of_lexical_tokens if first else 0.0,
                value_b=second.share_of_lexical_tokens if second else 0.0,
                unit_or_scale="proportion",
                denominator_a=(
                    f"{first.lexical_token_denominator} lexical tokens"
                    if first
                    else "no observed tokens in this POS group"
                ),
                denominator_b=(
                    f"{second.lexical_token_denominator} lexical tokens"
                    if second
                    else "no observed tokens in this POS group"
                ),
                note="POS labels are model outputs and can be uncertain in poetry.",
            )
        )
    rows.extend(_generic_dependent_rows(comparison))
    return rows


def _generic_dependent_rows(
    comparison: PoemComparison,
) -> list[PoemComparisonRow]:
    attributes = (
        ("pronunciation", "Structure & Sound"),
        ("meter", "Structure & Sound"),
        ("phonology", "Structure & Sound"),
        ("inherited_form", "Structure & Sound"),
        ("versemap", "Comparative Context"),
    )
    rows = []
    for attribute, section in attributes:
        first = getattr(comparison.first, attribute)
        second = getattr(comparison.second, attribute)
        if first is None or second is None:
            continue
        metrics_a = {
            (metric.metric_id, metric.scope_id, metric.weighting): metric
            for metric in first.module_result.metrics
            if metric.scope == "document"
        }
        metrics_b = {
            (metric.metric_id, metric.scope_id, metric.weighting): metric
            for metric in second.module_result.metrics
            if metric.scope == "document"
        }
        for key in sorted(set(metrics_a) & set(metrics_b)):
            a = metrics_a[key]
            b = metrics_b[key]
            rows.append(
                _row(
                    section=section,
                    source=first.module_result.module_name.replace("_", " ").title(),
                    analysis_view=a.scope_id or "document",
                    weighting=a.weighting or "method fixed",
                    metric_id=a.metric_id,
                    metric=a.metric_id.replace(".", " · ").replace("_", " ").title(),
                    value_a=a.value,
                    value_b=b.value,
                    unit_or_scale=a.unit,
                    denominator_a=a.denominator,
                    denominator_b=b.denominator,
                    note=a.note,
                )
            )
    return rows


def _poetry_id_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    first = comparison.first.poetry_id
    second = comparison.second.poetry_id
    if first is None or second is None:
        return []
    first_by_source = {
        assignment.source_analysis_id: assignment
        for assignment in first.assignments
        if assignment.analysis_view == analysis_view
        and assignment.weighting_mode == weighting
    }
    second_by_source = {
        assignment.source_analysis_id: assignment
        for assignment in second.assignments
        if assignment.analysis_view == analysis_view
        and assignment.weighting_mode == weighting
    }
    rows: list[PoemComparisonRow] = []
    for source_id in sorted(set(first_by_source) & set(second_by_source)):
        first_assignment = first_by_source[source_id]
        second_assignment = second_by_source[source_id]
        denominator_a = (
            f"{first_assignment.coverage.matched_token_count} matched tokens; "
            f"{first_assignment.coverage.matched_type_count} matched types"
        )
        denominator_b = (
            f"{second_assignment.coverage.matched_token_count} matched tokens; "
            f"{second_assignment.coverage.matched_type_count} matched types"
        )
        common = dict(
            section="Affective Evidence",
            source=first_assignment.source_lexicon_name,
            analysis_view=analysis_view,
            weighting=weighting,
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=first_assignment.coverage.token_coverage,
            coverage_b=second_assignment.coverage.token_coverage,
            unit_or_scale="canonical profile ID",
            note=(
                "Category fit is the primary rule-based archetype; nearest "
                "centroid is the secondary continuous-distance comparison."
            ),
        )
        rows.extend(
            (
                _row(
                    **common,
                    metric_id=f"poetry_id.{source_id}.category_fit",
                    metric="Category Fit Archetype",
                    value_a=first_assignment.categorical_archetype.name,
                    value_b=second_assignment.categorical_archetype.name,
                ),
                _row(
                    **common,
                    metric_id=f"poetry_id.{source_id}.nearest_centroid",
                    metric="Nearest Centroid Archetype",
                    value_a=first_assignment.nearest_centroid_archetype.name,
                    value_b=second_assignment.nearest_centroid_archetype.name,
                ),
            )
        )
    return rows


def _stopword_excluded_emotion_rows(
    comparison: PoemComparison,
    *,
    weighting: str,
) -> list[PoemComparisonRow]:
    """Derive stopword-excluded NRC rows from the published match audit."""

    rows: list[PoemComparisonRow] = []
    first_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.first.results
    }
    second_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.second.results
    }
    for lexicon_id in sorted(set(first_by_id) & set(second_by_id)):
        first = first_by_id[lexicon_id]
        second = second_by_id[lexicon_id]
        source = first.lexicon_metadata.display_name
        retained_a = tuple(
            item
            for item in first.matches
            if item.included and item.included_in_stopword_view
        )
        retained_b = tuple(
            item
            for item in second.matches
            if item.included and item.included_in_stopword_view
        )
        coverage_a = first.stopword_coverage
        coverage_b = second.stopword_coverage
        eligible_a = (
            (
                coverage_a.eligible_token_count
                if weighting == "token"
                else coverage_a.eligible_unique_type_count
            )
            if coverage_a is not None
            else 0
        )
        eligible_b = (
            (
                coverage_b.eligible_token_count
                if weighting == "token"
                else coverage_b.eligible_unique_type_count
            )
            if coverage_b is not None
            else 0
        )
        denominator_a = f"{eligible_a} stopword-excluded lexical {weighting}s"
        denominator_b = f"{eligible_b} stopword-excluded lexical {weighting}s"

        categories = sorted(
            {item.category for item in first.category_statistics}
            | {item.category for item in second.category_statistics}
        )
        for category in categories:
            category_a = tuple(
                item for item in retained_a if category in item.associations
            )
            category_b = tuple(
                item for item in retained_b if category in item.associations
            )
            count_a = (
                len(category_a)
                if weighting == "token"
                else len(
                    {
                        item.matched_lookup_form
                        for item in category_a
                        if item.matched_lookup_form
                    }
                )
            )
            count_b = (
                len(category_b)
                if weighting == "token"
                else len(
                    {
                        item.matched_lookup_form
                        for item in category_b
                        if item.matched_lookup_form
                    }
                )
            )
            rows.append(
                _row(
                    section="Affective Evidence",
                    source=source,
                    analysis_view="stopwords_excluded",
                    weighting=weighting,
                    metric_id=f"emotion.{lexicon_id}.{category}.proportion",
                    metric=f"{category.title()} association proportion",
                    value_a=count_a / eligible_a if eligible_a else None,
                    value_b=count_b / eligible_b if eligible_b else None,
                    unit_or_scale="proportion",
                    denominator_a=denominator_a,
                    denominator_b=denominator_b,
                    note=(
                        "NRC associations are multi-label and need not sum to one. "
                        "This view excludes active stopwords from its denominator."
                    ),
                )
            )

        intensity_categories = sorted(
            {item.category for item in first.intensity_statistics}
            & {item.category for item in second.intensity_statistics}
        )
        for category in intensity_categories:
            def retained_values(matches) -> tuple[float, ...]:
                pairs = [
                    (
                        item.matched_lookup_form or item.matched_term or "",
                        float(item.intensity_map()[category]),
                    )
                    for item in matches
                    if category in item.intensity_map()
                ]
                if weighting == "type":
                    pairs = list(dict(pairs).items())
                return tuple(value for _, value in pairs)

            values_a = retained_values(retained_a)
            values_b = retained_values(retained_b)
            mean_a = statistics.fmean(values_a) if values_a else None
            mean_b = statistics.fmean(values_b) if values_b else None
            sd_a = statistics.pstdev(values_a) if len(values_a) > 1 else None
            sd_b = statistics.pstdev(values_b) if len(values_b) > 1 else None
            pair_denominator_a = f"{len(values_a)} matched pairs"
            pair_denominator_b = f"{len(values_b)} matched pairs"
            rows.extend(
                (
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view="stopwords_excluded",
                        weighting=weighting,
                        metric_id=(
                            f"emotion_intensity.{lexicon_id}.{category}.mean"
                        ),
                        metric=f"Mean matched {category} intensity",
                        value_a=mean_a,
                        value_b=mean_b,
                        unit_or_scale="source 0-1",
                        denominator_a=pair_denominator_a,
                        denominator_b=pair_denominator_b,
                        note=(
                            "Absent word-emotion pairs remain missing, not zero; "
                            "active stopwords are excluded."
                        ),
                    ),
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view="stopwords_excluded",
                        weighting=weighting,
                        metric_id=(
                            "emotion_intensity."
                            f"{lexicon_id}.{category}.population_sd"
                        ),
                        metric=(
                            f"{category.title()} intensity population standard "
                            "deviation"
                        ),
                        value_a=sd_a,
                        value_b=sd_b,
                        unit_or_scale="source-scale points",
                        denominator_a=pair_denominator_a,
                        denominator_b=pair_denominator_b,
                        note="Within-poem dispersion across retained source pairs.",
                    ),
                )
            )
    return rows


def _emotion_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    if analysis_view != "all_matched":
        return _stopword_excluded_emotion_rows(
            comparison,
            weighting=weighting,
        )
    rows = []
    first_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.first.results
    }
    second_by_id = {
        result.lexicon_metadata.lexicon_id: result
        for result in comparison.second.results
    }
    for lexicon_id in sorted(set(first_by_id) & set(second_by_id)):
        first = first_by_id[lexicon_id]
        second = second_by_id[lexicon_id]
        source = first.lexicon_metadata.display_name
        categories_a = {row.category: row for row in first.category_statistics}
        categories_b = {row.category: row for row in second.category_statistics}
        for category in sorted(set(categories_a) | set(categories_b)):
            a = categories_a.get(category)
            b = categories_b.get(category)
            value_a = (
                (
                    a.proportion_of_lexical_tokens
                    if weighting == "token"
                    else a.proportion_of_unique_lexical_types
                )
                if a
                else 0.0
            )
            value_b = (
                (
                    b.proportion_of_lexical_tokens
                    if weighting == "token"
                    else b.proportion_of_unique_lexical_types
                )
                if b
                else 0.0
            )
            rows.append(
                _row(
                    section="Affective Evidence",
                    source=source,
                    analysis_view=analysis_view,
                    weighting=weighting,
                    metric_id=f"emotion.{lexicon_id}.{category}.proportion",
                    metric=f"{category.title()} association proportion",
                    value_a=value_a,
                    value_b=value_b,
                    unit_or_scale="proportion",
                    denominator_a=(
                        "all lexical tokens"
                        if weighting == "token"
                        else "unique lexical surface types"
                    ),
                    denominator_b=(
                        "all lexical tokens"
                        if weighting == "token"
                        else "unique lexical surface types"
                    ),
                    note="NRC associations are multi-label and need not sum to one.",
                )
            )
        intensity_a = {row.category: row for row in first.intensity_statistics}
        intensity_b = {row.category: row for row in second.intensity_statistics}
        for category in sorted(set(intensity_a) & set(intensity_b)):
            a = intensity_a[category]
            b = intensity_b[category]
            stats_a = a.token_weighted if weighting == "token" else a.type_weighted
            stats_b = b.token_weighted if weighting == "token" else b.type_weighted
            rows.extend(
                (
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=f"emotion_intensity.{lexicon_id}.{category}.mean",
                        metric=f"Mean matched {category} intensity",
                        value_a=stats_a.mean,
                        value_b=stats_b.mean,
                        unit_or_scale="source 0–1",
                        denominator_a=f"{stats_a.count} matched pairs",
                        denominator_b=f"{stats_b.count} matched pairs",
                        note="Absent word-emotion pairs remain missing, not zero.",
                    ),
                    _row(
                        section="Affective Evidence",
                        source=source,
                        analysis_view=analysis_view,
                        weighting=weighting,
                        metric_id=f"emotion_intensity.{lexicon_id}.{category}.population_sd",
                        metric=f"{category.title()} intensity population standard deviation",
                        value_a=stats_a.population_standard_deviation,
                        value_b=stats_b.population_standard_deviation,
                        unit_or_scale="source-scale points",
                        denominator_a=f"{stats_a.count} matched pairs",
                        denominator_b=f"{stats_b.count} matched pairs",
                        note="Within-poem dispersion across supplied source pairs.",
                    ),
                )
            )
    return rows


def _canonical_profile_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    """Compare retained configurable evidence under one canonical profile."""

    from versevad.analysis_profiles import (
        AggregationWeighting,
        AnalysisProfile,
        LexicalScope,
    )
    from versevad.workspace_profiles import workspace_profile_metrics

    scope = {
        "all_matched": LexicalScope.ALL_LEXICAL,
        "stopwords_excluded": LexicalScope.STOPWORD_EXCLUDED,
        "content_words": LexicalScope.CONTENT_WORDS,
    }[analysis_view]
    profile = AnalysisProfile(
        scope,
        AggregationWeighting.TYPE if weighting == "type" else AggregationWeighting.TOKEN,
    )
    first = {
        (row.module_id, row.source_id, row.metric_id): row
        for row in workspace_profile_metrics(comparison.first)
        if row.profile == profile
    }
    second = {
        (row.module_id, row.source_id, row.metric_id): row
        for row in workspace_profile_metrics(comparison.second)
        if row.profile == profile
    }
    section_by_module = {
        "vad": "Affective Evidence",
        "emotion_association": "Affective Evidence",
        "emotion_intensity": "Affective Evidence",
        "concreteness": "Lexical Character, Imagery & Embodiment",
        "frequency": "Lexical Character, Imagery & Embodiment",
        "aoa": "Lexical Character, Imagery & Embodiment",
        "sensorimotor": "Lexical Character, Imagery & Embodiment",
        "word_length": "Structure",
    }
    output: list[PoemComparisonRow] = []
    for key in sorted(set(first) & set(second)):
        row_a = first[key]
        row_b = second[key]
        if row_a.module_id == "vad":
            # VAD retains its established public metric IDs and complete
            # midpoint/volatility family in _vad_rows below.
            continue
        section = section_by_module.get(row_a.module_id, "Structure")
        type_weighted = weighting == "type"
        matched_a = (
            row_a.coverage.matched_type_count
            if type_weighted
            else row_a.coverage.matched_token_count
        )
        eligible_a = (
            row_a.coverage.eligible_type_count
            if type_weighted
            else row_a.coverage.eligible_token_count
        )
        matched_b = (
            row_b.coverage.matched_type_count
            if type_weighted
            else row_b.coverage.matched_token_count
        )
        eligible_b = (
            row_b.coverage.eligible_type_count
            if type_weighted
            else row_b.coverage.eligible_token_count
        )
        evidence_unit = "types" if type_weighted else "tokens"
        denominator_a = (
            f"{row_a.observation_count} observations; "
            f"{matched_a}/{eligible_a} eligible {evidence_unit} matched"
        )
        denominator_b = (
            f"{row_b.observation_count} observations; "
            f"{matched_b}/{eligible_b} eligible {evidence_unit} matched"
        )
        common = dict(
            section=section,
            source=row_a.source_label,
            analysis_view=analysis_view,
            weighting=weighting,
            denominator_a=denominator_a,
            denominator_b=denominator_b,
            coverage_a=(
                row_a.coverage.type_coverage
                if type_weighted
                else row_a.coverage.token_coverage
            ),
            coverage_b=(
                row_b.coverage.type_coverage
                if type_weighted
                else row_b.coverage.token_coverage
            ),
            note=(
                "Post-analysis aggregation from retained evidence; scope-relative "
                "coverage excludes out-of-scope tokens from the denominator."
            ),
        )
        metric_base = row_a.metric_id
        metric_statistic = "mean"
        module_prefix = row_a.module_id
        metric_label = row_a.metric_label
        if row_a.module_id == "emotion_association":
            module_prefix = "emotion"
            metric_base = metric_base.removesuffix("_association")
            metric_statistic = "proportion"
        elif row_a.module_id == "emotion_intensity":
            metric_base = metric_base.removesuffix("_intensity")
        output.append(
            _row(
                **common,
                metric_id=(
                    f"{module_prefix}.{row_a.source_id}.{metric_base}."
                    f"{metric_statistic}"
                ),
                metric=metric_label,
                value_a=row_a.value,
                value_b=row_b.value,
                unit_or_scale=row_a.unit,
            )
        )
        if (
            row_a.population_standard_deviation is not None
            or row_b.population_standard_deviation is not None
        ):
            output.append(
                _row(
                    **common,
                    metric_id=(
                        f"{module_prefix}.{row_a.source_id}.{metric_base}.population_sd"
                    ),
                    metric=f"{row_a.metric_label} population standard deviation",
                    value_a=row_a.population_standard_deviation,
                    value_b=row_b.population_standard_deviation,
                    unit_or_scale=row_a.unit,
                )
            )
        capabilities = metric_capabilities(row_a.module_id)
        if capabilities.supports_raw_accumulation and (
            row_a.cumulative_value is not None or row_b.cumulative_value is not None
        ):
            output.append(
                _row(
                    **common,
                    metric_id=(
                        f"{module_prefix}.{row_a.source_id}.{metric_base}.cumulative"
                    ),
                    metric=(
                        f"{row_a.metric_label} cumulative emotion intensity load"
                        if row_a.module_id == "emotion_intensity"
                        else f"{row_a.metric_label} method-defined cumulative load"
                    ),
                    value_a=row_a.cumulative_value,
                    value_b=row_b.cumulative_value,
                    unit_or_scale=f"summed {row_a.unit}",
                )
            )
    return output


def comparison_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> tuple[PoemComparisonRow, ...]:
    if analysis_view not in {
        "all_matched",
        "stopwords_excluded",
        "content_words",
    }:
        raise ValueError(f"Unknown comparison analysis view: {analysis_view}")
    if weighting not in {"token", "type"}:
        raise ValueError(f"Unknown comparison weighting: {weighting}")
    rows = [
        *_vad_rows(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        ),
        *_canonical_profile_rows(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        ),
        *_poetry_id_rows(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        ),
        *_method_fixed_rows(comparison),
    ]
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.section,
                row.source.casefold(),
                row.metric.casefold(),
                row.metric_id,
            ),
        )
    )


def comparison_set_rows(
    comparison_set: PoemComparisonSet,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> tuple[PoemComparisonSetRow, ...]:
    """Return source-compatible metric rows across a two-to-ten-poem set."""

    analyses = comparison_set.analyses
    rows_by_poem: list[dict[tuple[str, ...], PoemComparisonRow]] = []
    ordered_keys: dict[tuple[str, ...], None] = {}
    anchor = analyses[0]
    for analysis in analyses:
        pair_rows = comparison_rows(
            build_poem_comparison(anchor, analysis),
            analysis_view=analysis_view,
            weighting=weighting,
        )
        indexed: dict[tuple[str, ...], PoemComparisonRow] = {}
        for row in pair_rows:
            key = (
                row.section,
                row.source,
                row.analysis_view,
                row.weighting,
                row.metric_id,
                row.metric,
                row.unit_or_scale,
            )
            indexed[key] = row
            ordered_keys.setdefault(key, None)
        rows_by_poem.append(indexed)

    result: list[PoemComparisonSetRow] = []
    for key in ordered_keys:
        template = next(
            indexed[key] for indexed in rows_by_poem if key in indexed
        )
        values: list[PoemComparisonSetValue] = []
        numeric_values: list[float] = []
        categories: list[str] = []
        for analysis, indexed in zip(analyses, rows_by_poem, strict=True):
            row = indexed.get(key)
            value = row.value_b if row is not None else None
            numeric = _numeric(value)
            if numeric is not None:
                numeric_values.append(numeric)
            elif isinstance(value, str) and value:
                categories.append(value)
            values.append(
                PoemComparisonSetValue(
                    poem_id=analysis.document.text_version_id,
                    title=analysis.request.title,
                    value=value,
                    denominator=row.denominator_b if row is not None else "",
                    coverage=row.coverage_b if row is not None else None,
                )
            )
        categorical_summary = ""
        if categories:
            counts = Counter(categories)
            most_common = counts.most_common()
            highest = most_common[0][1]
            leaders = [
                label for label, count in most_common if count == highest
            ]
            categorical_summary = (
                f"{leaders[0]} ({highest}/{len(categories)})"
                if len(leaders) == 1
                else f"Mixed ({len(categories)} contributing poems)"
            )
        numeric_mean = (
            statistics.fmean(numeric_values) if numeric_values else None
        )
        numeric_sd = (
            statistics.pstdev(numeric_values)
            if len(numeric_values) > 1
            else None
        )
        numeric_range = (
            max(numeric_values) - min(numeric_values)
            if len(numeric_values) > 1
            else None
        )
        result.append(
            PoemComparisonSetRow(
                section=template.section,
                source=template.source,
                analysis_view=template.analysis_view,
                weighting=template.weighting,
                metric_id=template.metric_id,
                metric=template.metric,
                values=tuple(values),
                numeric_mean=numeric_mean,
                numeric_population_standard_deviation=numeric_sd,
                contributing_poem_count=(
                    len(numeric_values) if numeric_values else len(categories)
                ),
                categorical_summary=categorical_summary,
                unit_or_scale=template.unit_or_scale,
                note=template.note,
                numeric_range=numeric_range,
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.section,
                row.source.casefold(),
                row.metric.casefold(),
                row.metric_id,
            ),
        )
    )


__all__ = [
    "PoemComparison",
    "PoemComparisonRow",
    "PoemComparisonSet",
    "PoemComparisonSetRow",
    "PoemComparisonSetValue",
    "build_poem_comparison",
    "build_poem_comparison_set",
    "comparison_rows",
    "comparison_set_rows",
]
