"""Transparent offline readability formulas for literary-text orientation."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import asdict, dataclass

import pronouncing

from versevad import __version__
from versevad.core.documents import OrthographicFeatureKind
from versevad.core.modules import (
    ModuleCoverage,
    ModuleInput,
    ModuleMetric,
    ModuleProvenance,
    ModuleResult,
    ModuleWarning,
    ResultLayer,
    WarningSeverity,
)
from versevad.prosody.pronunciation import PronunciationOverride


_VOWELS = frozenset("aeiouy")


@dataclass(frozen=True)
class ReadabilityConfiguration:
    """Versioned word, sentence, and syllable policies."""

    pronunciation_overrides: tuple[PronunciationOverride, ...] = ()
    smog_minimum_sentences: int = 30
    scenario_id: str = "english-readability-v1"

    def __post_init__(self) -> None:
        if self.smog_minimum_sentences < 1:
            raise ValueError("The SMOG minimum sentence count must be positive.")
        if not self.scenario_id.strip():
            raise ValueError("A readability scenario requires a stable ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return "readability-config-v1:" + hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:16]


@dataclass(frozen=True)
class ReadabilityWordAudit:
    token_id: str
    token_position: int
    line_number: int
    surface_form: str
    lookup_form: str
    alphabetic_character_count: int
    syllable_count: int
    syllable_method: str
    pronunciation_candidate_count: int
    is_polysyllabic: bool


@dataclass(frozen=True)
class ReadabilitySummary:
    word_count: int
    sentence_count: int
    sentence_count_method: str
    syllable_count: int
    alphabetic_character_count: int
    polysyllabic_word_count: int
    dictionary_or_override_word_count: int
    heuristic_word_count: int
    pronunciation_coverage: float | None
    mean_words_per_sentence: float | None
    mean_syllables_per_word: float | None
    mean_characters_per_word: float | None
    flesch_reading_ease: float | None
    flesch_kincaid_grade: float | None
    gunning_fog_index: float | None
    automated_readability_index: float | None
    coleman_liau_index: float | None
    smog_index: float | None


@dataclass(frozen=True)
class ReadabilityAnalysisResult:
    module_result: ModuleResult
    configuration: ReadabilityConfiguration
    summary: ReadabilitySummary
    word_audit: tuple[ReadabilityWordAudit, ...]


def _letters(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in normalized
        if character.isalpha() and not unicodedata.combining(character)
    )


def _lookup(value: str) -> str:
    return value.casefold().replace("’", "'").strip()


def _phones_syllables(phones: str | tuple[str, ...]) -> int:
    symbols = phones.split() if isinstance(phones, str) else phones
    return sum(any(character.isdigit() for character in symbol) for symbol in symbols)


def _heuristic_syllables(value: str) -> int:
    """Return a deterministic last-resort English orthographic estimate."""

    letters = _letters(value)
    if not letters:
        return 1
    groups = sum(
        character in _VOWELS
        and (index == 0 or letters[index - 1] not in _VOWELS)
        for index, character in enumerate(letters)
    )
    if (
        len(letters) > 2
        and letters.endswith("e")
        and not (
            letters.endswith("le")
            and len(letters) > 2
            and letters[-3] not in _VOWELS
        )
        and groups > 1
    ):
        groups -= 1
    return max(groups, 1)


def _word_audit(
    module_input: ModuleInput,
    configuration: ReadabilityConfiguration,
) -> tuple[ReadabilityWordAudit, ...]:
    overrides = {
        override.lookup_form: override for override in configuration.pronunciation_overrides
    }
    poem = module_input.poem_document
    assert poem is not None
    token_by_id = {token.token_id: token for token in module_input.tokens}
    merge_spans = tuple(
        span
        for span in poem.orthographic_spans
        if span.kind
        in {
            OrthographicFeatureKind.CONTRACTION,
            OrthographicFeatureKind.HYPHENATED_EXPRESSION,
        }
        and any(
            token_by_id[token_id].is_lexical
            for token_id in span.token_ids
            if token_id in token_by_id
        )
    )
    span_by_token_id = {
        token_id: span
        for span in merge_spans
        for token_id in span.token_ids
    }
    emitted_spans: set[str] = set()
    rows = []
    for token in module_input.tokens:
        span = span_by_token_id.get(token.token_id)
        if span is not None:
            if span.span_id in emitted_spans:
                continue
            emitted_spans.add(span.span_id)
            members = tuple(
                token_by_id[token_id]
                for token_id in span.token_ids
                if token_id in token_by_id
            )
            lexical_members = tuple(item for item in members if item.is_lexical)
            if not lexical_members:
                continue
            row_token_id = span.span_id
            token_position = min(item.token_position for item in members)
            line_number = span.line_number
            surface_form = span.raw_text
            lookup = _lookup(span.raw_text)
        else:
            if not token.is_lexical:
                continue
            row_token_id = token.token_id
            token_position = token.token_position
            line_number = token.line_number
            surface_form = token.surface_form
            lookup = _lookup(token.normalized_form or token.surface_form)
        override = overrides.get(lookup)
        candidates = tuple(pronouncing.phones_for_word(lookup))
        if override is not None:
            syllables = _phones_syllables(override.phones)
            method = "session pronunciation override"
            candidate_count = len(candidates)
        elif candidates:
            candidate_counts = tuple(_phones_syllables(item) for item in candidates)
            syllables = candidate_counts[0]
            candidate_count = len(candidates)
            method = (
                "bundled CMUdict pronunciation"
                if len(set(candidate_counts)) == 1
                else "first bundled CMUdict pronunciation; alternatives differ"
            )
        else:
            syllables = _heuristic_syllables(lookup)
            method = "orthographic heuristic for out-of-dictionary word"
            candidate_count = 0
        rows.append(
            ReadabilityWordAudit(
                token_id=row_token_id,
                token_position=token_position,
                line_number=line_number,
                surface_form=surface_form,
                lookup_form=lookup,
                alphabetic_character_count=len(_letters(surface_form)),
                syllable_count=max(syllables, 1),
                syllable_method=method,
                pronunciation_candidate_count=candidate_count,
                is_polysyllabic=syllables >= 3,
            )
        )
    return tuple(rows)


def _safe_formula(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _summary(
    module_input: ModuleInput,
    rows: tuple[ReadabilityWordAudit, ...],
    configuration: ReadabilityConfiguration,
) -> ReadabilitySummary:
    poem = module_input.poem_document
    assert poem is not None
    words = len(rows)
    model_sentences = len(tuple(item for item in poem.sentences if item.raw_text.strip()))
    sentences = model_sentences if model_sentences else (1 if words else 0)
    sentence_method = (
        "shared model sentence segmentation"
        if model_sentences
        else "one-sentence fallback for nonempty text"
    )
    syllables = sum(item.syllable_count for item in rows)
    characters = sum(item.alphabetic_character_count for item in rows)
    polysyllables = sum(item.is_polysyllabic for item in rows)
    dictionary_count = sum(
        not item.syllable_method.startswith("orthographic heuristic")
        for item in rows
    )
    heuristic_count = words - dictionary_count
    if not words or not sentences:
        return ReadabilitySummary(
            word_count=words,
            sentence_count=sentences,
            sentence_count_method=sentence_method,
            syllable_count=syllables,
            alphabetic_character_count=characters,
            polysyllabic_word_count=polysyllables,
            dictionary_or_override_word_count=dictionary_count,
            heuristic_word_count=heuristic_count,
            pronunciation_coverage=None,
            mean_words_per_sentence=None,
            mean_syllables_per_word=None,
            mean_characters_per_word=None,
            flesch_reading_ease=None,
            flesch_kincaid_grade=None,
            gunning_fog_index=None,
            automated_readability_index=None,
            coleman_liau_index=None,
            smog_index=None,
        )
    words_per_sentence = words / sentences
    syllables_per_word = syllables / words
    characters_per_word = characters / words
    letters_per_100 = characters / words * 100
    sentences_per_100 = sentences / words * 100
    return ReadabilitySummary(
        word_count=words,
        sentence_count=sentences,
        sentence_count_method=sentence_method,
        syllable_count=syllables,
        alphabetic_character_count=characters,
        polysyllabic_word_count=polysyllables,
        dictionary_or_override_word_count=dictionary_count,
        heuristic_word_count=heuristic_count,
        pronunciation_coverage=dictionary_count / words,
        mean_words_per_sentence=words_per_sentence,
        mean_syllables_per_word=syllables_per_word,
        mean_characters_per_word=characters_per_word,
        flesch_reading_ease=_safe_formula(
            206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
        ),
        flesch_kincaid_grade=_safe_formula(
            0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
        ),
        gunning_fog_index=_safe_formula(
            0.4 * (words_per_sentence + 100 * polysyllables / words)
        ),
        automated_readability_index=_safe_formula(
            4.71 * characters_per_word + 0.5 * words_per_sentence - 21.43
        ),
        coleman_liau_index=_safe_formula(
            0.0588 * letters_per_100 - 0.296 * sentences_per_100 - 15.8
        ),
        smog_index=(
            _safe_formula(
                1.043 * math.sqrt(polysyllables * (30 / sentences)) + 3.1291
            )
            if sentences >= configuration.smog_minimum_sentences
            else None
        ),
    )


def _metrics(summary: ReadabilitySummary) -> tuple[ModuleMetric, ...]:
    rows = []
    metric_specs = (
        ("word_count", summary.word_count, "shared-preprocessing lexical tokens"),
        ("sentence_count", summary.sentence_count, summary.sentence_count_method),
        ("syllable_count", summary.syllable_count, "estimated syllables"),
        (
            "flesch_reading_ease",
            summary.flesch_reading_ease,
            "formula score; conventionally higher is easier",
        ),
        (
            "flesch_kincaid_grade",
            summary.flesch_kincaid_grade,
            "approximate U.S. grade-formula score",
        ),
        (
            "gunning_fog_index",
            summary.gunning_fog_index,
            "approximate grade-formula score",
        ),
        (
            "automated_readability_index",
            summary.automated_readability_index,
            "approximate U.S. grade-formula score",
        ),
        (
            "coleman_liau_index",
            summary.coleman_liau_index,
            "approximate U.S. grade-formula score",
        ),
        (
            "smog_index",
            summary.smog_index,
            "approximate grade-formula score",
        ),
    )
    for metric_id, value, unit in metric_specs:
        rows.append(
            ModuleMetric(
                metric_id=f"readability.{metric_id}",
                value=value,
                layer=(
                    ResultLayer.DIRECT_OBSERVATION
                    if metric_id in {"word_count", "sentence_count", "syllable_count"}
                    else ResultLayer.COMPUTED_SUMMARY
                ),
                unit=unit,
                denominator="complete preserved text",
            )
        )
    return tuple(rows)


class ReadabilityModule:
    """Calculate familiar English prose formulas without external downloads."""

    name = "readability"
    version = "1.0.0"

    def analyze(self, module_input: ModuleInput) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: ReadabilityConfiguration | None = None,
    ) -> ReadabilityAnalysisResult:
        configuration = configuration or ReadabilityConfiguration()
        if module_input.poem_document is None:
            raise ValueError(
                "Readability analysis requires the shared processing record."
            )
        audit = _word_audit(module_input, configuration)
        summary = _summary(module_input, audit, configuration)
        warnings = [
            ModuleWarning(
                code="readability.poetry_caution",
                message=(
                    "These formulas were designed for prose. Poetic lineation, "
                    "fragments, archaic diction, syntactic disruption, and deliberate "
                    "difficulty can make grade-style scores unstable or misleading; "
                    "they do not measure literary quality or reader ability."
                ),
            )
        ]
        if summary.heuristic_word_count:
            warnings.append(
                ModuleWarning(
                    code="readability.heuristic_syllables",
                    message=(
                        f"{summary.heuristic_word_count} word occurrence(s) were not "
                        "in the bundled pronunciation dictionary and used the "
                        "documented orthographic syllable heuristic."
                    ),
                )
            )
        if summary.smog_index is None:
            warnings.append(
                ModuleWarning(
                    code="readability.smog_unavailable",
                    message=(
                        f"SMOG remains missing below "
                        f"{configuration.smog_minimum_sentences} sentences."
                    ),
                    severity=WarningSeverity.INFORMATION,
                )
            )
        provenance = ModuleProvenance(
            software_version=__version__,
            source_text_sha256=module_input.document.text_sha256,
            preprocessing_recipe=module_input.preprocessing.recipe_id,
            pipeline_name=module_input.preprocessing.pipeline_name,
            pipeline_version=module_input.preprocessing.pipeline_version,
            configuration_id=configuration.configuration_id,
            scenario_id=configuration.scenario_id,
            lookup_policy=(
                "Session pronunciation overrides take priority; otherwise the "
                "installed pronouncing package's bundled CMUdict is used. "
                "Out-of-dictionary words receive a deterministic vowel-group heuristic."
            ),
            inclusion_policy=(
                "Word and sentence units reuse the shared processing record. "
                "Alphabetic characters exclude punctuation. Flesch Reading Ease, "
                "Flesch-Kincaid Grade, Gunning Fog, ARI, Coleman-Liau, and SMOG use "
                "their published formulas; SMOG remains missing below the configured "
                "sentence minimum."
            ),
            resources=(),
        )
        identity = json.dumps(
            {
                "text_sha256": module_input.document.text_sha256,
                "configuration": configuration.configuration_id,
                "summary": asdict(summary),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        module_result = ModuleResult(
            result_id="readability-result-v1:"
            + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
            module_name=self.name,
            module_version=self.version,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=_metrics(summary),
            coverage=(
                ModuleCoverage.from_counts(
                    coverage_id="readability.dictionary_or_override_syllables",
                    eligible_count=summary.word_count,
                    matched_count=summary.dictionary_or_override_word_count,
                    unit="shared-preprocessing lexical-token occurrences",
                    unmatched_items=tuple(
                        item.surface_form
                        for item in audit
                        if item.syllable_method.startswith("orthographic heuristic")
                    ),
                    note=(
                        "Unmatched dictionary words use the explicit heuristic for "
                        "formula completeness; they are not presented as confirmed pronunciations."
                    ),
                ),
            ),
            warnings=tuple(warnings),
            provenance=provenance,
        )
        return ReadabilityAnalysisResult(
            module_result=module_result,
            configuration=configuration,
            summary=summary,
            word_audit=audit,
        )
