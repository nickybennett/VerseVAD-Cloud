# Changelog

All notable VerseVAD changes will be recorded here.

## 1.0.0

### Changed

- Reworked Compare Poems around actual metric selection, side-by-side poem
  values, max-minus-min range, and separate metric-family tables; within-poem
  dispersion remains visible without an easily confused cross-poem SD column.
- Refined Compare Poems around a consistent means/composites, cumulative-load,
  then dispersion reading order; reduced PoetryID to one active Category Fit
  and Nearest Centroid pair while retaining alternate views in exports.
- Added NRC emotion/polarity association and intensity evidence to both shared
  token scopes, a shared pronunciation-review/reanalysis flow, and a focused
  multi-poem VerseMap PCA dashboard against the hosted reference corpus.
- Added shared comparison methodology controls for phrase handling, evidence
  thresholds, lexical modules, PoetryID, pronunciation, meter, and phonology.
- Made Saved Projects results show one poem or whole corpus, one report/module,
  and one metric family at a time while retaining complete audit exports.
- Versioned VV-PRE as `vv-pre-content-word-profile-1.0`: Frequency, AoA, and
  Word Complexity now use token-weighted `NOUN`/`VERB`/`ADJ`/`ADV`
  occurrences with repetition retained, while Line Accessibility continues to
  use all lexical words per nonblank line. Profile identity and component scope
  are retained in the interface, provenance, and exports.
- Completed the final top-level workspace architecture. Reference Corpora,
  standalone VerseMap, Form Library, Corpus Browser, Documentation, and
  Methodology now render working interfaces rather than planned-state copy.
- Added private local reference-corpus creation, UTF-8/path validation,
  incremental file maintenance, Standard Profile 1.0 index builds, read-only
  checks, and exact-confirmation deletion under ignored `projects/` storage.
  Hosted deployments keep the built-in reference corpus read-only.
- Added selectable-corpus standalone VerseMap with session drafts, historical
  Analysis Library saves, contextual notes, and note-aware CSV/Word bundles.
- Added read-only corpus inventories, release/model identities, feature
  coverage, distributions, poem profiles, and safely constrained source-text
  viewing.
- Added searchable inherited-form definitions/rules and packaged
  documentation/methodology readers. Every conditional sidebar now provides
  either applicable research controls or generic context, navigation, and
  privacy information.
- Tightened the narrow-window navigation breakpoint so hosted navigation and
  the appearance/settings/help controls remain readable without overlap.
- Implemented the hosted **Analysis Library** with immutable revisions,
  recoverable drafts, full-text versus results-only privacy choices,
  historical viewing without silent recalculation, Save As New, optional
  project associations, and exact-title deletion. Its isolated database lasts
  only for the current hosted session.
- Added contextual research notebooks with report, metric, chart, passage,
  word, rhyme, and form anchors plus tags, dates, editing, deletion, and
  explicit export eligibility.
- Added automatic drafts and a clear-text decision flow that can retain the
  draft, save a completed analysis, or discard only unsaved work.
- Excluded notes from exports by default. Deliberately selected notes appear in
  Word appendices and CSV/Markdown bundle artifacts.
- Made top navigation opaque and fixed, enlarged and responsively spaced its
  section labels, and dismissed hover menus after the pointer leaves.
- Replaced the flat workspace control with four grouped top-level sections:
  **Analyze**, **Collections**, **Explore**, and **Learn**. The existing Project
  / Corpus workspace is now labeled **Saved Projects**, while Personal Corpus
  remains unavailable in the hosted edition.
- Added a conditional research sidebar and expanded **Compare Poems** from two
  poems to a dynamic set of two through ten with side-by-side values,
  equal-poem means, poem-level dispersion, and long-form CSV/Word exports.
- Replaced the legacy presets with **Full Poetic Analysis**,
  **Computational Close Reading**, **Affect and Emotion**, **Sound and Prosody**,
  **Formal Analysis**, and **Teaching/Introductory**. Hosted custom profiles
  retain configuration only for the current browser session.
- Made PoetryID's **Category Fit Archetype** primary and the **Nearest Centroid
  Archetype** secondary. Multi-poem and corpus summaries remain limited to
  those two interpretable fields.
- Bundled the checksum-pinned Lancaster Sensorimotor Norms CSV in the private
  cloud repository so hosted sensorimotor analysis works without user setup;
  the public/local repository continues to treat it as user-supplied data.
- Reorganized **Compare Poems** to follow the Single Poem report map, with
  familiar default-collapsed subsections, compact source/scale-specific
  tables, automatically fitted side-by-side dot plots, and optional
  zero-centered B-minus-A difference bars.
- Standardized all front-end numeric presentation at no more than three
  decimal places across workspaces, result tables, mixed-value cells, chart
  axes, and tooltips while leaving CSV and Word export precision unchanged.
- Added a session-only **Compare Poems** workspace that runs two poems under
  one shared configuration and reports source-specific values, within-poem
  dispersion, cumulative and length-normalized lexical loads, coverage,
  denominators, and explicit Poem-B-minus-Poem-A differences. It reuses
  installed affective, sensorimotor, lexical, structure, sound, PoetryID,
  inherited-form, and VerseMap engines and exports CSV plus narrative Word
  reports.
- Updated presets so **Essential** and **Sound and Form** include
  sensorimotor imagery, while **Complete** includes both sensorimotor imagery
  and VerseMap. Literary continues to include sensorimotor evidence.
- Added optional **Sensorimotor Imagery & Embodiment** from the verified
  Lancaster Sensorimotor Norms: six perceptual modalities, five action
  effectors, source SDs, published composites, exclusivity, dominant
  dimensions, token/type and stopword scopes, cumulative/per-100 loads,
  line/stanza trajectories, coverage, provenance, CSV audit files, and a
  narrative Word report.
- Extended the same sensorimotor engine to Project / Corpus and Personal
  Corpus persistence and comparison, and expanded Lexicon Explorer with every
  available Lancaster field rather than a reduced summary.
- Renamed the one-text report family to **Lexical Character, Imagery &
  Embodiment** and added definitions and cautions that distinguish
  context-free lexical norms from contextual imagery, intention, and reader
  response.
