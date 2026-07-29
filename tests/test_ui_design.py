from pathlib import Path

import pandas as pd

import versevad.ui.design as design_services
from versevad.ui.design import (
    CLASSIC_TOKENS,
    CRIMSON_TOKENS,
    DARK_TOKENS,
    FOREST_TOKENS,
    LAVENDER_TOKENS,
    MODULE_PRESETS,
    OCEAN_TOKENS,
    THEME_TOKENS,
    collapse_control_html,
    preset_widget_state,
    render_dataframe,
    stylesheet_for,
)
from versevad.ui.preferences import (
    AppearanceMode,
    UiPreferences,
    load_preferences,
    save_preferences,
)


def test_ui_preferences_default_and_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "private" / "ui_preferences.json"
    assert load_preferences(path).appearance is AppearanceMode.CLASSIC

    saved = save_preferences(
        UiPreferences(appearance=AppearanceMode.LAVENDER),
        path,
    )
    assert saved == path
    assert load_preferences(path).appearance is AppearanceMode.LAVENDER


def test_ui_preferences_migrate_removed_appearances(tmp_path: Path) -> None:
    path = tmp_path / "ui_preferences.json"
    for legacy in ("Light", "System"):
        path.write_text(
            f'{{"version": 1, "appearance": "{legacy}"}}',
            encoding="utf-8",
        )
        preferences = load_preferences(path)
        assert preferences.appearance is AppearanceMode.CLASSIC
        assert preferences.version == 2


def test_malformed_ui_preferences_fail_safely(tmp_path: Path) -> None:
    path = tmp_path / "ui_preferences.json"
    path.write_text("{not valid", encoding="utf-8")
    assert load_preferences(path) == UiPreferences()
    path.write_text('{"appearance": []}', encoding="utf-8")
    assert load_preferences(path) == UiPreferences()


