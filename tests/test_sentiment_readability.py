import csv
import io
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from versevad.application import AnalysisRequest, run_workspace_analysis
from versevad.core.modules import ModuleInput
from versevad.exports.readability import export_readability_bundle
from versevad.exports.sentiment import export_vader_sentiment_bundle
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.lexical_semantic.readability import (
    ReadabilityConfiguration,
    ReadabilityModule,
    attach_poetic_reading_ease,
    calculate_poetic_reading_ease,
)
from versevad.lexical_semantic.sentiment import VaderSentimentModule
from versevad.preprocessing import create_text_document
from versevad.prosody.pronunciation import PronunciationOverride


def _input(preprocessor, text: str) -> ModuleInput:
    document = create_text_document("new-metrics", "New metrics", text)
    return ModuleInput.from_poem_document(
        preprocessor.process_document(document)
    )


def _rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def test_vader_reports_proportions_compound_sentences_and_cautions(
    preprocessor,
) -> None:
    result = VaderSentimentModule().analyze_detailed(
        _input(preprocessor, "I love this bright day. I hate the cruel night.")
    )

    score = result.document_score
    assert (
        score.positive_proportion
        + score.neutral_proportion
        + score.negative_proportion
    ) == pytest.approx(1, abs=0.002)
    assert -1 <= score.compound_score <= 1
    assert score.threshold_label in {"positive", "neutral", "negative"}
    assert len(result.sentence_scores) == 2
    assert any(
        warning.code == "vader.domain_caution"
        for warning in result.module_result.warnings
    )
    assert result.module_result.provenance.resources == ()

    bundle = export_vader_sentiment_bundle(result, text_title="New metrics")
    assert set(bundle) == {
        "vader_sentiment_summary.csv",
        "vader_sentiment_sentences.csv",
        "vader_sentiment_manifest.csv",
        "vader_sentiment_report.docx",
    }
    assert not any(name.endswith(".json") for name in bundle)
    summary = {row["metric"]: row for row in _rows(bundle["vader_sentiment_summary.csv"])}
    assert summary["compound_score"]["value"]


def test_vader_and_readability_ignore_line_edge_unicode_whitespace(
    preprocessor,
) -> None:
    clean_text = "I love this bright day.\nI hate the cruel night."
    indented_text = (
        "\t\u00a0I love this bright day. \u2003\n"
        "\u2003I hate the cruel night.\u00a0\t"
    )

    clean_vader = VaderSentimentModule().analyze_detailed(
        _input(preprocessor, clean_text)
    )
    indented_vader = VaderSentimentModule().analyze_detailed(
        _input(preprocessor, indented_text)
    )
    clean_readability = ReadabilityModule().analyze_detailed(
        _input(preprocessor, clean_text)
    )
    indented_readability = ReadabilityModule().analyze_detailed(
        _input(preprocessor, indented_text)
    )

    assert indented_vader.document_score == clean_vader.document_score
    assert [item.score for item in indented_vader.sentence_scores] == [
        item.score for item in clean_vader.sentence_scores
    ]
    assert indented_readability.summary == clean_readability.summary


def test_readability_uses_transparent_formulas_and_keeps_contractions_whole(
    preprocessor,
) -> None:
    result = ReadabilityModule().analyze_detailed(
        _input(preprocessor, "You're bright. Stone sings.")
    )
    summary = result.summary

    assert summary.word_count == 4
    assert summary.sentence_count == 2
    assert any(item.surface_form.casefold() == "you're" for item in result.word_audit)
    assert not any(item.surface_form.casefold() == "'re" for item in result.word_audit)
    assert not next(
        item for item in result.word_audit if item.surface_form.casefold() == "you're"
    ).is_vv_pre_content_word
    assert next(
        item for item in result.word_audit if item.surface_form.casefold() == "bright"
    ).is_vv_pre_content_word
    assert summary.flesch_reading_ease is not None
    assert summary.flesch_kincaid_grade is not None
    assert summary.gunning_fog_index is not None
    assert summary.automated_readability_index is not None
    assert summary.coleman_liau_index is not None
    assert summary.smog_index is None
    assert any(
        warning.code == "readability.smog_unavailable"
        for warning in result.module_result.warnings
    )

    bundle = export_readability_bundle(result, text_title="New metrics")
    assert set(bundle) == {
        "readability_summary.csv",
        "readability_word_audit.csv",
        "readability_manifest.csv",
        "readability_report.docx",
    }
    assert not any(name.endswith(".json") for name in bundle)


