from __future__ import annotations

import math

from versevad.analysis.statistics import descriptive_statistics


def test_empty_observations_remain_missing() -> None:
    result = descriptive_statistics([])

    assert result.count == 0
    assert result.mean is None
    assert result.minimum is None
    assert result.maximum is None


def test_single_observation_retains_location_but_not_inferred_dispersion() -> None:
    result = descriptive_statistics([4.0])

    assert result.count == 1
    assert result.mean == 4.0
    assert result.population_standard_deviation is None
    assert result.first_quartile is None
    assert result.third_quartile is None
    assert result.minimum == 4.0
    assert result.maximum == 4.0


def test_population_statistics_are_documented_and_deterministic() -> None:
    result = descriptive_statistics([1.0, 3.0, 5.0, 7.0])

    assert result.mean == 4.0
    assert result.median == 4.0
    assert result.first_quartile == 2.5
    assert result.third_quartile == 5.5
    assert math.isclose(result.population_standard_deviation or 0, math.sqrt(5))
