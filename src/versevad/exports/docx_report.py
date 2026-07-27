"""Shared deterministic narrative Word reports for VerseVAD exports."""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable, Mapping, Sequence

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_FIXED_CORE_DATE = datetime(2000, 1, 1, tzinfo=UTC)
_BLUE = "1F4E78"
_DARK_BLUE = "17365D"
_PALE_GRAY = "F2F4F7"


@dataclass(frozen=True, slots=True)
class NarrativeReportProfile:
    """Writing guidance for one exported analysis report."""

    title: str
    scope: str
    interpretation: str
    cautions: tuple[str, ...] = ()


REPORT_PROFILES: Mapping[str, NarrativeReportProfile] = {
    "concreteness": NarrativeReportProfile(
        "Concreteness Analysis Report",
        "This report summarizes matched normative concreteness ratings for the "
        "eligible language in the analyzed text.",
        "Higher source ratings indicate language judged as more concrete. Results "
        "describe the words covered by the resource; they do not determine a "
        "text's meaning or literary quality.",
        ("Unmatched items remain missing rather than being assigned a neutral value.",),
    ),
    "frequency": NarrativeReportProfile(
        "Word Frequency and Rarity Report",
        "This report summarizes SUBTLEX-US frequency evidence for eligible words "
        "in the analyzed text.",
        "Higher Zipf values indicate more frequent words in the reference corpus; "
        "lower values indicate rarer matched words.",
        ("Coverage and the configured eligibility scope should accompany comparisons.",),
    ),
    "aoa": NarrativeReportProfile(
        "Age of Acquisition Report",
        "This report summarizes Kuperman et al. normative age-of-acquisition "
        "ratings for matched words in the analyzed text.",
        "Higher values indicate later reported acquisition in the source norms. "
        "They are lexical norms, not estimates of a reader's actual age.",
        ("The source resource is principally a content-word resource.",),
    ),
    "vader_sentiment": NarrativeReportProfile(
        "VADER Sentiment Analysis Report",
        "This report summarizes offline VADER rule-based polarity evidence for "
        "the complete preserved text and its model-segmented sentences.",
        "Positive, neutral, and negative proportions describe VADER's raw lexical "
        "categories; compound is a rule-adjusted normalized composite.",
        (
            "VADER was designed for social-media sentiment and can misread poetic ambiguity, irony, persona, and historical usage.",
            "Its polarity outputs are not declarations of the poem's emotion or a reader's response.",
        ),
    ),
    "readability": NarrativeReportProfile(
        "Readability and Grade-Formula Report",
        "This report summarizes familiar English readability formulas using the "
        "shared sentence and lexical-token record plus auditable syllable estimates.",
        "The scores are prose-oriented orientation evidence; they are not literary "
        "quality judgments, reader diagnoses, or prescriptive grade requirements.",
        (
            "Poetic lineation, fragments, and deliberate syntactic disruption can make the formulas unstable.",
            "Out-of-dictionary syllables use an explicitly labeled orthographic heuristic unless a session override is supplied.",
        ),
    ),
    "pronunciation": NarrativeReportProfile(
        "Pronunciation and Stress Report",
        "This report summarizes dictionary-supported syllable and stress evidence "
        "for the analyzed text.",
        "Pronunciation results reflect the selected dictionary entry and any local "
        "overrides; poetic performance may legitimately differ.",
        ("Unresolved or ambiguous pronunciations reduce coverage.",),
    ),
    "meter": NarrativeReportProfile(
        "Meter and Scansion Report",
        "This report summarizes candidate metrical patterns and their alignment "
        "with the pronunciation-supported stress evidence.",
        "Meter labels are ranked analytical candidates, not declarations of a "
        "single correct performance.",
        (
            "Consult line-level candidates and alignment operations in the companion CSV files.",
            "Performance-aware alternatives are reported only when enabled and supported.",
        ),
    ),
    "phonology": NarrativeReportProfile(
        "Rhyme and Sound Pattern Report",
        "This report summarizes end rhyme, internal rhyme, alliteration, "
        "assonance, consonance, and pronunciation coverage.",
        "Sound-pattern classifications depend on dictionary pronunciations and "
        "the configured evidence thresholds.",
        ("Unresolved pronunciations can hide sound relationships.",),
    ),
    "lexical_style": NarrativeReportProfile(
        "Lexical Style Report",
        "This report summarizes lexical diversity, word length, line word count, "
        "and stanza word count.",
        "Diversity measures respond differently to text length and token order; "
        "compare like with like and retain the configured parameters.",
        ("A missing value means the configured calculation was unavailable.",),
    ),
    "poetry_id": NarrativeReportProfile(
        "PoetryID Report",
        "This report summarizes descriptive evidence from the PoetryID feature set.",
        "The reported features are aids to inspection and comparison, not a "
        "judgment of poetic identity, authorship, quality, or genre.",
        ("Interpret every value with its denominator and method information.",),
    ),
    "inherited_form": NarrativeReportProfile(
        "Inherited Form Analysis Report",
        "This report compares the poem with ten versioned, source-backed "
        "inherited-form profiles using line, stanza, rhyme, meter, syllable, "
        "refrain, and end-word evidence when available.",
        "The leading result is a potential structural match. Consistency and "
        "confidence are transparent rule-based indices, not probabilities or "
        "declarations of genre identity, quality, historical intention, or tradition.",
        (
            "Missing pronunciation, meter, or rhyme evidence remains missing and lowers evidence coverage.",
            "Traditional definitions describe conventions that admit historical, linguistic, and artistic variation.",
            "Volta, kigo, semantic autonomy, and other interpretive features are not guessed when they cannot be scored defensibly.",
        ),
    ),
    "lexicon_explorer": NarrativeReportProfile(
        "Lexicon Explorer Report",
        "This report records one local word-or-phrase lookup across the installed "
        "VerseVAD lexical and pronunciation resources.",
        "The values are decontextualized source ratings, associations, corpus "
        "frequency evidence, retrospective norms, or dictionary pronunciation "
        "candidates. They support inspection rather than determine contextual "
        "meaning.",
        (
            "Missing or unavailable evidence remains missing rather than receiving a neutral value.",
            "Normalized VAD comparisons do not make source samples interchangeable.",
            "Pronunciation entries are dictionary candidates, not definitive poetic performances.",
        ),
    ),
    "phase2": NarrativeReportProfile(
        "VerseVAD Analysis Report",
        "This report brings together the principal results available for the "
        "analyzed text. Detailed audit records remain in the companion CSV files.",
        "The report describes computational evidence. It should support, rather "
        "than replace, close reading and documented scholarly judgment.",
        (
            "Coverage varies by lexicon and pronunciation resource.",
            "Missing lexical matches remain missing rather than being treated as neutral.",
        ),
    ),
    "corpus": NarrativeReportProfile(
        "VerseVAD Corpus Report",
        "This report summarizes the works and compatible result records represented "
        "in the selected VerseVAD project.",
        "Corpus comparisons are descriptive and are most defensible when the works "
        "share compatible configurations, resources, and coverage.",
        ("Use the companion CSV files for complete work-level and audit data.",),
    ),
}


