"""CSV and narrative Word exports for VerseMap comparisons."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Iterable, Mapping, Sequence

from versevad.exports.docx_report import build_narrative_report_from_summary_csv
from versevad.exports.module_manifest import export_module_manifest_csv
from versevad.versemap import VerseMapAnalysisResult


def _csv_bytes(
    fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_versemap_summary_csv(result: VerseMapAnalysisResult) -> bytes:
    rows = [
        {
            "section": "map_position",
            "metric": "coordinate_1",
            "value": result.coordinate_1,
            "unit_or_scale": "weighted PCA coordinate",
            "denominator": result.model_id,
            "note": (
                f"Explains {result.explained_variance_1:.1%} of weighted reference "
                "variation; it is a composite axis, not a named literary trait."
            ),
        },
        {
            "section": "map_position",
            "metric": "coordinate_2",
            "value": result.coordinate_2,
            "unit_or_scale": "weighted PCA coordinate",
            "denominator": result.model_id,
            "note": (
                f"Explains {result.explained_variance_2:.1%} of weighted reference "
                "variation; it is a composite axis, not a named literary trait."
            ),
        },
        {
            "section": "coverage",
            "metric": "registered_feature_weight_available",
            "value": result.evidence_weight_coverage,
            "unit_or_scale": "proportion",
            "denominator": "equal-weight feature groups in Standard Profile 1.0",
            "note": "Missing evidence is omitted from distances, never entered as zero.",
        },
    ]
    rows.extend(
        {
            "section": "nearest_reference_poem",
            "metric": f"rank_{item.rank}",
            "value": item.title,
            "unit_or_scale": item.poet_name,
            "denominator": f"{item.shared_weight:.1%} shared registered weight",
            "note": (
                f"Standardized weighted distance {item.distance:.4f}; lower is "
                "nearer. This is not a probability or attribution."
            ),
        }
        for item in result.nearest_poems
    )
    rows.extend(
        {
            "section": "nearest_reference_poet",
            "metric": f"rank_{item.rank}",
            "value": item.poet_name,
            "unit_or_scale": "reference poet centroid",
            "denominator": f"{item.shared_weight:.1%} shared registered weight",
            "note": (
                f"Standardized weighted distance {item.distance:.4f}; lower is "
                "nearer. This is not a probability or authorship claim."
            ),
        }
        for item in result.nearest_poets
    )
    return _csv_bytes(
        ("section", "metric", "value", "unit_or_scale", "denominator", "note"),
        rows,
    )


def export_versemap_features_csv(result: VerseMapAnalysisResult) -> bytes:
    fields = tuple(asdict(result.feature_comparisons[0])) if result.feature_comparisons else (
        "feature_id",
        "label",
        "group_id",
        "unit",
        "query_value",
        "reference_mean",
        "reference_population_sd",
        "z_score",
        "percentile",
        "weight",
        "coverage_rate",
        "eligible_count",
        "matched_count",
    )
    return _csv_bytes(fields, (asdict(item) for item in result.feature_comparisons))


def export_versemap_neighbors_csv(result: VerseMapAnalysisResult) -> bytes:
    rows = (
        {"neighbor_set": "reference_poem", **asdict(item)}
        for item in result.nearest_poems
    )
    rows = (
        *rows,
        *(
            {"neighbor_set": "reference_poet", **asdict(item)}
            for item in result.nearest_poets
        ),
    )
    fields = (
        "neighbor_set",
        "rank",
        "point_id",
        "point_kind",
        "poet_name",
        "title",
        "distance",
        "shared_weight",
        "coordinate_1",
        "coordinate_2",
    )
    return _csv_bytes(fields, rows)


def export_versemap_map_points_csv(result: VerseMapAnalysisResult) -> bytes:
    rows = [
        {
            "point_id": result.profile.text_id,
            "point_kind": "query_poem",
            "poet_id": "",
            "poet_name": "",
            "title": result.profile.title,
            "poem_count": 1,
            "coordinate_1": result.coordinate_1,
            "coordinate_2": result.coordinate_2,
            "relative_path": "",
        }
    ]
    rows.extend(
        {
            "point_id": item.point_id,
            "point_kind": item.point_kind,
            "poet_id": item.poet_id,
            "poet_name": item.poet_name,
            "title": item.title,
            "poem_count": item.poem_count,
            "coordinate_1": item.coordinate_1,
            "coordinate_2": item.coordinate_2,
            "relative_path": item.relative_path,
        }
        for item in result.map_points
    )
    return _csv_bytes(tuple(rows[0]), rows)


def export_versemap_methodology_csv(result: VerseMapAnalysisResult) -> bytes:
    rows = (
        {
            "setting": "profile_id",
            "value": result.profile.profile_id,
            "note": "Pinned comparison profile.",
        },
        {
            "setting": "profile_build_id",
            "value": result.profile_build_id,
            "note": (
                "Pinned feature-extraction, adapter, and preprocessing build "
                "identity."
            ),
        },
        {
            "setting": "reference_release_id",
            "value": result.reference_release_id,
            "note": result.reference_release_sha256,
        },
        {"setting": "model_id", "value": result.model_id, "note": ""},
        {
            "setting": "inclusion",
            "value": "token-weighted; stopwords removed; content POS for lexical metrics",
            "note": "Repeated words retained; original spelling and lineation preserved.",
        },
        {
            "setting": "distance",
            "value": "weighted standardized Euclidean over shared dimensions",
            "note": (
                f"Minimum shared registered weight "
                f"{result.configuration.minimum_shared_weight:.0%}."
            ),
        },
        {
            "setting": "map",
            "value": "two-component weighted PCA of reference poems",
            "note": "Neighbor ranking uses full registered feature space, not 2D map distance.",
        },
    )
    return _csv_bytes(("setting", "value", "note"), rows)


def export_versemap_bundle(
    result: VerseMapAnalysisResult,
    *,
    text_title: str = "",
) -> dict[str, bytes]:
    bundle = {
        "versemap_summary.csv": export_versemap_summary_csv(result),
        "versemap_feature_profile.csv": export_versemap_features_csv(result),
        "versemap_nearest_neighbors.csv": export_versemap_neighbors_csv(result),
        "versemap_map_points.csv": export_versemap_map_points_csv(result),
        "versemap_methodology.csv": export_versemap_methodology_csv(result),
        "versemap_manifest.csv": export_module_manifest_csv(result),
    }
    bundle["versemap_report.docx"] = build_narrative_report_from_summary_csv(
        "versemap",
        bundle["versemap_summary.csv"],
        companion_csv_files=tuple(bundle),
        text_title=text_title,
        text_id=result.module_result.text_id,
        result_id=result.module_result.result_id,
        warnings=tuple(
            warning.message for warning in result.module_result.warnings
        ),
        additional_paragraphs=(
            "VerseMap reports descriptive proximity under one pinned analytical "
            "profile. It does not identify authorship, influence, quality, or meaning.",
        ),
    )
    return bundle


__all__ = [
    "export_versemap_bundle",
    "export_versemap_features_csv",
    "export_versemap_map_points_csv",
    "export_versemap_methodology_csv",
    "export_versemap_neighbors_csv",
    "export_versemap_summary_csv",
]
