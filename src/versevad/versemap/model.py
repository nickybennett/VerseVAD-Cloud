"""Versioned VerseMap reference model, projection, and comparisons."""

from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from versevad.core.modules import ModuleInput, ModuleMetric, ModuleResult, ResultLayer
from versevad.versemap.profile import (
    FEATURE_BY_ID,
    FEATURE_DEFINITIONS,
    PROFILE_BUILD_ID,
    PROFILE_ID,
    VerseMapProfile,
    build_module_result,
)


PROFILE_FILENAME = "_versemap_profiles.csv"
POET_PROFILE_FILENAME = "_versemap_poet_profiles.csv"
MODEL_FILENAME = "_versemap_model.csv"
PROFILE_SCHEMA_VERSION = "1.0"
MINIMUM_SHARED_WEIGHT = 0.60
DEFAULT_NEIGHBOR_COUNT = 10


@dataclass(frozen=True)
class VerseMapConfiguration:
    neighbor_count: int = DEFAULT_NEIGHBOR_COUNT
    minimum_shared_weight: float = MINIMUM_SHARED_WEIGHT
    profile_id: str = PROFILE_ID

    def __post_init__(self) -> None:
        if not 1 <= self.neighbor_count <= 100:
            raise ValueError("VerseMap neighbor count must be between 1 and 100.")
        if not 0 < self.minimum_shared_weight <= 1:
            raise ValueError(
                "VerseMap shared-evidence threshold must be above 0 and at most 1."
            )
        if self.profile_id != PROFILE_ID:
            raise ValueError(f"This release supports only {PROFILE_ID}.")

    @property
    def configuration_id(self) -> str:
        return (
            f"{self.profile_id}:neighbors={self.neighbor_count}:"
            f"shared={self.minimum_shared_weight:.3f}"
        )


@dataclass(frozen=True)
class ModelFeature:
    feature_id: str
    mean: float
    population_sd: float
    raw_mean: float
    raw_population_sd: float
    weight: float
    loading_1: float
    loading_2: float
    available_reference_count: int


@dataclass(frozen=True)
class ReferencePoint:
    point_id: str
    point_kind: str
    poet_id: str
    poet_name: str
    title: str
    relative_path: str
    source_sha256: str
    coordinate_1: float
    coordinate_2: float
    values: tuple[tuple[str, float | None], ...]
    poem_count: int = 1

    @property
    def value_map(self) -> dict[str, float | None]:
        return dict(self.values)


@dataclass(frozen=True)
class VerseMapReferenceIndex:
    source_root: Path
    profile_id: str
    profile_build_id: str
    reference_release_id: str
    reference_release_sha256: str
    model_id: str
    explained_variance_1: float
    explained_variance_2: float
    features: tuple[ModelFeature, ...]
    poems: tuple[ReferencePoint, ...]
    poets: tuple[ReferencePoint, ...]


@dataclass(frozen=True)
class VerseMapNeighbor:
    rank: int
    point_id: str
    point_kind: str
    poet_name: str
    title: str
    distance: float
    shared_weight: float
    coordinate_1: float
    coordinate_2: float


@dataclass(frozen=True)
class VerseMapFeatureComparison:
    feature_id: str
    label: str
    group_id: str
    unit: str
    query_value: float | None
    reference_mean: float
    reference_population_sd: float
    z_score: float | None
    percentile: float | None
    weight: float
    coverage_rate: float | None
    eligible_count: int
    matched_count: int


@dataclass(frozen=True)
class VerseMapAnalysisResult:
    module_result: ModuleResult
    configuration: VerseMapConfiguration
    profile: VerseMapProfile
    profile_build_id: str
    reference_release_id: str
    reference_release_sha256: str
    model_id: str
    coordinate_1: float | None
    coordinate_2: float | None
    explained_variance_1: float
    explained_variance_2: float
    evidence_weight_coverage: float
    nearest_poems: tuple[VerseMapNeighbor, ...]
    nearest_poets: tuple[VerseMapNeighbor, ...]
    feature_comparisons: tuple[VerseMapFeatureComparison, ...]
    map_points: tuple[ReferencePoint, ...]


