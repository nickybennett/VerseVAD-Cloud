"""Stable member names and readers for VerseVAD analysis export archives."""

from __future__ import annotations

import zipfile
from collections.abc import Iterable, Sequence


FLAT_ANALYSIS_REPORT_PATH = "VerseVAD_analysis_report.docx"
COMPLETE_AUDIT_ANALYSIS_REPORT_PATH = (
    "01_REPORTS/Analysis_Report.docx"
)
ANALYSIS_REPORT_PATHS = (
    COMPLETE_AUDIT_ANALYSIS_REPORT_PATH,
    "00_START_HERE/VerseVAD_Analysis_Report.docx",
    FLAT_ANALYSIS_REPORT_PATH,
)

FLAT_SELECTED_PROFILE_PATH = "profile_metrics_selected.csv"
COMPLETE_AUDIT_SELECTED_PROFILE_PATH = (
    "03_MASTER_DATA/Master_Metrics.csv"
)
SELECTED_PROFILE_PATHS = (
    "03_MASTER_DATA/Selected_Profiles.csv",
    COMPLETE_AUDIT_SELECTED_PROFILE_PATH,
    "05_COMPARATIVE_PROFILES/profile_metrics_selected.csv",
    FLAT_SELECTED_PROFILE_PATH,
)
MASTER_METRICS_PATHS = (
    "03_MASTER_DATA/Master_Metrics.csv",
    "corpus_vad_metrics.csv",
    "profile_metrics_all_compatible.csv",
    "profile_metrics_selected.csv",
)


class ExportArchiveContractError(KeyError):
    """Raised when a required artifact is absent from an export archive."""


def resolve_archive_member(
    member_names: Iterable[str],
    candidates: Sequence[str],
    *,
    artifact_label: str,
) -> str:
    """Return the first supported member path present in an archive."""

    available = set(member_names)
    for candidate in candidates:
        if candidate in available:
            return candidate
    expected = ", ".join(repr(candidate) for candidate in candidates)
    raise ExportArchiveContractError(
        f"Export archive does not contain {artifact_label}; expected one of {expected}."
    )


def read_analysis_report(archive: zipfile.ZipFile) -> bytes:
    """Read the narrative report from either supported bundle layout."""

    path = resolve_archive_member(
        archive.namelist(),
        ANALYSIS_REPORT_PATHS,
        artifact_label="the comprehensive analysis report",
    )
    return archive.read(path)


def read_selected_profile_metrics(archive: zipfile.ZipFile) -> bytes:
    """Read selected-profile metrics from either supported bundle layout."""

    path = resolve_archive_member(
        archive.namelist(),
        SELECTED_PROFILE_PATHS,
        artifact_label="the selected-profile metrics",
    )
    return archive.read(path)


def read_master_metrics(archive: zipfile.ZipFile) -> bytes:
    """Read the authoritative machine table from a standardized audit."""

    path = resolve_archive_member(
        archive.namelist(),
        MASTER_METRICS_PATHS,
        artifact_label="the canonical master metrics table",
    )
    return archive.read(path)


__all__ = [
    "ANALYSIS_REPORT_PATHS",
    "COMPLETE_AUDIT_ANALYSIS_REPORT_PATH",
    "COMPLETE_AUDIT_SELECTED_PROFILE_PATH",
    "ExportArchiveContractError",
    "FLAT_ANALYSIS_REPORT_PATH",
    "FLAT_SELECTED_PROFILE_PATH",
    "MASTER_METRICS_PATHS",
    "SELECTED_PROFILE_PATHS",
    "read_analysis_report",
    "read_master_metrics",
    "read_selected_profile_metrics",
    "resolve_archive_member",
]
