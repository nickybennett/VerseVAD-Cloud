from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from versevad.corpus import (
    CorpusAnalysisCancelled,
    CorpusAnalysisConfiguration,
    corpus_module_category_profiles,
    corpus_module_profiles,
    analyze_corpus,
)
from versevad.db import (
    CorpusModuleMetricRecord,
    CorpusTextImport,
    ProjectRepository,
)
from versevad.lexical_style import LexicalStyleConfiguration
from versevad.exports.corpus_csv import build_corpus_export_bundle
from versevad.prosody import MeterAnalysisMode, MeterConfiguration


def test_optional_module_only_corpus_batch_persists_auditable_results(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("Lexical style corpus")
    texts = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "First",
                "first.txt",
                "first.txt",
                "red blue red",
            ),
            CorpusTextImport(
                "Second",
                "second.txt",
                "second.txt",
                "green blue",
            ),
        ),
    )

    batch = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=(),
        text_ids=tuple(text.text_id for text in texts),
        module_configuration=CorpusAnalysisConfiguration(
            include_lexical_style=True,
            lexical_style_configuration=LexicalStyleConfiguration(
                mattr_window_size=2,
                hdd_sample_size=2,
                short_text_warning_threshold=2,
            ),
        ),
        preprocessor=preprocessor,
    )

    assert repository.schema_version() == 4
    assert batch.status == "complete"
    assert batch.lexicon_ids == ()
    assert batch.module_names == (
        "vader_sentiment",
        "readability",
        "lexical_style",
    )
    assert "vader_sentiment" in batch.module_configuration
    assert "readability" in batch.module_configuration
    assert (
        batch.module_configuration["lexical_style"]["mattr_window_size"]
        == 2
    )

    results = repository.list_module_results_for_batch(
        project.project_id,
        batch.batch_id,
    )
    assert len(results) == 6
    assert {row.module_name for row in results} == {
        "vader_sentiment",
        "readability",
        "lexical_style",
    }
    assert all(row.source_text_sha256 for row in results)

    metrics = repository.list_module_metrics_for_batch(
        project.project_id,
        batch.batch_id,
    )
    assert any(
        row.metric_id == "lexical_style.mattr"
        and row.scope == "document"
        and row.value == pytest.approx(1.0)
        for row in metrics
    )
    assert sorted(
        row.value
        for row in metrics
        if row.metric_id == "lexical_style.mean_words_per_nonblank_line"
        and row.scope == "document"
    ) == [2.0, 3.0]
    assert [
        row.value
        for row in metrics
        if row.metric_id == "lexical_style.mean_nonblank_lines_per_stanza"
        and row.scope == "document"
    ] == [1.0, 1.0]
    assert [
        row.value
        for row in metrics
        if row.metric_id == "lexical_style.word_count"
        and row.scope == "line"
    ] == [3, 2]

    coverage = repository.list_module_coverage_for_batch(
        project.project_id,
        batch.batch_id,
    )
    lexical_style_coverage = [
        row for row in coverage if row.module_name == "lexical_style"
    ]
    assert len(lexical_style_coverage) == 4
    assert all(row.coverage_rate == 1.0 for row in lexical_style_coverage)
    warnings = repository.list_module_warnings_for_batch(
        project.project_id,
        batch.batch_id,
    )
    assert {row.module_name for row in warnings} <= {
        "vader_sentiment",
        "readability",
        "lexical_style",
    }

    first = next(row for row in results if row.module_name == "lexical_style")
    artifacts = repository.list_module_artifacts(
        first.run_id,
        first.module_name,
    )
    assert {row.filename for row in artifacts} == {
        "lexical_style_summary.csv",
        "lexical_style_word_lengths.csv",
        "lexical_style_lines.csv",
        "lexical_style_stanzas.csv",
        "lexical_style_token_audit.csv",
        "lexical_style_manifest.csv",
        "lexical_style_report.docx",
    }
    bundle = repository.build_module_artifact_zip(
        first.run_id,
        first.module_name,
    )
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {row.filename for row in artifacts}

    aggregates = repository.list_module_aggregates_for_batch(
        project.project_id,
        batch.batch_id,
    )
    pooled = {
        row.metric_id: row
        for row in aggregates
        if row.aggregation_method == "ordered_pooled_token_sequence"
    }
    assert pooled["lexical_style.pooled.lexical_token_count"].value == 5
    assert pooled["lexical_style.pooled.normalized_surface_type_count"].value == 3
    assert pooled["lexical_style.pooled.surface_type_token_ratio"].value == (
        pytest.approx(3 / 5)
    )
    assert pooled["lexical_style.pooled.mattr"].value == pytest.approx(1.0)
    assert pooled["lexical_style.pooled.hdd"].value == pytest.approx(0.9)

    corpus_bundle = build_corpus_export_bundle(
        project,
        repository.list_texts(project.project_id),
        (),
        (),
        module_metrics=metrics,
        module_coverage=coverage,
        module_results=results,
        module_aggregates=aggregates,
        module_warnings=warnings,
    )
    with zipfile.ZipFile(io.BytesIO(corpus_bundle)) as archive:
        assert "corpus_report.docx" in archive.namelist()
        metric_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("corpus_module_metrics.csv").decode(
                        "utf-8-sig"
                    )
                )
            )
        )
        aggregate_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("corpus_module_aggregates.csv").decode(
                        "utf-8-sig"
                    )
                )
            )
        )
        assert {row["title"] for row in metric_rows} == {"First", "Second"}
        assert any(row["scope"] != "document" for row in metric_rows)
        assert any(
            row["aggregation_method"] == "ordered_pooled_token_sequence"
            for row in aggregate_rows
        )


