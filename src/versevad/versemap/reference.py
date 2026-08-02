"""Build a deterministic inventory for the tracked VerseMap reference corpus.

This command deliberately inventories source poems without analyzing or
rewriting them. The later VerseMap feature can build versioned analytical
profiles from this stable, auditable release boundary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

SCHEMA_VERSION = "1.0"
SOURCE_DIRECTORY = Path("resources") / "VerseMap_Reference_Corpus"
MANIFEST_FILENAME = "_versemap_manifest.csv"
RELEASE_FILENAME = "_versemap_release.txt"
GENERATED_FILENAMES = frozenset({MANIFEST_FILENAME, RELEASE_FILENAME})
MANIFEST_FIELDS = (
    "schema_version",
    "corpus_release_id",
    "poet_id",
    "poet_name",
    "poem_id",
    "title",
    "relative_path",
    "source_bytes",
    "source_sha256",
    "canonical_text_sha256",
    "unicode_character_count",
    "physical_line_count",
    "nonblank_line_count",
    "inventory_word_estimate",
    "warning_codes",
)
SHORT_WORD_THRESHOLD = 20
SHORT_LINE_THRESHOLD = 4
LONG_WORD_THRESHOLD = 5_000
LONG_LINE_THRESHOLD = 500
DISPLAYED_ISSUE_LIMIT = 50
PROFILE_DRAFT_FILENAME = "_versemap_profiles.work.csv"
_WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)
_NON_ID_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ValidationIssue:
    """A validation error or non-blocking inventory warning."""

    level: str
    code: str
    path: str
    message: str


@dataclass
class _PoemRecord:
    poet_id: str
    poet_name: str
    poem_id: str
    title: str
    relative_path: str
    source_bytes: int
    source_sha256: str
    canonical_text_sha256: str
    unicode_character_count: int
    physical_line_count: int
    nonblank_line_count: int
    inventory_word_estimate: int
    warning_codes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class BuildResult:
    """The complete in-memory output of one reference-corpus build."""

    source_root: Path
    release_id: str
    poet_count: int
    poem_count: int
    total_source_bytes: int
    manifest_bytes: bytes
    release_bytes: bytes
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == "warning")


@dataclass(frozen=True)
class ProfileBuildResult:
    """Status for the derived, versioned Standard Profile reference index."""

    model_id: str
    analyzed_count: int
    reused_count: int
    poem_count: int
    current: bool


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_source_root() -> Path:
    return _project_root() / SOURCE_DIRECTORY


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(character for character in decomposed if ord(character) < 128)
    slug = _NON_ID_PATTERN.sub("-", ascii_value).strip("-")
    if slug:
        return slug
    return f"poet-{_sha256(value.encode('utf-8'))[:12]}"


def _canonical_text(text: str) -> str:
    """Normalize line endings only; retain spelling, Unicode, and lineation."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def _physical_line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines()) or 1


def _relative_posix(path: Path, source_root: Path) -> str:
    return path.relative_to(source_root).as_posix()


def _add_issue(
    issues: list[ValidationIssue],
    level: str,
    code: str,
    path: str,
    message: str,
) -> None:
    issues.append(ValidationIssue(level=level, code=code, path=path, message=message))


