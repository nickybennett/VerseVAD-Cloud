"""Poetry-preserving, POS-sensitive linguistic preprocessing."""

from __future__ import annotations

import bisect
import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

from versevad.core.documents import (
    DEFAULT_SHARED_RECIPE_ID,
    DependencyRecord,
    DocumentWarning,
    DocumentWarningSeverity,
    EntityRecord,
    ModelVocabularyState,
    OrthographicFeatureKind,
    OrthographicSpan,
    PoemDocument,
    PreprocessingConfiguration,
    ProcessingCoverage,
    SentenceUnit,
    StructuralUnit,
    StructuralUnitKind,
    TokenClassification,
    TokenRole,
)
from versevad.models import PreprocessingMetadata, TextDocument, TokenRecord
from versevad.normalization import normalize_lookup, strip_edge_punctuation


DEFAULT_RECIPE_ID = DEFAULT_SHARED_RECIPE_ID
APOSTROPHE_CHARACTERS = frozenset({"'", "\u2018", "\u2019", "\u02bc", "\uff07"})
HYPHEN_CHARACTERS = frozenset({"-", "\u2010", "\u2011"})
# A zero-width tokenizer boundary around and within a run of at least two
# non-apostrophe punctuation marks joining alphabetic text.  This handles
# typography such as ``morrow;—vainly`` without changing contractions,
# apostrophe forms, abbreviations, or the preserved source text.
JOINED_PUNCTUATION_INFIX = (
    r"(?<=[^\W\d_])(?=[^\w\s'\u2019]{2})"
    r"|(?<=[^\w\s'\u2019])(?=[^\w\s'\u2019])"
    r"|(?<=[^\w\s'\u2019]{2})(?=[^\W\d_])"
)


class PreprocessingError(RuntimeError):
    """A plain-language preprocessing failure with optional technical detail."""

    def __init__(self, message: str, technical_detail: str = "") -> None:
        super().__init__(message)
        self.technical_detail = technical_detail


class TextPreprocessor(Protocol):
    @property
    def metadata(self) -> PreprocessingMetadata: ...

    def process(self, document: TextDocument) -> tuple[TokenRecord, ...]: ...

    def process_document(self, document: TextDocument) -> PoemDocument: ...


def create_text_document(text_id: str, title: str, original_text: str) -> TextDocument:
    """Create an immutable text-version identity without changing the text."""

    digest = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
    return TextDocument(
        text_id=text_id,
        title=title,
        original_text=original_text,
        text_sha256=digest,
        text_version_id=f"{text_id}:{digest[:16]}",
    )


@dataclass(frozen=True)
class _LineLocation:
    number: int
    stanza: int
    start: int
    end: int
    raw_text: str
    context: str
    line_ending: str
    indentation: str
    is_blank: bool


@dataclass(frozen=True)
class _AnalysisText:
    text: str
    original_character_offsets: tuple[int, ...]

    def original_span(self, start: int, end: int) -> tuple[int, int]:
        """Map a nonempty analysis-text span back to preserved source offsets."""

        if start < 0 or end < start or end > len(self.original_character_offsets):
            raise ValueError("Analysis-text span is outside the preserved source.")
        if start == end:
            if start < len(self.original_character_offsets):
                boundary = self.original_character_offsets[start]
            elif self.original_character_offsets:
                boundary = self.original_character_offsets[-1] + 1
            else:
                boundary = 0
            return boundary, boundary
        return (
            self.original_character_offsets[start],
            self.original_character_offsets[end - 1] + 1,
        )


def _line_ending(raw_line: str) -> str:
    if raw_line.endswith("\r\n"):
        return "\r\n"
    if raw_line.endswith(("\r", "\n")):
        return raw_line[-1]
    return ""