- Replaced the Light/System appearance choices with six persistent,
  contrast-tested themes: **Classic**, **Dark**, **Lavender**, **Ocean**,
  **Crimson**, and **Forest**. Existing Light and System preferences migrate
  safely to Classic; the selected theme remains UI-only and does not affect
  analysis or publication-light exports.
- Extended semantic theme styling to dropdown menus, popovers, tooltips,
  dialogs, sidebar controls, inputs, buttons, and disabled/hover states, with
  automated contrast checks across all six palettes.
- Added the first VerseMap reference-corpus source pipeline: tracked
  `resources/VerseMap_Reference_Corpus/<Poet Name>/*.txt` folders, exact and
  canonical SHA-256 evidence, stable poet/poem IDs, a deterministic CSV
  manifest and release record, review warnings, blocking validation, and
  no-write freshness checks.
- Added one-click Windows and macOS VerseMap reference updaters plus a
  maintainer guide for adding a poet, validating the corpus, and committing
  the same portable release to local and cloud repositories.
- Completed the public-facing VerseMap analytical layer in Single Poem and
  Project / Corpus: pinned Standard Profile 1.0 extraction, coverage-aware
  feature weighting, deterministic PCA map coordinates, reference-poem and
  reference-poet neighbors, project/work comparisons, schema-4 persistence,
  CSV audit data, and a narrative Word report.
- Removed pronunciation and every Sound & Form measure from VerseMap at the
  scholar's direction. Syllables, stress, meter, rhyme, refrain, alliteration,
  assonance, and consonance remain independent VerseVAD analyses and cannot
  affect VerseMap positions.
- Extended the reference updater to build and verify per-poem profiles, poet
  centroids, and model metadata, reuse unchanged poem hashes, and checkpoint
  every 25 poems for resumable maintainer updates. It never rewrites source
  poems or substitutes its rough inventory count for the shared tokenizer.
- Added a private-repository `streamlit_app.py` entrypoint and cloud-safe
  configuration for Streamlit Community Cloud. Hosted Project/Corpus data is
  isolated to an unguessable browser-session database, clearly labeled as
  nonpersistent, and appearance choices remain session-only so visitors cannot
  see or overwrite one another's application state.
- Made expanded-section collapse controls fully visible at rest in both themes
  with a contrast-tested circular surface and a sanitizer-safe upward glyph.
- Repaired **Clear text** by moving the text-area state update into a
  pre-rerun widget callback, eliminating the Streamlit session-state error.
- Promoted the complete sentence-level VADER score table from a nested
  expander into the visible sentiment interface and clarified that document
  compound is scored directly rather than averaged from sentence compounds.
- Made every bottom collapse arrow a centered, client-side control that closes
  its section immediately without rerunning the analysis page.
- Replaced the header's wide Appearance, Settings, and Help controls with
  compact circular appearance, gear, and question-mark popover icons.
- Made short textual metric results such as meter names and confidence bands
  scale responsively with their card width, with readable wrapping as a final
  fallback instead of Streamlit's clipped ellipsis.
- Added always-available, offline VADER rule-based sentiment evidence with
  positive/neutral/negative proportions, compound score, conventional threshold
  label, sentence-level audit, package/method provenance, social-media-domain
  cautions, CSV files, and a narrative Word report.
- Added always-available, transparent English readability evidence: Flesch
  Reading Ease, Flesch-Kincaid Grade, Gunning Fog, Automated Readability Index,
  Coleman-Liau, and sentence-qualified SMOG. Contractions and hyphenated forms
  count as one orthographic word; session pronunciation overrides take priority,
  and out-of-dictionary syllables remain explicitly heuristic and auditable.
- Added **Lexical Trajectory** under Affective Evidence with four fixed-color
  line series for token-weighted mean valence, arousal, dominance, and optional
  normalized concreteness by physical line. A stateful source dropdown keeps
  multiple VAD lexicons separate and retains the active report section.
- Expanded Lexicon Explorer to include local VADER polarity and applicable
  word-level readability evidence in both the interface and printable Word
  report, while reserving document-level readability formulas for analyzed
  poems or texts.
- Renamed the relevant report panels to **Emotion Association, Intensity &
  Sentiment** and **Acquisition & Readability**, added complete CSV/DOCX export
  coverage, and kept missing line and pronunciation evidence missing or
  explicitly estimated rather than neutral.
- Added bottom **Collapse** controls to the default-collapsed Additional
  Optional Models and Analysis Configuration and Methodology panels.
- Strengthened sidebar text, alert, widget, and installation-check contrast
  across every appearance theme without changing analytical state.
- Matched the standalone collapsed-sidebar expand arrow to the Installation
  Check secondary-button foreground, background, border, and hover treatment,
  including Streamlit's current `stExpandSidebarButton` selector.
- Removed provider-specific assistant/product references from runtime comments
  and public documentation, replacing privacy language with service-neutral
  descriptions. Existing Git history is not rewritten.
- Collapsed **Words Needing Attention** by default and placed provisional G2P
  review behind a default-off **Show Out-of-Dictionary Words** control, keeping
  the pronunciation report compact until review is requested.
- Changed Stage 5 contraction handling to look up each preserved complete
  spelling once. Forms such as `you're`, `can't`, `won't`, and `'tis` no longer
  expose linguistic-model fragments such as `'re`, `ca`, `wo`, or `n't` as
  separate out-of-dictionary words. The fragments remain explicit
  `not_eligible` audit rows, and the complete form supplies downstream syllable,
  stress, meter, rhyme/sound, and inherited-form evidence.
- Repaired **Apply Approved Pronunciations and Reanalyze** inside the
  fragment-scoped **Words Needing Attention** panel. A successful dictionary
  selection or approved/edited G2P candidate now requests one full-app rerun,
  allowing the queued session override to rebuild pronunciation, syllable,
  meter, rhyme/sound, and inherited-form evidence instead of merely refreshing
  the review panel.
- Standardized ordinary, form-submit, download, primary, secondary, tertiary,
  hover, and disabled button foregrounds through shared contrast-tested theme
  tokens. Nested Streamlit labels and icons now inherit those explicit colors,
  keeping controls such as **Create project** and **Search installed lexicons**
  legible in both light and dark appearance modes.
