"""Generate small schema-v3 export packages for manual release QA."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.analysis_profiles import ProfileSelection
from versevad.application import AnalysisRequest, WorkspaceAnalysis, detailed_export_zip
from versevad.comparison import build_poem_comparison_set
from versevad.db import CorpusMetricRecord, CorpusTextRecord, ProjectRecord
from versevad.exports.comparison import export_poem_comparison_set_bundle
from versevad.exports.corpus_csv import build_corpus_export_bundle
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import (
    PreparedPoemPreprocessor,
    SpacyEnglishPreprocessor,
    create_text_document,
)


def workspace(processor: SpacyEnglishPreprocessor, key: str, title: str, text: str) -> WorkspaceAnalysis:
    document = create_text_document(key, title, text)
    poem = processor.process_document(document)
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        PreparedPoemPreprocessor(poem),
        minimum_match_requirement=1,
    )
    return WorkspaceAnalysis(
        request=AnalysisRequest(
            project_name="Export QA",
            title=title,
            original_text=text,
            lexicon_ids=(result.lexicon_metadata.lexicon_id,),
            minimum_match_requirement=1,
        ),
        document=document,
        results=(result,),
        comparison=compare_lexicons((result,)),
        poem_document=poem,
    )


def main(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    processor = SpacyEnglishPreprocessor()
    first = workspace(processor, "qa-a", "Night", "Dark night glows.\nBright joy rises.")
    second = workspace(processor, "qa-b", "Morning", "Bright joy glows.\nCalm light rises.")
    third = workspace(processor, "qa-c", "Threshold", "Fear falls.\nPeace and joy rise.")

    (output_dir / "single_complete_audit.zip").write_bytes(
        detailed_export_zip(first, use_cache=False, author="QA Poet")
    )
    comparison = build_poem_comparison_set((first, second, third))
    (output_dir / "comparison_complete_audit.zip").write_bytes(
        export_poem_comparison_set_bundle(
            comparison,
            selection=ProfileSelection(),
            export_mode="complete_audit",
        )
    )

    project = ProjectRecord(
        project_id="qa-corpus",
        title="Export QA Corpus",
        description="Small deterministic corpus used only for export QA.",
        researcher="QA Researcher",
        created_at="2026-08-13T00:00:00+00:00",
        updated_at="2026-08-13T00:00:00+00:00",
    )
    texts: list[CorpusTextRecord] = []
    metrics: list[CorpusMetricRecord] = []
    for index, (title, author, value, matched, eligible) in enumerate(
        (("Night", "QA Poet", 0.35, 8, 10), ("Morning", "QA Poet", 0.72, 9, 10)),
        start=1,
    ):
        text_id = f"qa-work-{index}"
        text = CorpusTextRecord(
            text_id=text_id,
            text_version_id=f"{text_id}:v1",
            project_id=project.project_id,
            title=title,
            source_name=f"{title}.txt",
            relative_path=f"{title}.txt",
            author=author,
            collection="Export QA",
            date_label="2026",
            genre="poem",
            notes="",
            custom_metadata={},
            original_text="Synthetic QA poem.",
            text_sha256=str(index) * 64,
            imported_at=project.created_at,
            updated_at=project.updated_at,
        )
        texts.append(text)
        metrics.append(
            CorpusMetricRecord(
                run_id=f"run-{index}",
                text_id=text_id,
                text_version_id=text.text_version_id,
                title=title,
                author=author,
                collection=text.collection,
                date_label=text.date_label,
                genre=text.genre,
                lexicon_id="nrc_vad_v2_1",
                lexicon="NRC VAD Lexicon v2.1",
                value_kind="continuous",
                metric="vad_mean",
                dimension="valence",
                category="",
                weighting="token",
                scale="normalized 0-1",
                denominator=f"{matched} matched observations",
                value=value,
                observations=matched,
                matched_tokens=matched,
                lexical_tokens=eligible,
                coverage=matched / eligible,
                completed_at=project.updated_at,
                analysis_view="stopwords_excluded",
            )
        )
    (output_dir / "corpus_complete_audit.zip").write_bytes(
        build_corpus_export_bundle(project, tuple(texts), tuple(metrics), ())
    )


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tmp" / "export_qa"
    main(destination)
