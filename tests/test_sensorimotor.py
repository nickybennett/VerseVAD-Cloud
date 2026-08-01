from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from versevad.adapters.lancaster_sensorimotor import (
    COMPOSITE_COLUMNS,
    DIMENSION_COLUMNS,
    DOMINANT_COLUMNS,
    KNOWN_COLUMNS,
    LancasterSensorimotorAdapter,
    LancasterSensorimotorAdapterError,
)
from versevad.core import ModuleInput, ResourceSpec, ResourceState
from versevad.lexical_semantic.sensorimotor import (
    LANCASTER_SENSORIMOTOR_RELATIVE_PATH,
    LANCASTER_SENSORIMOTOR_SHA256,
    SensorimotorConfiguration,
    SensorimotorMatchMethod,
    SensorimotorModule,
)
from versevad.preprocessing import create_text_document


HEADER = (
    "Word",
    *(column for _dimension, column, _sd in DIMENSION_COLUMNS),
    *(sd for _dimension, _column, sd in DIMENSION_COLUMNS),
    *COMPOSITE_COLUMNS,
    *DOMINANT_COLUMNS,
    *KNOWN_COLUMNS,
)


def _row(
    word: str,
    *,
    auditory: float,
    visual: float = 1.0,
    dominant: str = "Auditory",
) -> dict[str, object]:
    means = {
        dimension: 1.0
        for dimension, _mean_column, _sd_column in DIMENSION_COLUMNS
    }
    means["auditory"] = auditory
    means["visual"] = visual
    row: dict[str, object] = {"Word": word}
    for dimension, mean_column, sd_column in DIMENSION_COLUMNS:
        row[mean_column] = means[dimension]
        row[sd_column] = 0.5
    row.update(
        {
            "Max_strength.perceptual": max(auditory, visual, 1.0),
            "Minkowski3.perceptual": 3.0,
            "Exclusivity.perceptual": 0.5,
            "Max_strength.action": 1.0,
            "Minkowski3.action": 2.0,
            "Exclusivity.action": 0.25,
            "Max_strength.sensorimotor": max(auditory, visual, 1.0),
            "Minkowski3.sensorimotor": 4.0,
            "Exclusivity.sensorimotor": 0.4,
            "Dominant.perceptual": dominant,
            "Dominant.action": "Hand_arm",
            "Dominant.sensorimotor": dominant,
            "Percent_known.perceptual": 1.0,
            "Percent_known.action": 1.0,
        }
    )
    return row


