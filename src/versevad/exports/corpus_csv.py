"""CSV and narrative Word export bundle for a local corpus project."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import asdict, replace
from enum import Enum
from typing import Iterable, Mapping, Sequence

from versevad.corpus import corpus_vad_profiles
from versevad.db import (
    CorpusMetricRecord,
    CorpusModuleAggregateRecord,
    CorpusModuleCoverageRecord,
    CorpusModuleMetricRecord,
    CorpusModuleResultRecord,
    CorpusModuleWarningRecord,
    CorpusTextRecord,
    ProjectRecord,
    UnmatchedQcRecord,
)
from versevad import __version__
from versevad.exports.docx_report import build_comprehensive_analysis_report
from versevad.exports.reproducibility import (
    build_file_inventory,
    build_reproducibility_readme,
    methods_appendix_paragraphs,
)
from versevad.analysis_profiles import (
    SCOPE_ORDER,
    WEIGHTING_ORDER,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
)
from versevad.module_capabilities import CapabilityCategory, MODULE_CAPABILITIES

CORPUS_EXPORT_API_VERSION = 1


_ELIGIBLE_TYPE_COUNT_PATTERN = re.compile(r"([\d,]+)\s+eligible\s+types", re.I)


def _repair_type_weighted_metadata(
    metrics: Sequence[CorpusMetricRecord],
) -> tuple[CorpusMetricRecord, ...]:
    """Normalize legacy type rows whose values were saved with token metadata.

    Completed runs already contain the correct type-weighted statistic and a
    canonical ``type_coverage`` row whose denominator records the eligible type
    count.  Use that retained evidence to repair the exported audit metadata;
    new runs are written correctly by the repository itself.
    """

    eligible_types: dict[tuple[str, str, str, str, str], int] = {}
    for row in metrics:
        if row.weighting.casefold() != "type" or row.metric != "type_coverage":
            continue
        match = _ELIGIBLE_TYPE_COUNT_PATTERN.search(row.denominator)
        if match is None:
            continue
        key = (
            row.run_id,
            row.text_id,
            row.text_version_id,
            row.lexicon_id,
            row.analysis_view,
        )
        eligible_types[key] = int(match.group(1).replace(",", ""))

    repaired: list[CorpusMetricRecord] = []
    for row in metrics:
        if row.weighting.casefold() != "type":
            repaired.append(row)
            continue
        key = (
            row.run_id,
            row.text_id,
            row.text_version_id,
            row.lexicon_id,
            row.analysis_view,
        )
        eligible_count = eligible_types.get(key)
        if not eligible_count:
            repaired.append(row)
            continue
        coverage = row.observations / eligible_count
        denominator = row.denominator
        if row.metric != "type_coverage":
            denominator = (
                f"{row.observations} observations; {row.observations}/"
                f"{eligible_count} eligible types matched"
            )
        repaired.append(
            replace(
                row,
                denominator=denominator,
                matched_tokens=row.observations,
                lexical_tokens=eligible_count,
                coverage=coverage,
            )
        )
    return tuple(repaired)
_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return " | ".join(
            f"{key}={_value(item)}" for key, item in sorted(value.items())
        )
    if isinstance(value, (tuple, list)):
        return " | ".join(str(_value(item)) for item in value)
    return value


def _csv_bytes(
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(fieldnames),
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def _record_rows(
    records: Sequence[object],
    *,
    record_type: type,
    exclude: frozenset[str] = frozenset(),
) -> tuple[list[str], list[dict[str, object]]]:
    rows = [
        {
            key: _value(value)
            for key, value in asdict(record).items()
            if key not in exclude
        }
        for record in records
    ]
    fields = [
        name
        for name in record_type.__dataclass_fields__
        if name not in exclude
    ]
    return (list(rows[0]) if rows else fields, rows)


def _mapping_rows(
    rows: Sequence[Mapping[str, object]],
) -> tuple[list[str], list[dict[str, object]]]:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    return (
        fields or ["record_status"],
        [{key: _value(row.get(key, "")) for key in fields} for row in rows],
    )


def _flatten_methodology(
    value: object,
    *,
    path: str = "",
) -> Iterable[dict[str, object]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            next_path = f"{path}.{key}" if path else str(key)
            yield from _flatten_methodology(value[key], path=next_path)
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value, start=1):
            yield from _flatten_methodology(item, path=f"{path}[{index}]")
        if not value:
            yield {"path": path, "value": ""}
        return
    yield {"path": path, "value": _value(value)}


def _add_records(
    bundle: dict[str, bytes],
    filename: str,
    records: Sequence[object],
    *,
    record_type: type,
    exclude: frozenset[str] = frozenset(),
) -> None:
    fields, rows = _record_rows(
        records,
        record_type=record_type,
        exclude=exclude,
    )
    bundle[filename] = _csv_bytes(fields, rows)


def build_corpus_export_bundle(
    project: ProjectRecord,
    texts: Sequence[CorpusTextRecord],
    metrics: Sequence[CorpusMetricRecord],
    unmatched: Sequence[UnmatchedQcRecord],
    methodology: Mapping[str, object] | None = None,
    review_decisions: Sequence[Mapping[str, object]] = (),
    part_of_speech_rows: Sequence[Mapping[str, object]] = (),
    module_metrics: Sequence[CorpusModuleMetricRecord] = (),
    module_coverage: Sequence[CorpusModuleCoverageRecord] = (),
    module_results: Sequence[CorpusModuleResultRecord] = (),
    module_aggregates: Sequence[CorpusModuleAggregateRecord] = (),
    module_warnings: Sequence[CorpusModuleWarningRecord] = (),
    profile_selection: ProfileSelection | None = None,
    export_mode: str = "complete_audit",
    report_section: str = "",
    active_preset: str = "",
) -> bytes:
    """Return a ZIP containing only CSV data and a narrative DOCX report."""

    if export_mode not in {"current_view", "complete_audit"}:
        raise ValueError(f"Unknown export mode: {export_mode}")
    metrics = _repair_type_weighted_metadata(tuple(metrics))
    module_metrics = tuple(module_metrics)
    module_coverage = tuple(module_coverage)
    module_results = tuple(module_results)
    module_aggregates = tuple(module_aggregates)
    module_warnings = tuple(module_warnings)
    calculated_module_names = {
        row.module_name
        for rows in (
            module_metrics,
            module_coverage,
            module_results,
            module_aggregates,
            module_warnings,
        )
        for row in rows
    }
    if metrics:
        calculated_module_names.add("vad")
    selection = profile_selection or ProfileSelection()
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    included_profiles = (
        selection.profiles
        if export_mode == "current_view"
        else tuple(
            AnalysisProfile(scope, weighting)
            for scope in SCOPE_ORDER
            for weighting in WEIGHTING_ORDER
        )
    )
    exported_metrics = tuple(metrics)
    if export_mode == "current_view":
        selected_views = {view_ids[scope] for scope in selection.scopes}
        selected_weightings = {
            weighting.value.casefold() for weighting in selection.weightings
        }
        exported_metrics = tuple(
            row
            for row in metrics
            if row.analysis_view in selected_views
            and row.weighting in selected_weightings
        )
        if report_section == "Overview":
            exported_metrics = tuple(
                row for row in exported_metrics if row.metric == "vad_mean"
            )
        elif report_section not in {"Affective Evidence", "Evidence & Diagnostics", ""}:
            exported_metrics = ()
    selected_module_names = {
        "Affective Evidence": {
            "poetry_id", "vader_sentiment",
        },
        "Lexical Character, Imagery & Embodiment": {
            "concreteness",
            "lexical_frequency",
            "age_of_acquisition",
            "sensorimotor_imagery_and_embodiment",
            "readability",
        },
        "Sound & Form": {
            "pronunciation_prosody_foundation",
            "candidate_meter_and_rhythmic_regularity",
            "rhyme_and_phonological_patterns",
            "inherited_form",
        },
        "Structure": {"lexical_style"},
        "VerseMap": {"versemap"},
        "Evidence & Diagnostics": None,
        "Overview": {"poetry_id", "vader_sentiment", "readability", "versemap"},
    }.get(report_section, None)
    if export_mode == "current_view" and selected_module_names is not None:
        module_metrics = tuple(
            row for row in module_metrics if row.module_name in selected_module_names
        )
        module_coverage = tuple(
            row for row in module_coverage if row.module_name in selected_module_names
        )
        module_results = tuple(
            row for row in module_results if row.module_name in selected_module_names
        )
        module_warnings = tuple(
            row for row in module_warnings if row.module_name in selected_module_names
        )
        module_aggregates = tuple(
            row for row in module_aggregates if row.module_name in selected_module_names
        )
    bundle: dict[str, bytes] = {}
    project_row = {key: _value(value) for key, value in asdict(project).items()}
    bundle["corpus_project.csv"] = _csv_bytes(
        list(project_row),
        [project_row],
    )
    _add_records(
        bundle,
        "corpus_works.csv",
        texts,
        record_type=CorpusTextRecord,
        exclude=frozenset({"original_text"}),
    )
    _add_records(
        bundle,
        "corpus_vad_metrics.csv",
        exported_metrics,
        record_type=CorpusMetricRecord,
    )
    _add_records(
        bundle,
        "corpus_unmatched_qc.csv",
        unmatched,
        record_type=UnmatchedQcRecord,
    )
    _add_records(
        bundle,
        "corpus_module_metrics.csv",
        module_metrics,
        record_type=CorpusModuleMetricRecord,
    )
    _add_records(
        bundle,
        "corpus_module_coverage.csv",
        module_coverage,
        record_type=CorpusModuleCoverageRecord,
    )
    _add_records(
        bundle,
        "corpus_module_results.csv",
        module_results,
        record_type=CorpusModuleResultRecord,
    )
    _add_records(
        bundle,
        "corpus_module_aggregates.csv",
        module_aggregates,
        record_type=CorpusModuleAggregateRecord,
    )
    _add_records(
        bundle,
        "corpus_module_warnings.csv",
        module_warnings,
        record_type=CorpusModuleWarningRecord,
    )

    pos_fields, pos_rows = _mapping_rows(part_of_speech_rows)
    bundle["corpus_part_of_speech.csv"] = _csv_bytes(pos_fields, pos_rows)
    decision_fields, decision_rows = _mapping_rows(review_decisions)
    bundle["corpus_review_decisions.csv"] = _csv_bytes(
        decision_fields,
        decision_rows,
    )
    methodology_rows = list(_flatten_methodology(methodology or {}))
    bundle["corpus_methodology.csv"] = _csv_bytes(
        ["path", "value"],
        methodology_rows,
    )

    profile_views = tuple(dict.fromkeys(row.analysis_view for row in exported_metrics))
    profile_weightings = tuple(dict.fromkeys(row.weighting for row in exported_metrics))
    profiles = corpus_vad_profiles(
        exported_metrics,
        total_works=len(texts),
        analysis_views=profile_views,
        weightings=profile_weightings or ("token",),
    )
    profile_rows = [
        {
            key: _value(value)
            for key, value in asdict(profile).items()
        }
        for profile in profiles
    ]
    profile_fields = list(profile_rows[0]) if profile_rows else ["record_status"]
    bundle["corpus_vad_profiles.csv"] = _csv_bytes(
        profile_fields,
        profile_rows,
    )
    scope_count_views = (
        {view_ids[scope] for scope in selection.scopes}
        if export_mode == "current_view"
        else set(view_ids.values())
    )
    scope_count_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for row in metrics:
        if row.weighting != "token" or row.analysis_view not in scope_count_views:
            continue
        key = (row.text_id, row.analysis_view)
        current = scope_count_lookup.get(key)
        if current is None or row.lexical_tokens > int(current["eligible_tokens"]):
            scope_count_lookup[key] = {
                "record_level": "poem",
                "text_id": row.text_id,
                "title": row.title,
                "analysis_view": row.analysis_view,
                "eligible_tokens": row.lexical_tokens,
            }
    scope_count_rows = list(scope_count_lookup.values())
    for analysis_view in sorted(scope_count_views):
        matching = [
            row for row in scope_count_rows if row["analysis_view"] == analysis_view
        ]
        scope_count_rows.append(
            {
                "record_level": "whole corpus",
                "text_id": "",
                "title": project.title,
                "analysis_view": analysis_view,
                "eligible_tokens": sum(int(row["eligible_tokens"]) for row in matching),
            }
        )
    bundle["corpus_scope_token_counts.csv"] = _csv_bytes(
        ("record_level", "text_id", "title", "analysis_view", "eligible_tokens"),
        scope_count_rows,
    )

    warning_messages = tuple(
        dict.fromkeys(row.message for row in module_warnings)
    )
    report_profile_rows: list[dict[str, object]] = []
    for profile in profiles:
        type_weighted = profile.weighting.casefold() == "type"
        pooled_coverage = {
            "eligible_token_count": "" if type_weighted else profile.lexical_tokens,
            "matched_token_count": "" if type_weighted else profile.matched_observations,
            "token_coverage": "" if type_weighted else profile.volume_coverage,
            "eligible_type_count": profile.lexical_tokens if type_weighted else "",
            "matched_type_count": profile.matched_observations if type_weighted else "",
            "type_coverage": profile.volume_coverage if type_weighted else "",
        }
        empty_coverage = {
            "eligible_token_count": "",
            "matched_token_count": "",
            "token_coverage": "",
            "eligible_type_count": "",
            "matched_type_count": "",
            "type_coverage": "",
        }
        common = {
            "scope": profile.analysis_view,
            "weighting": profile.weighting,
            "module_id": "vad",
            "source_id": profile.lexicon_id,
            "source": profile.lexicon,
            "unit": "normalized 0-1",
        }
        report_profile_rows.extend(
            (
                {
                    **common,
                    "profile_id": (
                        f"{profile.analysis_view}__{profile.weighting}__pooled_observation"
                    ),
                    "metric_id": f"{profile.dimension}_pooled_observation_mean",
                    "metric": f"{profile.dimension.title()} pooled-observation mean",
                    "value": profile.token_weighted_volume_mean,
                    "median": "",
                    "population_standard_deviation": (
                        profile.pooled_lexical_rating_standard_deviation
                    ),
                    "minimum": "",
                    "maximum": "",
                    "observation_count": profile.matched_observations,
                    **pooled_coverage,
                },
                {
                    **common,
                    "profile_id": (
                        f"{profile.analysis_view}__{profile.weighting}__equal_work"
                    ),
                    "metric_id": f"{profile.dimension}_equal_work_mean",
                    "metric": f"{profile.dimension.title()} equal-work mean",
                    "value": profile.work_weighted_volume_mean,
                    "median": profile.poem_mean_median,
                    "population_standard_deviation": (
                        profile.poem_mean_standard_deviation
                    ),
                    "minimum": profile.poem_mean_minimum,
                    "maximum": profile.poem_mean_maximum,
                    "observation_count": profile.works_included,
                    **empty_coverage,
                },
            )
        )
    report_profile_fields = (
        "profile_id",
        "scope",
        "weighting",
        "module_id",
        "source_id",
        "source",
        "metric_id",
        "metric",
        "value",
        "median",
        "population_standard_deviation",
        "minimum",
        "maximum",
        "observation_count",
        "eligible_token_count",
        "matched_token_count",
        "token_coverage",
        "eligible_type_count",
        "matched_type_count",
        "type_coverage",
        "unit",
    )
    report_files = dict(bundle)
    report_files["profile_metrics_selected.csv"] = _csv_bytes(
        report_profile_fields,
        report_profile_rows,
    )
    if export_mode == "complete_audit":
        report_files["profile_metrics_all_compatible.csv"] = _csv_bytes(
            report_profile_fields,
            report_profile_rows,
        )
    module_report_filenames = {
        "rhyme_and_phonological_patterns": "corpus_rhyme_phonological_aggregates.csv",
        "candidate_meter_and_rhythmic_regularity": "corpus_meter_aggregates.csv",
    }
    for module_name in sorted({row.module_name for row in module_aggregates}):
        selected_aggregates = tuple(
            row for row in module_aggregates if row.module_name == module_name
        )
        fields, rows = _record_rows(
            selected_aggregates,
            record_type=CorpusModuleAggregateRecord,
        )
        filename = module_report_filenames.get(
            module_name,
            f"corpus_{module_name}_aggregates.csv",
        )
        report_files[filename] = _csv_bytes(fields, rows)
    bundle["corpus_report.docx"] = build_comprehensive_analysis_report(
        export_files=report_files,
        text_title=project.title,
        author=project.researcher,
        analysis_timestamp=project.updated_at,
        export_mode=export_mode,
        visible_section=report_section or (
            "Complete Audit" if export_mode == "complete_audit" else "Current View"
        ),
        workspace_label="Saved Projects / Corpus",
        text_id=project.project_id,
        result_id=project.updated_at,
        source_sha256="; ".join(text.text_sha256 for text in texts),
        analysis_profiles=tuple(profile.id for profile in included_profiles),
        active_preset=active_preset,
        source_notes=project.description,
        software_version=__version__,
        warnings=warning_messages,
        resources=tuple(
            dict.fromkeys(
                [row.lexicon for row in metrics]
                + [
                    f"{row.module_name} {row.module_version}"
                    for row in module_results
                ]
            )
        ),
        methods_reproducibility=methods_appendix_paragraphs(
            included_profiles,
            source_sha256="; ".join(text.text_sha256 for text in texts),
        ),
        calculated_modules=tuple(sorted(calculated_module_names)),
    )
    selected_ids = ", ".join(profile.id for profile in included_profiles)
    fixed_modules = tuple(
        sorted(
            {
                row.module_name
                for row in module_results
                if row.module_name in MODULE_CAPABILITIES
                and MODULE_CAPABILITIES[row.module_name].category
                is CapabilityCategory.FIXED_PROFILE
            }
        )
    )
    bundle["REPRODUCIBILITY_README.txt"] = build_reproducibility_readme(
        export_mode=export_mode,
        workspace="Saved Projects",
        report_section=report_section,
        analysis_id=project.project_id,
        title=project.title,
        author=project.researcher,
        source_sha256="; ".join(text.text_sha256 for text in texts),
        visible_profiles=selection.profiles,
        included_profiles=included_profiles,
        active_preset=active_preset,
        resources=tuple(
            dict.fromkeys(
                [row.lexicon for row in metrics]
                + [f"{row.module_name} {row.module_version}" for row in module_results]
            )
        ),
        context=(
            f"Corpus: {project.title}; {len(texts)} works.",
            "Works remain separate; collection summaries do not concatenate poem texts.",
        ),
        included_fixed_modules=fixed_modules,
        export_timestamp=project.updated_at,
    )
    bundle["FILE_INVENTORY.txt"] = b""
    for _attempt in range(3):
        bundle["FILE_INVENTORY.txt"] = build_file_inventory(
            bundle,
            export_mode=export_mode,
            profile_ids=selected_ids,
        )

    archive = io.BytesIO()
    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as output:
        for filename in sorted(bundle):
            information = zipfile.ZipInfo(filename, _FIXED_TIMESTAMP)
            information.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(information, bundle[filename])
    return archive.getvalue()


__all__ = ["CORPUS_EXPORT_API_VERSION", "build_corpus_export_bundle"]