def test_readability_uses_session_pronunciation_override_before_heuristic(
    preprocessor,
) -> None:
    module_input = _input(preprocessor, "Xyzzy shines.")
    unresolved = ReadabilityModule().analyze_detailed(module_input)
    unresolved_word = next(
        item for item in unresolved.word_audit if item.lookup_form == "xyzzy"
    )
    assert unresolved_word.syllable_method.startswith("orthographic heuristic")

    resolved = ReadabilityModule().analyze_detailed(
        module_input,
        ReadabilityConfiguration(
            pronunciation_overrides=(
                PronunciationOverride(
                    term="xyzzy",
                    phones=("Z", "IH1", "Z", "IY0"),
                    note="Session reading selected for this poem.",
                ),
            )
        ),
    )
    resolved_word = next(
        item for item in resolved.word_audit if item.lookup_form == "xyzzy"
    )
    assert resolved_word.syllable_count == 2
    assert resolved_word.syllable_method == "session pronunciation override"
    assert resolved.summary.heuristic_word_count < unresolved.summary.heuristic_word_count


def test_poetic_reading_ease_uses_positive_weights_and_fixed_anchors() -> None:
    easiest = calculate_poetic_reading_ease(
        mean_zipf=6.5,
        mean_aoa=4.0,
        mean_words_per_line=3.0,
        mean_syllables_per_word=1.0,
    )
    hardest = calculate_poetic_reading_ease(
        mean_zipf=2.5,
        mean_aoa=12.0,
        mean_words_per_line=15.0,
        mean_syllables_per_word=2.5,
    )
    midpoint = calculate_poetic_reading_ease(
        mean_zipf=4.5,
        mean_aoa=8.0,
        mean_words_per_line=9.0,
        mean_syllables_per_word=1.75,
    )

    assert easiest.score == pytest.approx(100.0)
    assert easiest.interpretation_band == "Highly Accessible"
    assert hardest.score == pytest.approx(0.0)
    assert hardest.interpretation_band == "Highly Demanding"
    assert midpoint.score == pytest.approx(50.0)
    assert midpoint.interpretation_band == "Demanding"
    assert [component.weight for component in midpoint.components] == [
        0.30,
        0.25,
        0.30,
        0.15,
    ]
    assert midpoint.profile_id == "vv-pre-content-word-profile-1.0"


def test_poetic_reading_ease_fixed_profile_filters_function_words_and_proper_nouns(
    preprocessor,
) -> None:
    result = ReadabilityModule().analyze_detailed(
        _input(preprocessor, "Stone and brightly.")
    )
    frequency = SimpleNamespace(
        token_audit=(
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="NOUN",
                zipf_value=4.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="CCONJ",
                zipf_value=7.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="ADV",
                zipf_value=2.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=True,
                part_of_speech="PROPN",
                zipf_value=5.0,
            ),
        ),
        module_result=SimpleNamespace(result_id="frequency-source"),
    )
    aoa = SimpleNamespace(
        token_audit=(
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="NOUN",
                mean_age=6.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="CCONJ",
                mean_age=3.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=False,
                part_of_speech="ADV",
                mean_age=10.0,
            ),
            SimpleNamespace(
                is_lexical=True,
                is_proper_noun=True,
                part_of_speech="PROPN",
                mean_age=4.0,
            ),
        ),
        module_result=SimpleNamespace(result_id="aoa-source"),
    )
    lexical_style = SimpleNamespace(
        summary=SimpleNamespace(
            nonblank_line_word_count_statistics=SimpleNamespace(mean=3.0),
            lexical_token_count=3,
            nonblank_line_count=1,
        ),
        module_result=SimpleNamespace(result_id="lexical-style-source"),
    )

    attached = attach_poetic_reading_ease(
        result,
        frequency=frequency,
        aoa=aoa,
        lexical_style=lexical_style,
    )
    poetic = attached.poetic_reading_ease
    assert poetic is not None
    components = {component.component_id: component for component in poetic.components}
    assert components["frequency"].raw_value == pytest.approx(3.0)
    assert components["frequency"].eligible_count == 2
    assert components["aoa"].raw_value == pytest.approx(8.0)
    assert components["aoa"].eligible_count == 2
    assert components["word_complexity"].eligible_count == 2
    assert all(
        "content words" in components[item].scope_label.casefold()
        for item in ("frequency", "aoa", "word_complexity")
    )
    assert components["line_accessibility"].scope_label == (
        "All lexical words per nonblank line"
    )


