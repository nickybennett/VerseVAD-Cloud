from hashlib import sha256

from versevad.dictionary import (
    DATABASE_SHA256,
    DATABASE_SIZE,
    PACKAGED_DATABASE,
    PACKAGED_DATABASE_SHA256,
    ensure_open_english_wordnet_database,
    lookup_open_english_wordnet,
)


def _sha256(path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_packaged_open_english_wordnet_database_is_pinned() -> None:
    assert PACKAGED_DATABASE.is_file()
    assert _sha256(PACKAGED_DATABASE) == PACKAGED_DATABASE_SHA256

    directory = ensure_open_english_wordnet_database()
    database = directory / "wn.db"

    assert database.stat().st_size == DATABASE_SIZE
    assert _sha256(database) == DATABASE_SHA256


def test_dictionary_lookup_returns_source_senses_without_disambiguating() -> None:
    result = lookup_open_english_wordnet(
        "hope",
        lemma="hope",
        processing_pos="NOUN",
    )

    assert result.available is True
    assert result.version == "2025+"
    assert "no contextual sense was selected" in result.status_message
    assert result.senses
    assert result.senses[0].part_of_speech == "n"
    assert any(
        "feeling" in sense.definition.casefold()
        for sense in result.senses
        if sense.matched_lemma == "hope"
    )


def test_dictionary_lookup_prioritizes_model_pos_without_claiming_a_sense() -> None:
    result = lookup_open_english_wordnet(
        "hope",
        lemma="hope",
        processing_pos="VERB",
    )

    assert result.senses[0].part_of_speech == "v"
    assert {sense.part_of_speech for sense in result.senses} >= {"n", "v"}


def test_dictionary_lookup_retains_antonym_and_semantic_relations() -> None:
    result = lookup_open_english_wordnet(
        "good",
        lemma="good",
        processing_pos="ADJ",
    )

    assert any("bad" in sense.antonyms for sense in result.senses)
    assert any(
        sense.broader_terms or sense.narrower_terms
        for sense in result.senses
    )
