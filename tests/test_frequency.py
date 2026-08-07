from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import pytest
from openpyxl import Workbook

from versevad.adapters.subtlex_us import (
    REQUIRED_COLUMNS,
    SubtlexUsAdapter,
    SubtlexUsAdapterError,
)
from versevad.core import AnalysisModule, ModuleInput, ResourceSpec, ResourceState
from versevad.lexical_semantic.frequency import (
    SUBTLEX_US_RELATIVE_PATH,
    SUBTLEX_US_SHA256,
    FrequencyConfiguration,
    FrequencyMatchMethod,
    FrequencyModule,
)
from versevad.preprocessing import create_text_document


def _row(
    term: str,
    zipf_value: float,
    *,
    frequency_count: int = 10,
    contextual_diversity_count: int = 8,
    dominant_pos: str = "Noun",
) -> tuple[object, ...]:
    return (
        term,
        frequency_count,
        contextual_diversity_count,
        frequency_count,
        contextual_diversity_count,
        frequency_count / 51,
        math.log10(frequency_count + 1),
        contextual_diversity_count / 83.88,
        math.log10(contextual_diversity_count + 1),
        dominant_pos,
        frequency_count,
        1.0,
        dominant_pos,
        frequency_count,
        zipf_value,
    )


def _write_workbook(path: Path, rows: list[tuple[object, ...]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "out1g"
    sheet.append(REQUIRED_COLUMNS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module(
    tmp_path: Path,
    rows: list[tuple[object, ...]],
) -> FrequencyModule:
    source = tmp_path / "subtlex.xlsx"
    _write_workbook(source, rows)
    spec = ResourceSpec(
        resource_id="synthetic-subtlex-us",
        display_name="Synthetic SUBTLEX-US fixture",
        relative_path=source.name,
        version="synthetic-v1",
        accepted_sha256=(_sha256(source),),
        citation="Constructed test fixture.",
        license_notice="Synthetic test data.",
    )
    return FrequencyModule(tmp_path, resource_spec=spec)


def _analyze(
    module: FrequencyModule,
    preprocessor,
    text: str,
    *,
    configuration: FrequencyConfiguration | None = None,
):
    poem = preprocessor.process_document(
        create_text_document("frequency-test", "Frequency test", text)
    )
    return module.analyze_detailed(
        ModuleInput.from_poem_document(poem),
        configuration or FrequencyConfiguration(),
    )


def test_adapter_preserves_source_and_validates_zipf_fields(tmp_path: Path) -> None:
    source = tmp_path / "subtlex.xlsx"
    _write_workbook(
        source,
        [
            _row("stone", 4.5, frequency_count=100, contextual_diversity_count=40),
            _row("quartz", 2.2, frequency_count=2, contextual_diversity_count=2),
            (
                *_row("unclassified", 1.8)[:9],
                "#N/A",
                "#N/A",
                "#N/A",
                "#N/A",
                "#N/A",
                1.8,
            ),
        ],
    )
    before = _sha256(source)

    lexicon = SubtlexUsAdapter().load(source)

    assert _sha256(source) == before
    assert lexicon.validation.is_valid
    assert lexicon.validation.total_rows == 3
    assert lexicon.validation.usable_entries == 3
    assert lexicon.validation.source_sha256 == before
    assert lexicon.lookup("stone").zipf_value == pytest.approx(4.5)
    assert lexicon.lookup("unclassified").dominant_source_pos_frequency is None


def test_adapter_rejects_missing_columns_duplicates_and_bad_ranges(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.xlsx"
    workbook = Workbook()
    workbook.active.title = "out1g"
    workbook.active.append(("Word", "Zipf-value"))
    workbook.active.append(("stone", 4.0))
    workbook.save(missing)
    with pytest.raises(SubtlexUsAdapterError, match="expected columns"):
        SubtlexUsAdapter().load(missing)

    malformed = tmp_path / "malformed.xlsx"
    bad = list(_row("STONE", 9.0))
    bad[1] = 0
    _write_workbook(malformed, [_row("stone", 4.0), tuple(bad)])
    with pytest.raises(SubtlexUsAdapterError) as captured:
        SubtlexUsAdapter().load(malformed)
    detail = captured.value.technical_detail.casefold()
    assert "duplicate" in detail
    assert "outside" in detail or "at least" in detail
    assert not captured.value.data_changed


def test_exact_precedes_lemma_and_unmatched_remains_missing(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(
        tmp_path,
        [
            _row("saw", 2.0),
            _row("see", 5.0),
            _row("stone", 4.0),
        ],
    )
    poem = preprocessor.process_document(
        create_text_document(
            "exact-frequency",
            "Exact frequency",
            "saw stones quorvax",
        )
    )
    tokens = tuple(
        replace(token, lemma="see", normalized_lemma="see")
        if token.surface_form == "saw"
        else token
        for token in poem.tokens
    )
    result = module.analyze_detailed(
        ModuleInput(
            document=poem.source,
            tokens=tokens,
            preprocessing=poem.preprocessing,
        ),
        FrequencyConfiguration(exclude_proper_nouns=False),
    )
    by_surface = {row.surface_form: row for row in result.token_audit}

    assert by_surface["saw"].match_method is FrequencyMatchMethod.EXACT
    assert by_surface["saw"].zipf_value == pytest.approx(2.0)
    assert by_surface["stones"].match_method is FrequencyMatchMethod.LEMMA
    assert by_surface["stones"].zipf_value == pytest.approx(4.0)
    assert by_surface["quorvax"].match_method is FrequencyMatchMethod.UNMATCHED
    assert by_surface["quorvax"].zipf_value is None
    assert result.summary.token_coverage == pytest.approx(2 / 3)


def test_alphabetic_number_word_matches_but_numeric_literal_is_ineligible(
    tmp_path: Path,
    preprocessor,
) -> None:
    result = _analyze(_module(tmp_path, [_row("one", 6.0)]), preprocessor, "one 27")
    by_surface = {row.surface_form: row for row in result.token_audit}

    assert by_surface["one"].included is True
    assert by_surface["one"].zipf_value == pytest.approx(6.0)
    assert "alphabetically spelled" in by_surface["one"].reason
    assert by_surface["27"].eligible is False
    assert "pure numeric literal" in by_surface["27"].reason


def test_optional_content_word_scope_uses_only_requested_pos_tags(
    tmp_path: Path,
    preprocessor,
) -> None:
    terms = (
        "the",
        "stone",
        "runs",
        "bright",
        "swiftly",
        "she",
        "can",
        "under",
        "and",
        "because",
    )
    module = _module(
        tmp_path,
        [_row(term, 4.0 + (index / 10)) for index, term in enumerate(terms)],
    )
    poem = preprocessor.process_document(
        create_text_document(
            "content-scope",
            "Content scope",
            "the stone runs bright swiftly she can under and because",
        )
    )
    tags = {
        "the": "DET",
        "stone": "NOUN",
        "runs": "VERB",
        "bright": "ADJ",
        "swiftly": "ADV",
        "she": "PRON",
        "can": "AUX",
        "under": "ADP",
        "and": "CCONJ",
        "because": "SCONJ",
    }
    tokens = tuple(
        replace(token, part_of_speech=tags[token.normalized_form])
        for token in poem.tokens
    )
    module_input = ModuleInput(
        document=poem.source,
        tokens=tokens,
        preprocessing=poem.preprocessing,
    )

    default = module.analyze_detailed(
        module_input,
        FrequencyConfiguration(exclude_proper_nouns=False),
    )
    content = module.analyze_detailed(
        module_input,
        FrequencyConfiguration(
            exclude_proper_nouns=False,
            content_words_only=True,
        ),
    )

    assert default.summary.eligible_token_count == 10
    # The retired module-local flag is accepted for saved-profile compatibility,
    # but lookup retains all evidence. Canonical content-word scope is now a
    # post-analysis profile derived from this audit.
    assert content.summary.eligible_token_count == 10
    assert content.summary == default.summary
    assert all(row.match_method is not FrequencyMatchMethod.NOT_ELIGIBLE for row in content.token_audit)


def test_proper_names_are_included_by_default_and_can_be_excluded(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(tmp_path, [_row("alice", 5.0), _row("sings", 4.0)])
    poem = preprocessor.process_document(
        create_text_document("proper-frequency", "Proper frequency", "Alice sings")
    )
    tokens = tuple(
        replace(token, part_of_speech="PROPN", is_proper_noun=True)
        if token.surface_form == "Alice"
        else token
        for token in poem.tokens
    )
    result = module.analyze_detailed(
        ModuleInput(
            document=poem.source,
            tokens=tokens,
            preprocessing=poem.preprocessing,
        )
    )
    alice = next(row for row in result.token_audit if row.surface_form == "Alice")

    assert alice.match_method is FrequencyMatchMethod.EXACT
    assert alice.zipf_value == pytest.approx(5.0)
    assert result.summary.eligible_token_count == 2

    excluded = module.analyze_detailed(
        ModuleInput(
            document=poem.source,
            tokens=tokens,
            preprocessing=poem.preprocessing,
        ),
        FrequencyConfiguration(exclude_proper_nouns=True),
    )
    excluded_alice = next(
        row for row in excluded.token_audit if row.surface_form == "Alice"
    )
    assert excluded_alice.match_method is FrequencyMatchMethod.NOT_ELIGIBLE
    assert excluded_alice.zipf_value is None
    assert "proper" in excluded_alice.reason.casefold()
    assert excluded.summary.eligible_token_count == 1


def test_repetition_weights_tokens_and_median_is_primary(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(
        tmp_path,
        [
            _row("rareword", 2.0),
            _row("ordinary", 5.0),
            _row("common", 6.0),
        ],
    )
    result = _analyze(
        module,
        preprocessor,
        "rareword rareword ordinary common",
        configuration=FrequencyConfiguration(exclude_proper_nouns=False),
    )

    assert result.summary.statistics.mean == pytest.approx(3.75)
    assert result.summary.statistics.median == pytest.approx(3.5)
    assert result.summary.interquartile_range == pytest.approx(3.25)
    rare = next(term for term in result.term_summaries if term.source_term == "rareword")
    assert rare.matched_token_occurrences == 2
    assert result.lowest_frequency_terms[0].source_term == "rareword"
    assert result.rare_word_tail[0].source_term == "rareword"
    median_metric = next(
        metric
        for metric in result.module_result.metrics
        if metric.metric_id == "frequency.median_zipf"
        and metric.scope == "document"
    )
    assert "primary" in median_metric.note


def test_all_common_vocabulary_has_no_rare_tail(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(
        tmp_path,
        [
            _row("ordinary", 6.0),
            _row("familiar", 6.5),
            _row("everyday", 7.0),
        ],
    )
    result = _analyze(
        module,
        preprocessor,
        "ordinary familiar everyday",
        configuration=FrequencyConfiguration(exclude_proper_nouns=False),
    )

    assert result.summary.statistics.median == pytest.approx(6.5)
    assert result.rare_word_tail == ()
    bands = {band.band_id: band for band in result.summary.bands}
    assert bands["rare"].token_count == 0
    assert bands["very_common"].token_count == 3


def test_lemma_fallback_can_be_disabled(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(tmp_path, [_row("stone", 4.0)])
    result = _analyze(
        module,
        preprocessor,
        "stones",
        configuration=FrequencyConfiguration(
            exclude_proper_nouns=False,
            enable_lemma_fallback=False,
        ),
    )

    assert result.token_audit[0].match_method is FrequencyMatchMethod.UNMATCHED
    assert result.token_audit[0].zipf_value is None


def test_empty_and_wholly_unmatched_inputs_keep_aggregates_missing(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(tmp_path, [_row("stone", 4.0)])

    empty = _analyze(module, preprocessor, "")
    unmatched = _analyze(
        module,
        preprocessor,
        "quorvax",
        configuration=FrequencyConfiguration(exclude_proper_nouns=False),
    )

    assert empty.summary.statistics.median is None
    assert empty.summary.token_coverage is None
    assert empty.summary.unique_type_coverage is None
    assert unmatched.summary.statistics.median is None
    assert unmatched.summary.token_coverage == 0.0
    assert unmatched.token_audit[0].zipf_value is None


def test_module_resource_states_unicode_and_determinism(
    tmp_path: Path,
    preprocessor,
) -> None:
    missing_spec = ResourceSpec(
        resource_id="missing-subtlex",
        display_name="Missing SUBTLEX fixture",
        relative_path="missing.xlsx",
        version="synthetic-v1",
    )
    missing = FrequencyModule(tmp_path, resource_spec=missing_spec)
    assert isinstance(missing, AnalysisModule)
    assert missing.validate_resources()[0].state is ResourceState.MISSING

    available = _module(tmp_path, [_row("café", 4.2)])
    configuration = FrequencyConfiguration(exclude_proper_nouns=False)
    first = _analyze(
        available, preprocessor, "CAFÉ", configuration=configuration
    )
    second = _analyze(
        available, preprocessor, "CAFÉ", configuration=configuration
    )
    assert first == second
    assert first.token_audit[0].match_method is FrequencyMatchMethod.EXACT
    assert first.module_result.provenance.resources[0].source_sha256


def test_configuration_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="between"):
        FrequencyConfiguration(rare_below=0.5)
    with pytest.raises(ValueError, match="strictly increasing"):
        FrequencyConfiguration(
            rare_below=3.0,
            uncommon_below=3.0,
        )


def test_local_subtlex_us_file_passes_contract_if_present() -> None:
    source = Path("resources") / SUBTLEX_US_RELATIVE_PATH
    if not source.is_file():
        pytest.skip("The official local SUBTLEX-US workbook is not present.")

    lexicon = SubtlexUsAdapter().load(source)

    assert lexicon.validation.is_valid
    assert lexicon.validation.total_rows == 74_286
    assert lexicon.validation.usable_entries == 74_286
    assert lexicon.validation.source_sha256 == SUBTLEX_US_SHA256
    assert min(entry.zipf_value for entry in lexicon.entries.values()) == pytest.approx(
        1.5928641378084412
    )
    assert max(entry.zipf_value for entry in lexicon.entries.values()) == pytest.approx(
        7.621173840455432
    )
