import csv
import io
import zipfile
from dataclasses import replace

import pytest

import versevad.application as application_services
from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
)
from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import (
    AnalysisRequest,
    RESOURCE_DOWNLOAD_PAGES,
    TextImportError,
    WorkspaceAnalysis,
    WorkspaceAnalysisError,
    coverage_views,
    csv_reading_guide,
    decode_uploaded_text,
    detailed_export_zip,
    detailed_part_of_speech_views_for_tokens,
    emotion_association_views,
    emotion_intensity_views,
    match_views,
    installed_resource_readiness,
    lexical_trajectory_csv,
    lexical_trajectory_views,
    overview_notes,
    part_of_speech_views,
    part_of_speech_views_for_tokens,
    run_workspace_analysis,
    scholar_summary_csv,
    sentiment_association_views,
    unmatched_views,
    vad_part_of_speech_csv,
    vad_part_of_speech_views,
    vad_views,
)
from versevad.models import PhrasePolicy
from versevad.db import ProjectRepository
from versevad.phase2_validation import (
    phase2_synthetic_emotion_lexicon,
    phase2_synthetic_intensity_lexicon,
    phase2_synthetic_vad_lexicon,
)
from versevad.poetry_id import PoetryIDConfiguration
from versevad.preprocessing import (
    PreparedPoemPreprocessor,
    SpacyEnglishPreprocessor,
    create_text_document,
)
from versevad.prosody import (
    PronunciationConfiguration,
    PronunciationOverride,
)
from versevad.workspace_profiles import workspace_profile_metrics
from tests.test_pronunciation import _module as synthetic_pronunciation_module


@pytest.fixture
def synthetic_workspace(preprocessor) -> WorkspaceAnalysis:
    document = create_text_document(
        "friendly-summary", "Friendly summary", "Fear joy dark night."
    )
    poem_document = preprocessor.process_document(document)
    prepared = PreparedPoemPreprocessor(poem_document)
    results = (
        analyze_lexicon(document, phase2_synthetic_vad_lexicon(), prepared),
        analyze_lexicon(document, phase2_synthetic_emotion_lexicon(), prepared),
        analyze_lexicon(document, phase2_synthetic_intensity_lexicon(), prepared),
    )
    request = AnalysisRequest(
        project_name="Test workspace",
        title=document.title,
        original_text=document.original_text,
        lexicon_ids=tuple(result.lexicon_metadata.lexicon_id for result in results),
    )
    return WorkspaceAnalysis(
        request,
        document,
        results,
        compare_lexicons(results),
        poem_document,
    )


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def test_resource_readiness_reports_all_public_installation_contracts(
    tmp_path,
) -> None:
    source_root = tmp_path / "source_lexicons"
    resource_root = tmp_path / "resources"
    readiness = installed_resource_readiness(
        source_root=source_root,
        resource_root=resource_root,
    )

    assert len(readiness.all_statuses) == 13
    assert len(readiness.unavailable) == 13
    assert readiness.available_lexicon_ids == ()
    assert readiness.available_module_ids == ("lexical_style", "poetry_id")
    assert not readiness.pronunciation_available
    assert set(status.resource_id for status in readiness.all_statuses) == set(
        RESOURCE_DOWNLOAD_PAGES
    )


def test_resource_readiness_does_not_eagerly_parse_installed_datasets(
    tmp_path,
    monkeypatch,
) -> None:
    def reject_deep_validation(*args, **kwargs):
        del args, kwargs
        raise AssertionError(
            "Startup readiness must not parse a complete research dataset."
        )

    for module_type in (
        application_services.ConcretenessModule,
        application_services.FrequencyModule,
        application_services.AoAModule,
        application_services.SensorimotorModule,
        application_services.PronunciationModule,
    ):
        monkeypatch.setattr(
            module_type,
            "validate_resources",
            reject_deep_validation,
        )

    readiness = application_services.installed_resource_readiness(
        source_root=tmp_path / "source_lexicons",
        resource_root=tmp_path / "resources",
    )

    assert len(readiness.all_statuses) == 13
    assert len(readiness.unavailable) == 13


def test_text_file_import_preserves_unicode_and_line_endings() -> None:
    content = "Stone’s edge\r\nSecond line.\r\n".encode("utf-8")
    assert decode_uploaded_text("poem.TXT", content) == content.decode("utf-8")


