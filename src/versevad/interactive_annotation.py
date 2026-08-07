"""Framework-independent token evidence for interactive poem annotation.

The annotation view is deliberately a presentation layer over completed
analysis artifacts.  It never performs a lexicon lookup, retokenizes text, or
derives a new score.  Stable token IDs and source offsets join the existing
module audits so repeated words and phrase matches remain traceable.
"""

from __future__ import annotations

from typing import Iterable

from versevad.analysis_profiles import LexicalScope, token_is_in_scope
from versevad.lexical_eligibility import is_lexicon_eligible


ANNOTATION_PAYLOAD_VERSION = "1.2"
VAD_SOURCE_PRIORITY = (
    "nrc_vad_v2_1",
    "nrc_vad_v1",
    "warriner_vad_2013",
)
CONTINUOUS_LAYER_IDS = (
    "valence",
    "arousal",
    "dominance",
    "concreteness",
    "frequency",
    "aoa",
)
CATEGORICAL_LAYER_IDS = ("sensorimotor", "emotion", "pos")
ALL_LAYER_IDS = CONTINUOUS_LAYER_IDS + CATEGORICAL_LAYER_IDS

_POS_LABELS = {
    "ADJ": "Adjective",
    "ADP": "Preposition",
    "ADV": "Adverb",
    "AUX": "Auxiliary or copular verb",
    "CCONJ": "Coordinating conjunction",
    "DET": "Determiner",
    "INTJ": "Interjection",
    "NOUN": "Common noun",
    "NUM": "Numeral",
    "PART": "Particle",
    "PRON": "Pronoun",
    "PROPN": "Proper noun",
    "PUNCT": "Punctuation",
    "SCONJ": "Subordinating conjunction",
    "SPACE": "Whitespace",
    "SYM": "Symbol",
    "VERB": "Main verb",
    "X": "Other or uncertain",
}


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _source_priority(lexicon_id: str) -> tuple[int, str]:
    try:
        return (VAD_SOURCE_PRIORITY.index(lexicon_id), lexicon_id)
    except ValueError:
        return (len(VAD_SOURCE_PRIORITY), lexicon_id)


def _is_vad_result(result: object) -> bool:
    return any(
        getattr(match, "normalized_scores", None) is not None
        for match in getattr(result, "matches", ())
    ) or getattr(result, "vad_summary", None) is not None


def _expression_match(token_ids: Iterable[str], method: object) -> bool:
    return len(tuple(token_ids)) > 1 or "phrase" in _enum_value(method)


def _match_sort_key(match: object) -> tuple[int, int, int, str]:
    token_ids = tuple(getattr(match, "token_ids", ()))
    return (
        0 if getattr(match, "included", False) else 1,
        -len(token_ids),
        int(getattr(match, "start_token_position", 0)),
        str(getattr(match, "match_id", "")),
    )


def _match_status(matches: tuple[object, ...]) -> tuple[str, str]:
    if any(getattr(match, "included", False) for match in matches):
        return "matched", "Matched by the completed analysis."
    selection_values = {_enum_value(getattr(match, "selection", "")) for match in matches}
    if "unmatched" in selection_values:
        reason = next(
            (
                str(getattr(match, "reason", ""))
                for match in matches
                if _enum_value(getattr(match, "selection", "")) == "unmatched"
                and str(getattr(match, "reason", ""))
            ),
            "No entry in the active source.",
        )
        return "unmatched", reason
    if matches:
        reason = next(
            (str(getattr(match, "reason", "")) for match in matches if getattr(match, "reason", "")),
            "This token was not eligible for the active analysis.",
        )
        return "excluded", reason
    return "unmatched", "No token-level evidence was recorded by the active source."


def _vad_observation(match: object) -> dict[str, object]:
    scores = getattr(match, "normalized_scores", None)
    original_scores = getattr(match, "original_scores", None)
    token_ids = tuple(getattr(match, "token_ids", ()))
    return {
        "match_id": str(getattr(match, "match_id", "")),
        "token_ids": token_ids,
        "match_method": _enum_value(getattr(match, "method", "")),
        "matched_term": getattr(match, "matched_term", None),
        "matched_lookup_form": getattr(match, "matched_lookup_form", None),
        "source_rows": tuple(getattr(match, "source_rows", ())),
        "expression_match": _expression_match(token_ids, getattr(match, "method", "")),
        "values": (
            {
                "valence": float(scores.valence),
                "arousal": float(scores.arousal),
                "dominance": float(scores.dominance),
            }
            if scores is not None
            else {}
        ),
        "original_values": (
            {
                "valence": float(original_scores.valence),
                "arousal": float(original_scores.arousal),
                "dominance": float(original_scores.dominance),
            }
            if original_scores is not None
            else {}
        ),
        "reason": str(getattr(match, "reason", "")),
    }


