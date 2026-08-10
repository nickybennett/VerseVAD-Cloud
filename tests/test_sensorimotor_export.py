from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from versevad.application import (
    AnalysisRequest,
    detailed_export_zip,
    run_workspace_analysis,
    scholar_summary_csv,
)
from versevad.core import ModuleInput
from versevad.exports.sensorimotor import (
    export_sensorimotor_bundle,
    export_sensorimotor_observations_csv,
    export_sensorimotor_summary_csv,
    export_sensorimotor_unmatched_csv,
)
from versevad.lexical_semantic.sensorimotor import SensorimotorConfiguration
from versevad.preprocessing import create_text_document

from test_sensorimotor import _module


def _result(tmp_path: Path, preprocessor):
    poem = preprocessor.process_document(
        create_text_document(
            "sensorimotor-export",
            "Sensorimotor export",
            "stone\ndark night quorvax",
        )
    )
    return _module(tmp_path).analyze_detailed(
        ModuleInput.from_poem_document(poem),
        SensorimotorConfiguration(
            exclude_proper_nouns=False,
            minimum_match_requirement=1,
        ),
    )


def test_sensorimotor_csv_exports_are_utf8_and_keep_unmatched_separate(
    tmp_path: Path,
    preprocessor,
) -> None:
    result = _result(tmp_path, preprocessor)

    summary = export_sensorimotor_summary_csv(result)
    observations = export_sensorimotor_observations_csv(result)
    unmatched = export_sensorimotor_unmatched_csv(result)

    assert summary.startswith(b"\xef\xbb\xbf")
    summary_rows = list(
        csv.DictReader(io.StringIO(summary.decode("utf-8-sig")))
    )
    assert {row["metric"] for row in summary_rows} >= {
        "mean",
        "population_standard_deviation",
        "cumulative_load",
        "load_per_100_observations",
        "matched_token_coverage",
    }
    observation_rows = list(
        csv.DictReader(io.StringIO(observations.decode("utf-8-sig")))
    )
    assert {row["matched_source_term"] for row in observation_rows} == {
        "stone",
        "dark night",
    }
    unmatched_rows = list(
        csv.DictReader(io.StringIO(unmatched.decode("utf-8-sig")))
    )
    assert [row["surface_form"] for row in unmatched_rows] == ["quorvax"]


def test_sensorimotor_bundle_contains_csv_and_narrative_docx(
    tmp_path: Path,
    preprocessor,
) -> None:
    bundle = export_sensorimotor_bundle(
        _result(tmp_path, preprocessor),
        text_title="Synthetic",
    )

    assert set(bundle) == {
        "sensorimotor_summary.csv",
        "sensorimotor_dominant_dimensions.csv",
        "sensorimotor_by_structure.csv",
        "sensorimotor_terms.csv",
        "sensorimotor_observations.csv",
        "sensorimotor_unmatched.csv",
        "sensorimotor_manifest.csv",
        "sensorimotor_report.docx",
    }
    assert bundle["sensorimotor_report.docx"].startswith(b"PK")
    assert not any(name.endswith((".json", ".txt", ".xlsx")) for name in bundle)


def test_sensorimotor_workspace_and_complete_audit_bundle(
    tmp_path: Path,
    preprocessor,
) -> None:
    workspace = run_workspace_analysis(
        AnalysisRequest(
            project_name="Sensorimotor export",
            title="Synthetic",
            original_text="stone\ndark night quorvax",
            lexicon_ids=(),
            include_sensorimotor=True,
            sensorimotor_configuration=SensorimotorConfiguration(
                exclude_proper_nouns=False,
                minimum_match_requirement=1,
            ),
        ),
        preprocessor=preprocessor,
        resource_root=tmp_path,
        sensorimotor_module=_module(tmp_path),
    )

    assert workspace.sensorimotor is not None
    assert "Sensorimotor imagery and embodiment" in scholar_summary_csv(
        workspace
    ).decode("utf-8-sig")
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert names >= {
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/summary.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/dominant_dimensions.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/by_structure.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/terms.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/observations.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/unmatched.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/manifest.csv",
            "02_EXPERIENCE_AND_IMAGERY/sensorimotor/report.docx",
            "00_START_HERE/VerseVAD_Analysis_Report.docx",
        }
