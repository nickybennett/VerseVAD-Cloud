"""Framework-independent services for the beginner one-text workspace."""

from __future__ import annotations

import csv
import hashlib
import io
import statistics
import zipfile
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Iterable, Sequence

from versevad import __version__
from versevad.adapters import (
    NrcEmotionAdapter,
    NrcEmotionIntensityAdapter,
    NrcVadV1Adapter,
    NrcVadV21Adapter,
    WarrinerVadAdapter,
)
from versevad.analysis.phase2 import (
    analyze_lexicon,
    compare_lexicons,
    stopword_eligible_token_ids,
)
from versevad.analysis.statistics import weighted_vad_statistics
from versevad.core.documents import PoemDocument
from versevad.core.modules import ModuleInput
from versevad.core.resources import (
    LocalResourceManager,
    ResourceSpec,
    ResourceStatus,
)
from versevad.exports.aoa import export_aoa_bundle
from versevad.exports.concreteness import export_concreteness_bundle
from versevad.exports.docx_report import (
    build_narrative_report_from_summary_csv,
)
from versevad.exports.frequency import export_frequency_bundle
from versevad.exports.inherited_form import export_inherited_form_bundle
from versevad.exports.lexical_style import export_lexical_style_bundle
from versevad.exports.meter import export_meter_bundle
from versevad.exports.phase2_csv import export_phase2_csv
from versevad.exports.phonology import export_phonological_bundle
from versevad.exports.poem_document_csv import export_poem_document_csv_bundle
from versevad.exports.pronunciation import export_pronunciation_bundle
from versevad.exports.poetry_id import export_poetry_id_bundle
from versevad.exports.readability import export_readability_bundle
from versevad.exports.sentiment import export_vader_sentiment_bundle
from versevad.lexical_semantic.concreteness import (
    ConcretenessAnalysisResult,
    ConcretenessConfiguration,
    ConcretenessModule,
    ConcretenessModuleError,
)
from versevad.lexical_semantic.aoa import (
    AoAAnalysisResult,
    AoAConfiguration,
    AoAModule,
    AoAModuleError,
    attach_aoa_relationships,
)
from versevad.lexical_semantic.frequency import (
    FrequencyAnalysisResult,
    FrequencyConfiguration,
    FrequencyModule,
    FrequencyModuleError,
)
from versevad.lexical_semantic.readability import (
    ReadabilityAnalysisResult,
    ReadabilityConfiguration,
    ReadabilityModule,
)
from versevad.lexical_semantic.sentiment import (
    VaderSentimentAnalysisResult,
    VaderSentimentModule,
)
from versevad.lexical_style import (
    LexicalStyleAnalysisResult,
    LexicalStyleConfiguration,
    LexicalStyleModule,
    LexicalStyleModuleError,
)
from versevad.inherited_form import (
    InheritedFormAnalysisResult,
    InheritedFormConfiguration,
    InheritedFormEngine,
)
from versevad.models import (
    AffectMatchRecord,
    CrossLexiconComparison,
    MatchMethod,
    MatchSelection,
    Phase2AnalysisResult,
    PhrasePolicy,
    ReviewRule,
    StopwordMode,
    TextDocument,
    TokenRecord,
)
from versevad.preprocessing import (
    PreparedPoemPreprocessor,
    SpacyEnglishPreprocessor,
    TextPreprocessor,
    create_text_document,
)
from versevad.phonology import (
    PhonologicalAnalysisResult,
    PhonologicalConfiguration,
    PhonologicalModule,
    PhonologicalModuleError,
)
from versevad.performance import (
    AnalysisPerformanceReport,
    EXPORT_CACHE,
    MODULE_RESULT_CACHE,
    PREPROCESSING_CACHE,
    OperationTiming,
    cache_statistics,
    resource_cache_statistics,
    stable_fingerprint,
)
from versevad.prosody.pronunciation import (
    PronunciationAnalysisResult,
    PronunciationConfiguration,
    PronunciationModule,
    PronunciationModuleError,
)
from versevad.prosody.meter import (
    MeterAnalysisResult,
    MeterConfiguration,
    MeterModule,
    MeterModuleError,
)
from versevad.poetry_id import (
    PoetryIDAnalysisResult,
    PoetryIDConfiguration,
    PoetryIDEngine,
    lexical_evidence_from_results,
    vad_evidence_from_results,
)
from versevad.stopwords import DEFAULT_PROTECTED_WORDS, build_stopword_policy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source_lexicons"
RESOURCE_ROOT = PROJECT_ROOT / "resources"
MAX_TEXT_BYTES = 5 * 1024 * 1024


class TextImportError(ValueError):
    """A plain-language error for an input that was not changed or analyzed."""


class WorkspaceAnalysisError(RuntimeError):
    """A plain-language failure raised before a result is presented as complete."""


@dataclass(frozen=True)
class LexiconSpec:
    lexicon_id: str
    display_name: str
    relative_path: Path
    expected_sha256: str
    short_description: str


LEXICON_SPECS = (
    LexiconSpec(
        "warriner_vad_2013",
        "Warriner VAD",
        Path("XANEW-master/XANEW-master/Ratings_Warriner_et_al.csv"),
        "78ac8107c78e116bb96538fae4faa47281a155f5f8fe39f30bbc6ea3db05b446",
        "Normative valence, arousal, and dominance on the original 1-9 scale, including exact multiword entries.",
    ),
    LexiconSpec(
        "nrc_vad_v1",
        "NRC VAD v1",
        Path("NRC-VAD-Lexicon/NRC-VAD-Lexicon/NRC-VAD-Lexicon.txt"),
        "fd49023f760155c8377424d96ca18d57c6685891d78ba381e47af6f4a1b148a7",
        "Earlier NRC VAD ratings on the original 0-1 scale.",
    ),
    LexiconSpec(
        "nrc_vad_v2_1",
        "NRC VAD v2.1",
        Path("NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1.txt"),
        "42c718817fc91d5c133581b24b0bb31d2b14a0b16edb19bc6ce6ab70343e5a45",
        "Larger NRC VAD source with unigrams and multiword expressions on -1 to 1.",
    ),
    LexiconSpec(
        "nrc_emotion_v0_92",
        "NRC Emotion",
        Path(
            "NRC-Emotion-Lexicon/NRC-Emotion-Lexicon/"
            "NRC-Emotion-Lexicon-Wordlevel-v0.92.txt"
        ),
        "02c661544f4f12ae0c14f9576a10959e8d39a151bb091e455a71a08dcaa2535a",
        "Binary word associations for eight emotions and positive/negative sentiment.",
    ),
    LexiconSpec(
        "nrc_emotion_intensity_v1",
        "NRC Emotion Intensity",
        Path(
            "NRC-Emotion-Intensity-Lexicon/NRC-Emotion-Intensity-Lexicon/"
            "NRC-Emotion-Intensity-Lexicon-v1.txt"
        ),
        "2bed5450b43134e4f849b013424eb76a76e2bdc0ec35df7ec0a0a477031239cb",
        "Category-specific 0-1 intensity ratings for supplied word-emotion pairs.",
    ),
)
LEXICON_SPEC_BY_ID = {spec.lexicon_id: spec for spec in LEXICON_SPECS}
ADAPTER_BY_ID = {
    "warriner_vad_2013": WarrinerVadAdapter,
    "nrc_vad_v1": NrcVadV1Adapter,
    "nrc_vad_v2_1": NrcVadV21Adapter,
    "nrc_emotion_v0_92": NrcEmotionAdapter,
    "nrc_emotion_intensity_v1": NrcEmotionIntensityAdapter,
}

RESOURCE_DOWNLOAD_PAGES = {
    "warriner_vad_2013": (
        "https://link.springer.com/article/10.3758/s13428-012-0314-x"
    ),
    "nrc_vad_v1": "https://saifmohammad.com/WebPages/nrc-vad.html",
    "nrc_vad_v2_1": "https://saifmohammad.com/WebPages/nrc-vad.html",
    "nrc_emotion_v0_92": (
        "https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm"
    ),
    "nrc_emotion_intensity_v1": (
        "https://www.saifmohammad.com/WebPages/AffectIntensity.htm"
    ),
    "brysbaert-concreteness-2014": (
        "https://link.springer.com/article/10.3758/s13428-013-0403-5"
    ),
    "subtlex-us-zipf-official": (
        "https://www.ugent.be/pp/experimentele-psychologie/en/research/"
        "documents/subtlexus"
    ),
    "kuperman-aoa-2012-erratum-supplement": (
        "https://link.springer.com/article/10.3758/s13428-013-0348-8"
    ),
    "cmudict-dictionary": "https://github.com/cmusphinx/cmudict",
    "cmudict-phone-inventory": "https://github.com/cmusphinx/cmudict",
    "cmudict-symbol-inventory": "https://github.com/cmusphinx/cmudict",
}


@dataclass(frozen=True)
class ResourceReadiness:
    """Checksum-aware readiness for every runtime research resource."""

    affective_lexicons: tuple[ResourceStatus, ...]
    concreteness: ResourceStatus
    frequency: ResourceStatus
    aoa: ResourceStatus
    pronunciation: tuple[ResourceStatus, ...]

    @property
    def all_statuses(self) -> tuple[ResourceStatus, ...]:
        return (
            *self.affective_lexicons,
            self.concreteness,
            self.frequency,
            self.aoa,
            *self.pronunciation,
        )

    @property
    def unavailable(self) -> tuple[ResourceStatus, ...]:
        return tuple(status for status in self.all_statuses if not status.available)

    @property
    def available_lexicon_ids(self) -> tuple[str, ...]:
        return tuple(
            status.resource_id
            for status in self.affective_lexicons
            if status.available
        )

    @property
    def pronunciation_available(self) -> bool:
        return all(status.available for status in self.pronunciation)

    @property
    def available_module_ids(self) -> tuple[str, ...]:
        installed = ["lexical_style", "poetry_id"]
        if self.concreteness.available:
            installed.append("concreteness")
        if self.frequency.available:
            installed.append("frequency")
        if self.aoa.available:
            installed.append("aoa")
        if self.pronunciation_available:
            installed.extend(
                ("pronunciation", "meter", "phonology", "inherited_form")
            )
        return tuple(installed)


def validate_affective_resources(
    source_root: Path = SOURCE_ROOT,
) -> tuple[ResourceStatus, ...]:
    """Validate every configured affective source without loading its rows."""

    resource_specs = tuple(
        ResourceSpec(
            resource_id=spec.lexicon_id,
            display_name=spec.display_name,
            relative_path=spec.relative_path,
            version=spec.lexicon_id,
            accepted_sha256=(spec.expected_sha256,),
            minimum_bytes=100_000,
        )
        for spec in LEXICON_SPECS
    )
    return LocalResourceManager(source_root).validate_many(resource_specs)


def installed_resource_readiness(
    *,
    source_root: Path = SOURCE_ROOT,
    resource_root: Path = RESOURCE_ROOT,
) -> ResourceReadiness:
    """Return a fast, checksum-aware installation report for every workspace.

    Startup readiness establishes exact file identity without parsing complete
    workbooks or dictionaries. Each selected module still performs its adapter
    contract validation before analysis, and the resulting source SHA-256 is
    retained on every completed result.
    """

    supplementary_manager = LocalResourceManager(resource_root)
    concreteness_module = ConcretenessModule(resource_root)
    frequency_module = FrequencyModule(resource_root)
    aoa_module = AoAModule(resource_root)
    pronunciation_module = PronunciationModule(resource_root)

    return ResourceReadiness(
        affective_lexicons=validate_affective_resources(source_root),
        concreteness=supplementary_manager.validate(
            concreteness_module.resource_spec
        ),
        frequency=supplementary_manager.validate(frequency_module.resource_spec),
        aoa=supplementary_manager.validate(aoa_module.resource_spec),
        pronunciation=supplementary_manager.validate_many(
            pronunciation_module.resource_specs
        ),
    )


@dataclass(frozen=True)
class AnalysisRequest:
    project_name: str
    title: str
    original_text: str
    lexicon_ids: tuple[str, ...]
    phrase_policy: PhrasePolicy = PhrasePolicy.PHRASE_PREFERRED
    minimum_match_requirement: int = 3
    text_id: str | None = None
    text_version_id: str | None = None
    stopword_mode: StopwordMode = StopwordMode.STANDARD
    protected_stopwords: tuple[str, ...] = DEFAULT_PROTECTED_WORDS
    custom_stopword_additions: tuple[str, ...] = ()
    custom_stopword_removals: tuple[str, ...] = ()
    scenario_id: str = "phase2-multi-lexicon-v1"
    scenario_version_id: str = ""
    review_rules: tuple[ReviewRule, ...] = ()
    include_concreteness: bool = False
    concreteness_configuration: ConcretenessConfiguration = (
        ConcretenessConfiguration()
    )
    include_frequency: bool = False
    frequency_configuration: FrequencyConfiguration = FrequencyConfiguration()
    include_aoa: bool = False
    aoa_configuration: AoAConfiguration = AoAConfiguration()
    include_pronunciation: bool = False
    pronunciation_configuration: PronunciationConfiguration = (
        PronunciationConfiguration()
    )
    include_meter: bool = False
    meter_configuration: MeterConfiguration = MeterConfiguration()
    include_phonology: bool = False
    phonological_configuration: PhonologicalConfiguration = (
        PhonologicalConfiguration()
    )
    include_lexical_style: bool = False
    lexical_style_configuration: LexicalStyleConfiguration = (
        LexicalStyleConfiguration()
    )
    include_poetry_id: bool = False
    poetry_id_configuration: PoetryIDConfiguration = (
        PoetryIDConfiguration()
    )
    include_inherited_form: bool = False
    inherited_form_configuration: InheritedFormConfiguration = (
        InheritedFormConfiguration()
    )
    analysis_cache_enabled: bool = True
    performance_diagnostics: bool = True


@dataclass(frozen=True)
class WorkspaceAnalysis:
    request: AnalysisRequest
    document: TextDocument
    results: tuple[Phase2AnalysisResult, ...]
    comparison: CrossLexiconComparison
    poem_document: PoemDocument | None = None
    vader_sentiment: VaderSentimentAnalysisResult | None = None
    readability: ReadabilityAnalysisResult | None = None
    concreteness: ConcretenessAnalysisResult | None = None
    frequency: FrequencyAnalysisResult | None = None
    aoa: AoAAnalysisResult | None = None
    pronunciation: PronunciationAnalysisResult | None = None
    meter: MeterAnalysisResult | None = None
    phonology: PhonologicalAnalysisResult | None = None
    lexical_style: LexicalStyleAnalysisResult | None = None
    poetry_id: PoetryIDAnalysisResult | None = None
    inherited_form: InheritedFormAnalysisResult | None = None
    performance: AnalysisPerformanceReport | None = None


@dataclass(frozen=True)
class CoverageView:
    lexicon_id: str
    lexicon: str
    value_kind: str
    matched_tokens: int
    lexical_tokens: int
    coverage: float | None
    matched_types: int
    total_types: int
    exact_matches: int
    lemma_matches: int
    phrase_matches: int
    note: str


PART_OF_SPEECH_LABELS = {
    "ADJ": "Adjective",
    "ADP": "Preposition",
    "ADV": "Adverb",
    "CCONJ": "Coordinating Conjunction",
    "DET": "Determiner",
    "INTJ": "Interjection",
    "MIXED": "Mixed-POS Phrase",
    "NOUN": "Common Noun",
    "NOUN + PROPN": "Noun",
    "NUM": "Numeral",
    "PART": "Particle",
    "PRON": "Pronoun",
    "PROPN": "Proper Noun",
    "SCONJ": "Subordinating Conjunction",
    "SYM": "Symbol",
    "VERB": "Main Verb",
    "AUX": "Auxiliary or Copular Verb",
    "VERB + AUX": "Verb",
    "X": "Other or Uncertain",
}


@dataclass(frozen=True)
class PartOfSpeechView:
    tag: str
    category: str
    token_count: int
    share_of_lexical_tokens: float
    unique_type_count: int
    example_forms: str
    lexical_token_denominator: int


@dataclass(frozen=True)
class VadView:
    lexicon_id: str
    lexicon: str
    analysis_view: str
    matched_observations: int
    matched_types: int
    eligible_tokens: int
    lexical_coverage: float | None
    normalized_valence: float | None
    normalized_arousal: float | None
    normalized_dominance: float | None
    type_valence: float | None
    type_arousal: float | None
    type_dominance: float | None
    original_scale: str
    normalization_formula: str


@dataclass(frozen=True)
class LexicalTrajectoryPoint:
    lexicon_id: str
    lexicon: str
    analysis_view: str
    line_number: int
    stanza_number: int
    source_text: str
    valence_mean: float | None
    arousal_mean: float | None
    dominance_mean: float | None
    concreteness_mean_normalized: float | None
    concreteness_mean_source_scale: float | None
    vad_matched_observations: int
    concreteness_matched_tokens: int


