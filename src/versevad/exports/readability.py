"""CSV and narrative Word exports for transparent readability formulas."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict

from versevad.exports.docx_report import build_narrative_report_from_summary_csv
from versevad.exports.module_manifest import export_module_manifest_csv
from versevad.lexical_semantic.readability import ReadabilityAnalysisResult


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_readability_summary_csv(result: ReadabilityAnalysisResult) -> bytes:
    summary = result.summary
    rows = []
    notes = {
        "flesch_reading_ease": (
            "Conventionally higher means easier prose; poetry can violate the "
            "formula's assumptions."
        ),
        "flesch_kincaid_grade": "Approximate U.S. grade-formula score, not a reader requirement.",
        "gunning_fog_index": "Uses words with three or more estimated syllables.",
        "automated_readability_index": "Uses alphabetic characters, words, and sentences.",
        "coleman_liau_index": "Uses alphabetic letters and sentences per 100 words.",
        "smog_index": (
            f"Missing below {result.configuration.smog_minimum_sentences} sentences."
        ),
    }
    for metric, value in asdict(summary).items():
        rows.append(
            {
                "section": (
                    "readability_formula"
                    if metric in notes
                    else "counting_and_coverage"
                ),
                "metric": metric,
                "value": "" if value is None else value,
                "unit_or_scale": (
                    "formula score"
                    if metric in notes
                    else "explicitly named count, mean, method, or proportion"
                ),
                "denominator": "complete preserved text",
                "note": notes.get(metric, ""),
            }
        )
    return _csv_bytes(
        [
            "section",
            "metric",
            "value",
            "unit_or_scale",
            "denominator",
            "note",
        ],
        rows,
    )


def export_readability_word_audit_csv(
    result: ReadabilityAnalysisResult,
) -> bytes:
    return _csv_bytes(
        [
            "token_id",
            "token_position",
            "line_number",
            "surface_form",
            "lookup_form",
            "alphabetic_character_count",
            "syllable_count",
            "syllable_method",
            "pronunciation_candidate_count",
            "is_polysyllabic",
        ],
        [asdict(item) for item in result.word_audit],
    )


def export_readability_bundle(
    result: ReadabilityAnalysisResult,
    *,
    text_title: str = "",
) -> dict[str, bytes]:
    bundle = {
        "readability_summary.csv": export_readability_summary_csv(result),
        "readability_word_audit.csv": export_readability_word_audit_csv(result),
        "readability_manifest.csv": export_module_manifest_csv(result),
    }
    bundle["readability_report.docx"] = (
        build_narrative_report_from_summary_csv(
            "readability",
            bundle["readability_summary.csv"],
            companion_csv_files=tuple(bundle),
            text_title=text_title,
            text_id=result.module_result.text_id,
            result_id=result.module_result.result_id,
            warnings=tuple(
                warning.message for warning in result.module_result.warnings
            ),
        )
    )
    return bundle
