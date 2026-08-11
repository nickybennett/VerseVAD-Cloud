"""Module-specific reporting exceptions layered over the global profile selection.

These helpers never alter preprocessing, retained evidence, or the user's global
lexical scope.  They select an already-calculated content-word profile for the
small set of lexical modules that explicitly support the reporting exception.
"""

from __future__ import annotations

from collections.abc import Iterable

from versevad.analysis_profiles import (
    AnalysisProfile,
    LexicalScope,
    ProfileSelection,
    display_profile_order,
)


CONTENT_WORD_SCOPE_OVERRIDE_LABEL = "Content Words Only (Scope Override)"

CONTENT_WORD_SCOPE_OVERRIDE_GROUPS: dict[str, tuple[str, ...]] = {
    "emotion": ("emotion_association", "emotion_intensity"),
    "concreteness": ("concreteness",),
    "sensorimotor": ("sensorimotor",),
    "frequency": ("frequency",),
    "aoa": ("aoa",),
}

CONTENT_WORD_SCOPE_OVERRIDE_MODULES = frozenset(
    module_id
    for module_ids in CONTENT_WORD_SCOPE_OVERRIDE_GROUPS.values()
    for module_id in module_ids
)

CONTENT_WORD_SCOPE_OVERRIDE_TITLES = {
    "emotion": "Emotional Association and Intensity",
    "concreteness": "Concreteness",
    "sensorimotor": "Sensorimotor Imagery and Embodiment",
    "frequency": "Frequency and Rarity",
    "aoa": "Age of Acquisition",
}

REPORT_SECTION_OVERRIDE_MODULES: dict[str, frozenset[str]] = {
    "Affective Evidence": frozenset(
        {"emotion_association", "emotion_intensity"}
    ),
    "Lexical Character, Imagery & Embodiment": frozenset(
        {"concreteness", "sensorimotor", "frequency", "aoa"}
    ),
}


def content_word_selection(selection: ProfileSelection) -> ProfileSelection:
    """Retain the global weighting choices while forcing content-word scope."""

    return ProfileSelection(
        scopes=(LexicalScope.CONTENT_WORDS,),
        weightings=selection.weightings,
    )


def modules_for_groups(groups: Iterable[str]) -> frozenset[str]:
    return frozenset(
        module_id
        for group in groups
        for module_id in CONTENT_WORD_SCOPE_OVERRIDE_GROUPS.get(group, ())
    )


def selection_for_module(
    selection: ProfileSelection,
    module_id: str,
    overridden_modules: Iterable[str] = (),
) -> ProfileSelection:
    return (
        content_word_selection(selection)
        if module_id in frozenset(overridden_modules)
        else selection
    )


def profile_applies_to_module(
    profile: AnalysisProfile,
    *,
    module_id: str,
    selection: ProfileSelection,
    overridden_modules: Iterable[str] = (),
) -> bool:
    return profile in selection_for_module(
        selection,
        module_id,
        overridden_modules,
    ).profiles


def effective_profiles(
    selection: ProfileSelection,
    overridden_modules: Iterable[str] = (),
) -> tuple[AnalysisProfile, ...]:
    """Return the ordered union needed to render/export fixed and exception rows."""

    profiles = list(display_profile_order(selection))
    if frozenset(overridden_modules):
        for profile in display_profile_order(content_word_selection(selection)):
            if profile not in profiles:
                profiles.append(profile)
    return tuple(profiles)


def canonical_module_id(metric_id: str) -> str:
    """Map canonical metric identifiers to a scope-configurable module."""

    prefix = str(metric_id).split(".", 1)[0].strip().casefold()
    aliases = {
        "emotion": "emotion_association",
        "emotion_association": "emotion_association",
        "emotion_intensity": "emotion_intensity",
        "concreteness": "concreteness",
        "frequency": "frequency",
        "rarity": "frequency",
        "aoa": "aoa",
        "sensorimotor": "sensorimotor",
    }
    return aliases.get(prefix, prefix)


def corpus_metric_module_id(metric_name: str) -> str:
    """Map persisted corpus metric names to their canonical module."""

    normalized = str(metric_name).strip().casefold()
    aliases = (
        ("emotion_association_", "emotion_association"),
        ("emotion_intensity_", "emotion_intensity"),
        ("concreteness_", "concreteness"),
        ("frequency_", "frequency"),
        ("rarity_", "frequency"),
        ("aoa_", "aoa"),
        ("sensorimotor_", "sensorimotor"),
    )
    return next(
        (module_id for prefix, module_id in aliases if normalized.startswith(prefix)),
        "",
    )


def override_descriptions(
    selection: ProfileSelection,
    overridden_modules: Iterable[str],
) -> tuple[str, ...]:
    modules = frozenset(overridden_modules)
    if not modules:
        return ()
    weighting_labels = ", ".join(item.label for item in selection.weightings)
    descriptions: list[str] = []
    for group, group_modules in CONTENT_WORD_SCOPE_OVERRIDE_GROUPS.items():
        if modules.intersection(group_modules):
            descriptions.append(
                f"{CONTENT_WORD_SCOPE_OVERRIDE_TITLES[group]}: content words only; "
                f"aggregation weighting inherited from the global selection "
                f"({weighting_labels})."
            )
    return tuple(descriptions)


def overrides_for_report_section(
    report_section: str,
    overridden_modules: Iterable[str],
) -> frozenset[str]:
    """Limit active exceptions to modules represented by a Current View export."""

    return frozenset(overridden_modules).intersection(
        REPORT_SECTION_OVERRIDE_MODULES.get(str(report_section), frozenset())
    )


__all__ = [
    "CONTENT_WORD_SCOPE_OVERRIDE_GROUPS",
    "CONTENT_WORD_SCOPE_OVERRIDE_LABEL",
    "CONTENT_WORD_SCOPE_OVERRIDE_MODULES",
    "CONTENT_WORD_SCOPE_OVERRIDE_TITLES",
    "REPORT_SECTION_OVERRIDE_MODULES",
    "canonical_module_id",
    "content_word_selection",
    "corpus_metric_module_id",
    "effective_profiles",
    "modules_for_groups",
    "override_descriptions",
    "overrides_for_report_section",
    "profile_applies_to_module",
    "selection_for_module",
]
