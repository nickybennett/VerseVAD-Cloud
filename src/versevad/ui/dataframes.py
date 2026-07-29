"""Arrow-safe formatting helpers for heterogeneous Streamlit tables."""

from __future__ import annotations

import copy
import json
import math
from numbers import Integral, Real

import pandas as pd


DISPLAY_DECIMAL_PLACES = 3


def round_display_value(value: object) -> object:
    """Round finite non-integral numbers for display without changing exports."""

    if isinstance(value, bool) or isinstance(value, Integral):
        return value
    if isinstance(value, Real):
        numeric = float(value)
        return (
            round(numeric, DISPLAY_DECIMAL_PLACES)
            if math.isfinite(numeric)
            else value
        )
    return value


def _rounded_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rounded = frame.copy()
    for column in rounded.columns:
        rounded[column] = rounded[column].map(round_display_value)
    return rounded


def rounded_display_data(data: object) -> object:
    """Return a display-only copy whose numeric cells have at most 3 decimals."""

    if isinstance(data, pd.DataFrame):
        return _rounded_frame(data)
    frame = getattr(data, "data", None)
    if isinstance(frame, pd.DataFrame):
        display = copy.deepcopy(data)
        display.data = _rounded_frame(frame)
        return display
    return data


def _rounded_json_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _rounded_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rounded_json_value(item) for item in value]
    return round_display_value(value)


def heterogeneous_display_value(value: object) -> str:
    """Render a mixed-type analytical value as explicit display-only text."""

    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(_rounded_json_value(value), ensure_ascii=False)
    return str(round_display_value(value))
