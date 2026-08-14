from __future__ import annotations

import pytest

from versevad.analysis_profiles import (
    AggregationWeighting,
    LexicalScope,
    ProfileSelection,
    display_profile_order,
)
from versevad.ui import profile_details


@pytest.mark.parametrize("restored_value", (None, "Stale profile label"))
def test_detail_profile_falls_back_when_widget_state_is_missing_or_stale(
    monkeypatch: pytest.MonkeyPatch,
    restored_value: str | None,
) -> None:
    selection = ProfileSelection(
        scopes=(LexicalScope.ALL_LEXICAL, LexicalScope.STOPWORD_EXCLUDED),
        weightings=(AggregationWeighting.TOKEN,),
    )
    monkeypatch.setattr(
        profile_details.st,
        "selectbox",
        lambda *args, **kwargs: restored_value,
    )

    selected = profile_details.select_detail_profile(
        selection,
        key="profile-state-regression",
    )

    assert selected == display_profile_order(selection)[0]


def test_detail_profile_preserves_a_valid_widget_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = ProfileSelection(
        scopes=(LexicalScope.ALL_LEXICAL, LexicalScope.STOPWORD_EXCLUDED),
        weightings=(AggregationWeighting.TOKEN,),
    )
    profiles = display_profile_order(selection)
    monkeypatch.setattr(
        profile_details.st,
        "selectbox",
        lambda *args, **kwargs: profiles[-1].label,
    )

    selected = profile_details.select_detail_profile(
        selection,
        key="profile-state-regression",
    )

    assert selected == profiles[-1]


def test_affect_detail_helpers_treat_missing_profile_as_unavailable() -> None:
    assert profile_details.affect_continuous_profile_detail(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        profile=None,
        module_id="emotion_association",
        metric_id="joy_association",
        value_getter=lambda match: 1.0,
    ) is None
    assert profile_details.categorical_affect_contributors(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        profile=None,
        category="joy",
    ) == ()
