"""CSV and narrative Word exports for like-for-like poem comparison."""

from __future__ import annotations

import csv
import io
import zipfile

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
from versevad.exports.docx_report import build_narrative_report_from_summary_csv
from versevad.exports.reproducibility import (
    build_file_inventory,
    build_reproducibility_readme,
    methods_appendix_paragraphs,
)
from versevad.module_capabilities import CapabilityCategory, MODULE_CAPABILITIES


COMPARISON_EXPORT_API_VERSION = 1


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
    report_section: str = "",
    include_configurable: bool = True,
    include_fixed: bool = True,
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
) -> bytes:
    """Build a readable set-comparison report backed by the long-form CSV."""

    csv_content = export_poem_comparison_set_csv(
        comparison_set,
        analysis_view=analysis_view,
        weighting=weighting,
        report_section=report_section,
        include_configurable=include_configurable,
        include_fixed=include_fixed,
    )
    titles = [
        analysis.request.title or f"Poem {index}"
        for index, analysis in enumerate(comparison_set.analyses, start=1)
    ]
    return build_narrative_report_from_summary_csv(
        "compare_poems",
        csv_content,
        companion_csv_files=("versevad_poem_comparison_set.csv",),
        text_title=f"Comparison set: {', '.join(titles)}",
        result_id=comparison_set.comparison_set_id,
        warnings=(
            "Ranges are descriptive maximum-minus-minimum comparisons, not significance tests.",
            "Missing values remain missing; compare coverage and denominators before interpretation.",
        ),
        additional_paragraphs=(
            f"{len(titles)} poems; shared lexical view: "
            f"{analysis_view.replace('_', ' ')}; shared weighting: "
            f"{weighting} weighted.",
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
            source_sha256="; ".join(
                analysis.document.text_sha256 for analysis in comparison_set.analyses
            ),
        ),
    )


def export_poem_comparison_set_bundle(
    comparison_set: PoemComparisonSet,
    *,
    selection: ProfileSelection,
    export_mode: str,
    visible_section: str = "",
) -> bytes:
    """Package selected or complete comparison profiles with an inventory."""

    if export_mode not in {"current_view", "complete_audit"}:
        raise ValueError(f"Unknown export mode: {export_mode}")
    profiles = (
        selection.profiles
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
    for profile in profiles:
        stem = profile.id.casefold()
        view = view_ids[profile.scope]
        weighting = profile.weighting.value.casefold()
        files[f"comparison_{stem}.csv"] = export_poem_comparison_set_csv(
            comparison_set,
            analysis_view=view,
            weighting=weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_fixed=False,
        )
        files[f"comparison_{stem}.docx"] = export_poem_comparison_set_docx(
            comparison_set,
            analysis_view=view,
            weighting=weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_fixed=False,
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
        files["comparison_fixed_profiles.docx"] = export_poem_comparison_set_docx(
            comparison_set,
            analysis_view=fixed_view,
            weighting=fixed_weighting,
            report_section=(visible_section if export_mode == "current_view" else ""),
            include_configurable=False,
            include_fixed=True,
        )
    selected_ids = ", ".join(profile.id for profile in profiles)
    first_analysis = comparison_set.analyses[0]
    files["REPRODUCIBILITY_README.txt"] = build_reproducibility_readme(
        export_mode=export_mode,
        workspace="Compare Poems",
        report_section=visible_section,
        analysis_id=comparison_set.comparison_set_id,
        title="; ".join(
            analysis.request.title or f"Poem {position}"
            for position, analysis in enumerate(comparison_set.analyses, start=1)
        ),
        source_sha256="; ".join(
            analysis.document.text_sha256 for analysis in comparison_set.analyses
        ),
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
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for filename, content in files.items():
            bundle.writestr(filename, content)
    return archive.getvalue()


__all__ = [
    "COMPARISON_EXPORT_API_VERSION",
    "export_poem_comparison_csv",
    "export_poem_comparison_docx",
    "export_poem_comparison_set_csv",
    "export_poem_comparison_set_docx",
    "export_poem_comparison_set_bundle",
]