- Made the optional one-text **Workspace Name** blank by default and confirmed
  that temporary analysis does not require it. Textarea keyboard/mouse focus
  now outlines the complete poem-input boundary instead of appearing as a
  stray blue line inside the field.
- Promoted **Words Needing Attention** to title case and added explicit
  retained-CMUdict candidate selection. Applying one or more choices writes
  reversible session overrides and automatically recalculates pronunciation,
  meter, rhyme/sound, and inherited-form evidence.
- Added local, review-only US-English G2P candidates for words absent from
  CMUdict. Such words retain `unmatched` status and missing syllable/stress
  evidence until the user explicitly approves or edits the provisional
  ARPAbet. **Leave explicitly unresolved** is the default; approval writes a
  source-labeled session override before dependent evidence is recalculated.
- Isolated the Inherited Form report as a Streamlit fragment so selecting a
  profile in **All Inherited Forms** refreshes only that report and no longer
  recollapses the surrounding Sound & Form sections.
- Expanded Inherited Form Analysis from the initial ten-profile foundation to
  a 169-profile, source-documented registry with automatic, partial, and manual
  assessment modes. The no-match view now shows ten nearest profiles while the
  **All Inherited Forms** selector and exports retain every profile, its
  traditional definition, requirements, weights, sources, limitations, and
  poem-specific evidence.
- Promoted **Analysis Configuration and Methodology** to its own title-cased,
  bordered section and grouped additional optional models into a prominent
  default-collapsed panel to reduce initial page length.
- Added a **Structural Count Summary** to **Lexical & Structural Measures** with
  average words per nonblank physical line, average words per stanza, and
  average nonblank physical lines per stanza, each paired with its within-poem
  population standard deviation. The shared typed engine, corpus-persisted
  document metrics, scholar summary, CSV/Word exports, and validation fixtures
  now expose the same calculations.
- Standardized all 103 interactive result tables on a shared renderer that
  preserves Streamlit's fixed header row and pins the leftmost data column
  during horizontal scrolling across Single Poem, Other Text, Project / Corpus,
  PoetryID, and Lexicon Explorer views. Calculations, sorting, formatting, and
  exports are unchanged.
- Replaced the one-text horizontal report-family control with a persistent
  dropdown, made every large report panel initially collapsed while preserving
  independent multi-panel expansion, and made Streamlit's native sidebar
  collapse/restore affordance visible and high-contrast so the wide workspace
  automatically reflows on Windows and macOS browsers.
- Moved **Dispersion of Matched Ratings** out of the token/type mean comparison
  and into a standalone Affective Evidence VAD section directly after the VAD
  definitions, without changing the population-standard-deviation calculation.
- Replaced rerun-resetting one-text report tabs and Project / Corpus tabs with
  state-backed, responsive section controls. Lexicon, token-scope, weighting,
  and other display changes now retain the active section, and preparing
  downloads remains in Export & Help without browser-specific scripting.
- Added independent PoetryID VAD-source, token-scope, and token/type-weighting
  result selectors. New one-text and corpus configurations select both
  all-matched and stopword-excluded evidence by default while preserving
  unmatched vocabulary as missing and keeping every combination separate.
- Repaired Project / Corpus deletion so the destructive action runs in the
  button callback before expensive tab rendering, clears the deleted selector
  state, and reruns onto another project or the empty-project view without an
  `Unknown project` error.
- Expanded Project / Corpus VAD reporting with a pooled matched-token
  population standard deviation, a separate population standard deviation
  across poem means, poem-mean median/range, and side-by-side within-poem VAD
  means/SDs. Corpus CSV and Word exports retain the same distinctions.
- Added a cross-platform in-place update guide for GitHub Desktop and Terminal,
  including clone detection, guarded fast-forward pulls, locked dependency
  synchronization, preservation of ignored local data, and ZIP migration.
- Standardized user-facing analysis exports on UTF-8 CSV data and narrative
  DOCX reports. JSON, TXT, and corpus XLSX analysis exports were replaced by
  complete CSV audit tables; ZIP remains a container for related files.
- Replaced the nested poem-document JSON with explicit `processing_*.csv`
  tables and added a comprehensive one-text report, module-specific reports,
  and a corpus narrative report.
- Updated the PoetryID direct synthetic validation to its current seven-CSV
  plus one-DOCX export contract instead of the superseded CSV/TXT count.

### Added

- Added on-demand **Hear** controls for every displayed ARPAbet candidate in
  **Words Needing Attention** and Lexicon Explorer. Pinned cross-platform
  eSpeak NG formant synthesis produces each preview locally on Windows and
  Intel/Apple-silicon macOS; the interface labels it as a synthetic
  orientation aid rather than a recording, dialect authority, or analytical
  source.
- Added **Inherited Form Analysis** to Sound & Form with a versioned,
  source-backed registry of ten initial profiles: Elizabethan, Petrarchan, and
  Spenserian sonnets; villanelle; sestina; limerick; an explicitly narrow
  English-language 5–7–5 haiku profile; pantoum; terza rima; and ghazal.
  Weighted evidence reuses the existing pronunciation, performance-aware/fixed
  meter, and graded-rhyme modules and adds ordered refrain, end-word rotation,
  radif/qafia, and line-length detectors. Results separate candidate,
  consistency, coverage, nearest alternative, classification, and
  non-probabilistic confidence; missing evidence is never converted to
  mismatch.
- Added traditional-definition tooltips for every suggested potential form
  match. Each tooltip identifies the conventional markers and the analyzed
  poem's principal agreements and departures; complete definitions, sources,
  limitations, and feature evidence remain in the interface and exports.
- Added the same inherited-form engine to Project / Corpus with per-poem
  candidate, classification, consistency, coverage, confidence, runner-up, and
  margin comparison. Generic schema-4 persistence stores the module result and
  six CSV files plus a narrative DOCX report without JSON.

- First public-release version of VerseVAD.
- Project-local macOS setup, startup, and diagnostics helpers for Apple silicon
  and Intel Macs, using the same universal lockfile, managed Python 3.12,
  loopback-only service, offline ordinary launch, and local research files as
  Windows.
