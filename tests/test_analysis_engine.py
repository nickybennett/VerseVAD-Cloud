from __future__ import annotations

import math

from versevad.analysis import analyze_vad
from versevad.models import MatchMethod
from versevad.preprocessing import create_text_document
from versevad.validation import (
    PHASE1_DEMO_TEXT,
    phase1_synthetic_lexicon,
    validate_phase1_demo,
)


def test_hand_calculated_phase1_example(preprocessor) -> None:
    document = create_text_document("demo", "Demo", PHASE1_DEMO_TEXT)

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)

    assert validate_phase1_demo(result) == ()
    assert math.isclose(result.coverage.lexical_token_coverage or 0, 7 / 9)
    assert math.isclose(result.coverage.type_coverage or 0, 5 / 7)


def test_exact_entry_precedes_different_lemma_entry(preprocessor) -> None:
    document = create_text_document("exact-first", "Exact first", "Broken.")

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)
    match = next(match for match in result.matches if match.included)

    assert match.method == MatchMethod.EXACT
    assert match.matched_term == "broken"
    assert match.original_scores is not None
    assert match.original_scores.valence == 1.0


def test_pos_sensitive_lemma_fallback_is_recorded(preprocessor) -> None:
    document = create_text_document("lemma", "Lemma", "Mountains cried.")

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)
    included = [match for match in result.matches if match.included]

    assert [match.method for match in included] == [MatchMethod.LEMMA, MatchMethod.LEMMA]
    assert [match.matched_term for match in included] == ["mountain", "cry"]


def test_possessive_match_records_its_provenance(preprocessor) -> None:
    lexicon = phase1_synthetic_lexicon()
    stone = lexicon.entries["stone"]
    extended = type(lexicon).create(
        lexicon.metadata,
        {**lexicon.entries, "death": type(stone)(
            lexicon_id=lexicon.metadata.lexicon_id,
            source_term="death",
            lookup_form="death",
            source_row=99,
            original=stone.original,
            normalized=stone.normalized,
        )},
        lexicon.validation,
    )
    document = create_text_document("possessive", "Possessive", "Death’s shadow.")

    result = analyze_vad(document, extended, preprocessor)
    included = [match for match in result.matches if match.included]

    assert len(included) == 1
    assert included[0].method == MatchMethod.POSSESSIVE
    assert included[0].matched_term == "death"


def test_repetition_changes_token_weighting_but_not_type_weighting(preprocessor) -> None:
    document = create_text_document("repeated", "Repeated", "Bright bright stone.")

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)

    assert math.isclose(
        result.vad_summary.token_weighted_original.valence.mean or 0,
        19 / 3,
    )
    assert result.vad_summary.type_weighted_original.valence.mean == 5.5


def test_no_matches_are_missing_not_neutral(preprocessor) -> None:
    document = create_text_document("none", "No matches", "Arms rest.")

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)

    assert result.coverage.matched_token_count == 0
    assert result.vad_summary.token_weighted_original.valence.count == 0
    assert result.vad_summary.token_weighted_original.valence.mean is None
    assert result.vad_summary.is_sparse
    assert any("missing, not zero" in warning for warning in result.warnings)


def test_one_match_is_calculated_and_flagged_sparse(preprocessor) -> None:
    document = create_text_document("one", "One match", "Stone rests.")

    result = analyze_vad(document, phase1_synthetic_lexicon(), preprocessor)

    stats = result.vad_summary.token_weighted_original.valence
    assert stats.count == 1
    assert stats.mean == 3.0
    assert stats.population_standard_deviation is None
    assert result.vad_summary.is_sparse