def _transform(value: float, feature_id: str) -> float:
    if FEATURE_BY_ID[feature_id].transform == "log1p":
        return math.log1p(max(value, 0.0))
    return value


def feature_weights() -> dict[str, float]:
    groups: dict[str, list[str]] = {}
    for feature in FEATURE_DEFINITIONS:
        groups.setdefault(feature.group_id, []).append(feature.feature_id)
    group_weight = 1.0 / len(groups)
    return {
        feature_id: group_weight / len(feature_ids)
        for feature_ids in groups.values()
        for feature_id in feature_ids
    }


def _csv_bytes(
    fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def build_reference_model_bytes(
    rows: Sequence[Mapping[str, object]],
    *,
    reference_release_id: str,
    reference_release_sha256: str,
) -> tuple[bytes, bytes, bytes, str]:
    """Fit weighted PCA and poet centroids from raw per-poem profile rows."""

    if len(rows) < 2:
        raise ValueError("VerseMap requires at least two reference poems.")
    feature_ids = [item.feature_id for item in FEATURE_DEFINITIONS]
    weights = feature_weights()
    raw = np.array(
        [
            [
                (
                    float(row[feature_id])
                    if row.get(feature_id) not in (None, "")
                    else np.nan
                )
                for feature_id in feature_ids
            ]
            for row in rows
        ],
        dtype=float,
    )
    transformed = raw.copy()
    for index, feature_id in enumerate(feature_ids):
        if FEATURE_BY_ID[feature_id].transform == "log1p":
            transformed[:, index] = np.log1p(np.maximum(transformed[:, index], 0))
    means = np.nanmean(transformed, axis=0)
    standard_deviations = np.nanstd(transformed, axis=0)
    standard_deviations = np.where(
        standard_deviations > 1e-12, standard_deviations, 1.0
    )
    z = (transformed - means) / standard_deviations
    z_imputed = np.where(np.isnan(z), 0.0, z)
    weight_array = np.sqrt(np.array([weights[item] for item in feature_ids]))
    weighted = z_imputed * weight_array
    _, singular, vt = np.linalg.svd(weighted, full_matrices=False)
    loadings = vt[:2].T
    for component in range(loadings.shape[1]):
        anchor = int(np.argmax(np.abs(loadings[:, component])))
        if loadings[anchor, component] < 0:
            loadings[:, component] *= -1
    coordinates = weighted @ loadings
    variance = singular**2
    variance_ratio = variance / variance.sum() if variance.sum() else variance
    explained_1 = float(variance_ratio[0]) if len(variance_ratio) else 0.0
    explained_2 = float(variance_ratio[1]) if len(variance_ratio) > 1 else 0.0

    profile_fields = [
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
        "content_token_count",
        "coordinate_1",
        "coordinate_2",
        *feature_ids,
        *[f"{feature_id}__eligible" for feature_id in feature_ids],
        *[f"{feature_id}__matched" for feature_id in feature_ids],
    ]
    profile_rows = []
    for row, coordinate in zip(rows, coordinates, strict=True):
        output = {field: row.get(field, "") for field in profile_fields}
        output.update(
            {
                "schema_version": PROFILE_SCHEMA_VERSION,
                "profile_id": PROFILE_ID,
                "profile_build_id": PROFILE_BUILD_ID,
                "reference_release_id": reference_release_id,
                "coordinate_1": f"{coordinate[0]:.12g}",
                "coordinate_2": f"{coordinate[1]:.12g}",
            }
        )
        profile_rows.append(output)
    profile_bytes = _csv_bytes(profile_fields, profile_rows)

    poet_rows: list[dict[str, object]] = []
    poet_names = sorted(
        {(str(row["poet_id"]), str(row["poet_name"])) for row in rows}
    )
    for poet_id, poet_name in poet_names:
        indices = [
            index for index, row in enumerate(rows) if row["poet_id"] == poet_id
        ]
        centroid_z = np.nanmean(z[indices, :], axis=0)
        centroid_z = np.where(np.isnan(centroid_z), 0.0, centroid_z)
        centroid_coordinate = (centroid_z * weight_array) @ loadings
        output: dict[str, object] = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "profile_id": PROFILE_ID,
            "profile_build_id": PROFILE_BUILD_ID,
            "reference_release_id": reference_release_id,
            "poet_id": poet_id,
            "poet_name": poet_name,
            "poem_count": len(indices),
            "coordinate_1": f"{centroid_coordinate[0]:.12g}",
            "coordinate_2": f"{centroid_coordinate[1]:.12g}",
        }
        for feature_index, feature_id in enumerate(feature_ids):
            available = raw[indices, feature_index]
            output[feature_id] = (
                f"{float(np.nanmean(available)):.12g}"
                if not np.all(np.isnan(available))
                else ""
            )
        poet_rows.append(output)
    poet_fields = [
        "schema_version",
        "profile_id",
        "profile_build_id",
        "reference_release_id",
        "poet_id",
        "poet_name",
        "poem_count",
        "coordinate_1",
        "coordinate_2",
        *feature_ids,
    ]
    poet_bytes = _csv_bytes(poet_fields, poet_rows)

    model_seed = hashlib.sha256(profile_bytes + poet_bytes).hexdigest()
    model_id = f"versemap-model-{model_seed[:16]}"
    model_fields = (
        "schema_version",
        "profile_id",
        "profile_build_id",
        "reference_release_id",
        "reference_release_sha256",
        "model_id",
        "feature_id",
        "group_id",
        "label",
        "unit",
        "transform",
        "reference_mean_transformed",
        "reference_population_sd_transformed",
        "reference_mean_raw",
        "reference_population_sd_raw",
        "weight",
        "loading_1",
        "loading_2",
        "available_reference_count",
        "explained_variance_1",
        "explained_variance_2",
    )
    model_rows = []
    for index, definition in enumerate(FEATURE_DEFINITIONS):
        model_rows.append(
            {
                "schema_version": PROFILE_SCHEMA_VERSION,
                "profile_id": PROFILE_ID,
                "profile_build_id": PROFILE_BUILD_ID,
                "reference_release_id": reference_release_id,
                "reference_release_sha256": reference_release_sha256,
                "model_id": model_id,
                "feature_id": definition.feature_id,
                "group_id": definition.group_id,
                "label": definition.label,
                "unit": definition.unit,
                "transform": definition.transform,
                "reference_mean_transformed": f"{means[index]:.12g}",
                "reference_population_sd_transformed": (
                    f"{standard_deviations[index]:.12g}"
                ),
                "reference_mean_raw": (
                    f"{float(np.nanmean(raw[:, index])):.12g}"
                    if not np.all(np.isnan(raw[:, index]))
                    else "0"
                ),
                "reference_population_sd_raw": (
                    f"{float(np.nanstd(raw[:, index])):.12g}"
                    if not np.all(np.isnan(raw[:, index]))
                    else "0"
                ),
                "weight": f"{weights[definition.feature_id]:.12g}",
                "loading_1": f"{loadings[index, 0]:.12g}",
                "loading_2": f"{loadings[index, 1]:.12g}",
                "available_reference_count": int(
                    np.count_nonzero(~np.isnan(raw[:, index]))
                ),
                "explained_variance_1": f"{explained_1:.12g}",
                "explained_variance_2": f"{explained_2:.12g}",
            }
        )
    model_bytes = _csv_bytes(model_fields, model_rows)
    return profile_bytes, poet_bytes, model_bytes, model_id


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def load_reference_index(source_root: Path | str) -> VerseMapReferenceIndex:
    root = Path(source_root).resolve()
    model_rows = _read_csv(root / MODEL_FILENAME)
    profile_rows = _read_csv(root / PROFILE_FILENAME)
    poet_rows = _read_csv(root / POET_PROFILE_FILENAME)
    if not model_rows:
        raise ValueError("VerseMap's reference model is empty. Run the reference updater.")
    header = model_rows[0]
    if header["profile_id"] != PROFILE_ID:
        raise ValueError(
            "The VerseMap reference model uses an unsupported profile version."
        )
    if header.get("profile_build_id") != PROFILE_BUILD_ID:
        raise ValueError(
            "The VerseMap reference model uses an unsupported analytical build. "
            "Run the reference updater."
        )
    features = tuple(
        ModelFeature(
            feature_id=row["feature_id"],
            mean=float(row["reference_mean_transformed"]),
            population_sd=float(row["reference_population_sd_transformed"]),
            raw_mean=float(row["reference_mean_raw"]),
            raw_population_sd=float(row["reference_population_sd_raw"]),
            weight=float(row["weight"]),
            loading_1=float(row["loading_1"]),
            loading_2=float(row["loading_2"]),
            available_reference_count=int(row["available_reference_count"]),
        )
        for row in model_rows
    )

    def point(row: Mapping[str, str], kind: str) -> ReferencePoint:
        return ReferencePoint(
            point_id=(
                row["poem_id"] if kind == "reference_poem" else row["poet_id"]
            ),
            point_kind=kind,
            poet_id=row["poet_id"],
            poet_name=row["poet_name"],
            title=row.get("title", "") or row["poet_name"],
            relative_path=row.get("relative_path", ""),
            source_sha256=row.get("source_sha256", ""),
            coordinate_1=float(row["coordinate_1"]),
            coordinate_2=float(row["coordinate_2"]),
            values=tuple(
                (
                    definition.feature_id,
                    (
                        float(row[definition.feature_id])
                        if row.get(definition.feature_id, "") != ""
                        else None
                    ),
                )
                for definition in FEATURE_DEFINITIONS
            ),
            poem_count=int(row.get("poem_count", "1")),
        )

    return VerseMapReferenceIndex(
        source_root=root,
        profile_id=header["profile_id"],
        profile_build_id=header["profile_build_id"],
        reference_release_id=header["reference_release_id"],
        reference_release_sha256=header["reference_release_sha256"],
        model_id=header["model_id"],
        explained_variance_1=float(header["explained_variance_1"]),
        explained_variance_2=float(header["explained_variance_2"]),
        features=features,
        poems=tuple(point(row, "reference_poem") for row in profile_rows),
        poets=tuple(point(row, "reference_poet") for row in poet_rows),
    )


