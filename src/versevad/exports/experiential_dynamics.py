"""Machine-readable exports for one Experiential Dynamics assessment."""

from __future__ import annotations

import csv
import io

from versevad.experiential_dynamics import (
    DIMENSION_LABELS,
    ExperientialDynamicsMeasurements,
    ExperientialDynamicsResult,
)


def _csv_bytes(fields: tuple[str, ...], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def export_experiential_dynamics_bundle(
    result: ExperientialDynamicsResult,
    measurements: ExperientialDynamicsMeasurements,
) -> dict[str, bytes]:
    if result.text_version_id != measurements.text_version_id:
        raise ValueError("Experiential Dynamics result and measurements must match.")
    dimension_rows: list[dict[str, object]] = []
    for component in result.dimensions:
        measurement = measurements.dimension(component.dimension)
        coverage = measurement.coverage
        dimension_rows.append(
            {
                "assessment_id": result.assessment_id,
                "text_version_id": result.text_version_id,
                "assessment_timing": result.assessment_timing.value,
                "submitted_at": result.submitted_at,
                "methodology_version": result.configuration.methodology_version,
                "questionnaire_version": result.configuration.questionnaire_version,
                "configuration_id": result.configuration.configuration_id,
                "fixed_profile_id": result.configuration.profile.id,
                "fixed_profile_label": result.configuration.profile.label,
                "fixed_scope": result.configuration.lexical_scope.value,
                "fixed_weighting": result.configuration.weighting.value,
                "agreement_tolerance": result.configuration.agreement_tolerance,
                "dynamic_signature": result.dynamic_signature,
                "compact_code": result.compact_code,
                "dimension": component.dimension,
                "dimension_label": DIMENSION_LABELS[component.dimension],
                "resource_id": measurement.source_id,
                "resource": measurement.source_label,
                "resource_version": measurement.source_version,
                "resource_sha256": measurement.source_sha256,
                "measured_source_value": component.measured_source_value,
                "measured_source_unit": measurement.source_unit,
                "measured_normalized_0_1": component.measured_normalized,
                "experienced_raw_mean_1_5": component.experienced_raw_mean,
                "experienced_normalized_0_1": component.experienced_normalized,
                "reader_response_population_sd": component.response_population_standard_deviation,
                "dynamic_gap_experienced_minus_measured": component.dynamic_gap,
                "relationship": component.relationship.value,
                "relationship_label": component.relationship_label,
                "compact_symbol": component.compact_symbol,
                "eligible_token_count": (
                    coverage.eligible_token_count if coverage is not None else None
                ),
                "matched_token_count": (
                    coverage.matched_token_count if coverage is not None else None
                ),
                "token_coverage": (
                    coverage.token_coverage if coverage is not None else None
                ),
            }
        )
    response_rows = [
        {
            "assessment_id": result.assessment_id,
            "text_version_id": result.text_version_id,
            "assessment_timing": result.assessment_timing.value,
            "item_id": response.item_id,
            "dimension": response.dimension,
            "prompt": response.prompt,
            "numeric_response_1_5": response.numeric_value,
            "selected_response": response.option_label,
        }
        for response in result.responses
    ]
    return {
        "experiential_dynamics_summary.csv": _csv_bytes(
            tuple(dimension_rows[0]),
            dimension_rows,
        ),
        "experiential_dynamics_responses.csv": _csv_bytes(
            tuple(response_rows[0]),
            response_rows,
        ),
    }


__all__ = ["export_experiential_dynamics_bundle"]