def _analysis_text_without_line_edge_whitespace(text: str) -> _AnalysisText:
    """Build the metric-evaluation view plus its source-offset mapping."""

    raw_lines = text.splitlines(keepends=True)
    if not raw_lines:
        raw_lines = [""]
    consumed = sum(len(line) for line in raw_lines)
    if consumed < len(text):
        raw_lines.append(text[consumed:])

    analysis_characters: list[str] = []
    original_offsets: list[int] = []
    source_offset = 0
    for raw_line in raw_lines:
        ending = _line_ending(raw_line)
        context = raw_line[: -len(ending)] if ending else raw_line
        leading_count = len(context) - len(context.lstrip())
        trailing_boundary = len(context.rstrip())
        if trailing_boundary < leading_count:
            trailing_boundary = leading_count

        for index in range(leading_count, trailing_boundary):
            analysis_characters.append(context[index])
            original_offsets.append(source_offset + index)
        for index, character in enumerate(ending, start=len(context)):
            analysis_characters.append(character)
            original_offsets.append(source_offset + index)
        source_offset += len(raw_line)

    return _AnalysisText(
        text="".join(analysis_characters),
        original_character_offsets=tuple(original_offsets),
    )


def strip_line_edge_whitespace(text: str) -> str:
    """Remove Unicode whitespace at physical-line edges for metric evaluation.

    VerseVAD preserves the supplied source text, offsets, line endings, and
    indentation in its audit record.  This helper provides the corresponding
    analysis-only view for the small number of modules that score raw strings
    directly.  Internal whitespace and every line break remain unchanged.
    """

    return _analysis_text_without_line_edge_whitespace(text).text


class _LineIndex:
    def __init__(self, text: str) -> None:
        raw_lines = text.splitlines(keepends=True)
        if not raw_lines:
            raw_lines = [""]
        if raw_lines and sum(len(line) for line in raw_lines) < len(text):
            raw_lines.append(text[sum(len(line) for line in raw_lines) :])

        locations: list[_LineLocation] = []
        starts: list[int] = []
        offset = 0
        stanza = 0
        inside_stanza = False
        for number, raw_line in enumerate(raw_lines, start=1):
            ending = _line_ending(raw_line)
            context = raw_line[: -len(ending)] if ending else raw_line
            if context.strip():
                if not inside_stanza:
                    stanza += 1
                inside_stanza = True
            else:
                inside_stanza = False
            line_stanza = stanza if context.strip() else 0
            # Capture all Unicode horizontal whitespace used as indentation,
            # including tabs and non-breaking/em/thin spaces.  The source is
            # retained verbatim; this field is audit metadata only.
            indentation_match = re.match(r"[^\S\r\n]*", context)
            starts.append(offset)
            locations.append(
                _LineLocation(
                    number=number,
                    stanza=line_stanza,
                    start=offset,
                    end=offset + len(raw_line),
                    raw_text=raw_line,
                    context=context,
                    line_ending=ending,
                    indentation=(
                        indentation_match.group(0) if indentation_match else ""
                    ),
                    is_blank=not context.strip(),
                )
            )
            offset += len(raw_line)

        self._starts = starts
        self._locations = locations

    @property
    def locations(self) -> tuple[_LineLocation, ...]:
        return tuple(self._locations)

    def locate(self, character_offset: int) -> _LineLocation:
        index = max(0, bisect.bisect_right(self._starts, character_offset) - 1)
        return self._locations[index]


@dataclass(frozen=True)
class PreparedPoemPreprocessor:
    """Reuse one completed processing representation across analysis modules."""

    poem_document: PoemDocument

    @property
    def metadata(self) -> PreprocessingMetadata:
        return self.poem_document.preprocessing

    def _validate(self, document: TextDocument) -> None:
        if document != self.poem_document.source:
            raise PreprocessingError(
                "The prepared processing representation belongs to a different "
                "text version. No analysis was run."
            )

    def process_document(self, document: TextDocument) -> PoemDocument:
        self._validate(document)
        return self.poem_document

    def process(self, document: TextDocument) -> tuple[TokenRecord, ...]:
        self._validate(document)
        return self.poem_document.tokens


