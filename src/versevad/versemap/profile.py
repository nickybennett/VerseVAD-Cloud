"""Pinned, auditable feature extraction for VerseMap Standard Profile 1.0."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from versevad import __version__
from versevad.analysis.phase2 import stopword_eligible_token_ids
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
from versevad.core.resources import ResourceProvenance
from versevad.lexical_style import calculate_hdd, calculate_mattr, calculate_mtld
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.concreteness import ConcretenessConfiguration
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.lexical_style import LexicalStyleConfiguration

if TYPE_CHECKING:
    from versevad.application import WorkspaceAnalysis


PROFILE_ID = "versemap-standard-profile-1.0"
PROFILE_BUILD_ID = "versemap-profile-build-1.0.0"
MODULE_NAME = "versemap"
MODULE_VERSION = "1.0.0"
CONTENT_POS_TAGS = frozenset({"NOUN", "VERB", "ADJ", "ADV"})
EMOTION_CATEGORIES = (
    "anger",
    "anticipation",
    "disgust",
    "fear",
    "joy",
    "sadness",
    "surprise",
    "trust",
)


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    label: str
    group_id: str
    unit: str
    transform: str = "identity"
    description: str = ""


FEATURE_DEFINITIONS = (
    FeatureDefinition("vad_valence_mean", "Valence Mean", "vad", "normalized 0-1"),
    FeatureDefinition("vad_valence_sd", "Valence Dispersion", "vad", "population SD"),
    FeatureDefinition("vad_arousal_mean", "Arousal Mean", "vad", "normalized 0-1"),
    FeatureDefinition("vad_arousal_sd", "Arousal Dispersion", "vad", "population SD"),
    FeatureDefinition("vad_dominance_mean", "Dominance Mean", "vad", "normalized 0-1"),
    FeatureDefinition("vad_dominance_sd", "Dominance Dispersion", "vad", "population SD"),
    *(
        FeatureDefinition(
            f"emotion_{category}_proportion",
            f"{category.title()} Association",
            "emotion",
            "eligible-token proportion",
        )
        for category in EMOTION_CATEGORIES
    ),
    FeatureDefinition("concreteness_mean", "Concreteness Mean", "concreteness", "1-5"),
    FeatureDefinition(
        "concreteness_sd", "Concreteness Dispersion", "concreteness", "population SD"
    ),
    FeatureDefinition(
        "lexical_rarity_mean",
        "Lexical Rarity",
        "lexical_norms",
        "7 minus SUBTLEX Zipf",
    ),
    FeatureDefinition(
        "age_of_acquisition_mean",
        "Age of Acquisition",
        "lexical_norms",
        "years",
    ),
    FeatureDefinition("mattr", "MATTR", "lexical_character", "proportion"),
    FeatureDefinition("hdd", "HD-D", "lexical_character", "proportion"),
    FeatureDefinition(
        "mtld", "MTLD", "lexical_character", "tokens", transform="log1p"
    ),
    FeatureDefinition(
        "mean_content_word_length",
        "Mean Content-Word Length",
        "lexical_character",
        "alphabetic characters",
        transform="log1p",
    ),
    FeatureDefinition("noun_proportion", "Noun Proportion", "part_of_speech", "proportion"),
    FeatureDefinition("verb_proportion", "Verb Proportion", "part_of_speech", "proportion"),
    FeatureDefinition(
        "adjective_proportion", "Adjective Proportion", "part_of_speech", "proportion"
    ),
    FeatureDefinition(
        "adverb_proportion", "Adverb Proportion", "part_of_speech", "proportion"
    ),
    FeatureDefinition(
        "mean_words_per_line",
        "Mean Words per Line",
        "structure",
        "lexical tokens",
        transform="log1p",
    ),
    FeatureDefinition(
        "sd_words_per_line",
        "Line-Length Dispersion",
        "structure",
        "population SD",
        transform="log1p",
    ),
    FeatureDefinition(
        "mean_words_per_stanza",
        "Mean Words per Stanza",
        "structure",
        "lexical tokens",
        transform="log1p",
    ),
    FeatureDefinition(
        "mean_lines_per_stanza",
        "Mean Lines per Stanza",
        "structure",
        "nonblank lines",
        transform="log1p",
    ),
)
FEATURE_BY_ID = {item.feature_id: item for item in FEATURE_DEFINITIONS}


def standard_concreteness_configuration() -> ConcretenessConfiguration:
    return ConcretenessConfiguration(
        exclude_proper_nouns=True,
        scenario_id="versemap-concreteness-1.0",
    )


def standard_frequency_configuration() -> FrequencyConfiguration:
    return FrequencyConfiguration(
        exclude_proper_nouns=True,
        content_words_only=True,
        minimum_matched_tokens=1,
        scenario_id="versemap-frequency-1.0",
    )


def standard_aoa_configuration() -> AoAConfiguration:
    return AoAConfiguration(
        exclude_proper_nouns=True,
        content_words_only=True,
        minimum_matched_tokens=1,
        scenario_id="versemap-aoa-1.0",
    )


def standard_lexical_style_configuration() -> LexicalStyleConfiguration:
    return LexicalStyleConfiguration(scenario_id="versemap-lexical-style-1.0")


@dataclass(frozen=True)
class FeatureObservation:
    feature_id: str
    value: float | None
    eligible_count: int
    matched_count: int
    note: str = ""

    @property
    def coverage_rate(self) -> float | None:
        return (
            self.matched_count / self.eligible_count
            if self.eligible_count
            else None
        )


@dataclass(frozen=True)
class VerseMapProfile:
    profile_id: str
    text_id: str
    text_version_id: str
    title: str
    observations: tuple[FeatureObservation, ...]
    content_token_count: int
    warnings: tuple[str, ...] = ()

    @property
    def values(self) -> dict[str, float | None]:
        return {item.feature_id: item.value for item in self.observations}

    @property
    def observation_map(self) -> dict[str, FeatureObservation]:
        return {item.feature_id: item for item in self.observations}


def _mean(values: Iterable[float]) -> float | None:
    rows = tuple(float(value) for value in values if math.isfinite(float(value)))
    return statistics.fmean(rows) if rows else None


def _population_sd(values: Iterable[float]) -> float | None:
    rows = tuple(float(value) for value in values if math.isfinite(float(value)))
    return statistics.pstdev(rows) if rows else None


def _observation(
    feature_id: str,
    value: float | None,
    *,
    eligible: int,
    matched: int,
    note: str = "",
) -> FeatureObservation:
    return FeatureObservation(
        feature_id=feature_id,
        value=(float(value) if value is not None and math.isfinite(value) else None),
        eligible_count=max(int(eligible), 0),
        matched_count=min(max(int(matched), 0), max(int(eligible), 0)),
        note=note,
    )


def extract_standard_profile(workspace: WorkspaceAnalysis) -> VerseMapProfile:
    """Extract Profile 1.0 from shared results without neutral imputation."""

    if workspace.poem_document is None:
        raise ValueError("VerseMap requires the shared poem processing record.")

    tokens = tuple(workspace.poem_document.tokens)
    vad = next(
        (
            result
            for result in workspace.results
            if result.lexicon_metadata.lexicon_id == "nrc_vad_v2_1"
        ),
        None,
    )
    emotion = next(
        (
            result
            for result in workspace.results
            if result.lexicon_metadata.lexicon_id == "nrc_emotion_v0_92"
        ),
        None,
    )
    policy_source = vad or emotion
    policy_eligible_ids = (
        stopword_eligible_token_ids(
            policy_source.tokens,
            policy_source.matches,
            policy_source.stopword_policy,
        )
        if policy_source is not None
        and policy_source.stopword_policy is not None
        else frozenset(
            token.token_id
            for token in tokens
            if token.is_lexical and not token.is_stopword
        )
    )
    eligible_tokens = tuple(
        token
        for token in tokens
        if token.is_lexical
        and token.part_of_speech in CONTENT_POS_TAGS
        and token.token_id in policy_eligible_ids
    )
    eligible_ids = {token.token_id for token in eligible_tokens}
    eligible_count = len(eligible_tokens)
    observations: dict[str, FeatureObservation] = {}
    warnings: list[str] = []

    if vad is not None:
        included = tuple(
            match
            for match in vad.matches
            if match.included
            and match.included_in_stopword_view
            and match.normalized_scores is not None
            and match.token_ids
            and set(match.token_ids).issubset(eligible_ids)
        )
        matched_ids = (
            set().union(*(set(match.token_ids) for match in included))
            if included
            else set()
        )
        for dimension in ("valence", "arousal", "dominance"):
            values = tuple(
                getattr(match.normalized_scores, dimension) for match in included
            )
            observations[f"vad_{dimension}_mean"] = _observation(
                f"vad_{dimension}_mean",
                _mean(values),
                eligible=eligible_count,
                matched=len(matched_ids),
                note="NRC VAD v2.1; token-weighted, stopwords removed, content POS only.",
            )
            observations[f"vad_{dimension}_sd"] = _observation(
                f"vad_{dimension}_sd",
                _population_sd(values),
                eligible=eligible_count,
                matched=len(matched_ids),
                note="Population standard deviation over retained matched occurrences.",
            )
    else:
        warnings.append("NRC VAD v2.1 evidence was unavailable.")

    for category in EMOTION_CATEGORIES:
        feature_id = f"emotion_{category}_proportion"
        if emotion is None:
            observations[feature_id] = _observation(
                feature_id, None, eligible=eligible_count, matched=0
            )
            continue
        category_ids: set[str] = set()
        all_matched_ids: set[str] = set()
        for match in emotion.matches:
            if (
                match.included
                and match.included_in_stopword_view
                and match.token_ids
                and set(match.token_ids).issubset(eligible_ids)
            ):
                all_matched_ids.update(match.token_ids)
                if category in match.associations:
                    category_ids.update(match.token_ids)
        observations[feature_id] = _observation(
            feature_id,
            len(category_ids) / eligible_count if eligible_count else None,
            eligible=eligible_count,
            matched=len(all_matched_ids),
            note=(
                "NRC Emotion v0.92 token-position association prevalence. "
                "Categories are multi-label and need not sum to one."
            ),
        )
    if emotion is None:
        warnings.append("NRC Emotion v0.92 evidence was unavailable.")

    def lexical_values(result, attribute: str) -> tuple[float, ...]:
        if result is None:
            return ()
        return tuple(
            float(value)
            for row in result.token_audit
            if row.token_id in eligible_ids
            and row.included
            and (value := getattr(row, attribute)) is not None
        )

    concrete_values = lexical_values(workspace.concreteness, "rating")
    observations["concreteness_mean"] = _observation(
        "concreteness_mean",
        _mean(concrete_values),
        eligible=eligible_count,
        matched=len(concrete_values),
        note="Brysbaert et al. ratings; repeated eligible token occurrences retained.",
    )
    observations["concreteness_sd"] = _observation(
        "concreteness_sd",
        _population_sd(concrete_values),
        eligible=eligible_count,
        matched=len(concrete_values),
    )

    frequency_values = lexical_values(workspace.frequency, "zipf_value")
    frequency_mean = _mean(frequency_values)
    observations["lexical_rarity_mean"] = _observation(
        "lexical_rarity_mean",
        7.0 - frequency_mean if frequency_mean is not None else None,
        eligible=eligible_count,
        matched=len(frequency_values),
        note="Higher means rarer: 7.0 minus mean SUBTLEX-US Zipf frequency.",
    )
    aoa_values = lexical_values(workspace.aoa, "mean_age")
    observations["age_of_acquisition_mean"] = _observation(
        "age_of_acquisition_mean",
        _mean(aoa_values),
        eligible=eligible_count,
        matched=len(aoa_values),
        note="Kuperman et al. mean acquisition age in years.",
    )

    normalized_lemmas = tuple(
        token.normalized_lemma or token.normalized_form
        for token in eligible_tokens
        if token.normalized_lemma or token.normalized_form
    )
    alpha_lengths = tuple(
        value
        for token in eligible_tokens
        if (
            value := sum(
                character.isalpha() for character in token.lemma or token.surface_form
            )
        )
    )
    observations["mattr"] = _observation(
        "mattr",
        calculate_mattr(normalized_lemmas, window_size=50),
        eligible=eligible_count,
        matched=len(normalized_lemmas),
        note="POS-aware normalized lemmas; fixed 50-token overlapping windows.",
    )
    observations["hdd"] = _observation(
        "hdd",
        calculate_hdd(normalized_lemmas, sample_size=42),
        eligible=eligible_count,
        matched=len(normalized_lemmas),
        note="POS-aware normalized lemmas; fixed without-replacement sample of 42.",
    )
    observations["mtld"] = _observation(
        "mtld",
        calculate_mtld(normalized_lemmas, threshold=0.72),
        eligible=eligible_count,
        matched=len(normalized_lemmas),
        note="Bidirectional MTLD over POS-aware normalized lemmas at TTR 0.72.",
    )
    observations["mean_content_word_length"] = _observation(
        "mean_content_word_length",
        _mean(alpha_lengths),
        eligible=eligible_count,
        matched=len(alpha_lengths),
    )
    for tag, feature_id in (
        ("NOUN", "noun_proportion"),
        ("VERB", "verb_proportion"),
        ("ADJ", "adjective_proportion"),
        ("ADV", "adverb_proportion"),
    ):
        observations[feature_id] = _observation(
            feature_id,
            (
                sum(token.part_of_speech == tag for token in eligible_tokens)
                / eligible_count
                if eligible_count
                else None
            ),
            eligible=eligible_count,
            matched=eligible_count,
        )

    lexical = workspace.lexical_style
    if lexical is not None:
        summary = lexical.summary
        line_stats = summary.nonblank_line_word_count_statistics
        stanza_word_stats = summary.stanza_word_count_statistics
        stanza_line_stats = summary.stanza_line_count_statistics
        for feature_id, value, count in (
            ("mean_words_per_line", line_stats.mean, line_stats.count),
            (
                "sd_words_per_line",
                line_stats.population_standard_deviation,
                line_stats.count,
            ),
            ("mean_words_per_stanza", stanza_word_stats.mean, stanza_word_stats.count),
            ("mean_lines_per_stanza", stanza_line_stats.mean, stanza_line_stats.count),
        ):
            observations[feature_id] = _observation(
                feature_id, value, eligible=count, matched=count
            )

    for definition in FEATURE_DEFINITIONS:
        observations.setdefault(
            definition.feature_id,
            _observation(
                definition.feature_id,
                None,
                eligible=eligible_count,
                matched=0,
                note="Required supporting evidence was unavailable.",
            ),
        )
    unavailable = sum(item.value is None for item in observations.values())
    if unavailable:
        warnings.append(
            f"{unavailable} of {len(FEATURE_DEFINITIONS)} profile dimensions remain "
            "missing; VerseMap distance uses only shared, weighted evidence."
        )
    return VerseMapProfile(
        profile_id=PROFILE_ID,
        text_id=workspace.document.text_id,
        text_version_id=workspace.document.text_version_id,
        title=workspace.document.title,
        observations=tuple(observations[item.feature_id] for item in FEATURE_DEFINITIONS),
        content_token_count=eligible_count,
        warnings=tuple(warnings),
    )


def build_module_result(
    module_input: ModuleInput,
    profile: VerseMapProfile,
    *,
    reference_release_id: str,
    reference_release_sha256: str,
    model_id: str,
    evidence_weight_coverage: float | None,
    x: float | None,
    y: float | None,
) -> ModuleResult:
    metrics = [
        ModuleMetric(
            f"versemap.{item.feature_id}",
            item.value,
            ResultLayer.COMPUTED_SUMMARY,
            unit=FEATURE_BY_ID[item.feature_id].unit,
            weighting="standard-profile-token",
            denominator=(
                f"{item.matched_count} matched of {item.eligible_count} eligible "
                "observations"
            ),
            note=item.note,
        )
        for item in profile.observations
    ]
    metrics.extend(
        (
            ModuleMetric(
                "versemap.coordinate_1",
                x,
                ResultLayer.INTERPRETATION,
                unit="weighted PCA coordinate",
            ),
            ModuleMetric(
                "versemap.coordinate_2",
                y,
                ResultLayer.INTERPRETATION,
                unit="weighted PCA coordinate",
            ),
            ModuleMetric(
                "versemap.evidence_weight_coverage",
                evidence_weight_coverage,
                ResultLayer.COMPUTED_SUMMARY,
                unit="proportion of registered feature weight",
            ),
        )
    )
    coverage = tuple(
        ModuleCoverage.from_counts(
            coverage_id=f"versemap.{item.feature_id}",
            eligible_count=item.eligible_count,
            matched_count=item.matched_count,
            unit="eligible observations",
            note=item.note,
        )
        for item in profile.observations
    )
    module_warnings = tuple(
        ModuleWarning(
            code=f"versemap.profile_warning_{index}",
            message=message,
            severity=WarningSeverity.CAUTION,
        )
        for index, message in enumerate(profile.warnings, start=1)
    )
    identity = json.dumps(
        {
            "text_version_id": module_input.document.text_version_id,
            "profile_id": PROFILE_ID,
            "reference_release_id": reference_release_id,
            "model_id": model_id,
            "values": profile.values,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return ModuleResult(
        result_id="versemap-result-v1:"
        + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        text_id=module_input.document.text_id,
        text_version_id=module_input.document.text_version_id,
        metrics=tuple(metrics),
        coverage=coverage,
        warnings=module_warnings,
        provenance=ModuleProvenance(
            software_version=__version__,
            source_text_sha256=module_input.document.text_sha256,
            preprocessing_recipe=module_input.preprocessing.recipe_id,
            pipeline_name=module_input.preprocessing.pipeline_name,
            pipeline_version=module_input.preprocessing.pipeline_version,
            configuration_id=PROFILE_ID,
            scenario_id=PROFILE_ID,
            lookup_policy=(
                "Lowercase NFC lookup through pinned shared adapters; POS-aware "
                "lemmatization for lexical diversity; original source preserved."
            ),
            inclusion_policy=(
                "Token-weighted; repeated words retained; stopwords removed; "
                "NOUN, VERB, ADJ, and ADV used for lexical metrics; count-based "
                "formal measures normalized by their documented structural unit."
            ),
            resources=(
                ResourceProvenance(
                    resource_id="versemap_reference_corpus",
                    display_name="VerseMap Reference Corpus",
                    version=reference_release_id,
                    source_sha256=reference_release_sha256,
                    license_notice=(
                        "Bundled public-domain poem texts; individual source "
                        "provenance remains recorded in the reference inventory."
                    ),
                    adapter_version=PROFILE_BUILD_ID,
                ),
            ),
        ),
    )


__all__ = [
    "CONTENT_POS_TAGS",
    "EMOTION_CATEGORIES",
    "FEATURE_BY_ID",
    "FEATURE_DEFINITIONS",
    "FeatureDefinition",
    "FeatureObservation",
    "MODULE_NAME",
    "MODULE_VERSION",
    "PROFILE_BUILD_ID",
    "PROFILE_ID",
    "VerseMapProfile",
    "build_module_result",
    "extract_standard_profile",
    "standard_aoa_configuration",
    "standard_concreteness_configuration",
    "standard_frequency_configuration",
    "standard_lexical_style_configuration",
]