def test_corpus_uses_same_optional_performance_aware_meter_engine(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "meter-corpus.sqlite3")
    project = repository.create_project("Performance meter corpus")
    text = "the stone the stone the stone the stone"
    imported = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Measured",
                "measured.txt",
                "measured.txt",
                "\n".join((text, text, text, text)),
            ),
        ),
    )

    batch = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=(),
        text_ids=(imported[0].text_id,),
        module_configuration=CorpusAnalysisConfiguration(
            include_meter=True,
            meter_configuration=MeterConfiguration(
                analysis_mode=MeterAnalysisMode.PERFORMANCE_AWARE,
            ),
        ),
        preprocessor=preprocessor,
    )

    metrics = repository.list_module_metrics_for_batch(
        project.project_id,
        batch.batch_id,
    )
    performance = {
        row.metric_id: row.value
        for row in metrics
        if row.metric_id.startswith("meter.performance.")
    }
    assert performance["meter.performance.primary_candidate"] == (
        "Iambic tetrameter"
    )
    assert performance["meter.performance.rhythmic_organization"] == (
        "accentual_syllabic"
    )
    meter_result = next(
        row
        for row in repository.list_module_results_for_batch(
            project.project_id,
            batch.batch_id,
        )
        if row.module_name == "candidate_meter_and_rhythmic_regularity"
    )
    artifacts = {
        item.filename
        for item in repository.list_module_artifacts(
            meter_result.run_id,
            meter_result.module_name,
        )
    }
    assert {
        "meter_realizations.csv",
        "meter_stanzas.csv",
        "meter_rhythm_trajectory.csv",
        "meter_report.docx",
    } <= artifacts


def test_corpus_uses_and_persists_sensorimotor_module_when_installed(
    tmp_path,
    preprocessor,
) -> None:
    resource = (
        Path("resources")
        / "Lancaster_Sensorimotor_Norms"
        / "Lancaster_sensorimotor_norms_for_39707_words.csv"
    )
    if not resource.is_file():
        pytest.skip("The user-supplied Lancaster source is not present.")
    repository = ProjectRepository(tmp_path / "sensorimotor-corpus.sqlite3")
    project = repository.create_project("Sensorimotor corpus")
    imported = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Embodied",
                "embodied.txt",
                "embodied.txt",
                "Stone sings in the dark night.\nHands touch water.",
            ),
        ),
    )

    batch = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=(),
        text_ids=(imported[0].text_id,),
        module_configuration=CorpusAnalysisConfiguration(
            include_sensorimotor=True,
        ),
        preprocessor=preprocessor,
    )

    assert "sensorimotor_imagery_and_embodiment" in batch.module_names
    result = next(
        row
        for row in repository.list_module_results_for_batch(
            project.project_id,
            batch.batch_id,
        )
        if row.module_name == "sensorimotor_imagery_and_embodiment"
    )
    metrics = repository.list_module_metrics_for_batch(
        project.project_id,
        batch.batch_id,
    )
    assert any(
        row.metric_id == "sensorimotor.visual.mean"
        and row.scope_id == "all_token"
        and row.value is not None
        for row in metrics
    )
    artifacts = {
        item.filename
        for item in repository.list_module_artifacts(
            result.run_id,
            result.module_name,
        )
    }
    assert {
        "sensorimotor_summary.csv",
        "sensorimotor_by_structure.csv",
        "sensorimotor_observations.csv",
        "sensorimotor_unmatched.csv",
        "sensorimotor_report.docx",
    } <= artifacts