- A core runtime-only setup diagnostic so a public checkout can be installed
  before separately licensed lexicons are downloaded; the in-app/full
  diagnostic continues to report every missing or unsupported resource.
- Safari-oriented CSS fallbacks for text sizing, sticky headers, momentum
  scrolling, overflow containment, narrow workspace navigation, readable
  text-entry sizing, and wrapping action/download buttons.
- A dedicated macOS installation and browser guide plus cross-platform launcher
  and responsive-style regression coverage.
- A dedicated PoetryID corpus table comparing every poem's threshold-based
  categorical profile with its nearest continuous centroid, including
  agreement, both distances, rule-based confidence, and VAD coordinates for
  the selected compatible source/view/weighting group.
- A deterministic printable Lexicon Explorer Word report containing the
  current lookup, match methods, all available lexical and pronunciation
  evidence, derived comparisons, notices, missing-resource states, and source
  provenance.
- Root-level `CITATION.cff` metadata naming Nicky Bennett as the software
  author, linking the canonical VerseVAD source repository, and recording the
  2026-07-24 release date. The DOI remains intentionally absent until a stable
  public identifier exists.
- Source- and analysis-view-specific normalized VAD means inside the one-text
  Part-of-Speech Profile, with token-weighted and type-weighted valence,
  arousal, and dominance shown together; group-level coverage, sparse evidence,
  and mixed-POS published phrases remain explicit.
- `vad_by_part_of_speech.csv` in the complete audit bundle, including
  normalized and original-scale means, matched observation/type/token counts,
  coverage, phrase evidence, and normalization provenance.
- Stage 14 optional performance-aware meter realization above the unchanged
  fixed candidate layer, with source lexical stress, metrical position,
  promotion/demotion, substitutions, caesura, clashes/lapses, pronunciation
  paths, alternate readings, inspectable component scores, and rule-based
  confidence.
- Seven declared, versioned broad meter interpretation profiles plus
  Summary/Standard/Detailed presentation, stanza recurrence, generic
  alternating sequence, rhythmic-organization labels, and trajectory evidence.
  Candidate meter remains the default, and no named stanza-form classifier is
  restored.
- Four always-present performance-aware meter audit exports, a conditional
  scholar-revisions CSV, and the same engine/configuration in Single Poem,
  Other Text, and Project/Corpus work-level analysis.
- Bounded thread-safe preprocessing, module-result, visualization-data, and
  export caches with deterministic dependency fingerprints, validation,
  concurrent duplicate suppression, precise invalidation, timings,
  diagnostics, debugging disablement, clearing, and static-resource release.
- Cached token-independent meter alignment plans while preserving exact Stage
  6 candidate results; on-demand complete exports; ordinary-startup removal of
  development hot reloads; safe corpus cancellation hooks at work boundaries.
- Repeatable synthetic benchmark harness, pre/post performance report,
  candidate-equivalence fixtures, performance-aware synthetic validation, and
  cache/invalidation/corpus/export/interface regression coverage.
- Project development version advanced to `0.18.0.dev0`.
- GPL-3.0-only licensing for VerseVAD code and documentation, with the
  canonical GPLv3 text and package metadata.
- A public resource-installation guide with official source pages, exact local
  destinations, supported SHA-256 values, and third-party license cautions.
- Checksum-aware startup resource notices across all workspaces, unavailable
  source/module filtering, and cached file validation that detects a replaced
  resource without re-hashing unchanged workbooks on every rerun.
- Relocatable Windows setup that detects and safely rebuilds only a stale
  project-local virtual environment after the VerseVAD folder is moved or
  renamed.
- The local repository folder renamed from `ANEW VAD Study` to `VerseVAD`;
  tracked runtime paths and beginner instructions remain location-independent.
- Stage 14 completion validation: `285 passed`, all eleven direct synthetic
  demonstrations, 12 diagnostics, immutable source inspection, supplementary
  resource contracts, the 86-package offline lock/sync, final quick benchmark,
  responsive four-workspace review, GPL/public-package boundary checks, and
  zero-finding Word accessibility audits passed. The canonical DOCX renderer
  was attempted but remains unavailable because LibreOffice/`soffice` is not
  installed; no page-image visual inspection is claimed.
- Poetic Fingerprint Stage 13 shared application shell with **Single Poem**,
  **Project / Corpus**, **Other Text**, and **Lexicon Explorer** workspaces,
  current-version context, visible appearance, settings, and help controls.
- Central semantic appearance design tokens, measured contrast, visible
  focus, reduced-motion behavior, responsive stacking, stable
  publication-light chart styling, and an ignored application-level appearance
  preference that never enters analytical or project state.
- Explicit Essential, Literary, Sound and Form, Complete, and Custom
  module-selection presets for single-text and corpus work. Presets require an
  Apply action and never overwrite advanced methodology.
- Single-text input metadata, live orientation counts, confirmed clear-text
  action, staged progress, grouped result overview, seven report families, and
  collapsible module sections with visible completion states.
- Other Text reuse of the Single Poem engines and report presentation, with
  poetry-specific sound/form modules visibly marked experimental for prose.
- Project status metrics, searchable/filterable sortable work list with
  analysis status, corpus presets, and the **Analyze Corpus** action.
- Stage 13 pre-implementation interface audit, preference/token/component and
  interface regression tests, visual-validation procedure, and refreshed
  documentation.
- Project development version advanced to `0.17.0.dev0`.
- Stage 13 completion validation: `252 passed`, all ten direct synthetic
  demonstrations, 11 diagnostics, immutable source-lexicon inspection, six
  supplementary resource contracts, the 86-package offline lock check,
  four-workspace browser checks, documentation structure/content, and
  accessibility checks passed. The canonical DOCX renderer was attempted but
  remained unavailable because LibreOffice/`soffice` is not installed; no
  visual-render success is claimed.
- Poetic Fingerprint Stage 12 PoetryID as a dependent, framework-independent
  classifier over completed source-specific normalized VAD results, with no
  re-tokenization, lexicon reload, rematching, or VAD recalculation.
