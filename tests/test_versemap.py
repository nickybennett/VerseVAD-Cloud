from __future__ import annotations

import csv
import zipfile
from dataclasses import replace
from io import BytesIO

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.core.modules import ModuleInput
from versevad.exports.versemap import export_versemap_bundle
from versevad.models import PreprocessingMetadata, TextDocument
from versevad.phase2_validation import (
    phase2_synthetic_emotion_lexicon,
    phase2_synthetic_intensity_lexicon,
    phase2_synthetic_vad_lexicon,
)
from versevad.preprocessing import PreparedPoemPreprocessor, create_text_document
from versevad.versemap import (
    FEATURE_DEFINITIONS,
    PROFILE_BUILD_ID,
    PROFILE_ID,
    FeatureObservation,
    VerseMapProfile,
    analyze_profile,
    build_reference_model_bytes,
    extract_standard_profile,
    load_reference_index,
    standard_aoa_configuration,
    standard_concreteness_configuration,
    standard_frequency_configuration,
)
from versevad.versemap.model import (
    MODEL_FILENAME,
    POET_PROFILE_FILENAME,
    PROFILE_FILENAME,
)
from versevad.versemap.profile import BROWSER_VAD_DIAGNOSTIC_IDS
from versevad.versemap.reference import (
    PROFILE_DRAFT_FILENAME,
    _existing_browser_vad_rows,
)


def _profile_rows() -> list[dict[str, object]]:
    rows = []
    for poem_index, (poet_id, poet_name) in enumerate(
        (("poet-a", "Poet A"), ("poet-b", "Poet B"), ("poet-b", "Poet B")),
        start=1,
    ):
        row: dict[str, object] = {
            "poet_id": poet_id,
            "poet_name": poet_name,
            "poem_id": f"poem-{poem_index}",
            "title": f"Poem {poem_index}",
            "relative_path": f"{poet_name}/Poem {poem_index}.txt",
            "source_sha256": str(poem_index) * 64,
            "content_token_count": 50,
        }
        for feature_index, definition in enumerate(FEATURE_DEFINITIONS, start=1):
            row[definition.feature_id] = poem_index * 0.1 + feature_index * 0.01
            row[f"{definition.feature_id}__eligible"] = 50
            row[f"{definition.feature_id}__matched"] = 45
        rows.append(row)
    return rows


def test_browser_vad_diagnostics_resume_from_profile_checkpoint(tmp_path) -> None:
    checkpoint = tmp_path / PROFILE_DRAFT_FILENAME
    fields = (
        "profile_build_id",
        "poem_id",
        "source_sha256",
        *BROWSER_VAD_DIAGNOSTIC_IDS,
    )
    with checkpoint.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "profile_build_id": PROFILE_BUILD_ID,
                "poem_id": "checkpointed-poem",
                "source_sha256": "a" * 64,
                **{
                    metric_id: "0.125"
                    for metric_id in BROWSER_VAD_DIAGNOSTIC_IDS
                },
            }
        )

    rows = _existing_browser_vad_rows(tmp_path)

    assert ("checkpointed-poem", "a" * 64) in rows
    assert rows[("checkpointed-poem", "a" * 64)][
        BROWSER_VAD_DIAGNOSTIC_IDS[0]
    ] == "0.125"


def test_standard_profile_keeps_pinned_proper_noun_exclusion() -> None:
    assert standard_concreteness_configuration().exclude_proper_nouns is True
    assert standard_frequency_configuration().exclude_proper_nouns is True
    assert standard_aoa_configuration().exclude_proper_nouns is True