class SpacyEnglishPreprocessor:
    """Use a pinned spaCy English pipeline while retaining poem structure."""

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        *,
        configuration: PreprocessingConfiguration | None = None,
    ) -> None:
        self._configuration = configuration or PreprocessingConfiguration()
        excluded = [] if self._configuration.enable_ner else ["ner"]
        try:
            import spacy
            from spacy.util import compile_infix_regex

            self._nlp = spacy.load(model_name, exclude=excluded)
            infixes = (JOINED_PUNCTUATION_INFIX,) + tuple(
                self._nlp.Defaults.infixes
            )
            self._nlp.tokenizer.infix_finditer = compile_infix_regex(
                infixes
            ).finditer
        except (ImportError, OSError) as error:
            raise PreprocessingError(
                "VerseVAD could not load its English linguistic model. "
                "No text was changed. Run the project setup again, then retry.",
                technical_detail=str(error),
            ) from error
        self._model_name = model_name

    @property
    def metadata(self) -> PreprocessingMetadata:
        return PreprocessingMetadata(
            recipe_id=self._configuration.recipe_id,
            pipeline_name=self._model_name,
            pipeline_version=str(self._nlp.meta.get("version", "unknown")),
            disabled_components=(
                ("ner",) if not self._configuration.enable_ner else ()
            ),
        )

    @property
    def configuration(self) -> PreprocessingConfiguration:
        return self._configuration

    def _merge_possessives(self, document: object) -> None:
        spans = []
        for token in document[:-1]:
            following = document[token.i + 1]
            touching = token.idx + len(token.text) == following.idx
            if (
                touching
                and following.text in {"'s", "\u2019s"}
                and following.pos_ == "PART"
                and token.pos_ in {"NOUN", "PROPN"}
            ):
                spans.append(document[token.i : token.i + 2])
        if not spans:
            return
        with document.retokenize() as retokenizer:
            for span in spans:
                head = span[0]
                retokenizer.merge(
                    span,
                    attrs={
                        "LEMMA": head.lemma_,
                        "POS": head.pos,
                        "TAG": head.tag,
                    },
                )

    @staticmethod
    def _structural_units(
        document: TextDocument, line_index: _LineIndex
    ) -> tuple[StructuralUnit, ...]:
        section_id = f"{document.text_version_id}:section:1"
        section = StructuralUnit(
            unit_id=section_id,
            text_id=document.text_id,
            text_version_id=document.text_version_id,
            kind=StructuralUnitKind.SECTION,
            ordinal=1,
            parent_id="",
            character_start=0,
            character_end=len(document.original_text),
            raw_text=document.original_text,
            content_text=document.original_text,
            is_blank=not document.original_text.strip(),
        )

        stanza_locations: dict[int, list[_LineLocation]] = {}
        for location in line_index.locations:
            if location.stanza:
                stanza_locations.setdefault(location.stanza, []).append(location)

        stanzas = []
        for stanza_number, locations in stanza_locations.items():
            start = locations[0].start
            end = locations[-1].end
            raw_text = document.original_text[start:end]
            stanzas.append(
                StructuralUnit(
                    unit_id=f"{document.text_version_id}:stanza:{stanza_number}",
                    text_id=document.text_id,
                    text_version_id=document.text_version_id,
                    kind=StructuralUnitKind.STANZA,
                    ordinal=stanza_number,
                    parent_id=section_id,
                    character_start=start,
                    character_end=end,
                    raw_text=raw_text,
                    content_text=raw_text,
                    is_blank=False,
                )
            )

        lines = []
        for location in line_index.locations:
            parent_id = (
                f"{document.text_version_id}:stanza:{location.stanza}"
                if location.stanza
                else section_id
            )
            lines.append(
                StructuralUnit(
                    unit_id=f"{document.text_version_id}:line:{location.number}",
                    text_id=document.text_id,
                    text_version_id=document.text_version_id,
                    kind=StructuralUnitKind.LINE,
                    ordinal=location.number,
                    parent_id=parent_id,
                    character_start=location.start,
                    character_end=location.end,
                    raw_text=location.raw_text,
                    content_text=location.context,
                    line_ending=location.line_ending,
                    indentation=location.indentation,
                    is_blank=location.is_blank,
                )
            )
        return (section, *stanzas, *lines)

    @staticmethod
    def _sentence_units(
        document: TextDocument,
        spacy_document: object,
        record_by_spacy_index: dict[int, TokenRecord],
        analysis_text: _AnalysisText,
    ) -> tuple[SentenceUnit, ...]:
        units = []
        try:
            sentences = tuple(spacy_document.sents)
        except ValueError:
            sentences = ()
        for sentence_number, sentence in enumerate(sentences, start=1):
            character_start, character_end = analysis_text.original_span(
                sentence.start_char,
                sentence.end_char,
            )
            records = tuple(
                record_by_spacy_index[token.i]
                for token in sentence
                if token.i in record_by_spacy_index
            )
            line_numbers = tuple(dict.fromkeys(record.line_number for record in records))
            stanza_numbers = tuple(
                dict.fromkeys(record.stanza_number for record in records)
            )
            units.append(
                SentenceUnit(
                    sentence_id=(
                        f"{document.text_version_id}:sentence:{sentence_number}"
                    ),
                    text_id=document.text_id,
                    text_version_id=document.text_version_id,
                    ordinal=sentence_number,
                    character_start=character_start,
                    character_end=character_end,
                    raw_text=document.original_text[character_start:character_end],
                    token_ids=tuple(record.token_id for record in records),
                    line_numbers=line_numbers,
                    stanza_numbers=stanza_numbers,
                    crosses_line_boundary=len(line_numbers) > 1,
                    crosses_stanza_boundary=len(stanza_numbers) > 1,
                )
            )
        return tuple(units)

    @staticmethod
    def _dependency_records(
        spacy_document: object,
        record_by_spacy_index: dict[int, TokenRecord],
    ) -> tuple[DependencyRecord, ...]:
        if not spacy_document.has_annotation("DEP"):
            return ()
        records = []
        for token in spacy_document:
            current = record_by_spacy_index.get(token.i)
            if current is None:
                continue
            head = record_by_spacy_index.get(token.head.i)
            is_root = token.head.i == token.i or token.dep_ == "ROOT"
            records.append(
                DependencyRecord(
                    token_id=current.token_id,
                    head_token_id=None if is_root or head is None else head.token_id,
                    dependency_label=token.dep_,
                    sentence_id=(
                        f"{current.text_version_id}:sentence:{current.sentence_number}"
                        if current.sentence_number is not None
                        else ""
                    ),
                    crosses_line_boundary=(
                        False
                        if is_root or head is None
                        else current.line_number != head.line_number
                    ),
                    crosses_stanza_boundary=(
                        False
                        if is_root or head is None
                        else current.stanza_number != head.stanza_number
                    ),
                    confidence=None,
                )
            )
        return tuple(records)

    @staticmethod
    def _entity_records(
        document: TextDocument,
        spacy_document: object,
        record_by_spacy_index: dict[int, TokenRecord],
        analysis_text: _AnalysisText,
        *,
        enabled: bool,
    ) -> tuple[EntityRecord, ...]:
        if not enabled or not spacy_document.has_annotation("ENT_IOB"):
            return ()
        records = []
        for entity_number, entity in enumerate(spacy_document.ents, start=1):
            character_start, character_end = analysis_text.original_span(
                entity.start_char,
                entity.end_char,
            )
            tokens = tuple(
                record_by_spacy_index[token.i]
                for token in entity
                if token.i in record_by_spacy_index
            )
            records.append(
                EntityRecord(
                    entity_id=f"{document.text_version_id}:entity:{entity_number}",
                    label=entity.label_,
                    character_start=character_start,
                    character_end=character_end,
                    raw_text=document.original_text[character_start:character_end],
                    token_ids=tuple(token.token_id for token in tokens),
                    line_numbers=tuple(
                        dict.fromkeys(token.line_number for token in tokens)
                    ),
                    stanza_numbers=tuple(
                        dict.fromkeys(token.stanza_number for token in tokens)
                    ),
                )
            )
        return tuple(records)

    @staticmethod
    def _orthographic_spans(
        document: TextDocument, tokens: tuple[TokenRecord, ...]
    ) -> tuple[OrthographicSpan, ...]:
        candidates: list[
            tuple[
                OrthographicFeatureKind,
                int,
                int,
                tuple[TokenRecord, ...],
            ]
        ] = []

        index = 0
        while index < len(tokens):
            start = index
            end = index
            if tokens[start].is_lexical:
                while (
                    end + 2 < len(tokens)
                    and tokens[end + 1].surface_form in HYPHEN_CHARACTERS
                    and tokens[end + 2].is_lexical
                    and tokens[end].character_end == tokens[end + 1].character_start
                    and tokens[end + 1].character_end
                    == tokens[end + 2].character_start
                    and tokens[start].line_number == tokens[end + 2].line_number
                ):
                    end += 2
            if end > start:
                members = tokens[start : end + 1]
                candidates.append(
                    (
                        OrthographicFeatureKind.HYPHENATED_EXPRESSION,
                        members[0].character_start,
                        members[-1].character_end,
                        members,
                    )
                )
                index = end + 1
            else:
                index += 1

        contraction_token_ids: set[str] = set()
        index = 0
        while index < len(tokens):
            if tokens[index].is_punctuation:
                index += 1
                continue
            end = index
            while (
                end + 1 < len(tokens)
                and not tokens[end + 1].is_punctuation
                and tokens[end].character_end == tokens[end + 1].character_start
                and tokens[index].line_number == tokens[end + 1].line_number
            ):
                end += 1
            members = tokens[index : end + 1]
            if len(members) > 1:
                raw_text = document.original_text[
                    members[0].character_start : members[-1].character_end
                ]
                if any(character in APOSTROPHE_CHARACTERS for character in raw_text):
                    candidates.append(
                        (
                            OrthographicFeatureKind.CONTRACTION,
                            members[0].character_start,
                            members[-1].character_end,
                            members,
                        )
                    )
                    contraction_token_ids.update(
                        member.token_id for member in members
                    )
            index = end + 1

        for token in tokens:
            if (
                token.token_id not in contraction_token_ids
                and any(
                    character in APOSTROPHE_CHARACTERS
                    for character in token.surface_form
                )
            ):
                candidates.append(
                    (
                        OrthographicFeatureKind.APOSTROPHE_FORM,
                        token.character_start,
                        token.character_end,
                        (token,),
                    )
                )

        candidates.sort(key=lambda item: (item[1], item[2], item[0].value))
        spans = []
        for number, (kind, start, end, members) in enumerate(candidates, start=1):
            spans.append(
                OrthographicSpan(
                    span_id=f"{document.text_version_id}:orthographic:{number}",
                    kind=kind,
                    character_start=start,
                    character_end=end,
                    raw_text=document.original_text[start:end],
                    token_ids=tuple(member.token_id for member in members),
                    line_number=members[0].line_number,
                    stanza_number=members[0].stanza_number,
                )
            )
        return tuple(spans)

    def _token_classifications(
        self,
        spacy_document: object,
        tokens: tuple[TokenRecord, ...],
        record_by_spacy_index: dict[int, TokenRecord],
        orthographic_spans: tuple[OrthographicSpan, ...],
    ) -> tuple[TokenClassification, ...]:
        hyphenated_ids = {
            token_id
            for span in orthographic_spans
            if span.kind is OrthographicFeatureKind.HYPHENATED_EXPRESSION
            for token_id in span.token_ids
        }
        contraction_ids = {
            token_id
            for span in orthographic_spans
            if span.kind is OrthographicFeatureKind.CONTRACTION
            for token_id in span.token_ids
        }
        spacy_token_by_record_id = {
            record.token_id: spacy_document[index]
            for index, record in record_by_spacy_index.items()
        }
        vocabulary_available = bool(spacy_document.vocab.vectors_length)
        classifications = []
        for token in tokens:
            if not token.is_lexical:
                role = TokenRole.NON_LEXICAL
            elif token.part_of_speech in self._configuration.content_pos_tags:
                role = TokenRole.CONTENT
            elif token.part_of_speech in self._configuration.function_pos_tags:
                role = TokenRole.FUNCTION
            else:
                role = TokenRole.OTHER
            if not vocabulary_available:
                vocabulary_state = ModelVocabularyState.UNAVAILABLE
            else:
                vocabulary_state = (
                    ModelVocabularyState.OUT_OF_VOCABULARY
                    if spacy_token_by_record_id[token.token_id].is_oov
                    else ModelVocabularyState.IN_VOCABULARY
                )
            classifications.append(
                TokenClassification(
                    token_id=token.token_id,
                    role=role,
                    is_hyphenated_component=token.token_id in hyphenated_ids,
                    is_contraction_component=token.token_id in contraction_ids,
                    has_apostrophe=any(
                        character in APOSTROPHE_CHARACTERS
                        for character in token.surface_form
                    ),
                    model_vocabulary_state=vocabulary_state,
                )
            )
        return tuple(classifications)

    @staticmethod
    def _coverage(
        tokens: tuple[TokenRecord, ...],
        sentences: tuple[SentenceUnit, ...],
        dependencies: tuple[DependencyRecord, ...],
        entities: tuple[EntityRecord, ...],
        classifications: tuple[TokenClassification, ...],
        *,
        vocabulary_available: bool,
    ) -> ProcessingCoverage:
        total = len(tokens)
        lexical_count = sum(token.is_lexical for token in tokens)
        sentence_tokens = sum(
            token.sentence_number is not None for token in tokens
        )
        if vocabulary_available:
            model_oov_count = sum(
                classification.model_vocabulary_state
                is ModelVocabularyState.OUT_OF_VOCABULARY
                for token, classification in zip(tokens, classifications)
                if token.is_lexical
            )
            model_oov_rate = (
                model_oov_count / lexical_count if lexical_count else None
            )
        else:
            model_oov_count = None
            model_oov_rate = None
        return ProcessingCoverage(
            total_token_count=total,
            lexical_token_count=lexical_count,
            sentence_count=len(sentences),
            tokens_with_sentence_count=sentence_tokens,
            sentence_annotation_rate=sentence_tokens / total if total else None,
            dependency_record_count=len(dependencies),
            dependency_annotation_rate=(
                len(dependencies) / total if total else None
            ),
            entity_count=len(entities),
            model_vocabulary_available=vocabulary_available,
            model_oov_count=model_oov_count,
            model_oov_rate=model_oov_rate,
        )

    @staticmethod
    def _document_warnings(
        tokens: tuple[TokenRecord, ...],
        coverage: ProcessingCoverage,
    ) -> tuple[DocumentWarning, ...]:
        warnings = [
            DocumentWarning(
                code="general_model_on_poetry",
                message=(
                    "Part-of-speech, lemma, sentence, and dependency annotations "
                    "are statistical model outputs and may be less reliable for "
                    "poetic syntax, archaism, or coined forms."
                ),
            )
        ]
        if not tokens:
            warnings.append(
                DocumentWarning(
                    code="empty_text",
                    message=(
                        "The preserved text contains no processable tokens; "
                        "coverage values with empty denominators remain missing."
                    ),
                    severity=DocumentWarningSeverity.INFORMATION,
                )
            )
        elif coverage.sentence_annotation_rate != 1.0:
            warnings.append(
                DocumentWarning(
                    code="incomplete_sentence_annotations",
                    message=(
                        "The linguistic model did not assign every token to a "
                        "sentence."
                    ),
                )
            )
        if tokens and coverage.dependency_annotation_rate != 1.0:
            warnings.append(
                DocumentWarning(
                    code="incomplete_dependency_annotations",
                    message=(
                        "The linguistic model did not produce a dependency record "
                        "for every token."
                    ),
                )
            )
        if not coverage.model_vocabulary_available:
            warnings.append(
                DocumentWarning(
                    code="model_vocabulary_unavailable",
                    message=(
                        "The installed small English model has no static vector "
                        "vocabulary, so model-vocabulary OOV counts are unavailable. "
                        "This is separate from later resource-specific unmatched "
                        "coverage."
                    ),
                    severity=DocumentWarningSeverity.INFORMATION,
                )
            )
        uncertain_count = sum(
            token.part_of_speech == "X" for token in tokens if token.is_lexical
        )
        if uncertain_count:
            warnings.append(
                DocumentWarning(
                    code="uncertain_pos_tags",
                    message=(
                        f"The linguistic model assigned the uncertain POS tag X "
                        f"to {uncertain_count} lexical token(s)."
                    ),
                )
            )
        return tuple(warnings)

    def process_document(self, document: TextDocument) -> PoemDocument:
        analysis_text = _analysis_text_without_line_edge_whitespace(
            document.original_text
        )
        spacy_document = self._nlp(analysis_text.text)
        if self._configuration.merge_possessives:
            self._merge_possessives(spacy_document)
        line_index = _LineIndex(document.original_text)

        sentence_positions: dict[int, tuple[int, int]] = {}
        try:
            for sentence_number, sentence in enumerate(spacy_document.sents, start=1):
                for position, token in enumerate(sentence, start=1):
                    sentence_positions[token.i] = (sentence_number, position)
        except ValueError:
            sentence_positions = {}

        records: list[TokenRecord] = []
        for token in spacy_document:
            if token.is_space:
                continue
            character_start, character_end = analysis_text.original_span(
                token.idx,
                token.idx + len(token.text),
            )
            location = line_index.locate(character_start)
            token_position = len(records) + 1
            sentence_number, position_in_sentence = sentence_positions.get(
                token.i, (None, None)
            )
            surface = token.text
            stripped = strip_edge_punctuation(surface)
            lemma = token.lemma_ or surface
            warnings: list[str] = []
            if token.pos_ == "X":
                warnings.append(
                    "The linguistic model assigned an uncertain POS tag (X)."
                )
            if not token.lemma_:
                warnings.append("The linguistic model did not provide a lemma.")

            records.append(
                TokenRecord(
                    token_id=f"{document.text_version_id}:t{token_position}",
                    text_id=document.text_id,
                    text_version_id=document.text_version_id,
                    section_number=1,
                    stanza_number=location.stanza,
                    line_number=location.number,
                    token_position=token_position,
                    sentence_number=sentence_number,
                    token_position_in_sentence=position_in_sentence,
                    character_start=character_start,
                    character_end=character_end,
                    surface_form=surface,
                    lowercase_form=surface.lower(),
                    punctuation_stripped_form=stripped,
                    normalized_form=normalize_lookup(surface),
                    part_of_speech=token.pos_,
                    lemma=lemma,
                    normalized_lemma=normalize_lookup(lemma),
                    morphological_features=str(token.morph),
                    is_punctuation=bool(token.is_punct),
                    is_numeric=bool(token.like_num),
                    is_proper_noun=token.pos_ == "PROPN",
                    is_stopword=bool(token.is_stop),
                    context=location.context,
                    preprocessing_warnings=tuple(warnings),
                )
            )

        token_records = tuple(records)
        spacy_tokens = tuple(token for token in spacy_document if not token.is_space)
        record_by_spacy_index = {
            spacy_token.i: record
            for spacy_token, record in zip(spacy_tokens, token_records)
        }
        structural_units = self._structural_units(document, line_index)
        sentences = self._sentence_units(
            document,
            spacy_document,
            record_by_spacy_index,
            analysis_text,
        )
        dependencies = self._dependency_records(
            spacy_document, record_by_spacy_index
        )
        entities = self._entity_records(
            document,
            spacy_document,
            record_by_spacy_index,
            analysis_text,
            enabled=self._configuration.enable_ner,
        )
        orthographic_spans = self._orthographic_spans(document, token_records)
        classifications = self._token_classifications(
            spacy_document,
            token_records,
            record_by_spacy_index,
            orthographic_spans,
        )
        vocabulary_available = bool(spacy_document.vocab.vectors_length)
        coverage = self._coverage(
            token_records,
            sentences,
            dependencies,
            entities,
            classifications,
            vocabulary_available=vocabulary_available,
        )
        return PoemDocument(
            source=document,
            configuration=self._configuration,
            preprocessing=self.metadata,
            structural_units=structural_units,
            sentences=sentences,
            tokens=token_records,
            dependencies=dependencies,
            entities=entities,
            orthographic_spans=orthographic_spans,
            token_classifications=classifications,
            coverage=coverage,
            warnings=self._document_warnings(token_records, coverage),
        )

    def process(self, document: TextDocument) -> tuple[TokenRecord, ...]:
        """Backward-compatible token API used by the validated affective engine."""

        return self.process_document(document).tokens
