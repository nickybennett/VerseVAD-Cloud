from __future__ import annotations

import io
import zipfile

import pytest

from versevad.exports.archive_contract import (
    COMPLETE_AUDIT_ANALYSIS_REPORT_PATH,
    COMPLETE_AUDIT_SELECTED_PROFILE_PATH,
    ExportArchiveContractError,
    FLAT_ANALYSIS_REPORT_PATH,
    FLAT_SELECTED_PROFILE_PATH,
    read_analysis_report,
    read_selected_profile_metrics,
)


@pytest.mark.parametrize(
    ("report_path", "profile_path"),
    (
        (FLAT_ANALYSIS_REPORT_PATH, FLAT_SELECTED_PROFILE_PATH),
        (
            COMPLETE_AUDIT_ANALYSIS_REPORT_PATH,
            COMPLETE_AUDIT_SELECTED_PROFILE_PATH,
        ),
    ),
)
def test_archive_readers_support_both_export_layouts(
    report_path: str,
    profile_path: str,
) -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(report_path, b"report")
        archive.writestr(profile_path, b"metrics")

    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
        assert read_analysis_report(archive) == b"report"
        assert read_selected_profile_metrics(archive) == b"metrics"


def test_missing_report_raises_descriptive_contract_error() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("unrelated.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
        with pytest.raises(
            ExportArchiveContractError,
            match="comprehensive analysis report",
        ):
            read_analysis_report(archive)