def test_text_file_import_rejects_unsupported_or_invalid_files() -> None:
    with pytest.raises(TextImportError, match="plain-text"):
        decode_uploaded_text("poem.docx", b"not a Word file")
    with pytest.raises(TextImportError, match="UTF-8"):
        decode_uploaded_text("poem.txt", b"\xff\xfe")
    with pytest.raises(TextImportError, match="ordinary plain-text"):
        decode_uploaded_text("poem.txt", b"abc\x00def")


def test_workspace_analysis_preserves_text_and_runs_selected_real_source(preprocessor) -> None:
    original = "A bit of bright night.\n"
    request = AnalysisRequest(
        project_name="Private reading",
        title="Working title",
        original_text=original,
        lexicon_ids=("nrc_vad_v2_1",),
        phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
    )
    workspace = run_workspace_analysis(request, preprocessor=preprocessor)
    assert workspace.document.original_text == original
    assert workspace.poem_document is not None
    assert workspace.poem_document.source is workspace.document
    assert workspace.poem_document.tokens == workspace.results[0].tokens
    assert len(workspace.results) == 1
    assert workspace.results[0].lexicon_validation.source_sha256.startswith("42c71881")
    assert workspace.results[0].coverage.phrase_match_count >= 1


def test_lexical_trajectory_keeps_sources_separate_and_preserves_lines(
    preprocessor,
) -> None:
    workspace = run_workspace_analysis(
        AnalysisRequest(
            project_name="Trajectory",
            title="Two lines",
            original_text="bright stone\nnight dream",
            lexicon_ids=("nrc_vad_v1", "nrc_vad_v2_1"),
            include_concreteness=True,
        ),
        preprocessor=preprocessor,
    )

    points = lexical_trajectory_views(
        workspace,
        lexicon_id="nrc_vad_v2_1",
        analysis_view="All matched tokens",
    )
    assert [point.line_number for point in points] == [1, 2]
    assert {point.lexicon_id for point in points} == {"nrc_vad_v2_1"}
    assert any(point.valence_mean is not None for point in points)
    concrete_point = next(
        point
        for point in points
        if point.concreteness_mean_source_scale is not None
    )
    assert concrete_point.concreteness_mean_normalized == pytest.approx(
        (concrete_point.concreteness_mean_source_scale - 1) / 4
    )
    exported = _csv_rows(lexical_trajectory_csv(workspace))
    assert {row["lexicon_id"] for row in exported} == {
        "nrc_vad_v1",
        "nrc_vad_v2_1",
    }
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        assert (
            "04_AUDIT/06_CROSS_MODULE_ANALYSIS/lexical_trajectory/values.csv"
            in bundle.namelist()
        )


def test_workspace_poetry_id_reuses_completed_vad_and_has_no_json_export(
    preprocessor,
) -> None:
    request = AnalysisRequest(
        project_name="PoetryID workspace",
        title="Profile evidence",
        original_text="joy love peace light happy calm strong",
        lexicon_ids=("nrc_vad_v1",),
        include_poetry_id=True,
        poetry_id_configuration=PoetryIDConfiguration(
            analysis_views=("all_matched", "stopwords_excluded"),
        ),
    )

    workspace = run_workspace_analysis(request, preprocessor=preprocessor)

    assert workspace.poetry_id is not None
    assert workspace.poetry_id.status == "complete"
    assert {row.source_analysis_id for row in workspace.poetry_id.assignments} == {
        workspace.results[0].analysis_id
    }
    assert {row.weighting_mode for row in workspace.poetry_id.assignments} == {
        "token",
        "type",
    }
    assert {row.analysis_view for row in workspace.poetry_id.assignments} == {
        "all_matched",
        "stopwords_excluded",
    }
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        poetry_id_files = {
            name
            for name in bundle.namelist()
            if name.startswith("04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/")
        }
        assert poetry_id_files == {
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/summary.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/neighbors.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/lexical_character.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/methodology.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/archetype_map.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/vad_scales.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/manifest.csv",
            "04_AUDIT/05_COMPARATIVE_PROFILES/poetry_id/report.docx",
        }
        assert not any(name.endswith(".json") for name in poetry_id_files)


def test_workspace_preprocesses_once_for_multiple_lexicons() -> None:
    class CountingPreprocessor:
        def __init__(self) -> None:
            self.delegate = SpacyEnglishPreprocessor()
            self.document_calls = 0
            self.token_calls = 0

        @property
        def metadata(self):
            return self.delegate.metadata

        def process_document(self, document):
            self.document_calls += 1
            return self.delegate.process_document(document)

        def process(self, document):
            self.token_calls += 1
            return self.delegate.process(document)

    processor = CountingPreprocessor()
    request = AnalysisRequest(
        project_name="Shared processing",
        title="One representation",
        original_text="Bright night.",
        lexicon_ids=("nrc_vad_v1", "nrc_emotion_v0_92"),
    )

    workspace = run_workspace_analysis(request, preprocessor=processor)

    assert processor.document_calls == 1
    assert processor.token_calls == 0
    assert workspace.poem_document is not None
    assert all(
        result.tokens == workspace.poem_document.tokens
        for result in workspace.results
    )


