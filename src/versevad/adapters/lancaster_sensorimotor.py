"""Read-only adapter for the Lancaster Sensorimotor Norms CSV source."""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from versevad.normalization import normalize_lookup


DIMENSION_COLUMNS = (
    ("auditory", "Auditory.mean", "Auditory.SD"),
    ("gustatory", "Gustatory.mean", "Gustatory.SD"),
    ("haptic", "Haptic.mean", "Haptic.SD"),
    ("interoceptive", "Interoceptive.mean", "Interoceptive.SD"),
    ("olfactory", "Olfactory.mean", "Olfactory.SD"),
    ("visual", "Visual.mean", "Visual.SD"),
    ("foot_leg", "Foot_leg.mean", "Foot_leg.SD"),
    ("hand_arm", "Hand_arm.mean", "Hand_arm.SD"),
    ("head", "Head.mean", "Head.SD"),
    ("mouth", "Mouth.mean", "Mouth.SD"),
    ("torso", "Torso.mean", "Torso.SD"),
)

COMPOSITE_COLUMNS = (
    "Max_strength.perceptual",
    "Minkowski3.perceptual",
    "Exclusivity.perceptual",
    "Max_strength.action",
    "Minkowski3.action",
    "Exclusivity.action",
    "Max_strength.sensorimotor",
    "Minkowski3.sensorimotor",
    "Exclusivity.sensorimotor",
)

DOMINANT_COLUMNS = (
    "Dominant.perceptual",
    "Dominant.action",
    "Dominant.sensorimotor",
)

KNOWN_COLUMNS = (
    "Percent_known.perceptual",
    "Percent_known.action",
)

REQUIRED_COLUMNS = (
    "Word",
    *(column for _dimension, column, _sd_column in DIMENSION_COLUMNS),
    *(sd_column for _dimension, _column, sd_column in DIMENSION_COLUMNS),
    *COMPOSITE_COLUMNS,
    *DOMINANT_COLUMNS,
    *KNOWN_COLUMNS,
)


class LancasterSensorimotorAdapterError(RuntimeError):
    """Plain-language source-contract failure; the source is never changed."""

    def __init__(self, message: str, technical_detail: str = "") -> None:
        super().__init__(message)
        self.technical_detail = technical_detail
        self.data_changed = False


@dataclass(frozen=True)
class SensorimotorVector:
    auditory: float
    gustatory: float
    haptic: float
    interoceptive: float
    olfactory: float
    visual: float
    foot_leg: float
    hand_arm: float
    head: float
    mouth: float
    torso: float

    def by_id(self) -> dict[str, float]:
        return {
            dimension: getattr(self, dimension)
            for dimension, _mean_column, _sd_column in DIMENSION_COLUMNS
        }


@dataclass(frozen=True)
class SensorimotorEntry:
    source_term: str
    lookup_form: str
    source_row: int
    is_multiword: bool
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

    @property
    def word_count(self) -> int:
        return len(self.lookup_form.split())


@dataclass(frozen=True)
class LancasterSensorimotorValidation:
    source_path: Path
    source_sha256: str
    total_rows: int
    usable_entries: int
    phrase_entries: int
    blank_terms: int
    malformed_rows: int
    duplicate_keys: int


