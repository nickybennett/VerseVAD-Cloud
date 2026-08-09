from __future__ import annotations

import io

from docx import Document

from versevad.exports.docx_report import build_comprehensive_analysis_report


def _csv(text: str) -> bytes:
    return text.strip().encode("utf-8") + b"\n"


def _document_text(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join((*paragraphs, *cells))


def _profile_csv() -> bytes:
    return _csv(
        """
profile_id,scope,weighting,module_id,source_id,source,metric_id,metric,value,median,population_standard_deviation,first_quartile,third_quartile,minimum,maximum,cumulative_value,value_per_100_observations,above_midpoint_load,below_midpoint_load,net_midpoint_load,absolute_midpoint_load,average_deviation_from_mean,observation_count,eligible_token_count,matched_token_count,unmatched_token_count,token_coverage,eligible_type_count,matched_type_count,unmatched_type_count,type_coverage,excluded_stopword_count,excluded_non_content_count,phrase_match_count,type_identity_rule,unit
stopword_excluded-token_weighted,stopword_excluded,token_weighted,vad,nrc_vad_v2_1,NRC VAD Lexicon v2.1,valence,Mean normative valence,0.572345,0.646111,0.188812,0.421111,0.711111,0.111111,0.922222,2.345678,8.687696,1.234567,0.567891,0.666676,1.802458,0.145678,27,31,27,4,0.870967,24,22,2,0.916667,5,0,1,lemma,normalized 0-1
stopword_excluded-token_weighted,stopword_excluded,token_weighted,concreteness,brysbaert_concreteness,Brysbaert ratings,concreteness,Mean concreteness,3.255555,3.100001,0.912345,2.500001,3.800001,1.500001,4.900001,97.666650,325.555500,,,,,0.711111,30,31,30,1,0.967742,24,23,1,0.958333,5,0,0,lemma,source 1-5
"""
    )


def test_current_view_comprehensive_report_is_readable_and_deterministic() -> None:
    files = {
        "profile_metrics_selected.csv": _profile_csv(),
        "readability_summary.csv": _csv(
            "section,metric,value,unit_or_scale,denominator,note\n"
            "VerseVAD Poetic Reading Ease,VV-PRE score,76.42891,0-100,one completed text,Accessible\n"
        ),
        "phase2_match_audit.csv": _csv("token,value\nhope,0.9\n"),
    }
    kwargs = dict(
        export_files=files,
        text_title="Example Poem",
        author="Example Author",
        analysis_timestamp="2026-08-09T08:30:00-04:00",
        export_mode="current_view",
        visible_section="Affective Evidence",
        workspace_label="Single Poem",
        text_id="text-1",
        result_id="version-1",
        source_sha256="abc123",
        analysis_profiles=("stopword_excluded-token_weighted",),
        active_preset="Full Poetic Analysis",
        software_version="1.0.0",
    )
    first = build_comprehensive_analysis_report(**kwargs)
    second = build_comprehensive_analysis_report(**kwargs)
    assert first == second
    text = _document_text(first)
    assert "Computational Poetics\nAnalysis Report" in text
    assert "Current View Report" in text
    assert "Example Author" in text
    assert "[Enter analyst name]" in text
    assert "[Enter research question]" in text
    assert "0.572" in text
    assert "Valence, Arousal, and Dominance" in text
    assert "Not reported" in text


def test_complete_audit_report_marks_uncalculated_modules_and_lists_audit_files() -> None:
    content = build_comprehensive_analysis_report(
        export_files={
            "profile_metrics_selected.csv": _profile_csv(),
            "profile_metrics_all_compatible.csv": _profile_csv(),
            "phase2_token_audit.csv": _csv("token,value\nhope,0.9\n"),
        },
        text_title="Example Poem",
        export_mode="complete_audit",
        software_version="1.0.0",
    )
    text = _document_text(content)
    assert "Complete Audit Report" in text
    assert "All Compatible Lexical Profiles" in text
    assert "Not calculated" in text
    assert "phase2_token_audit.csv" in text
    assert "full-precision" in text.lower()
