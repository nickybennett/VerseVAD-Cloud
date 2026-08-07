"""Central report capability and fixed analytical-profile registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


FIXED_PROFILE_NOTICE = (
    "Fixed analytical profile: This section uses its documented scope and "
    "weighting rules for methodological accuracy and comparability. Global "
    "report controls do not alter these results."
)


class CapabilityCategory(StrEnum):
    SCOPE_AND_WEIGHTING = "A"
    SCOPE_ONLY = "B"
    WEIGHTING_ONLY = "C"
    FIXED_PROFILE = "D"


@dataclass(frozen=True)
class ModuleCapability:
    module_id: str
    category: CapabilityCategory
    type_identity_rule: str = "normalized_surface"
    fixed_profile_id: str = ""
    method_note: str = ""

    @property
    def scope_configurable(self) -> bool:
        return self.category in {
            CapabilityCategory.SCOPE_AND_WEIGHTING,
            CapabilityCategory.SCOPE_ONLY,
        }

    @property
    def weighting_configurable(self) -> bool:
        return self.category in {
            CapabilityCategory.SCOPE_AND_WEIGHTING,
            CapabilityCategory.WEIGHTING_ONLY,
        }


_REGISTRY = {
    # Category A: both global controls apply.
    "vad": ModuleCapability("vad", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "emotion_association": ModuleCapability("emotion_association", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "emotion_intensity": ModuleCapability("emotion_intensity", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_entry_category"),
    "concreteness": ModuleCapability("concreteness", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "frequency": ModuleCapability("frequency", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "aoa": ModuleCapability("aoa", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "sensorimotor": ModuleCapability("sensorimotor", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_resource_entry"),
    "poetry_id": ModuleCapability("poetry_id", CapabilityCategory.SCOPE_AND_WEIGHTING, "matched_vad_entry"),
    "word_length": ModuleCapability("word_length", CapabilityCategory.SCOPE_AND_WEIGHTING, "normalized_surface"),
    "part_of_speech": ModuleCapability("part_of_speech", CapabilityCategory.SCOPE_AND_WEIGHTING, "pos_aware_lemma"),
    # Category B: scope changes eligibility; occurrence weighting is not meaningful.
    "interactive_annotation": ModuleCapability("interactive_annotation", CapabilityCategory.SCOPE_ONLY),
    "lexical_diagnostics": ModuleCapability("lexical_diagnostics", CapabilityCategory.SCOPE_ONLY),
    "lexical_diversity": ModuleCapability(
        "lexical_diversity",
        CapabilityCategory.SCOPE_ONLY,
        method_note="MATTR, HD-D, and MTLD retain their native occurrence-sequence definitions.",
    ),
    # Category D: methodologically fixed profiles.
    "versemap": ModuleCapability("versemap", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="VERSEMAP_REGISTERED_V1"),
    "vv_pre": ModuleCapability("vv_pre", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="VV_PRE_V1"),
    "vader": ModuleCapability("vader", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="VADER_NATIVE_V1"),
    "traditional_readability": ModuleCapability("traditional_readability", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="TRADITIONAL_READABILITY_NATIVE_V1"),
    "pronunciation": ModuleCapability("pronunciation", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="FULL_TEXT_PROSODY_V1"),
    "meter": ModuleCapability("meter", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="FULL_TEXT_PROSODY_V1"),
    "phonology": ModuleCapability("phonology", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="FULL_TEXT_PROSODY_V1"),
    "inherited_form": ModuleCapability("inherited_form", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="INHERITED_FORM_V2"),
    "structure": ModuleCapability("structure", CapabilityCategory.FIXED_PROFILE, fixed_profile_id="FULL_TEXT_STRUCTURE_V1"),
}

MODULE_CAPABILITIES: Mapping[str, ModuleCapability] = MappingProxyType(_REGISTRY)


def module_capability(module_id: str) -> ModuleCapability:
    try:
        return MODULE_CAPABILITIES[module_id]
    except KeyError as error:
        raise KeyError(f"No scope/weighting capability is registered for {module_id!r}.") from error


def fixed_profile_notice(module_id: str) -> str:
    capability = module_capability(module_id)
    if capability.category is not CapabilityCategory.FIXED_PROFILE:
        return ""
    return f"{FIXED_PROFILE_NOTICE} Profile ID: {capability.fixed_profile_id}."


__all__ = [
    "CapabilityCategory",
    "FIXED_PROFILE_NOTICE",
    "MODULE_CAPABILITIES",
    "ModuleCapability",
    "fixed_profile_notice",
    "module_capability",
]