def _z_value(value: float | None, feature: ModelFeature) -> float | None:
    if value is None:
        return None
    return (
        _transform(value, feature.feature_id) - feature.mean
    ) / feature.population_sd


def _project(
    profile: VerseMapProfile, index: VerseMapReferenceIndex
) -> tuple[float, float, float]:
    values = profile.values
    x = y = available_weight = 0.0
    for feature in index.features:
        z = _z_value(values.get(feature.feature_id), feature)
        if z is None:
            continue
        scaled = z * math.sqrt(feature.weight)
        x += scaled * feature.loading_1
        y += scaled * feature.loading_2
        available_weight += feature.weight
    return x, y, available_weight


def _distance(
    query: Mapping[str, float | None],
    point: ReferencePoint,
    index: VerseMapReferenceIndex,
) -> tuple[float | None, float]:
    total = shared = 0.0
    reference = point.value_map
    for feature in index.features:
        left = _z_value(query.get(feature.feature_id), feature)
        right = _z_value(reference.get(feature.feature_id), feature)
        if left is None or right is None:
            continue
        total += feature.weight * (left - right) ** 2
        shared += feature.weight
    if shared <= 0:
        return None, 0.0
    return math.sqrt(total / shared), shared


def analyze_profile(
    module_input: ModuleInput,
    profile: VerseMapProfile,
    index: VerseMapReferenceIndex,
    configuration: VerseMapConfiguration | None = None,
) -> VerseMapAnalysisResult:
    configuration = configuration or VerseMapConfiguration()
    x, y, available_weight = _project(profile, index)

    def neighbors(
        points: Sequence[ReferencePoint],
    ) -> tuple[VerseMapNeighbor, ...]:
        rows = []
        for point in points:
            distance, shared = _distance(profile.values, point, index)
            if (
                distance is None
                or shared < configuration.minimum_shared_weight
            ):
                continue
            rows.append((distance, point, shared))
        rows.sort(key=lambda item: (item[0], item[1].poet_name, item[1].title))
        return tuple(
            VerseMapNeighbor(
                rank=rank,
                point_id=point.point_id,
                point_kind=point.point_kind,
                poet_name=point.poet_name,
                title=point.title,
                distance=distance,
                shared_weight=shared,
                coordinate_1=point.coordinate_1,
                coordinate_2=point.coordinate_2,
            )
            for rank, (distance, point, shared) in enumerate(
                rows[: configuration.neighbor_count], start=1
            )
        )

    observation_map = profile.observation_map
    comparisons = []
    for feature in index.features:
        definition = FEATURE_BY_ID[feature.feature_id]
        observation = observation_map[feature.feature_id]
        z = _z_value(observation.value, feature)
        percentile = (
            0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            if z is not None
            else None
        )
        comparisons.append(
            VerseMapFeatureComparison(
                feature_id=feature.feature_id,
                label=definition.label,
                group_id=definition.group_id,
                unit=definition.unit,
                query_value=observation.value,
                reference_mean=feature.raw_mean,
                reference_population_sd=feature.raw_population_sd,
                z_score=z,
                percentile=percentile,
                weight=feature.weight,
                coverage_rate=observation.coverage_rate,
                eligible_count=observation.eligible_count,
                matched_count=observation.matched_count,
            )
        )
    nearest_poems = neighbors(index.poems)
    nearest_poets = neighbors(index.poets)
    module_result = build_module_result(
        module_input,
        profile,
        reference_release_id=index.reference_release_id,
        reference_release_sha256=index.reference_release_sha256,
        model_id=index.model_id,
        evidence_weight_coverage=available_weight,
        x=x,
        y=y,
    )
    neighbor_metrics = []
    for kind, rows in (
        ("poem_neighbor", nearest_poems),
        ("poet_neighbor", nearest_poets),
    ):
        for item in rows:
            scope_id = f"{kind}:{item.rank}"
            neighbor_metrics.extend(
                (
                    ModuleMetric(
                        "versemap.neighbor_name",
                        item.title if kind == "poem_neighbor" else item.poet_name,
                        ResultLayer.INTERPRETATION,
                        scope=kind,
                        scope_id=scope_id,
                        note=item.poet_name,
                    ),
                    ModuleMetric(
                        "versemap.neighbor_distance",
                        item.distance,
                        ResultLayer.INTERPRETATION,
                        scope=kind,
                        scope_id=scope_id,
                        unit="weighted standardized distance",
                    ),
                    ModuleMetric(
                        "versemap.neighbor_shared_weight",
                        item.shared_weight,
                        ResultLayer.COMPUTED_SUMMARY,
                        scope=kind,
                        scope_id=scope_id,
                        unit="proportion of registered feature weight",
                    ),
                )
            )
    module_result = replace(
        module_result,
        metrics=(*module_result.metrics, *neighbor_metrics),
    )
    return VerseMapAnalysisResult(
        module_result=module_result,
        configuration=configuration,
        profile=profile,
        profile_build_id=index.profile_build_id,
        reference_release_id=index.reference_release_id,
        reference_release_sha256=index.reference_release_sha256,
        model_id=index.model_id,
        coordinate_1=x,
        coordinate_2=y,
        explained_variance_1=index.explained_variance_1,
        explained_variance_2=index.explained_variance_2,
        evidence_weight_coverage=available_weight,
        nearest_poems=nearest_poems,
        nearest_poets=nearest_poets,
        feature_comparisons=tuple(comparisons),
        map_points=(*index.poems, *index.poets),
    )


__all__ = [
    "DEFAULT_NEIGHBOR_COUNT",
    "MINIMUM_SHARED_WEIGHT",
    "MODEL_FILENAME",
    "ModelFeature",
    "POET_PROFILE_FILENAME",
    "PROFILE_FILENAME",
    "PROFILE_SCHEMA_VERSION",
    "ReferencePoint",
    "VerseMapAnalysisResult",
    "VerseMapConfiguration",
    "VerseMapFeatureComparison",
    "VerseMapNeighbor",
    "VerseMapReferenceIndex",
    "analyze_profile",
    "build_reference_model_bytes",
    "feature_weights",
    "load_reference_index",
]
