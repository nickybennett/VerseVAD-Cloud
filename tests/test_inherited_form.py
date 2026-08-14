from __future__ import annotations

import io
import zipfile

from versevad.application import (
    AnalysisRequest,
    detailed_export_zip,
    run_workspace_analysis,
)
from versevad.core import ModuleInput
from versevad.db import CorpusTextImport, ProjectRepository
from versevad.inherited_form import (
    FORM_PROFILES,
    InheritedFormConfiguration,
    InheritedFormEngine,
)
from versevad.phonology import PhonologicalModule
from versevad.preprocessing import create_text_document
from versevad.prosody import (
    MeterModule,
    PronunciationConfiguration,
    PronunciationOverride,
)
from tests.test_pronunciation import _module


def _module_input(preprocessor, text: str, name: str = "fixture") -> ModuleInput:
    poem = preprocessor.process_document(
        create_text_document(name, name.title(), text)
    )
    return ModuleInput.from_poem_document(poem)


def _structural_result(preprocessor, text: str, name: str = "fixture"):
    return InheritedFormEngine().analyze(
        _module_input(preprocessor, text, name),
        None,
        None,
        None,
    )


def _villanelle_text() -> str:
    return "\n\n".join(
        (
            "bright cat\nsilver stone\nsoftly night",
            "motion love\nsilver stone\nbright cat",
            "ocean true\nsilver stone\nsoftly night",
            "rings move\nsilver stone\nbright cat",
            "alice sing\nsilver stone\nsoftly night",
            "wind permit\nsilver stone\nbright cat\nsoftly night",
        )
    )


def _sestina_text() -> str:
    seed = ("bright", "cat", "night", "stone", "love", "motion")
    orders = (
        (0, 1, 2, 3, 4, 5),
        (5, 0, 4, 1, 3, 2),
        (2, 5, 3, 0, 1, 4),
        (4, 2, 1, 5, 0, 3),
        (3, 4, 0, 2, 5, 1),
        (1, 3, 5, 4, 2, 0),
    )
    stanzas = [
        "\n".join(f"the {seed[index]}" for index in order)
        for order in orders
    ]
    stanzas.append("cat stone love\nmotion night\nthe bright")
    return "\n\n".join(stanzas)


def _pantoum_text() -> str:
    return "\n\n".join(
        (
            "bright cat\nsilver night\nsoftly stone\nmotion love",
            "silver night\nocean true\nmotion love\nalice sings",
            "ocean true\nwind moves\nalice sings\nbright cat",
        )
    )


def test_registry_contains_comprehensive_unique_source_backed_profiles() -> None:
    assert len(FORM_PROFILES) == 169
    assert len({profile.profile_id for profile in FORM_PROFILES}) == len(
        FORM_PROFILES
    )
    assert all(profile.tooltip_definition for profile in FORM_PROFILES)
    assert all(profile.source_urls for profile in FORM_PROFILES)
    assert {profile.assessment_mode for profile in FORM_PROFILES} == {
        "automatic",
        "partial",
        "manual",
    }
    assert any("not a general definition" in profile.definition for profile in FORM_PROFILES)


def test_villanelle_refrain_and_stanza_architecture_rank_first(
    preprocessor,
) -> None:
    result = _structural_result(
        preprocessor,
        _villanelle_text(),
        "villanelle-fixture",
    )

    assert result.best_candidate is not None
    assert result.best_candidate.profile_id == "villanelle"
    assert result.best_candidate.consistency == 1.0
    assert result.best_candidate.required_evidence_coverage == 1.0
    assert "Traditionally:" in result.best_candidate.tooltip
    assert "Agreement:" in result.best_candidate.tooltip


def test_line_edge_unicode_whitespace_does_not_change_form_ranking(
    preprocessor,
) -> None:
    clean_text = _villanelle_text()
    indented_text = "\n".join(
        (
            line
            if not line
            else f"\t\u00a0\u2003{line}\u2009\u00a0"
        )
        for line in clean_text.split("\n")
    )

    clean = _structural_result(preprocessor, clean_text, "villanelle-clean")
    indented = _structural_result(
        preprocessor,
        indented_text,
        "villanelle-indented",
    )

    assert indented.best_candidate is not None
    assert clean.best_candidate is not None
    assert indented.best_candidate.profile_id == clean.best_candidate.profile_id
    assert indented.best_candidate.consistency == clean.best_candidate.consistency
    assert (
        indented.best_candidate.required_evidence_coverage
        == clean.best_candidate.required_evidence_coverage
    )


