"""Canonical lexical scope and aggregation profile contracts.

These definitions are deliberately independent of Streamlit and of any one
lexical resource.  A completed analysis retains evidence once; report and
export code uses these contracts to select compatible perspectives without
repeating linguistic processing or resource lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import product
from typing import Iterable, Mapping, Sequence

from versevad.lexical_eligibility import is_lexicon_eligible
from versevad.models import TokenRecord


PROFILE_SCHEMA_VERSION = "2.0"
CONTENT_WORD_DEFINITION_ID = "versevad-content-pos-v1"
CONTENT_WORD_POS_TAGS = frozenset({"NOUN", "VERB", "ADJ", "ADV"})
PHRASE_SCOPE_POLICY_ID = "retain-complete-matched-expression-v1"


class LexicalScope(StrEnum):
    """The only configurable lexical eligibility scopes in VerseVAD."""

    ALL_LEXICAL = "ALL_LEXICAL"
    STOPWORD_EXCLUDED = "STOPWORD_EXCLUDED"
    CONTENT_WORDS = "CONTENT_WORDS"

    @property
    def label(self) -> str:
        return {
            self.ALL_LEXICAL: "All lexical tokens",
            self.STOPWORD_EXCLUDED: "Stopword-excluded",
            self.CONTENT_WORDS: "Content words only",
        }[self]


class AggregationWeighting(StrEnum):
    """The only configurable within-text lexical aggregation weightings."""

    TOKEN = "TOKEN"
    TYPE = "TYPE"

    @property
    def label(self) -> str:
        return {
            self.TOKEN: "Token-weighted",
            self.TYPE: "Type-weighted",
        }[self]


SCOPE_ORDER = (
    LexicalScope.ALL_LEXICAL,
    LexicalScope.STOPWORD_EXCLUDED,
    LexicalScope.CONTENT_WORDS,
)
WEIGHTING_ORDER = (
    AggregationWeighting.TOKEN,
    AggregationWeighting.TYPE,
)
DEFAULT_SCOPES = (LexicalScope.STOPWORD_EXCLUDED,)
DEFAULT_WEIGHTINGS = (AggregationWeighting.TOKEN,)
ALL_COMPATIBLE_PROFILES = tuple(product(SCOPE_ORDER, WEIGHTING_ORDER))


@dataclass(frozen=True, order=True)
class AnalysisProfile:
    scope: LexicalScope
    weighting: AggregationWeighting

    @property
    def id(self) -> str:
        return f"{self.scope.value}__{self.weighting.value}"

    @property
    def label(self) -> str:
        return f"{self.scope.label} · {self.weighting.label}"


@dataclass(frozen=True)
class ProfileSelection:
    """One non-empty report/display selection."""

    scopes: tuple[LexicalScope, ...] = DEFAULT_SCOPES
    weightings: tuple[AggregationWeighting, ...] = DEFAULT_WEIGHTINGS

    def __post_init__(self) -> None:
        scopes = canonical_scopes(self.scopes)
        weightings = canonical_weightings(self.weightings)
        if not scopes:
            raise ValueError("At least one lexical scope must remain selected.")
        if not weightings:
            raise ValueError("At least one aggregation weighting must remain selected.")
        object.__setattr__(self, "scopes", scopes)
        object.__setattr__(self, "weightings", weightings)

    @property
    def profiles(self) -> tuple[AnalysisProfile, ...]:
        return tuple(
            AnalysisProfile(scope, weighting)
            for scope in self.scopes
            for weighting in self.weightings
        )


@dataclass(frozen=True)
class ProfileCoverage:
    """Explicit scope-relative denominators and exclusion counts."""

    scope: LexicalScope
    eligible_token_count: int
    eligible_type_count: int
    matched_token_count: int
    unmatched_token_count: int
    matched_type_count: int
    unmatched_type_count: int
    excluded_stopword_count: int
    excluded_non_content_count: int
    phrase_match_count: int
    token_coverage: float | None
    type_coverage: float | None
    type_identity_rule: str


def canonical_scopes(values: Iterable[LexicalScope | str]) -> tuple[LexicalScope, ...]:
    supplied = {coerce_scope(value) for value in values}
    return tuple(scope for scope in SCOPE_ORDER if scope in supplied)


def canonical_weightings(
    values: Iterable[AggregationWeighting | str],
) -> tuple[AggregationWeighting, ...]:
    supplied = {coerce_weighting(value) for value in values}
    return tuple(weighting for weighting in WEIGHTING_ORDER if weighting in supplied)


def coerce_scope(value: LexicalScope | str) -> LexicalScope:
    if isinstance(value, LexicalScope):
        return value
    normalized = str(value).strip().replace("-", "_").replace(" ", "_").upper()
    aliases = {
        "ALL_MATCHED": LexicalScope.ALL_LEXICAL,
        "ALL_MATCHED_TOKENS": LexicalScope.ALL_LEXICAL,
        "ALL_TOKENS": LexicalScope.ALL_LEXICAL,
        "STOPWORDS_EXCLUDED": LexicalScope.STOPWORD_EXCLUDED,
        "CONTENT_WORDS_ONLY": LexicalScope.CONTENT_WORDS,
    }
    if normalized in aliases:
        return aliases[normalized]
    return LexicalScope(normalized)


def coerce_weighting(value: AggregationWeighting | str) -> AggregationWeighting:
    if isinstance(value, AggregationWeighting):
        return value
    normalized = str(value).strip().replace("-", "_").replace(" ", "_").upper()
    aliases = {
        "TOKEN_WEIGHTED": AggregationWeighting.TOKEN,
        "TYPE_WEIGHTED": AggregationWeighting.TYPE,
    }
    if normalized in aliases:
        return aliases[normalized]
    return AggregationWeighting(normalized)


def token_is_in_scope(
    token: TokenRecord,
    scope: LexicalScope,
    *,
    active_stopwords: Iterable[str] = (),
) -> bool:
    """Return eligibility under one canonical scope.

    Alphabetically spelled number words remain lexicon eligible under the
    shared lexical-eligibility policy.  A stopword scope uses only the recorded
    list resource, never POS as a proxy.
    """

    if not is_lexicon_eligible(token):
        return False
    if scope is LexicalScope.ALL_LEXICAL:
        return True
    if scope is LexicalScope.CONTENT_WORDS:
        return token.part_of_speech in CONTENT_WORD_POS_TAGS
    stopwords = frozenset(str(word).casefold() for word in active_stopwords)
    return token.normalized_form.casefold() not in stopwords


def scoped_token_ids(
    tokens: Sequence[TokenRecord],
    scope: LexicalScope,
    *,
    active_stopwords: Iterable[str] = (),
) -> frozenset[str]:
    return frozenset(
        token.token_id
        for token in tokens
        if token_is_in_scope(token, scope, active_stopwords=active_stopwords)
    )


def phrase_is_in_scope(
    token_ids: Iterable[str],
    base_eligible_token_ids: Iterable[str],
) -> bool:
    """Keep a complete expression when any lexical component is in scope."""

    span = frozenset(token_ids)
    return bool(span and span.intersection(base_eligible_token_ids))


def phrase_adjusted_eligible_ids(
    base_eligible_token_ids: Iterable[str],
    matched_phrase_token_ids: Iterable[Iterable[str]],
) -> frozenset[str]:
    """Apply the non-fragmentation rule to metric-specific eligibility."""

    eligible = set(base_eligible_token_ids)
    for token_ids in matched_phrase_token_ids:
        span = tuple(token_ids)
        if phrase_is_in_scope(span, eligible):
            eligible.update(span)
    return frozenset(eligible)


def type_identity_for_token(token: TokenRecord, rule: str) -> str:
    """Return a stable identity for documented generic type rules."""

    if rule == "lemma":
        return token.normalized_lemma or token.normalized_form
    if rule == "pos_aware_lemma":
        lemma = token.normalized_lemma or token.normalized_form
        return f"{token.part_of_speech}:{lemma}"
    return token.normalized_form


def scope_definitions() -> Mapping[str, str]:
    return {
        LexicalScope.ALL_LEXICAL.value: (
            "All eligible lexical word tokens, including stopwords and function words; "
            "punctuation-only and nonlexical artifacts are excluded."
        ),
        LexicalScope.STOPWORD_EXCLUDED.value: (
            "Eligible lexical tokens not present in the recorded list-based stopword resource."
        ),
        LexicalScope.CONTENT_WORDS.value: (
            "Eligible lexical tokens contextually tagged NOUN, VERB, ADJ, or ADV."
        ),
    }


__all__ = [
    "ALL_COMPATIBLE_PROFILES",
    "CONTENT_WORD_DEFINITION_ID",
    "CONTENT_WORD_POS_TAGS",
    "DEFAULT_SCOPES",
    "DEFAULT_WEIGHTINGS",
    "PHRASE_SCOPE_POLICY_ID",
    "PROFILE_SCHEMA_VERSION",
    "SCOPE_ORDER",
    "WEIGHTING_ORDER",
    "AggregationWeighting",
    "AnalysisProfile",
    "LexicalScope",
    "ProfileCoverage",
    "ProfileSelection",
    "canonical_scopes",
    "canonical_weightings",
    "coerce_scope",
    "coerce_weighting",
    "phrase_adjusted_eligible_ids",
    "phrase_is_in_scope",
    "scope_definitions",
    "scoped_token_ids",
    "token_is_in_scope",
    "type_identity_for_token",
]
