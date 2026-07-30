"""Safe discovery and local management of VerseMap reference corpora."""

from __future__ import annotations

import configparser
import csv
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

from versevad.application import PROJECT_ROOT, RESOURCE_ROOT
from versevad.versemap import VerseMapReferenceIndex, load_reference_index
from versevad.versemap.model import (
    MODEL_FILENAME,
    POET_PROFILE_FILENAME,
    PROFILE_FILENAME,
)
from versevad.versemap.reference import (
    BuildResult,
    ProfileBuildResult,
    build_reference_release,
    update_reference_profiles,
    update_reference_release,
)


BUILT_IN_CORPUS_ID = "built-in"
BUILT_IN_CORPUS_NAME = "VerseVAD Public-Domain Reference Corpus"
CORPUS_INFO_FILENAME = ".versevad-corpus.ini"
USER_CORPUS_DIRECTORY = Path("projects") / "reference_corpora"
_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._ -]+")
_SAFE_SLUG = re.compile(r"[^a-z0-9]+")


class ReferenceCorpusError(ValueError):
    """A safe, user-facing reference-corpus management error."""


@dataclass(frozen=True)
class ReferenceCorpusDescriptor:
    corpus_id: str
    display_name: str
    source_root: Path
    built_in: bool
    index_available: bool
    poem_count: int
    poet_count: int
    release_id: str
    model_id: str

    @property
    def scope_label(self) -> str:
        return "Built in" if self.built_in else "Local user corpus"


def user_reference_corpora_root() -> Path:
    configured = os.environ.get("VERSEVAD_REFERENCE_CORPORA_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (PROJECT_ROOT / USER_CORPUS_DIRECTORY).resolve()


def built_in_reference_corpus_root() -> Path:
    return (RESOURCE_ROOT / "VerseMap_Reference_Corpus").resolve()


def _slug(value: str) -> str:
    slug = _SAFE_SLUG.sub("-", value.casefold()).strip("-")
    return slug[:80]


def _corpus_display_name(source_root: Path) -> str:
    info_path = source_root / CORPUS_INFO_FILENAME
    if info_path.is_file():
        parser = configparser.ConfigParser()
        try:
            parser.read(info_path, encoding="utf-8")
            value = parser.get("corpus", "name", fallback="").strip()
        except (OSError, configparser.Error):
            value = ""
        if value:
            return value
    return source_root.name.replace("_", " ").replace("-", " ").strip().title()


def _file_signature(path: Path) -> tuple[str, int, int] | None:
    """Return a cheap signature that invalidates caches after corpus updates."""

    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path.resolve()), stat.st_size, stat.st_mtime_ns


@lru_cache(maxsize=32)
def _index_header_cached(
    signature: tuple[str, int, int],
) -> tuple[str, str]:
    path = Path(signature[0])
    if not path.is_file():
        return "", ""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            row = next(csv.DictReader(handle), None)
    except (OSError, csv.Error):
        return "", ""
    if not row:
        return "", ""
    return row.get("reference_release_id", ""), row.get("model_id", "")


def _index_header(source_root: Path) -> tuple[str, str]:
    signature = _file_signature(source_root / MODEL_FILENAME)
    return _index_header_cached(signature) if signature is not None else ("", "")


@lru_cache(maxsize=64)
def _csv_row_count_cached(signature: tuple[str, int, int]) -> int:
    path = Path(signature[0])
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return sum(1 for _ in csv.DictReader(handle))
    except (OSError, csv.Error):
        return 0


def _profile_counts(source_root: Path) -> tuple[int, int]:
    def count_rows(path: Path) -> int:
        signature = _file_signature(path)
        return (
            _csv_row_count_cached(signature)
            if signature is not None
            else 0
        )

    return (
        count_rows(source_root / PROFILE_FILENAME),
        count_rows(source_root / POET_PROFILE_FILENAME),
    )


def _descriptor(
    source_root: Path,
    *,
    corpus_id: str,
    display_name: str,
    built_in: bool,
) -> ReferenceCorpusDescriptor:
    index_available = all(
        (source_root / filename).is_file()
        for filename in (MODEL_FILENAME, PROFILE_FILENAME, POET_PROFILE_FILENAME)
    )
    release_id, model_id = _index_header(source_root)
    poem_count, poet_count = _profile_counts(source_root)
    return ReferenceCorpusDescriptor(
        corpus_id=corpus_id,
        display_name=display_name,
        source_root=source_root.resolve(),
        built_in=built_in,
        index_available=index_available and bool(model_id),
        poem_count=poem_count,
        poet_count=poet_count,
        release_id=release_id,
        model_id=model_id,
    )


