import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from versevad.analysis.phase2 import analyze_lexicon, compare_lexicons
from versevad.application import AnalysisRequest, WorkspaceAnalysis
from versevad.interactive_annotation import (
    build_interactive_annotation_payload,
    sanitize_annotation_settings,
)
from versevad.models import PhrasePolicy
from versevad.phase2_validation import (
    phase2_synthetic_emotion_lexicon,
    phase2_synthetic_vad_lexicon,
)
from versevad.preprocessing import PreparedPoemPreprocessor, create_text_document


_UI_SOURCE = (
    Path(__file__).parents[1]
    / "src"
    / "versevad"
    / "ui"
    / "interactive_annotation.py"
).read_text(encoding="utf-8")


def _ui_constant(name: str) -> str:
    tree = ast.parse(_UI_SOURCE)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    )
    return ast.literal_eval(assignment.value)


def _workspace(preprocessor) -> WorkspaceAnalysis:
    document = create_text_document(
        "interactive-annotation",
        "Interactive annotation",
        "Dark night, joy.\n\nUnknown bright.",
    )
    poem_document = preprocessor.process_document(document)
    prepared = PreparedPoemPreprocessor(poem_document)
    results = (
        analyze_lexicon(
            document,
            phase2_synthetic_vad_lexicon(),
            prepared,
            phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
        ),
        analyze_lexicon(
            document,
            phase2_synthetic_emotion_lexicon(),
            prepared,
            phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
        ),
    )
    request = AnalysisRequest(
        project_name="",
        title=document.title,
        original_text=document.original_text,
        lexicon_ids=tuple(result.lexicon_metadata.lexicon_id for result in results),
        phrase_policy=PhrasePolicy.PHRASE_PREFERRED,
    )
    return WorkspaceAnalysis(
        request,
        document,
        results,
        compare_lexicons(results),
        poem_document,
    )


def test_payload_preserves_exact_source_offsets_and_repeated_occurrence_ids(
    preprocessor,
) -> None:
    workspace = _workspace(preprocessor)
    payload = build_interactive_annotation_payload(workspace)

    assert payload["original_text"] == workspace.document.original_text
    assert len({token["token_id"] for token in payload["tokens"]}) == len(
        payload["tokens"]
    )
    for token in payload["tokens"]:
        assert (
            payload["original_text"][token["start"] : token["end"]]
            == token["surface"]
        )


def test_phrase_match_is_attached_to_each_member_without_becoming_unigram_data(
    preprocessor,
) -> None:
    payload = build_interactive_annotation_payload(_workspace(preprocessor))
    source = payload["settings"]["vad_source"]
    dark, night = payload["tokens"][:2]

    for token in (dark, night):
        evidence = token["evidence"]["vad"][source]
        assert evidence["status"] == "matched"
        assert evidence["primary"]["expression_match"] is True
        assert evidence["primary"]["matched_term"] == "dark night"
        assert len(evidence["primary"]["token_ids"]) == 2
        assert evidence["primary"]["values"]["valence"] == 0.125


def test_vad_unmatched_state_is_shared_by_dimensions_within_active_source(
    preprocessor,
) -> None:
    payload = build_interactive_annotation_payload(_workspace(preprocessor))
    source = payload["settings"]["vad_source"]
    unknown = next(token for token in payload["tokens"] if token["surface"] == "Unknown")
    evidence = unknown["evidence"]["vad"][source]

    assert evidence["status"] == "unmatched"
    assert evidence["primary"] is None
    assert evidence["observations"] == ()


def test_emotional_associations_reuse_completed_token_evidence(preprocessor) -> None:
    payload = build_interactive_annotation_payload(_workspace(preprocessor))
    joy = next(token for token in payload["tokens"] if token["surface"] == "joy")

    assert joy["evidence"]["emotion"]["status"] == "matched"
    assert joy["evidence"]["emotion"]["categories"] == ("joy", "positive")


def test_vad_source_defaults_to_largest_supported_source(preprocessor) -> None:
    base = _workspace(preprocessor)
    vad_result = base.results[0]
    renamed = []
    for lexicon_id, display_name in (
        ("warriner_vad_2013", "Warriner"),
        ("nrc_vad_v1", "NRC v1"),
        ("nrc_vad_v2_1", "NRC v2.1"),
    ):
        renamed.append(
            replace(
                vad_result,
                lexicon_metadata=replace(
                    vad_result.lexicon_metadata,
                    lexicon_id=lexicon_id,
                    display_name=display_name,
                ),
            )
        )
    workspace = SimpleNamespace(
        document=base.document,
        poem_document=base.poem_document,
        results=tuple(reversed(renamed)),
        concreteness=None,
        frequency=None,
        aoa=None,
        sensorimotor=None,
    )

    payload = build_interactive_annotation_payload(workspace)

    assert [source["id"] for source in payload["sources"]["vad"]] == [
        "nrc_vad_v2_1",
        "nrc_vad_v1",
        "warriner_vad_2013",
    ]
    assert payload["settings"]["vad_source"] == "nrc_vad_v2_1"
    assert payload["default_settings"] == payload["settings"]


def test_settings_allow_clear_all_and_drop_unavailable_layers() -> None:
    settings = sanitize_annotation_settings(
        {
            "enabled_layers": [],
            "active_lens": "frequency",
            "vad_source": "missing",
            "underline_unmatched": True,
        },
        available_layers=("valence", "pos"),
        available_vad_sources=("nrc_vad_v2_1",),
    )

    assert settings == {
        "enabled_layers": [],
        "active_lens": "",
        "vad_source": "nrc_vad_v2_1",
        "underline_unmatched": True,
    }


def test_client_component_keeps_hover_and_selection_in_the_browser() -> None:
    javascript = _ui_constant("_COMPONENT_JS")

    assert 'addEventListener("pointerenter"' in javascript
    assert 'addEventListener("pointerleave"' in javascript
    assert 'event.key === "Enter"' in javascript
    assert 'event.key === "Escape"' in javascript
    assert "closePanel(root, payload); node.focus()" not in javascript
    assert 'setStateValue("settings"' in javascript
    assert "payload.default_settings" in javascript
    assert "sourceMeta = sourceFor(payload, layer.id, settings)" in javascript
    assert "current.vadSource" not in javascript
    assert "source.slice(start, end)" in javascript
    assert "innerHTML" not in javascript


def test_client_component_uses_streamlit_theme_tokens_and_responsive_layout() -> None:
    css = _ui_constant("_COMPONENT_CSS")

    assert "--st-background-color" in css
    assert "--st-secondary-background-color" in css
    assert "--st-text-color" in css
    assert "--st-primary-color" in css
    assert "--vv-theme-background" in css
    assert ".vv-panel-empty[hidden], .vv-panel-content[hidden]" in css
    assert "display: none !important" in css
    assert "@media (max-width: 860px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
