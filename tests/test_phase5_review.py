from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.corpus import analyze_corpus, corpus_scenario_deltas
from versevad.db import CorpusTextImport, ProjectRepository
from versevad.db import repository as repository_module
from versevad.models import (
    MatchMethod,
    MatchSelection,
    PhrasePolicy,
    ReviewAction,
    ReviewRule,
    ReviewScope,
)
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import create_text_document


LEXICON_ID = "synthetic_vad_phase2"


def _rule(
    revision: str,
    action: ReviewAction,
    source: str,
    *,
    text_id: str,
    text_version_id: str,
    target: str = "",
    token_position: int | None = None,
    scope: ReviewScope = ReviewScope.WORK,
) -> ReviewRule:
    return ReviewRule(
        decision_id=f"decision-{revision}",
        decision_revision_id=revision,
        action=action,
        scope=scope,
        lexicon_id=LEXICON_ID,
        source_form=source,
        mapping_target=target,
        project_id="project-test",
        text_id=text_id if scope in {ReviewScope.WORK, ReviewScope.OCCURRENCE} else "",
        text_version_id=(
            text_version_id if scope == ReviewScope.OCCURRENCE else ""
        ),
        token_position=token_position if scope == ReviewScope.OCCURRENCE else None,
        risk_category="scholarly_review",
        rationale="Synthetic hand-checked decision.",
    )


def _workspace(text, preprocessor, *, rules=(), scenario_id="baseline", version_id=""):
    document = replace(
        create_text_document(text.text_id, text.title, text.original_text),
        text_version_id=text.text_version_id,
    )
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        preprocessor,
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
        scenario_id=scenario_id,
        scenario_version_id=version_id,
        review_rules=tuple(rules),
        minimum_match_requirement=1,
    )
    request = AnalysisRequest(
        project_name="Synthetic corpus",
        title=text.title,
        original_text=text.original_text,
        lexicon_ids=(LEXICON_ID,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
        minimum_match_requirement=1,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
        scenario_id=scenario_id,
        scenario_version_id=version_id,
        review_rules=tuple(rules),
    )
    return WorkspaceAnalysis(request, document, (result,), compare_lexicons((result,)))


def test_review_mapping_exclusion_and_flag_are_explicit_and_hand_calculated(
    preprocessor,
) -> None:
    document = create_text_document(
        "review-text",
        "Review fixture",
        "Bright mystery dark.",
    )
    rules = (
        _rule(
            "revision-map",
            ReviewAction.MAP,
            "mystery",
            text_id=document.text_id,
            text_version_id=document.text_version_id,
            target="bright",
        ),
        _rule(
            "revision-exclude",
            ReviewAction.EXCLUDE,
            "dark",
            text_id=document.text_id,
            text_version_id=document.text_version_id,
        ),
        _rule(
            "revision-flag",
            ReviewAction.FLAG,
            "bright",
            text_id=document.text_id,
            text_version_id=document.text_version_id,
        ),
    )
    lexicon = phase2_synthetic_vad_lexicon()
    original_entry_count = len(lexicon.entries)
    result = analyze_lexicon(
        document,
        lexicon,
        preprocessor,
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
        scenario_id="review-scenario",
        scenario_version_id="scenario-version-2",
        review_rules=rules,
        minimum_match_requirement=1,
    )

    mapped = next(
        match for match in result.matches if match.method == MatchMethod.USER_MAPPING
    )
    excluded = next(
        match
        for match in result.matches
        if match.selection == MatchSelection.EXCLUDED_REVIEW
    )
    assert mapped.matched_term == "bright"
    assert "revision-map" in mapped.reason
    assert excluded.matched_term == "dark"
    assert "revision-exclude" in excluded.reason
    assert result.coverage.approved_mapping_count == 1
    assert result.coverage.excluded_token_count == 1
    assert result.coverage.matched_token_count == 3
    assert result.coverage.unmatched_token_count == 0
    assert result.vad_summary is not None
    assert result.vad_summary.token_weighted_original.valence.mean == 8.0
    assert any("non-scoring review flag" in warning for warning in result.warnings)
    assert result.scenario_version_id == "scenario-version-2"
    assert result.review_rules == rules
    assert len(lexicon.entries) == original_entry_count


def test_schema_four_migration_creates_a_verified_version_three_backup(
    tmp_path,
) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        connection.executescript(repository_module._MIGRATION_1)
        connection.executescript(repository_module._MIGRATION_2)
        connection.executescript(repository_module._MIGRATION_3)
        connection.executemany(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, 'test')",
            ((1,), (2,), (3,)),
        )
    repository = ProjectRepository(database_path)
    assert repository.schema_version() == 5
    backup_path = tmp_path / "legacy.pre-v5.sqlite3"
    assert backup_path.is_file()
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0] == 3


