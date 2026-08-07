"""Instant, theme-aware interactive annotation for completed poem analyses."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from versevad.analysis_profiles import LexicalScope
from versevad.interactive_annotation import (
    build_interactive_annotation_payload,
    sanitize_annotation_settings,
)


ANNOTATION_SETTINGS_KEY = "interactive_annotation_settings"
ANNOTATION_COMPONENT_KEY = "interactive_annotation_component"

_COMPONENT_HTML = """
<section class="vv-annotation" aria-label="Interactive poem annotation">
  <div class="vv-toolbar">
    <div>
      <p class="vv-eyebrow">Completed-analysis evidence</p>
      <h3>Interactive Annotation</h3>
      <p class="vv-intro">Hover for a concise reading; select a token for its full evidence and provenance.</p>
    </div>
    <div class="vv-toolbar-actions">
      <button class="vv-secondary" id="vv-clear" type="button">Clear layers</button>
      <button class="vv-secondary" id="vv-default" type="button">Restore default</button>
    </div>
  </div>

  <details class="vv-config">
    <summary>Annotation layers and methodology</summary>
    <div class="vv-config-body">
      <div class="vv-control-group">
        <span class="vv-control-label">Evidence layers</span>
        <div class="vv-layer-controls" id="vv-layer-controls"></div>
      </div>
      <div class="vv-select-grid">
        <label class="vv-field" id="vv-vad-source-field">
          <span>VAD source</span>
          <select id="vv-vad-source"></select>
        </label>
        <label class="vv-field">
          <span>Active color lens</span>
          <select id="vv-active-lens"></select>
        </label>
        <label class="vv-check vv-unmatched-check">
          <input id="vv-unmatched" type="checkbox" />
          <span>Underline unmatched tokens for the active lens</span>
        </label>
      </div>
      <div class="vv-methodology" id="vv-methodology"></div>
    </div>
  </details>

  <div class="vv-legend" id="vv-legend" aria-live="polite"></div>
  <div class="vv-workspace">
    <div class="vv-poem-wrap">
      <pre class="vv-poem" id="vv-poem" aria-label="Annotated poem text"></pre>
    </div>
    <aside class="vv-panel" id="vv-panel" aria-label="Selected token evidence">
      <div class="vv-panel-empty" id="vv-panel-empty">
        <span class="vv-panel-symbol" aria-hidden="true">◇</span>
        <h4>Select a word</h4>
        <p>Click a word—or focus it and press Enter—to keep its complete evidence visible here.</p>
      </div>
      <div class="vv-panel-content" id="vv-panel-content" hidden>
        <div class="vv-panel-heading">
          <div>
            <p class="vv-eyebrow">Selected token</p>
            <h4 id="vv-panel-token"></h4>
          </div>
          <button class="vv-icon-button" id="vv-panel-close" type="button" aria-label="Close token details">×</button>
        </div>
        <div id="vv-panel-body"></div>
      </div>
    </aside>
  </div>
  <div class="vv-tooltip" id="vv-tooltip" role="tooltip" aria-hidden="true"></div>
