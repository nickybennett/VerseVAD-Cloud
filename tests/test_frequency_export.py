from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from pathlib import Path

from openpyxl import Workbook

from versevad.adapters.subtlex_us import REQUIRED_COLUMNS
from versevad.application import (
    AnalysisRequest,
    detailed_export_zip,
    run_workspace_analysis,
    scholar_summary_csv,
)
from versevad.core import ResourceSpec
from versevad.exports.frequency import (
    export_frequency_by_pos_csv,
    export_frequency_by_structure_csv,
    export_frequency_distribution_csv,
    export_frequency_summary_csv,
    export_frequency_terms_csv,
    export_frequency_token_audit_csv,
)
from versevad.lexical_semantic.frequency import (
    FrequencyConfiguration,
    FrequencyModule,
)


def _row(term: str, zipf_value: float) -> tuple[object, ...]:
    frequency_count = 10
    contextual_diversity_count = 8
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
        "Noun",
        frequency_count,
        1.0,
        "Noun",
        frequency_count,
        zipf_value,
    )


def _module(tmp_path: Path) -> FrequencyModule:
    source = tmp_path / "subtlex.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "out1g"
    sheet.append(REQUIRED_COLUMNS)
    sheet.append(_row("stone", 4.8))
    sheet.append(_row("idea", 5.2))
    workbook.save(source)
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    return FrequencyModule(
        tmp_path,
        resource_spec=ResourceSpec(
            resource_id="synthetic-frequency-export",
            display_name="Synthetic frequency export fixture",
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
            project_name="Frequency export",
            title="Synthetic",
            original_text="stone\n\nidea quorvax",
            lexicon_ids=(),
            include_frequency=True,
            frequency_configuration=FrequencyConfiguration(
                exclude_proper_nouns=False
            ),
        ),
        preprocessor=preprocessor,
        resource_root=tmp_path,
        frequency_module=_module(tmp_path),
    )


def test_frequency_exports_are_complete_and_keep_missing_values_empty(
    tmp_path: Path,
    preprocessor,
) -> None:
    workspace = _workspace(tmp_path, preprocessor)
    result = workspace.frequency
    assert result is not None

    assert result.module_result.module_name == "lexical_frequency"
    assert result.summary.token_coverage == 2 / 3

    summary_rows = list(
        csv.DictReader(
            io.StringIO(export_frequency_summary_csv(result).decode("utf-8-sig"))
        )
    )
    assert {row["metric"] for row in summary_rows} >= {
        "median_zipf",
        "mean_zipf",
        "population_standard_deviation",
        "interquartile_range",
        "matched_token_coverage",
        "matched_unique_word_coverage",
        "analysis_scope",
    }
    assert export_frequency_distribution_csv(result).startswith(b"\xef\xbb\xbf")
    assert export_frequency_by_structure_csv(result).startswith(b"\xef\xbb\xbf")
    assert export_frequency_by_pos_csv(result).startswith(b"\xef\xbb\xbf")
    assert export_frequency_terms_csv(result).startswith(b"\xef\xbb\xbf")
    audit_rows = list(
        csv.DictReader(
            io.StringIO(export_frequency_token_audit_csv(result).decode("utf-8-sig"))
        )
    )
    unmatched_csv = next(row for row in audit_rows if row["surface_form"] == "quorvax")
    assert unmatched_csv["zipf_value"] == ""
    assert unmatched_csv["match_method"] == "unmatched"


def test_frequency_only_workspace_and_full_bundle(
    tmp_path: Path,
    preprocessor,
) -> None:
    workspace = _workspace(tmp_path, preprocessor)

    assert not workspace.results
    assert not workspace.comparison.metrics
    assert workspace.frequency is not None
    summary = scholar_summary_csv(workspace).decode("utf-8-sig")
    assert "Median SUBTLEX-US Zipf frequency" in summary
    with zipfile.ZipFile(io.BytesIO(detailed_export_zip(workspace))) as bundle:
        names = set(bundle.namelist())
        assert names >= {
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/summary.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/distribution.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/by_structure.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/by_pos.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/terms.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/token_audit.csv",
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/report.docx",
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
            "04_AUDIT/03_LEXICAL_ACCESSIBILITY_AND_STYLE/frequency/report.docx"
        ).startswith(b"PK")