@dataclass(frozen=True)
class LancasterSensorimotorLexicon:
    entries: Mapping[str, SensorimotorEntry]
    phrases_by_first_word: Mapping[str, tuple[SensorimotorEntry, ...]]
    validation: LancasterSensorimotorValidation

    def lookup(self, normalized_form: str) -> SensorimotorEntry | None:
        return self.entries.get(normalized_form)


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float(
    row: Mapping[str, str],
    column: str,
    *,
    source_row: int,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw_value = (row.get(column) or "").strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise LancasterSensorimotorAdapterError(
            f"The Lancaster source contains a non-numeric {column!r} value.",
            f"Row {source_row}: {raw_value!r}",
        ) from error
    if not math.isfinite(value):
        raise LancasterSensorimotorAdapterError(
            f"The Lancaster source contains a non-finite {column!r} value.",
            f"Row {source_row}: {raw_value!r}",
        )
    if minimum is not None and value < minimum:
        raise LancasterSensorimotorAdapterError(
            f"The Lancaster source contains an out-of-range {column!r} value.",
            f"Row {source_row}: {value!r}",
        )
    if maximum is not None and value > maximum:
        raise LancasterSensorimotorAdapterError(
            f"The Lancaster source contains an out-of-range {column!r} value.",
            f"Row {source_row}: {value!r}",
        )
    return value


def _vector(
    row: Mapping[str, str],
    *,
    source_row: int,
    use_standard_deviation: bool,
) -> SensorimotorVector:
    values = {}
    for dimension, mean_column, sd_column in DIMENSION_COLUMNS:
        column = sd_column if use_standard_deviation else mean_column
        values[dimension] = _float(
            row,
            column,
            source_row=source_row,
            minimum=0.0,
            maximum=None if use_standard_deviation else 5.0,
        )
    return SensorimotorVector(**values)


class LancasterSensorimotorAdapter:
    """Parse the authors' CSV in place without rewriting or deriving it."""

    adapter_version = "1.0.0"

    def load(self, path: Path | str) -> LancasterSensorimotorLexicon:
        source_path = Path(path)
        if not source_path.is_file():
            raise LancasterSensorimotorAdapterError(
                f"The Lancaster Sensorimotor Norms file was not found: {source_path}"
            )

        entries: dict[str, SensorimotorEntry] = {}
        phrase_groups: dict[str, list[SensorimotorEntry]] = {}
        total_rows = blank_terms = malformed_rows = duplicate_keys = 0
        try:
            with source_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                fieldnames = tuple(reader.fieldnames or ())
                missing = sorted(set(REQUIRED_COLUMNS) - set(fieldnames))
                if missing:
                    raise LancasterSensorimotorAdapterError(
                        "The Lancaster source does not contain the expected columns.",
                        "Missing columns: " + ", ".join(missing),
                    )
                for source_row, row in enumerate(reader, start=2):
                    total_rows += 1
                    source_term = (row.get("Word") or "").strip()
                    lookup_form = normalize_lookup(source_term)
                    if not lookup_form:
                        blank_terms += 1
                        continue
                    if lookup_form in entries:
                        duplicate_keys += 1
                        raise LancasterSensorimotorAdapterError(
                            "The Lancaster source contains duplicate normalized terms.",
                            f"Row {source_row}: {source_term!r} -> {lookup_form!r}",
                        )
                    try:
                        entry = SensorimotorEntry(
                            source_term=source_term,
                            lookup_form=lookup_form,
                            source_row=source_row,
                            is_multiword=any(
                                character.isspace() for character in lookup_form
                            ),
                            means=_vector(
                                row,
                                source_row=source_row,
                                use_standard_deviation=False,
                            ),
                            source_standard_deviations=_vector(
                                row,
                                source_row=source_row,
                                use_standard_deviation=True,
                            ),
                            max_perceptual_strength=_float(
                                row,
                                "Max_strength.perceptual",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            minkowski3_perceptual_strength=_float(
                                row,
                                "Minkowski3.perceptual",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            perceptual_exclusivity=_float(
                                row,
                                "Exclusivity.perceptual",
                                source_row=source_row,
                                minimum=0.0,
                                maximum=1.0,
                            ),
                            dominant_perceptual=(
                                row["Dominant.perceptual"].strip()
                            ),
                            max_action_strength=_float(
                                row,
                                "Max_strength.action",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            minkowski3_action_strength=_float(
                                row,
                                "Minkowski3.action",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            action_exclusivity=_float(
                                row,
                                "Exclusivity.action",
                                source_row=source_row,
                                minimum=0.0,
                                maximum=1.0,
                            ),
                            dominant_action=row["Dominant.action"].strip(),
                            max_sensorimotor_strength=_float(
                                row,
                                "Max_strength.sensorimotor",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            minkowski3_sensorimotor_strength=_float(
                                row,
                                "Minkowski3.sensorimotor",
                                source_row=source_row,
                                minimum=0.0,
                            ),
                            sensorimotor_exclusivity=_float(
                                row,
                                "Exclusivity.sensorimotor",
                                source_row=source_row,
                                minimum=0.0,
                                maximum=1.0,
                            ),
                            dominant_sensorimotor=(
                                row["Dominant.sensorimotor"].strip()
                            ),
                            percent_known_perceptual=_float(
                                row,
                                "Percent_known.perceptual",
                                source_row=source_row,
                                minimum=0.0,
                                maximum=1.0,
                            ),
                            percent_known_action=_float(
                                row,
                                "Percent_known.action",
                                source_row=source_row,
                                minimum=0.0,
                                maximum=1.0,
                            ),
                        )
                    except (KeyError, LancasterSensorimotorAdapterError):
                        malformed_rows += 1
                        raise
                    entries[lookup_form] = entry
                    if entry.is_multiword:
                        first_word = lookup_form.split()[0]
                        phrase_groups.setdefault(first_word, []).append(entry)
        except UnicodeError as error:
            raise LancasterSensorimotorAdapterError(
                "The Lancaster source could not be read as UTF-8.",
                str(error),
            ) from error
        except OSError as error:
            raise LancasterSensorimotorAdapterError(
                "The Lancaster source could not be opened.",
                str(error),
            ) from error

        phrases = {
            first: tuple(
                sorted(
                    group,
                    key=lambda item: (-item.word_count, item.lookup_form),
                )
            )
            for first, group in phrase_groups.items()
        }
        validation = LancasterSensorimotorValidation(
            source_path=source_path,
            source_sha256=_source_sha256(source_path),
            total_rows=total_rows,
            usable_entries=len(entries),
            phrase_entries=sum(entry.is_multiword for entry in entries.values()),
            blank_terms=blank_terms,
            malformed_rows=malformed_rows,
            duplicate_keys=duplicate_keys,
        )
        return LancasterSensorimotorLexicon(
            entries=MappingProxyType(entries),
            phrases_by_first_word=MappingProxyType(phrases),
            validation=validation,
        )