@dataclass(frozen=True)
class VadPartOfSpeechView:
    lexicon_id: str
    lexicon: str
    analysis_view: str
    tag: str
    category: str
    matched_observations: int
    matched_types: int
    matched_token_occurrences: int
    eligible_token_occurrences: int | None
    lexical_coverage: float | None
    token_weighted_valence: float | None
    token_weighted_arousal: float | None
    token_weighted_dominance: float | None
    type_weighted_valence: float | None
    type_weighted_arousal: float | None
    type_weighted_dominance: float | None
    original_token_weighted_valence: float | None
    original_token_weighted_arousal: float | None
    original_token_weighted_dominance: float | None
    original_type_weighted_valence: float | None
    original_type_weighted_arousal: float | None
    original_type_weighted_dominance: float | None
    phrase_observations: int
    is_sparse: bool
    original_scale: str
    normalization_formula: str


VAD_DEFINITIONS = {
    "valence": (
        "Normative pleasantness: lower ratings are associated with more unpleasant "
        "vocabulary and higher ratings with more pleasant vocabulary."
    ),
    "arousal": (
        "Normative activation or energy—not specifically sexual arousal. Lower "
        "ratings are calmer or more subdued; higher ratings are more activated, "
        "alert, excited, or agitated."
    ),
    "dominance": (
        "Normative power, control, or agency. Lower ratings are associated with "
        "constraint or vulnerability; higher ratings with greater control or power."
    ),
}


def _broad_part_of_speech_tag(source_tag: str | None) -> str:
    tag = source_tag or "X"
    if tag in {"NOUN", "PROPN"}:
        return "NOUN + PROPN"
    if tag in {"VERB", "AUX"}:
        return "VERB + AUX"
    return tag


def part_of_speech_views_for_tokens(
    tokens: Sequence[TokenRecord],
) -> tuple[PartOfSpeechView, ...]:
    """Summarize broad, reader-facing POS families over lexical tokens."""

    return _part_of_speech_views_for_tokens(tokens, merge_broad_categories=True)


def detailed_part_of_speech_views_for_tokens(
    tokens: Sequence[TokenRecord],
) -> tuple[PartOfSpeechView, ...]:
    """Preserve the model's universal POS tags as a separate audit view."""

    return _part_of_speech_views_for_tokens(tokens, merge_broad_categories=False)


def _part_of_speech_views_for_tokens(
    tokens: Sequence[TokenRecord],
    *,
    merge_broad_categories: bool,
) -> tuple[PartOfSpeechView, ...]:
    lexical_tokens = tuple(token for token in tokens if token.is_lexical)
    denominator = len(lexical_tokens)
    if not denominator:
        return ()
    by_tag: dict[str, list[TokenRecord]] = {}
    for token in lexical_tokens:
        source_tag = token.part_of_speech or "X"
        tag = (
            _broad_part_of_speech_tag(source_tag)
            if merge_broad_categories
            else source_tag
        )
        by_tag.setdefault(tag, []).append(token)
    rows = []
    for tag, tagged_tokens in by_tag.items():
        forms = Counter(
            token.normalized_form or token.surface_form.casefold()
            for token in tagged_tokens
        )
        examples = ", ".join(
            form
            for form, _frequency in sorted(
                forms.items(),
                key=lambda item: (-item[1], item[0]),
            )[:6]
        )
        rows.append(
            PartOfSpeechView(
                tag=tag,
                category=PART_OF_SPEECH_LABELS.get(tag, tag.title()),
                token_count=len(tagged_tokens),
                share_of_lexical_tokens=len(tagged_tokens) / denominator,
                unique_type_count=len(forms),
                example_forms=examples,
                lexical_token_denominator=denominator,
            )
        )
    return tuple(
        sorted(
            rows,
            key=lambda row: (-row.token_count, row.category, row.tag),
        )
    )


def part_of_speech_views(
    workspace: WorkspaceAnalysis,
) -> tuple[PartOfSpeechView, ...]:
    """Return a lexicon-independent POS profile for one analyzed text."""

    if workspace.poem_document is not None:
        return part_of_speech_views_for_tokens(workspace.poem_document.tokens)
    if workspace.results:
        return part_of_speech_views_for_tokens(workspace.results[0].tokens)
    return ()


def detailed_part_of_speech_views(
    workspace: WorkspaceAnalysis,
) -> tuple[PartOfSpeechView, ...]:
    """Return the unmerged universal-tag profile for one analyzed text."""

    if workspace.poem_document is not None:
        return detailed_part_of_speech_views_for_tokens(
            workspace.poem_document.tokens
        )
    if workspace.results:
        return detailed_part_of_speech_views_for_tokens(
            workspace.results[0].tokens
        )
    return ()


@dataclass(frozen=True)
class VadInterpretationView:
    lexicon_id: str
    lexicon: str
    analysis_view: str
    dimension: str
    mean: float
    matched_observations: int
    lexical_coverage: float | None
    relation_to_midpoint: str
    explanation: str


@dataclass(frozen=True)
class VadContributorView:
    lexicon_id: str
    lexicon: str
    analysis_view: str
    dimension: str
    term: str
    surface_forms: str
    observations: int
    normalized_rating: float
    original_rating: float
    midpoint_deviation_per_occurrence: float
    signed_contribution: float
    absolute_contribution: float
    effect_on_mean: float | None
    direction: str
    stopword_status: str
    example_surface: str
    example_line: int
    example_context: str
    match_method: str


@dataclass(frozen=True)
class VadCumulativeView:
    """Length-sensitive token totals on the derived 0-1 VAD scale."""

    lexicon_id: str
    lexicon: str
    analysis_view: str
    dimension: str
    matched_observations: int
    lexical_tokens: int
    lexical_coverage: float | None
    rating_total: float
    above_midpoint_deviation: float
    below_midpoint_deviation: float
    net_midpoint_deviation: float
    absolute_midpoint_deviation: float


@dataclass(frozen=True)
class VadSensitivityView:
    lexicon_id: str
    lexicon: str
    weighting: str
    dimension: str
    all_matched_mean: float | None
    stopwords_excluded_mean: float | None
    difference: float | None


@dataclass(frozen=True)
class EmotionAssociationView:
    category: str
    token_count: int
    unique_types: int
    rate_per_lexical_token: float | None
    rate_among_emotion_bearing_tokens: float | None
    top_terms: str


@dataclass(frozen=True)
class EmotionIntensityView:
    category: str
    token_count: int
    distinct_pairs: int
    prevalence_per_lexical_token: float | None
    mean_matched_intensity: float | None
    median_matched_intensity: float | None
    maximum_matched_intensity: float | None
    top_terms: str


@dataclass(frozen=True)
class MatchView:
    lexicon_id: str
    lexicon: str
    surface: str
    normalized: str
    line: int
    stanza: int
    pos: str
    lemma: str
    matched_term: str
    method: str
    status: str
    value: str
    context: str
    explanation: str
    stopword_status: str
    included_in_full: bool
    included_in_filtered: bool
    stopword_exclusion_reason: str


@dataclass(frozen=True)
class UnmatchedView:
    lexicon_id: str
    lexicon: str
    surface: str
    normalized_form: str
    frequency: int
    pos: str
    proposed_lemma: str
    example_line: int
    example_context: str


def decode_uploaded_text(filename: str, content: bytes) -> str:
    """Decode a private UTF-8 plain-text file without rewriting its content."""

    if not filename.lower().endswith(".txt"):
        raise TextImportError(
            "Phase 3 accepts UTF-8 plain-text (.txt) files. Save this poem as a "
            ".txt file or paste it into the text box."
        )
    if len(content) > MAX_TEXT_BYTES:
        raise TextImportError(
            "This file is larger than the 5 MB Phase 3 safety limit. No text was imported."
        )
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise TextImportError(
            "VerseVAD could not read this file as UTF-8. Save a UTF-8 copy or "
            "paste the text directly; the original file was not changed."
        ) from error
    if "\x00" in text:
        raise TextImportError(
            "This does not appear to be an ordinary plain-text file. No text was imported."
        )
    return text


def _adapter(lexicon_id: str):
    try:
        return ADAPTER_BY_ID[lexicon_id]()
    except KeyError as error:
        raise WorkspaceAnalysisError(f"Unknown lexicon selection: {lexicon_id}") from error


@lru_cache(maxsize=10)
def load_lexicon(lexicon_id: str, source_root: str = str(SOURCE_ROOT)):
    spec = LEXICON_SPEC_BY_ID.get(lexicon_id)
    if spec is None:
        raise WorkspaceAnalysisError(f"Unknown lexicon selection: {lexicon_id}")
    lexicon = _adapter(lexicon_id).load(Path(source_root) / spec.relative_path)
    if lexicon.validation.source_sha256 != spec.expected_sha256:
        raise WorkspaceAnalysisError(
            f"{spec.display_name} does not match the source inspected during setup. "
            "No analysis was run. Restore the original source file, then retry."
        )
    return lexicon


@lru_cache(maxsize=2)
def _default_preprocessor(model_name: str = "en_core_web_sm") -> TextPreprocessor:
    """Share one read-only spaCy pipeline per process."""

    return SpacyEnglishPreprocessor(model_name)


def _module_result_id(value: object | None) -> str:
    if value is None:
        return ""
    module_result = getattr(value, "module_result", None)
    if module_result is not None:
        return str(getattr(module_result, "result_id", ""))
    return str(getattr(value, "analysis_id", ""))


def run_workspace_analysis(
    request: AnalysisRequest,
    *,
    preprocessor: TextPreprocessor | None = None,
    source_root: Path = SOURCE_ROOT,
    resource_root: Path = RESOURCE_ROOT,
    concreteness_module: ConcretenessModule | None = None,
    frequency_module: FrequencyModule | None = None,
    aoa_module: AoAModule | None = None,
    pronunciation_module: PronunciationModule | None = None,
    meter_module: MeterModule | None = None,
    phonological_module: PhonologicalModule | None = None,
    lexical_style_module: LexicalStyleModule | None = None,
    poetry_id_engine: PoetryIDEngine | None = None,
    inherited_form_engine: InheritedFormEngine | None = None,
    vader_sentiment_module: VaderSentimentModule | None = None,
    readability_module: ReadabilityModule | None = None,
) -> WorkspaceAnalysis:
    if not request.title.strip():
        raise WorkspaceAnalysisError("Enter a title or working label for this text.")
    if not request.original_text.strip():
        raise WorkspaceAnalysisError("Paste a poem or choose a UTF-8 text file before analyzing.")
    unknown = set(request.lexicon_ids) - set(LEXICON_SPEC_BY_ID)
    if unknown:
        raise WorkspaceAnalysisError(f"Unknown lexicon selection: {sorted(unknown)}")
    if request.minimum_match_requirement < 1:
        raise WorkspaceAnalysisError("The minimum matched-item setting must be at least 1.")

    analysis_started = perf_counter()
    timing_rows: list[OperationTiming] = []

    def cached_operation(
        module_name: str,
        dependencies: object,
        compute,
        *,
        validator=None,
        enabled: bool = True,
        cache=MODULE_RESULT_CACHE,
    ):
        key = stable_fingerprint(
            __version__,
            module_name,
            dependencies,
        )
        operation_started = perf_counter()
        value, lookup = cache.get_or_compute(
            key,
            compute,
            enabled=request.analysis_cache_enabled and enabled,
            validator=validator,
        )
        elapsed_ms = (perf_counter() - operation_started) * 1000
        if request.performance_diagnostics:
            timing_rows.append(
                OperationTiming(
                    module=module_name,
                    status="complete",
                    queue_ms=0.0,
                    resource_load_ms=0.0,
                    processing_ms=(
                        elapsed_ms if lookup.status != "hit" else 0.0
                    ),
                    serialization_ms=0.0,
                    total_ms=elapsed_ms,
                    cache_status=lookup.status,
                    cache_reason=lookup.reason,
                )
            )
        return value

    identity = hashlib.sha256(
        f"{request.project_name}|{request.title}".encode("utf-8")
    ).hexdigest()[:16]
    document = create_text_document(
        text_id=request.text_id or f"workspace-{identity}",
        title=request.title.strip(),
        original_text=request.original_text,
    )
    if request.text_version_id is not None:
        document = replace(document, text_version_id=request.text_version_id)
    processor = preprocessor or _default_preprocessor()
    try:
        stopword_policy = build_stopword_policy(
            mode=request.stopword_mode,
            protected_words=request.protected_stopwords,
            custom_additions=request.custom_stopword_additions,
            custom_removals=request.custom_stopword_removals,
        )
    except ValueError as error:
        raise WorkspaceAnalysisError(str(error)) from error
    poem_document = cached_operation(
        "shared_preprocessing",
        {
            "text_id": document.text_id,
            "text_version_id": document.text_version_id,
            "text_sha256": document.text_sha256,
            "title": document.title,
            "preprocessing": processor.metadata,
        },
        lambda: processor.process_document(document),
        validator=lambda value: (
            isinstance(value, PoemDocument)
            and value.source == document
        ),
        enabled=isinstance(processor, SpacyEnglishPreprocessor),
        cache=PREPROCESSING_CACHE,
    )
    prepared_processor = PreparedPoemPreprocessor(poem_document)
    module_input = ModuleInput.from_poem_document(poem_document)
    sentiment_engine = vader_sentiment_module or VaderSentimentModule()
    vader_sentiment = cached_operation(
        "vader_sentiment",
        {
            "text_sha256": document.text_sha256,
            "text_version_id": document.text_version_id,
            "module_version": sentiment_engine.version,
        },
        lambda: sentiment_engine.analyze_detailed(module_input),
        validator=lambda value: (
            isinstance(value, VaderSentimentAnalysisResult)
            and value.module_result.text_version_id == document.text_version_id
        ),
        enabled=vader_sentiment_module is None,
    )
    readability_engine = readability_module or ReadabilityModule()
    readability_configuration = ReadabilityConfiguration(
        pronunciation_overrides=request.pronunciation_configuration.overrides,
    )
    readability = cached_operation(
        "readability",
        {
            "text_sha256": document.text_sha256,
            "text_version_id": document.text_version_id,
            "preprocessing": poem_document.preprocessing,
            "configuration": readability_configuration,
            "module_version": readability_engine.version,
        },
        lambda: readability_engine.analyze_detailed(
            module_input,
            readability_configuration,
        ),
        validator=lambda value: (
            isinstance(value, ReadabilityAnalysisResult)
            and value.module_result.text_version_id == document.text_version_id
        ),
        enabled=readability_module is None,
    )
    result_rows = []
    for lexicon_id in request.lexicon_ids:
        spec = LEXICON_SPEC_BY_ID[lexicon_id]
        result_rows.append(
            cached_operation(
                f"affective_lexicon:{lexicon_id}",
                {
                    "text_version_id": document.text_version_id,
                    "text_sha256": document.text_sha256,
                    "preprocessing": poem_document.preprocessing,
                    "lexicon_id": lexicon_id,
                    "source_sha256": spec.expected_sha256,
                    "source_root": source_root.resolve(),
                    "phrase_policy": request.phrase_policy,
                    "minimum_match_requirement": (
                        request.minimum_match_requirement
                    ),
                    "stopword_policy": stopword_policy,
                    "scenario_id": request.scenario_id,
                    "scenario_version_id": request.scenario_version_id,
                    "review_rules": request.review_rules,
                },
                lambda lexicon_id=lexicon_id: analyze_lexicon(
                    document,
                    load_lexicon(
                        lexicon_id,
                        str(source_root.resolve()),
                    ),
                    prepared_processor,
                    phrase_policy=request.phrase_policy,
                    minimum_match_requirement=(
                        request.minimum_match_requirement
                    ),
                    stopword_policy=stopword_policy,
                    scenario_id=request.scenario_id,
                    scenario_version_id=request.scenario_version_id,
                    review_rules=request.review_rules,
                ),
                validator=lambda value: (
                    isinstance(value, Phase2AnalysisResult)
                    and value.document.text_version_id
                    == document.text_version_id
                ),
            )
        )
    results = tuple(result_rows)
    if results:
        comparison = cached_operation(
            "cross_lexicon_comparison",
            {
                "analysis_ids": tuple(result.analysis_id for result in results),
                "scenario_id": request.scenario_id,
                "phrase_policy": request.phrase_policy,
            },
            lambda: compare_lexicons(results),
            validator=lambda value: (
                isinstance(value, CrossLexiconComparison)
                and value.text_version_id == document.text_version_id
            ),
        )
    else:
        comparison_signature = "|".join(
            (
                document.text_version_id,
                request.scenario_id,
                request.phrase_policy.value,
                "no-affective-lexicons",
            )
        )
        comparison = CrossLexiconComparison(
            comparison_id=hashlib.sha256(
                comparison_signature.encode("utf-8")
            ).hexdigest(),
            text_version_id=document.text_version_id,
            scenario_id=request.scenario_id,
            phrase_policy=request.phrase_policy,
            lexicon_ids=(),
            metrics=(),
        )
    concreteness = None
    if request.include_concreteness:
        module = concreteness_module or ConcretenessModule(resource_root)
        try:
            concreteness = cached_operation(
                "concreteness",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "preprocessing": poem_document.preprocessing,
                    "configuration": request.concreteness_configuration,
                    "module_version": module.version,
                    "resource_root": resource_root.resolve(),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    request.concreteness_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, ConcretenessAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=concreteness_module is None,
            )
        except ConcretenessModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    frequency = None
    if request.include_frequency:
        module = frequency_module or FrequencyModule(resource_root)
        try:
            frequency = cached_operation(
                "frequency",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "preprocessing": poem_document.preprocessing,
                    "configuration": request.frequency_configuration,
                    "module_version": module.version,
                    "resource_root": resource_root.resolve(),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    request.frequency_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, FrequencyAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=frequency_module is None,
            )
        except FrequencyModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    aoa = None
    if request.include_aoa:
        module = aoa_module or AoAModule(resource_root)
        try:
            raw_aoa = cached_operation(
                "age_of_acquisition",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "preprocessing": poem_document.preprocessing,
                    "configuration": request.aoa_configuration,
                    "module_version": module.version,
                    "resource_root": resource_root.resolve(),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    request.aoa_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, AoAAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=aoa_module is None,
            )
            aoa = cached_operation(
                "age_of_acquisition_relationships",
                {
                    "aoa_result_id": _module_result_id(raw_aoa),
                    "frequency_result_id": _module_result_id(frequency),
                    "concreteness_result_id": _module_result_id(concreteness),
                },
                lambda: attach_aoa_relationships(
                    raw_aoa,
                    frequency=frequency,
                    concreteness=concreteness,
                ),
                validator=lambda value: isinstance(
                    value,
                    AoAAnalysisResult,
                ),
            )
        except AoAModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    pronunciation = None
    if (
        request.include_pronunciation
        or request.include_meter
        or request.include_phonology
        or request.include_inherited_form
    ):
        module = pronunciation_module or PronunciationModule(resource_root)
        try:
            pronunciation = cached_operation(
                "pronunciation",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "preprocessing": poem_document.preprocessing,
                    "configuration": request.pronunciation_configuration,
                    "module_version": module.version,
                    "resource_root": resource_root.resolve(),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    request.pronunciation_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, PronunciationAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=pronunciation_module is None,
            )
        except PronunciationModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    meter = None
    if request.include_meter or request.include_inherited_form:
        if pronunciation is None:  # pragma: no cover - guarded by dependency
            raise WorkspaceAnalysisError(
                "Meter analysis requires the pronunciation foundation."
            )
        module = meter_module or MeterModule()
        try:
            meter = cached_operation(
                "meter",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "configuration": request.meter_configuration,
                    "module_version": module.version,
                    "pronunciation_result_id": _module_result_id(
                        pronunciation
                    ),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    pronunciation,
                    request.meter_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, MeterAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=meter_module is None,
            )
        except MeterModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    phonology = None
    if request.include_phonology or request.include_inherited_form:
        if pronunciation is None:  # pragma: no cover - guarded by dependency
            raise WorkspaceAnalysisError(
                "Rhyme and phonological analysis requires the pronunciation "
                "foundation."
            )
        module = phonological_module or PhonologicalModule()
        try:
            phonology = cached_operation(
                "rhyme_and_phonological_patterning",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "configuration": request.phonological_configuration,
                    "module_version": module.version,
                    "pronunciation_result_id": _module_result_id(
                        pronunciation
                    ),
                },
                lambda: module.analyze_detailed(
                    module_input,
                    pronunciation,
                    request.phonological_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, PhonologicalAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=phonological_module is None,
            )
        except PhonologicalModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    lexical_style = None
    if request.include_lexical_style:
        module = lexical_style_module or LexicalStyleModule()
        try:
            lexical_style = cached_operation(
                "lexical_style",
                {
                    "text_sha256": document.text_sha256,
                    "text_version_id": document.text_version_id,
                    "preprocessing": poem_document.preprocessing,
                    "configuration": request.lexical_style_configuration,
                    "module_version": module.version,
                },
                lambda: module.analyze_detailed(
                    module_input,
                    request.lexical_style_configuration,
                ),
                validator=lambda value: (
                    isinstance(value, LexicalStyleAnalysisResult)
                    and value.module_result.text_version_id
                    == document.text_version_id
                ),
                enabled=lexical_style_module is None,
            )
        except LexicalStyleModuleError as error:
            raise WorkspaceAnalysisError(str(error)) from error
    poetry_id = None
    if request.include_poetry_id:
        engine = poetry_id_engine or PoetryIDEngine()
        poetry_id = cached_operation(
            "poetry_id",
            {
                "text_sha256": document.text_sha256,
                "text_version_id": document.text_version_id,
                "configuration": request.poetry_id_configuration,
                "engine_version": engine.version,
                "affective_analysis_ids": tuple(
                    result.analysis_id for result in results
                ),
                "concreteness_result_id": _module_result_id(concreteness),
                "frequency_result_id": _module_result_id(frequency),
                "aoa_result_id": _module_result_id(aoa),
            },
            lambda: engine.analyze(
                module_input,
                vad_evidence_from_results(
                    results,
                    request.poetry_id_configuration,
                ),
                request.poetry_id_configuration,
                lexical_evidence=lexical_evidence_from_results(
                    concreteness=concreteness,
                    frequency=frequency,
                    aoa=aoa,
                ),
            ),
            validator=lambda value: (
                isinstance(value, PoetryIDAnalysisResult)
                and value.module_result.text_version_id
                == document.text_version_id
            ),
            enabled=poetry_id_engine is None,
        )
    inherited_form = None
    if request.include_inherited_form:
        if pronunciation is None or meter is None or phonology is None:
            raise WorkspaceAnalysisError(
                "Inherited-form analysis requires pronunciation, meter, and "
                "rhyme evidence."
            )
        engine = inherited_form_engine or InheritedFormEngine()
        inherited_form = cached_operation(
            "inherited_form",
            {
                "text_sha256": document.text_sha256,
                "text_version_id": document.text_version_id,
                "configuration": request.inherited_form_configuration,
                "engine_version": engine.version,
                "pronunciation_result_id": _module_result_id(pronunciation),
                "meter_result_id": _module_result_id(meter),
                "phonology_result_id": _module_result_id(phonology),
            },
            lambda: engine.analyze(
                module_input,
                pronunciation,
                meter,
                phonology,
                request.inherited_form_configuration,
            ),
            validator=lambda value: (
                isinstance(value, InheritedFormAnalysisResult)
                and value.module_result.text_version_id
                == document.text_version_id
            ),
            enabled=inherited_form_engine is None,
        )
    performance_report = (
        AnalysisPerformanceReport(
            enabled=True,
            total_ms=(perf_counter() - analysis_started) * 1000,
            operations=tuple(timing_rows),
            caches=cache_statistics() + resource_cache_statistics(),
        )
        if request.performance_diagnostics
        else None
    )
    return WorkspaceAnalysis(
        request=request,
        document=document,
        results=results,
        comparison=comparison,
        poem_document=poem_document,
        vader_sentiment=vader_sentiment,
        readability=readability,
        concreteness=concreteness,
        frequency=frequency,
        aoa=aoa,
        pronunciation=pronunciation,
        meter=meter,
        phonology=phonology,
        lexical_style=lexical_style,
        poetry_id=poetry_id,
        inherited_form=inherited_form,
        performance=performance_report,
    )


