"""Phase 2 multi-lexicon matching, aggregation, and comparison."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from typing import Iterable

from versevad.analysis.statistics import descriptive_statistics, weighted_vad_statistics
from versevad.models import (
    AffectMatchRecord,
    ComparisonMetric,
    CoverageStatistics,
    CrossLexiconComparison,
    EmotionAssociationEntry,
    EmotionAssociationLexicon,
    EmotionCategoryStatistics,
    EmotionIntensityEntry,
    EmotionIntensityLexicon,
    EmotionIntensityStatistics,
    LexiconValueKind,
    MatchMethod,
    MatchSelection,
    Phase2AnalysisResult,
    PhrasePolicy,
    ReviewAction,
    ReviewRule,
    ReviewScope,
    StopwordCoverageStatistics,
    StopwordPolicy,
    TermContribution,
    TextDocument,
    TokenRecord,
    VadEntry,
    VadLexicon,
    VadSummary,
)
from versevad.lexical_eligibility import (
    LEXICON_ELIGIBILITY_POLICY_ID,
    append_lexicon_eligibility_note,
    is_lexicon_eligible,
    lexicon_ineligibility_reason,
)
from versevad.normalization import normalize_lookup, possessive_surface_base
from versevad.preprocessing import TextPreprocessor
from versevad.stopwords import build_stopword_policy, classify_match_stopword


PHASE2_SCENARIO_ID = "phase2-multi-lexicon-v2"
SupportedLexicon = VadLexicon | EmotionAssociationLexicon | EmotionIntensityLexicon
SupportedEntry = VadEntry | EmotionAssociationEntry | EmotionIntensityEntry


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _entry_payload(entry: SupportedEntry) -> dict[str, object]:
    if isinstance(entry, VadEntry):
        return {
            "source_rows": (entry.source_row,),
            "original_scores": entry.original,
            "normalized_scores": entry.normalized,
            "associations": (),
            "intensities": (),
        }
    if isinstance(entry, EmotionAssociationEntry):
        return {
            "source_rows": entry.source_rows,
            "original_scores": None,
            "normalized_scores": None,
            "associations": entry.associations,
            "intensities": (),
        }
    return {
        "source_rows": entry.source_rows,
        "original_scores": None,
        "normalized_scores": None,
        "associations": (),
        "intensities": entry.intensities,
    }


def _record(
    *,
    match_id: str,
    lexicon_id: str,
    tokens: tuple[TokenRecord, ...],
    method: MatchMethod,
    selection: MatchSelection,
    entry: SupportedEntry | None,
    included: bool,
    reason: str,
    stopword_policy: StopwordPolicy,
    suppressed_by: str | None = None,
) -> AffectMatchRecord:
    first = tokens[0]
    payload = _entry_payload(entry) if entry is not None else {
        "source_rows": (),
        "original_scores": None,
        "normalized_scores": None,
        "associations": (),
        "intensities": (),
    }
    stopword_status, stopword_excluded, stopword_reason = classify_match_stopword(
        tokens,
        stopword_policy,
        is_published_phrase=method == MatchMethod.PHRASE and entry is not None,
    )
    return AffectMatchRecord(
        match_id=match_id,
        lexicon_id=lexicon_id,
        token_ids=tuple(token.token_id for token in tokens),
        start_token_position=first.token_position,
        end_token_position=tokens[-1].token_position,
        line_number=first.line_number,
        stanza_number=first.stanza_number,
        method=method,
        selection=selection,
        matched_term=entry.source_term if entry is not None else None,
        matched_lookup_form=entry.lookup_form if entry is not None else None,
        included=included,
        suppressed_by_match_id=suppressed_by,
        reason=reason,
        stopword_status=stopword_status,
        included_in_stopword_view=included and not stopword_excluded,
        stopword_exclusion_reason=stopword_reason,
        **payload,
    )


def _resolve_unigram(
    token: TokenRecord, lexicon: SupportedLexicon
) -> tuple[SupportedEntry | None, MatchMethod, str]:
    if not is_lexicon_eligible(token):
        return None, MatchMethod.NOT_ELIGIBLE, lexicon_ineligibility_reason(token)
    entry, conflict = lexicon.resolve(token.normalized_form, token.surface_form)
    if conflict:
        return (
            None,
            MatchMethod.UNMATCHED,
            append_lexicon_eligibility_note(
                "Case-insensitive source collision requires review; no entry was guessed.",
                token,
            ),
        )
    if entry is not None:
        return (
            entry,
            MatchMethod.EXACT,
            append_lexicon_eligibility_note(
                "Exact normalized surface-form match.", token
            ),
        )

    possessive = possessive_surface_base(token.surface_form)
    if possessive is not None:
        entry, conflict = lexicon.resolve(normalize_lookup(possessive), possessive)
        if conflict:
            return (
                None,
                MatchMethod.UNMATCHED,
                append_lexicon_eligibility_note(
                    "Possessive normalization reached a source collision requiring review.",
                    token,
                ),
            )
        if entry is not None:
            return (
                entry,
                MatchMethod.POSSESSIVE,
                append_lexicon_eligibility_note(
                    "Matched after conservative possessive normalization.", token
                ),
            )

    if token.normalized_lemma != token.normalized_form:
        entry, conflict = lexicon.resolve(token.normalized_lemma, token.lemma)
        if conflict:
            return (
                None,
                MatchMethod.UNMATCHED,
                append_lexicon_eligibility_note(
                    "Lemma fallback reached a source collision requiring review.",
                    token,
                ),
            )
        if entry is not None:
            return (
                entry,
                MatchMethod.LEMMA,
                append_lexicon_eligibility_note(
                    "Matched by POS-sensitive lemma after exact candidates failed.",
                    token,
                ),
            )
    return (
        None,
        MatchMethod.UNMATCHED,
        append_lexicon_eligibility_note(
            "No entry matched under the Phase 2 policy.", token
        ),
    )


_REVIEW_SCOPE_PRIORITY = {
    ReviewScope.GLOBAL: 0,
    ReviewScope.PROJECT: 1,
    ReviewScope.WORK: 2,
    ReviewScope.OCCURRENCE: 3,
}


def _rule_matches_tokens(
    rule: ReviewRule,
    tokens: tuple[TokenRecord, ...],
) -> bool:
    """Match a normalized selector without widening its declared scope."""

    if not tokens:
        return False
    observed = " ".join(token.normalized_form for token in tokens)
    first = tokens[0]
    if observed != rule.source_form:
        return False
    if rule.scope in {ReviewScope.WORK, ReviewScope.OCCURRENCE}:
        if rule.text_id != first.text_id:
            return False
    if rule.scope == ReviewScope.OCCURRENCE:
        return (
            rule.text_version_id == first.text_version_id
            and rule.token_position == first.token_position
        )
    return True


def _top_mapping_rule(
    rules: tuple[ReviewRule, ...],
    token: TokenRecord,
) -> ReviewRule | None:
    candidates = [
        rule
        for rule in rules
        if rule.action == ReviewAction.MAP
        and _rule_matches_tokens(rule, (token,))
    ]
    if not candidates:
        return None
    highest = max(_REVIEW_SCOPE_PRIORITY[rule.scope] for rule in candidates)
    top = [
        rule
        for rule in candidates
        if _REVIEW_SCOPE_PRIORITY[rule.scope] == highest
    ]
    targets = {rule.mapping_target for rule in top}
    if len(targets) > 1:
        raise ValueError(
            f"Conflicting active review mappings target {token.surface_form!r} "
            "at the same scope. Revise the scenario before analysis."
        )
    return sorted(top, key=lambda rule: rule.decision_revision_id)[-1]


def _review_exclusion_revisions(
    rules: tuple[ReviewRule, ...],
    tokens: tuple[TokenRecord, ...],
) -> tuple[str, ...]:
    return tuple(
        rule.decision_revision_id
        for rule in rules
        if rule.action == ReviewAction.EXCLUDE
        and _rule_matches_tokens(rule, tokens)
    )


def _phrase_candidates(
    tokens: tuple[TokenRecord, ...], lexicon: SupportedLexicon
) -> list[tuple[tuple[TokenRecord, ...], SupportedEntry]]:
    if not lexicon.metadata.phrase_support:
        return []
    phrase_index: dict[str, list[tuple[tuple[str, ...], SupportedEntry]]] = defaultdict(list)
    for key, entry in lexicon.entries.items():
        parts = tuple(key.split())
        if len(parts) > 1:
            phrase_index[parts[0]].append((parts, entry))
    for values in phrase_index.values():
        values.sort(key=lambda item: (-len(item[0]), item[0]))

    candidates: list[tuple[tuple[TokenRecord, ...], SupportedEntry]] = []
    for start, token in enumerate(tokens):
        if not is_lexicon_eligible(token):
            continue
        for parts, entry in phrase_index.get(token.normalized_form, ()):
            end = start + len(parts)
            if end > len(tokens):
                continue
            span = tokens[start:end]
            if any(not is_lexicon_eligible(item) for item in span):
                continue
            if any(item.line_number != token.line_number for item in span):
                continue
            if tuple(item.normalized_form for item in span) == parts:
                candidates.append((span, entry))
    return candidates


def _select_phrases(
    candidates: list[tuple[tuple[TokenRecord, ...], SupportedEntry]],
) -> tuple[
    list[tuple[tuple[TokenRecord, ...], SupportedEntry]],
    list[tuple[tuple[TokenRecord, ...], SupportedEntry]],
]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            -len(item[0]),
            item[0][0].token_position,
            item[1].lookup_form,
        ),
    )
    occupied: set[str] = set()
    selected = []
    suppressed = []
    for span, entry in ordered:
        token_ids = {token.token_id for token in span}
        if occupied.isdisjoint(token_ids):
            selected.append((span, entry))
            occupied.update(token_ids)
        else:
            suppressed.append((span, entry))
    selected.sort(key=lambda item: item[0][0].token_position)
    suppressed.sort(key=lambda item: item[0][0].token_position)
    return selected, suppressed


def _build_matches(
    tokens: tuple[TokenRecord, ...],
    lexicon: SupportedLexicon,
    phrase_policy: PhrasePolicy,
    stopword_policy: StopwordPolicy,
    review_rules: tuple[ReviewRule, ...],
) -> tuple[tuple[AffectMatchRecord, ...], tuple[str, ...]]:
    records: list[AffectMatchRecord] = []
    review_warnings: list[str] = []
    selected_phrases = []
    suppressed_phrases = []
    if phrase_policy != PhrasePolicy.UNIGRAM_ONLY:
        selected_phrases, suppressed_phrases = _select_phrases(
            _phrase_candidates(tokens, lexicon)
        )

    phrase_by_token: dict[str, str] = {}
    for span, entry in selected_phrases:
        match_id = f"{lexicon.metadata.lexicon_id}:m{len(records) + 1}"
        record = _record(
            match_id=match_id,
            lexicon_id=lexicon.metadata.lexicon_id,
            tokens=span,
            method=MatchMethod.PHRASE,
            selection=MatchSelection.INCLUDED,
            entry=entry,
            included=True,
            stopword_policy=stopword_policy,
            reason=append_lexicon_eligibility_note(
                "Selected as the deterministic longest non-overlapping exact "
                "phrase candidate.",
                span,
            ),
        )
        exclusion_revisions = _review_exclusion_revisions(review_rules, span)
        if exclusion_revisions:
            record = replace(
                record,
                selection=MatchSelection.EXCLUDED_REVIEW,
                included=False,
                included_in_stopword_view=False,
                reason=(
                    "Excluded by active review decision revision(s): "
                    + ", ".join(exclusion_revisions)
                    + ". The published phrase match remains in the audit trail."
                ),
            )
        records.append(record)
        for token in span:
            phrase_by_token[token.token_id] = match_id

    for span, entry in suppressed_phrases:
        suppressor = next(
            phrase_by_token[token.token_id]
            for token in span
            if token.token_id in phrase_by_token
        )
        records.append(
            _record(
                match_id=f"{lexicon.metadata.lexicon_id}:m{len(records) + 1}",
                lexicon_id=lexicon.metadata.lexicon_id,
                tokens=span,
                method=MatchMethod.PHRASE,
                selection=MatchSelection.SUPPRESSED_OVERLAP,
                entry=entry,
                included=False,
                stopword_policy=stopword_policy,
                suppressed_by=suppressor,
                reason="A longer or earlier equal-length phrase occupied part of this span.",
            )
        )

    for token in tokens:
        entry, method, reason = _resolve_unigram(token, lexicon)
        if (
            entry is None
            and method == MatchMethod.UNMATCHED
            and token.token_id not in phrase_by_token
        ):
            mapping_rule = _top_mapping_rule(review_rules, token)
            if mapping_rule is not None:
                target = normalize_lookup(mapping_rule.mapping_target)
                mapped_entry, conflict = lexicon.resolve(
                    target,
                    mapping_rule.mapping_target,
                )
                if conflict:
                    review_warnings.append(
                        f"Review mapping {mapping_rule.decision_revision_id} for "
                        f"{token.surface_form!r} reached a source collision and was not applied."
                    )
                elif mapped_entry is None:
                    review_warnings.append(
                        f"Review mapping {mapping_rule.decision_revision_id} targets "
                        f"{mapping_rule.mapping_target!r}, which is not an exact published "
                        f"entry in {lexicon.metadata.display_name}; the token remains unmatched."
                    )
                else:
                    entry = mapped_entry
                    method = MatchMethod.USER_MAPPING
                    reason = append_lexicon_eligibility_note(
                        f"Matched only through approved review mapping "
                        f"{mapping_rule.decision_revision_id}: "
                        f"{token.surface_form} → {mapped_entry.source_term}.",
                        token,
                    )
        if method == MatchMethod.NOT_ELIGIBLE:
            selection = MatchSelection.NOT_ELIGIBLE
            included = False
        elif token.token_id in phrase_by_token and phrase_policy == PhrasePolicy.PHRASE_PREFERRED:
            selection = MatchSelection.SUPPRESSED_COMPONENT
            included = False
            reason = (
                "Component retained for audit but suppressed because the selected "
                "phrase supplies the default summary observation. " + reason
            )
        elif entry is None:
            selection = MatchSelection.UNMATCHED
            included = False
        else:
            selection = MatchSelection.INCLUDED
            included = True
        record = _record(
            match_id=f"{lexicon.metadata.lexicon_id}:m{len(records) + 1}",
            lexicon_id=lexicon.metadata.lexicon_id,
            tokens=(token,),
            method=method,
            selection=selection,
            entry=entry,
            included=included,
            stopword_policy=stopword_policy,
            suppressed_by=(
                phrase_by_token.get(token.token_id)
                if selection == MatchSelection.SUPPRESSED_COMPONENT
                else None
            ),
            reason=reason,
        )
        if record.included:
            exclusion_revisions = _review_exclusion_revisions(
                review_rules,
                (token,),
            )
            if exclusion_revisions:
                record = replace(
                    record,
                    selection=MatchSelection.EXCLUDED_REVIEW,
                    included=False,
                    included_in_stopword_view=False,
                    reason=(
                        "Excluded by active review decision revision(s): "
                        + ", ".join(exclusion_revisions)
                        + ". The candidate match remains in the audit trail."
                    ),
                )
        records.append(record)
    return tuple(records), tuple(dict.fromkeys(review_warnings))


def _coverage(
    tokens: tuple[TokenRecord, ...], matches: tuple[AffectMatchRecord, ...]
) -> CoverageStatistics:
    lexical = tuple(token for token in tokens if is_lexicon_eligible(token))
    lexical_by_id = {token.token_id: token for token in lexical}
    included = tuple(match for match in matches if match.included)
    excluded = tuple(
        match
        for match in matches
        if match.selection == MatchSelection.EXCLUDED_REVIEW
    )
    matched_evidence = (*included, *excluded)
    matched_token_ids = {
        token_id
        for match in matched_evidence
        for token_id in match.token_ids
        if token_id in lexical_by_id
    }
    lexical_types = {token.normalized_form for token in lexical}
    matched_types = {lexical_by_id[token_id].normalized_form for token_id in matched_token_ids}
    exact = sum(match.method == MatchMethod.EXACT for match in matched_evidence)
    possessive = sum(match.method == MatchMethod.POSSESSIVE for match in matched_evidence)
    lemma = sum(match.method == MatchMethod.LEMMA for match in matched_evidence)
    phrases = sum(match.method == MatchMethod.PHRASE for match in matched_evidence)
    mappings = sum(match.method == MatchMethod.USER_MAPPING for match in matched_evidence)
    excluded_token_ids = {
        token_id
        for match in excluded
        for token_id in match.token_ids
        if token_id in lexical_by_id
    }
    return CoverageStatistics(
        total_tokens=len(tokens),
        total_lexical_tokens=len(lexical),
        total_unique_types=len(lexical_types),
        matched_token_count=len(matched_token_ids),
        unmatched_token_count=len(lexical) - len(matched_token_ids),
        matched_type_count=len(matched_types),
        unmatched_type_count=len(lexical_types) - len(matched_types),
        token_coverage=_safe_rate(len(matched_token_ids), len(tokens)),
        lexical_token_coverage=_safe_rate(len(matched_token_ids), len(lexical)),
        type_coverage=_safe_rate(len(matched_types), len(lexical_types)),
        exact_match_count=exact,
        exact_match_coverage=_safe_rate(exact, len(lexical)),
        possessive_match_count=possessive,
        possessive_match_coverage=_safe_rate(possessive, len(lexical)),
        lemma_fallback_count=lemma,
        lemma_fallback_coverage=_safe_rate(lemma, len(lexical)),
        phrase_match_count=phrases,
        phrase_match_coverage=_safe_rate(phrases, len(lexical)),
        approved_mapping_count=mappings,
        approved_mapping_coverage=_safe_rate(mappings, len(lexical)),
        compound_derived_count=0,
        compound_derived_coverage=_safe_rate(0, len(lexical)),
        excluded_token_count=len(excluded_token_ids),
        excluded_token_rate=_safe_rate(len(excluded_token_ids), len(lexical)),
    )


def stopword_eligible_token_ids(
    tokens: tuple[TokenRecord, ...],
    matches: tuple[AffectMatchRecord, ...],
    policy: StopwordPolicy,
) -> frozenset[str]:
    """Return the exact token denominator for the recorded secondary view."""

    lexical = tuple(token for token in tokens if is_lexicon_eligible(token))
    lexical_by_id = {token.token_id: token for token in lexical}
    retained_phrase_token_ids = {
        token_id
        for match in matches
        if match.included
        and match.method == MatchMethod.PHRASE
        and match.included_in_stopword_view
        for token_id in match.token_ids
    }
    eligible_ids = {
        token.token_id
        for token in lexical
        if (
            not classify_match_stopword(
                (token,),
                policy,
                is_published_phrase=False,
            )[1]
            or token.token_id in retained_phrase_token_ids
        )
    }
    review_excluded_ids = {
        token_id
        for match in matches
        if match.selection == MatchSelection.EXCLUDED_REVIEW
        for token_id in match.token_ids
        if token_id in lexical_by_id
    }
    eligible_ids.difference_update(review_excluded_ids)
    return frozenset(eligible_ids)


def _stopword_coverage(
    tokens: tuple[TokenRecord, ...],
    matches: tuple[AffectMatchRecord, ...],
    policy: StopwordPolicy,
) -> StopwordCoverageStatistics:
    """Calculate content-focused coverage without penalizing intentional removals."""

    lexical = tuple(token for token in tokens if is_lexicon_eligible(token))
    lexical_by_id = {token.token_id: token for token in lexical}
    eligible_ids = stopword_eligible_token_ids(tokens, matches, policy)
    filtered_matches = tuple(
        match for match in matches if match.included_in_stopword_view
    )
    matched_ids = {
        token_id
        for match in filtered_matches
        for token_id in match.token_ids
        if token_id in eligible_ids
    }
    eligible_types = {
        lexical_by_id[token_id].normalized_form for token_id in eligible_ids
    }
    matched_types = {
        lexical_by_id[token_id].normalized_form for token_id in matched_ids
    }
    excluded_matches = tuple(
        match
        for match in matches
        if match.included and not match.included_in_stopword_view
    )
    excluded_token_ids = {
        token_id
        for match in excluded_matches
        for token_id in match.token_ids
        if token_id in lexical_by_id
    }
    excluded_types = {
        match.matched_lookup_form
        for match in excluded_matches
        if match.matched_lookup_form is not None
    }
    return StopwordCoverageStatistics(
        eligible_token_count=len(eligible_ids),
        eligible_unique_type_count=len(eligible_types),
        matched_token_count=len(matched_ids),
        unmatched_token_count=len(eligible_ids - matched_ids),
        matched_type_count=len(matched_types),
        unmatched_type_count=len(eligible_types - matched_types),
        lexical_token_coverage=_safe_rate(len(matched_ids), len(eligible_ids)),
        type_coverage=_safe_rate(len(matched_types), len(eligible_types)),
        excluded_matched_observation_count=len(excluded_matches),
        excluded_matched_token_count=len(excluded_token_ids),
        excluded_matched_type_count=len(excluded_types),
    )


def _vad_summary(
    matches: tuple[AffectMatchRecord, ...], minimum_match_requirement: int
) -> VadSummary:
    included = tuple(
        match for match in matches if match.included and match.original_scores is not None
    )
    unique: dict[str, AffectMatchRecord] = {}
    for match in included:
        if match.matched_lookup_form is not None:
            unique.setdefault(match.matched_lookup_form, match)
    filtered = tuple(
        match
        for match in included
        if match.included_in_stopword_view
    )
    filtered_unique: dict[str, AffectMatchRecord] = {}
    for match in filtered:
        if match.matched_lookup_form is not None:
            filtered_unique.setdefault(match.matched_lookup_form, match)
    return VadSummary(
        token_weighted_original=weighted_vad_statistics(
            match.original_scores for match in included if match.original_scores is not None
        ),
        type_weighted_original=weighted_vad_statistics(
            match.original_scores for match in unique.values() if match.original_scores is not None
        ),
        token_weighted_normalized=weighted_vad_statistics(
            match.normalized_scores for match in included if match.normalized_scores is not None
        ),
        type_weighted_normalized=weighted_vad_statistics(
            match.normalized_scores for match in unique.values() if match.normalized_scores is not None
        ),
        minimum_match_requirement=minimum_match_requirement,
        is_sparse=len(included) < minimum_match_requirement,
        stopword_excluded_token_weighted_original=weighted_vad_statistics(
            match.original_scores
            for match in filtered
            if match.original_scores is not None
        ),
        stopword_excluded_type_weighted_original=weighted_vad_statistics(
            match.original_scores
            for match in filtered_unique.values()
            if match.original_scores is not None
        ),
        stopword_excluded_token_weighted_normalized=weighted_vad_statistics(
            match.normalized_scores
            for match in filtered
            if match.normalized_scores is not None
        ),
        stopword_excluded_type_weighted_normalized=weighted_vad_statistics(
            match.normalized_scores
            for match in filtered_unique.values()
            if match.normalized_scores is not None
        ),
        stopword_excluded_is_sparse=len(filtered) < minimum_match_requirement,
    )


def _distribution(records: Iterable[AffectMatchRecord], field: str) -> tuple[tuple[int, int], ...]:
    counts = Counter(getattr(record, field) for record in records)
    return tuple(sorted(counts.items()))


def _category_statistics(
    tokens: tuple[TokenRecord, ...],
    matches: tuple[AffectMatchRecord, ...],
    categories: tuple[str, ...],
) -> tuple[EmotionCategoryStatistics, ...]:
    lexical = tuple(token for token in tokens if is_lexicon_eligible(token))
    lexical_types = {token.normalized_form for token in lexical}
    included = tuple(match for match in matches if match.included and match.associations)
    emotion_token_ids = {token_id for match in included for token_id in match.token_ids}
    summaries = []
    for category in categories:
        records = tuple(match for match in included if category in match.associations)
        terms = Counter(match.matched_lookup_form for match in records if match.matched_lookup_form)
        summaries.append(
            EmotionCategoryStatistics(
                category=category,
                associated_token_count=len(records),
                associated_unique_type_count=len(terms),
                proportion_of_lexical_tokens=_safe_rate(len(records), len(lexical)),
                proportion_of_matched_emotion_bearing_tokens=_safe_rate(
                    len(records), len(emotion_token_ids)
                ),
                proportion_of_unique_lexical_types=_safe_rate(len(terms), len(lexical_types)),
                line_distribution=_distribution(records, "line_number"),
                stanza_distribution=_distribution(records, "stanza_number"),
                top_contributing_terms=tuple(
                    TermContribution(term=term, token_count=count)
                    for term, count in sorted(terms.items(), key=lambda item: (-item[1], item[0]))[:10]
                ),
            )
        )
    return tuple(summaries)


def _intensity_statistics(
    tokens: tuple[TokenRecord, ...],
    matches: tuple[AffectMatchRecord, ...],
    categories: tuple[str, ...],
) -> tuple[EmotionIntensityStatistics, ...]:
    lexical = tuple(token for token in tokens if is_lexicon_eligible(token))
    included = tuple(match for match in matches if match.included and match.intensities)
    intensity_token_ids = {token_id for match in included for token_id in match.token_ids}
    summaries = []
    for category in categories:
        records = tuple(match for match in included if category in match.intensity_map())
        token_values = [match.intensity_map()[category] for match in records]
        type_values: dict[str, float] = {}
        term_counts: Counter[str] = Counter()
        for match in records:
            assert match.matched_lookup_form is not None
            value = match.intensity_map()[category]
            type_values.setdefault(match.matched_lookup_form, value)
            term_counts[match.matched_lookup_form] += 1
        summaries.append(
            EmotionIntensityStatistics(
                category=category,
                matched_word_emotion_pairs=len(type_values),
                matched_token_occurrences=len(records),
                prevalence_among_lexical_tokens=_safe_rate(len(records), len(lexical)),
                prevalence_among_emotion_intensity_matches=_safe_rate(
                    len(records), len(intensity_token_ids)
                ),
                token_weighted=descriptive_statistics(token_values),
                type_weighted=descriptive_statistics(type_values.values()),
                line_distribution=_distribution(records, "line_number"),
                stanza_distribution=_distribution(records, "stanza_number"),
                top_contributing_terms=tuple(
                    TermContribution(
                        term=term,
                        token_count=count,
                        source_value=type_values[term],
                    )
                    for term, count in sorted(
                        term_counts.items(),
                        key=lambda item: (-(item[1] * type_values[item[0]]), item[0]),
                    )[:10]
                ),
            )
        )
    return tuple(summaries)


def analyze_lexicon(
    document: TextDocument,
    lexicon: SupportedLexicon,
    preprocessor: TextPreprocessor,
    *,
    phrase_policy: PhrasePolicy = PhrasePolicy.PHRASE_PREFERRED,
    scenario_id: str = PHASE2_SCENARIO_ID,
    minimum_match_requirement: int = 3,
    stopword_policy: StopwordPolicy | None = None,
    scenario_version_id: str = "",
    review_rules: tuple[ReviewRule, ...] = (),
) -> Phase2AnalysisResult:
    """Run one supplied lexicon independently under an explicit phrase policy."""

    if minimum_match_requirement < 1:
        raise ValueError("minimum_match_requirement must be at least 1")
    if not lexicon.validation.is_valid:
        raise ValueError("A lexicon with validation errors cannot be analyzed.")
    active_stopword_policy = stopword_policy or build_stopword_policy()
    tokens = preprocessor.process(document)
    lexicon_rules = tuple(
        rule for rule in review_rules if rule.lexicon_id == lexicon.metadata.lexicon_id
    )
    matches, review_warnings = _build_matches(
        tokens,
        lexicon,
        phrase_policy,
        active_stopword_policy,
        lexicon_rules,
    )
    coverage = _coverage(tokens, matches)
    stopword_coverage = _stopword_coverage(tokens, matches, active_stopword_policy)
    vad_summary = None
    categories = ()
    intensities = ()
    if isinstance(lexicon, VadLexicon):
        vad_summary = _vad_summary(matches, minimum_match_requirement)
    elif isinstance(lexicon, EmotionAssociationLexicon):
        categories = _category_statistics(tokens, matches, lexicon.metadata.dimensions)
    else:
        intensities = _intensity_statistics(tokens, matches, lexicon.metadata.dimensions)

    warnings = list(lexicon.validation.warnings)
    warnings.extend(review_warnings)
    flag_count = sum(rule.action == ReviewAction.FLAG for rule in lexicon_rules)
    if flag_count:
        warnings.append(
            f"This scenario contains {flag_count} non-scoring review flag(s) for "
            f"{lexicon.metadata.display_name}; flags do not change aggregates."
        )
    if not coverage.matched_token_count:
        warnings.append(
            "No lexical tokens matched this lexicon; missing aggregates remain missing, not zero."
        )
    if vad_summary is not None and vad_summary.is_sparse:
        warnings.append(
            f"Only {vad_summary.token_weighted_original.valence.count} VAD match "
            f"observation(s) were included; the configured minimum is "
            f"{minimum_match_requirement}. Treat the aggregate as sparse."
        )
    if (
        vad_summary is not None
        and vad_summary.stopword_excluded_is_sparse
        and stopword_coverage.excluded_matched_observation_count
    ):
        filtered_count = (
            vad_summary.stopword_excluded_token_weighted_original.valence.count
            if vad_summary.stopword_excluded_token_weighted_original is not None
            else 0
        )
        warnings.append(
            f"The stopword-excluded view contains {filtered_count} VAD match "
            f"observation(s), below the configured minimum of "
            f"{minimum_match_requirement}; treat that alternative view as sparse."
        )
    if phrase_policy == PhrasePolicy.PHRASE_AND_COMPONENT:
        warnings.append(
            "Exploratory phrase-and-component mode intentionally double-counts "
            "selected phrase spans and independently matched components in summaries."
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
            phrase_policy.value,
            str(minimum_match_requirement),
            active_stopword_policy.mode.value,
            active_stopword_policy.active_list_sha256,
            scenario_version_id,
            repr(tuple(asdict(rule) for rule in lexicon_rules)),
        )
    )
    return Phase2AnalysisResult(
        analysis_id=hashlib.sha256(signature.encode("utf-8")).hexdigest(),
        scenario_id=scenario_id,
        phrase_policy=phrase_policy,
        document=document,
        lexicon_metadata=lexicon.metadata,
        lexicon_validation=lexicon.validation,
        preprocessing=preprocessor.metadata,
        tokens=tokens,
        matches=matches,
        coverage=coverage,
        vad_summary=vad_summary,
        category_statistics=categories,
        intensity_statistics=intensities,
        warnings=tuple(warnings),
        stopword_policy=active_stopword_policy,
        stopword_coverage=stopword_coverage,
        scenario_version_id=scenario_version_id,
        review_rules=lexicon_rules,
    )


def _comparison_metrics(result: Phase2AnalysisResult) -> list[ComparisonMetric]:
    metadata = result.lexicon_metadata
    common = {
        "lexicon_id": metadata.lexicon_id,
        "display_name": metadata.display_name,
        "family": metadata.family,
        "version": metadata.version,
        "value_kind": metadata.value_kind,
    }
    metrics = [
        ComparisonMetric(
            **common,
            metric="matched_token_count",
            weighting="token",
            scale="count",
            denominator="all lexical tokens",
            value=result.coverage.matched_token_count,
            analysis_view="all_matched",
        ),
        ComparisonMetric(
            **common,
            metric="lexical_token_coverage",
            weighting="token",
            scale="proportion",
            denominator="all lexical tokens",
            value=result.coverage.lexical_token_coverage,
            analysis_view="all_matched",
        ),
    ]
    if result.stopword_coverage is not None:
        metrics.extend(
            (
                ComparisonMetric(
                    **common,
                    metric="matched_token_count",
                    weighting="token",
                    scale="count",
                    denominator="eligible non-stopword, non-review-excluded lexical tokens",
                    value=result.stopword_coverage.matched_token_count,
                    analysis_view="stopwords_excluded",
                ),
                ComparisonMetric(
                    **common,
                    metric="lexical_token_coverage",
                    weighting="token",
                    scale="proportion",
                    denominator="eligible non-stopword, non-review-excluded lexical tokens",
                    value=result.stopword_coverage.lexical_token_coverage,
                    analysis_view="stopwords_excluded",
                ),
            )
        )
    if result.vad_summary is not None:
        summary = result.vad_summary
        vad_groups = (
            (
                "all_matched",
                "token",
                summary.token_weighted_normalized,
                "all included matched VAD observations",
            ),
            (
                "all_matched",
                "type",
                summary.type_weighted_normalized,
                "distinct included matched VAD entries",
            ),
            (
                "stopwords_excluded",
                "token",
                summary.stopword_excluded_token_weighted_normalized,
                "included matched VAD observations after stopword exclusion",
            ),
            (
                "stopwords_excluded",
                "type",
                summary.stopword_excluded_type_weighted_normalized,
                "distinct matched VAD entries after stopword exclusion",
            ),
        )
        for analysis_view, weighting, group, denominator in vad_groups:
            if group is None:
                continue
            for dimension, stats in group.by_dimension().items():
                metrics.append(
                    ComparisonMetric(
                        **common,
                        metric=f"mean_normative_{dimension}",
                        weighting=weighting,
                        scale="normalized_0_1",
                        denominator=denominator,
                        value=stats.mean,
                        analysis_view=analysis_view,
                    )
                )
    for category in result.category_statistics:
        metrics.append(
            ComparisonMetric(
                **common,
                metric=f"{category.category}_association_rate",
                weighting="token",
                scale="proportion",
                denominator="all lexical tokens",
                value=category.proportion_of_lexical_tokens,
            )
        )
    for category in result.intensity_statistics:
        metrics.extend(
            (
                ComparisonMetric(
                    **common,
                    metric=f"{category.category}_intensity_prevalence",
                    weighting="token",
                    scale="proportion",
                    denominator="all lexical tokens",
                    value=category.prevalence_among_lexical_tokens,
                ),
                ComparisonMetric(
                    **common,
                    metric=f"mean_{category.category}_intensity",
                    weighting="token",
                    scale="source_0_1",
                    denominator=f"matched {category.category} entries only",
                    value=category.token_weighted.mean,
                ),
            )
        )
    return metrics


def compare_lexicons(results: Iterable[Phase2AnalysisResult]) -> CrossLexiconComparison:
    """Create side-by-side metrics while deliberately producing no consensus score."""

    result_tuple = tuple(results)
    if not result_tuple:
        raise ValueError("At least one result is required for comparison.")
    first = result_tuple[0]
    for result in result_tuple[1:]:
        if result.document.text_version_id != first.document.text_version_id:
            raise ValueError("Cross-lexicon results must analyze the same text version.")
        if result.scenario_id != first.scenario_id:
            raise ValueError("Cross-lexicon results must use the same scenario.")
        if result.scenario_version_id != first.scenario_version_id:
            raise ValueError(
                "Cross-lexicon results must use the same scenario version."
            )
        if result.phrase_policy != first.phrase_policy:
            raise ValueError("Cross-lexicon results must use the same phrase policy.")
        if result.stopword_policy != first.stopword_policy:
            raise ValueError("Cross-lexicon results must use the same stopword policy.")
    lexicon_ids = tuple(result.lexicon_metadata.lexicon_id for result in result_tuple)
    signature = "|".join(result.analysis_id for result in result_tuple)
    metrics = tuple(metric for result in result_tuple for metric in _comparison_metrics(result))
    return CrossLexiconComparison(
        comparison_id=hashlib.sha256(signature.encode("utf-8")).hexdigest(),
        text_version_id=first.document.text_version_id,
        scenario_id=first.scenario_id,
        phrase_policy=first.phrase_policy,
        lexicon_ids=lexicon_ids,
        metrics=metrics,
    )
