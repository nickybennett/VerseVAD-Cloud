import csv
import io
import zipfile

import pytest
import pandas as pd
import pyarrow as pa

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.comparison import build_poem_comparison, comparison_rows
from versevad.exports.comparison import (
    export_poem_comparison_csv,
    export_poem_comparison_docx,
)
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import PreparedPoemPreprocessor, create_text_document
from versevad.ui.comparison import _arrow_safe_display_frame


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


def test_comparison_display_values_are_arrow_safe() -> None:
    display = _arrow_safe_display_frame(
        pd.DataFrame(
            {
                "Poem A": [0.5, "accentual-syllabic", None],
                "Poem B": [0.6, "free verse", None],
                "B minus A": [0.1, None, None],
            }
        )
    )

    assert display["Poem A"].tolist() == [
        "0.5",
        "accentual-syllabic",
        "—",
    ]
    assert pa.Table.from_pandas(display).num_rows == 3
