import csv
import io
import zipfile

import pytest
import pandas as pd
import pyarrow as pa

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.comparison import (
    build_poem_comparison,
    build_poem_comparison_set,
    comparison_rows,
    comparison_set_rows,
)
from versevad.exports.comparison import (
    export_poem_comparison_csv,
    export_poem_comparison_docx,
    export_poem_comparison_set_csv,
    export_poem_comparison_set_docx,
)
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import PreparedPoemPreprocessor, create_text_document
from versevad.ui.comparison import (
    _REPORT_SECTIONS,
    _arrow_safe_display_frame,
    _chart_domain,
    _comparison_metric_family,
    _report_location,
)


def _workspace(preprocessor, *, identifier: str, title: str, text: str):
    document = create_text_document(identifier, title, text)
    poem = preprocessor.process_document(document)
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        PreparedPoemPreprocessor(poem),
        minimum_match_requirement=1,
    )
    request = AnalysisRequest(
        project_name="Comparison test",
        title=title,
        original_text=text,
        lexicon_ids=(result.lexicon_metadata.lexicon_id,),
        minimum_match_requirement=1,
    )
    return WorkspaceAnalysis(
        request=request,
        document=document,
        results=(result,),
        comparison=compare_lexicons((result,)),
        poem_document=poem,
    )


@pytest.fixture
def poem_comparison(preprocessor):
    first = _workspace(
        preprocessor,
        identifier="comparison-a",
        title="Poem A",
        text="Very dark night glows.\nBright night glows.",
    )
    second = _workspace(
        preprocessor,
        identifier="comparison-b",
        title="Poem B",
        text="Bright bright bright glows.\nNight glows.",
    )
    return build_poem_comparison(first, second)


@pytest.fixture
def poem_comparison_set(preprocessor):
    analyses = (
        _workspace(
            preprocessor,
            identifier="comparison-set-a",
            title="Poem A",
            text="Very dark night glows.\nBright night glows.",
        ),
        _workspace(
            preprocessor,
            identifier="comparison-set-b",
            title="Poem B",
            text="Bright bright bright glows.\nNight glows.",
        ),
        _workspace(
            preprocessor,
            identifier="comparison-set-c",
            title="Poem C",
            text="Dark night.\nVery bright glows.",
        ),
    )
    return build_poem_comparison_set(analyses)


def test_comparison_reports_like_for_like_means_dispersion_and_loads(
    poem_comparison,
) -> None:
    rows = comparison_rows(
        poem_comparison,
        analysis_view="all_matched",
        weighting="token",
    )
    by_id = {row.metric_id: row for row in rows}
    prefix = "vad.synthetic_vad_phase2.valence"

    mean = by_id[f"{prefix}.mean"]
    dispersion = by_id[f"{prefix}.population_sd"]
    cumulative = by_id[f"{prefix}.rating_total"]

    assert mean.value_a is not None
    assert mean.value_b is not None
    assert mean.difference_b_minus_a == pytest.approx(
        float(mean.value_b) - float(mean.value_a)
    )
    assert dispersion.value_a is not None
    assert dispersion.note.startswith("Within-poem lexical dispersion")
    assert cumulative.value_a is not None
    assert cumulative.denominator_a.endswith("token-weighted observations")


def test_comparison_type_view_changes_repetition_sensitive_denominator(
    poem_comparison,
) -> None:
    token_rows = comparison_rows(poem_comparison, weighting="token")
    type_rows = comparison_rows(poem_comparison, weighting="type")
    metric_id = "vad.synthetic_vad_phase2.valence.mean"
    token = next(row for row in token_rows if row.metric_id == metric_id)
    type_weighted = next(row for row in type_rows if row.metric_id == metric_id)

    assert token.denominator_b != type_weighted.denominator_b
    assert token.value_b != type_weighted.value_b


def test_comparison_rejects_mismatched_configuration(
    poem_comparison,
) -> None:
    mismatched = WorkspaceAnalysis(
        request=AnalysisRequest(
            **{
                **poem_comparison.second.request.__dict__,
                "minimum_match_requirement": 9,
            }
        ),
        document=poem_comparison.second.document,
        results=poem_comparison.second.results,
        comparison=poem_comparison.second.comparison,
        poem_document=poem_comparison.second.poem_document,
    )
    with pytest.raises(ValueError, match="shared configuration"):
        build_poem_comparison(poem_comparison.first, mismatched)