def _set_cell_shading(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_margins(cell, *, top: int, start: int, bottom: int, end: int) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for edge, value in (
        ("top", top),
        ("start", start),
        ("bottom", bottom),
        ("end", end),
    ):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def _set_table_width(table, widths: Sequence[int]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    properties = table._tbl.tblPr
    layout = properties.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        properties.append(layout)
    layout.set(qn("w:type"), "fixed")
    width = properties.find(qn("w:tblW"))
    if width is None:
        width = OxmlElement("w:tblW")
        properties.append(width)
    width.set(qn("w:w"), str(sum(widths)))
    width.set(qn("w:type"), "dxa")
    for row in table.rows:
        for cell, cell_width in zip(row.cells, widths, strict=True):
            cell.width = Inches(cell_width / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell, top=80, start=120, bottom=80, end=120)


def _add_page_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    run.font.size = Pt(9)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, separate, text, end))


def _configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1

    for name, size, color, before, after in (
        ("Title", 20, _DARK_BLUE, 0, 8),
        ("Heading 1", 16, _BLUE, 16, 8),
        ("Heading 2", 13, _BLUE, 12, 6),
        ("Heading 3", 12, _DARK_BLUE, 8, 4),
    ):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    _add_page_field(section.footer.paragraphs[0])


def _read_summary_rows(summary_csv: bytes) -> list[dict[str, str]]:
    text = summary_csv.decode("utf-8-sig")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _display_name(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "nan"} else text


def _metric_sentence(row: Mapping[str, str]) -> str:
    metric = _display_name(_clean(row.get("metric", "Metric")))
    value = _clean(row.get("value", "")) or "not available"
    unit = _clean(row.get("unit_or_scale", row.get("unit", "")))
    denominator = _clean(row.get("denominator", ""))
    note = _clean(row.get("note", row.get("plain_language_note", "")))
    sentence = f"{metric}: {value}"
    if unit:
        sentence += f" ({unit})"
    sentence += "."
    if denominator:
        sentence += f" Denominator: {denominator}."
    if note:
        sentence += f" {note}"
    return sentence


def _add_metadata_table(
    document: Document,
    metadata: Sequence[tuple[str, str]],
) -> None:
    rows = [(label, value) for label, value in metadata if _clean(value)]
    if not rows:
        return
    table = document.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for index, (label, value) in enumerate(rows):
        table.cell(index, 0).text = label
        table.cell(index, 1).text = value
        _set_cell_shading(table.cell(index, 0), _PALE_GRAY)
        table.cell(index, 0).paragraphs[0].runs[0].bold = True
    _set_table_width(table, (2300, 7060))


