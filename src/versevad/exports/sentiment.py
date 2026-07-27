"""CSV and narrative Word exports for offline VADER polarity evidence."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict

from versevad.exports.docx_report import build_narrative_report_from_summary_csv
from versevad.exports.module_manifest import export_module_manifest_csv
from versevad.lexical_semantic.sentiment import VaderSentimentAnalysisResult


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_vader_sentiment_summary_csv(
    result: VaderSentimentAnalysisResult,
) -> bytes:
    score = result.document_score
    rows = [
        {
            "section": "document_polarity",
            "metric": metric,
            "value": value,
            "unit_or_scale": unit,
            "denominator": denominator,
            "note": note,
        }
        for metric, value, unit, denominator, note in (
            (
                "positive_proportion",
                score.positive_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "The three proportions sum to approximately one.",
            ),
            (
                "neutral_proportion",
                score.neutral_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "Neutral categorization is not evidence of emotional neutrality.",
            ),
            (
                "negative_proportion",
                score.negative_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "The three proportions sum to approximately one.",
            ),
            (
                "compound_score",
                score.compound_score,
                "normalized weighted composite (-1 to 1)",
                "complete preserved text",
                "Includes VADER's rule-based adjustments.",
            ),
            (
                "conventional_threshold_label",
                score.threshold_label,
                "positive / neutral / negative",
                "document compound score",
                (
                    f"Positive >= {result.configuration.positive_minimum}; "
                    f"negative <= {result.configuration.negative_maximum}. "
                    "This is not a poem-emotion diagnosis."
                ),
            ),
            (
                "vader_package_version",
                result.package_version,
                "software version",
                "",
                result.citation,
            ),
        )
    ]
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


def export_vader_sentence_scores_csv(
    result: VaderSentimentAnalysisResult,
) -> bytes:
    rows = []
    for item in result.sentence_scores:
        row = {
            "segment_id": item.segment_id,
            "sentence_number": item.ordinal,
            "line_numbers": " | ".join(str(value) for value in item.line_numbers),
            "source_text": item.source_text,
            **asdict(item.score),
        }
        rows.append(row)
    return _csv_bytes(
        [
            "segment_id",
            "sentence_number",
            "line_numbers",
            "source_text",
            "positive_proportion",
            "neutral_proportion",
            "negative_proportion",
            "compound_score",
            "threshold_label",
        ],
        rows,
    )


def export_vader_sentiment_bundle(
    result: VaderSentimentAnalysisResult,
    *,
    text_title: str = "",
) -> dict[str, bytes]:
    bundle = {
        "vader_sentiment_summary.csv": export_vader_sentiment_summary_csv(result),
        "vader_sentiment_sentences.csv": export_vader_sentence_scores_csv(result),
        "vader_sentiment_manifest.csv": export_module_manifest_csv(result),
    }
    bundle["vader_sentiment_report.docx"] = (
        build_narrative_report_from_summary_csv(
            "vader_sentiment",
            bundle["vader_sentiment_summary.csv"],
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
