"""Deterministic descriptive statistics for matched VAD observations."""

from __future__ import annotations

import statistics
from collections.abc import Iterable

from versevad.models import DescriptiveStatistics, VadScores, WeightedVadStatistics


def descriptive_statistics(values: Iterable[float]) -> DescriptiveStatistics:
    observations = tuple(float(value) for value in values)
    if not observations:
        return DescriptiveStatistics(
            count=0,
            mean=None,
            median=None,
            population_standard_deviation=None,
            minimum=None,
            first_quartile=None,
            third_quartile=None,
            maximum=None,
        )

    if len(observations) == 1:
        # A single observed value supports a location statement, but it does
        # not supply an empirical distribution.  Do not manufacture zero
        # dispersion or zero range from an unavailable estimate.
        first_quartile = None
        third_quartile = None
        population_standard_deviation = None
    else:
        quartiles = statistics.quantiles(observations, n=4, method="inclusive")
        first_quartile = quartiles[0]
        third_quartile = quartiles[2]
        population_standard_deviation = statistics.pstdev(observations)

    return DescriptiveStatistics(
        count=len(observations),
        mean=statistics.fmean(observations),
        median=statistics.median(observations),
        population_standard_deviation=population_standard_deviation,
        minimum=min(observations),
        first_quartile=first_quartile,
        third_quartile=third_quartile,
        maximum=max(observations),
    )


def weighted_vad_statistics(values: Iterable[VadScores]) -> WeightedVadStatistics:
    observations = tuple(values)
    return WeightedVadStatistics(
        valence=descriptive_statistics(item.valence for item in observations),
        arousal=descriptive_statistics(item.arousal for item in observations),
        dominance=descriptive_statistics(item.dominance for item in observations),
    )
