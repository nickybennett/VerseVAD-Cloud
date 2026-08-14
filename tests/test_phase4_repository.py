from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.corpus import (
    analyze_corpus,
    corpus_vad_profiles,
    corpus_vad_work_comparisons,
    decode_corpus_files,
)
from versevad.db import CorpusMetricRecord, CorpusTextImport, ProjectRepository
from versevad.models import PhrasePolicy
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import create_text_document


def _workspace(text, preprocessor) -> WorkspaceAnalysis:
    document = replace(
        create_text_document(text.text_id, text.title, text.original_text),
        text_version_id=text.text_version_id,
    )
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        preprocessor,
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
    )
    request = AnalysisRequest(
        project_name="Synthetic corpus",
        title=text.title,
        original_text=text.original_text,
        lexicon_ids=(result.lexicon_metadata.lexicon_id,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
    )
    return WorkspaceAnalysis(request, document, (result,), compare_lexicons((result,)))


def _vad_metric(
    *,
    text_id: str,
    title: str,
    metric: str,
    value: float,
    observations: int,
) -> CorpusMetricRecord:
    return CorpusMetricRecord(
        run_id=f"run-{text_id}",
        text_id=text_id,
        text_version_id=f"{text_id}:v1",
        title=title,
        author="",
        collection="Fixture collection",
        date_label="",
        genre="poem",
        lexicon_id="fixture-vad",
        lexicon="Fixture VAD",
        value_kind="vad",
        metric=metric,
        dimension="valence",
        category="",
        weighting="token",
        scale="normalized_0_1",
        denominator=f"{observations} included matched observations",
        value=value,
        observations=observations,
        matched_tokens=observations,
        lexical_tokens=observations,
        coverage=1.0,
        completed_at="2026-07-26T00:00:00+00:00",
        analysis_view="all_matched",
    )


def test_corpus_vad_dispersion_keeps_pooled_ratings_and_poem_means_distinct() -> None:
    metrics = (
        _vad_metric(
            text_id="a",
            title="First",
            metric="vad_mean",
            value=0.2,
            observations=2,
        ),
        _vad_metric(
            text_id="a",
            title="First",
            metric="vad_standard_deviation",
            value=0.1,
            observations=2,
        ),
        _vad_metric(
            text_id="b",
            title="Second",
            metric="vad_mean",
            value=0.8,
            observations=3,
        ),
        _vad_metric(
            text_id="b",
            title="Second",
            metric="vad_standard_deviation",
            value=0.2,
            observations=3,
        ),
    )

    profile = corpus_vad_profiles(metrics, total_works=2)[0]
    assert profile.token_weighted_volume_mean == pytest.approx(0.56)
    assert profile.pooled_lexical_rating_standard_deviation == pytest.approx(
        (0.1144) ** 0.5
    )
    assert profile.work_weighted_volume_mean == pytest.approx(0.5)
    assert profile.poem_mean_standard_deviation == pytest.approx(0.3)
    assert profile.poem_mean_median == pytest.approx(0.5)
    assert profile.poem_mean_minimum == pytest.approx(0.2)
    assert profile.poem_mean_maximum == pytest.approx(0.8)

    comparisons = corpus_vad_work_comparisons(metrics)
    assert [row.population_standard_deviation for row in comparisons] == [
        pytest.approx(0.1),
        pytest.approx(0.2),
    ]


def test_corpus_vad_pooled_dispersion_stays_missing_when_a_work_sd_is_missing() -> None:
    metrics = (
        _vad_metric(
            text_id="a",
            title="First",
            metric="vad_mean",
            value=0.2,
            observations=2,
        ),
        _vad_metric(
            text_id="a",
            title="First",
            metric="vad_standard_deviation",
            value=0.1,
            observations=2,
        ),
        _vad_metric(
            text_id="b",
            title="Second",
            metric="vad_mean",
            value=0.8,
            observations=3,
        ),
    )

    profile = corpus_vad_profiles(metrics, total_works=2)[0]
    assert profile.pooled_lexical_rating_standard_deviation is None
    assert profile.poem_mean_standard_deviation == pytest.approx(0.3)
    comparisons = corpus_vad_work_comparisons(metrics)
    assert comparisons[0].population_standard_deviation == pytest.approx(0.1)
    assert comparisons[1].population_standard_deviation is None


def test_corpus_vad_profiles_honor_scope_and_within_poem_weighting() -> None:
    token_metric = _vad_metric(
        text_id="a",
        title="First",
        metric="vad_mean",
        value=0.2,
        observations=4,
    )
    type_metric = replace(
        token_metric,
        value=0.6,
        observations=2,
        matched_tokens=4,
        lexical_tokens=5,
        weighting="type",
    )
    content_metric = replace(
        token_metric,
        value=0.9,
        observations=3,
        analysis_view="content_words",
    )

    profiles = corpus_vad_profiles(
        (token_metric, type_metric, content_metric),
        total_works=1,
        analysis_views=("all_matched",),
        weightings=("type",),
    )

    assert len(profiles) == 1
    assert profiles[0].analysis_view == "all_matched"
    assert profiles[0].weighting == "type"
    assert profiles[0].token_weighted_volume_mean == pytest.approx(0.6)


def test_folder_decode_preserves_relative_paths_and_text() -> None:
    summary = decode_corpus_files(
        (
            ("Volume/Second poem.txt", b"Dark.\r\n"),
            ("Volume/First poem.txt", b"Bright.\n"),
        )
    )
    assert [item.relative_path for item in summary.files] == [
        "Volume/First poem.txt",
        "Volume/Second poem.txt",
    ]
    assert summary.files[1].original_text == "Dark.\r\n"
    assert summary.total_bytes == 15


def test_sqlite_import_versions_and_metadata_are_preserved(tmp_path) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    assert repository.schema_version() == 5
    project = repository.create_project("Jeffers test", researcher="Researcher")
    original = CorpusTextImport("Poem", "poem.txt", "book/poem.txt", "Bright.\n")
    first = repository.import_texts(project.project_id, (original,))[0]
    same = repository.import_texts(project.project_id, (original,))[0]
    assert same.text_version_id == first.text_version_id
    changed = repository.import_texts(
        project.project_id,
        (CorpusTextImport("Poem", "poem.txt", "book/poem.txt", "Bright!\n"),),
    )[0]
    assert changed.text_id == first.text_id
    assert changed.text_version_id != first.text_version_id
    assert changed.original_text == "Bright!\n"
    updated = repository.update_text_metadata(
        changed.text_id,
        title="Poem title",
        author="Robinson Jeffers",
        collection="Volume",
        date_label="1925",
        genre="lyric",
        notes="Editorial note",
        custom_metadata={"sequence": 3},
    )
    assert updated.collection == "Volume"
    assert updated.custom_metadata == {"sequence": 3}
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM text_versions WHERE text_id = ?", (first.text_id,)
        ).fetchone()[0] == 2