def test_dataframe_renderer_pins_leftmost_data_column(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_dataframe(data, **kwargs):
        captured["data"] = data
        captured.update(kwargs)

    monkeypatch.setattr(design_services.st, "dataframe", fake_dataframe)
    frame = pd.DataFrame({"Meaning": ["Valence"], "Value": [0.5]})

    render_dataframe(frame, hide_index=True, width="stretch")

    assert captured["data"] is frame
    assert captured["hide_index"] is True
    assert captured["width"] == "stretch"
    assert captured["column_config"]["Meaning"]["pinned"] is True


def test_stylesheet_uses_semantic_tokens_and_accessibility_modes() -> None:
    sheets = {
        appearance: stylesheet_for(appearance)
        for appearance in AppearanceMode
    }

    for sheet in sheets.values():
        assert "--color-background" in sheet
        assert "--color-text-primary" in sheet
        assert "--color-focus" in sheet
        assert "prefers-reduced-motion" in sheet
        assert "focus-visible" in sheet
        assert '[data-testid="stTextAreaRootElement"]' in sheet
        assert '[data-testid="stTextAreaRootElement"]:focus-within' in sheet
        assert (
            '[data-testid="stTextAreaRootElement"] textarea:focus-visible'
            in sheet
        )
        assert '[data-testid="stTextInputRootElement"]' in sheet
        assert 'button[data-testid^="stBaseButton-primary"]' in sheet
        assert '[data-testid="stFormSubmitButton"] button' in sheet
        assert '[data-testid="stDownloadButton"] button' in sheet
        assert '[data-testid^="stBaseButton-secondary"]' in sheet
        assert '[data-testid^="stBaseButton-tertiary"]' in sheet
        assert "[kind^=\"primary\"]" in sheet
        assert "button:disabled" in sheet
        assert '[aria-label="Project section"]' in sheet
        assert '[data-testid="stSidebarCollapseButton"]' in sheet
        assert '[data-testid="stSidebarCollapsedControl"]' in sheet
        assert 'button[data-testid="stExpandSidebarButton"]' in sheet
        assert '[data-testid="stSidebar"] [data-testid="stAlert"] *' in sheet
        assert '[data-testid="stSidebar"] p' in sheet
        assert ".versevad-collapse-control" in sheet
        assert ".versevad-collapse-button" in sheet
        assert ".versevad-collapse-glyph" in sheet
        assert (
            "background: var(--color-button-secondary-background) !important"
            in sheet
        )
        assert '[class*="st-key-versevad_header_icon__"]' in sheet
        assert 'button > div > div[aria-hidden="true"]' in sheet
        assert '[data-testid="stIconMaterial"]' in sheet
        assert "transform: translateX(.09375rem)" in sheet
        assert "width: 2.25rem" in sheet
        assert '[data-testid="stMetricValue"] > div' in sheet
        assert "container-type: inline-size" in sheet
        assert "font-size: clamp(1rem, 8cqi, 2.25rem)" in sheet
        assert "text-overflow: clip" in sheet
        assert "overflow-wrap: anywhere" in sheet
        assert "-webkit-text-fill-color" in sheet
        assert "caret-color" in sheet
        assert "::placeholder" in sheet
        assert '[data-testid="stFileUploaderDropzone"]' in sheet
        assert '[data-testid="stSelectbox"] [role="group"]' in sheet
        assert '[data-baseweb="tag"]' in sheet
        assert '[data-baseweb="popover"]' in sheet
        assert '[data-baseweb="tooltip"]' in sheet
        assert '[data-testid="stTooltipContent"]' in sheet
        assert '[role="listbox"]' in sheet
        assert "prefers-color-scheme: dark" not in sheet
        assert (
            "[class*=\"st-key-versevad_header_icon__\"] button:hover"
            in sheet
        )
    assert len(set(sheets.values())) == len(AppearanceMode)
    assert tuple(mode.value for mode in AppearanceMode) == (
        "Classic",
        "Dark",
        "Lavender",
        "Ocean",
        "Crimson",
        "Forest",
    )
    assert THEME_TOKENS == {
        AppearanceMode.CLASSIC: CLASSIC_TOKENS,
        AppearanceMode.DARK: DARK_TOKENS,
        AppearanceMode.LAVENDER: LAVENDER_TOKENS,
        AppearanceMode.OCEAN: OCEAN_TOKENS,
        AppearanceMode.CRIMSON: CRIMSON_TOKENS,
        AppearanceMode.FOREST: FOREST_TOKENS,
    }


def test_collapse_control_is_accessible_and_client_side() -> None:
    markup = collapse_control_html("PoetryID & Form", "report_poetry_id")

    assert 'aria-label="Collapse PoetryID &amp; Form"' in markup
    assert 'title="Collapse PoetryID &amp; Form"' in markup
    assert 'data-collapse-id="report_poetry_id"' in markup
    assert 'class="versevad-collapse-glyph"' in markup
    assert "&#8593;" in markup
    assert "<svg" not in markup
    assert 'button.closest("details")' in markup
    assert 'closest(\'[data-testid="stExpander"]\')' in markup
    assert "details.open = false" in markup


def _relative_luminance(value: str) -> float:
    channels = [
        int(value[index : index + 2], 16) / 255
        for index in (1, 3, 5)
    ]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_primary_text_and_focus_tokens_meet_contrast_expectations() -> None:
    for tokens in THEME_TOKENS.values():
        for surface in (
            "background",
            "surface",
            "surface-raised",
            "surface-muted",
        ):
            assert _contrast(tokens["text-primary"], tokens[surface]) >= 7
            assert _contrast(tokens["text-secondary"], tokens[surface]) >= 4.5
        for surface in ("background", "surface", "surface-raised"):
            assert _contrast(tokens["focus"], tokens[surface]) >= 3
            assert _contrast(tokens["accent"], tokens[surface]) >= 4.5
        assert _contrast(tokens["accent-strong"], tokens["accent-soft"]) >= 4.5
        assert (
            _contrast(tokens["text-inverse"], tokens["accent-strong"]) >= 4.5
        )
        assert _contrast(tokens["text-inverse"], tokens["accent"]) >= 4.5
        assert _contrast(tokens["success"], tokens["success-soft"]) >= 4.5
        assert _contrast(tokens["warning"], tokens["warning-soft"]) >= 4.5


def test_all_button_states_meet_text_contrast_expectations() -> None:
    for tokens in THEME_TOKENS.values():
        assert (
            _contrast(
                tokens["button-primary-text"],
                tokens["button-primary-background"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-primary-text"],
                tokens["button-primary-hover"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-secondary-text"],
                tokens["button-secondary-background"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-secondary-text"],
                tokens["button-secondary-hover"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-tertiary-text"],
                tokens["background"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-tertiary-text"],
                tokens["surface"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-tertiary-text"],
                tokens["accent-soft"],
            )
            >= 4.5
        )
        assert (
            _contrast(
                tokens["button-disabled-text"],
                tokens["button-disabled-background"],
            )
            >= 4.5
        )


def test_presets_change_only_module_selection_not_advanced_settings() -> None:
    state = preset_widget_state(
        "Literary",
        available_lexicon_ids=(
            "warriner_vad_2013",
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        ),
    )
    assert state["include_poetry_id"] is True
    assert state["include_meter"] is False
    assert "frequency_rare_threshold" not in state
    assert "poetry_id_low_threshold" not in state
    assert preset_widget_state(
        "Custom",
        available_lexicon_ids=(),
    ) == {}
    assert set(MODULE_PRESETS) == {
        "Essential",
        "Literary",
        "Sound and Form",
        "Complete",
        "Custom",
    }
