import pytest

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.models import MatchSelection, PhrasePolicy
from versevad.phase2_validation import (
    PHASE2_PHRASE_TEXT,
    phase2_synthetic_emotion_lexicon,
    phase2_synthetic_intensity_lexicon,
    phase2_synthetic_vad_lexicon,
)
from versevad.preprocessing import create_text_document


def _category(result, name):
    return next(item for item in result.category_statistics if item.category == name)


def _intensity(result, name):
    return next(item for item in result.intensity_statistics if item.category == name)


def test_phrase_preferred_is_longest_first_and_suppresses_components(preprocessor) -> None:
    document = create_text_document("p2-phrase", "Phrase fixture", PHASE2_PHRASE_TEXT)
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        preprocessor,
        phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
    )
    selected_phrases = [
        match for match in result.matches if match.included and match.method.value == "exact_phrase"
    ]
    assert [match.matched_term for match in selected_phrases] == ["very dark night"]
    assert any(
        match.matched_term == "dark night"
        and match.selection == MatchSelection.SUPPRESSED_OVERLAP
        for match in result.matches
    )
    suppressed_components = [
        match for match in result.matches if match.selection == MatchSelection.SUPPRESSED_COMPONENT
    ]
    assert len(suppressed_components) == 3
    assert result.coverage.matched_token_count == 7
    assert result.coverage.phrase_match_count == 1
    assert result.vad_summary is not None
    assert result.vad_summary.token_weighted_original.valence.count == 5
    assert result.vad_summary.token_weighted_original.valence.mean == pytest.approx(27 / 5)


def test_number_word_can_complete_phrase_while_numeric_literal_stays_excluded(
    preprocessor,
) -> None:
    document = create_text_document(
        "p2-number-word",
        "Number-word phrase",
        "As of some one gently rapping, 27 times.",
    )
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        preprocessor,
        phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
    )
    token_by_id = {token.token_id: token for token in result.tokens}
    phrase = next(
        match
        for match in result.matches
        if match.included and match.matched_term == "some one"
    )

    assert [token_by_id[token_id].surface_form for token_id in phrase.token_ids] == [
        "some",
        "one",
    ]
    assert "alphabetically spelled" in phrase.reason
    one = next(token for token in result.tokens if token.surface_form == "one")
    assert one.part_of_speech == "NUM"
    assert one.is_numeric is True
    assert one.is_lexical is False
    assert result.coverage.matched_token_count >= 2
    numeric = next(token for token in result.tokens if token.surface_form == "27")
    numeric_audit = next(
        match
        for match in result.matches
        if match.token_ids == (numeric.token_id,)
    )
    assert numeric_audit.selection is MatchSelection.NOT_ELIGIBLE
    assert "pure numeric literal" in numeric_audit.reason


def test_unigram_only_and_exploratory_policies_are_distinct(preprocessor) -> None:
    document = create_text_document("p2-policies", "Policy fixture", PHASE2_PHRASE_TEXT)
    lexicon = phase2_synthetic_vad_lexicon()
    unigram = analyze_lexicon(
        document, lexicon, preprocessor, phrase_policy=PhrasePolicy.UNIGRAM_ONLY
    )
    exploratory = analyze_lexicon(
        document,
        lexicon,
        preprocessor,
        phrase_policy=PhrasePolicy.PHRASE_AND_COMPONENT,
    )
    assert unigram.coverage.matched_token_count == 6
    assert unigram.coverage.phrase_match_count == 0
    assert unigram.vad_summary is not None
    assert unigram.vad_summary.token_weighted_original.valence.count == 6
    assert exploratory.coverage.matched_token_count == 7
    assert exploratory.vad_summary is not None
    assert exploratory.vad_summary.token_weighted_original.valence.count == 7
    assert any("double-counts" in warning for warning in exploratory.warnings)


def test_exact_phrases_do_not_cross_poetic_line_boundaries(preprocessor) -> None:
    document = create_text_document(
        "p2-lines", "Line boundary", "Very dark\nnight glows.\n"
    )
    result = analyze_lexicon(document, phase2_synthetic_vad_lexicon(), preprocessor)
    assert result.coverage.phrase_match_count == 0
    assert result.coverage.matched_token_count == 3


def test_categorical_associations_use_explicit_denominators(preprocessor) -> None:
    document = create_text_document("p2-emotion", "Emotion fixture", "Joy joy fear stone.")
    result = analyze_lexicon(document, phase2_synthetic_emotion_lexicon(), preprocessor)
    joy = _category(result, "joy")
    fear = _category(result, "fear")
    assert result.coverage.total_lexical_tokens == 4
    assert result.coverage.matched_token_count == 4
    assert joy.associated_token_count == 2
    assert joy.associated_unique_type_count == 1
    assert joy.proportion_of_lexical_tokens == pytest.approx(0.5)
    assert joy.proportion_of_matched_emotion_bearing_tokens == pytest.approx(2 / 3)
    assert fear.associated_token_count == 1
    assert _category(result, "positive").associated_token_count == 2
    assert _category(result, "anticipation").associated_token_count == 0
    assert sum(
        item.proportion_of_lexical_tokens or 0 for item in result.category_statistics
    ) > 1.0


def test_intensity_means_exclude_missing_word_emotion_pairs(preprocessor) -> None:
    document = create_text_document(
        "p2-intensity", "Intensity fixture", "Rage rage fear stone."
    )
    result = analyze_lexicon(document, phase2_synthetic_intensity_lexicon(), preprocessor)
    anger = _intensity(result, "anger")
    fear = _intensity(result, "fear")
    assert result.coverage.matched_token_count == 3
    assert anger.matched_word_emotion_pairs == 2
    assert anger.matched_token_occurrences == 3
    assert anger.prevalence_among_lexical_tokens == pytest.approx(3 / 4)
    assert anger.prevalence_among_emotion_intensity_matches == pytest.approx(1.0)
    assert anger.token_weighted.mean == pytest.approx(0.6)
    assert anger.type_weighted.mean == pytest.approx(0.5)
    assert fear.token_weighted.count == 1
    assert fear.token_weighted.mean == pytest.approx(0.6)
    assert _intensity(result, "joy").token_weighted.mean is None


def test_cross_lexicon_comparison_has_no_consensus_score(preprocessor) -> None:
    document = create_text_document(
        "p2-compare", "Comparison fixture", "Fear joy dark night."
    )
    results = (
        analyze_lexicon(document, phase2_synthetic_vad_lexicon(), preprocessor),
        analyze_lexicon(document, phase2_synthetic_emotion_lexicon(), preprocessor),
        analyze_lexicon(document, phase2_synthetic_intensity_lexicon(), preprocessor),
    )
    comparison = compare_lexicons(results)
    assert comparison.consensus_score is None
    assert comparison.lexicon_ids == tuple(
        result.lexicon_metadata.lexicon_id for result in results
    )
    assert any(metric.metric == "mean_normative_valence" for metric in comparison.metrics)
    assert any(metric.metric == "fear_association_rate" for metric in comparison.metrics)
    assert any(metric.metric == "mean_fear_intensity" for metric in comparison.metrics)


def test_comparison_rejects_different_text_versions(preprocessor) -> None:
    lexicon = phase2_synthetic_vad_lexicon()
    first = analyze_lexicon(
        create_text_document("one", "One", "Dark night."), lexicon, preprocessor
    )
    second = analyze_lexicon(
        create_text_document("two", "Two", "Bright night."), lexicon, preprocessor
    )
    with pytest.raises(ValueError, match="same text version"):
        compare_lexicons((first, second))
