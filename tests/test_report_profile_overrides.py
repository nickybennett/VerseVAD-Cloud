from versevad.analysis_profiles import (
    AggregationWeighting,
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
)
from versevad.report_profile_overrides import (
    CONTENT_WORD_SCOPE_OVERRIDE_LABEL,
    canonical_module_id,
    content_word_selection,
    corpus_metric_module_id,
    effective_profiles,
    modules_for_groups,
    profile_applies_to_module,
)


def test_content_word_override_preserves_global_weightings_only() -> None:
    selection = ProfileSelection(
        scopes=(LexicalScope.ALL_LEXICAL, LexicalScope.STOPWORD_EXCLUDED),
        weightings=(AggregationWeighting.TOKEN, AggregationWeighting.TYPE),
    )

    overridden = content_word_selection(selection)

    assert overridden.scopes == (LexicalScope.CONTENT_WORDS,)
    assert overridden.weightings == selection.weightings
    assert CONTENT_WORD_SCOPE_OVERRIDE_LABEL == "Content Words Only (Scope Override)"


def test_override_applies_only_to_named_modules() -> None:
    selection = ProfileSelection()
    content_profile = AnalysisProfile(
        LexicalScope.CONTENT_WORDS,
        AggregationWeighting.TOKEN,
    )
    default_profile = selection.profiles[0]
    modules = modules_for_groups(("emotion", "frequency"))

    assert profile_applies_to_module(
        content_profile,
        module_id="frequency",
        selection=selection,
        overridden_modules=modules,
    )
    assert not profile_applies_to_module(
        default_profile,
        module_id="frequency",
        selection=selection,
        overridden_modules=modules,
    )
    assert profile_applies_to_module(
        default_profile,
        module_id="concreteness",
        selection=selection,
        overridden_modules=modules,
    )
    assert not profile_applies_to_module(
        content_profile,
        module_id="concreteness",
        selection=selection,
        overridden_modules=modules,
    )


def test_effective_profiles_add_content_scope_without_replacing_global_profile() -> None:
    selection = ProfileSelection()
    profiles = effective_profiles(selection, ("aoa",))

    assert profiles == (
        AnalysisProfile(
            LexicalScope.STOPWORD_EXCLUDED,
            AggregationWeighting.TOKEN,
        ),
        AnalysisProfile(
            LexicalScope.CONTENT_WORDS,
            AggregationWeighting.TOKEN,
        ),
    )


def test_metric_identifier_aliases_share_one_canonical_policy() -> None:
    assert canonical_module_id("emotion.anger.association") == "emotion_association"
    assert canonical_module_id("rarity.mean") == "frequency"
    assert corpus_metric_module_id("emotion_intensity_anger_mean") == "emotion_intensity"
    assert corpus_metric_module_id("frequency_frequency_mean") == "frequency"
    assert corpus_metric_module_id("vad_mean") == ""