def _read_poem(
    poem_path: Path,
    source_root: Path,
    poet_id: str,
    poet_name: str,
    issues: list[ValidationIssue],
) -> _PoemRecord | None:
    relative_path = _relative_posix(poem_path, source_root)
    payload = poem_path.read_bytes()
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        _add_issue(
            issues,
            "error",
            "not_utf8",
            relative_path,
            f"File is not valid UTF-8 ({error}). Save it as UTF-8 and run the updater again.",
        )
        return None

    canonical = _canonical_text(text)
    if not canonical.strip():
        _add_issue(
            issues,
            "error",
            "empty_poem",
            relative_path,
            "Poem file is empty or contains only whitespace.",
        )
        return None

    physical_lines = _physical_line_count(canonical)
    nonblank_lines = sum(bool(line.strip()) for line in canonical.splitlines())
    word_estimate = len(_WORD_PATTERN.findall(canonical))
    stable_path = relative_path.casefold()
    poem_digest = _sha256(f"{poet_id}\0{stable_path}".encode("utf-8"))[:16]
    record = _PoemRecord(
        poet_id=poet_id,
        poet_name=poet_name,
        poem_id=f"{poet_id}-{poem_digest}",
        title=poem_path.stem,
        relative_path=relative_path,
        source_bytes=len(payload),
        source_sha256=_sha256(payload),
        canonical_text_sha256=_sha256(canonical.encode("utf-8")),
        unicode_character_count=len(canonical),
        physical_line_count=physical_lines,
        nonblank_line_count=nonblank_lines,
        inventory_word_estimate=word_estimate,
    )

    if word_estimate < SHORT_WORD_THRESHOLD or nonblank_lines < SHORT_LINE_THRESHOLD:
        record.warning_codes.add("suspiciously_short")
        _add_issue(
            issues,
            "warning",
            "suspiciously_short",
            relative_path,
            f"Only {word_estimate} estimated words and {nonblank_lines} nonblank lines; verify that this is a complete poem.",
        )
    if word_estimate > LONG_WORD_THRESHOLD or nonblank_lines > LONG_LINE_THRESHOLD:
        record.warning_codes.add("suspiciously_long")
        _add_issue(
            issues,
            "warning",
            "suspiciously_long",
            relative_path,
            f"{word_estimate} estimated words and {nonblank_lines} nonblank lines; verify that this is one poem rather than a collection.",
        )
    return record


def _release_id(records: Sequence[_PoemRecord]) -> str:
    digest = hashlib.sha256()
    digest.update(f"versemap-reference-schema:{SCHEMA_VERSION}\n".encode("utf-8"))
    for record in records:
        digest.update(
            (
                f"{record.poet_id}\0{record.poet_name}\0{record.relative_path}"
                f"\0{record.canonical_text_sha256}\n"
            ).encode("utf-8")
        )
    return f"versemap-reference-{digest.hexdigest()[:16]}"


def _manifest_bytes(records: Sequence[_PoemRecord], release_id: str) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "schema_version": SCHEMA_VERSION,
                "corpus_release_id": release_id,
                "poet_id": record.poet_id,
                "poet_name": record.poet_name,
                "poem_id": record.poem_id,
                "title": record.title,
                "relative_path": record.relative_path,
                "source_bytes": record.source_bytes,
                "source_sha256": record.source_sha256,
                "canonical_text_sha256": record.canonical_text_sha256,
                "unicode_character_count": record.unicode_character_count,
                "physical_line_count": record.physical_line_count,
                "nonblank_line_count": record.nonblank_line_count,
                "inventory_word_estimate": record.inventory_word_estimate,
                "warning_codes": "|".join(sorted(record.warning_codes)),
            }
        )
    return output.getvalue().encode("utf-8")