def test_sestina_rotation_and_envoi_rank_first(preprocessor) -> None:
    result = _structural_result(
        preprocessor,
        _sestina_text(),
        "sestina-fixture",
    )

    assert result.best_candidate is not None
    assert result.best_candidate.profile_id == "sestina"
    features = {
        item.feature_id: item
        for item in result.best_candidate.feature_evidence
    }
    assert features["sestina_rotation"].score == 1.0
    assert features["sestina_envoi"].score == 1.0


def test_pantoum_ordered_repetition_ranks_first(preprocessor) -> None:
    result = _structural_result(
        preprocessor,
        _pantoum_text(),
        "pantoum-fixture",
    )

    assert result.best_candidate is not None
    assert result.best_candidate.profile_id == "pantoum"
    repetition = next(
        item
        for item in result.best_candidate.feature_evidence
        if item.feature_id == "pantoum_repetition"
    )
    assert repetition.score == 1.0


def test_missing_required_syllable_evidence_is_not_a_strict_haiku_match(
    preprocessor,
) -> None:
    result = _structural_result(
        preprocessor,
        "red sun on the hill\nthe blue moon is over us\nbirds sing in the rain",
        "haiku-missing-evidence",
    )
    candidate = next(
        item
        for item in result.candidates
        if item.profile_id == "english_575_haiku"
    )

    assert candidate.consistency == 1.0
    assert candidate.evidence_coverage < 0.5
    assert candidate.required_evidence_coverage < 0.7
    assert not candidate.suggested
    assert result.best_candidate is None


def test_shakespearean_fixture_consumes_existing_meter_and_rhyme_layers(
    tmp_path,
    preprocessor,
) -> None:
    endings = (
        "bright",
        "cat",
        "night",
        "hat",
        "love",
        "ring",
        "dove",
        "sing",
        "sit",
        "true",
        "fit",
        "blue",
        "stone",
        "known",
    )
    lines = [
        " ".join(("the stone",) * 4 + (f"the {ending}",))
        for ending in endings
    ]
    module_input = _module_input(
        preprocessor,
        "\n".join(lines),
        "shakespearean-fixture",
    )
    configuration = PronunciationConfiguration(
        overrides=(
            PronunciationOverride("the", ("DH", "AH0"), "Resolve function-word stress."),
            PronunciationOverride("dove", ("D", "AH1", "V"), "Synthetic rhyme fixture."),
            PronunciationOverride("ring", ("R", "IH1", "NG"), "Synthetic rhyme fixture."),
            PronunciationOverride("fit", ("F", "IH1", "T"), "Synthetic rhyme fixture."),
            PronunciationOverride("blue", ("B", "L", "UW1"), "Synthetic rhyme fixture."),
            PronunciationOverride("known", ("N", "OW1", "N"), "Synthetic rhyme fixture."),
        )
    )
    pronunciation = _module(tmp_path).analyze_detailed(
        module_input,
        configuration,
    )
    meter = MeterModule().analyze_detailed(module_input, pronunciation)
    phonology = PhonologicalModule().analyze_detailed(
        module_input,
        pronunciation,
    )
    result = InheritedFormEngine().analyze(
        module_input,
        pronunciation,
        meter,
        phonology,
    )

    assert phonology.summary.whole_poem_rhyme_scheme == "ABABCDCDEFEFGG"
    assert meter.summary.closest_candidate_label == "Iambic pentameter"
    assert result.best_candidate is not None
    assert result.best_candidate.profile_id == "elizabethan_sonnet"
    assert result.best_candidate.consistency > 0.95
    assert result.best_candidate.confidence in {"moderate", "high"}


def test_near_miss_remains_graded_not_binary(preprocessor) -> None:
    lines = _villanelle_text().splitlines()
    lines[6] = "a deliberately altered refrain"
    result = _structural_result(
        preprocessor,
        "\n".join(lines),
        "modified-villanelle",
    )
    candidate = next(
        item for item in result.candidates if item.profile_id == "villanelle"
    )

    assert 0 < candidate.consistency < 1
    assert candidate.classification in {
        "Strongly conforming",
        "Modified",
        "Form-derived",
        "Suggestive resemblance",
        "No inherited-form match",
    }