- Canonical 27-profile low/moderate/high VAD registry, versioned default and
  custom-fixed thresholds, continuous centroids, all-candidate Euclidean
  distances, nearest alternatives, inverse-distance relative affinities,
  categorical/centroid agreement, boundary evidence, and rule-based
  non-probabilistic confidence.
- Separate PoetryID results for every selected VAD source,
  all-matched/stopword-excluded view, and token/type weighting, including
  structured sparse/low-coverage/unavailable states and exact upstream
  analysis/source provenance.
- Optional secondary PoetryID lexical character from already completed
  concreteness, SUBTLEX-US Zipf, and Kuperman AoA summaries without changing
  the VAD archetype.
- One Poem PoetryID controls and tab with continuous VAD first, threshold
  scales, three 3x3 dominance maps, all 27 neighbors, coverage, methodology,
  cautions, and downloads.
- Project/corpus PoetryID batch controls, schema-4 per-work persistence,
  source/view/weighting-compatible profile distributions, map counts,
  continuous VAD positions, token/type sensitivity, workbook fields, and
  checksummed artifact ZIPs.
- Six PoetryID CSV exports and one plain-text report. At the scholar's
  direction, PoetryID has no JSON export.
- Stage 12 synthetic validation command and engine, integration, application,
  export, corpus, repository, workbook, UI compile, and regression tests.
- Project development version advanced to `0.16.0.dev0`.
- Stage 12 completion validation: `245 passed`, all ten direct synthetic
  demonstrations, 11 diagnostics, immutable source-lexicon inspection,
  supplementary resource contracts, offline dependency-lock validation,
  documentation structure/content, accessibility, and diff checks passed.
  The canonical DOCX renderer was attempted but remained unavailable because
  LibreOffice/`soffice` is not installed; no visual-render success is claimed.
- Poetic Fingerprint Stage 11 project/corpus integration for all seven existing
  optional modules, reusing the One Poem engines and shared preprocessing.
- SQLite schema 4 generic immutable module results, scoped metrics, coverage,
  warnings, provenance, checksummed artifacts, explicit batch configurations,
  and separately labeled corpus aggregates.
- Optional-module-only corpus batches, project/corpus module controls,
  non-default Frequency/AoA content-word scopes, collection/work/structural
  views, warnings, coverage, and deterministic per-work audit ZIP downloads.
- Equal-work module summaries, safe observation-weighted summaries, and
  ordered-pooled-token lexical-diversity recalculation without naively
  averaging work-level MATTR, HD-D, or MTLD.
- Seven optional-module Excel sheets for collection means, categorical
  prevalence, work results, structural results, coverage, provenance, and
  warnings.
- Expanded Lexicon Explorer lookup across installed concreteness, SUBTLEX-US,
  Kuperman AoA, and CMUdict resources, including all source fields and
  pronunciation/stress alternatives with explicit missingness states.
- Stage 11 schema, repository, corpus, aggregation, artifact, Explorer,
  workbook, interface, regression, documentation, and synthetic tests.
- Project development version advanced to `0.15.0.dev0`.
- Stage 11 completion validation: `230 passed`, all nine synthetic
  demonstrations, an all-seven-module real-resource corpus smoke run, 11
  diagnostics, source/resource contracts, offline lock, documentation
  structure/accessibility, and diff checks passed; canonical DOCX page
  rendering remained unavailable because LibreOffice is not installed.
- Phase 0 project structure and development safeguards.
- Read-only five-lexicon inspection utility.
- Verified lexicon inventory with hashes, formats, ranges, and citations.
- Initial architecture, methodology, data-model, testing, and user-guide
  documentation.
- Project-local, locked Python 3.12 environment configuration.
- Versioned VAD adapter contract and Warriner et al. adapter.
- Poetry-aware structural token records backed by a pinned spaCy English model.
- Exact-first, possessive, and POS-sensitive lemma matching with provenance.
- Token- and type-weighted original-scale and normalized VAD statistics.
- Coverage calculations and sparse/no-match warnings.
- Atomic token-audit, coverage, summary, and analysis-manifest CSV exports.
- Invented hand-calculated validation corpus and double-clickable Phase 1 test.
- Read-only NRC VAD v1, NRC VAD v2.1, NRC Emotion v0.92, and NRC Emotion
  Intensity v1 adapters with source-contract validation.
- Explicit source-value kinds, dimensions, formats, scales, column mappings,
  phrases, citations, usage notices, adapter versions, and source hashes.
- Deterministic longest-first exact phrase matching with phrase-preferred,
  unigram-only, and exploratory phrase-and-component policies.
- Auditable included, unmatched, ineligible, suppressed-component, and
  suppressed-overlap match records.
- Categorical emotion association counts, unique types, stated denominators,
  structural distributions, and contributing terms.
- Emotion-intensity prevalence plus separate token- and type-weighted matched
  intensity statistics without converting absent pairs to zero.
- Side-by-side cross-lexicon metrics that retain source/family identity and do
  not generate a consensus score.
- Seven-file Phase 2 CSV bundle and double-clickable five-lexicon validation.
- Framework-independent Phase 3 application services for validated UTF-8 text
  import, source selection, one-text analysis, view models, and downloads.
- Local Streamlit workspace with paste and `.txt` import, coverage overview,
  normalized VAD comparison, distinct association and intensity profiles,
  filterable match evidence, unmatched vocabulary, and embedded guidance.
- Friendly scholar-summary CSV and CSV reading guide alongside an in-memory ZIP
  containing the complete seven-file Phase 2 audit bundle.
- Project-local Windows setup, offline launcher, diagnostics launcher, and an
  in-app 11-check self-test.
- Phase 3 service, diagnostics, Streamlit smoke, launcher-safety, and local
  browser validation tests.
- Beginner-facing VAD definitions, midpoint interpretations, all-dimension
  token/type comparison, leave-one-type-out contributors, and cumulative
  normative lexical-load views.
- Explicit cumulative rating, above-midpoint, below-midpoint, net-midpoint, and
  absolute-midpoint totals with matched counts and coverage.
- Persistent local SQLite projects, first schema migration, stable work/text
  version identities, transactional import, extensible metadata, and immutable
  complete corpus batches.
