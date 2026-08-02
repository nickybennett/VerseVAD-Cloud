"""Shared downstream eligibility policy for exact lexical resources.

The preprocessing layer deliberately preserves a model's linguistic judgment
that alphabetically spelled number words (for example, ``one``) are
number-like.  Lexicon matching is a separate decision: written word forms may
participate in lexical lookup, while pure numeric literals remain excluded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from versevad.models import TokenRecord


LEXICON_ELIGIBILITY_POLICY_ID = "versevad-lexicon-eligibility-v2"
ALPHABETIC_NUMBER_WORD_NOTE = (
    "Included for exact lexical lookup because the number-like token is "
    "alphabetically spelled."
)


def contains_alphabetic_character(value: str) -> bool:
    """Return whether a surface form contains at least one Unicode letter."""

    return any(character.isalpha() for character in value)


def is_alphabetic_number_word(token: TokenRecord) -> bool:
    """Identify number-like tokens whose observed form is still a word form."""

    return (
        token.is_numeric
        and not token.is_punctuation
        and contains_alphabetic_character(token.surface_form)
    )


def is_lexicon_eligible(token: TokenRecord) -> bool:
    """Apply the shared broad-scope eligibility rule for lexical lookup."""

    return token.is_lexical or is_alphabetic_number_word(token)


def lexicon_eligibility_note(token: TokenRecord) -> str:
    """Return the audit note required for an admitted number-like word."""

    return ALPHABETIC_NUMBER_WORD_NOTE if is_alphabetic_number_word(token) else ""


def lexicon_eligibility_note_for_tokens(tokens: tuple[TokenRecord, ...]) -> str:
    """Return one audit note when any member used the number-word exception."""

    return (
        ALPHABETIC_NUMBER_WORD_NOTE
        if any(is_alphabetic_number_word(token) for token in tokens)
        else ""
    )


def append_lexicon_eligibility_note(
    reason: str,
    tokens: TokenRecord | tuple[TokenRecord, ...],
) -> str:
    """Append the policy note without changing the module's primary reason."""

    members = tokens if isinstance(tokens, tuple) else (tokens,)
    note = lexicon_eligibility_note_for_tokens(members)
    return f"{reason.rstrip()} {note}" if note else reason


def lexicon_ineligibility_reason(token: TokenRecord) -> str:
    """Explain why a token is outside broad lexical-resource denominators."""

    if token.is_punctuation:
        return "Excluded from the lexicon denominator as punctuation."
    if token.is_numeric:
        return "Excluded from the lexicon denominator as a pure numeric literal."
    return "Excluded from the lexicon denominator as non-lexical text."


__all__ = [
    "ALPHABETIC_NUMBER_WORD_NOTE",
    "LEXICON_ELIGIBILITY_POLICY_ID",
    "append_lexicon_eligibility_note",
    "contains_alphabetic_character",
    "is_alphabetic_number_word",
    "is_lexicon_eligible",
    "lexicon_eligibility_note",
    "lexicon_eligibility_note_for_tokens",
    "lexicon_ineligibility_reason",
]
