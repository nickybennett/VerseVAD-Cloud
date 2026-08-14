"""Transactional SQLite repository for local projects and corpus results."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from versevad import __version__
from versevad.application import WorkspaceAnalysis, unmatched_views, vad_cumulative_views
from versevad.exports.aoa import export_aoa_bundle
from versevad.exports.concreteness import export_concreteness_bundle
from versevad.exports.frequency import export_frequency_bundle
from versevad.exports.lexical_style import export_lexical_style_bundle
from versevad.exports.meter import export_meter_bundle
from versevad.exports.phonology import export_phonological_bundle
from versevad.exports.pronunciation import export_pronunciation_bundle
from versevad.exports.poetry_id import export_poetry_id_bundle
from versevad.exports.inherited_form import export_inherited_form_bundle
from versevad.exports.readability import export_readability_bundle
from versevad.exports.sensorimotor import export_sensorimotor_bundle
from versevad.exports.sentiment import export_vader_sentiment_bundle
from versevad.exports.versemap import export_versemap_bundle
from versevad.models import (
    MatchMethod,
    MatchSelection,
    ReviewAction,
    ReviewRule,
    ReviewScope,
)
from versevad.normalization import normalize_lookup


SCHEMA_VERSION = 5
PROJECT_ROOT = Path(__file__).resolve().parents[3]

_OBSERVATION_COVERAGE_BY_METRIC = {
    ("concreteness", "concreteness.mean"): (
        "concreteness.rated_token_coverage"
    ),
    ("lexical_frequency", "frequency.mean_zipf"): (
        "frequency.matched_token_coverage"
    ),
    ("age_of_acquisition", "aoa.mean_years"): (
        "aoa.matched_token_coverage"
    ),
    (
        "pronunciation_prosody_foundation",
        "pronunciation.mean_syllables_per_resolved_word",
    ): "pronunciation.resolved_token_coverage",
    (
        "pronunciation_prosody_foundation",
        "pronunciation.mean_syllables_per_complete_line",
    ): "pronunciation.complete_line_coverage",
    (
        "candidate_meter_and_rhythmic_regularity",
        "meter.whole_poem_mean_fit",
    ): "meter.analyzable_physical_lines",
    (
        "candidate_meter_and_rhythmic_regularity",
        "meter.matching_line_proportion",
    ): "meter.analyzable_physical_lines",
    (
        "rhyme_and_phonological_patterns",
        "phonology.rhyme_density",
    ): "phonology.analyzable_line_endings",
    (
        "lexical_style",
        "lexical_style.mean_word_length",
    ): "lexical_style.alphabetic_word_lengths",
}


def default_database_path() -> Path:
    configured = os.environ.get("VERSEVAD_DATABASE_PATH")
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / "projects" / "versevad.sqlite3"


def default_personal_corpus_database_path() -> Path:
    """Return the isolated local database used by the Personal Corpus view."""

    configured = os.environ.get("VERSEVAD_PERSONAL_CORPUS_DATABASE_PATH")
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / "projects" / "personal_corpus.sqlite3"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)!r} as project data.")


def _json_dumps(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    title: str
    description: str
    researcher: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CorpusTextImport:
    title: str
    source_name: str
    relative_path: str
    original_text: str


@dataclass(frozen=True)
class CorpusTextRecord:
    text_id: str
    text_version_id: str
    project_id: str
    title: str
    source_name: str
    relative_path: str
    author: str
    collection: str
    date_label: str
    genre: str
    notes: str
    custom_metadata: Mapping[str, object]
    original_text: str
    text_sha256: str
    imported_at: str
    updated_at: str


@dataclass(frozen=True)
class CorpusMetricRecord:
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    author: str
    collection: str
    date_label: str
    genre: str
    lexicon_id: str
    lexicon: str
    value_kind: str
    metric: str
    dimension: str
    category: str
    weighting: str
    scale: str
    denominator: str
    value: float | None
    observations: int
    matched_tokens: int
    lexical_tokens: int
    coverage: float | None
    completed_at: str
    analysis_view: str = "all_matched"


@dataclass(frozen=True)
class CorpusBatchRecord:
    batch_id: str
    project_id: str
    status: str
    text_ids: tuple[str, ...]
    lexicon_ids: tuple[str, ...]
    module_names: tuple[str, ...]
    module_configuration: Mapping[str, object]
    phrase_policy: str
    minimum_match_requirement: int
    stopword_mode: str
    protected_stopwords: tuple[str, ...]
    custom_stopword_additions: tuple[str, ...]
    custom_stopword_removals: tuple[str, ...]
    scenario_version_id: str
    created_at: str
    completed_at: str | None
    error_message: str


@dataclass(frozen=True)
class CorpusModuleResultRecord:
    module_result_row_id: str
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    author: str
    collection: str
    date_label: str
    genre: str
    module_name: str
    module_version: str
    result_id: str
    configuration_id: str
    scenario_id: str
    source_text_sha256: str
    provenance: Mapping[str, object]
    completed_at: str


@dataclass(frozen=True)
class CorpusModuleMetricRecord:
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    author: str
    collection: str
    date_label: str
    genre: str
    module_name: str
    module_version: str
    result_id: str
    configuration_id: str
    metric_id: str
    value: object
    layer: str
    scope: str
    scope_id: str
    unit: str
    weighting: str
    denominator: str
    observation_count: int | None
    note: str
    completed_at: str


@dataclass(frozen=True)
class CorpusModuleCoverageRecord:
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    module_name: str
    configuration_id: str
    coverage_id: str
    scope: str
    scope_id: str
    eligible_count: int
    matched_count: int
    unmatched_count: int
    coverage_rate: float | None
    unit: str
    unmatched_items: tuple[str, ...]
    note: str
    completed_at: str


@dataclass(frozen=True)
class CorpusModuleWarningRecord:
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    module_name: str
    configuration_id: str
    code: str
    message: str
    severity: str
    technical_detail: str
    completed_at: str


@dataclass(frozen=True)
class CorpusModuleArtifactRecord:
    run_id: str
    text_id: str
    text_version_id: str
    title: str
    module_name: str
    filename: str
    content: bytes
    content_sha256: str
    size_bytes: int


@dataclass(frozen=True)
class CorpusModuleAggregateRecord:
    aggregate_id: str
    batch_id: str
    project_id: str
    module_name: str
    configuration_id: str
    metric_id: str
    aggregation_method: str
    value: object
    unit: str
    works_included: int
    works_omitted: int
    observation_count: int
    note: str


@dataclass(frozen=True)
class UnmatchedQcRecord:
    project_id: str
    text_id: str
    text_title: str
    lexicon_id: str
    lexicon: str
    normalized_form: str
    display_form: str
    frequency: int
    pos: str
    proposed_lemma: str
    example_line: int
    example_context: str
    status: str
    note: str
    proposed_mapping: str
    note_id: str | None
    updated_at: str | None


@dataclass(frozen=True)
class ReviewScenarioRecord:
    scenario_id: str
    project_id: str
    name: str
    description: str
    scenario_version_id: str
    version_number: int
    decision_count: int
    created_at: str
    version_created_at: str


@dataclass(frozen=True)
class ReviewScenarioVersionRecord:
    scenario_version_id: str
    scenario_id: str
    version_number: int
    decision_count: int
    change_note: str
    created_at: str


@dataclass(frozen=True)
class ReviewDecisionRecord:
    decision_revision_id: str
    decision_id: str
    scenario_id: str
    revision_number: int
    state: str
    action: str
    scope: str
    project_id: str
    text_id: str
    text_version_id: str
    lexicon_id: str
    source_form: str
    token_position: int | None
    mapping_target: str
    risk_category: str
    rationale: str
    supersedes_revision_id: str
    created_at: str


@dataclass(frozen=True)
class ReviewCandidateRecord:
    run_id: str
    project_id: str
    text_id: str
    text_version_id: str
    text_title: str
    lexicon_id: str
    lexicon: str
    match_id: str
    token_position: int
    line_number: int
    surface_form: str
    normalized_form: str
    matched_term: str
    method: str
    selection: str
    included: bool
    risk_category: str
    risk_reason: str
    context: str


_MIGRATION_1 = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    researcher TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE texts (
    text_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    collection_name TEXT NOT NULL DEFAULT '',
    date_label TEXT NOT NULL DEFAULT '',
    genre TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    custom_metadata_json TEXT NOT NULL DEFAULT '{}',
    active_text_version_id TEXT REFERENCES text_versions(text_version_id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(project_id, relative_path)
);

CREATE TABLE text_versions (
    text_version_id TEXT PRIMARY KEY,
    text_id TEXT NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    source_encoding TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(text_id, text_sha256)
);

CREATE TABLE corpus_batches (
    batch_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('pending', 'complete', 'failed')),
    text_ids_json TEXT NOT NULL,
    lexicon_ids_json TEXT NOT NULL,
    phrase_policy TEXT NOT NULL,
    minimum_match_requirement INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT NOT NULL DEFAULT ''
);

CREATE TABLE analysis_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    text_id TEXT NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    text_version_id TEXT NOT NULL REFERENCES text_versions(text_version_id),
    batch_id TEXT REFERENCES corpus_batches(batch_id),
    status TEXT NOT NULL CHECK(status IN ('complete', 'failed')),
    scenario_id TEXT NOT NULL,
    phrase_policy TEXT NOT NULL,
    minimum_match_requirement INTEGER NOT NULL,
    lexicon_ids_json TEXT NOT NULL,
    software_version TEXT NOT NULL,
    run_signature TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL
);

CREATE TABLE analysis_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    lexicon_id TEXT NOT NULL,
    lexicon_display_name TEXT NOT NULL,
    value_kind TEXT NOT NULL,
    metric TEXT NOT NULL,
    dimension TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    weighting TEXT NOT NULL DEFAULT '',
    scale TEXT NOT NULL DEFAULT '',
    denominator TEXT NOT NULL,
    value REAL,
    observations INTEGER NOT NULL,
    matched_tokens INTEGER NOT NULL,
    lexical_tokens INTEGER NOT NULL,
    coverage REAL
);

CREATE TABLE unmatched_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    text_id TEXT NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    lexicon_id TEXT NOT NULL,
    lexicon_display_name TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    display_form TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    pos TEXT NOT NULL,
    proposed_lemma TEXT NOT NULL,
    example_line INTEGER NOT NULL,
    example_context TEXT NOT NULL
);

CREATE TABLE unmatched_notes (
    note_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    text_id TEXT NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    lexicon_id TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    display_form TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL,
    proposed_mapping TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(project_id, text_id, lexicon_id, normalized_form)
);

CREATE INDEX idx_texts_project ON texts(project_id);
CREATE INDEX idx_versions_text ON text_versions(text_id, imported_at);
CREATE INDEX idx_runs_project_text ON analysis_runs(project_id, text_id, completed_at);
CREATE INDEX idx_batches_project ON corpus_batches(project_id, completed_at);
CREATE INDEX idx_metrics_run ON analysis_metrics(run_id);
CREATE INDEX idx_unmatched_run ON unmatched_observations(run_id);
CREATE INDEX idx_notes_lookup ON unmatched_notes(project_id, text_id, lexicon_id, normalized_form);
"""

_MIGRATION_2 = """
ALTER TABLE analysis_metrics
ADD COLUMN analysis_view TEXT NOT NULL DEFAULT 'all_matched';

ALTER TABLE corpus_batches
ADD COLUMN stopword_mode TEXT NOT NULL DEFAULT 'standard';

ALTER TABLE corpus_batches
ADD COLUMN protected_stopwords_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE corpus_batches
ADD COLUMN custom_stopword_additions_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE corpus_batches
ADD COLUMN custom_stopword_removals_json TEXT NOT NULL DEFAULT '[]';
"""

_MIGRATION_3 = """
ALTER TABLE corpus_batches
ADD COLUMN scenario_version_id TEXT NOT NULL DEFAULT '';

ALTER TABLE analysis_runs
ADD COLUMN scenario_version_id TEXT NOT NULL DEFAULT '';

CREATE TABLE review_scenarios (
    scenario_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(project_id, name COLLATE NOCASE)
);

CREATE TABLE review_decisions (
    decision_revision_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL REFERENCES review_scenarios(scenario_id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('active', 'revoked')),
    action TEXT NOT NULL CHECK(action IN ('flag', 'exclude', 'map')),
    scope TEXT NOT NULL CHECK(scope IN ('occurrence', 'work', 'project', 'global')),
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    text_id TEXT NOT NULL DEFAULT '',
    text_version_id TEXT NOT NULL DEFAULT '',
    lexicon_id TEXT NOT NULL,
    source_form TEXT NOT NULL,
    token_position INTEGER,
    mapping_target TEXT NOT NULL DEFAULT '',
    risk_category TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL,
    supersedes_revision_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(decision_id, revision_number)
);

CREATE TABLE review_scenario_versions (
    scenario_version_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL REFERENCES review_scenarios(scenario_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    decision_revision_ids_json TEXT NOT NULL,
    change_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(scenario_id, version_number)
);

CREATE TABLE review_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    text_id TEXT NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    text_version_id TEXT NOT NULL REFERENCES text_versions(text_version_id),
    lexicon_id TEXT NOT NULL,
    lexicon_display_name TEXT NOT NULL,
    match_id TEXT NOT NULL,
    token_position INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    surface_form TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    matched_term TEXT NOT NULL,
    method TEXT NOT NULL,
    selection TEXT NOT NULL,
    included INTEGER NOT NULL,
    risk_category TEXT NOT NULL,
    risk_reason TEXT NOT NULL,
    context TEXT NOT NULL,
    UNIQUE(run_id, lexicon_id, match_id)
);

CREATE INDEX idx_review_scenarios_project
ON review_scenarios(project_id, created_at);

CREATE INDEX idx_review_decisions_scenario
ON review_decisions(scenario_id, decision_id, revision_number);

CREATE INDEX idx_review_versions_scenario
ON review_scenario_versions(scenario_id, version_number);

CREATE INDEX idx_review_candidates_run
ON review_candidates(run_id, risk_category, text_id);
"""