def test_same_scope_conflicting_review_mappings_are_rejected(preprocessor) -> None:
    document = create_text_document("conflict", "Conflict", "Mystery.")
    rules = (
        _rule(
            "revision-one",
            ReviewAction.MAP,
            "mystery",
            text_id=document.text_id,
            text_version_id=document.text_version_id,
            target="bright",
        ),
        _rule(
            "revision-two",
            ReviewAction.MAP,
            "mystery",
            text_id=document.text_id,
            text_version_id=document.text_version_id,
            target="dark",
        ),
    )
    with pytest.raises(ValueError, match="Conflicting active review mappings"):
        analyze_lexicon(
            document,
            phase2_synthetic_vad_lexicon(),
            preprocessor,
            review_rules=rules,
        )


def test_scenario_decisions_are_versioned_revocable_and_restorable(tmp_path) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    assert repository.schema_version() == 5
    project = repository.create_project("Review project")
    text = repository.import_texts(
        project.project_id,
        (CorpusTextImport("Poem", "poem.txt", "poem.txt", "Mystery."),),
    )[0]
    scenario = repository.create_review_scenario(
        project.project_id,
        "Conservative reviewed analysis",
        description="Only hand-approved mappings.",
    )
    version_one = scenario.scenario_version_id
    assert scenario.version_number == 1
    assert scenario.decision_count == 0

    scenario = repository.create_review_decision(
        scenario.scenario_id,
        action=ReviewAction.MAP,
        scope=ReviewScope.WORK,
        lexicon_id=LEXICON_ID,
        source_form="Mystery",
        mapping_target="Bright",
        text_id=text.text_id,
        rationale="The edition modernizes this form to bright.",
        risk_category="unmatched",
    )
    version_two = scenario.scenario_version_id
    assert scenario.version_number == 2
    active = repository.list_review_decisions(version_two, active_only=True)
    assert len(active) == 1
    assert active[0].source_form == "mystery"
    assert active[0].mapping_target == "bright"
    rules = repository.review_rules_for_text(
        version_two,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
    )
    assert len(rules) == 1
    assert rules[0].action == ReviewAction.MAP

    scenario = repository.set_review_decision_state(
        scenario.scenario_id,
        active[0].decision_id,
        active=False,
        rationale="Withdraw pending further editorial evidence.",
    )
    assert scenario.version_number == 3
    assert repository.review_rules_for_text(
        scenario.scenario_version_id,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
    ) == ()
    assert len(
        repository.review_rules_for_text(
            version_two,
            text_id=text.text_id,
            text_version_id=text.text_version_id,
        )
    ) == 1

    restored = repository.restore_review_scenario_version(
        scenario.scenario_id,
        version_two,
        rationale="Editorial evidence confirmed the mapping.",
    )
    assert restored.version_number == 4
    assert len(
        repository.review_rules_for_text(
            restored.scenario_version_id,
            text_id=text.text_id,
            text_version_id=text.text_version_id,
        )
    ) == 1
    assert repository.list_review_decisions(version_one) == ()