def _vad_evidence(result: object, token_id: str) -> dict[str, object]:
    matches = tuple(
        sorted(
            (
                match
                for match in getattr(result, "matches", ())
                if token_id in tuple(getattr(match, "token_ids", ()))
            ),
            key=_match_sort_key,
        )
    )
    status, reason = _match_status(matches)
    included = tuple(match for match in matches if getattr(match, "included", False))
    observations = tuple(_vad_observation(match) for match in included)
    return {
        "status": status,
        "reason": reason,
        "primary": observations[0] if observations else None,
        "observations": observations,
    }


def _audit_status(row: object | None) -> tuple[str, str]:
    if row is None:
        return "unavailable", "This module did not record evidence for the token."
    if bool(getattr(row, "included", False)):
        return "matched", str(getattr(row, "reason", "Matched by the completed analysis."))
    if bool(getattr(row, "eligible", False)):
        return "unmatched", str(getattr(row, "reason", "No entry in the active source."))
    return "excluded", str(
        getattr(row, "reason", "This token was not eligible for the active analysis.")
    )


def _audit_evidence(
    row: object | None,
    *,
    value_name: str,
    value_attribute: str,
) -> dict[str, object]:
    status, reason = _audit_status(row)
    if row is None:
        return {"status": status, "reason": reason, "primary": None, "observations": ()}
    group_token_ids = tuple(getattr(row, "match_group_token_ids", ())) or (
        str(getattr(row, "token_id", "")),
    )
    value = getattr(row, value_attribute, None)
    observation = None
    if bool(getattr(row, "included", False)) and value is not None:
        observation = {
            "token_ids": group_token_ids,
            "match_method": _enum_value(getattr(row, "match_method", "")),
            "matched_term": getattr(row, "matched_source_term", None),
            "matched_lookup_form": getattr(row, "matched_lookup_form", None),
            "source_rows": (
                (int(getattr(row, "source_row")),)
                if getattr(row, "source_row", None) is not None
                else ()
            ),
            "expression_match": _expression_match(
                group_token_ids,
                getattr(row, "match_method", ""),
            ) or bool(getattr(row, "source_is_multiword", False)),
            "values": {value_name: float(value)},
            "reason": reason,
        }
    observations = (observation,) if observation is not None else ()
    return {
        "status": status,
        "reason": reason,
        "primary": observation,
        "observations": observations,
    }


def _sensorimotor_observation(observation: object) -> dict[str, object]:
    token_ids = tuple(getattr(observation, "token_ids", ()))
    means = getattr(observation, "means", None)
    values = means.by_id() if means is not None and hasattr(means, "by_id") else {}
    return {
        "observation_id": str(getattr(observation, "observation_id", "")),
        "token_ids": token_ids,
        "match_method": _enum_value(getattr(observation, "match_method", "")),
        "matched_term": str(getattr(observation, "matched_source_term", "")),
        "matched_lookup_form": str(getattr(observation, "matched_lookup_form", "")),
        "source_rows": (int(getattr(observation, "source_row", 0)),),
        "expression_match": _expression_match(
            token_ids,
            getattr(observation, "match_method", ""),
        ) or bool(getattr(observation, "source_is_multiword", False)),
        "dominant_perceptual": str(getattr(observation, "dominant_perceptual", "")),
        "dominant_action": str(getattr(observation, "dominant_action", "")),
        "dominant_sensorimotor": str(
            getattr(observation, "dominant_sensorimotor", "")
        ),
        "values": {key: float(value) for key, value in values.items()},
        "perceptual_strength": float(
            getattr(observation, "minkowski3_perceptual_strength", 0.0)
        ),
        "action_strength": float(
            getattr(observation, "minkowski3_action_strength", 0.0)
        ),
        "sensorimotor_strength": float(
            getattr(observation, "minkowski3_sensorimotor_strength", 0.0)
        ),
        "reason": str(getattr(observation, "eligibility_note", "")),
        "context": str(getattr(observation, "context", "")),
    }


