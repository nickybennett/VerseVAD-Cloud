"""Normative lexical concreteness analysis using a local research workbook."""

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
from versevad.adapters.concreteness import (
    BrysbaertConcretenessAdapter,
    ConcretenessAdapterError,
    ConcretenessEntry,
    ConcretenessLexicon,
    ConcretenessValidation,
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


BRYSBAERT_CONCRETENESS_FILENAME = (
    "brysbaert_warriner_kuperman_concreteness_DATA.xlsx"
)
BRYSBAERT_CONCRETENESS_SHA256 = (
    "1673ead761e28833a40e82c0d20f10782955ced9366d600eafeefee0f2254545"
)
BRYSBAERT_CONCRETENESS_CITATION = (
    "Brysbaert, M., Warriner, A. B., & Kuperman, V. (2014). "
    "Concreteness ratings for 40 thousand generally known English word "
    "lemmas. Behavior Research Methods, 46, 904-911. "
    "https://doi.org/10.3758/s13428-013-0403-5"
)
BRYSBAERT_CONCRETENESS_LICENSE_NOTICE = (
    "User-supplied local research resource; VerseVAD does not redistribute "
    "the workbook. The user is responsible for the applicable license and "
    "usage terms."
)
BRYSBAERT_CONCRETENESS_SPEC = ResourceSpec(
    resource_id="brysbaert-concreteness-2014",
    display_name="Brysbaert, Warriner, and Kuperman concreteness ratings",
    relative_path=BRYSBAERT_CONCRETENESS_FILENAME,
    version="2014 supplementary workbook; 39,954 rated stimuli",
    accepted_sha256=(BRYSBAERT_CONCRETENESS_SHA256,),
    minimum_bytes=1_000_000,
    citation=BRYSBAERT_CONCRETENESS_CITATION,
    license_notice=BRYSBAERT_CONCRETENESS_LICENSE_NOTICE,
)


class ConcretenessModuleError(RuntimeError):
    """Plain-language module failure for the application boundary."""


class ConcretenessMatchMethod(StrEnum):
    EXACT = "exact_surface"
    EXACT_PHRASE = "exact_phrase"
    LEMMA = "lemma"
    DOCUMENTED_FALLBACK = "documented_fallback"
    UNMATCHED = "unmatched"
    NOT_ELIGIBLE = "not_eligible"


@dataclass(frozen=True)
class ConcretenessConfiguration:
    """Explicit choices for coverage, matching, warnings, and display bands."""

    highly_abstract_max: float = 2.0
    highly_concrete_min: float = 4.0
    exclude_proper_nouns: bool = False
    activate_multiword_expressions: bool = True
    minimum_rated_tokens: int = 3
    low_coverage_warning_threshold: float = 0.6
    top_term_count: int = 10
    scenario_id: str = "concreteness-baseline-v1"

    def __post_init__(self) -> None:
        if not 1 <= self.highly_abstract_max <= 5:
            raise ValueError(
                "The highly abstract threshold must be on the source 1-5 scale."
            )
        if not 1 <= self.highly_concrete_min <= 5:
            raise ValueError(
                "The highly concrete threshold must be on the source 1-5 scale."
            )
        if self.highly_abstract_max >= self.highly_concrete_min:
            raise ValueError(
                "The highly abstract threshold must be below the highly concrete "
                "threshold."
            )
        if self.minimum_rated_tokens < 1:
            raise ValueError("The minimum rated-token count must be at least 1.")
        if not 0 <= self.low_coverage_warning_threshold <= 1:
            raise ValueError("The low-coverage warning threshold must be 0-1.")
        if self.top_term_count < 1:
            raise ValueError("At least one term must be retained in each ranking.")
        if not self.scenario_id.strip():
            raise ValueError("A concreteness scenario requires a stable ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"concreteness-config-v1:{digest}"


@dataclass(frozen=True)
class ConcretenessTokenRating:
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
    match_method: ConcretenessMatchMethod
    match_group_id: str
    match_group_token_ids: tuple[str, ...]
    matched_source_term: str | None
    matched_lookup_form: str | None
    source_row: int | None
    source_is_multiword: bool | None
    rating: float | None
    source_rating_standard_deviation: float | None
    source_unknown_count: int | None
    source_rater_count: int | None
    source_percent_known: float | None
    source_subtlex_count: int | None
    reason: str


@dataclass(frozen=True)
class ConcretenessSummary:
    statistics: DescriptiveStatistics
    interquartile_range: float | None
    eligible_token_count: int
    rated_token_count: int
    unmatched_token_count: int
    token_coverage: float | None
    eligible_unique_type_count: int
    rated_unique_type_count: int
    unmatched_unique_type_count: int
    unique_type_coverage: float | None
    matched_expression_occurrence_count: int
    highly_concrete_token_count: int
    highly_concrete_proportion: float | None
    highly_abstract_token_count: int
    highly_abstract_proportion: float | None
    highly_concrete_min: float
    highly_abstract_max: float
    minimum_rated_tokens: int
    is_sparse: bool


@dataclass(frozen=True)
class ConcretenessGroupSummary:
    scope: str
    scope_id: str
    ordinal: int
    label: str
    source_text: str
    statistics: DescriptiveStatistics
    interquartile_range: float | None
    eligible_token_count: int
    rated_token_count: int
    unmatched_token_count: int
    token_coverage: float | None
    eligible_unique_type_count: int
    rated_unique_type_count: int
    unique_type_coverage: float | None


@dataclass(frozen=True)
class ConcretenessTermSummary:
    source_term: str
    lookup_form: str
    rating: float
    source_rating_standard_deviation: float
    rated_token_occurrences: int
    expression_occurrences: int
    surface_forms: tuple[str, ...]
    part_of_speech_tags: tuple[str, ...]
    source_row: int
    source_is_multiword: bool
    source_percent_known: float


@dataclass(frozen=True)
class ConcretenessAnalysisResult:
    module_result: ModuleResult
    configuration: ConcretenessConfiguration
    resource_status: ResourceStatus
    resource_validation: ConcretenessValidation
    summary: ConcretenessSummary
    part_of_speech_summaries: tuple[ConcretenessGroupSummary, ...]
    line_summaries: tuple[ConcretenessGroupSummary, ...]
    stanza_summaries: tuple[ConcretenessGroupSummary, ...]
    term_summaries: tuple[ConcretenessTermSummary, ...]
    most_concrete_terms: tuple[ConcretenessTermSummary, ...]
    most_abstract_terms: tuple[ConcretenessTermSummary, ...]
    token_audit: tuple[ConcretenessTokenRating, ...]

    def __post_init__(self) -> None:
        eligible = sum(row.eligible for row in self.token_audit)
        rated = sum(row.included for row in self.token_audit)
        if (
            self.summary.eligible_token_count != eligible
            or self.summary.rated_token_count != rated
        ):
            raise ValueError(
                "Concreteness summary counts must agree with the token audit."
            )
        if any(
            row.rating is not None
            for row in self.token_audit
            if not row.included
        ):
            raise ValueError(
                "Unmatched or ineligible concreteness rows cannot carry ratings."
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


def _group_id(
    module_input: ModuleInput,
    tokens: tuple[TokenRecord, ...],
    lookup_form: str,
    method: ConcretenessMatchMethod,
) -> str:
    signature = "|".join(
        (
            module_input.document.text_version_id,
            method.value,
            lookup_form,
            *(token.token_id for token in tokens),
        )
    )
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def _entry_rating(
    *,
    token: TokenRecord,
    tokens: tuple[TokenRecord, ...],
    module_input: ModuleInput,
    entry: ConcretenessEntry,
    method: ConcretenessMatchMethod,
    reason: str,
) -> ConcretenessTokenRating:
    return ConcretenessTokenRating(
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
        match_group_id=_group_id(
            module_input,
            tokens,
            entry.lookup_form,
            method,
        ),
        match_group_token_ids=tuple(item.token_id for item in tokens),
        matched_source_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        source_is_multiword=entry.is_multiword,
        rating=entry.mean,
        source_rating_standard_deviation=entry.standard_deviation,
        source_unknown_count=entry.unknown_count,
        source_rater_count=entry.rater_count,
        source_percent_known=entry.percent_known,
        source_subtlex_count=entry.subtlex_count,
        reason=reason,
    )


def _unrated_token(
    token: TokenRecord,
    *,
    method: ConcretenessMatchMethod,
    eligible: bool,
    reason: str,
) -> ConcretenessTokenRating:
    return ConcretenessTokenRating(
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
        match_group_id="",
        match_group_token_ids=(token.token_id,),
        matched_source_term=None,
        matched_lookup_form=None,
        source_row=None,
        source_is_multiword=None,
        rating=None,
        source_rating_standard_deviation=None,
        source_unknown_count=None,
        source_rater_count=None,
        source_percent_known=None,
        source_subtlex_count=None,
        reason=reason,
    )


def _is_eligible(
    token: TokenRecord,
    configuration: ConcretenessConfiguration,
) -> bool:
    return token.is_lexical and not (
        configuration.exclude_proper_nouns and token.is_proper_noun
    )


def _unigram(
    lexicon: ConcretenessLexicon,
    lookup_form: str,
) -> ConcretenessEntry | None:
    entry = lexicon.lookup(lookup_form)
    return entry if entry is not None and not entry.is_multiword else None


def _token_audit(
    module_input: ModuleInput,
    lexicon: ConcretenessLexicon,
    configuration: ConcretenessConfiguration,
) -> tuple[ConcretenessTokenRating, ...]:
    tokens = module_input.tokens
    assigned: dict[str, ConcretenessTokenRating] = {}

    if configuration.activate_multiword_expressions:
        for length in lexicon.phrase_lengths:
            for start in range(0, len(tokens) - length + 1):
                window = tokens[start : start + length]
                if any(token.token_id in assigned for token in window):
                    continue
                if not all(_is_eligible(token, configuration) for token in window):
                    continue
                if len({token.line_number for token in window}) != 1:
                    continue
                if len({token.stanza_number for token in window}) != 1:
                    continue
                lookup_form = " ".join(
                    normalize_lookup(token.normalized_form or token.surface_form)
                    for token in window
                )
                entry = lexicon.lookup(lookup_form)
                if (
                    entry is None
                    or not entry.is_multiword
                    or entry.word_count != length
                ):
                    continue
                for token in window:
                    assigned[token.token_id] = _entry_rating(
                        token=token,
                        tokens=window,
                        module_input=module_input,
                        entry=entry,
                        method=ConcretenessMatchMethod.EXACT_PHRASE,
                        reason=(
                            "Exact normalized multiword source entry matched within "
                            "one physical line. Its rating is assigned to each covered "
                            "token for token-weighted summaries."
                        ),
                    )

    rows: list[ConcretenessTokenRating] = []
    for token in tokens:
        phrase_row = assigned.get(token.token_id)
        if phrase_row is not None:
            rows.append(phrase_row)
            continue
        if not token.is_lexical:
            kind = "numeric" if token.is_numeric else "punctuation or non-lexical"
            rows.append(
                _unrated_token(
                    token,
                    method=ConcretenessMatchMethod.NOT_ELIGIBLE,
                    eligible=False,
                    reason=f"Excluded from the lexical denominator as {kind}.",
                )
            )
            continue
        if configuration.exclude_proper_nouns and token.is_proper_noun:
            rows.append(
                _unrated_token(
                    token,
                    method=ConcretenessMatchMethod.NOT_ELIGIBLE,
                    eligible=False,
                    reason=(
                        "Excluded by the configured proper-name policy. The source "
                        "paper states that proper names were not included in its "
                        "lemma list."
                    ),
                )
            )
            continue

        surface_lookup = normalize_lookup(
            token.normalized_form or token.surface_form
        )
        exact_entry = _unigram(lexicon, surface_lookup)
        if exact_entry is not None:
            rows.append(
                _entry_rating(
                    token=token,
                    tokens=(token,),
                    module_input=module_input,
                    entry=exact_entry,
                    method=ConcretenessMatchMethod.EXACT,
                    reason=(
                        "Exact normalized surface form matched before any lemma or "
                        "fallback was considered."
                    ),
                )
            )
            continue

        lemma_lookup = normalize_lookup(token.normalized_lemma or token.lemma)
        lemma_entry = (
            _unigram(lexicon, lemma_lookup)
            if lemma_lookup and lemma_lookup != surface_lookup
            else None
        )
        if lemma_entry is not None:
            rows.append(
                _entry_rating(
                    token=token,
                    tokens=(token,),
                    module_input=module_input,
                    entry=lemma_entry,
                    method=ConcretenessMatchMethod.LEMMA,
                    reason=(
                        "No exact normalized surface entry was available; the "
                        "installed model's normalized lemma matched."
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
            canonical_lemma
            and canonical_lemma not in {surface_lookup, lemma_lookup}
        ):
            fallback_candidates.append(
                (canonical_lemma, "canonicalized lemma apostrophe form")
            )
        tried: set[str] = {surface_lookup, lemma_lookup}
        fallback_match: tuple[ConcretenessEntry, str] | None = None
        for candidate, label in fallback_candidates:
            if candidate in tried:
                continue
            tried.add(candidate)
            entry = _unigram(lexicon, candidate)
            if entry is not None:
                fallback_match = (entry, label)
                break
        if fallback_match is not None:
            entry, fallback_label = fallback_match
            rows.append(
                _entry_rating(
                    token=token,
                    tokens=(token,),
                    module_input=module_input,
                    entry=entry,
                    method=ConcretenessMatchMethod.DOCUMENTED_FALLBACK,
                    reason=(
                        "No surface or lemma entry was available; the documented "
                        f"{fallback_label} matched."
                    ),
                )
            )
            continue
        rows.append(
            _unrated_token(
                token,
                method=ConcretenessMatchMethod.UNMATCHED,
                eligible=True,
                reason=(
                    "No normalized surface, lemma, or documented conservative "
                    "fallback entry was found. The rating remains missing."
                ),
            )
        )
    return tuple(rows)


def _summary(
    audit: tuple[ConcretenessTokenRating, ...],
    configuration: ConcretenessConfiguration,
) -> ConcretenessSummary:
    eligible = tuple(row for row in audit if row.eligible)
    rated = tuple(row for row in eligible if row.included and row.rating is not None)
    statistics = descriptive_statistics(
        row.rating for row in rated if row.rating is not None
    )
    eligible_types = {row.normalized_form for row in eligible}
    rated_types = {row.normalized_form for row in rated}
    highly_concrete = sum(
        row.rating is not None
        and row.rating >= configuration.highly_concrete_min
        for row in rated
    )
    highly_abstract = sum(
        row.rating is not None
        and row.rating <= configuration.highly_abstract_max
        for row in rated
    )
    expression_groups = {row.match_group_id for row in rated}
    return ConcretenessSummary(
        statistics=statistics,
        interquartile_range=_iqr(statistics),
        eligible_token_count=len(eligible),
        rated_token_count=len(rated),
        unmatched_token_count=len(eligible) - len(rated),
        token_coverage=_rate(len(rated), len(eligible)),
        eligible_unique_type_count=len(eligible_types),
        rated_unique_type_count=len(rated_types),
        unmatched_unique_type_count=len(eligible_types - rated_types),
        unique_type_coverage=_rate(len(rated_types), len(eligible_types)),
        matched_expression_occurrence_count=len(expression_groups),
        highly_concrete_token_count=highly_concrete,
        highly_concrete_proportion=_rate(highly_concrete, len(rated)),
        highly_abstract_token_count=highly_abstract,
        highly_abstract_proportion=_rate(highly_abstract, len(rated)),
        highly_concrete_min=configuration.highly_concrete_min,
        highly_abstract_max=configuration.highly_abstract_max,
        minimum_rated_tokens=configuration.minimum_rated_tokens,
        is_sparse=len(rated) < configuration.minimum_rated_tokens,
    )


def _group_summary(
    rows: Iterable[ConcretenessTokenRating],
    *,
    scope: str,
    scope_id: str,
    ordinal: int,
    label: str,
    source_text: str,
) -> ConcretenessGroupSummary:
    row_tuple = tuple(rows)
    eligible = tuple(row for row in row_tuple if row.eligible)
    rated = tuple(row for row in eligible if row.included and row.rating is not None)
    statistics = descriptive_statistics(
        row.rating for row in rated if row.rating is not None
    )
    eligible_types = {row.normalized_form for row in eligible}
    rated_types = {row.normalized_form for row in rated}
    return ConcretenessGroupSummary(
        scope=scope,
        scope_id=scope_id,
        ordinal=ordinal,
        label=label,
        source_text=source_text,
        statistics=statistics,
        interquartile_range=_iqr(statistics),
        eligible_token_count=len(eligible),
        rated_token_count=len(rated),
        unmatched_token_count=len(eligible) - len(rated),
        token_coverage=_rate(len(rated), len(eligible)),
        eligible_unique_type_count=len(eligible_types),
        rated_unique_type_count=len(rated_types),
        unique_type_coverage=_rate(len(rated_types), len(eligible_types)),
    )


def _structural_summaries(
    module_input: ModuleInput,
    audit: tuple[ConcretenessTokenRating, ...],
    kind: StructuralUnitKind,
) -> tuple[ConcretenessGroupSummary, ...]:
    scope = kind.value
    number_field = "line_number" if kind is StructuralUnitKind.LINE else "stanza_number"
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
    audit: tuple[ConcretenessTokenRating, ...],
) -> tuple[ConcretenessGroupSummary, ...]:
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
    audit: tuple[ConcretenessTokenRating, ...],
) -> tuple[ConcretenessTermSummary, ...]:
    by_lookup: dict[str, list[ConcretenessTokenRating]] = defaultdict(list)
    for row in audit:
        if row.included and row.matched_lookup_form is not None:
            by_lookup[row.matched_lookup_form].append(row)
    summaries = []
    for lookup_form, rows in by_lookup.items():
        first = rows[0]
        assert first.matched_source_term is not None
        assert first.rating is not None
        assert first.source_rating_standard_deviation is not None
        assert first.source_row is not None
        assert first.source_is_multiword is not None
        assert first.source_percent_known is not None
        summaries.append(
            ConcretenessTermSummary(
                source_term=first.matched_source_term,
                lookup_form=lookup_form,
                rating=first.rating,
                source_rating_standard_deviation=(
                    first.source_rating_standard_deviation
                ),
                rated_token_occurrences=len(rows),
                expression_occurrences=len(
                    {row.match_group_id for row in rows}
                ),
                surface_forms=tuple(
                    sorted({row.surface_form for row in rows}, key=str.casefold)
                ),
                part_of_speech_tags=tuple(
                    sorted({row.part_of_speech or "X" for row in rows})
                ),
                source_row=first.source_row,
                source_is_multiword=first.source_is_multiword,
                source_percent_known=first.source_percent_known,
            )
        )
    return tuple(
        sorted(summaries, key=lambda item: item.source_term.casefold())
    )


def _warnings(
    summary: ConcretenessSummary,
    audit: tuple[ConcretenessTokenRating, ...],
    configuration: ConcretenessConfiguration,
) -> tuple[ModuleWarning, ...]:
    warnings: list[ModuleWarning] = []
    if not summary.eligible_token_count:
        warnings.append(
            ModuleWarning(
                code="no_eligible_tokens",
                message=(
                    "No eligible lexical tokens were available. Concreteness "
                    "aggregates and coverage rates remain missing."
                ),
                severity=WarningSeverity.INFORMATION,
            )
        )
    elif not summary.rated_token_count:
        warnings.append(
            ModuleWarning(
                code="no_rated_tokens",
                message=(
                    "No eligible token found a concreteness rating. Aggregate "
                    "values remain missing rather than being set to a neutral score."
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
                    "Rated-token coverage is below the configured caution "
                    f"threshold of {configuration.low_coverage_warning_threshold:.0%}. "
                    "Inspect unmatched vocabulary before interpreting aggregates."
                ),
                technical_detail=(
                    f"{summary.rated_token_count} of "
                    f"{summary.eligible_token_count} eligible tokens were rated."
                ),
            )
        )
    if summary.is_sparse:
        warnings.append(
            ModuleWarning(
                code="sparse_rated_sample",
                message=(
                    "Fewer than the configured minimum number of rated tokens "
                    "contributed. Descriptive statistics are available only when "
                    "defined and should be treated as sparse."
                ),
                technical_detail=(
                    f"Rated {summary.rated_token_count}; configured minimum "
                    f"{configuration.minimum_rated_tokens}."
                ),
            )
        )
    phrase_groups = {
        row.match_group_id
        for row in audit
        if row.match_method is ConcretenessMatchMethod.EXACT_PHRASE
    }
    if phrase_groups:
        warnings.append(
            ModuleWarning(
                code="phrase_rating_assignment",
                message=(
                    "Exact source-supplied expressions were activated. Each "
                    "expression rating was assigned to its covered component tokens "
                    "for token-weighted coverage and summaries; the shared match "
                    "group remains visible in the audit."
                ),
                severity=WarningSeverity.INFORMATION,
                technical_detail=(
                    f"{len(phrase_groups)} expression occurrence(s) activated."
                ),
            )
        )
    return tuple(warnings)


def _module_metrics(
    summary: ConcretenessSummary,
    groups: tuple[ConcretenessGroupSummary, ...],
) -> tuple[ModuleMetric, ...]:
    statistics = summary.statistics
    document_values = (
        ("concreteness.mean", statistics.mean, "source 1-5"),
        ("concreteness.median", statistics.median, "source 1-5"),
        (
            "concreteness.population_standard_deviation",
            statistics.population_standard_deviation,
            "source 1-5",
        ),
        ("concreteness.minimum", statistics.minimum, "source 1-5"),
        ("concreteness.first_quartile", statistics.first_quartile, "source 1-5"),
        ("concreteness.third_quartile", statistics.third_quartile, "source 1-5"),
        (
            "concreteness.interquartile_range",
            summary.interquartile_range,
            "source-scale points",
        ),
        ("concreteness.maximum", statistics.maximum, "source 1-5"),
        (
            "concreteness.highly_concrete_proportion",
            summary.highly_concrete_proportion,
            "proportion",
        ),
        (
            "concreteness.highly_abstract_proportion",
            summary.highly_abstract_proportion,
            "proportion",
        ),
    )
    metrics = [
        ModuleMetric(
            metric_id=metric_id,
            value=value,
            layer=ResultLayer.COMPUTED_SUMMARY,
            unit=unit,
            weighting="rated token occurrences",
            denominator=(
                f"{summary.rated_token_count} rated eligible token occurrences"
            ),
        )
        for metric_id, value, unit in document_values
    ]
    for group in groups:
        metrics.extend(
            (
                ModuleMetric(
                    metric_id="concreteness.mean",
                    value=group.statistics.mean,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="source 1-5",
                    weighting="rated token occurrences",
                    denominator=f"{group.rated_token_count} rated tokens",
                ),
                ModuleMetric(
                    metric_id="concreteness.median",
                    value=group.statistics.median,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="source 1-5",
                    weighting="rated token occurrences",
                    denominator=f"{group.rated_token_count} rated tokens",
                ),
                ModuleMetric(
                    metric_id="concreteness.token_coverage",
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
def _load_cached(path: str, source_sha256: str) -> ConcretenessLexicon:
    del source_sha256
    return BrysbaertConcretenessAdapter().load(Path(path))


class ConcretenessModule:
    """Framework-independent Stage 2 module backed by a named local resource."""

    name = "concreteness"
    version = "1.0.0"

    def __init__(
        self,
        resource_root: Path | str,
        *,
        resource_spec: ResourceSpec = BRYSBAERT_CONCRETENESS_SPEC,
    ) -> None:
        self.resource_root = Path(resource_root)
        self.resource_spec = resource_spec
        self.resource_manager = LocalResourceManager(self.resource_root)

    def validate_resources(self) -> tuple[ResourceStatus, ...]:
        status = self.resource_manager.validate(self.resource_spec)
        if status.available:
            try:
                _load_cached(
                    str(status.configured_path),
                    status.source_sha256,
                )
            except ConcretenessAdapterError as error:
                status = replace(
                    status,
                    state=ResourceState.MALFORMED,
                    message=(
                        f"{self.resource_spec.display_name} is readable but does "
                        f"not satisfy the workbook contract: {error}"
                    ),
                )
        return (status,)

    def _available(
        self,
    ) -> tuple[ResourceStatus, ConcretenessLexicon]:
        status = self.validate_resources()[0]
        if not status.available:
            raise ConcretenessModuleError(status.message)
        try:
            lexicon = _load_cached(
                str(status.configured_path),
                status.source_sha256,
            )
        except ConcretenessAdapterError as error:
            detail = f" Technical detail: {error.technical_detail}" if error.technical_detail else ""
            raise ConcretenessModuleError(f"{error}{detail}") from error
        return status, lexicon

    def analyze(
        self,
        module_input: ModuleInput,
    ) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: ConcretenessConfiguration | None = None,
    ) -> ConcretenessAnalysisResult:
        config = configuration or ConcretenessConfiguration()
        status, lexicon = self._available()
        audit = _token_audit(module_input, lexicon, config)
        summary = _summary(audit, config)
        line_summaries = _structural_summaries(
            module_input,
            audit,
            StructuralUnitKind.LINE,
        )
        stanza_summaries = _structural_summaries(
            module_input,
            audit,
            StructuralUnitKind.STANZA,
        )
        pos_summaries = _pos_summaries(audit)
        terms = _term_summaries(audit)
        concrete_terms = tuple(
            sorted(
                terms,
                key=lambda item: (
                    -item.rating,
                    -item.rated_token_occurrences,
                    item.source_term.casefold(),
                ),
            )[: config.top_term_count]
        )
        abstract_terms = tuple(
            sorted(
                terms,
                key=lambda item: (
                    item.rating,
                    -item.rated_token_occurrences,
                    item.source_term.casefold(),
                ),
            )[: config.top_term_count]
        )
        warnings = _warnings(summary, audit, config)
        resource_provenance = ResourceProvenance.from_available_status(
            status,
            citation=self.resource_spec.citation,
            license_notice=self.resource_spec.license_notice,
            adapter_version=BrysbaertConcretenessAdapter.adapter_version,
        )
        inclusion_policy = (
            "All lexical tokens except punctuation and numeric tokens; "
            + (
                "model-tagged proper nouns excluded by explicit configuration."
                if config.exclude_proper_nouns
                else "model-tagged proper nouns included by default."
            )
        )
        lookup_policy = (
            "Longest exact source expression within a physical line when enabled; "
            "then exact normalized surface, model lemma, documented apostrophe/"
            "possessive fallbacks, unmatched."
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
                    coverage_id="concreteness.rated_token_coverage",
                    eligible_count=summary.eligible_token_count,
                    matched_count=summary.rated_token_count,
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
                        "Multiword source ratings cover and contribute once for "
                        "each component token; the shared expression group remains "
                        "auditable."
                    ),
                ),
                ModuleCoverage.from_counts(
                    coverage_id="concreteness.rated_unique_word_coverage",
                    eligible_count=summary.eligible_unique_type_count,
                    matched_count=summary.rated_unique_type_count,
                    unit="unique normalized surface word types",
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
                        "The denominator uses normalized observed surface types, "
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
        return ConcretenessAnalysisResult(
            module_result=module_result,
            configuration=config,
            resource_status=status,
            resource_validation=lexicon.validation,
            summary=summary,
            part_of_speech_summaries=pos_summaries,
            line_summaries=line_summaries,
            stanza_summaries=stanza_summaries,
            term_summaries=terms,
            most_concrete_terms=concrete_terms,
            most_abstract_terms=abstract_terms,
            token_audit=audit,
        )
