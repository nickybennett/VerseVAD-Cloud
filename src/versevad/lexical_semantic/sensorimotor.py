"""Normative sensorimotor imagery and embodiment evidence."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from versevad import __version__
from versevad.adapters.lancaster_sensorimotor import (
    DIMENSION_COLUMNS,
    LancasterSensorimotorAdapter,
    LancasterSensorimotorAdapterError,
    LancasterSensorimotorLexicon,
    SensorimotorEntry,
    SensorimotorVector,
)
from versevad.analysis.statistics import descriptive_statistics
from versevad.core.documents import StructuralUnitKind
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
from versevad.core.resources import (
    LocalResourceManager,
    ResourceProvenance,
    ResourceSpec,
    ResourceState,
    ResourceStatus,
)
from versevad.models import DescriptiveStatistics, StopwordMode, TokenRecord
from versevad.lexical_eligibility import (
    LEXICON_ELIGIBILITY_POLICY_ID,
    append_lexicon_eligibility_note,
    is_lexicon_eligible,
    lexicon_eligibility_note_for_tokens,
)
from versevad.normalization import normalize_lookup, possessive_base
from versevad.stopwords import (
    DEFAULT_PROTECTED_WORDS,
    build_stopword_policy,
    classify_match_stopword,
)


LANCASTER_SENSORIMOTOR_RELATIVE_PATH = Path(
    "Lancaster_Sensorimotor_Norms"
) / "Lancaster_sensorimotor_norms_for_39707_words.csv"
LANCASTER_SENSORIMOTOR_SHA256 = (
    "445d363fb1f9f3e50b86d88e2f46cdc9a22b5dd8a713ce4e7be2a773d57f43c5"
)
LANCASTER_SENSORIMOTOR_CITATION = (
    "Lynott, D., Connell, L., Brysbaert, M., Brand, J., & Carney, J. "
    "(2020). The Lancaster Sensorimotor Norms: multidimensional measures "
    "of perceptual and action strength for 40,000 English words. "
    "Behavior Research Methods, 52, 1271-1291. "
    "https://doi.org/10.3758/s13428-019-01316-z"
)
LANCASTER_SENSORIMOTOR_LICENSE = (
    "The published resource identifies the data as Creative Commons "
    "Attribution 4.0 (CC BY 4.0). Retain the source citation, license, and "
    "exact source checksum."
)
LANCASTER_SENSORIMOTOR_SPEC = ResourceSpec(
    resource_id="lancaster-sensorimotor-2020",
    display_name="Lancaster Sensorimotor Norms",
    relative_path=LANCASTER_SENSORIMOTOR_RELATIVE_PATH,
    version="2020-39,707-concepts",
    accepted_sha256=(LANCASTER_SENSORIMOTOR_SHA256,),
    minimum_bytes=10_000_000,
    citation=LANCASTER_SENSORIMOTOR_CITATION,
    license_notice=LANCASTER_SENSORIMOTOR_LICENSE,
)


@dataclass(frozen=True)
class SensorimotorDimension:
    dimension_id: str
    label: str
    family: str
    definition: str


SENSORIMOTOR_DIMENSIONS = (
    SensorimotorDimension(
        "auditory",
        "Auditory",
        "perceptual",
        "Normative strength of experiencing a concept through hearing.",
    ),
    SensorimotorDimension(
        "gustatory",
        "Gustatory",
        "perceptual",
        "Normative strength of experiencing a concept through taste.",
    ),
    SensorimotorDimension(
        "haptic",
        "Haptic",
        "perceptual",
        "Normative strength of experiencing a concept through touch.",
    ),
    SensorimotorDimension(
        "interoceptive",
        "Interoceptive",
        "perceptual",
        "Normative strength of experiencing a concept through sensations inside the body.",
    ),
    SensorimotorDimension(
        "olfactory",
        "Olfactory",
        "perceptual",
        "Normative strength of experiencing a concept through smell.",
    ),
    SensorimotorDimension(
        "visual",
        "Visual",
        "perceptual",
        "Normative strength of experiencing a concept through sight.",
    ),
    SensorimotorDimension(
        "foot_leg",
        "Foot / Leg Action",
        "action",
        "Normative strength of experiencing a concept through foot or leg action.",
    ),
    SensorimotorDimension(
        "hand_arm",
        "Hand / Arm Action",
        "action",
        "Normative strength of experiencing a concept through hand or arm action.",
    ),
    SensorimotorDimension(
        "head",
        "Head Action",
        "action",
        "Normative strength of experiencing a concept through head action, excluding the mouth.",
    ),
    SensorimotorDimension(
        "mouth",
        "Mouth / Throat Action",
        "action",
        "Normative strength of experiencing a concept through mouth or throat action.",
    ),
    SensorimotorDimension(
        "torso",
        "Torso Action",
        "action",
        "Normative strength of experiencing a concept through torso action.",
    ),
)
DIMENSION_BY_ID = {
    dimension.dimension_id: dimension for dimension in SENSORIMOTOR_DIMENSIONS
}


class SensorimotorModuleError(RuntimeError):
    pass


class SensorimotorMatchMethod(StrEnum):
    PHRASE = "exact_published_phrase"
    EXACT = "exact_normalized_surface"
    POSSESSIVE = "possessive_normalization"
    LEMMA = "pos_sensitive_lemma"


@dataclass(frozen=True)
class SensorimotorConfiguration:
    include_phrases: bool = True
    exclude_proper_nouns: bool = False
    minimum_match_requirement: int = 3
    top_term_count: int = 12
    stopword_mode: StopwordMode = StopwordMode.STANDARD
    protected_stopwords: tuple[str, ...] = DEFAULT_PROTECTED_WORDS
    custom_stopword_additions: tuple[str, ...] = ()
    custom_stopword_removals: tuple[str, ...] = ()
    scenario_id: str = "lancaster-sensorimotor-default-v2"

    def __post_init__(self) -> None:
        if self.minimum_match_requirement < 1:
            raise ValueError("The sensorimotor minimum match count must be at least 1.")
        if self.top_term_count < 1:
            raise ValueError("The sensorimotor top-term count must be at least 1.")

    @property
    def configuration_id(self) -> str:
        payload = asdict(self)
        payload["stopword_mode"] = self.stopword_mode.value
        digest = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:16]
        return f"lancaster-sensorimotor-v2:{digest}"


@dataclass(frozen=True)
class SensorimotorObservation:
    observation_id: str
    token_ids: tuple[str, ...]
    token_position: int
    line_number: int
    stanza_number: int
    surface_form: str
    normalized_surface: str
    normalized_lemma: str
    part_of_speech: str
    match_method: SensorimotorMatchMethod
    matched_source_term: str
    matched_lookup_form: str
    source_row: int
    source_is_multiword: bool
    stopword_status: str
    stopword_reason: str
    included_in_stopword_view: bool
    means: SensorimotorVector
    source_standard_deviations: SensorimotorVector
    max_perceptual_strength: float
    minkowski3_perceptual_strength: float
    perceptual_exclusivity: float
    dominant_perceptual: str
    max_action_strength: float
    minkowski3_action_strength: float
    action_exclusivity: float
    dominant_action: str
    max_sensorimotor_strength: float
    minkowski3_sensorimotor_strength: float
    sensorimotor_exclusivity: float
    dominant_sensorimotor: str
    percent_known_perceptual: float
    percent_known_action: float
    context: str
    eligibility_note: str = ""


@dataclass(frozen=True)
class SensorimotorUnmatchedToken:
    token_id: str
    token_position: int
    surface_form: str
    normalized_form: str
    normalized_lemma: str
    part_of_speech: str
    line_number: int
    stanza_number: int
    reason: str
    context: str


@dataclass(frozen=True)
class SensorimotorDimensionSummary:
    dimension_id: str
    label: str
    family: str
    statistics: DescriptiveStatistics
    cumulative_load: float | None
    load_per_100_observations: float | None


@dataclass(frozen=True)
class SensorimotorCategorySummary:
    category: str
    label: str
    family: str
    count: int
    proportion: float | None


@dataclass(frozen=True)
class SensorimotorProfile:
    profile_id: str
    analysis_view: str
    weighting: str
    eligible_token_count: int
    matched_token_count: int
    token_coverage: float | None
    matched_observation_count: int
    matched_type_count: int
    dimensions: tuple[SensorimotorDimensionSummary, ...]
    perceptual_strength: DescriptiveStatistics
    action_strength: DescriptiveStatistics
    overall_sensorimotor_strength: DescriptiveStatistics
    perceptual_exclusivity: DescriptiveStatistics
    action_exclusivity: DescriptiveStatistics
    sensorimotor_exclusivity: DescriptiveStatistics
    dominant_categories: tuple[SensorimotorCategorySummary, ...]
    dominant_category_diversity: float | None


@dataclass(frozen=True)
class SensorimotorStructuralSummary:
    analysis_view: str
    scope: str
    scope_id: str
    ordinal: int
    source_text: str
    eligible_token_count: int
    matched_token_count: int
    token_coverage: float | None
    matched_observation_count: int
    dimension_means: tuple[tuple[str, float | None], ...]


@dataclass(frozen=True)
class SensorimotorTermSummary:
    source_term: str
    lookup_form: str
    source_row: int
    source_is_multiword: bool
    observation_count: int
    surface_forms: tuple[str, ...]
    part_of_speech_tags: tuple[str, ...]
    means: SensorimotorVector
    dominant_sensorimotor: str
    minkowski3_sensorimotor_strength: float
    sensorimotor_exclusivity: float


@dataclass(frozen=True)
class SensorimotorAnalysisResult:
    module_result: ModuleResult
    configuration: SensorimotorConfiguration
    resource_status: ResourceStatus
    profiles: tuple[SensorimotorProfile, ...]
    structural_summaries: tuple[SensorimotorStructuralSummary, ...]
    term_summaries: tuple[SensorimotorTermSummary, ...]
    observations: tuple[SensorimotorObservation, ...]
    unmatched_tokens: tuple[SensorimotorUnmatchedToken, ...]

    def profile(
        self,
        analysis_view: str = "All matched tokens",
        weighting: str = "token",
    ) -> SensorimotorProfile:
        return next(
            profile
            for profile in self.profiles
            if profile.analysis_view == analysis_view
            and profile.weighting == weighting
        )


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _eligible(token: TokenRecord, configuration: SensorimotorConfiguration) -> bool:
    return (
        is_lexicon_eligible(token)
        and not (configuration.exclude_proper_nouns and token.is_proper_noun)
    )


def _entry_for_unigram(
    token: TokenRecord,
    lexicon: LancasterSensorimotorLexicon,
) -> tuple[SensorimotorEntry | None, SensorimotorMatchMethod | None]:
    entry = lexicon.lookup(token.normalized_form)
    if entry is not None and not entry.is_multiword:
        return entry, SensorimotorMatchMethod.EXACT
    possessive = possessive_base(token.normalized_form)
    if possessive:
        entry = lexicon.lookup(possessive)
        if entry is not None and not entry.is_multiword:
            return entry, SensorimotorMatchMethod.POSSESSIVE
    if token.normalized_lemma and token.normalized_lemma != token.normalized_form:
        entry = lexicon.lookup(token.normalized_lemma)
        if entry is not None and not entry.is_multiword:
            return entry, SensorimotorMatchMethod.LEMMA
    return None, None


def _phrase_at(
    tokens: tuple[TokenRecord, ...],
    start: int,
    lexicon: LancasterSensorimotorLexicon,
) -> tuple[SensorimotorEntry, tuple[TokenRecord, ...], SensorimotorMatchMethod] | None:
    first = tokens[start]
    candidate_groups = (
        (
            first.normalized_form,
            lambda group: " ".join(token.normalized_form for token in group),
        ),
        (
            first.normalized_lemma,
            lambda group: " ".join(token.normalized_lemma for token in group),
        ),
    )
    for first_form, joiner in candidate_groups:
        if not first_form:
            continue
        for entry in lexicon.phrases_by_first_word.get(first_form, ()):
            end = start + entry.word_count
            if end > len(tokens):
                continue
            group = tokens[start:end]
            if any(
                current.token_position != previous.token_position + 1
                for previous, current in zip(group, group[1:])
            ):
                continue
            if joiner(group) == entry.lookup_form:
                method = (
                    SensorimotorMatchMethod.PHRASE
                    if first_form == first.normalized_form
                    else SensorimotorMatchMethod.LEMMA
                )
                return entry, group, method
    return None


def _observation(
    entry: SensorimotorEntry,
    tokens: tuple[TokenRecord, ...],
    method: SensorimotorMatchMethod,
    stopword_policy,
) -> SensorimotorObservation:
    status, excluded, reason = classify_match_stopword(
        tokens,
        stopword_policy,
        is_published_phrase=entry.is_multiword,
    )
    surface = " ".join(token.surface_form for token in tokens)
    normalized_surface = " ".join(token.normalized_form for token in tokens)
    normalized_lemma = " ".join(token.normalized_lemma for token in tokens)
    tags = tuple(sorted({token.part_of_speech for token in tokens}))
    signature = "|".join(
        (
            tokens[0].text_version_id,
            ",".join(token.token_id for token in tokens),
            entry.lookup_form,
            method.value,
        )
    )
    return SensorimotorObservation(
        observation_id=hashlib.sha256(signature.encode("utf-8")).hexdigest(),
        token_ids=tuple(token.token_id for token in tokens),
        token_position=tokens[0].token_position,
        line_number=tokens[0].line_number,
        stanza_number=tokens[0].stanza_number,
        surface_form=surface,
        normalized_surface=normalized_surface,
        normalized_lemma=normalized_lemma,
        part_of_speech=tags[0] if len(tags) == 1 else "MIXED",
        match_method=method,
        matched_source_term=entry.source_term,
        matched_lookup_form=entry.lookup_form,
        source_row=entry.source_row,
        source_is_multiword=entry.is_multiword,
        stopword_status=status,
        stopword_reason=reason,
        included_in_stopword_view=not excluded,
        means=entry.means,
        source_standard_deviations=entry.source_standard_deviations,
        max_perceptual_strength=entry.max_perceptual_strength,
        minkowski3_perceptual_strength=entry.minkowski3_perceptual_strength,
        perceptual_exclusivity=entry.perceptual_exclusivity,
        dominant_perceptual=entry.dominant_perceptual,
        max_action_strength=entry.max_action_strength,
        minkowski3_action_strength=entry.minkowski3_action_strength,
        action_exclusivity=entry.action_exclusivity,
        dominant_action=entry.dominant_action,
        max_sensorimotor_strength=entry.max_sensorimotor_strength,
        minkowski3_sensorimotor_strength=entry.minkowski3_sensorimotor_strength,
        sensorimotor_exclusivity=entry.sensorimotor_exclusivity,
        dominant_sensorimotor=entry.dominant_sensorimotor,
        percent_known_perceptual=entry.percent_known_perceptual,
        percent_known_action=entry.percent_known_action,
        context=tokens[0].context,
        eligibility_note=lexicon_eligibility_note_for_tokens(tokens),
    )


def _match(
    module_input: ModuleInput,
    lexicon: LancasterSensorimotorLexicon,
    configuration: SensorimotorConfiguration,
):
    policy = build_stopword_policy(
        mode=configuration.stopword_mode,
        protected_words=configuration.protected_stopwords,
        custom_additions=configuration.custom_stopword_additions,
        custom_removals=configuration.custom_stopword_removals,
    )
    eligible_tokens = tuple(
        token for token in module_input.tokens if _eligible(token, configuration)
    )
    by_line: dict[int, list[TokenRecord]] = {}
    for token in eligible_tokens:
        by_line.setdefault(token.line_number, []).append(token)
    observations: list[SensorimotorObservation] = []
    unmatched: list[SensorimotorUnmatchedToken] = []
    for line_number in sorted(by_line):
        line_tokens = tuple(
            sorted(by_line[line_number], key=lambda token: token.token_position)
        )
        position = 0
        while position < len(line_tokens):
            token = line_tokens[position]
            phrase = (
                _phrase_at(line_tokens, position, lexicon)
                if configuration.include_phrases
                else None
            )
            if phrase is not None:
                entry, group, method = phrase
                observations.append(_observation(entry, group, method, policy))
                position += len(group)
                continue
            entry, method = _entry_for_unigram(token, lexicon)
            if entry is None or method is None:
                unmatched.append(
                    SensorimotorUnmatchedToken(
                        token_id=token.token_id,
                        token_position=token.token_position,
                        surface_form=token.surface_form,
                        normalized_form=token.normalized_form,
                        normalized_lemma=token.normalized_lemma,
                        part_of_speech=token.part_of_speech,
                        line_number=token.line_number,
                        stanza_number=token.stanza_number,
                        reason=append_lexicon_eligibility_note(
                            "No exact surface, possessive-base, or model-lemma entry.",
                            token,
                        ),
                        context=token.context,
                    )
                )
            else:
                observations.append(_observation(entry, (token,), method, policy))
            position += 1
    return tuple(eligible_tokens), tuple(observations), tuple(unmatched), policy


def _dimension_summaries(
    observations: tuple[SensorimotorObservation, ...],
) -> tuple[SensorimotorDimensionSummary, ...]:
    rows = []
    for dimension in SENSORIMOTOR_DIMENSIONS:
        values = tuple(
            getattr(observation.means, dimension.dimension_id)
            for observation in observations
        )
        stats = descriptive_statistics(values)
        cumulative = sum(values) if values else None
        rows.append(
            SensorimotorDimensionSummary(
                dimension_id=dimension.dimension_id,
                label=dimension.label,
                family=dimension.family,
                statistics=stats,
                cumulative_load=cumulative,
                load_per_100_observations=(
                    cumulative / len(values) * 100 if values else None
                ),
            )
        )
    return tuple(rows)


def _dominant_categories(
    observations: tuple[SensorimotorObservation, ...],
) -> tuple[SensorimotorCategorySummary, ...]:
    counts = Counter(
        normalize_lookup(observation.dominant_sensorimotor).replace(" ", "_")
        for observation in observations
    )
    total = len(observations)
    rows = []
    for dimension in SENSORIMOTOR_DIMENSIONS:
        rows.append(
            SensorimotorCategorySummary(
                category=dimension.dimension_id,
                label=dimension.label,
                family=dimension.family,
                count=counts.get(dimension.dimension_id, 0),
                proportion=_rate(counts.get(dimension.dimension_id, 0), total),
            )
        )
    return tuple(rows)


def _diversity(categories: tuple[SensorimotorCategorySummary, ...]) -> float | None:
    proportions = [
        category.proportion
        for category in categories
        if category.proportion is not None and category.proportion > 0
    ]
    if not proportions:
        return None
    if len(SENSORIMOTOR_DIMENSIONS) == 1:
        return 0.0
    entropy = -sum(value * math.log(value) for value in proportions)
    return entropy / math.log(len(SENSORIMOTOR_DIMENSIONS))


def _profile(
    observations: tuple[SensorimotorObservation, ...],
    *,
    analysis_view: str,
    weighting: str,
    eligible_token_count: int,
    matched_token_count: int,
) -> SensorimotorProfile:
    selected = observations
    if weighting == "type":
        unique: dict[str, SensorimotorObservation] = {}
        for observation in selected:
            unique.setdefault(observation.matched_lookup_form, observation)
        selected = tuple(unique.values())
    categories = _dominant_categories(selected)
    profile_id = (
        ("all" if analysis_view == "All matched tokens" else "stopwords_excluded")
        + f"_{weighting}"
    )
    return SensorimotorProfile(
        profile_id=profile_id,
        analysis_view=analysis_view,
        weighting=weighting,
        eligible_token_count=eligible_token_count,
        matched_token_count=matched_token_count,
        token_coverage=_rate(matched_token_count, eligible_token_count),
        matched_observation_count=len(selected),
        matched_type_count=len(
            {observation.matched_lookup_form for observation in selected}
        ),
        dimensions=_dimension_summaries(selected),
        perceptual_strength=descriptive_statistics(
            observation.minkowski3_perceptual_strength
            for observation in selected
        ),
        action_strength=descriptive_statistics(
            observation.minkowski3_action_strength for observation in selected
        ),
        overall_sensorimotor_strength=descriptive_statistics(
            observation.minkowski3_sensorimotor_strength
            for observation in selected
        ),
        perceptual_exclusivity=descriptive_statistics(
            observation.perceptual_exclusivity for observation in selected
        ),
        action_exclusivity=descriptive_statistics(
            observation.action_exclusivity for observation in selected
        ),
        sensorimotor_exclusivity=descriptive_statistics(
            observation.sensorimotor_exclusivity for observation in selected
        ),
        dominant_categories=categories,
        dominant_category_diversity=_diversity(categories),
    )


def _structural_summaries(
    module_input: ModuleInput,
    eligible_tokens: tuple[TokenRecord, ...],
    observations: tuple[SensorimotorObservation, ...],
    *,
    analysis_view: str,
    active_stopwords: frozenset[str],
) -> tuple[SensorimotorStructuralSummary, ...]:
    if module_input.poem_document is None:
        return ()
    filtered = analysis_view == "Stopwords excluded"
    retained_phrase_ids = {
        token_id
        for observation in observations
        if observation.source_is_multiword and observation.included_in_stopword_view
        for token_id in observation.token_ids
    }
    view_tokens = tuple(
        token
        for token in eligible_tokens
        if not filtered
        or token.token_id in retained_phrase_ids
        or (
            token.normalized_form not in active_stopwords
            and token.normalized_lemma not in active_stopwords
        )
    )
    view_observations = tuple(
        observation
        for observation in observations
        if not filtered or observation.included_in_stopword_view
    )
    rows = []
    for kind, units in (
        (StructuralUnitKind.LINE, module_input.poem_document.lines),
        (StructuralUnitKind.STANZA, module_input.poem_document.stanzas),
    ):
        for unit in units:
            if kind is StructuralUnitKind.LINE:
                unit_tokens = tuple(
                    token for token in view_tokens if token.line_number == unit.ordinal
                )
                unit_observations = tuple(
                    observation
                    for observation in view_observations
                    if observation.line_number == unit.ordinal
                )
            else:
                unit_tokens = tuple(
                    token
                    for token in view_tokens
                    if token.stanza_number == unit.ordinal
                )
                unit_observations = tuple(
                    observation
                    for observation in view_observations
                    if observation.stanza_number == unit.ordinal
                )
            matched_ids = {
                token_id
                for observation in unit_observations
                for token_id in observation.token_ids
            }
            rows.append(
                SensorimotorStructuralSummary(
                    analysis_view=analysis_view,
                    scope=kind.value,
                    scope_id=unit.unit_id,
                    ordinal=unit.ordinal,
                    source_text=unit.content_text,
                    eligible_token_count=len(unit_tokens),
                    matched_token_count=len(matched_ids),
                    token_coverage=_rate(len(matched_ids), len(unit_tokens)),
                    matched_observation_count=len(unit_observations),
                    dimension_means=tuple(
                        (
                            dimension.dimension_id,
                            (
                                statistics.fmean(
                                    getattr(observation.means, dimension.dimension_id)
                                    for observation in unit_observations
                                )
                                if unit_observations
                                else None
                            ),
                        )
                        for dimension in SENSORIMOTOR_DIMENSIONS
                    ),
                )
            )
    return tuple(rows)


def _term_summaries(
    observations: tuple[SensorimotorObservation, ...],
) -> tuple[SensorimotorTermSummary, ...]:
    groups: dict[str, list[SensorimotorObservation]] = {}
    for observation in observations:
        groups.setdefault(observation.matched_lookup_form, []).append(observation)
    rows = []
    for lookup_form, group in groups.items():
        first = group[0]
        rows.append(
            SensorimotorTermSummary(
                source_term=first.matched_source_term,
                lookup_form=lookup_form,
                source_row=first.source_row,
                source_is_multiword=first.source_is_multiword,
                observation_count=len(group),
                surface_forms=tuple(
                    sorted({item.surface_form for item in group}, key=str.casefold)
                ),
                part_of_speech_tags=tuple(
                    sorted({item.part_of_speech for item in group})
                ),
                means=first.means,
                dominant_sensorimotor=first.dominant_sensorimotor,
                minkowski3_sensorimotor_strength=(
                    first.minkowski3_sensorimotor_strength
                ),
                sensorimotor_exclusivity=first.sensorimotor_exclusivity,
            )
        )
    return tuple(
        sorted(
            rows,
            key=lambda row: (-row.observation_count, row.lookup_form),
        )
    )


def _module_metrics(
    profiles: tuple[SensorimotorProfile, ...],
) -> tuple[ModuleMetric, ...]:
    metrics: list[ModuleMetric] = []
    for profile in profiles:
        denominator = (
            f"{profile.matched_observation_count} matched "
            f"{profile.weighting}-weighted observations"
        )
        for dimension in profile.dimensions:
            base = f"sensorimotor.{dimension.dimension_id}"
            for suffix, value, unit, note in (
                (
                    "mean",
                    dimension.statistics.mean,
                    "source 0-5",
                    "Mean normative sensorimotor strength.",
                ),
                (
                    "population_standard_deviation",
                    dimension.statistics.population_standard_deviation,
                    "source-scale points",
                    "Population dispersion across matched source means.",
                ),
                (
                    "cumulative_load",
                    dimension.cumulative_load,
                    "summed source ratings",
                    "Length- and repetition-sensitive sum.",
                ),
                (
                    "load_per_100_observations",
                    dimension.load_per_100_observations,
                    "summed ratings per 100 observations",
                    "Length-normalized cumulative load.",
                ),
            ):
                metrics.append(
                    ModuleMetric(
                        metric_id=f"{base}.{suffix}",
                        value=value,
                        layer=ResultLayer.COMPUTED_SUMMARY,
                        scope="document",
                        scope_id=profile.profile_id,
                        unit=unit,
                        weighting=profile.weighting,
                        denominator=denominator,
                        note=note,
                    )
                )
        for suffix, stats, unit in (
            (
                "minkowski3_perceptual_strength",
                profile.perceptual_strength,
                "source composite",
            ),
            (
                "minkowski3_action_strength",
                profile.action_strength,
                "source composite",
            ),
            (
                "minkowski3_sensorimotor_strength",
                profile.overall_sensorimotor_strength,
                "source composite",
            ),
            (
                "perceptual_exclusivity",
                profile.perceptual_exclusivity,
                "proportion",
            ),
            ("action_exclusivity", profile.action_exclusivity, "proportion"),
            (
                "sensorimotor_exclusivity",
                profile.sensorimotor_exclusivity,
                "proportion",
            ),
        ):
            metrics.append(
                ModuleMetric(
                    metric_id=f"sensorimotor.{suffix}.mean",
                    value=stats.mean,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope="document",
                    scope_id=profile.profile_id,
                    unit=unit,
                    weighting=profile.weighting,
                    denominator=denominator,
                )
            )
        metrics.append(
            ModuleMetric(
                metric_id="sensorimotor.dominant_category_diversity",
                value=profile.dominant_category_diversity,
                layer=ResultLayer.COMPUTED_SUMMARY,
                scope="document",
                scope_id=profile.profile_id,
                unit="normalized Shannon entropy 0-1",
                weighting=profile.weighting,
                denominator=denominator,
            )
        )
        for category in profile.dominant_categories:
            metrics.append(
                ModuleMetric(
                    metric_id=(
                        f"sensorimotor.dominant_{category.category}.proportion"
                    ),
                    value=category.proportion,
                    layer=ResultLayer.COMPUTED_SUMMARY,
                    scope="document",
                    scope_id=profile.profile_id,
                    unit="proportion",
                    weighting=profile.weighting,
                    denominator=denominator,
                )
            )
    return tuple(metrics)


@lru_cache(maxsize=4)
def _load_cached(
    path: str,
    source_sha256: str,
) -> LancasterSensorimotorLexicon:
    del source_sha256
    return LancasterSensorimotorAdapter().load(Path(path))


class SensorimotorModule:
    """Framework-independent Lancaster sensorimotor analysis module."""

    name = "sensorimotor_imagery_and_embodiment"
    version = "1.1.0"

    def __init__(
        self,
        resource_root: Path | str,
        *,
        resource_spec: ResourceSpec = LANCASTER_SENSORIMOTOR_SPEC,
    ) -> None:
        self.resource_root = Path(resource_root)
        self.resource_spec = resource_spec
        self.resource_manager = LocalResourceManager(self.resource_root)

    def validate_resources(self) -> tuple[ResourceStatus, ...]:
        status = self.resource_manager.validate(self.resource_spec)
        if status.available:
            try:
                _load_cached(str(status.configured_path), status.source_sha256)
            except LancasterSensorimotorAdapterError as error:
                status = replace(
                    status,
                    state=ResourceState.MALFORMED,
                    message=(
                        f"{self.resource_spec.display_name} is readable but does "
                        f"not satisfy the CSV contract: {error}"
                    ),
                )
        return (status,)

    def _available(
        self,
    ) -> tuple[ResourceStatus, LancasterSensorimotorLexicon]:
        status = self.validate_resources()[0]
        if not status.available:
            raise SensorimotorModuleError(status.message)
        try:
            return status, _load_cached(
                str(status.configured_path),
                status.source_sha256,
            )
        except LancasterSensorimotorAdapterError as error:
            raise SensorimotorModuleError(str(error)) from error

    def analyze(self, module_input: ModuleInput) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: SensorimotorConfiguration | None = None,
    ) -> SensorimotorAnalysisResult:
        config = configuration or SensorimotorConfiguration()
        status, lexicon = self._available()
        eligible_tokens, observations, unmatched, policy = _match(
            module_input,
            lexicon,
            config,
        )
        matched_ids = {
            token_id for observation in observations for token_id in observation.token_ids
        }
        filtered_observations = tuple(
            observation
            for observation in observations
            if observation.included_in_stopword_view
        )
        retained_match_ids = {
            token_id
            for observation in filtered_observations
            for token_id in observation.token_ids
        }
        filtered_eligible = tuple(
            token
            for token in eligible_tokens
            if token.token_id in retained_match_ids
            or (
                token.normalized_form not in policy.active_words
                and token.normalized_lemma not in policy.active_words
            )
        )
        filtered_matched_ids = {
            token_id
            for observation in filtered_observations
            for token_id in observation.token_ids
        }
        profiles = tuple(
            _profile(
                selected,
                analysis_view=view,
                weighting=weighting,
                eligible_token_count=len(eligible),
                matched_token_count=len(matched),
            )
            for view, selected, eligible, matched in (
                (
                    "All matched tokens",
                    observations,
                    eligible_tokens,
                    matched_ids,
                ),
                (
                    "Stopwords excluded",
                    filtered_observations,
                    filtered_eligible,
                    filtered_matched_ids,
                ),
            )
            for weighting in ("token", "type")
        )
        structural = tuple(
            item
            for view in ("All matched tokens", "Stopwords excluded")
            for item in _structural_summaries(
                module_input,
                eligible_tokens,
                observations,
                analysis_view=view,
                active_stopwords=frozenset(policy.active_words),
            )
        )
        warnings: list[ModuleWarning] = [
            ModuleWarning(
                code="context_free_norms",
                message=(
                    "Sensorimotor ratings describe source-normed lexical "
                    "associations, not contextual imagery, a reader's experience, "
                    "or an author's intention."
                ),
                severity=WarningSeverity.INFORMATION,
            )
        ]
        if len(observations) < config.minimum_match_requirement:
            warnings.append(
                ModuleWarning(
                    code="sparse_sensorimotor_evidence",
                    message=(
                        "Fewer than the configured minimum number of matched "
                        "sensorimotor observations were available."
                    ),
                )
            )
        coverage = _rate(len(matched_ids), len(eligible_tokens))
        if coverage is not None and coverage < 0.6:
            warnings.append(
                ModuleWarning(
                    code="low_sensorimotor_coverage",
                    message=(
                        "Fewer than 60% of eligible lexical token occurrences "
                        "matched the Lancaster source; interpret aggregates cautiously."
                    ),
                )
            )
        resource_provenance = ResourceProvenance.from_available_status(
            status,
            citation=self.resource_spec.citation,
            license_notice=self.resource_spec.license_notice,
            adapter_version=LancasterSensorimotorAdapter.adapter_version,
        )
        signature = "|".join(
            (
                self.name,
                self.version,
                LEXICON_ELIGIBILITY_POLICY_ID,
                module_input.document.text_version_id,
                config.configuration_id,
                status.source_sha256,
            )
        )
        module_result = ModuleResult(
            result_id=hashlib.sha256(signature.encode("utf-8")).hexdigest(),
            module_name=self.name,
            module_version=self.version,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=_module_metrics(profiles),
            coverage=(
                ModuleCoverage.from_counts(
                    coverage_id="sensorimotor.all_matched_token_coverage",
                    eligible_count=len(eligible_tokens),
                    matched_count=len(matched_ids),
                    unit="eligible lexical token occurrences",
                    unmatched_items=tuple(
                        sorted({item.normalized_form for item in unmatched})
                    ),
                    note="Published multiword concepts count once as observations while their component tokens remain in coverage.",
                ),
                ModuleCoverage.from_counts(
                    coverage_id="sensorimotor.stopwords_excluded_token_coverage",
                    eligible_count=len(filtered_eligible),
                    matched_count=len(filtered_matched_ids),
                    unit="stopword-excluded eligible lexical token occurrences",
                    note="Published source phrases remain intact in the secondary view.",
                ),
            ),
            warnings=tuple(warnings),
            provenance=ModuleProvenance(
                software_version=__version__,
                source_text_sha256=module_input.document.text_sha256,
                preprocessing_recipe=module_input.preprocessing.recipe_id,
                pipeline_name=module_input.preprocessing.pipeline_name,
                pipeline_version=module_input.preprocessing.pipeline_version,
                configuration_id=config.configuration_id,
                scenario_id=config.scenario_id,
                lookup_policy=(
                    "Longest exact published expression within one physical line; "
                    "then exact normalized surface, conservative possessive base, "
                    "POS-aware model lemma, unmatched."
                ),
                inclusion_policy=(
                    "Ordinary lexical tokens plus alphabetically spelled "
                    "number-like tokens; punctuation and pure numeric literals "
                    "excluded; model-tagged proper nouns "
                    + (
                        "excluded. "
                        if config.exclude_proper_nouns
                        else "included. "
                    )
                    + "Both all-matched and configured stopword-excluded views "
                    "are retained; published phrases stay intact."
                ),
                resources=(resource_provenance,),
            ),
        )
        return SensorimotorAnalysisResult(
            module_result=module_result,
            configuration=config,
            resource_status=status,
            profiles=profiles,
            structural_summaries=structural,
            term_summaries=_term_summaries(observations),
            observations=observations,
            unmatched_tokens=unmatched,
        )
