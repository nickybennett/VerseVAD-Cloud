"""Immutable, poetry-preserving document records for shared analysis modules."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from versevad.models import PreprocessingMetadata, TextDocument, TokenRecord


DEFAULT_CONTENT_POS_TAGS = ("ADJ", "ADV", "INTJ", "NOUN", "PROPN", "VERB")
DEFAULT_FUNCTION_POS_TAGS = (
    "ADP",
    "AUX",
    "CCONJ",
    "DET",
    "PART",
    "PRON",
    "SCONJ",
)
DEFAULT_SHARED_RECIPE_ID = "versevad-default-preprocessing-v2"


class StructuralUnitKind(StrEnum):
    SECTION = "section"
    STANZA = "stanza"
    LINE = "line"


class TokenRole(StrEnum):
    CONTENT = "content"
    FUNCTION = "function"
    OTHER = "other"
    NON_LEXICAL = "non_lexical"


class ModelVocabularyState(StrEnum):
    IN_VOCABULARY = "in_vocabulary"
    OUT_OF_VOCABULARY = "out_of_vocabulary"
    UNAVAILABLE = "unavailable"


class OrthographicFeatureKind(StrEnum):
    HYPHENATED_EXPRESSION = "hyphenated_expression"
    CONTRACTION = "contraction"
    APOSTROPHE_FORM = "apostrophe_form"


class DocumentWarningSeverity(StrEnum):
    INFORMATION = "information"
    CAUTION = "caution"
    ERROR = "error"


@dataclass(frozen=True)
class PreprocessingConfiguration:
    """Versioned choices that create the processing representation."""

    recipe_id: str = DEFAULT_SHARED_RECIPE_ID
    unicode_normalization_form: str = "NFC"
    preserve_original_text: bool = True
    preserve_punctuation: bool = True
    merge_possessives: bool = True
    enable_ner: bool = False
    content_pos_tags: tuple[str, ...] = DEFAULT_CONTENT_POS_TAGS
    function_pos_tags: tuple[str, ...] = DEFAULT_FUNCTION_POS_TAGS
    hyphenated_word_policy: str = "preserve_components_and_record_span"
    contraction_policy: str = "preserve_model_tokens_and_record_span"
    apostrophe_policy: str = "preserve_surface_and_record_span"

    def __post_init__(self) -> None:
        if not self.recipe_id.strip():
            raise ValueError("A preprocessing recipe must have a stable ID.")
        if self.unicode_normalization_form != "NFC":
            raise ValueError(
                "Stage 1 supports NFC lookup normalization only; original text "
                "always remains unchanged."
            )
        if not self.preserve_original_text:
            raise ValueError("VerseVAD must preserve the original text.")
        if not self.preserve_punctuation:
            raise ValueError("VerseVAD must preserve punctuation.")
        overlap = set(self.content_pos_tags) & set(self.function_pos_tags)
        if overlap:
            raise ValueError(
                "Content-word and function-word POS sets cannot overlap: "
                + ", ".join(sorted(overlap))
            )

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"{self.recipe_id}:{digest}"


@dataclass(frozen=True)
class StructuralUnit:
    unit_id: str
    text_id: str
    text_version_id: str
    kind: StructuralUnitKind
    ordinal: int
    parent_id: str
    character_start: int
    character_end: int
    raw_text: str
    content_text: str
    line_ending: str = ""
    indentation: str = ""
    is_blank: bool = False

    def __post_init__(self) -> None:
        if not self.unit_id or self.ordinal < 1:
            raise ValueError("A structural unit requires a stable ID and ordinal.")
        if self.character_start < 0 or self.character_end < self.character_start:
            raise ValueError("A structural unit has invalid character offsets.")
        if self.kind is StructuralUnitKind.LINE:
            if self.raw_text != self.content_text + self.line_ending:
                raise ValueError(
                    "A line's content and line ending must reconstruct its raw text."
                )
            if self.is_blank != (not self.content_text.strip()):
                raise ValueError("A line's blank status must match its content.")


@dataclass(frozen=True)
class SentenceUnit:
    sentence_id: str
    text_id: str
    text_version_id: str
    ordinal: int
    character_start: int
    character_end: int
    raw_text: str
    token_ids: tuple[str, ...]
    line_numbers: tuple[int, ...]
    stanza_numbers: tuple[int, ...]
    crosses_line_boundary: bool
    crosses_stanza_boundary: bool


@dataclass(frozen=True)
class DependencyRecord:
    token_id: str
    head_token_id: str | None
    dependency_label: str
    sentence_id: str
    crosses_line_boundary: bool
    crosses_stanza_boundary: bool
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and (
            not math.isfinite(self.confidence)
            or self.confidence < 0
            or self.confidence > 1
        ):
            raise ValueError("Dependency confidence must be between zero and one.")


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    label: str
    character_start: int
    character_end: int
    raw_text: str
    token_ids: tuple[str, ...]
    line_numbers: tuple[int, ...]
    stanza_numbers: tuple[int, ...]


@dataclass(frozen=True)
class OrthographicSpan:
    span_id: str
    kind: OrthographicFeatureKind
    character_start: int
    character_end: int
    raw_text: str
    token_ids: tuple[str, ...]
    line_number: int
    stanza_number: int


@dataclass(frozen=True)
class TokenClassification:
    token_id: str
    role: TokenRole
    is_hyphenated_component: bool
    is_contraction_component: bool
    has_apostrophe: bool
    model_vocabulary_state: ModelVocabularyState


@dataclass(frozen=True)
class DocumentWarning:
    code: str
    message: str
    severity: DocumentWarningSeverity = DocumentWarningSeverity.CAUTION
    technical_detail: str = ""


@dataclass(frozen=True)
class ProcessingCoverage:
    total_token_count: int
    lexical_token_count: int
    sentence_count: int
    tokens_with_sentence_count: int
    sentence_annotation_rate: float | None
    dependency_record_count: int
    dependency_annotation_rate: float | None
    entity_count: int
    model_vocabulary_available: bool
    model_oov_count: int | None
    model_oov_rate: float | None

    def __post_init__(self) -> None:
        counts = (
            self.total_token_count,
            self.lexical_token_count,
            self.sentence_count,
            self.tokens_with_sentence_count,
            self.dependency_record_count,
            self.entity_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("Processing coverage counts cannot be negative.")
        if self.lexical_token_count > self.total_token_count:
            raise ValueError("Lexical tokens cannot exceed total tokens.")
        if self.tokens_with_sentence_count > self.total_token_count:
            raise ValueError("Sentence-annotated tokens cannot exceed total tokens.")
        if self.dependency_record_count > self.total_token_count:
            raise ValueError("Dependency records cannot exceed total tokens.")
        expected_sentence_rate = (
            self.tokens_with_sentence_count / self.total_token_count
            if self.total_token_count
            else None
        )
        expected_dependency_rate = (
            self.dependency_record_count / self.total_token_count
            if self.total_token_count
            else None
        )
        if self.sentence_annotation_rate != expected_sentence_rate:
            raise ValueError("Sentence coverage must agree with its counts.")
        if self.dependency_annotation_rate != expected_dependency_rate:
            raise ValueError("Dependency coverage must agree with its counts.")
        if not self.model_vocabulary_available:
            if self.model_oov_count is not None or self.model_oov_rate is not None:
                raise ValueError(
                    "OOV coverage must remain missing when model vocabulary is "
                    "unavailable."
                )
        else:
            if self.model_oov_count is None:
                raise ValueError(
                    "Available model vocabulary requires an explicit OOV count."
                )
            if self.model_oov_count < 0 or self.model_oov_count > self.lexical_token_count:
                raise ValueError("The model OOV count is outside its denominator.")
            expected_oov_rate = (
                self.model_oov_count / self.lexical_token_count
                if self.lexical_token_count
                else None
            )
            if self.model_oov_rate != expected_oov_rate:
                raise ValueError("Model OOV coverage must agree with its counts.")


@dataclass(frozen=True)
class PoemDocument:
    """Exact source text plus a separate, traceable processing representation."""

    source: TextDocument
    configuration: PreprocessingConfiguration
    preprocessing: PreprocessingMetadata
    structural_units: tuple[StructuralUnit, ...]
    sentences: tuple[SentenceUnit, ...]
    tokens: tuple[TokenRecord, ...]
    dependencies: tuple[DependencyRecord, ...]
    entities: tuple[EntityRecord, ...]
    orthographic_spans: tuple[OrthographicSpan, ...]
    token_classifications: tuple[TokenClassification, ...]
    coverage: ProcessingCoverage
    warnings: tuple[DocumentWarning, ...]

    def __post_init__(self) -> None:
        sections = [
            unit
            for unit in self.structural_units
            if unit.kind is StructuralUnitKind.SECTION
        ]
        if len(sections) != 1 or sections[0].raw_text != self.source.original_text:
            raise ValueError(
                "A poem document requires one section containing the exact source text."
            )
        if any(
            unit.raw_text
            != self.source.original_text[unit.character_start : unit.character_end]
            for unit in self.structural_units
        ):
            raise ValueError(
                "Every structural unit must point to its exact source-text substring."
            )
        structural_ids = {unit.unit_id for unit in self.structural_units}
        if len(structural_ids) != len(self.structural_units):
            raise ValueError("Structural-unit IDs must be unique.")
        if any(
            unit.parent_id and unit.parent_id not in structural_ids
            for unit in self.structural_units
        ):
            raise ValueError("Structural-unit parents must exist in the poem.")
        if "".join(line.raw_text for line in self.lines) != self.source.original_text:
            raise ValueError("Physical line records must reconstruct the source text.")
        token_ids = {token.token_id for token in self.tokens}
        if len(token_ids) != len(self.tokens):
            raise ValueError("Token IDs must be unique within a poem document.")
        if any(
            token.text_id != self.source.text_id
            or token.text_version_id != self.source.text_version_id
            for token in self.tokens
        ):
            raise ValueError("Every token must belong to the poem's source version.")
        classification_ids = {
            classification.token_id for classification in self.token_classifications
        }
        if classification_ids != token_ids:
            raise ValueError("Every token requires exactly one classification.")
        if len(classification_ids) != len(self.token_classifications):
            raise ValueError("Token classifications cannot contain duplicate IDs.")
        if any(
            dependency.token_id not in token_ids
            or (
                dependency.head_token_id is not None
                and dependency.head_token_id not in token_ids
            )
            for dependency in self.dependencies
        ):
            raise ValueError("Dependency records must reference tokens in the poem.")
        if any(
            token_id not in token_ids
            for entity in self.entities
            for token_id in entity.token_ids
        ):
            raise ValueError("Entity records must reference tokens in the poem.")
        if any(
            sentence.raw_text
            != self.source.original_text[
                sentence.character_start : sentence.character_end
            ]
            for sentence in self.sentences
        ):
            raise ValueError("Sentence units must retain exact source substrings.")
        if any(
            entity.raw_text
            != self.source.original_text[
                entity.character_start : entity.character_end
            ]
            for entity in self.entities
        ):
            raise ValueError("Entity records must retain exact source substrings.")
        if any(
            span.raw_text
            != self.source.original_text[span.character_start : span.character_end]
            for span in self.orthographic_spans
        ):
            raise ValueError(
                "Orthographic spans must retain exact source substrings."
            )
        if (
            self.coverage.total_token_count != len(self.tokens)
            or self.coverage.lexical_token_count
            != sum(token.is_lexical for token in self.tokens)
            or self.coverage.sentence_count != len(self.sentences)
            or self.coverage.dependency_record_count != len(self.dependencies)
            or self.coverage.entity_count != len(self.entities)
        ):
            raise ValueError(
                "Processing coverage must agree with the poem document records."
            )

    @property
    def section(self) -> StructuralUnit:
        return next(
            unit
            for unit in self.structural_units
            if unit.kind is StructuralUnitKind.SECTION
        )

    @property
    def stanzas(self) -> tuple[StructuralUnit, ...]:
        return tuple(
            unit
            for unit in self.structural_units
            if unit.kind is StructuralUnitKind.STANZA
        )

    @property
    def lines(self) -> tuple[StructuralUnit, ...]:
        return tuple(
            unit
            for unit in self.structural_units
            if unit.kind is StructuralUnitKind.LINE
        )

    def classification_map(self) -> Mapping[str, TokenClassification]:
        return MappingProxyType(
            {
                classification.token_id: classification
                for classification in self.token_classifications
            }
        )
