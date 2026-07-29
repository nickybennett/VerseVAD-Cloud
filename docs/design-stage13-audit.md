# Design Stage 13: Interface Audit and Migration Plan

This audit was completed before the Stage 13 interface overhaul. It describes
the interface as it existed at the Stage 12 checkpoint and defines an
incremental migration that preserves analytical and project behavior.

## Existing workspace map

| Workspace | Current entry point | Main regions | Persistent data |
|---|---|---|---|
| One Poem | `ui/app.py` | temporary text input, lexicon/module controls, advanced methodology, 15 result tabs, downloads | Streamlit session only |
| Projects & Corpus | `ui/corpus.py` | project creation/selection, works and metadata, language profile, batch analysis and comparison, review scenarios, Excel export, project settings | schema-4 SQLite repository |
| Lexicon Explorer | `ui/explorer.py` | query/mapping form, match transparency, affective resources, supplementary resources, pronunciation, provenance | current result in Streamlit session |
| Other Text | not separately exposed | no dedicated route; the One Poem engine can already process arbitrary preserved text | none |

PoetryID is correctly implemented as a dependent module within One Poem and
Projects/Corpus. It is not a separate application.

## Repeated and inconsistent patterns

- Workspace navigation is a single segmented control with three choices and no
  shared header, appearance control, help access, or active-workspace context.
- Each workspace creates its own title, kicker, sidebar privacy message, empty
  state, and explanatory copy.
- One Poem exposes fifteen result tabs at once. On laptop widths these become
  difficult to scan and provide no higher-level grouping.
- Optional modules are presented as one long sequence of checkboxes rather than
  Core, Lexical Character, Sound and Form, and Structural families.
- There are no module presets.
- Status, warning, methodology, and download patterns are individually authored
  in each module. Their language is strong, but hierarchy and placement vary.
- Metric cards, bordered containers, captions, expanders, and tables are used
  repeatedly without shared presentation helpers.
- Projects/Corpus is functionally organized but lacks a compact project status
  header before its six tabs.
- Empty states are plain information alerts and do not consistently explain the
  next action.
- Lexicon Explorer already has the required all-resource lookup behavior and
  must receive visual-system changes only.

## Analytical logic and presentation boundaries

The calculation engines, adapters, exports, corpus orchestration, and
repository are framework-independent. This is the key migration safeguard.
Presentation code does, however, remain concentrated in two large files:

- `ui/app.py` is approximately 4,500 lines and constructs the complete
  `AnalysisRequest` alongside all One Poem controls and results.
- `ui/corpus.py` is approximately 2,200 lines and constructs
  `CorpusAnalysisConfiguration` alongside project and report controls.

The redesign will not move calculations into UI helpers. Shared components may
format summaries or manage visual preferences, but analytical configuration
objects will continue to be constructed explicitly at the application
boundary.

## Current styling architecture

The complete custom style was one inline block in `ui/app.py`. It contained
four partly semantic color variables but also direct hex values, a fixed light
gradient, fixed white metric cards, a fixed light sidebar, and no alternate
appearance mode. Chart defaults were authored per module.

Alternate appearances are feasible without changing analysis. Streamlit uses
a central CSS token sheet whose Classic, Dark, Lavender, Ocean, Crimson, and
Forest mappings share the same semantic names. Appearance is stored in one
ignored local application-preference file and mirrored in session state.
Exports remain independent and light-oriented.

## Accessibility findings

- The native Streamlit controls provide useful labels and keyboard behavior,
  but the page lacks a consistent visible-focus treatment.
- Fixed light colors do not guarantee contrast under a dark browser or
  operating-system preference.
- The long result-tab strip is difficult at narrow widths and imposes a high
  navigation burden.
- Chart purpose and source tables exist, but chart containers do not use a
  shared visible text-alternative pattern.
- Color is not generally the sole carrier of analytical meaning; this existing
  strength must be retained.
- Some explanatory strings contain legacy encoding artifacts that should be
  corrected when their surrounding interface copy is touched.
- Reduced-motion behavior is not declared.
- Empty states and status notices are not consistently structured with a
  heading and next action.

## Proposed component hierarchy

The incremental component layer will contain:

- `AppShell` behavior: global wordmark, version, workspace navigation,
  appearance, settings summary, and help access;
- `WorkspaceHeader`: title, short description, status metadata, and optional
  actions;
- `ModuleSelector` and `PresetSelector`: grouped module controls whose state
  remains explicit;
- `AnalysisToolbar`: primary action and compact run-state guidance;
- `ReportOverview`: grouped emotional, lexical, sound/form, structure, and
  coverage summaries;
- `ResultNavigation`: a small set of report families rather than fifteen
  peer-level tabs;
- `ResultSection`: consistent heading, purpose, status, warning, methodology,
  and export affordances;
- `EmptyState`, `StatusPill`, `MethodologyPanel`, `WarningPanel`, and
  `ExportMenu` visual patterns;
- `ProjectStatusHeader`: project title, work count, database/schema status, and
  last-modified information;
- table and chart wrappers prepared for later virtualization and lazy loading.

Streamlit remains the only UI framework.

## Proposed semantic token structure

`ui/design.py` will own token mappings and the generated stylesheet:

- color: `background`, `surface`, `surface-raised`, `text-primary`,
  `text-secondary`, `border`, `border-strong`, `accent`, status colors,
  `focus`, and chart colors;
- typography: interface sans, literary serif, compact metadata, and tabular
  numerals;
- spacing: 4/8/12/16/24/32/48 pixel steps;
- border and radius: subtle, strong, small, medium, and large;
- elevation: restrained surface and navigation shadows;
- motion: fast and standard transitions with a reduced-motion override;
- charts: publication-light defaults plus interface-safe label/grid tokens.

Components will refer to semantic variables rather than embedding their own
theme colors.

## Files to add or modify

Add:

- `src/versevad/ui/design.py`
- `src/versevad/ui/preferences.py`
- Stage 13 design and validation documentation
- focused preference, component, and interface tests

Modify:

- `src/versevad/ui/app.py`
- `src/versevad/ui/corpus.py`
- `src/versevad/ui/explorer.py`
- `src/versevad/ui/poetry_id.py`
- existing interface tests and user documentation

No adapter, lexicon, calculation, repository schema, or stored result format is
scheduled to change.

## Migration risks and controls

1. **Widget-state loss.** Existing Streamlit keys will be retained. Workspace
   navigation will continue to leave One Poem input in session state.
2. **Analytical drift.** Engine inputs and application requests will be
   regression-tested before and after the visual changes.
3. **Project compatibility.** No schema migration is planned. Existing projects
   will be opened in the normal repository tests and interface smoke test.
4. **Preset surprise.** Presets will change module selections only after an
   explicit Apply action; they will not overwrite advanced parameters.
5. **Theme leakage into exports.** Appearance remains UI-only. Existing export
   bytes and publication-oriented chart defaults will not read the UI theme.
6. **Large-page regressions.** The initial pass reduces peer-level result
   navigation and prepares lazy containers without moving or duplicating result
   objects.
7. **Explorer drift.** Explorer service calls, match resolution, fields, and
   exports will remain unchanged; only its framing and shared visual styles are
   in scope.
8. **Responsive regressions.** Desktop remains primary. Shared CSS will add
   narrow-screen stacking and horizontal table access without shrinking body
   text.
