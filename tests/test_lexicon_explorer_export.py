from __future__ import annotations

import io
from dataclasses import replace

from docx import Document

from versevad.dictionary import lookup_open_english_wordnet
from versevad.explorer import (
    SupplementaryEvidenceValue,
    SupplementaryExplorerEntry,
    explore_loaded_lexicons,
)
from versevad.exports.lexicon_explorer import (
    export_lexicon_explorer_docx,
    lexicon_explorer_report_filename,
)
from versevad.phase2_validation import phase2_synthetic_vad_lexicon


def test_lexicon_explorer_word_report_is_complete_and_deterministic(
    preprocessor,
) -> None:
    base = explore_loaded_lexicons(
        "bright",
        (phase2_synthetic_vad_lexicon(),),
        preprocessor,
    )
    result = replace(
        base,
        supplementary_entries=(
            SupplementaryExplorerEntry(
                resource_id="synthetic-frequency",
                resource="Synthetic Frequency",
                construct="frequency",
                status="matched",
                status_message="A local frequency entry was found.",
                matched_term="bright",
                match_method="exact entry",
                variant_label="",
                source_rows=(17,),
                values=(
                    SupplementaryEvidenceValue(
                        "Zipf value",
                        4.25,
                        "synthetic Zipf",
                    ),
                    SupplementaryEvidenceValue(
                        "Dominant source POS",
                        "Adjective",
                    ),
                ),
                source_file="synthetic_frequency.csv",
                source_sha256="a" * 64,
                source_hashes=(),
                version="synthetic-v1",
                adapter_version="1.0.0",
                citation="Synthetic export test source.",
            ),
        ),
        notices=("Synthetic lookup notice.",),
        dictionary=lookup_open_english_wordnet(
            "bright",
            lemma="bright",
            processing_pos="ADJ",
        ),
    )

    first = export_lexicon_explorer_docx(result)
    second = export_lexicon_explorer_docx(result)

    assert first == second
    assert first.startswith(b"PK")
    assert lexicon_explorer_report_filename("bright light") == (
        "VerseVAD_Lexicon_Explorer_bright_light.docx"
    )

    document = Document(io.BytesIO(first))
    content = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert document.core_properties.title == "Lexicon Explorer Report"
    assert "Query: bright." in content
    assert "Matched Source Entry: bright." in content
    assert "Dictionary Sense 1 - Adjective" in content
    assert "Open English WordNet" in content
    assert "CC BY 4.0" in content
    assert "Valence - Original: 8 (1 to 9)." in content
    assert "Valence - Normalized: 0.875 (derived 0-1)." in content
    assert "Zipf Value: 4.25 (synthetic Zipf)." in content
    assert "Dominant Source Pos: Adjective." in content
    assert "Positive Proportion:" in content
    assert "Compound Score:" in content
    assert "Readability Word Count: 1 (word units)." in content
    assert "Estimated Syllable Count: 1 (syllables)." in content
    assert "Document Readability Formulas: Not reported for an isolated lookup." in content
    assert "Synthetic export test source." in content
    assert "Notice 1: Synthetic lookup notice." in content
    assert "Missing or unavailable evidence remains missing" in content
