from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


ROOT = Path(__file__).parents[1]
MANUAL = ROOT / "docs" / "VerseVAD_User_Manual.docx"
SOURCE = ROOT / "docs" / "VerseVAD_User_Manual_Source.md"
VALUES_GUIDE = ROOT / "docs" / "VerseVAD_Values_and_Terminology_Guide.docx"
VALUES_SOURCE = (
    ROOT / "docs" / "VerseVAD_Values_and_Terminology_Guide_Source.md"
)
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = f"{{{NS['w']}}}"


def _xml(package: ZipFile, member: str):
    return ElementTree.fromstring(package.read(member))


def test_comprehensive_user_manual_is_current_and_structurally_sound() -> None:
    assert MANUAL.is_file()
    assert MANUAL.stat().st_size > 40_000
    assert SOURCE.is_file()

    with ZipFile(MANUAL) as package:
        names = set(package.namelist())
        assert {
            "word/document.xml",
            "word/styles.xml",
            "word/numbering.xml",
            "word/header1.xml",
            "word/footer1.xml",
        }.issubset(names)
        document = _xml(package, "word/document.xml")
        text = "".join(element.text or "" for element in document.iter(f"{W}t"))
        assert "{{VERSION}}" not in text
        assert "{{DATE}}" not in text
        assert "```" not in text
        assert "Common meter" not in text
        assert "meter_schemes.csv" not in text
        assert "permit = P ER0 M IH1 T | verb reading in this line" in text
        for required in (
            "Dual VAD reporting and stopwords",
            "Single Poem and Other Text Workspaces",
            "Saved Projects Workspace",
            "Analyze",
            "Collections",
            "Explore",
            "Learn",
            "Full Poetic Analysis",
            "Computational Close Reading",
            "Teaching/Introductory",
            "Classic, Dark, Lavender, Ocean, Crimson, and Forest",
            "Affective Evidence",
            "Evidence & Diagnostics",
            "Lexicon Explorer",
            "Mathematical formulas",
            "Midpoint-centered contribution",
            "Delete a project",
            "VerseVAD_analysis_report.docx",
            "132 whitespace-containing rows in NRC VAD v1",
            "Review decisions and named scenarios",
            "Positive and negative sentiment associations",
            "Installation Check",
            "Part-of-speech profile",
            "Detailed Model-Tag Breakdown",
            "Concreteness Profile",
            "Normative lexical concreteness",
            "concreteness_token_audit.csv",
            "39,954 rows",
            "Frequency & Rarity",
            "Content words only",
            "frequency_token_audit.csv",
            "74,286 word-form rows",
            "NOUN, VERB, ADJ, and ADV",
            "Acquisition and Readability section",
            "Retrospective normative lexical Age of Acquisition",
            "aoa_token_audit.csv",
            "31,124 unique nonblank word rows",
            "not diagnostic of cognitive impairment or decline",
            "VADER reports raw positive",
            "vader_sentiment_summary.csv",
            "Lexical Trajectory section",
            "lexical_trajectory.csv",
            "Flesch-Kincaid Grade",
            "readability_word_audit.csv",
            "Dictionary pronunciation, syllables, and lexical stress",
            "Pronunciation & Prosody",
            "pronunciation_token_audit.csv",
            "provisional—not confirmed",
            "Leave explicitly unresolved",
            "Approve or edit for this session",
            "Candidate meter and rhythmic regularity",
            "Meter & Rhythm section",
            "meter_alignment_operations.csv",
            "meter_line_fit = max(0, 1 - selected_alignment_cost",
            "Rhyme and phonological patterns",
            "Rhyme & Recurring Sound section",
            "rhyme_pairs.csv",
            "slant_similarity = 0.35(stressed_vowel)",
            "dictionary-based ending evidence produced an ABAB",
            "Lexical diversity, word length, and structural word counts",
            "Lexical and Structural Measures section",
            "Structural Count Summary",
            "average nonblank physical lines per stanza",
            "population standard deviation",
            "lexical_style_lines.csv",
            "MATTR(w) = mean",
            "normalized observed surface forms",
            "Additional module corpus results",
            "corpus_module_*.csv",
            "ordered pooled token evidence",
            "Additional lexical evidence",
            "Rule-based sentiment and readability evidence",
            "Document-level Flesch Reading Ease",
            "Resource unavailable",
            "every exact CMUdict pronunciation candidate",
            "PoetryID section",
            "all 27 centroid distances",
            "poetry_id_neighbors.csv",
            "does not generate JSON",
            "GPL-3.0-only",
            "docs/resource-installation.md",
            "docs/macos-installation.md",
            "setup_macos.command",
            "start_versevad.command",
            "Current Safari",
            "Performance-aware realization",
            "meter_realizations.csv",
            "meter_scholar_revisions.csv",
            "If the VerseVAD folder is moved",
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

        tables = document.findall(".//w:tbl", NS)
        # Callouts are accessible bordered paragraphs rather than layout tables.
        assert len(tables) >= 9
        for table in tables:
            width = table.find("w:tblPr/w:tblW", NS)
            indent = table.find("w:tblPr/w:tblInd", NS)
            grid_widths = [
                int(column.get(f"{W}w"))
                for column in table.findall("w:tblGrid/w:gridCol", NS)
            ]
            assert width is not None
            assert width.get(f"{W}type") == "dxa"
            assert int(width.get(f"{W}w")) == 9360
            assert indent is not None
            assert int(indent.get(f"{W}w")) == 120
            assert sum(grid_widths) == 9360
            for row in table.findall("w:tr", NS):
                cell_widths = [
                    int(cell.get(f"{W}w"))
                    for cell in row.findall("w:tc/w:tcPr/w:tcW", NS)
                ]
                assert cell_widths == grid_widths

        numbering = _xml(package, "word/numbering.xml")
        formats = {
            element.get(f"{W}val")
            for element in numbering.iter(f"{W}numFmt")
        }
        assert {"bullet", "decimal"}.issubset(formats)
        level_texts = {
            element.get(f"{W}val")
            for element in numbering.iter(f"{W}lvlText")
        }
        assert "\u2022" in level_texts
        children = list(numbering)
        first_number_index = next(
            index
            for index, element in enumerate(children)
            if element.tag == f"{W}num"
        )
        assert all(
            element.tag == f"{W}abstractNum"
            for element in children[:first_number_index]
        )
        assert all(
            element.tag == f"{W}num"
            for element in children[first_number_index:]
        )
        decimal_restarts = numbering.findall(
            ".//w:num/w:lvlOverride/w:startOverride",
            NS,
        )
        assert decimal_restarts
        assert all(
            element.get(f"{W}val") == "1"
            for element in decimal_restarts
        )


def test_beginner_values_guide_defines_requested_terms_and_formulas() -> None:
    assert VALUES_GUIDE.is_file()
    assert VALUES_GUIDE.stat().st_size > 35_000
    assert VALUES_SOURCE.is_file()

    with ZipFile(VALUES_GUIDE) as package:
        document = _xml(package, "word/document.xml")
        text = "".join(element.text or "" for element in document.iter(f"{W}t"))
        assert "{{VERSION}}" not in text
        assert "{{DATE}}" not in text
        assert "```" not in text
        assert "Common meter" not in text
        for required in (
            "Valence, Arousal, and Dominance",
            "Stopwords and the Two VAD Views",
            "Token-Weighted and Type-Weighted Statistics",
            "Part-of-Speech Profiles",
            "Detailed Model Tags",
            "Dispersion of Matched Ratings",
            "Stopword Sensitivity",
            "Cumulative Normative Lexical Load",
            "Above-Midpoint Load",
            "Below-Midpoint Load",
            "Net Midpoint Load",
            "Absolute Midpoint Load",
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
            "Concreteness orientation band",
            "mean normative lexical concreteness of 3.7",
            "SUBTLEX-US Zipf Frequency and Rarity",
            "Content words only",
            "median SUBTLEX-US Zipf value of 4.3",
            "about one point represents a tenfold",
            "Retrospective Normative Lexical Age of Acquisition",
            "AoA orientation band",
            "mean retrospective normative lexical AoA of 7.2 years",
            "Numeric-response proportion",
            "Dictionary Pronunciation, Syllables, and Lexical Stress",
            "poem-specific ARPAbet override",
            "provisional—not confirmed",
            "Provisional G2P candidate",
            "Candidate Meter and Fit",
            "Rhyme and Recurring Phonological Patterns",
            "slant_similarity = 0.35(stressed_vowel)",
            "Example J: Exact, Slant, and Eye-Rhyme Evidence",
            "dictionary-based ending evidence produced an ABAB",
            "Meter fit",
            "Lexical Diversity, Word Length, and Structural Word Counts",
            "MATTR(w) = mean",
            "HD-D = sum(P(type observed)",
            "Example K: Lexical Diversity and Structural Word Counts",
            "Line word counts are 3, 2, 0, 2",
            "Lexical-style word unit",
            "Additional-module collection summaries",
            "Equal-work module mean",
            "Ordered pooled-token result",
            "Resource unavailable",
            "PoetryID Candidate Lexical-Affective Profiles",
            "3 x 3 x 3 = 27",
            "relative affinities are not probabilities",
            "PoetryID centroid",
            "Interface Terms Are Not Analytical Terms",
            "Classic, Dark, Lavender, Ocean, Crimson, and Forest",
            "Performance-Aware Meter Realization",
            "Declared meter style profile",
            "realization_score = bounded weighted component evidence",
        ):
            assert required in text