def test_completed_batch_persists_metrics_loads_and_unmatched_notes(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("Corpus")
    texts = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Long bright",
                "long.txt",
                "long.txt",
                " ".join(["Bright"] * 10) + " mystery.",
            ),
            CorpusTextImport("Short dark", "short.txt", "short.txt", "Dark."),
        ),
    )
    batch = repository.begin_corpus_batch(
        project.project_id,
        text_ids=(text.text_id for text in texts),
        lexicon_ids=("synthetic_vad_phase2",),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY.value,
        minimum_match_requirement=3,
    )
    for text in texts:
        repository.save_analysis(
            project.project_id,
            text.text_id,
            _workspace(text, preprocessor),
            batch_id=batch.batch_id,
        )
    assert repository.list_latest_metrics(project.project_id) == ()
    completed = repository.finish_corpus_batch(batch.batch_id)
    assert completed.status == "complete"
    with pytest.raises(ValueError, match="immutable"):
        repository.finish_corpus_batch(batch.batch_id)

    metrics = repository.list_latest_metrics(project.project_id)
    assert any(row.metric == "vad_absolute_midpoint_load" for row in metrics)
    assert any(
        row.metric == "vad_absolute_midpoint_load_per_observation"
        for row in metrics
    )
    assert any(
        row.metric == "vad_absolute_midpoint_load_per_100_observations"
        for row in metrics
    )
    assert any(
        row.metric == "vad_average_deviation_from_poem_mean"
        for row in metrics
    )
    assert {
        row.weighting
        for row in metrics
        if row.metric == "vad_average_deviation_from_poem_mean"
    } == {"token", "type"}
    valence = next(
        row
        for row in corpus_vad_profiles(metrics, total_works=2)
        if row.dimension == "valence" and row.analysis_view == "all_matched"
    )
    assert valence.matched_observations == 11
    assert valence.token_weighted_volume_mean == pytest.approx(9 / 11)
    assert valence.work_weighted_volume_mean == pytest.approx((0.875 + 0.25) / 2)
    assert abs(valence.work_minus_token_difference) > 0.25

    unmatched = repository.list_latest_unmatched(project.project_id)
    mystery = next(row for row in unmatched if row.normalized_form == "mystery")
    note_id = repository.upsert_unmatched_note(
        project_id=project.project_id,
        text_id=mystery.text_id,
        lexicon_id=mystery.lexicon_id,
        normalized_form=mystery.normalized_form,
        display_form=mystery.display_form,
        status="needs mapping",
        note="Check historical usage.",
        proposed_mapping="mystery",
    )
    refreshed = next(
        row
        for row in repository.list_latest_unmatched(project.project_id)
        if row.normalized_form == "mystery"
    )
    assert refreshed.note_id == note_id
    assert refreshed.status == "needs mapping"
    assert refreshed.note == "Check historical usage."