def _release_bytes(
    *,
    release_id: str,
    poet_count: int,
    poem_count: int,
    total_source_bytes: int,
    manifest_bytes: bytes,
    issues: Sequence[ValidationIssue],
) -> bytes:
    warning_counts = Counter(
        issue.code for issue in issues if issue.level == "warning"
    )
    lines = [
        "VerseMap Reference Corpus Release",
        f"schema_version: {SCHEMA_VERSION}",
        f"corpus_release_id: {release_id}",
        f"poet_count: {poet_count}",
        f"poem_count: {poem_count}",
        f"total_source_bytes: {total_source_bytes}",
        f"manifest_sha256: {_sha256(manifest_bytes)}",
        f"warning_count: {sum(warning_counts.values())}",
    ]
    for code, count in sorted(warning_counts.items()):
        lines.append(f"warning_{code}: {count}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_reference_release(source_root: Path | str | None = None) -> BuildResult:
    """Validate and build deterministic release files without writing them."""

    root = Path(source_root) if source_root is not None else _default_source_root()
    root = root.resolve()
    issues: list[ValidationIssue] = []
    records: list[_PoemRecord] = []

    if not root.is_dir():
        _add_issue(
            issues,
            "error",
            "missing_source_root",
            str(root),
            "VerseMap reference folder does not exist.",
        )
        return BuildResult(root, "", 0, 0, 0, b"", b"", tuple(issues))

    poet_directories = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )
    if not poet_directories:
        _add_issue(
            issues,
            "error",
            "no_poets",
            str(root),
            "No poet folders were found.",
        )

    poet_ids: dict[str, str] = {}
    seen_paths: dict[str, str] = {}
    for poet_directory in poet_directories:
        poet_name = poet_directory.name
        poet_id = _stable_slug(poet_name)
        previous_poet = poet_ids.get(poet_id)
        if previous_poet is not None:
            _add_issue(
                issues,
                "error",
                "poet_id_collision",
                _relative_posix(poet_directory, root),
                f'Poet folders "{previous_poet}" and "{poet_name}" resolve to the same stable ID.',
            )
            continue
        poet_ids[poet_id] = poet_name

        poem_paths = sorted(
            (
                path
                for path in poet_directory.rglob("*")
                if path.is_file()
                and path.suffix.casefold() == ".txt"
                and path.name not in GENERATED_FILENAMES
            ),
            key=lambda path: (
                _relative_posix(path, root).casefold(),
                _relative_posix(path, root),
            ),
        )
        if not poem_paths:
            _add_issue(
                issues,
                "error",
                "poet_has_no_poems",
                _relative_posix(poet_directory, root),
                "Poet folder contains no .txt poem files.",
            )
            continue

        for poem_path in poem_paths:
            relative_path = _relative_posix(poem_path, root)
            path_key = relative_path.casefold()
            previous_path = seen_paths.get(path_key)
            if previous_path is not None:
                _add_issue(
                    issues,
                    "error",
                    "path_case_collision",
                    relative_path,
                    f'Path conflicts with "{previous_path}" on case-insensitive systems.',
                )
                continue
            seen_paths[path_key] = relative_path
            record = _read_poem(poem_path, root, poet_id, poet_name, issues)
            if record is not None:
                records.append(record)

    records.sort(
        key=lambda record: (
            record.poet_name.casefold(),
            record.poet_name,
            record.relative_path.casefold(),
            record.relative_path,
        )
    )

    content_groups: dict[str, list[_PoemRecord]] = defaultdict(list)
    title_groups: dict[tuple[str, str], list[_PoemRecord]] = defaultdict(list)
    poem_id_groups: dict[str, list[_PoemRecord]] = defaultdict(list)
    for record in records:
        content_groups[record.canonical_text_sha256].append(record)
        title_groups[(record.poet_id, record.title.casefold())].append(record)
        poem_id_groups[record.poem_id].append(record)

    for group in content_groups.values():
        if len(group) < 2:
            continue
        paths = ", ".join(record.relative_path for record in group)
        for record in group:
            record.warning_codes.add("duplicate_text")
        _add_issue(
            issues,
            "warning",
            "duplicate_text",
            group[0].relative_path,
            f"Identical canonical text appears in {len(group)} files: {paths}",
        )

    for group in title_groups.values():
        if len(group) < 2:
            continue
        paths = ", ".join(record.relative_path for record in group)
        for record in group:
            record.warning_codes.add("duplicate_title")
        _add_issue(
            issues,
            "warning",
            "duplicate_title",
            group[0].relative_path,
            f"Repeated filename title within one poet folder: {paths}",
        )

    for group in poem_id_groups.values():
        if len(group) > 1:
            paths = ", ".join(record.relative_path for record in group)
            _add_issue(
                issues,
                "error",
                "poem_id_collision",
                group[0].relative_path,
                f"Stable poem ID collision: {paths}",
            )

    if not records:
        _add_issue(
            issues,
            "error",
            "no_poems",
            str(root),
            "No valid UTF-8 .txt poem files were found.",
        )

    release_id = _release_id(records) if records else ""
    manifest = _manifest_bytes(records, release_id) if records else b""
    release = (
        _release_bytes(
            release_id=release_id,
            poet_count=len({record.poet_id for record in records}),
            poem_count=len(records),
            total_source_bytes=sum(record.source_bytes for record in records),
            manifest_bytes=manifest,
            issues=issues,
        )
        if records
        else b""
    )
    ordered_issues = tuple(
        sorted(
            issues,
            key=lambda issue: (
                0 if issue.level == "error" else 1,
                issue.code,
                issue.path.casefold(),
                issue.path,
            ),
        )
    )
    return BuildResult(
        source_root=root,
        release_id=release_id,
        poet_count=len({record.poet_id for record in records}),
        poem_count=len(records),
        total_source_bytes=sum(record.source_bytes for record in records),
        manifest_bytes=manifest,
        release_bytes=release,
        issues=ordered_issues,
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _matches(path: Path, expected: bytes) -> bool:
    return path.is_file() and path.read_bytes() == expected


def _manifest_rows(payload: bytes) -> tuple[dict[str, str], ...]:
    return tuple(
        csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    )


def _existing_profile_rows(source_root: Path) -> dict[tuple[str, str], dict[str, str]]:
    from versevad.versemap.model import PROFILE_FILENAME
    from versevad.versemap.profile import PROFILE_BUILD_ID, PROFILE_ID

    existing: dict[tuple[str, str], dict[str, str]] = {}
    for path in (
        source_root / PROFILE_FILENAME,
        source_root / PROFILE_DRAFT_FILENAME,
    ):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = tuple(csv.DictReader(handle))
        existing.update(
            {
                (row.get("poem_id", ""), row.get("source_sha256", "")): row
                for row in rows
                if row.get("profile_id", "") in ("", PROFILE_ID)
                and row.get("profile_build_id", "") in ("", PROFILE_BUILD_ID)
            }
        )
    return existing


def _raw_profile_row(manifest_row: dict[str, str], profile) -> dict[str, object]:
    from versevad.versemap.profile import PROFILE_BUILD_ID

    row: dict[str, object] = {
        **manifest_row,
        "profile_build_id": PROFILE_BUILD_ID,
        "content_token_count": profile.content_token_count,
    }
    for observation in profile.observations:
        row[observation.feature_id] = (
            "" if observation.value is None else f"{observation.value:.12g}"
        )
        row[f"{observation.feature_id}__eligible"] = observation.eligible_count
        row[f"{observation.feature_id}__matched"] = observation.matched_count
    for metric_id, value in profile.browser_diagnostics:
        row[metric_id] = "" if value is None else f"{value:.12g}"
    row["vad_midpoint_matched_observations"] = (
        profile.vad_midpoint_matched_observations
    )
    return row


def _existing_browser_vad_rows(
    source_root: Path,
) -> dict[tuple[str, str], dict[str, str]]:
    from versevad.versemap.model import BROWSER_VAD_FILENAME
    from versevad.versemap.profile import (
        BROWSER_VAD_DIAGNOSTIC_IDS,
        PROFILE_BUILD_ID,
        PROFILE_ID,
    )

    for path in (
        source_root / BROWSER_VAD_FILENAME,
        source_root / PROFILE_DRAFT_FILENAME,
    ):
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not set(BROWSER_VAD_DIAGNOSTIC_IDS).issubset(
                    reader.fieldnames or ()
                ):
                    continue
                rows = tuple(reader)
        except (OSError, csv.Error):
            continue
        return {
            (row.get("poem_id", ""), row.get("source_sha256", "")): row
            for row in rows
            if row.get("profile_id", "") in ("", PROFILE_ID)
            and row.get("profile_build_id") == PROFILE_BUILD_ID
        }
    return {}


def _browser_vad_bytes(
    rows: Sequence[dict[str, object]],
    *,
    release_id: str,
) -> bytes:
    from versevad.versemap.profile import (
        BROWSER_VAD_DIAGNOSTIC_IDS,
        PROFILE_BUILD_ID,
        PROFILE_ID,
    )

    fields = (
        "schema_version",
        "profile_id",
        "profile_build_id",
        "reference_release_id",
        "poet_id",
        "poet_name",
        "poem_id",
        "title",
        "relative_path",
        "source_sha256",
        "vad_midpoint_matched_observations",
        *BROWSER_VAD_DIAGNOSTIC_IDS,
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **{field: row.get(field, "") for field in fields},
                "schema_version": SCHEMA_VERSION,
                "profile_id": PROFILE_ID,
                "profile_build_id": PROFILE_BUILD_ID,
                "reference_release_id": release_id,
            }
        )
    return output.getvalue().encode("utf-8")


