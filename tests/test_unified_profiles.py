from __future__ import annotations

from dataclasses import replace

import pytest

from versevad.analysis_profiles import (
    ALL_COMPATIBLE_PROFILES,
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
    display_profile_order,
    primary_display_profile,
)
from versevad.exports.reproducibility import (
    build_file_inventory,
    build_reproducibility_readme,
)
from versevad.preprocessing import create_text_document
from versevad.profile_aggregation import ScalarEvidence, aggregate_scalar_evidence
from versevad.ui.workspace_state import (
    activate_workspace_state,
    clear_workspace_state,
)


def _tokens(preprocessor, text: str, pos: tuple[str, ...]):
    processed = preprocessor.process_document(
        create_text_document("profiles", "Profiles", text)
    )
    lexical = [token for token in processed.tokens if not token.is_punctuation]
    assert len(lexical) == len(pos)
    return tuple(
        replace(token, part_of_speech=part_of_speech)
        for token, part_of_speech in zip(lexical, pos, strict=True)
    )


def test_six_profiles_are_derived_from_retained_evidence(preprocessor) -> None:
    tokens = _tokens(
        preprocessor,
        "the bright bright river",
        ("DET", "ADJ", "ADJ", "NOUN"),
    )
    values = (0.5, 0.9, 0.9, 0.3)
    observations = tuple(
        ScalarEvidence((token.token_id,), value, token.normalized_form)
        for token, value in zip(tokens, values, strict=True)
    )

    summaries = aggregate_scalar_evidence(
        tokens=tokens,
        observations=observations,
        active_stopwords=("the",),
    )

    assert {
        (profile.scope, profile.weighting) for profile in summaries
    } == set(ALL_COMPATIBLE_PROFILES)
    assert summaries[
        AnalysisProfile(LexicalScope.ALL_LEXICAL, AggregationWeighting.TOKEN)
    ].statistics.mean == pytest.approx(0.65)
    assert summaries[
        AnalysisProfile(LexicalScope.ALL_LEXICAL, AggregationWeighting.TYPE)
    ].statistics.mean == pytest.approx((0.5 + 0.9 + 0.3) / 3)
    stopword_profile = summaries[
        AnalysisProfile(LexicalScope.STOPWORD_EXCLUDED, AggregationWeighting.TOKEN)
    ]
    assert stopword_profile.statistics.count == 3
    assert stopword_profile.coverage.excluded_stopword_count == 1
    assert stopword_profile.coverage.unmatched_token_count == 0


def test_compact_displays_prefer_stopword_excluded_token_weighting() -> None:
    selection = ProfileSelection(
        scopes=(LexicalScope.ALL_LEXICAL, LexicalScope.STOPWORD_EXCLUDED),
        weightings=(AggregationWeighting.TOKEN, AggregationWeighting.TYPE),
    )

    primary = primary_display_profile(selection)

    assert primary == AnalysisProfile(
        LexicalScope.STOPWORD_EXCLUDED,
        AggregationWeighting.TOKEN,
    )
    assert display_profile_order(selection)[0] == primary
    assert set(display_profile_order(selection)) == set(selection.profiles)


def test_compact_displays_use_selected_profile_when_default_is_absent() -> None:
    selection = ProfileSelection(
        scopes=(LexicalScope.CONTENT_WORDS,),
        weightings=(AggregationWeighting.TYPE,),
    )

    assert primary_display_profile(selection) == selection.profiles[0]


def test_phrase_is_preserved_and_counted_as_one_occurrence(preprocessor) -> None:
    tokens = _tokens(preprocessor, "kind of rests", ("ADJ", "ADP", "VERB"))
    observations = (
        ScalarEvidence(
            (tokens[0].token_id, tokens[1].token_id),
            0.8,
            "kind of",
            phrase=True,
        ),
        ScalarEvidence((tokens[2].token_id,), 0.4, "rest"),
    )

    summaries = aggregate_scalar_evidence(
        tokens=tokens,
        observations=observations,
        active_stopwords=("of",),
    )

    for scope in LexicalScope:
        token_summary = summaries[
            AnalysisProfile(scope, AggregationWeighting.TOKEN)
        ]
        assert token_summary.statistics.count == 2
        assert token_summary.statistics.mean == pytest.approx(0.6)
        assert token_summary.coverage.eligible_token_count == 3
        assert token_summary.coverage.matched_token_count == 3
        assert token_summary.coverage.phrase_match_count == 1


def test_reproducibility_companions_distinguish_empty_fixed_selection() -> None:
    profile = AnalysisProfile(
        LexicalScope.STOPWORD_EXCLUDED,
        AggregationWeighting.TOKEN,
    )
    readme = build_reproducibility_readme(
        export_mode="current_view",
        workspace="Single Poem",
        report_section="Affective Evidence",
        analysis_id="analysis-1",
        title="Example",
        visible_profiles=(profile,),
        included_profiles=(profile,),
        included_fixed_modules=(),
    ).decode("utf-8")
    assert profile.id in readme
    assert "PoetryID Profile" not in readme

    inventory = build_file_inventory(
        {"metrics.csv": b"a,b\n", "report.docx": b"docx"},
        export_mode="current_view",
        profile_ids=profile.id,
    ).decode("utf-8")
    assert "metrics.csv\ttabular analysis or audit data" in inventory
    assert "report.docx\tnarrative report" in inventory


def test_text_workspace_state_is_isolated_and_clear_is_targeted() -> None:
    state: dict[str, object] = {}
    activate_workspace_state(state, "Single Poem")
    state["poem_text"] = "single poem"
    state["poem_title"] = "Single"

    activate_workspace_state(state, "Other Text")
    assert "poem_text" not in state
    state["poem_text"] = "other text"

    activate_workspace_state(state, "Single Poem")
    assert state["poem_text"] == "single poem"
    assert state["poem_title"] == "Single"

    clear_workspace_state(state, "Single Poem")
    assert "poem_text" not in state
    activate_workspace_state(state, "Other Text")
    assert state["poem_text"] == "other text"


def test_experiential_dynamics_state_belongs_only_to_single_poem() -> None:
    state: dict[str, object] = {}
    activate_workspace_state(state, "Single Poem")
    state["experiential_dynamics_text_version_id"] = "version-1"
    state["experiential_dynamics_response_V1"] = 4

    activate_workspace_state(state, "Other Text")
    assert "experiential_dynamics_text_version_id" not in state
    assert "experiential_dynamics_response_V1" not in state

    activate_workspace_state(state, "Single Poem")
    assert state["experiential_dynamics_text_version_id"] == "version-1"
    assert state["experiential_dynamics_response_V1"] == 4


def test_text_workspace_upload_widget_is_never_restored() -> None:
    upload = object()
    state: dict[str, object] = {}
    activate_workspace_state(state, "Single Poem")
    state["poem_text"] = "single poem"
    state["uploaded_poem"] = upload

    activate_workspace_state(state, "Lexicon Explorer")
    assert "uploaded_poem" not in state

    activate_workspace_state(state, "Single Poem")
    assert state["poem_text"] == "single poem"
    assert "uploaded_poem" not in state


def test_text_workspace_ignores_legacy_vaulted_upload_widget() -> None:
    state: dict[str, object] = {
        "_versevad_workspace_state": {
            "Single Poem": {
                "poem_text": "restored poem",
                "uploaded_poem": object(),
            }
        },
        "_versevad_active_workspace_state": "Lexicon Explorer",
    }

    activate_workspace_state(state, "Single Poem")

    assert state["poem_text"] == "restored poem"
    assert "uploaded_poem" not in state