def list_reference_corpora(
    *,
    include_user: bool = True,
) -> tuple[ReferenceCorpusDescriptor, ...]:
    """Return built-in and available local user reference corpora."""

    rows: list[ReferenceCorpusDescriptor] = []
    built_in = built_in_reference_corpus_root()
    if built_in.is_dir():
        rows.append(
            _descriptor(
                built_in,
                corpus_id=BUILT_IN_CORPUS_ID,
                display_name=BUILT_IN_CORPUS_NAME,
                built_in=True,
            )
        )
    if include_user:
        local_root = user_reference_corpora_root()
        if local_root.is_dir():
            for path in sorted(
                (item for item in local_root.iterdir() if item.is_dir()),
                key=lambda item: item.name.casefold(),
            ):
                rows.append(
                    _descriptor(
                        path,
                        corpus_id=f"user:{path.name}",
                        display_name=_corpus_display_name(path),
                        built_in=False,
                    )
                )
    return tuple(rows)


def reference_corpus(
    corpus_id: str,
    *,
    include_user: bool = True,
) -> ReferenceCorpusDescriptor:
    for descriptor in list_reference_corpora(include_user=include_user):
        if descriptor.corpus_id == corpus_id:
            return descriptor
    raise ReferenceCorpusError("The selected reference corpus is unavailable.")


def load_corpus_index(
    descriptor: ReferenceCorpusDescriptor,
) -> VerseMapReferenceIndex:
    if not descriptor.index_available:
        raise ReferenceCorpusError(
            f"{descriptor.display_name} has no current VerseMap index. "
            "Validate it and build its Standard Profile 1.0 index first."
        )
    signatures = tuple(
        _file_signature(descriptor.source_root / filename)
        for filename in (MODEL_FILENAME, PROFILE_FILENAME, POET_PROFILE_FILENAME)
    )
    if any(signature is None for signature in signatures):
        raise ReferenceCorpusError(
            f"{descriptor.display_name} has an incomplete VerseMap index."
        )
    try:
        return _load_corpus_index_cached(
            str(descriptor.source_root.resolve()),
            tuple(signature for signature in signatures if signature is not None),
        )
    except (OSError, ValueError) as error:
        raise ReferenceCorpusError(
            f"{descriptor.display_name} has an unreadable or stale VerseMap "
            f"index. {error}"
        ) from error


@lru_cache(maxsize=8)
def _load_corpus_index_cached(
    source_root: str,
    signatures: tuple[tuple[str, int, int], ...],
) -> VerseMapReferenceIndex:
    """Parse each unchanged reference index once per application process."""

    del signatures  # The cache key carries automatic size/mtime invalidation.
    return load_reference_index(Path(source_root))


def _safe_upload_path(
    supplied_name: str,
    *,
    default_poet: str,
) -> Path:
    normalized = supplied_name.replace("\\", "/").strip("/")
    parts = list(PurePosixPath(normalized).parts)
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ReferenceCorpusError(
            f"The uploaded path {supplied_name!r} is not a safe relative path."
        )
    if len(parts) == 1:
        parts.insert(0, default_poet.strip() or "Unassigned")
    clean_parts: list[str] = []
    for part in parts:
        clean = _SAFE_COMPONENT.sub("-", part).strip(" .")
        if not clean:
            raise ReferenceCorpusError(
                f"The uploaded path {supplied_name!r} contains an empty name."
            )
        clean_parts.append(clean)
    relative = Path(*clean_parts)
    if relative.suffix.casefold() != ".txt":
        raise ReferenceCorpusError("Reference-corpus uploads must be `.txt` files.")
    if relative.name.casefold().startswith("_versemap_"):
        raise ReferenceCorpusError(
            "Names beginning with `_versemap_` are reserved for generated files."
        )
    return relative


def _validated_uploads(
    uploads: Iterable[tuple[str, bytes]],
    *,
    default_poet: str,
) -> tuple[tuple[Path, bytes], ...]:
    supplied = tuple(uploads)
    normalized_names = [
        PurePosixPath(name.replace("\\", "/").strip("/")).parts
        for name, _ in supplied
    ]
    common_directory = (
        normalized_names[0][0]
        if normalized_names
        and all(
            len(parts) >= 3 and parts[0] == normalized_names[0][0]
            for parts in normalized_names
        )
        else ""
    )
    rows: list[tuple[Path, bytes]] = []
    seen: set[str] = set()
    for supplied_name, payload in supplied:
        relative_name = supplied_name
        if common_directory:
            parts = PurePosixPath(
                supplied_name.replace("\\", "/").strip("/")
            ).parts
            relative_name = PurePosixPath(*parts[1:]).as_posix()
        relative = _safe_upload_path(
            relative_name,
            default_poet=default_poet,
        )
        key = relative.as_posix().casefold()
        if key in seen:
            raise ReferenceCorpusError(
                f"Two uploaded files resolve to {relative.as_posix()}."
            )
        seen.add(key)
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ReferenceCorpusError(
                f"{supplied_name} is not a UTF-8 text file."
            ) from error
        if not text.strip():
            raise ReferenceCorpusError(f"{supplied_name} is empty.")
        rows.append((relative, payload))
    if not rows:
        raise ReferenceCorpusError("Choose at least one UTF-8 `.txt` poem.")
    return tuple(rows)


