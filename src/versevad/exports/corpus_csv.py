"""CSV and narrative Word export bundle for a local corpus project."""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import asdict
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
from versevad.exports.docx_report import REPORT_PROFILES, build_narrative_report
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
            "concreteness", "frequency", "aoa", "sensorimotor",
        },
        "Sound & Form": {
            "pronunciation", "meter", "performance_meter", "phonology",
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

    profiles = corpus_vad_profiles(exported_metrics, total_works=len(texts))
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

    report_rows: list[dict[str, str]] = [
        {
            "section": "collection overview",
            "metric": "works represented",
            "value": str(len(texts)),
            "unit_or_scale": "works",
            "denominator": project.title,
            "note": (
                "Full literary texts are not duplicated in this export; the works "
                "CSV retains identifiers, paths, and SHA-256 hashes."
            ),
        },
        {
            "section": "collection overview",
            "metric": "VAD metric records",
            "value": str(len(exported_metrics)),
            "unit_or_scale": "records",
            "denominator": "",
            "note": "Each record retains its source, view, weighting, and scale.",
        },
        {
            "section": "collection overview",
            "metric": "additional module result records",
            "value": str(len(module_results)),
            "unit_or_scale": "records",
            "denominator": "",
            "note": "Module configurations remain distinct.",
        },
    ]
    for profile in profiles:
        section = (
            f"{profile.lexicon} · {profile.analysis_view} · {profile.dimension}"
        )
        report_rows.extend(
            (
                {
                    "section": section,
                    "metric": "token weighted volume mean",
                    "value": f"{profile.token_weighted_volume_mean:.4f}",
                    "unit_or_scale": "normalized 0-1",
                    "denominator": (
                        f"{profile.matched_observations} matched observations"
                    ),
                    "note": "Longer works contribute more observations.",
                },
                {
                    "section": section,
                    "metric": "pooled lexical rating population standard deviation",
                    "value": (
                        f"{profile.pooled_lexical_rating_standard_deviation:.4f}"
                        if profile.pooled_lexical_rating_standard_deviation
                        is not None
                        else "unavailable"
                    ),
                    "unit_or_scale": "normalized 0-1",
                    "denominator": (
                        f"{profile.matched_observations} matched observations"
                    ),
                    "note": (
                        "Spread of pooled matched token ratings; withheld if a "
                        "required work-level standard deviation is unavailable."
                    ),
                },
                {
                    "section": section,
                    "metric": "work weighted volume mean",
                    "value": f"{profile.work_weighted_volume_mean:.4f}",
                    "unit_or_scale": "normalized 0-1",
                    "denominator": (
                        f"{profile.works_included} included works; "
                        f"{profile.works_omitted} omitted"
                    ),
                    "note": "Each included work contributes one mean.",
                },
                {
                    "section": section,
                    "metric": "across poem mean population standard deviation",
                    "value": f"{profile.poem_mean_standard_deviation:.4f}",
                    "unit_or_scale": "normalized 0-1",
                    "denominator": f"{profile.works_included} included works",
                    "note": (
                        "Spread of poem-level token means, not source-rater "
                        "uncertainty or a confidence interval."
                    ),
                },
                {
                    "section": section,
                    "metric": "poem mean median",
                    "value": f"{profile.poem_mean_median:.4f}",
                    "unit_or_scale": "normalized 0-1",
                    "denominator": f"{profile.works_included} included works",
                    "note": "Median of the included poem-level token means.",
                },
                {
                    "section": section,
                    "metric": "poem mean range",
                    "value": (
                        f"{profile.poem_mean_minimum:.4f} to "
                        f"{profile.poem_mean_maximum:.4f}"
                    ),
                    "unit_or_scale": "normalized 0-1",
                    "denominator": f"{profile.works_included} included works",
                    "note": "Lowest and highest included poem-level token means.",
                },
            )
        )
    warning_messages = tuple(
        dict.fromkeys(row.message for row in module_warnings)
    )
    bundle["corpus_report.docx"] = build_narrative_report(
        profile=REPORT_PROFILES["corpus"],
        summary_rows=report_rows,
        companion_csv_files=tuple(bundle),
        text_title=project.title,
        text_id=project.project_id,
        warnings=warning_messages,
        methods_reproducibility=methods_appendix_paragraphs(
            included_profiles,
            source_sha256="; ".join(text.text_sha256 for text in texts),
        ),
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