def test_workspace_requires_title_and_text_but_runs_resource_free_metrics(
    preprocessor,
) -> None:
    base = dict(project_name="Temporary", title="Poem", original_text="Stone.")
    with pytest.raises(WorkspaceAnalysisError, match="title"):
        run_workspace_analysis(
            AnalysisRequest(**{**base, "title": "", "lexicon_ids": ("nrc_vad_v1",)}),
            preprocessor=preprocessor,
        )
    with pytest.raises(WorkspaceAnalysisError, match="Paste a poem"):
        run_workspace_analysis(
            AnalysisRequest(**{**base, "original_text": "", "lexicon_ids": ("nrc_vad_v1",)}),
            preprocessor=preprocessor,
        )
    resource_free = run_workspace_analysis(
        AnalysisRequest(**base, lexicon_ids=()), preprocessor=preprocessor
    )
    assert resource_free.results == ()
    assert resource_free.vader_sentiment is not None
    assert resource_free.readability is not None
    summary_sections = {
        row["section"] for row in _csv_rows(scholar_summary_csv(resource_free))
    }
    assert {"VADER sentiment", "Readability"} <= summary_sections
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(resource_free))) as bundle:
        names = set(bundle.namelist())
        assert {
            "04_AUDIT/01_AFFECT/vader/summary.csv",
            "04_AUDIT/01_AFFECT/vader/sentences.csv",
            "04_AUDIT/01_AFFECT/vader/report.docx",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/readability/summary.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/readability/word_audit.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/readability/report.docx",
        } <= names
        assert "04_AUDIT/06_CROSS_MODULE_ANALYSIS/lexical_trajectory/values.csv" not in names
        assert not any(name.endswith(".json") for name in names)


def test_workspace_name_is_optional_for_temporary_analysis(preprocessor) -> None:
    workspace = run_workspace_analysis(
        AnalysisRequest(
            project_name="",
            title="Untitled workspace",
            original_text="Stone.",
            lexicon_ids=(),
            include_lexical_style=True,
        ),
        preprocessor=preprocessor,
    )

    assert workspace.request.project_name == ""
    assert workspace.document.title == "Untitled workspace"


def test_readable_views_keep_constructs_and_denominators_separate(
    synthetic_workspace,
) -> None:
    coverage = coverage_views(synthetic_workspace)
    assert len(coverage) == 3
    assert all(row.lexical_tokens == 4 for row in coverage)
    vad = vad_views(synthetic_workspace)
    assert len(vad) == 2
    assert {row.analysis_view for row in vad} == {
        "All matched tokens",
        "Stopwords excluded",
    }
    assert vad[0].normalized_valence is not None
    assert vad[0].original_scale == "1 to 9"
    associations = emotion_association_views(synthetic_workspace)
    assert {row.category for row in associations} <= {
        "anger",
        "anticipation",
        "disgust",
        "fear",
        "joy",
        "sadness",
        "surprise",
        "trust",
    }
    assert not {"positive", "negative"} & {row.category for row in associations}
    fear = next(row for row in associations if row.category == "fear")
    assert fear.token_count == 1
    assert fear.rate_per_lexical_token == pytest.approx(0.25)
    sentiments = sentiment_association_views(synthetic_workspace)
    assert {row.category for row in sentiments} == {"positive", "negative"}
    pos_rows = part_of_speech_views(synthetic_workspace)
    assert sum(row.token_count for row in pos_rows) == 4
    assert sum(row.share_of_lexical_tokens for row in pos_rows) == pytest.approx(1.0)
    assert all(row.lexical_token_denominator == 4 for row in pos_rows)
    assert all(row.category != "Proper Noun" for row in pos_rows)
    intensities = emotion_intensity_views(synthetic_workspace)
    fear_intensity = next(row for row in intensities if row.category == "fear")
    assert fear_intensity.mean_matched_intensity == pytest.approx(0.6)
    assert any("not expected to sum" in note for note in overview_notes(synthetic_workspace))