def _write_info(source_root: Path, display_name: str) -> None:
    parser = configparser.ConfigParser()
    parser["corpus"] = {"name": display_name.strip()}
    with (source_root / CORPUS_INFO_FILENAME).open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        parser.write(handle)


def _write_upload_rows(
    source_root: Path,
    rows: Sequence[tuple[Path, bytes]],
) -> None:
    for relative, payload in rows:
        target = source_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, target)


def create_user_reference_corpus(
    display_name: str,
    uploads: Iterable[tuple[str, bytes]],
    *,
    default_poet: str = "",
) -> ReferenceCorpusDescriptor:
    """Create a validated private reference-corpus source folder."""

    name = display_name.strip()
    slug = _slug(name)
    if not name or not slug:
        raise ReferenceCorpusError("Enter a reference-corpus name.")
    local_root = user_reference_corpora_root()
    local_root.mkdir(parents=True, exist_ok=True)
    target = (local_root / slug).resolve()
    if target.parent != local_root or target.exists():
        raise ReferenceCorpusError(
            "A local reference corpus with that name already exists."
        )
    rows = _validated_uploads(uploads, default_poet=default_poet)
    temporary = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=local_root))
    try:
        _write_upload_rows(temporary, rows)
        _write_info(temporary, name)
        result = build_reference_release(temporary)
        if result.errors:
            raise ReferenceCorpusError(result.errors[0].message)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return _descriptor(
        target,
        corpus_id=f"user:{slug}",
        display_name=name,
        built_in=False,
    )


def add_user_reference_files(
    descriptor: ReferenceCorpusDescriptor,
    uploads: Iterable[tuple[str, bytes]],
    *,
    default_poet: str = "",
) -> BuildResult:
    if descriptor.built_in:
        raise ReferenceCorpusError("The built-in reference corpus is read-only.")
    rows = _validated_uploads(uploads, default_poet=default_poet)
    local_root = user_reference_corpora_root()
    target = descriptor.source_root.resolve()
    try:
        target.relative_to(local_root)
    except ValueError as error:
        raise ReferenceCorpusError("The selected corpus is outside private storage.") from error
    temporary = Path(tempfile.mkdtemp(prefix=".validate-", dir=local_root))
    try:
        shutil.copytree(target, temporary / "corpus", dirs_exist_ok=True)
        _write_upload_rows(temporary / "corpus", rows)
        result = build_reference_release(temporary / "corpus")
        if result.errors:
            raise ReferenceCorpusError(result.errors[0].message)
        _write_upload_rows(target, rows)
        return build_reference_release(target)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def validate_reference_corpus(
    descriptor: ReferenceCorpusDescriptor,
) -> BuildResult:
    return build_reference_release(descriptor.source_root)


def build_reference_corpus_index(
    descriptor: ReferenceCorpusDescriptor,
    *,
    progress=None,
) -> tuple[BuildResult, ProfileBuildResult]:
    if descriptor.built_in:
        raise ReferenceCorpusError(
            "Use the maintainer VerseMap updater for the built-in corpus."
        )
    result, _ = update_reference_release(descriptor.source_root)
    if result.errors:
        raise ReferenceCorpusError(result.errors[0].message)
    profile_result = update_reference_profiles(result, progress=progress)
    return result, profile_result


def delete_user_reference_corpus(
    descriptor: ReferenceCorpusDescriptor,
    *,
    confirmation: str,
) -> None:
    if descriptor.built_in:
        raise ReferenceCorpusError("The built-in reference corpus cannot be deleted.")
    if confirmation != descriptor.display_name:
        raise ReferenceCorpusError("Type the exact corpus name to confirm deletion.")
    local_root = user_reference_corpora_root()
    target = descriptor.source_root.resolve()
    if target.parent != local_root or target == local_root or target.is_symlink():
        raise ReferenceCorpusError("VerseVAD refused an unsafe deletion target.")
    shutil.rmtree(target)


__all__ = [
    "BUILT_IN_CORPUS_ID",
    "BUILT_IN_CORPUS_NAME",
    "ReferenceCorpusDescriptor",
    "ReferenceCorpusError",
    "add_user_reference_files",
    "build_reference_corpus_index",
    "built_in_reference_corpus_root",
    "create_user_reference_corpus",
    "delete_user_reference_corpus",
    "list_reference_corpora",
    "load_corpus_index",
    "reference_corpus",
    "user_reference_corpora_root",
    "validate_reference_corpus",
]
