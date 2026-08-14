"""CSV and narrative Word exports for like-for-like poem comparison."""

from __future__ import annotations

import csv
import io
import zipfile

from versevad import __version__
from versevad.analysis_profiles import (
    SCOPE_ORDER,
    WEIGHTING_ORDER,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
)

from versevad.comparison import (
    PoemComparison,
    PoemComparisonSet,
    comparison_rows,
    comparison_set_rows,
)
from versevad.exports.docx_report import build_comprehensive_analysis_report
from versevad.exports.reproducibility import (
    build_file_inventory,
    build_reproducibility_readme,
    methods_appendix_paragraphs,
)
from versevad.module_capabilities import CapabilityCategory, MODULE_CAPABILITIES
from versevad.report_profile_overrides import (
    CONTENT_WORD_SCOPE_OVERRIDE_MODULES,
    canonical_module_id,
    effective_profiles,
    override_descriptions,
    overrides_for_report_section,
    profile_applies_to_module,
)


COMPARISON_EXPORT_API_VERSION = 1


def _calculated_modules(analysis) -> tuple[str, ...]:
    modules: set[str] = set()
    if any(result.vad_summary is not None for result in analysis.results):
        modules.add("vad")
    if any(result.category_statistics for result in analysis.results):
        modules.add("emotion_association")
    if any(result.intensity_statistics for result in analysis.results):
        modules.add("emotion_intensity")
    for attribute in (
        "vader_sentiment",
        "readability",
        "concreteness",
        "frequency",
        "aoa",
        "sensorimotor",
        "pronunciation",
        "meter",
        "phonology",
        "lexical_style",
        "poetry_id",
        "inherited_form",
        "versemap",
    ):
        result = getattr(analysis, attribute, None)
        if result is not None:
            modules.add(result.module_result.module_name)
    return tuple(sorted(modules))


_COMPARISON_REPORT_FILENAMES = {
    "Affective Evidence": "comparison_phase2_vad.csv",
    "Emotion": "comparison_phase2_emotion.csv",
    "Lexical Character, Imagery & Embodiment": (
        "comparison_concreteness_frequency_aoa.csv"
    ),
    "Sensorimotor": "comparison_sensorimotor.csv",
    "Readability": "comparison_readability.csv",
    "Sound & Form": "comparison_pronunciation_meter_rhyme_inherited_form.csv",
    "Structure": "comparison_lexical_style.csv",
    "PoetryID": "comparison_poetry_id.csv",
    "VerseMap": "comparison_versemap.csv",
    "Evidence & Diagnostics": "comparison_diagnostics.csv",
}


def _comparison_report_family(metric_id: str) -> str:
    prefix = metric_id.split(".", 1)[0]
    if prefix == "poetry_id":
        return "PoetryID"
    if prefix in {"emotion", "emotion_intensity", "vader"}:
        return "Emotion"
    if prefix == "sensorimotor":
        return "Sensorimotor"
    if prefix == "readability":
        return "Readability"
    return _dashboard_section(metric_id)