def coverage_views(workspace: WorkspaceAnalysis) -> tuple[CoverageView, ...]:
    rows = []
    for result in workspace.results:
        coverage = result.coverage.lexical_token_coverage
        if coverage is None:
            note = "No lexical tokens were available."
        elif coverage >= 0.8:
            note = "At least 80% of lexical tokens matched under this policy."
        elif coverage >= 0.6:
            note = "Between 60% and 80% of lexical tokens matched; inspect unmatched terms."
        else:
            note = "Fewer than 60% matched; interpret aggregates cautiously."
        rows.append(
            CoverageView(
                lexicon_id=result.lexicon_metadata.lexicon_id,
                lexicon=result.lexicon_metadata.display_name,
                value_kind=result.lexicon_metadata.value_kind.value,
                matched_tokens=result.coverage.matched_token_count,
                lexical_tokens=result.coverage.total_lexical_tokens,
                coverage=coverage,
                matched_types=result.coverage.matched_type_count,
                total_types=result.coverage.total_unique_types,
                exact_matches=result.coverage.exact_match_count,
                lemma_matches=result.coverage.lemma_fallback_count,
                phrase_matches=result.coverage.phrase_match_count,
                note=note,
            )
        )
    return tuple(rows)


def vad_views(workspace: WorkspaceAnalysis) -> tuple[VadView, ...]:
    rows = []
    for result in workspace.results:
        summary = result.vad_summary
        if summary is None:
            continue
        metadata = result.lexicon_metadata
        filtered_token = summary.stopword_excluded_token_weighted_normalized
        filtered_type = summary.stopword_excluded_type_weighted_normalized
        view_groups = [
            (
                "All matched tokens",
                summary.token_weighted_normalized,
                summary.type_weighted_normalized,
                result.coverage.matched_type_count,
                result.coverage.total_lexical_tokens,
                result.coverage.lexical_token_coverage,
            )
        ]
        if (
            filtered_token is not None
            and filtered_type is not None
            and result.stopword_coverage is not None
        ):
            view_groups.append(
                (
                    "Stopwords excluded",
                    filtered_token,
                    filtered_type,
                    result.stopword_coverage.matched_type_count,
                    result.stopword_coverage.eligible_token_count,
                    result.stopword_coverage.lexical_token_coverage,
                )
            )
        for (
            analysis_view,
            token,
            kind,
            matched_types,
            eligible_tokens,
            coverage,
        ) in view_groups:
            rows.append(
                VadView(
                    lexicon_id=metadata.lexicon_id,
                    lexicon=metadata.display_name,
                    analysis_view=analysis_view,
                    matched_observations=token.valence.count,
                    matched_types=matched_types,
                    eligible_tokens=eligible_tokens,
                    lexical_coverage=coverage,
                    normalized_valence=token.valence.mean,
                    normalized_arousal=token.arousal.mean,
                    normalized_dominance=token.dominance.mean,
                    type_valence=kind.valence.mean,
                    type_arousal=kind.arousal.mean,
                    type_dominance=kind.dominance.mean,
                    original_scale=(
                        f"{metadata.source_scale_min:g} to "
                        f"{metadata.source_scale_max:g}"
                    ),
                    normalization_formula=metadata.normalization_formula,
                )
            )
    return tuple(rows)


def lexical_trajectory_views(
    workspace: WorkspaceAnalysis,
    *,
    lexicon_id: str,
    analysis_view: str = "All matched tokens",
) -> tuple[LexicalTrajectoryPoint, ...]:
    """Return source-specific token-weighted VAD and concreteness means by line.

    Concreteness is rescaled from its source 1-5 range to 0-1 only for the
    overlaid chart. Its source-scale mean remains alongside the normalized
    display value. Missing line evidence remains missing.
    """

    result = next(
        (
            candidate
            for candidate in workspace.results
            if candidate.lexicon_metadata.lexicon_id == lexicon_id
            and candidate.vad_summary is not None
        ),
        None,
    )
    if result is None or workspace.poem_document is None:
        return ()
    if analysis_view not in {"All matched tokens", "Stopwords excluded"}:
        raise ValueError(f"Unknown lexical-trajectory analysis view: {analysis_view}")
    stopwords_excluded = analysis_view == "Stopwords excluded"
    vad_by_line: dict[int, list] = {}
    for match in result.matches:
        included = (
            match.included_in_stopword_view
            if stopwords_excluded
            else match.included
        )
        if not included or match.normalized_scores is None:
            continue
        vad_by_line.setdefault(match.line_number, []).append(match.normalized_scores)

    eligible_token_ids: set[str] | None = None
    if stopwords_excluded and result.stopword_policy is not None:
        eligible_token_ids = stopword_eligible_token_ids(
            result.tokens,
            result.matches,
            result.stopword_policy,
        )
    concreteness_by_line: dict[int, list[float]] = {}
    if workspace.concreteness is not None:
        for row in workspace.concreteness.token_audit:
            if not row.included or row.rating is None:
                continue
            if eligible_token_ids is not None and row.token_id not in eligible_token_ids:
                continue
            concreteness_by_line.setdefault(row.line_number, []).append(row.rating)

    rows = []
    for line in workspace.poem_document.lines:
        scores = vad_by_line.get(line.ordinal, ())
        concreteness_values = concreteness_by_line.get(line.ordinal, ())
        concreteness_mean = (
            statistics.fmean(concreteness_values)
            if concreteness_values
            else None
        )
        rows.append(
            LexicalTrajectoryPoint(
                lexicon_id=lexicon_id,
                lexicon=result.lexicon_metadata.display_name,
                analysis_view=analysis_view,
                line_number=line.ordinal,
                stanza_number=next(
                    (
                        token.stanza_number
                        for token in result.tokens
                        if token.line_number == line.ordinal
                        and token.stanza_number
                    ),
                    0,
                ),
                source_text=line.content_text,
                valence_mean=(
                    statistics.fmean(score.valence for score in scores)
                    if scores
                    else None
                ),
                arousal_mean=(
                    statistics.fmean(score.arousal for score in scores)
                    if scores
                    else None
                ),
                dominance_mean=(
                    statistics.fmean(score.dominance for score in scores)
                    if scores
                    else None
                ),
                concreteness_mean_normalized=(
                    (concreteness_mean - 1) / 4
                    if concreteness_mean is not None
                    else None
                ),
                concreteness_mean_source_scale=concreteness_mean,
                vad_matched_observations=len(scores),
                concreteness_matched_tokens=len(concreteness_values),
            )
        )
    return tuple(rows)


def lexical_trajectory_csv(workspace: WorkspaceAnalysis) -> bytes:
    """Export every source/view trajectory without blending lexicons."""

    fields = [
        "lexicon_id",
        "lexicon",
        "analysis_view",
        "line_number",
        "stanza_number",
        "source_text",
        "mean_valence_0_1",
        "mean_arousal_0_1",
        "mean_dominance_0_1",
        "mean_concreteness_normalized_0_1",
        "mean_concreteness_source_scale_1_5",
        "vad_matched_observations",
        "concreteness_matched_tokens",
    ]
    rows = []
    for result in workspace.results:
        if result.vad_summary is None:
            continue
        views = ["All matched tokens"]
        if result.stopword_coverage is not None:
            views.append("Stopwords excluded")
        for view in views:
            for row in lexical_trajectory_views(
                workspace,
                lexicon_id=result.lexicon_metadata.lexicon_id,
                analysis_view=view,
            ):
                rows.append(
                    {
                        "lexicon_id": row.lexicon_id,
                        "lexicon": row.lexicon,
                        "analysis_view": row.analysis_view,
                        "line_number": row.line_number,
                        "stanza_number": row.stanza_number,
                        "source_text": row.source_text,
                        "mean_valence_0_1": (
                            row.valence_mean
                            if row.valence_mean is not None
                            else ""
                        ),
                        "mean_arousal_0_1": (
                            row.arousal_mean
                            if row.arousal_mean is not None
                            else ""
                        ),
                        "mean_dominance_0_1": (
                            row.dominance_mean
                            if row.dominance_mean is not None
                            else ""
                        ),
                        "mean_concreteness_normalized_0_1": (
                            row.concreteness_mean_normalized
                            if row.concreteness_mean_normalized is not None
                            else ""
                        ),
                        "mean_concreteness_source_scale_1_5": (
                            row.concreteness_mean_source_scale
                            if row.concreteness_mean_source_scale is not None
                            else ""
                        ),
                        "vad_matched_observations": row.vad_matched_observations,
                        "concreteness_matched_tokens": (
                            row.concreteness_matched_tokens
                        ),
                    }
                )
    return _csv_bytes(fields, rows)


def _match_part_of_speech_tag(
    match: AffectMatchRecord,
    token_by_id: dict[str, TokenRecord],
) -> str:
    tags = {
        _broad_part_of_speech_tag(token_by_id[token_id].part_of_speech)
        for token_id in match.token_ids
        if token_id in token_by_id and token_by_id[token_id].is_lexical
    }
    if len(tags) == 1:
        return next(iter(tags))
    return "MIXED"


