import csv
import io

import pytest

from versevad.core.modules import ModuleInput
from versevad.exports.readability import export_readability_bundle
from versevad.exports.sentiment import export_vader_sentiment_bundle
from versevad.lexical_semantic.readability import (
    ReadabilityConfiguration,
    ReadabilityModule,
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
