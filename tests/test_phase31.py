import pytest

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import (
    AnalysisRequest,
    VAD_DEFINITIONS,
    WorkspaceAnalysis,
    vad_contributor_views,
    vad_cumulative_views,
    vad_interpretation_views,
)
from versevad.models import PhrasePolicy
from versevad.phase2_validation import phase2_synthetic_vad_lexicon
from versevad.preprocessing import create_text_document


@pytest.fixture
def contributor_workspace(preprocessor) -> WorkspaceAnalysis:
    document = create_text_document(
        "contributors",
        "Contributor test",
        "Bright bright dark.",
    )
    result = analyze_lexicon(
        document,
        phase2_synthetic_vad_lexicon(),
        preprocessor,
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
    )
    request = AnalysisRequest(
        project_name="Synthetic",
        title=document.title,
        original_text=document.original_text,
        lexicon_ids=(result.lexicon_metadata.lexicon_id,),
        phrase_policy=PhrasePolicy.UNIGRAM_ONLY,
    )
    return WorkspaceAnalysis(request, document, (result,), compare_lexicons((result,)))


def test_definitions_explain_vad_in_beginner_language() -> None:
    assert "pleasant" in VAD_DEFINITIONS["valence"]
    assert "not specifically sexual" in VAD_DEFINITIONS["arousal"]
    assert "control" in VAD_DEFINITIONS["dominance"]


def test_vad_interpretation_states_matches_coverage_and_scope(
    contributor_workspace,
) -> None:
    rows = vad_interpretation_views(contributor_workspace)
    valence = next(row for row in rows if row.dimension == "valence")
    assert valence.matched_observations == 3
    assert valence.relation_to_midpoint == "above"
    assert "included matched observations" in valence.explanation
    assert "not the poem or speaker" in valence.explanation


def test_vad_contributors_use_midpoint_centered_weighted_deviation(
    contributor_workspace,
) -> None:
    rows = vad_contributor_views(contributor_workspace)
    valence = [
        row
        for row in rows
        if row.dimension == "valence"
        and row.analysis_view == "All matched tokens"
        and row.weighting == "Token-weighted"
    ]
    bright = next(row for row in valence if row.term == "bright")
    dark = next(row for row in valence if row.term == "dark")
    assert bright.observations == 2
    assert bright.direction == "above-midpoint weighted deviation"
    assert bright.signed_contribution == pytest.approx(0.75)
    assert bright.effect_on_mean == pytest.approx(5 / 12)
    assert dark.direction == "below-midpoint weighted deviation"
    assert dark.signed_contribution == pytest.approx(-0.25)
    assert dark.effect_on_mean == pytest.approx(-5 / 24)
    assert bright.example_line == 1


def test_cumulative_vad_keeps_length_sensitive_token_totals(
    contributor_workspace,
) -> None:
    rows = vad_cumulative_views(contributor_workspace)
    valence = next(
        row
        for row in rows
        if row.dimension == "valence"
        and row.analysis_view == "All matched tokens"
    )
    assert valence.matched_observations == 3
    assert valence.rating_total == pytest.approx(2.0)
    assert valence.above_midpoint_deviation == pytest.approx(0.75)
    assert valence.below_midpoint_deviation == pytest.approx(0.25)
    assert valence.net_midpoint_deviation == pytest.approx(0.5)
    assert valence.absolute_midpoint_deviation == pytest.approx(1.0)
    assert valence.above_midpoint_deviation_per_observation == pytest.approx(0.25)
    assert valence.below_midpoint_deviation_per_observation == pytest.approx(1 / 12)
    assert valence.absolute_midpoint_deviation_per_observation == pytest.approx(1 / 3)
    assert valence.above_midpoint_deviation_per_100 == pytest.approx(25.0)
    assert valence.below_midpoint_deviation_per_100 == pytest.approx(25 / 3)
    assert valence.absolute_midpoint_deviation_per_100 == pytest.approx(100 / 3)
    assert valence.average_deviation_from_poem_mean == pytest.approx(5 / 18)

    type_valence = next(
        row
        for row in rows
        if row.dimension == "valence"
        and row.analysis_view == "All matched tokens"
        and row.weighting == "Type-weighted"
    )
    assert type_valence.matched_observations == 2
    assert type_valence.rating_total == pytest.approx(1.125)
    assert type_valence.absolute_midpoint_deviation == pytest.approx(0.625)
    assert type_valence.average_deviation_from_poem_mean == pytest.approx(0.3125)