def test_part_of_speech_profile_merges_common_and_proper_nouns(
    synthetic_workspace,
) -> None:
    source_tokens = synthetic_workspace.results[0].tokens[:2]
    tokens = (
        replace(
            source_tokens[0],
            part_of_speech="NOUN",
            normalized_form="river",
        ),
        replace(
            source_tokens[1],
            part_of_speech="PROPN",
            normalized_form="raven",
        ),
    )
    rows = part_of_speech_views_for_tokens(tokens)
    assert len(rows) == 1
    assert rows[0].tag == "NOUN + PROPN"
    assert rows[0].category == "Noun"
    assert rows[0].token_count == 2
    assert rows[0].share_of_lexical_tokens == 1.0
    assert rows[0].unique_type_count == 2
    detailed = detailed_part_of_speech_views_for_tokens(tokens)
    assert {row.tag for row in detailed} == {"NOUN", "PROPN"}
    assert {row.category for row in detailed} == {"Common Noun", "Proper Noun"}


def test_part_of_speech_profile_merges_main_and_auxiliary_verbs(
    synthetic_workspace,
) -> None:
    source_tokens = synthetic_workspace.results[0].tokens[:2]
    tokens = (
        replace(
            source_tokens[0],
            part_of_speech="VERB",
            normalized_form="sing",
        ),
        replace(
            source_tokens[1],
            part_of_speech="AUX",
            normalized_form="be",
        ),
    )
    rows = part_of_speech_views_for_tokens(tokens)
    assert len(rows) == 1
    assert rows[0].tag == "VERB + AUX"
    assert rows[0].category == "Verb"
    assert rows[0].token_count == 2
    assert rows[0].share_of_lexical_tokens == 1.0
    detailed = detailed_part_of_speech_views_for_tokens(tokens)
    assert {row.tag for row in detailed} == {"VERB", "AUX"}
    assert {row.category for row in detailed} == {
        "Main Verb",
        "Auxiliary or Copular Verb",
    }


def test_vad_part_of_speech_profile_reports_token_and_type_weighted_means(
    preprocessor,
) -> None:
    document = create_text_document(
        "vad-pos-weighting",
        "VAD POS weighting",
        "dark dark bright night.",
    )
    poem_document = preprocessor.process_document(document)
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        PreparedPoemPreprocessor(poem_document),
    )
    pos_by_form = {"dark": "ADJ", "bright": "ADJ", "night": "NOUN"}
    tokens = tuple(
        replace(
            token,
            part_of_speech=pos_by_form.get(
                token.normalized_form,
                token.part_of_speech,
            ),
        )
        for token in result.tokens
    )
    result = replace(result, tokens=tokens)
    poem_document = replace(poem_document, tokens=tokens)
    request = AnalysisRequest(
        project_name="Test workspace",
        title=document.title,
        original_text=document.original_text,
        lexicon_ids=(result.lexicon_metadata.lexicon_id,),
    )
    workspace = WorkspaceAnalysis(
        request,
        document,
        (result,),
        compare_lexicons((result,)),
        poem_document,
    )

    rows = vad_part_of_speech_views(workspace)
    adjective = next(
        row
        for row in rows
        if row.analysis_view == "All matched tokens" and row.tag == "ADJ"
    )
    assert adjective.matched_observations == 3
    assert adjective.matched_types == 2
    assert adjective.matched_token_occurrences == 3
    assert adjective.eligible_token_occurrences == 3
    assert adjective.lexical_coverage == 1.0
    assert adjective.token_weighted_valence == pytest.approx(
        (0.25 + 0.25 + 0.875) / 3
    )
    assert adjective.type_weighted_valence == pytest.approx(
        (0.25 + 0.875) / 2
    )
    assert adjective.token_weighted_arousal == pytest.approx(
        (0.625 + 0.625 + 0.5) / 3
    )
    assert adjective.type_weighted_arousal == pytest.approx(
        (0.625 + 0.5) / 2
    )
    assert adjective.token_weighted_dominance == pytest.approx(
        (0.375 + 0.375 + 0.75) / 3
    )
    assert adjective.type_weighted_dominance == pytest.approx(
        (0.375 + 0.75) / 2
    )

    exported = _csv_rows(vad_part_of_speech_csv(workspace))
    exported_adjective = next(
        row
        for row in exported
        if row["analysis_view"] == "All matched tokens"
        and row["source_pos_tags"] == "ADJ"
    )
    assert float(exported_adjective["token_weighted_mean_valence_0_1"]) == (
        pytest.approx(adjective.token_weighted_valence)
    )
    assert float(exported_adjective["type_weighted_mean_valence_0_1"]) == (
        pytest.approx(adjective.type_weighted_valence)
    )