def vad_part_of_speech_views(
    workspace: WorkspaceAnalysis,
) -> tuple[VadPartOfSpeechView, ...]:
    """Group source-specific normative VAD evidence by broad model POS.

    Token weighting counts every included match occurrence. Type weighting
    counts each distinct matched lexicon lookup form once within its source,
    analysis view, and POS group. Published phrases that span broad POS groups
    remain in an explicit mixed-POS row.
    """

    rows: list[VadPartOfSpeechView] = []
    for result in workspace.results:
        summary = result.vad_summary
        if summary is None:
            continue
        metadata = result.lexicon_metadata
        lexical_by_id = {
            token.token_id: token
            for token in result.tokens
            if token.is_lexical
        }
        all_eligible_ids = set(lexical_by_id)
        view_groups = [
            (
                "All matched tokens",
                all_eligible_ids,
                tuple(
                    match
                    for match in result.matches
                    if match.included and match.normalized_scores is not None
                ),
            )
        ]
        if result.stopword_coverage is not None and result.stopword_policy is not None:
            view_groups.append(
                (
                    "Stopwords excluded",
                    stopword_eligible_token_ids(
                        result.tokens,
                        result.matches,
                        result.stopword_policy,
                    ),
                    tuple(
                        match
                        for match in result.matches
                        if match.included_in_stopword_view
                        and match.normalized_scores is not None
                    ),
                )
            )

        for analysis_view, eligible_ids, included_matches in view_groups:
            eligible_by_tag: dict[str, set[str]] = {}
            for token_id in eligible_ids:
                token = lexical_by_id[token_id]
                tag = _broad_part_of_speech_tag(token.part_of_speech)
                eligible_by_tag.setdefault(tag, set()).add(token_id)

            matches_by_tag: dict[str, list[AffectMatchRecord]] = {}
            for match in included_matches:
                tag = _match_part_of_speech_tag(match, lexical_by_id)
                matches_by_tag.setdefault(tag, []).append(match)

            for tag in set(eligible_by_tag) | set(matches_by_tag):
                matches = tuple(matches_by_tag.get(tag, ()))
                unique_matches = {}
                for match in matches:
                    if match.matched_lookup_form is not None:
                        unique_matches.setdefault(match.matched_lookup_form, match)
                token_normalized = weighted_vad_statistics(
                    match.normalized_scores
                    for match in matches
                    if match.normalized_scores is not None
                )
                type_normalized = weighted_vad_statistics(
                    match.normalized_scores
                    for match in unique_matches.values()
                    if match.normalized_scores is not None
                )
                token_original = weighted_vad_statistics(
                    match.original_scores
                    for match in matches
                    if match.original_scores is not None
                )
                type_original = weighted_vad_statistics(
                    match.original_scores
                    for match in unique_matches.values()
                    if match.original_scores is not None
                )
                matched_token_ids = {
                    token_id
                    for match in matches
                    for token_id in match.token_ids
                    if token_id in lexical_by_id
                }
                eligible_for_tag = eligible_by_tag.get(tag)
                eligible_count = (
                    len(eligible_for_tag)
                    if eligible_for_tag is not None
                    else None
                )
                coverage = (
                    len(matched_token_ids & eligible_for_tag) / eligible_count
                    if eligible_for_tag is not None and eligible_count
                    else None
                )
                rows.append(
                    VadPartOfSpeechView(
                        lexicon_id=metadata.lexicon_id,
                        lexicon=metadata.display_name,
                        analysis_view=analysis_view,
                        tag=tag,
                        category=PART_OF_SPEECH_LABELS.get(tag, tag.title()),
                        matched_observations=len(matches),
                        matched_types=len(unique_matches),
                        matched_token_occurrences=len(matched_token_ids),
                        eligible_token_occurrences=eligible_count,
                        lexical_coverage=coverage,
                        token_weighted_valence=token_normalized.valence.mean,
                        token_weighted_arousal=token_normalized.arousal.mean,
                        token_weighted_dominance=token_normalized.dominance.mean,
                        type_weighted_valence=type_normalized.valence.mean,
                        type_weighted_arousal=type_normalized.arousal.mean,
                        type_weighted_dominance=type_normalized.dominance.mean,
                        original_token_weighted_valence=token_original.valence.mean,
                        original_token_weighted_arousal=token_original.arousal.mean,
                        original_token_weighted_dominance=token_original.dominance.mean,
                        original_type_weighted_valence=type_original.valence.mean,
                        original_type_weighted_arousal=type_original.arousal.mean,
                        original_type_weighted_dominance=type_original.dominance.mean,
                        phrase_observations=sum(
                            match.method == MatchMethod.PHRASE for match in matches
                        ),
                        is_sparse=(
                            len(matches) < summary.minimum_match_requirement
                        ),
                        original_scale=(
                            f"{metadata.source_scale_min:g} to "
                            f"{metadata.source_scale_max:g}"
                        ),
                        normalization_formula=metadata.normalization_formula,
                    )
                )
    view_order = {"All matched tokens": 0, "Stopwords excluded": 1}
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.lexicon.casefold(),
                view_order.get(row.analysis_view, 99),
                -(
                    row.eligible_token_occurrences
                    if row.eligible_token_occurrences is not None
                    else row.matched_token_occurrences
                ),
                row.category,
                row.tag,
            ),
        )
    )


def vad_interpretation_views(
    workspace: WorkspaceAnalysis,
) -> tuple[VadInterpretationView, ...]:
    """Explain normalized VAD means without making contextual emotion claims."""

    rows = []
    for view in vad_views(workspace):
        values = {
            "valence": view.normalized_valence,
            "arousal": view.normalized_arousal,
            "dominance": view.normalized_dominance,
        }
        for dimension, value in values.items():
            if value is None:
                continue
            if value > 0.5:
                relation = "above"
            elif value < 0.5:
                relation = "below"
            else:
                relation = "at"
            coverage_text = (
                "Coverage was unavailable"
                if view.lexical_coverage is None
                else f"Lexical-token coverage was {view.lexical_coverage:.1%}"
            )
            rows.append(
                VadInterpretationView(
                    lexicon_id=view.lexicon_id,
                    lexicon=view.lexicon,
                    analysis_view=view.analysis_view,
                    dimension=dimension,
                    mean=value,
                    matched_observations=view.matched_observations,
                    lexical_coverage=view.lexical_coverage,
                    relation_to_midpoint=relation,
                    explanation=(
                        f"{view.analysis_view}: mean normative {dimension} among "
                        f"{view.matched_observations} "
                        f"included matched observations was {value:.3f}, {relation} "
                        f"the 0.5 midpoint of the derived display scale. {coverage_text}. "
                        "This describes matched lexical ratings, not the poem or speaker."
                    ),
                )
            )
    return tuple(rows)


def vad_sensitivity_views(
    workspace: WorkspaceAnalysis,
) -> tuple[VadSensitivityView, ...]:
    """Compare filtered minus full means without preferring either view."""

    rows: list[VadSensitivityView] = []
    for result in workspace.results:
        summary = result.vad_summary
        if summary is None:
            continue
        groups = (
            (
                "token",
                summary.token_weighted_normalized,
                summary.stopword_excluded_token_weighted_normalized,
            ),
            (
                "type",
                summary.type_weighted_normalized,
                summary.stopword_excluded_type_weighted_normalized,
            ),
        )
        for weighting, all_group, filtered_group in groups:
            if filtered_group is None:
                continue
            for dimension in ("valence", "arousal", "dominance"):
                all_mean = getattr(all_group, dimension).mean
                filtered_mean = getattr(filtered_group, dimension).mean
                difference = (
                    filtered_mean - all_mean
                    if all_mean is not None and filtered_mean is not None
                    else None
                )
                rows.append(
                    VadSensitivityView(
                        lexicon_id=result.lexicon_metadata.lexicon_id,
                        lexicon=result.lexicon_metadata.display_name,
                        weighting=weighting,
                        dimension=dimension,
                        all_matched_mean=all_mean,
                        stopwords_excluded_mean=filtered_mean,
                        difference=difference,
                    )
                )
    return tuple(rows)


def vad_contributor_views(
    workspace: WorkspaceAnalysis,
    *,
    per_direction: int = 5,
) -> tuple[VadContributorView, ...]:
    """Return midpoint-centered term contributions for both VAD views."""

    if per_direction < 1:
        raise ValueError("per_direction must be at least 1")
    rows: list[VadContributorView] = []
    for result in workspace.results:
        summary = result.vad_summary
        if summary is None:
            continue
        all_included = tuple(
            match
            for match in result.matches
            if match.included
            and match.normalized_scores is not None
            and match.original_scores is not None
            and match.matched_term is not None
        )
        if not all_included:
            continue
        token_map = {token.token_id: token for token in result.tokens}
        analysis_groups = (
            (
                "All matched tokens",
                all_included,
                summary.token_weighted_normalized,
            ),
            (
                "Stopwords excluded",
                tuple(
                    match for match in all_included if match.included_in_stopword_view
                ),
                summary.stopword_excluded_token_weighted_normalized,
            ),
        )
        for analysis_view, included, statistics_group in analysis_groups:
            if not included or statistics_group is None:
                continue
            means = {
                dimension: statistics.mean
                for dimension, statistics in statistics_group.by_dimension().items()
            }
            for dimension, mean in means.items():
                if mean is None:
                    continue
                grouped: dict[str, list] = {}
                for match in included:
                    grouped.setdefault(match.matched_term or "", []).append(match)
                dimension_rows = []
                total = len(included)
                for term, matches in grouped.items():
                    first_match = matches[0]
                    normalized_rating = getattr(first_match.normalized_scores, dimension)
                    original_rating = getattr(first_match.original_scores, dimension)
                    count = len(matches)
                    midpoint_deviation = normalized_rating - 0.5
                    signed_contribution = count * midpoint_deviation
                    effect = None
                    if total > count:
                        mean_without = (
                            mean * total - normalized_rating * count
                        ) / (total - count)
                        effect = mean - mean_without
                    if signed_contribution > 0:
                        direction = "above-midpoint weighted deviation"
                    elif signed_contribution < 0:
                        direction = "below-midpoint weighted deviation"
                    else:
                        direction = "at midpoint"
                    first_tokens = tuple(
                        token_map[token_id] for token_id in first_match.token_ids
                    )
                    surface_forms = sorted(
                        {
                            " ".join(
                                token_map[token_id].surface_form
                                for token_id in match.token_ids
                            )
                            for match in matches
                        },
                        key=str.casefold,
                    )
                    dimension_rows.append(
                        VadContributorView(
                            lexicon_id=result.lexicon_metadata.lexicon_id,
                            lexicon=result.lexicon_metadata.display_name,
                            analysis_view=analysis_view,
                            dimension=dimension,
                            term=term,
                            surface_forms=", ".join(surface_forms),
                            observations=count,
                            normalized_rating=normalized_rating,
                            original_rating=original_rating,
                            midpoint_deviation_per_occurrence=midpoint_deviation,
                            signed_contribution=signed_contribution,
                            absolute_contribution=abs(signed_contribution),
                            effect_on_mean=effect,
                            direction=direction,
                            stopword_status=", ".join(
                                sorted(
                                    {match.stopword_status for match in matches},
                                    key=str.casefold,
                                )
                            ),
                            example_surface=" ".join(
                                token.surface_form for token in first_tokens
                            ),
                            example_line=first_match.line_number,
                            example_context=first_tokens[0].context,
                            match_method=first_match.method.value,
                        )
                    )
                positive = sorted(
                    (row for row in dimension_rows if row.signed_contribution > 0),
                    key=lambda row: (
                        -row.signed_contribution,
                        row.term.casefold(),
                    ),
                )[:per_direction]
                negative = sorted(
                    (row for row in dimension_rows if row.signed_contribution < 0),
                    key=lambda row: (
                        row.signed_contribution,
                        row.term.casefold(),
                    ),
                )[:per_direction]
                neutral = [
                    row for row in dimension_rows if row.signed_contribution == 0
                ][:per_direction]
                rows.extend((*positive, *negative, *neutral))
    return tuple(rows)


def vad_cumulative_views(
    workspace: WorkspaceAnalysis,
) -> tuple[VadCumulativeView, ...]:
    """Return length-sensitive token totals without claiming reader response.

    Each included match contributes once. For an activated multiword expression,
    the phrase is one matched observation, consistent with the analysis policy.
    Unmatched tokens remain missing and contribute neither a score nor a zero.
    """

    rows: list[VadCumulativeView] = []
    for result in workspace.results:
        if result.vad_summary is None:
            continue
        all_included = tuple(
            match
            for match in result.matches
            if match.included and match.normalized_scores is not None
        )
        analysis_groups = [
            (
                "All matched tokens",
                all_included,
                result.coverage.total_lexical_tokens,
                result.coverage.lexical_token_coverage,
            )
        ]
        if result.stopword_coverage is not None:
            analysis_groups.append(
                (
                    "Stopwords excluded",
                    tuple(
                        match
                        for match in all_included
                        if match.included_in_stopword_view
                    ),
                    result.stopword_coverage.eligible_token_count,
                    result.stopword_coverage.lexical_token_coverage,
                )
            )
        for analysis_view, included, lexical_tokens, lexical_coverage in analysis_groups:
            for dimension in ("valence", "arousal", "dominance"):
                values = [
                    float(getattr(match.normalized_scores, dimension))
                    for match in included
                    if match.normalized_scores is not None
                ]
                if not values:
                    continue
                above = sum(max(value - 0.5, 0.0) for value in values)
                below = sum(max(0.5 - value, 0.0) for value in values)
                rows.append(
                    VadCumulativeView(
                        lexicon_id=result.lexicon_metadata.lexicon_id,
                        lexicon=result.lexicon_metadata.display_name,
                        analysis_view=analysis_view,
                        dimension=dimension,
                        matched_observations=len(values),
                        lexical_tokens=lexical_tokens,
                        lexical_coverage=lexical_coverage,
                        rating_total=sum(values),
                        above_midpoint_deviation=above,
                        below_midpoint_deviation=below,
                        net_midpoint_deviation=above - below,
                        absolute_midpoint_deviation=above + below,
                    )
                )
    return tuple(rows)


def emotion_association_views(
    workspace: WorkspaceAnalysis,
) -> tuple[EmotionAssociationView, ...]:
    return _association_views(
        workspace,
        {
            "anger",
            "anticipation",
            "disgust",
            "fear",
            "joy",
            "sadness",
            "surprise",
            "trust",
        },
    )


def sentiment_association_views(
    workspace: WorkspaceAnalysis,
) -> tuple[EmotionAssociationView, ...]:
    """Keep positive/negative sentiment distinct from the eight emotions."""

    return _association_views(workspace, {"positive", "negative"})


def _association_views(
    workspace: WorkspaceAnalysis,
    categories: set[str],
) -> tuple[EmotionAssociationView, ...]:
    rows = []
    for result in workspace.results:
        for stats in result.category_statistics:
            if stats.category not in categories:
                continue
            rows.append(
                EmotionAssociationView(
                    category=stats.category,
                    token_count=stats.associated_token_count,
                    unique_types=stats.associated_unique_type_count,
                    rate_per_lexical_token=stats.proportion_of_lexical_tokens,
                    rate_among_emotion_bearing_tokens=(
                        stats.proportion_of_matched_emotion_bearing_tokens
                    ),
                    top_terms=", ".join(item.term for item in stats.top_contributing_terms[:5]),
                )
            )
    return tuple(rows)


def emotion_intensity_views(
    workspace: WorkspaceAnalysis,
) -> tuple[EmotionIntensityView, ...]:
    rows = []
    for result in workspace.results:
        for stats in result.intensity_statistics:
            rows.append(
                EmotionIntensityView(
                    category=stats.category,
                    token_count=stats.matched_token_occurrences,
                    distinct_pairs=stats.matched_word_emotion_pairs,
                    prevalence_per_lexical_token=stats.prevalence_among_lexical_tokens,
                    mean_matched_intensity=stats.token_weighted.mean,
                    median_matched_intensity=stats.token_weighted.median,
                    maximum_matched_intensity=stats.token_weighted.maximum,
                    top_terms=", ".join(item.term for item in stats.top_contributing_terms[:5]),
                )
            )
    return tuple(rows)


def _match_value(match) -> str:
    if match.normalized_scores is not None:
        scores = match.normalized_scores
        return f"V {scores.valence:.3f}; A {scores.arousal:.3f}; D {scores.dominance:.3f} (0-1)"
    if match.associations:
        return ", ".join(match.associations)
    if match.intensities:
        return "; ".join(f"{name} {value:.3f}" for name, value in match.intensities)
    return ""


def match_views(workspace: WorkspaceAnalysis) -> tuple[MatchView, ...]:
    rows = []
    for result in workspace.results:
        token_map = {token.token_id: token for token in result.tokens}
        for match in result.matches:
            tokens = tuple(token_map[token_id] for token_id in match.token_ids)
            first = tokens[0]
            rows.append(
                MatchView(
                    lexicon_id=result.lexicon_metadata.lexicon_id,
                    lexicon=result.lexicon_metadata.display_name,
                    surface=" ".join(token.surface_form for token in tokens),
                    normalized=" ".join(token.normalized_form for token in tokens),
                    line=match.line_number,
                    stanza=match.stanza_number,
                    pos=" + ".join(token.part_of_speech for token in tokens),
                    lemma=" ".join(token.lemma for token in tokens),
                    matched_term=match.matched_term or "",
                    method=match.method.value,
                    status=match.selection.value,
                    value=_match_value(match),
                    context=first.context,
                    explanation=match.reason,
                    stopword_status=match.stopword_status,
                    included_in_full=match.included,
                    included_in_filtered=match.included_in_stopword_view,
                    stopword_exclusion_reason=match.stopword_exclusion_reason,
                )
            )
    return tuple(rows)


