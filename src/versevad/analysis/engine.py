"""Exact-first VAD matching and transparent Phase 1 aggregation."""

from __future__ import annotations

import hashlib

from versevad.analysis.statistics import weighted_vad_statistics
from versevad.lexical_eligibility import (
    LEXICON_ELIGIBILITY_POLICY_ID,
    append_lexicon_eligibility_note,
    is_lexicon_eligible,
    lexicon_ineligibility_reason,
)
from versevad.models import (
    AnalysisResult,
    CoverageStatistics,
    MatchMethod,
    TextDocument,
    TokenMatch,
    VadLexicon,
    VadSummary,
)
from versevad.normalization import normalize_lookup, possessive_surface_base
from versevad.preprocessing import TextPreprocessor


DEFAULT_SCENARIO_ID = "phase1-default-v2"


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _resolve_token(token: object, lexicon: VadLexicon) -> TokenMatch:
    if not is_lexicon_eligible(token):
        return TokenMatch(
            token_id=token.token_id,
            lexicon_id=lexicon.metadata.lexicon_id,
            method=MatchMethod.NOT_ELIGIBLE,
            matched_term=None,
            matched_lookup_form=None,
            source_row=None,
            original_scores=None,
            normalized_scores=None,
            included=False,
            reason=lexicon_ineligibility_reason(token),
        )

    entry, unresolved_conflict = lexicon.resolve(
        token.normalized_form, token.surface_form
    )
    method = MatchMethod.EXACT
    reason = append_lexicon_eligibility_note(
        "Exact normalized surface-form match.", token
    )

    if unresolved_conflict:
        return TokenMatch(
            token_id=token.token_id,
            lexicon_id=lexicon.metadata.lexicon_id,
            method=MatchMethod.UNMATCHED,
            matched_term=None,
            matched_lookup_form=token.normalized_form,
            source_row=None,
            original_scores=None,
            normalized_scores=None,
            included=False,
            reason=(
                "Multiple source entries collide under case-insensitive lookup, "
                "and capitalization did not identify one source form. Review is required."
            ),
        )

    if entry is None:
        base_surface = possessive_surface_base(token.surface_form)
        if base_surface is not None:
            entry, unresolved_conflict = lexicon.resolve(
                normalize_lookup(base_surface), base_surface
            )
            if unresolved_conflict:
                return TokenMatch(
                    token_id=token.token_id,
                    lexicon_id=lexicon.metadata.lexicon_id,
                    method=MatchMethod.UNMATCHED,
                    matched_term=None,
                    matched_lookup_form=normalize_lookup(base_surface),
                    source_row=None,
                    original_scores=None,
                    normalized_scores=None,
                    included=False,
                    reason=(
                        "Possessive normalization reached case-colliding source "
                        "entries that require review."
                    ),
                )
            if entry is not None:
                method = MatchMethod.POSSESSIVE
                reason = append_lexicon_eligibility_note(
                    "Matched after conservative possessive normalization.", token
                )

    if entry is None and token.normalized_lemma != token.normalized_form:
        entry, unresolved_conflict = lexicon.resolve(
            token.normalized_lemma, token.lemma
        )
        if unresolved_conflict:
            return TokenMatch(
                token_id=token.token_id,
                lexicon_id=lexicon.metadata.lexicon_id,
                method=MatchMethod.UNMATCHED,
                matched_term=None,
                matched_lookup_form=token.normalized_lemma,
                source_row=None,
                original_scores=None,
                normalized_scores=None,
                included=False,
                reason=(
                    "Lemma fallback reached case-colliding source entries that "
                    "require review."
                ),
            )
        if entry is not None:
            method = MatchMethod.LEMMA
            reason = append_lexicon_eligibility_note(
                "Matched by POS-sensitive lemma after exact candidates failed.",
                token,
            )

    if entry is None:
        return TokenMatch(
            token_id=token.token_id,
            lexicon_id=lexicon.metadata.lexicon_id,
            method=MatchMethod.UNMATCHED,
            matched_term=None,
            matched_lookup_form=None,
            source_row=None,
            original_scores=None,
            normalized_scores=None,
            included=False,
            reason=append_lexicon_eligibility_note(
                "No lexicon entry matched under the Phase 1 policy.", token
            ),
        )

    return TokenMatch(
        token_id=token.token_id,
        lexicon_id=lexicon.metadata.lexicon_id,
        method=method,
        matched_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        original_scores=entry.original,
        normalized_scores=entry.normalized,
        included=True,
        reason=reason,
    )


