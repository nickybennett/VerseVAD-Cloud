"""Corpus-relative lexical frequency analysis using local SUBTLEX-US Zipf data."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from versevad import __version__
from versevad.adapters.subtlex_us import (
    SubtlexUsAdapter,
    SubtlexUsAdapterError,
    SubtlexUsEntry,
    SubtlexUsLexicon,
    SubtlexUsValidation,
)
from versevad.analysis.statistics import descriptive_statistics
from versevad.core.documents import StructuralUnitKind
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
from versevad.core.resources import (
    LocalResourceManager,
    ResourceProvenance,
    ResourceSpec,
    ResourceState,
    ResourceStatus,
)
from versevad.models import DescriptiveStatistics, TokenRecord
from versevad.normalization import (
    canonicalize_apostrophes,
    normalize_lookup,
    possessive_base,
)


SUBTLEX_US_RELATIVE_PATH = (
    "subtlex-us/SUBTLEX-US frequency list with PoS and Zipf information.xlsx"
)
SUBTLEX_US_SHA256 = (
    "3a8cb93a4e28988c2ce722a63f6b8d394acdc42ebe2ab6e1f0e484ee0d4167a7"
)
SUBTLEX_US_CITATION = (
    "Brysbaert, M., & New, B. (2009). Moving beyond Kucera and Francis: "
    "A critical evaluation of current word frequency norms and the "
    "introduction of a new and improved word frequency measure for American "
    "English. Behavior Research Methods, 41, 977-990. "
    "https://doi.org/10.3758/BRM.41.4.977; Zipf scale introduced by "
    "van Heuven, W. J. B., Mandera, P., Keuleers, E., & Brysbaert, M. "
    "(2014), https://doi.org/10.1080/17470218.2013.850521"
)
SUBTLEX_US_LICENSE_NOTICE = (
    "Official Ghent University research download retained locally. VerseVAD "
    "does not redistribute the workbook or substitute another frequency source."
)
SUBTLEX_US_SPEC = ResourceSpec(
    resource_id="subtlex-us-zipf-official",
    display_name="SUBTLEX-US word frequencies with Zipf values",
    relative_path=SUBTLEX_US_RELATIVE_PATH,
    version=(
        "Official 74,286-word SUBTLEX-US workbook with PoS and Zipf values; "
        "downloaded 2026-07-23"
    ),
    accepted_sha256=(SUBTLEX_US_SHA256,),
    minimum_bytes=10_000_000,
    citation=SUBTLEX_US_CITATION,
    license_notice=SUBTLEX_US_LICENSE_NOTICE,
)

CONTENT_WORD_POS = frozenset({"NOUN", "VERB", "ADJ", "ADV"})


class FrequencyModuleError(RuntimeError):
    """Plain-language module failure for the application boundary."""


class FrequencyMatchMethod(StrEnum):
    EXACT = "exact_surface"
    LEMMA = "lemma"
    DOCUMENTED_FALLBACK = "documented_fallback"
    UNMATCHED = "unmatched"
    NOT_ELIGIBLE = "not_eligible"


@dataclass(frozen=True)
class FrequencyConfiguration:
    """Explicit frequency matching, scope, coverage, and display-band choices."""

    rare_below: float = 3.0
    uncommon_below: float = 4.0
    moderately_common_below: float = 5.0
    very_common_min: float = 6.0
    exclude_proper_nouns: bool = False
    content_words_only: bool = False
    enable_lemma_fallback: bool = True
    minimum_matched_tokens: int = 3
    low_coverage_warning_threshold: float = 0.6
    top_term_count: int = 10
    rare_tail_count: int = 25
    scenario_id: str = "subtlex-us-frequency-v1"

    def __post_init__(self) -> None:
        thresholds = (
            self.rare_below,
            self.uncommon_below,
            self.moderately_common_below,
            self.very_common_min,
        )
        if any(not 1 <= threshold <= 8 for threshold in thresholds):
            raise ValueError("All Zipf thresholds must be between 1 and 8.")
        if thresholds != tuple(sorted(thresholds)) or len(set(thresholds)) != 4:
            raise ValueError("Zipf thresholds must be strictly increasing.")
        if self.minimum_matched_tokens < 1:
            raise ValueError("The minimum matched-token count must be at least 1.")
        if not 0 <= self.low_coverage_warning_threshold <= 1:
            raise ValueError("The low-coverage warning threshold must be 0-1.")
        if self.top_term_count < 1 or self.rare_tail_count < 1:
            raise ValueError("Term ranking limits must be at least 1.")
        if not self.scenario_id.strip():
            raise ValueError("A frequency scenario requires a stable ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"frequency-config-v1:{digest}"

    @property
    def scope_label(self) -> str:
        return (
            "Content words only (NOUN, VERB, ADJ, ADV)"
            if self.content_words_only
            else "All lexical tokens"
        )


@dataclass(frozen=True)
class FrequencyTokenRating:
    token_id: str
    token_position: int
    surface_form: str
    normalized_form: str
    lemma: str
    normalized_lemma: str
    part_of_speech: str
    line_number: int
    stanza_number: int
    context: str
    is_lexical: bool
    is_proper_noun: bool
    eligible: bool
    included: bool
    match_method: FrequencyMatchMethod
    matched_source_term: str | None
    matched_lookup_form: str | None
    source_row: int | None
    zipf_value: float | None
    frequency_count: int | None
    frequency_per_million: float | None
    contextual_diversity_count: int | None
    contextual_diversity_percent: float | None
    lowercase_frequency_count: int | None
    lowercase_contextual_diversity_count: int | None
    dominant_source_pos: str | None
    dominant_source_pos_frequency: int | None
    dominant_source_pos_proportion: float | None
    reason: str


@dataclass(frozen=True)
class FrequencyBandSummary:
    band_id: str
    label: str
    lower_bound: float | None
    lower_inclusive: bool
    upper_bound: float | None
    upper_inclusive: bool
    token_count: int
    proportion: float | None


@dataclass(frozen=True)
class FrequencySummary:
    statistics: DescriptiveStatistics
    interquartile_range: float | None
    eligible_token_count: int
    matched_token_count: int
    unmatched_token_count: int
    token_coverage: float | None
    eligible_unique_type_count: int
    matched_unique_type_count: int
    unmatched_unique_type_count: int
    unique_type_coverage: float | None
    scope_label: str
    minimum_matched_tokens: int
    is_sparse: bool
    bands: tuple[FrequencyBandSummary, ...]


@dataclass(frozen=True)
class FrequencyGroupSummary:
    scope: str
    scope_id: str
    ordinal: int
    label: str
    source_text: str
    statistics: DescriptiveStatistics
    interquartile_range: float | None
    eligible_token_count: int
    matched_token_count: int
    unmatched_token_count: int
    token_coverage: float | None
    eligible_unique_type_count: int
    matched_unique_type_count: int
    unique_type_coverage: float | None


@dataclass(frozen=True)
class FrequencyTermSummary:
    source_term: str
    lookup_form: str
    zipf_value: float
    frequency_count: int
    frequency_per_million: float
    contextual_diversity_count: int
    contextual_diversity_percent: float
    matched_token_occurrences: int
    surface_forms: tuple[str, ...]
    part_of_speech_tags: tuple[str, ...]
    source_row: int
    dominant_source_pos: str


@dataclass(frozen=True)
class FrequencyAnalysisResult:
    module_result: ModuleResult
    configuration: FrequencyConfiguration
    resource_status: ResourceStatus
    resource_validation: SubtlexUsValidation
    summary: FrequencySummary
    part_of_speech_summaries: tuple[FrequencyGroupSummary, ...]
    line_summaries: tuple[FrequencyGroupSummary, ...]
    stanza_summaries: tuple[FrequencyGroupSummary, ...]
    term_summaries: tuple[FrequencyTermSummary, ...]
    lowest_frequency_terms: tuple[FrequencyTermSummary, ...]
    highest_frequency_terms: tuple[FrequencyTermSummary, ...]
    rare_word_tail: tuple[FrequencyTermSummary, ...]
    token_audit: tuple[FrequencyTokenRating, ...]

    def __post_init__(self) -> None:
        eligible = sum(row.eligible for row in self.token_audit)
        matched = sum(row.included for row in self.token_audit)
        if (
            self.summary.eligible_token_count != eligible
            or self.summary.matched_token_count != matched
        ):
            raise ValueError("Frequency summary counts must agree with the token audit.")
        if any(
            row.zipf_value is not None
            for row in self.token_audit
            if not row.included
        ):
            raise ValueError(
                "Unmatched or ineligible frequency rows cannot carry Zipf values."
            )


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _iqr(statistics: DescriptiveStatistics) -> float | None:
    if (
        statistics.first_quartile is None
        or statistics.third_quartile is None
    ):
        return None
    return statistics.third_quartile - statistics.first_quartile


def _matched_token(
    token: TokenRecord,
    entry: SubtlexUsEntry,
    method: FrequencyMatchMethod,
    reason: str,
) -> FrequencyTokenRating:
    return FrequencyTokenRating(
        token_id=token.token_id,
        token_position=token.token_position,
        surface_form=token.surface_form,
        normalized_form=token.normalized_form,
        lemma=token.lemma,
        normalized_lemma=token.normalized_lemma,
        part_of_speech=token.part_of_speech,
        line_number=token.line_number,
        stanza_number=token.stanza_number,
        context=token.context,
        is_lexical=token.is_lexical,
        is_proper_noun=token.is_proper_noun,
        eligible=True,
        included=True,
        match_method=method,
        matched_source_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        zipf_value=entry.zipf_value,
        frequency_count=entry.frequency_count,
        frequency_per_million=entry.frequency_per_million,
        contextual_diversity_count=entry.contextual_diversity_count,
        contextual_diversity_percent=entry.contextual_diversity_percent,
        lowercase_frequency_count=entry.lowercase_frequency_count,
        lowercase_contextual_diversity_count=(
            entry.lowercase_contextual_diversity_count
        ),
        dominant_source_pos=entry.dominant_source_pos,
        dominant_source_pos_frequency=entry.dominant_source_pos_frequency,
        dominant_source_pos_proportion=entry.dominant_source_pos_proportion,
        reason=reason,
    )


def _unmatched_token(
    token: TokenRecord,
    *,
    method: FrequencyMatchMethod,
    eligible: bool,
    reason: str,
) -> FrequencyTokenRating:
    return FrequencyTokenRating(
        token_id=token.token_id,
        token_position=token.token_position,
        surface_form=token.surface_form,
        normalized_form=token.normalized_form,
        lemma=token.lemma,
        normalized_lemma=token.normalized_lemma,
        part_of_speech=token.part_of_speech,
        line_number=token.line_number,
        stanza_number=token.stanza_number,
        context=token.context,
        is_lexical=token.is_lexical,
        is_proper_noun=token.is_proper_noun,
        eligible=eligible,
        included=False,
        match_method=method,
        matched_source_term=None,
        matched_lookup_form=None,
        source_row=None,
        zipf_value=None,
        frequency_count=None,
        frequency_per_million=None,
        contextual_diversity_count=None,
        contextual_diversity_percent=None,
        lowercase_frequency_count=None,
        lowercase_contextual_diversity_count=None,
        dominant_source_pos=None,
        dominant_source_pos_frequency=None,
        dominant_source_pos_proportion=None,
        reason=reason,
    )


def _ineligible_reason(
    token: TokenRecord,
    configuration: FrequencyConfiguration,
) -> str | None:
    if not token.is_lexical:
        kind = "numeric" if token.is_numeric else "punctuation or non-lexical"
        return f"Excluded from the lexical denominator as {kind}."
    if configuration.exclude_proper_nouns and token.is_proper_noun:
        return (
            "Excluded by the configured proper-name policy because names can "
            "inflate subtitle-corpus counts."
        )
    if (
        configuration.content_words_only
        and token.part_of_speech not in CONTENT_WORD_POS
    ):
        return (
            "Excluded by the optional content-word-only scope. Eligible model "
            "tags are NOUN, VERB, ADJ, and ADV; auxiliaries and function-word "
            "tags remain outside this denominator."
        )
    return None


def _token_audit(
    module_input: ModuleInput,
    lexicon: SubtlexUsLexicon,
    configuration: FrequencyConfiguration,
) -> tuple[FrequencyTokenRating, ...]:
    rows = []
    for token in module_input.tokens:
        ineligible_reason = _ineligible_reason(token, configuration)
        if ineligible_reason is not None:
            rows.append(
                _unmatched_token(
                    token,
                    method=FrequencyMatchMethod.NOT_ELIGIBLE,
                    eligible=False,
                    reason=ineligible_reason,
                )
            )
            continue

        surface_lookup = normalize_lookup(
            token.normalized_form or token.surface_form
        )
        exact_entry = lexicon.lookup(surface_lookup)
        if exact_entry is not None:
            rows.append(
                _matched_token(
                    token,
                    exact_entry,
                    FrequencyMatchMethod.EXACT,
                    (
                        "Exact normalized word form matched before any lemma or "
                        "fallback was considered."
                    ),
                )
            )
            continue

        lemma_lookup = normalize_lookup(token.normalized_lemma or token.lemma)
        lemma_entry = (
            lexicon.lookup(lemma_lookup)
            if configuration.enable_lemma_fallback
            and lemma_lookup
            and lemma_lookup != surface_lookup
            else None
        )
        if lemma_entry is not None:
            rows.append(
                _matched_token(
                    token,
                    lemma_entry,
                    FrequencyMatchMethod.LEMMA,
                    (
                        "No exact word-form entry was available; the installed "
                        "model's normalized lemma matched. This remains distinct "
                        "from an observed word-form frequency."
                    ),
                )
            )
            continue

        fallback_candidates: list[tuple[str, str]] = []
        canonical_surface = normalize_lookup(
            canonicalize_apostrophes(surface_lookup)
        )
        if canonical_surface and canonical_surface != surface_lookup:
            fallback_candidates.append(
                (canonical_surface, "canonicalized apostrophe form")
            )
        possessive_lookup = possessive_base(surface_lookup)
        if possessive_lookup:
            fallback_candidates.append(
                (possessive_lookup, "conservative possessive base")
            )
        canonical_lemma = normalize_lookup(canonicalize_apostrophes(lemma_lookup))
        if (
            configuration.enable_lemma_fallback
            and canonical_lemma
            and canonical_lemma not in {surface_lookup, lemma_lookup}
        ):
            fallback_candidates.append(
                (canonical_lemma, "canonicalized lemma apostrophe form")
            )
        tried = {surface_lookup, lemma_lookup}
        fallback_match: tuple[SubtlexUsEntry, str] | None = None
        for candidate, label in fallback_candidates:
            if candidate in tried:
                continue
            tried.add(candidate)
            entry = lexicon.lookup(candidate)
            if entry is not None:
                fallback_match = (entry, label)
                break
        if fallback_match is not None:
            entry, label = fallback_match
            rows.append(
                _matched_token(
                    token,
                    entry,
                    FrequencyMatchMethod.DOCUMENTED_FALLBACK,
                    (
                        "No exact word-form or enabled lemma entry was available; "
                        f"the documented {label} matched."
                    ),
                )
            )
            continue
        rows.append(
            _unmatched_token(
                token,
                method=FrequencyMatchMethod.UNMATCHED,
                eligible=True,
                reason=(
                    "No exact word-form, enabled lemma, or documented conservative "
                    "fallback entry was found. Frequency remains missing, not zero."
                ),
            )
        )
    return tuple(rows)


def _bands(
    values: tuple[float, ...],
    configuration: FrequencyConfiguration,
) -> tuple[FrequencyBandSummary, ...]:
    definitions = (
        (
            "rare",
            "Rare",
            None,
            False,
            configuration.rare_below,
            False,
        ),
        (
            "uncommon",
            "Uncommon",
            configuration.rare_below,
            True,
            configuration.uncommon_below,
            False,
        ),
        (
            "moderately_common",
            "Moderately common",
            configuration.uncommon_below,
            True,
            configuration.moderately_common_below,
            False,
        ),
        (
            "common",
            "Common",
            configuration.moderately_common_below,
            True,
            configuration.very_common_min,
            False,
        ),
        (
            "very_common",
            "Very common",
            configuration.very_common_min,
            True,
            None,
            False,
        ),
    )
    rows = []
    for (
        band_id,
        label,
        lower,
        lower_inclusive,
        upper,
        upper_inclusive,
    ) in definitions:
        count = sum(
            (lower is None or value >= lower)
            and (upper is None or value < upper)
            for value in values
        )
        rows.append(
            FrequencyBandSummary(
                band_id=band_id,
                label=label,
                lower_bound=lower,
                lower_inclusive=lower_inclusive,
                upper_bound=upper,
                upper_inclusive=upper_inclusive,
                token_count=count,
                proportion=_rate(count, len(values)),
            )
        )
    return tuple(rows)


def _summary(
    audit: tuple[FrequencyTokenRating, ...],
    configuration: FrequencyConfiguration,
) -> FrequencySummary:
    eligible = tuple(row for row in audit if row.eligible)
    matched = tuple(
        row
        for row in eligible
        if row.included and row.zipf_value is not None
    )
    values = tuple(
        row.zipf_value for row in matched if row.zipf_value is not None
    )
    statistics = descriptive_statistics(values)
    eligible_types = {row.normalized_form for row in eligible}
    matched_types = {row.normalized_form for row in matched}
    return FrequencySummary(
        statistics=statistics,
        interquartile_range=_iqr(statistics),
        eligible_token_count=len(eligible),
        matched_token_count=len(matched),
        unmatched_token_count=len(eligible) - len(matched),
        token_coverage=_rate(len(matched), len(eligible)),
        eligible_unique_type_count=len(eligible_types),
        matched_unique_type_count=len(matched_types),
        unmatched_unique_type_count=len(eligible_types - matched_types),
        unique_type_coverage=_rate(len(matched_types), len(eligible_types)),
        scope_label=configuration.scope_label,
        minimum_matched_tokens=configuration.minimum_matched_tokens,
        is_sparse=len(matched) < configuration.minimum_matched_tokens,
        bands=_bands(values, configuration),
    )


def _group_summary(
    rows: Iterable[FrequencyTokenRating],
    *,
    scope: str,
    scope_id: str,
    ordinal: int,
    label: str,
    source_text: str,
) -> FrequencyGroupSummary:
    row_tuple = tuple(rows)
    eligible = tuple(row for row in row_tuple if row.eligible)
    matched = tuple(
        row
        for row in eligible
        if row.included and row.zipf_value is not None
    )
    statistics = descriptive_statistics(
        row.zipf_value for row in matched if row.zipf_value is not None
    )
    eligible_types = {row.normalized_form for row in eligible}
    matched_types = {row.normalized_form for row in matched}
    return FrequencyGroupSummary(
        scope=scope,
        scope_id=scope_id,
        ordinal=ordinal,
        label=label,
        source_text=source_text,
        statistics=statistics,
        interquartile_range=_iqr(statistics),
        eligible_token_count=len(eligible),
        matched_token_count=len(matched),
        unmatched_token_count=len(eligible) - len(matched),
        token_coverage=_rate(len(matched), len(eligible)),
        eligible_unique_type_count=len(eligible_types),
        matched_unique_type_count=len(matched_types),
        unique_type_coverage=_rate(len(matched_types), len(eligible_types)),
    )


def _structural_summaries(
    module_input: ModuleInput,
    audit: tuple[FrequencyTokenRating, ...],
    kind: StructuralUnitKind,
) -> tuple[FrequencyGroupSummary, ...]:
    scope = kind.value
    number_field = (
        "line_number" if kind is StructuralUnitKind.LINE else "stanza_number"
    )
    if module_input.poem_document is not None:
        units = (
            module_input.poem_document.lines
            if kind is StructuralUnitKind.LINE
            else module_input.poem_document.stanzas
        )
        return tuple(
            _group_summary(
                (
                    row
                    for row in audit
                    if getattr(row, number_field) == unit.ordinal
                ),
                scope=scope,
                scope_id=unit.unit_id,
                ordinal=unit.ordinal,
                label=f"{scope.title()} {unit.ordinal}",
                source_text=unit.content_text,
            )
            for unit in units
        )
    ordinals = sorted({getattr(row, number_field) for row in audit})
    return tuple(
        _group_summary(
            (row for row in audit if getattr(row, number_field) == ordinal),
            scope=scope,
            scope_id=f"{scope}-{ordinal}",
            ordinal=ordinal,
            label=f"{scope.title()} {ordinal}",
            source_text="",
        )
        for ordinal in ordinals
    )


def _pos_summaries(
    audit: tuple[FrequencyTokenRating, ...],
) -> tuple[FrequencyGroupSummary, ...]:
    tags = sorted({row.part_of_speech or "X" for row in audit if row.eligible})
    return tuple(
        _group_summary(
            (
                row
                for row in audit
                if row.eligible and (row.part_of_speech or "X") == tag
            ),
            scope="part_of_speech",
            scope_id=tag,
            ordinal=index,
            label=tag,
            source_text="",
        )
        for index, tag in enumerate(tags, start=1)
    )


def _term_summaries(
    audit: tuple[FrequencyTokenRating, ...],
) -> tuple[FrequencyTermSummary, ...]:
    by_lookup: dict[str, list[FrequencyTokenRating]] = defaultdict(list)
    for row in audit:
        if row.included and row.matched_lookup_form is not None:
            by_lookup[row.matched_lookup_form].append(row)
    summaries = []
    for lookup_form, rows in by_lookup.items():
        first = rows[0]
        assert first.matched_source_term is not None
        assert first.zipf_value is not None
        assert first.frequency_count is not None
        assert first.frequency_per_million is not None
        assert first.contextual_diversity_count is not None
        assert first.contextual_diversity_percent is not None
        assert first.source_row is not None
        assert first.dominant_source_pos is not None
        summaries.append(
            FrequencyTermSummary(
                source_term=first.matched_source_term,
                lookup_form=lookup_form,
                zipf_value=first.zipf_value,
                frequency_count=first.frequency_count,
                frequency_per_million=first.frequency_per_million,
                contextual_diversity_count=first.contextual_diversity_count,
                contextual_diversity_percent=(
                    first.contextual_diversity_percent
                ),
                matched_token_occurrences=len(rows),
                surface_forms=tuple(
                    sorted({row.surface_form for row in rows}, key=str.casefold)
                ),
                part_of_speech_tags=tuple(
                    sorted({row.part_of_speech or "X" for row in rows})
                ),
                source_row=first.source_row,
                dominant_source_pos=first.dominant_source_pos,
            )
        )
    return tuple(
        sorted(summaries, key=lambda item: item.source_term.casefold())
    )


def _warnings(
    summary: FrequencySummary,
    audit: tuple[FrequencyTokenRating, ...],
    configuration: FrequencyConfiguration,
) -> tuple[ModuleWarning, ...]:
    warnings = []
    if not summary.eligible_token_count:
        warnings.append(
            ModuleWarning(
                code="no_eligible_tokens",
                message=(
                    "No tokens were eligible under the selected frequency scope. "
                    "Aggregates and coverage rates remain missing."
                ),
                severity=WarningSeverity.INFORMATION,
            )
        )
    elif not summary.matched_token_count:
        warnings.append(
            ModuleWarning(
                code="no_matched_tokens",
                message=(
                    "No eligible word found a SUBTLEX-US entry. Aggregate values "
                    "remain missing rather than being set to Zipf zero."
                ),
            )
        )
    if (
        summary.token_coverage is not None
        and summary.token_coverage < configuration.low_coverage_warning_threshold
    ):
        warnings.append(
            ModuleWarning(
                code="low_coverage",
                message=(
                    "Frequency coverage is below the configured caution threshold "
                    f"of {configuration.low_coverage_warning_threshold:.0%}. "
                    "Inspect unmatched vocabulary before interpreting aggregates."
                ),
                technical_detail=(
                    f"{summary.matched_token_count} of "
                    f"{summary.eligible_token_count} eligible tokens matched."
                ),
            )
        )
    if summary.is_sparse:
        warnings.append(
            ModuleWarning(
                code="sparse_matched_sample",
                message=(
                    "Fewer than the configured minimum number of matched tokens "
                    "contributed. Defined statistics should be treated as sparse."
                ),
                technical_detail=(
                    f"Matched {summary.matched_token_count}; configured minimum "
                    f"{configuration.minimum_matched_tokens}."
                ),
            )
        )
    if configuration.content_words_only:
        warnings.append(
            ModuleWarning(
                code="content_words_only_scope",
                message=(
                    "The optional content-word-only scope is active. Only "
                    "model-tagged NOUN, VERB, ADJ, and ADV tokens contribute; "
                    "function words, auxiliaries, and punctuation are excluded."
                ),
                severity=WarningSeverity.INFORMATION,
            )
        )
    lemma_count = sum(
        row.match_method is FrequencyMatchMethod.LEMMA for row in audit
    )
    if lemma_count:
        warnings.append(
            ModuleWarning(
                code="lemma_frequency_fallback",
                message=(
                    "Some observed word forms were absent and used an explicitly "
                    "audited lemma fallback. These are lemma-entry substitutes, "
                    "not exact observed-form frequencies."
                ),
                severity=WarningSeverity.INFORMATION,
                technical_detail=f"{lemma_count} token occurrence(s) used a lemma.",
            )
        )
    return tuple(warnings)


def _module_metrics(
    summary: FrequencySummary,
    groups: tuple[FrequencyGroupSummary, ...],
) -> tuple[ModuleMetric, ...]:
    statistics = summary.statistics
    document_values = (
        ("frequency.median_zipf", statistics.median, "SUBTLEX-US Zipf"),
        ("frequency.mean_zipf", statistics.mean, "SUBTLEX-US Zipf"),
        (
            "frequency.population_standard_deviation",
            statistics.population_standard_deviation,
            "Zipf points",
        ),
        ("frequency.minimum_zipf", statistics.minimum, "SUBTLEX-US Zipf"),
        ("frequency.first_quartile_zipf", statistics.first_quartile, "SUBTLEX-US Zipf"),
        ("frequency.third_quartile_zipf", statistics.third_quartile, "SUBTLEX-US Zipf"),
        ("frequency.interquartile_range", summary.interquartile_range, "Zipf points"),
        ("frequency.maximum_zipf", statistics.maximum, "SUBTLEX-US Zipf"),
    )
    metrics = [
        ModuleMetric(
            metric_id=metric_id,
            value=value,
            layer=ResultLayer.COMPUTED_SUMMARY,
            unit=unit,
            weighting="matched token occurrences",
            denominator=(
                f"{summary.matched_token_count} matched eligible token occurrences"
            ),
            note=(
                "Median is the primary summary because unusually rare terms can "
                "pull the mean downward."
                if metric_id == "frequency.median_zipf"
                else ""
            ),
        )
        for metric_id, value, unit in document_values
    ]
    metrics.extend(
        ModuleMetric(
            metric_id=f"frequency.band.{band.band_id}.proportion",
            value=band.proportion,
            layer=ResultLayer.COMPUTED_SUMMARY,
            unit="proportion",
            weighting="matched token occurrences",
            denominator=f"{summary.matched_token_count} matched tokens",
            note="Configurable VerseVAD orientation band.",
        )
        for band in summary.bands
    )
    for group in groups:
        metrics.extend(
            (
                ModuleMetric(
                    metric_id="frequency.median_zipf",
                    value=group.statistics.median,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="SUBTLEX-US Zipf",
                    weighting="matched token occurrences",
                    denominator=f"{group.matched_token_count} matched tokens",
                ),
                ModuleMetric(
                    metric_id="frequency.mean_zipf",
                    value=group.statistics.mean,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="SUBTLEX-US Zipf",
                    weighting="matched token occurrences",
                    denominator=f"{group.matched_token_count} matched tokens",
                ),
                ModuleMetric(
                    metric_id="frequency.token_coverage",
                    value=group.token_coverage,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="proportion",
                    denominator=f"{group.eligible_token_count} eligible tokens",
                ),
            )
        )
    return tuple(metrics)


@lru_cache(maxsize=12)
def _load_cached(path: str, source_sha256: str) -> SubtlexUsLexicon:
    del source_sha256
    return SubtlexUsAdapter().load(Path(path))


class FrequencyModule:
    """Framework-independent Stage 3 module backed by pinned SUBTLEX-US data."""

    name = "lexical_frequency"
    version = "1.0.0"

    def __init__(
        self,
        resource_root: Path | str,
        *,
        resource_spec: ResourceSpec = SUBTLEX_US_SPEC,
    ) -> None:
        self.resource_root = Path(resource_root)
        self.resource_spec = resource_spec
        self.resource_manager = LocalResourceManager(self.resource_root)

    def validate_resources(self) -> tuple[ResourceStatus, ...]:
        status = self.resource_manager.validate(self.resource_spec)
        if status.available:
            try:
                _load_cached(str(status.configured_path), status.source_sha256)
            except SubtlexUsAdapterError as error:
                status = replace(
                    status,
                    state=ResourceState.MALFORMED,
                    message=(
                        f"{self.resource_spec.display_name} is readable but does "
                        f"not satisfy the workbook contract: {error}"
                    ),
                )
        return (status,)

    def _available(self) -> tuple[ResourceStatus, SubtlexUsLexicon]:
        status = self.validate_resources()[0]
        if not status.available:
            raise FrequencyModuleError(status.message)
        try:
            lexicon = _load_cached(
                str(status.configured_path), status.source_sha256
            )
        except SubtlexUsAdapterError as error:
            detail = (
                f" Technical detail: {error.technical_detail}"
                if error.technical_detail
                else ""
            )
            raise FrequencyModuleError(f"{error}{detail}") from error
        return status, lexicon

    def analyze(self, module_input: ModuleInput) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: FrequencyConfiguration | None = None,
    ) -> FrequencyAnalysisResult:
        config = configuration or FrequencyConfiguration()
        status, lexicon = self._available()
        audit = _token_audit(module_input, lexicon, config)
        summary = _summary(audit, config)
        line_summaries = _structural_summaries(
            module_input, audit, StructuralUnitKind.LINE
        )
        stanza_summaries = _structural_summaries(
            module_input, audit, StructuralUnitKind.STANZA
        )
        pos_summaries = _pos_summaries(audit)
        terms = _term_summaries(audit)
        ascending = tuple(
            sorted(
                terms,
                key=lambda item: (
                    item.zipf_value,
                    -item.matched_token_occurrences,
                    item.source_term.casefold(),
                ),
            )
        )
        descending = tuple(
            sorted(
                terms,
                key=lambda item: (
                    -item.zipf_value,
                    -item.matched_token_occurrences,
                    item.source_term.casefold(),
                ),
            )
        )
        lowest_terms = ascending[: config.top_term_count]
        highest_terms = descending[: config.top_term_count]
        rare_tail = tuple(
            term
            for term in ascending
            if term.zipf_value < config.rare_below
        )[: config.rare_tail_count]
        warnings = _warnings(summary, audit, config)
        resource_provenance = ResourceProvenance.from_available_status(
            status,
            citation=self.resource_spec.citation,
            license_notice=self.resource_spec.license_notice,
            adapter_version=SubtlexUsAdapter.adapter_version,
        )
        if config.content_words_only:
            inclusion_policy = (
                "Only model-tagged NOUN, VERB, ADJ, and ADV lexical tokens; "
                "function words, auxiliaries, punctuation, and numeric tokens "
                "excluded; model-tagged PROPN tokens are outside this explicit "
                "content-word scope."
            )
        else:
            inclusion_policy = (
                "All lexical tokens except punctuation and numeric tokens; "
                + (
                    "model-tagged proper nouns excluded by explicit configuration."
                    if config.exclude_proper_nouns
                    else (
                        "model-tagged proper nouns included by default."
                    )
                )
            )
        lookup_policy = (
            "Exact normalized observed word form first; "
            + (
                "then explicit model-lemma fallback; "
                if config.enable_lemma_fallback
                else "lemma fallback disabled; "
            )
            + "then documented apostrophe/possessive fallbacks; unmatched "
            "observations remain missing."
        )
        result_signature = "|".join(
            (
                self.name,
                self.version,
                module_input.document.text_version_id,
                config.configuration_id,
                status.source_sha256,
            )
        )
        result_id = hashlib.sha256(result_signature.encode("utf-8")).hexdigest()
        groups = (*line_summaries, *stanza_summaries, *pos_summaries)
        module_result = ModuleResult(
            result_id=result_id,
            module_name=self.name,
            module_version=self.version,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=_module_metrics(summary, groups),
            coverage=(
                ModuleCoverage.from_counts(
                    coverage_id="frequency.matched_token_coverage",
                    eligible_count=summary.eligible_token_count,
                    matched_count=summary.matched_token_count,
                    unit="eligible lexical token occurrences",
                    unmatched_items=tuple(
                        sorted(
                            {
                                row.normalized_form
                                for row in audit
                                if row.eligible and not row.included
                            }
                        )
                    ),
                    note=(
                        "Unmatched observations remain missing rather than "
                        "receiving a zero or estimated Zipf value."
                    ),
                ),
                ModuleCoverage.from_counts(
                    coverage_id="frequency.matched_unique_word_coverage",
                    eligible_count=summary.eligible_unique_type_count,
                    matched_count=summary.matched_unique_type_count,
                    unit="unique normalized observed surface types",
                    unmatched_items=tuple(
                        sorted(
                            {
                                row.normalized_form
                                for row in audit
                                if row.eligible and not row.included
                            }
                        )
                    ),
                    note=(
                        "The denominator uses observed normalized surface types, "
                        "not lemma types or distinct source entries."
                    ),
                ),
            ),
            warnings=warnings,
            provenance=ModuleProvenance(
                software_version=__version__,
                source_text_sha256=module_input.document.text_sha256,
                preprocessing_recipe=module_input.preprocessing.recipe_id,
                pipeline_name=module_input.preprocessing.pipeline_name,
                pipeline_version=module_input.preprocessing.pipeline_version,
                configuration_id=config.configuration_id,
                scenario_id=config.scenario_id,
                lookup_policy=lookup_policy,
                inclusion_policy=inclusion_policy,
                resources=(resource_provenance,),
            ),
        )
        return FrequencyAnalysisResult(
            module_result=module_result,
            configuration=config,
            resource_status=status,
            resource_validation=lexicon.validation,
            summary=summary,
            part_of_speech_summaries=pos_summaries,
            line_summaries=line_summaries,
            stanza_summaries=stanza_summaries,
            term_summaries=terms,
            lowest_frequency_terms=lowest_terms,
            highest_frequency_terms=highest_terms,
            rare_word_tail=rare_tail,
            token_audit=audit,
        )