</section>
"""

_COMPONENT_CSS = """
:host {
  --vv-bg: var(--vv-theme-background, var(--st-background-color, #ffffff));
  --vv-surface: var(--vv-theme-surface, var(--st-secondary-background-color, #f5f5f5));
  --vv-text: var(--vv-theme-text, var(--st-text-color, #17212b));
  --vv-accent: var(--vv-theme-accent, var(--st-primary-color, #8f452d));
  --vv-border: var(--vv-theme-border, color-mix(in srgb, var(--vv-text) 18%, transparent));
  --vv-muted: color-mix(in srgb, var(--vv-text) 64%, transparent);
  --vv-shadow: 0 12px 34px color-mix(in srgb, #000000 14%, transparent);
  color: var(--vv-text);
  font-family: var(--st-font, system-ui, sans-serif);
}

* { box-sizing: border-box; }
button, select, input { font: inherit; }

.vv-annotation {
  position: relative;
  color: var(--vv-text);
  background: var(--vv-bg);
  border: 1px solid var(--vv-border);
  border-radius: 16px;
  overflow: visible;
}

.vv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.1rem 1.2rem;
  border-bottom: 1px solid var(--vv-border);
}

.vv-toolbar h3, .vv-panel h4 { margin: 0; color: var(--vv-text); }
.vv-intro { margin: .25rem 0 0; color: var(--vv-muted); font-size: .92rem; }
.vv-eyebrow { margin: 0 0 .2rem; color: var(--vv-accent); font-size: .72rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }
.vv-toolbar-actions { display: flex; gap: .5rem; flex-wrap: wrap; justify-content: flex-end; }

.vv-secondary, .vv-icon-button {
  border: 1px solid var(--vv-border);
  background: var(--vv-surface);
  color: var(--vv-text);
  border-radius: 999px;
  cursor: pointer;
  min-height: 2.35rem;
}
.vv-secondary { padding: .45rem .85rem; }
.vv-icon-button { width: 2.35rem; padding: 0; font-size: 1.25rem; }
.vv-secondary:hover, .vv-icon-button:hover { border-color: var(--vv-accent); }
.vv-secondary:focus-visible, .vv-icon-button:focus-visible, select:focus-visible, input:focus-visible, .vv-token:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--vv-accent) 42%, transparent);
  outline-offset: 2px;
}

.vv-config { border-bottom: 1px solid var(--vv-border); background: color-mix(in srgb, var(--vv-surface) 70%, var(--vv-bg)); }
.vv-config summary { cursor: pointer; padding: .8rem 1.2rem; font-weight: 680; }
.vv-config-body { padding: .1rem 1.2rem 1.1rem; }
.vv-control-label, .vv-field > span { display: block; margin-bottom: .42rem; color: var(--vv-muted); font-size: .8rem; font-weight: 650; }
.vv-layer-controls { display: flex; flex-wrap: wrap; gap: .42rem .8rem; }
.vv-check { display: inline-flex; align-items: center; gap: .42rem; color: var(--vv-text); font-size: .88rem; }
.vv-check input { accent-color: var(--vv-accent); width: 1rem; height: 1rem; }
.vv-check[data-unavailable="true"] { opacity: .5; }
.vv-select-grid { display: grid; grid-template-columns: minmax(12rem, 1fr) minmax(12rem, 1fr) minmax(16rem, 1.35fr); gap: .9rem; margin-top: .9rem; align-items: end; }
.vv-field select { width: 100%; min-height: 2.35rem; padding: .38rem .55rem; border: 1px solid var(--vv-border); border-radius: 9px; background: var(--vv-bg); color: var(--vv-text); }
.vv-unmatched-check { min-height: 2.35rem; align-self: end; }
.vv-methodology { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .4rem .9rem; margin-top: .9rem; color: var(--vv-muted); font-size: .78rem; }
.vv-methodology p { margin: 0; }

.vv-legend { min-height: 3.5rem; padding: .75rem 1.2rem; display: flex; align-items: center; gap: .8rem; border-bottom: 1px solid var(--vv-border); }
.vv-legend-title { min-width: max-content; font-size: .82rem; font-weight: 700; }
.vv-gradient { height: .72rem; min-width: 12rem; flex: 1; max-width: 32rem; border-radius: 999px; border: 1px solid var(--vv-border); background: linear-gradient(90deg, rgba(72,123,210,.58), rgba(150,150,160,.15) 50%, rgba(220,79,105,.58)); }
.vv-legend-edge { color: var(--vv-muted); font-size: .76rem; }
.vv-legend-note { margin-left: auto; color: var(--vv-muted); font-size: .76rem; }

.vv-workspace { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(17rem, .75fr); min-height: 28rem; }
.vv-poem-wrap { padding: 1.35rem; border-right: 1px solid var(--vv-border); overflow: auto; }
.vv-poem { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font-family: var(--st-code-font, ui-monospace, SFMono-Regular, Consolas, monospace); font-size: 1rem; line-height: 1.85; color: var(--vv-text); background: transparent; }
.vv-token { position: relative; border-radius: 4px; cursor: pointer; transition: background-color 80ms linear, box-shadow 80ms linear; }
.vv-token[data-lexical="false"] { cursor: text; }
.vv-token:hover, .vv-token[data-selected="true"] { box-shadow: 0 0 0 2px color-mix(in srgb, var(--vv-accent) 48%, transparent); }
.vv-token[data-sensorimotor="true"]::before { content: ""; position: absolute; width: .32rem; height: .32rem; border-radius: 50%; background: #04a8ad; top: -.2rem; left: 50%; transform: translateX(-50%); }
.vv-token[data-emotion="true"] { text-decoration-line: underline; text-decoration-style: wavy; text-decoration-color: #b23b82; text-decoration-thickness: 1.4px; text-underline-offset: .18em; }
.vv-token[data-unmatched="true"] { outline: 1.5px dotted #d07b00; outline-offset: 1px; }

.vv-panel { position: sticky; top: 5.5rem; align-self: start; max-height: calc(100vh - 6.25rem); overflow-y: auto; overscroll-behavior: contain; padding: 1.1rem; background: color-mix(in srgb, var(--vv-surface) 76%, var(--vv-bg)); min-width: 0; }
.vv-panel-empty[hidden], .vv-panel-content[hidden] { display: none !important; }
.vv-panel-empty { min-height: 21rem; display: grid; place-content: center; text-align: center; color: var(--vv-muted); }
.vv-panel-empty h4 { margin-top: .55rem; }
.vv-panel-empty p { max-width: 22rem; margin: .5rem auto 0; }
.vv-panel-symbol { font-size: 2rem; color: var(--vv-accent); }
.vv-panel-heading { display: flex; justify-content: space-between; gap: 1rem; align-items: start; padding-bottom: .8rem; border-bottom: 1px solid var(--vv-border); }
.vv-panel-heading h4 { font-size: 1.45rem; overflow-wrap: anywhere; }
.vv-token-meta { color: var(--vv-muted); font-size: .8rem; margin: .35rem 0 .8rem; }
.vv-evidence-card { background: var(--vv-bg); border: 1px solid var(--vv-border); border-radius: 11px; padding: .72rem; margin-top: .6rem; }
.vv-evidence-card h5 { margin: 0 0 .35rem; color: var(--vv-text); font-size: .9rem; }
.vv-evidence-row { display: flex; justify-content: space-between; gap: 1rem; margin-top: .2rem; font-size: .82rem; }
.vv-evidence-row span:first-child { color: var(--vv-muted); }
.vv-status { display: inline-flex; align-items: center; border-radius: 999px; padding: .13rem .45rem; font-size: .7rem; font-weight: 700; background: var(--vv-surface); color: var(--vv-text); }
.vv-status[data-status="matched"] { background: color-mix(in srgb, #39a36c 18%, var(--vv-bg)); }
.vv-status[data-status="unmatched"] { background: color-mix(in srgb, #d98700 20%, var(--vv-bg)); }
.vv-provenance, .vv-reason { margin: .42rem 0 0; color: var(--vv-muted); font-size: .76rem; line-height: 1.4; overflow-wrap: anywhere; }
.vv-category-list { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .4rem; }
.vv-chip { border: 1px solid var(--vv-border); border-radius: 999px; padding: .15rem .45rem; font-size: .72rem; background: var(--vv-surface); }
.vv-dimension-grid { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .15rem .6rem; margin-top: .4rem; font-size: .75rem; }
.vv-dimension-grid span:nth-child(odd) { color: var(--vv-muted); }

.vv-tooltip { position: fixed; z-index: 999999; display: none; width: min(22rem, calc(100vw - 2rem)); padding: .68rem .75rem; border: 1px solid color-mix(in srgb, var(--vv-accent) 45%, var(--vv-border)); border-radius: 10px; background: var(--vv-bg); color: var(--vv-text); box-shadow: var(--vv-shadow); pointer-events: none; font-size: .78rem; line-height: 1.4; }
.vv-tooltip[data-visible="true"] { display: block; }
.vv-tooltip-title { font-weight: 760; font-size: .9rem; margin-bottom: .2rem; }
.vv-tooltip-line { color: var(--vv-muted); }
.vv-tooltip strong { color: var(--vv-text); }

@media (max-width: 860px) {
  .vv-toolbar { align-items: flex-start; flex-direction: column; }
  .vv-toolbar-actions { justify-content: flex-start; }
  .vv-select-grid, .vv-methodology { grid-template-columns: 1fr; }
  .vv-workspace { grid-template-columns: 1fr; }
  .vv-poem-wrap { border-right: 0; border-bottom: 1px solid var(--vv-border); }
  .vv-panel { position: static; max-height: none; overflow-y: visible; }
  .vv-panel-empty { min-height: 10rem; }
  .vv-legend { flex-wrap: wrap; }
  .vv-legend-note { width: 100%; margin-left: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .vv-token { transition: none; }
}
"""

_COMPONENT_JS = r"""
const selectedByAnalysis = new Map();

function el(root, selector) { return root.querySelector(selector); }
function text(node, value) { node.textContent = value == null ? "" : String(value); }
function rounded(value) { return Number.isFinite(Number(value)) ? Number(value).toFixed(3) : "—"; }
function titleCase(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
function byId(payload, layerId) { return (payload.layers || []).find(layer => layer.id === layerId); }
function enabled(settings, layerId) { return (settings.enabled_layers || []).includes(layerId); }
function isVad(layerId) { return ["valence", "arousal", "dominance"].includes(layerId); }

function baseScopeEligible(token, settings) {
  return Boolean(token.scope_eligibility?.[settings.active_scope]);
}

function scopeEligible(payload, token, evidence, settings) {
  if (baseScopeEligible(token, settings)) return true;
  const primary = evidence?.primary;
  if (!primary?.expression_match || !Array.isArray(primary.token_ids)) return false;
  const ids = new Set(primary.token_ids);
  return (payload.tokens || []).some(candidate => ids.has(candidate.token_id) && baseScopeEligible(candidate, settings));
}

function normalizeSettings(payload, candidate) {
  const available = new Set((payload.layers || []).filter(layer => layer.available).map(layer => layer.id));
  const sources = (payload.sources?.vad || []).map(source => source.id);
  const incoming = candidate && typeof candidate === "object" ? candidate : {};
  const enabledLayers = Array.isArray(incoming.enabled_layers)
    ? incoming.enabled_layers.filter(layer => available.has(layer))
    : ["valence", "pos"].filter(layer => available.has(layer));
  const continuous = enabledLayers.filter(layer => ["valence", "arousal", "dominance", "concreteness", "frequency", "aoa"].includes(layer));
  let activeLens = continuous.includes(incoming.active_lens) ? incoming.active_lens : (continuous[0] || "");
  let vadSource = sources.includes(incoming.vad_source) ? incoming.vad_source : (sources[0] || "");
  return {
    enabled_layers: enabledLayers,
    active_lens: activeLens,
    vad_source: vadSource,
    underline_unmatched: Boolean(incoming.underline_unmatched),
    active_scope: String(payload.active_scope || incoming.active_scope || "STOPWORD_EXCLUDED"),
  };
}

function evidenceFor(token, layerId, settings) {
  if (isVad(layerId)) return token.evidence?.vad?.[settings.vad_source] || {status: "unavailable", reason: "No active VAD source."};
  return token.evidence?.[layerId] || {status: "unavailable", reason: "No evidence was recorded."};
}

function valueFor(token, layerId, settings) {
  const evidence = evidenceFor(token, layerId, settings);
  return evidence?.primary?.values?.[layerId];
}

function sourceFor(payload, layerId, settings) {
  if (isVad(layerId)) return (payload.sources?.vad || []).find(source => source.id === settings.vad_source);
  return payload.sources?.[layerId];
}

function interpretation(layer, value) {
  if (!Number.isFinite(Number(value))) return "No value";
  const number = Number(value);
  if (layer.id === "frequency") {
    if (number < 3) return "Very rare";
    if (number < 4) return "Rare / less common";
    if (number < 5) return "Moderately common";
    if (number < 6) return "Common";
    return "Very common";
  }
  if (layer.id === "aoa") {
    if (number <= 5) return "Earlier-acquired";
    if (number >= 12) return "Later-acquired";
    return "Middle-acquired";
  }
  if (layer.id === "concreteness") {
    if (number <= 2) return "Highly abstract";
    if (number >= 4) return "Highly concrete";
    return "Intermediate";
  }
  const ratio = (number - layer.minimum) / (layer.maximum - layer.minimum);
  if (ratio < .35) return `Low ${layer.label.toLowerCase()}`;
  if (ratio > .65) return `High ${layer.label.toLowerCase()}`;
  return `Mid-range ${layer.label.toLowerCase()}`;
}

function positionTooltip(tooltip, target) {
  const rect = target.getBoundingClientRect();
  const box = tooltip.getBoundingClientRect();
  let left = rect.left + rect.width / 2 - box.width / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - box.width - 8));
  let top = rect.top - box.height - 9;
  if (top < 8) top = rect.bottom + 9;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${Math.max(8, top)}px`;
}

function phraseLabel(observation) {
  if (!observation?.expression_match) return "";
  const term = observation.matched_term || observation.matched_lookup_form || "expression";
  return `Matched as the expression “${term}”; this value belongs to the whole expression.`;
}

function appendLine(parent, label, value, className = "vv-evidence-row") {
  const row = document.createElement("div");
  row.className = className;
  const key = document.createElement("span");
  const val = document.createElement("span");
  text(key, label); text(val, value);
  row.append(key, val); parent.appendChild(row);
  return row;
}

function appendChips(parent, values) {
  const list = document.createElement("div");
  list.className = "vv-category-list";
  (values || []).forEach(value => {
    const chip = document.createElement("span");
    chip.className = "vv-chip";
    text(chip, titleCase(value));
    list.appendChild(chip);
  });
  parent.appendChild(list);
}

function evidenceCard(payload, token, layer, settings) {
  const card = document.createElement("section");
  card.className = "vv-evidence-card";
  const heading = document.createElement("h5");
  text(heading, layer.label);
  card.appendChild(heading);

  if (layer.id === "pos") {
    appendLine(card, "Tag", `${token.part_of_speech_label} (${token.part_of_speech})`);
    appendLine(card, "Lemma", token.lemma || "—");
    return card;
  }

  const evidence = evidenceFor(token, layer.id, settings);
  const status = document.createElement("span");
  status.className = "vv-status";
  status.dataset.status = evidence.status || "unavailable";
  text(status, titleCase(evidence.status || "unavailable"));
  card.appendChild(status);

  if (layer.id === "emotion") {
    if (evidence.categories?.length) appendChips(card, evidence.categories);
  } else if (layer.id === "sensorimotor" && evidence.primary) {
    appendLine(card, "Dominant perceptual domain", titleCase(evidence.primary.dominant_perceptual));
    appendLine(card, "Dominant action domain", titleCase(evidence.primary.dominant_action));
    appendLine(card, "Overall dominant domain", titleCase(evidence.primary.dominant_sensorimotor));
    appendLine(card, "Perceptual strength", rounded(evidence.primary.perceptual_strength));
    appendLine(card, "Action strength", rounded(evidence.primary.action_strength));
    const dimensions = document.createElement("div");
    dimensions.className = "vv-dimension-grid";
    Object.entries(evidence.primary.values || {}).sort((a, b) => b[1] - a[1]).forEach(([dimension, value]) => {
      const label = document.createElement("span");
      const number = document.createElement("span");
      text(label, titleCase(dimension)); text(number, rounded(value));
      dimensions.append(label, number);
    });
    card.appendChild(dimensions);
  } else if (evidence.primary) {
    const value = valueFor(token, layer.id, settings);
    appendLine(card, isVad(layer.id) ? "Normalized value" : "Value", rounded(value));
    if (isVad(layer.id) && Number.isFinite(Number(evidence.primary.original_values?.[layer.id]))) {
      const sourceMeta = sourceFor(payload, layer.id, settings);
      appendLine(
        card,
        "Source value",
        `${rounded(evidence.primary.original_values[layer.id])} / ${sourceMeta?.original_scale || "source scale"}`,
      );
    }
    appendLine(card, "Interpretation", interpretation(layer, value));
    appendLine(card, "Scale", layer.scale || "—");
    appendLine(card, "Lookup form", evidence.primary.matched_lookup_form || "—");
  }

  if (evidence.reason) {
    const reason = document.createElement("p");
    reason.className = "vv-reason";
    text(reason, evidence.reason);
    card.appendChild(reason);
  }
  if (evidence.primary) {
    const source = sourceFor(payload, layer.id, settings);
    const provenance = document.createElement("p");
    provenance.className = "vv-provenance";
    const bits = [source?.label, source?.version ? `version ${source.version}` : "", titleCase(evidence.primary.match_method), evidence.primary.source_rows?.length ? `source row ${evidence.primary.source_rows.join(", ")}` : ""].filter(Boolean);
    const phrase = phraseLabel(evidence.primary);
    text(provenance, `${bits.join(" · ")}${phrase ? `\n${phrase}` : ""}`);
    card.appendChild(provenance);
  }
  return card;
}

function showPanel(root, payload, token, settings) {
  hideTooltip(root);
  selectedByAnalysis.set(payload.analysis_id, token.token_id);
  root.querySelectorAll(".vv-token").forEach(node => { node.dataset.selected = String(node.dataset.tokenId === token.token_id); });
  el(root, "#vv-panel-empty").hidden = true;
  el(root, "#vv-panel-content").hidden = false;
  text(el(root, "#vv-panel-token"), token.surface);
  const body = el(root, "#vv-panel-body");
  body.replaceChildren();
  const meta = document.createElement("p");
  meta.className = "vv-token-meta";
  text(meta, `Line ${token.line_number} · stanza ${token.stanza_number} · token ${token.token_position} · ${token.part_of_speech_label}`);
  body.appendChild(meta);
  appendLine(body, "Normalized token", token.normalized || "—");
  appendLine(body, "Lemma", token.lemma || "—");
  if (settings.active_lens) {
    appendLine(
      body,
      "Active-lens status",
      titleCase(evidenceFor(token, settings.active_lens, settings).status),
    );
  }
  (payload.layers || []).filter(layer => enabled(settings, layer.id)).forEach(layer => body.appendChild(evidenceCard(payload, token, layer, settings)));
}

function closePanel(root, payload) {
  hideTooltip(root);
  selectedByAnalysis.delete(payload.analysis_id);
  root.querySelectorAll(".vv-token").forEach(node => { node.dataset.selected = "false"; });
  el(root, "#vv-panel-empty").hidden = false;
  el(root, "#vv-panel-content").hidden = true;
  el(root, "#vv-panel-body").replaceChildren();
}

function showTooltip(root, payload, token, target, settings) {
  const tooltip = el(root, "#vv-tooltip");
  tooltip.replaceChildren();
  const title = document.createElement("div");
  title.className = "vv-tooltip-title";
  text(title, `${token.surface}${enabled(settings, "pos") ? ` · ${token.part_of_speech}` : ""}`);
  tooltip.appendChild(title);
  if (enabled(settings, "pos")) {
    const identity = document.createElement("div");
    identity.className = "vv-tooltip-line";
    text(identity, `Lemma: ${token.lemma || "—"} · ${token.part_of_speech_label}`);
    tooltip.appendChild(identity);
  }
  const active = settings.active_lens;
  if (active) {
    const evidence = evidenceFor(token, active, settings);
    const line = document.createElement("div");
    line.className = "vv-tooltip-line";
    const label = byId(payload, active)?.label || titleCase(active);
    const layer = byId(payload, active);
    const value = valueFor(token, active, settings);
    text(line, `${label}: ${evidence.status === "matched" ? `${rounded(value)} · ${interpretation(layer, value)}` : `${titleCase(evidence.status)} · ${evidence.reason || "No value available for this metric."}`}${evidence.primary?.expression_match ? " · expression match" : ""}`);
    tooltip.appendChild(line);
  }
  (payload.layers || []).filter(layer => layer.kind === "continuous" && enabled(settings, layer.id) && layer.id !== active).forEach(layer => {
    const evidence = evidenceFor(token, layer.id, settings);
    const value = valueFor(token, layer.id, settings);
    const line = document.createElement("div");
    line.className = "vv-tooltip-line";
    text(line, `${layer.label}: ${evidence.status === "matched" ? `${rounded(value)} · ${interpretation(layer, value)}` : titleCase(evidence.status)}`);
    tooltip.appendChild(line);
  });
  if (enabled(settings, "sensorimotor")) {
    const evidence = token.evidence?.sensorimotor;
    const line = document.createElement("div");
    line.className = "vv-tooltip-line";
    text(line, evidence?.primary ? `Sensorimotor: ${titleCase(evidence.primary.dominant_perceptual)} / ${titleCase(evidence.primary.dominant_action)}` : `Sensorimotor: ${titleCase(evidence?.status)}`);
    tooltip.appendChild(line);
  }
  if (enabled(settings, "emotion")) {
    const line = document.createElement("div");
    line.className = "vv-tooltip-line";
    text(line, `Emotion: ${token.evidence?.emotion?.categories?.length ? token.evidence.emotion.categories.map(titleCase).join(", ") : titleCase(token.evidence?.emotion?.status)}`);
    tooltip.appendChild(line);
  }
  tooltip.dataset.visible = "true";
  tooltip.setAttribute("aria-hidden", "false");
  positionTooltip(tooltip, target);
}

function hideTooltip(root) {
  const tooltip = el(root, "#vv-tooltip");
  tooltip.dataset.visible = "false";
  tooltip.setAttribute("aria-hidden", "true");
}

function paletteFor(layerId) {
  const palettes = {
    valence: [[148, 61, 66], [42, 125, 80]],
    arousal: [[78, 132, 184], [209, 93, 40]],
    dominance: [[116, 79, 148], [28, 132, 144]],
    concreteness: [[137, 132, 165], [151, 96, 43]],
    frequency: [[73, 69, 154], [28, 133, 117]],
    aoa: [[41, 130, 134], [205, 119, 25]],
  };
  return palettes[layerId] || palettes.valence;
}

function fillFor(value, layer) {
  if (!Number.isFinite(Number(value)) || !Number.isFinite(layer.minimum) || !Number.isFinite(layer.maximum) || layer.maximum === layer.minimum) return "transparent";
  const ratio = Math.max(0, Math.min(1, (Number(value) - layer.minimum) / (layer.maximum - layer.minimum)));
  const [low, high] = paletteFor(layer.id);
  const color = ratio <= .5 ? low : high;
  const alpha = .10 + Math.abs(ratio - .5) * .90;
  return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha.toFixed(3)})`;
}

function applyTokenStyles(root, payload, settings) {
  const activeLayer = byId(payload, settings.active_lens);
  root.querySelectorAll(".vv-token").forEach(node => {
    const token = payload.tokens[Number(node.dataset.tokenIndex)];
    const evidence = settings.active_lens ? evidenceFor(token, settings.active_lens, settings) : null;
    const value = settings.active_lens ? valueFor(token, settings.active_lens, settings) : null;
    const eligible = scopeEligible(payload, token, evidence, settings);
    node.style.backgroundColor = activeLayer && eligible && evidence?.status === "matched" ? fillFor(value, activeLayer) : "transparent";
    node.dataset.scopeExcluded = String(!eligible);
    node.dataset.unmatched = String(Boolean(settings.underline_unmatched && settings.active_lens && eligible && evidence?.status === "unmatched"));
    const sensorEvidence = token.evidence?.sensorimotor;
    const emotionEvidence = token.evidence?.emotion;
    node.dataset.sensorimotor = String(Boolean(enabled(settings, "sensorimotor") && scopeEligible(payload, token, sensorEvidence, settings) && sensorEvidence?.status === "matched"));
    node.dataset.emotion = String(Boolean(enabled(settings, "emotion") && scopeEligible(payload, token, emotionEvidence, settings) && emotionEvidence?.categories?.length));
  });
}

function renderLegend(root, payload, settings) {
  const legend = el(root, "#vv-legend");
  legend.replaceChildren();
  const layer = byId(payload, settings.active_lens);
  if (!layer) {
    const note = document.createElement("span");
    note.className = "vv-legend-note";
    text(note, "No continuous color lens is active. Categorical markers may still be displayed.");
    legend.appendChild(note);
    return;
  }
  const label = document.createElement("span");
  label.className = "vv-legend-title";
  text(label, layer.label);
  const low = document.createElement("span"); low.className = "vv-legend-edge"; text(low, `${layer.low_label} · ${layer.minimum}`);
  const gradient = document.createElement("div"); gradient.className = "vv-gradient"; gradient.setAttribute("aria-hidden", "true");
  const [lowColor, highColor] = paletteFor(layer.id);
  gradient.style.background = `linear-gradient(90deg, rgba(${lowColor.join(",")},.72), rgba(150,150,160,.10) 50%, rgba(${highColor.join(",")},.72))`;
  const high = document.createElement("span"); high.className = "vv-legend-edge"; text(high, `${layer.maximum} · ${layer.high_label}`);
  const note = document.createElement("span"); note.className = "vv-legend-note"; text(note, `${layer.scale}; midpoint ${layer.midpoint}`);
  legend.append(label, low, gradient, high, note);
}

function renderPoem(root, payload, settings) {
  const poem = el(root, "#vv-poem");
  poem.replaceChildren();
  const source = String(payload.original_text || "");
  let cursor = 0;
  (payload.tokens || []).forEach((token, index) => {
    const start = Math.max(cursor, Number(token.start));
    const end = Math.max(start, Number(token.end));
    if (start > cursor) poem.appendChild(document.createTextNode(source.slice(cursor, start)));
    const span = document.createElement("span");
    span.className = "vv-token";
    span.dataset.tokenIndex = String(index);
    span.dataset.tokenId = token.token_id;
    span.dataset.lexical = String(Boolean(token.lexicon_eligible));
    span.dataset.selected = String(selectedByAnalysis.get(payload.analysis_id) === token.token_id);
    span.tabIndex = token.lexicon_eligible ? 0 : -1;
    span.setAttribute("role", token.lexicon_eligible ? "button" : "text");
    span.setAttribute("aria-label", `${token.surface}, ${token.part_of_speech_label}, line ${token.line_number}`);
    text(span, source.slice(start, end));
    poem.appendChild(span);
    cursor = end;
  });
  if (cursor < source.length) poem.appendChild(document.createTextNode(source.slice(cursor)));
  applyTokenStyles(root, payload, settings);

  poem.querySelectorAll(".vv-token").forEach(node => {
    const token = payload.tokens[Number(node.dataset.tokenIndex)];
    if (!token.lexicon_eligible) return;
    node.addEventListener("pointerenter", () => showTooltip(root, payload, token, node, settings));
    node.addEventListener("pointerleave", () => hideTooltip(root));
    node.addEventListener("focus", () => showTooltip(root, payload, token, node, settings));
    node.addEventListener("blur", () => hideTooltip(root));
    node.addEventListener("click", () => {
      const evidence = settings.active_lens ? evidenceFor(token, settings.active_lens, settings) : null;
      if (scopeEligible(payload, token, evidence, settings)) showPanel(root, payload, token, settings);
    });
    node.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); showPanel(root, payload, token, settings); }
      if (event.key === "Escape") { event.preventDefault(); hideTooltip(root); closePanel(root, payload); }
    });
  });

  const selectedId = selectedByAnalysis.get(payload.analysis_id);
  const selectedToken = (payload.tokens || []).find(token => token.token_id === selectedId);
  if (selectedToken) showPanel(root, payload, selectedToken, settings);
}

function populateControls(root, payload, settings, commit) {
  const controls = el(root, "#vv-layer-controls");
  controls.replaceChildren();
  (payload.layers || []).forEach(layer => {
    const label = document.createElement("label");
    label.className = "vv-check";
    label.dataset.unavailable = String(!layer.available);
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = enabled(settings, layer.id);
    input.disabled = !layer.available;
    input.dataset.layerId = layer.id;
    const caption = document.createElement("span");
    text(caption, `${layer.label}${layer.available ? "" : " · not analyzed"}`);
    label.append(input, caption); controls.appendChild(label);
    input.addEventListener("change", () => {
      const set = new Set(settings.enabled_layers || []);
      input.checked ? set.add(layer.id) : set.delete(layer.id);
      settings.enabled_layers = Array.from(set);
      if (layer.kind === "continuous" && input.checked && !settings.active_lens) settings.active_lens = layer.id;
      if (layer.id === settings.active_lens && !input.checked) settings.active_lens = settings.enabled_layers.find(id => byId(payload, id)?.kind === "continuous") || "";
      commit();
    });
  });

  const sourceSelect = el(root, "#vv-vad-source");
  sourceSelect.replaceChildren();
  (payload.sources?.vad || []).forEach(source => {
    const option = document.createElement("option"); option.value = source.id; text(option, `${source.label}${source.version ? ` · ${source.version}` : ""}`); sourceSelect.appendChild(option);
  });
  sourceSelect.value = settings.vad_source;
  el(root, "#vv-vad-source-field").hidden = !(payload.sources?.vad || []).length;
  sourceSelect.onchange = () => { settings.vad_source = sourceSelect.value; commit(); };

  const lensSelect = el(root, "#vv-active-lens");
  lensSelect.replaceChildren();
  const none = document.createElement("option"); none.value = ""; text(none, "None"); lensSelect.appendChild(none);
  (payload.layers || []).filter(layer => layer.kind === "continuous" && layer.available && enabled(settings, layer.id)).forEach(layer => {
    const option = document.createElement("option"); option.value = layer.id; text(option, layer.label); lensSelect.appendChild(option);
  });
  lensSelect.value = settings.active_lens;
  lensSelect.onchange = () => { settings.active_lens = lensSelect.value; commit(); };

  const unmatched = el(root, "#vv-unmatched");
  unmatched.checked = settings.underline_unmatched;
  unmatched.disabled = !settings.active_lens;
  unmatched.onchange = () => { settings.underline_unmatched = unmatched.checked; commit(); };
}

export default function(component) {
  const {data, parentElement, setStateValue} = component;
  const root = parentElement;
  const payload = data?.payload || {};
  const themeTarget = root.host || root;
  const theme = data?.theme || {};
  const themeProperties = {
    "--vv-theme-background": theme.background,
    "--vv-theme-surface": theme.surface,
    "--vv-theme-text": theme.text,
    "--vv-theme-accent": theme.accent,
    "--vv-theme-border": theme.border,
  };
  Object.entries(themeProperties).forEach(([name, value]) => {
    if (value) themeTarget.style.setProperty(name, value);
    else themeTarget.style.removeProperty(name);
  });
  let settings = normalizeSettings(payload, data?.settings || payload.settings);

  const methodology = el(root, "#vv-methodology");
  methodology.replaceChildren();
  Object.values(payload.methodology || {}).forEach(value => {
    const paragraph = document.createElement("p"); text(paragraph, value); methodology.appendChild(paragraph);
  });

  let saveTimer = null;
  const render = () => {
    populateControls(root, payload, settings, commit);
    renderLegend(root, payload, settings);
    renderPoem(root, payload, settings);
  };
  const commit = () => {
    hideTooltip(root);
    settings = normalizeSettings(payload, settings);
    render();
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => setStateValue("settings", settings), 120);
  };

  el(root, "#vv-clear").onclick = () => { settings.enabled_layers = []; settings.active_lens = ""; settings.underline_unmatched = false; commit(); };
  el(root, "#vv-default").onclick = () => { settings = normalizeSettings(payload, payload.default_settings); commit(); };
  el(root, "#vv-panel-close").onclick = () => closePanel(root, payload);
  const onRootKeydown = event => {
    if (event.key === "Escape") { hideTooltip(root); closePanel(root, payload); }
  };
  root.addEventListener("keydown", onRootKeydown);
  const onScroll = () => hideTooltip(root);
  window.addEventListener("scroll", onScroll, true);
  render();

  return () => { window.clearTimeout(saveTimer); hideTooltip(root); root.removeEventListener("keydown", onRootKeydown); window.removeEventListener("scroll", onScroll, true); };
}
"""


def _annotation_component():
    """Register in the active Streamlit runner only when the report is open."""

    return st.components.v2.component(
        "versevad_interactive_annotation",
        html=_COMPONENT_HTML,
        css=_COMPONENT_CSS,
        js=_COMPONENT_JS,
    )


def _component_settings() -> object:
    state = st.session_state.get(ANNOTATION_COMPONENT_KEY)
    if isinstance(state, Mapping):
        return state.get("settings")
    return getattr(state, "settings", None)


def _persist_component_settings() -> None:
    settings = _component_settings()
    if isinstance(settings, Mapping):
        st.session_state[ANNOTATION_SETTINGS_KEY] = dict(settings)


def render_interactive_annotation(
    workspace: object,
    *,
    theme_tokens: Mapping[str, str] | None = None,
    active_scope: LexicalScope = LexicalScope.STOPWORD_EXCLUDED,
) -> None:
    """Render a completed analysis without recalculating any metric."""

    saved = st.session_state.get(ANNOTATION_SETTINGS_KEY)
    payload = build_interactive_annotation_payload(
        workspace,
        saved_settings=saved,
        active_scope=active_scope,
    )
    available_layers = tuple(
        layer["id"] for layer in payload["layers"] if layer["available"]
    )
    vad_sources = tuple(source["id"] for source in payload["sources"]["vad"])
    settings = sanitize_annotation_settings(
        payload["settings"],
        available_layers=available_layers,
        available_vad_sources=vad_sources,
    )
    payload["settings"] = settings
    if not payload["tokens"]:
        st.info(
            "This historical result does not contain the stable token record "
            "required for interactive annotation. Prepare a current reanalysis "
            "to create it."
        )
        return
    _annotation_component()(
        key=ANNOTATION_COMPONENT_KEY,
        data={
            "payload": payload,
            "settings": settings,
            "theme": {
                "background": theme_tokens.get("background", "") if theme_tokens else "",
                "surface": theme_tokens.get("surface", "") if theme_tokens else "",
                "text": theme_tokens.get("text-primary", "") if theme_tokens else "",
                "accent": theme_tokens.get("accent", "") if theme_tokens else "",
                "border": theme_tokens.get("border", "") if theme_tokens else "",
            },
        },
        default={"settings": settings},
        on_settings_change=_persist_component_settings,
        width="stretch",
        height="content",
    )


__all__ = [
    "ANNOTATION_COMPONENT_KEY",
    "ANNOTATION_SETTINGS_KEY",
    "render_interactive_annotation",
]