def test_poetic_reading_ease_fixed_profile_is_independent_of_visible_fallback(
    preprocessor,
) -> None:
    resource_root = Path(__file__).parents[1] / "resources"
    required = (
        resource_root
        / "subtlex-us"
        / "SUBTLEX-US frequency list with PoS and Zipf information.xlsx",
        resource_root / "kuperman_2013_erratum_ESM1_official.xlsx",
    )
    if not all(path.is_file() for path in required):
        pytest.skip("The optional VV-PRE lexical resources are not installed.")
    text = "so much depends\nupon\n\na red wheel\nbarrow\n\nglazed with rain\nwater"
    common = {
        "project_name": "VV-PRE fixed profile",
        "title": "Fixed profile",
        "original_text": text,
        "lexicon_ids": (),
        "include_frequency": True,
        "include_aoa": True,
        "include_lexical_style": True,
    }
    ordinary = run_workspace_analysis(
        AnalysisRequest(**common),
        preprocessor=preprocessor,
        resource_root=resource_root,
    )
    restricted_visible_reports = run_workspace_analysis(
        AnalysisRequest(
            **common,
            frequency_configuration=FrequencyConfiguration(
                enable_lemma_fallback=False
            ),
            aoa_configuration=AoAConfiguration(enable_lemma_fallback=False),
        ),
        preprocessor=preprocessor,
        resource_root=resource_root,
    )

    ordinary_poetic = ordinary.readability.poetic_reading_ease
    restricted_poetic = restricted_visible_reports.readability.poetic_reading_ease
    assert ordinary_poetic is not None
    assert restricted_poetic is not None
    assert restricted_poetic.score == pytest.approx(ordinary_poetic.score)
    assert [
        component.raw_value for component in restricted_poetic.components
    ] == pytest.approx(
        [component.raw_value for component in ordinary_poetic.components]
    )


def test_poetic_reading_ease_does_not_reweight_missing_components() -> None:
    result = calculate_poetic_reading_ease(
        mean_zipf=6.0,
        mean_aoa=None,
        mean_words_per_line=4.0,
        mean_syllables_per_word=1.2,
    )

    assert result.score is None
    assert result.interpretation_band is None
    assert result.missing_component_ids == ("aoa",)
    assert result.evidence_confidence is None


def test_poetic_reading_ease_confidence_uses_coverage_and_sample_size() -> None:
    common = {
        "mean_zipf": 5.5,
        "mean_aoa": 6.0,
        "mean_words_per_line": 4.0,
        "mean_syllables_per_word": 1.2,
        "line_count": 8,
    }
    high = calculate_poetic_reading_ease(
        **common,
        frequency_counts=(25, 23),
        aoa_counts=(24, 22),
        syllable_counts=(25, 24),
    )
    moderate = calculate_poetic_reading_ease(
        **common,
        frequency_counts=(20, 16),
        aoa_counts=(18, 14),
        syllable_counts=(20, 18),
    )
    limited = calculate_poetic_reading_ease(
        **common,
        frequency_counts=(6, 6),
        aoa_counts=(6, 6),
        syllable_counts=(6, 6),
    )

    assert high.evidence_confidence == "High"
    assert high.minimum_component_coverage == pytest.approx(22 / 24)
    assert high.minimum_lexical_matched_count == 22
    assert moderate.evidence_confidence == "Moderate"
    assert moderate.minimum_component_coverage == pytest.approx(14 / 18)
    assert moderate.minimum_lexical_matched_count == 14
    assert limited.evidence_confidence == "Limited"
    assert limited.minimum_component_coverage == pytest.approx(1.0)
    assert limited.minimum_lexical_matched_count == 6


def test_readability_export_retains_vv_pre_score_components_and_coverage(
    preprocessor,
) -> None:
    result = ReadabilityModule().analyze_detailed(
        _input(preprocessor, "Bright birds sing. Stone shines.")
    )
    poetic = calculate_poetic_reading_ease(
        mean_zipf=5.5,
        mean_aoa=6.0,
        mean_words_per_line=3.0,
        mean_syllables_per_word=result.summary.mean_syllables_per_word,
        frequency_counts=(6, 5),
        aoa_counts=(6, 4),
        line_count=2,
        syllable_counts=(result.summary.word_count, result.summary.word_count),
    )

    rows = _rows(
        export_readability_bundle(
            replace(result, poetic_reading_ease=poetic),
            text_title="New metrics",
        )["readability_summary.csv"]
    )
    exported = {row["metric"]: row for row in rows}
    assert float(exported["vv_pre_score"]["value"]) == pytest.approx(poetic.score)
    assert (
        exported["vv_pre_interpretation_band"]["value"]
        == poetic.interpretation_band
    )
    assert float(exported["frequency.ease_score"]["value"]) == pytest.approx(75.0)
    assert float(exported["frequency.coverage"]["value"]) == pytest.approx(5 / 6)
    assert exported["vv_pre_evidence_confidence"]["value"] == "Limited"
    assert float(
        exported["vv_pre_minimum_component_coverage"]["value"]
    ) == pytest.approx(4 / 6)
    assert exported["vv_pre_minimum_lexical_matched_count"]["value"] == "4"
    assert exported["vv_pre_profile_id"]["value"] == (
        "vv-pre-content-word-profile-1.0"
    )