def test_vad_part_of_speech_profile_keeps_cross_pos_phrases_separate(
    preprocessor,
) -> None:
    document = create_text_document(
        "vad-pos-phrase",
        "VAD POS phrase",
        "dark night.",
    )
    poem_document = preprocessor.process_document(document)
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        PreparedPoemPreprocessor(poem_document),
    )
    tokens = tuple(
        replace(
            token,
            part_of_speech=(
                "ADJ"
                if token.normalized_form == "dark"
                else "NOUN"
                if token.normalized_form == "night"
                else token.part_of_speech
            ),
        )
        for token in result.tokens
    )
    result = replace(result, tokens=tokens)
    poem_document = replace(poem_document, tokens=tokens)
    request = AnalysisRequest(
        project_name="Test workspace",
        title=document.title,
        original_text=document.original_text,
        lexicon_ids=(result.lexicon_metadata.lexicon_id,),
    )
    workspace = WorkspaceAnalysis(
        request,
        document,
        (result,),
        compare_lexicons((result,)),
        poem_document,
    )

    mixed = next(
        row
        for row in vad_part_of_speech_views(workspace)
        if row.analysis_view == "All matched tokens" and row.tag == "MIXED"
    )
    assert mixed.category == "Mixed-POS Phrase"
    assert mixed.matched_observations == 1
    assert mixed.matched_types == 1
    assert mixed.matched_token_occurrences == 2
    assert mixed.eligible_token_occurrences is None
    assert mixed.lexical_coverage is None
    assert mixed.phrase_observations == 1
    assert mixed.token_weighted_valence == pytest.approx(0.125)
    assert mixed.type_weighted_valence == pytest.approx(0.125)
    unmatched_adjective = next(
        row
        for row in vad_part_of_speech_views(workspace)
        if row.analysis_view == "All matched tokens" and row.tag == "ADJ"
    )
    assert unmatched_adjective.matched_observations == 0
    assert unmatched_adjective.token_weighted_valence is None
    assert unmatched_adjective.type_weighted_valence is None


def test_match_and_unmatched_views_are_plain_language_drilldowns(synthetic_workspace) -> None:
    matches = match_views(synthetic_workspace)
    phrase = next(row for row in matches if row.surface == "dark night" and row.status == "included")
    assert phrase.method == "exact_phrase"
    assert "V " in phrase.value
    unmatched = unmatched_views(synthetic_workspace)
    assert any(row.surface.casefold() == "joy" for row in unmatched)
    assert all(row.example_context for row in unmatched)


def test_scholar_summary_and_guide_are_excel_friendly(synthetic_workspace) -> None:
    summary = scholar_summary_csv(synthetic_workspace)
    guide = csv_reading_guide()
    assert summary.startswith(b"\xef\xbb\xbf")
    assert guide.startswith(b"\xef\xbb\xbf")
    summary_rows = _csv_rows(summary)
    assert {row["section"] for row in summary_rows} >= {
        "Coverage",
        "Part of speech",
        "Normalized VAD",
        "Cumulative normative lexical load",
        "Stopword sensitivity",
        "Emotion association",
        "Sentiment association",
        "Emotion intensity",
    }
    vad_metrics = [
        row["metric"] for row in summary_rows if row["section"] == "Normalized VAD"
    ]
    assert any("token-weighted" in metric for metric in vad_metrics)
    assert any("type-weighted" in metric for metric in vad_metrics)
    guide_rows = _csv_rows(guide)
    assert guide_rows[0]["file"] == "scholar_summary.csv"
    assert any(row["file"] == "phase2_match_audit.csv" for row in guide_rows)
    assert any(row["file"] == "vad_by_part_of_speech.csv" for row in guide_rows)