- Browser folder import for UTF-8 `.txt` corpora, collection/author/genre
  filtering, and separate work-level analyses.
- Token-weighted and equal-work-weighted collection VAD profiles with divergence
  reporting for mixed-length collections.
- Persistent unmatched-vocabulary quality-control status, notes, and proposed
  mappings that do not alter completed scores.
- Styled Excel corpus workbook with a reading guide, dual collection profiles,
  work-level token/type VAD, cumulative loads, coverage/emotion data, unmatched
  notes, and text/version provenance.
- Lexicon Explorer with exact word/phrase, explicit lemma and user-mapped
  lookup, non-substituting suggestions, derived component averages, original
  and normalized VAD, emotion results, source provenance, and descriptive
  cross-lexicon spread.
- Warriner source standard deviations and dimension-specific rater counts for
  Lexicon Explorer uncertainty inspection.
- Phase 3.1/4 application, repository, aggregation, workbook, Explorer, adapter,
  and interface validation tests.
- Dual VAD reporting for all matched observations and a separately labeled
  stopword-excluded view in one-poem, corpus, comparison, and export workflows.
- A pinned spaCy English stopword policy with protected negation/modal/
  intensifier terms, surface/lemma audit evidence, custom additions/removals,
  text import/export, version, count, and SHA-256 provenance.
- Content-focused coverage, stopword-sensitivity differences, population
  dispersion, cumulative totals, and midpoint-centered contributor rankings
  for both reporting views.
- A machine-readable `phase2_results.json` alongside the CSV audit files.
- Safe local project deletion requiring an exact, case-sensitive project title
  and deleting only that project's related database records.
- Header workspace tabs for One poem, Projects & corpus, and Lexicon Explorer.
- Comprehensive Word user manual with a maintainable Markdown source and
  repeatable local build script.
- Phase 5 schema-3 review system with named scenarios, immutable scenario
  versions, append-only flag/exclude/map decision revisions, occurrence/work/
  project/global scopes, rationales, and semantic-risk candidate evidence.
- Verified non-overwriting pre-schema-3 database backups and exact
  scenario-version links on immutable corpus batches and analysis runs.
- Unreviewed-versus-reviewed batch comparison with like-for-like coverage and
  VAD deltas, plus revoke, restore, and restore-snapshot workflows.
- Review decisions and methodology provenance in CSV, JSON, ZIP, and optional
  corpus Excel sheets.
- Separate eight-emotion and positive/negative sentiment presentation in the
  one-poem workspace, Lexicon Explorer, readable summary, and Excel construct
  labels.
- Lexicon-independent part-of-speech profiles with universal POS counts,
  lexical-token shares, unique types, examples, one-poem visualization,
  combined/work-level corpus comparison, and Excel export.
- A dedicated beginner-focused Word values and terminology guide with formulas,
  worked examples, interpretive cautions, and reporting templates.
- Framework-independent Poetic Fingerprint module contracts for immutable
  inputs, metrics, coverage, warnings, provenance, and results.
- A read-only local resource manager with root-path containment, SHA-256
  recording, and distinct available, missing, malformed, and unsupported-version
  states.
- A tracked local-resource instruction file while all installed research data
  beneath `resources/` remain excluded from source control.
- Expansion Stage 0 reconciliation documentation covering the current
  architecture, the additive Stage 1 document model, and a future schema-4
  module-result persistence design.
- Expansion Stage 1 immutable `PoemDocument` records for exact section,
  stanza, physical-line, model-sentence, token, dependency, optional entity,
  and orthographic-span structure.
- Explicit shared preprocessing configuration IDs, content/function/other
  token roles, model-vocabulary availability, processing coverage, and
  plain-language warnings.
- One-pass one-poem preprocessing reused across every selected lexicon and
  exposed to future modules through `ModuleInput.from_poem_document`.
- A visible Shared Processing Record in Language Profile and a complete local
  `poem_document.json` in the full audit ZIP.
- Synthetic shared-processing regression cases for exact line endings and
  stanza separators, em dashes, apostrophes, contractions, hyphenated forms,
  capitalization, one-word and punctuation-free lines, archaisms, repeated
  refrains, optional NER, unavailable OOV coverage, and multi-lexicon reuse.
- Read-only Brysbaert, Warriner, and Kuperman concreteness workbook adapter
  with exact SHA-256, worksheet/header, range, rater-field, phrase, collision,
  and expected-count validation.
- Optional framework-independent one-poem concreteness module with exact
  phrase/surface priority, explicit lemma and conservative fallbacks, default
  proper-name exclusion, missing unmatched values, and complete provenance.
- Token-weighted source-scale mean, median, inclusive quartiles, IQR,
  population SD, configurable orientation bands, token/type coverage,
  physical-line/stanza/POS summaries, term rankings, and warnings.
- Dedicated Concreteness Profile, mixed or concreteness-only one-poem runs,
  readable summary rows, five UTF-8 CSV audit files, and a structured JSON
  result.
- Hand-calculated Stage 2 demonstration plus adapter, matching, Unicode,
  missing/empty, repetition, configuration, deterministic, UI, and export
  regression tests.
- Read-only official SUBTLEX-US workbook adapter with pinned SHA-256,
  worksheet/header, row-count, lookup-key, numeric-relationship, source-POS,
  and Zipf-range validation.
- Optional framework-independent one-poem frequency module with exact observed
  word-form priority, explicit lemma and conservative fallbacks, default
  proper-name exclusion, missing unmatched values, and complete provenance.
- Token-weighted median Zipf as the primary frequency summary, plus mean,
  inclusive quartiles, IQR, population SD, range, configurable orientation
  bands, token/type coverage, physical-line/stanza/POS summaries, term
  rankings, rare tail, and warnings.
- A non-default frequency scope limited to exact model tags `NOUN`, `VERB`,
  `ADJ`, and `ADV`, excluding `AUX` and function-word tags with every decision
  retained in the token audit.
- Dedicated Frequency & Rarity profile, frequency-only or mixed one-poem runs,
  readable summary rows, six UTF-8 CSV files, and a structured JSON result.
