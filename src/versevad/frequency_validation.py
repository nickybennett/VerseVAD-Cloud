"""Invented, hand-calculated validation for the SUBTLEX-US frequency module."""

from __future__ import annotations

import hashlib
import math
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from openpyxl import Workbook

from versevad.adapters.subtlex_us import REQUIRED_COLUMNS
from versevad.core import ModuleInput, ResourceSpec
from versevad.lexical_semantic.frequency import (
    FrequencyConfiguration,
    FrequencyMatchMethod,
    FrequencyModule,
)
from versevad.preprocessing import SpacyEnglishPreprocessor, create_text_document


def _row(
    term: str,
    zipf_value: float,
    dominant_pos: str,
) -> tuple[object, ...]:
    frequency_count = 10
    contextual_diversity_count = 8
    return (
        term,
        frequency_count,
        contextual_diversity_count,
        frequency_count,
        contextual_diversity_count,
        frequency_count / 51,
        math.log10(frequency_count + 1),
        contextual_diversity_count / 83.88,
        math.log10(contextual_diversity_count + 1),
        dominant_pos,
        frequency_count,
        1.0,
        dominant_pos,
        frequency_count,
        zipf_value,
    )


_ROWS = (
    _row("rareword", 2.0, "Noun"),
    _row("stone", 4.0, "Noun"),
    _row("run", 5.0, "Verb"),
    _row("the", 7.0, "Article"),
    _row("runs", 4.5, "Verb"),
    _row("bright", 4.2, "Adjective"),
    _row("swiftly", 3.5, "Adverb"),
    _row("and", 7.0, "Conjunction"),
    _row("she", 6.5, "Pronoun"),
    _row("can", 6.2, "Verb"),
    _row("under", 5.8, "Preposition"),
)
_TEXT = "rareword rareword\nstone stones\nrun quorvax"
_CONTENT_TEXT = "the stone runs bright swiftly and she can under"


@dataclass(frozen=True)
class SyntheticFrequencyValidation:
    eligible_tokens: int
    matched_tokens: int
    token_coverage: float | None
    median_zipf: float | None
    mean_zipf: float | None
    exact_tokens: int
    lemma_tokens: int
    unmatched_tokens: int
    content_scope_eligible_tokens: int
    content_scope_excluded_tokens: int
    source_unchanged: bool


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "out1g"
    sheet.append(REQUIRED_COLUMNS)
    for row in _ROWS:
        sheet.append(row)
    workbook.save(path)


def run_synthetic_frequency_validation(
) -> tuple[SyntheticFrequencyValidation, tuple[str, ...]]:
    """Run invented examples whose expected Zipf results can be checked by hand."""

    with tempfile.TemporaryDirectory(prefix="versevad-frequency-") as directory:
        root = Path(directory)
        source = root / "synthetic_subtlex_us.xlsx"
        _write_fixture(source)
        before = _sha256(source)
        resource = ResourceSpec(
            resource_id="synthetic-frequency-validation",
            display_name="Synthetic frequency validation fixture",
            relative_path=source.name,
            version="synthetic-v1",
            accepted_sha256=(before,),
            citation="Invented VerseVAD validation data.",
            license_notice="Synthetic data generated locally for validation.",
        )
        module = FrequencyModule(root, resource_spec=resource)
        processor = SpacyEnglishPreprocessor()
        poem = processor.process_document(
            create_text_document(
                "frequency-validation",
                "Invented frequency validation",
                _TEXT,
            )
        )
        result = module.analyze_detailed(
            ModuleInput.from_poem_document(poem),
            FrequencyConfiguration(exclude_proper_nouns=False),
        )

        content_poem = processor.process_document(
            create_text_document(
                "frequency-content-validation",
                "Invented content-scope validation",
                _CONTENT_TEXT,
            )
        )
        tags = {
            "the": "DET",
            "stone": "NOUN",
            "runs": "VERB",
            "bright": "ADJ",
            "swiftly": "ADV",
            "and": "CCONJ",
            "she": "PRON",
            "can": "AUX",
            "under": "ADP",
        }
        content_tokens = tuple(
            replace(token, part_of_speech=tags[token.normalized_form])
            for token in content_poem.tokens
        )
        content_result = module.analyze_detailed(
            ModuleInput(
                document=content_poem.source,
                tokens=content_tokens,
                preprocessing=content_poem.preprocessing,
            ),
            FrequencyConfiguration(
                exclude_proper_nouns=False,
                content_words_only=True,
            ),
        )
        after = _sha256(source)

    method_counts = {
        method: sum(row.match_method is method for row in result.token_audit)
        for method in FrequencyMatchMethod
    }
    report = SyntheticFrequencyValidation(
        eligible_tokens=result.summary.eligible_token_count,
        matched_tokens=result.summary.matched_token_count,
        token_coverage=result.summary.token_coverage,
        median_zipf=result.summary.statistics.median,
        mean_zipf=result.summary.statistics.mean,
        exact_tokens=method_counts[FrequencyMatchMethod.EXACT],
        lemma_tokens=method_counts[FrequencyMatchMethod.LEMMA],
        unmatched_tokens=method_counts[FrequencyMatchMethod.UNMATCHED],
        content_scope_eligible_tokens=(
            content_result.summary.eligible_token_count
        ),
        content_scope_excluded_tokens=sum(
            not row.eligible for row in content_result.token_audit
        ),
        source_unchanged=before == after,
    )

    problems = []
    expected = {
        "eligible_tokens": 6,
        "matched_tokens": 5,
        "exact_tokens": 4,
        "lemma_tokens": 1,
        "unmatched_tokens": 1,
        # The legacy module-local content_words_only flag is intentionally a
        # no-op. Content scope is now reconstructed from retained evidence.
        "content_scope_eligible_tokens": 9,
        "content_scope_excluded_tokens": 0,
    }
    for field, value in expected.items():
        if getattr(report, field) != value:
            problems.append(
                f"{field} was {getattr(report, field)!r}; expected {value!r}."
            )
    if report.token_coverage is None or not math.isclose(
        report.token_coverage, 5 / 6
    ):
        problems.append("Token coverage did not equal the hand-calculated 5/6.")
    if report.median_zipf is None or not math.isclose(report.median_zipf, 4.0):
        problems.append("Median Zipf did not equal the hand-calculated 4.0.")
    if report.mean_zipf is None or not math.isclose(report.mean_zipf, 3.4):
        problems.append("Mean Zipf did not equal the hand-calculated 3.4.")
    if not report.source_unchanged:
        problems.append("The synthetic source workbook changed during analysis.")
    if any(
        row.zipf_value is not None
        for row in result.token_audit
        if not row.included
    ):
        problems.append("An unmatched or ineligible token received a Zipf value.")
    return report, tuple(problems)


def main() -> int:
    report, problems = run_synthetic_frequency_validation()
    if problems:
        print("VerseVAD's frequency validation did not match expectations.")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("VerseVAD SUBTLEX-US frequency validation passed.")
    print(
        "Matched lexical tokens: "
        f"{report.matched_tokens}/{report.eligible_tokens} "
        f"({report.token_coverage:.1%} coverage)."
    )
    print(
        "Median/mean Zipf of matched tokens: "
        f"{report.median_zipf:.6f}/{report.mean_zipf:.6f}."
    )
    print(
        "Exact forms, the explicit lemma fallback, the unmatched token, and "
        "the optional NOUN/VERB/ADJ/ADV-only scope followed the expected audit."
    )
    print("The generated synthetic workbook remained unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
