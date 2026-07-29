"""Auditable exact, lemma, phrase, and comparison lookup across loaded lexicons."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from versevad.adapters.cmudict import CMUDictEntry, CMUPronunciation
from versevad.adapters.concreteness import (
    BrysbaertConcretenessAdapter,
    ConcretenessEntry,
)
from versevad.adapters.kuperman_aoa import (
    KupermanAoAAdapter,
    KupermanAoAEntry,
)
from versevad.adapters.lancaster_sensorimotor import (
    LancasterSensorimotorAdapter,
    SensorimotorEntry,
)
from versevad.adapters.subtlex_us import SubtlexUsAdapter, SubtlexUsEntry
from versevad.application import (
    LEXICON_SPECS,
    RESOURCE_ROOT,
    load_lexicon,
)
from versevad.core.modules import ModuleInput
from versevad.lexical_semantic.aoa import AoAModule, KUPERMAN_AOA_SPEC
from versevad.lexical_semantic.concreteness import (
    BRYSBAERT_CONCRETENESS_SPEC,
    ConcretenessModule,
)
from versevad.lexical_semantic.frequency import (
    FrequencyModule,
    SUBTLEX_US_SPEC,
)
from versevad.lexical_semantic.sensorimotor import (
    LANCASTER_SENSORIMOTOR_SPEC,
    SENSORIMOTOR_DIMENSIONS,
    SensorimotorModule,
)
from versevad.lexical_semantic.readability import (
    ReadabilityAnalysisResult,
    ReadabilityModule,
)
from versevad.lexical_semantic.sentiment import (
    VaderSentimentAnalysisResult,
    VaderSentimentModule,
)
from versevad.models import (
    EmotionAssociationEntry,
    EmotionIntensityEntry,
    VadEntry,
    VadLexicon,
    VadScores,
)
from versevad.normalization import normalize_lookup
from versevad.preprocessing import TextPreprocessor, create_text_document
from versevad.prosody.pronunciation import (
    CMUDICT_DICTIONARY_SPEC,
    PronunciationModule,
)


@dataclass(frozen=True)
class LexiconExplorerEntry:
    lexicon_id: str
    lexicon: str
    value_kind: str
    matched_term: str
    match_method: str
    source_rows: tuple[int, ...]
    original_scale: str
    original_scores: VadScores | None
    normalized_scores: VadScores | None
    standard_deviation: VadScores | None
    rater_count: VadScores | None
    associations: tuple[str, ...]
    intensities: tuple[tuple[str, float], ...]
    source_file: str
    source_sha256: str
    version: str
    adapter_version: str
    citation: str
    normalization_formula: str


@dataclass(frozen=True)
class ComponentAverage:
    lexicon_id: str
    lexicon: str
    components: tuple[str, ...]
    original_scores: VadScores
    normalized_scores: VadScores
    original_scale: str


@dataclass(frozen=True)
class CrossLexiconSpread:
    dimension: str
    entry_count: int
    minimum: float
    maximum: float
    spread: float
    descriptive_agreement: str


@dataclass(frozen=True)
class SupplementaryEvidenceValue:
    field: str
    value: object
    unit: str = ""
    note: str = ""


@dataclass(frozen=True)
class SupplementaryExplorerResource:
    """One installed or expected non-affective lexical lookup resource."""

    resource_id: str
    resource: str
    construct: str
    state: str
    status_message: str
    lexicon: object | None
    source_file: str
    source_sha256: str
    version: str
    adapter_version: str
    citation: str
    source_hashes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SupplementaryExplorerEntry:
    resource_id: str
    resource: str
    construct: str
    status: str
    status_message: str
    matched_term: str
    match_method: str
    variant_label: str
    source_rows: tuple[int, ...]
    values: tuple[SupplementaryEvidenceValue, ...]
    source_file: str
    source_sha256: str
    source_hashes: tuple[tuple[str, str], ...]
    version: str
    adapter_version: str
    citation: str


@dataclass(frozen=True)
class LexiconExplorerResult:
    query: str
    normalized_query: str
    processing_lemma: str
    processing_pos: str
    entries: tuple[LexiconExplorerEntry, ...]
    supplementary_entries: tuple[SupplementaryExplorerEntry, ...]
    component_averages: tuple[ComponentAverage, ...]
    comparisons: tuple[CrossLexiconSpread, ...]
    suggestions: tuple[str, ...]
    notices: tuple[str, ...]
    vader_sentiment: VaderSentimentAnalysisResult | None = None
    readability: ReadabilityAnalysisResult | None = None


def _mean_scores(values: Iterable[VadScores]) -> VadScores:
    rows = tuple(values)
    return VadScores(
        valence=sum(row.valence for row in rows) / len(rows),
        arousal=sum(row.arousal for row in rows) / len(rows),
        dominance=sum(row.dominance for row in rows) / len(rows),
    )


def _entry_view(lexicon, entry, method: str) -> LexiconExplorerEntry:
    metadata = lexicon.metadata
    validation = lexicon.validation
    source_path = validation.source_path
    common = dict(
        lexicon_id=metadata.lexicon_id,
        lexicon=metadata.display_name,
        value_kind=metadata.value_kind.value,
        matched_term=entry.source_term,
        match_method=method,
        original_scale=f"{metadata.source_scale_min:g} to {metadata.source_scale_max:g}",
        source_file=str(source_path) if source_path is not None else "not recorded",
        source_sha256=validation.source_sha256,
        version=metadata.version,
        adapter_version=metadata.adapter_version,
        citation=metadata.citation,
        normalization_formula=metadata.normalization_formula,
    )
    if isinstance(entry, VadEntry):
        return LexiconExplorerEntry(
            **common,
            source_rows=(entry.source_row,),
            original_scores=entry.original,
            normalized_scores=entry.normalized,
            # Streamlit can retain entries created before these optional
            # uncertainty fields were added to VadEntry. Treat their absence
            # as unavailable source data rather than failing the lookup.
            standard_deviation=getattr(entry, "standard_deviation", None),
            rater_count=getattr(entry, "rater_count", None),
            associations=(),
            intensities=(),
        )
    if isinstance(entry, EmotionAssociationEntry):
        return LexiconExplorerEntry(
            **common,
            source_rows=entry.source_rows,
            original_scores=None,
            normalized_scores=None,
            standard_deviation=None,
            rater_count=None,
            associations=entry.associations,
            intensities=(),
        )
    if isinstance(entry, EmotionIntensityEntry):
        return LexiconExplorerEntry(
            **common,
            source_rows=entry.source_rows,
            original_scores=None,
            normalized_scores=None,
            standard_deviation=None,
            rater_count=None,
            associations=(),
            intensities=entry.intensities,
        )
    raise TypeError(f"Unsupported lexicon entry: {type(entry)!r}")


def _supplementary_entry(
    resource: SupplementaryExplorerResource,
    *,
    status: str,
    status_message: str,
    matched_term: str = "",
    match_method: str = "",
    variant_label: str = "",
    source_rows: tuple[int, ...] = (),
    values: tuple[SupplementaryEvidenceValue, ...] = (),
) -> SupplementaryExplorerEntry:
    return SupplementaryExplorerEntry(
        resource_id=resource.resource_id,
        resource=resource.resource,
        construct=resource.construct,
        status=status,
        status_message=status_message,
        matched_term=matched_term,
        match_method=match_method,
        variant_label=variant_label,
        source_rows=source_rows,
        values=values,
        source_file=resource.source_file,
        source_sha256=resource.source_sha256,
        source_hashes=resource.source_hashes,
        version=resource.version,
        adapter_version=resource.adapter_version,
        citation=resource.citation,
    )


def _concreteness_evidence(
    resource: SupplementaryExplorerResource,
    entry: ConcretenessEntry,
    method: str,
) -> SupplementaryExplorerEntry:
    return _supplementary_entry(
        resource,
        status="matched",
        status_message="A source rating was found.",
        matched_term=entry.source_term,
        match_method=method,
        source_rows=(entry.source_row,),
        values=(
            SupplementaryEvidenceValue("Mean rating", entry.mean, "source 1-5"),
            SupplementaryEvidenceValue(
                "Rating standard deviation",
                entry.standard_deviation,
                "source 1-5",
            ),
            SupplementaryEvidenceValue("Rater count", entry.rater_count),
            SupplementaryEvidenceValue("Unknown count", entry.unknown_count),
            SupplementaryEvidenceValue(
                "Percent known",
                entry.percent_known,
                "percent",
            ),
            SupplementaryEvidenceValue(
                "Source SUBTLEX count",
                entry.subtlex_count,
            ),
            SupplementaryEvidenceValue(
                "Multiword source entry",
                entry.is_multiword,
            ),
        ),
    )


def _frequency_evidence(
    resource: SupplementaryExplorerResource,
    entry: SubtlexUsEntry,
    method: str,
) -> SupplementaryExplorerEntry:
    return _supplementary_entry(
        resource,
        status="matched",
        status_message="A SUBTLEX-US word-form entry was found.",
        matched_term=entry.source_term,
        match_method=method,
        source_rows=(entry.source_row,),
        values=(
            SupplementaryEvidenceValue(
                "Zipf value",
                entry.zipf_value,
                "SUBTLEX-US Zipf",
            ),
            SupplementaryEvidenceValue(
                "Frequency count",
                entry.frequency_count,
            ),
            SupplementaryEvidenceValue(
                "Contextual-diversity count",
                entry.contextual_diversity_count,
            ),
            SupplementaryEvidenceValue(
                "Frequency per million",
                entry.frequency_per_million,
            ),
            SupplementaryEvidenceValue(
                "Log10 frequency",
                entry.log10_frequency,
            ),
            SupplementaryEvidenceValue(
                "Contextual diversity",
                entry.contextual_diversity_percent,
                "percent",
            ),
            SupplementaryEvidenceValue(
                "Log10 contextual diversity",
                entry.log10_contextual_diversity,
            ),
            SupplementaryEvidenceValue(
                "Lowercase frequency count",
                entry.lowercase_frequency_count,
            ),
            SupplementaryEvidenceValue(
                "Lowercase contextual-diversity count",
                entry.lowercase_contextual_diversity_count,
            ),
            SupplementaryEvidenceValue(
                "Dominant source POS",
                entry.dominant_source_pos,
            ),
            SupplementaryEvidenceValue(
                "Dominant source POS frequency",
                entry.dominant_source_pos_frequency,
            ),
            SupplementaryEvidenceValue(
                "Dominant source POS proportion",
                entry.dominant_source_pos_proportion,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "All source POS labels",
                entry.all_source_pos,
            ),
            SupplementaryEvidenceValue(
                "All source POS frequencies",
                entry.all_source_pos_frequencies,
            ),
        ),
    )


def _aoa_evidence(
    resource: SupplementaryExplorerResource,
    entry: KupermanAoAEntry,
    method: str,
) -> SupplementaryExplorerEntry:
    status = "matched" if entry.mean_age is not None else "source_unrated"
    message = (
        "A numeric retrospective source rating was found."
        if entry.mean_age is not None
        else (
            "The source contains this word but supplies no numeric AoA mean. "
            "The missing rating remains missing."
        )
    )
    return _supplementary_entry(
        resource,
        status=status,
        status_message=message,
        matched_term=entry.source_term,
        match_method=method,
        source_rows=(entry.source_row,),
        values=(
            SupplementaryEvidenceValue(
                "Mean AoA",
                entry.mean_age,
                "retrospective source years",
            ),
            SupplementaryEvidenceValue(
                "Rating standard deviation",
                entry.standard_deviation,
                "years",
            ),
            SupplementaryEvidenceValue(
                "Total responses",
                entry.occurrence_total,
            ),
            SupplementaryEvidenceValue(
                "Numeric responses",
                entry.numeric_response_count,
            ),
            SupplementaryEvidenceValue(
                "Unknown responses",
                entry.unknown_response_count,
            ),
            SupplementaryEvidenceValue(
                "Numeric-response proportion",
                entry.numeric_response_proportion,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Source Dunno value",
                entry.source_dunno_value,
            ),
            SupplementaryEvidenceValue(
                "Source frequency per million",
                entry.frequency_per_million,
            ),
        ),
    )


def _sensorimotor_evidence(
    resource: SupplementaryExplorerResource,
    entry: SensorimotorEntry,
    method: str,
) -> SupplementaryExplorerEntry:
    values: list[SupplementaryEvidenceValue] = []
    for dimension in SENSORIMOTOR_DIMENSIONS:
        values.extend(
            (
                SupplementaryEvidenceValue(
                    f"{dimension.label} mean",
                    getattr(entry.means, dimension.dimension_id),
                    "source 0-5",
                    dimension.definition,
                ),
                SupplementaryEvidenceValue(
                    f"{dimension.label} source standard deviation",
                    getattr(
                        entry.source_standard_deviations,
                        dimension.dimension_id,
                    ),
                    "source-scale points",
                    "Dispersion among source norming responses.",
                ),
            )
        )
    values.extend(
        (
            SupplementaryEvidenceValue(
                "Maximum perceptual strength",
                entry.max_perceptual_strength,
                "source 0-5",
            ),
            SupplementaryEvidenceValue(
                "Minkowski-3 perceptual strength",
                entry.minkowski3_perceptual_strength,
                "published composite",
            ),
            SupplementaryEvidenceValue(
                "Perceptual exclusivity",
                entry.perceptual_exclusivity,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Dominant perceptual modality",
                entry.dominant_perceptual,
            ),
            SupplementaryEvidenceValue(
                "Maximum action strength",
                entry.max_action_strength,
                "source 0-5",
            ),
            SupplementaryEvidenceValue(
                "Minkowski-3 action strength",
                entry.minkowski3_action_strength,
                "published composite",
            ),
            SupplementaryEvidenceValue(
                "Action exclusivity",
                entry.action_exclusivity,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Dominant action effector",
                entry.dominant_action,
            ),
            SupplementaryEvidenceValue(
                "Maximum overall sensorimotor strength",
                entry.max_sensorimotor_strength,
                "source 0-5",
            ),
            SupplementaryEvidenceValue(
                "Minkowski-3 overall sensorimotor strength",
                entry.minkowski3_sensorimotor_strength,
                "published composite",
            ),
            SupplementaryEvidenceValue(
                "Overall sensorimotor exclusivity",
                entry.sensorimotor_exclusivity,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Dominant overall sensorimotor dimension",
                entry.dominant_sensorimotor,
            ),
            SupplementaryEvidenceValue(
                "Percent known: perceptual ratings",
                entry.percent_known_perceptual,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Percent known: action ratings",
                entry.percent_known_action,
                "proportion",
            ),
            SupplementaryEvidenceValue(
                "Published multiword concept",
                entry.is_multiword,
            ),
        )
    )
    return _supplementary_entry(
        resource,
        status="matched",
        status_message=(
            "A Lancaster context-free normative sensorimotor entry was found."
        ),
        matched_term=entry.source_term,
        match_method=method,
        source_rows=(entry.source_row,),
        values=tuple(values),
    )


def _pronunciation_evidence(
    resource: SupplementaryExplorerResource,
    entry: CMUDictEntry,
    method: str,
) -> tuple[SupplementaryExplorerEntry, ...]:
    return tuple(
        _supplementary_entry(
            resource,
            status="matched",
            status_message=(
                "An exact CMUdict pronunciation candidate was found. "
                "Alternatives remain separate."
            ),
            matched_term=entry.source_term,
            match_method=method,
            variant_label=f"Variant {candidate.variant_number}",
            source_rows=(candidate.source_line,),
            values=(
                SupplementaryEvidenceValue(
                    "ARPAbet phones",
                    candidate.phones_text,
                ),
                SupplementaryEvidenceValue(
                    "Syllable count",
                    candidate.syllable_count,
                ),
                SupplementaryEvidenceValue(
                    "Lexical stress",
                    candidate.stress_pattern,
                    "CMUdict stress digits",
                    "0 unstressed; 1 primary; 2 secondary.",
                ),
                SupplementaryEvidenceValue(
                    "Source comment",
                    candidate.source_comment,
                ),
            ),
        )
        for candidate in entry.pronunciations
    )


def _lookup_supplementary_resources(
    *,
    normalized: str,
    lemma: str,
    mapped_query: str,
    resources: Iterable[SupplementaryExplorerResource],
) -> tuple[SupplementaryExplorerEntry, ...]:
    rows = []
    mapped = mapped_query.strip()
    for resource in resources:
        if resource.state != "available" or resource.lexicon is None:
            rows.append(
                _supplementary_entry(
                    resource,
                    status="resource_unavailable",
                    status_message=resource.status_message,
                )
            )
            continue
        entry = resource.lexicon.lookup(normalized)
        method = "exact entry"
        if (
            entry is None
            and resource.construct != "pronunciation"
            and lemma
            and lemma != normalized
        ):
            entry = resource.lexicon.lookup(lemma)
            if entry is not None:
                method = "lemma-derived entry"
        if entry is None and mapped:
            entry = resource.lexicon.lookup(normalize_lookup(mapped))
            if entry is not None:
                method = "user-supplied mapped lookup"
        if entry is None:
            rows.append(
                _supplementary_entry(
                    resource,
                    status="unmatched",
                    status_message=(
                        "The resource is available, but no accepted entry was "
                        "found. No neutral value was assigned."
                    ),
                )
            )
            continue
        if isinstance(entry, ConcretenessEntry):
            rows.append(_concreteness_evidence(resource, entry, method))
        elif isinstance(entry, SubtlexUsEntry):
            rows.append(_frequency_evidence(resource, entry, method))
        elif isinstance(entry, KupermanAoAEntry):
            rows.append(_aoa_evidence(resource, entry, method))
        elif isinstance(entry, SensorimotorEntry):
            rows.append(_sensorimotor_evidence(resource, entry, method))
        elif isinstance(entry, CMUDictEntry):
            rows.extend(_pronunciation_evidence(resource, entry, method))
        else:
            raise TypeError(
                "Unsupported supplementary Explorer entry: "
                f"{type(entry)!r}"
            )
    return tuple(rows)


@lru_cache(maxsize=4)
def load_supplementary_explorer_resources(
    resource_root: str = str(RESOURCE_ROOT),
) -> tuple[SupplementaryExplorerResource, ...]:
    """Validate and load every local non-affective lexical lookup source."""

    root = Path(resource_root)
    resources = []

    concreteness_module = ConcretenessModule(root)
    concreteness_status = concreteness_module.validate_resources()[0]
    concreteness_lexicon = (
        concreteness_module._available()[1]
        if concreteness_status.available
        else None
    )
    resources.append(
        SupplementaryExplorerResource(
            resource_id=BRYSBAERT_CONCRETENESS_SPEC.resource_id,
            resource=BRYSBAERT_CONCRETENESS_SPEC.display_name,
            construct="concreteness",
            state=concreteness_status.state.value,
            status_message=concreteness_status.message,
            lexicon=concreteness_lexicon,
            source_file=str(concreteness_status.configured_path),
            source_sha256=concreteness_status.source_sha256,
            version=BRYSBAERT_CONCRETENESS_SPEC.version,
            adapter_version=BrysbaertConcretenessAdapter.adapter_version,
            citation=BRYSBAERT_CONCRETENESS_SPEC.citation,
        )
    )

    frequency_module = FrequencyModule(root)
    frequency_status = frequency_module.validate_resources()[0]
    frequency_lexicon = (
        frequency_module._available()[1]
        if frequency_status.available
        else None
    )
    resources.append(
        SupplementaryExplorerResource(
            resource_id=SUBTLEX_US_SPEC.resource_id,
            resource=SUBTLEX_US_SPEC.display_name,
            construct="frequency",
            state=frequency_status.state.value,
            status_message=frequency_status.message,
            lexicon=frequency_lexicon,
            source_file=str(frequency_status.configured_path),
            source_sha256=frequency_status.source_sha256,
            version=SUBTLEX_US_SPEC.version,
            adapter_version=SubtlexUsAdapter.adapter_version,
            citation=SUBTLEX_US_SPEC.citation,
        )
    )

    aoa_module = AoAModule(root)
    aoa_status = aoa_module.validate_resources()[0]
    aoa_lexicon = aoa_module._available()[1] if aoa_status.available else None
    resources.append(
        SupplementaryExplorerResource(
            resource_id=KUPERMAN_AOA_SPEC.resource_id,
            resource=KUPERMAN_AOA_SPEC.display_name,
            construct="aoa",
            state=aoa_status.state.value,
            status_message=aoa_status.message,
            lexicon=aoa_lexicon,
            source_file=str(aoa_status.configured_path),
            source_sha256=aoa_status.source_sha256,
            version=KUPERMAN_AOA_SPEC.version,
            adapter_version=KupermanAoAAdapter.adapter_version,
            citation=KUPERMAN_AOA_SPEC.citation,
        )
    )

    sensorimotor_module = SensorimotorModule(root)
    sensorimotor_status = sensorimotor_module.validate_resources()[0]
    sensorimotor_lexicon = (
        sensorimotor_module._available()[1]
        if sensorimotor_status.available
        else None
    )
    resources.append(
        SupplementaryExplorerResource(
            resource_id=LANCASTER_SENSORIMOTOR_SPEC.resource_id,
            resource=LANCASTER_SENSORIMOTOR_SPEC.display_name,
            construct="sensorimotor imagery and embodiment",
            state=sensorimotor_status.state.value,
            status_message=sensorimotor_status.message,
            lexicon=sensorimotor_lexicon,
            source_file=str(sensorimotor_status.configured_path),
            source_sha256=sensorimotor_status.source_sha256,
            version=LANCASTER_SENSORIMOTOR_SPEC.version,
            adapter_version=LancasterSensorimotorAdapter.adapter_version,
            citation=LANCASTER_SENSORIMOTOR_SPEC.citation,
        )
    )

    pronunciation_module = PronunciationModule(root)
    pronunciation_statuses = pronunciation_module.validate_resources()
    pronunciation_available = all(
        status.available for status in pronunciation_statuses
    )
    pronunciation_lexicon = (
        pronunciation_module._load()[0]
        if pronunciation_available
        else None
    )
    dictionary_status = pronunciation_statuses[0]
    resources.append(
        SupplementaryExplorerResource(
            resource_id=CMUDICT_DICTIONARY_SPEC.resource_id,
            resource=CMUDICT_DICTIONARY_SPEC.display_name,
            construct="pronunciation",
            state=(
                "available"
                if pronunciation_available
                else next(
                    status.state.value
                    for status in pronunciation_statuses
                    if not status.available
                )
            ),
            status_message=" ".join(
                status.message for status in pronunciation_statuses
            ),
            lexicon=pronunciation_lexicon,
            source_file="; ".join(
                str(status.configured_path)
                for status in pronunciation_statuses
            ),
            source_sha256=dictionary_status.source_sha256,
            version=CMUDICT_DICTIONARY_SPEC.version,
            adapter_version="1.0.0",
            citation=CMUDICT_DICTIONARY_SPEC.citation,
            source_hashes=tuple(
                (status.resource_id, status.source_sha256)
                for status in pronunciation_statuses
            ),
        )
    )
    return tuple(resources)


def explore_loaded_lexicons(
    query: str,
    lexicons: Iterable[object],
    preprocessor: TextPreprocessor,
    *,
    mapped_query: str = "",
    supplementary_resources: Iterable[
        SupplementaryExplorerResource
    ] = (),
) -> LexiconExplorerResult:
    """Search loaded source entries without silently substituting a lemma."""

    raw_query = query.strip()
    if not raw_query:
        raise ValueError("Enter a word or phrase to look up.")
    if len(raw_query) > 200 or "\n" in raw_query or "\r" in raw_query:
        raise ValueError("Look up one word or phrase of at most 200 characters.")
    normalized = normalize_lookup(raw_query)
    document = create_text_document("lexicon-explorer", "Lexicon Explorer", raw_query)
    poem_document = preprocessor.process_document(document)
    module_input = ModuleInput.from_poem_document(poem_document)
    tokens = tuple(token for token in poem_document.tokens if token.is_lexical)
    lemma = ""
    pos = ""
    if len(tokens) == 1:
        lemma = tokens[0].normalized_lemma
        pos = tokens[0].part_of_speech

    loaded = tuple(lexicons)
    views: list[LexiconExplorerEntry] = []
    notices: list[str] = []
    matched_lexicons: set[str] = set()
    for lexicon in loaded:
        entry, conflict = lexicon.resolve(normalized, raw_query)
        if conflict:
            notices.append(
                f"{lexicon.metadata.display_name} has a capitalization collision for "
                "this lookup; no source entry was guessed."
            )
        method = "exact phrase" if len(tokens) > 1 else "exact entry"
        if entry is None and lemma and lemma != normalized:
            entry, lemma_conflict = lexicon.resolve(lemma, tokens[0].lemma)
            if lemma_conflict:
                notices.append(
                    f"{lexicon.metadata.display_name} has an unresolved collision for the proposed lemma."
                )
            if entry is not None:
                method = "lemma-derived entry"
        if entry is not None:
            views.append(_entry_view(lexicon, entry, method))
            matched_lexicons.add(lexicon.metadata.lexicon_id)

    mapped = mapped_query.strip()
    if mapped and normalize_lookup(mapped) != normalized:
        mapped_normalized = normalize_lookup(mapped)
        for lexicon in loaded:
            if lexicon.metadata.lexicon_id in matched_lexicons:
                continue
            entry, conflict = lexicon.resolve(mapped_normalized, mapped)
            if conflict:
                notices.append(
                    f"{lexicon.metadata.display_name} has a capitalization collision for the user-supplied mapping."
                )
            if entry is not None:
                views.append(_entry_view(lexicon, entry, "user-supplied mapped lookup"))
                matched_lexicons.add(lexicon.metadata.lexicon_id)
        notices.append(
            f"User-supplied mapping shown for lookup only: {raw_query} → {mapped}. "
            "It does not alter corpus or poem analyses."
        )

    component_averages: list[ComponentAverage] = []
    if len(tokens) > 1:
        for lexicon in loaded:
            if not isinstance(lexicon, VadLexicon):
                continue
            if lexicon.metadata.lexicon_id in matched_lexicons:
                continue
            component_entries = []
            for token in tokens:
                entry, conflict = lexicon.resolve(token.normalized_form, token.surface_form)
                if conflict or entry is None:
                    component_entries = []
                    break
                component_entries.append(entry)
            if component_entries:
                component_averages.append(
                    ComponentAverage(
                        lexicon_id=lexicon.metadata.lexicon_id,
                        lexicon=lexicon.metadata.display_name,
                        components=tuple(entry.source_term for entry in component_entries),
                        original_scores=_mean_scores(entry.original for entry in component_entries),
                        normalized_scores=_mean_scores(
                            entry.normalized for entry in component_entries
                        ),
                        original_scale=(
                            f"{lexicon.metadata.source_scale_min:g} to "
                            f"{lexicon.metadata.source_scale_max:g}"
                        ),
                    )
                )

    comparisons = []
    vad_views = [row for row in views if row.normalized_scores is not None]
    if len(vad_views) >= 2:
        methods = {row.match_method for row in vad_views}
        if len(methods) > 1:
            notices.append(
                "The normalized spread includes more than one lookup method. "
                "Inspect the exact, lemma-derived, or mapped labels before treating the entries as equivalent."
            )
        for dimension in ("valence", "arousal", "dominance"):
            values = [
                float(getattr(row.normalized_scores, dimension))
                for row in vad_views
                if row.normalized_scores is not None
            ]
            spread = max(values) - min(values)
            agreement = "high" if spread <= 0.10 else "moderate" if spread <= 0.25 else "low"
            comparisons.append(
                CrossLexiconSpread(
                    dimension=dimension,
                    entry_count=len(values),
                    minimum=min(values),
                    maximum=max(values),
                    spread=spread,
                    descriptive_agreement=agreement,
                )
            )

    suggestions: tuple[str, ...] = ()
    if not views:
        source_terms: dict[str, str] = {}
        for lexicon in loaded:
            for key, entry in lexicon.entries.items():
                source_terms.setdefault(key, entry.source_term)
        close = get_close_matches(normalized, source_terms.keys(), n=8, cutoff=0.72)
        suggestions = tuple(source_terms[key] for key in close)
    supplementary_entries = _lookup_supplementary_resources(
        normalized=normalized,
        lemma=lemma,
        mapped_query=mapped_query,
        resources=supplementary_resources,
    )
    return LexiconExplorerResult(
        query=raw_query,
        normalized_query=normalized,
        processing_lemma=lemma,
        processing_pos=pos,
        entries=tuple(views),
        supplementary_entries=supplementary_entries,
        component_averages=tuple(component_averages),
        comparisons=tuple(comparisons),
        suggestions=suggestions,
        notices=tuple(notices),
        vader_sentiment=VaderSentimentModule().analyze_detailed(module_input),
        readability=ReadabilityModule().analyze_detailed(module_input),
    )


def explore_lexicons(
    query: str,
    preprocessor: TextPreprocessor,
    *,
    mapped_query: str = "",
) -> LexiconExplorerResult:
    """Load and search every installed source, using the known source hashes."""

    return explore_loaded_lexicons(
        query,
        (load_lexicon(spec.lexicon_id) for spec in LEXICON_SPECS),
        preprocessor,
        mapped_query=mapped_query,
        supplementary_resources=load_supplementary_explorer_resources(
            str(RESOURCE_ROOT.resolve())
        ),
    )
