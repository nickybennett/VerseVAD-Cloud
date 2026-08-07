"""Optional retrospective age-of-acquisition analysis using Kuperman norms."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from statistics import fmean
from typing import TYPE_CHECKING, Iterable

from versevad import __version__
from versevad.adapters.kuperman_aoa import (
    KupermanAoAAdapter,
    KupermanAoAAdapterError,
    KupermanAoAEntry,
    KupermanAoALexicon,
    KupermanAoAValidation,
)
from versevad.analysis.statistics import descriptive_statistics
from versevad.analysis_profiles import CONTENT_WORD_POS_TAGS
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
from versevad.lexical_eligibility import (
    LEXICON_ELIGIBILITY_POLICY_ID,
    append_lexicon_eligibility_note,
    is_lexicon_eligible,
    lexicon_ineligibility_reason,
)
from versevad.normalization import (
    canonicalize_apostrophes,
    normalize_lookup,
    possessive_base,
)

if TYPE_CHECKING:
    from versevad.lexical_semantic.concreteness import ConcretenessAnalysisResult
    from versevad.lexical_semantic.frequency import FrequencyAnalysisResult


KUPERMAN_AOA_FILENAME = "kuperman_2013_erratum_ESM1_official.xlsx"
KUPERMAN_AOA_SHA256 = (
    "3f69a1332359de1cd4a7ccd3c4c3c2e39b388eeb171d6e90544709c3dc1a8a6e"
)
KUPERMAN_AOA_CITATION = (
    "Kuperman, V., Stadthagen-Gonzalez, H., & Brysbaert, M. (2012). "
    "Age-of-acquisition ratings for 30,000 English words. Behavior Research "
    "Methods, 44, 978-990. https://doi.org/10.3758/s13428-012-0210-4; "
    "supplement supplied through the 2013 erratum, "
    "https://doi.org/10.3758/s13428-013-0348-8"
)
KUPERMAN_AOA_LICENSE_NOTICE = (
    "Publisher supplementary material retained locally for licensed research "
    "use. VerseVAD records its checksum and does not redistribute the workbook."
)
KUPERMAN_AOA_SPEC = ResourceSpec(
    resource_id="kuperman-aoa-2012-erratum-supplement",
    display_name="Kuperman et al. English age-of-acquisition ratings",
    relative_path=KUPERMAN_AOA_FILENAME,
    version="Official Springer erratum ESM 1 workbook; downloaded 2026-07-23",
    accepted_sha256=(KUPERMAN_AOA_SHA256,),
    minimum_bytes=1_700_000,
    citation=KUPERMAN_AOA_CITATION,
    license_notice=KUPERMAN_AOA_LICENSE_NOTICE,
)

AOA_CONTENT_WORD_POS = CONTENT_WORD_POS_TAGS


class AoAModuleError(RuntimeError):
    """Plain-language module failure for the application boundary."""


class AoAMatchMethod(StrEnum):
    EXACT = "exact_surface"
    LEMMA = "lemma"
    DOCUMENTED_FALLBACK = "documented_fallback"
    SOURCE_UNRATED = "source_entry_without_numeric_rating"
    UNMATCHED = "unmatched"
    NOT_ELIGIBLE = "not_eligible"


@dataclass(frozen=True)
class AoAConfiguration:
    """Explicit matching, scope, band, coverage, and relationship choices."""

    early_acquired_max: float = 5.0
    later_acquired_min: float = 12.0
    exclude_proper_nouns: bool = False
    # Legacy field: report scope no longer restricts retained evidence.
    content_words_only: bool = False
    enable_lemma_fallback: bool = True
    minimum_matched_tokens: int = 3
    minimum_relationship_types: int = 3
    low_coverage_warning_threshold: float = 0.6
    top_term_count: int = 10
    scenario_id: str = "kuperman-aoa-v2"

    def __post_init__(self) -> None:
        if not 0 <= self.early_acquired_max <= 25:
            raise ValueError("The early-acquired threshold must be between 0 and 25.")
        if not 0 <= self.later_acquired_min <= 25:
            raise ValueError("The later-acquired threshold must be between 0 and 25.")
        if self.early_acquired_max >= self.later_acquired_min:
            raise ValueError(
                "The early-acquired threshold must be below the later-acquired "
                "threshold."
            )
        if self.minimum_matched_tokens < 1:
            raise ValueError("The minimum matched-token count must be at least 1.")
        if self.minimum_relationship_types < 3:
            raise ValueError(
                "At least three paired types are required for a relationship."
            )
        if not 0 <= self.low_coverage_warning_threshold <= 1:
            raise ValueError("The low-coverage warning threshold must be 0-1.")
        if self.top_term_count < 1:
            raise ValueError("At least one term must be retained in each ranking.")
        if not self.scenario_id.strip():
            raise ValueError("An age-of-acquisition scenario requires a stable ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"aoa-config-v2:{digest}"

    @property
    def scope_label(self) -> str:
        return "All lexicon-eligible word tokens; report scope is selected later"


@dataclass(frozen=True)
class AoATokenRating:
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
    match_method: AoAMatchMethod
    matched_source_term: str | None
    matched_lookup_form: str | None
    source_row: int | None
    mean_age: float | None
    source_rating_standard_deviation: float | None
    source_occurrence_total: int | None
    source_numeric_response_count: int | None
    source_unknown_response_count: int | None
    source_numeric_response_proportion: float | None
    source_dunno_value: float | None
    source_frequency_per_million: float | None
    reason: str


@dataclass(frozen=True)
class AoABandSummary:
    band_id: str
    label: str
    lower_bound: float | None
    lower_inclusive: bool
    upper_bound: float | None
    upper_inclusive: bool
    token_count: int
    proportion: float | None


@dataclass(frozen=True)
class AoASummary:
    statistics: DescriptiveStatistics
    interquartile_range: float | None
    source_standard_deviation_statistics: DescriptiveStatistics
    eligible_token_count: int
    matched_token_count: int
    unmatched_token_count: int
    source_unrated_token_count: int
    token_coverage: float | None
    eligible_unique_type_count: int
    matched_unique_type_count: int
    unmatched_unique_type_count: int
    unique_type_coverage: float | None
    minimum_source_numeric_responses: int | None
    low_response_token_count: int
    scope_label: str
    minimum_matched_tokens: int
    is_sparse: bool
    bands: tuple[AoABandSummary, ...]


@dataclass(frozen=True)
class AoAGroupSummary:
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
class AoATermSummary:
    source_term: str
    lookup_form: str
    mean_age: float
    source_rating_standard_deviation: float | None
    source_occurrence_total: int
    source_numeric_response_count: int
    source_unknown_response_count: int
    source_numeric_response_proportion: float
    matched_token_occurrences: int
    surface_forms: tuple[str, ...]
    part_of_speech_tags: tuple[str, ...]
    source_row: int


@dataclass(frozen=True)
class AoARelationshipSummary:
    relationship_id: str
    other_module: str
    other_metric: str
    pair_count: int
    coefficient: float | None
    method: str
    weighting: str
    note: str


@dataclass(frozen=True)
class AoAAnalysisResult:
    module_result: ModuleResult
    configuration: AoAConfiguration
    resource_status: ResourceStatus
    resource_validation: KupermanAoAValidation
    summary: AoASummary
    part_of_speech_summaries: tuple[AoAGroupSummary, ...]
    line_summaries: tuple[AoAGroupSummary, ...]
    stanza_summaries: tuple[AoAGroupSummary, ...]
    term_summaries: tuple[AoATermSummary, ...]
    earliest_acquired_terms: tuple[AoATermSummary, ...]
    latest_acquired_terms: tuple[AoATermSummary, ...]
    relationships: tuple[AoARelationshipSummary, ...]
    token_audit: tuple[AoATokenRating, ...]

    def __post_init__(self) -> None:
        eligible = sum(row.eligible for row in self.token_audit)
        matched = sum(row.included for row in self.token_audit)
        if (
            self.summary.eligible_token_count != eligible
            or self.summary.matched_token_count != matched
        ):
            raise ValueError("AoA summary counts must agree with the token audit.")
        if any(row.mean_age is not None for row in self.token_audit if not row.included):
            raise ValueError(
                "Unmatched, source-unrated, or ineligible AoA rows cannot carry "
                "a numeric mean age."
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


def _base_token_values(token: TokenRecord) -> dict[str, object]:
    return {
        "token_id": token.token_id,
        "token_position": token.token_position,
        "surface_form": token.surface_form,
        "normalized_form": token.normalized_form,
        "lemma": token.lemma,
        "normalized_lemma": token.normalized_lemma,
        "part_of_speech": token.part_of_speech,
        "line_number": token.line_number,
        "stanza_number": token.stanza_number,
        "context": token.context,
        "is_lexical": token.is_lexical,
        "is_proper_noun": token.is_proper_noun,
    }


def _matched_token(
    token: TokenRecord,
    entry: KupermanAoAEntry,
    method: AoAMatchMethod,
    reason: str,
) -> AoATokenRating:
    assert entry.mean_age is not None
    return AoATokenRating(
        **_base_token_values(token),
        eligible=True,
        included=True,
        match_method=method,
        matched_source_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        mean_age=entry.mean_age,
        source_rating_standard_deviation=entry.standard_deviation,
        source_occurrence_total=entry.occurrence_total,
        source_numeric_response_count=entry.numeric_response_count,
        source_unknown_response_count=entry.unknown_response_count,
        source_numeric_response_proportion=entry.numeric_response_proportion,
        source_dunno_value=entry.source_dunno_value,
        source_frequency_per_million=entry.frequency_per_million,
        reason=append_lexicon_eligibility_note(reason, token),
    )


def _source_unrated_token(
    token: TokenRecord,
    entry: KupermanAoAEntry,
    matched_by: AoAMatchMethod,
) -> AoATokenRating:
    return AoATokenRating(
        **_base_token_values(token),
        eligible=True,
        included=False,
        match_method=AoAMatchMethod.SOURCE_UNRATED,
        matched_source_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        mean_age=None,
        source_rating_standard_deviation=entry.standard_deviation,
        source_occurrence_total=entry.occurrence_total,
        source_numeric_response_count=entry.numeric_response_count,
        source_unknown_response_count=entry.unknown_response_count,
        source_numeric_response_proportion=entry.numeric_response_proportion,
        source_dunno_value=entry.source_dunno_value,
        source_frequency_per_million=entry.frequency_per_million,
        reason=append_lexicon_eligibility_note(
            f"A source entry was found by {matched_by.value}, but Rating.Mean is "
            "unavailable. The observation remains missing rather than receiving "
            "an invented age.",
            token,
        ),
    )


def _unmatched_token(
    token: TokenRecord,
    *,
    method: AoAMatchMethod,
    eligible: bool,
    reason: str,
) -> AoATokenRating:
    return AoATokenRating(
        **_base_token_values(token),
        eligible=eligible,
        included=False,
        match_method=method,
        matched_source_term=None,
        matched_lookup_form=None,
        source_row=None,
        mean_age=None,
        source_rating_standard_deviation=None,
        source_occurrence_total=None,
        source_numeric_response_count=None,
        source_unknown_response_count=None,
        source_numeric_response_proportion=None,
        source_dunno_value=None,
        source_frequency_per_million=None,
        reason=(
            append_lexicon_eligibility_note(reason, token)
            if eligible
            else reason
        ),
    )


def _ineligible_reason(
    token: TokenRecord,
    configuration: AoAConfiguration,
) -> str | None:
    if not is_lexicon_eligible(token):
        return lexicon_ineligibility_reason(token)
    if configuration.exclude_proper_nouns and token.is_proper_noun:
        return (
            "Excluded by the configured proper-name policy because a source "
            "spelling match need not represent this named entity."
        )
    return None


def _resolved_token(
    token: TokenRecord,
    entry: KupermanAoAEntry,
    method: AoAMatchMethod,
    reason: str,
) -> AoATokenRating:
    if entry.mean_age is None:
        return _source_unrated_token(token, entry, method)
    return _matched_token(token, entry, method, reason)


def _token_audit(
    module_input: ModuleInput,
    lexicon: KupermanAoALexicon,
    configuration: AoAConfiguration,
) -> tuple[AoATokenRating, ...]:
    rows = []
    for token in module_input.tokens:
        ineligible_reason = _ineligible_reason(token, configuration)
        if ineligible_reason is not None:
            rows.append(
                _unmatched_token(
                    token,
                    method=AoAMatchMethod.NOT_ELIGIBLE,
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
                _resolved_token(
                    token,
                    exact_entry,
                    AoAMatchMethod.EXACT,
                    (
                        "Exact normalized observed form matched before any lemma "
                        "or fallback was considered."
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
                _resolved_token(
                    token,
                    lemma_entry,
                    AoAMatchMethod.LEMMA,
                    (
                        "No exact observed-form entry was available; the "
                        "installed model's normalized lemma matched. This "
                        "substitution remains explicit in the audit."
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
        fallback_match: tuple[KupermanAoAEntry, str] | None = None
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
                _resolved_token(
                    token,
                    entry,
                    AoAMatchMethod.DOCUMENTED_FALLBACK,
                    (
                        "No exact observed-form or enabled lemma entry was "
                        f"available; the documented {label} matched."
                    ),
                )
            )
            continue
        rows.append(
            _unmatched_token(
                token,
                method=AoAMatchMethod.UNMATCHED,
                eligible=True,
                reason=(
                    "No exact observed form, enabled lemma, or documented "
                    "conservative fallback entry was found. AoA remains missing."
                ),
            )
        )
    return tuple(rows)


def _bands(
    values: tuple[float, ...],
    configuration: AoAConfiguration,
) -> tuple[AoABandSummary, ...]:
    definitions = (
        (
            "early_acquired",
            "Early-acquired",
            None,
            False,
            configuration.early_acquired_max,
            True,
        ),
        (
            "middle_range",
            "Middle range",
            configuration.early_acquired_max,
            False,
            configuration.later_acquired_min,
            False,
        ),
        (
            "later_acquired",
            "Later-acquired",
            configuration.later_acquired_min,
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
            (
                lower is None
                or value > lower
                or (lower_inclusive and value == lower)
            )
            and (
                upper is None
                or value < upper
                or (upper_inclusive and value == upper)
            )
            for value in values
        )
        rows.append(
            AoABandSummary(
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
    audit: tuple[AoATokenRating, ...],
    configuration: AoAConfiguration,
) -> AoASummary:
    eligible = tuple(row for row in audit if row.eligible)
    matched = tuple(
        row for row in eligible if row.included and row.mean_age is not None
    )
    values = tuple(row.mean_age for row in matched if row.mean_age is not None)
    source_sds = tuple(
        row.source_rating_standard_deviation
        for row in matched
        if row.source_rating_standard_deviation is not None
    )
    statistics = descriptive_statistics(values)
    eligible_types = {row.normalized_form for row in eligible}
    matched_types = {row.normalized_form for row in matched}
    response_counts = tuple(
        row.source_numeric_response_count
        for row in matched
        if row.source_numeric_response_count is not None
    )
    return AoASummary(
        statistics=statistics,
        interquartile_range=_iqr(statistics),
        source_standard_deviation_statistics=descriptive_statistics(source_sds),
        eligible_token_count=len(eligible),
        matched_token_count=len(matched),
        unmatched_token_count=len(eligible) - len(matched),
        source_unrated_token_count=sum(
            row.match_method is AoAMatchMethod.SOURCE_UNRATED for row in eligible
        ),
        token_coverage=_rate(len(matched), len(eligible)),
        eligible_unique_type_count=len(eligible_types),
        matched_unique_type_count=len(matched_types),
        unmatched_unique_type_count=len(eligible_types - matched_types),
        unique_type_coverage=_rate(len(matched_types), len(eligible_types)),
        minimum_source_numeric_responses=(
            min(response_counts) if response_counts else None
        ),
        low_response_token_count=sum(
            count < 5 for count in response_counts
        ),
        scope_label=configuration.scope_label,
        minimum_matched_tokens=configuration.minimum_matched_tokens,
        is_sparse=len(matched) < configuration.minimum_matched_tokens,
        bands=_bands(values, configuration),
    )


def _group_summary(
    rows: Iterable[AoATokenRating],
    *,
    scope: str,
    scope_id: str,
    ordinal: int,
    label: str,
    source_text: str,
) -> AoAGroupSummary:
    row_tuple = tuple(rows)
    eligible = tuple(row for row in row_tuple if row.eligible)
    matched = tuple(
        row for row in eligible if row.included and row.mean_age is not None
    )
    statistics = descriptive_statistics(
        row.mean_age for row in matched if row.mean_age is not None
    )
    eligible_types = {row.normalized_form for row in eligible}
    matched_types = {row.normalized_form for row in matched}
    return AoAGroupSummary(
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
    audit: tuple[AoATokenRating, ...],
    kind: StructuralUnitKind,
) -> tuple[AoAGroupSummary, ...]:
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
    audit: tuple[AoATokenRating, ...],
) -> tuple[AoAGroupSummary, ...]:
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
    audit: tuple[AoATokenRating, ...],
) -> tuple[AoATermSummary, ...]:
    by_lookup: dict[str, list[AoATokenRating]] = defaultdict(list)
    for row in audit:
        if row.included and row.matched_lookup_form is not None:
            by_lookup[row.matched_lookup_form].append(row)
    summaries = []
    for lookup_form, rows in by_lookup.items():
        first = rows[0]
        assert first.matched_source_term is not None
        assert first.mean_age is not None
        assert first.source_occurrence_total is not None
        assert first.source_numeric_response_count is not None
        assert first.source_unknown_response_count is not None
        assert first.source_numeric_response_proportion is not None
        assert first.source_row is not None
        summaries.append(
            AoATermSummary(
                source_term=first.matched_source_term,
                lookup_form=lookup_form,
                mean_age=first.mean_age,
                source_rating_standard_deviation=(
                    first.source_rating_standard_deviation
                ),
                source_occurrence_total=first.source_occurrence_total,
                source_numeric_response_count=first.source_numeric_response_count,
                source_unknown_response_count=first.source_unknown_response_count,
                source_numeric_response_proportion=(
                    first.source_numeric_response_proportion
                ),
                matched_token_occurrences=len(rows),
                surface_forms=tuple(
                    sorted({row.surface_form for row in rows}, key=str.casefold)
                ),
                part_of_speech_tags=tuple(
                    sorted({row.part_of_speech or "X" for row in rows})
                ),
                source_row=first.source_row,
            )
        )
    return tuple(sorted(summaries, key=lambda item: item.source_term.casefold()))


def _warnings(
    summary: AoASummary,
    audit: tuple[AoATokenRating, ...],
    configuration: AoAConfiguration,
) -> tuple[ModuleWarning, ...]:
    warnings = [
        ModuleWarning(
            code="aoa_non_diagnostic",
            message=(
                "Age-of-acquisition results describe retrospective normative "
                "lexical patterns and are not diagnostic of cognitive impairment "
                "or decline."
            ),
            severity=WarningSeverity.INFORMATION,
        ),
        ModuleWarning(
            code="source_sampling_and_context",
            message=(
                "The paper selected base forms used chiefly as nouns, verbs, or "
                "adjectives, but the official supplement includes polyfunctional "
                "spellings that can occur as function words. Source sampling and "
                "the poem occurrence's model POS are separate evidence."
            ),
            severity=WarningSeverity.INFORMATION,
        ),
        ModuleWarning(
            code="aoa_orientation_bands",
            message=(
                "Early- and later-acquired thresholds are configurable VerseVAD "
                "orientation aids, not categories validated by the source paper."
            ),
            severity=WarningSeverity.INFORMATION,
        ),
    ]
    if not summary.eligible_token_count:
        warnings.append(
            ModuleWarning(
                code="no_eligible_tokens",
                message=(
                    "No tokens were eligible under the selected AoA scope. "
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
                    "No eligible word had an available numeric Kuperman rating. "
                    "Aggregate values remain missing rather than becoming zero."
                ),
            )
        )
    if summary.source_unrated_token_count:
        warnings.append(
            ModuleWarning(
                code="source_entries_without_numeric_ratings",
                message=(
                    "Some spellings were present in the source but had no numeric "
                    "Rating.Mean. They remain unavailable and do not contribute."
                ),
                technical_detail=(
                    f"{summary.source_unrated_token_count} token occurrence(s)."
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
                    "AoA coverage is below the configured caution threshold of "
                    f"{configuration.low_coverage_warning_threshold:.0%}. Inspect "
                    "unmatched vocabulary before interpreting aggregates."
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
                code="legacy_content_scope_migrated",
                message=(
                    "A legacy content-word setting was retained as provenance. "
                    "The completed result still retains all lexical evidence; "
                    "Content words only is now selected in report controls."
                ),
                severity=WarningSeverity.INFORMATION,
            )
        )
    if summary.low_response_token_count:
        warnings.append(
            ModuleWarning(
                code="low_source_response_count",
                message=(
                    "Some represented source means are based on fewer than five "
                    "numeric responses. The paper recommends caution with such "
                    "items in small stimulus sets; response counts remain visible."
                ),
                severity=WarningSeverity.INFORMATION,
                technical_detail=(
                    f"{summary.low_response_token_count} matched token occurrence(s)."
                ),
            )
        )
    lemma_count = sum(row.match_method is AoAMatchMethod.LEMMA for row in audit)
    if lemma_count:
        warnings.append(
            ModuleWarning(
                code="lemma_aoa_fallback",
                message=(
                    "Some observed forms were absent and used an explicitly "
                    "audited model-lemma fallback. These are not exact observed-"
                    "form matches."
                ),
                severity=WarningSeverity.INFORMATION,
                technical_detail=f"{lemma_count} token occurrence(s) used a lemma.",
            )
        )
    return tuple(warnings)


def _module_metrics(
    summary: AoASummary,
    groups: tuple[AoAGroupSummary, ...],
) -> tuple[ModuleMetric, ...]:
    statistics = summary.statistics
    document_values = (
        ("aoa.mean_years", statistics.mean, "source mean age in years"),
        ("aoa.median_years", statistics.median, "source mean age in years"),
        (
            "aoa.population_standard_deviation",
            statistics.population_standard_deviation,
            "years",
        ),
        ("aoa.minimum_years", statistics.minimum, "source mean age in years"),
        (
            "aoa.first_quartile_years",
            statistics.first_quartile,
            "source mean age in years",
        ),
        (
            "aoa.third_quartile_years",
            statistics.third_quartile,
            "source mean age in years",
        ),
        ("aoa.interquartile_range", summary.interquartile_range, "years"),
        ("aoa.maximum_years", statistics.maximum, "source mean age in years"),
        (
            "aoa.mean_source_rating_standard_deviation",
            summary.source_standard_deviation_statistics.mean,
            "source-rating years",
        ),
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
                "This is dispersion among the poem's matched normative mean "
                "ratings, not uncertainty within each source entry."
                if metric_id == "aoa.population_standard_deviation"
                else ""
            ),
        )
        for metric_id, value, unit in document_values
    ]
    metrics.extend(
        ModuleMetric(
            metric_id=f"aoa.band.{band.band_id}.proportion",
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
                    metric_id="aoa.mean_years",
                    value=group.statistics.mean,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="source mean age in years",
                    weighting="matched token occurrences",
                    denominator=f"{group.matched_token_count} matched tokens",
                ),
                ModuleMetric(
                    metric_id="aoa.median_years",
                    value=group.statistics.median,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope=group.scope,
                    scope_id=group.scope_id,
                    unit="source mean age in years",
                    weighting="matched token occurrences",
                    denominator=f"{group.matched_token_count} matched tokens",
                ),
                ModuleMetric(
                    metric_id="aoa.token_coverage",
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


def _average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2
        for position in range(start, end):
            ranks[ordered[position][0]] = average_rank
        start = end
    return tuple(ranks)


def _pearson(left: tuple[float, ...], right: tuple[float, ...]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_sum = sum((value - left_mean) ** 2 for value in left)
    right_sum = sum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_sum * right_sum)
    return numerator / denominator if denominator else None


def _spearman(pairs: tuple[tuple[float, float], ...]) -> float | None:
    if len(pairs) < 2:
        return None
    left = tuple(pair[0] for pair in pairs)
    right = tuple(pair[1] for pair in pairs)
    return _pearson(_average_ranks(left), _average_ranks(right))


def _paired_types(
    aoa: AoAAnalysisResult,
    other_rows: Iterable[object],
    *,
    value_field: str,
    exclude_multiword: bool = False,
) -> tuple[tuple[float, float], ...]:
    aoa_by_token = {
        row.token_id: row
        for row in aoa.token_audit
        if row.included and row.mean_age is not None
    }
    by_type: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for other in other_rows:
        token_id = getattr(other, "token_id", "")
        aoa_row = aoa_by_token.get(token_id)
        other_value = getattr(other, value_field, None)
        if (
            aoa_row is None
            or not getattr(other, "included", False)
            or other_value is None
        ):
            continue
        if exclude_multiword and getattr(other, "source_is_multiword", False):
            continue
        by_type[aoa_row.normalized_form].append(
            (aoa_row.mean_age, float(other_value))
        )
    return tuple(
        (fmean(pair[0] for pair in values), fmean(pair[1] for pair in values))
        for _lookup, values in sorted(by_type.items())
    )


def attach_aoa_relationships(
    aoa: AoAAnalysisResult,
    *,
    frequency: FrequencyAnalysisResult | None = None,
    concreteness: ConcretenessAnalysisResult | None = None,
) -> AoAAnalysisResult:
    """Attach optional descriptive type-level relationships to enabled modules."""

    relationships = []
    if frequency is not None:
        pairs = _paired_types(
            aoa,
            frequency.token_audit,
            value_field="zipf_value",
        )
        relationships.append(
            AoARelationshipSummary(
                relationship_id="aoa_vs_frequency",
                other_module=frequency.module_result.module_name,
                other_metric="SUBTLEX-US Zipf frequency",
                pair_count=len(pairs),
                coefficient=(
                    _spearman(pairs)
                    if len(pairs) >= aoa.configuration.minimum_relationship_types
                    else None
                ),
                method="Spearman rank correlation",
                weighting="unique normalized observed surface types",
                note=(
                    "Descriptive only; repeated occurrences are collapsed and "
                    "the association does not establish causation."
                ),
            )
        )
    if concreteness is not None:
        pairs = _paired_types(
            aoa,
            concreteness.token_audit,
            value_field="rating",
            exclude_multiword=True,
        )
        relationships.append(
            AoARelationshipSummary(
                relationship_id="aoa_vs_concreteness",
                other_module=concreteness.module_result.module_name,
                other_metric="normative concreteness",
                pair_count=len(pairs),
                coefficient=(
                    _spearman(pairs)
                    if len(pairs) >= aoa.configuration.minimum_relationship_types
                    else None
                ),
                method="Spearman rank correlation",
                weighting="unique normalized observed surface types",
                note=(
                    "Descriptive only; repeated occurrences are collapsed, "
                    "multiword concreteness assignments are excluded, and the "
                    "association does not establish causation."
                ),
            )
        )
    if not relationships:
        return aoa

    relationship_metrics = tuple(
        ModuleMetric(
            metric_id=f"aoa.relationship.{item.relationship_id}.spearman",
            value=item.coefficient,
            layer=ResultLayer.COMPUTED_SUMMARY,
            unit="Spearman rho",
            weighting=item.weighting,
            denominator=f"{item.pair_count} paired types",
            note=item.note,
        )
        for item in relationships
    )
    relationship_warnings = tuple(
        ModuleWarning(
            code=f"{item.relationship_id}_sparse",
            message=(
                f"The {item.other_metric} relationship has fewer than "
                f"{aoa.configuration.minimum_relationship_types} paired types; "
                "its coefficient remains missing."
            ),
            severity=WarningSeverity.INFORMATION,
            technical_detail=f"{item.pair_count} paired type(s).",
        )
        for item in relationships
        if item.pair_count < aoa.configuration.minimum_relationship_types
    )
    updated_module_result = replace(
        aoa.module_result,
        metrics=(*aoa.module_result.metrics, *relationship_metrics),
        warnings=(*aoa.module_result.warnings, *relationship_warnings),
    )
    return replace(
        aoa,
        module_result=updated_module_result,
        relationships=tuple(relationships),
    )


@lru_cache(maxsize=12)
def _load_cached(path: str, source_sha256: str) -> KupermanAoALexicon:
    del source_sha256
    return KupermanAoAAdapter().load(Path(path))


class AoAModule:
    """Framework-independent optional Stage 4 module backed by Kuperman data."""

    name = "age_of_acquisition"
    version = "1.1.0"

    def __init__(
        self,
        resource_root: Path | str,
        *,
        resource_spec: ResourceSpec = KUPERMAN_AOA_SPEC,
    ) -> None:
        self.resource_root = Path(resource_root)
        self.resource_spec = resource_spec
        self.resource_manager = LocalResourceManager(self.resource_root)

    def validate_resources(self) -> tuple[ResourceStatus, ...]:
        status = self.resource_manager.validate(self.resource_spec)
        if status.available:
            try:
                _load_cached(str(status.configured_path), status.source_sha256)
            except KupermanAoAAdapterError as error:
                status = replace(
                    status,
                    state=ResourceState.MALFORMED,
                    message=(
                        f"{self.resource_spec.display_name} is readable but does "
                        f"not satisfy the workbook contract: {error}"
                    ),
                )
        return (status,)

    def _available(self) -> tuple[ResourceStatus, KupermanAoALexicon]:
        status = self.validate_resources()[0]
        if not status.available:
            raise AoAModuleError(status.message)
        try:
            lexicon = _load_cached(
                str(status.configured_path), status.source_sha256
            )
        except KupermanAoAAdapterError as error:
            detail = (
                f" Technical detail: {error.technical_detail}"
                if error.technical_detail
                else ""
            )
            raise AoAModuleError(f"{error}{detail}") from error
        return status, lexicon

    def analyze(self, module_input: ModuleInput) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: AoAConfiguration | None = None,
    ) -> AoAAnalysisResult:
        config = configuration or AoAConfiguration()
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
        earliest = tuple(
            sorted(
                terms,
                key=lambda item: (
                    item.mean_age,
                    -item.matched_token_occurrences,
                    item.source_term.casefold(),
                ),
            )
        )[: config.top_term_count]
        latest = tuple(
            sorted(
                terms,
                key=lambda item: (
                    -item.mean_age,
                    -item.matched_token_occurrences,
                    item.source_term.casefold(),
                ),
            )
        )[: config.top_term_count]
        warnings = _warnings(summary, audit, config)
        resource_provenance = ResourceProvenance.from_available_status(
            status,
            citation=self.resource_spec.citation,
            license_notice=self.resource_spec.license_notice,
            adapter_version=KupermanAoAAdapter.adapter_version,
        )
        inclusion_policy = (
            "All ordinary lexical tokens plus alphabetically spelled "
            "number-like tokens; punctuation and pure numeric literals excluded; "
            + (
                "model-tagged proper nouns excluded by explicit configuration."
                if config.exclude_proper_nouns
                else "model-tagged proper nouns included by default."
            )
            + " Scope and weighting are applied later from retained evidence."
        )
        lookup_policy = (
            "Exact normalized observed form first; "
            + (
                "then explicit model-lemma fallback; "
                if config.enable_lemma_fallback
                else "lemma fallback disabled; "
            )
            + "then documented apostrophe/possessive fallbacks; source entries "
            "without numeric means and unmatched observations remain missing."
        )
        result_signature = "|".join(
            (
                self.name,
                self.version,
                LEXICON_ELIGIBILITY_POLICY_ID,
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
                    coverage_id="aoa.matched_token_coverage",
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
                        "Unmatched and source-unrated observations remain missing "
                        "rather than receiving zero or an estimated acquisition age."
                    ),
                ),
                ModuleCoverage.from_counts(
                    coverage_id="aoa.matched_unique_word_coverage",
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
        return AoAAnalysisResult(
            module_result=module_result,
            configuration=config,
            resource_status=status,
            resource_validation=lexicon.validation,
            summary=summary,
            part_of_speech_summaries=pos_summaries,
            line_summaries=line_summaries,
            stanza_summaries=stanza_summaries,
            term_summaries=terms,
            earliest_acquired_terms=earliest,
            latest_acquired_terms=latest,
            relationships=(),
            token_audit=audit,
        )
