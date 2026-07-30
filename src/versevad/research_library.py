"""Versioned saved analyses, recoverable drafts, and contextual research notes.

The research library is intentionally separate from project/corpus storage.
Local installations retain its SQLite database in ``projects/``; hosted
deployments point the same repository at their isolated temporary session
directory.  Saved revisions are immutable and serialized as restricted,
compressed JSON rather than executable pickle data.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import os
import sqlite3
import zlib
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import MISSING, dataclass, fields, is_dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


LIBRARY_SCHEMA_VERSION = 1
_ALLOWED_CLASS_PREFIX = "versevad."


class ResearchLibraryError(RuntimeError):
    """Raised when saved research cannot be validated or restored safely."""


@dataclass(frozen=True)
class LibraryItem:
    item_id: str
    parent_type: str
    workspace_id: str
    title: str
    author: str
    status: str
    current_revision_id: str
    project_id: str
    created_at: str
    updated_at: str
    last_opened_at: str


@dataclass(frozen=True)
class LibraryRevision:
    revision_id: str
    item_id: str
    revision_number: int
    storage_mode: str
    text_sha256: str
    payload_sha256: str
    profile_name: str
    software_version: str
    settings: object
    data_versions: object
    warnings: object
    summary: object
    artifact_bundle: bytes | None
    created_at: str


@dataclass(frozen=True)
class ResearchNote:
    note_id: str
    parent_type: str
    parent_id: str
    analysis_id: str
    project_id: str
    module: str
    metric: str
    anchor_type: str
    anchor_label: str
    title: str
    body: str
    tags: tuple[str, ...]
    include_in_export: bool
    created_at: str
    updated_at: str


def _qualified_name(value: object) -> str:
    cls = value if isinstance(value, type) else type(value)
    return f"{cls.__module__}:{cls.__qualname__}"


def _encode(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {
            "$type": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, Path):
        return {"$type": "path", "value": str(value)}
    if isinstance(value, datetime):
        return {"$type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$type": "date", "value": value.isoformat()}
    if isinstance(value, time):
        return {"$type": "time", "value": value.isoformat()}
    if isinstance(value, Enum):
        qualified_name = _qualified_name(value)
        if not qualified_name.startswith(_ALLOWED_CLASS_PREFIX):
            raise ResearchLibraryError(
                f"Cannot serialize enum outside VerseVAD: {qualified_name}"
            )
        return {
            "$type": "enum",
            "class": qualified_name,
            "name": value.name,
        }
    if is_dataclass(value) and not isinstance(value, type):
        qualified_name = _qualified_name(value)
        if not qualified_name.startswith(_ALLOWED_CLASS_PREFIX):
            raise ResearchLibraryError(
                f"Cannot serialize dataclass outside VerseVAD: {qualified_name}"
            )
        return {
            "$type": "dataclass",
            "class": qualified_name,
            "fields": {
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
            },
        }
    if isinstance(value, Mapping):
        return {
            "$type": "mapping",
            "items": [
                [_encode(key), _encode(item_value)]
                for key, item_value in value.items()
            ],
        }
    if isinstance(value, tuple):
        return {"$type": "tuple", "items": [_encode(item) for item in value]}
    if isinstance(value, list):
        return {"$type": "list", "items": [_encode(item) for item in value]}
    if isinstance(value, frozenset):
        return {
            "$type": "frozenset",
            "items": [_encode(item) for item in sorted(value, key=repr)],
        }
    if isinstance(value, set):
        return {
            "$type": "set",
            "items": [_encode(item) for item in sorted(value, key=repr)],
        }
    raise ResearchLibraryError(
        f"Unsupported saved-analysis value: {_qualified_name(value)}"
    )


def _resolve_class(qualified_name: str) -> type:
    if not qualified_name.startswith(_ALLOWED_CLASS_PREFIX):
        raise ResearchLibraryError(
            f"Saved analysis references a disallowed class: {qualified_name}"
        )
    module_name, separator, qualname = qualified_name.partition(":")
    if not separator or "<locals>" in qualname:
        raise ResearchLibraryError(
            f"Saved analysis contains an invalid class name: {qualified_name}"
        )
    module = importlib.import_module(module_name)
    resolved: object = module
    for component in qualname.split("."):
        resolved = getattr(resolved, component)
    if not isinstance(resolved, type):
        raise ResearchLibraryError(
            f"Saved analysis class did not resolve to a type: {qualified_name}"
        )
    return resolved


def _decode(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if not isinstance(value, dict):
        raise ResearchLibraryError("Saved analysis contains malformed JSON.")
    value_type = value.get("$type")
    if value_type == "bytes":
        return base64.b64decode(str(value["base64"]), validate=True)
    if value_type == "path":
        return Path(str(value["value"]))
    if value_type == "datetime":
        return datetime.fromisoformat(str(value["value"]))
    if value_type == "date":
        return date.fromisoformat(str(value["value"]))
    if value_type == "time":
        return time.fromisoformat(str(value["value"]))
    if value_type == "enum":
        cls = _resolve_class(str(value["class"]))
        if not issubclass(cls, Enum):
            raise ResearchLibraryError("Saved enum class is no longer an enum.")
        return cls[str(value["name"])]
    if value_type == "dataclass":
        cls = _resolve_class(str(value["class"]))
        if not is_dataclass(cls):
            raise ResearchLibraryError(
                "Saved dataclass class is no longer a dataclass."
            )
        raw_fields = value.get("fields")
        if not isinstance(raw_fields, dict):
            raise ResearchLibraryError("Saved dataclass fields are malformed.")
        class_fields = {field.name: field for field in fields(cls)}
        accepted = set(class_fields)
        unknown = set(raw_fields) - accepted
        if unknown:
            raise ResearchLibraryError(
                "Saved analysis contains fields the current class does not "
                f"accept: {sorted(unknown)}"
            )
        # Restoring an immutable historical result must not rerun contemporary
        # ``__post_init__`` validation or derived calculations.  That could
        # silently reinterpret the old result, and module reloads can also
        # leave identity-sensitive enums belonging to an earlier class object.
        # Construct the allowlisted dataclass without executing application
        # code, then assign every persisted field directly.
        restored = cls.__new__(cls)
        for field_name, field in class_fields.items():
            if field_name in raw_fields:
                field_value = _decode(raw_fields[field_name])
            elif field.default is not MISSING:
                field_value = field.default
            elif field.default_factory is not MISSING:
                field_value = field.default_factory()
            else:
                raise ResearchLibraryError(
                    "Saved analysis is missing required field "
                    f"{cls.__qualname__}.{field_name}."
                )
            # Early saved analyses recorded a few enum-backed settings as
            # their plain string values. Coerce those historical values to
            # the current enum type without rerunning dataclass validation or
            # recalculating the immutable analysis.
            if isinstance(field.default, Enum) and isinstance(field_value, str):
                enum_type = type(field.default)
                try:
                    field_value = enum_type(field_value)
                except ValueError:
                    try:
                        field_value = enum_type[field_value]
                    except KeyError as error:
                        raise ResearchLibraryError(
                            "Saved analysis contains an unsupported value for "
                            f"{cls.__qualname__}.{field_name}: {field_value!r}."
                        ) from error
            object.__setattr__(restored, field_name, field_value)
        return restored
    raw_items = value.get("items")
    if value_type in {"mapping", "tuple", "list", "set", "frozenset"}:
        if not isinstance(raw_items, list):
            raise ResearchLibraryError("Saved collection is malformed.")
        if value_type == "mapping":
            decoded: dict[object, object] = {}
            for pair in raw_items:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ResearchLibraryError("Saved mapping entry is malformed.")
                decoded[_decode(pair[0])] = _decode(pair[1])
            return decoded
        decoded_items = [_decode(item) for item in raw_items]
        if value_type == "tuple":
            return tuple(decoded_items)
        if value_type == "list":
            return decoded_items
        if value_type == "set":
            return set(decoded_items)
        return frozenset(decoded_items)
    raise ResearchLibraryError("Saved analysis contains an unknown value type.")


def serialize_value(value: object) -> bytes:
    """Return deterministic, compressed, non-executable saved-analysis bytes."""

    raw = json.dumps(
        _encode(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return zlib.compress(raw, level=9)


def deserialize_value(payload: bytes) -> object:
    """Restore a value written by :func:`serialize_value`."""

    try:
        raw = zlib.decompress(payload)
        encoded = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResearchLibraryError("Saved analysis payload is corrupt.") from error
    return _decode(encoded)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _identifier(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def default_research_library_path() -> Path:
    """Return the source-controlled installation's private library path."""

    configured = os.environ.get("VERSEVAD_RESEARCH_LIBRARY_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[2] / "projects" / "analysis_library.sqlite3"


def session_research_library_path(
    session_state: MutableMapping[str, object],
) -> Path:
    """Return local persistent or hosted session-only storage as appropriate."""

    if os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT") == "1":
        try:
            from versevad.deployment import cloud_session_database_path
        except ImportError as error:  # pragma: no cover - deployment packaging guard
            raise ResearchLibraryError(
                "Hosted-session storage is unavailable in this installation."
            ) from error
        return cloud_session_database_path(session_state).with_name(
            "analysis_library.sqlite3"
        )
    return default_research_library_path()


class ResearchLibraryRepository:
    """Transactional access to saved research and contextual notes."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(
            database_path or default_research_library_path()
        ).resolve()
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()
        except (OSError, sqlite3.Error) as error:
            raise ResearchLibraryError(
                "VerseVAD could not open the private analysis library at "
                f"{self.database_path}."
            ) from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_library_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS library_items (
                    item_id TEXT PRIMARY KEY,
                    parent_type TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('saved', 'draft')),
                    current_revision_id TEXT NOT NULL DEFAULT '',
                    project_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS library_revisions (
                    revision_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL REFERENCES library_items(item_id)
                        ON DELETE CASCADE,
                    revision_number INTEGER NOT NULL CHECK(revision_number >= 1),
                    storage_mode TEXT NOT NULL
                        CHECK(storage_mode IN ('full', 'results_only', 'draft')),
                    text_sha256 TEXT NOT NULL DEFAULT '',
                    payload_sha256 TEXT NOT NULL,
                    profile_name TEXT NOT NULL DEFAULT '',
                    software_version TEXT NOT NULL,
                    settings_payload BLOB NOT NULL,
                    data_versions_payload BLOB NOT NULL,
                    warnings_payload BLOB NOT NULL,
                    summary_payload BLOB NOT NULL,
                    analysis_payload BLOB,
                    artifact_bundle BLOB,
                    created_at TEXT NOT NULL,
                    UNIQUE(item_id, revision_number)
                );
                CREATE TABLE IF NOT EXISTS research_notes (
                    note_id TEXT PRIMARY KEY,
                    parent_type TEXT NOT NULL,
                    parent_id TEXT NOT NULL,
                    analysis_id TEXT NOT NULL DEFAULT '',
                    project_id TEXT NOT NULL DEFAULT '',
                    module TEXT NOT NULL DEFAULT '',
                    metric TEXT NOT NULL DEFAULT '',
                    anchor_type TEXT NOT NULL DEFAULT 'analysis',
                    anchor_label TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags_payload BLOB NOT NULL,
                    include_in_export INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_library_items_status_updated
                    ON library_items(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_library_revisions_item
                    ON library_revisions(item_id, revision_number DESC);
                CREATE INDEX IF NOT EXISTS idx_notes_parent
                    ON research_notes(parent_type, parent_id, updated_at DESC);
                """
            )
            row = connection.execute(
                "SELECT value FROM research_library_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO research_library_meta(key, value) VALUES (?, ?)",
                    ("schema_version", str(LIBRARY_SCHEMA_VERSION)),
                )
            elif int(row["value"]) != LIBRARY_SCHEMA_VERSION:
                raise ResearchLibraryError(
                    "This analysis library uses an unsupported schema version."
                )

    @staticmethod
    def _item(row: sqlite3.Row) -> LibraryItem:
        return LibraryItem(**dict(row))

    @staticmethod
    def _revision(row: sqlite3.Row) -> LibraryRevision:
        return LibraryRevision(
            revision_id=row["revision_id"],
            item_id=row["item_id"],
            revision_number=row["revision_number"],
            storage_mode=row["storage_mode"],
            text_sha256=row["text_sha256"],
            payload_sha256=row["payload_sha256"],
            profile_name=row["profile_name"],
            software_version=row["software_version"],
            settings=deserialize_value(row["settings_payload"]),
            data_versions=deserialize_value(row["data_versions_payload"]),
            warnings=deserialize_value(row["warnings_payload"]),
            summary=deserialize_value(row["summary_payload"]),
            artifact_bundle=row["artifact_bundle"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _note(row: sqlite3.Row) -> ResearchNote:
        tags = deserialize_value(row["tags_payload"])
        return ResearchNote(
            note_id=row["note_id"],
            parent_type=row["parent_type"],
            parent_id=row["parent_id"],
            analysis_id=row["analysis_id"],
            project_id=row["project_id"],
            module=row["module"],
            metric=row["metric"],
            anchor_type=row["anchor_type"],
            anchor_label=row["anchor_label"],
            title=row["title"],
            body=row["body"],
            tags=tuple(str(tag) for tag in tags),
            include_in_export=bool(row["include_in_export"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def save_revision(
        self,
        *,
        parent_type: str,
        workspace_id: str,
        title: str,
        software_version: str,
        payload: object | None,
        storage_mode: str,
        text_sha256: str = "",
        author: str = "",
        status: str = "saved",
        profile_name: str = "",
        settings: object = None,
        data_versions: object = None,
        warnings: object = None,
        summary: object = None,
        artifact_bundle: bytes | None = None,
        item_id: str | None = None,
        project_id: str = "",
        deduplicate: bool = False,
    ) -> tuple[LibraryItem, LibraryRevision, bool]:
        """Append one immutable revision, optionally deduplicating autosaves."""

        if status not in {"saved", "draft"}:
            raise ResearchLibraryError("Library item status must be saved or draft.")
        if storage_mode not in {"full", "results_only", "draft"}:
            raise ResearchLibraryError("Unknown analysis storage mode.")
        if storage_mode in {"full", "draft"} and payload is None:
            raise ResearchLibraryError(
                "Full analyses and recoverable drafts require a payload."
            )
        item_title = title.strip() or "Untitled analysis"
        analysis_payload = (
            serialize_value(payload) if payload is not None else None
        )
        payload_sha256 = hashlib.sha256(
            analysis_payload
            if analysis_payload is not None
            else serialize_value(
                {
                    "summary": summary,
                    "settings": settings,
                    "artifact": hashlib.sha256(
                        artifact_bundle or b""
                    ).hexdigest(),
                }
            )
        ).hexdigest()
        now = _utc_now()
        item_identifier = item_id or _identifier(
            "draft" if status == "draft" else "analysis"
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM library_items WHERE item_id = ?",
                (item_identifier,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO library_items(
                        item_id, parent_type, workspace_id, title, author,
                        status, project_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_identifier,
                        parent_type,
                        workspace_id,
                        item_title,
                        author.strip(),
                        status,
                        project_id,
                        now,
                        now,
                    ),
                )
                revision_number = 1
            else:
                latest = connection.execute(
                    """
                    SELECT * FROM library_revisions
                    WHERE item_id = ?
                    ORDER BY revision_number DESC LIMIT 1
                    """,
                    (item_identifier,),
                ).fetchone()
                if (
                    deduplicate
                    and latest is not None
                    and latest["payload_sha256"] == payload_sha256
                ):
                    connection.execute(
                        """
                        UPDATE library_items SET title = ?, author = ?,
                            updated_at = ? WHERE item_id = ?
                        """,
                        (item_title, author.strip(), now, item_identifier),
                    )
                    item_row = connection.execute(
                        "SELECT * FROM library_items WHERE item_id = ?",
                        (item_identifier,),
                    ).fetchone()
                    return (
                        self._item(item_row),
                        self._revision(latest),
                        False,
                    )
                revision_number = (
                    int(latest["revision_number"]) + 1 if latest is not None else 1
                )
                connection.execute(
                    """
                    UPDATE library_items SET parent_type = ?, workspace_id = ?,
                        title = ?, author = ?, status = ?, project_id = ?,
                        updated_at = ? WHERE item_id = ?
                    """,
                    (
                        parent_type,
                        workspace_id,
                        item_title,
                        author.strip(),
                        status,
                        project_id,
                        now,
                        item_identifier,
                    ),
                )
                if existing["status"] == "draft" and status == "saved":
                    connection.execute(
                        """
                        UPDATE research_notes SET parent_type = ?,
                            updated_at = ?
                        WHERE parent_type = 'draft' AND parent_id = ?
                        """,
                        (parent_type, now, item_identifier),
                    )
            revision_id = _identifier("revision")
            connection.execute(
                """
                INSERT INTO library_revisions(
                    revision_id, item_id, revision_number, storage_mode,
                    text_sha256, payload_sha256, profile_name, software_version,
                    settings_payload, data_versions_payload, warnings_payload,
                    summary_payload, analysis_payload, artifact_bundle, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    item_identifier,
                    revision_number,
                    storage_mode,
                    text_sha256,
                    payload_sha256,
                    profile_name,
                    software_version,
                    serialize_value(settings),
                    serialize_value(data_versions),
                    serialize_value(warnings),
                    serialize_value(summary),
                    analysis_payload,
                    artifact_bundle,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE library_items
                SET current_revision_id = ?, updated_at = ?
                WHERE item_id = ?
                """,
                (revision_id, now, item_identifier),
            )
            item_row = connection.execute(
                "SELECT * FROM library_items WHERE item_id = ?",
                (item_identifier,),
            ).fetchone()
            revision_row = connection.execute(
                "SELECT * FROM library_revisions WHERE revision_id = ?",
                (revision_id,),
            ).fetchone()
        return self._item(item_row), self._revision(revision_row), True

    def list_items(self, *, status: str | None = None) -> tuple[LibraryItem, ...]:
        query = "SELECT * FROM library_items"
        parameters: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY updated_at DESC, item_id"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(self._item(row) for row in rows)

    def get_item(self, item_id: str) -> LibraryItem:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM library_items WHERE item_id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise ResearchLibraryError("Unknown saved analysis.")
        return self._item(row)

    def list_revisions(self, item_id: str) -> tuple[LibraryRevision, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM library_revisions WHERE item_id = ?
                ORDER BY revision_number DESC
                """,
                (item_id,),
            ).fetchall()
        return tuple(self._revision(row) for row in rows)

    def get_revision(self, revision_id: str) -> LibraryRevision:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM library_revisions WHERE revision_id = ?",
                (revision_id,),
            ).fetchone()
        if row is None:
            raise ResearchLibraryError("Unknown saved-analysis revision.")
        return self._revision(row)

    def load_payload(self, revision_id: str) -> object:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT analysis_payload FROM library_revisions
                WHERE revision_id = ?
                """,
                (revision_id,),
            ).fetchone()
            if row is None:
                raise ResearchLibraryError("Unknown saved-analysis revision.")
            if row["analysis_payload"] is None:
                raise ResearchLibraryError(
                    "This results-only revision does not retain restorable text."
                )
            payload = bytes(row["analysis_payload"])
            connection.execute(
                """
                UPDATE library_items SET last_opened_at = ?
                WHERE item_id = (
                    SELECT item_id FROM library_revisions WHERE revision_id = ?
                )
                """,
                (_utc_now(), revision_id),
            )
        return deserialize_value(payload)

    def delete_item(self, item_id: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            deleted = connection.execute(
                "DELETE FROM library_items WHERE item_id = ?", (item_id,)
            ).rowcount
            connection.execute(
                """
                DELETE FROM research_notes
                WHERE parent_type IN ('analysis', 'comparison', 'draft')
                  AND parent_id = ?
                """,
                (item_id,),
            )
        if not deleted:
            raise ResearchLibraryError("Unknown saved analysis.")

    def reparent_notes(
        self,
        *,
        old_parent_id: str,
        new_parent_type: str,
        new_parent_id: str,
        copy: bool = False,
    ) -> None:
        """Move or copy contextual notes when an unsaved object is saved."""

        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM research_notes WHERE parent_id = ?",
                (old_parent_id,),
            ).fetchall()
            if copy:
                for row in rows:
                    connection.execute(
                        """
                        INSERT INTO research_notes(
                            note_id, parent_type, parent_id, analysis_id,
                            project_id, module, metric, anchor_type, anchor_label,
                            title, body, tags_payload, include_in_export,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            _identifier("note"),
                            new_parent_type,
                            new_parent_id,
                            new_parent_id,
                            row["project_id"],
                            row["module"],
                            row["metric"],
                            row["anchor_type"],
                            row["anchor_label"],
                            row["title"],
                            row["body"],
                            row["tags_payload"],
                            row["include_in_export"],
                            now,
                            now,
                        ),
                    )
            else:
                connection.execute(
                    """
                    UPDATE research_notes SET parent_type = ?, parent_id = ?,
                        analysis_id = ?, updated_at = ?
                    WHERE parent_id = ?
                    """,
                    (
                        new_parent_type,
                        new_parent_id,
                        new_parent_id,
                        now,
                        old_parent_id,
                    ),
                )

    def promote_draft(self, item_id: str) -> LibraryItem:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE library_items SET status = 'saved', updated_at = ?
                WHERE item_id = ? AND status = 'draft'
                """,
                (now, item_id),
            ).rowcount
            if not changed:
                raise ResearchLibraryError("Unknown recoverable draft.")
            connection.execute(
                """
                UPDATE research_notes SET parent_type = 'analysis',
                    updated_at = ? WHERE parent_type = 'draft' AND parent_id = ?
                """,
                (now, item_id),
            )
            row = connection.execute(
                "SELECT * FROM library_items WHERE item_id = ?", (item_id,)
            ).fetchone()
        return self._item(row)

    def save_note(
        self,
        *,
        parent_type: str,
        parent_id: str,
        title: str,
        body: str,
        tags: Sequence[str] = (),
        analysis_id: str = "",
        project_id: str = "",
        module: str = "",
        metric: str = "",
        anchor_type: str = "analysis",
        anchor_label: str = "",
        include_in_export: bool = False,
        note_id: str | None = None,
    ) -> ResearchNote:
        clean_body = body.strip()
        if not clean_body:
            raise ResearchLibraryError("A research note cannot be empty.")
        clean_tags = tuple(
            dict.fromkeys(tag.strip() for tag in tags if tag.strip())
        )
        now = _utc_now()
        identifier = note_id or _identifier("note")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT created_at FROM research_notes WHERE note_id = ?",
                (identifier,),
            ).fetchone()
            created_at = existing["created_at"] if existing is not None else now
            connection.execute(
                """
                INSERT INTO research_notes(
                    note_id, parent_type, parent_id, analysis_id, project_id,
                    module, metric, anchor_type, anchor_label, title, body,
                    tags_payload, include_in_export, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(note_id) DO UPDATE SET
                    parent_type = excluded.parent_type,
                    parent_id = excluded.parent_id,
                    analysis_id = excluded.analysis_id,
                    project_id = excluded.project_id,
                    module = excluded.module,
                    metric = excluded.metric,
                    anchor_type = excluded.anchor_type,
                    anchor_label = excluded.anchor_label,
                    title = excluded.title,
                    body = excluded.body,
                    tags_payload = excluded.tags_payload,
                    include_in_export = excluded.include_in_export,
                    updated_at = excluded.updated_at
                """,
                (
                    identifier,
                    parent_type,
                    parent_id,
                    analysis_id,
                    project_id,
                    module,
                    metric,
                    anchor_type,
                    anchor_label,
                    title.strip() or "Research note",
                    clean_body,
                    serialize_value(clean_tags),
                    int(include_in_export),
                    created_at,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM research_notes WHERE note_id = ?", (identifier,)
            ).fetchone()
        return self._note(row)

    def list_notes(
        self,
        *,
        parent_type: str | None = None,
        parent_id: str | None = None,
    ) -> tuple[ResearchNote, ...]:
        conditions: list[str] = []
        parameters: list[object] = []
        if parent_type is not None:
            conditions.append("parent_type = ?")
            parameters.append(parent_type)
        if parent_id is not None:
            conditions.append("parent_id = ?")
            parameters.append(parent_id)
        query = "SELECT * FROM research_notes"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC, note_id"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return tuple(self._note(row) for row in rows)

    def delete_note(self, note_id: str) -> None:
        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM research_notes WHERE note_id = ?", (note_id,)
            ).rowcount
        if not deleted:
            raise ResearchLibraryError("Unknown research note.")


__all__ = [
    "LIBRARY_SCHEMA_VERSION",
    "LibraryItem",
    "LibraryRevision",
    "ResearchLibraryError",
    "ResearchLibraryRepository",
    "ResearchNote",
    "default_research_library_path",
    "deserialize_value",
    "serialize_value",
    "session_research_library_path",
]
