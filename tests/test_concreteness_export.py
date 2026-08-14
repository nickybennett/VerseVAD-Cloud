from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path

from openpyxl import Workbook

from versevad.application import (
    AnalysisRequest,
    detailed_export_zip,
    run_workspace_analysis,
    scholar_summary_csv,
)
from versevad.core import ResourceSpec
from versevad.exports.concreteness import (
    export_concreteness_by_pos_csv,
    export_concreteness_by_structure_csv,
    export_concreteness_summary_csv,
    export_concreteness_terms_csv,
    export_concreteness_token_audit_csv,
)
from versevad.lexical_semantic.concreteness import ConcretenessModule
from versevad.lexical_semantic.concreteness import ConcretenessConfiguration


HEADER = (
    "Word",
    "Bigram",
    "Conc.M",
    "Conc.SD",
    "Unknown",
    "Total",
    "Percent_known",
    "SUBTLEX",
)


def _module(tmp_path: Path) -> ConcretenessModule:
    source = tmp_path / "ratings.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(HEADER)
    sheet.append(("stone", 0, 4.8, 0.4, 0, 30, 1.0, 100))
    sheet.append(("idea", 0, 1.2, 0.7, 0, 30, 1.0, 100))
    workbook.save(source)
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    return ConcretenessModule(
        tmp_path,
        resource_spec=ResourceSpec(
            resource_id="synthetic-concreteness-export",
            display_name="Synthetic export fixture",
            relative_path=source.name,
            version="synthetic-v1",
            accepted_sha256=(checksum,),
            citation="Constructed test fixture.",
            license_notice="Synthetic test data.",
        ),
    )


def _workspace(tmp_path: Path, preprocessor):
    return run_workspace_analysis(
        AnalysisRequest(
            project_name="Concreteness export",
            title="Synthetic",
            original_text="stone\n\nidea quorvax",
            lexicon_ids=(),
            include_concreteness=True,
            concreteness_configuration=ConcretenessConfiguration(
                exclude_proper_nouns=False
            ),
        ),
        preprocessor=preprocessor,
        resource_root=tmp_path,
        concreteness_module=_module(tmp_path),
    )


def test_concreteness_exports_are_complete_and_keep_missing_values_empty(
    tmp_path: Path,
    preprocessor,
) -> None:
    workspace = _workspace(tmp_path, preprocessor)
    result = workspace.concreteness
    assert result is not None

    assert result.module_result.module_name == "concreteness"
    assert result.summary.token_coverage == 2 / 3

    summary_rows = list(
        csv.DictReader(
            io.StringIO(export_concreteness_summary_csv(result).decode("utf-8-sig"))
        )
    )
    assert {row["metric"] for row in summary_rows} >= {
        "mean",
        "median",
        "population_standard_deviation",
        "interquartile_range",
        "rated_token_coverage",
        "rated_unique_word_coverage",
    }
    assert export_concreteness_by_structure_csv(result).startswith(b"\xef\xbb\xbf")
    assert export_concreteness_by_pos_csv(result).startswith(b"\xef\xbb\xbf")
    assert export_concreteness_terms_csv(result).startswith(b"\xef\xbb\xbf")
    audit_rows = list(
        csv.DictReader(
            io.StringIO(export_concreteness_token_audit_csv(result).decode("utf-8-sig"))
        )
    )
    unmatched_csv = next(row for row in audit_rows if row["surface_form"] == "quorvax")
    assert unmatched_csv["rating"] == ""
    assert unmatched_csv["match_method"] == "unmatched"


def test_concreteness_only_workspace_and_full_bundle(
    tmp_path: Path,
    preprocessor,
) -> None:
    workspace = _workspace(tmp_path, preprocessor)

    assert not workspace.results
    assert not workspace.comparison.metrics
    assert workspace.concreteness is not None
    summary = scholar_summary_csv(workspace).decode("utf-8-sig")
    assert "Concreteness" in summary
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert names >= {
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/summary.csv",
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/by_structure.csv",
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/by_pos.csv",
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/terms.csv",
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/token_audit.csv",
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/report.docx",
            "04_AUDIT/07_PROCESSING_AUDIT/source.csv",
            "04_AUDIT/07_PROCESSING_AUDIT/tokens.csv",
            "01_REPORTS/Analysis_Report.docx",
        }
        assert not any(name.startswith("phase2_") for name in names)
        assert not any(name.endswith((".json", ".xlsx")) for name in names)
        assert {
            "05_REPRODUCIBILITY/REPRODUCIBILITY_README.txt",
            "05_REPRODUCIBILITY/FILE_INVENTORY.csv",
        } <= names
        assert bundle.read(
            "04_AUDIT/02_EXPERIENCE_AND_IMAGERY/concreteness/report.docx"
        ).startswith(b"PK")
