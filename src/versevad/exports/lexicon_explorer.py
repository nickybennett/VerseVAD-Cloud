"""Printable narrative Word export for one Lexicon Explorer lookup."""

from __future__ import annotations

from typing import Mapping

from versevad.explorer import LexiconExplorerResult
from versevad.exports.docx_report import REPORT_PROFILES, build_narrative_report


def _display_value(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _add_row(
    rows: list[dict[str, str]],
    *,
    section: str,
    metric: str,
    value: object,
    unit: str = "",
    denominator: str = "",
    note: str = "",
) -> None:
    rows.append(
        {
            "section": section,
            "metric": metric,
            "value": _display_value(value),
            "unit_or_scale": unit,
            "denominator": denominator,
            "note": note,
        }
    )


def _add_source_provenance(
    rows: list[dict[str, str]],
    *,
    section: str,
    values: Mapping[str, object],
) -> None:
    for metric, value in values.items():
        _add_row(
            rows,
            section=section,
            metric=metric,
            value=value,
        )


def export_lexicon_explorer_docx(result: LexiconExplorerResult) -> bytes:
    """Return a deterministic printable report containing all lookup evidence."""

    rows: list[dict[str, str]] = []
    lookup_section = "Lookup"
    _add_row(rows, section=lookup_section, metric="Query", value=result.query)
    _add_row(
        rows,
        section=lookup_section,
        metric="Normalized lookup",
        value=result.normalized_query,
    )
    _add_row(
        rows,
        section=lookup_section,
        metric="Processing lemma",
        value=result.processing_lemma,
    )
    _add_row(
        rows,
        section=lookup_section,
        metric="Processing part of speech",
        value=result.processing_pos,
    )
    if not result.entries:
        _add_row(
            rows,
            section=lookup_section,
            metric="Affective-source lookup status",
            value="No exact or lemma-derived affective entry was found.",
        )

    for entry in result.entries:
        section = f"Affective evidence - {entry.lexicon}"
        _add_row(
            rows,
            section=section,
            metric="Matched source entry",
            value=entry.matched_term,
        )
        _add_row(
            rows,
            section=section,
            metric="Match method",
            value=entry.match_method,
        )
        _add_row(
            rows,
            section=section,
            metric="Value kind",
            value=entry.value_kind.replace("_", " ").title(),
        )
        if entry.original_scores is not None:
            assert entry.normalized_scores is not None
            for dimension in ("valence", "arousal", "dominance"):
                label = dimension.title()
                _add_row(
                    rows,
                    section=section,
                    metric=f"{label} - original",
                    value=getattr(entry.original_scores, dimension),
                    unit=entry.original_scale,
                )
                _add_row(
                    rows,
                    section=section,
                    metric=f"{label} - normalized",
                    value=getattr(entry.normalized_scores, dimension),
                    unit="derived 0-1",
                )
                if entry.standard_deviation is not None:
                    _add_row(
                        rows,
                        section=section,
                        metric=f"{label} rating standard deviation",
                        value=getattr(entry.standard_deviation, dimension),
                        unit=entry.original_scale,
                        note="Source-supplied participant-rating dispersion.",
                    )
                if entry.rater_count is not None:
                    _add_row(
                        rows,
                        section=section,
                        metric=f"{label} rater count",
                        value=getattr(entry.rater_count, dimension),
                        unit="source raters",
                    )
        if entry.value_kind == "categorical_association":
            _add_row(
                rows,
                section=section,
                metric="Source associations",
                value=(
                    ", ".join(entry.associations)
                    if entry.associations
                    else "None marked in the source entry"
                ),
            )
        for category, intensity in entry.intensities:
            _add_row(
                rows,
                section=section,
                metric=f"{category.title()} source intensity",
                value=intensity,
                unit=entry.original_scale,
            )

        _add_source_provenance(
            rows,
            section=f"Affective source provenance - {entry.lexicon}",
            values={
                "Resource version": entry.version,
                "Source rows": ", ".join(
                    str(value) for value in entry.source_rows
                ),
                "Original scale": entry.original_scale,
                "Normalization formula": entry.normalization_formula,
                "Adapter version": entry.adapter_version,
                "Source file": entry.source_file,
                "Source SHA-256": entry.source_sha256,
                "Citation": entry.citation,
            },
        )

    for average in result.component_averages:
        section = f"Derived component average - {average.lexicon}"
        _add_row(
            rows,
            section=section,
            metric="Components",
            value=" + ".join(average.components),
            note=(
                "VerseVAD-derived arithmetic mean; not a published phrase rating."
            ),
        )
        for dimension in ("valence", "arousal", "dominance"):
            label = dimension.title()
            _add_row(
                rows,
                section=section,
                metric=f"{label} - original component average",
                value=getattr(average.original_scores, dimension),
                unit=average.original_scale,
            )
            _add_row(
                rows,
                section=section,
                metric=f"{label} - normalized component average",
                value=getattr(average.normalized_scores, dimension),
                unit="derived 0-1",
            )

    if result.comparisons:
        section = "VerseVAD-derived cross-lexicon spread"
        for comparison in result.comparisons:
            label = comparison.dimension.title()
            _add_row(
                rows,
                section=section,
                metric=f"{label} entries compared",
                value=comparison.entry_count,
                unit="matched VAD entries",
            )
            _add_row(
                rows,
                section=section,
                metric=f"{label} normalized minimum",
                value=comparison.minimum,
                unit="derived 0-1",
            )
            _add_row(
                rows,
                section=section,
                metric=f"{label} normalized maximum",
                value=comparison.maximum,
                unit="derived 0-1",
            )
            _add_row(
                rows,
                section=section,
                metric=f"{label} normalized range",
                value=comparison.spread,
                unit="derived 0-1",
            )
            _add_row(
                rows,
                section=section,
                metric=f"{label} descriptive agreement",
                value=comparison.descriptive_agreement.title(),
                note=(
                    "VerseVAD range heuristic; not a source reliability statistic."
                ),
                )

    if result.vader_sentiment is not None:
        sentiment = result.vader_sentiment
        score = sentiment.document_score
        section = "Locally derived VADER sentiment"
        for metric, value, unit in (
            ("Positive proportion", score.positive_proportion, "proportion"),
            ("Neutral proportion", score.neutral_proportion, "proportion"),
            ("Negative proportion", score.negative_proportion, "proportion"),
            ("Compound score", score.compound_score, "-1 to 1"),
            (
                "Conventional compound label",
                score.threshold_label.title(),
                "configured threshold label",
            ),
        ):
            _add_row(
                rows,
                section=section,
                metric=metric,
                value=value,
                unit=unit,
                denominator="entered word or phrase",
            )
        _add_source_provenance(
            rows,
            section="VADER method provenance",
            values={
                "Module version": sentiment.module_result.module_version,
                "Package version": sentiment.package_version,
                "Configuration ID": sentiment.configuration.configuration_id,
                "Negative threshold": sentiment.configuration.negative_maximum,
                "Positive threshold": sentiment.configuration.positive_minimum,
                "Citation": sentiment.citation,
            },
        )

    if result.readability is not None:
        readability = result.readability
        summary = readability.summary
        section = "Locally derived word-level readability evidence"
        for metric, value, unit in (
            ("Readability word count", summary.word_count, "word units"),
            (
                "Alphabetic character count",
                summary.alphabetic_character_count,
                "Unicode alphabetic characters",
            ),
            ("Estimated syllable count", summary.syllable_count, "syllables"),
            (
                "Polysyllabic word count",
                summary.polysyllabic_word_count,
                "words with at least three estimated syllables",
            ),
            (
                "Mean syllables per word",
                summary.mean_syllables_per_word,
                "estimated syllables per word",
            ),
            (
                "Mean alphabetic characters per word",
                summary.mean_characters_per_word,
                "alphabetic characters per word",
            ),
            (
                "Pronunciation coverage",
                summary.pronunciation_coverage,
                "proportion",
            ),
        ):
            _add_row(
                rows,
                section=section,
                metric=metric,
                value=value,
                unit=unit,
                denominator="entered word or phrase",
            )
        for position, word in enumerate(readability.word_audit, start=1):
            audit_section = f"Readability word evidence - {position}"
            for metric, value in (
                ("Surface word", word.surface_form),
                ("Lookup form", word.lookup_form),
                (
                    "Alphabetic character count",
                    word.alphabetic_character_count,
                ),
                ("Estimated syllable count", word.syllable_count),
                ("Syllable method", word.syllable_method),
                (
                    "Pronunciation candidate count",
                    word.pronunciation_candidate_count,
                ),
                ("Polysyllabic", word.is_polysyllabic),
            ):
                _add_row(
                    rows,
                    section=audit_section,
                    metric=metric,
                    value=value,
                )
        _add_row(
            rows,
            section=section,
            metric="Document readability formulas",
            value="Not reported for an isolated lookup",
            note=(
                "Flesch, grade, Fog, ARI, Coleman-Liau, and SMOG are reserved "
                "for analyzed poems or texts with a defensible document scope."
            ),
        )
        _add_source_provenance(
            rows,
            section="Readability method provenance",
            values={
                "Module version": readability.module_result.module_version,
                "Configuration ID": readability.configuration.configuration_id,
                "Syllable lookup policy": (
                    readability.module_result.provenance.lookup_policy
                ),
            },
        )

    for entry in result.supplementary_entries:
        variant = f" - {entry.variant_label}" if entry.variant_label else ""
        section = f"Additional lexical evidence - {entry.resource}{variant}"
        _add_row(
            rows,
            section=section,
            metric="Construct",
            value=entry.construct.replace("_", " ").title(),
        )
        _add_row(
            rows,
            section=section,
            metric="Lookup status",
            value=entry.status.replace("_", " ").title(),
            note=entry.status_message,
        )
        _add_row(
            rows,
            section=section,
            metric="Matched source entry",
            value=entry.matched_term,
        )
        _add_row(
            rows,
            section=section,
            metric="Match method",
            value=entry.match_method,
        )
        for evidence in entry.values:
            _add_row(
                rows,
                section=section,
                metric=evidence.field,
                value=evidence.value,
                unit=evidence.unit,
                note=evidence.note,
            )

        _add_source_provenance(
            rows,
            section=f"Additional source provenance - {entry.resource}{variant}",
            values={
                "Resource version": entry.version,
                "Source rows": ", ".join(
                    str(value) for value in entry.source_rows
                ),
                "Adapter version": entry.adapter_version,
                "Source file": entry.source_file,
                "Source SHA-256": entry.source_sha256,
                "Additional source hashes": "; ".join(
                    f"{resource_id}: {sha256}"
                    for resource_id, sha256 in entry.source_hashes
                ),
                "Citation": entry.citation,
            },
        )

    if result.suggestions:
        _add_row(
            rows,
            section="Suggestions and notices",
            metric="Possible nearby forms",
            value=", ".join(result.suggestions),
            note="Suggestions are not substitutes and were not used as matches.",
        )
    for index, notice in enumerate(result.notices, start=1):
        _add_row(
            rows,
            section="Suggestions and notices",
            metric=f"Notice {index}",
            value=notice,
        )

    return build_narrative_report(
        profile=REPORT_PROFILES["lexicon_explorer"],
        summary_rows=rows,
        companion_csv_files=(),
        additional_paragraphs=(
            "This printable record reflects the installed local resources and "
            "the lookup methods shown for this query. VADER and word-level "
            "readability values are local derived evidence, not published "
            "lexicon ratings. It does not alter poem or corpus analyses.",
        ),
    )


def lexicon_explorer_report_filename(query: str) -> str:
    """Return a portable, readable filename for one Explorer report."""

    stem = "".join(
        character if character.isalnum() else "_"
        for character in query.strip()
    )
    stem = "_".join(part for part in stem.split("_") if part)[:60]
    return f"VerseVAD_Lexicon_Explorer_{stem or 'lookup'}.docx"


__all__ = [
    "export_lexicon_explorer_docx",
    "lexicon_explorer_report_filename",
]