def unmatched_views(workspace: WorkspaceAnalysis) -> tuple[UnmatchedView, ...]:
    grouped: dict[tuple[str, str, str, str, str], list[tuple[int, str]]] = {}
    display_names = {
        result.lexicon_metadata.lexicon_id: result.lexicon_metadata.display_name
        for result in workspace.results
    }
    for result in workspace.results:
        token_map = {token.token_id: token for token in result.tokens}
        for match in result.matches:
            if match.selection != MatchSelection.UNMATCHED or len(match.token_ids) != 1:
                continue
            token = token_map[match.token_ids[0]]
            if not token.is_lexical:
                continue
            key = (
                match.lexicon_id,
                token.surface_form,
                token.normalized_form,
                token.part_of_speech,
                token.lemma,
            )
            grouped.setdefault(key, []).append((token.line_number, token.context))
    rows = []
    for (lexicon_id, surface, normalized_form, pos, lemma), examples in grouped.items():
        rows.append(
            UnmatchedView(
                lexicon_id=lexicon_id,
                lexicon=display_names[lexicon_id],
                surface=surface,
                normalized_form=normalized_form,
                frequency=len(examples),
                pos=pos,
                proposed_lemma=lemma,
                example_line=examples[0][0],
                example_context=examples[0][1],
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.lexicon, -row.frequency, row.surface.casefold())))


def overview_notes(workspace: WorkspaceAnalysis) -> tuple[str, ...]:
    notes = [
        "Every number describes lexical evidence under the selected matching policy, not the emotion of the poem or its speaker.",
        "Coverage tells you how much eligible vocabulary contributed. Compare scores only alongside matched counts and coverage.",
    ]
    vad = vad_views(workspace)
    if vad:
        notes.append(
            "The VAD comparison uses separately derived 0-1 values. Original source scales and formulas remain available."
        )
    if emotion_association_views(workspace):
        notes.append(
            "The eight emotion associations are multi-label categories, so their "
            "percentages are not expected to sum to 100%. Positive/negative "
            "sentiment is reported separately."
        )
    if emotion_intensity_views(workspace):
        notes.append(
            "Emotion intensity means use only supplied word-emotion pairs; missing pairs are not treated as zero."
        )
    if workspace.concreteness is not None:
        notes.append(
            "Concreteness results describe matched normative lexical ratings on "
            "the source 1-5 scale. They do not measure imagery success, "
            "readability, literary quality, intelligence, or comprehension."
        )
    if workspace.frequency is not None:
        notes.append(
            "Frequency results describe how represented word forms are distributed "
            "in SUBTLEX-US. Zipf values are corpus-relative and do not measure "
            "difficulty, sophistication, accessibility, or literary quality."
        )
    if workspace.aoa is not None:
        notes.append(
            "Age-of-acquisition results aggregate retrospective normative lexical "
            "ratings in years. They are not grade level, difficulty, intelligence, "
            "familiarity, or diagnostic evidence of cognitive impairment or decline."
        )
    if workspace.inherited_form is not None:
        notes.append(
            "Inherited Form Analysis reports structural resemblance to a "
            "comprehensive, versioned registry of traditional and inherited "
            "form profiles. A potential match, consistency "
            "index, and confidence band are not a declaration of genre identity "
            "or a probability."
        )
    if workspace.lexical_style is not None:
        notes.append(
            "Lexical-diversity, word-length, and structural word-count results "
            "describe normalized observed surface forms and shared-preprocessing "
            "lexical tokens. They do not measure literary quality, vocabulary "
            "knowledge, or reader ability."
        )
    if workspace.poetry_id is not None:
        notes.append(
            "PoetryID reports nearest candidate lexical-affective profiles "
            "under explicit thresholds, source, view, and weighting choices. "
            "Its affinities and confidence labels are not probabilities, and "
            "it does not identify the poem's emotion."
        )
    if workspace.phonology is not None:
        notes.append(
            "Rhyme and recurring-sound results are derived from local dictionary "
            "pronunciations and spelling. They describe textual evidence, not a "
            "particular reading, dialect, performance, or definitive rhyme judgment."
        )
    if workspace.request.scenario_version_id:
        notes.append(
            f"This is a reviewed scenario result pinned to "
            f"{workspace.request.scenario_version_id} with "
            f"{len(workspace.request.review_rules)} active decision revision(s). "
            "The unreviewed baseline remains separate."
        )
    return tuple(notes)


