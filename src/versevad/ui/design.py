"""Shared Stage 13 visual system and reusable Streamlit presentation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Literal, Mapping, Sequence

import altair as alt
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from versevad import __version__
from versevad.deployment import cloud_deployment_enabled
from versevad.ui.preferences import (
    AppearanceMode,
    UiPreferences,
    load_preferences,
    save_appearance,
)


WORKSPACES = (
    "Single Poem",
    "Project / Corpus",
    "Other Text",
    "Lexicon Explorer",
)

LIGHT_TOKENS = {
    "background": "#f6f3ed",
    "surface": "#fffdf9",
    "surface-raised": "#ffffff",
    "surface-muted": "#eee9df",
    "text-primary": "#17242d",
    "text-secondary": "#59656d",
    "text-inverse": "#ffffff",
    "button-primary-background": "#5f2619",
    "button-primary-hover": "#7a3524",
    "button-primary-text": "#ffffff",
    "button-secondary-background": "#fffdf9",
    "button-secondary-hover": "#f2e6df",
    "button-secondary-text": "#17242d",
    "button-tertiary-text": "#5f2619",
    "button-disabled-background": "#eee9df",
    "button-disabled-text": "#59656d",
    "border": "#d9d3c8",
    "border-strong": "#a9a197",
    "accent": "#7a3524",
    "accent-strong": "#5f2619",
    "accent-soft": "#f2e6df",
    "success": "#2f654a",
    "success-soft": "#e6f0e9",
    "warning": "#866219",
    "warning-soft": "#f6eed8",
    "danger": "#943c3c",
    "danger-soft": "#f7e6e4",
    "info": "#345f72",
    "info-soft": "#e5eff3",
    "focus": "#176b8a",
    "shadow": "rgba(32, 28, 24, 0.10)",
    "chart-grid": "#d8d2c8",
    "chart-label": "#34434c",
}

DARK_TOKENS = {
    "background": "#11171b",
    "surface": "#182126",
    "surface-raised": "#202a30",
    "surface-muted": "#28343b",
    "text-primary": "#f3f0e9",
    "text-secondary": "#b8c1c5",
    "text-inverse": "#11171b",
    "button-primary-background": "#efaa8f",
    "button-primary-hover": "#d58a6d",
    "button-primary-text": "#11171b",
    "button-secondary-background": "#202a30",
    "button-secondary-hover": "#28343b",
    "button-secondary-text": "#f3f0e9",
    "button-tertiary-text": "#efaa8f",
    "button-disabled-background": "#28343b",
    "button-disabled-text": "#b8c1c5",
    "border": "#3b484f",
    "border-strong": "#65737a",
    "accent": "#d58a6d",
    "accent-strong": "#efaa8f",
    "accent-soft": "#3d2a25",
    "success": "#8fc8a6",
    "success-soft": "#20372b",
    "warning": "#e1c37a",
    "warning-soft": "#3c3421",
    "danger": "#ee9994",
    "danger-soft": "#422827",
    "info": "#91c5d7",
    "info-soft": "#213740",
    "focus": "#76c8e6",
    "shadow": "rgba(0, 0, 0, 0.30)",
    "chart-grid": "#46545b",
    "chart-label": "#dce3e5",
}

PUBLICATION_CHART_COLORS = (
    "#9f4528",
    "#c77d3f",
    "#326b78",
    "#4f7658",
    "#705d8f",
)


def publication_chart(chart: alt.Chart) -> alt.Chart:
    """Apply a stable light publication treatment independent of UI appearance."""

    return (
        chart.configure(background="#fffdf9")
        .configure_view(stroke="#d9d3c8")
        .configure_axis(
            domainColor="#a9a197",
            gridColor="#e3ded5",
            labelColor="#34434c",
            titleColor="#17242d",
        )
        .configure_legend(
            labelColor="#34434c",
            titleColor="#17242d",
        )
        .configure_title(color="#17242d")
    )


@dataclass(frozen=True)
class ModulePreset:
    label: str
    description: str
    lexicon_ids: tuple[str, ...]
    modules: tuple[str, ...]


MODULE_PRESETS = {
    "Essential": ModulePreset(
        label="Essential",
        description="VAD, emotion association, and emotion intensity.",
        lexicon_ids=(
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        ),
        modules=(),
    ),
    "Literary": ModulePreset(
        label="Literary",
        description="Core affective evidence plus lexical character and structure.",
        lexicon_ids=(
            "warriner_vad_2013",
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        ),
        modules=(
            "include_concreteness",
            "include_frequency",
            "include_aoa",
            "include_lexical_style",
            "include_poetry_id",
        ),
    ),
    "Sound and Form": ModulePreset(
        label="Sound and Form",
        description="Pronunciation, meter, rhyme/sound, and structural measures.",
        lexicon_ids=(),
        modules=(
            "include_pronunciation",
            "include_meter",
            "include_phonology",
            "include_inherited_form",
            "include_lexical_style",
        ),
    ),
    "Complete": ModulePreset(
        label="Complete",
        description="Every installed analytical module.",
        lexicon_ids=(
            "warriner_vad_2013",
            "nrc_vad_v1",
            "nrc_vad_v2_1",
            "nrc_emotion_v0_92",
            "nrc_emotion_intensity_v1",
        ),
        modules=(
            "include_concreteness",
            "include_frequency",
            "include_aoa",
            "include_lexical_style",
            "include_poetry_id",
            "include_pronunciation",
            "include_meter",
            "include_phonology",
            "include_inherited_form",
        ),
    ),
    "Custom": ModulePreset(
        label="Custom",
        description="Keep the current manual module selection.",
        lexicon_ids=(),
        modules=(),
    ),
}

_OPTIONAL_MODULE_KEYS = frozenset(
    key
    for preset in MODULE_PRESETS.values()
    for key in preset.modules
)


def preset_widget_state(
    preset_name: str,
    *,
    available_lexicon_ids: Sequence[str],
) -> dict[str, object]:
    """Return only module-selection state; advanced settings are never touched."""

    preset = MODULE_PRESETS[preset_name]
    if preset_name == "Custom":
        return {}
    available = set(available_lexicon_ids)
    selected = [item for item in preset.lexicon_ids if item in available]
    state: dict[str, object] = {"selected_lexicons": selected}
    enabled = set(preset.modules)
    state.update({key: key in enabled for key in _OPTIONAL_MODULE_KEYS})
    return state


def _token_declarations(tokens: Mapping[str, str]) -> str:
    return "\n".join(f"      --color-{name}: {value};" for name, value in tokens.items())


def stylesheet_for(mode: AppearanceMode | str) -> str:
    appearance = AppearanceMode(mode)
    base = DARK_TOKENS if appearance is AppearanceMode.DARK else LIGHT_TOKENS
    system_override = ""
    if appearance is AppearanceMode.SYSTEM:
        system_override = f"""
    @media (prefers-color-scheme: dark) {{
      :root {{
{_token_declarations(DARK_TOKENS)}
        color-scheme: dark;
      }}
    }}
