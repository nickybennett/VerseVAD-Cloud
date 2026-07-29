"""CSV and narrative Word exports for sensorimotor evidence."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Iterable

from versevad.exports.docx_report import build_narrative_report_from_summary_csv
from versevad.exports.module_manifest import export_module_manifest_csv
from versevad.lexical_semantic.sensorimotor import (
    DIMENSION_BY_ID,
    SENSORIMOTOR_DIMENSIONS,
    SensorimotorAnalysisResult,
)


def _csv_bytes(
    fieldnames: list[str],
    rows: Iterable[dict[str, object]],
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_sensorimotor_summary_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    rows: list[dict[str, object]] = []
    for profile in result.profiles:
        denominator = (
            f"{profile.matched_observation_count} matched "
            f"{profile.weighting}-weighted observations"
        )
        for dimension in profile.dimensions:
            for metric, value, unit, note in (
                (
                    "mean",
                    dimension.statistics.mean,
                    "source 0-5",
                    DIMENSION_BY_ID[dimension.dimension_id].definition,
                ),
                (
                    "population_standard_deviation",
                    dimension.statistics.population_standard_deviation,
                    "source-scale points",
                    "Population dispersion across matched normative word means.",
                ),
                (
                    "cumulative_load",
                    dimension.cumulative_load,
                    "summed source ratings",
                    "Length- and repetition-sensitive when token weighted.",
                ),
                (
                    "load_per_100_observations",
                    dimension.load_per_100_observations,
                    "summed ratings per 100 observations",
                    "Length-normalized cumulative load.",
                ),
            ):
                rows.append(
                    {
                        "analysis_view": profile.analysis_view,
                        "weighting": profile.weighting,
                        "section": "dimension",
                        "dimension": dimension.dimension_id,
                        "label": dimension.label,
                        "family": dimension.family,
                        "metric": metric,
                        "value": value if value is not None else "",
                        "unit_or_scale": unit,
                        "denominator": denominator,
                        "note": note,
                    }
                )
        for metric, statistics, unit, note in (
            (
                "minkowski3_perceptual_strength",
                profile.perceptual_strength,
                "source composite",
                "Published composite across the six perceptual dimensions.",
            ),
            (
                "minkowski3_action_strength",
                profile.action_strength,
                "source composite",
                "Published composite across the five action dimensions.",
            ),
            (
                "minkowski3_sensorimotor_strength",
                profile.overall_sensorimotor_strength,
                "source composite",
                "Published composite across all eleven dimensions.",
            ),
            (
                "perceptual_exclusivity",
                profile.perceptual_exclusivity,
                "proportion",
                "Higher values indicate concentration in one perceptual modality.",
            ),
            (
                "action_exclusivity",
                profile.action_exclusivity,
                "proportion",
                "Higher values indicate concentration in one action effector.",
            ),
            (
                "sensorimotor_exclusivity",
                profile.sensorimotor_exclusivity,
                "proportion",
                "Higher values indicate concentration in one sensorimotor dimension.",
            ),
        ):
            rows.append(
                {
                    "analysis_view": profile.analysis_view,
                    "weighting": profile.weighting,
                    "section": "composite",
                    "dimension": "",
                    "label": metric.replace("_", " ").title(),
                    "family": "composite",
                    "metric": "mean",
                    "value": (
                        statistics.mean if statistics.mean is not None else ""
                    ),
                    "unit_or_scale": unit,
                    "denominator": denominator,
                    "note": note,
                }
            )
        rows.extend(
            (
                {
                    "analysis_view": profile.analysis_view,
                    "weighting": profile.weighting,
                    "section": "coverage",
                    "dimension": "",
                    "label": label,
                    "family": "coverage",
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": denominator_text,
                    "note": note,
                }
                for label, metric, value, unit, denominator_text, note in (
                    (
                        "Matched-token coverage",
                        "matched_token_coverage",
                        profile.token_coverage,
                        "proportion",
                        (
                            f"{profile.matched_token_count} of "
                            f"{profile.eligible_token_count} eligible tokens"
                        ),
                        "Unmatched tokens remain missing rather than zero.",
                    ),
                    (
                        "Dominant-category diversity",
                        "dominant_category_diversity",
                        profile.dominant_category_diversity,
                        "normalized Shannon entropy 0-1",
                        denominator,
                        "Higher values indicate a more even spread across dominant dimensions.",
                    ),
                )
            )
        )
    return _csv_bytes(
        [
            "analysis_view",
            "weighting",
            "section",
            "dimension",
            "label",
            "family",
            "metric",
            "value",
            "unit_or_scale",
            "denominator",
            "note",
        ],
        rows,
    )


def export_sensorimotor_dominance_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    rows = []
    for profile in result.profiles:
        for category in profile.dominant_categories:
            rows.append(
                {
                    "analysis_view": profile.analysis_view,
                    "weighting": profile.weighting,
                    "category": category.category,
                    "label": category.label,
                    "family": category.family,
                    "count": category.count,
                    "proportion": (
                        category.proportion
                        if category.proportion is not None
                        else ""
                    ),
                    "denominator": profile.matched_observation_count,
                }
            )
    return _csv_bytes(
        [
            "analysis_view",
            "weighting",
            "category",
            "label",
            "family",
            "count",
            "proportion",
            "denominator",
        ],
        rows,
    )


def export_sensorimotor_by_structure_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    fields = [
        "analysis_view",
        "scope",
        "scope_id",
        "ordinal",
        "source_text",
        "eligible_token_count",
        "matched_token_count",
        "token_coverage",
        "matched_observation_count",
        *[f"mean_{dimension.dimension_id}" for dimension in SENSORIMOTOR_DIMENSIONS],
    ]
    rows = []
    for summary in result.structural_summaries:
        row = {
            "analysis_view": summary.analysis_view,
            "scope": summary.scope,
            "scope_id": summary.scope_id,
            "ordinal": summary.ordinal,
            "source_text": summary.source_text,
            "eligible_token_count": summary.eligible_token_count,
            "matched_token_count": summary.matched_token_count,
            "token_coverage": (
                summary.token_coverage
                if summary.token_coverage is not None
                else ""
            ),
            "matched_observation_count": summary.matched_observation_count,
        }
        row.update(
            {
                f"mean_{dimension_id}": value if value is not None else ""
                for dimension_id, value in summary.dimension_means
            }
        )
        rows.append(row)
    return _csv_bytes(fields, rows)


def export_sensorimotor_terms_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    fields = [
        "source_term",
        "lookup_form",
        "source_row",
        "source_is_multiword",
        "observation_count",
        "surface_forms",
        "part_of_speech_tags",
        *[f"mean_{dimension.dimension_id}" for dimension in SENSORIMOTOR_DIMENSIONS],
        "dominant_sensorimotor",
        "minkowski3_sensorimotor_strength",
        "sensorimotor_exclusivity",
    ]
    rows = []
    for term in result.term_summaries:
        row = {
            "source_term": term.source_term,
            "lookup_form": term.lookup_form,
            "source_row": term.source_row,
            "source_is_multiword": term.source_is_multiword,
            "observation_count": term.observation_count,
            "surface_forms": " | ".join(term.surface_forms),
            "part_of_speech_tags": " | ".join(term.part_of_speech_tags),
            "dominant_sensorimotor": term.dominant_sensorimotor,
            "minkowski3_sensorimotor_strength": (
                term.minkowski3_sensorimotor_strength
            ),
            "sensorimotor_exclusivity": term.sensorimotor_exclusivity,
        }
        row.update(
            {
                f"mean_{dimension.dimension_id}": getattr(
                    term.means,
                    dimension.dimension_id,
                )
                for dimension in SENSORIMOTOR_DIMENSIONS
            }
        )
        rows.append(row)
    return _csv_bytes(fields, rows)


def export_sensorimotor_observations_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    fields = [
        "observation_id",
        "token_ids",
        "token_position",
        "line_number",
        "stanza_number",
        "surface_form",
        "normalized_surface",
        "normalized_lemma",
        "part_of_speech",
        "match_method",
        "matched_source_term",
        "matched_lookup_form",
        "source_row",
        "source_is_multiword",
        "stopword_status",
        "stopword_reason",
        "included_in_stopword_view",
        *[f"mean_{dimension.dimension_id}" for dimension in SENSORIMOTOR_DIMENSIONS],
        *[
            f"source_sd_{dimension.dimension_id}"
            for dimension in SENSORIMOTOR_DIMENSIONS
        ],
        "max_perceptual_strength",
        "minkowski3_perceptual_strength",
        "perceptual_exclusivity",
        "dominant_perceptual",
        "max_action_strength",
        "minkowski3_action_strength",
        "action_exclusivity",
        "dominant_action",
        "max_sensorimotor_strength",
        "minkowski3_sensorimotor_strength",
        "sensorimotor_exclusivity",
        "dominant_sensorimotor",
        "percent_known_perceptual",
        "percent_known_action",
        "context",
    ]
    rows = []
    for observation in result.observations:
        row = asdict(observation)
        row["token_ids"] = " | ".join(observation.token_ids)
        row["match_method"] = observation.match_method.value
        row.pop("means")
        row.pop("source_standard_deviations")
        row.update(
            {
                f"mean_{dimension.dimension_id}": getattr(
                    observation.means,
                    dimension.dimension_id,
                )
                for dimension in SENSORIMOTOR_DIMENSIONS
            }
        )
        row.update(
            {
                f"source_sd_{dimension.dimension_id}": getattr(
                    observation.source_standard_deviations,
                    dimension.dimension_id,
                )
                for dimension in SENSORIMOTOR_DIMENSIONS
            }
        )
        rows.append(row)
    return _csv_bytes(fields, rows)


def export_sensorimotor_unmatched_csv(
    result: SensorimotorAnalysisResult,
) -> bytes:
    fields = [
        "token_id",
        "token_position",
        "surface_form",
        "normalized_form",
        "normalized_lemma",
        "part_of_speech",
        "line_number",
        "stanza_number",
        "reason",
        "context",
    ]
    return _csv_bytes(fields, (asdict(item) for item in result.unmatched_tokens))


def export_sensorimotor_bundle(
    result: SensorimotorAnalysisResult,
    *,
    text_title: str = "",
) -> dict[str, bytes]:
    bundle = {
        "sensorimotor_summary.csv": export_sensorimotor_summary_csv(result),
        "sensorimotor_dominant_dimensions.csv": (
            export_sensorimotor_dominance_csv(result)
        ),
        "sensorimotor_by_structure.csv": (
            export_sensorimotor_by_structure_csv(result)
        ),
        "sensorimotor_terms.csv": export_sensorimotor_terms_csv(result),
        "sensorimotor_observations.csv": (
            export_sensorimotor_observations_csv(result)
        ),
        "sensorimotor_unmatched.csv": export_sensorimotor_unmatched_csv(result),
        "sensorimotor_manifest.csv": export_module_manifest_csv(result),
    }
    bundle["sensorimotor_report.docx"] = build_narrative_report_from_summary_csv(
        "sensorimotor imagery and embodiment",
        bundle["sensorimotor_summary.csv"],
        companion_csv_files=tuple(bundle),
        text_title=text_title,
        text_id=result.module_result.text_id,
        result_id=result.module_result.result_id,
        warnings=tuple(
            warning.message for warning in result.module_result.warnings
        ),
    )
    return bundle