def test_corpus_cancellation_occurs_only_at_safe_work_boundary(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "cancel-corpus.sqlite3")
    project = repository.create_project("Cancellable corpus")
    imported = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport("First", "first.txt", "first.txt", "red blue"),
            CorpusTextImport(
                "Second",
                "second.txt",
                "second.txt",
                "green gold",
            ),
        ),
    )
    checks = 0

    def cancel_after_first_boundary() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    with pytest.raises(CorpusAnalysisCancelled, match="cancelled safely"):
        analyze_corpus(
            repository,
            project.project_id,
            lexicon_ids=(),
            text_ids=tuple(item.text_id for item in imported),
            module_configuration=CorpusAnalysisConfiguration(
                include_lexical_style=True,
            ),
            preprocessor=preprocessor,
            cancel_check=cancel_after_first_boundary,
        )

    assert repository.list_completed_batches(project.project_id) == ()


def _module_metric(
    *,
    run_id: str,
    text_id: str,
    title: str,
    module_name: str,
    metric_id: str,
    value: float | None,
    observation_count: int | None,
    configuration_id: str = "same-config",
) -> CorpusModuleMetricRecord:
    return CorpusModuleMetricRecord(
        run_id=run_id,
        text_id=text_id,
        text_version_id=f"{text_id}-version",
        title=title,
        author="",
        collection="",
        date_label="",
        genre="",
        module_name=module_name,
        module_version="1.0.0",
        result_id=f"{run_id}-result",
        configuration_id=configuration_id,
        metric_id=metric_id,
        value=value,
        layer="computed_summary",
        scope="document",
        scope_id="",
        unit="source scale",
        weighting="matched token occurrences",
        denominator="synthetic",
        observation_count=observation_count,
        note="",
        completed_at="now",
    )


def test_corpus_module_profiles_never_naively_weight_diversity_metrics() -> None:
    metrics = (
        _module_metric(
            run_id="r1",
            text_id="t1",
            title="Long",
            module_name="concreteness",
            metric_id="concreteness.mean",
            value=4.0,
            observation_count=9,
        ),
        _module_metric(
            run_id="r2",
            text_id="t2",
            title="Short",
            module_name="concreteness",
            metric_id="concreteness.mean",
            value=2.0,
            observation_count=1,
        ),
        _module_metric(
            run_id="r1",
            text_id="t1",
            title="Long",
            module_name="lexical_style",
            metric_id="lexical_style.mattr",
            value=0.8,
            observation_count=None,
        ),
        _module_metric(
            run_id="r2",
            text_id="t2",
            title="Short",
            module_name="lexical_style",
            metric_id="lexical_style.mattr",
            value=0.4,
            observation_count=None,
        ),
    )

    profiles = {
        (row.module_name, row.metric_id): row
        for row in corpus_module_profiles(metrics, total_works=2)
    }
    concreteness = profiles[("concreteness", "concreteness.mean")]
    assert concreteness.equal_work_mean == pytest.approx(3.0)
    assert concreteness.observation_weighted_mean == pytest.approx(3.8)
    assert concreteness.total_observations == 10

    mattr = profiles[("lexical_style", "lexical_style.mattr")]
    assert mattr.equal_work_mean == pytest.approx(0.6)
    assert mattr.observation_weighted_mean is None
    assert "not averaged as though tokens were pooled" in mattr.note


def test_corpus_module_category_profiles_report_prevalence_not_consensus() -> None:
    metrics = (
        _module_metric(
            run_id="r1",
            text_id="t1",
            title="First",
            module_name="candidate_meter_and_rhythmic_regularity",
            metric_id="meter.closest_candidate",
            value="iambic pentameter",
            observation_count=None,
        ),
        _module_metric(
            run_id="r2",
            text_id="t2",
            title="Second",
            module_name="candidate_meter_and_rhythmic_regularity",
            metric_id="meter.closest_candidate",
            value="iambic pentameter",
            observation_count=None,
        ),
        _module_metric(
            run_id="r3",
            text_id="t3",
            title="Third",
            module_name="candidate_meter_and_rhythmic_regularity",
            metric_id="meter.closest_candidate",
            value="trochaic tetrameter",
            observation_count=None,
        ),
    )
    rows = corpus_module_category_profiles(metrics)
    assert [(row.category, row.works_with_category) for row in rows] == [
        ("iambic pentameter", 2),
        ("trochaic tetrameter", 1),
    ]
    assert rows[0].prevalence == pytest.approx(2 / 3)
    assert "does not declare one corpus-wide meter" in rows[0].note
