"""Human-readable reproducibility records shared by research ZIP exports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping, Sequence

from versevad import __version__
from versevad.analysis_profiles import (
    CONTENT_WORD_DEFINITION_ID,
    CONTENT_WORD_POS_TAGS,
    PHRASE_SCOPE_POLICY_ID,
    PROFILE_SCHEMA_VERSION,
    AnalysisProfile,
    scope_definitions,
)
from versevad.module_capabilities import MODULE_CAPABILITIES


def _lines(title: str, values: Sequence[str]) -> list[str]:
    return [title, *(f"- {value}" for value in values), ""]


def build_reproducibility_readme(
    *,
    export_mode: str,
    workspace: str,
    report_section: str,
    analysis_id: str,
    title: str,
    author: str = "",
    source_filename: str = "",
    source_sha256: str = "",
    visible_profiles: Sequence[AnalysisProfile] = (),
    included_profiles: Sequence[AnalysisProfile] = (),
    active_annotation_scope: str = "",
    active_preset: str = "",
    preprocessing: Sequence[str] = (),
    resources: Sequence[str] = (),
    overrides: Sequence[str] = (),
    context: Sequence[str] = (),
    included_fixed_modules: Sequence[str] | None = None,
    export_timestamp: str | None = None,
) -> bytes:
    """Build the required plain-language audit companion."""

    fixed_ids = (
        None
        if included_fixed_modules is None
        else frozenset(included_fixed_modules)
    )
    fixed = [
        f"{module_id}: {capability.fixed_profile_id} — "
        f"{capability.method_note or 'documented native rules'}"
        for module_id, capability in MODULE_CAPABILITIES.items()
        if capability.fixed_profile_id
        and (fixed_ids is None or module_id in fixed_ids)
    ]
    definitions = scope_definitions()
    lines = [
        "VerseVAD Reproducibility README",
        "================================",
        "",
        "Analysis identity",
        f"- VerseVAD version: {__version__}",
        f"- Profile schema: {PROFILE_SCHEMA_VERSION}",
        f"- Export timestamp: {export_timestamp or datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- Workspace: {workspace}",
        f"- Report section: {report_section or 'complete analysis'}",
        f"- Analysis or project ID: {analysis_id}",
        f"- Title: {title}",
        f"- Author: {author or 'not supplied'}",
        f"- Source filename: {source_filename or 'pasted text or not supplied'}",
        f"- Source-text SHA-256: {source_sha256 or 'not available'}",
        "",
        "Export mode",
        f"- {'Current View' if export_mode == 'current_view' else 'Complete Audit'}",
        "",
    ]
    lines += _lines(
        "Profiles visible when exported",
        [profile.label + f" ({profile.id})" for profile in visible_profiles]
        or ["none recorded"],
    )
    lines += _lines(
        "Profiles included in this package",
        [profile.label + f" ({profile.id})" for profile in included_profiles]
        or ["fixed-profile results only"],
    )
    lines += [
        "Displayed state",
        f"- Active annotation scope: {active_annotation_scope or 'not applicable'}",
        f"- Active analysis preset: {active_preset or 'custom or not recorded'}",
        "",
        "Scope definitions",
        f"- All lexical tokens: {definitions['ALL_LEXICAL']}",
        f"- Stopword-excluded: {definitions['STOPWORD_EXCLUDED']}",
        f"- Content words only: {definitions['CONTENT_WORDS']}",
        f"- Content-word definition: {CONTENT_WORD_DEFINITION_ID}; eligible POS: {', '.join(sorted(CONTENT_WORD_POS_TAGS))}",
        f"- Phrase rule: {PHRASE_SCOPE_POLICY_ID}; a matched expression is never partly excluded.",
        "",
        "Weighting definitions",
        "- Token-weighted: every eligible occurrence contributes, so repetition affects aggregates.",
        "- Type-weighted: each documented metric-specific type identity contributes once.",
        "- Exact type-identity rules are recorded in profile metric CSV rows.",
        "",
    ]
    lines += _lines("Fixed analytical profiles", fixed)
    lines += _lines(
        "Preprocessing and text handling",
        list(preprocessing)
        or [
            "Unicode and whitespace normalization are applied only to a separate processing representation.",
            "Original spelling, punctuation, lineation, stanza breaks, and source text are retained for display and formal analysis.",
            "Tokenizer, POS, lemma, sentence, line, and stanza evidence are retained in the audit tables where available.",
        ],
    )
    lines += _lines("Resources and provenance", list(resources) or ["See resource and manifest CSV files."])
    lines += _lines("Scholar overrides", list(overrides) or ["none recorded"])
    lines += _lines("Corpus and comparison context", list(context) or ["not applicable"])
    lines += [
        "Metric and missing-value rules",
        "- Every profile metric records scope, weighting, observation count, eligible denominators, coverage, exclusions, phrase matches, unit, and type identity.",
        "- Missing resource values remain missing; they are never silently converted to zero or neutral values.",
        "- Scope-excluded words are not counted as unmatched.",
        "- Interface rounding is presentational; exported numeric values retain their available precision.",
        "",
        "Limitations",
        "- Lexicon coverage, polysemy, context, irony, historical usage, spelling, proper names, and model-generated linguistic annotations can affect results.",
        "- Fixed-profile readability, sound/form, VerseMap, and sentiment results follow their documented native methods rather than the global display controls.",
        "- VerseVAD provides evidence for interpretation; it does not determine a poem's emotion, quality, meaning, authorial intent, or reader response.",
        "",
    ]
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build_file_inventory(
    files: Mapping[str, bytes],
    *,
    export_mode: str,
    profile_ids: str,
) -> bytes:
    """List every packaged file in the required human-readable companion."""

    lines = [
        "filename\tpurpose\texport_mode\tprofile_or_fixed_module\tbytes"
    ]
    for filename, content in sorted(files.items()):
        purpose = (
            "narrative report"
            if filename.endswith(".docx")
            else "tabular analysis or audit data"
            if filename.endswith(".csv")
            else "reproducibility documentation"
        )
        lines.append(
            f"{filename}\t{purpose}\t{export_mode}\t{profile_ids or 'fixed/native'}\t{len(content)}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def methods_appendix_paragraphs(
    profiles: Sequence[AnalysisProfile],
    *,
    source_sha256: str,
) -> tuple[str, ...]:
    labels = ", ".join(profile.label for profile in profiles) or "fixed native profile"
    return (
        f"VerseVAD {__version__}; displayed configurable profiles: {labels}.",
        "Configurable aggregates were produced from retained token/resource evidence; changing scope or weighting did not rerun preprocessing or lookup.",
        f"Source-text SHA-256: {source_sha256 or 'not available'}.",
        "Missing values remained missing, excluded words were not counted as unmatched, and complete matched phrases were preserved.",
    )


__all__ = [
    "build_file_inventory",
    "build_reproducibility_readme",
    "methods_appendix_paragraphs",
]