def _csv_rows_bytes(rows: list[dict[str, str]]) -> bytes:
    if not rows:
        return b""
    preferred = (
        "poem_title",
        "profile",
        "source",
        "metric",
        "value",
        "unit_or_scale",
        "denominator",
        "coverage",
        "range_max_minus_min",
        "categorical_summary",
        "note",
    )
    fields = [field for field in preferred if any(field in row for row in rows)]
    fields.extend(
        field
        for field in dict.fromkeys(field for row in rows for field in row)
        if field not in fields
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def _comparison_report_files(
    profile_csvs: tuple[tuple[str, bytes], ...],
) -> dict[str, bytes]:
    """Pivot long comparison evidence into readable poem-by-poem report tables."""

    grouped: dict[str, dict[tuple[str, ...], dict[str, str]]] = {}
    for profile_label, content in profile_csvs:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        for source_row in reader:
            row = dict(source_row)
            family = _comparison_report_family(row.get("metric_id", ""))
            key = (
                profile_label,
                row.get("source", ""),
                row.get("metric_id", ""),
                row.get("metric", ""),
                row.get("unit_or_scale", ""),
                row.get("range_max_minus_min", ""),
                row.get("categorical_summary", ""),
                row.get("note", ""),
            )
            report_row = grouped.setdefault(family, {}).setdefault(
                key,
                {
                    "profile": profile_label,
                    "source": row.get("source", ""),
                    "metric": row.get("metric", ""),
                    "unit_or_scale": row.get("unit_or_scale", ""),
                    "range_max_minus_min": row.get("range_max_minus_min", ""),
                    "categorical_summary": row.get("categorical_summary", ""),
                    "note": row.get("note", ""),
                },
            )
            poem_title = row.get("poem_title", "") or "Untitled poem"
            report_row[poem_title] = row.get("value", "")
    return {
        _COMPARISON_REPORT_FILENAMES[family]: _csv_rows_bytes(list(rows.values()))
        for family, rows in grouped.items()
        if rows
    }


def _dashboard_section(metric_id: str) -> str:
    prefix = metric_id.split(".", 1)[0]
    if prefix in {"vad", "emotion", "emotion_intensity", "poetry_id", "vader"}:
        return "Affective Evidence"
    if prefix in {"concreteness", "frequency", "rarity", "aoa", "readability", "sensorimotor"}:
        return "Lexical Character, Imagery & Embodiment"
    if prefix in {"pronunciation", "meter", "phonology", "inherited_form"}:
        return "Sound & Form"
    if prefix in {"lexical_style", "word_length", "pos"}:
        return "Structure"
    if prefix == "versemap":
        return "VerseMap"
    return "Evidence & Diagnostics"


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
    """Build a comprehensive comparison report backed by the complete CSV."""

    csv_content = export_poem_comparison_csv(
        comparison,
        analysis_view=analysis_view,
        weighting=weighting,
    )
    title_a = comparison.first.request.title or "Poem A"
    title_b = comparison.second.request.title or "Poem B"
    profile_label = (
        f"{analysis_view.replace('_', ' ').title()} · {weighting.title()}-weighted"
    )
    return build_comprehensive_analysis_report(
        export_files=_comparison_report_files(((profile_label, csv_content),)),
        text_title=f"{title_a} compared with {title_b}",
        author="; ".join(
            filter(
                None,
                (
                    getattr(comparison.first.request, "author", ""),
                    getattr(comparison.second.request, "author", ""),
                ),
            )
        ),
        export_mode="current_view",
        visible_section="Complete comparison",
        workspace_label="Compare Poems",
        text_id=comparison.comparison_id,
        result_id=comparison.comparison_id,
        source_sha256="; ".join(
            (
                comparison.first.document.text_sha256,
                comparison.second.document.text_sha256,
            )
        ),
        calculated_modules=_calculated_modules(comparison.first),
        analysis_profiles=(profile_label,),
        software_version=__version__,
        warnings=(
            "Differences are descriptive B minus A values, not significance tests.",
            "Missing values remain missing; compare coverage and denominators before interpretation.",
        ),
        methods_reproducibility=methods_appendix_paragraphs(
            (
                AnalysisProfile(
                    next(
                        scope
                        for scope, view in {
                            LexicalScope.ALL_LEXICAL: "all_matched",
                            LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
                            LexicalScope.CONTENT_WORDS: "content_words",
                        }.items()
                        if view == analysis_view
                    ),
                    next(
                        item
                        for item in WEIGHTING_ORDER
                        if item.value.casefold() == weighting
                    ),
                ),
            ),
            source_sha256="; ".join(
                (
                    comparison.first.document.text_sha256,
                    comparison.second.document.text_sha256,
                )
            ),
        ),
    )


def export_poem_comparison_set_csv(
    comparison_set: PoemComparisonSet,
    *,
    analysis_view: str = "all_matched",
    weighting: str = "token",
    report_section: str = "",
    include_configurable: bool = True,
    include_fixed: bool = True,
    profile_selection: ProfileSelection | None = None,
    module_scope_overrides: frozenset[str] = frozenset(),
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
        "range_max_minus_min",
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
        configurable = (
            row.analysis_view in {"all_matched", "stopwords_excluded", "content_words"}
            and row.weighting in {"token", "type"}
        )
        if configurable and profile_selection is not None:
            profile = AnalysisProfile(
                next(scope for scope in SCOPE_ORDER if {
                    LexicalScope.ALL_LEXICAL: "all_matched",
                    LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
                    LexicalScope.CONTENT_WORDS: "content_words",
                }[scope] == row.analysis_view),
                next(
                    item for item in WEIGHTING_ORDER
                    if item.value.casefold() == row.weighting
                ),
            )
            module_id = canonical_module_id(row.metric_id)
            if module_id in CONTENT_WORD_SCOPE_OVERRIDE_MODULES:
                if not profile_applies_to_module(
                    profile,
                    module_id=module_id,
                    selection=profile_selection,
                    overridden_modules=module_scope_overrides,
                ):
                    continue
            elif profile not in profile_selection.profiles:
                continue
        if report_section:
            if report_section == "Overview":
                if not (
                    row.metric_id.endswith(".mean")
                    or row.metric_id.endswith(".category_fit")
                    or row.metric_id.endswith(".nearest_centroid")
                ):
                    continue
            elif report_section != "Evidence & Diagnostics" and (
                _dashboard_section(row.metric_id) != report_section
            ):
                continue
        if configurable and not include_configurable:
            continue
        if not configurable and not include_fixed:
            continue
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
                    "range_max_minus_min": (
                        "" if row.numeric_range is None else row.numeric_range
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
    report_section: str = "",
    include_configurable: bool = True,
    include_fixed: bool = True,
    profile_selection: ProfileSelection | None = None,
    module_scope_overrides: frozenset[str] = frozenset(),
) -> bytes:
    """Build a comprehensive set-comparison report backed by the long-form CSV."""

    csv_content = export_poem_comparison_set_csv(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
        report_section=report_section,
        include_configurable=include_configurable,
        include_fixed=include_fixed,
        profile_selection=profile_selection,
        module_scope_overrides=module_scope_overrides,
    )
    titles = [
        analysis.request.title or f"Poem {index}"
        for index, analysis in enumerate(comparison_set.analyses, start=1)
    ]
    profile_label = (
        f"{analysis_view.replace('_', ' ').title()} · {weighting.title()}-weighted"
    )
    source_sha256 = "; ".join(
        analysis.document.text_sha256 for analysis in comparison_set.analyses
    )
    return build_comprehensive_analysis_report(
        export_files=_comparison_report_files(((profile_label, csv_content),)),
        text_title=f"Comparison set: {', '.join(titles)}",
        author="; ".join(
            dict.fromkeys(
                filter(
                    None,
                    (
                        getattr(analysis.request, "author", "")
                        for analysis in comparison_set.analyses
                    ),
                )
            )
        ),
        export_mode="current_view",
        visible_section=report_section or "Complete comparison",
        workspace_label="Compare Poems",
        text_id=comparison_set.comparison_set_id,
        result_id=comparison_set.comparison_set_id,
        source_sha256=source_sha256,
        calculated_modules=_calculated_modules(comparison_set.analyses[0]),
        analysis_profiles=(profile_label,),
        software_version=__version__,
        warnings=(
            "Ranges are descriptive maximum-minus-minimum comparisons, not significance tests.",
            "Missing values remain missing; compare coverage and denominators before interpretation.",
        ),
        methods_reproducibility=methods_appendix_paragraphs(
            (
                AnalysisProfile(
                    next(
                        scope
                        for scope, view in {
                            LexicalScope.ALL_LEXICAL: "all_matched",
                            LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
                            LexicalScope.CONTENT_WORDS: "content_words",
                        }.items()
                        if view == analysis_view
                    ),
                    next(
                        item
                        for item in WEIGHTING_ORDER
                        if item.value.casefold() == weighting
                    ),
                ),
            ) if include_configurable else (),
            source_sha256=source_sha256,
        ),
    )


def export_poem_comparison_set_bundle(
    comparison_set: PoemComparisonSet,
    *,
    selection: ProfileSelection,
    export_mode: str,
    visible_section: str = "",
    module_scope_overrides: frozenset[str] = frozenset(),
) -> bytes:
    """Package selected or complete comparison profiles with an inventory."""

    if export_mode not in {"current_view", "complete_audit"}:
        raise ValueError(f"Unknown export mode: {export_mode}")
    overridden_modules = (
        overrides_for_report_section(visible_section, module_scope_overrides)
        if export_mode == "current_view"
        else frozenset()
    )
    profiles = (
        effective_profiles(selection, overridden_modules)
        if export_mode == "current_view"
        else tuple(
            AnalysisProfile(scope, weighting)
            for scope in SCOPE_ORDER
            for weighting in WEIGHTING_ORDER
        )
    )
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    files: dict[str, bytes] = {}
    report_csvs: list[tuple[str, bytes]] = []
    for profile in profiles:
        stem = profile.id.casefold()
        view = view_ids[profile.scope]
        weighting = profile.weighting.value.casefold()
        profile_csv = export_poem_comparison_set_csv(
            comparison_set,
            analysis_view=view,
            weighting=weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_fixed=False,
            profile_selection=(selection if export_mode == "current_view" else None),
            module_scope_overrides=overridden_modules,
        )
        files[f"comparison_{stem}.csv"] = profile_csv
        report_csvs.append((profile.label, profile_csv))
        files[f"comparison_{stem}.docx"] = export_poem_comparison_set_docx(
            comparison_set,
            analysis_view=view,
            weighting=weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_fixed=False,
            profile_selection=(selection if export_mode == "current_view" else None),
            module_scope_overrides=overridden_modules,
        )
    first_profile = profiles[0] if profiles else AnalysisProfile(
        LexicalScope.STOPWORD_EXCLUDED,
        WEIGHTING_ORDER[0],
    )
    fixed_view = view_ids[first_profile.scope]
    fixed_weighting = first_profile.weighting.value.casefold()
    fixed_rows = comparison_set_rows(
        comparison_set,
        analysis_view=fixed_view,
        weighting=fixed_weighting,
    )
    fixed_csv = export_poem_comparison_set_csv(
        comparison_set,
        analysis_view=fixed_view,
        weighting=fixed_weighting,
        report_section=(visible_section if export_mode == "current_view" else ""),
        include_configurable=False,
        include_fixed=True,
    )
    if len(fixed_csv.decode("utf-8-sig").splitlines()) > 1:
        files["comparison_fixed_profiles.csv"] = fixed_csv
        report_csvs.append(("Fixed-profile metrics", fixed_csv))
        files["comparison_fixed_profiles.docx"] = export_poem_comparison_set_docx(
            comparison_set,
            analysis_view=fixed_view,
            weighting=fixed_weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_configurable=False,
            include_fixed=True,
        )
    report_files = _comparison_report_files(tuple(report_csvs))
    exception_descriptions = override_descriptions(selection, overridden_modules)
    if exception_descriptions:
        files["module_scope_overrides.csv"] = _csv_rows_bytes(
            [
                {
                    "module_id": module_id,
                    "scope_override": "Content words only",
                    "weighting": ", ".join(
                        weighting.label for weighting in selection.weightings
                    ),
                    "note": "The global lexical scope remains unchanged.",
                }
                for module_id in sorted(overridden_modules)
            ]
        )
    report_title = "; ".join(
        analysis.request.title or f"Poem {position}"
        for position, analysis in enumerate(comparison_set.analyses, start=1)
    )
    source_sha256 = "; ".join(
        analysis.document.text_sha256 for analysis in comparison_set.analyses
    )
    first_analysis = comparison_set.analyses[0]
    files["VerseVAD_comprehensive_comparison_report.docx"] = (
        build_comprehensive_analysis_report(
            export_files=report_files,
            text_title=f"Comparison set: {report_title}",
            author="; ".join(
                dict.fromkeys(
                    filter(
                        None,
                        (
                            getattr(analysis.request, "author", "")
                            for analysis in comparison_set.analyses
                        ),
                    )
                )
            ),
            export_mode=export_mode,
            visible_section=(
                visible_section
                if export_mode == "current_view"
                else "Complete Audit"
            ),
            workspace_label="Compare Poems",
            text_id=comparison_set.comparison_set_id,
            result_id=comparison_set.comparison_set_id,
            source_sha256=source_sha256,
            analysis_profiles=tuple(profile.label for profile in profiles),
            profile_exceptions=exception_descriptions,
            active_preset="Shared comparison profile",
            software_version=__version__,
            warnings=(
                "Ranges are descriptive maximum-minus-minimum comparisons, not significance tests.",
                "Missing values remain missing; compare coverage and denominators before interpretation.",
            ),
            resources=tuple(
                dict.fromkeys(
                    result.lexicon_metadata.display_name
                    for result in first_analysis.results
                )
            ),
            methods_reproducibility=methods_appendix_paragraphs(
                profiles,
                source_sha256=source_sha256,
            ),
            calculated_modules=_calculated_modules(first_analysis),
        )
    )
    selected_ids = ", ".join(profile.id for profile in profiles)
    files["REPRODUCIBILITY_README.txt"] = build_reproducibility_readme(
        export_mode=export_mode,
        workspace="Compare Poems",
        report_section=visible_section,
        analysis_id=comparison_set.comparison_set_id,
        title=report_title,
        source_sha256=source_sha256,
        visible_profiles=selection.profiles,
        included_profiles=profiles,
        active_preset="shared comparison profile",
        preprocessing=(
            "Every poem used the same retained preprocessing and analytical configuration.",
            "Poem texts were not concatenated; within-poem statistics remain distinct.",
        ),
        resources=tuple(
            result.lexicon_metadata.display_name
            for result in first_analysis.results
        ),
        context=(
            f"Comparison contains {len(comparison_set.analyses)} poems.",
            "Ranges are descriptive maximum-minus-minimum values, not significance tests.",
        ),
        overrides=exception_descriptions,
        included_fixed_modules=tuple(
            module_id
            for module_id, capability in MODULE_CAPABILITIES.items()
            if capability.category is CapabilityCategory.FIXED_PROFILE
            and any(
                row.metric_id.startswith(module_id + ".")
                for row in fixed_rows
            )
        ),
    )
    files["FILE_INVENTORY.txt"] = b""
    for _attempt in range(3):
        files["FILE_INVENTORY.txt"] = build_file_inventory(
            files,
            export_mode=export_mode,
            profile_ids=selected_ids,
        )
    from versevad.exports.canonical_schema import standardize_export_files

    files = standardize_export_files(
        files,
        analysis_mode="compare_poems",
        export_mode=export_mode,
        analysis_id=comparison_set.comparison_set_id,
        title=report_title,
        author="; ".join(
            dict.fromkeys(
                filter(
                    None,
                    (
                        getattr(analysis.request, "author", "")
                        for analysis in comparison_set.analyses
                    ),
                )
            )
        ),
        main_report_path="VerseVAD_comprehensive_comparison_report.docx",
        main_report_name="Comparison_Report.docx",
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for filename, content in files.items():
            bundle.writestr(filename, content)
    return archive.getvalue()


def export_poem_comparison_set_selected_csv(
    comparison_set: PoemComparisonSet,
    *,
    selection: ProfileSelection,
    export_mode: str = "current_view",
    visible_section: str = "",
    module_scope_overrides: frozenset[str] = frozenset(),
) -> bytes:
    """Return one long CSV containing the same profiles as the selected bundle."""

    overridden_modules = (
        overrides_for_report_section(visible_section, module_scope_overrides)
        if export_mode == "current_view"
        else frozenset()
    )
    profiles = (
        effective_profiles(selection, overridden_modules)
        if export_mode == "current_view"
        else tuple(
            AnalysisProfile(scope, weighting)
            for scope in SCOPE_ORDER
            for weighting in WEIGHTING_ORDER
        )
    )
    view_ids = {
        LexicalScope.ALL_LEXICAL: "all_matched",
        LexicalScope.STOPWORD_EXCLUDED: "stopwords_excluded",
        LexicalScope.CONTENT_WORDS: "content_words",
    }
    rows: list[dict[str, str]] = []
    for profile in profiles:
        content = export_poem_comparison_set_csv(
            comparison_set,
            analysis_view=view_ids[profile.scope],
            weighting=profile.weighting.value.casefold(),
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_fixed=False,
            profile_selection=(selection if export_mode == "current_view" else None),
            module_scope_overrides=overridden_modules,
        )
        rows.extend(
            dict(row)
            for row in csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        )
    if profiles:
        first = profiles[0]
        fixed = export_poem_comparison_set_csv(
            comparison_set,
            analysis_view=view_ids[first.scope],
            weighting=first.weighting.value.casefold(),
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_configurable=False,
            include_fixed=True,
        )
        rows.extend(
            dict(row)
            for row in csv.DictReader(io.StringIO(fixed.decode("utf-8-sig")))
        )
    return _csv_rows_bytes(rows)


__all__ = [
    "COMPARISON_EXPORT_API_VERSION",
    "export_poem_comparison_csv",
    "export_poem_comparison_docx",
    "export_poem_comparison_set_csv",
    "export_poem_comparison_set_docx",
    "export_poem_comparison_set_bundle",
    "export_poem_comparison_set_selected_csv",
]
