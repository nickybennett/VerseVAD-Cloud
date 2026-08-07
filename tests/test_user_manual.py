from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


ROOT = Path(__file__).parents[1]
MANUAL = ROOT / "docs" / "VerseVAD_User_Manual.docx"
SOURCE = ROOT / "docs" / "VerseVAD_User_Manual_Source.md"
VALUES_GUIDE = ROOT / "docs" / "VerseVAD_Values_and_Terminology_Guide.docx"
VALUES_SOURCE = ROOT / "docs" / "VerseVAD_Values_and_Terminology_Guide_Source.md"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = f"{{{NS['w']}}}"


def _xml(package: ZipFile, member: str):
    return ElementTree.fromstring(package.read(member))


def _document_text(path: Path) -> tuple[ZipFile, ElementTree.Element, str]:
    package = ZipFile(path)
    document = _xml(package, "word/document.xml")
    text = "".join(element.text or "" for element in document.iter(f"{W}t"))
    return package, document, text


def _assert_current_document(text: str) -> None:
    assert "{{VERSION}}" not in text
    assert "{{DATE}}" not in text
    assert "```" not in text
    assert "Common meter" not in text
    assert "Stage 1" not in text
    assert "Stage 2" not in text


def test_comprehensive_user_manual_is_current_and_structurally_sound() -> None:
    assert MANUAL.is_file()
    assert MANUAL.stat().st_size > 40_000
    assert SOURCE.is_file()

    package, document, text = _document_text(MANUAL)
    with package:
        assert {
            "word/document.xml",
            "word/styles.xml",
            "word/numbering.xml",
            "word/header1.xml",
            "word/footer1.xml",
        }.issubset(package.namelist())
        _assert_current_document(text)
        for required in (
            "The basic workflow",
            "Navigation and session behavior",
            "Analysis profiles and report profiles",
            "All lexical tokens",
            "Stopword-excluded",
            "Content words only",
            "Token-weighted",
            "Type-weighted",
            "Fixed analytical profiles",
            "Analyze a poem",
            "Interactive Annotation",
            "Resolve pronunciation",
            "Compare two to ten poems",
            "Other Text",
            "Saved Projects and corpus analysis",
            "Personal Corpus",
            "Reference Corpora and Corpus Browser",
            "VerseMap",
            "Lexicon Explorer",
            "Form Library and inherited-form results",
            "Analysis Library and research notes",
            "Read coverage and missingness",
            "Understand common statistics",
            "Export Current View and Export Complete Audit",
            "Classic, Dark, Lavender, Ocean, Crimson, and Forest",
            "REPRODUCIBILITY_README.txt",
            "FILE_INVENTORY.txt",
        ):
            assert required in text

        section = document.find(".//w:sectPr", NS)
        assert section is not None
        page_size = section.find("w:pgSz", NS)
        page_margins = section.find("w:pgMar", NS)
        assert page_size is not None
        assert page_size.get(f"{W}w") == "12240"
        assert page_size.get(f"{W}h") == "15840"
        assert page_margins is not None
        for side in ("top", "right", "bottom", "left"):
            assert page_margins.get(f"{W}{side}") == "1440"

        numbering = _xml(package, "word/numbering.xml")
        formats = {
            element.get(f"{W}val")
            for element in numbering.iter(f"{W}numFmt")
        }
        assert {"bullet", "decimal"}.issubset(formats)


def test_values_guide_defines_current_terms_and_formulas() -> None:
    assert VALUES_GUIDE.is_file()
    assert VALUES_GUIDE.stat().st_size > 35_000
    assert VALUES_SOURCE.is_file()

    package, _document, text = _document_text(VALUES_GUIDE)
    with package:
        _assert_current_document(text)
        for required in (
            "Valence, Arousal, and Dominance",
            "Global Lexical Scopes",
            "Stopword",
            "Scope-Relative Coverage",
            "Token-Weighted and Type-Weighted Statistics",
            "Part-of-Speech Profiles",
            "Dispersion of Matched Ratings",
            "Cumulative Normative Lexical Load",
            "Above-Midpoint Load",
            "Below-Midpoint Load",
            "Net Midpoint Load",
            "Absolute Midpoint Load",
            "Average Deviation from Poem Mean",
            "Positive and Negative Sentiment Associations",
            "VADER Rule-Based Polarity",
            "Lexical Trajectory",
            "Readability and Grade-Level Formulas",
            "Review Decisions and Scenarios",
            "Worked Examples",
            "How to Report a Result",
            "mean_token = sum(x_i) / N",
            "absolute = above + below",
            "Normative Lexical Concreteness",
            "SUBTLEX-US Zipf Frequency and Rarity",
            "Retrospective Normative Lexical Age of Acquisition",
            "Dictionary Pronunciation, Syllables, and Lexical Stress",
            "Candidate Meter and Fit",
            "Rhyme and Recurring Phonological Patterns",
            "slant_similarity = 0.35(stressed_vowel)",
            "Lexical Diversity, Word Length, and Structural Word Counts",
            "MATTR(w) = mean",
            "HD-D = sum(P(type observed)",
            "PoetryID Candidate Lexical-Affective Profiles",
            "3 x 3 x 3 = 27",
            "relative affinities are not probabilities",
            "Performance-Aware Meter Realization",
            "realization_score = bounded weighted component evidence",
        ):
            assert required in text