def _sensorimotor_evidence(result: object | None, token_id: str) -> dict[str, object]:
    if result is None:
        return {
            "status": "unavailable",
            "reason": "Sensorimotor imagery and embodiment was not enabled.",
            "primary": None,
            "observations": (),
        }
    observations = tuple(
        _sensorimotor_observation(observation)
        for observation in sorted(
            (
                observation
                for observation in getattr(result, "observations", ())
                if token_id in tuple(getattr(observation, "token_ids", ()))
            ),
            key=lambda observation: (
                -len(tuple(getattr(observation, "token_ids", ()))),
                int(getattr(observation, "token_position", 0)),
            ),
        )
    )
    if observations:
        return {
            "status": "matched",
            "reason": "Matched by the completed Lancaster analysis.",
            "primary": observations[0],
            "observations": observations,
        }
    unmatched = next(
        (
            row
            for row in getattr(result, "unmatched_tokens", ())
            if str(getattr(row, "token_id", "")) == token_id
        ),
        None,
    )
    if unmatched is not None:
        return {
            "status": "unmatched",
            "reason": str(getattr(unmatched, "reason", "No Lancaster entry.")),
            "primary": None,
            "observations": (),
        }
    return {
        "status": "excluded",
        "reason": "This token was not eligible for the sensorimotor analysis.",
        "primary": None,
        "observations": (),
    }


def _emotion_source(results: tuple[object, ...]) -> object | None:
    association = next(
        (
            result
            for result in results
            if str(getattr(getattr(result, "lexicon_metadata", None), "lexicon_id", ""))
            == "nrc_emotion_v0_92"
        ),
        None,
    )
    if association is not None:
        return association
    return next(
        (
            result
            for result in results
            if not _is_vad_result(result)
            and any(getattr(match, "associations", ()) for match in getattr(result, "matches", ()))
        ),
        None,
    )


def _emotion_evidence(result: object | None, token_id: str) -> dict[str, object]:
    if result is None:
        return {
            "status": "unavailable",
            "reason": "Emotional association analysis was not enabled.",
            "categories": (),
            "observations": (),
        }
    matches = tuple(
        sorted(
            (
                match
                for match in getattr(result, "matches", ())
                if token_id in tuple(getattr(match, "token_ids", ()))
            ),
            key=_match_sort_key,
        )
    )
    status, reason = _match_status(matches)
    observations = tuple(
        {
            "match_id": str(getattr(match, "match_id", "")),
            "token_ids": tuple(getattr(match, "token_ids", ())),
            "match_method": _enum_value(getattr(match, "method", "")),
            "matched_term": getattr(match, "matched_term", None),
            "matched_lookup_form": getattr(match, "matched_lookup_form", None),
            "source_rows": tuple(getattr(match, "source_rows", ())),
            "expression_match": _expression_match(
                getattr(match, "token_ids", ()), getattr(match, "method", "")
            ),
            "categories": tuple(getattr(match, "associations", ())),
            "reason": str(getattr(match, "reason", "")),
        }
        for match in matches
        if getattr(match, "included", False) and getattr(match, "associations", ())
    )
    categories = tuple(
        sorted(
            {
                category
                for observation in observations
                for category in observation["categories"]
            }
        )
    )
    return {
        "status": status,
        "reason": reason,
        "categories": categories,
        "primary": observations[0] if observations else None,
        "observations": observations,
    }


def _resource_source(result: object | None, *, fallback: str) -> dict[str, object] | None:
    if result is None:
        return None
    status = getattr(result, "resource_status", None)
    metadata = getattr(result, "lexicon_metadata", None)
    return {
        "id": str(
            getattr(metadata, "lexicon_id", "")
            or getattr(status, "resource_id", "")
            or fallback
        ),
        "label": str(
            getattr(metadata, "display_name", "")
            or getattr(status, "display_name", "")
            or fallback
        ),
        "version": str(getattr(metadata, "version", "")),
    }


def _layer_contracts(available: set[str]) -> tuple[dict[str, object], ...]:
    contracts = (
        ("valence", "Valence", "continuous", 0.0, 1.0, 0.5, "negative", "positive", "normalized 0–1"),
        ("arousal", "Arousal", "continuous", 0.0, 1.0, 0.5, "calm", "activated", "normalized 0–1"),
        ("dominance", "Dominance", "continuous", 0.0, 1.0, 0.5, "submissive", "dominant", "normalized 0–1"),
        ("concreteness", "Concreteness", "continuous", 1.0, 5.0, 3.0, "abstract", "concrete", "source 1–5"),
        ("frequency", "Frequency", "continuous", 1.0, 8.0, 4.5, "rare", "common", "SUBTLEX Zipf"),
        ("aoa", "Age of Acquisition", "continuous", 0.0, 25.0, 12.5, "earlier", "later", "mean years"),
        ("sensorimotor", "Sensorimotor Domain", "categorical", None, None, None, "", "", "Lancaster dominant domains"),
        ("emotion", "Emotional Association", "categorical", None, None, None, "", "", "NRC associations"),
        ("pos", "Part of Speech", "categorical", None, None, None, "", "", "model tag"),
    )
    return tuple(
        {
            "id": layer_id,
            "label": label,
            "kind": kind,
            "available": layer_id in available,
            "minimum": minimum,
            "maximum": maximum,
            "midpoint": midpoint,
            "low_label": low_label,
            "high_label": high_label,
            "scale": scale,
        }
        for (
            layer_id,
            label,
            kind,
            minimum,
            maximum,
            midpoint,
            low_label,
            high_label,
            scale,
        ) in contracts
    )


