from versevad.lexical_eligibility import (
    ALPHABETIC_NUMBER_WORD_NOTE,
    LEXICON_ELIGIBILITY_POLICY_ID,
    is_alphabetic_number_word,
    is_lexicon_eligible,
    lexicon_ineligibility_reason,
)
from versevad.preprocessing import create_text_document


def test_alphabetic_number_words_are_lexicon_eligible_without_reclassification(
    preprocessor,
) -> None:
    poem = preprocessor.process_document(
        create_text_document("number-words", "Number words", "one 27 3.5")
    )
    by_surface = {token.surface_form: token for token in poem.tokens}

    one = by_surface["one"]
    assert one.part_of_speech == "NUM"
    assert one.is_numeric is True
    assert one.is_lexical is False
    assert is_alphabetic_number_word(one) is True
    assert is_lexicon_eligible(one) is True

    for surface in ("27", "3.5"):
        literal = by_surface[surface]
        assert literal.is_numeric is True
        assert is_alphabetic_number_word(literal) is False
        assert is_lexicon_eligible(literal) is False
        assert "pure numeric literal" in lexicon_ineligibility_reason(literal)

    assert LEXICON_ELIGIBILITY_POLICY_ID.endswith("-v2")
    assert "alphabetically spelled" in ALPHABETIC_NUMBER_WORD_NOTE