def test_detailed_download_starts_with_friendly_files_and_retains_audit(
    synthetic_workspace,
) -> None:
    archive = detailed_export_zip(synthetic_workspace)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        names = set(bundle.namelist())
        assert "01_REPORTS/Analysis_Report.docx" in names
        assert "01_REPORTS/Coverage_and_Data_Quality.docx" in names
        assert "03_MASTER_DATA/Master_Metrics.csv" in names
        assert "04_AUDIT/08_REPRODUCIBILITY/scholar_summary.csv" in names
        assert "04_AUDIT/08_REPRODUCIBILITY/csv_reading_guide.csv" in names
        assert "04_AUDIT/01_AFFECT/lexical_match_audit.csv" in names
        assert "04_AUDIT/08_REPRODUCIBILITY/affect_lexicon_manifest.csv" in names
        assert "04_AUDIT/07_PROCESSING_AUDIT/source.csv" in names
        assert "04_AUDIT/07_PROCESSING_AUDIT/tokens.csv" in names
        assert "04_AUDIT/07_PROCESSING_AUDIT/configuration.csv" in names
        assert "04_AUDIT/06_CROSS_MODULE_ANALYSIS/vad_by_part_of_speech.csv" in names
        assert not any(name.endswith((".json", ".xlsx")) for name in names)
        assert {
            "05_REPRODUCIBILITY/REPRODUCIBILITY_README.txt",
            "05_REPRODUCIBILITY/FILE_INVENTORY.csv",
        } <= names
        source = _csv_rows(bundle.read("04_AUDIT/07_PROCESSING_AUDIT/source.csv"))[0]
        assert source["original_text"] == "Fear joy dark night."
        configuration = _csv_rows(
            bundle.read("04_AUDIT/07_PROCESSING_AUDIT/configuration.csv")
        )[0]
        assert configuration["preserve_original_text"] == "True"
        coverage = _csv_rows(bundle.read("04_AUDIT/07_PROCESSING_AUDIT/coverage.csv"))[0]
        assert int(coverage["total_token_count"]) > 0
        structure = _csv_rows(bundle.read("04_AUDIT/07_PROCESSING_AUDIT/structure.csv"))
        assert any(unit["kind"] == "line" for unit in structure)
        inventory = _csv_rows(
            bundle.read("05_REPRODUCIBILITY/FILE_INVENTORY.csv")
        )
        assert {row["path"] for row in inventory} <= names
        metric_rows = _csv_rows(bundle.read("03_MASTER_DATA/Master_Metrics.csv"))
        assert metric_rows
        assert {row["export_schema_version"] for row in metric_rows} == {"3.0"}
        assert {row["analysis_mode"] for row in metric_rows} == {"single_poem"}
        assert all(row["metric_id"] for row in metric_rows)


def test_current_view_export_applies_scope_exception_only_to_target_module(
    synthetic_workspace,
) -> None:
    archive = detailed_export_zip(
        synthetic_workspace,
        use_cache=False,
        profile_selection=ProfileSelection(),
        export_mode="current_view",
        visible_section="Affective Evidence",
        module_scope_overrides=("emotion_association", "emotion_intensity"),
    )

    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        rows = _csv_rows(bundle.read("03_MASTER_DATA/Selected_Profiles.csv"))
        override_rows = _csv_rows(
            bundle.read("05_REPRODUCIBILITY/Module_Scope_Overrides.csv")
        )

    vad_rows = [row for row in rows if row["module_id"] == "vad"]
    emotion_rows = [
        row
        for row in rows
        if row["module_id"] in {"emotion_association", "emotion_intensity"}
    ]
    assert vad_rows and {row["scope"] for row in vad_rows} == {"STOPWORD_EXCLUDED"}
    assert emotion_rows and {row["scope"] for row in emotion_rows} == {"CONTENT_WORDS"}
    assert {row["module_id"] for row in override_rows} == {
        "emotion_association",
        "emotion_intensity",
    }


def test_profile_semantics_suppress_invalid_generic_statistics(
    synthetic_workspace,
) -> None:
    rows = workspace_profile_metrics(synthetic_workspace)
    association_rows = [
        row for row in rows if row.module_id == "emotion_association"
    ]
    assert association_rows
    assert all(row.value is not None for row in association_rows)
    assert all(row.population_standard_deviation is None for row in association_rows)
    assert all(row.cumulative_value is None for row in association_rows)
    assert all(row.value_per_100_observations is None for row in association_rows)

    intensity_rows = [row for row in rows if row.module_id == "emotion_intensity"]
    assert intensity_rows
    assert any(row.cumulative_value is not None for row in intensity_rows)
    assert all(row.value_per_100_observations is None for row in intensity_rows)

    vad_rows = [row for row in rows if row.module_id == "vad"]
    assert vad_rows
    assert all(row.cumulative_value is None for row in vad_rows)
    assert any(row.absolute_midpoint_load is not None for row in vad_rows)


def test_type_weighted_association_rate_uses_type_denominator(
    synthetic_workspace,
) -> None:
    profile = AnalysisProfile(LexicalScope.ALL_LEXICAL, AggregationWeighting.TYPE)
    row = next(
        item
        for item in workspace_profile_metrics(synthetic_workspace)
        if item.module_id == "emotion_association"
        and item.metric_id == "fear_association"
        and item.profile == profile
    )
    # The category rate remains the metric value, while the attached Coverage
    # object describes the entire NRC Emotion resource. In this fixture, one
    # of four eligible lexical types is fear-associated, whereas two of four
    # eligible types are matched by the resource at all.
    assert row.value == pytest.approx(1 / 4)
    assert row.coverage.type_coverage == pytest.approx(2 / 4)
    assert row.value != pytest.approx(row.coverage.type_coverage)