def sanitize_annotation_settings(
    settings: object,
    *,
    available_layers: Iterable[str],
    available_vad_sources: Iterable[str],
) -> dict[str, object]:
    """Return a durable, forward-compatible settings record."""

    available = set(available_layers)
    vad_sources = tuple(available_vad_sources)
    supplied = settings if isinstance(settings, dict) else {}
    supplied_layers = supplied.get("enabled_layers")
    if isinstance(supplied_layers, (list, tuple, set, frozenset)):
        enabled = [
            str(layer_id)
            for layer_id in supplied_layers
            if str(layer_id) in ALL_LAYER_IDS and str(layer_id) in available
        ]
    else:
        enabled = [
            layer_id for layer_id in ("valence", "pos") if layer_id in available
        ]
    active = str(supplied.get("active_lens", "valence"))
    enabled_continuous = [layer for layer in enabled if layer in CONTINUOUS_LAYER_IDS]
    if active not in enabled_continuous:
        active = enabled_continuous[0] if enabled_continuous else ""
    source = str(supplied.get("vad_source", ""))
    if source not in vad_sources:
        source = vad_sources[0] if vad_sources else ""
    return {
        "enabled_layers": enabled,
        "active_lens": active,
        "vad_source": source,
        "underline_unmatched": bool(supplied.get("underline_unmatched", False)),
    }