def test_reference_model_projects_and_exports_without_json(tmp_path) -> None:
    sound_terms = (
        "pronunciation",
        "syllable",
        "stress",
        "meter",
        "rhyme",
        "refrain",
        "alliteration",
        "assonance",
        "consonance",
        "phonolog",
    )
    assert all(
        not any(term in definition.feature_id for term in sound_terms)
        for definition in FEATURE_DEFINITIONS
    )

    profiles, poets, model, model_id = build_reference_model_bytes(
        _profile_rows(),
        reference_release_id="reference-test",
        reference_release_sha256="a" * 64,
    )
    (tmp_path / PROFILE_FILENAME).write_bytes(profiles)
    (tmp_path / POET_PROFILE_FILENAME).write_bytes(poets)
    (tmp_path / MODEL_FILENAME).write_bytes(model)
    index = load_reference_index(tmp_path)
    observations = tuple(
        FeatureObservation(
            definition.feature_id,
            0.2 + position * 0.01,
            eligible_count=20,
            matched_count=18,
        )
        for position, definition in enumerate(FEATURE_DEFINITIONS, start=1)
    )
    profile = VerseMapProfile(
        profile_id=PROFILE_ID,
        text_id="query",
        text_version_id="query-v1",
        title="Query poem",
        observations=observations,
        content_token_count=20,
    )
    document = TextDocument(
        text_id="query",
        title="Query poem",
        original_text="Query poem.",
        text_sha256="b" * 64,
        text_version_id="query-v1",
    )
    module_input = ModuleInput(
        document=document,
        tokens=(),
        preprocessing=PreprocessingMetadata(
            recipe_id="test-recipe",
            pipeline_name="test",
            pipeline_version="1",
            disabled_components=(),
        ),
    )

    result = analyze_profile(module_input, profile, index)
    bundle = export_versemap_bundle(result, text_title=document.title)

    assert index.model_id == model_id
    assert index.profile_build_id == PROFILE_BUILD_ID
    assert result.coordinate_1 is not None
    assert result.nearest_poems
    assert result.nearest_poets
    assert result.nearest_poems[0].distance >= 0
    assert "versemap_report.docx" in bundle
    assert all(not name.endswith(".json") for name in bundle)
    with zipfile.ZipFile(BytesIO(bundle["versemap_report.docx"])) as archive:
        assert "word/document.xml" in archive.namelist()


def test_standard_profile_uses_fixed_vad_and_emotion_sources(
    preprocessor,
) -> None:
    document = create_text_document(
        "versemap-profile", "VerseMap profile", "Fear joy dark night."
    )
    poem_document = preprocessor.process_document(document)
    prepared = PreparedPoemPreprocessor(poem_document)
    vad = analyze_lexicon(document, phase2_synthetic_vad_lexicon(), prepared)
    emotion = analyze_lexicon(
        document, phase2_synthetic_emotion_lexicon(), prepared
    )
    intensity = analyze_lexicon(
        document, phase2_synthetic_intensity_lexicon(), prepared
    )
    vad = replace(
        vad,
        lexicon_metadata=replace(
            vad.lexicon_metadata,
            lexicon_id="nrc_vad_v2_1",
        ),
    )
    emotion = replace(
        emotion,
        lexicon_metadata=replace(
            emotion.lexicon_metadata,
            lexicon_id="nrc_emotion_v0_92",
        ),
    )
    results = (vad, emotion, intensity)
    workspace = WorkspaceAnalysis(
        request=AnalysisRequest(
            project_name="Test",
            title=document.title,
            original_text=document.original_text,
            lexicon_ids=tuple(
                result.lexicon_metadata.lexicon_id for result in results
            ),
        ),
        document=document,
        results=results,
        comparison=compare_lexicons(results),
        poem_document=poem_document,
    )

    profile = extract_standard_profile(workspace)

    assert profile.profile_id == PROFILE_ID
    assert profile.content_token_count > 0
    assert profile.values["vad_valence_mean"] is not None
    assert (
        profile.browser_diagnostic_map[
            "vad_valence_absolute_midpoint_deviation_per_observation"
        ]
        is not None
    )
    assert (
        profile.browser_diagnostic_map[
            "vad_valence_average_deviation_from_poem_mean"
        ]
        is not None
    )
    assert profile.values["emotion_fear_proportion"] is not None
    assert profile.values["concreteness_mean"] is None