def test_profile_subset_configuration_is_explicit(preprocessor) -> None:
    result = InheritedFormEngine().analyze(
        _module_input(preprocessor, _pantoum_text(), "profile-subset"),
        None,
        None,
        None,
        InheritedFormConfiguration(profile_ids=("pantoum", "villanelle")),
    )

    assert [item.profile_id for item in result.candidates] == [
        "pantoum",
        "villanelle",
    ]


def test_manual_profiles_remain_inspectable_but_never_suggested(
    preprocessor,
) -> None:
    result = _structural_result(
        preprocessor,
        "A bright opening\nA second line\nA final line",
        "manual-profile-guard",
    )
    manual_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.assessment_mode == "manual"
    ]

    assert manual_candidates
    assert not any(candidate.suggested for candidate in manual_candidates)
    assert all(
        candidate.classification == "Manual confirmation required"
        for candidate in manual_candidates
    )
    assert any(
        evidence.feature_id == "manual_requirement"
        and evidence.score is None
        and evidence.evidence_coverage == 0.0
        for candidate in manual_candidates
        for evidence in candidate.feature_evidence
    )


def test_workspace_selection_runs_shared_dependencies_and_complete_export(
    tmp_path,
    preprocessor,
) -> None:
    workspace = run_workspace_analysis(
        AnalysisRequest(
            project_name="Inherited form integration",
            title="Villanelle integration",
            original_text=_villanelle_text(),
            lexicon_ids=(),
            include_inherited_form=True,
            analysis_cache_enabled=False,
        ),
        preprocessor=preprocessor,
        pronunciation_module=_module(tmp_path),
    )

    assert workspace.pronunciation is not None
    assert workspace.meter is not None
    assert workspace.phonology is not None
    assert workspace.inherited_form is not None
    assert workspace.inherited_form.best_candidate is not None
    assert workspace.inherited_form.best_candidate.profile_id == "villanelle"
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as archive:
        assert {
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/summary.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/candidates.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/features.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/profiles.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/methodology.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/manifest.csv",
            "04_AUDIT/04_SOUND_AND_FORM/inherited_form/report.docx",
        } <= set(archive.namelist())
        assert not any(name.endswith(".json") for name in archive.namelist())


def test_project_persistence_keeps_form_metrics_and_artifacts_per_poem(
    tmp_path,
    preprocessor,
) -> None:
    repository = ProjectRepository(tmp_path / "inherited-form.sqlite3")
    project = repository.create_project("Inherited form corpus")
    imported = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Villanelle",
                "villanelle.txt",
                "villanelle.txt",
                _villanelle_text(),
            ),
        ),
    )[0]
    pronunciation_root = tmp_path / "cmudict"
    pronunciation_root.mkdir()
    workspace = run_workspace_analysis(
        AnalysisRequest(
            project_name=project.title,
            title=imported.title,
            original_text=imported.original_text,
            lexicon_ids=(),
            text_id=imported.text_id,
            text_version_id=imported.text_version_id,
            include_inherited_form=True,
            analysis_cache_enabled=False,
        ),
        preprocessor=preprocessor,
        pronunciation_module=_module(pronunciation_root),
    )

    run_id = repository.save_analysis(
        project.project_id,
        imported.text_id,
        workspace,
    )
    results = repository.list_latest_module_results(project.project_id)
    assert {item.module_name for item in results} >= {
        "pronunciation_prosody_foundation",
        "candidate_meter_and_rhythmic_regularity",
        "rhyme_and_phonological_patterns",
        "inherited_form",
    }
    metrics = repository.list_latest_module_metrics(project.project_id)
    assert any(
        item.metric_id == "inherited_form.best_candidate_name"
        and item.value == "Villanelle"
        for item in metrics
    )
    artifacts = repository.list_module_artifacts(run_id, "inherited_form")
    assert {item.filename for item in artifacts} == {
        "inherited_form_summary.csv",
        "inherited_form_candidates.csv",
        "inherited_form_features.csv",
        "inherited_form_profiles.csv",
        "inherited_form_methodology.csv",
        "inherited_form_manifest.csv",
        "inherited_form_report.docx",
    }