def test_occurrence_scope_and_review_candidate_audit_are_preserved(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("Occurrence project")
    text = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Poem",
                "poem.txt",
                "poem.txt",
                "Mystery bright mystery.",
            ),
        ),
    )[0]
    baseline = _workspace(text, preprocessor)
    batch = repository.begin_corpus_batch(
        project.project_id,
        text_ids=(text.text_id,),
        lexicon_ids=(LEXICON_ID,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY.value,
        minimum_match_requirement=1,
    )
    repository.save_analysis(
        project.project_id,
        text.text_id,
        baseline,
        batch_id=batch.batch_id,
    )
    repository.finish_corpus_batch(batch.batch_id)
    candidates = repository.list_review_candidates(project.project_id)
    mysteries = [
        candidate
        for candidate in candidates
        if candidate.normalized_form == "mystery"
    ]
    assert len(mysteries) == 2
    assert {candidate.risk_category for candidate in mysteries} == {"unmatched"}
    assert repository.list_review_candidates(
        project.project_id,
        include_exact=True,
    )

    scenario = repository.create_review_scenario(project.project_id, "One occurrence")
    selected = mysteries[0]
    scenario = repository.create_review_decision(
        scenario.scenario_id,
        action=ReviewAction.MAP,
        scope=ReviewScope.OCCURRENCE,
        lexicon_id=LEXICON_ID,
        source_form=selected.normalized_form,
        mapping_target="bright",
        text_id=selected.text_id,
        text_version_id=selected.text_version_id,
        token_position=selected.token_position,
        rationale="Only this occurrence has the documented sense.",
        risk_category=selected.risk_category,
    )
    rules = repository.review_rules_for_text(
        scenario.scenario_version_id,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
    )
    reviewed = _workspace(
        text,
        preprocessor,
        rules=rules,
        scenario_id=scenario.scenario_id,
        version_id=scenario.scenario_version_id,
    )
    result = reviewed.results[0]
    assert result.coverage.approved_mapping_count == 1
    assert sum(
        match.method == MatchMethod.USER_MAPPING for match in result.matches
    ) == 1
    assert sum(
        match.selection == MatchSelection.UNMATCHED for match in result.matches
    ) == 1


def test_reviewed_batch_records_exact_scenario_and_can_compare_prior_batch(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("Comparison project")
    text = repository.import_texts(
        project.project_id,
        (CorpusTextImport("Poem", "poem.txt", "poem.txt", "Mystery bright."),),
    )[0]

    baseline_batch = repository.begin_corpus_batch(
        project.project_id,
        text_ids=(text.text_id,),
        lexicon_ids=(LEXICON_ID,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY.value,
        minimum_match_requirement=1,
    )
    repository.save_analysis(
        project.project_id,
        text.text_id,
        _workspace(text, preprocessor),
        batch_id=baseline_batch.batch_id,
    )
    baseline_batch = repository.finish_corpus_batch(baseline_batch.batch_id)

    scenario = repository.create_review_scenario(project.project_id, "Reviewed")
    scenario = repository.create_review_decision(
        scenario.scenario_id,
        action="map",
        scope="project",
        lexicon_id=LEXICON_ID,
        source_form="mystery",
        mapping_target="bright",
        rationale="Synthetic approved mapping.",
    )
    rules = repository.review_rules_for_text(
        scenario.scenario_version_id,
        text_id=text.text_id,
        text_version_id=text.text_version_id,
    )
    reviewed_batch = repository.begin_corpus_batch(
        project.project_id,
        text_ids=(text.text_id,),
        lexicon_ids=(LEXICON_ID,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY.value,
        minimum_match_requirement=1,
        scenario_version_id=scenario.scenario_version_id,
    )
    repository.save_analysis(
        project.project_id,
        text.text_id,
        _workspace(
            text,
            preprocessor,
            rules=rules,
            scenario_id=scenario.scenario_id,
            version_id=scenario.scenario_version_id,
        ),
        batch_id=reviewed_batch.batch_id,
    )
    reviewed_batch = repository.finish_corpus_batch(reviewed_batch.batch_id)

    assert reviewed_batch.scenario_version_id == scenario.scenario_version_id
    baseline_metrics = repository.list_metrics_for_batch(
        project.project_id,
        baseline_batch.batch_id,
    )
    reviewed_metrics = repository.list_metrics_for_batch(
        project.project_id,
        reviewed_batch.batch_id,
    )
    baseline_coverage = next(
        row
        for row in baseline_metrics
        if row.metric == "coverage" and row.analysis_view == "all_matched"
    )
    reviewed_coverage = next(
        row
        for row in reviewed_metrics
        if row.metric == "coverage" and row.analysis_view == "all_matched"
    )
    assert baseline_coverage.value == pytest.approx(0.5)
    assert reviewed_coverage.value == pytest.approx(1.0)
    deltas = corpus_scenario_deltas(baseline_metrics, reviewed_metrics)
    coverage_delta = next(
        row
        for row in deltas
        if row.metric == "coverage" and row.analysis_view == "all_matched"
    )
    assert coverage_delta.difference == pytest.approx(0.5)
    methodology = repository.latest_methodology(project.project_id)
    assert methodology["scenario_version_id"] == scenario.scenario_version_id
    assert len(methodology["review_decisions"]) == 1


def test_corpus_service_applies_a_pinned_review_scenario_end_to_end(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "versevad.sqlite3")
    project = repository.create_project("Live source review")
    repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Poem",
                "poem.txt",
                "poem.txt",
                "Bright mysteryword.",
            ),
        ),
    )
    baseline = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=("nrc_vad_v1",),
        minimum_match_requirement=1,
        preprocessor=preprocessor,
    )
    scenario = repository.create_review_scenario(project.project_id, "Approved mapping")
    scenario = repository.create_review_decision(
        scenario.scenario_id,
        action=ReviewAction.MAP,
        scope=ReviewScope.PROJECT,
        lexicon_id="nrc_vad_v1",
        source_form="mysteryword",
        mapping_target="bright",
        rationale="Synthetic integration decision.",
    )
    reviewed = analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=("nrc_vad_v1",),
        minimum_match_requirement=1,
        scenario_version_id=scenario.scenario_version_id,
        preprocessor=preprocessor,
    )
    assert baseline.scenario_version_id == ""
    assert reviewed.scenario_version_id == scenario.scenario_version_id
    baseline_metrics = repository.list_metrics_for_batch(
        project.project_id,
        baseline.batch_id,
    )
    reviewed_metrics = repository.list_metrics_for_batch(
        project.project_id,
        reviewed.batch_id,
    )
    baseline_coverage = next(
        row
        for row in baseline_metrics
        if row.metric == "coverage" and row.analysis_view == "all_matched"
    )
    reviewed_coverage = next(
        row
        for row in reviewed_metrics
        if row.metric == "coverage" and row.analysis_view == "all_matched"
    )
    assert baseline_coverage.value == pytest.approx(0.5)
    assert reviewed_coverage.value == pytest.approx(1.0)
    assert any(
        candidate.risk_category == "approved_mapping"
        for candidate in repository.list_review_candidates(project.project_id)
    )