def test_corpus_service_runs_each_preserved_work_and_completes_batch(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("End-to-end corpus")
    repository.import_texts(
        project.project_id,
        (
            CorpusTextImport("First", "first.txt", "first.txt", "Bright blood."),
            CorpusTextImport("Second", "second.txt", "second.txt", "Dark night."),
        ),
    )
    batch = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=("nrc_vad_v1",),
        preprocessor=preprocessor,
    )
    assert batch.status == "complete"
    metrics = repository.list_latest_metrics(project.project_id)
    assert {row.title for row in metrics} == {"First", "Second"}
    assert any(row.metric == "vad_mean" and row.weighting == "token" for row in metrics)
    assert {row.analysis_view for row in metrics if row.metric == "vad_mean"} == {
        "all_matched",
        "stopwords_excluded",
        "content_words",
    }


def test_project_deletion_requires_exact_title_and_is_scoped(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    first = repository.create_project("Delete this project")
    second = repository.create_project("Keep this project")
    disposable_text = repository.import_texts(
        first.project_id,
        (CorpusTextImport("First", "first.txt", "first.txt", "Bright."),),
    )[0]
    repository.import_texts(
        second.project_id,
        (CorpusTextImport("Second", "second.txt", "second.txt", "Dark."),),
    )

    with pytest.raises(ValueError, match="exactly match"):
        repository.delete_project(first.project_id, confirmation_title="delete this project")

    batch = repository.begin_corpus_batch(
        first.project_id,
        text_ids=(disposable_text.text_id,),
        lexicon_ids=("synthetic_vad_phase2",),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY.value,
        minimum_match_requirement=1,
    )
    repository.save_analysis(
        first.project_id,
        disposable_text.text_id,
        _workspace(disposable_text, preprocessor),
        batch_id=batch.batch_id,
    )
    repository.finish_corpus_batch(batch.batch_id)
    repository.create_review_scenario(first.project_id, "Reviewed")

    repository.delete_project(
        first.project_id,
        confirmation_title="Delete this project",
    )

    assert [project.project_id for project in repository.list_projects()] == [
        second.project_id
    ]
    assert repository.list_texts(second.project_id)[0].title == "Second"
    with pytest.raises(KeyError, match="Unknown project"):
        repository.get_project(first.project_id)
    with sqlite3.connect(repository.database_path) as connection:
        for table in (
            "texts",
            "text_versions",
            "corpus_batches",
            "analysis_runs",
            "analysis_metrics",
            "review_scenarios",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == (
                1 if table in {"texts", "text_versions"} else 0
            )


def test_text_deletion_requires_exact_title_and_is_scoped(tmp_path) -> None:
    repository = ProjectRepository(tmp_path / "personal_corpus.sqlite3")
    project = repository.create_project("My Personal Corpus")
    repository.import_texts(
        project.project_id,
        (
            CorpusTextImport("Delete Me", "delete.txt", "delete.txt", "Bright."),
            CorpusTextImport("Keep Me", "keep.txt", "keep.txt", "Dark."),
        ),
    )
    delete_me, keep_me = repository.list_texts(project.project_id)
    if delete_me.title != "Delete Me":
        delete_me, keep_me = keep_me, delete_me

    with pytest.raises(ValueError, match="exactly match"):
        repository.delete_text(
            project.project_id,
            delete_me.text_id,
            confirmation_title="delete me",
        )

    repository.delete_text(
        project.project_id,
        delete_me.text_id,
        confirmation_title="Delete Me",
    )

    remaining = repository.list_texts(project.project_id)
    assert [text.text_id for text in remaining] == [keep_me.text_id]
    assert remaining[0].title == "Keep Me"
    with pytest.raises(KeyError, match="Unknown text"):
        repository.get_text(delete_me.text_id)