- Hand-calculated Stage 3 demonstration plus adapter, matching, Unicode,
  proper-name, repetition, all-common, empty/unmatched, configuration,
  deterministic, UI, content-scope, and export regression tests.
- Read-only official Kuperman Age of Acquisition erratum-supplement adapter
  with pinned SHA-256, sheet/header, row-count, unique-key, numeric-range,
  response-count, source `NA`, source `#N/A`, and source-field relationship
  validation.
- Optional framework-independent one-poem Age of Acquisition module with exact
  observed-form priority, explicit lemma and conservative fallbacks, default
  proper-name exclusion, source-unrated evidence, missing unmatched values,
  and complete provenance.
- Token-weighted source-age mean, median, inclusive quartiles, IQR, population
  SD, range, configurable early/middle/later orientation bands, token/type
  coverage, physical-line/stanza/POS summaries, term rankings,
  source-response evidence, and warnings.
- A non-default contextual AoA scope limited to exact model tags `NOUN`,
  `VERB`, `ADJ`, and `ADV`. It remains available because the source paper's
  content-word sampling rule does not establish the grammatical role of a
  polyfunctional spelling in a particular poem occurrence.
- Optional descriptive unique-surface-type Spearman relationships between AoA
  and enabled Frequency or Concreteness results, with paired-type counts,
  multiword-concreteness exclusion, minimum sample requirements, and
  non-causal cautions.
- Dedicated Age of Acquisition profile, AoA-only or mixed one-poem runs,
  readable summary rows, seven UTF-8 CSV files, and a structured JSON result.
- Hand-calculated Stage 4 demonstration plus adapter, matching, Unicode,
  proper-name, repetition, empty/unmatched, source-unrated, configuration,
  deterministic, UI, contextual content-scope, relationship, and export
  regression tests.
- Read-only official CMU Pronouncing Dictionary adapter pinned to an exact
  upstream commit and exact dictionary, phone-inventory, and symbol-inventory
  SHA-256 checksums, with alternative, ARPAbet, stress, count, duplicate,
  vowelless, and malformed-source validation.
- Optional framework-independent one-poem pronunciation/prosody-foundation
  module with exact observed-form lookup, retained dictionary alternatives,
  unique and prosodic-consensus resolution, explicit unresolved ambiguity,
  missing out-of-dictionary values, and complete provenance.
- Validated poem-specific ARPAbet pronunciation overrides with required
  scholarly notes, stable configuration identity, local-symbol validation, and
  visible separation from retained dictionary candidates.
- Resolved-word syllable distributions, complete-line syllable totals,
  word-grouped lexical-stress sequences, primary/secondary stress counts,
  stress density, token/type/line coverage, ambiguity evidence, and warnings.
- Dedicated Pronunciation & Prosody profile, pronunciation-only or mixed
  one-poem runs, readable summary rows, four UTF-8 CSV files, and a structured
  JSON result.
- Hand-calculated Stage 5 demonstration plus adapter, unique/consensus/
  ambiguous/override, Unicode/apostrophe, proper-name, possessive,
  repetition, empty, incomplete-line, invalid-source, deterministic, UI, and
  export regression tests.
- Framework-independent Stage 6 candidate-meter engine with deterministic
  stress-template alignment, configurable penalties and thresholds, retained
  CMUdict stress alternatives, explicit missing-line refusal, stable
  configuration identity, metrics, warnings, and dependency provenance.
- Forty fixed candidates crossing iambic, trochaic, anapestic, dactylic, and
  amphibrachic patterns with monometer through octameter, plus explicit local
  spondaic/pyrrhic substitutions, inversions, feminine/catalectic endings, and
  extra/omitted syllables.
- Optional Meter & Rhythm one-poem workflow, automatic Stage 5 dependency,
  advanced method controls, dedicated reading tab, scholar-summary rows, CSV
  reading guidance, five audit CSV files, and complete JSON result.
- Hand-calculated Stage 6 validation plus regular-pattern, deviation,
  alternative-path, missingness, application, UI, export, and regression tests.
- Stage 6 completion validation: 204 automated tests, every synthetic
  demonstration, all 11 diagnostics, read-only source checks, the pinned
  CMUdict contract, the 86-package offline lock check, and visual inspection
  of all 68 pages across both rebuilt Word guides.
- Framework-independent Stage 7 rhyme and phonological-pattern engine consuming
  retained Stage 5 evidence without predicting or silently selecting a
  pronunciation.
- Robust whole-poem and stanza exact-rhyme schemes; perfect, identical,
  masculine, feminine, multisyllabic, graded slant, eye, and internal-rhyme
  evidence; exact refrain grouping; and explicit unresolved ending coverage.
- Configurable graded-slant components for stressed vowel, final consonants,
  rhyme-part edit, stress alignment, and syllable similarity, retaining
  conservative and maximum scores across pronunciation alternatives.
- Phonemic alliteration, assonance, consonance, per-line densities, dominant
  sound families, exact line/pair evidence, warnings, provenance, and capped
  pair comparisons.
- Optional Rhyme & Sound one-poem workflow with automatic Stage 5 dependency,
  advanced settings, readable scholar summary, seven UTF-8 CSV/JSON audit
  files, and beginner guidance.
- Hand-calculated Stage 7 validation plus engine, application, UI, export,
  ambiguity, missingness, determinism, and regression tests.
- Resource-free narrowed Stage 10 lexical-style engine over the shared
  `PoemDocument`, with normalized observed surface-form diversity, configurable
  MATTR, HD-D, bidirectional MTLD, descriptive TTR, and explicit missing-value
  behavior for unavailable denominators.
- Unicode alphabetic-character word-length statistics/distribution plus
  lexical-token counts for every preserved physical line and stanza, retaining
  blank separator lines with count zero and a complete token audit.
- Optional Lexical Style One Poem workflow, transparent advanced parameters,
  scholar summary, six UTF-8 CSV/JSON audit files, local validation command,
  and beginner guidance.
- Narrowed Stage 10 completion validation: 225 automated tests, all nine direct
  synthetic demonstrations, all 11 diagnostics, read-only lexicon and
  installed-resource checks, the 86-package offline lock check, and rebuilt
  Word guides passing structural/accessibility tests plus local Word opening
  and pagination. Page-image rendering remains unavailable because LibreOffice
  is absent.