def test_comparison_csv_and_docx_exports_are_auditable(poem_comparison) -> None:
    csv_content = export_poem_comparison_csv(poem_comparison)
    rows = list(
        csv.DictReader(io.StringIO(csv_content.decode("utf-8-sig")))
    )

    assert rows
    assert rows[0]["poem_a_title"] == "Poem A"
    assert rows[0]["poem_b_title"] == "Poem B"
    assert "difference_b_minus_a" in rows[0]
    assert "poem_a_denominator" in rows[0]
    assert "poem_b_coverage" in rows[0]

    docx_content = export_poem_comparison_docx(poem_comparison)
    with zipfile.ZipFile(io.BytesIO(docx_content)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Contrastive Evaluation Report" in document_xml
    assert "Poem A compared with Poem B" in document_xml


def test_comparison_set_supports_three_poems_and_descriptive_ranges(
    poem_comparison_set,
) -> None:
    rows = comparison_set_rows(poem_comparison_set)
    mean = next(
        row
        for row in rows
        if row.metric_id == "vad.synthetic_vad_phase2.valence.mean"
    )
    values = [float(value.value) for value in mean.values]

    assert len(mean.values) == 3
    assert mean.contributing_poem_count == 3
    assert mean.numeric_mean == pytest.approx(sum(values) / 3)
    assert mean.numeric_population_standard_deviation is not None
    assert mean.numeric_range == pytest.approx(max(values) - min(values))


def test_comparison_set_enforces_two_to_ten_poem_boundary(
    poem_comparison_set,
) -> None:
    analyses = poem_comparison_set.analyses

    with pytest.raises(ValueError, match="between 2 and 10"):
        build_poem_comparison_set(analyses[:1])
    with pytest.raises(ValueError, match="between 2 and 10"):
        build_poem_comparison_set(analyses * 4)


def test_comparison_set_exports_are_long_form_without_pairwise_differences(
    poem_comparison_set,
) -> None:
    csv_content = export_poem_comparison_set_csv(poem_comparison_set)
    rows = list(csv.DictReader(io.StringIO(csv_content.decode("utf-8-sig"))))

    assert rows
    assert {row["poem_title"] for row in rows} == {
        "Poem A",
        "Poem B",
        "Poem C",
    }
    assert "equal_poem_mean" in rows[0]
    assert "poem_level_population_sd" in rows[0]
    assert "range_max_minus_min" in rows[0]
    assert "difference_b_minus_a" not in rows[0]

    docx_content = export_poem_comparison_set_docx(poem_comparison_set)
    with zipfile.ZipFile(io.BytesIO(docx_content)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Comparison set: Poem A, Poem B, Poem C" in document_xml


def test_comparison_display_values_are_arrow_safe() -> None:
    display = _arrow_safe_display_frame(
        pd.DataFrame(
            {
                "Poem A": [0.5, "accentual-syllabic", None],
                "Poem B": [0.6, "free verse", None],
                "B − A Difference": [0.1, None, None],
            }
        )
    )

    assert display["Poem A"].tolist() == [
        "0.5",
        "accentual-syllabic",
        "—",
    ]
    assert pa.Table.from_pandas(display).num_rows == 3


def test_comparison_set_display_values_are_arrow_safe() -> None:
    display = _arrow_safe_display_frame(
        pd.DataFrame(
            {
                "Poem One": [0.5, "accentual-syllabic"],
                "Poem Two": [0.6, "free verse"],
            }
        ),
        value_columns=("Poem One", "Poem Two"),
    )

    assert display["Poem One"].tolist() == ["0.5", "accentual-syllabic"]
    assert pa.Table.from_pandas(display).num_rows == 2


def test_comparison_report_map_matches_single_poem_structure() -> None:
    assert _REPORT_SECTIONS == (
        "Overview",
        "Affective Evidence",
        "Lexical Character, Imagery & Embodiment",
        "Sound & Form",
        "Structure",
        "VerseMap",
        "Evidence & Diagnostics",
        "Export & Help",
    )
    assert _report_location("vad.source.valence.mean") == (
        "Affective Evidence",
        "VAD Profile",
    )
    assert _report_location("sensorimotor.visual.mean") == (
        "Lexical Character, Imagery & Embodiment",
        "Sensorimotor Imagery & Embodiment",
    )


def test_comparison_metric_families_separate_means_loads_and_dispersion() -> None:
    assert _comparison_metric_family(
        "vad.source.valence.mean",
        "Mean normative valence",
        "VAD Profile",
    ) == "VAD Means"
    assert _comparison_metric_family(
        "vad.source.valence.population_sd",
        "Valence population standard deviation",
        "VAD Profile",
    ) == "Within-Poem Dispersion"
    assert _comparison_metric_family(
        "vad.source.valence.net_midpoint",
        "Valence — Net midpoint load",
        "VAD Profile",
    ) == "Cumulative Lexical Load"
    assert _report_location("meter.whole_poem_mean_fit") == (
        "Sound & Form",
        "Candidate Meter & Rhythmic Regularity",
    )


def test_comparison_value_chart_domain_is_fitted_around_observed_values() -> None:
    domain = _chart_domain([4.2, 4.4])

    assert domain[0] > 0
    assert domain[0] < 4.2
    assert domain[1] > 4.4