def _write_source(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module(tmp_path: Path) -> SensorimotorModule:
    source = tmp_path / "sensorimotor.csv"
    _write_source(
        source,
        [
            _row("stone", auditory=5.0),
            _row("dark night", auditory=4.0, dominant="Visual"),
            _row("the", auditory=0.0),
            _row("not", auditory=0.5),
            _row("idea", auditory=1.0),
        ],
    )
    return SensorimotorModule(
        tmp_path,
        resource_spec=ResourceSpec(
            resource_id="synthetic-sensorimotor",
            display_name="Synthetic sensorimotor fixture",
            relative_path=source.name,
            version="synthetic-v1",
            accepted_sha256=(_sha256(source),),
            citation="Constructed test fixture.",
            license_notice="Synthetic test data.",
        ),
    )


def _analyze(
    module: SensorimotorModule,
    preprocessor,
    text: str,
    *,
    configuration: SensorimotorConfiguration | None = None,
):
    poem = preprocessor.process_document(
        create_text_document("sensorimotor-test", "Sensorimotor test", text)
    )
    return module.analyze_detailed(
        ModuleInput.from_poem_document(poem),
        configuration
        or SensorimotorConfiguration(
            exclude_proper_nouns=False,
            minimum_match_requirement=1,
        ),
    )


def test_proper_nouns_are_included_by_default() -> None:
    assert SensorimotorConfiguration().exclude_proper_nouns is False


def test_adapter_is_read_only_and_validates_source_contract(tmp_path: Path) -> None:
    source = tmp_path / "sensorimotor.csv"
    _write_source(
        source,
        [
            _row("stone", auditory=5.0),
            _row("dark night", auditory=4.0, dominant="Visual"),
        ],
    )
    before = _sha256(source)

    lexicon = LancasterSensorimotorAdapter().load(source)

    assert _sha256(source) == before
    assert lexicon.validation.total_rows == 2
    assert lexicon.validation.usable_entries == 2
    assert lexicon.validation.phrase_entries == 1
    assert lexicon.validation.source_sha256 == before
    assert lexicon.entries["stone"].means.auditory == pytest.approx(5.0)
    assert lexicon.entries["dark night"].is_multiword


def test_adapter_rejects_duplicates_missing_columns_and_bad_ranges(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate.csv"
    _write_source(
        duplicate,
        [
            _row("stone", auditory=5.0),
            _row("STONE", auditory=4.0),
        ],
    )
    with pytest.raises(LancasterSensorimotorAdapterError, match="duplicate"):
        LancasterSensorimotorAdapter().load(duplicate)

    missing = tmp_path / "missing.csv"
    with missing.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=("Word", "Auditory.mean"))
        writer.writeheader()
        writer.writerow({"Word": "stone", "Auditory.mean": 5})
    with pytest.raises(LancasterSensorimotorAdapterError, match="expected columns"):
        LancasterSensorimotorAdapter().load(missing)

    bad = tmp_path / "bad.csv"
    _write_source(bad, [_row("stone", auditory=6.0)])
    with pytest.raises(LancasterSensorimotorAdapterError, match="out-of-range"):
        LancasterSensorimotorAdapter().load(bad)


def test_phrase_matching_profiles_coverage_and_missing_values(
    tmp_path: Path,
    preprocessor,
) -> None:
    result = _analyze(
        _module(tmp_path),
        preprocessor,
        "stone stone\ndark night\nthe idea quorvax",
    )

    assert len(result.observations) == 5
    assert len(result.unmatched_tokens) == 1
    assert result.unmatched_tokens[0].surface_form == "quorvax"
    phrase = next(item for item in result.observations if item.source_is_multiword)
    assert phrase.match_method is SensorimotorMatchMethod.PHRASE
    assert phrase.surface_form == "dark night"
    assert len(phrase.token_ids) == 2

    all_token = result.profile("All matched tokens", "token")
    all_type = result.profile("All matched tokens", "type")
    stop_token = result.profile("Stopwords excluded", "token")
    auditory = next(
        item for item in all_token.dimensions if item.dimension_id == "auditory"
    )
    assert all_token.eligible_token_count == 7
    assert all_token.matched_token_count == 6
    assert all_token.token_coverage == pytest.approx(6 / 7)
    assert all_token.matched_observation_count == 5
    assert auditory.statistics.mean == pytest.approx(3.0)
    assert auditory.cumulative_load == pytest.approx(15.0)
    assert auditory.load_per_100_observations == pytest.approx(300.0)
    assert all_type.matched_observation_count == 4
    assert next(
        item for item in all_type.dimensions if item.dimension_id == "auditory"
    ).statistics.mean == pytest.approx(2.5)
    assert stop_token.eligible_token_count == 6
    assert stop_token.matched_token_count == 5
    assert stop_token.matched_observation_count == 4
    assert next(
        item for item in stop_token.dimensions if item.dimension_id == "auditory"
    ).statistics.mean == pytest.approx(3.75)
    assert result.module_result.coverage[0].unmatched_items == ("quorvax",)
    assert any(
        warning.code == "context_free_norms"
        for warning in result.module_result.warnings
    )


def test_empty_and_unmatched_inputs_do_not_invent_zero_ratings(
    tmp_path: Path,
    preprocessor,
) -> None:
    module = _module(tmp_path)
    empty = _analyze(module, preprocessor, "")
    unmatched = _analyze(module, preprocessor, "quorvax")

    empty_auditory = empty.profile().dimensions[0]
    unmatched_auditory = unmatched.profile().dimensions[0]
    assert empty_auditory.statistics.mean is None
    assert empty.profile().token_coverage is None
    assert unmatched_auditory.statistics.mean is None
    assert unmatched.profile().token_coverage == 0.0
    assert unmatched.unmatched_tokens[0].normalized_form == "quorvax"


def test_protected_contraction_lemma_remains_eligible_in_stopword_view(
    tmp_path: Path,
    preprocessor,
) -> None:
    result = _analyze(_module(tmp_path), preprocessor, "can't")

    coverage = next(
        row
        for row in result.module_result.coverage
        if row.coverage_id
        == "sensorimotor.stopwords_excluded_token_coverage"
    )
    assert coverage.eligible_count == 1
    assert coverage.matched_count == 1
    assert result.profile(
        "Stopwords excluded",
        "token",
    ).matched_observation_count == 1


def test_module_resource_states_and_determinism(
    tmp_path: Path,
    preprocessor,
) -> None:
    missing = SensorimotorModule(
        tmp_path,
        resource_spec=ResourceSpec(
            resource_id="missing-sensorimotor",
            display_name="Missing sensorimotor fixture",
            relative_path="missing.csv",
            version="synthetic-v1",
        ),
    )
    assert missing.validate_resources()[0].state is ResourceState.MISSING

    module = _module(tmp_path)
    first = _analyze(module, preprocessor, "STONE dark night")
    second = _analyze(module, preprocessor, "STONE dark night")
    assert first == second
    assert first.module_result.provenance.resources[0].source_sha256


def test_local_supplied_lancaster_file_passes_contract_if_present() -> None:
    source = Path("resources") / LANCASTER_SENSORIMOTOR_RELATIVE_PATH
    if not source.is_file():
        pytest.skip("The user-supplied Lancaster source is not present.")

    lexicon = LancasterSensorimotorAdapter().load(source)

    assert lexicon.validation.total_rows == 39_707
    assert lexicon.validation.usable_entries == 39_707
    assert lexicon.validation.phrase_entries == 2_896
    assert lexicon.validation.source_sha256 == LANCASTER_SENSORIMOTOR_SHA256
    assert min(entry.means.visual for entry in lexicon.entries.values()) >= 0.0
    assert max(entry.means.visual for entry in lexicon.entries.values()) <= 5.0