def test_persisted_type_weighted_metrics_use_type_metadata(
    synthetic_workspace,
) -> None:
    profile = AnalysisProfile(LexicalScope.ALL_LEXICAL, AggregationWeighting.TYPE)
    expected = next(
        item
        for item in workspace_profile_metrics(synthetic_workspace)
        if item.module_id == "emotion_association"
        and item.metric_id == "fear_association"
        and item.profile == profile
    )
    persisted = next(
        row
        for row in ProjectRepository._metric_rows(synthetic_workspace)
        if row[3] == "all_matched"
        and row[4] == "emotion_association_fear_association_mean"
        and row[7] == "type"
    )
    assert "eligible types matched" in persisted[9]
    assert persisted[11] == expected.observation_count
    assert persisted[12] == expected.coverage.matched_type_count
    assert persisted[13] == expected.coverage.eligible_type_count
    assert persisted[14] == pytest.approx(expected.coverage.type_coverage)


def test_workspace_can_run_pronunciation_without_an_affective_lexicon(
    tmp_path,
    preprocessor,
) -> None:
    request = AnalysisRequest(
        project_name="Pronunciation-only workspace",
        title="Stage 5",
        original_text="stone rings\nstone quorvax",
        lexicon_ids=(),
        include_pronunciation=True,
    )
    workspace = run_workspace_analysis(
        request,
        preprocessor=preprocessor,
        resource_root=tmp_path,
        pronunciation_module=synthetic_pronunciation_module(tmp_path),
    )

    assert workspace.results == ()
    assert workspace.pronunciation is not None
    assert workspace.pronunciation.summary.resolved_token_count == 3
    summary_rows = _csv_rows(scholar_summary_csv(workspace))
    assert any(
        row["section"] == "Pronunciation and prosody foundation"
        for row in summary_rows
    )
    mean_line_row = next(
        row
        for row in summary_rows
        if row["metric"] == "Mean syllables per complete line"
    )
    assert float(mean_line_row["value"]) == pytest.approx(2.0)
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert "04_AUDIT/04_SOUND_AND_FORM/pronunciation/summary.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/pronunciation/lines.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/pronunciation/token_audit.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/pronunciation/report.docx" in names
        assert not any(name.endswith(".json") for name in names)


def test_workspace_can_run_meter_and_automatically_include_pronunciation(
    tmp_path,
    preprocessor,
) -> None:
    tetrameter = "the stone the stone the stone the stone"
    request = AnalysisRequest(
        project_name="Meter-only workspace",
        title="Stage 6",
        original_text="\n".join((tetrameter,) * 4),
        lexicon_ids=(),
        include_meter=True,
    )

    workspace = run_workspace_analysis(
        request,
        preprocessor=preprocessor,
        resource_root=tmp_path,
        pronunciation_module=synthetic_pronunciation_module(tmp_path),
    )

    assert workspace.results == ()
    assert workspace.pronunciation is not None
    assert workspace.meter is not None
    assert workspace.meter.summary.closest_candidate_label == "Iambic tetrameter"
    assert workspace.meter.summary.closest_candidate_kind == (
        "fixed pattern and foot count"
    )
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/summary.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/candidates.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/schemes.csv" not in names
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/lines.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/alignment_operations.csv" in names
        assert "04_AUDIT/04_SOUND_AND_FORM/meter/report.docx" in names
        assert not any(name.endswith(".json") for name in names)


def test_workspace_can_run_phonology_and_automatically_include_pronunciation(
    tmp_path,
    preprocessor,
) -> None:
    request = AnalysisRequest(
        project_name="Rhyme-only workspace",
        title="Stage 7",
        original_text="bright cat\nsilver night\nsoftly hat\nstone bright",
        lexicon_ids=(),
        include_phonology=True,
    )

    workspace = run_workspace_analysis(
        request,
        preprocessor=preprocessor,
        resource_root=tmp_path,
        pronunciation_module=synthetic_pronunciation_module(tmp_path),
    )

    assert workspace.results == ()
    assert workspace.pronunciation is not None
    assert workspace.phonology is not None
    assert workspace.phonology.summary.whole_poem_rhyme_scheme == "ABAB"
    summary_rows = _csv_rows(scholar_summary_csv(workspace))
    assert any(
        row["section"] == "Rhyme and phonological patterns"
        and row["metric"] == "Whole-poem end-rhyme scheme"
        for row in summary_rows
    )
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert {
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/summary.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/stanzas.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/lines.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/pairs.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/internal.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/sounds.csv",
            "04_AUDIT/04_SOUND_AND_FORM/rhyme_and_sound/report.docx",
        } <= names


