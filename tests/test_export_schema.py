import csv
import io

import pytest
from docx import Document

from versevad.exports.canonical_schema import (
    EXPORT_METADATA_PATH,
    EXPORT_SCHEMA_VERSION,
    MASTER_METRICS_PATH,
    standardize_export_files,
)


def _csv_bytes(rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _docx_bytes() -> bytes:
    document = Document()
    document.add_heading("Synthetic report", level=1)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _master(files: dict[str, bytes]) -> list[dict[str, str]]:
    return list(
        csv.DictReader(
            io.StringIO(files[MASTER_METRICS_PATH].decode("utf-8-sig"))
        )
    )


def test_schema_v3_normalizes_equivalent_work_metrics_across_analysis_modes() -> None:
    value = "0.625"
    single = standardize_export_files(
        {
            "profile_metrics_all_compatible.csv": _csv_bytes(
                [{
                    "module_id": "vad",
                    "metric_id": "valence_mean",
                    "metric": "Mean normative valence",
                    "source_id": "nrc_vad_v2_1",
                    "source": "NRC VAD Lexicon v2.1",
                    "scope": "stopwords_excluded",
                    "weighting": "token-weighted",
                    "value": value,
                    "unit": "normalized 0-1",
                    "denominator": "8 rated observations",
                    "eligible_token_count": "10",
                    "matched_token_count": "8",
                    "token_coverage": "0.8",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="single_poem",
        export_mode="complete_audit",
        analysis_id="single",
        work_id="same-work",
        title="Same Poem",
        author="Poet",
        main_report_path="report.docx",
        main_report_name="Analysis_Report.docx",
    )
    comparison = standardize_export_files(
        {
            "comparison_stopwords_excluded_token.csv": _csv_bytes(
                [{
                    "poem_id": "same-work",
                    "poem_title": "Same Poem",
                    "author": "Poet",
                    "metric_id": "vad.nrc_vad_v2_1.valence.mean",
                    "metric": "Mean normative valence",
                    "source": "NRC VAD Lexicon v2.1",
                    "analysis_view": "stopwords_excluded",
                    "weighting": "token-weighted",
                    "value": value,
                    "unit_or_scale": "normalized 0-1",
                    "denominator": "8 of 10 eligible tokens matched",
                    "coverage": "0.8",
                    "note": "",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="compare_poems",
        export_mode="complete_audit",
        analysis_id="comparison",
        title="Same Poem comparison",
        main_report_path="report.docx",
        main_report_name="Comparison_Report.docx",
    )
    corpus = standardize_export_files(
        {
            "corpus_vad_metrics.csv": _csv_bytes(
                [{
                    "text_id": "same-work",
                    "title": "Same Poem",
                    "author": "Poet",
                    "collection": "",
                    "date_label": "",
                    "genre": "",
                    "lexicon_id": "nrc_vad_v2_1",
                    "lexicon": "NRC VAD Lexicon v2.1",
                    "analysis_view": "stopwords_excluded",
                    "weighting": "token-weighted",
                    "dimension": "valence",
                    "category": "",
                    "metric": "vad_mean",
                    "value": value,
                    "scale": "normalized 0-1",
                    "denominator": "8 rated observations",
                    "observations": "8",
                    "eligible_token_count": "10",
                    "matched_token_count": "8",
                    "token_coverage": "0.8",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="corpus",
        export_mode="complete_audit",
        analysis_id="corpus",
        title="Corpus",
        main_report_path="report.docx",
        main_report_name="Corpus_Report.docx",
    )

    rows = [_master(files)[0] for files in (single, comparison, corpus)]
    identity = (
        "metric_id",
        "resource_id",
        "lexical_scope",
        "weighting",
        "unit",
        "value",
    )
    assert [{field: row[field] for field in identity} for row in rows] == [
        {
            "metric_id": "vad.valence.mean",
            "resource_id": "nrc_vad_v2_1",
            "lexical_scope": "stopword_excluded",
            "weighting": "token",
            "unit": "normalized 0-1",
            "value": value,
        }
    ] * 3
    assert all(row["eligible_token_count"] == "10" for row in rows)
    assert all(row["matched_token_count"] == "8" for row in rows)
    assert all(row["unmatched_token_count"] == "2" for row in rows)
    assert all(row["token_coverage"] == "0.8" for row in rows)
    for files, mode in zip(
        (single, comparison, corpus),
        ("single_poem", "compare_poems", "corpus"),
        strict=True,
    ):
        metadata = list(
            csv.DictReader(
                io.StringIO(files[EXPORT_METADATA_PATH].decode("utf-8-sig"))
            )
        )[0]
        assert metadata["export_schema_version"] == EXPORT_SCHEMA_VERSION
        assert metadata["analysis_mode"] == mode
        assert not any(path.endswith(".json") for path in files)


def test_type_weighted_comparison_counts_stay_in_type_fields() -> None:
    files = standardize_export_files(
        {
            "comparison_content_words_type.csv": _csv_bytes(
                [{
                    "poem_id": "work",
                    "poem_title": "Poem",
                    "metric_id": "concreteness.concreteness_mean",
                    "metric": "Mean concreteness",
                    "source": "Brysbaert concreteness ratings",
                    "analysis_view": "content words only",
                    "weighting": "type-weighted",
                    "value": "3.1",
                    "unit_or_scale": "source 1-5",
                    "denominator": "7 of 9 eligible types matched",
                    "coverage": "0.7777777778",
                    "note": "",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="compare_poems",
        export_mode="current_view",
        analysis_id="comparison",
        title="Comparison",
        main_report_path="report.docx",
        main_report_name="Comparison_Report.docx",
    )
    row = _master(files)[0]
    assert row["eligible_type_count"] == "9"
    assert row["matched_type_count"] == "7"
    assert row["unmatched_type_count"] == "2"
    assert float(row["type_coverage"]) == pytest.approx(7 / 9)
    assert row["eligible_token_count"] == ""
    assert row["token_coverage"] == ""


def test_category_proportion_never_leaks_into_canonical_coverage() -> None:
    files = standardize_export_files(
        {
            "comparison_stopwords_excluded_token.csv": _csv_bytes(
                [{
                    "poem_id": "work",
                    "poem_title": "Poem",
                    "metric_id": "emotion.nrc_emotion.anger.proportion",
                    "metric": "Anger association",
                    "source": "NRC Emotion Lexicon",
                    "analysis_view": "stopwords_excluded",
                    "weighting": "token-weighted",
                    "value": "0.125",
                    "unit_or_scale": "proportion of eligible lexical evidence",
                    "denominator": "4 associated observations",
                    "coverage": "0.125",
                    "note": "",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="compare_poems",
        export_mode="complete_audit",
        analysis_id="comparison",
        title="Comparison",
        main_report_path="report.docx",
        main_report_name="Comparison_Report.docx",
    )
    row = _master(files)[0]
    assert row["value"] == "0.125"
    assert row["eligible_token_count"] == ""
    assert row["matched_token_count"] == ""
    assert row["token_coverage"] == ""


def test_category_value_and_resource_coverage_remain_independent() -> None:
    files = standardize_export_files(
        {
            "comparison_stopwords_excluded_token.csv": _csv_bytes(
                [{
                    "poem_id": "work",
                    "poem_title": "Poem",
                    "metric_id": "emotion.nrc_emotion.anger.proportion",
                    "metric": "Anger association",
                    "source": "NRC Emotion Lexicon",
                    "analysis_view": "stopwords_excluded",
                    "weighting": "token-weighted",
                    "value": "0.125",
                    "unit_or_scale": "proportion of eligible lexical evidence",
                    "denominator": "24 of 30 eligible tokens matched",
                    "coverage": "0.125",
                    "note": "",
                }]
            ),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="compare_poems",
        export_mode="complete_audit",
        analysis_id="comparison",
        title="Comparison",
        main_report_path="report.docx",
        main_report_name="Comparison_Report.docx",
    )
    row = _master(files)[0]
    assert row["value"] == "0.125"
    assert row["eligible_token_count"] == "30"
    assert row["matched_token_count"] == "24"
    assert row["unmatched_token_count"] == "6"
    assert row["token_coverage"] == "0.8"

    coverage_rows = list(
        csv.DictReader(
            io.StringIO(
                files["02_METRIC_TABLES/Coverage_and_Data_Quality.csv"].decode(
                    "utf-8-sig"
                )
            )
        )
    )
    assert len(coverage_rows) == 1
    assert coverage_rows[0]["Coverage"] == "0.8"


def test_corpus_readable_labels_are_concise_without_changing_identity_or_value() -> None:
    source_rows = [
        {
            "text_id": "work",
            "title": "Poem",
            "author": "Poet",
            "collection": "",
            "date_label": "",
            "genre": "",
            "lexicon_id": resource_id,
            "lexicon": resource_label,
            "analysis_view": "stopwords_excluded",
            "weighting": "token",
            "dimension": dimension,
            "category": "",
            "metric": metric,
            "value": value,
            "scale": unit,
            "denominator": "8 observations; 8/10 eligible tokens matched",
            "observations": "8",
            "eligible_token_count": "10",
            "matched_token_count": "8",
            "token_coverage": "0.8",
        }
        for resource_id, resource_label, dimension, metric, value, unit in (
            ("brysbaert-concreteness-2014", "Brysbaert concreteness ratings", "concreteness_mean", "concreteness_concreteness_mean_mean", "3.25", "source 1-5"),
            ("subtlex-us-zipf-official", "SUBTLEX-US Zipf frequencies", "frequency_mean", "frequency_frequency_mean_standard_deviation", "0.75", "Zipf"),
            ("kuperman-aoa-2012-erratum-supplement", "Kuperman Age of Acquisition ratings", "aoa_mean", "aoa_aoa_mean_mean", "6.5", "years"),
            ("lancaster-sensorimotor-2020", "Lancaster Sensorimotor Norms", "auditory", "sensorimotor_auditory_cumulative", "9.0", "summed ratings"),
            ("nrc_emotion_intensity_v1", "NRC Emotion Intensity Lexicon", "anger_intensity", "emotion_intensity_anger_intensity_standard_deviation", "0.12", "normalized 0-1"),
        )
    ]
    files = standardize_export_files(
        {"corpus_vad_metrics.csv": _csv_bytes(source_rows), "report.docx": _docx_bytes()},
        analysis_mode="corpus",
        export_mode="complete_audit",
        analysis_id="corpus",
        title="Corpus",
        main_report_path="report.docx",
        main_report_name="Corpus_Report.docx",
    )
    master = _master(files)
    assert [row["metric_label"] for row in master] == [
        "Mean Concreteness",
        "Frequency SD",
        "Mean Age of Acquisition",
        "Auditory Cumulative",
        "Anger Intensity SD",
    ]
    assert [row["value"] for row in master] == [row["value"] for row in source_rows]
    assert [row["legacy_metric_id"] for row in master] == [row["metric"] for row in source_rows]
    readable = "".join(
        files[path].decode("utf-8-sig")
        for path in (
            "02_METRIC_TABLES/Experience_and_Imagery_Corpus.csv",
            "02_METRIC_TABLES/Lexical_Accessibility_Corpus.csv",
            "02_METRIC_TABLES/Affect_Corpus.csv",
        )
    )
    assert "Concreteness Mean Concreteness" not in readable
    assert "Aoa Mean Aoa" not in readable
    assert "Sensorimotor Auditory" not in readable


def test_corpus_summary_preserves_equal_work_and_token_pool_values() -> None:
    files = standardize_export_files(
        {
            "corpus_vad_profiles.csv": _csv_bytes([{
                "lexicon_id": "nrc_vad_v2_1",
                "lexicon": "NRC VAD Lexicon v2.1",
                "analysis_view": "stopwords_excluded",
                "weighting": "token",
                "dimension": "valence",
                "work_weighted_volume_mean": "0.61",
                "token_weighted_volume_mean": "0.64",
                "works_included": "12",
                "matched_observations": "240",
                "lexical_tokens": "260",
                "volume_coverage": "0.9230769231",
            }]),
            "report.docx": _docx_bytes(),
        },
        analysis_mode="corpus",
        export_mode="complete_audit",
        analysis_id="corpus",
        title="Corpus",
        main_report_path="report.docx",
        main_report_name="Corpus_Report.docx",
    )
    summary = list(csv.DictReader(io.StringIO(files["02_METRIC_TABLES/Corpus_Summary.csv"].decode("utf-8-sig"))))
    assert len(summary) == 1
    assert summary[0]["Metric"] == "Mean Valence"
    assert summary[0]["Equal-work Value"] == "0.61"
    assert summary[0]["Token-pool Value"] == "0.64"
    assert {row["metric_id"] for row in _master(files)} == {"vad.valence.mean"}