def build_interactive_annotation_payload(
    workspace: object,
    *,
    saved_settings: object = None,
    active_scope: LexicalScope = LexicalScope.STOPWORD_EXCLUDED,
) -> dict[str, object]:
    """Join completed token audits into a JSON-safe annotation view-model."""

    results = tuple(getattr(workspace, "results", ()))
    poem_document = getattr(workspace, "poem_document", None)
    tokens = tuple(
        getattr(poem_document, "tokens", ())
        or (getattr(results[0], "tokens", ()) if results else ())
    )
    vad_results = tuple(sorted((result for result in results if _is_vad_result(result)), key=lambda result: _source_priority(str(getattr(getattr(result, "lexicon_metadata", None), "lexicon_id", "")))))
    emotion_result = _emotion_source(results)

    vad_sources = tuple(
        {
            "id": str(result.lexicon_metadata.lexicon_id),
            "label": str(result.lexicon_metadata.display_name),
            "version": str(result.lexicon_metadata.version),
            "scale": "normalized 0–1",
            "original_scale": (
                f"{result.lexicon_metadata.source_scale_min:g}–"
                f"{result.lexicon_metadata.source_scale_max:g}"
            ),
        }
        for result in vad_results
    )
    vad_by_id = {source["id"]: result for source, result in zip(vad_sources, vad_results)}
    stopword_policy = next(
        (
            getattr(result, "stopword_policy", None)
            for result in vad_results
            if getattr(result, "stopword_policy", None) is not None
        ),
        None,
    )
    active_stopwords = tuple(getattr(stopword_policy, "active_words", ()) or ())

    optional_results = {
        "concreteness": getattr(workspace, "concreteness", None),
        "frequency": getattr(workspace, "frequency", None),
        "aoa": getattr(workspace, "aoa", None),
        "sensorimotor": getattr(workspace, "sensorimotor", None),
    }
    audits = {
        layer_id: {
            str(getattr(row, "token_id", "")): row
            for row in getattr(result, "token_audit", ())
        }
        for layer_id, result in optional_results.items()
        if result is not None and layer_id != "sensorimotor"
    }

    available = {"pos"}
    if vad_sources:
        available.update(("valence", "arousal", "dominance"))
    available.update(layer_id for layer_id, result in optional_results.items() if result is not None)
    if emotion_result is not None:
        available.add("emotion")

    settings = sanitize_annotation_settings(
        saved_settings,
        available_layers=available,
        available_vad_sources=(source["id"] for source in vad_sources),
    )
    default_settings = sanitize_annotation_settings(
        None,
        available_layers=available,
        available_vad_sources=(source["id"] for source in vad_sources),
    )

    token_rows: list[dict[str, object]] = []
    for token in sorted(tokens, key=lambda item: (item.character_start, item.character_end, item.token_position)):
        token_id = str(token.token_id)
        evidence: dict[str, object] = {
            "vad": {
                source_id: _vad_evidence(result, token_id)
                for source_id, result in vad_by_id.items()
            },
            "concreteness": _audit_evidence(
                audits.get("concreteness", {}).get(token_id),
                value_name="concreteness",
                value_attribute="rating",
            ) if optional_results["concreteness"] is not None else {
                "status": "unavailable", "reason": "Concreteness was not enabled.", "primary": None, "observations": ()
            },
            "frequency": _audit_evidence(
                audits.get("frequency", {}).get(token_id),
                value_name="frequency",
                value_attribute="zipf_value",
            ) if optional_results["frequency"] is not None else {
                "status": "unavailable", "reason": "Frequency and rarity was not enabled.", "primary": None, "observations": ()
            },
            "aoa": _audit_evidence(
                audits.get("aoa", {}).get(token_id),
                value_name="aoa",
                value_attribute="mean_age",
            ) if optional_results["aoa"] is not None else {
                "status": "unavailable", "reason": "Age of acquisition was not enabled.", "primary": None, "observations": ()
            },
            "sensorimotor": _sensorimotor_evidence(optional_results["sensorimotor"], token_id),
            "emotion": _emotion_evidence(emotion_result, token_id),
        }
        token_rows.append(
            {
                "token_id": token_id,
                "start": int(token.character_start),
                "end": int(token.character_end),
                "surface": str(token.surface_form),
                "normalized": str(token.normalized_form),
                "lemma": str(token.lemma),
                "part_of_speech": str(token.part_of_speech),
                "part_of_speech_label": _POS_LABELS.get(
                    str(token.part_of_speech), str(token.part_of_speech).title()
                ),
                "line_number": int(token.line_number),
                "stanza_number": int(token.stanza_number),
                "token_position": int(token.token_position),
                "is_lexical": bool(token.is_lexical),
                "lexicon_eligible": bool(is_lexicon_eligible(token)),
                "is_punctuation": bool(token.is_punctuation),
                "is_stopword": bool(token.is_stopword),
                "scope_eligibility": {
                    scope.value: token_is_in_scope(
                        token,
                        scope,
                        active_stopwords=active_stopwords,
                    )
                    for scope in LexicalScope
                },
                "context": str(token.context),
                "evidence": evidence,
            }
        )

    sources = {
        "vad": vad_sources,
        "concreteness": _resource_source(optional_results["concreteness"], fallback="Brysbaert concreteness"),
        "frequency": _resource_source(optional_results["frequency"], fallback="SUBTLEX-US"),
        "aoa": _resource_source(optional_results["aoa"], fallback="Kuperman AoA"),
        "sensorimotor": _resource_source(optional_results["sensorimotor"], fallback="Lancaster sensorimotor norms"),
        "emotion": _resource_source(emotion_result, fallback="NRC Emotion"),
    }
    document = getattr(workspace, "document")
    analysis_id = next(
        (str(getattr(result, "analysis_id", "")) for result in results if getattr(result, "analysis_id", "")),
        str(document.text_version_id),
    )
    return {
        "version": ANNOTATION_PAYLOAD_VERSION,
        "analysis_id": analysis_id,
        "text_version_id": str(document.text_version_id),
        "title": str(document.title),
        "original_text": str(document.original_text),
        "tokens": tuple(token_rows),
        "layers": _layer_contracts(available),
        "sources": sources,
        "settings": settings,
        "active_scope": active_scope.value,
        "default_settings": default_settings,
        "methodology": {
            "text": "Exact source text is preserved; annotations use stable token offsets from the completed analysis.",
            "phrases": "An expression match is attached to every participating token and identified as expression-level evidence.",
            "unmatched": "Unmatched underlining is relative to the active continuous lens and selected VAD source.",
            "sensorimotor": "Markers use the recorded dominant perceptual and action domains; full Lancaster dimensional strengths remain available in token details.",
        },
    }


__all__ = [
    "ALL_LAYER_IDS",
    "ANNOTATION_PAYLOAD_VERSION",
    "CATEGORICAL_LAYER_IDS",
    "CONTINUOUS_LAYER_IDS",
    "VAD_SOURCE_PRIORITY",
    "build_interactive_annotation_payload",
    "sanitize_annotation_settings",
]
