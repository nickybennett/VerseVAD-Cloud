"""Framework-independent corpus import, analysis, and collection summaries."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Callable, Iterable, Sequence

from versevad.application import (
    AnalysisRequest,
    TextImportError,
    decode_uploaded_text,
    run_workspace_analysis,
)
from versevad.db import (
    CorpusBatchRecord,
    CorpusMetricRecord,
    CorpusModuleAggregateRecord,
    CorpusModuleMetricRecord,
    CorpusTextImport,
    ProjectRepository,
)
from versevad.lexical_semantic.aoa import AoAConfiguration
from versevad.lexical_semantic.concreteness import ConcretenessConfiguration
from versevad.lexical_semantic.frequency import FrequencyConfiguration
from versevad.lexical_semantic.readability import ReadabilityConfiguration
from versevad.lexical_semantic.sentiment import VaderSentimentConfiguration
from versevad.lexical_style import (
    LexicalStyleConfiguration,
    calculate_hdd,
    calculate_mattr,
    calculate_mtld,
)
from versevad.models import PhrasePolicy, StopwordMode
from versevad.phonology import PhonologicalConfiguration
from versevad.preprocessing import SpacyEnglishPreprocessor, TextPreprocessor
from versevad.prosody import MeterConfiguration, PronunciationConfiguration
from versevad.poetry_id import PoetryIDConfiguration
from versevad.inherited_form import InheritedFormConfiguration
from versevad.stopwords import DEFAULT_PROTECTED_WORDS


MAX_CORPUS_FILES = 5_000
MAX_CORPUS_BYTES = 250 * 1024 * 1024


class CorpusAnalysisCancelled(RuntimeError):
    """Raised only at a safe work boundary before another text starts."""


@dataclass(frozen=True)
class CorpusImportSummary:
    files: tuple[CorpusTextImport, ...]
    total_bytes: int


@dataclass(frozen=True)
class CorpusVadProfile:
    """Collection means and their distinct descriptive dispersion measures."""

    lexicon_id: str
    lexicon: str
    analysis_view: str
    dimension: str
    works_included: int
    works_omitted: int
    matched_observations: int
    lexical_tokens: int
    token_weighted_volume_mean: float
    pooled_lexical_rating_standard_deviation: float | None
    work_weighted_volume_mean: float
    poem_mean_standard_deviation: float
    poem_mean_median: float
    poem_mean_minimum: float
    poem_mean_maximum: float
    work_minus_token_difference: float
    volume_coverage: float | None


@dataclass(frozen=True)
class CorpusVadWorkComparison:
    """One work-level VAD mean paired with its within-work population SD."""

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
    analysis_view: str
    dimension: str
    weighting: str
    observations: int
    coverage: float | None
    mean: float
    population_standard_deviation: float | None


@dataclass(frozen=True)
class CorpusScenarioDelta:
    """Like-for-like difference between two immutable corpus batches."""

    text_id: str
    title: str
    lexicon_id: str
    lexicon: str
    analysis_view: str
    metric: str
    dimension: str
    weighting: str
    scale: str
    baseline_value: float
    reviewed_value: float
    difference: float


@dataclass(frozen=True)
class CorpusAnalysisConfiguration:
    """Optional modules and exact reusable configurations for one corpus batch."""

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

    @property
    def module_names(self) -> tuple[str, ...]:
        names = ["vader_sentiment", "readability"]
        if self.include_concreteness:
            names.append("concreteness")
        if self.include_frequency:
            names.append("lexical_frequency")
        if self.include_aoa:
            names.append("age_of_acquisition")
        if (
            self.include_pronunciation
            or self.include_meter
            or self.include_phonology
            or self.include_inherited_form
        ):
            names.append("pronunciation_prosody_foundation")
        if self.include_meter or self.include_inherited_form:
            names.append("candidate_meter_and_rhythmic_regularity")
        if self.include_phonology or self.include_inherited_form:
            names.append("rhyme_and_phonological_patterns")
        if self.include_lexical_style:
            names.append("lexical_style")
        if self.include_poetry_id:
            names.append("poetry_id")
        if self.include_inherited_form:
            names.append("inherited_form")
        return tuple(names)

    @property
    def manifest(self) -> dict[str, object]:
        rows = (
            (
                True,
                "vader_sentiment",
                VaderSentimentConfiguration(),
            ),
            (
                True,
                "readability",
                ReadabilityConfiguration(
                    pronunciation_overrides=(
                        self.pronunciation_configuration.overrides
                    ),
                ),
            ),
            (
                self.include_concreteness,
                "concreteness",
                self.concreteness_configuration,
            ),
            (
                self.include_frequency,
                "lexical_frequency",
                self.frequency_configuration,
            ),
            (
                self.include_aoa,
                "age_of_acquisition",
                self.aoa_configuration,
            ),
            (
                (
                    self.include_pronunciation
                    or self.include_meter
                    or self.include_phonology
                    or self.include_inherited_form
                ),
                "pronunciation_prosody_foundation",
                self.pronunciation_configuration,
            ),
            (
                self.include_meter or self.include_inherited_form,
                "candidate_meter_and_rhythmic_regularity",
                self.meter_configuration,
            ),
            (
                self.include_phonology or self.include_inherited_form,
                "rhyme_and_phonological_patterns",
                self.phonological_configuration,
            ),
            (
                self.include_lexical_style,
                "lexical_style",
                self.lexical_style_configuration,
            ),
            (
                self.include_poetry_id,
                "poetry_id",
                self.poetry_id_configuration,
            ),
            (
                self.include_inherited_form,
                "inherited_form",
                self.inherited_form_configuration,
            ),
        )
        return {
            name: asdict(configuration)
            for enabled, name, configuration in rows
            if enabled
        }


@dataclass(frozen=True)
class CorpusModuleProfile:
    """Compatible per-work module values summarized without hidden pooling."""

    module_name: str
    module_version: str
    configuration_id: str
    metric_id: str
    unit: str
    weighting: str
    works_included: int
    works_omitted: int
    equal_work_mean: float
    observation_weighted_mean: float | None
    total_observations: int
    note: str
    scope_id: str = ""


@dataclass(frozen=True)
class CorpusModuleCategoryProfile:
    """Per-work prevalence for selected categorical module evidence."""

    module_name: str
    module_version: str
    configuration_id: str
    metric_id: str
    category: str
    works_included: int
    works_with_category: int
    prevalence: float
    note: str
    scope_id: str = ""
    weighting: str = ""


def decode_corpus_files(
    files: Iterable[tuple[str, bytes]],
) -> CorpusImportSummary:
    """Validate a browser-selected folder and preserve every UTF-8 text separately."""

    supplied = tuple(files)
    if not supplied:
        raise TextImportError("Choose a folder containing at least one UTF-8 .txt file.")
    if len(supplied) > MAX_CORPUS_FILES:
        raise TextImportError(
            f"This folder contains more than {MAX_CORPUS_FILES:,} text files. "
            "Split it into smaller research projects before importing."
        )
    total_bytes = sum(len(content) for _, content in supplied)
    if total_bytes > MAX_CORPUS_BYTES:
        raise TextImportError(
            "This folder is larger than VerseVAD's 250 MB import safety limit. "
            "Split it into smaller research projects before importing."
        )
    imported: list[CorpusTextImport] = []
    seen_paths: set[str] = set()
    for raw_name, content in supplied:
        relative_path = raw_name.replace("\\", "/").lstrip("/")
        path = PurePosixPath(relative_path)
        if not relative_path or ".." in path.parts:
            raise TextImportError("A selected filename contained an unsafe relative path.")
        if path.suffix.casefold() != ".txt":
            raise TextImportError(
                f"{relative_path} is not a .txt file. Only UTF-8 plain text is imported."
            )
        key = relative_path.casefold()
        if key in seen_paths:
            raise TextImportError(f"The selected folder contains a duplicate path: {relative_path}")
        seen_paths.add(key)
        try:
            original_text = decode_uploaded_text(path.name, content)
        except TextImportError as error:
            raise TextImportError(f"{relative_path}: {error}") from error
        if not original_text.strip():
            raise TextImportError(f"{relative_path} is blank, so the folder was not imported.")
        imported.append(
            CorpusTextImport(
                title=path.stem,
                source_name=path.name,
                relative_path=relative_path,
                original_text=original_text,
            )
        )
    imported.sort(key=lambda item: item.relative_path.casefold())
    return CorpusImportSummary(tuple(imported), total_bytes)


def corpus_vad_profiles(
    metrics: Sequence[CorpusMetricRecord],
    *,
    total_works: int | None = None,
) -> tuple[CorpusVadProfile, ...]:
    """Compute collection VAD means and two non-interchangeable dispersions.

    Token-weighted collection means reconstruct a pooled matched-observation mean.
    Work-weighted means average the eligible poem-level token means. Missing poem
    scores stay missing and are reported as omitted, never changed to 0.5 or zero.

    The pooled lexical-rating population SD is reconstructed from every included
    work's mean, population SD, and observation count. It is withheld if any
    matching work-level SD is absent or inconsistent. The poem-mean population SD
    instead describes variation among the included work-level means.
    """

    selected = tuple(
        row
        for row in metrics
        if row.metric == "vad_mean"
        and row.weighting == "token"
        and row.scale == "normalized_0_1"
        and row.value is not None
        and row.observations > 0
    )
    if total_works is None:
        total_works = len({row.text_id for row in metrics})
    standard_deviations = {
        (
            row.run_id,
            row.text_id,
            row.text_version_id,
            row.lexicon_id,
            row.analysis_view,
            row.dimension,
            row.weighting,
            row.scale,
        ): row
        for row in metrics
        if row.metric == "vad_standard_deviation"
        and row.weighting == "token"
        and row.scale == "normalized_0_1"
        and row.value is not None
        and row.observations > 0
    }
    grouped: dict[tuple[str, str, str, str], list[CorpusMetricRecord]] = {}
    for row in selected:
        grouped.setdefault(
            (row.lexicon_id, row.lexicon, row.analysis_view, row.dimension),
            [],
        ).append(row)
    profiles = []
    for (lexicon_id, lexicon, analysis_view, dimension), rows in grouped.items():
        observations = sum(row.observations for row in rows)
        work_values = tuple(float(row.value) for row in rows)
        work_mean = statistics.fmean(work_values)
        token_mean = (
            sum(float(row.value) * row.observations for row in rows) / observations
        )
        pooled_variance_total = 0.0
        pooled_standard_deviation_available = True
        for row in rows:
            standard_deviation = standard_deviations.get(
                (
                    row.run_id,
                    row.text_id,
                    row.text_version_id,
                    row.lexicon_id,
                    row.analysis_view,
                    row.dimension,
                    row.weighting,
                    row.scale,
                )
            )
            if (
                standard_deviation is None
                or standard_deviation.observations != row.observations
                or float(standard_deviation.value) < 0
            ):
                pooled_standard_deviation_available = False
                break
            pooled_variance_total += row.observations * (
                float(standard_deviation.value) ** 2
                + (float(row.value) - token_mean) ** 2
            )
        pooled_standard_deviation = (
            math.sqrt(max(pooled_variance_total / observations, 0.0))
            if pooled_standard_deviation_available
            else None
        )
        lexical_tokens = sum(row.lexical_tokens for row in rows)
        matched_tokens = sum(row.matched_tokens for row in rows)
        coverage = matched_tokens / lexical_tokens if lexical_tokens else None
        profiles.append(
            CorpusVadProfile(
                lexicon_id=lexicon_id,
                lexicon=lexicon,
                analysis_view=analysis_view,
                dimension=dimension,
                works_included=len(rows),
                works_omitted=max(total_works - len(rows), 0),
                matched_observations=observations,
                lexical_tokens=lexical_tokens,
                token_weighted_volume_mean=token_mean,
                pooled_lexical_rating_standard_deviation=(
                    pooled_standard_deviation
                ),
                work_weighted_volume_mean=work_mean,
                poem_mean_standard_deviation=statistics.pstdev(work_values),
                poem_mean_median=statistics.median(work_values),
                poem_mean_minimum=min(work_values),
                poem_mean_maximum=max(work_values),
                work_minus_token_difference=work_mean - token_mean,
                volume_coverage=coverage,
            )
        )
    return tuple(
        sorted(
            profiles,
            key=lambda row: (
                row.lexicon.casefold(),
                row.analysis_view,
                row.dimension,
            ),
        )
    )


def corpus_vad_work_comparisons(
    metrics: Sequence[CorpusMetricRecord],
) -> tuple[CorpusVadWorkComparison, ...]:
    """Pair each normalized work-level VAD mean with its matching population SD."""

    standard_deviations = {
        (
            row.run_id,
            row.text_id,
            row.text_version_id,
            row.lexicon_id,
            row.analysis_view,
            row.dimension,
            row.weighting,
            row.scale,
        ): row
        for row in metrics
        if row.metric == "vad_standard_deviation"
        and row.scale == "normalized_0_1"
        and row.value is not None
        and row.observations > 0
    }
    comparisons = []
    for row in metrics:
        if (
            row.metric != "vad_mean"
            or row.scale != "normalized_0_1"
            or row.value is None
            or row.observations <= 0
        ):
            continue
        standard_deviation = standard_deviations.get(
            (
                row.run_id,
                row.text_id,
                row.text_version_id,
                row.lexicon_id,
                row.analysis_view,
                row.dimension,
                row.weighting,
                row.scale,
            )
        )
        deviation_value = None
        if (
            standard_deviation is not None
            and standard_deviation.observations == row.observations
            and float(standard_deviation.value) >= 0
        ):
            deviation_value = float(standard_deviation.value)
        comparisons.append(
            CorpusVadWorkComparison(
                run_id=row.run_id,
                text_id=row.text_id,
                text_version_id=row.text_version_id,
                title=row.title,
                author=row.author,
                collection=row.collection,
                date_label=row.date_label,
                genre=row.genre,
                lexicon_id=row.lexicon_id,
                lexicon=row.lexicon,
                analysis_view=row.analysis_view,
                dimension=row.dimension,
                weighting=row.weighting,
                observations=row.observations,
                coverage=row.coverage,
                mean=float(row.value),
                population_standard_deviation=deviation_value,
            )
        )
    return tuple(
        sorted(
            comparisons,
            key=lambda item: (
                item.lexicon.casefold(),
                item.weighting,
                item.analysis_view,
                item.title.casefold(),
                item.text_id,
                item.dimension,
            ),
        )
    )


def corpus_module_profiles(
    metrics: Sequence[CorpusModuleMetricRecord],
    *,
    total_works: int | None = None,
) -> tuple[CorpusModuleProfile, ...]:
    """Summarize compatible numeric document metrics across works.

    Equal-work means are supplied for every numeric document metric. An
    observation-weighted mean is supplied only when the integration layer
    recorded an exact, defensible observation count for that metric. This
    deliberately excludes MATTR, HD-D, MTLD, medians, dispersion, schemes, and
    other quantities that cannot be pooled by weighting work-level values.
    """

    selected = tuple(
        row
        for row in metrics
        if row.scope == "document"
        and not isinstance(row.value, bool)
        and isinstance(row.value, (int, float))
    )
    if total_works is None:
        total_works = len({row.text_id for row in metrics})
    grouped: dict[
        tuple[str, str, str, str, str, str, str],
        list[CorpusModuleMetricRecord],
    ] = {}
    for row in selected:
        grouped.setdefault(
            (
                row.module_name,
                row.module_version,
                row.configuration_id,
                row.metric_id,
                row.unit,
                row.weighting,
                row.scope_id,
            ),
            [],
        ).append(row)

    profiles = []
    for (
        module_name,
        module_version,
        configuration_id,
        metric_id,
        unit,
        weighting,
        scope_id,
    ), rows in grouped.items():
        values = tuple(float(row.value) for row in rows)
        weighted = None
        observations = 0
        if all(
            row.observation_count is not None
            and row.observation_count > 0
            for row in rows
        ):
            observations = sum(int(row.observation_count) for row in rows)
            weighted = (
                sum(
                    float(row.value) * int(row.observation_count)
                    for row in rows
                )
                / observations
            )
        if metric_id in {
            "lexical_style.surface_type_token_ratio",
            "lexical_style.mattr",
            "lexical_style.hdd",
            "lexical_style.mtld",
        }:
            note = (
                "Work values receive equal descriptive weight here and are not "
                "averaged as though tokens were pooled. The separately labeled "
                "ordered pooled-token result is calculated from token evidence."
            )
        elif weighted is not None:
            note = (
                "Both equal-work and observation-weighted descriptive means are "
                "available; compare their stated denominators."
            )
        else:
            note = (
                "Only an equal-work descriptive mean is supplied because a "
                "defensible pooled-observation denominator is unavailable."
            )
        profiles.append(
            CorpusModuleProfile(
                module_name=module_name,
                module_version=module_version,
                configuration_id=configuration_id,
                metric_id=metric_id,
                unit=unit,
                weighting=weighting,
                works_included=len(rows),
                works_omitted=max(total_works - len(rows), 0),
                equal_work_mean=statistics.fmean(values),
                observation_weighted_mean=weighted,
                total_observations=observations,
                note=note,
                scope_id=scope_id,
            )
        )
    return tuple(
        sorted(
            profiles,
            key=lambda row: (
                row.module_name,
                row.metric_id,
                row.scope_id,
                row.weighting,
                row.configuration_id,
            ),
        )
    )


def corpus_module_category_profiles(
    metrics: Sequence[CorpusModuleMetricRecord],
) -> tuple[CorpusModuleCategoryProfile, ...]:
    """Count work-level meter/rhyme categories without inventing consensus."""

    supported = {
        "meter.closest_candidate",
        "meter.closest_candidate_kind",
        "meter.candidate_confidence",
        "meter.performance.rhythmic_organization",
        "meter.performance.primary_candidate",
        "meter.performance.confidence",
        "phonology.rhyme_scheme",
        "poetry_id.categorical_archetype_id",
        "poetry_id.confidence_label",
        "inherited_form.best_candidate_id",
        "inherited_form.best_candidate_name",
        "inherited_form.confidence_label",
        "inherited_form.classification",
        "inherited_form.nearest_alternative_id",
        "inherited_form.nearest_alternative_name",
    }
    grouped: dict[
        tuple[str, str, str, str, str, str],
        list[CorpusModuleMetricRecord],
    ] = {}
    for row in metrics:
        if (
            row.scope == "document"
            and row.metric_id in supported
            and isinstance(row.value, str)
            and row.value.strip()
        ):
            grouped.setdefault(
                (
                    row.module_name,
                    row.module_version,
                    row.configuration_id,
                    row.metric_id,
                    row.scope_id,
                    row.weighting,
                ),
                [],
            ).append(row)
    profiles = []
    for key, rows in grouped.items():
        by_work = {row.text_id: str(row.value) for row in rows}
        total = len(by_work)
        counts: dict[str, int] = {}
        for category in by_work.values():
            counts[category] = counts.get(category, 0) + 1
        for category, count in counts.items():
            profiles.append(
                CorpusModuleCategoryProfile(
                    module_name=key[0],
                    module_version=key[1],
                    configuration_id=key[2],
                    metric_id=key[3],
                    category=category,
                    works_included=total,
                    works_with_category=count,
                    prevalence=count / total,
                    note=(
                        "Descriptive work prevalence among works with this "
                        "metric and compatible source/view/weighting; this "
                        "does not declare one corpus-wide meter, rhyme scheme, "
                        "or PoetryID profile."
                    ),
                    scope_id=key[4],
                    weighting=key[5],
                )
            )
    return tuple(
        sorted(
            profiles,
            key=lambda row: (
                row.module_name,
                row.metric_id,
                -row.works_with_category,
                row.category,
            ),
        )
    )


def corpus_scenario_deltas(
    baseline: Sequence[CorpusMetricRecord],
    reviewed: Sequence[CorpusMetricRecord],
) -> tuple[CorpusScenarioDelta, ...]:
    """Compare only directly compatible metrics; missing values stay unpaired."""

    def key(row: CorpusMetricRecord) -> tuple[str, ...]:
        return (
            row.text_id,
            row.lexicon_id,
            row.analysis_view,
            row.metric,
            row.dimension,
            row.category,
            row.weighting,
            row.scale,
        )

    baseline_by_key = {
        key(row): row for row in baseline if row.value is not None
    }
    reviewed_by_key = {
        key(row): row for row in reviewed if row.value is not None
    }
    rows = []
    for shared in sorted(set(baseline_by_key) & set(reviewed_by_key)):
        first = baseline_by_key[shared]
        second = reviewed_by_key[shared]
        rows.append(
            CorpusScenarioDelta(
                text_id=first.text_id,
                title=first.title,
                lexicon_id=first.lexicon_id,
                lexicon=first.lexicon,
                analysis_view=first.analysis_view,
                metric=first.metric,
                dimension=first.dimension,
                weighting=first.weighting,
                scale=first.scale,
                baseline_value=float(first.value),
                reviewed_value=float(second.value),
                difference=float(second.value) - float(first.value),
            )
        )
    return tuple(rows)


def _aggregate_id(
    batch_id: str,
    module_name: str,
    metric_id: str,
    aggregation_method: str,
) -> str:
    payload = "|".join(
        (batch_id, module_name, metric_id, aggregation_method)
    )
    return "corpus-module-aggregate-v1:" + hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()[:20]


def _pooled_lexical_style_aggregates(
    repository: ProjectRepository,
    *,
    project_id: str,
    batch_id: str,
    configuration: LexicalStyleConfiguration,
    total_works: int,
) -> tuple[CorpusModuleAggregateRecord, ...]:
    results = tuple(
        row
        for row in repository.list_module_results_for_batch(
            project_id,
            batch_id,
        )
        if row.module_name == "lexical_style"
    )
    if not results:
        return ()
    configuration_ids = {row.configuration_id for row in results}
    if len(configuration_ids) != 1:
        raise ValueError(
            "Pooled lexical-style analysis requires one shared configuration "
            "across every included work."
        )

    forms = []
    lengths = []
    for result in results:
        artifacts = {
            row.filename: row
            for row in repository.list_module_artifacts(
                result.run_id,
                result.module_name,
            )
        }
        audit = artifacts.get("lexical_style_token_audit.csv")
        if audit is None:
            raise RuntimeError(
                "A completed lexical-style result is missing its token audit."
            )
        rows = csv.DictReader(
            io.StringIO(audit.content.decode("utf-8-sig"))
        )
        for row in rows:
            if row["included"].casefold() != "true":
                continue
            normalized = row["normalized_surface_type"].strip()
            if normalized:
                forms.append(normalized)
            character_count = row["alphabetic_character_count"].strip()
            if character_count:
                lengths.append(int(character_count))

    observations = tuple(forms)
    method = "ordered_pooled_token_sequence"
    configuration_id = next(iter(configuration_ids))
    values = (
        (
            "lexical_style.pooled.lexical_token_count",
            len(observations),
            "shared-preprocessing lexical tokens",
        ),
        (
            "lexical_style.pooled.normalized_surface_type_count",
            len(set(observations)),
            "normalized observed surface types",
        ),
        (
            "lexical_style.pooled.surface_type_token_ratio",
            len(set(observations)) / len(observations)
            if observations
            else None,
            "proportion",
        ),
        (
            "lexical_style.pooled.mattr",
            calculate_mattr(
                observations,
                window_size=configuration.mattr_window_size,
            ),
            "mean overlapping-window type-token ratio",
        ),
        (
            "lexical_style.pooled.hdd",
            calculate_hdd(
                observations,
                sample_size=configuration.hdd_sample_size,
            ),
            "expected distinct-type proportion",
        ),
        (
            "lexical_style.pooled.mtld",
            calculate_mtld(
                observations,
                threshold=configuration.mtld_threshold,
            ),
            "mean lexical-token factor length",
        ),
        (
            "lexical_style.pooled.mean_word_length",
            statistics.fmean(lengths) if lengths else None,
            "Unicode alphabetic characters per lexical token",
        ),
    )
    note = (
        "Calculated from normalized observed surface-form tokens concatenated "
        "in the selected batch's stable work order. Work boundaries are retained "
        "in the per-work results but do not reset the pooled token sequence. "
        "This exploratory pooled result is not an average of work-level diversity "
        "statistics."
    )
    return tuple(
        CorpusModuleAggregateRecord(
            aggregate_id=_aggregate_id(
                batch_id,
                "lexical_style",
                metric_id,
                method,
            ),
            batch_id=batch_id,
            project_id=project_id,
            module_name="lexical_style",
            configuration_id=configuration_id,
            metric_id=metric_id,
            aggregation_method=method,
            value=value,
            unit=unit,
            works_included=len(results),
            works_omitted=max(total_works - len(results), 0),
            observation_count=len(observations),
            note=note,
        )
        for metric_id, value, unit in values
    )


def analyze_corpus(
    repository: ProjectRepository,
    project_id: str,
    *,
    lexicon_ids: Sequence[str],
    text_ids: Sequence[str] | None = None,
    phrase_policy: PhrasePolicy = PhrasePolicy.PHRASE_PREFERRED,
    minimum_match_requirement: int = 3,
    stopword_mode: StopwordMode = StopwordMode.STANDARD,
    protected_stopwords: Sequence[str] = DEFAULT_PROTECTED_WORDS,
    custom_stopword_additions: Sequence[str] = (),
    custom_stopword_removals: Sequence[str] = (),
    scenario_version_id: str = "",
    module_configuration: CorpusAnalysisConfiguration | None = None,
    preprocessor: TextPreprocessor | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> CorpusBatchRecord:
    """Analyze each work independently and publish comparisons only as a full batch."""

    module_configuration = module_configuration or CorpusAnalysisConfiguration()
    project = repository.get_project(project_id)
    available = repository.list_texts(project_id)
    selected_ids = tuple(text_ids) if text_ids is not None else tuple(
        text.text_id for text in available
    )
    selected_set = set(selected_ids)
    selected = tuple(text for text in available if text.text_id in selected_set)
    if len(selected) != len(selected_set):
        raise ValueError("One or more selected texts do not belong to this project.")
    scenario = (
        repository.get_review_scenario_version(scenario_version_id)
        if scenario_version_id
        else None
    )
    if scenario is not None and scenario.project_id != project_id:
        raise ValueError("The selected review scenario does not belong to this project.")
    batch = repository.begin_corpus_batch(
        project_id,
        text_ids=(text.text_id for text in selected),
        lexicon_ids=lexicon_ids,
        module_names=module_configuration.module_names,
        module_configuration=module_configuration.manifest,
        phrase_policy=phrase_policy.value,
        minimum_match_requirement=minimum_match_requirement,
        stopword_mode=stopword_mode.value,
        protected_stopwords=protected_stopwords,
        custom_stopword_additions=custom_stopword_additions,
        custom_stopword_removals=custom_stopword_removals,
        scenario_version_id=scenario_version_id,
    )
    processor = preprocessor or SpacyEnglishPreprocessor()
    total = len(selected)
    try:
        for position, text in enumerate(selected, start=1):
            if cancel_check is not None and cancel_check():
                raise CorpusAnalysisCancelled(
                    "Corpus analysis was cancelled safely before starting "
                    f"work {position} of {total}. The incomplete batch was not "
                    "published to corpus comparisons."
                )
            if progress is not None:
                progress(position - 1, total, text.title)
            review_rules = (
                repository.review_rules_for_text(
                    scenario_version_id,
                    text_id=text.text_id,
                    text_version_id=text.text_version_id,
                )
                if scenario_version_id
                else ()
            )
            workspace = run_workspace_analysis(
                AnalysisRequest(
                    project_name=project.title,
                    title=text.title,
                    original_text=text.original_text,
                    lexicon_ids=tuple(lexicon_ids),
                    phrase_policy=phrase_policy,
                    minimum_match_requirement=minimum_match_requirement,
                    text_id=text.text_id,
                    text_version_id=text.text_version_id,
                    stopword_mode=stopword_mode,
                    protected_stopwords=tuple(protected_stopwords),
                    custom_stopword_additions=tuple(custom_stopword_additions),
                    custom_stopword_removals=tuple(custom_stopword_removals),
                    scenario_id=(
                        scenario.scenario_id
                        if scenario is not None
                        else "phase2-multi-lexicon-v1"
                    ),
                    scenario_version_id=scenario_version_id,
                    review_rules=review_rules,
                    include_concreteness=(
                        module_configuration.include_concreteness
                    ),
                    concreteness_configuration=(
                        module_configuration.concreteness_configuration
                    ),
                    include_frequency=module_configuration.include_frequency,
                    frequency_configuration=(
                        module_configuration.frequency_configuration
                    ),
                    include_aoa=module_configuration.include_aoa,
                    aoa_configuration=module_configuration.aoa_configuration,
                    include_pronunciation=(
                        module_configuration.include_pronunciation
                    ),
                    pronunciation_configuration=(
                        module_configuration.pronunciation_configuration
                    ),
                    include_meter=module_configuration.include_meter,
                    meter_configuration=(
                        module_configuration.meter_configuration
                    ),
                    include_phonology=module_configuration.include_phonology,
                    phonological_configuration=(
                        module_configuration.phonological_configuration
                    ),
                    include_lexical_style=(
                        module_configuration.include_lexical_style
                    ),
                    lexical_style_configuration=(
                        module_configuration.lexical_style_configuration
                    ),
                    include_poetry_id=(
                        module_configuration.include_poetry_id
                    ),
                    poetry_id_configuration=(
                        module_configuration.poetry_id_configuration
                    ),
                    include_inherited_form=(
                        module_configuration.include_inherited_form
                    ),
                    inherited_form_configuration=(
                        module_configuration.inherited_form_configuration
                    ),
                    analysis_cache_enabled=(
                        module_configuration.analysis_cache_enabled
                    ),
                    performance_diagnostics=(
                        module_configuration.performance_diagnostics
                    ),
                ),
                preprocessor=processor,
            )
            repository.save_analysis(
                project_id,
                text.text_id,
                workspace,
                batch_id=batch.batch_id,
            )
            if progress is not None:
                cache_note = ""
                if workspace.performance is not None:
                    hits = sum(
                        operation.cache_status == "hit"
                        for operation in workspace.performance.operations
                    )
                    cache_note = (
                        f" ({hits}/{len(workspace.performance.operations)} "
                        "operations reused)"
                    )
                progress(position, total, text.title + cache_note)
        if module_configuration.include_lexical_style:
            repository.save_module_aggregates(
                batch.batch_id,
                _pooled_lexical_style_aggregates(
                    repository,
                    project_id=project_id,
                    batch_id=batch.batch_id,
                    configuration=(
                        module_configuration.lexical_style_configuration
                    ),
                    total_works=total,
                ),
            )
    except Exception as error:
        repository.finish_corpus_batch(batch.batch_id, error_message=str(error))
        raise
    return repository.finish_corpus_batch(batch.batch_id)