def _csv_bytes(fieldnames: list[str], rows: Iterable[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def vad_part_of_speech_csv(workspace: WorkspaceAnalysis) -> bytes:
    """Export the source- and view-specific VAD-by-POS table."""

    fields = [
        "lexicon_id",
        "lexicon",
        "analysis_view",
        "source_pos_tags",
        "part_of_speech",
        "matched_observations",
        "distinct_matched_lexicon_entries",
        "matched_token_occurrences",
        "eligible_token_occurrences",
        "lexical_token_coverage",
        "token_weighted_mean_valence_0_1",
        "token_weighted_mean_arousal_0_1",
        "token_weighted_mean_dominance_0_1",
        "type_weighted_mean_valence_0_1",
        "type_weighted_mean_arousal_0_1",
        "type_weighted_mean_dominance_0_1",
        "token_weighted_mean_valence_original_scale",
        "token_weighted_mean_arousal_original_scale",
        "token_weighted_mean_dominance_original_scale",
        "type_weighted_mean_valence_original_scale",
        "type_weighted_mean_arousal_original_scale",
        "type_weighted_mean_dominance_original_scale",
        "published_phrase_observations",
        "sparse_below_configured_minimum",
        "original_scale",
        "normalization_formula",
    ]
    rows = []
    for row in vad_part_of_speech_views(workspace):
        rows.append(
            {
                "lexicon_id": row.lexicon_id,
                "lexicon": row.lexicon,
                "analysis_view": row.analysis_view,
                "source_pos_tags": row.tag,
                "part_of_speech": row.category,
                "matched_observations": row.matched_observations,
                "distinct_matched_lexicon_entries": row.matched_types,
                "matched_token_occurrences": row.matched_token_occurrences,
                "eligible_token_occurrences": (
                    row.eligible_token_occurrences
                    if row.eligible_token_occurrences is not None
                    else ""
                ),
                "lexical_token_coverage": (
                    row.lexical_coverage
                    if row.lexical_coverage is not None
                    else ""
                ),
                "token_weighted_mean_valence_0_1": (
                    row.token_weighted_valence
                    if row.token_weighted_valence is not None
                    else ""
                ),
                "token_weighted_mean_arousal_0_1": (
                    row.token_weighted_arousal
                    if row.token_weighted_arousal is not None
                    else ""
                ),
                "token_weighted_mean_dominance_0_1": (
                    row.token_weighted_dominance
                    if row.token_weighted_dominance is not None
                    else ""
                ),
                "type_weighted_mean_valence_0_1": (
                    row.type_weighted_valence
                    if row.type_weighted_valence is not None
                    else ""
                ),
                "type_weighted_mean_arousal_0_1": (
                    row.type_weighted_arousal
                    if row.type_weighted_arousal is not None
                    else ""
                ),
                "type_weighted_mean_dominance_0_1": (
                    row.type_weighted_dominance
                    if row.type_weighted_dominance is not None
                    else ""
                ),
                "token_weighted_mean_valence_original_scale": (
                    row.original_token_weighted_valence
                    if row.original_token_weighted_valence is not None
                    else ""
                ),
                "token_weighted_mean_arousal_original_scale": (
                    row.original_token_weighted_arousal
                    if row.original_token_weighted_arousal is not None
                    else ""
                ),
                "token_weighted_mean_dominance_original_scale": (
                    row.original_token_weighted_dominance
                    if row.original_token_weighted_dominance is not None
                    else ""
                ),
                "type_weighted_mean_valence_original_scale": (
                    row.original_type_weighted_valence
                    if row.original_type_weighted_valence is not None
                    else ""
                ),
                "type_weighted_mean_arousal_original_scale": (
                    row.original_type_weighted_arousal
                    if row.original_type_weighted_arousal is not None
                    else ""
                ),
                "type_weighted_mean_dominance_original_scale": (
                    row.original_type_weighted_dominance
                    if row.original_type_weighted_dominance is not None
                    else ""
                ),
                "published_phrase_observations": row.phrase_observations,
                "sparse_below_configured_minimum": row.is_sparse,
                "original_scale": row.original_scale,
                "normalization_formula": row.normalization_formula,
            }
        )
    return _csv_bytes(fields, rows)


def scholar_summary_csv(workspace: WorkspaceAnalysis) -> bytes:
    fields = [
        "section",
        "lexicon",
        "analysis_view",
        "metric",
        "value",
        "unit_or_scale",
        "denominator",
        "plain_language_note",
    ]
    rows: list[dict[str, object]] = []
    if workspace.request.scenario_version_id:
        rows.extend(
            (
                {
                    "section": "Review methodology",
                    "lexicon": "",
                    "analysis_view": "Reviewed scenario",
                    "metric": "Scenario version ID",
                    "value": workspace.request.scenario_version_id,
                    "unit_or_scale": "stable local identifier",
                    "denominator": "",
                    "plain_language_note": (
                        "This immutable result uses the exact decision revisions "
                        "listed in the detailed manifest."
                    ),
                },
                {
                    "section": "Review methodology",
                    "lexicon": "",
                    "analysis_view": "Reviewed scenario",
                    "metric": "Active review decision revisions",
                    "value": len(workspace.request.review_rules),
                    "unit_or_scale": "count",
                    "denominator": "",
                    "plain_language_note": (
                        "Flags are non-scoring; mappings and exclusions apply only "
                        "within this scenario."
                    ),
                },
            )
        )
    for pos in part_of_speech_views(workspace):
        rows.append(
            {
                "section": "Part of speech",
                "lexicon": "spaCy English linguistic model",
                "analysis_view": "All eligible lexical tokens",
                "metric": f"{pos.category} share",
                "value": pos.share_of_lexical_tokens,
                "unit_or_scale": "proportion",
                "denominator": (
                    f"{pos.token_count} of {pos.lexical_token_denominator} "
                    "lexical token occurrences"
                ),
                "plain_language_note": (
                    f"Source POS tag(s) {pos.tag}; {pos.unique_type_count} unique "
                    f"normalized type(s). Examples: {pos.example_forms or 'none'}. "
                    "Labels are model-generated and may be uncertain in poetic syntax."
                ),
            }
        )
    for coverage in coverage_views(workspace):
        rows.append(
            {
                "section": "Coverage",
                "lexicon": coverage.lexicon,
                "analysis_view": "All matched tokens",
                "metric": "Lexical-token coverage",
                "value": coverage.coverage if coverage.coverage is not None else "",
                "unit_or_scale": "proportion",
                "denominator": f"{coverage.lexical_tokens} lexical tokens",
                "plain_language_note": coverage.note,
            }
        )
    for result in workspace.results:
        if result.stopword_coverage is None:
            continue
        coverage = result.stopword_coverage
        rows.append(
            {
                "section": "Coverage",
                "lexicon": result.lexicon_metadata.display_name,
                "analysis_view": "Stopwords excluded",
                "metric": "Content-focused lexical coverage",
                "value": (
                    coverage.lexical_token_coverage
                    if coverage.lexical_token_coverage is not None
                    else ""
                ),
                "unit_or_scale": "proportion",
                "denominator": (
                    f"{coverage.eligible_token_count} eligible non-stopword, "
                    "non-review-excluded tokens"
                ),
                "plain_language_note": (
                    "Intentionally excluded stopwords and scenario exclusions are "
                    "removed from this secondary denominator."
                ),
            }
        )
    contributors = vad_contributor_views(workspace, per_direction=3)
    for row in vad_views(workspace):
        dimensions = (
            ("valence", row.normalized_valence, row.type_valence),
            ("arousal", row.normalized_arousal, row.type_arousal),
            ("dominance", row.normalized_dominance, row.type_dominance),
        )
        for dimension, token_value, type_value in dimensions:
            terms = [
                item
                for item in contributors
                if item.lexicon_id == row.lexicon_id
                and item.analysis_view == row.analysis_view
                and item.dimension == dimension
            ]
            contributor_note = "; ".join(
                f"{item.term} ({item.signed_contribution:+.3f} weighted deviation)"
                for item in terms
            )
            for weighting, value in (("token", token_value), ("type", type_value)):
                rows.append(
                    {
                        "section": "Normalized VAD",
                        "lexicon": row.lexicon,
                        "analysis_view": row.analysis_view,
                        "metric": f"Mean normative {dimension} ({weighting}-weighted)",
                        "value": value if value is not None else "",
                        "unit_or_scale": "derived 0-1",
                        "denominator": (
                            f"{row.matched_observations} included matched observations"
                            if weighting == "token"
                            else "distinct matched lexicon entries"
                        ),
                        "plain_language_note": (
                            f"Top token-mean contributors: {contributor_note or 'not available'}. "
                            "Original values and formula remain in the detailed audit."
                        ),
                    }
                )
    for row in vad_cumulative_views(workspace):
        for label, value in (
            ("Rating total", row.rating_total),
            ("Above-midpoint load", row.above_midpoint_deviation),
            ("Below-midpoint load", row.below_midpoint_deviation),
            ("Net midpoint load", row.net_midpoint_deviation),
            ("Absolute midpoint load", row.absolute_midpoint_deviation),
        ):
            rows.append(
                {
                    "section": "Cumulative normative lexical load",
                    "lexicon": row.lexicon,
                    "analysis_view": row.analysis_view,
                    "metric": f"{row.dimension.title()} — {label}",
                    "value": value,
                    "unit_or_scale": "length-sensitive token sum on derived 0-1 scale",
                    "denominator": f"{row.matched_observations} included matched observations",
                    "plain_language_note": (
                        "Describes cumulative lexical evidence, not a measured effect on a reader."
                    ),
                }
            )
    for row in vad_sensitivity_views(workspace):
        rows.append(
            {
                "section": "Stopword sensitivity",
                "lexicon": row.lexicon,
                "analysis_view": "Filtered minus full",
                "metric": (
                    f"Mean normative {row.dimension} difference "
                    f"({row.weighting}-weighted)"
                ),
                "value": row.difference if row.difference is not None else "",
                "unit_or_scale": "derived 0-1 difference",
                "denominator": "stopword-excluded mean minus all-matched mean",
                "plain_language_note": (
                    "A larger absolute difference indicates greater sensitivity to "
                    "common grammatical words; neither view is labeled more accurate."
                ),
            }
        )
    for row in emotion_association_views(workspace):
        rows.append(
            {
                "section": "Emotion association",
                "lexicon": "NRC Emotion",
                "analysis_view": "All matched tokens",
                "metric": f"{row.category} association rate",
                "value": row.rate_per_lexical_token if row.rate_per_lexical_token is not None else "",
                "unit_or_scale": "proportion",
                "denominator": "all lexical tokens",
                "plain_language_note": f"Contributors: {row.top_terms or 'none'}",
            }
        )
    for row in sentiment_association_views(workspace):
        rows.append(
            {
                "section": "Sentiment association",
                "lexicon": "NRC Emotion",
                "analysis_view": "All matched tokens",
                "metric": f"{row.category} sentiment-association rate",
                "value": (
                    row.rate_per_lexical_token
                    if row.rate_per_lexical_token is not None
                    else ""
                ),
                "unit_or_scale": "proportion",
                "denominator": "all lexical tokens",
                "plain_language_note": (
                    f"Contributors: {row.top_terms or 'none'}. Sentiment is "
                    "presented separately from the eight emotion categories."
                ),
            }
        )
    for row in emotion_intensity_views(workspace):
        rows.append(
            {
                "section": "Emotion intensity",
                "lexicon": "NRC Emotion Intensity",
                "analysis_view": "All matched tokens",
                "metric": f"Mean matched {row.category} intensity",
                "value": row.mean_matched_intensity if row.mean_matched_intensity is not None else "",
                "unit_or_scale": "source 0-1",
                "denominator": f"{row.token_count} matched {row.category} occurrences",
                "plain_language_note": "Absent word-emotion pairs are missing, not zero.",
            }
        )
    if workspace.vader_sentiment is not None:
        vader = workspace.vader_sentiment
        score = vader.document_score
        for metric, value, unit, note in (
            (
                "Positive proportion",
                score.positive_proportion,
                "proportion",
                "Raw lexical polarity category; the three proportions sum to approximately one.",
            ),
            (
                "Neutral proportion",
                score.neutral_proportion,
                "proportion",
                "Raw lexical polarity category; not evidence of emotional neutrality.",
            ),
            (
                "Negative proportion",
                score.negative_proportion,
                "proportion",
                "Raw lexical polarity category; the three proportions sum to approximately one.",
            ),
            (
                "Compound score",
                score.compound_score,
                "normalized weighted composite (-1 to 1)",
                "Includes VADER's rule-based adjustments.",
            ),
            (
                "Conventional threshold label",
                score.threshold_label,
                "positive / neutral / negative",
                "A rule-based polarity label, not a declaration of the poem's emotion.",
            ),
        ):
            rows.append(
                {
                    "section": "VADER sentiment",
                    "lexicon": f"vaderSentiment {vader.package_version}",
                    "analysis_view": "Complete preserved text",
                    "metric": metric,
                    "value": value,
                    "unit_or_scale": unit,
                    "denominator": "complete preserved text",
                    "plain_language_note": note,
                }
            )
    if workspace.concreteness is not None:
        concreteness = workspace.concreteness
        summary = concreteness.summary
        stats = summary.statistics
        for metric, value, unit in (
            ("Mean normative concreteness", stats.mean, "source 1-5"),
            ("Median normative concreteness", stats.median, "source 1-5"),
            (
                "Population standard deviation",
                stats.population_standard_deviation,
                "source-scale points",
            ),
            ("Interquartile range", summary.interquartile_range, "source-scale points"),
        ):
            rows.append(
                {
                    "section": "Concreteness",
                    "lexicon": concreteness.resource_status.display_name,
                    "analysis_view": "Rated eligible token occurrences",
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": (
                        f"{summary.rated_token_count} rated eligible token occurrences"
                    ),
                    "plain_language_note": (
                        "Normative lexical evidence only; unmatched observations "
                        "remain missing."
                    ),
                }
            )
        for metric, value, denominator, note in (
            (
                "Rated-token coverage",
                summary.token_coverage,
                (
                    f"{summary.rated_token_count} of "
                    f"{summary.eligible_token_count} eligible token occurrences"
                ),
                "Multiword ratings retain a shared expression group in the audit.",
            ),
            (
                "Rated unique-word coverage",
                summary.unique_type_coverage,
                (
                    f"{summary.rated_unique_type_count} of "
                    f"{summary.eligible_unique_type_count} normalized surface types"
                ),
                "The denominator uses observed surface types, not lemma types.",
            ),
            (
                "Configured highly concrete proportion",
                summary.highly_concrete_proportion,
                f"{summary.rated_token_count} rated token occurrences",
                (
                    f"VerseVAD orientation band >= "
                    f"{summary.highly_concrete_min:g}; not a source-paper category."
                ),
            ),
            (
                "Configured highly abstract proportion",
                summary.highly_abstract_proportion,
                f"{summary.rated_token_count} rated token occurrences",
                (
                    f"VerseVAD orientation band <= "
                    f"{summary.highly_abstract_max:g}; not a source-paper category."
                ),
            ),
        ):
            rows.append(
                {
                    "section": "Concreteness",
                    "lexicon": concreteness.resource_status.display_name,
                    "analysis_view": "Rated eligible token occurrences",
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": "proportion",
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
    if workspace.frequency is not None:
        frequency = workspace.frequency
        summary = frequency.summary
        stats = summary.statistics
        for metric, value, unit, note in (
            (
                "Median SUBTLEX-US Zipf frequency",
                stats.median,
                "SUBTLEX-US Zipf",
                "Primary token-weighted summary; the Zipf scale is logarithmic.",
            ),
            (
                "Mean SUBTLEX-US Zipf frequency",
                stats.mean,
                "SUBTLEX-US Zipf",
                "Rare outliers can pull the mean downward.",
            ),
            (
                "Population standard deviation",
                stats.population_standard_deviation,
                "Zipf points",
                "Population, not sample, standard deviation.",
            ),
            (
                "Interquartile range",
                summary.interquartile_range,
                "Zipf points",
                "Inclusive quartiles among matched token occurrences.",
            ),
        ):
            rows.append(
                {
                    "section": "Lexical frequency",
                    "lexicon": frequency.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": (
                        f"{summary.matched_token_count} matched eligible "
                        "token occurrences"
                    ),
                    "plain_language_note": note,
                }
            )
        for metric, value, denominator, note in (
            (
                "Matched-token coverage",
                summary.token_coverage,
                (
                    f"{summary.matched_token_count} of "
                    f"{summary.eligible_token_count} eligible token occurrences"
                ),
                "Unmatched observations remain missing rather than Zipf zero.",
            ),
            (
                "Matched unique-word coverage",
                summary.unique_type_coverage,
                (
                    f"{summary.matched_unique_type_count} of "
                    f"{summary.eligible_unique_type_count} normalized surface types"
                ),
                "The denominator uses observed surface types, not lemma types.",
            ),
        ):
            rows.append(
                {
                    "section": "Lexical frequency",
                    "lexicon": frequency.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": "proportion",
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
        for band in summary.bands:
            rows.append(
                {
                    "section": "Lexical frequency",
                    "lexicon": frequency.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": f"Configured {band.label.casefold()} proportion",
                    "value": band.proportion if band.proportion is not None else "",
                    "unit_or_scale": "proportion",
                    "denominator": (
                        f"{summary.matched_token_count} matched token occurrences"
                    ),
                    "plain_language_note": (
                        "Configurable VerseVAD orientation band; not a universal "
                        "linguistic category."
                    ),
                }
            )
    if workspace.readability is not None:
        readability = workspace.readability.summary
        for metric, value, unit in (
            (
                "Flesch Reading Ease",
                readability.flesch_reading_ease,
                "formula score; conventionally higher is easier",
            ),
            (
                "Flesch-Kincaid Grade",
                readability.flesch_kincaid_grade,
                "approximate U.S. grade-formula score",
            ),
            (
                "Gunning Fog Index",
                readability.gunning_fog_index,
                "approximate grade-formula score",
            ),
            (
                "Automated Readability Index",
                readability.automated_readability_index,
                "approximate U.S. grade-formula score",
            ),
            (
                "Coleman-Liau Index",
                readability.coleman_liau_index,
                "approximate U.S. grade-formula score",
            ),
            (
                "SMOG Index",
                readability.smog_index,
                "approximate grade-formula score",
            ),
        ):
            rows.append(
                {
                    "section": "Readability",
                    "lexicon": "Transparent offline English formulas",
                    "analysis_view": "Complete preserved text",
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": (
                        f"{readability.word_count} lexical tokens and "
                        f"{readability.sentence_count} model-segmented sentence(s)"
                    ),
                    "plain_language_note": (
                        "Prose-oriented formula evidence only; not literary quality, "
                        "reader ability, or a prescriptive grade requirement."
                    ),
                }
            )
    if workspace.aoa is not None:
        aoa = workspace.aoa
        summary = aoa.summary
        stats = summary.statistics
        for metric, value, unit, note in (
            (
                "Mean normative age of acquisition",
                stats.mean,
                "source mean age in years",
                "Mean of matched retrospective source Rating.Mean values.",
            ),
            (
                "Median normative age of acquisition",
                stats.median,
                "source mean age in years",
                "Token-weighted median of matched retrospective source means.",
            ),
            (
                "Population standard deviation",
                stats.population_standard_deviation,
                "years",
                (
                    "Variation among the poem's matched source means, not "
                    "within-entry rater uncertainty."
                ),
            ),
            (
                "Interquartile range",
                summary.interquartile_range,
                "years",
                "Inclusive quartiles among matched token occurrences.",
            ),
        ):
            rows.append(
                {
                    "section": "Age of acquisition",
                    "lexicon": aoa.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": (
                        f"{summary.matched_token_count} matched eligible "
                        "token occurrences"
                    ),
                    "plain_language_note": note,
                }
            )
        for metric, value, denominator, note in (
            (
                "Matched-token coverage",
                summary.token_coverage,
                (
                    f"{summary.matched_token_count} of "
                    f"{summary.eligible_token_count} eligible token occurrences"
                ),
                "Unmatched and source-unrated observations remain missing.",
            ),
            (
                "Matched unique-word coverage",
                summary.unique_type_coverage,
                (
                    f"{summary.matched_unique_type_count} of "
                    f"{summary.eligible_unique_type_count} normalized surface types"
                ),
                "The denominator uses observed surface types, not lemma types.",
            ),
        ):
            rows.append(
                {
                    "section": "Age of acquisition",
                    "lexicon": aoa.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": "proportion",
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
        for band in summary.bands:
            rows.append(
                {
                    "section": "Age of acquisition",
                    "lexicon": aoa.resource_status.display_name,
                    "analysis_view": summary.scope_label,
                    "metric": f"Configured {band.label.casefold()} proportion",
                    "value": band.proportion if band.proportion is not None else "",
                    "unit_or_scale": "proportion",
                    "denominator": (
                        f"{summary.matched_token_count} matched token occurrences"
                    ),
                    "plain_language_note": (
                        "Configurable VerseVAD orientation band; not a "
                        "source-paper category."
                    ),
                }
            )
        for relationship in aoa.relationships:
            rows.append(
                {
                    "section": "Age of acquisition",
                    "lexicon": aoa.resource_status.display_name,
                    "analysis_view": relationship.weighting,
                    "metric": (
                        f"Spearman relationship with "
                        f"{relationship.other_metric}"
                    ),
                    "value": (
                        relationship.coefficient
                        if relationship.coefficient is not None
                        else ""
                    ),
                    "unit_or_scale": "Spearman rho",
                    "denominator": (
                        f"{relationship.pair_count} paired normalized surface types"
                    ),
                    "plain_language_note": relationship.note,
                }
            )
    if workspace.lexical_style is not None:
        lexical_style = workspace.lexical_style
        summary = lexical_style.summary
        configuration = lexical_style.configuration
        for metric, value, unit, denominator, note in (
            (
                "Lexical token count",
                summary.lexical_token_count,
                "shared-preprocessing lexical tokens",
                "complete preserved text",
                "Punctuation and numeric tokens are excluded.",
            ),
            (
                "Normalized observed surface types",
                summary.normalized_surface_type_count,
                "normalized surface types",
                f"{summary.lexical_token_count} lexical tokens",
                "No lemma is silently substituted for an observed surface form.",
            ),
            (
                "Moving-average type-token ratio",
                summary.mattr,
                "mean overlapping-window TTR",
                (
                    f"{summary.mattr_window_count} windows of "
                    f"{configuration.mattr_window_size} lexical tokens"
                ),
                "Compare only results using the same window and word-unit policy.",
            ),
            (
                "Hypergeometric distribution diversity",
                summary.hdd,
                "expected distinct-type proportion",
                (
                    f"without-replacement samples of "
                    f"{configuration.hdd_sample_size} lexical tokens"
                ),
                "Compare only results using the same sample and word-unit policy.",
            ),
            (
                "Measure of textual lexical diversity",
                summary.mtld,
                "mean lexical-token factor length",
                (
                    f"forward and reverse factorization at TTR "
                    f"{configuration.mtld_threshold:g}"
                ),
                "Short poems can still yield unstable lexical-diversity estimates.",
            ),
            (
                "Mean word length",
                summary.mean_alphabetic_characters_per_token,
                "Unicode alphabetic characters per lexical token",
                (
                    f"{summary.word_length_observation_count} lexical tokens "
                    "with alphabetic-character lengths"
                ),
                "Punctuation marks inside a surface token are not counted as letters.",
            ),
            (
                "Average words per nonblank line",
                summary.nonblank_line_word_count_statistics.mean,
                "lexical tokens per nonblank physical line",
                f"{summary.nonblank_line_count} nonblank physical lines",
                "Blank separator lines remain visible with word count zero in the audit.",
            ),
            (
                "Population SD of words per nonblank line",
                (
                    summary.nonblank_line_word_count_statistics
                    .population_standard_deviation
                ),
                "lexical tokens per nonblank physical line",
                f"{summary.nonblank_line_count} nonblank physical lines",
                "Population, not sample, standard deviation.",
            ),
            (
                "Median words per nonblank line",
                summary.nonblank_line_word_count_statistics.median,
                "lexical tokens per nonblank physical line",
                f"{summary.nonblank_line_count} nonblank physical lines",
                "",
            ),
            (
                "Average words per stanza",
                summary.stanza_word_count_statistics.mean,
                "lexical tokens per stanza",
                f"{summary.stanza_count} stanzas",
                "",
            ),
            (
                "Population SD of words per stanza",
                (
                    summary.stanza_word_count_statistics
                    .population_standard_deviation
                ),
                "lexical tokens per stanza",
                f"{summary.stanza_count} stanzas",
                "Population, not sample, standard deviation.",
            ),
            (
                "Median words per stanza",
                summary.stanza_word_count_statistics.median,
                "lexical tokens per stanza",
                f"{summary.stanza_count} stanzas",
                "",
            ),
            (
                "Average nonblank lines per stanza",
                summary.stanza_line_count_statistics.mean,
                "nonblank physical lines per stanza",
                f"{summary.stanza_count} stanzas",
                "",
            ),
            (
                "Population SD of nonblank lines per stanza",
                summary.stanza_line_count_statistics.population_standard_deviation,
                "nonblank physical lines per stanza",
                f"{summary.stanza_count} stanzas",
                "Population, not sample, standard deviation.",
            ),
        ):
            rows.append(
                {
                    "section": "Lexical diversity and word counts",
                    "lexicon": "No external lexical resource",
                    "analysis_view": configuration.scenario_id,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
    if workspace.pronunciation is not None:
        pronunciation = workspace.pronunciation
        summary = pronunciation.summary
        for metric, value, unit, denominator, note in (
            (
                "Mean syllables per resolved word",
                summary.syllables_per_resolved_word.mean,
                "dictionary syllables per resolved lexical token",
                f"{summary.resolved_token_count} resolved tokens",
                (
                    "Dictionary-based North American pronunciation evidence; "
                    "materially different alternatives remain unresolved."
                ),
            ),
            (
                "Median syllables per complete line",
                summary.syllables_per_complete_line.median,
                "dictionary syllables per complete physical line",
                f"{summary.complete_line_count} complete lines",
                "Incomplete lines remain missing rather than undercounted.",
            ),
            (
                "Lexical stress density",
                summary.stress_density,
                "proportion of resolved syllables",
                f"{summary.total_resolved_syllables} resolved syllables",
                (
                    "Primary and secondary dictionary stress combined; not "
                    "meter or performed rhythm."
                ),
            ),
            (
                "Resolved pronunciation coverage",
                summary.token_coverage,
                "proportion",
                (
                    f"{summary.resolved_token_count} of "
                    f"{summary.eligible_token_count} eligible lexical tokens"
                ),
                "Unmatched and materially ambiguous observations remain missing.",
            ),
            (
                "Complete-line coverage",
                summary.complete_line_coverage,
                "proportion",
                (
                    f"{summary.complete_line_count} of "
                    f"{summary.eligible_line_count} eligible physical lines"
                ),
                (
                    "A line is complete only when every eligible lexical token "
                    "has resolved syllable and stress evidence."
                ),
            ),
        ):
            rows.append(
                {
                    "section": "Pronunciation and prosody foundation",
                    "lexicon": "Pinned official CMU Pronouncing Dictionary",
                    "analysis_view": "Exact observed-form dictionary evidence",
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
    if workspace.meter is not None:
        meter = workspace.meter
        summary = meter.summary
        for metric, value, unit, denominator, note in (
            (
                "Nearest configured candidate",
                summary.closest_candidate_label,
                summary.closest_candidate_kind,
                f"{summary.analyzable_line_count} analyzable physical lines",
                (
                    "A candidate comparison, not a definitive meter or "
                    "performed scansion."
                ),
            ),
            (
                "Mean candidate fit",
                summary.whole_poem_mean_fit,
                "normalized configured alignment similarity 0-1",
                f"{summary.analyzable_line_count} analyzable physical lines",
                "Configured sequence-alignment similarity; not a probability.",
            ),
            (
                "Matching-line proportion",
                summary.matching_line_proportion,
                "proportion",
                f"{summary.analyzable_line_count} analyzable physical lines",
                (
                    f"Uses the configured "
                    f"{meter.configuration.line_match_threshold:g} line-fit "
                    "threshold."
                ),
            ),
            (
                "Rule-based candidate confidence",
                summary.candidate_confidence,
                "configured category",
                f"{summary.analyzable_line_count} analyzable physical lines",
                summary.confidence_explanation,
            ),
        ):
            rows.append(
                {
                    "section": "Candidate meter and rhythmic regularity",
                    "lexicon": "Stage 5 pronunciation evidence",
                    "analysis_view": meter.configuration.scenario_id,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
    if workspace.phonology is not None:
        phonology = workspace.phonology
        summary = phonology.summary
        for metric, value, unit, denominator, note in (
            (
                "Whole-poem end-rhyme scheme",
                summary.whole_poem_rhyme_scheme,
                "exact-rhyme labels; x unrhymed; ? unresolved",
                f"{summary.eligible_line_count} eligible physical lines",
                (
                    "Only robust perfect or identical dictionary rhyme parts "
                    "create scheme groups; slant and eye evidence remain separate."
                ),
            ),
            (
                "Analyzable ending coverage",
                summary.ending_coverage,
                "proportion",
                (
                    f"{summary.analyzable_ending_count} of "
                    f"{summary.eligible_line_count} eligible line endings"
                ),
                "Unresolved endings receive no rhyme label or neutral value.",
            ),
            (
                "End-rhyme density",
                summary.rhyme_density,
                "proportion",
                f"{summary.analyzable_ending_count} analyzable line endings",
                "Share of analyzable lines participating in a within-stanza exact rhyme pair.",
            ),
            (
                "Perfect rhyme pairs",
                summary.perfect_rhyme_pair_count,
                "within-stanza ending pairs",
                "",
                "Masculine, feminine, and multisyllabic evidence is retained on pair rows.",
            ),
            (
                "Identical rhyme pairs",
                summary.identical_rhyme_pair_count,
                "within-stanza ending pairs",
                "",
                "Repeated words and complete homophonic endings remain explicitly labeled.",
            ),
            (
                "Graded slant-rhyme pairs",
                summary.slant_rhyme_pair_count,
                "within-stanza ending pairs",
                "",
                (
                    "Configured phoneme-and-stress similarity heuristic; "
                    "not a probability or performance judgment."
                ),
            ),
            (
                "Eye-rhyme pairs",
                summary.eye_rhyme_pair_count,
                "within-stanza orthographic pairs",
                "",
                "Spelling resemblance is reported separately from phonetic rhyme.",
            ),
            (
                "Internal-rhyme pairs",
                summary.internal_rhyme_pair_count,
                "within-line token pairs",
                "",
                "Uses exact dictionary rhyme parts within each physical line.",
            ),
            (
                "Alliteration density",
                summary.alliteration_density,
                "proportion of supported lexical tokens",
                "phonologically supported lexical tokens",
                "Repeated initial consonant phonemes within physical lines.",
            ),
            (
                "Assonance density",
                summary.assonance_density,
                "proportion of supported lexical tokens",
                "phonologically supported lexical tokens",
                "Repeated stressed-vowel phonemes within physical lines.",
            ),
            (
                "Consonance density",
                summary.consonance_density,
                "proportion of consonant occurrences",
                "resolved consonant phoneme occurrences",
                "Repeated consonant phonemes within physical lines.",
            ),
        ):
            rows.append(
                {
                    "section": "Rhyme and phonological patterns",
                    "lexicon": "Pinned official CMU Pronouncing Dictionary",
                    "analysis_view": phonology.configuration.scenario_id,
                    "metric": metric,
                    "value": value if value is not None else "",
                    "unit_or_scale": unit,
                    "denominator": denominator,
                    "plain_language_note": note,
                }
            )
    if workspace.poetry_id is not None:
        poetry_id = workspace.poetry_id
        for assignment in poetry_id.assignments:
            view = (
                f"{assignment.analysis_view}; "
                f"{assignment.weighting_mode}-weighted"
            )
            denominator = (
                f"{assignment.coverage.matched_token_count} matched "
                "observations"
                if assignment.weighting_mode == "token"
                else (
                    f"{assignment.coverage.matched_type_count} matched types"
                )
            )
            for metric, value, unit, note in (
                (
                    "Nearest categorical PoetryID profile",
                    assignment.categorical_archetype.name,
                    "canonical 27-profile label",
                    (
                        "Nearest candidate under the selected categorical "
                        "thresholds; not a declaration of the poem's emotion."
                    ),
                ),
                (
                    "Nearest Euclidean centroid profile",
                    assignment.nearest_centroid_archetype.name,
                    "canonical 27-profile label",
                    (
                        "Calculated across continuous normalized VAD; retained "
                        "separately from the categorical result."
                    ),
                ),
                (
                    "Rule-based PoetryID confidence",
                    assignment.confidence.label,
                    "documented evidence label",
                    (
                        f"{assignment.confidence.explanation} This is not a "
                        "probability."
                    ),
                ),
                (
                    "Categorical centroid distance",
                    assignment.centroid_distance,
                    "normalized Euclidean distance",
                    "Smaller means closer to the assigned profile centroid.",
                ),
            ):
                rows.append(
                    {
                        "section": "PoetryID",
                        "lexicon": assignment.source_lexicon_name,
                        "analysis_view": view,
                        "metric": metric,
                        "value": value,
                        "unit_or_scale": unit,
                        "denominator": denominator,
                        "plain_language_note": note,
                    }
                )
            for dimension in ("valence", "arousal", "dominance"):
                rows.append(
                    {
                        "section": "PoetryID",
                        "lexicon": assignment.source_lexicon_name,
                        "analysis_view": view,
                        "metric": (
                            f"Continuous normalized {dimension}"
                        ),
                        "value": getattr(assignment.vad, dimension),
                        "unit_or_scale": "normalized 0-1",
                        "denominator": denominator,
                        "plain_language_note": (
                            "Inherited from the completed source-specific VAD "
                            "analysis; PoetryID did not recalculate it."
                        ),
                    }
                )
    if workspace.inherited_form is not None:
        inherited = workspace.inherited_form
        best = inherited.best_candidate
        alternative = inherited.nearest_alternative
        rows.extend(
            (
                {
                    "section": "Inherited Form Analysis",
                    "lexicon": "Comprehensive inherited-form registry",
                    "analysis_view": inherited.configuration.scenario_id,
                    "metric": "Potential inherited-form match",
                    "value": best.profile_name if best else "No inherited-form match",
                    "unit_or_scale": (
                        best.classification
                        if best
                        else "configured no-match state"
                    ),
                    "denominator": "available weighted profile evidence",
                    "plain_language_note": (
                        best.tooltip
                        if best
                        else (
                            "No candidate met both the suggestion and minimum "
                            "evidence thresholds."
                        )
                    ),
                },
                {
                    "section": "Inherited Form Analysis",
                    "lexicon": "Comprehensive inherited-form registry",
                    "analysis_view": inherited.configuration.scenario_id,
                    "metric": "Form consistency",
                    "value": (
                        best.consistency
                        if best and best.consistency is not None
                        else ""
                    ),
                    "unit_or_scale": "proportion",
                    "denominator": "available weighted profile evidence",
                    "plain_language_note": (
                        "Consistency is not a probability; missing evidence is "
                        "excluded and separately lowers coverage."
                    ),
                },
                {
                    "section": "Inherited Form Analysis",
                    "lexicon": "Comprehensive inherited-form registry",
                    "analysis_view": inherited.configuration.scenario_id,
                    "metric": "Evidence coverage",
                    "value": (
                        best.evidence_coverage
                        if best
                        else inherited.candidates[0].evidence_coverage
                    ),
                    "unit_or_scale": "proportion",
                    "denominator": "potential profile weight",
                    "plain_language_note": (
                        "Unavailable pronunciation, meter, or rhyme evidence "
                        "stays missing rather than becoming a failed feature."
                    ),
                },
                {
                    "section": "Inherited Form Analysis",
                    "lexicon": "Comprehensive inherited-form registry",
                    "analysis_view": inherited.configuration.scenario_id,
                    "metric": "Nearest alternative",
                    "value": (
                        alternative.profile_name if alternative else ""
                    ),
                    "unit_or_scale": "candidate profile",
                    "denominator": "second-ranked enabled profile",
                    "plain_language_note": (
                        "Related forms can share features; the runner-up is "
                        "retained to make that ambiguity visible."
                    ),
                },
            )
        )
    return _csv_bytes(fields, rows)


def csv_reading_guide() -> bytes:
    fields = ["file", "what_it_answers", "start_with", "important_caution"]
    rows = [
        {
            "file": "scholar_summary.csv",
            "what_it_answers": "What are the principal readable results?",
            "start_with": "Coverage, VADER polarity, readability, concreteness, median Zipf frequency, normative AoA, token/type VAD means, cumulative load, contributors, association rates, and matched intensity means.",
            "important_caution": "Read every metric with its denominator and plain-language note.",
        },
        {
            "file": "vader_sentiment_summary.csv",
            "what_it_answers": (
                "What positive, neutral, and negative proportions and rule-adjusted "
                "compound polarity score did VADER assign?"
            ),
            "start_with": (
                "positive_proportion, neutral_proportion, negative_proportion, "
                "compound_score, and conventional_threshold_label."
            ),
            "important_caution": (
                "VADER is social-media-tuned rule-based polarity evidence, not a "
                "declaration of the poem's emotion or a reader's response."
            ),
        },
        {
            "file": "readability_summary.csv",
            "what_it_answers": (
                "What do familiar English readability formulas report for the text?"
            ),
            "start_with": (
                "Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog, "
                "Automated Readability Index, Coleman-Liau, and SMOG."
            ),
            "important_caution": (
                "These prose-oriented formulas do not measure literary quality, "
                "reader ability, or a prescriptive grade requirement."
            ),
        },
        {
            "file": "lexical_trajectory.csv",
            "what_it_answers": (
                "How do line-level mean VAD and concreteness ratings change through "
                "the poem for each source and token scope?"
            ),
            "start_with": (
                "lexicon, analysis_view, line_number, the four means, and their "
                "matched-observation counts."
            ),
            "important_caution": (
                "VAD sources remain separate; concreteness is normalized from 1-5 "
                "to 0-1 only for overlay display, and missing lines remain missing."
            ),
        },
        {
            "file": "poetry_id_summary.csv",
            "what_it_answers": (
                "Which source-, view-, and weighting-specific PoetryID "
                "candidate profile is reported?"
            ),
            "start_with": (
                "continuous VAD, categorical and nearest-centroid profiles, "
                "confidence, boundary dimensions, and coverage."
            ),
            "important_caution": (
                "A PoetryID label is a nearest candidate lexical-affective "
                "profile, not the poem's emotion."
            ),
        },
        {
            "file": "inherited_form_summary.csv",
            "what_it_answers": (
                "Which inherited form is the leading potential match, and how "
                "strong and well-covered is the evidence?"
            ),
            "start_with": (
                "best candidate, classification, consistency, evidence coverage, "
                "confidence, nearest alternative, and traditional definition."
            ),
            "important_caution": (
                "A potential match and confidence band are rule-based evidence, "
                "not a probability or definitive genre identity."
            ),
        },
        {
            "file": "inherited_form_features.csv",
            "what_it_answers": (
                "How did each expected form feature agree with the observed poem?"
            ),
            "start_with": (
                "profile, role, weight, expected, detected, score, coverage, "
                "and source modules."
            ),
            "important_caution": (
                "Unavailable dependent evidence remains missing and lowers "
                "coverage; it is not scored as zero."
            ),
        },
        {
            "file": "inherited_form_profiles.csv",
            "what_it_answers": (
                "What traditional definition, sources, and limitations define "
                "each of the ten versioned profiles?"
            ),
            "start_with": (
                "profile name, tradition, definition, source URLs, and limitations."
            ),
            "important_caution": (
                "The profiles describe documented conventions with historical "
                "and artistic variation."
            ),
        },
        {
            "file": "poetry_id_neighbors.csv",
            "what_it_answers": (
                "How far is the work from every one of the 27 profile centroids?"
            ),
            "start_with": "rank, distance, and relative_affinity.",
            "important_caution": (
                "Inverse-distance relative affinities are not probabilities."
            ),
        },
        {
            "file": "poetry_id_lexical_character.csv",
            "what_it_answers": (
                "What optional concreteness, frequency, and AoA character "
                "accompanies the VAD result?"
            ),
            "start_with": "dimension, weighting, mean, coverage, and orientation.",
            "important_caution": (
                "Secondary lexical character never changes the VAD archetype."
            ),
        },
        {
            "file": "poetry_id_methodology.csv",
            "what_it_answers": (
                "Which thresholds, centroids, distance rule, evidence minimums, "
                "and configuration produced PoetryID?"
            ),
            "start_with": "method, threshold_profile, threshold, and centroid rows.",
            "important_caution": (
                "Version 1 supports fixed and custom-fixed thresholds only."
            ),
        },
        {
            "file": "poetry_id_archetype_map.csv",
            "what_it_answers": (
                "What are all 27 canonical VAD combinations and their centroids?"
            ),
            "start_with": "levels, centroid coordinates, descriptor, and caution.",
            "important_caution": (
                "Names are interpretive labels for normative lexical neighborhoods."
            ),
        },
        {
            "file": "poetry_id_vad_scales.csv",
            "what_it_answers": (
                "What chart-ready score and boundary values appear on each VAD scale?"
            ),
            "start_with": "dimension, score, level, low_max, and high_min.",
            "important_caution": (
                "Scores remain source-, view-, and weighting-specific."
            ),
        },
        {
            "file": "concreteness_summary.csv",
            "what_it_answers": "What is the matched normative lexical concreteness profile?",
            "start_with": "mean, median, dispersion, rated-token coverage, and rated unique-word coverage.",
            "important_caution": "The 1-5 ratings describe source norms; they do not measure imagery success, readability, quality, intelligence, or comprehension.",
        },
        {
            "file": "concreteness_by_structure.csv",
            "what_it_answers": "How do rated-token summaries vary by physical line and stanza?",
            "start_with": "scope, ordinal, token_coverage, mean, and median.",
            "important_caution": "Missing line or stanza aggregates mean that no eligible tokens were rated there; they are not zero.",
        },
        {
            "file": "concreteness_by_pos.csv",
            "what_it_answers": "How do normative ratings and coverage vary by model-generated part-of-speech tag?",
            "start_with": "label, rated_token_count, token_coverage, mean, and median.",
            "important_caution": "Part-of-speech labels are model outputs and may be uncertain in poetic language.",
        },
        {
            "file": "concreteness_terms.csv",
            "what_it_answers": "Which matched source terms have the highest and lowest ratings?",
            "start_with": "rating, rated_token_occurrences, and the two rank columns.",
            "important_caution": "Rankings concern matched normative source ratings, not contextual interpretation.",
        },
        {
            "file": "concreteness_token_audit.csv",
            "what_it_answers": "How was every token included, matched, excluded, or left unmatched?",
            "start_with": "surface_form, match_method, matched_source_term, rating, and reason.",
            "important_caution": "Phrase components share a match_group_id; unmatched and ineligible rows carry no rating.",
        },
        {
            "file": "frequency_summary.csv",
            "what_it_answers": "What is the poem's corpus-relative lexical-frequency profile?",
            "start_with": "median Zipf, matched-token coverage, analysis scope, mean, and dispersion.",
            "important_caution": "SUBTLEX-US Zipf values describe an American subtitle corpus; they do not measure difficulty, sophistication, accessibility, or quality.",
        },
        {
            "file": "frequency_distribution.csv",
            "what_it_answers": "How do matched tokens fall into the configured Zipf orientation bands?",
            "start_with": "label, bounds, token_count, and proportion.",
            "important_caution": "These configurable labels are interface aids, not universal linguistic categories.",
        },
        {
            "file": "frequency_by_structure.csv",
            "what_it_answers": "How do median and mean Zipf values vary by physical line and stanza?",
            "start_with": "scope, ordinal, token_coverage, median_zipf, and mean_zipf.",
            "important_caution": "Missing structural aggregates mean no eligible word matched there; they are not Zipf zero.",
        },
        {
            "file": "frequency_by_pos.csv",
            "what_it_answers": "How do Zipf values and coverage vary by poem-specific model POS tag?",
            "start_with": "label, matched_token_count, token_coverage, and median_zipf.",
            "important_caution": "POS labels are model outputs; the optional content-word scope is limited to NOUN, VERB, ADJ, and ADV.",
        },
        {
            "file": "frequency_terms.csv",
            "what_it_answers": "Which represented source terms are least and most frequent?",
            "start_with": "zipf_value, matched_token_occurrences, lowest_frequency_rank, and rare_tail_rank.",
            "important_caution": "Low frequency is corpus-relative and does not imply difficulty or literary merit.",
        },
        {
            "file": "frequency_token_audit.csv",
            "what_it_answers": "How was every token included, matched, excluded, or left unmatched?",
            "start_with": "surface_form, part_of_speech, eligible, match_method, matched_source_term, and zipf_value.",
            "important_caution": "Lemma fallbacks are explicit; unmatched and ineligible rows carry no Zipf value.",
        },
        {
            "file": "aoa_summary.csv",
            "what_it_answers": "What is the poem's matched retrospective normative AoA profile?",
            "start_with": "mean and median source age, coverage, response evidence, and the non-diagnostic warning.",
            "important_caution": "AoA is not difficulty, grade level, intelligence, familiarity, or a diagnostic measure.",
        },
        {
            "file": "aoa_distribution.csv",
            "what_it_answers": "How do matched tokens fall into configured early, middle, and later orientation bands?",
            "start_with": "label, bounds, token_count, and proportion.",
            "important_caution": "These thresholds are VerseVAD orientation aids, not categories validated by the source paper.",
        },
        {
            "file": "aoa_by_structure.csv",
            "what_it_answers": "How do matched AoA means and medians vary by physical line and stanza?",
            "start_with": "scope, ordinal, token_coverage, mean_normative_aoa, and median_normative_aoa.",
            "important_caution": "Missing structural aggregates mean no eligible word had a numeric rating; they are not zero.",
        },
        {
            "file": "aoa_by_pos.csv",
            "what_it_answers": "How do AoA values and coverage vary by poem-specific model POS tag?",
            "start_with": "label, matched_token_count, token_coverage, and mean_normative_aoa.",
            "important_caution": "The optional content-word scope uses contextual model tags; source sampling is a separate matter.",
        },
        {
            "file": "aoa_terms.csv",
            "what_it_answers": "Which represented source terms have the earliest and latest normative mean ages?",
            "start_with": "mean_age, source_rating_standard_deviation, source_numeric_response_count, and rank columns.",
            "important_caution": "Source response evidence and term rankings do not establish contextual difficulty or reader experience.",
        },
        {
            "file": "aoa_relationships.csv",
            "what_it_answers": "What descriptive type-level relationships exist with enabled frequency or concreteness modules?",
            "start_with": "pair_count, coefficient, method, weighting, and note.",
            "important_caution": "Coefficients are descriptive, repeated occurrences are collapsed, and association is not causation.",
        },
        {
            "file": "aoa_token_audit.csv",
            "what_it_answers": "How was every token included, matched, excluded, source-unrated, or left unmatched?",
            "start_with": "surface_form, part_of_speech, match_method, mean_age, response count, and reason.",
            "important_caution": "Lemma fallbacks are explicit; unmatched, source-unrated, and ineligible rows carry no mean age.",
        },
        {
            "file": "lexical_style_summary.csv",
            "what_it_answers": (
                "What are the text-level lexical-diversity, character-length, "
                "line-word-count, and stanza-word-count summaries?"
            ),
            "start_with": (
                "lexical token/type counts, MATTR, HD-D, MTLD, word-length "
                "statistics, and line/stanza medians."
            ),
            "important_caution": (
                "Compare diversity values only with the same token policy and "
                "configuration; short poems can yield unstable or unavailable values."
            ),
        },
        {
            "file": "lexical_style_word_lengths.csv",
            "what_it_answers": (
                "How are represented lexical-token surfaces distributed by "
                "alphabetic-character length?"
            ),
            "start_with": (
                "alphabetic_character_count, token_count, token_proportion, "
                "and denominator."
            ),
            "important_caution": (
                "Lengths count Unicode alphabetic characters, not syllables, bytes, "
                "or punctuation marks."
            ),
        },
        {
            "file": "lexical_style_lines.csv",
            "what_it_answers": (
                "How many lexical tokens and normalized surface types occur on "
                "each preserved physical line?"
            ),
            "start_with": (
                "ordinal, source_text, is_blank, word_count, type count, and "
                "mean word length."
            ),
            "important_caution": (
                "Blank structural separator lines remain visible with word count "
                "zero rather than being removed."
            ),
        },
        {
            "file": "lexical_style_stanzas.csv",
            "what_it_answers": (
                "How many lexical tokens and normalized surface types occur in "
                "each preserved stanza?"
            ),
            "start_with": (
                "ordinal, line_count, word_count, type count, and mean word length."
            ),
            "important_caution": (
                "Counts use the shared preprocessing token unit and should not be "
                "silently equated with an editor's orthographic word policy."
            ),
        },
        {
            "file": "lexical_style_token_audit.csv",
            "what_it_answers": (
                "Which tokens entered diversity, word-length, line, and stanza counts?"
            ),
            "start_with": (
                "surface_form, normalized_surface_type, line/stanza, included, "
                "alphabetic_character_count, and reason."
            ),
            "important_caution": (
                "Lemmas remain separate evidence and never replace observed "
                "surface types in this module."
            ),
        },
        {
            "file": "pronunciation_summary.csv",
            "what_it_answers": "What dictionary-based syllable, lexical-stress, and coverage summaries are available?",
            "start_with": "resolved-token coverage, complete-line coverage, syllables per word and line, and stress density.",
            "important_caution": "CMUdict reflects North American dictionary pronunciations; the results are not meter, rhyme, or performed scansion.",
        },
        {
            "file": "pronunciation_lines.csv",
            "what_it_answers": "Which physical lines have complete dictionary syllable and lexical-stress evidence?",
            "start_with": "source_text, resolution_coverage, is_complete, syllable_count, and lexical_stress_sequence.",
            "important_caution": "Incomplete lines keep totals and sequences missing rather than deceptively low.",
        },
        {
            "file": "pronunciation_types.csv",
            "what_it_answers": "Which observed word forms resolve, remain ambiguous, or require correction?",
            "start_with": "lookup_form, statuses, dictionary_candidate_count, candidate_phones, and resolved fields.",
            "important_caution": "Observed forms are not silently replaced by lemmas or possessive bases.",
        },
        {
            "file": "pronunciation_token_audit.csv",
            "what_it_answers": "What pronunciation candidates and decisions apply to every token occurrence?",
            "start_with": "surface_form, status, candidate phones/stresses/syllables, resolved fields, and reason.",
            "important_caution": "Confidence labels are categorical source-resolution descriptions, not calibrated probabilities.",
        },
        {
            "file": "meter_summary.csv",
            "what_it_answers": "What fixed line template is nearest under the configured alignment method?",
            "start_with": "candidate label, pattern, foot count, mean fit, matching-line proportion, confidence, and coverage.",
            "important_caution": "Fit and confidence are configured descriptive evidence, not probabilities or definitive scansion.",
        },
        {
            "file": "meter_candidates.csv",
            "what_it_answers": "How do all 40 fixed pattern-by-foot-count templates compare across analyzable lines?",
            "start_with": "rank, pattern, foot_count_name, mean_fit, variability, and matching_line_proportion.",
            "important_caution": "Spondees and pyrrhics are local substitution labels, not additional whole-line base templates.",
        },
        {
            "file": "meter_lines.csv",
            "what_it_answers": "What candidate, stress path, fit, and deviations were selected for each physical line?",
            "start_with": "status, closest_candidate, selected_stress_sequence, templates, fit_score, and deviation counts.",
            "important_caution": "A line with missing pronunciation evidence remains unscored rather than receiving a partial or neutral fit.",
        },
        {
            "file": "meter_alignment_operations.csv",
            "what_it_answers": "Which syllable-to-template operations produced each selected line fit?",
            "start_with": "line, operation number, stresses, cost, word, POS, and ending flags.",
            "important_caution": "Function-word flexibility and secondary stress use explicit configured costs; the alignment is not performed rhythm.",
        },
        {
            "file": "meter_realizations.csv",
            "what_it_answers": "How does the optional performance-aware layer rerank primary and alternate line readings?",
            "start_with": "raw lexical stress, candidate template, realized scansion, separate component scores, substitutions, and pronunciation path.",
            "important_caution": "Realizations depend on a declared broad profile and rule-based contextual evidence; they are not mandatory performances.",
        },
        {
            "file": "meter_stanzas.csv",
            "what_it_answers": "Which candidate recurrences and exceptions appear within each preserved stanza?",
            "start_with": "primary candidate, alternate candidate, line-position sequence, regularity, and exceptions.",
            "important_caution": "A recurring sequence is reported generically; no named stanza form is assigned.",
        },
        {
            "file": "meter_rhythm_trajectory.csv",
            "what_it_answers": "How do realized score, syllable count, beats, substitutions, and caesura evidence vary by line?",
            "start_with": "line number, stanza, candidate, realized score, syllables, beats, and substitutions.",
            "important_caution": "The trajectory is descriptive textual evidence, not a recording of performed timing.",
        },
        {
            "file": "meter_scholar_revisions.csv",
            "what_it_answers": "How does an optional scholar-supplied reading differ from the retained automatic reading?",
            "start_with": "line, automatic candidate/scansion, revised candidate/scansion, and required scholar note.",
            "important_caution": "This conditional file keeps the two readings separate; a revision never overwrites source lexical stress or the automatic result.",
        },
        {
            "file": "rhyme_summary.csv",
            "what_it_answers": "What are the principal end-rhyme, coverage, internal-rhyme, refrain, and recurring-sound results?",
            "start_with": "whole-poem scheme, rhyme density, ending coverage, pair counts, and sound densities.",
            "important_caution": "Schemes use robust perfect/identical dictionary rhyme parts; slant and eye evidence remain separate.",
        },
        {
            "file": "rhyme_stanzas.csv",
            "what_it_answers": "How do rhyme scheme, coverage, and density vary by stanza?",
            "start_with": "stanza number, eligible and analyzable endings, scheme, pair counts, and rhyme density.",
            "important_caution": "Unresolved endings are marked ? rather than assigned a rhyme or neutral score.",
        },
        {
            "file": "rhyme_lines.csv",
            "what_it_answers": "What end-word, pronunciation, rhyme-group, refrain, and recurring-sound evidence applies to each physical line?",
            "start_with": "status, ending word, candidate phones, rhyme parts, scheme label, sound sequences, and densities.",
            "important_caution": "Materially different pronunciation alternatives remain ambiguous unless a scholar override resolves them.",
        },
        {
            "file": "rhyme_pairs.csv",
            "what_it_answers": "Which within-stanza ending pairs show perfect, identical, graded slant, or eye-rhyme evidence?",
            "start_with": "relationship, rhyme types, similarity components, eye-rhyme flag, confidence label, and note.",
            "important_caution": "The graded slant score is a configured heuristic, not a probability or definitive performance judgment.",
        },
        {
            "file": "rhyme_internal.csv",
            "what_it_answers": "Which exact dictionary rhyme parts recur within a physical line?",
            "start_with": "line, paired words, rhyme part, and relationship.",
            "important_caution": "These are phonological word-pair observations, not claims about intentional sound patterning.",
        },
        {
            "file": "phonological_sounds.csv",
            "what_it_answers": "Which initial consonants, stressed vowels, and consonants recur most strongly?",
            "start_with": "category, phoneme, occurrence count, line count, and within-category share.",
            "important_caution": "Counts derive from retained dictionary pronunciations rather than a recorded reading.",
        },
        {
            "file": "phase2_coverage.csv",
            "what_it_answers": "How much vocabulary matched each source?",
            "start_with": "lexical_token_coverage and matched_token_count.",
            "important_caution": "Coverage differs by lexicon and matching policy.",
        },
        {
            "file": "phase2_vad_summary.csv",
            "what_it_answers": "What are the VAD distributions?",
            "start_with": "token weighting plus normalized_0_1 scale.",
            "important_caution": "Source and normalized scales are separate; unmatched tokens are absent.",
        },
        {
            "file": "vad_by_part_of_speech.csv",
            "what_it_answers": "How do matched normative VAD means vary across model-assigned broad part-of-speech groups?",
            "start_with": "lexicon, analysis view, POS, coverage, then token- and type-weighted normalized means.",
            "important_caution": "Sources and analysis views remain separate; missing matches are not neutral, and cross-POS phrases remain in a mixed-POS row.",
        },
        {
            "file": "phase2_emotion_associations.csv",
            "what_it_answers": "Which categorical associations occur?",
            "start_with": "proportion_of_lexical_tokens and top_contributing_terms.",
            "important_caution": "A token may have several associations; rates need not sum to 100%.",
        },
        {
            "file": "phase2_emotion_intensity.csv",
            "what_it_answers": "How prevalent and intense are supplied category pairs?",
            "start_with": "prevalence_among_lexical_tokens and token_mean.",
            "important_caution": "Missing category pairs are not zero intensity.",
        },
        {
            "file": "phase2_match_audit.csv",
            "what_it_answers": "Which exact evidence produced each result?",
            "start_with": "surface_span, lexicon_id, selection, matched_term, and reason.",
            "important_caution": "Suppressed rows are audit candidates, not included observations.",
        },
        {
            "file": "phase2_cross_lexicon_comparison.csv",
            "what_it_answers": "How do independent source-specific metrics compare?",
            "start_with": "metric, scale, denominator, and value.",
            "important_caution": "There is deliberately no consensus score.",
        },
        {
            "file": "phase2_manifest.csv",
            "what_it_answers": "Can this analysis be reproduced?",
            "start_with": "text/source hashes, versions, model, scenario, phrase policy, and stopword-list metadata.",
            "important_caution": "This is provenance rather than a results table; reviewed runs also list exact decision revisions.",
        },
    ]
    rows.extend(
        (
            {
                "file": "VerseVAD_analysis_report.docx",
                "what_it_answers": (
                    "What are the principal results in a readable narrative?"
                ),
                "start_with": (
                    "Scope and interpretation, key findings, coverage and cautions."
                ),
                "important_caution": (
                    "The Word report is an orientation; retain the companion CSV "
                    "files for complete values and audit evidence."
                ),
            },
            {
                "file": "*_report.docx",
                "what_it_answers": (
                    "What does each optional analysis report in plain language?"
                ),
                "start_with": (
                    "The module-specific scope, findings, denominators, and cautions."
                ),
                "important_caution": (
                    "Narrative reports do not replace their module CSV files."
                ),
            },
            {
                "file": "*_manifest.csv",
                "what_it_answers": (
                    "Which exact module configuration, provenance, resource "
                    "identity, coverage records, and warnings supported the result?"
                ),
                "start_with": "path and value.",
                "important_caution": (
                    "Manifest rows are reproducibility evidence; interpretive "
                    "results remain in the summary and audit CSV files."
                ),
            },
            {
                "file": "processing_*.csv",
                "what_it_answers": (
                    "What exact text, structure, annotations, configuration, "
                    "coverage, and warnings supported the analyses?"
                ),
                "start_with": (
                    "processing_source.csv, processing_tokens.csv, and "
                    "processing_configuration.csv."
                ),
                "important_caution": (
                    "POS, lemma, sentence, dependency, and optional entity records "
                    "are model outputs, not corrected ground truth."
                ),
            },
        )
    )
    return _csv_bytes(fields, rows)


def _build_detailed_export_zip(workspace: WorkspaceAnalysis) -> bytes:
    """Create the complete audit bundle temporarily and return an in-memory ZIP."""

    with TemporaryDirectory(prefix="versevad-export-") as temporary:
        directory = Path(temporary)
        paths = (
            export_phase2_csv(workspace.results, workspace.comparison, directory)
            if workspace.results
            else ()
        )
        export_files = {
            path.name: path.read_bytes()
            for path in paths
        }
        title = workspace.document.title
        optional_results = (
            (workspace.vader_sentiment, export_vader_sentiment_bundle),
            (workspace.readability, export_readability_bundle),
            (workspace.concreteness, export_concreteness_bundle),
            (workspace.frequency, export_frequency_bundle),
            (workspace.aoa, export_aoa_bundle),
            (workspace.pronunciation, export_pronunciation_bundle),
            (workspace.meter, export_meter_bundle),
            (workspace.phonology, export_phonological_bundle),
            (workspace.lexical_style, export_lexical_style_bundle),
            (workspace.poetry_id, export_poetry_id_bundle),
            (workspace.inherited_form, export_inherited_form_bundle),
        )
        for result, exporter in optional_results:
            if result is not None:
                export_files.update(exporter(result, text_title=title))
        if workspace.poem_document is not None:
            export_files.update(
                export_poem_document_csv_bundle(workspace.poem_document)
            )
        if vad_part_of_speech_views(workspace):
            export_files["vad_by_part_of_speech.csv"] = (
                vad_part_of_speech_csv(workspace)
            )
        if any(result.vad_summary is not None for result in workspace.results):
            export_files["lexical_trajectory.csv"] = lexical_trajectory_csv(
                workspace
            )
        summary_csv = scholar_summary_csv(workspace)
        export_files["scholar_summary.csv"] = summary_csv
        export_files["csv_reading_guide.csv"] = csv_reading_guide()
        warning_messages = [
            warning
            for result in workspace.results
            for warning in result.warnings
        ]
        for optional_result in (
            workspace.vader_sentiment,
            workspace.readability,
            workspace.concreteness,
            workspace.frequency,
            workspace.aoa,
            workspace.pronunciation,
            workspace.meter,
            workspace.phonology,
            workspace.lexical_style,
            workspace.poetry_id,
            workspace.inherited_form,
        ):
            if optional_result is not None:
                warning_messages.extend(
                    warning.message
                    for warning in optional_result.module_result.warnings
                )
        if workspace.poem_document is not None:
            warning_messages.extend(
                warning.message for warning in workspace.poem_document.warnings
            )
        export_files["VerseVAD_analysis_report.docx"] = (
            build_narrative_report_from_summary_csv(
                "phase2",
                summary_csv,
                companion_csv_files=tuple(
                    name
                    for name in export_files
                    if name.endswith(".csv")
                ),
                text_title=workspace.document.title,
                text_id=workspace.document.text_id,
                result_id=workspace.document.text_version_id,
                warnings=tuple(dict.fromkeys(warning_messages)),
            )
        )
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for filename, content in export_files.items():
                bundle.writestr(filename, content)
        return archive.getvalue()


def detailed_export_zip(
    workspace: WorkspaceAnalysis,
    *,
    use_cache: bool = True,
) -> bytes:
    """Return a bounded cached export for an immutable completed analysis."""

    key = stable_fingerprint(
        __version__,
        "detailed_export_zip",
        workspace.document.text_version_id,
        workspace.document.text_sha256,
        tuple(result.analysis_id for result in workspace.results),
        workspace.comparison.comparison_id,
        _module_result_id(workspace.vader_sentiment),
        _module_result_id(workspace.readability),
        _module_result_id(workspace.concreteness),
        _module_result_id(workspace.frequency),
        _module_result_id(workspace.aoa),
        _module_result_id(workspace.pronunciation),
        _module_result_id(workspace.meter),
        _module_result_id(workspace.phonology),
        _module_result_id(workspace.lexical_style),
        _module_result_id(workspace.poetry_id),
        _module_result_id(workspace.inherited_form),
    )
    content, _lookup = EXPORT_CACHE.get_or_compute(
        key,
        lambda: _build_detailed_export_zip(workspace),
        enabled=use_cache,
        validator=lambda value: (
            isinstance(value, bytes)
            and value.startswith(b"PK")
        ),
    )
    return content