def _browser_vad_is_current(result: BuildResult) -> bool:
    from versevad.versemap.model import BROWSER_VAD_FILENAME

    current = _existing_browser_vad_rows(result.source_root)
    manifest = _manifest_rows(result.manifest_bytes)
    expected = {
        (row["poem_id"], row["source_sha256"]) for row in manifest
    }
    if set(current) != expected:
        return False
    return all(
        row.get("reference_release_id") == result.release_id
        for row in current.values()
    ) and (result.source_root / BROWSER_VAD_FILENAME).is_file()


def _write_profile_draft(
    source_root: Path,
    rows: Sequence[dict[str, object]],
) -> None:
    if not rows:
        return
    fields = tuple(rows[0])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write(
        source_root / PROFILE_DRAFT_FILENAME,
        output.getvalue().encode("utf-8"),
    )


def _index_is_current(result: BuildResult) -> tuple[bool, str]:
    from versevad.versemap.model import (
        BROWSER_VAD_FILENAME,
        MODEL_FILENAME,
        POET_PROFILE_FILENAME,
        PROFILE_FILENAME,
    )
    from versevad.versemap.profile import PROFILE_BUILD_ID, PROFILE_ID

    paths = (
        result.source_root / PROFILE_FILENAME,
        result.source_root / POET_PROFILE_FILENAME,
        result.source_root / MODEL_FILENAME,
    )
    if not all(path.is_file() for path in paths):
        return False, ""
    try:
        with paths[2].open("r", encoding="utf-8-sig", newline="") as handle:
            model_rows = tuple(csv.DictReader(handle))
        with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
            profile_rows = tuple(csv.DictReader(handle))
    except (OSError, csv.Error):
        return False, ""
    if not model_rows:
        return False, ""
    header = model_rows[0]
    manifest = _manifest_rows(result.manifest_bytes)
    current_sources = {
        (row["poem_id"], row["source_sha256"]) for row in manifest
    }
    indexed_sources = {
        (row.get("poem_id", ""), row.get("source_sha256", ""))
        for row in profile_rows
    }
    current = (
        header.get("profile_id") == PROFILE_ID
        and header.get("profile_build_id") == PROFILE_BUILD_ID
        and header.get("reference_release_id") == result.release_id
        and header.get("reference_release_sha256") == _sha256(result.release_bytes)
        and current_sources == indexed_sources
        and all(
            row.get("profile_build_id") == PROFILE_BUILD_ID
            for row in profile_rows
        )
    )
    return current, header.get("model_id", "")