def analyze_vad(
    document: TextDocument,
    lexicon: VadLexicon,
    preprocessor: TextPreprocessor,
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    minimum_match_requirement: int = 3,
) -> AnalysisResult:
    """Analyze a text while retaining every token and match decision."""

    if minimum_match_requirement < 1:
        raise ValueError("minimum_match_requirement must be at least 1")
    if not lexicon.validation.is_valid:
        raise ValueError("A lexicon with validation errors cannot be analyzed.")

    tokens = preprocessor.process(document)
    matches = tuple(_resolve_token(token, lexicon) for token in tokens)
    lexical_tokens = tuple(token for token in tokens if is_lexicon_eligible(token))
    token_by_id = {token.token_id: token for token in tokens}
    included = tuple(match for match in matches if match.included)

    lexical_types = {token.normalized_form for token in lexical_tokens}
    matched_surface_types = {
        token_by_id[match.token_id].normalized_form for match in included
    }
    exact_count = sum(match.method == MatchMethod.EXACT for match in included)
    possessive_count = sum(match.method == MatchMethod.POSSESSIVE for match in included)
    lemma_count = sum(match.method == MatchMethod.LEMMA for match in included)

    coverage = CoverageStatistics(
        total_tokens=len(tokens),
        total_lexical_tokens=len(lexical_tokens),
        total_unique_types=len(lexical_types),
        matched_token_count=len(included),
        unmatched_token_count=len(lexical_tokens) - len(included),
        matched_type_count=len(matched_surface_types),
        unmatched_type_count=len(lexical_types) - len(matched_surface_types),
        token_coverage=_safe_rate(len(included), len(tokens)),
        lexical_token_coverage=_safe_rate(len(included), len(lexical_tokens)),
        type_coverage=_safe_rate(len(matched_surface_types), len(lexical_types)),
        exact_match_count=exact_count,
        exact_match_coverage=_safe_rate(exact_count, len(lexical_tokens)),
        possessive_match_count=possessive_count,
        possessive_match_coverage=_safe_rate(possessive_count, len(lexical_tokens)),
        lemma_fallback_count=lemma_count,
        lemma_fallback_coverage=_safe_rate(lemma_count, len(lexical_tokens)),
        phrase_match_count=0,
        phrase_match_coverage=_safe_rate(0, len(lexical_tokens)),
        approved_mapping_count=0,
        approved_mapping_coverage=_safe_rate(0, len(lexical_tokens)),
        compound_derived_count=0,
        compound_derived_coverage=_safe_rate(0, len(lexical_tokens)),
        excluded_token_count=0,
        excluded_token_rate=_safe_rate(0, len(lexical_tokens)),
    )

    unique_matches = {}
    for match in included:
        assert match.matched_lookup_form is not None
        unique_matches.setdefault(match.matched_lookup_form, match)

    token_original = tuple(
        match.original_scores for match in included if match.original_scores is not None
    )
    token_normalized = tuple(
        match.normalized_scores
        for match in included
        if match.normalized_scores is not None
    )
    type_original = tuple(
        match.original_scores
        for match in unique_matches.values()
        if match.original_scores is not None
    )
    type_normalized = tuple(
        match.normalized_scores
        for match in unique_matches.values()
        if match.normalized_scores is not None
    )
    summary = VadSummary(
        token_weighted_original=weighted_vad_statistics(token_original),
        type_weighted_original=weighted_vad_statistics(type_original),
        token_weighted_normalized=weighted_vad_statistics(token_normalized),
        type_weighted_normalized=weighted_vad_statistics(type_normalized),
        minimum_match_requirement=minimum_match_requirement,
        is_sparse=len(included) < minimum_match_requirement,
    )

    warnings = list(lexicon.validation.warnings)
    if not included:
        warnings.append(
            "No lexical tokens matched this lexicon. VAD statistics are missing, not zero."
        )
    elif summary.is_sparse:
        warnings.append(
            f"Only {len(included)} matched token occurrence(s) met the active policy; "
            f"the configured minimum is {minimum_match_requirement}. Treat the "
            "aggregate as sparse."
        )

    signature = "|".join(
        (
            document.text_sha256,
            lexicon.validation.source_sha256,
            lexicon.metadata.adapter_version,
            preprocessor.metadata.recipe_id,
            preprocessor.metadata.pipeline_name,
            preprocessor.metadata.pipeline_version,
            LEXICON_ELIGIBILITY_POLICY_ID,
            scenario_id,
            str(minimum_match_requirement),
        )
    )
    analysis_id = hashlib.sha256(signature.encode("utf-8")).hexdigest()

    return AnalysisResult(
        analysis_id=analysis_id,
        scenario_id=scenario_id,
        document=document,
        lexicon_metadata=lexicon.metadata,
        lexicon_validation=lexicon.validation,
        preprocessing=preprocessor.metadata,
        tokens=tokens,
        matches=matches,
        coverage=coverage,
        vad_summary=summary,
        warnings=tuple(warnings),
    )
