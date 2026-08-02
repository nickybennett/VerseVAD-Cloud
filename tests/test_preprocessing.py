from __future__ import annotations

import hashlib

from versevad.preprocessing import create_text_document


def test_original_text_checksum_and_structure_are_preserved(preprocessor) -> None:
    original = "Mountains cried.\n\nBroken stone.\n"
    document = create_text_document("structure", "Structure fixture", original)

    tokens = preprocessor.process(document)
    lexical = [token for token in tokens if token.is_lexical]

    assert document.original_text == original
    assert document.text_sha256 == hashlib.sha256(original.encode("utf-8")).hexdigest()
    assert [(token.surface_form, token.line_number, token.stanza_number) for token in lexical] == [
        ("Mountains", 1, 1),
        ("cried", 1, 1),
        ("Broken", 3, 2),
        ("stone", 3, 2),
    ]


def test_pinned_pipeline_provides_pos_sensitive_lemmas(preprocessor) -> None:
    document = create_text_document(
        "lemmas", "Lemma fixture", "Mountains cried. Broken arms rested."
    )
    tokens = preprocessor.process(document)
    by_surface = {token.surface_form: token for token in tokens}

    assert by_surface["Mountains"].normalized_lemma == "mountain"
    assert by_surface["Mountains"].part_of_speech in {"NOUN", "PROPN"}
    assert by_surface["cried"].normalized_lemma == "cry"
    assert by_surface["cried"].part_of_speech == "VERB"
    assert by_surface["rested"].normalized_lemma == "rest"


def test_possessive_noun_is_one_auditable_token(preprocessor) -> None:
    document = create_text_document("possessive", "Possessive fixture", "Death’s shadow.")
    lexical = [token for token in preprocessor.process(document) if token.is_lexical]

    assert lexical[0].surface_form == "Death’s"
    assert lexical[0].normalized_lemma == "death"
    assert lexical[0].part_of_speech == "NOUN"


def test_same_surface_form_retains_different_pos_and_lemma_analyses(preprocessor) -> None:
    document = create_text_document("ambiguous", "Ambiguous form", "I saw a saw.")

    saw_tokens = [
        token for token in preprocessor.process(document) if token.normalized_form == "saw"
    ]

    assert len(saw_tokens) == 2
    assert (saw_tokens[0].part_of_speech, saw_tokens[0].normalized_lemma) == (
        "VERB",
        "see",
    )
    assert (saw_tokens[1].part_of_speech, saw_tokens[1].normalized_lemma) == (
        "NOUN",
        "saw",
    )


def test_punctuation_joined_words_are_separate_without_changing_source(
    preprocessor,
) -> None:
    original = "Eagerly I wished the morrow;—vainly I had sought to borrow."
    document = create_text_document(
        "joined-punctuation",
        "Joined punctuation fixture",
        original,
    )

    poem = preprocessor.process_document(document)
    surfaces = [token.surface_form for token in poem.tokens]
    start = surfaces.index("morrow")
    joined = poem.tokens[start : start + 4]

    assert [token.surface_form for token in joined] == [
        "morrow",
        ";",
        "—",
        "vainly",
    ]
    assert [token.is_punctuation for token in joined] == [False, True, True, False]
    assert joined[0].normalized_form == "morrow"
    assert joined[0].part_of_speech == "NOUN"
    assert joined[3].normalized_form == "vainly"
    assert joined[3].part_of_speech == "ADV"
    assert [
        original[token.character_start : token.character_end]
        for token in joined
    ] == ["morrow", ";", "—", "vainly"]
    assert poem.source.original_text == original
    assert poem.source.text_sha256 == document.text_sha256
    assert poem.preprocessing.recipe_id == "versevad-default-preprocessing-v2"


def test_joined_punctuation_rule_does_not_split_apostrophes_or_abbreviations(
    preprocessor,
) -> None:
    document = create_text_document(
        "joined-punctuation-boundary",
        "Joined punctuation boundary fixture",
        "I've heard o’er U.S.A. references.",
    )
    surfaces = [token.surface_form for token in preprocessor.process(document)]

    assert surfaces[:2] == ["I", "'ve"]
    assert "o’er" in surfaces
    assert "U.S.A." in surfaces


def test_line_edge_unicode_whitespace_is_analytically_inert(preprocessor) -> None:
    clean = "Stone turns.\n\nNight falls.\n"
    indented = (
        "\t\u00a0\u2003Stone turns. \t\u00a0\u2009\n"
        " \t\u00a0\u2003 \n"
        "\u00a0\tNight falls.\u2003\u00a0\n"
    )

    clean_poem = preprocessor.process_document(
        create_text_document("clean-spacing", "Clean spacing", clean)
    )
    indented_poem = preprocessor.process_document(
        create_text_document("mixed-spacing", "Mixed spacing", indented)
    )

    def token_signature(poem):
        return [
            (
                token.surface_form,
                token.normalized_form,
                token.normalized_lemma,
                token.part_of_speech,
                token.is_punctuation,
                token.is_stopword,
                token.line_number,
                token.stanza_number,
            )
            for token in poem.tokens
        ]

    assert token_signature(indented_poem) == token_signature(clean_poem)
    assert [line.is_blank for line in indented_poem.lines] == [False, True, False]
    assert [token.stanza_number for token in indented_poem.tokens if token.is_lexical] == [
        1,
        1,
        2,
        2,
    ]
    assert indented_poem.lines[0].indentation == "\t\u00a0\u2003"
    assert indented_poem.lines[1].indentation == " \t\u00a0\u2003 "
    assert indented_poem.lines[2].indentation == "\u00a0\t"
    assert indented_poem.source.original_text == indented
    assert indented_poem.source.text_sha256 != clean_poem.source.text_sha256
