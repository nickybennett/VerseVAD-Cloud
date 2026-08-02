"""Invented Phase 2 fixtures with hand-calculable multi-lexicon values."""

from __future__ import annotations

import hashlib

from versevad.models import (
    EmotionAssociationEntry,
    EmotionAssociationLexicon,
    EmotionIntensityEntry,
    EmotionIntensityLexicon,
    LexiconMetadata,
    LexiconValidation,
    LexiconValueKind,
    VadEntry,
    VadLexicon,
    VadScores,
)
from versevad.normalization import normalize_lookup


PHASE2_PHRASE_TEXT = "Very dark night glows.\nBright night glows.\n"


def _validation(lexicon_id: str, lines: list[str], entries: int, phrases: int = 0) -> LexiconValidation:
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return LexiconValidation(
        source_path=None,
        source_sha256=digest,
        total_rows=len(lines),
        usable_entries=entries,
        phrase_entries=phrases,
        blank_terms=0,
        malformed_rows=0,
        duplicate_keys=0,
        conflicting_normalized_keys=0,
        out_of_range_scores=0,
    )


def phase2_synthetic_vad_lexicon() -> VadLexicon:
    values = (
        ("very dark night", 1.0, 8.0, 2.0),
        ("dark night", 2.0, 7.0, 3.0),
        ("some one", 5.0, 5.0, 5.0),
        ("some", 4.0, 4.0, 4.0),
        ("one", 6.0, 6.0, 6.0),
        ("dark", 3.0, 6.0, 4.0),
        ("night", 4.0, 5.0, 6.0),
        ("glow", 7.0, 4.0, 6.0),
        ("bright", 8.0, 5.0, 7.0),
    )
    metadata = LexiconMetadata(
        lexicon_id="synthetic_vad_phase2",
        display_name="VerseVAD Phase 2 synthetic phrase VAD fixture",
        family="VerseVAD validation fixtures",
        version="2",
        language="English",
        unit_of_analysis="invented unigrams and phrases",
        source_scale_min=1.0,
        source_scale_max=9.0,
        normalization_formula="normalized = (original - 1) / 8",
        adapter_version="synthetic-2",
        citation="Invented VerseVAD validation data.",
        license_notice="Invented public-domain validation data.",
        phrase_support=True,
    )
    entries = {}
    lines = []
    for row, (term, valence, arousal, dominance) in enumerate(values, start=1):
        original = VadScores(valence, arousal, dominance)
        key = normalize_lookup(term)
        entries[key] = VadEntry(
            lexicon_id=metadata.lexicon_id,
            source_term=term,
            lookup_form=key,
            source_row=row,
            original=original,
            normalized=VadScores(
                (valence - 1.0) / 8.0,
                (arousal - 1.0) / 8.0,
                (dominance - 1.0) / 8.0,
            ),
        )
        lines.append(f"{term}\t{valence}\t{arousal}\t{dominance}")
    return VadLexicon.create(
        metadata,
        entries,
        _validation(metadata.lexicon_id, lines, len(entries), phrases=3),
    )


def phase2_synthetic_emotion_lexicon() -> EmotionAssociationLexicon:
    associations = {
        "joy": ("joy", "positive"),
        "fear": ("anger", "fear", "negative"),
        "stone": (),
    }
    categories = (
        "anger",
        "anticipation",
        "disgust",
        "fear",
        "joy",
        "negative",
        "positive",
        "sadness",
        "surprise",
        "trust",
    )
    metadata = LexiconMetadata(
        lexicon_id="synthetic_emotion_phase2",
        display_name="VerseVAD Phase 2 synthetic emotion fixture",
        family="VerseVAD validation fixtures",
        version="2",
        language="English",
        unit_of_analysis="invented categorical word associations",
        source_scale_min=0.0,
        source_scale_max=1.0,
        normalization_formula="not applicable",
        adapter_version="synthetic-2",
        citation="Invented VerseVAD validation data.",
        license_notice="Invented public-domain validation data.",
        phrase_support=False,
        value_kind=LexiconValueKind.CATEGORICAL_ASSOCIATION,
        dimensions=categories,
    )
    lines = []
    entries = {}
    for row, (term, values) in enumerate(associations.items(), start=1):
        key = normalize_lookup(term)
        entries[key] = EmotionAssociationEntry(
            lexicon_id=metadata.lexicon_id,
            source_term=term,
            lookup_form=key,
            source_rows=(row,),
            associations=values,
        )
        lines.append(f"{term}\t{'|'.join(values)}")
    return EmotionAssociationLexicon.create(
        metadata, entries, _validation(metadata.lexicon_id, lines, len(entries))
    )


def phase2_synthetic_intensity_lexicon() -> EmotionIntensityLexicon:
    values = {
        "rage": (("anger", 0.8),),
        "fear": (("anger", 0.2), ("fear", 0.6)),
    }
    categories = (
        "anger",
        "anticipation",
        "disgust",
        "fear",
        "joy",
        "sadness",
        "surprise",
        "trust",
    )
    metadata = LexiconMetadata(
        lexicon_id="synthetic_intensity_phase2",
        display_name="VerseVAD Phase 2 synthetic intensity fixture",
        family="VerseVAD validation fixtures",
        version="2",
        language="English",
        unit_of_analysis="invented word-emotion intensities",
        source_scale_min=0.0,
        source_scale_max=1.0,
        normalization_formula="normalized = original (identity)",
        adapter_version="synthetic-2",
        citation="Invented VerseVAD validation data.",
        license_notice="Invented public-domain validation data.",
        phrase_support=False,
        value_kind=LexiconValueKind.EMOTION_INTENSITY,
        dimensions=categories,
    )
    lines = []
    entries = {}
    row = 1
    for term, intensities in values.items():
        key = normalize_lookup(term)
        source_rows = tuple(range(row, row + len(intensities)))
        entries[key] = EmotionIntensityEntry(
            lexicon_id=metadata.lexicon_id,
            source_term=term,
            lookup_form=key,
            source_rows=source_rows,
            intensities=intensities,
        )
        for category, value in intensities:
            lines.append(f"{term}\t{category}\t{value}")
        row += len(intensities)
    return EmotionIntensityLexicon.create(
        metadata, entries, _validation(metadata.lexicon_id, lines, len(entries))
    )
