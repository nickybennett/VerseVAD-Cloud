"""Transparent candidate ranking for inherited poetic forms."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from statistics import fmean, pstdev
from typing import Iterable, Sequence

from versevad import __version__
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
from versevad.phonology import PhonologicalAnalysisResult
from versevad.preprocessing import strip_line_edge_whitespace
from versevad.prosody import (
    MeterAnalysisResult,
    MeterLineStatus,
    PronunciationAnalysisResult,
)

from .profiles import (
    FORM_PROFILES,
    FORM_PROFILE_BY_ID,
    PROFILE_REGISTRY_VERSION,
    FormProfile,
    FormRule,
    RuleRole,
)


MODULE_NAME = "inherited_form"
MODULE_VERSION = "2.0.0"
_PHONE_VOWEL = re.compile(r"^[A-Z]+[012]$")


@dataclass(frozen=True)
class InheritedFormConfiguration:
    profile_ids: tuple[str, ...] = tuple(profile.profile_id for profile in FORM_PROFILES)
    suggestion_threshold: float = 0.45
    minimum_evidence_coverage: float = 0.70
    minimum_required_evidence_coverage: float = 0.70
    moderate_confidence_threshold: float = 0.58
    high_confidence_threshold: float = 0.75
    moderate_margin: float = 0.03
    high_margin: float = 0.08
    modified_refrain_floor: float = 0.70
    scenario_id: str = "inherited-form-comprehensive-v2"

    def __post_init__(self) -> None:
        if not self.profile_ids or len(set(self.profile_ids)) != len(self.profile_ids):
            raise ValueError("Select one or more unique inherited-form profiles.")
        unknown = set(self.profile_ids) - set(FORM_PROFILE_BY_ID)
        if unknown:
            raise ValueError(f"Unknown inherited-form profiles: {sorted(unknown)}")
        proportions = (
            self.suggestion_threshold,
            self.minimum_evidence_coverage,
            self.minimum_required_evidence_coverage,
            self.moderate_confidence_threshold,
            self.high_confidence_threshold,
            self.moderate_margin,
            self.high_margin,
            self.modified_refrain_floor,
        )
        if any(not 0 <= value <= 1 for value in proportions):
            raise ValueError("Inherited-form thresholds must be between zero and one.")
        if self.moderate_confidence_threshold > self.high_confidence_threshold:
            raise ValueError("Moderate confidence cannot exceed high confidence.")
        if self.moderate_margin > self.high_margin:
            raise ValueError("Moderate candidate margin cannot exceed high margin.")
        if not self.scenario_id:
            raise ValueError("Inherited-form analysis requires a scenario ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return "inherited-form-config-v2:" + hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:16]


@dataclass(frozen=True)
class FormFeatureEvidence:
    rule_id: str
    feature_id: str
    label: str
    role: str
    weight: float
    expected: str
    detected: str
    score: float | None
    evidence_coverage: float | None
    explanation: str
    source_modules: tuple[str, ...]

    @property
    def available(self) -> bool:
        return self.score is not None


@dataclass(frozen=True)
class FormCandidateResult:
    rank: int
    profile_id: str
    profile_name: str
    definition: str
    tooltip: str
    consistency: float | None
    evidence_coverage: float
    required_feature_agreement: float | None
    required_evidence_coverage: float
    required_contradiction_count: int
    margin_over_next: float | None
    confidence: str
    classification: str
    suggested: bool
    assessment_mode: str
    narrative: str
    feature_evidence: tuple[FormFeatureEvidence, ...]


@dataclass(frozen=True)
class InheritedFormAnalysisResult:
    module_result: ModuleResult
    configuration: InheritedFormConfiguration
    registry_version: str
    status: str
    best_candidate: FormCandidateResult | None
    nearest_alternative: FormCandidateResult | None
    candidates: tuple[FormCandidateResult, ...]


@dataclass(frozen=True)
class _Observations:
    line_numbers: tuple[int, ...]
    line_texts: tuple[str, ...]
    line_words: tuple[tuple[str, ...], ...]
    line_word_proper_flags: tuple[tuple[bool, ...], ...]
    line_token_ids: tuple[tuple[str, ...], ...]
    stanza_lengths: tuple[int, ...]
    syllable_counts: tuple[int | None, ...]
    stress_counts: tuple[int | None, ...]
    rhyme_labels: tuple[str, ...]
    stanza_rhyme_labels: tuple[str, ...]
    ending_stressed_vowels: tuple[str, ...]
    line_alliteration_densities: tuple[float | None, ...]

    @property
    def line_count(self) -> int:
        return len(self.line_numbers)

    @property
    def ending_words(self) -> tuple[str, ...]:
        return tuple(words[-1] if words else "" for words in self.line_words)

    @property
    def word_counts(self) -> tuple[int, ...]:
        return tuple(len(words) for words in self.line_words)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _count_score(observed: int, expected: int) -> float:
    return _clamp(1 - abs(observed - expected) / max(2, expected * 0.25))


def _sequence_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left or not right:
        return 0.0
    if tuple(left) == tuple(right):
        return 1.0
    return SequenceMatcher(None, tuple(left), tuple(right)).ratio()


def _stanza_similarity(observed: tuple[int, ...], expected: tuple[int, ...]) -> float:
    if observed == expected:
        return 1.0
    if not observed or not expected:
        return 0.0
    count_fit = _count_score(len(observed), len(expected))
    padded = max(len(observed), len(expected))
    differences = sum(
        abs((observed[index] if index < len(observed) else 0) -
            (expected[index] if index < len(expected) else 0))
        for index in range(padded)
    )
    length_fit = _clamp(1 - differences / max(sum(expected), 1))
    return (count_fit + length_fit) / 2


def _scheme_pair_score(
    expected: str,
    observed: tuple[str, ...],
    pair_lookup: dict[tuple[int, int], tuple[str, float | None]],
) -> tuple[float | None, float]:
    if len(observed) < len(expected):
        expected = expected[: len(observed)]
    expected_rhyme_relations: list[float] = []
    expected_difference_relations: list[float] = []
    eligible = 0
    possible = 0
    for first in range(len(expected)):
        for second in range(first + 1, len(expected)):
            possible += 1
            left = observed[first] if first < len(observed) else "?"
            right = observed[second] if second < len(observed) else "?"
            if not left or not right or "?" in (left, right):
                continue
            eligible += 1
            should_rhyme = expected[first] == expected[second]
            observed_rhyme = left == right
            target = (
                expected_rhyme_relations
                if should_rhyme
                else expected_difference_relations
            )
            if should_rhyme:
                if observed_rhyme:
                    target.append(1.0)
                    continue
                relationship, similarity = pair_lookup.get(
                    (first + 1, second + 1), ("", None)
                )
                if relationship in {"perfect", "identical"}:
                    target.append(1.0)
                elif relationship == "slant":
                    target.append(0.45 + 0.45 * (similarity or 0.0))
                elif relationship == "eye":
                    target.append(0.25)
                else:
                    target.append(0.0)
            else:
                target.append(0.0 if observed_rhyme else 1.0)
    category_scores = [
        fmean(items)
        for items in (
            expected_rhyme_relations,
            expected_difference_relations,
        )
        if items
    ]
    return (
        fmean(category_scores) if category_scores else None,
        eligible / possible if possible else 0.0,
    )


def _rhyme_pair_lookup(
    result: PhonologicalAnalysisResult | None,
) -> dict[tuple[int, int], tuple[str, float | None]]:
    if result is None:
        return {}
    lookup = {}
    line_number_by_id = {line.line_id: line.line_number for line in result.line_results}
    for pair in result.pair_results:
        first = line_number_by_id.get(pair.first_line_id, pair.first_line_number)
        second = line_number_by_id.get(pair.second_line_id, pair.second_line_number)
        lookup[(min(first, second), max(first, second))] = (
            pair.relationship,
            pair.similarity_score,
        )
    return lookup


def _range_score(observed: float, minimum: float, maximum: float) -> float:
    if minimum <= observed <= maximum:
        return 1.0
    distance = minimum - observed if observed < minimum else observed - maximum
    return _clamp(1 - distance / max(2.0, (maximum - minimum + 1) * 0.5))


def _ranking_score(
    profile: FormProfile,
    consistency: float | None,
    evidence_coverage: float,
) -> float:
    if consistency is None:
        return -1.0
    mode_factor = {
        "automatic": 1.0,
        "partial": 0.90,
        "manual": 0.50,
    }[profile.assessment_mode]
    return consistency * evidence_coverage * mode_factor


def _numeric_pattern_score(
    observed: Sequence[int | None],
    expected: Sequence[int],
    *,
    repeating: bool = False,
    tolerance: float = 3.0,
) -> tuple[float | None, float]:
    targets = (
        tuple(expected[index % len(expected)] for index in range(len(observed)))
        if repeating and expected
        else tuple(expected)
    )
    pairs = [
        (actual, target)
        for actual, target in zip(observed, targets)
        if actual is not None
    ]
    if not pairs:
        return None, 0.0
    return (
        fmean(_clamp(1 - abs(actual - target) / tolerance) for actual, target in pairs),
        len(pairs) / max(len(targets), 1),
    )


def _rhyme_relation_score(
    observations: _Observations,
    phonology: PhonologicalAnalysisResult | None,
    first: int,
    second: int,
) -> tuple[float | None, float]:
    if (
        phonology is None
        or first < 1
        or second < 1
        or first > observations.line_count
        or second > observations.line_count
    ):
        return None, 0.0
    left = observations.rhyme_labels[first - 1]
    right = observations.rhyme_labels[second - 1]
    if not left or not right or "?" in (left, right):
        return None, 0.0
    if left == right:
        return 1.0, 1.0
    relationship, similarity = _rhyme_pair_lookup(phonology).get(
        (min(first, second), max(first, second)),
        ("", None),
    )
    if relationship in {"perfect", "identical"}:
        return 1.0, 1.0
    if relationship == "slant":
        return 0.45 + 0.45 * (similarity or 0.0), 1.0
    if relationship == "eye":
        return 0.25, 1.0
    return 0.0, 1.0


def _line_repetition_score(
    observations: _Observations,
    groups: Sequence[Sequence[int]],
) -> tuple[float | None, float, str]:
    comparisons: list[float] = []
    possible = 0
    for group in groups:
        if not group:
            continue
        anchor_position = int(group[0])
        for position in group[1:]:
            possible += 1
            if (
                anchor_position <= observations.line_count
                and int(position) <= observations.line_count
            ):
                comparisons.append(
                    _sequence_similarity(
                        observations.line_words[anchor_position - 1],
                        observations.line_words[int(position) - 1],
                    )
                )
    return (
        fmean(comparisons) if comparisons else None,
        len(comparisons) / possible if possible else 0.0,
        f"{len(comparisons)} of {possible} prescribed line repetitions compared",
    )


def _scheme_for_repeated_blocks(scheme: str, line_count: int) -> str:
    expected: list[str] = []
    block = len(scheme)
    for start in range(0, line_count, block):
        symbol_map: dict[str, str] = {}
        for symbol in scheme[: min(block, line_count - start)]:
            if symbol not in symbol_map:
                symbol_map[symbol] = chr(0x100 + len(expected) + len(symbol_map))
            expected.append(symbol_map[symbol])
    return "".join(expected)


def _feature(
    rule: FormRule,
    observations: _Observations,
    pronunciation: PronunciationAnalysisResult | None,
    meter: MeterAnalysisResult | None,
    phonology: PhonologicalAnalysisResult | None,
    configuration: InheritedFormConfiguration,
) -> FormFeatureEvidence:
    parameters = rule.parameter_map
    feature_id = rule.feature_id
    score: float | None = None
    coverage: float | None = 1.0
    detected = ""
    explanation = ""
    sources = ["shared_poem_document"]

    if feature_id == "line_count_exact":
        expected = int(parameters["count"])
        score = _count_score(observations.line_count, expected)
        detected = f"{observations.line_count} nonblank lines"
        explanation = "Exact line count receives full credit; near counts receive graded credit."
    elif feature_id == "stanza_pattern":
        patterns = tuple(parameters["patterns"])
        score = max(_stanza_similarity(observations.stanza_lengths, item) for item in patterns)
        detected = "/".join(map(str, observations.stanza_lengths)) or "no nonblank stanzas"
        explanation = "Physical stanza layout is supporting evidence; logical architecture is scored elsewhere."
    elif feature_id == "rhyme_scheme":
        sources.append("rhyme_and_phonological_patterns")
        if phonology is None:
            coverage = 0.0
        else:
            schemes = tuple(str(item).replace(" ", "") for item in parameters["schemes"])
            pair_lookup = _rhyme_pair_lookup(phonology)
            results = [
                _scheme_pair_score(scheme, observations.rhyme_labels, pair_lookup)
                for scheme in schemes
            ]
            available = [item for item in results if item[0] is not None]
            if available:
                score, coverage = max(available, key=lambda item: item[0] or 0.0)
            else:
                coverage = 0.0
            detected = phonology.summary.whole_poem_rhyme_scheme or "unavailable"
            explanation = "Expected rhyme relations receive full, slant, eye, or no credit from the graded rhyme evidence."
    elif feature_id == "meter_pattern":
        sources.extend(("pronunciation_prosody_foundation", "candidate_meter_and_rhythmic_regularity"))
        pattern = str(parameters["pattern"])
        foot_count = int(parameters["foot_count"])
        scores = []
        eligible = observations.line_count
        if meter is not None and meter.performance_aware is not None:
            for line in meter.performance_aware.line_results:
                realization = line.primary_realization
                if realization is None:
                    continue
                base = realization.scores.overall
                if realization.pattern.value == pattern and realization.foot_count == foot_count:
                    scores.append(base)
                elif realization.pattern.value == pattern:
                    scores.append(base * 0.45)
                else:
                    scores.append(0.0)
        elif meter is not None:
            for line in meter.line_results:
                if line.status is not MeterLineStatus.ANALYZED:
                    continue
                fit = next(
                    (
                        item.fit_score
                        for item in line.candidate_fits
                        if item.pattern.value == pattern and item.foot_count == foot_count
                    ),
                    None,
                )
                if fit is not None:
                    scores.append(fit)
        score = fmean(scores) if scores else None
        coverage = len(scores) / eligible if eligible else 0.0
        detected = (
            meter.performance_aware.poem_summary.primary_meter
            if meter is not None and meter.performance_aware is not None
            else meter.summary.closest_candidate_label
            if meter is not None
            else "unavailable"
        )
        explanation = "This consumes VerseVAD's existing governing-meter analysis; the form module does not rescan independently."
    elif feature_id == "syllable_pattern":
        sources.append("pronunciation_prosody_foundation")
        expected = tuple(int(item) for item in parameters["counts"])
        supported = [
            (observed, target)
            for observed, target in zip(observations.syllable_counts, expected)
            if observed is not None
        ]
        score = (
            fmean(_clamp(1 - abs(observed - target) / 3) for observed, target in supported)
            if supported
            else None
        )
        coverage = len(supported) / len(expected)
        detected = "/".join("?" if item is None else str(item) for item in observations.syllable_counts[: len(expected)])
        explanation = "Only fully pronunciation-supported line totals are scored; unresolved lines remain missing."
    elif feature_id == "maximum_total_syllables":
        sources.append("pronunciation_prosody_foundation")
        counts = [item for item in observations.syllable_counts if item is not None]
        if len(counts) == observations.line_count and counts:
            maximum = int(parameters["maximum"])
            total = sum(counts)
            score = 1.0 if total <= maximum else _clamp(1 - (total - maximum) / maximum)
            detected = f"{total} resolved syllables"
        else:
            coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        explanation = "Brevity is supporting evidence and requires complete line-level syllable totals."
    elif feature_id == "villanelle_refrains":
        positions = ((1, 6, 12, 18), (3, 9, 15, 19))
        comparisons = []
        possible = 0
        for group in positions:
            if group[0] > observations.line_count:
                continue
            anchor = observations.line_words[group[0] - 1]
            for position in group[1:]:
                possible += 1
                if position <= observations.line_count:
                    comparisons.append(_sequence_similarity(anchor, observations.line_words[position - 1]))
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / possible if possible else 0.0
        detected = f"{len(comparisons)} of {possible} prescribed refrain comparisons available"
        explanation = "Exact repeated lines receive full credit; lexically modified refrains receive graded credit."
    elif feature_id == "sestina_rotation":
        endings = observations.ending_words
        expected_indices = (0, 1, 2, 3, 4, 5, 5, 0, 4, 1, 3, 2, 2, 5, 3, 0, 1, 4, 4, 2, 1, 5, 0, 3, 3, 4, 0, 2, 5, 1, 1, 3, 5, 4, 2, 0)
        if len(endings) >= 6 and all(endings[:6]):
            seed = endings[:6]
            comparisons = [
                1.0 if endings[index] == seed[seed_index] else 0.0
                for index, seed_index in enumerate(expected_indices)
                if index < len(endings) and endings[index]
            ]
            score = fmean(comparisons) if comparisons else None
            coverage = len(comparisons) / len(expected_indices)
            detected = f"{sum(comparisons):.0f} of {len(comparisons)} available rotation positions agree"
        else:
            coverage = 0.0
        explanation = "Normalized lexical line-ending words are compared with the traditional six-word rotation."
    elif feature_id == "sestina_envoi":
        endings = observations.ending_words
        if len(endings) >= 39 and all(endings[:6]):
            seed = endings[:6]
            final = endings[36:39]
            terminal_score = max(
                fmean(1.0 if actual == seed[index] else 0.0 for actual, index in zip(final, variant))
                for variant in ((4, 2, 0), (0, 2, 4))
            )
            envoi_words = {
                word
                for words in observations.line_words[36:39]
                for word in words
            }
            return_score = len(set(seed) & envoi_words) / len(set(seed))
            score = (terminal_score + return_score) / 2
            detected = f"terminal words {'/'.join(final)}; {len(set(seed) & envoi_words)} of 6 seed words present"
        else:
            coverage = min(1.0, max(0, len(endings) - 36) / 3)
        explanation = "The three terminal end-words and the return of all six seed words are scored separately and averaged."
    elif feature_id == "limerick_length_relation":
        counts = observations.syllable_counts[:5]
        if len(counts) == 5 and all(item is not None for item in counts):
            long_mean = fmean(counts[index] for index in (0, 1, 4) if counts[index] is not None)
            short_mean = fmean(counts[index] for index in (2, 3) if counts[index] is not None)
            score = _clamp((long_mean - short_mean + 1) / max(long_mean * 0.35, 1))
            detected = f"long-line mean {long_mean:.1f}; short-line mean {short_mean:.1f} syllables"
        else:
            coverage = sum(item is not None for item in counts) / 5
        explanation = "Resolved syllable totals test the conventional longer 1/2/5 and shorter 3/4 relationship."
    elif feature_id == "limerick_meter":
        sources.extend(("pronunciation_prosody_foundation", "candidate_meter_and_rhythmic_regularity"))
        if meter is not None and len(meter.line_results) >= 5:
            scores = []
            for index, line in enumerate(meter.line_results[:5]):
                target_feet = 3 if index in (0, 1, 4) else 2
                fit = next(
                    (
                        item.fit_score
                        for item in line.candidate_fits
                        if item.pattern.value == "anapestic" and item.foot_count == target_feet
                    ),
                    None,
                )
                if fit is not None:
                    scores.append(fit)
            score = fmean(scores) if scores else None
            coverage = len(scores) / 5
            detected = f"{len(scores)} of 5 lines had comparable anapestic candidates"
        else:
            coverage = 0.0
        explanation = "The conventional anapestic long/short pattern is read from existing line-level meter candidates."
    elif feature_id == "quatrain_sequence":
        minimum = int(parameters["minimum"])
        if observations.stanza_lengths:
            quatrains = sum(length == 4 for length in observations.stanza_lengths)
            score = min(1.0, quatrains / minimum) * (
                quatrains / len(observations.stanza_lengths)
            )
            detected = f"{quatrains} quatrains across {len(observations.stanza_lengths)} printed stanzas"
        explanation = "Printed quatrains are counted directly."
    elif feature_id == "pantoum_repetition":
        stanzas = _line_ranges(observations.stanza_lengths)
        comparisons = []
        for current, following in zip(stanzas, stanzas[1:]):
            if len(current) >= 4 and len(following) >= 3:
                comparisons.extend(
                    (
                        _sequence_similarity(observations.line_words[current[1]], observations.line_words[following[0]]),
                        _sequence_similarity(observations.line_words[current[3]], observations.line_words[following[2]]),
                    )
                )
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / max(2 * (len(stanzas) - 1), 1)
        detected = f"{len(comparisons)} interstanza repetition comparisons"
        explanation = "Successive 2→1 and 4→3 line repetitions receive exact or graded lexical credit."
    elif feature_id == "pantoum_closure":
        stanzas = _line_ranges(observations.stanza_lengths)
        if len(stanzas) >= 2 and len(stanzas[0]) >= 3 and len(stanzas[-1]) >= 4:
            opening = stanzas[0]
            final = stanzas[-1]
            score = max(
                fmean((
                    _sequence_similarity(observations.line_words[opening[0]], observations.line_words[final[3]]),
                    _sequence_similarity(observations.line_words[opening[2]], observations.line_words[final[1]]),
                )),
                fmean((
                    _sequence_similarity(observations.line_words[opening[0]], observations.line_words[final[1]]),
                    _sequence_similarity(observations.line_words[opening[2]], observations.line_words[final[3]]),
                )),
            )
            detected = "opening and final-stanza lines compared"
        explanation = "Traditional circular closure is supporting, not required, evidence."
    elif feature_id == "terza_stanzas":
        lengths = observations.stanza_lengths
        if lengths:
            core = lengths[:-1] if lengths[-1] in (1, 2) else lengths
            terminal_ok = lengths[-1] in (1, 2, 3)
            score = (sum(item == 3 for item in core) / max(len(core), 1)) * (1.0 if terminal_ok else 0.8)
            detected = "/".join(map(str, lengths))
        explanation = "Physical tercets receive full credit; a terminal line or couplet is allowed."
    elif feature_id == "terza_rhyme":
        sources.append("rhyme_and_phonological_patterns")
        if phonology is not None and observations.line_count >= 6:
            letters = []
            current = ord("A")
            stanzas = observations.line_count // 3
            for index in range(stanzas):
                a = chr(current + index)
                b = chr(current + index + 1)
                letters.extend((a, b, a))
            expected = "".join(letters)
            score, coverage = _scheme_pair_score(
                expected,
                observations.rhyme_labels,
                _rhyme_pair_lookup(phonology),
            )
            detected = phonology.summary.whole_poem_rhyme_scheme
        else:
            coverage = 0.0
        explanation = "The ABA BCB CDC equivalence chain uses VerseVAD's graded rhyme evidence."
    elif feature_id == "line_length_uniformity":
        counts = [item for item in observations.syllable_counts if item is not None]
        if len(counts) >= 3 and fmean(counts) > 0:
            coefficient = pstdev(counts) / fmean(counts)
            score = _clamp(1 - coefficient / 0.35)
            coverage = len(counts) / observations.line_count
            detected = f"syllable-count coefficient of variation {coefficient:.3f}"
        else:
            coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        explanation = "Resolved syllable-count variability supplies supporting line-length evidence."
    elif feature_id == "ghazal_architecture":
        minimum = int(parameters["minimum"])
        maximum = int(parameters["maximum"])
        lengths = observations.stanza_lengths
        if lengths:
            couplets = sum(item == 2 for item in lengths)
            stanza_fit = couplets / len(lengths)
            range_fit = 1.0 if minimum <= couplets <= maximum else _clamp(1 - min(abs(couplets - minimum), abs(couplets - maximum)) / minimum)
            score = (stanza_fit + range_fit) / 2
            detected = f"{couplets} printed couplets across {len(lengths)} stanzas"
        explanation = "The profile tests five to fifteen physically printed couplets."
    elif feature_id == "ghazal_radif_qafia":
        sources.append("pronunciation_prosody_foundation")
        score, coverage, detected = _ghazal_score(observations, pronunciation)
        explanation = "Repeated lexical suffixes identify a radif candidate; the preceding resolved pronunciation supplies qafia-rhyme evidence."
    elif feature_id == "line_count_range":
        minimum = int(parameters["minimum"])
        maximum = int(parameters["maximum"])
        score = _range_score(observations.line_count, minimum, maximum)
        detected = f"{observations.line_count} nonblank lines"
        explanation = "Counts inside the documented range receive full credit; nearby counts receive graded credit."
    elif feature_id == "syllable_pattern_repeating":
        sources.append("pronunciation_prosody_foundation")
        expected = tuple(int(item) for item in parameters["counts"])
        score, coverage = _numeric_pattern_score(
            observations.syllable_counts,
            expected,
            repeating=True,
        )
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.syllable_counts
        )
        explanation = "The documented syllable sequence is repeated across all lines; unresolved lines lower coverage."
    elif feature_id == "syllable_range":
        sources.append("pronunciation_prosody_foundation")
        minimum = int(parameters["minimum"])
        maximum = int(parameters["maximum"])
        counts = [item for item in observations.syllable_counts if item is not None]
        score = (
            fmean(_range_score(item, minimum, maximum) for item in counts)
            if counts
            else None
        )
        coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.syllable_counts
        )
        explanation = "Each fully resolved line is compared with the documented syllable range."
    elif feature_id == "word_count_pattern":
        expected = tuple(int(item) for item in parameters["counts"])
        score, coverage = _numeric_pattern_score(
            observations.word_counts,
            expected,
            tolerance=2.0,
        )
        detected = "/".join(map(str, observations.word_counts[: len(expected)]))
        explanation = "Normalized lexical-word counts are compared line by line; punctuation and numbers are excluded."
    elif feature_id == "alphabetic_line_initials":
        initials = []
        for text in observations.line_texts[:26]:
            match = re.search(r"[A-Za-z]", text)
            initials.append(match.group(0).lower() if match else "")
        comparisons = [
            1.0 if initial == chr(ord("a") + index) else 0.0
            for index, initial in enumerate(initials)
            if initial
        ]
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / min(observations.line_count, 26) if observations.line_count else 0.0
        detected = "".join(initial or "?" for initial in initials) or "unavailable"
        explanation = "The first Latin letter on successive lines is compared with A, B, C, and onward."
    elif feature_id == "uniform_stanza_size":
        size = int(parameters["size"])
        minimum = int(parameters.get("minimum", 1))
        if observations.stanza_lengths:
            matching = sum(item == size for item in observations.stanza_lengths)
            score = (
                matching / len(observations.stanza_lengths)
                * min(1.0, matching / minimum)
            )
            detected = "/".join(map(str, observations.stanza_lengths))
        explanation = "Printed stanza lengths are tested for a uniform repeated size."
    elif feature_id == "stress_count_pattern_repeating":
        sources.append("pronunciation_prosody_foundation")
        expected = tuple(int(item) for item in parameters["counts"])
        score, coverage = _numeric_pattern_score(
            observations.stress_counts,
            expected,
            repeating=True,
            tolerance=2.0,
        )
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.stress_counts
        )
        explanation = "Resolved lexical primary and secondary stresses are counted per line and compared with the repeating accentual pattern."
    elif feature_id == "rhyme_absence":
        sources.append("rhyme_and_phonological_patterns")
        maximum = float(parameters["maximum_density"])
        if phonology is not None and phonology.summary.rhyme_density is not None:
            density = phonology.summary.rhyme_density
            score = 1.0 if density <= maximum else _clamp(1 - (density - maximum) / max(1 - maximum, 0.01))
            detected = f"rhyme density {density:.1%}"
        else:
            coverage = 0.0
        explanation = "Low end-rhyme density supports an unrhymed form; unavailable rhyme evidence remains missing."
    elif feature_id == "blues_repetition":
        ranges = _line_ranges(observations.stanza_lengths)
        triples = (
            [item for item in ranges if len(item) == 3]
            if any(len(item) == 3 for item in ranges)
            else [
                tuple(range(index, min(index + 3, observations.line_count)))
                for index in range(0, observations.line_count, 3)
                if index + 2 < observations.line_count
            ]
        )
        comparisons = [
            _sequence_similarity(
                observations.line_words[group[0]],
                observations.line_words[group[1]],
            )
            for group in triples
        ]
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / max(len(triples), 1)
        detected = f"{len(comparisons)} A-to-A line comparisons"
        explanation = "The first two lines of each available three-line unit are compared as an AAB repetition pattern."
    elif feature_id == "line_length_variation":
        sources.append("pronunciation_prosody_foundation")
        minimum = float(parameters["minimum_cv"])
        counts = [item for item in observations.syllable_counts if item is not None]
        if len(counts) >= 3 and fmean(counts) > 0:
            coefficient = pstdev(counts) / fmean(counts)
            score = _clamp(coefficient / max(minimum, 0.01))
            coverage = len(counts) / observations.line_count
            detected = f"syllable-count coefficient of variation {coefficient:.3f}"
        else:
            coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        explanation = "Resolved syllable totals test the documented contrast in line lengths."
    elif feature_id == "duplex_echo":
        groups = tuple(
            (position, position + 1)
            for position in range(2, observations.line_count, 2)
        )
        score, coverage, detected = _line_repetition_score(observations, groups)
        explanation = "Each couplet's second line is compared lexically with the next couplet's opening line; modified echoes receive graded credit."
    elif feature_id == "first_last_line_echo":
        score, coverage, detected = _line_repetition_score(
            observations,
            ((1, observations.line_count),),
        )
        explanation = "Opening and closing lines are compared lexically, with graded credit for a modified return."
    elif feature_id == "glosa_refrains":
        score, coverage, detected = _line_repetition_score(
            observations,
            ((1, 14), (2, 24), (3, 34), (4, 44)),
        )
        explanation = "The four epigraph lines are compared with the prescribed stanza-ending returns."
    elif feature_id == "line_repetition_groups":
        groups = tuple(tuple(int(item) for item in group) for group in parameters["groups"])
        score, coverage, detected = _line_repetition_score(observations, groups)
        explanation = "Prescribed repeated-line positions receive exact or graded lexical similarity credit."
    elif feature_id == "stanza_refrain":
        ranges = _line_ranges(observations.stanza_lengths)
        positions = tuple(group[-1] + 1 for group in ranges if group)
        score, coverage, detected = _line_repetition_score(
            observations,
            (positions,),
        )
        explanation = "The final line of each printed stanza is compared with the first available stanza-ending refrain."
    elif feature_id == "bop_refrain":
        if observations.stanza_lengths == (7, 9, 7):
            positions = (7, 16, 23)
        elif observations.stanza_lengths == (6, 1, 8, 1, 6, 1):
            positions = (7, 16, 23)
        else:
            positions = (7, 16, 23)
        score, coverage, detected = _line_repetition_score(
            observations,
            (positions,),
        )
        explanation = "The refrain positions following the six-, eight-, and six-line argument sections are compared lexically."
    elif feature_id in {"rhyme_couplets", "terminal_rhyming_couplet"}:
        sources.append("rhyme_and_phonological_patterns")
        pairs = (
            ((observations.line_count - 1, observations.line_count),)
            if feature_id == "terminal_rhyming_couplet"
            else tuple(
                (position, position + 1)
                for position in range(1, observations.line_count, 2)
                if position + 1 <= observations.line_count
            )
        )
        results = [
            _rhyme_relation_score(observations, phonology, first, second)
            for first, second in pairs
        ]
        available = [item for item in results if item[0] is not None]
        score = fmean(float(item[0]) for item in available) if available else None
        coverage = len(available) / len(pairs) if pairs else 0.0
        detected = f"{len(available)} of {len(pairs)} couplet rhyme relations resolved"
        explanation = "Adjacent line endings are scored with VerseVAD's perfect, identical, slant, eye, or non-rhyme evidence."
    elif feature_id == "rhyme_scheme_repeating":
        sources.append("rhyme_and_phonological_patterns")
        if phonology is not None:
            scheme = str(parameters["scheme"]).replace(" ", "")
            expected = _scheme_for_repeated_blocks(scheme, observations.line_count)
            score, coverage = _scheme_pair_score(
                expected,
                observations.rhyme_labels,
                _rhyme_pair_lookup(phonology),
            )
            detected = phonology.summary.whole_poem_rhyme_scheme or "unavailable"
        else:
            coverage = 0.0
        explanation = "The stanza scheme is repeated in independent rhyme classes and compared through graded rhyme relations."
    elif feature_id == "terminal_line_longer":
        sources.append("pronunciation_prosody_foundation")
        period = int(parameters["period"])
        comparisons = []
        possible = 0
        for end in range(period - 1, observations.line_count, period):
            group = observations.syllable_counts[max(0, end - period + 1):end]
            possible += 1
            if observations.syllable_counts[end] is not None and all(item is not None for item in group):
                terminal = observations.syllable_counts[end]
                comparison = fmean(float(item) for item in group if item is not None)
                comparisons.append(_clamp((float(terminal) - comparison + 1) / 3))
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / possible if possible else 0.0
        detected = f"{len(comparisons)} of {possible} stanza-final length relations resolved"
        explanation = "Each stanza-final line is compared with the mean resolved syllable length of the preceding lines."
    elif feature_id == "periodic_line_length_relation":
        sources.append("pronunciation_prosody_foundation")
        period = int(parameters["period"])
        long_positions = tuple(int(item) for item in parameters["long_positions"])
        short_positions = tuple(int(item) for item in parameters["short_positions"])
        relations = []
        possible = 0
        for start in range(0, observations.line_count, period):
            long_values = [
                observations.syllable_counts[start + pos - 1]
                for pos in long_positions
                if start + pos - 1 < observations.line_count
            ]
            short_values = [
                observations.syllable_counts[start + pos - 1]
                for pos in short_positions
                if start + pos - 1 < observations.line_count
            ]
            possible += 1
            if long_values and short_values and all(item is not None for item in (*long_values, *short_values)):
                long_mean = fmean(float(item) for item in long_values if item is not None)
                short_mean = fmean(float(item) for item in short_values if item is not None)
                relations.append(_clamp((long_mean - short_mean + 1) / 3))
        score = fmean(relations) if relations else None
        coverage = len(relations) / possible if possible else 0.0
        detected = f"{len(relations)} of {possible} periodic long/short groups resolved"
        explanation = "Documented long-line positions are compared with documented short-line positions in each stanza-sized block."
    elif feature_id == "alternating_stanza_sizes":
        sizes = tuple(int(item) for item in parameters["sizes"])
        if observations.stanza_lengths:
            expected = tuple(
                sizes[index % len(sizes)]
                for index in range(len(observations.stanza_lengths))
            )
            score = fmean(
                _count_score(actual, target)
                for actual, target in zip(observations.stanza_lengths, expected)
            )
            detected = "/".join(map(str, observations.stanza_lengths))
        explanation = "Printed stanza sizes are compared with the repeating documented sequence."
    elif feature_id == "total_syllable_range":
        sources.append("pronunciation_prosody_foundation")
        minimum = int(parameters["minimum"])
        maximum = int(parameters["maximum"])
        counts = [item for item in observations.syllable_counts if item is not None]
        if counts and len(counts) == observations.line_count:
            total = sum(counts)
            score = _range_score(total, minimum, maximum)
            detected = f"{total} resolved syllables"
        else:
            coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        explanation = "The whole-poem total is scored only when every line has a resolved syllable count."
    elif feature_id == "partial_refrain_positions":
        anchor = int(parameters["anchor"])
        positions = tuple(int(item) for item in parameters["positions"])
        comparisons = []
        for position in positions:
            if anchor <= observations.line_count and position <= observations.line_count:
                opening = observations.line_words[anchor - 1]
                target = observations.line_words[position - 1]
                prefix = target[: min(len(opening), len(target), 5)]
                comparisons.append(
                    max(
                        _sequence_similarity(opening, target),
                        _sequence_similarity(opening[: len(prefix)], prefix),
                    )
                )
        score = fmean(comparisons) if comparisons else None
        coverage = len(comparisons) / len(positions) if positions else 0.0
        detected = f"{len(comparisons)} of {len(positions)} rentrement positions compared"
        explanation = "Opening words are compared with the prescribed partial-refrain positions; modified returns receive graded credit."
    elif feature_id == "rondel_refrains":
        groups = (
            ((1, 7, 13), (2, 8, 14))
            if observations.line_count >= 14
            else ((1, 7, 13), (2, 8))
        )
        score, coverage, detected = _line_repetition_score(observations, groups)
        explanation = "Opening lines are compared with the customary mid-poem and closing refrain positions."
    elif feature_id == "rhyme_class_count":
        sources.append("rhyme_and_phonological_patterns")
        target = int(parameters["count"])
        labels = [item for item in observations.rhyme_labels if item and item != "?"]
        if labels:
            observed = len(set(labels))
            score = _count_score(observed, target)
            coverage = len(labels) / observations.line_count
            detected = f"{observed} resolved rhyme classes"
        else:
            coverage = 0.0
        explanation = "The count of resolved whole-poem rhyme classes is compared with the documented constraint."
    elif feature_id in {"even_line_assonance", "seguidilla_assonance"}:
        sources.append("rhyme_and_phonological_patterns")
        values = [
            observations.ending_stressed_vowels[index]
            for index in range(1, observations.line_count, 2)
            if observations.ending_stressed_vowels[index]
        ]
        if values:
            dominant = max(set(values), key=values.count)
            score = values.count(dominant) / len(values)
            coverage = len(values) / max(observations.line_count // 2, 1)
            detected = f"dominant even-line stressed vowel {dominant} on {values.count(dominant)} of {len(values)} resolved endings"
        else:
            coverage = 0.0
        explanation = "Resolved stressed vowels on even-numbered line endings supply conservative assonance evidence."
    elif feature_id == "rubaiyat_chain":
        sources.append("rhyme_and_phonological_patterns")
        if phonology is not None:
            expected = []
            current = 0
            for start in range(0, observations.line_count, 4):
                a = chr(0x180 + current)
                b = chr(0x180 + current + 1)
                expected.extend((a, a, b, a)[: observations.line_count - start])
                current += 1
            score, coverage = _scheme_pair_score(
                "".join(expected),
                observations.rhyme_labels,
                _rhyme_pair_lookup(phonology),
            )
            detected = phonology.summary.whole_poem_rhyme_scheme or "unavailable"
        else:
            coverage = 0.0
        explanation = "Successive AABA-style quatrains are compared through graded rhyme evidence."
    elif feature_id == "monorhyme":
        sources.append("rhyme_and_phonological_patterns")
        labels = [item for item in observations.rhyme_labels if item and item != "?"]
        if labels:
            dominant = max(set(labels), key=labels.count)
            score = labels.count(dominant) / len(labels)
            coverage = len(labels) / observations.line_count
            detected = f"largest rhyme class contains {labels.count(dominant)} of {len(labels)} resolved endings"
        else:
            coverage = 0.0
        explanation = "The share of resolved endings in the dominant rhyme family supplies monorhyme evidence."
    elif feature_id == "terzanelle_refrains":
        score, coverage, detected = _line_repetition_score(
            observations,
            ((1, 6, 12), (3, 10, 18)),
        )
        explanation = "The two principal refrain lines are compared with their customary later positions; variants require manual review."
    elif feature_id == "terminal_line_shorter":
        sources.append("pronunciation_prosody_foundation")
        counts = observations.syllable_counts
        if len(counts) >= 3 and counts[-1] is not None:
            preceding = [item for item in counts[:-1] if item is not None]
            if preceding:
                mean = fmean(preceding)
                score = _clamp((mean - counts[-1] + 1) / 3)
                coverage = (len(preceding) + 1) / len(counts)
                detected = f"final line {counts[-1]} syllables; preceding mean {mean:.1f}"
        else:
            coverage = sum(item is not None for item in counts) / len(counts) if counts else 0.0
        explanation = "The resolved final line is compared with the mean length of preceding resolved lines."
    elif feature_id == "sonnet_crown_links":
        sonnet_count = int(parameters["sonnet_count"])
        groups = tuple(
            (14 * index, 14 * index + 1)
            for index in range(1, sonnet_count - 1)
        )
        score, coverage, detected = _line_repetition_score(observations, groups)
        explanation = "Each sonnet's closing line is compared with the next sonnet's opening line; master-sonnet gathering remains a scholarly check."
    elif feature_id == "syllable_pattern_alternatives":
        sources.append("pronunciation_prosody_foundation")
        patterns = tuple(
            tuple(int(item) for item in pattern)
            for pattern in parameters["patterns"]
        )
        results = [
            _numeric_pattern_score(observations.syllable_counts, pattern)
            for pattern in patterns
        ]
        available = [item for item in results if item[0] is not None]
        if available:
            score, coverage = max(available, key=lambda item: float(item[0] or 0.0))
        else:
            coverage = 0.0
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.syllable_counts
        )
        explanation = "The resolved line totals are scored against each documented alternative and the strongest supported analysis is retained."
    elif feature_id == "terminal_pair_rhyme":
        sources.append("rhyme_and_phonological_patterns")
        positions = tuple(int(item) for item in parameters["positions"])
        if len(positions) == 2:
            score, coverage = _rhyme_relation_score(
                observations,
                phonology,
                positions[0],
                positions[1],
            )
            detected = f"lines {positions[0]} and {positions[1]} compared"
        explanation = "The specified terminal line endings are compared through graded rhyme evidence."
    elif feature_id == "paradelle_repetition":
        groups = []
        for start in (1, 7, 13):
            groups.extend(((start, start + 1), (start + 2, start + 3)))
        score, coverage, detected = _line_repetition_score(observations, groups)
        explanation = "The paired repeated lines in each of the first three sestets are compared exactly or with graded lexical similarity."
    elif feature_id == "maximum_word_length":
        maximum = int(parameters["maximum"])
        exempt_proper = bool(parameters.get("exempt_proper_nouns", False))
        values = []
        for words, flags in zip(
            observations.line_words,
            observations.line_word_proper_flags,
        ):
            values.extend(
                len(word)
                for word, is_proper in zip(words, flags)
                if not (exempt_proper and is_proper)
            )
        if values:
            score = sum(item <= maximum for item in values) / len(values)
            detected = f"{sum(item <= maximum for item in values)} of {len(values)} eligible words contain at most {maximum} letters"
        explanation = "Normalized lexical forms are counted by letters; proper nouns are omitted when the profile specifies an exemption."
    elif feature_id == "stress_count_range":
        sources.append("pronunciation_prosody_foundation")
        minimum = int(parameters["minimum"])
        maximum = int(parameters["maximum"])
        counts = [item for item in observations.stress_counts if item is not None]
        score = (
            fmean(_range_score(item, minimum, maximum) for item in counts)
            if counts
            else None
        )
        coverage = len(counts) / observations.line_count if observations.line_count else 0.0
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.stress_counts
        )
        explanation = "Resolved primary and secondary lexical stresses are counted per line and compared with the documented range."
    elif feature_id == "alliteration_density":
        sources.append("rhyme_and_phonological_patterns")
        minimum = float(parameters["minimum"])
        values = [
            item
            for item in observations.line_alliteration_densities
            if item is not None
        ]
        if values:
            mean = fmean(values)
            score = _clamp(mean / max(minimum, 0.01))
            coverage = len(values) / observations.line_count
            detected = f"mean line alliteration density {mean:.1%}"
        else:
            coverage = 0.0
        explanation = "This reuses VerseVAD's line-level repeated-initial-consonant density."
    elif feature_id == "rondeau_redouble_refrains":
        score, coverage, detected = _line_repetition_score(
            observations,
            ((1, 8), (2, 12), (3, 16), (4, 20)),
        )
        explanation = "The opening quatrain's lines are compared with their prescribed successive stanza-ending returns."
    elif feature_id == "chanso_architecture":
        lengths = observations.stanza_lengths
        if len(lengths) >= 6:
            body = lengths[:-1]
            body_size = round(fmean(body))
            uniformity = sum(item == body_size for item in body) / len(body)
            envoi_fit = _count_score(lengths[-1], max(1, round(body_size / 2)))
            stanza_count_fit = max(
                _count_score(len(body), 5),
                _count_score(len(body), 6),
            )
            score = fmean((uniformity, envoi_fit, stanza_count_fit))
            detected = "/".join(map(str, lengths))
        explanation = "Five or six equal body stanzas and an approximately half-length envoi are scored from printed stanza boundaries."
    elif feature_id == "choka_syllable_pattern":
        sources.append("pronunciation_prosody_foundation")
        expected = [
            5 if index % 2 == 0 else 7
            for index in range(observations.line_count)
        ]
        if expected:
            expected[-1] = 7
        score, coverage = _numeric_pattern_score(
            observations.syllable_counts,
            expected,
        )
        detected = "/".join(
            "?" if item is None else str(item)
            for item in observations.syllable_counts
        )
        explanation = "English syllable totals approximate the traditional 5/7 sound-unit alternation and final additional 7-unit segment."
    elif feature_id == "manual_requirement":
        coverage = 0.0
        detected = "manual scholarly confirmation required"
        explanation = (
            "This defining contextual, visual, thematic, linguistic, or "
            "compositional requirement is not responsibly inferable from the "
            "current automatic evidence. It remains visible and unscored."
        )
    else:  # pragma: no cover - registry validation should make this unreachable
        raise ValueError(f"Unsupported inherited-form feature: {feature_id}")

    return FormFeatureEvidence(
        rule_id=rule.rule_id,
        feature_id=feature_id,
        label=rule.label,
        role=rule.role.value,
        weight=rule.weight,
        expected=rule.expected,
        detected=detected or "unavailable",
        score=None if score is None else _clamp(score),
        evidence_coverage=None if coverage is None else _clamp(coverage),
        explanation=explanation,
        source_modules=tuple(dict.fromkeys(sources)),
    )


def _line_ranges(lengths: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    start = 0
    rows = []
    for length in lengths:
        rows.append(tuple(range(start, start + length)))
        start += length
    return tuple(rows)


def _pronunciation_rime(phones: str | None) -> tuple[str, ...]:
    sequence = tuple((phones or "").split())
    if not sequence:
        return ()
    primary = [index for index, phone in enumerate(sequence) if phone.endswith("1")]
    vowels = [index for index, phone in enumerate(sequence) if _PHONE_VOWEL.match(phone)]
    start = primary[-1] if primary else vowels[-1] if vowels else -1
    return sequence[start:] if start >= 0 else ()


def _ghazal_score(
    observations: _Observations,
    pronunciation: PronunciationAnalysisResult | None,
) -> tuple[float | None, float, str]:
    targets = [0, 1, *range(3, observations.line_count, 2)]
    targets = [index for index in targets if index < observations.line_count]
    if len(targets) < 4:
        return None, len(targets) / 6, "too few candidate radif positions"
    first_words = observations.line_words[targets[0]]
    candidates = [
        first_words[-length:]
        for length in range(1, min(4, len(first_words)) + 1)
    ]
    best_suffix: tuple[str, ...] = ()
    best_support = 0.0
    for suffix in candidates:
        support = sum(
            tuple(observations.line_words[index][-len(suffix):]) == tuple(suffix)
            for index in targets
            if len(observations.line_words[index]) >= len(suffix)
        ) / len(targets)
        adjusted = support + 0.01 * len(suffix)
        if adjusted > best_support:
            best_support = adjusted
            best_suffix = tuple(suffix)
    radif_support = max(0.0, best_support - 0.01 * len(best_suffix))
    if not best_suffix or radif_support < 0.5:
        return radif_support, 1.0, "no repeated radif candidate on most prescribed lines"
    pronunciation_by_token = (
        {item.token_id: item for item in pronunciation.token_results}
        if pronunciation is not None
        else {}
    )
    qafia_rimes = []
    for line_index in targets:
        words = observations.line_words[line_index]
        token_ids = observations.line_token_ids[line_index]
        if (
            len(words) <= len(best_suffix)
            or tuple(words[-len(best_suffix):]) != best_suffix
        ):
            continue
        token_index = len(token_ids) - len(best_suffix) - 1
        if token_index < 0:
            continue
        token = pronunciation_by_token.get(token_ids[token_index])
        rime = _pronunciation_rime(token.resolved_phones if token is not None else None)
        if rime:
            qafia_rimes.append(rime)
    qafia_score = None
    if len(qafia_rimes) >= 2:
        anchor = qafia_rimes[0]
        qafia_score = fmean(
            1.0 if item == anchor else _sequence_similarity(anchor, item) * 0.6
            for item in qafia_rimes[1:]
        )
    score = radif_support if qafia_score is None else 0.65 * radif_support + 0.35 * qafia_score
    qafia_coverage = len(qafia_rimes) / len(targets)
    coverage = 0.65 + 0.35 * qafia_coverage
    return (
        score,
        coverage,
        f"radif candidate “{' '.join(best_suffix)}” on {radif_support:.0%} of prescribed lines; "
        f"{len(qafia_rimes)} qafia pronunciations resolved",
    )


def _observations(
    module_input: ModuleInput,
    pronunciation: PronunciationAnalysisResult | None,
    phonology: PhonologicalAnalysisResult | None,
) -> _Observations:
    poem = module_input.poem_document
    if poem is None:
        raise ValueError("Inherited-form analysis requires the shared poem document.")
    lines = tuple(line for line in poem.lines if not line.is_blank)
    line_numbers = tuple(line.ordinal for line in lines)
    line_number_set = set(line_numbers)
    tokens_by_line: dict[int, list] = {number: [] for number in line_numbers}
    for token in module_input.tokens:
        if token.line_number in line_number_set and token.is_lexical:
            tokens_by_line[token.line_number].append(token)
    line_words = tuple(
        tuple(token.normalized_form for token in tokens_by_line[number])
        for number in line_numbers
    )
    line_word_proper_flags = tuple(
        tuple(token.is_proper_noun for token in tokens_by_line[number])
        for number in line_numbers
    )
    line_token_ids = tuple(
        tuple(token.token_id for token in tokens_by_line[number])
        for number in line_numbers
    )
    stanza_lengths = []
    for stanza in poem.stanzas:
        count = sum(
            not line.is_blank and line.parent_id == stanza.unit_id
            for line in poem.lines
        )
        if count:
            stanza_lengths.append(count)
    syllables = {}
    stresses = {}
    if pronunciation is not None:
        syllables = {
            line.line_number: line.syllable_count if line.is_complete else None
            for line in pronunciation.line_summaries
        }
        stresses = {
            line.line_number: (
                (line.primary_stress_count or 0)
                + (line.secondary_stress_count or 0)
                if line.is_complete
                else None
            )
            for line in pronunciation.line_summaries
        }
    rhyme = {}
    stanza_rhyme = {}
    stressed_vowels = {}
    alliteration_densities = {}
    if phonology is not None:
        rhyme = {
            line.line_number: line.poem_scheme_label or "?"
            for line in phonology.line_results
        }
        stanza_rhyme = {
            line.line_number: line.stanza_scheme_label or "?"
            for line in phonology.line_results
        }
        stressed_vowels = {
            line.line_number: line.stressed_vowel
            for line in phonology.line_results
        }
        alliteration_densities = {
            line.line_number: line.alliteration_density
            for line in phonology.line_results
        }
    return _Observations(
        line_numbers=line_numbers,
        line_texts=tuple(
            strip_line_edge_whitespace(line.content_text) for line in lines
        ),
        line_words=line_words,
        line_word_proper_flags=line_word_proper_flags,
        line_token_ids=line_token_ids,
        stanza_lengths=tuple(stanza_lengths),
        syllable_counts=tuple(syllables.get(number) for number in line_numbers),
        stress_counts=tuple(stresses.get(number) for number in line_numbers),
        rhyme_labels=tuple(rhyme.get(number, "?") for number in line_numbers),
        stanza_rhyme_labels=tuple(
            stanza_rhyme.get(number, "?") for number in line_numbers
        ),
        ending_stressed_vowels=tuple(
            stressed_vowels.get(number, "") for number in line_numbers
        ),
        line_alliteration_densities=tuple(
            alliteration_densities.get(number) for number in line_numbers
        ),
    )


def _classification(consistency: float | None, required: float | None) -> str:
    if consistency is None:
        return "No inherited-form match"
    if consistency >= 0.95 and (required is None or required >= 0.95):
        return "Strict"
    if consistency >= 0.82:
        return "Strongly conforming"
    if consistency >= 0.68:
        return "Modified"
    if consistency >= 0.55:
        return "Form-derived"
    if consistency >= 0.45:
        return "Suggestive resemblance"
    return "No inherited-form match"


def _tooltip(profile: FormProfile, evidence: Sequence[FormFeatureEvidence]) -> str:
    available = [item for item in evidence if item.score is not None]
    strongest = sorted(available, key=lambda item: item.weight * (item.score or 0), reverse=True)[:2]
    departures = sorted(available, key=lambda item: item.score if item.score is not None else 1)[:2]
    text = profile.tooltip_definition
    if strongest:
        text += " Agreement: " + "; ".join(f"{item.label} ({item.detected})" for item in strongest) + "."
    if departures and any((item.score or 0) < 0.8 for item in departures):
        text += " Departures: " + "; ".join(
            f"{item.label} ({item.detected})"
            for item in departures
            if (item.score or 0) < 0.8
        ) + "."
    return text


class InheritedFormEngine:
    name = MODULE_NAME
    version = MODULE_VERSION

    @staticmethod
    def validate_resources() -> tuple:
        return ()

    def analyze(
        self,
        module_input: ModuleInput,
        pronunciation: PronunciationAnalysisResult | None,
        meter: MeterAnalysisResult | None,
        phonology: PhonologicalAnalysisResult | None,
        configuration: InheritedFormConfiguration = InheritedFormConfiguration(),
    ) -> InheritedFormAnalysisResult:
        observations = _observations(module_input, pronunciation, phonology)
        raw = []
        for profile_id in configuration.profile_ids:
            profile = FORM_PROFILE_BY_ID[profile_id]
            evidence = tuple(
                _feature(
                    rule,
                    observations,
                    pronunciation,
                    meter,
                    phonology,
                    configuration,
                )
                for rule in profile.rules
            )
            available = [item for item in evidence if item.score is not None]
            effective_weights = {
                item.rule_id: item.weight * (
                    item.evidence_coverage
                    if item.evidence_coverage is not None
                    else 1.0
                )
                for item in available
            }
            available_weight = sum(effective_weights.values())
            total_weight = sum(item.weight for item in evidence)
            consistency = (
                sum(
                    effective_weights[item.rule_id] * float(item.score)
                    for item in available
                )
                / available_weight
                if available_weight
                else None
            )
            required = [
                item
                for item in available
                if item.role == RuleRole.REQUIRED.value
            ]
            required_potential_weight = sum(
                item.weight
                for item in evidence
                if item.role == RuleRole.REQUIRED.value
            )
            required_evidence_coverage = (
                sum(effective_weights[item.rule_id] for item in required)
                / required_potential_weight
                if required_potential_weight
                else 1.0
            )
            required_agreement = (
                sum(
                    effective_weights[item.rule_id] * float(item.score)
                    for item in required
                )
                / sum(effective_weights[item.rule_id] for item in required)
                if required
                else None
            )
            contradictions = sum((item.score or 0) < 0.2 for item in required)
            raw.append(
                (
                    profile,
                    evidence,
                    consistency,
                    available_weight / total_weight,
                    required_agreement,
                    required_evidence_coverage,
                    contradictions,
                )
            )
        raw.sort(
            key=lambda item: (
                -_ranking_score(item[0], item[2], item[3]),
                -(item[2] if item[2] is not None else -1),
                item[0].profile_id,
            )
        )
        candidates = []
        for index, (
            profile,
            evidence,
            consistency,
            coverage,
            required,
            required_coverage,
            contradictions,
        ) in enumerate(raw):
            next_item = next(
                (
                    item
                    for item in raw[index + 1:]
                    if item[0].assessment_mode != "manual"
                    and item[2] is not None
                ),
                None,
            )
            margin = (
                _ranking_score(profile, consistency, coverage)
                - _ranking_score(next_item[0], next_item[2], next_item[3])
                if consistency is not None and next_item is not None
                else None
            )
            suggested = (
                profile.assessment_mode != "manual"
                and
                consistency is not None
                and consistency >= configuration.suggestion_threshold
                and coverage >= configuration.minimum_evidence_coverage
                and required_coverage
                >= configuration.minimum_required_evidence_coverage
                and contradictions == 0
            )
            if (
                suggested
                and consistency >= configuration.high_confidence_threshold
                and coverage >= 0.75
                and (margin or 0) >= configuration.high_margin
            ):
                confidence = "high"
            elif (
                suggested
                and consistency >= configuration.moderate_confidence_threshold
                and coverage >= 0.50
                and (margin or 0) >= configuration.moderate_margin
            ):
                confidence = "moderate"
            else:
                confidence = "low"
            classification = _classification(consistency, required)
            if profile.assessment_mode == "manual":
                classification = "Manual confirmation required"
            elif not suggested:
                classification = "No inherited-form match"
            narrative = (
                f"{classification} {profile.name} candidate. "
                f"Observed consistency is {consistency:.1%} across {coverage:.1%} "
                "of the profile's weighted evidence."
                if consistency is not None
                else f"{profile.name} could not be scored from the available evidence."
            )
            candidates.append(
                FormCandidateResult(
                    rank=index + 1,
                    profile_id=profile.profile_id,
                    profile_name=profile.name,
                    definition=profile.definition,
                    tooltip=_tooltip(profile, evidence),
                    consistency=consistency,
                    evidence_coverage=coverage,
                    required_feature_agreement=required,
                    required_evidence_coverage=required_coverage,
                    required_contradiction_count=contradictions,
                    margin_over_next=margin,
                    confidence=confidence,
                    classification=classification,
                    suggested=suggested,
                    assessment_mode=profile.assessment_mode,
                    narrative=narrative,
                    feature_evidence=evidence,
                )
            )
        best = next((candidate for candidate in candidates if candidate.suggested), None)
        alternative = next(
            (
                candidate
                for candidate in candidates
                if candidate is not best
                and candidate.consistency is not None
                and candidate.assessment_mode != "manual"
            ),
            None,
        ) if best is not None else None
        warnings = []
        if best is None:
            warnings.append(
                ModuleWarning(
                    code="inherited_form_no_suggestion",
                    message=(
                        "No candidate met the configured suggestion and evidence "
                        "thresholds. The ranked evidence remains available for inspection."
                    ),
                    severity=WarningSeverity.INFORMATION,
                )
            )
        elif best.confidence == "low":
            warnings.append(
                ModuleWarning(
                    code="inherited_form_low_confidence",
                    message=(
                        f"{best.profile_name} is a low-confidence potential match; "
                        "inspect coverage, required features, and the nearest alternative."
                    ),
                )
            )
        module_result = self._module_result(
            module_input,
            configuration,
            tuple(candidates),
            best,
            alternative,
            tuple(warnings),
        )
        return InheritedFormAnalysisResult(
            module_result=module_result,
            configuration=configuration,
            registry_version=PROFILE_REGISTRY_VERSION,
            status="suggested" if best is not None else "no_match",
            best_candidate=best,
            nearest_alternative=alternative,
            candidates=tuple(candidates),
        )

    @staticmethod
    def _module_result(
        module_input: ModuleInput,
        configuration: InheritedFormConfiguration,
        candidates: tuple[FormCandidateResult, ...],
        best: FormCandidateResult | None,
        alternative: FormCandidateResult | None,
        warnings: tuple[ModuleWarning, ...],
    ) -> ModuleResult:
        metrics = [
            ModuleMetric(
                "inherited_form.result_status",
                "suggested" if best is not None else "no_match",
                ResultLayer.INTERPRETATION,
                unit="status label",
                denominator=f"{len(candidates)} enabled inherited-form profiles",
                note="A suggestion is a rule-based potential match, not a declaration of genre identity.",
            ),
            ModuleMetric(
                "inherited_form.best_candidate_id",
                best.profile_id if best else None,
                ResultLayer.INTERPRETATION,
                unit="profile ID",
                denominator="ranked enabled profiles",
            ),
            ModuleMetric(
                "inherited_form.best_candidate_name",
                best.profile_name if best else None,
                ResultLayer.INTERPRETATION,
                unit="display label",
                denominator="ranked enabled profiles",
            ),
            ModuleMetric(
                "inherited_form.best_consistency",
                best.consistency if best else None,
                ResultLayer.COMPUTED_SUMMARY,
                unit="proportion",
                denominator="available weighted profile evidence",
            ),
            ModuleMetric(
                "inherited_form.best_evidence_coverage",
                best.evidence_coverage if best else candidates[0].evidence_coverage,
                ResultLayer.COMPUTED_SUMMARY,
                unit="proportion",
                denominator="potential profile weight",
            ),
            ModuleMetric(
                "inherited_form.confidence_label",
                best.confidence if best else "none",
                ResultLayer.INTERPRETATION,
                unit="rule-based evidence label",
                denominator="consistency, coverage, required-feature contradictions, and candidate margin",
                note="Confidence is not a probability.",
            ),
            ModuleMetric(
                "inherited_form.classification",
                best.classification if best else "No inherited-form match",
                ResultLayer.INTERPRETATION,
                unit="conformity label",
                denominator="documented consistency thresholds",
            ),
            ModuleMetric(
                "inherited_form.nearest_alternative_id",
                alternative.profile_id if alternative else None,
                ResultLayer.COMPUTED_SUMMARY,
                unit="profile ID",
                denominator="second-ranked enabled profile",
            ),
            ModuleMetric(
                "inherited_form.nearest_alternative_name",
                alternative.profile_name if alternative else None,
                ResultLayer.COMPUTED_SUMMARY,
                unit="display label",
                denominator="second-ranked enabled profile",
            ),
            ModuleMetric(
                "inherited_form.candidate_margin",
                best.margin_over_next if best else None,
                ResultLayer.COMPUTED_SUMMARY,
                unit="coverage-adjusted ranking-score difference",
                denominator="best minus next automatically suggestible candidate",
            ),
        ]
        for candidate in candidates:
            scope_id = candidate.profile_id
            metrics.extend(
                (
                    ModuleMetric(
                        "inherited_form.candidate_name",
                        candidate.profile_name,
                        ResultLayer.INTERPRETATION,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="display label",
                        denominator="one versioned form profile",
                    ),
                    ModuleMetric(
                        "inherited_form.candidate_rank",
                        candidate.rank,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="rank",
                        denominator=f"{len(candidates)} enabled profiles",
                    ),
                    ModuleMetric(
                        "inherited_form.candidate_consistency",
                        candidate.consistency,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="proportion",
                        denominator="available weighted profile evidence",
                    ),
                    ModuleMetric(
                        "inherited_form.candidate_evidence_coverage",
                        candidate.evidence_coverage,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="proportion",
                        denominator="potential profile weight",
                    ),
                    ModuleMetric(
                        "inherited_form.candidate_classification",
                        candidate.classification,
                        ResultLayer.INTERPRETATION,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="conformity label",
                        denominator="documented consistency thresholds",
                    ),
                    ModuleMetric(
                        "inherited_form.candidate_assessment_mode",
                        candidate.assessment_mode,
                        ResultLayer.INTERPRETATION,
                        scope="candidate",
                        scope_id=scope_id,
                        unit="assessment-mode label",
                        denominator="versioned profile registry",
                        note=(
                            "Manual profiles remain inspectable but cannot become "
                            "automatic suggestions."
                        ),
                    ),
                )
            )
        available_rules = sum(
            evidence.score is not None
            for candidate in candidates
            for evidence in candidate.feature_evidence
        )
        total_rules = sum(len(candidate.feature_evidence) for candidate in candidates)
        coverage = (
            ModuleCoverage.from_counts(
                coverage_id="inherited_form.rule_evidence",
                eligible_count=total_rules,
                matched_count=available_rules,
                unit="profile rules",
                note="Unavailable dependent evidence remains missing rather than receiving a zero score.",
            ),
        )
        provenance = ModuleProvenance(
            software_version=__version__,
            source_text_sha256=module_input.document.text_sha256,
            preprocessing_recipe=module_input.preprocessing.recipe_id,
            pipeline_name="VerseVAD inherited-form candidate ranking",
            pipeline_version=MODULE_VERSION,
            configuration_id=configuration.configuration_id,
            scenario_id=configuration.scenario_id,
            lookup_policy="Versioned rule profiles with graded structural evidence.",
            inclusion_policy=(
                "Nonblank physical lines; missing pronunciation, meter, or rhyme "
                "evidence lowers coverage and is never converted to mismatch."
            ),
            resources=(),
        )
        signature = "|".join(
            (
                module_input.document.text_version_id,
                configuration.configuration_id,
                *(candidate.profile_id + ":" + str(candidate.consistency) for candidate in candidates),
            )
        )
        return ModuleResult(
            result_id="inherited-form:" + hashlib.sha256(signature.encode("utf-8")).hexdigest(),
            module_name=MODULE_NAME,
            module_version=MODULE_VERSION,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=tuple(metrics),
            coverage=coverage,
            warnings=warnings,
            provenance=provenance,
        )


__all__ = [
    "InheritedFormAnalysisResult",
    "InheritedFormConfiguration",
    "InheritedFormEngine",
    "FormCandidateResult",
    "FormFeatureEvidence",
    "MODULE_NAME",
    "MODULE_VERSION",
]