def update_reference_profiles(
    result: BuildResult,
    *,
    check: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
) -> ProfileBuildResult:
    """Build the analytical index while reusing unchanged poem profiles."""

    from versevad.application import AnalysisRequest, run_workspace_analysis
    from versevad.models import PhrasePolicy, StopwordMode
    from versevad.preprocessing import SpacyEnglishPreprocessor
    from versevad.versemap.model import (
        BROWSER_VAD_FILENAME,
        MODEL_FILENAME,
        POET_PROFILE_FILENAME,
        PROFILE_FILENAME,
        build_reference_model_bytes,
    )
    from versevad.versemap.profile import (
        PROFILE_BUILD_ID,
        extract_standard_profile,
        standard_aoa_configuration,
        standard_concreteness_configuration,
        standard_frequency_configuration,
        standard_lexical_style_configuration,
    )

    current, current_model_id = _index_is_current(result)
    browser_vad_current = _browser_vad_is_current(result)
    if check or (current and browser_vad_current):
        return ProfileBuildResult(
            model_id=current_model_id,
            analyzed_count=0,
            reused_count=(
                result.poem_count if current and browser_vad_current else 0
            ),
            poem_count=result.poem_count,
            current=current and browser_vad_current,
        )

    manifest = _manifest_rows(result.manifest_bytes)
    existing = _existing_profile_rows(result.source_root)
    existing_browser_vad = _existing_browser_vad_rows(result.source_root)
    rows: list[dict[str, object]] = []
    processor = SpacyEnglishPreprocessor()
    analyzed = reused = 0
    for position, manifest_row in enumerate(manifest, start=1):
        cache_key = (manifest_row["poem_id"], manifest_row["source_sha256"])
        cached = existing.get(cache_key)
        cached_browser_vad = existing_browser_vad.get(cache_key)
        if cached is not None and cached_browser_vad is not None:
            migrated = dict(cached)
            migrated["profile_build_id"] = PROFILE_BUILD_ID
            migrated.update(cached_browser_vad)
            rows.append(migrated)
            reused += 1
        else:
            poem_path = result.source_root / Path(manifest_row["relative_path"])
            text = poem_path.read_text(encoding="utf-8-sig")
            backfill_vad_only = cached is not None
            workspace = run_workspace_analysis(
                AnalysisRequest(
                    project_name="VerseMap Reference Corpus",
                    title=manifest_row["title"],
                    original_text=text,
                    text_id=manifest_row["poem_id"],
                    lexicon_ids=(
                        ("nrc_vad_v2_1",)
                        if backfill_vad_only
                        else ("nrc_vad_v2_1", "nrc_emotion_v0_92")
                    ),
                    phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
                    minimum_match_requirement=1,
                    stopword_mode=StopwordMode.STANDARD,
                    scenario_id="versemap-reference-profile-1.0",
                    include_concreteness=not backfill_vad_only,
                    concreteness_configuration=(
                        standard_concreteness_configuration()
                    ),
                    include_frequency=not backfill_vad_only,
                    frequency_configuration=standard_frequency_configuration(),
                    include_aoa=not backfill_vad_only,
                    aoa_configuration=standard_aoa_configuration(),
                    include_lexical_style=not backfill_vad_only,
                    lexical_style_configuration=(
                        standard_lexical_style_configuration()
                    ),
                    analysis_cache_enabled=False,
                    performance_diagnostics=False,
                ),
                preprocessor=processor,
            )
            profile = extract_standard_profile(workspace)
            if cached is None:
                rows.append(_raw_profile_row(manifest_row, profile))
            else:
                migrated = dict(cached)
                migrated["profile_build_id"] = PROFILE_BUILD_ID
                for metric_id, value in profile.browser_diagnostics:
                    migrated[metric_id] = (
                        "" if value is None else f"{value:.12g}"
                    )
                migrated["vad_midpoint_matched_observations"] = (
                    profile.vad_midpoint_matched_observations
                )
                rows.append(migrated)
            analyzed += 1
        if progress is not None:
            progress(position, len(manifest), manifest_row["title"])
        if position % 25 == 0:
            _write_profile_draft(result.source_root, rows)

    profile_bytes, poet_bytes, model_bytes, model_id = build_reference_model_bytes(
        rows,
        reference_release_id=result.release_id,
        reference_release_sha256=_sha256(result.release_bytes),
    )
    _atomic_write(result.source_root / PROFILE_FILENAME, profile_bytes)
    _atomic_write(result.source_root / POET_PROFILE_FILENAME, poet_bytes)
    _atomic_write(result.source_root / MODEL_FILENAME, model_bytes)
    _atomic_write(
        result.source_root / BROWSER_VAD_FILENAME,
        _browser_vad_bytes(rows, release_id=result.release_id),
    )
    (result.source_root / PROFILE_DRAFT_FILENAME).unlink(missing_ok=True)
    return ProfileBuildResult(
        model_id=model_id,
        analyzed_count=analyzed,
        reused_count=reused,
        poem_count=len(rows),
        current=False,
    )


