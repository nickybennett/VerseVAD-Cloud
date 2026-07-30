"""CSV and narrative Word exports for like-for-like poem comparison."""

from __future__ import annotations

import csv
import io

from versevad.comparison import (
    PoemComparison,
    PoemComparisonSet,
    comparison_rows,
    comparison_set_rows,
)
from versevad.exports.docx_report import build_narrative_report_from_summary_csv


COMPARISON_EXPORT_API_VERSION = 1


def export_poem_comparison_csv(
    comparison: PoemComparison,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> bytes:
    """Export every shared comparison metric with its denominators and cautions."""

    output = io.StringIO(newline="")
    fields = (
        "comparison_id",
        "poem_a_title",
        "poem_b_title",
        "section",
        "source",
        "analysis_view",
        "weighting",
        "metric_id",
        "metric",
        "value",
        "poem_a_value",
        "poem_b_value",
        "difference_b_minus_a",
        "absolute_difference",
        "unit_or_scale",
        "denominator",
        "poem_a_denominator",
        "poem_b_denominator",
        "poem_a_coverage",
        "poem_b_coverage",
        "note",
    )
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in comparison_rows(
        comparison,
        analysis_view=analysis_view,
        weighting=weighting,
    ):
        writer.writerow(
            {
                "comparison_id": comparison.comparison_id,
                "poem_a_title": comparison.first.request.title,
                "poem_b_title": comparison.second.request.title,
                "section": row.section,
                "source": row.source,
                "analysis_view": row.analysis_view,
                "weighting": row.weighting,
                "metric_id": row.metric_id,
                "metric": row.metric,
                "value": (
                    f"A: {'' if row.value_a is None else row.value_a}; "
                    f"B: {'' if row.value_b is None else row.value_b}; "
                    "B minus A: "
                    f"{'' if row.difference_b_minus_a is None else row.difference_b_minus_a}"
                ),
                "poem_a_value": (
                    "" if row.value_a is None else row.value_a
                ),
                "poem_b_value": (
                    "" if row.value_b is None else row.value_b
                ),
                "difference_b_minus_a": (
                    ""
                    if row.difference_b_minus_a is None
                    else row.difference_b_minus_a
                ),
                "absolute_difference": (
                    ""
                    if row.absolute_difference is None
                    else row.absolute_difference
                ),
                "unit_or_scale": row.unit_or_scale,
                "denominator": (
                    f"A: {row.denominator_a}; B: {row.denominator_b}"
                ),
                "poem_a_denominator": row.denominator_a,
                "poem_b_denominator": row.denominator_b,
                "poem_a_coverage": (
                    "" if row.coverage_a is None else row.coverage_a
                ),
                "poem_b_coverage": (
                    "" if row.coverage_b is None else row.coverage_b
                ),
                "note": row.note,
            }
        )
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_poem_comparison_docx(
    comparison: PoemComparison,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> bytes:
    """Build a readable comparison report backed by the complete CSV."""

    csv_content = export_poem_comparison_csv(
        comparison,
        analysis_view=analysis_view,
        weighting=weighting,
    )
    title_a = comparison.first.request.title or "Poem A"
    title_b = comparison.second.request.title or "Poem B"
    return build_narrative_report_from_summary_csv(
        "compare_poems",
        csv_content,
        companion_csv_files=("versevad_poem_comparison.csv",),
        text_title=f"{title_a} compared with {title_b}",
        result_id=comparison.comparison_id,
        warnings=(
            "Differences are descriptive B minus A values, not significance tests.",
            "Missing values remain missing; compare coverage and denominators before interpretation.",
        ),
        additional_paragraphs=(
            f"Shared lexical view: {analysis_view.replace('_', ' ')}; "
            f"shared weighting: {weighting} weighted.",
        ),
    )


def export_poem_comparison_set_csv(
    comparison_set: PoemComparisonSet,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> bytes:
    """Export a long-form two-to-ten-poem comparison without pairwise deltas."""

    output = io.StringIO(newline="")
    fields = (
        "comparison_set_id",
        "poem_position",
        "poem_id",
        "poem_title",
        "section",
        "source",
        "analysis_view",
        "weighting",
        "metric_id",
        "metric",
        "value",
        "unit_or_scale",
        "denominator",
        "coverage",
        "equal_poem_mean",
        "poem_level_population_sd",
        "contributing_poems",
        "categorical_summary",
        "note",
    )
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in comparison_set_rows(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
    ):
        for position, poem_value in enumerate(row.values, start=1):
            writer.writerow(
                {
                    "comparison_set_id": comparison_set.comparison_set_id,
                    "poem_position": position,
                    "poem_id": poem_value.poem_id,
                    "poem_title": poem_value.title,
                    "section": row.section,
                    "source": row.source,
                    "analysis_view": row.analysis_view,
                    "weighting": row.weighting,
                    "metric_id": row.metric_id,
                    "metric": row.metric,
                    "value": (
                        "" if poem_value.value is None else poem_value.value
                    ),
                    "unit_or_scale": row.unit_or_scale,
                    "denominator": poem_value.denominator,
                    "coverage": (
                        ""
                        if poem_value.coverage is None
                        else poem_value.coverage
                    ),
                    "equal_poem_mean": (
                        ""
                        if row.numeric_mean is None
                        else row.numeric_mean
                    ),
                    "poem_level_population_sd": (
                        ""
                        if row.numeric_population_standard_deviation is None
                        else row.numeric_population_standard_deviation
                    ),
                    "contributing_poems": row.contributing_poem_count,
                    "categorical_summary": row.categorical_summary,
                    "note": row.note,
                }
            )
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_poem_comparison_set_docx(
    comparison_set: PoemComparisonSet,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
) -> bytes:
    """Build a readable set-comparison report backed by the long-form CSV."""

    csv_content = export_poem_comparison_set_csv(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
    )
    titles = [
        analysis.request.title or f"Poem {index}"
        for index, analysis in enumerate(
            comparison_set.analyses,
            start=1,
        )
    ]
    return build_narrative_report_from_summary_csv(
        "compare_poems",
        csv_content,
        companion_csv_files=("versevad_poem_comparison_set.csv",),
        text_title=f"Comparison set: {', '.join(titles)}",
        result_id=comparison_set.comparison_set_id,
        warnings=(
            "Set means are equal-poem descriptive summaries, not significance tests.",
            "Missing values remain missing; compare coverage and denominators before interpretation.",
        ),
        additional_paragraphs=(
            f"{len(titles)} poems; shared lexical view: "
            f"{analysis_view.replace('_', ' ')}; shared weighting: "
            f"{weighting} weighted.",
        ),
    )


__all__ = [
    "COMPARISON_EXPORT_API_VERSION",
    "export_poem_comparison_csv",
    "export_poem_comparison_docx",
    "export_poem_comparison_set_csv",
    "export_poem_comparison_set_docx",
]
