from __future__ import annotations

import math

import pytest

from versevad.core import AnalysisModule, ModuleInput
from versevad.lexical_style import (
    LexicalStyleConfiguration,
    LexicalStyleModule,
    calculate_hdd,
    calculate_mattr,
    calculate_mtld,
)
from versevad.preprocessing import create_text_document


def _analyze(preprocessor, text: str, configuration=None):
    poem = preprocessor.process_document(
        create_text_document("lexical-style-test", "Lexical style test", text)
    )
    return LexicalStyleModule().analyze_detailed(
        ModuleInput.from_poem_document(poem),
        configuration or LexicalStyleConfiguration(),
    )


def test_length_resistant_metrics_reproduce_hand_calculations() -> None:
    forms = ("red", "blue", "red", "green", "blue", "yellow", "red")

    assert calculate_mattr(forms, window_size=3) == pytest.approx(14 / 15)
    assert calculate_hdd(forms, sample_size=3) == pytest.approx(86 / 105)
    assert calculate_mtld(
        ("a", "b", "a", "b", "a", "b", "a", "b"),
        threshold=0.72,
    ) == pytest.approx(4.0)


def test_unavailable_metric_inputs_remain_missing() -> None:
    assert calculate_mattr(("one", "two"), window_size=3) is None
    assert calculate_hdd(("one", "two"), sample_size=3) is None
    assert calculate_mtld(("one", "two", "three"), threshold=0.72) is None
    assert calculate_mattr((), window_size=3) is None
    assert calculate_hdd((), sample_size=3) is None
    assert calculate_mtld((), threshold=0.72) is None


def test_configuration_rejects_opaque_or_invalid_choices() -> None:
    with pytest.raises(ValueError, match="MATTR window"):
        LexicalStyleConfiguration(mattr_window_size=1)
    with pytest.raises(ValueError, match="HD-D sample"):
        LexicalStyleConfiguration(hdd_sample_size=1)
    with pytest.raises(ValueError, match="MTLD threshold"):
        LexicalStyleConfiguration(mtld_threshold=1.0)
    with pytest.raises(ValueError, match="short-text warning"):
        LexicalStyleConfiguration(short_text_warning_threshold=1)
    with pytest.raises(ValueError, match="scenario"):
        LexicalStyleConfiguration(scenario_id=" ")


def test_module_reports_document_line_stanza_and_word_length_data(
    preprocessor,
) -> None:
    result = _analyze(
        preprocessor,
        "red blue red\ngreen blue\n\nyellow red",
        LexicalStyleConfiguration(
            mattr_window_size=3,
            hdd_sample_size=3,
            short_text_warning_threshold=10,
        ),
    )

    assert isinstance(LexicalStyleModule(), AnalysisModule)
    assert result.summary.lexical_token_count == 7
    assert result.summary.normalized_surface_type_count == 4
    assert result.summary.surface_type_token_ratio == pytest.approx(4 / 7)
    assert result.summary.mattr == pytest.approx(14 / 15)
    assert result.summary.hdd == pytest.approx(86 / 105)
    assert result.summary.mean_alphabetic_characters_per_token == pytest.approx(4.0)
    assert result.summary.median_alphabetic_characters_per_token == pytest.approx(4.0)
    assert result.summary.minimum_alphabetic_characters == 3
    assert result.summary.maximum_alphabetic_characters == 6
    assert [row.word_count for row in result.line_summaries] == [3, 2, 0, 2]
    assert [row.is_blank for row in result.line_summaries] == [
        False,
        False,
        True,
        False,
    ]
    assert [row.word_count for row in result.stanza_summaries] == [5, 2]
    assert [row.line_count for row in result.stanza_summaries] == [2, 1]
    assert result.summary.nonblank_line_word_count_statistics.mean == pytest.approx(
        7 / 3
    )
    assert (
        result.summary.nonblank_line_word_count_statistics
        .population_standard_deviation
        == pytest.approx((2 / 9) ** 0.5)
    )
    assert result.summary.stanza_word_count_statistics.mean == pytest.approx(3.5)
    assert (
        result.summary.stanza_word_count_statistics.population_standard_deviation
        == pytest.approx(1.5)
    )
    assert result.summary.stanza_line_count_statistics.mean == pytest.approx(1.5)
    assert (
        result.summary.stanza_line_count_statistics.population_standard_deviation
        == pytest.approx(0.5)
    )
    assert {
        metric.metric_id
        for metric in result.module_result.metrics
        if metric.scope == "document"
    } >= {
        "lexical_style.mean_words_per_nonblank_line",
        "lexical_style.population_sd_words_per_nonblank_line",
        "lexical_style.mean_words_per_stanza",
        "lexical_style.population_sd_words_per_stanza",
        "lexical_style.mean_nonblank_lines_per_stanza",
        "lexical_style.population_sd_nonblank_lines_per_stanza",
    }
    assert sum(item.token_count for item in result.word_length_distribution) == 7
    assert any(
        warning.code == "lexical_style.short_text"
        for warning in result.module_result.warnings
    )
    assert result.module_result.module_version == "1.1.0"
    assert result.module_result.result_id.startswith("lexical-style-result-v2:")


def test_word_counts_exclude_punctuation_and_numeric_tokens_without_zero_fill(
    preprocessor,
) -> None:
    result = _analyze(
        preprocessor,
        "Stone, 42 — sky!",
        LexicalStyleConfiguration(
            mattr_window_size=2,
            hdd_sample_size=2,
            short_text_warning_threshold=2,
        ),
    )

    assert result.summary.lexical_token_count == 2
    assert [item.surface_form for item in result.token_audit if item.included] == [
        "Stone",
        "sky",
    ]
    assert all(
        item.alphabetic_character_count is None
        for item in result.token_audit
        if not item.included
    )
    assert result.line_summaries[0].word_count == 2
    assert result.module_result.coverage[0].coverage_rate == 1.0
    assert math.isfinite(result.summary.mattr)


def test_line_edge_unicode_whitespace_does_not_change_structural_metrics(
    preprocessor,
) -> None:
    configuration = LexicalStyleConfiguration(
        mattr_window_size=3,
        hdd_sample_size=3,
        short_text_warning_threshold=3,
    )
    clean = _analyze(
        preprocessor,
        "red blue red\ngreen blue\n\nyellow red",
        configuration,
    )
    indented = _analyze(
        preprocessor,
        (
            "\t\u00a0red blue red \u2003\n"
            " \u2003green blue\t\n"
            "\u00a0\t\u2009\n"
            "\u2003yellow red\u00a0"
        ),
        configuration,
    )

    assert indented.summary == clean.summary
    assert [item.word_count for item in indented.line_summaries] == [3, 2, 0, 2]
    assert [item.word_count for item in indented.stanza_summaries] == [5, 2]


def test_module_requires_the_shared_poem_document(preprocessor) -> None:
    poem = preprocessor.process_document(
        create_text_document("missing-poem", "Missing poem", "red blue")
    )
    module_input = ModuleInput(
        document=poem.source,
        tokens=poem.tokens,
        preprocessing=poem.preprocessing,
    )

    with pytest.raises(
        RuntimeError,
        match="shared poetry-preserving processing record",
    ):
        LexicalStyleModule().analyze_detailed(module_input)