- Stage 7 completion validation: 215 automated tests, every synthetic
  demonstration, all 11 diagnostics, read-only lexicon/source checks, the
  pinned CMUdict contract, the 86-package offline lock check, and rebuilt Word
  guides passing structural/accessibility tests plus local Word opening and
  pagination. Page-image inspection remains unavailable because LibreOffice is
  absent and the local Word PDF exporter stalls.

### Changed

- Removed the short-lived common-meter classifier and `meter_schemes.csv` at
  the user's direction while preserving all 40 fixed meter candidates,
  line-level stress alignment, deviations, coverage, and exports.
- Project development version advanced to `0.13.0.dev0`.
- The broader planned Stage 8 visible-structure and Stage 9 syntax/lineation
  work was skipped at the scholar's direction; only line/stanza word counts
  were carried into the narrowed lexical-style stage.
- Project development version advanced to `0.14.0.dev0`.

- The lexicon inspector now distinguishes duplicate source keys from
  case-insensitive lookup collisions.
- Phase 2 identifies NRC VAD v1 and v2.1 as versions of the same family rather
  than independent replications.
- Project development version advanced to `0.5.0.dev0`.
- VAD charts now present derived 0-1 dimensions side by side instead of
  visually stacking different dimensions.
- Warriner's 102 whitespace-containing entries now participate as exact,
  longest-first phrase candidates under the selected policy; the inactive-entry
  warning was removed without changing the source file.
- NRC VAD v1's 132 whitespace-containing entries now participate as exact,
  longest-first phrase candidates under the selected policy; its inactive-entry
  caution was removed without changing the source file.
- The visible interface now uses VerseVAD navigation and a minimal toolbar while
  retaining Streamlit only as the internal local UI framework.
- Corpus database schema version 2 records the stopword methodology and an
  explicit analysis view on every persisted comparison metric.
- Contributor ranking now uses the signed midpoint-centered contribution
  `frequency × (normalized rating - 0.5)` while retaining the mean-change audit
  value.
- Project development version advanced to `0.6.0.dev0`; corpus database schema
  advanced to version 3 and corpus workbook API to version 4.
- Visible navigation, tabs, sections, and workspace headings now use consistent
  title case, including `Projects & Corpus` and `Installation Check`.
- Part-of-speech output merges source `NOUN` and `PROPN` tags into the single
  beginner-facing category `Noun`, retains the original tags in evidence, and
  labels `ADP` as `Preposition`. It also merges `VERB` and `AUX` into `Verb`,
  so auxiliary and copular forms such as `was` remain in the broad verb count.
- Part-of-speech output now pairs the broad reader-facing profile with a
  detailed Universal Dependencies tag breakdown, preserving separate
  NOUN/PROPN and VERB/AUX counts and shares for methodological audit.
- The Poetic Fingerprint plan now names a versioned local SUBTLEX-US source as
  the sole frequency source and excludes `wordfreq` as an alternate or
  fallback.
- A formal centroid/region emotional-profile classifier is explicitly deferred;
  the existing Emotion Profile workspace is not described as that model.
- Project development version advanced to `0.7.0.dev0`; database schema 3 and
  existing affective calculations remain unchanged.
- One-poem analysis now creates the shared processing representation once
  instead of invoking the statistical pipeline separately for each selected
  lexicon.
- Project development version advanced to `0.8.0.dev0`; Stage 2 remains
  additive, in memory, and leaves database schema 3 and affective results
  unchanged.
- Project development version advanced to `0.9.0.dev0`; Stage 3 remains
  additive and in memory, uses only the pinned SUBTLEX-US Zipf source, and
  leaves database schema 3 and existing analyses unchanged.
- Project development version advanced to `0.10.0.dev0`; Stage 4 remains
  additive and in memory, uses only the pinned official Kuperman erratum
  supplement, adds no cognitive or diagnostic claim, and leaves database
  schema 3 and existing analyses unchanged.
- Project development version advanced to `0.11.0.dev0`; Stage 5 remains
  additive and in memory, uses exact pinned local CMUdict files, does not add
  pronunciation prediction, meter, rhyme, or performed-scansion claims, and
  leaves database schema 3 and existing analyses unchanged.
- Project development version advanced to `0.12.0.dev0`; Stage 6 remains
  additive and in memory, exposes nearest configured candidates rather than
  definitive scansion or performed rhythm, and leaves database schema 3 and
  existing analyses unchanged.

### Fixed

- Replaced historical-save widget-key heuristics with an allowlist of durable
  analytical state. Legacy action, upload, download, audio, and future
  unregistered widget values are ignored instead of being assigned through
  Streamlit session state.
- Prevented Arrow serialization warnings when Lexicon Explorer or generic
  Project/Corpus result tables display source fields that legitimately mix
  numbers, text, booleans, and missing values. Only the presentation column is
  rendered as text; typed analytical records and exports remain unchanged.
- Removed Streamlit's default-plus-Session-State widget warnings by giving
  workspace, lexicon, module, preset, and corpus controls one state owner.
- Repaired Dark text-entry foreground/caret/placeholder colors and primary
  Analyze-label contrast across every appearance with
  stable semantic selectors.
- Reduced installed-resource readiness from full eager workbook/dictionary
  parsing to exact checksum identity checks; selected modules still perform
  complete adapter validation before analysis and preserve source hashes.
- Closed the deferred Stage 4 Word-render carryover by exporting both rebuilt
  guides through installed Microsoft Word and inspecting all 63 pages; added
  fenced-code-block support to the shared guide builder after the review
  exposed a literal Markdown fence around the pronunciation override example.
- Preserved ten differently rated Warriner capitalization pairs instead of
  allowing case-insensitive lookup to select one silently.
- Prevented stale Streamlit module state from breaking Lexicon Explorer after
  application-model updates.
- Prevented an already-open Streamlit process from pairing the updated corpus
  page with the older four-argument Excel exporter.
- Prevented stale Streamlit state from pairing Phase 5 or part-of-speech UI
  code with older application and workbook service APIs.