_MIGRATION_4 = """
ALTER TABLE corpus_batches
ADD COLUMN module_names_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE corpus_batches
ADD COLUMN module_configuration_json TEXT NOT NULL DEFAULT '{}';

CREATE TABLE module_results (
    module_result_row_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    module_version TEXT NOT NULL,
    result_id TEXT NOT NULL,
    configuration_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    source_text_sha256 TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, module_name)
);

CREATE TABLE module_metrics (
    module_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_result_row_id TEXT NOT NULL
        REFERENCES module_results(module_result_row_id) ON DELETE CASCADE,
    metric_id TEXT NOT NULL,
    value_json TEXT NOT NULL,
    layer TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    weighting TEXT NOT NULL DEFAULT '',
    denominator TEXT NOT NULL DEFAULT '',
    observation_count INTEGER,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE module_coverage (
    module_coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_result_row_id TEXT NOT NULL
        REFERENCES module_results(module_result_row_id) ON DELETE CASCADE,
    coverage_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT NOT NULL DEFAULT '',
    eligible_count INTEGER NOT NULL,
    matched_count INTEGER NOT NULL,
    unmatched_count INTEGER NOT NULL,
    coverage_rate REAL,
    unit TEXT NOT NULL,
    unmatched_items_json TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE module_warnings (
    module_warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_result_row_id TEXT NOT NULL
        REFERENCES module_results(module_result_row_id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    technical_detail TEXT NOT NULL DEFAULT ''
);

CREATE TABLE module_artifacts (
    module_artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_result_row_id TEXT NOT NULL
        REFERENCES module_results(module_result_row_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content BLOB NOT NULL,
    content_sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    UNIQUE(module_result_row_id, filename)
);

CREATE TABLE corpus_module_aggregates (
    aggregate_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL REFERENCES corpus_batches(batch_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    configuration_id TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    aggregation_method TEXT NOT NULL,
    value_json TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    works_included INTEGER NOT NULL,
    works_omitted INTEGER NOT NULL,
    observation_count INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(
        batch_id,
        module_name,
        configuration_id,
        metric_id,
        aggregation_method
    )
);

CREATE INDEX idx_module_results_run
ON module_results(run_id, module_name);

CREATE INDEX idx_module_metrics_result
ON module_metrics(module_result_row_id, scope, metric_id);

CREATE INDEX idx_module_coverage_result
ON module_coverage(module_result_row_id, coverage_id);

CREATE INDEX idx_module_artifacts_result
ON module_artifacts(module_result_row_id, filename);

CREATE INDEX idx_corpus_module_aggregates_batch
ON corpus_module_aggregates(batch_id, module_name, metric_id);
"""

# Version 5 changes the semantic contract of ``analysis_metrics.analysis_view``
# to the three canonical scope identifiers and guarantees all six
# scope/weighting rows for newly completed batches. No physical table change
# is required; recording the migration prevents silent mixed-schema claims.
_MIGRATION_5 = """
CREATE INDEX IF NOT EXISTS idx_corpus_metrics_profile
ON analysis_metrics(run_id, analysis_view, weighting, metric);
"""