def test_approved_session_pronunciation_updates_all_enabled_sound_dependencies(
    tmp_path,
    preprocessor,
) -> None:
    text = "quorvax stone\nstone quorvax"
    module = synthetic_pronunciation_module(tmp_path)
    unresolved = run_workspace_analysis(
        AnalysisRequest(
            project_name="Unresolved G2P review",
            title="Before approval",
            original_text=text,
            lexicon_ids=(),
            include_inherited_form=True,
            analysis_cache_enabled=False,
        ),
        preprocessor=preprocessor,
        resource_root=tmp_path,
        pronunciation_module=module,
    )
    approved = run_workspace_analysis(
        AnalysisRequest(
            project_name="Approved G2P review",
            title="After approval",
            original_text=text,
            lexicon_ids=(),
            pronunciation_configuration=PronunciationConfiguration(
                overrides=(
                    PronunciationOverride(
                        term="quorvax",
                        phones=("K", "W", "AO1", "R", "V", "AE0", "K", "S"),
                        note=(
                            "User approved the provisional G2P candidate "
                            "for this session."
                        ),
                    ),
                )
            ),
            include_inherited_form=True,
            analysis_cache_enabled=False,
        ),
        preprocessor=preprocessor,
        resource_root=tmp_path,
        pronunciation_module=module,
    )

    assert unresolved.pronunciation is not None
    assert unresolved.meter is not None
    assert unresolved.phonology is not None
    assert unresolved.inherited_form is not None
    assert approved.pronunciation is not None
    assert approved.meter is not None
    assert approved.phonology is not None
    assert approved.inherited_form is not None
    assert unresolved.pronunciation.summary.unmatched_token_count == 2
    assert unresolved.pronunciation.summary.complete_line_count == 0
    assert unresolved.meter.summary.line_coverage == 0.0
    assert unresolved.phonology.summary.ending_coverage == 0.5
    assert approved.pronunciation.summary.unmatched_token_count == 0
    assert approved.pronunciation.summary.complete_line_count == 2
    assert approved.meter.summary.line_coverage == 1.0
    assert approved.phonology.summary.ending_coverage == 1.0
    assert (
        unresolved.inherited_form.module_result.result_id
        != approved.inherited_form.module_result.result_id
    )


def test_workspace_can_run_lexical_style_without_external_resources(
    tmp_path,
    preprocessor,
) -> None:
    request = AnalysisRequest(
        project_name="Lexical-style-only workspace",
        title="Lexical style",
        original_text="red blue red\ngreen blue\n\nyellow red",
        lexicon_ids=(),
        include_lexical_style=True,
    )

    workspace = run_workspace_analysis(
        request,
        preprocessor=preprocessor,
        resource_root=tmp_path,
    )

    assert workspace.results == ()
    assert workspace.lexical_style is not None
    assert workspace.lexical_style.summary.lexical_token_count == 7
    assert [
        item.word_count for item in workspace.lexical_style.line_summaries
    ] == [3, 2, 0, 2]
    summary_rows = _csv_rows(scholar_summary_csv(workspace))
    assert any(
        row["section"] == "Lexical diversity and word counts"
        and row["metric"] == "Lexical token count"
        for row in summary_rows
    )
    summary_by_metric = {row["metric"]: row for row in summary_rows}
    assert summary_by_metric["Average words per nonblank line"]["value"] == str(
        7 / 3
    )
    assert summary_by_metric[
        "Population SD of words per nonblank line"
    ]["value"] == str((2 / 9) ** 0.5)
    assert summary_by_metric["Median words per nonblank line"]["value"] == "2.0"
    assert summary_by_metric["Average words per stanza"]["value"] == "3.5"
    assert summary_by_metric["Population SD of words per stanza"]["value"] == "1.5"
    assert summary_by_metric["Median words per stanza"]["value"] == "3.5"
    assert summary_by_metric["Average nonblank lines per stanza"]["value"] == "1.5"
    assert (
        summary_by_metric["Population SD of nonblank lines per stanza"]["value"]
        == "0.5"
    )
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        assert {
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/summary.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/word_lengths.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/lines.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/stanzas.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/token_audit.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/lexical_style/report.docx",
        } <= set(bundle.namelist())