"""
    return f"""
    <style>
    :root {{
{_token_declarations(base)}
      color-scheme: {"dark" if appearance is AppearanceMode.DARK else "light"};
      --font-interface: Inter, "Segoe UI", Arial, sans-serif;
      --font-literary: Georgia, "Times New Roman", serif;
      --space-1: .25rem;
      --space-2: .5rem;
      --space-3: .75rem;
      --space-4: 1rem;
      --space-6: 1.5rem;
      --space-8: 2rem;
      --radius-small: .35rem;
      --radius-medium: .7rem;
      --radius-large: 1rem;
      --transition-fast: 120ms ease;
    }}
{system_override}
    html, body, [class*="css"] {{
      font-family: var(--font-interface);
      color: var(--color-text-primary);
    }}
    html {{
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
    }}
    .stApp {{
      background: var(--color-background);
      color: var(--color-text-primary);
      min-width: 0;
      transition: background-color var(--transition-fast), color var(--transition-fast);
    }}
    .main .block-container {{
      max-width: 92rem;
      min-width: 0;
      padding-top: 1rem;
      padding-bottom: 4rem;
      width: 100%;
    }}
    h1, h2, h3, h4 {{
      color: var(--color-text-primary);
      letter-spacing: -.012em;
    }}
    h1, .versevad-literary {{
      font-family: var(--font-literary);
    }}
    p, label, [data-testid="stCaptionContainer"] {{
      color: var(--color-text-secondary);
      overflow-wrap: anywhere;
    }}
    [data-testid="stTextAreaRootElement"],
    [data-testid="stTextInputRootElement"] {{
      background: var(--color-surface) !important;
      border-color: var(--color-border) !important;
    }}
    [data-testid="stTextAreaRootElement"] textarea,
    [data-testid="stTextInputRootElement"] input {{
      caret-color: var(--color-accent);
      color: var(--color-text-primary) !important;
      -webkit-text-fill-color: var(--color-text-primary) !important;
    }}
    [data-testid="stTextAreaRootElement"] textarea::placeholder,
    [data-testid="stTextInputRootElement"] input::placeholder {{
      color: var(--color-text-secondary) !important;
      opacity: 1;
    }}
    /*
     * Streamlit uses distinct test IDs for ordinary, form-submit, and
     * download buttons, and some releases suffix the base-button variant
     * (for example, primaryFormSubmit). Keep every visible label and icon on
     * the same explicit, contrast-tested foreground instead of allowing a
     * nested Markdown paragraph to restore Streamlit's theme default.
     */
    [data-testid="stButton"] button,
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button,
    [data-testid^="stBaseButton-secondary"] {{
      background: var(--color-button-secondary-background) !important;
      border-color: var(--color-border-strong) !important;
      color: var(--color-button-secondary-text) !important;
      -webkit-text-fill-color: var(--color-button-secondary-text) !important;
      opacity: 1;
    }}
    [data-testid="stButton"] button:hover,
    [data-testid="stFormSubmitButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover,
    [data-testid^="stBaseButton-secondary"]:hover {{
      background: var(--color-button-secondary-hover) !important;
      border-color: var(--color-accent) !important;
      color: var(--color-button-secondary-text) !important;
      -webkit-text-fill-color: var(--color-button-secondary-text) !important;
    }}
    button[data-testid^="stBaseButton-primary"],
    [data-testid="stButton"] button[data-testid^="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] button[data-testid^="stBaseButton-primary"],
    [data-testid="stDownloadButton"] button[data-testid^="stBaseButton-primary"],
    [data-testid="stButton"] button[kind^="primary"],
    [data-testid="stFormSubmitButton"] button[kind^="primary"],
    [data-testid="stDownloadButton"] button[kind^="primary"] {{
      background: var(--color-button-primary-background) !important;
      border-color: var(--color-button-primary-background) !important;
      color: var(--color-button-primary-text) !important;
      -webkit-text-fill-color: var(--color-button-primary-text) !important;
      opacity: 1;
    }}
    button[data-testid^="stBaseButton-primary"]:hover,
    [data-testid="stButton"] button[data-testid^="stBaseButton-primary"]:hover,
    [data-testid="stFormSubmitButton"] button[data-testid^="stBaseButton-primary"]:hover,
    [data-testid="stDownloadButton"] button[data-testid^="stBaseButton-primary"]:hover,
    [data-testid="stButton"] button[kind^="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind^="primary"]:hover,
    [data-testid="stDownloadButton"] button[kind^="primary"]:hover {{
      background: var(--color-button-primary-hover) !important;
      border-color: var(--color-button-primary-hover) !important;
      color: var(--color-button-primary-text) !important;
      -webkit-text-fill-color: var(--color-button-primary-text) !important;
    }}
    button[data-testid^="stBaseButton-tertiary"],
    [data-testid="stButton"] button[data-testid^="stBaseButton-tertiary"],
    [data-testid="stFormSubmitButton"] button[data-testid^="stBaseButton-tertiary"],
    [data-testid="stDownloadButton"] button[data-testid^="stBaseButton-tertiary"],
    [data-testid="stButton"] button[kind^="tertiary"],
    [data-testid="stFormSubmitButton"] button[kind^="tertiary"],
    [data-testid="stDownloadButton"] button[kind^="tertiary"] {{
      background: transparent !important;
      border-color: transparent !important;
      color: var(--color-button-tertiary-text) !important;
      -webkit-text-fill-color: var(--color-button-tertiary-text) !important;
      opacity: 1;
    }}
    button[data-testid^="stBaseButton-tertiary"]:hover,
    [data-testid="stButton"] button[data-testid^="stBaseButton-tertiary"]:hover,
    [data-testid="stFormSubmitButton"] button[data-testid^="stBaseButton-tertiary"]:hover,
    [data-testid="stDownloadButton"] button[data-testid^="stBaseButton-tertiary"]:hover,
    [data-testid="stButton"] button[kind^="tertiary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind^="tertiary"]:hover,
    [data-testid="stDownloadButton"] button[kind^="tertiary"]:hover {{
      background: var(--color-accent-soft) !important;
      border-color: var(--color-accent) !important;
      color: var(--color-button-tertiary-text) !important;
      -webkit-text-fill-color: var(--color-button-tertiary-text) !important;
    }}
    [data-testid="stButton"] button *,
    [data-testid="stFormSubmitButton"] button *,
    [data-testid="stDownloadButton"] button *,
    [data-testid^="stBaseButton-"] * {{
      color: inherit !important;
      -webkit-text-fill-color: inherit !important;
    }}
    [data-testid="stButton"] button svg,
    [data-testid="stFormSubmitButton"] button svg,
    [data-testid="stDownloadButton"] button svg,
    [data-testid^="stBaseButton-"] svg {{
      fill: currentColor !important;
      stroke: currentColor !important;
    }}
    [data-testid="stButton"] button:disabled,
    [data-testid="stFormSubmitButton"] button:disabled,
    [data-testid="stDownloadButton"] button:disabled,
    [data-testid^="stBaseButton-"]:disabled {{
      background: var(--color-button-disabled-background) !important;
      border-color: var(--color-border-strong) !important;
      color: var(--color-button-disabled-text) !important;
      -webkit-text-fill-color: var(--color-button-disabled-text) !important;
      cursor: not-allowed;
      opacity: 1 !important;
    }}
    a {{
      color: var(--color-accent);
    }}
    [data-testid="stSidebar"] {{
      background: var(--color-surface-muted);
      border-right: 1px solid var(--color-border);
      color: var(--color-text-primary);
    }}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] strong,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
      color: var(--color-text-primary) !important;
      -webkit-text-fill-color: var(--color-text-primary) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stAlert"] *,
    [data-testid="stSidebar"] [data-testid="stNotification"] * {{
      color: var(--color-text-primary) !important;
      -webkit-text-fill-color: var(--color-text-primary) !important;
    }}
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] * {{
      color: var(--color-text-primary) !important;
      -webkit-text-fill-color: var(--color-text-primary) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button *,
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button * {{
      color: inherit !important;
      -webkit-text-fill-color: inherit !important;
    }}
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"] {{
      color: var(--color-text-primary) !important;
    }}
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] button {{
      background: var(--color-surface-raised) !important;
      border: 1px solid var(--color-border-strong) !important;
      color: var(--color-text-primary) !important;
      min-height: 2.5rem;
      min-width: 2.5rem;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover {{
      background: var(--color-accent-soft) !important;
      border-color: var(--color-accent) !important;
      color: var(--color-accent-strong) !important;
    }}
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg {{
      fill: currentColor !important;
      stroke: currentColor !important;
    }}
    [data-testid="stHeader"] {{
      background: transparent;
    }}
    [data-testid="stMetric"] {{
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-medium);
      padding: .75rem .9rem;
      box-shadow: none;
      font-variant-numeric: tabular-nums;
    }}
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
      color: var(--color-text-primary);
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
      border: 1px solid var(--color-border);
      border-radius: var(--radius-small);
      max-width: 100%;
      overflow: auto;
      -webkit-overflow-scrolling: touch;
    }}
    [data-testid="stExpander"], [data-testid="stForm"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
      background: var(--color-surface);
      border-color: var(--color-border) !important;
      border-radius: var(--radius-medium);
    }}
    [data-baseweb="tab-list"] {{
      gap: var(--space-2);
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
    }}
    [data-baseweb="tab"] {{
      color: var(--color-text-secondary);
      white-space: nowrap;
    }}
    [aria-selected="true"][data-baseweb="tab"] {{
      color: var(--color-accent-strong);
    }}
    [role="radiogroup"][aria-label="Workspace"] button {{
      background: var(--color-surface) !important;
      border-color: var(--color-border) !important;
      color: var(--color-text-secondary) !important;
    }}
    [role="radiogroup"][aria-label="Workspace"] button p {{
      color: inherit !important;
    }}
    [role="radiogroup"][aria-label="Workspace"] button[data-selected="true"] {{
      background: var(--color-accent-soft) !important;
      border-color: var(--color-accent) !important;
      color: var(--color-accent-strong) !important;
    }}
    [role="radiogroup"][aria-label="Project section"] {{
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      width: 100%;
    }}
    [role="radiogroup"][aria-label="Project section"] button {{
      background: var(--color-surface) !important;
      border-color: var(--color-border) !important;
      color: var(--color-text-secondary) !important;
      flex: 1 1 9rem;
      min-height: 2.6rem;
      white-space: normal;
    }}
    [role="radiogroup"][aria-label="Project section"] button p {{
      color: inherit !important;
    }}
    [role="radiogroup"][aria-label="Project section"] button[data-selected="true"] {{
      background: var(--color-accent-soft) !important;
      border-color: var(--color-accent) !important;
      color: var(--color-accent-strong) !important;
    }}
    button:focus-visible, input:focus-visible,
    [role="button"]:focus-visible, [role="tab"]:focus-visible {{
      outline: 3px solid var(--color-focus) !important;
      outline-offset: 2px !important;
    }}
    [data-testid="stTextAreaRootElement"]:focus-within {{
      border-radius: var(--radius-small);
      outline: 3px solid var(--color-focus) !important;
      outline-offset: 2px !important;
    }}
    [data-testid="stTextAreaRootElement"] textarea:focus-visible {{
      outline: none !important;
    }}
    .versevad-shell {{
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-large);
      padding: .7rem 1rem;
      box-shadow: 0 .35rem 1rem var(--color-shadow);
      margin-bottom: var(--space-4);
    }}
    .st-key-versevad_global_header {{
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-large);
      box-shadow: 0 .35rem 1rem var(--color-shadow);
      margin-bottom: var(--space-4);
      padding: .55rem .8rem;
      position: -webkit-sticky;
      position: sticky;
      top: .5rem;
      z-index: 900;
    }}
    .versevad-wordmark {{
      color: var(--color-text-primary);
      font-family: var(--font-literary);
      font-size: 1.55rem;
      font-weight: 700;
      line-height: 1.05;
      white-space: nowrap;
    }}
    .versevad-platform {{
      color: var(--color-text-secondary);
      font-size: .73rem;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .versevad-kicker {{
      color: var(--color-accent);
      font-size: .75rem;
      font-weight: 700;
      letter-spacing: .11em;
      margin-bottom: -.55rem;
      text-transform: uppercase;
    }}
    .versevad-workspace-header {{
      border-bottom: 1px solid var(--color-border);
      margin-bottom: var(--space-6);
      padding: .4rem 0 var(--space-4);
    }}
    .versevad-workspace-header h1 {{
      margin: 0 0 var(--space-2);
    }}
    .versevad-workspace-header p {{
      font-size: 1.02rem;
      margin: 0;
      max-width: 72ch;
    }}
    .versevad-empty {{
      background: var(--color-surface);
      border: 1px dashed var(--color-border-strong);
      border-radius: var(--radius-large);
      padding: var(--space-8);
      text-align: center;
    }}
    .versevad-empty h3 {{
      margin-top: 0;
    }}
    .versevad-callout {{
      background: var(--color-info-soft);
      border-left: 4px solid var(--color-info);
      border-radius: var(--radius-small);
      color: var(--color-text-primary);
      padding: .8rem 1rem;
      margin: .5rem 0 1rem;
    }}
    .versevad-section-intro {{
      color: var(--color-text-secondary);
      margin-top: -.5rem;
      max-width: 76ch;
    }}
    .versevad-status {{
      border: 1px solid var(--color-border);
      border-radius: 999px;
      color: var(--color-text-secondary);
      display: inline-block;
      font-size: .76rem;
      font-weight: 650;
      padding: .18rem .55rem;
    }}
    .versevad-status--complete {{
      background: var(--color-success-soft);
      color: var(--color-success);
    }}
    .versevad-status--warning {{
      background: var(--color-warning-soft);
      color: var(--color-warning);
    }}
    code, pre {{
      background: var(--color-surface-muted) !important;
      color: var(--color-text-primary) !important;
    }}
    pre {{
      max-width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    button, [role="button"] {{
      touch-action: manipulation;
    }}
    #MainMenu, footer {{
      visibility: hidden;
    }}
    @media (max-width: 800px) {{
      .main .block-container {{
        max-width: 100%;
        overflow-x: hidden;
        overflow-x: clip;
      }}
      .main .block-container {{
        padding-left: .8rem;
        padding-right: .8rem;
      }}
      .st-key-versevad_global_header [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap;
        gap: var(--space-2);
      }}
      .st-key-versevad_global_header [data-testid="stColumn"]:first-child {{
        flex: 1 1 100% !important;
        width: 100% !important;
      }}
      .st-key-versevad_global_header [data-testid="stColumn"]:not(:first-child) {{
        flex: 1 1 7rem !important;
        min-width: 7rem !important;
        width: auto !important;
      }}
      .st-key-versevad_global_header button {{
        white-space: nowrap;
      }}
      .versevad-shell {{
        padding: .6rem;
      }}
      .versevad-empty {{
        padding: var(--space-6) var(--space-4);
      }}
    }}
    @media (max-width: 520px) {{
      .st-key-versevad_global_header {{
        position: static;
      }}
      .st-key-versevad_global_header [data-testid="stColumn"]:not(:first-child) {{
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
      }}
      [role="radiogroup"][aria-label="Workspace"] {{
        display: flex;
        flex-wrap: wrap;
        width: 100%;
      }}
      [role="radiogroup"][aria-label="Workspace"] button {{
        flex: 1 1 calc(50% - var(--space-2));
        min-width: 8.5rem;
        white-space: normal;
      }}
      [data-testid="stTextAreaRootElement"] textarea,
      [data-testid="stTextInputRootElement"] input {{
        font-size: 16px;
      }}
      [data-testid="stDownloadButton"] button,
      [data-testid="stBaseButton-primary"] {{
        min-height: 2.75rem;
        white-space: normal;
      }}
      .versevad-wordmark {{
        white-space: normal;
      }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: .01ms !important;
      }}
    }}
    </style>
    """


def apply_design_system(mode: AppearanceMode | str) -> None:
    st.markdown(stylesheet_for(mode), unsafe_allow_html=True)


def _persist_appearance() -> None:
    if cloud_deployment_enabled():
        return
    save_appearance(st.session_state["appearance_mode"])


def render_app_shell() -> tuple[str, AppearanceMode]:
    """Render the shared application header and return active workspace/theme."""

    preferences = (
        UiPreferences()
        if cloud_deployment_enabled()
        else load_preferences()
    )
    st.session_state.setdefault("appearance_mode", preferences.appearance.value)
    st.session_state.setdefault("analysis_cache_enabled", True)
    st.session_state.setdefault("performance_diagnostics_enabled", True)
    st.session_state.setdefault("workspace_page", WORKSPACES[0])
    legacy_workspace = {
        "One Poem": "Single Poem",
        "Projects & Corpus": "Project / Corpus",
    }
    if (
        "workspace_page" in st.session_state
        and st.session_state["workspace_page"] not in WORKSPACES
    ):
        st.session_state["workspace_page"] = legacy_workspace.get(
            st.session_state["workspace_page"],
            WORKSPACES[0],
        )
    appearance = AppearanceMode(st.session_state["appearance_mode"])
    apply_design_system(appearance)

    with st.container(key="versevad_global_header"):
        brand, appearance_column, settings_column, help_column = st.columns(
            [4.5, 1.3, 1, 1],
            vertical_alignment="center",
        )
        with brand:
            st.markdown(
                '<div class="versevad-wordmark">VerseVAD</div>'
                '<div class="versevad-platform">'
                f"Computational Poetics · Version {__version__}"
                "</div>",
                unsafe_allow_html=True,
            )
        with appearance_column:
            st.selectbox(
                "Appearance",
                options=[mode.value for mode in AppearanceMode],
                key="appearance_mode",
                on_change=_persist_appearance,
                help="System follows the browser or operating-system preference.",
            )
        with settings_column:
            with st.popover("Settings", width="stretch"):
                st.markdown("**Interface**")
                st.caption(
                    "Appearance is application-level and never changes an analysis."
                )
                st.markdown("**Analysis defaults**")
                st.caption(
                    "Weighting, thresholds, filtering, pronunciation, and module "
                    "parameters remain explicit in each analysis configuration."
                )
                st.markdown("**Exports & performance**")
                st.toggle(
                    "Reuse unchanged analysis",
                    key="analysis_cache_enabled",
                    help=(
                        "Uses bounded process-local caches with dependency-specific "
                        "keys. Disable only when debugging."
                    ),
                )
                st.toggle(
                    "Record analysis timings",
                    key="performance_diagnostics_enabled",
                    help=(
                        "Adds lightweight cache and wall-clock timing diagnostics "
                        "to completed in-memory analyses."
                    ),
                )
                from versevad.performance import (
                    cache_statistics,
                    clear_analysis_caches,
                    clear_export_cache,
                    clear_resource_caches,
                    clear_visualization_cache,
                    resource_cache_statistics,
                )

                statistics = (
                    cache_statistics() + resource_cache_statistics()
                )
                st.caption(
                    "Process cache: "
                    f"{sum(item.entry_count for item in statistics):,} entries; "
                    f"{sum(item.hits for item in statistics):,} hits; "
                    f"{sum(item.misses for item in statistics):,} misses. "
                    "Clearing it never removes projects, source files, or results."
                )
                clear_columns = st.columns(3)
                if clear_columns[0].button(
                    "Clear analysis cache",
                    key="clear_analysis_cache",
                    width="stretch",
                ):
                    clear_analysis_caches()
                    st.toast("Analysis cache cleared.")
                if clear_columns[1].button(
                    "Clear display/export cache",
                    key="clear_display_export_cache",
                    width="stretch",
                ):
                    clear_visualization_cache()
                    clear_export_cache()
                    st.toast("Display and export caches cleared.")
                if clear_columns[2].button(
                    "Release loaded resources",
                    key="release_resource_cache",
                    width="stretch",
                    help=(
                        "Releases reloadable lexicons, pronunciation data, the "
                        "language model, and meter plans. The next relevant "
                        "analysis reloads them."
                    ),
                ):
                    clear_resource_caches()
                    st.toast("Reloadable resources released.")
        with help_column:
            with st.popover("Help", width="stretch"):
                st.markdown("**How to use VerseVAD**")
                st.caption(
                    "Choose a workspace, add or select text, configure evidence, "
                    "run the analysis, then begin with Overview."
                )
                st.caption(
                    "Detailed methodology, values, testing, and user guidance are "
                    "available in the local docs folder and every completed "
                    "module's methodology panel."
                )
                st.markdown("**License**")
                st.caption(
                    "VerseVAD is free software under GPL-3.0-only, without "
                    "warranty. See LICENSE. Research datasets retain their own "
                    "terms and are not included in that license."
                )
        workspace = st.segmented_control(
            "Workspace",
            options=WORKSPACES,
            selection_mode="single",
            key="workspace_page",
        )
    return workspace or WORKSPACES[0], appearance


def render_workspace_header(
    title: str,
    description: str,
    *,
    kicker: str,
    status: str | None = None,
) -> None:
    st.markdown(
        f'<div class="versevad-kicker">{escape(kicker)}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    if status:
        st.markdown(
            f'<span class="versevad-status">{escape(status)}</span>',
            unsafe_allow_html=True,
        )
    st.write(description)
    st.divider()


def render_empty_state(title: str, description: str, action: str) -> None:
    st.markdown(
        '<div class="versevad-empty">'
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(description)}</p>"
        f"<strong>{escape(action)}</strong>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_section_intro(title: str, purpose: str, *, status: str = "Complete") -> None:
    modifier = "complete" if status == "Complete" else "warning"
    st.markdown(
        f"### {escape(title)} "
        f'<span class="versevad-status versevad-status--{modifier}">'
        f"{escape(status)}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="versevad-section-intro">{escape(purpose)}</p>',
        unsafe_allow_html=True,
    )


def render_dataframe(data: Any, **kwargs: Any) -> Any:
    """Render a scrollable table with its first data column pinned."""

    tabular_data = data if hasattr(data, "columns") else getattr(data, "data", None)
    columns = getattr(tabular_data, "columns", ())
    if len(columns):
        first_column = columns[0]
        column_config = dict(kwargs.pop("column_config", {}) or {})
        existing_config = column_config.get(first_column)
        if isinstance(existing_config, Mapping):
            column_config[first_column] = {
                **existing_config,
                "pinned": True,
            }
        else:
            column_config[first_column] = st.column_config.Column(pinned=True)
        kwargs["column_config"] = column_config
    return st.dataframe(data, **kwargs)


def render_stateful_section_navigation(
    label: str,
    options: Sequence[str],
    *,
    state_key: str,
    container_key_prefix: str,
    default: str | None = None,
    help_text: str | None = None,
    control: Literal["segmented", "dropdown"] = "segmented",
) -> tuple[str, dict[str, DeltaGenerator]]:
    """Render rerun-stable section navigation and keyed content containers."""

    section_options = tuple(options)
    if not section_options or len(set(section_options)) != len(section_options):
        raise ValueError("Section navigation requires unique, non-empty options.")
    selected_default = default or section_options[0]
    if selected_default not in section_options:
        raise ValueError("The default section must be one of the options.")
    if not container_key_prefix.replace("_", "").isalnum():
        raise ValueError(
            "The section container prefix may contain only letters, numbers, "
            "and underscores."
        )
    if st.session_state.get(state_key) not in section_options:
        st.session_state[state_key] = selected_default

    if control == "dropdown":
        selected = st.selectbox(
            label,
            options=section_options,
            index=None,
            key=state_key,
            help=help_text,
        )
    elif control == "segmented":
        selected = st.segmented_control(
            label,
            options=section_options,
            selection_mode="single",
            key=state_key,
            help=help_text,
        )
    else:
        raise ValueError("Section navigation control must be 'segmented' or 'dropdown'.")
    active_section = selected or selected_default
    container_keys = {
        section: f"{container_key_prefix}_{index}"
        for index, section in enumerate(section_options)
    }
    hidden_selectors = ",\n".join(
        f".st-key-{container_key}" for container_key in container_keys.values()
    )
    active_selector = f".st-key-{container_keys[active_section]}"
    st.markdown(
        "<style>"
        f"{hidden_selectors} {{ display: none; }}"
        f"{active_selector} {{ display: block; }}"
        "</style>",
        unsafe_allow_html=True,
    )
    containers = {
        section: st.container(key=container_keys[section])
        for section in section_options
    }
    return active_section, containers