class ProjectRepository:
    """Own the local SQLite database and its explicit migrations."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path or default_database_path()).resolve()

    def _backup_before_migration(
        self,
        connection: sqlite3.Connection,
        current_version: int,
    ) -> None:
        """Create and verify one non-overwriting local backup before schema changes."""

        if current_version <= 0 or current_version >= SCHEMA_VERSION:
            return
        backup_path = self.database_path.with_name(
            f"{self.database_path.stem}.pre-v{SCHEMA_VERSION}.sqlite3"
        )
        if not backup_path.exists():
            backup = sqlite3.connect(backup_path)
            try:
                connection.backup(backup)
                backup.commit()
            finally:
                backup.close()
        verification = sqlite3.connect(backup_path)
        try:
            integrity = verification.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            verification.close()
        if integrity != "ok":
            raise RuntimeError(
                f"VerseVAD could not verify the pre-migration backup at {backup_path}. "
                "The project database was not migrated."
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            current = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()[0]
            if current > SCHEMA_VERSION:
                raise RuntimeError(
                    "This project database was created by a newer VerseVAD version. "
                    "No data was changed."
                )
            self._backup_before_migration(connection, int(current))
            if current < 1:
                connection.executescript(_MIGRATION_1)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, _now()),
                )
                current = 1
            if current < 2:
                connection.executescript(_MIGRATION_2)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (2, _now()),
                )
                current = 2
            if current < 3:
                connection.executescript(_MIGRATION_3)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (3, _now()),
                )
                current = 3
            if current < 4:
                connection.executescript(_MIGRATION_4)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (4, _now()),
                )
                current = 4
            if current < 5:
                connection.executescript(_MIGRATION_5)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (5, _now()),
                )

    def schema_version(self) -> int:
        self.initialize()
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0]
            )

    def create_project(
        self,
        title: str,
        *,
        description: str = "",
        researcher: str = "",
    ) -> ProjectRecord:
        title = title.strip()
        if not title:
            raise ValueError("Enter a project title.")
        self.initialize()
        now = _now()
        project = ProjectRecord(_id("project"), title, description.strip(), researcher.strip(), now, now)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO projects(project_id, title, description, researcher, created_at, updated_at) "
                "VALUES (:project_id, :title, :description, :researcher, :created_at, :updated_at)",
                asdict(project),
            )
        return project

    @staticmethod
    def _project(row: sqlite3.Row) -> ProjectRecord:
        return ProjectRecord(**dict(row))

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT project_id, title, description, researcher, created_at, updated_at "
                "FROM projects ORDER BY updated_at DESC, title COLLATE NOCASE"
            ).fetchall()
        return tuple(self._project(row) for row in rows)

    def get_project(self, project_id: str) -> ProjectRecord:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT project_id, title, description, researcher, created_at, updated_at "
                "FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown project: {project_id}")
        return self._project(row)

    def delete_project(self, project_id: str, *, confirmation_title: str) -> None:
        """Delete exactly one project after an exact, case-sensitive title check."""

        self.initialize()
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT title FROM projects WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown project: {project_id}")
                if confirmation_title != row["title"]:
                    raise ValueError(
                        "The confirmation text does not exactly match the project title."
                    )

                # Several preserved-history foreign keys intentionally use
                # NO ACTION so ordinary record edits cannot erase evidence.
                # Project deletion is the one explicitly confirmed lifecycle
                # operation that must remove that evidence. Delete in a stable
                # dependency order and break the active-version cycle first.
                connection.execute(
                    "UPDATE texts SET active_text_version_id = NULL WHERE project_id = ?",
                    (project_id,),
                )
                connection.execute(
                    "DELETE FROM analysis_runs WHERE project_id = ?",
                    (project_id,),
                )
                connection.execute(
                    "DELETE FROM corpus_batches WHERE project_id = ?",
                    (project_id,),
                )
                connection.execute(
                    "DELETE FROM review_scenarios WHERE project_id = ?",
                    (project_id,),
                )
                connection.execute(
                    "DELETE FROM unmatched_notes WHERE project_id = ?",
                    (project_id,),
                )
                connection.execute(
                    "DELETE FROM texts WHERE project_id = ?",
                    (project_id,),
                )
                cursor = connection.execute(
                    "DELETE FROM projects WHERE project_id = ?",
                    (project_id,),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "VerseVAD could not delete the selected project."
                    )
        except sqlite3.Error as error:
            raise RuntimeError(
                "The project database rejected the deletion; no partial deletion "
                "was saved."
            ) from error

    @staticmethod
    def _review_scenario(
        connection: sqlite3.Connection,
        scenario_id: str,
    ) -> ReviewScenarioRecord:
        row = connection.execute(
            """
            SELECT s.scenario_id, s.project_id, s.name, s.description, s.created_at,
                   v.scenario_version_id, v.version_number,
                   v.decision_revision_ids_json, v.created_at AS version_created_at
            FROM review_scenarios s
            JOIN review_scenario_versions v
              ON v.scenario_id = s.scenario_id
            WHERE s.scenario_id = ?
            ORDER BY v.version_number DESC
            LIMIT 1
            """,
            (scenario_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown review scenario: {scenario_id}")
        values = dict(row)
        decision_ids = json.loads(values.pop("decision_revision_ids_json"))
        values["decision_count"] = len(decision_ids)
        return ReviewScenarioRecord(**values)

    @staticmethod
    def _append_review_scenario_version(
        connection: sqlite3.Connection,
        scenario_id: str,
        decision_revision_ids: Sequence[str],
        *,
        change_note: str,
    ) -> str:
        current = connection.execute(
            """
            SELECT COALESCE(MAX(version_number), 0)
            FROM review_scenario_versions
            WHERE scenario_id = ?
            """,
            (scenario_id,),
        ).fetchone()[0]
        scenario_version_id = _id("scenario-version")
        connection.execute(
            """
            INSERT INTO review_scenario_versions(
                scenario_version_id, scenario_id, version_number,
                decision_revision_ids_json, change_note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_version_id,
                scenario_id,
                int(current) + 1,
                json.dumps(tuple(decision_revision_ids)),
                change_note.strip(),
                _now(),
            ),
        )
        return scenario_version_id

    def create_review_scenario(
        self,
        project_id: str,
        name: str,
        *,
        description: str = "",
    ) -> ReviewScenarioRecord:
        """Create a named scenario with an immutable empty first version."""

        name = name.strip()
        if not name:
            raise ValueError("Enter a scenario name.")
        self.initialize()
        scenario_id = _id("scenario")
        now = _now()
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown project: {project_id}")
            try:
                connection.execute(
                    """
                    INSERT INTO review_scenarios(
                        scenario_id, project_id, name, description, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (scenario_id, project_id, name, description.strip(), now),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError(
                    "This project already has a review scenario with that name."
                ) from error
            self._append_review_scenario_version(
                connection,
                scenario_id,
                (),
                change_note="Scenario created with no active review decisions.",
            )
        return self.get_review_scenario(scenario_id)

    def get_review_scenario(self, scenario_id: str) -> ReviewScenarioRecord:
        self.initialize()
        with self._connect() as connection:
            return self._review_scenario(connection, scenario_id)

    def get_review_scenario_version(
        self,
        scenario_version_id: str,
    ) -> ReviewScenarioRecord:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT s.scenario_id, s.project_id, s.name, s.description, s.created_at,
                       v.scenario_version_id, v.version_number,
                       v.decision_revision_ids_json,
                       v.created_at AS version_created_at
                FROM review_scenario_versions v
                JOIN review_scenarios s ON s.scenario_id = v.scenario_id
                WHERE v.scenario_version_id = ?
                """,
                (scenario_version_id,),
            ).fetchone()
            if row is None:
                raise KeyError(
                    f"Unknown review scenario version: {scenario_version_id}"
                )
            values = dict(row)
            decision_ids = json.loads(values.pop("decision_revision_ids_json"))
            values["decision_count"] = len(decision_ids)
            return ReviewScenarioRecord(**values)

    def list_review_scenarios(
        self,
        project_id: str,
    ) -> tuple[ReviewScenarioRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            ids = connection.execute(
                """
                SELECT scenario_id
                FROM review_scenarios
                WHERE project_id = ?
                ORDER BY name COLLATE NOCASE, created_at
                """,
                (project_id,),
            ).fetchall()
            return tuple(
                self._review_scenario(connection, row["scenario_id"])
                for row in ids
            )

    def list_review_scenario_versions(
        self,
        scenario_id: str,
    ) -> tuple[ReviewScenarioVersionRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM review_scenarios WHERE scenario_id = ?",
                (scenario_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown review scenario: {scenario_id}")
            rows = connection.execute(
                """
                SELECT scenario_version_id, scenario_id, version_number,
                       decision_revision_ids_json, change_note, created_at
                FROM review_scenario_versions
                WHERE scenario_id = ?
                ORDER BY version_number DESC
                """,
                (scenario_id,),
            ).fetchall()
        return tuple(
            ReviewScenarioVersionRecord(
                scenario_version_id=row["scenario_version_id"],
                scenario_id=row["scenario_id"],
                version_number=row["version_number"],
                decision_count=len(json.loads(row["decision_revision_ids_json"])),
                change_note=row["change_note"],
                created_at=row["created_at"],
            )
            for row in rows
        )

    @staticmethod
    def _scenario_revision_ids(
        connection: sqlite3.Connection,
        scenario_version_id: str,
    ) -> tuple[str, ...]:
        row = connection.execute(
            """
            SELECT decision_revision_ids_json
            FROM review_scenario_versions
            WHERE scenario_version_id = ?
            """,
            (scenario_version_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown review scenario version: {scenario_version_id}")
        return tuple(json.loads(row["decision_revision_ids_json"]))

    @staticmethod
    def _review_decision(row: sqlite3.Row) -> ReviewDecisionRecord:
        return ReviewDecisionRecord(**dict(row))

    def list_review_decisions(
        self,
        scenario_version_id: str,
        *,
        active_only: bool = False,
    ) -> tuple[ReviewDecisionRecord, ...]:
        """Return the exact pinned decision revisions for one scenario version."""

        self.initialize()
        with self._connect() as connection:
            revision_ids = self._scenario_revision_ids(
                connection,
                scenario_version_id,
            )
            if not revision_ids:
                return ()
            placeholders = ",".join("?" for _ in revision_ids)
            state_clause = " AND state = 'active'" if active_only else ""
            rows = connection.execute(
                f"""
                SELECT decision_revision_id, decision_id, scenario_id,
                       revision_number, state, action, scope, project_id, text_id,
                       text_version_id, lexicon_id, source_form, token_position,
                       mapping_target, risk_category, rationale,
                       supersedes_revision_id, created_at
                FROM review_decisions
                WHERE decision_revision_id IN ({placeholders}){state_clause}
                """,
                revision_ids,
            ).fetchall()
            by_id = {
                row["decision_revision_id"]: self._review_decision(row)
                for row in rows
            }
        return tuple(
            by_id[revision_id]
            for revision_id in revision_ids
            if revision_id in by_id
        )

    def create_review_decision(
        self,
        scenario_id: str,
        *,
        action: ReviewAction | str,
        scope: ReviewScope | str,
        lexicon_id: str,
        source_form: str,
        rationale: str,
        mapping_target: str = "",
        text_id: str = "",
        text_version_id: str = "",
        token_position: int | None = None,
        risk_category: str = "",
    ) -> ReviewScenarioRecord:
        """Append a decision revision and a new immutable scenario snapshot."""

        try:
            selected_action = ReviewAction(action)
            selected_scope = ReviewScope(scope)
        except ValueError as error:
            raise ValueError("Choose a supported review action and scope.") from error
        normalized_source = normalize_lookup(source_form)
        normalized_target = normalize_lookup(mapping_target) if mapping_target.strip() else ""
        if not normalized_source:
            raise ValueError("Choose a word or phrase to review.")
        if not lexicon_id.strip():
            raise ValueError("Choose a lexicon for this review decision.")
        if not rationale.strip():
            raise ValueError("Record a rationale so this decision remains auditable.")
        if selected_action == ReviewAction.MAP:
            if not normalized_target:
                raise ValueError("A mapping decision needs an exact target lexicon entry.")
            if " " in normalized_source or " " in normalized_target:
                raise ValueError(
                    "Review mappings currently operate on one token at a time. "
                    "Phrase entries can be flagged or excluded."
                )
        else:
            normalized_target = ""
        self.initialize()
        with self._connect() as connection:
            scenario = self._review_scenario(connection, scenario_id)
            if selected_scope in {ReviewScope.WORK, ReviewScope.OCCURRENCE}:
                owner = connection.execute(
                    """
                    SELECT t.project_id, t.active_text_version_id
                    FROM texts t WHERE t.text_id = ?
                    """,
                    (text_id,),
                ).fetchone()
                if owner is None or owner["project_id"] != scenario.project_id:
                    raise ValueError(
                        "The selected work does not belong to this scenario's project."
                    )
                if selected_scope == ReviewScope.OCCURRENCE:
                    if (
                        not text_version_id
                        or text_version_id != owner["active_text_version_id"]
                        or token_position is None
                        or token_position < 0
                    ):
                        raise ValueError(
                            "An occurrence decision needs the active text version "
                            "and exact token position."
                        )
                else:
                    text_version_id = ""
                    token_position = None
            else:
                text_id = ""
                text_version_id = ""
                token_position = None

            decision_id = _id("decision")
            revision_id = _id("decision-revision")
            connection.execute(
                """
                INSERT INTO review_decisions(
                    decision_revision_id, decision_id, scenario_id, revision_number,
                    state, action, scope, project_id, text_id, text_version_id,
                    lexicon_id, source_form, token_position, mapping_target,
                    risk_category, rationale, supersedes_revision_id, created_at
                ) VALUES (?, ?, ?, 1, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?)
                """,
                (
                    revision_id,
                    decision_id,
                    scenario_id,
                    selected_action.value,
                    selected_scope.value,
                    scenario.project_id,
                    text_id,
                    text_version_id,
                    lexicon_id.strip(),
                    normalized_source,
                    token_position,
                    normalized_target,
                    risk_category.strip(),
                    rationale.strip(),
                    _now(),
                ),
            )
            revision_ids = list(
                self._scenario_revision_ids(
                    connection,
                    scenario.scenario_version_id,
                )
            )
            revision_ids.append(revision_id)
            self._append_review_scenario_version(
                connection,
                scenario_id,
                revision_ids,
                change_note=(
                    f"Added {selected_action.value} decision for "
                    f"{normalized_source} in {lexicon_id.strip()}."
                ),
            )
        return self.get_review_scenario(scenario_id)

    def set_review_decision_state(
        self,
        scenario_id: str,
        decision_id: str,
        *,
        active: bool,
        rationale: str,
    ) -> ReviewScenarioRecord:
        """Revoke or restore a decision by appending, never overwriting, a revision."""

        if not rationale.strip():
            raise ValueError("Record why this decision was changed.")
        self.initialize()
        with self._connect() as connection:
            scenario = self._review_scenario(connection, scenario_id)
            revision_ids = list(
                self._scenario_revision_ids(
                    connection,
                    scenario.scenario_version_id,
                )
            )
            if not revision_ids:
                raise KeyError(f"Unknown review decision: {decision_id}")
            placeholders = ",".join("?" for _ in revision_ids)
            current = connection.execute(
                f"""
                SELECT decision_revision_id, decision_id, scenario_id,
                       revision_number, state, action, scope, project_id, text_id,
                       text_version_id, lexicon_id, source_form, token_position,
                       mapping_target, risk_category, rationale,
                       supersedes_revision_id, created_at
                FROM review_decisions
                WHERE decision_revision_id IN ({placeholders}) AND decision_id = ?
                """,
                (*revision_ids, decision_id),
            ).fetchone()
            if current is None:
                raise KeyError(f"Unknown review decision: {decision_id}")
            maximum = connection.execute(
                """
                SELECT COALESCE(MAX(revision_number), 0)
                FROM review_decisions WHERE decision_id = ?
                """,
                (decision_id,),
            ).fetchone()[0]
            revision_id = _id("decision-revision")
            new_state = "active" if active else "revoked"
            connection.execute(
                """
                INSERT INTO review_decisions(
                    decision_revision_id, decision_id, scenario_id, revision_number,
                    state, action, scope, project_id, text_id, text_version_id,
                    lexicon_id, source_form, token_position, mapping_target,
                    risk_category, rationale, supersedes_revision_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    decision_id,
                    scenario_id,
                    int(maximum) + 1,
                    new_state,
                    current["action"],
                    current["scope"],
                    current["project_id"],
                    current["text_id"],
                    current["text_version_id"],
                    current["lexicon_id"],
                    current["source_form"],
                    current["token_position"],
                    current["mapping_target"],
                    current["risk_category"],
                    rationale.strip(),
                    current["decision_revision_id"],
                    _now(),
                ),
            )
            revision_ids[
                revision_ids.index(current["decision_revision_id"])
            ] = revision_id
            self._append_review_scenario_version(
                connection,
                scenario_id,
                revision_ids,
                change_note=(
                    f"{'Restored' if active else 'Revoked'} decision "
                    f"{decision_id}: {rationale.strip()}"
                ),
            )
        return self.get_review_scenario(scenario_id)

    def restore_review_scenario_version(
        self,
        scenario_id: str,
        source_version_id: str,
        *,
        rationale: str,
    ) -> ReviewScenarioRecord:
        """Append a new version whose pinned decision set matches an earlier version."""

        if not rationale.strip():
            raise ValueError("Record why this scenario version was restored.")
        self.initialize()
        with self._connect() as connection:
            self._review_scenario(connection, scenario_id)
            row = connection.execute(
                """
                SELECT decision_revision_ids_json
                FROM review_scenario_versions
                WHERE scenario_version_id = ? AND scenario_id = ?
                """,
                (source_version_id, scenario_id),
            ).fetchone()
            if row is None:
                raise ValueError(
                    "The selected historical version does not belong to this scenario."
                )
            self._append_review_scenario_version(
                connection,
                scenario_id,
                tuple(json.loads(row["decision_revision_ids_json"])),
                change_note=f"Restored {source_version_id}: {rationale.strip()}",
            )
        return self.get_review_scenario(scenario_id)

    def review_rules_for_text(
        self,
        scenario_version_id: str,
        *,
        text_id: str,
        text_version_id: str,
    ) -> tuple[ReviewRule, ...]:
        """Resolve only rules eligible for this preserved work and scenario snapshot."""

        decisions = self.list_review_decisions(
            scenario_version_id,
            active_only=True,
        )
        rules = []
        for decision in decisions:
            scope = ReviewScope(decision.scope)
            if scope in {ReviewScope.WORK, ReviewScope.OCCURRENCE}:
                if decision.text_id != text_id:
                    continue
            if scope == ReviewScope.OCCURRENCE:
                if decision.text_version_id != text_version_id:
                    continue
            rules.append(
                ReviewRule(
                    decision_id=decision.decision_id,
                    decision_revision_id=decision.decision_revision_id,
                    action=ReviewAction(decision.action),
                    scope=scope,
                    lexicon_id=decision.lexicon_id,
                    source_form=decision.source_form,
                    mapping_target=decision.mapping_target,
                    project_id=decision.project_id,
                    text_id=decision.text_id,
                    text_version_id=decision.text_version_id,
                    token_position=decision.token_position,
                    risk_category=decision.risk_category,
                    rationale=decision.rationale,
                )
            )
        return tuple(rules)

    @staticmethod
    def _batch(row: sqlite3.Row) -> CorpusBatchRecord:
        values = dict(row)
        values["text_ids"] = tuple(json.loads(values.pop("text_ids_json")))
        values["lexicon_ids"] = tuple(json.loads(values.pop("lexicon_ids_json")))
        values["module_names"] = tuple(
            json.loads(values.pop("module_names_json"))
        )
        values["module_configuration"] = json.loads(
            values.pop("module_configuration_json")
        )
        values["protected_stopwords"] = tuple(
            json.loads(values.pop("protected_stopwords_json"))
        )
        values["custom_stopword_additions"] = tuple(
            json.loads(values.pop("custom_stopword_additions_json"))
        )
        values["custom_stopword_removals"] = tuple(
            json.loads(values.pop("custom_stopword_removals_json"))
        )
        return CorpusBatchRecord(**values)

    def begin_corpus_batch(
        self,
        project_id: str,
        *,
        text_ids: Iterable[str],
        lexicon_ids: Iterable[str],
        module_names: Iterable[str] = (),
        module_configuration: Mapping[str, object] | None = None,
        phrase_policy: str,
        minimum_match_requirement: int,
        stopword_mode: str = "standard",
        protected_stopwords: Iterable[str] = (),
        custom_stopword_additions: Iterable[str] = (),
        custom_stopword_removals: Iterable[str] = (),
        scenario_version_id: str = "",
    ) -> CorpusBatchRecord:
        """Create a pending comparison batch; pending results stay off dashboards."""

        selected_texts = tuple(dict.fromkeys(text_ids))
        selected_lexicons = tuple(dict.fromkeys(lexicon_ids))
        selected_modules = tuple(dict.fromkeys(module_names))
        protected = tuple(dict.fromkeys(protected_stopwords))
        additions = tuple(dict.fromkeys(custom_stopword_additions))
        removals = tuple(dict.fromkeys(custom_stopword_removals))
        if not selected_texts:
            raise ValueError("Select at least one corpus text to analyze.")
        if not selected_lexicons and not selected_modules:
            raise ValueError("Select at least one lexicon or optional analysis module.")
        if minimum_match_requirement < 1:
            raise ValueError("The minimum matched-item setting must be at least 1.")
        self.initialize()
        batch_id = _id("batch")
        now = _now()
        with self._connect() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if project is None:
                raise KeyError(f"Unknown project: {project_id}")
            if scenario_version_id:
                scenario = connection.execute(
                    """
                    SELECT s.project_id
                    FROM review_scenario_versions v
                    JOIN review_scenarios s ON s.scenario_id = v.scenario_id
                    WHERE v.scenario_version_id = ?
                    """,
                    (scenario_version_id,),
                ).fetchone()
                if scenario is None or scenario["project_id"] != project_id:
                    raise ValueError(
                        "The selected review scenario version does not belong to this project."
                    )
            placeholders = ",".join("?" for _ in selected_texts)
            found = connection.execute(
                f"SELECT text_id FROM texts WHERE project_id = ? AND text_id IN ({placeholders})",
                (project_id, *selected_texts),
            ).fetchall()
            if {row["text_id"] for row in found} != set(selected_texts):
                raise ValueError("One or more selected texts do not belong to this project.")
            connection.execute(
                """
                INSERT INTO corpus_batches(
                    batch_id, project_id, status, text_ids_json, lexicon_ids_json,
                    module_names_json, module_configuration_json,
                    phrase_policy, minimum_match_requirement, stopword_mode,
                    protected_stopwords_json, custom_stopword_additions_json,
                    custom_stopword_removals_json, scenario_version_id, created_at
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    project_id,
                    json.dumps(selected_texts),
                    json.dumps(selected_lexicons),
                    json.dumps(selected_modules),
                    json.dumps(
                        dict(module_configuration or {}),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    phrase_policy,
                    minimum_match_requirement,
                    stopword_mode,
                    json.dumps(protected),
                    json.dumps(additions),
                    json.dumps(removals),
                    scenario_version_id,
                    now,
                ),
            )
        return self.get_batch(batch_id)

    def get_batch(self, batch_id: str) -> CorpusBatchRecord:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT batch_id, project_id, status, text_ids_json, lexicon_ids_json,
                       module_names_json, module_configuration_json,
                       phrase_policy, minimum_match_requirement, stopword_mode,
                       protected_stopwords_json, custom_stopword_additions_json,
                       custom_stopword_removals_json, scenario_version_id,
                       created_at, completed_at,
                       error_message
                FROM corpus_batches WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown corpus batch: {batch_id}")
        return self._batch(row)

    def finish_corpus_batch(
        self,
        batch_id: str,
        *,
        error_message: str | None = None,
    ) -> CorpusBatchRecord:
        self.initialize()
        now = _now()
        status = "failed" if error_message else "complete"
        with self._connect() as connection:
            batch = connection.execute(
                "SELECT project_id, status, text_ids_json FROM corpus_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if batch is None:
                raise KeyError(f"Unknown corpus batch: {batch_id}")
            if batch["status"] != "pending":
                raise ValueError("This corpus batch is already immutable and cannot be changed.")
            if status == "complete":
                expected = len(json.loads(batch["text_ids_json"]))
                actual = connection.execute(
                    "SELECT COUNT(DISTINCT text_id) FROM analysis_runs WHERE batch_id = ? AND status = 'complete'",
                    (batch_id,),
                ).fetchone()[0]
                if actual != expected:
                    raise ValueError(
                        "The corpus batch does not contain one completed run per selected text."
                    )
            connection.execute(
                """
                UPDATE corpus_batches
                SET status = ?, completed_at = ?, error_message = ?
                WHERE batch_id = ?
                """,
                (status, now, (error_message or "").strip(), batch_id),
            )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?",
                (now, batch["project_id"]),
            )
        return self.get_batch(batch_id)

    def import_texts(
        self,
        project_id: str,
        items: Iterable[CorpusTextImport],
    ) -> tuple[CorpusTextRecord, ...]:
        self.initialize()
        imported = tuple(items)
        if not imported:
            raise ValueError("Choose a folder containing at least one UTF-8 .txt file.")
        now = _now()
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone() is None:
                raise KeyError(f"Unknown project: {project_id}")
            for item in imported:
                title = item.title.strip()
                if not title or not item.original_text.strip():
                    raise ValueError("Every imported text needs a title and nonblank content.")
                relative_path = item.relative_path.replace("\\", "/").lstrip("/")
                if not relative_path or ".." in Path(relative_path).parts:
                    raise ValueError("A corpus filename contained an unsafe relative path.")
                row = connection.execute(
                    "SELECT text_id FROM texts WHERE project_id = ? AND relative_path = ?",
                    (project_id, relative_path),
                ).fetchone()
                text_id = row["text_id"] if row else _id("text")
                if row is None:
                    connection.execute(
                        "INSERT INTO texts(text_id, project_id, title, source_name, relative_path, "
                        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (text_id, project_id, title, item.source_name, relative_path, now, now),
                    )
                else:
                    connection.execute(
                        "UPDATE texts SET title = ?, source_name = ?, updated_at = ? WHERE text_id = ?",
                        (title, item.source_name, now, text_id),
                    )
                digest = hashlib.sha256(item.original_text.encode("utf-8")).hexdigest()
                version = connection.execute(
                    "SELECT text_version_id FROM text_versions WHERE text_id = ? AND text_sha256 = ?",
                    (text_id, digest),
                ).fetchone()
                text_version_id = version["text_version_id"] if version else _id("version")
                if version is None:
                    connection.execute(
                        "INSERT INTO text_versions(text_version_id, text_id, original_text, text_sha256, "
                        "source_encoding, imported_at) VALUES (?, ?, ?, ?, 'utf-8', ?)",
                        (text_version_id, text_id, item.original_text, digest, now),
                    )
                connection.execute(
                    "UPDATE texts SET active_text_version_id = ?, updated_at = ? WHERE text_id = ?",
                    (text_version_id, now, text_id),
                )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id)
            )
        return self.list_texts(project_id)

    @staticmethod
    def _text(row: sqlite3.Row) -> CorpusTextRecord:
        values = dict(row)
        values["custom_metadata"] = json.loads(values.pop("custom_metadata_json"))
        return CorpusTextRecord(**values)

    def list_texts(self, project_id: str) -> tuple[CorpusTextRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT t.text_id, v.text_version_id, t.project_id, t.title, t.source_name,
                       t.relative_path, t.author, t.collection_name AS collection,
                       t.date_label, t.genre, t.notes, t.custom_metadata_json,
                       v.original_text, v.text_sha256, v.imported_at, t.updated_at
                FROM texts t
                JOIN text_versions v ON v.text_version_id = t.active_text_version_id
                WHERE t.project_id = ?
                ORDER BY t.title COLLATE NOCASE, t.relative_path COLLATE NOCASE
                """,
                (project_id,),
            ).fetchall()
        return tuple(self._text(row) for row in rows)

    def get_text(self, text_id: str) -> CorpusTextRecord:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT t.text_id, v.text_version_id, t.project_id, t.title, t.source_name,
                       t.relative_path, t.author, t.collection_name AS collection,
                       t.date_label, t.genre, t.notes, t.custom_metadata_json,
                       v.original_text, v.text_sha256, v.imported_at, t.updated_at
                FROM texts t
                JOIN text_versions v ON v.text_version_id = t.active_text_version_id
                WHERE t.text_id = ?
                """,
                (text_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown text: {text_id}")
        return self._text(row)

    def update_text_metadata(
        self,
        text_id: str,
        *,
        title: str,
        author: str = "",
        collection: str = "",
        date_label: str = "",
        genre: str = "",
        notes: str = "",
        custom_metadata: Mapping[str, object] | None = None,
    ) -> CorpusTextRecord:
        if not title.strip():
            raise ValueError("A corpus text title cannot be blank.")
        self.initialize()
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE texts SET title = ?, author = ?, collection_name = ?, date_label = ?,
                    genre = ?, notes = ?, custom_metadata_json = ?, updated_at = ?
                WHERE text_id = ?
                """,
                (
                    title.strip(),
                    author.strip(),
                    collection.strip(),
                    date_label.strip(),
                    genre.strip(),
                    notes.strip(),
                    json.dumps(dict(custom_metadata or {}), ensure_ascii=False, sort_keys=True),
                    now,
                    text_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown text: {text_id}")
            project_id = connection.execute(
                "SELECT project_id FROM texts WHERE text_id = ?", (text_id,)
            ).fetchone()[0]
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id)
            )
        return self.get_text(text_id)

    def delete_text(
        self,
        project_id: str,
        text_id: str,
        *,
        confirmation_title: str,
    ) -> None:
        """Delete exactly one corpus work after an exact title confirmation."""

        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT title
                FROM texts
                WHERE text_id = ? AND project_id = ?
                """,
                (text_id, project_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown text in this corpus: {text_id}")
            if confirmation_title != row["title"]:
                raise ValueError(
                    "The confirmation text does not exactly match the poem title."
                )
            cursor = connection.execute(
                "DELETE FROM texts WHERE text_id = ? AND project_id = ?",
                (text_id, project_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("VerseVAD could not delete the selected poem.")
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?",
                (_now(), project_id),
            )

    @staticmethod
    def _workspace_modules(workspace: WorkspaceAnalysis) -> tuple[tuple, ...]:
        """Return completed reusable results and their existing audit exporters."""

        candidates = (
            (workspace.vader_sentiment, export_vader_sentiment_bundle),
            (workspace.readability, export_readability_bundle),
            (workspace.concreteness, export_concreteness_bundle),
            (workspace.sensorimotor, export_sensorimotor_bundle),
            (workspace.frequency, export_frequency_bundle),
            (workspace.aoa, export_aoa_bundle),
            (workspace.pronunciation, export_pronunciation_bundle),
            (workspace.meter, export_meter_bundle),
            (workspace.phonology, export_phonological_bundle),
            (workspace.lexical_style, export_lexical_style_bundle),
            (workspace.poetry_id, export_poetry_id_bundle),
            (workspace.inherited_form, export_inherited_form_bundle),
            (workspace.versemap, export_versemap_bundle),
        )
        return tuple(
            (result, exporter)
            for result, exporter in candidates
            if result is not None
        )

    @staticmethod
    def _module_configurations(workspace: WorkspaceAnalysis) -> dict[str, object]:
        request = workspace.request
        rows = (
            (
                workspace.vader_sentiment is not None,
                "vader_sentiment",
                (
                    workspace.vader_sentiment.configuration
                    if workspace.vader_sentiment is not None
                    else None
                ),
            ),
            (
                workspace.readability is not None,
                "readability",
                (
                    workspace.readability.configuration
                    if workspace.readability is not None
                    else None
                ),
            ),
            (
                workspace.concreteness is not None,
                "concreteness",
                (
                    workspace.concreteness.configuration
                    if workspace.concreteness is not None
                    else None
                ),
            ),
            (
                workspace.sensorimotor is not None,
                "sensorimotor_imagery_and_embodiment",
                (
                    workspace.sensorimotor.configuration
                    if workspace.sensorimotor is not None
                    else None
                ),
            ),
            (
                workspace.frequency is not None,
                "lexical_frequency",
                (
                    workspace.frequency.configuration
                    if workspace.frequency is not None
                    else None
                ),
            ),
            (
                workspace.aoa is not None,
                "age_of_acquisition",
                (
                    workspace.aoa.configuration
                    if workspace.aoa is not None
                    else None
                ),
            ),
            (
                (
                    request.include_pronunciation
                    or request.include_meter
                    or request.include_phonology
                    or request.include_inherited_form
                ),
                "pronunciation_prosody_foundation",
                request.pronunciation_configuration,
            ),
            (
                request.include_meter or request.include_inherited_form,
                "candidate_meter_and_rhythmic_regularity",
                request.meter_configuration,
            ),
            (
                request.include_phonology or request.include_inherited_form,
                "rhyme_and_phonological_patterns",
                request.phonological_configuration,
            ),
            (
                workspace.lexical_style is not None,
                "lexical_style",
                (
                    workspace.lexical_style.configuration
                    if workspace.lexical_style is not None
                    else None
                ),
            ),
            (
                request.include_poetry_id,
                "poetry_id",
                request.poetry_id_configuration,
            ),
            (
                request.include_inherited_form,
                "inherited_form",
                request.inherited_form_configuration,
            ),
            (
                request.include_versemap,
                "versemap",
                request.versemap_configuration,
            ),
        )
        return {
            name: asdict(configuration)
            for included, name, configuration in rows
            if included
        }

    @staticmethod
    def _manifest(workspace: WorkspaceAnalysis) -> dict[str, object]:
        stopword_policy = next(
            (
                result.stopword_policy
                for result in workspace.results
                if result.stopword_policy is not None
            ),
            None,
        )
        return {
            "software_version": __version__,
            "text_version_id": workspace.document.text_version_id,
            "text_sha256": workspace.document.text_sha256,
            "scenario_id": workspace.comparison.scenario_id,
            "scenario_version_id": workspace.request.scenario_version_id,
            "review_decisions": [
                asdict(rule) for rule in workspace.request.review_rules
            ],
            "phrase_policy": workspace.request.phrase_policy.value,
            "minimum_match_requirement": workspace.request.minimum_match_requirement,
            "stopword_policy": (
                {
                    "mode": stopword_policy.mode.value,
                    "source": stopword_policy.source,
                    "library_version": stopword_policy.library_version,
                    "list_version": stopword_policy.list_version,
                    "standard_word_count": stopword_policy.standard_word_count,
                    "standard_list_sha256": stopword_policy.standard_list_sha256,
                    "active_words": stopword_policy.active_words,
                    "active_list_sha256": stopword_policy.active_list_sha256,
                    "protected_words": stopword_policy.protected_words,
                    "custom_additions": stopword_policy.custom_additions,
                    "custom_removals": stopword_policy.custom_removals,
                }
                if stopword_policy is not None
                else None
            ),
            "lexicons": [
                {
                    "lexicon_id": result.lexicon_metadata.lexicon_id,
                    "source_sha256": result.lexicon_validation.source_sha256,
                    "adapter_version": result.lexicon_metadata.adapter_version,
                    "source_scale_min": result.lexicon_metadata.source_scale_min,
                    "source_scale_max": result.lexicon_metadata.source_scale_max,
                    "normalization_formula": result.lexicon_metadata.normalization_formula,
                }
                for result in workspace.results
            ],
            "optional_modules": [
                {
                    "module_name": result.module_result.module_name,
                    "module_version": result.module_result.module_version,
                    "result_id": result.module_result.result_id,
                    "configuration_id": (
                        result.module_result.provenance.configuration_id
                    ),
                    "scenario_id": result.module_result.provenance.scenario_id,
                    "resources": [
                        asdict(resource)
                        for resource in result.module_result.provenance.resources
                    ],
                }
                for result, _exporter in ProjectRepository._workspace_modules(
                    workspace
                )
            ],
            "optional_module_configurations": (
                ProjectRepository._module_configurations(workspace)
            ),
        }

    @staticmethod
    def _metric_rows(workspace: WorkspaceAnalysis) -> list[tuple]:
        # Version 2 stores the complete six-profile cross-product directly
        # from retained evidence. Fixed-profile modules continue through the
        # module-metric persistence path below.
        from versevad.workspace_profiles import workspace_profile_metrics

        canonical_rows: list[tuple] = []
        recorded_coverage: set[tuple[str, str, str]] = set()
        scope_ids = {
            "ALL_LEXICAL": "all_matched",
            "STOPWORD_EXCLUDED": "stopwords_excluded",
            "CONTENT_WORDS": "content_words",
        }
        for item in workspace_profile_metrics(workspace):
            coverage = item.coverage
            coverage_key = (
                item.source_id,
                item.profile.scope.value,
                item.profile.weighting.value,
            )
            type_weighted = item.profile.weighting.value == "TYPE"
            matched_count = (
                coverage.matched_type_count
                if type_weighted
                else coverage.matched_token_count
            )
            eligible_count = (
                coverage.eligible_type_count
                if type_weighted
                else coverage.eligible_token_count
            )
            coverage_value = (
                coverage.type_coverage
                if type_weighted
                else coverage.token_coverage
            )
            if coverage_key not in recorded_coverage:
                recorded_coverage.add(coverage_key)
                if coverage_value is not None:
                    canonical_rows.append(
                        (
                            item.source_id,
                            item.source_label,
                            "continuous",
                            scope_ids[item.profile.scope.value],
                            "type_coverage" if type_weighted else "coverage",
                            "",
                            "",
                            item.profile.weighting.value.casefold(),
                            "proportion",
                            f"{eligible_count} eligible "
                            f"{'types' if type_weighted else 'tokens'}",
                            float(coverage_value),
                            matched_count,
                            matched_count,
                            eligible_count,
                            coverage_value,
                        )
                    )
            values: tuple[tuple[str, float | None, str], ...] = (
                ("mean", item.value, item.unit),
                (
                    "standard_deviation",
                    item.population_standard_deviation,
                    item.unit,
                ),
                ("cumulative", item.cumulative_value, f"summed {item.unit}"),
            )
            if item.module_id == "vad":
                observation_count = item.observation_count
                per_observation = (
                    1.0 / observation_count if observation_count else None
                )
                values += (
                    (
                        "above_midpoint_load",
                        item.above_midpoint_load,
                        "summed normalized distance above 0.5",
                    ),
                    (
                        "below_midpoint_load",
                        item.below_midpoint_load,
                        "summed normalized distance below 0.5",
                    ),
                    (
                        "net_midpoint_load",
                        item.net_midpoint_load,
                        "signed normalized midpoint distance",
                    ),
                    (
                        "absolute_midpoint_load",
                        item.absolute_midpoint_load,
                        "summed absolute normalized midpoint distance",
                    ),
                    (
                        "average_deviation_from_poem_mean",
                        item.average_deviation_from_mean,
                        "mean absolute deviation",
                    ),
                )
                if per_observation is not None:
                    values += tuple(
                        (
                            f"{name}_per_observation",
                            value * per_observation if value is not None else None,
                            "normalized midpoint distance per observation",
                        )
                        for name, value in (
                            ("above_midpoint_load", item.above_midpoint_load),
                            ("below_midpoint_load", item.below_midpoint_load),
                            ("net_midpoint_load", item.net_midpoint_load),
                            ("absolute_midpoint_load", item.absolute_midpoint_load),
                        )
                    )
                    values += tuple(
                        (
                            f"{name}_per_100_observations",
                            value * per_observation * 100 if value is not None else None,
                            "normalized midpoint distance per 100 observations",
                        )
                        for name, value in (
                            ("above_midpoint_load", item.above_midpoint_load),
                            ("below_midpoint_load", item.below_midpoint_load),
                            ("net_midpoint_load", item.net_midpoint_load),
                            ("absolute_midpoint_load", item.absolute_midpoint_load),
                        )
                    )
            for statistic, value, unit in values:
                if value is None:
                    continue
                metric_name = f"{item.module_id}_{item.metric_id}_{statistic}"
                dimension = item.metric_id
                scale = unit
                if item.module_id == "vad":
                    dimension = item.metric_id.removesuffix("_mean")
                    metric_name = {
                        "mean": "vad_mean",
                        "standard_deviation": "vad_standard_deviation",
                        "cumulative": "vad_rating_total",
                        "above_midpoint_load": "vad_above_midpoint_load",
                        "below_midpoint_load": "vad_below_midpoint_load",
                        "net_midpoint_load": "vad_net_midpoint_load",
                        "absolute_midpoint_load": "vad_absolute_midpoint_load",
                        "average_deviation_from_poem_mean": (
                            "vad_average_deviation_from_poem_mean"
                        ),
                        "above_midpoint_load_per_observation": (
                            "vad_above_midpoint_load_per_observation"
                        ),
                        "below_midpoint_load_per_observation": (
                            "vad_below_midpoint_load_per_observation"
                        ),
                        "net_midpoint_load_per_observation": (
                            "vad_net_midpoint_load_per_observation"
                        ),
                        "absolute_midpoint_load_per_observation": (
                            "vad_absolute_midpoint_load_per_observation"
                        ),
                        "above_midpoint_load_per_100_observations": (
                            "vad_above_midpoint_load_per_100_observations"
                        ),
                        "below_midpoint_load_per_100_observations": (
                            "vad_below_midpoint_load_per_100_observations"
                        ),
                        "net_midpoint_load_per_100_observations": (
                            "vad_net_midpoint_load_per_100_observations"
                        ),
                        "absolute_midpoint_load_per_100_observations": (
                            "vad_absolute_midpoint_load_per_100_observations"
                        ),
                    }[statistic]
                    if statistic in {"mean", "standard_deviation"}:
                        scale = "normalized_0_1"
                    elif statistic == "cumulative":
                        scale = "normalized_0_1_sum"
                canonical_rows.append(
                    (
                        item.source_id,
                        item.source_label,
                        "continuous",
                        scope_ids[item.profile.scope.value],
                        metric_name,
                        dimension,
                        "",
                        item.profile.weighting.value.casefold(),
                        scale,
                        (
                            f"{item.observation_count} observations; "
                            f"{matched_count}/"
                            f"{eligible_count} eligible "
                            f"{'types' if type_weighted else 'tokens'} matched"
                        ),
                        float(value),
                        item.observation_count,
                        matched_count,
                        eligible_count,
                        coverage_value,
                    )
                )
        return canonical_rows

        # Legacy construction remains below solely as a readable migration
        # reference for older database exports.
        rows = []
        view_key = {
            "All matched tokens": "all_matched",
            "Stopwords excluded": "stopwords_excluded",
        }
        cumulative = {
            (
                row.lexicon_id,
                view_key[row.analysis_view],
                row.weighting,
                row.dimension,
            ): row
            for row in vad_cumulative_views(workspace)
        }
        for result in workspace.results:
            metadata = result.lexicon_metadata
            common = (
                metadata.lexicon_id,
                metadata.display_name,
                metadata.value_kind.value,
            )
            all_coverage = result.coverage.lexical_token_coverage
            all_denominator = f"{result.coverage.total_lexical_tokens} lexical tokens"
            rows.append(
                (
                    *common,
                    "all_matched",
                    "coverage",
                    "",
                    "",
                    "token",
                    "proportion",
                    all_denominator,
                    all_coverage,
                    result.coverage.matched_token_count,
                    result.coverage.matched_token_count,
                    result.coverage.total_lexical_tokens,
                    all_coverage,
                )
            )
            if result.stopword_coverage is not None:
                filtered_coverage = result.stopword_coverage.lexical_token_coverage
                rows.append(
                    (
                        *common,
                        "stopwords_excluded",
                        "coverage",
                        "",
                        "",
                        "token",
                        "proportion",
                        (
                            f"{result.stopword_coverage.eligible_token_count} "
                            "eligible non-stopword, non-review-excluded tokens"
                        ),
                        filtered_coverage,
                        result.stopword_coverage.matched_token_count,
                        result.stopword_coverage.matched_token_count,
                        result.stopword_coverage.eligible_token_count,
                        filtered_coverage,
                    )
                )
            if result.vad_summary is not None:
                summary = result.vad_summary
                groups = (
                    (
                        "all_matched",
                        "token",
                        "normalized_0_1",
                        summary.token_weighted_normalized,
                        result.coverage.matched_token_count,
                        result.coverage.total_lexical_tokens,
                        all_coverage,
                    ),
                    (
                        "all_matched",
                        "type",
                        "normalized_0_1",
                        summary.type_weighted_normalized,
                        result.coverage.matched_token_count,
                        result.coverage.total_lexical_tokens,
                        all_coverage,
                    ),
                    (
                        "all_matched",
                        "token",
                        "source",
                        summary.token_weighted_original,
                        result.coverage.matched_token_count,
                        result.coverage.total_lexical_tokens,
                        all_coverage,
                    ),
                    (
                        "all_matched",
                        "type",
                        "source",
                        summary.type_weighted_original,
                        result.coverage.matched_token_count,
                        result.coverage.total_lexical_tokens,
                        all_coverage,
                    ),
                )
                filtered_groups = ()
                if result.stopword_coverage is not None:
                    filtered_groups = (
                        (
                            "stopwords_excluded",
                            "token",
                            "normalized_0_1",
                            summary.stopword_excluded_token_weighted_normalized,
                            result.stopword_coverage.matched_token_count,
                            result.stopword_coverage.eligible_token_count,
                            result.stopword_coverage.lexical_token_coverage,
                        ),
                        (
                            "stopwords_excluded",
                            "type",
                            "normalized_0_1",
                            summary.stopword_excluded_type_weighted_normalized,
                            result.stopword_coverage.matched_token_count,
                            result.stopword_coverage.eligible_token_count,
                            result.stopword_coverage.lexical_token_coverage,
                        ),
                        (
                            "stopwords_excluded",
                            "token",
                            "source",
                            summary.stopword_excluded_token_weighted_original,
                            result.stopword_coverage.matched_token_count,
                            result.stopword_coverage.eligible_token_count,
                            result.stopword_coverage.lexical_token_coverage,
                        ),
                        (
                            "stopwords_excluded",
                            "type",
                            "source",
                            summary.stopword_excluded_type_weighted_original,
                            result.stopword_coverage.matched_token_count,
                            result.stopword_coverage.eligible_token_count,
                            result.stopword_coverage.lexical_token_coverage,
                        ),
                    )
                for (
                    analysis_view,
                    weighting,
                    scale,
                    statistics,
                    matched_tokens,
                    lexical_tokens,
                    coverage,
                ) in (*groups, *filtered_groups):
                    if statistics is None:
                        continue
                    for dimension, values in statistics.by_dimension().items():
                        rows.append(
                            (
                                *common,
                                analysis_view,
                                "vad_mean",
                                dimension,
                                "",
                                weighting,
                                scale,
                                f"{values.count} included matched observations",
                                values.mean,
                                values.count,
                                matched_tokens,
                                lexical_tokens,
                                coverage,
                            )
                        )
                        rows.append(
                            (
                                *common,
                                analysis_view,
                                "vad_standard_deviation",
                                dimension,
                                "",
                                weighting,
                                scale,
                                f"{values.count} included matched observations",
                                values.population_standard_deviation,
                                values.count,
                                matched_tokens,
                                lexical_tokens,
                                coverage,
                            )
                        )
                for analysis_view in ("all_matched", "stopwords_excluded"):
                    for weighting_label, weighting in (
                        ("Token-weighted", "token"),
                        ("Type-weighted", "type"),
                    ):
                        for dimension in ("valence", "arousal", "dominance"):
                            totals = cumulative.get(
                                (
                                    metadata.lexicon_id,
                                    analysis_view,
                                    weighting_label,
                                    dimension,
                                )
                            )
                            if totals is None:
                                continue
                            cumulative_values = (
                            ("vad_rating_total", "normalized_0_1_sum", totals.rating_total),
                            (
                                "vad_above_midpoint_load",
                                "midpoint_deviation_sum",
                                totals.above_midpoint_deviation,
                            ),
                            (
                                "vad_below_midpoint_load",
                                "midpoint_deviation_sum",
                                totals.below_midpoint_deviation,
                            ),
                            (
                                "vad_net_midpoint_load",
                                "midpoint_deviation_sum",
                                totals.net_midpoint_deviation,
                            ),
                            (
                                "vad_absolute_midpoint_load",
                                "midpoint_deviation_sum",
                                totals.absolute_midpoint_deviation,
                            ),
                            (
                                "vad_above_midpoint_load_per_observation",
                                "mean_midpoint_deviation",
                                totals.above_midpoint_deviation_per_observation,
                            ),
                            (
                                "vad_below_midpoint_load_per_observation",
                                "mean_midpoint_deviation",
                                totals.below_midpoint_deviation_per_observation,
                            ),
                            (
                                "vad_net_midpoint_load_per_observation",
                                "mean_midpoint_deviation",
                                totals.net_midpoint_deviation_per_observation,
                            ),
                            (
                                "vad_absolute_midpoint_load_per_observation",
                                "mean_midpoint_deviation",
                                totals.absolute_midpoint_deviation_per_observation,
                            ),
                            (
                                "vad_above_midpoint_load_per_100_observations",
                                "midpoint_deviation_per_100_observations",
                                totals.above_midpoint_deviation_per_100,
                            ),
                            (
                                "vad_below_midpoint_load_per_100_observations",
                                "midpoint_deviation_per_100_observations",
                                totals.below_midpoint_deviation_per_100,
                            ),
                            (
                                "vad_net_midpoint_load_per_100_observations",
                                "midpoint_deviation_per_100_observations",
                                totals.net_midpoint_deviation_per_100,
                            ),
                            (
                                "vad_absolute_midpoint_load_per_100_observations",
                                "midpoint_deviation_per_100_observations",
                                totals.absolute_midpoint_deviation_per_100,
                            ),
                            (
                                "vad_average_deviation_from_poem_mean",
                                "mean_absolute_deviation",
                                totals.average_deviation_from_poem_mean,
                            ),
                            )
                            matched_tokens = (
                                result.coverage.matched_token_count
                                if analysis_view == "all_matched"
                                else result.stopword_coverage.matched_token_count
                            )
                            for metric, scale, value in cumulative_values:
                                rows.append(
                                    (
                                        *common,
                                        analysis_view,
                                        metric,
                                        dimension,
                                        "",
                                        weighting,
                                        scale,
                                        (
                                            f"{totals.matched_observations} included "
                                            "matched observations"
                                        ),
                                        value,
                                        totals.matched_observations,
                                        matched_tokens,
                                        totals.lexical_tokens,
                                        totals.lexical_coverage,
                                    )
                                )
            for statistics in result.category_statistics:
                rows.append(
                    (
                        *common,
                        "all_matched",
                        "association_rate",
                        "",
                        statistics.category,
                        "token",
                        "proportion",
                        all_denominator,
                        statistics.proportion_of_lexical_tokens,
                        statistics.associated_token_count,
                        result.coverage.matched_token_count,
                        result.coverage.total_lexical_tokens,
                        all_coverage,
                    )
                )
            for statistics in result.intensity_statistics:
                rows.extend(
                    (
                        (
                            *common,
                            "all_matched",
                            "intensity_prevalence",
                            "",
                            statistics.category,
                            "token",
                            "proportion",
                            all_denominator,
                            statistics.prevalence_among_lexical_tokens,
                            statistics.matched_token_occurrences,
                            result.coverage.matched_token_count,
                            result.coverage.total_lexical_tokens,
                            all_coverage,
                        ),
                        (
                            *common,
                            "all_matched",
                            "intensity_mean",
                            "",
                            statistics.category,
                            "token",
                            "source_0_1",
                            (
                                f"{statistics.matched_token_occurrences} supplied "
                                "matched pairs"
                            ),
                            statistics.token_weighted.mean,
                            statistics.matched_token_occurrences,
                            result.coverage.matched_token_count,
                            result.coverage.total_lexical_tokens,
                            all_coverage,
                        ),
                    )
                )
        return rows

    @staticmethod
    def _review_candidate_rows(workspace: WorkspaceAnalysis) -> list[tuple]:
        """Retain occurrence-level evidence for semantic review without source text copies."""

        rows: list[tuple] = []
        for result in workspace.results:
            tokens_by_id = {token.token_id: token for token in result.tokens}
            for match in result.matches:
                if match.selection in {
                    MatchSelection.NOT_ELIGIBLE,
                    MatchSelection.SUPPRESSED_COMPONENT,
                    MatchSelection.SUPPRESSED_OVERLAP,
                }:
                    continue
                tokens = tuple(
                    tokens_by_id[token_id]
                    for token_id in match.token_ids
                    if token_id in tokens_by_id
                )
                if not tokens or not any(token.is_lexical for token in tokens):
                    continue
                if match.selection == MatchSelection.EXCLUDED_REVIEW:
                    risk_category = "review_exclusion"
                    risk_reason = "An active review decision excluded this candidate match."
                elif "collision" in match.reason.casefold():
                    risk_category = "source_collision"
                    risk_reason = (
                        "Capitalization did not resolve multiple source entries; no entry was guessed."
                    )
                elif match.method == MatchMethod.UNMATCHED:
                    risk_category = "unmatched"
                    risk_reason = "No published entry matched under the active policy."
                elif match.method == MatchMethod.LEMMA:
                    risk_category = "lemma_fallback"
                    risk_reason = (
                        "A POS-sensitive lemma supplied the match after the exact form failed."
                    )
                elif match.method == MatchMethod.POSSESSIVE:
                    risk_category = "possessive_normalization"
                    risk_reason = "Conservative possessive normalization supplied the match."
                elif match.method == MatchMethod.PHRASE:
                    risk_category = "multiword_phrase"
                    risk_reason = "A source-supplied multiword entry supplied this match."
                elif match.method == MatchMethod.USER_MAPPING:
                    risk_category = "approved_mapping"
                    risk_reason = "An explicit active review mapping supplied this match."
                else:
                    risk_category = "exact_match"
                    risk_reason = "Direct published entry; available for optional contextual review."
                rows.append(
                    (
                        result.lexicon_metadata.lexicon_id,
                        result.lexicon_metadata.display_name,
                        match.match_id,
                        match.start_token_position,
                        match.line_number,
                        " ".join(token.surface_form for token in tokens),
                        " ".join(token.normalized_form for token in tokens),
                        match.matched_term or "",
                        match.method.value,
                        match.selection.value,
                        int(match.included),
                        risk_category,
                        risk_reason,
                        tokens[0].context,
                    )
                )
        return rows

    @staticmethod
    def _module_persistence_rows(
        workspace: WorkspaceAnalysis,
    ) -> tuple[dict[str, object], ...]:
        """Materialize generic module envelopes and existing exports once."""

        rows = []
        for detailed_result, exporter in ProjectRepository._workspace_modules(
            workspace
        ):
            result = detailed_result.module_result
            coverage_by_id = {
                item.coverage_id: item for item in result.coverage
            }
            metric_rows = []
            for metric in result.metrics:
                coverage_id = _OBSERVATION_COVERAGE_BY_METRIC.get(
                    (result.module_name, metric.metric_id)
                )
                coverage = (
                    coverage_by_id.get(coverage_id)
                    if metric.scope == "document" and coverage_id
                    else None
                )
                metric_rows.append(
                    (
                        metric.metric_id,
                        _json_dumps(metric.value),
                        metric.layer.value,
                        metric.scope,
                        metric.scope_id,
                        metric.unit,
                        metric.weighting,
                        metric.denominator,
                        coverage.matched_count if coverage is not None else None,
                        metric.note,
                    )
                )
            coverage_rows = [
                (
                    item.coverage_id,
                    item.scope,
                    item.scope_id,
                    item.eligible_count,
                    item.matched_count,
                    item.unmatched_count,
                    item.coverage_rate,
                    item.unit,
                    _json_dumps(item.unmatched_items),
                    item.note,
                )
                for item in result.coverage
            ]
            warning_rows = [
                (
                    warning.code,
                    warning.message,
                    warning.severity.value,
                    warning.technical_detail,
                )
                for warning in result.warnings
            ]
            artifacts = []
            for filename, content in exporter(detailed_result).items():
                if (
                    not filename
                    or Path(filename).name != filename
                    or "/" in filename
                    or "\\" in filename
                ):
                    raise ValueError(
                        "A module export supplied an unsafe artifact filename."
                    )
                payload = bytes(content)
                artifacts.append(
                    (
                        filename,
                        payload,
                        hashlib.sha256(payload).hexdigest(),
                        len(payload),
                    )
                )
            rows.append(
                {
                    "module_result": result,
                    "provenance_json": _json_dumps(asdict(result.provenance)),
                    "metrics": tuple(metric_rows),
                    "coverage": tuple(coverage_rows),
                    "warnings": tuple(warning_rows),
                    "artifacts": tuple(artifacts),
                }
            )
        return tuple(rows)

    def save_analysis(
        self,
        project_id: str,
        text_id: str,
        workspace: WorkspaceAnalysis,
        *,
        batch_id: str | None = None,
    ) -> str:
        """Atomically persist a completed immutable corpus analysis."""

        self.initialize()
        text = self.get_text(text_id)
        if text.project_id != project_id:
            raise ValueError("The selected text does not belong to this project.")
        if text.text_sha256 != workspace.document.text_sha256:
            raise ValueError("The analysis does not match the active preserved text version.")
        if workspace.document.text_id != text.text_id:
            raise ValueError("The analysis text identity does not match the selected corpus text.")
        if workspace.document.text_version_id != text.text_version_id:
            raise ValueError("The analysis does not identify the active preserved text version.")
        run_id = _id("run")
        now = _now()
        manifest = self._manifest(workspace)
        signature_source = _json_dumps(manifest)
        signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()
        metric_rows = self._metric_rows(workspace)
        unmatched = unmatched_views(workspace)
        review_candidates = self._review_candidate_rows(workspace)
        module_rows = self._module_persistence_rows(workspace)
        with self._connect() as connection:
            if batch_id is not None:
                batch = connection.execute(
                    "SELECT project_id, status FROM corpus_batches WHERE batch_id = ?",
                    (batch_id,),
                ).fetchone()
                if batch is None or batch["project_id"] != project_id:
                    raise ValueError("The corpus batch does not belong to this project.")
                if batch["status"] != "pending":
                    raise ValueError("The corpus batch is no longer accepting results.")
            connection.execute(
                """
                INSERT INTO analysis_runs(
                    run_id, project_id, text_id, text_version_id, batch_id, status, scenario_id,
                    scenario_version_id, phrase_policy, minimum_match_requirement, lexicon_ids_json,
                    software_version, run_signature, manifest_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, 'complete', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    text_id,
                    text.text_version_id,
                    batch_id,
                    workspace.comparison.scenario_id,
                    workspace.request.scenario_version_id,
                    workspace.request.phrase_policy.value,
                    workspace.request.minimum_match_requirement,
                    json.dumps(workspace.request.lexicon_ids),
                    __version__,
                    signature,
                    _json_dumps(manifest),
                    now,
                    now,
                ),
            )
            connection.executemany(
                """
                INSERT INTO analysis_metrics(
                    run_id, lexicon_id, lexicon_display_name, value_kind, analysis_view, metric,
                    dimension, category, weighting, scale, denominator, value,
                    observations, matched_tokens, lexical_tokens, coverage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(run_id, *row) for row in metric_rows],
            )
            connection.executemany(
                """
                INSERT INTO unmatched_observations(
                    run_id, project_id, text_id, lexicon_id, lexicon_display_name,
                    normalized_form, display_form, frequency, pos, proposed_lemma,
                    example_line, example_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        project_id,
                        text_id,
                        row.lexicon_id,
                        row.lexicon,
                        row.normalized_form,
                        row.surface,
                        row.frequency,
                        row.pos,
                        row.proposed_lemma,
                        row.example_line,
                        row.example_context,
                    )
                    for row in unmatched
                ],
            )
            connection.executemany(
                """
                INSERT INTO review_candidates(
                    run_id, project_id, text_id, text_version_id, lexicon_id,
                    lexicon_display_name, match_id, token_position, line_number,
                    surface_form, normalized_form, matched_term, method, selection,
                    included, risk_category, risk_reason, context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        project_id,
                        text_id,
                        text.text_version_id,
                        *row,
                    )
                    for row in review_candidates
                ],
            )
            for module_row in module_rows:
                module_result = module_row["module_result"]
                module_result_row_id = (
                    f"{run_id}:{module_result.module_name}"
                )
                connection.execute(
                    """
                    INSERT INTO module_results(
                        module_result_row_id, run_id, module_name,
                        module_version, result_id, configuration_id,
                        scenario_id, source_text_sha256, provenance_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        module_result_row_id,
                        run_id,
                        module_result.module_name,
                        module_result.module_version,
                        module_result.result_id,
                        module_result.provenance.configuration_id,
                        module_result.provenance.scenario_id,
                        module_result.provenance.source_text_sha256,
                        module_row["provenance_json"],
                        now,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO module_metrics(
                        module_result_row_id, metric_id, value_json, layer,
                        scope, scope_id, unit, weighting, denominator,
                        observation_count, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (module_result_row_id, *row)
                        for row in module_row["metrics"]
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO module_coverage(
                        module_result_row_id, coverage_id, scope, scope_id,
                        eligible_count, matched_count, unmatched_count,
                        coverage_rate, unit, unmatched_items_json, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (module_result_row_id, *row)
                        for row in module_row["coverage"]
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO module_warnings(
                        module_result_row_id, code, message, severity,
                        technical_detail
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (module_result_row_id, *row)
                        for row in module_row["warnings"]
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO module_artifacts(
                        module_result_row_id, filename, content,
                        content_sha256, size_bytes
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (module_result_row_id, *row)
                        for row in module_row["artifacts"]
                    ],
                )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id)
            )
        return run_id

    @staticmethod
    def _visible_run_ids(
        connection: sqlite3.Connection,
        project_id: str,
    ) -> tuple[str, ...]:
        """Return one internally consistent completed batch when available."""

        batch = connection.execute(
            """
            SELECT batch_id FROM corpus_batches
            WHERE project_id = ? AND status = 'complete'
            ORDER BY completed_at DESC, rowid DESC LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        if batch is not None:
            rows = connection.execute(
                """
                SELECT run_id FROM analysis_runs
                WHERE batch_id = ? AND status = 'complete'
                ORDER BY text_id, completed_at
                """,
                (batch["batch_id"],),
            ).fetchall()
            return tuple(row["run_id"] for row in rows)
        rows = connection.execute(
            """
            WITH ranked AS (
                SELECT run_id, ROW_NUMBER() OVER (
                    PARTITION BY text_id ORDER BY completed_at DESC, rowid DESC
                ) AS rank_number
                FROM analysis_runs
                WHERE project_id = ? AND status = 'complete' AND batch_id IS NULL
            )
            SELECT run_id FROM ranked WHERE rank_number = 1
            """,
            (project_id,),
        ).fetchall()
        return tuple(row["run_id"] for row in rows)

    def list_latest_metrics(
        self,
        project_id: str,
        *,
        text_id: str | None = None,
        analysis_views: Sequence[str] | None = None,
        weightings: Sequence[str] | None = None,
        metrics: Sequence[str] | None = None,
    ) -> tuple[CorpusMetricRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            run_ids = self._visible_run_ids(connection, project_id)
            if not run_ids:
                return ()
            return self._metrics_for_run_ids(
                connection,
                run_ids,
                text_id=text_id,
                analysis_views=analysis_views,
                weightings=weightings,
                metrics=metrics,
            )

    @staticmethod
    def _metrics_for_run_ids(
        connection: sqlite3.Connection,
        run_ids: Sequence[str],
        *,
        text_id: str | None = None,
        analysis_views: Sequence[str] | None = None,
        weightings: Sequence[str] | None = None,
        metrics: Sequence[str] | None = None,
    ) -> tuple[CorpusMetricRecord, ...]:
        if not run_ids:
            return ()
        placeholders = ",".join("?" for _ in run_ids)
        clauses = [f"r.run_id IN ({placeholders})"]
        parameters: list[object] = list(run_ids)
        if text_id is not None:
            clauses.append("r.text_id = ?")
            parameters.append(text_id)
        for column, values in (
            ("m.analysis_view", analysis_views),
            ("m.weighting", weightings),
            ("m.metric", metrics),
        ):
            selected = tuple(values or ())
            if selected:
                value_placeholders = ",".join("?" for _ in selected)
                clauses.append(f"{column} IN ({value_placeholders})")
                parameters.extend(selected)
        rows = connection.execute(
            f"""
            SELECT r.run_id, r.text_id, r.text_version_id, t.title, t.author,
                   t.collection_name AS collection, t.date_label, t.genre,
                   m.lexicon_id, m.lexicon_display_name AS lexicon, m.value_kind,
                   m.analysis_view, m.metric, m.dimension, m.category, m.weighting, m.scale,
                   m.denominator, m.value, m.observations, m.matched_tokens, m.lexical_tokens,
                   m.coverage, r.completed_at
            FROM analysis_runs r
            JOIN analysis_metrics m ON m.run_id = r.run_id
            JOIN texts t ON t.text_id = r.text_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.title COLLATE NOCASE, m.lexicon_display_name, m.metric,
                     m.dimension, m.category, m.weighting, m.scale
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(CorpusMetricRecord(**dict(row)) for row in rows)

    def list_completed_batches(
        self,
        project_id: str,
    ) -> tuple[CorpusBatchRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT batch_id, project_id, status, text_ids_json, lexicon_ids_json,
                       module_names_json, module_configuration_json,
                       phrase_policy, minimum_match_requirement, stopword_mode,
                       protected_stopwords_json, custom_stopword_additions_json,
                       custom_stopword_removals_json, scenario_version_id,
                       created_at, completed_at, error_message
                FROM corpus_batches
                WHERE project_id = ? AND status = 'complete'
                ORDER BY completed_at DESC, rowid DESC
                """,
                (project_id,),
            ).fetchall()
        return tuple(self._batch(row) for row in rows)

    def list_metrics_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusMetricRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            batch = connection.execute(
                """
                SELECT project_id, status
                FROM corpus_batches WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchone()
            if (
                batch is None
                or batch["project_id"] != project_id
                or batch["status"] != "complete"
            ):
                raise ValueError(
                    "Choose a completed corpus batch belonging to this project."
                )
            rows = connection.execute(
                """
                SELECT run_id FROM analysis_runs
                WHERE batch_id = ? AND status = 'complete'
                ORDER BY text_id, completed_at
                """,
                (batch_id,),
            ).fetchall()
            return self._metrics_for_run_ids(
                connection,
                tuple(row["run_id"] for row in rows),
            )

    @staticmethod
    def _module_results_for_run_ids(
        connection: sqlite3.Connection,
        run_ids: Sequence[str],
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleResultRecord, ...]:
        if not run_ids:
            return ()
        placeholders = ",".join("?" for _ in run_ids)
        clauses = [f"r.run_id IN ({placeholders})"]
        parameters: list[object] = list(run_ids)
        if text_id is not None:
            clauses.append("r.text_id = ?")
            parameters.append(text_id)
        selected_modules = tuple(module_names or ())
        if selected_modules:
            module_placeholders = ",".join("?" for _ in selected_modules)
            clauses.append(f"mr.module_name IN ({module_placeholders})")
            parameters.extend(selected_modules)
        rows = connection.execute(
            f"""
            SELECT mr.module_result_row_id, r.run_id, r.text_id,
                   r.text_version_id, t.title, t.author,
                   t.collection_name AS collection, t.date_label, t.genre,
                   mr.module_name, mr.module_version, mr.result_id,
                   mr.configuration_id, mr.scenario_id,
                   mr.source_text_sha256, mr.provenance_json,
                   r.completed_at
            FROM analysis_runs r
            JOIN module_results mr ON mr.run_id = r.run_id
            JOIN texts t ON t.text_id = r.text_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.title COLLATE NOCASE, mr.module_name
            """,
            tuple(parameters),
        ).fetchall()
        materialized = []
        for row in rows:
            values = dict(row)
            values["provenance"] = json.loads(
                values.pop("provenance_json")
            )
            materialized.append(CorpusModuleResultRecord(**values))
        return tuple(materialized)

    def list_latest_module_results(
        self,
        project_id: str,
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleResultRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_results_for_run_ids(
                connection,
                self._visible_run_ids(connection, project_id),
                text_id=text_id,
                module_names=module_names,
            )

    def _validated_batch_run_ids(
        self,
        connection: sqlite3.Connection,
        project_id: str,
        batch_id: str,
    ) -> tuple[str, ...]:
        batch = connection.execute(
            """
            SELECT project_id, status FROM corpus_batches
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()
        if (
            batch is None
            or batch["project_id"] != project_id
            or batch["status"] not in {"pending", "complete"}
        ):
            raise ValueError(
                "Choose a current or completed corpus batch belonging to this project."
            )
        rows = connection.execute(
            """
            SELECT run_id FROM analysis_runs
            WHERE batch_id = ? AND status = 'complete'
            ORDER BY text_id, completed_at
            """,
            (batch_id,),
        ).fetchall()
        return tuple(row["run_id"] for row in rows)

    def list_module_results_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusModuleResultRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_results_for_run_ids(
                connection,
                self._validated_batch_run_ids(
                    connection,
                    project_id,
                    batch_id,
                ),
            )

    @staticmethod
    def _module_metrics_for_run_ids(
        connection: sqlite3.Connection,
        run_ids: Sequence[str],
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
        scopes: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleMetricRecord, ...]:
        if not run_ids:
            return ()
        placeholders = ",".join("?" for _ in run_ids)
        clauses = [f"r.run_id IN ({placeholders})"]
        parameters: list[object] = list(run_ids)
        if text_id is not None:
            clauses.append("r.text_id = ?")
            parameters.append(text_id)
        for column, values in (
            ("mr.module_name", module_names),
            ("mm.scope", scopes),
        ):
            selected = tuple(values or ())
            if selected:
                value_placeholders = ",".join("?" for _ in selected)
                clauses.append(f"{column} IN ({value_placeholders})")
                parameters.extend(selected)
        rows = connection.execute(
            f"""
            SELECT r.run_id, r.text_id, r.text_version_id, t.title, t.author,
                   t.collection_name AS collection, t.date_label, t.genre,
                   mr.module_name, mr.module_version, mr.result_id,
                   mr.configuration_id, mm.metric_id, mm.value_json,
                   mm.layer, mm.scope, mm.scope_id, mm.unit, mm.weighting,
                   mm.denominator, mm.observation_count, mm.note,
                   r.completed_at
            FROM analysis_runs r
            JOIN module_results mr ON mr.run_id = r.run_id
            JOIN module_metrics mm
              ON mm.module_result_row_id = mr.module_result_row_id
            JOIN texts t ON t.text_id = r.text_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.title COLLATE NOCASE, mr.module_name, mm.scope,
                     mm.scope_id, mm.metric_id
            """,
            tuple(parameters),
        ).fetchall()
        materialized = []
        for row in rows:
            values = dict(row)
            values["value"] = json.loads(values.pop("value_json"))
            materialized.append(CorpusModuleMetricRecord(**values))
        return tuple(materialized)

    def list_latest_module_metrics(
        self,
        project_id: str,
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
        scopes: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleMetricRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_metrics_for_run_ids(
                connection,
                self._visible_run_ids(connection, project_id),
                text_id=text_id,
                module_names=module_names,
                scopes=scopes,
            )

    def list_module_metrics_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusModuleMetricRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_metrics_for_run_ids(
                connection,
                self._validated_batch_run_ids(
                    connection,
                    project_id,
                    batch_id,
                ),
            )

    @staticmethod
    def _module_coverage_for_run_ids(
        connection: sqlite3.Connection,
        run_ids: Sequence[str],
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
        scopes: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleCoverageRecord, ...]:
        if not run_ids:
            return ()
        placeholders = ",".join("?" for _ in run_ids)
        clauses = [f"r.run_id IN ({placeholders})"]
        parameters: list[object] = list(run_ids)
        if text_id is not None:
            clauses.append("r.text_id = ?")
            parameters.append(text_id)
        for column, values in (
            ("mr.module_name", module_names),
            ("mc.scope", scopes),
        ):
            selected = tuple(values or ())
            if selected:
                value_placeholders = ",".join("?" for _ in selected)
                clauses.append(f"{column} IN ({value_placeholders})")
                parameters.extend(selected)
        rows = connection.execute(
            f"""
            SELECT r.run_id, r.text_id, r.text_version_id, t.title,
                   mr.module_name, mr.configuration_id, mc.coverage_id,
                   mc.scope, mc.scope_id, mc.eligible_count,
                   mc.matched_count, mc.unmatched_count, mc.coverage_rate,
                   mc.unit, mc.unmatched_items_json, mc.note, r.completed_at
            FROM analysis_runs r
            JOIN module_results mr ON mr.run_id = r.run_id
            JOIN module_coverage mc
              ON mc.module_result_row_id = mr.module_result_row_id
            JOIN texts t ON t.text_id = r.text_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.title COLLATE NOCASE, mr.module_name, mc.coverage_id
            """,
            tuple(parameters),
        ).fetchall()
        materialized = []
        for row in rows:
            values = dict(row)
            values["unmatched_items"] = tuple(
                json.loads(values.pop("unmatched_items_json"))
            )
            materialized.append(CorpusModuleCoverageRecord(**values))
        return tuple(materialized)

    def list_latest_module_coverage(
        self,
        project_id: str,
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
        scopes: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleCoverageRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_coverage_for_run_ids(
                connection,
                self._visible_run_ids(connection, project_id),
                text_id=text_id,
                module_names=module_names,
                scopes=scopes,
            )

    def list_module_coverage_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusModuleCoverageRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_coverage_for_run_ids(
                connection,
                self._validated_batch_run_ids(
                    connection,
                    project_id,
                    batch_id,
                ),
            )

    @staticmethod
    def _module_warnings_for_run_ids(
        connection: sqlite3.Connection,
        run_ids: Sequence[str],
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleWarningRecord, ...]:
        if not run_ids:
            return ()
        placeholders = ",".join("?" for _ in run_ids)
        clauses = [f"r.run_id IN ({placeholders})"]
        parameters: list[object] = list(run_ids)
        if text_id is not None:
            clauses.append("r.text_id = ?")
            parameters.append(text_id)
        selected_modules = tuple(module_names or ())
        if selected_modules:
            module_placeholders = ",".join("?" for _ in selected_modules)
            clauses.append(f"mr.module_name IN ({module_placeholders})")
            parameters.extend(selected_modules)
        rows = connection.execute(
            f"""
            SELECT r.run_id, r.text_id, r.text_version_id, t.title,
                   mr.module_name, mr.configuration_id, mw.code, mw.message,
                   mw.severity, mw.technical_detail, r.completed_at
            FROM analysis_runs r
            JOIN module_results mr ON mr.run_id = r.run_id
            JOIN module_warnings mw
              ON mw.module_result_row_id = mr.module_result_row_id
            JOIN texts t ON t.text_id = r.text_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.title COLLATE NOCASE, mr.module_name, mw.code
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(CorpusModuleWarningRecord(**dict(row)) for row in rows)

    def list_latest_module_warnings(
        self,
        project_id: str,
        *,
        text_id: str | None = None,
        module_names: Sequence[str] | None = None,
    ) -> tuple[CorpusModuleWarningRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_warnings_for_run_ids(
                connection,
                self._visible_run_ids(connection, project_id),
                text_id=text_id,
                module_names=module_names,
            )

    def list_module_warnings_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusModuleWarningRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            return self._module_warnings_for_run_ids(
                connection,
                self._validated_batch_run_ids(
                    connection,
                    project_id,
                    batch_id,
                ),
            )

    def list_module_artifacts(
        self,
        run_id: str,
        module_name: str,
    ) -> tuple[CorpusModuleArtifactRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.run_id, r.text_id, r.text_version_id, t.title,
                       mr.module_name, ma.filename, ma.content,
                       ma.content_sha256, ma.size_bytes
                FROM analysis_runs r
                JOIN module_results mr ON mr.run_id = r.run_id
                JOIN module_artifacts ma
                  ON ma.module_result_row_id = mr.module_result_row_id
                JOIN texts t ON t.text_id = r.text_id
                WHERE r.run_id = ? AND mr.module_name = ?
                ORDER BY ma.filename
                """,
                (run_id, module_name),
            ).fetchall()
        return tuple(
            CorpusModuleArtifactRecord(**dict(row)) for row in rows
        )

    def build_module_artifact_zip(
        self,
        run_id: str,
        module_name: str,
    ) -> bytes:
        artifacts = self.list_module_artifacts(run_id, module_name)
        if not artifacts:
            raise ValueError(
                "No persisted audit artifacts were found for this work and module."
            )
        output = io.BytesIO()
        with zipfile.ZipFile(
            output,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for artifact in artifacts:
                if hashlib.sha256(artifact.content).hexdigest() != (
                    artifact.content_sha256
                ):
                    raise RuntimeError(
                        "A persisted module artifact failed its checksum check."
                    )
                info = zipfile.ZipInfo(
                    artifact.filename,
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, artifact.content)
        return output.getvalue()

    def save_module_aggregates(
        self,
        batch_id: str,
        records: Iterable[CorpusModuleAggregateRecord],
    ) -> None:
        materialized = tuple(records)
        self.initialize()
        with self._connect() as connection:
            batch = connection.execute(
                """
                SELECT project_id, status FROM corpus_batches
                WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchone()
            if batch is None:
                raise KeyError(f"Unknown corpus batch: {batch_id}")
            if batch["status"] != "pending":
                raise ValueError(
                    "Only a pending corpus batch can receive aggregate results."
                )
            for row in materialized:
                if (
                    row.batch_id != batch_id
                    or row.project_id != batch["project_id"]
                ):
                    raise ValueError(
                        "A module aggregate does not belong to this corpus batch."
                    )
                if row.works_included < 0 or row.works_omitted < 0:
                    raise ValueError(
                        "Module aggregate work counts cannot be negative."
                    )
                if row.observation_count < 0:
                    raise ValueError(
                        "A module aggregate observation count cannot be negative."
                    )
            connection.executemany(
                """
                INSERT INTO corpus_module_aggregates(
                    aggregate_id, batch_id, project_id, module_name,
                    configuration_id, metric_id, aggregation_method,
                    value_json, unit, works_included, works_omitted,
                    observation_count, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.aggregate_id,
                        row.batch_id,
                        row.project_id,
                        row.module_name,
                        row.configuration_id,
                        row.metric_id,
                        row.aggregation_method,
                        _json_dumps(row.value),
                        row.unit,
                        row.works_included,
                        row.works_omitted,
                        row.observation_count,
                        row.note,
                    )
                    for row in materialized
                ],
            )

    def list_module_aggregates_for_batch(
        self,
        project_id: str,
        batch_id: str,
    ) -> tuple[CorpusModuleAggregateRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            batch = connection.execute(
                """
                SELECT project_id, status FROM corpus_batches
                WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchone()
            if (
                batch is None
                or batch["project_id"] != project_id
                or batch["status"] not in {"pending", "complete"}
            ):
                raise ValueError(
                    "Choose a current or completed corpus batch belonging to this project."
                )
            rows = connection.execute(
                """
                SELECT aggregate_id, batch_id, project_id, module_name,
                       configuration_id, metric_id, aggregation_method,
                       value_json, unit, works_included, works_omitted,
                       observation_count, note
                FROM corpus_module_aggregates
                WHERE batch_id = ?
                ORDER BY module_name, metric_id, aggregation_method
                """,
                (batch_id,),
            ).fetchall()
        materialized = []
        for row in rows:
            values = dict(row)
            values["value"] = json.loads(values.pop("value_json"))
            materialized.append(CorpusModuleAggregateRecord(**values))
        return tuple(materialized)

    def list_latest_module_aggregates(
        self,
        project_id: str,
    ) -> tuple[CorpusModuleAggregateRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT batch_id FROM corpus_batches
                WHERE project_id = ? AND status = 'complete'
                ORDER BY completed_at DESC, rowid DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return ()
        return self.list_module_aggregates_for_batch(
            project_id,
            row["batch_id"],
        )

    def latest_methodology(self, project_id: str) -> Mapping[str, object]:
        """Return one recorded manifest from the latest visible complete batch."""

        self.initialize()
        with self._connect() as connection:
            run_ids = self._visible_run_ids(connection, project_id)
            if not run_ids:
                return {}
            row = connection.execute(
                "SELECT manifest_json FROM analysis_runs WHERE run_id = ?",
                (run_ids[0],),
            ).fetchone()
        return json.loads(row["manifest_json"]) if row is not None else {}

    def upsert_unmatched_note(
        self,
        *,
        project_id: str,
        text_id: str,
        lexicon_id: str,
        normalized_form: str,
        display_form: str,
        status: str,
        note: str,
        proposed_mapping: str = "",
    ) -> str:
        allowed = {"unreviewed", "reviewed", "needs mapping", "accepted gap"}
        if status not in allowed:
            raise ValueError(f"Unknown quality-control status: {status}")
        normalized_form = normalized_form.strip()
        if not normalized_form:
            raise ValueError("An unmatched note needs a word or normalized form.")
        self.initialize()
        now = _now()
        with self._connect() as connection:
            owner = connection.execute(
                "SELECT project_id FROM texts WHERE text_id = ?", (text_id,)
            ).fetchone()
            if owner is None or owner["project_id"] != project_id:
                raise ValueError("The unmatched item does not belong to this project.")
            existing = connection.execute(
                """
                SELECT note_id, created_at FROM unmatched_notes
                WHERE project_id = ? AND text_id = ? AND lexicon_id = ? AND normalized_form = ?
                """,
                (project_id, text_id, lexicon_id, normalized_form),
            ).fetchone()
            note_id = existing["note_id"] if existing else _id("note")
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                INSERT INTO unmatched_notes(
                    note_id, project_id, text_id, lexicon_id, normalized_form,
                    display_form, status, note, proposed_mapping, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, text_id, lexicon_id, normalized_form)
                DO UPDATE SET display_form = excluded.display_form,
                              status = excluded.status,
                              note = excluded.note,
                              proposed_mapping = excluded.proposed_mapping,
                              updated_at = excluded.updated_at
                """,
                (
                    note_id,
                    project_id,
                    text_id,
                    lexicon_id,
                    normalized_form,
                    display_form,
                    status,
                    note.strip(),
                    proposed_mapping.strip(),
                    created_at,
                    now,
                ),
            )
        return note_id

    def list_latest_unmatched(self, project_id: str) -> tuple[UnmatchedQcRecord, ...]:
        self.initialize()
        with self._connect() as connection:
            run_ids = self._visible_run_ids(connection, project_id)
            if not run_ids:
                return ()
            placeholders = ",".join("?" for _ in run_ids)
            rows = connection.execute(
                f"""
                SELECT o.project_id, o.text_id, t.title AS text_title, o.lexicon_id,
                       o.lexicon_display_name AS lexicon, o.normalized_form,
                       o.display_form, o.frequency, o.pos, o.proposed_lemma,
                       o.example_line, o.example_context,
                       COALESCE(n.status, 'unreviewed') AS status,
                       COALESCE(n.note, '') AS note,
                       COALESCE(n.proposed_mapping, '') AS proposed_mapping,
                       n.note_id, n.updated_at
                FROM unmatched_observations o
                JOIN texts t ON t.text_id = o.text_id
                LEFT JOIN unmatched_notes n
                  ON n.project_id = o.project_id AND n.text_id = o.text_id
                 AND n.lexicon_id = o.lexicon_id
                 AND n.normalized_form = o.normalized_form
                WHERE o.run_id IN ({placeholders})
                ORDER BY t.title COLLATE NOCASE, o.lexicon_display_name,
                         o.frequency DESC, o.display_form COLLATE NOCASE
                """,
                run_ids,
            ).fetchall()
        return tuple(UnmatchedQcRecord(**dict(row)) for row in rows)

    def list_review_candidates(
        self,
        project_id: str,
        *,
        include_exact: bool = False,
    ) -> tuple[ReviewCandidateRecord, ...]:
        """List occurrence-level evidence from the latest visible complete batch."""

        self.initialize()
        with self._connect() as connection:
            run_ids = self._visible_run_ids(connection, project_id)
            if not run_ids:
                return ()
            placeholders = ",".join("?" for _ in run_ids)
            exact_clause = "" if include_exact else " AND c.risk_category != 'exact_match'"
            rows = connection.execute(
                f"""
                SELECT c.run_id, c.project_id, c.text_id, c.text_version_id,
                       t.title AS text_title, c.lexicon_id,
                       c.lexicon_display_name AS lexicon, c.match_id,
                       c.token_position, c.line_number, c.surface_form,
                       c.normalized_form, c.matched_term, c.method, c.selection,
                       c.included, c.risk_category, c.risk_reason, c.context
                FROM review_candidates c
                JOIN texts t ON t.text_id = c.text_id
                WHERE c.run_id IN ({placeholders}){exact_clause}
                ORDER BY
                    CASE c.risk_category
                        WHEN 'source_collision' THEN 0
                        WHEN 'approved_mapping' THEN 1
                        WHEN 'review_exclusion' THEN 2
                        WHEN 'unmatched' THEN 3
                        WHEN 'lemma_fallback' THEN 4
                        WHEN 'possessive_normalization' THEN 5
                        WHEN 'multiword_phrase' THEN 6
                        ELSE 7
                    END,
                    t.title COLLATE NOCASE, c.lexicon_display_name,
                    c.token_position
                """,
                run_ids,
            ).fetchall()
        return tuple(
            ReviewCandidateRecord(
                **{
                    **dict(row),
                    "included": bool(row["included"]),
                }
            )
            for row in rows
        )