def update_reference_release(
    source_root: Path | str | None = None,
    *,
    check: bool = False,
) -> tuple[BuildResult, bool]:
    """Build and optionally write the manifest and release record.

    Returns the build result and whether both on-disk generated files already
    matched the expected deterministic output before any writes.
    """

    result = build_reference_release(source_root)
    if result.errors:
        return result, False

    manifest_path = result.source_root / MANIFEST_FILENAME
    release_path = result.source_root / RELEASE_FILENAME
    current = _matches(manifest_path, result.manifest_bytes) and _matches(
        release_path, result.release_bytes
    )
    if not check and not current:
        _atomic_write(manifest_path, result.manifest_bytes)
        _atomic_write(release_path, result.release_bytes)
    return result, current


def _print_issues(issues: Iterable[ValidationIssue]) -> None:
    issue_list = list(issues)
    for issue in issue_list[:DISPLAYED_ISSUE_LIMIT]:
        print(f"{issue.level.upper():7} {issue.code}: {issue.path}")
        print(f"        {issue.message}")
    remaining = len(issue_list) - DISPLAYED_ISSUE_LIMIT
    if remaining > 0:
        print(
            f"... and {remaining} additional messages not displayed; warning "
            "codes are recorded in the manifest."
        )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="versevad-update-versemap",
        description=(
            "Validate the tracked public-domain VerseMap source folders and "
            "rebuild their deterministic manifest."
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help=(
            "Override the reference-corpus folder. Defaults to "
            "resources/VerseMap_Reference_Corpus in this VerseVAD checkout."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that generated release files are current without changing them.",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help=(
            "Update only the source inventory. Maintainer launchers normally "
            "build both the inventory and Standard Profile reference index."
        ),
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return a failure status when non-blocking inventory warnings exist.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    result, current = update_reference_release(
        arguments.source_root,
        check=arguments.check,
    )

    if result.issues:
        _print_issues(result.issues)
        print()
    if result.errors:
        print(
            f"VerseMap reference update stopped: {len(result.errors)} blocking "
            "validation error(s). No release files were changed."
        )
        return 2

    action = "checked" if arguments.check else ("unchanged" if current else "updated")
    print(f"VerseMap reference corpus {action}.")
    print(f"Release: {result.release_id}")
    print(f"Poets: {result.poet_count}")
    print(f"Poems: {result.poem_count}")
    print(f"Source bytes: {result.total_source_bytes}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Manifest: {result.source_root / MANIFEST_FILENAME}")
    print(f"Release record: {result.source_root / RELEASE_FILENAME}")

    profile_result = None
    if not arguments.source_only:
        if not arguments.check:
            print()
            print("Building VerseMap Standard Profile 1.0 reference index...")

        def report_progress(completed: int, total: int, title: str) -> None:
            if completed == 1 or completed == total or completed % 25 == 0:
                print(f"  {completed:,}/{total:,} profiles ready - {title}")

        profile_result = update_reference_profiles(
            result,
            check=arguments.check,
            progress=report_progress,
        )
        if arguments.check:
            print(
                "Analytical index: "
                + ("current" if profile_result.current else "stale or missing")
            )
        else:
            print(f"Model: {profile_result.model_id}")
            print(f"Profiles analyzed: {profile_result.analyzed_count}")
            print(f"Profiles reused: {profile_result.reused_count}")

    if arguments.check and (
        not current
        or (profile_result is not None and not profile_result.current)
    ):
        print()
        print(
            "The generated files are stale. Run versevad-update-versemap "
            "without --check, then review and commit the changes."
        )
        return 1
    if arguments.strict_warnings and result.warnings:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
