"""Offline Open English WordNet lookup for Lexicon Explorer.

The packaged artifact is a compressed, pre-indexed ``wn`` SQLite database.
It is expanded into VerseVAD's ignored runtime area on first use so ordinary
lookups never require a network request or rebuild the source wordnet.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import importlib
import lzma
import os
from pathlib import Path
import tempfile
import threading

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_DIRECTORY = PROJECT_ROOT / "resources" / "open_english_wordnet"
PACKAGED_DATABASE = RESOURCE_DIRECTORY / "oewn-2025-plus-wn.db.xz"
PACKAGED_DATABASE_SHA256 = (
    "c5f6259591247d1bf1a81454553599d4c5eb41a7f9d668de46e41ab3b8f5806f"
)
DATABASE_SHA256 = (
    "6c3c5f0376be143775026ce3f39c802359a1a51d431e7dc0c97df0f3e5058201"
)
DATABASE_SIZE = 112_513_024
SOURCE_LMF_SHA256 = (
    "31f4af16c54b532fd5484d4cc33aee588a31bb5b70683ae8197842fde5b586bc"
)
OEWN_ID = "oewn:2025+"
OEWN_VERSION = "2025+"
OEWN_LABEL = "Open English WordNet"
OEWN_LICENSE = "CC BY 4.0, incorporating Princeton WordNet material"
OEWN_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OEWN_SOURCE_URL = "https://en-word.net/static/english-wordnet-2025-plus.xml.gz"
OEWN_CITATION = (
    "McCrae, John P., Alexandre Rademaker, Francis Bond, Ewa Rudnicka, and "
    "Christiane Fellbaum. 2019. English WordNet 2019: An Open-Source WordNet "
    "for English. Proceedings of the 10th Global WordNet Conference."
)
WN_VERSION = "1.1.0"

_UNPACK_LOCK = threading.Lock()
_POS_LABELS = {
    "n": "Noun",
    "v": "Verb",
    "a": "Adjective",
    "s": "Adjective satellite",
    "r": "Adverb",
}
_MODEL_POS = {
    "NOUN": "n",
    "PROPN": "n",
    "VERB": "v",
    "AUX": "v",
    "ADJ": "a",
    "ADV": "r",
}


class DictionaryResourceError(RuntimeError):
    """Raised when the packaged dictionary cannot be validated or opened."""


@dataclass(frozen=True)
class DictionarySense:
    sense_id: str
    synset_id: str
    matched_lemma: str
    part_of_speech: str
    part_of_speech_label: str
    definition: str
    examples: tuple[str, ...]
    synonyms: tuple[str, ...]
    antonyms: tuple[str, ...]
    broader_terms: tuple[str, ...]
    broader_term_count: int
    narrower_terms: tuple[str, ...]
    narrower_term_count: int


@dataclass(frozen=True)
class DictionaryLookupResult:
    query: str
    lookup_form: str
    match_method: str
    processing_pos: str
    available: bool
    status_message: str
    senses: tuple[DictionarySense, ...]
    source: str = OEWN_LABEL
    version: str = OEWN_VERSION
    source_url: str = OEWN_SOURCE_URL
    source_lmf_sha256: str = SOURCE_LMF_SHA256
    packaged_database_sha256: str = PACKAGED_DATABASE_SHA256
    license: str = OEWN_LICENSE
    license_url: str = OEWN_LICENSE_URL
    citation: str = OEWN_CITATION
    adapter_version: str = "1.0.0"
    library: str = f"wn {WN_VERSION}"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_root() -> Path:
    configured = os.environ.get("VERSEVAD_RUNTIME_DIR", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        (
            PROJECT_ROOT / ".runtime",
            Path(tempfile.gettempdir()) / "versevad-runtime",
        )
    )
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".dictionary-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    raise DictionaryResourceError(
        "VerseVAD could not create a local runtime directory for the packaged dictionary."
    )


def _database_directory() -> Path:
    return (
        _runtime_root()
        / "open_english_wordnet"
        / f"{OEWN_VERSION}-{PACKAGED_DATABASE_SHA256[:12]}"
    )


def _database_ready(database: Path, marker: Path) -> bool:
    if not database.is_file() or database.stat().st_size != DATABASE_SIZE:
        return False
    try:
        return marker.read_text(encoding="ascii").strip() == DATABASE_SHA256
    except OSError:
        return False


@lru_cache(maxsize=1)
def ensure_open_english_wordnet_database() -> Path:
    """Validate and expand the pinned database once into ignored runtime data."""

    if not PACKAGED_DATABASE.is_file():
        raise DictionaryResourceError(
            "The packaged Open English WordNet database is missing. Reinstall or "
            "update VerseVAD; no online lookup was attempted."
        )
    if _sha256(PACKAGED_DATABASE) != PACKAGED_DATABASE_SHA256:
        raise DictionaryResourceError(
            "The packaged Open English WordNet database failed its SHA-256 check. "
            "Reinstall VerseVAD before using dictionary lookup."
        )

    directory = _database_directory()
    database = directory / "wn.db"
    marker = directory / "wn.db.sha256"
    if _database_ready(database, marker):
        return directory

    with _UNPACK_LOCK:
        if _database_ready(database, marker):
            return directory
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / (
            f"wn.db.tmp-{os.getpid()}-{threading.get_ident()}"
        )
        digest = sha256()
        try:
            with lzma.open(PACKAGED_DATABASE, "rb") as source, temporary.open(
                "wb"
            ) as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                    digest.update(chunk)
            if temporary.stat().st_size != DATABASE_SIZE:
                raise DictionaryResourceError(
                    "The packaged Open English WordNet database expanded to an "
                    "unexpected size."
                )
            if digest.hexdigest() != DATABASE_SHA256:
                raise DictionaryResourceError(
                    "The expanded Open English WordNet database failed its SHA-256 check."
                )
            os.replace(temporary, database)
            marker.write_text(DATABASE_SHA256, encoding="ascii")
        finally:
            temporary.unlink(missing_ok=True)
    return directory


@lru_cache(maxsize=1)
def _wn_module():
    return importlib.import_module("wn")


@lru_cache(maxsize=1)
def _wordnet():
    directory = ensure_open_english_wordnet_database()
    try:
        wn_module = _wn_module()
    except ImportError as error:
        raise DictionaryResourceError(
            "The pinned wn dictionary library is not installed. Run VerseVAD setup again."
        ) from error
    wn_module.config.data_directory = directory
    wn_module.config.allow_multithreading = True
    try:
        return wn_module.Wordnet(OEWN_ID)
    except Exception as error:  # wn normalizes several SQLite/index failures.
        raise DictionaryResourceError(
            "VerseVAD could not open the packaged Open English WordNet database."
        ) from error


def _unique(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _related_terms(synsets, *, limit: int = 12) -> tuple[tuple[str, ...], int]:
    terms = _unique(
        lemma
        for related in synsets
        for lemma in related.lemmas()
    )
    return terms[:limit], len(terms)


def _sense_view(word, sense) -> DictionarySense:
    synset = sense.synset()
    synonyms = _unique(
        lemma for lemma in synset.lemmas() if lemma.casefold() != word.lemma().casefold()
    )
    antonyms = _unique(
        related.word().lemma()
        for related in sense.relations().get("antonym", ())
    )
    broader_terms, broader_count = _related_terms(synset.hypernyms())
    narrower_terms, narrower_count = _related_terms(synset.hyponyms())
    return DictionarySense(
        sense_id=sense.id,
        synset_id=synset.id,
        matched_lemma=word.lemma(),
        part_of_speech=synset.pos,
        part_of_speech_label=_POS_LABELS.get(synset.pos, synset.pos),
        definition=synset.definition() or "Definition unavailable.",
        examples=tuple(synset.examples()),
        synonyms=synonyms,
        antonyms=antonyms,
        broader_terms=broader_terms,
        broader_term_count=broader_count,
        narrower_terms=narrower_terms,
        narrower_term_count=narrower_count,
    )


@lru_cache(maxsize=256)
def lookup_open_english_wordnet(
    query: str,
    *,
    lemma: str = "",
    processing_pos: str = "",
) -> DictionaryLookupResult:
    """Return available senses without claiming contextual disambiguation."""

    raw_query = query.strip()
    if not raw_query:
        raise ValueError("Enter a word or phrase to look up.")
    try:
        wordnet = _wordnet()
    except DictionaryResourceError as error:
        return DictionaryLookupResult(
            query=raw_query,
            lookup_form=raw_query,
            match_method="resource unavailable",
            processing_pos=processing_pos,
            available=False,
            status_message=str(error),
            senses=(),
        )

    candidates: list[tuple[str, str]] = [(raw_query, "dictionary entry")]
    normalized_lemma = lemma.strip()
    if normalized_lemma and normalized_lemma.casefold() != raw_query.casefold():
        candidates.append((normalized_lemma, "model-lemma dictionary entry"))

    words = ()
    lookup_form = raw_query
    match_method = "dictionary entry"
    for candidate, method in candidates:
        found = tuple(wordnet.words(candidate))
        if found:
            exact = tuple(word for word in found if word.lemma() == candidate)
            insensitive = tuple(word for word in found if word not in exact)
            words = exact + insensitive
            lookup_form = candidate
            match_method = method
            break

    if not words:
        return DictionaryLookupResult(
            query=raw_query,
            lookup_form=lookup_form,
            match_method="unmatched",
            processing_pos=processing_pos,
            available=True,
            status_message=(
                "Open English WordNet is available, but it contains no entry for "
                "this spelling or the model lemma."
            ),
            senses=(),
        )

    preferred_pos = _MODEL_POS.get(processing_pos.upper(), "")
    words = tuple(
        sorted(
            words,
            key=lambda word: (
                word.pos != preferred_pos if preferred_pos else False,
                word.lemma() != lookup_form,
                word.pos,
                word.lemma().casefold(),
            ),
        )
    )
    senses = []
    seen = set()
    for word in words:
        for sense in word.senses():
            if sense.id in seen:
                continue
            seen.add(sense.id)
            senses.append(_sense_view(word, sense))

    return DictionaryLookupResult(
        query=raw_query,
        lookup_form=lookup_form,
        match_method=match_method,
        processing_pos=processing_pos,
        available=True,
        status_message=(
            f"{len(senses)} available dictionary sense"
            f"{'s' if len(senses) != 1 else ''}; no contextual sense was selected."
        ),
        senses=tuple(senses),
    )


__all__ = [
    "DictionaryLookupResult",
    "DictionaryResourceError",
    "DictionarySense",
    "lookup_open_english_wordnet",
]
