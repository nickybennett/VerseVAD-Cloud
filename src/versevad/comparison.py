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
    selected = [
        match
        for match in result.matches
        if match.included
        and match.normalized_scores is not None
        and (
            analysis_view == "all_matched"
            or match.included_in_stopword_view
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
        group_a = _vad_group(first, analysis_view, weighting)
        group_b = _vad_group(second, analysis_view, weighting)
        if group_a is None or group_b is None:
            continue
        source = first.lexicon_metadata.display_name
        coverage_a = _vad_coverage(first, analysis_view)
        coverage_b = _vad_coverage(second, analysis_view)
        matches_a = _selected_vad_matches(first, analysis_view, weighting)
        matches_b = _selected_vad_matches(second, analysis_view, weighting)
        denominator_a = f"{len(matches_a)} matched {weighting}-weighted observations"
        denominator_b = f"{len(matches_b)} matched {weighting}-weighted observations"
        for dimension in ("valence", "arousal", "dominance"):
            stats_a = getattr(group_a, dimension)
            stats_b = getattr(group_b, dimension)
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
                ("rating_total", "Rating total"),
                ("above_midpoint", "Above-midpoint load"),
                ("below_midpoint", "Below-midpoint load"),
                ("net_midpoint", "Net midpoint load"),
                ("absolute_midpoint", "Absolute midpoint load"),
                ("rating_total_per_100", "Rating total per 100 observations"),
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
                            "summed normalized ratings per 100 observations"
                            if key.endswith("per_100")
                            else "summed normalized ratings"
                        ),
                        denominator_a=denominator_a,
                        denominator_b=denominator_b,
                        coverage_a=coverage_a,
                        coverage_b=coverage_b,
                        note=(
                            "Raw loads retain length and repetition in the token "
                            "view; per-100 totals support length-normalized comparison."
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
        }
    above = sum(max(value - 0.5, 0.0) for value in numbers)
    below = sum(max(0.5 - value, 0.0) for value in numbers)
    total = sum(numbers)
    return {
        "rating_total": total,
        "above_midpoint": above,
        "below_midpoint": below,
        "net_midpoint": above - below,
        "absolute_midpoint": above + below,
        "rating_total_per_100": total / len(numbers) * 100,
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
    sd_a = statistics.pstdev(values_a) if values_a else None
    sd_b = statistics.pstdev(values_b) if values_b else None
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
        ("poetry_id", "Affective Evidence"),
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


def _emotion_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str,
    weighting: str,
) -> list[PoemComparisonRow]:
    if analysis_view != "all_matched":
        return []
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


def comparison_rows(
    comparison: PoemComparison,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> tuple[PoemComparisonRow, ...]:
    if analysis_view not in {"all_matched", "stopwords_excluded"}:
        raise ValueError(f"Unknown comparison analysis view: {analysis_view}")
    if weighting not in {"token", "type"}:
        raise ValueError(f"Unknown comparison weighting: {weighting}")
    rows = [
        *_vad_rows(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        ),
        *_emotion_rows(
            comparison,
            analysis_view=analysis_view,
            weighting=weighting,
        ),
        *_lexical_rows(
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
            else (0.0 if numeric_values else None)
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