def _add_companion_table(document: Document, filenames: Sequence[str]) -> None:
    if not filenames:
        return
    document.add_heading("Companion data files", level=1)
    document.add_paragraph(
        "The Word report is a readable orientation. These CSV files preserve the "
        "tabular values, denominators, provenance, and audit evidence:"
    )
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "CSV file"
    table.cell(0, 1).text = "Purpose"
    for cell in table.rows[0].cells:
        _set_cell_shading(cell, _BLUE)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    _set_repeat_table_header(table.rows[0])
    for filename in filenames:
        cells = table.add_row().cells
        cells[0].text = filename
        stem = filename.removesuffix(".csv").replace("_", " ")
        cells[1].text = f"Machine-readable {stem} data."
    _set_table_width(table, (3900, 5460))


def _normalize_docx(package: bytes) -> bytes:
    """Return a byte-for-byte stable DOCX ZIP package."""

    source = io.BytesIO(package)
    target = io.BytesIO()
    with zipfile.ZipFile(source, "r") as archive, zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as output:
        for name in sorted(archive.namelist()):
            information = zipfile.ZipInfo(name, _FIXED_TIMESTAMP)
            information.compress_type = zipfile.ZIP_DEFLATED
            information.external_attr = archive.getinfo(name).external_attr
            output.writestr(information, archive.read(name))
    return target.getvalue()


def build_narrative_report(
    *,
    profile: NarrativeReportProfile,
    summary_rows: Iterable[Mapping[str, str]],
    companion_csv_files: Sequence[str],
    text_title: str = "",
    text_id: str = "",
    result_id: str = "",
    warnings: Sequence[str] = (),
    additional_paragraphs: Sequence[str] = (),
) -> bytes:
    """Build one accessible narrative report with stable package bytes."""

    document = Document()
    _configure_document(document)
    document.core_properties.title = profile.title
    document.core_properties.subject = "VerseVAD narrative analysis report"
    document.core_properties.author = "VerseVAD"
    document.core_properties.created = _FIXED_CORE_DATE
    document.core_properties.modified = _FIXED_CORE_DATE

    title = document.add_paragraph(style="Title")
    title.add_run(profile.title)
    strapline = document.add_paragraph("VerseVAD · Local analytical evidence")
    strapline.style = document.styles["Subtitle"]
    _add_metadata_table(
        document,
        (
            ("Text", text_title),
            ("Text ID", text_id),
            ("Result ID", result_id),
        ),
    )

    document.add_heading("Scope and interpretation", level=1)
    document.add_paragraph(profile.scope)
    document.add_paragraph(profile.interpretation)
    for paragraph in additional_paragraphs:
        if _clean(paragraph):
            document.add_paragraph(_clean(paragraph))

    rows = list(summary_rows)
    if rows:
        document.add_heading("Key findings", level=1)
        current_section = ""
        for row in rows:
            section = _clean(row.get("section", "")) or "summary"
            if section != current_section:
                document.add_heading(_display_name(section), level=2)
                current_section = section
            document.add_paragraph(_metric_sentence(row))
    else:
        document.add_heading("Key findings", level=1)
        document.add_paragraph("No summary rows were available for this report.")

    cautions = [*profile.cautions, *(_clean(item) for item in warnings)]
    cautions = [item for item in cautions if item]
    if cautions:
        document.add_heading("Coverage and cautions", level=1)
        for caution in cautions:
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.add_run(caution)

    _add_companion_table(document, companion_csv_files)
    document.add_heading("How to cite and reproduce", level=1)
    document.add_paragraph(
        "Retain this report with its companion CSV files. Record the VerseVAD "
        "version, configuration identifiers, resource names and hashes, and any "
        "local overrides shown in the exported data."
    )

    output = io.BytesIO()
    document.save(output)
    return _normalize_docx(output.getvalue())


def build_narrative_report_from_summary_csv(
    module_name: str,
    summary_csv: bytes,
    *,
    companion_csv_files: Sequence[str],
    text_title: str = "",
    text_id: str = "",
    result_id: str = "",
    warnings: Sequence[str] = (),
    additional_paragraphs: Sequence[str] = (),
) -> bytes:
    """Build a report from any VerseVAD summary CSV using a named profile."""

    return build_narrative_report(
        profile=REPORT_PROFILES[module_name],
        summary_rows=_read_summary_rows(summary_csv),
        companion_csv_files=companion_csv_files,
        text_title=text_title,
        text_id=text_id,
        result_id=result_id,
        warnings=warnings,
        additional_paragraphs=additional_paragraphs,
    )
