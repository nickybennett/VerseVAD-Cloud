# VerseVAD Implementation Plan

## Completed stacked-punctuation tokenization correction

- [x] Split alphabetic words joined by two or more non-apostrophe punctuation
  marks while retaining each exact punctuation character and source offset.
- [x] Preserve contraction, apostrophe-form, abbreviation, lineation, and
  original-text behavior.
- [x] Version the shared default processing recipe as v2 and validate every
  downstream analytical workspace in public and hosted repositories.

## Completed offline dictionary and annotation-panel refinement

- [x] Package the checksum-pinned Open English WordNet 2025+ database with
  complete CC BY 4.0 and Princeton WordNet attribution.
- [x] Add offline definitions, examples, synonyms, antonyms, and semantic
  relations near the top of Lexicon Explorer without changing poem scores.
- [x] Preserve every available dictionary sense in the printable Word report
  and state that source order is not contextual word-sense disambiguation.
- [x] Keep the Interactive Annotation evidence panel visible while scrolling
  long poems, with a bounded internal scrollbar and narrow-screen fallback.
- [x] Validate public and hosted behavior, exports, licensing boundaries, and
  cross-repository parity with automated and synthetic tests.

## Completed saved-result and hosted-theme reliability pass

- [x] Keep restored immutable results visible when the historical notice is
  dismissed, without a second rerun or state loss.
- [x] Prepare current-version reanalysis by clearing only computed output while
  retaining restored text, metadata, settings, and the saved revision.
- [x] Restore analytical widget settings without duplicate-default warnings.
- [x] Persist hosted appearance per browser across refreshes without a shared
  server-side theme preference, using a refresh-stable URL value with the
  browser cookie retained as a fallback.
- [x] Cover both historical actions, warning-free restoration, cookie safety,
  documentation, and hosted/public parity with automated tests.

## Completed public training workspace

- [x] Add **Learn → Training** to the shared local/hosted navigation and sidebar.
- [x] Describe the four free VerseVAD courses and link prominently to
  `versevad.org/training`.
- [x] Package only the four learner manuals and four applied analysis exercises
  for public download.
- [x] Keep evaluator answer keys, scoring rubrics, certificates, and private
  instructional source files outside the repository and application routes.
- [x] Record the owner decision to defer automated and rendered-document
  validation for this packaging pass.

## Completed focused Compare Poems dashboard refinement

- [x] Limit visible PoetryID comparison evidence to the active shared scope,
  weighting, and one identified source: Category Fit then Nearest Centroid.
- [x] Order VAD, concreteness, frequency/rarity, sensorimotor, AoA, and
  readability families from headline means/composites through cumulative loads
  to within-poem dispersion.
- [x] Retain NRC emotion, positive/negative association, and emotion-intensity
  evidence under all-matched and stopword-excluded comparison views.
- [x] Add safe shared pronunciation review and dependent reanalysis while
  directing genuinely poem-specific conflicting readings to Single Poem.
- [x] Replace the repeated VerseMap feature dashboard with one joint PCA plot
  and a concise coordinate/nearest-poem/nearest-poet table.
- [x] Clarify Evidence & Diagnostics as coverage/denominator/method audit rather
  than a second score dashboard; validate interface, exports, and documentation.

## Completed comparison and corpus usability refinement

- [x] Expose shared phrase, evidence, lexical, PoetryID, pronunciation, meter,
  and phonological configuration in Compare Poems.
- [x] Replace opaque source/scale chart navigation with selection by actual
  metric and one fitted side-by-side poem chart.
- [x] Replace normal-view equal-poem mean and cross-poem SD columns with
  maximum-minus-minimum range while retaining full audit calculations and
  within-poem dispersion rows.
- [x] Split comparison results into reader-facing metric families and keep
  coverage/denominator diagnostics focused by analytical panel.
- [x] Make Saved Projects corpus results expose one scope, report, module, and
  metric family at a time while keeping complete records in exports.
- [x] Validate two- and three-poem comparisons, profile restoration, corpus
  scope navigation, exports, documentation, and hosted behavior.

## Completed VV-PRE content-word scoring profile

- [x] Version the fixed calculation as `vv-pre-content-word-profile-1.0`.
- [x] Use token-weighted `NOUN`/`VERB`/`ADJ`/`ADV` occurrences with
  repetitions retained for Frequency, AoA, and Word Complexity.
- [x] Continue to use all lexical words per nonblank line for Line
  Accessibility.
- [x] Keep the score independent of visible Frequency/AoA report settings and
  preserve the profile ID, component scopes, coverage, and source identities.
- [x] Retain historical saved-analysis compatibility through defaults for
  newly recorded audit/provenance fields.
- [x] Validate the calculation, interface, exports, documentation, and hosted
  resource behavior.

## Completed research-workspace architecture Stage 3

- [x] Replace every remaining planned route with a working **Reference
  Corpora**, standalone **VerseMap**, **Form Library**, **Corpus Browser**,
  **Documentation**, or **Methodology** workspace.
- [x] Add a shared reference-corpus registry used by management, browsing, and
  VerseMap rather than duplicating corpus discovery or model loading.
- [x] Keep the built-in public-domain corpus read-only while allowing local
  installations to create, validate, add to, index, and exactly confirm
  deletion of private reference corpora under ignored project storage.
- [x] Add standalone selectable-corpus VerseMap analysis under the pinned
  Standard Profile 1.0, with drafts, saved historical results, research notes,
  and note-aware CSV/Word audit bundles.
- [x] Add read-only corpus contents, release/model identity, coverage,
  dimension distributions, poem profiles, and safely opened source text.
- [x] Turn the complete inherited-form registry into a searchable educational
  library of definitions, requirements, weights, limitations, and sources.
- [x] Add packaged in-application documentation and searchable methodology,
  provenance, VerseMap, form-registry, and data-model readers.
- [x] Ensure every workspace sidebar contains contextual research controls or
  generic workspace information, related navigation, and privacy guidance.
- [x] Keep hosted reference-corpus management read-only and retain user-created
  corpora only in the downloadable local edition.
- [x] Cover private-corpus path safety and lifecycle, all live routes,
  nonblank sidebars, cross-platform styling, documentation, and exports with
  automated and browser validation.

## Completed research-workspace architecture Stage 2

- [x] Implement **Analysis Library** for saved analyses, recoverable drafts,
  historical revisions, and contextual notebooks.
- [x] Use isolated temporary SQLite storage for each hosted session and label
  its nonpersistent lifecycle throughout the interface.
- [x] Serialize immutable results as restricted compressed JSON rather than
  executable pickle data, with software/profile/settings/provenance metadata.
- [x] Autosave changed drafts under stable IDs and preserve anchored notes.
- [x] Add full-text and results-only privacy choices, Save / Save As New,
  revision history, optional project association, and exact-title deletion.
- [x] Reopen historical results without silent recalculation and offer an
  explicit current-version reanalysis path.
- [x] Exclude notes from exports by default; add deliberately selected notes
  to Word, CSV, and Markdown artifacts.
- [x] Make top navigation opaque and fixed, enlarge and responsively space the
  four section labels, and dismiss hover menus when the pointer leaves.
- [x] Cover repository, serializer, notes, exports, navigation, and hosted
  session behavior with automated and live-browser validation.

## Completed research-workspace architecture Stage 1

- [x] Replace the flat workspace switcher with grouped top navigation:
  **Analyze**, **Collections**, **Explore**, and **Learn**, using stable URL
  routes and a shared conditional sidebar shell.
- [x] Keep Personal Corpus local-only, rename Project / Corpus to Saved
  Projects, and reserve clearly labeled routes for later library,
  notebook, corpus-management, and learning stages.
- [x] Expand Compare Poems from exactly two to a dynamic two-through-ten poem
  set with one shared design, poem-level columns, equal-poem means,
  poem-level dispersion, fitted charts, and CSV/Word exports without arbitrary
  B-minus-A framing.
- [x] Replace the legacy presets with six research-oriented profiles and
  hosted-session custom profiles that never save poem text or results.
- [x] Present PoetryID category fit as primary and nearest centroid as
  secondary in one-poem, comparison, and corpus presentation.

## Completed comparison-presentation and display-precision refinement

- [x] Align Compare Poems with the eight-section Single Poem report map and
  default-collapse its familiar analytical subsections.
- [x] Replace zero-baseline raw-value bars with automatically fitted
  side-by-side dot plots and offer zero-centered B-minus-A difference bars.
- [x] Limit front-end tables, mixed-value displays, chart axes, and tooltips to
  at most three decimals without rounding analytical engines or exports.
- [x] Cover report routing, fitted chart domains, mixed table serialization,
  display-only rounding, and export independence with regression tests.

## Completed contrastive poem evaluation

- [x] Add a session-only **Compare Poems** workspace outside the single-poem
  and corpus workflows.
- [x] Enforce one shared configuration and report source-specific A/B values,
  B-minus-A differences, coverage, denominators, missingness, VAD dispersion,
  and cumulative plus per-100 lexical loads.
- [x] Reuse the sensorimotor, affective, lexical, structure, sound, PoetryID,
  inherited-form, and VerseMap engines without duplicating their calculations.
- [x] Add scale-isolated charts, a complete evidence table, CSV export, a
  narrative Word report, documentation, and regression tests.
- [x] Include sensorimotor imagery in Essential, Sound and Form, Literary, and
  Complete presets; include VerseMap in Complete.

## Completed sensorimotor imagery and embodiment module

- [x] Pin the official Lancaster Sensorimotor Norms CSV by exact filename,
  SHA-256, citation, version, and source license without redistributing or
  rewriting the user-installed source.
- [x] Add a strict read-only adapter for all eleven published means and SDs,
  perceptual/action/overall composites, exclusivity, dominant dimensions, and
  percent-known evidence.
- [x] Match longest published expressions before exact surface, conservative
  possessive, and POS-aware lemma fallbacks; keep unmatched concepts missing.
- [x] Calculate token/type-weighted all-matched and stopword-excluded profiles,
  poem-level dispersion, cumulative and per-100 loads, dominant proportions,
  diversity, line/stanza trajectories, coverage, warnings, and provenance.
- [x] Add a dedicated single-text report section, corpus/project persistence
  and summaries, complete CSV/Word exports, and full-field Lexicon Explorer
  lookup with explanatory definitions and cautions.
- [x] Cover the adapter, calculations, phrase and stopword behavior, source
  immutability, exports, corpus reuse, Explorer, and Streamlit interface with
  synthetic and installed-source regression tests.

## Completed persistent multi-theme interface

- [x] Rename Light to Classic, remove System, and add Lavender, Ocean,
  Crimson, and Forest alongside Dark.
- [x] Persist the selected appearance outside analytical/project state and
  migrate legacy Light/System preference files safely to Classic.
- [x] Apply contrast-tested semantic tokens to controls, text, sidebar
  surfaces, menus, popovers, tooltips, dialogs, hover states, and disabled
  states in every theme.
- [x] Keep publication-oriented exports and analytical results independent of
  the active interface theme.

## Completed VerseMap comparative module and reference pipeline

- [x] Establish a narrowly tracked
  `resources/VerseMap_Reference_Corpus/<Poet Name>/*.txt` convention without
  exposing licensed lexicons, personal corpora, projects, or private texts.
- [x] Add a deterministic updater that validates UTF-8 source files without
  rewriting them, assigns stable poet/poem IDs, records exact and canonical
  hashes, and creates an auditable CSV manifest and release identity.
- [x] Keep questionable fragments, duplicate texts, and book-length files
  visible as review warnings while reserving blocking errors for invalid,
  empty, missing, or cross-platform-colliding source files.
- [x] Add beginner-friendly Windows and macOS launchers, a no-write check mode,
  synthetic regression tests, and a tracked-corpus freshness test.
- [x] Document the add-folder, update, review, commit, and push workflow for
  synchronized local and cloud repositories.
- [x] Pin Standard Profile 1.0 with content-word VAD, emotion associations,
  concreteness, SUBTLEX rarity, AoA, lexical character, content POS, and
  normalized line/stanza structure.
- [x] Exclude pronunciation and all Sound & Form evidence from VerseMap so
  dictionary alternatives cannot affect its coordinates or distances.
- [x] Build per-poem profiles, poet centroids, weighted PCA display
  coordinates, full-space neighbor distances, coverage, and resumable
  hash-based update checkpoints.
- [x] Add optional Single Poem and Project / Corpus report sections with
  responsive maps, nearest comparisons, methodology, CSV data, Word reports,
  and schema-4 project persistence.

## Completed private Streamlit Community Cloud preparation

- [x] Add a root `streamlit_app.py` entrypoint without changing the public
  repository or the ordinary Windows/macOS launch paths.
- [x] Retain the locked Python 3.12 environment and verify that the bundled
  eSpeak NG dependency provides a compatible Linux wheel.
- [x] Remove local-only server binding from the private cloud configuration.
- [x] Isolate hosted Project/Corpus databases by browser session, describe
  their nonpersistent lifecycle in the interface, and keep appearance settings
  session-only.
- [x] Add deployment, configuration, and session-isolation regression tests.

## Completed interface interaction refinements

- [x] Clear the active text through a widget callback before Streamlit recreates
  the text area, avoiding mutation of an already-instantiated widget.
- [x] Display sentence-level VADER scores directly in the sentiment section and
  distinguish them from the independently calculated document compound.
- [x] Replace rerun-driven bottom collapse actions with centered, accessible,
  client-side controls that close their parent expander immediately.
- [x] Convert Appearance, Settings, and Help into compact circular header
  popover icons with responsive light/dark styling.

## Completed compact bottom-collapse controls

- [x] Replace the full-width front-page collapse actions with accessible,
  compact upward-arrow icon controls.
- [x] Add the same bottom action to every large one-text report expander while
  retaining independent expansion and default-collapsed behavior.
- [x] Preserve the selected report family and use stable per-workspace section
  state when a bottom icon forces its section closed.

## Completed responsive metric-result typography

- [x] Scale metric-result text with the available card width while preserving
  the existing metric-card dimensions and visual hierarchy.
- [x] Remove Streamlit's single-line ellipsis behavior and retain wrapping as a
  fallback for unusually long categorical results.
- [x] Verify the shared rule across all appearance styles so meter,
  confidence, classification, and other metric-card outputs inherit the fix.

## Completed compact pronunciation review and contraction handling

- [x] Collapse **Words Needing Attention** by default and keep
  **Out-of-Dictionary Words** hidden behind its own default-off reveal control.
- [x] Use preserved full contraction spellings for exact pronunciation lookup
  while retaining model-token components as explicit, excluded audit rows.
- [x] Cover regular, irregular, and leading-apostrophe examples so `you're`,
  `can't`, `won't`, and `'tis` do not produce fragment-level unmatched items.
- [x] Advance pronunciation module/scenario cache identities and verify complete
  contraction evidence remains available to downstream prosody and form
  analysis.

## Completed pronunciation-review fragment rerun repair

- [x] Preserve the fragment-scoped pronunciation review controls for responsive
  candidate selection and audio previews.
- [x] Request a full-app rerun after a valid dictionary or G2P approval so the
  queued override reaches the shared analysis request.
- [x] Verify that applied words leave **Words Needing Attention** and that
  downstream pronunciation-dependent evidence is recalculated.

## Completed cross-theme button contrast audit

- [x] Give primary, secondary, tertiary, hover, and disabled button states
  explicit, shared light/dark foreground and background tokens.
- [x] Cover ordinary, form-submit, and download-button markup, including
  Streamlit's suffixed base-button variants and nested labels/icons.
- [x] Add WCAG AA contrast regression checks and retain semantic workspace
  checks for **Create project** and **Search installed lexicons**.

## Completed pronunciation review and local audible previews

- [x] Leave out-of-dictionary words explicitly unmatched while showing a
  clearly labeled, local provisional G2P candidate that is never used without
  explicit approval.
- [x] Let the user approve the prediction, edit its ARPAbet before approval, or
  leave the word explicitly unresolved; write only approved/edited values into
  reversible session overrides with predictor provenance.
- [x] Add type-level CMUdict-candidate selection under title-cased **Words
  Needing Attention**, copy choices into reversible session overrides, and
  automatically recompute dependent pronunciation, meter, rhyme/sound, and
  inherited-form evidence.
- [x] Add lazily generated, offline eSpeak NG speaker previews for every
  displayed candidate in the one-text workflow and Lexicon Explorer, with
  cross-platform locked wheels and explicit synthetic-audio cautions.
- [x] Make the optional workspace name blank by default and move textarea focus
  indication to the complete input boundary rather than drawing a line inside
  the poem.
- [x] Add IPA-to-ARPAbet mapping, G2P missingness safeguards, WAV, override,
  analysis, interface, styling, dependency, documentation, and cross-platform
  regression coverage.

## Completed structural count summary

- [x] Reuse the existing nonblank-line and stanza lexical-token counts to
  report average words per nonblank line and average words per stanza.
- [x] Aggregate each stanza's audited nonblank-line count to report average
  nonblank lines per stanza.
- [x] Pair all three averages with population standard deviations in the
  Structure interface, typed module metrics, scholar summary, and CSV/Word
  exports.
- [x] Add hand-calculated engine, export, corpus persistence, interface,
  documentation, and manual regression coverage.

## Completed frozen table context

- [x] Route every interactive result table through one shared renderer.
- [x] Retain the grid's fixed header row and pin the first identifying data
  column for horizontal scrolling.
- [x] Preserve table sorting, styling, calculations, and export schemas across
  one-text, corpus, PoetryID, and Lexicon Explorer views.
- [x] Add shared-helper, interface, documentation, and full-suite regression
  coverage.

## Completed compact report navigation and collapsible results

- [x] Present one-text report families in a rerun-stable dropdown while keeping
  the existing responsive Project / Corpus section control.
- [x] Expose Streamlit's native high-contrast sidebar collapse/restore controls
  so the main workspace automatically expands and resizes across supported
  Windows and macOS browsers.
- [x] Start all large report panels collapsed while retaining independent,
  simultaneous expansion.
- [x] Promote matched-rating population dispersion to its own Affective
  Evidence VAD section immediately after the VAD definitions.
- [x] Add interface, styling, cross-platform, and documentation regression
  coverage.

## Completed rerun-stable section navigation

- [x] Replace native report and Project / Corpus tabs, whose selected state was
  unavailable to Streamlit, with session-backed section controls.
- [x] Retain the active section through lexicon, weighting, token-scope, display,
  analysis, and export-preparation reruns.
- [x] Use wrapping, accessible controls without browser-specific JavaScript and
  add Single Poem, corpus, export, Safari/Chrome, and documentation regression
  coverage.

## Completed PoetryID token-scope selection

- [x] Request all-matched and stopword-excluded PoetryID evidence by default in
  the one-text and corpus interfaces.
- [x] Present VAD source, token scope, and token/type weighting as independent
  result controls without merging compatible combinations.
- [x] Preserve unmatched-vocabulary missingness and add interface, integration,
  cross-platform, export, and documentation regression coverage.

## Completed Project / Corpus deletion repair

- [x] Move confirmed deletion into the pre-rerun button callback.
- [x] Clear and defensively reject stale active-project IDs.
- [x] Preserve exact-title confirmation and project-scoped database deletion.
- [x] Add repository, callback, and stale-browser-selection regression
  coverage.

## Completed corpus VAD dispersion and safe-update guidance

- [x] Reconstruct the pooled matched-token population standard deviation from
  compatible work means, population SDs, and observation counts.
- [x] Report the distinct population SD, median, minimum, and maximum across
  poem-level token means without treating missing values as zero.
- [x] Pair normalized valence, arousal, and dominance means with within-poem
  population SDs in the individual-work corpus comparison.
- [x] Add both dispersion levels to corpus CSV and narrative Word exports with
  explicit interpretive boundaries.
- [x] Document safe in-place updates through GitHub Desktop and Terminal on
  Windows and macOS, including clone detection and ZIP migration.
- [x] Add hand-calculated, missingness, export, interface, and documentation
  regression coverage.

## Completed Lexicon Explorer Word export

- [x] Add a deterministic printable DOCX report for the current Explorer
  lookup.
- [x] Include all available affective, supplementary, pronunciation,
  comparison, notice, missingness, and provenance evidence.
- [x] Add a direct download control, focused regression coverage, and aligned
  documentation.

## Completed PoetryID corpus comparison

- [x] Add a selected-group per-poem table that keeps the categorical PoetryID
  profile and nearest continuous centroid side by side.
- [x] Report agreement, nearest and categorical distances, rule-based
  confidence, and continuous VAD coordinates without presenting either result
  as a definitive emotional identity.
- [x] Add focused regression coverage and align the user documentation.

## Completed export-policy overhaul

- [x] Standardize visible analysis downloads on UTF-8 CSV data and narrative
  DOCX reports, using ZIP only as a multi-file container.
- [x] Replace JSON/TXT result artifacts, the nested poem-document JSON, and the
  corpus XLSX workbook with complete CSV audit tables.
- [x] Add a comprehensive one-text report, module-specific reports, and a
  corpus report; update the interface, documentation, and regression coverage.

Last updated: 2026-07-26

Status markers: `[x]` complete, `[ ]` pending, `[~]` in progress, `[?]` human
review required.

## Phase 0 - Inspection and planning

- [x] Inspect the repository without modifying source lexicons.
- [x] Identify the five supplied lexicon packages and their primary files.
- [x] Inspect supplied README files and relevant research-paper PDFs.
- [x] Record versions, formats, scales, counts, citations, and usage terms.
- [x] Compute source-file hashes and run structural validation.
- [x] Document architecture, methodology, data model, and testing strategy.
- [x] Create repository safeguards and an initial package/test structure.
- [x] Record unresolved scholarly, licensing, and provenance questions.
- [x] Create a source-control checkpoint if repository initialization is
  available in the working environment.

### Phase 0 exit criteria

- [x] No supplied lexicon file changed.
- [x] All five primary source files are readable and within documented ranges.
- [x] No malformed rows, blank terms, or duplicate source primary keys were
  found; ten Warriner case-insensitive lookup collisions were documented.
- [x] Phase 1 can begin without a data-format blocker.

## Phase 1 - Minimum validated engine

- [x] Define a versioned adapter interface and validation result model.
- [x] Implement the first VAD adapter using a synthetic fixture before the
  full source file.
- [x] Preserve line and stanza structure during tokenization.
- [x] Add exact normalized matching, conservative possessive normalization,
  and POS-sensitive lemma fallback.
- [x] Produce a token-level audit table with match provenance.
- [x] Calculate coverage and token- and type-weighted VAD summaries.
- [x] Export the token audit, coverage, summaries, and manifest to CSV.
- [x] Add hand-calculated validation cases and automated tests.
- [x] Document exactly how the first engine can be tested.

### Phase 1 exit criteria

- [x] The invented validation example reproduces all hand-calculated counts and
  means.
- [x] The local supplied Warriner source passes its adapter contract and works
  end to end without source-file modification.
- [x] Exact entries take priority over lemma entries.
- [x] Unmatched words remain missing rather than receiving neutral scores.
- [x] Case-insensitive source collisions remain separate and unresolved cases
  are sent to review instead of being guessed.
- [x] All Phase 0 and Phase 1 automated tests pass.
- [x] Create the Phase 1 source-control checkpoint.

## Phase 2 - All five lexicons

- [x] Implement and validate the remaining four adapters.
- [x] Retain source-scale values and add explicit derived normalization.
- [x] Implement categorical emotion and intensity calculations.
- [x] Implement longest-first phrase matching and overlap policies.
- [x] Add side-by-side cross-lexicon results without a default consensus score.
- [x] Add a double-clickable five-lexicon validation and audit export.

### Phase 2 exit criteria

- [x] All five private source files pass their adapter contracts and known
  SHA-256 checksums without modification.
- [x] NRC VAD v1 retains its 0-1 source scale; NRC VAD v2.1 retains -1-1 source
  values and separately derives `(original + 1) / 2` values.
- [x] Longest-first phrase selection, suppressed overlaps, and all three phrase
  policies reproduce hand-calculated fixtures.
- [x] Categorical associations state both lexical-token and matched-bearing-token
  denominators, and category rates are not forced to total 100%.
- [x] Emotion-intensity prevalence remains separate from matched-entry intensity;
  missing word-emotion pairs never become zero observations.
- [x] Cross-lexicon exports remain source-specific and contain no consensus score.
- [x] All Phase 0-2 automated tests and the five-lexicon demonstration pass.
- [x] Create the Phase 2 source-control checkpoint.

## Phase 3 - Local graphical interface

- [x] Add a temporary private workspace, paste/UTF-8 text import, analysis,
  coverage, profile, evidence, guidance, and download views.
- [x] Keep the beginner path visible while exposing phrase policy and sparse
  result controls under advanced methodology settings.
- [x] Add a local Windows setup workflow and double-clickable launcher.
- [x] Add command-line diagnostics and an in-app "Run self-test" control.
- [x] Add a friendly scholar summary and CSV reading guide alongside the full
  seven-file audit bundle.

### Phase 3 exit criteria

- [x] A scholar can paste a poem or choose a UTF-8 `.txt` file, analyze it
  locally with any supplied lexicon selection, and inspect results without
  using the command line.
- [x] The original text, line breaks, source hashes, original ratings,
  separately derived normalized ratings, denominators, and match provenance
  remain traceable.
- [x] VAD sources can be viewed on a documented derived 0-1 scale while
  categorical associations and intensity ratings remain separate constructs.
- [x] The Overview, profile, evidence, guidance, friendly CSV, and full audit
  ZIP use plain scholarly language and avoid claims about a poem's emotion.
- [x] Windows setup is project-local; ordinary startup and analysis are offline
  and usage telemetry is disabled.
- [x] All 62 automated tests, the 11-check diagnostic, synthetic validation,
  and a live beginner-path browser test pass.
- [x] Documentation reflects the tested Phase 3 behavior and limitations.
- [x] Create the Phase 3 source-control checkpoint.

## Phase 3.1 - Interpretation and usability

- [x] Define valence, arousal, and dominance in beginner-facing language.
- [x] Explain each normalized mean relative to the derived midpoint with matched
  counts, coverage, and an explicit lexical-evidence scope statement.
- [x] Display all three token- and type-weighted VAD means side by side.
- [x] Rank the largest leave-one-matched-type-out contributors to each token
  mean with source evidence and examples.
- [x] Add cumulative rating and midpoint-deviation totals without presenting
  them as a measured psychological load on a reader.
- [x] Keep Streamlit internal while using VerseVAD titles, navigation, styling,
  and a minimal hidden-branding toolbar configuration.

## Phase 4 - Corpus and metadata

- [x] Add the persistent SQLite project database and explicit first migration.
- [x] Add browser folder import, preserved text versions, stable IDs, source
  hashes, extensible metadata, grouping, and filtering.
- [x] Analyze each work separately and publish comparisons only after a complete
  immutable corpus batch.
- [x] Add token-weighted and work-weighted collection VAD profiles so long works
  can be influential without being the only collection view.
- [x] Add length-sensitive cumulative normative VAD loads alongside mean-based
  token/type results.
- [x] Add persistent per-text, per-lexicon unmatched-vocabulary quality-control
  notes that do not silently alter analyses.
- [x] Add a readable Excel workbook with collection profiles, work-level data,
  cumulative loads, quality-control notes, and provenance.
- [x] Add a local Lexicon Explorer for exact, phrase, lemma-derived, component,
  mapped, uncertainty, comparison, and provenance views.

### Phase 4 exit criteria

- [x] Imported literary texts, projects, results, notes, and workbooks remain
  local and excluded from source control.
- [x] Pending or failed batches never replace the most recent complete corpus
  comparison.
- [x] Missing words and missing work scores remain missing rather than neutral.
- [x] Warriner whitespace-containing entries participate as audited exact phrase
  candidates without modifying the supplied source file.
- [x] Automated calculations reproduce a deliberately divergent long/short-work
  example for token- and work-weighted collection means.
- [x] All 78 automated tests, both synthetic validation demonstrations, the
  11-check diagnostic, live browser workflow, and rendered workbook review pass.
- [x] Current behavior, methodology, limitations, and beginner test steps are
  documented.
- [x] Create the Phase 4 source-control checkpoint using the bundled local Git
  executable.

## Phase 4.1 - Dual VAD reporting and project usability

- [x] Report every VAD result for both all matched observations and a separately
  labeled stopword-excluded view.
- [x] Pin and record the spaCy English stopword source, version, active-list
  hash, protected meaning-changing terms, and custom additions/removals.
- [x] Preserve exact published phrase matches as one unit in both views.
- [x] Add content-focused coverage, stopword-sensitivity differences, separate
  contributors, cumulative totals, and population dispersion for both views.
- [x] Persist both views in corpus metrics and include the methodology in CSV,
  JSON, ZIP, and Excel exports.
- [x] Add header workspace tabs and remove the workspace selector from the
  sidebar.
- [x] Add project-scoped deletion requiring an exact, case-sensitive project
  title confirmation.
- [x] Keep the existing visible Windows launcher behavior unchanged.
- [x] Add a comprehensive maintainable Word user manual covering every
  workspace, output, formula, term, safeguard, and troubleshooting path.

### Phase 4.1 exit criteria

- [x] Stopword recognition uses surface and lemma evidence without changing
  exact-first lexicon matching.
- [x] Protected negation, modal, and intensifier terms remain included unless a
  scholar explicitly overrides the protection.
- [x] Custom stopword changes are normalized, auditable, importable, and
  exportable.
- [x] Deleting a project cannot delete another project and is unavailable until
  the exact title is entered.
- [x] Full automated, synthetic, diagnostic, and live browser validation.
- [x] Create a source-control checkpoint using the bundled Git executable.

## Phase 4.2 - NRC VAD v1 phrase activation

- [x] Activate all 132 source-supplied whitespace-containing NRC VAD v1 entries
  as exact, longest-first phrase candidates.
- [x] Keep line/punctuation boundaries, phrase policies, suppressed components,
  source ratings, stopword decisions, and match provenance fully auditable.
- [x] Remove the inactive-entry caution without modifying the source lexicon.
- [x] Update the complete documentation/manual, run full validation, and create
  a source-control checkpoint.

## Phase 5 - Review system

- [x] Add named project review scenarios and immutable scenario-version
  snapshots.
- [x] Add append-only, reversible flag, exclusion, and approved-mapping
  decision revisions with recorded rationales.
- [x] Add occurrence, work, project, and global-within-scenario-use scopes and
  reject conflicting same-scope mappings.
- [x] Apply mappings only after exact, apostrophe/possessive, and lemma
  candidates fail; verify every mapping target as an exact installed entry.
- [x] Preserve review-excluded candidates in the audit while omitting them from
  reviewed aggregates; keep flags non-scoring.
- [x] Add semantic-risk review candidates, optional exact-match review, and
  legacy unmatched-quality-control notes.
- [x] Pin every reviewed batch and run to its exact scenario version and
  decision revisions.
- [x] Add baseline-versus-reviewed immutable batch comparison and review
  decision provenance in CSV, JSON, ZIP, and Excel.
- [x] Create and verify a non-overwriting backup before schema-3 migration.
- [x] Separate positive/negative sentiment from the eight emotion categories.
- [x] Add lexicon-independent part-of-speech quantity/share profiles for one
  poem, combined corpus, work-level comparison, summaries, and Excel.
- [x] Merge common/proper noun tags into one displayed Noun category and label
  English `ADP` output as Preposition while retaining source tags in evidence.
- [x] Merge main-verb and auxiliary/copular tags into one displayed Verb
  category while retaining original `VERB`/`AUX` tags in token evidence.
- [x] Pair broad POS families with a detailed Universal Dependencies tag
  breakdown so every merge remains quantitatively auditable.
- [x] Standardize visible headings and navigation in title case.
- [x] Add a beginner-focused values/terminology Word guide and update the
  comprehensive user manual, methodology, data model, and validation steps.

### Phase 5 exit criteria

- [x] A scholar can retain an unreviewed baseline, apply a named reviewed
  scenario, compare immutable batches, and reproduce the exact active decision
  revisions.
- [x] Revoke, restore, and restore-snapshot operations append history rather
  than rewriting completed decisions, scenario versions, or analysis runs.
- [x] Flags do not change scores; exclusions and mappings change only the
  explicitly selected scenario.
- [x] Occurrence-scoped mappings affect only the pinned token position and
  broader scopes remain explicit in the audit.
- [x] Part-of-speech shares use all eligible lexical tokens independently of
  affective-lexicon coverage and retain the model/version caution.
- [x] Eight-emotion, positive/negative sentiment, and numeric intensity results
  remain separately labeled constructs.
- [x] All 100 automated tests, both synthetic validation demonstrations, the
  11-check diagnostic, source checks, and lock-file check pass.
- [x] Phase 5 documentation and beginner test steps match current behavior.
- [x] Create the Phase 5 source-control checkpoint using the bundled Git
  executable.

## Poetic Fingerprint expansion - Stage 0 reconciliation

- [x] Audit the expansion brief against the implemented Phase 5 architecture,
  data models, tests, exports, and local resources.
- [x] Record that the current Emotion Profile workspace is not a formal
  centroid/region classifier and defer that classifier until its scholarly
  specification is complete.
- [x] Select an explicitly versioned local SUBTLEX-US resource as the sole
  planned frequency source; do not use `wordfreq` as an alternate or fallback.
- [x] Add a framework-independent `AnalysisModule` protocol and immutable common
  module input, metric, coverage, warning, provenance, and result records.
- [x] Add a centralized read-only local resource manager with path containment,
  SHA-256 recording, and available/missing/malformed/unsupported-version states.
- [x] Protect future locally installed research resources from source control
  and document their expected local layout.
- [x] Document the additive Stage 1 `PoemDocument`/structural-unit design and a
  future schema-4 module-result migration without changing schema 3.
- [x] Add synthetic tests for module contracts, missing-value behavior,
  immutability, resource checksums, unsupported versions, malformed data, and
  path containment.
- [x] Run the complete automated suite, both synthetic demonstrations, and all
  local diagnostics; verify documentation and report beginner test steps.
- [x] Create the expansion Stage 0 source-control checkpoint when Git is
  available.

### Expansion Stage 0 exit criteria

- [x] Existing VAD, emotion, corpus, review, interface, and export behavior is
  unchanged.
- [x] Unmatched resource observations remain missing and no generic contract
  requires a neutral numeric fallback.
- [x] New module code is independent of Streamlit and the existing affective
  engine.
- [x] No source lexicon or private literary text is copied, changed, or added to
  source control.
- [x] All automated and local validation checks pass.
- [x] The contract, migration design, plans, changelog, and user-facing project
  status agree.
- [x] Create the expansion Stage 0 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 1 shared processing

- [x] Add an immutable, framework-independent `PoemDocument` that retains the
  exact `TextDocument`, processing configuration, preprocessing provenance,
  structural units, sentences, tokens, dependencies, optional entities,
  orthographic spans, token classifications, coverage, and warnings.
- [x] Parse one exact section plus stanza and physical-line records without
  changing original characters, indentation, blank lines, or line endings.
- [x] Keep NFC lookup normalization separate from source text while preserving
  punctuation, capitalization, token surface forms, lemmas, part-of-speech
  tags, morphological features, and character offsets.
- [x] Record content/function/other/non-lexical roles, proper-noun evidence,
  hyphenated expressions, contractions, apostrophe forms, and model-vocabulary
  availability without inventing missing values.
- [x] Make named-entity recognition an explicit disabled-by-default
  configuration choice and retain sentence/dependency boundary crossings.
- [x] Process each one-poem request once, reuse the exact shared token records
  across all selected lexicons, and make the common document available to
  future `AnalysisModule` implementations.
- [x] Add `poem_document.json` to the full local audit ZIP and show shared
  processing coverage, configuration, provenance, and cautions in Language
  Profile.
- [x] Verify current behavior, methodology, limitations, exports, and
  beginner-friendly Stage 1 test steps in all maintained documentation and the
  rendered Word manual.
- [x] Run the complete automated suite, both synthetic demonstrations, all
  local diagnostics, and the required document render review.
- [x] Create the expansion Stage 1 source-control checkpoint.

### Expansion Stage 1 exit criteria

- [x] Blank stanza separators, em dashes, apostrophes, contractions,
  hyphenated compounds, unusual capitalization, one-word lines,
  punctuation-free poems, archaic forms, and repeated refrains have synthetic
  regression coverage.
- [x] Original source substrings reconstruct exactly from structural records;
  normalized/model-derived forms never overwrite them.
- [x] Unmatched lexicon observations remain missing, and unavailable
  small-model vocabulary coverage remains missing rather than becoming zero.
- [x] POS, lemma, morphology, sentence, dependency, and optional entity records
  are labeled as model outputs, not corrected literary facts.
- [x] Existing exact-first matching, calculations, database schema 3, source
  lexicons, and private literary data remain unchanged.
- [x] All automated and local validation checks pass and the manual render has
  no clipped, overlapping, or broken content.
- [x] Create the expansion Stage 1 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 2 concreteness

- [x] Inspect the locally supplied Brysbaert, Warriner, and Kuperman
  supplementary workbook and paper without changing or redistributing either
  file; record their SHA-256 hashes, source structure, scale, citation, and
  stated limitations.
- [x] Add a versioned, read-only workbook adapter and an independent
  Concreteness `AnalysisModule` using the shared `PoemDocument`.
- [x] Apply exact normalized surface lookup before lemma lookup, followed only
  by documented conservative fallbacks; keep every unmatched observation
  missing and exclude model-tagged proper nouns by default.
- [x] Calculate token-weighted descriptive statistics, configurable extreme
  bands, token and normalized-surface-type coverage, part-of-speech summaries,
  line and stanza summaries, term rankings, and low-coverage warnings.
- [x] Activate exact source-supplied two-word expressions within physical-line
  boundaries and retain the phrase-to-token rating assignment in the audit.
- [x] Add optional one-poem interface controls, a dedicated Concreteness
  Profile, readable summary rows, and complete CSV/JSON audit exports.
- [x] Add synthetic adapter, matching, missing-resource, Unicode, proper-name,
  repetition, empty-input, low-coverage, deterministic-output, and export
  tests, plus an optional local-source contract check.
- [x] Update methodology, architecture, user guidance, validation notes,
  changelog, and the rendered Word manual with exact beginner-friendly test
  steps.
- [x] Run the complete automated suite, synthetic demonstrations, diagnostics,
  source checks, lock-file check, and document render review.
- [x] Create the expansion Stage 2 source-control checkpoint.

### Expansion Stage 2 exit criteria

- [x] The installed 39,954-row source passes its exact adapter contract in
  place, including 37,058 single words, 2,896 two-word expressions, the 1-5
  scale, and the recorded source checksum.
- [x] Exact surface matches take priority over lemma matches; phrases,
  fallbacks, proper-name exclusions, and unmatched tokens remain explicit in
  the token audit.
- [x] Empty and wholly unmatched inputs produce missing aggregates and missing
  coverage rates rather than zero or neutral concreteness scores.
- [x] Thresholds are configurable VerseVAD orientation aids and are not
  attributed to the source paper as validated categories.
- [x] Results are described as normative lexical concreteness evidence, not
  imagery success, readability, literary quality, cognition, or the emotion
  of a poem.
- [x] Existing affective results, review behavior, database schema 3, source
  lexicons, private texts, and local research resources remain unchanged and
  excluded from source control.
- [x] All automated and local validation checks pass, and the manual render has
  no clipped, overlapping, or broken content.
- [x] Create the expansion Stage 2 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 3 lexical frequency and rarity

- [x] Download the official Ghent University SUBTLEX-US Zipf workbook and
  methodological papers into the ignored local `resources/` directory; inspect
  them without modification and record filenames, SHA-256 hashes, source
  structure, scale, citation, and limitations.
- [x] Add a versioned, read-only SUBTLEX-US adapter and an independent
  Frequency `AnalysisModule` using the shared immutable `PoemDocument`.
- [x] Apply exact normalized word-form lookup before explicit lemma lookup,
  followed only by documented conservative fallbacks; leave absent forms
  unmatched rather than assigning frequency zero, and exclude model-tagged
  proper nouns by default.
- [x] Calculate token-weighted median Zipf frequency as the primary summary,
  plus mean, population standard deviation, inclusive quartiles, IQR, range,
  configurable rarity/commonness bands, token/type coverage, content-word-only
  summaries, an optional non-default `NOUN`/`VERB`/`ADJ`/`ADV`-only analysis
  scope, POS/line/stanza summaries, term rankings, and warnings.
- [x] Add optional one-poem interface controls, a dedicated Frequency & Rarity
  Profile, readable summary rows, distribution-ready data, and complete
  CSV/JSON audit exports.
- [x] Add synthetic adapter, matching, missing-resource, malformed-resource,
  Unicode, proper-name, repetition, empty-input, low-coverage, deterministic,
  configuration, export, and optional local-source contract tests.
- [x] Update methodology, architecture, user guidance, validation notes,
  changelog, and both rendered Word guides with exact beginner-friendly test
  steps and corpus-relative interpretation limits.
- [x] Run the complete automated suite, all synthetic demonstrations,
  diagnostics, source checks, lock-file check, and full document render review.
- [x] Create the expansion Stage 3 source-control checkpoint.

### Expansion Stage 3 exit criteria

- [x] The pinned official SUBTLEX-US source passes its exact read-only adapter
  contract in place and retains its recorded source checksum.
- [x] Exact word forms take priority over lemma matches; fallbacks,
  proper-name exclusions, and unmatched tokens remain explicit in the audit.
- [x] Empty and wholly unmatched inputs produce missing aggregates and missing
  coverage rates rather than zero or invented Zipf scores.
- [x] Median Zipf frequency is emphasized, the logarithmic 1-7 scale and
  corpus dependence are explained, and configurable bands are identified as
  VerseVAD orientation aids.
- [x] Results are described as corpus-relative lexical frequency evidence, not
  difficulty, sophistication, accessibility, intelligence, or literary quality.
- [x] No `wordfreq` dependency or fallback is introduced, and values from
  different frequency resources are not combined.
- [x] Existing affective and concreteness results, review behavior, database
  schema 3, source lexicons, private texts, and local research resources remain
  unchanged and excluded from source control.
- [x] All automated and local validation checks pass, and both rendered Word
  guides have no clipped, overlapping, or broken content.
- [x] Create the expansion Stage 3 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 4 age of acquisition

- [x] Download and inspect the official Kuperman, Stadthagen-Gonzalez, and
  Brysbaert erratum supplement and publisher paper without modifying either;
  record their SHA-256 hashes, source structure, rating method, citation, and
  usage limitations.
- [x] Reconcile the paper's content-word sampling description with the actual
  supplement, which includes rated polyfunctional forms that can occur as
  function words in a poem; retain an optional contextual
  `NOUN`/`VERB`/`ADJ`/`ADV` scope rather than assuming every exact spelling
  match is a content-word use.
- [x] Add a versioned, read-only Kuperman adapter and an independent optional
  Age of Acquisition `AnalysisModule` using the shared immutable
  `PoemDocument`.
- [x] Apply exact normalized observed-form lookup before explicit lemma lookup,
  followed only by documented conservative fallbacks; keep unrated and
  unmatched observations missing and exclude model-tagged proper nouns by
  default.
- [x] Calculate mean, median, population dispersion, inclusive quartiles, IQR,
  range, configurable early/later orientation bands, token/type coverage,
  part-of-speech, line, stanza, term, and source-response summaries.
- [x] Add optional non-default content-word-only analysis, descriptive
  type-level relationships with enabled frequency and concreteness modules,
  low-coverage and sparse-pair warnings, and stable longitudinal-ready metric
  identifiers without adding a schema migration.
- [x] Add optional one-poem interface controls, a dedicated Age of Acquisition
  Profile, readable summary rows, and complete CSV/JSON audit exports.
- [x] Add synthetic adapter, matching, missing/malformed-resource, Unicode,
  proper-name, function-word-scope, repetition, empty-input, low-coverage,
  deterministic, relationship, configuration, export, and optional
  local-source contract tests.
- [x] Update methodology, architecture, user guidance, validation notes,
  changelog, local resource instructions, and both rendered Word guides with
  exact beginner-friendly test steps and the required non-diagnostic warning.
- [x] Run the complete automated suite, all synthetic demonstrations,
  diagnostics, source checks, lock-file check, and full PDF/Word render review.
- [x] Create the expansion Stage 4 source-control checkpoint.

### Expansion Stage 4 exit criteria

- [x] The pinned official supplement passes its exact read-only adapter
  contract in place, retains its recorded source checksum, and preserves the
  19 source entries without numeric AoA ratings as unavailable values.
- [x] Exact word forms take priority over lemma matches; fallbacks,
  proper-name exclusions, optional contextual content-word exclusions,
  low-response evidence, and unmatched tokens remain explicit in the audit.
- [x] Empty and wholly unmatched inputs produce missing aggregates and missing
  coverage rates rather than zero or an invented acquisition age.
- [x] Configurable early/later bands are identified as VerseVAD orientation
  aids, and source response counts and uncertainty remain distinct from the
  poem-level dispersion of matched normative means.
- [x] Results are described as retrospective normative lexical AoA evidence,
  not word difficulty, grade level, intelligence, familiarity, comprehension,
  or evidence of cognitive impairment or decline.
- [x] Kuperman ratings are not combined with the separate derivative and
  test-based AoA workbooks; existing affective, concreteness, and frequency
  behavior, database schema 3, private texts, and local research resources
  remain unchanged and excluded from source control.
- [x] All automated and local validation checks pass, the downloaded paper has
  been visually verified page by page, and both Word guides have no clipped,
  overlapping, or broken content.
- [x] Create the expansion Stage 4 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 5 prosody foundation

- [x] Pin the official CMU Pronouncing Dictionary at an exact upstream commit;
  retain the dictionary, phone inventory, symbol inventory, license, and
  README locally under `resources/pronunciation/` with exact SHA-256 hashes.
- [x] Pin the `pronouncing` and `cmudict` Python packages and record their
  versions while keeping the exact local CMUdict files authoritative at
  analysis time.
- [x] Add a versioned, read-only CMUdict adapter that validates the source
  contract, alternative-pronunciation suffixes, ARPAbet symbols, vowel stress,
  duplicate variants, counts, and checksums without rewriting the source.
- [x] Add an independent optional pronunciation/prosody-foundation
  `AnalysisModule` using the shared immutable `PoemDocument`.
- [x] Preserve every dictionary pronunciation candidate. Resolve a unique
  candidate directly; resolve multiple candidates only when they agree on
  syllable count and lexical-stress sequence; otherwise keep the token
  explicitly ambiguous until a scholar override selects a pronunciation.
- [x] Keep out-of-dictionary, ambiguous, non-lexical, and invalid-override
  observations missing rather than fabricating a pronunciation, syllable
  count, stress pattern, or numeric confidence.
- [x] Add validated, poem-specific scholar pronunciation overrides with
  explicit ARPAbet phones, stress, note/rationale, configuration identity, and
  audit provenance.
- [x] Calculate syllables per resolved word, complete-line syllable totals,
  mean/median/dispersion across complete lines, lexical stress sequences,
  primary/secondary stress counts, stress density, token/type/line coverage,
  line summaries, and out-of-dictionary/ambiguity evidence.
- [x] Add optional One Poem controls, a dedicated Pronunciation & Prosody tab,
  readable summary rows, complete CSV/DOCX audit exports, and an explicit
  North American English/source-coverage warning.
- [x] Add synthetic adapter, unique/multiple/consensus/ambiguous pronunciation,
  override, Unicode/apostrophe, proper-name, repeated-word, empty-input,
  incomplete-line, invalid-source, deterministic, UI, export, and installed
  local-source contract tests.
- [x] Add a hand-calculated Stage 5 validation command and exact
  beginner-friendly interface steps.
- [x] Update methodology, architecture, data model, user guidance, lexicon and
  resource documentation, testing notes, changelog, and both Word guides.
- [x] Run the complete automated suite, every synthetic demonstration,
  diagnostics, source checks, lock-file check, and full Word render review.
- [x] Close the two Stage 4 `[~]` Word-render carryovers after both rebuilt
  guides have been visually inspected page by page.
- [x] Create the expansion Stage 5 source-control checkpoint.

### Expansion Stage 5 exit criteria

- [x] The pinned official CMUdict files pass their exact read-only contracts,
  retain their checksums, and remain excluded from source control.
- [x] All source pronunciations and alternative variants remain auditable;
  VerseVAD never silently selects a materially different syllable/stress
  pattern.
- [x] Unmatched and unresolved tokens remain missing, and incomplete lines do
  not produce deceptively low total-syllable or stress summaries.
- [x] Scholar overrides are validated, explicit, poem-specific, reversible,
  and distinguishable from dictionary evidence.
- [x] Results are described as dictionary-based North American pronunciation,
  syllable, and lexical-stress evidence, not definitive performed scansion.
- [x] Stage 5 does not claim meter or rhyme classification; those remain
  Stages 6 and 7.
- [x] Existing affective, concreteness, frequency, AoA, review, database,
  export, and resource behavior remains unchanged.
- [x] All automated/local checks pass, and both Word guides have no clipped,
  overlapping, or broken content.
- [x] Create the expansion Stage 5 source-control checkpoint.

## Future Poetic Fingerprint stages from the expansion brief

## Poetic Fingerprint expansion - Stage 6 candidate meter and rhythmic regularity

- [x] Define a transparent, configurable candidate-meter method that consumes
  Stage 5 evidence without changing dictionary pronunciation results.
- [x] Compare five primary recurring foot patterns: iambic `01`, trochaic
  `10`, anapestic `001`, dactylic `100`, and amphibrachic `010`.
- [x] Compare every primary pattern at one through eight feet: monometer,
  dimeter, trimeter, tetrameter, pentameter, hexameter, heptameter, and
  octameter.
- [x] Treat spondees `11` and pyrrhics `00` as local substitutions rather than
  ordinary whole-line base meters; report initial inversion, feminine ending,
  catalexis, extra syllables, and omitted syllables separately.
- [x] Use deterministic sequence alignment with configurable mismatch,
  insertion, omission, secondary-stress, function-word-promotion, inversion,
  feminine-ending, and catalexis costs.
- [x] Explore retained CMUdict stress alternatives without silently rewriting
  the Stage 5 pronunciation decision; retain the candidate-specific selected
  stress path and refuse lines with missing source pronunciation evidence or
  unmanageably many combinations.
- [x] Report the closest fixed pattern/foot-count candidate, dominant pattern
  family, alternative candidate, line-level fit, whole-poem fit, rule-based
  categorical confidence, matching-line proportion, deviation counts,
  recurring-pattern regularity, and fit variability.
- [x] Remove the short-lived common-meter comparison at the user's direction
  before Stage 7; retain all 40 fixed pattern-by-foot-count candidates and
  their line evidence.
- [x] Add an independent framework-free Stage 6 module, stable metrics,
  configuration identity, dependency provenance, warnings, and complete line
  and candidate audit records.
- [x] Add One Poem controls and a dedicated Meter & Rhythm tab with method,
  coverage, candidate ranking, line-level evidence, deviations, cautions, and
  provenance.
- [x] Add readable scholar-summary rows and complete UTF-8 CSV/JSON audit
  exports.
- [x] Add tests before completion for regular iambic pentameter, trochaic
  tetrameter, anapestic and amphibrachic lines, feminine endings, initial
  inversion, catalexis, spondaic/pyrrhic substitutions, alternative
  pronunciations, mixed line lengths, free verse, ambiguity, missing
  pronunciation evidence, empty input, deterministic output, UI, exports, and
  regression behavior.
- [x] Add a hand-calculated Stage 6 validation command and exact
  beginner-friendly interface steps.
- [x] Update methodology, architecture, data model, user guidance, testing
  notes, changelog, roadmap, and both Word guides.
- [x] Run the complete suite, every synthetic demonstration, diagnostics,
  source checks, lock-file check, and full Word render review.
- [x] Create the expansion Stage 6 source-control checkpoint.

### Expansion Stage 6 exit criteria

- [x] Every result says closest or candidate meter and never definitive meter
  or performed rhythm.
- [x] Pattern and foot count remain separate fields even when combined into a
  readable label.
- [x] Missing pronunciation evidence produces missing line scansion and
  explicit coverage loss, never an invented stress or neutral fit.
- [x] Multiple pronunciation alternatives remain visible, and a metrically
  preferred path is not promoted to a dictionary or performance fact.
- [x] Fit is a documented alignment similarity, and confidence is a
  rule-based category rather than a calibrated probability.
- [x] Mixed/irregular assessment remains available when evidence is sparse,
  the nearest candidates are weak, or alternatives are too close.
- [x] Existing pronunciation, affective, concreteness, frequency, AoA,
  review, database, export, and resource behavior remains unchanged.
- [x] All automated/local checks pass, and both Word guides have no clipped,
  overlapping, or broken content.
- [x] Create the expansion Stage 6 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 7 rhyme and phonological patterns

- [x] Add a framework-independent Stage 7 module that consumes the exact Stage
  5 pronunciation result without changing or silently resolving it.
- [x] Extract the last lexical word and robust rhyme part for each physical
  line, preserving stanza boundaries, missingness, and materially different
  dictionary alternatives.
- [x] Build whole-poem and stanza end-rhyme schemes from robust perfect or
  identical rhyme groups, using `x` for analyzable ungrouped endings and `?`
  for unresolved endings.
- [x] Retain perfect, identical, masculine, feminine, multisyllabic, graded
  slant, eye, internal-rhyme, and exact refrain evidence as distinct fields.
- [x] Add a configurable graded-slant heuristic with stressed-vowel, final-
  consonant, rhyme-part-edit, stress-alignment, and syllable-count components;
  retain conservative minimum and maximum alternative-pronunciation scores.
- [x] Add phonemic alliteration, assonance, consonance, per-line densities,
  aggregate densities, dominant sound families, and exact supporting phone
  sequences.
- [x] Keep absent, ambiguous, and source-vowelless endings unresolved, record
  line-ending coverage, warn under sparse coverage, and cap pair comparisons.
- [x] Add optional One Poem controls, automatic Stage 5 dependency handling, a
  dedicated Rhyme & Sound tab, warnings, methodology, and provenance.
- [x] Add readable scholar-summary rows and seven UTF-8 CSV/JSON audit exports.
- [x] Add synthetic engine, application, UI, export, validation, missingness,
  ambiguity, empty-input, configuration, and determinism tests.
- [x] Add the hand-calculated Stage 7 validation command and exact beginner-
  friendly interface steps.
- [x] Update methodology, architecture, data model, user guidance, testing,
  changelog, roadmap, and both Word guides.
- [x] Run the complete suite, every synthetic demonstration, diagnostics,
  source checks, lock-file check, Word structural/accessibility tests, and
  local Word opening/pagination checks; record the unavailable PNG-render
  exception because LibreOffice is absent and Word PDF export stalls.
- [x] Create the expansion Stage 7 source-control checkpoint.

### Expansion Stage 7 exit criteria

- [x] CMUdict is identified as pronunciation evidence; VerseVAD-derived rhyme
  and recurring-sound classifications are not attributed to the dictionary.
- [x] Every result is framed as dictionary/spelling/textual evidence rather
  than a definitive performed rhyme, dialect, intention, or sound effect.
- [x] Slant similarity is documented as a configurable heuristic rather than a
  probability, and slant/eye evidence never silently creates exact schemes.
- [x] Materially different pronunciation alternatives, absent forms, and
  source-vowelless rows remain unresolved unless an explicit Stage 5 scholar
  override applies.
- [x] Unresolved endings reduce coverage and receive no neutral value or
  fabricated rhyme label.
- [x] Existing fixed candidate meter, pronunciation, affective, concreteness,
  frequency, AoA, review, database, export, and resource behavior remains
  unchanged.
- [x] All automated/local software and Word structural checks pass. Both guides
  open and paginate in Word; the absence of LibreOffice and stalled Word PDF
  export prevent the otherwise required page-image inspection, as recorded in
  the validation report.
- [x] Create the expansion Stage 7 source-control checkpoint.

## Later Poetic Fingerprint stages from the expansion brief

- [x] Stage 8 broader visible poetic structure skipped at the scholar's
  direction on 2026-07-24. Only line/stanza lexical-token counts move into the
  narrowed Stage 10 work.
- [x] Stage 9 syntax, enjambment, end-stopping, and lineation skipped at the
  scholar's direction on 2026-07-24.
- [x] Stage 10 narrowed lexical style: lexical diversity, alphabetic-character
  word length, physical-line word counts, and stanza word counts.
- [x] Stage 11: project/corpus module port and foundational longitudinal
  comparison, including expanded all-resource Lexicon Explorer lookup.
- [x] Stage 12: PoetryID dependent VAD-archetype module, lexical character,
  corpus distributions, and accessible visual reporting.
- [x] Stage 13: application-wide design and information-architecture
  runthrough.
- [x] Stage 14: performance-aware meter plus measured speed, caching,
  optimization, and interface-responsiveness pass.

## Poetic Fingerprint expansion - Stage 14 performance-aware meter and optimization

- [x] Read both implementation briefs and audit the existing pronunciation,
  candidate-meter, application, corpus, cache, database, export, and UI paths.
- [x] Record pre-change startup, analysis, memory-oriented, and profiler
  baselines without weakening validation or omitting requested work.
- [x] Preserve the complete Stage 6 candidate-meter layer and add optional
  contextual realized scansion with explicit lexical stress, metrical
  position, promotion/demotion, substitutions, phrasing, caesura, alternatives,
  component scores, confidence, and methodological safeguards.
- [x] Add broad, versioned style profiles that transparently rerank realized
  candidates without rewriting lexical stress or inferring literary period.
- [x] Add poem/stanza inference, generic alternating line-position patterns,
  accentual/syllabic/mixed outcomes, regularity components, and trajectory
  evidence without reintroducing the removed named common-meter classifier.
- [x] Reuse and optimize validated alignment work with bounded caches and exact
  candidate-output equivalence tests.
- [x] Add explicit dependency fingerprints, layered bounded caches, timing and
  cache diagnostics, safe cache management, and precise invalidation.
- [x] Remove ordinary-startup development reloads and defer expensive exports
  and hidden derived content until requested.
- [x] Add safe corpus cancellation/resumption boundaries and cache-aware
  progress while retaining deterministic transactional persistence.
- [x] Add a repeatable benchmark harness and record before/after medians,
  memory-oriented measurements, environment, remaining bottlenecks, and
  performance budgets.
- [x] Extend Single Poem, Other Text, Project / Corpus, schema-4 persistence,
  exports, and the existing design system for the new meter and diagnostics.
- [x] Add candidate equivalence, contextual meter, style, stanza, cache,
  invalidation, corruption, corpus, export, UI, and benchmark-smoke tests.
- [x] Rebuild documentation and both Word guides, then validate desktop and
  narrow layouts, all appearance modes, completed reports, scansion,
  responsiveness, overflow, focus, and browser diagnostics.
- [x] Run the full suite, every synthetic demonstration, diagnostics,
  source/resource and lock checks, benchmark comparison, document checks, and
  `git diff --check`.
- [x] Create the Stage 14 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 15 inherited-form analysis

- [x] Define a versioned ten-profile registry with required, preferred, and
  optional rules, weights, tolerances, traditional definitions, sources, and
  explicit limitations.
- [x] Reuse the shared poem document, pronunciation, meter, and graded-rhyme
  results; do not rescan or duplicate their resource loading.
- [x] Add line/stanza, syllable, ordered refrain, sestina end-word rotation,
  pantoum linkage, terza-rima chaining, limerick proportion, and
  ghazal radif/qafia evidence.
- [x] Separate candidate rank, weighted consistency, evidence coverage,
  required-feature coverage, classification, runner-up margin, and
  non-probabilistic confidence.
- [x] Keep missing dependent evidence missing and lower coverage instead of
  treating it as a failed rule.
- [x] Add source-backed traditional-definition tooltips with poem-specific
  agreements and departures for suggested potential matches.
- [x] Add Single Poem and Project / Corpus presentation through the same
  engine, including a per-poem corpus candidate table.
- [x] Add six CSV audit tables and one deterministic narrative DOCX report;
  do not add JSON.
- [x] Add exact-form, modified-form, missing-evidence, persistence, UI, export,
  and direct synthetic validation coverage.
- [x] Expand the reviewed version-1 foundation to registry version 2.0 with
  169 source-documented profiles and explicit automatic, partial, and manual
  assessment modes.
- [x] Limit the concise no-match ranking to ten nearest profiles while keeping
  every form selectable through the full-registry inspector and available in
  CSV/Word exports.
- [x] Move optional models and methodology settings into prominent,
  default-collapsed panels without changing analysis defaults.
- [x] Select `GPL-3.0-only`, add its canonical license text, and clearly
  separate the software license from user-installed research-source terms.
- [x] Document official resource pages, exact paths/names/checksums, and add
  checksum-aware missing/unsupported-resource alerts and availability filters.
- [x] Rename the repository folder from `ANEW VAD Study` to `VerseVAD` after
  final validation, with a relocatable setup check for stale absolute virtual-
  environment paths.

## Poetic Fingerprint expansion - Stage 13 design and interface

- [x] Audit the existing workspace map, repeated patterns, UI/service
  boundaries, styling architecture, accessibility, dark-mode feasibility,
  proposed components and tokens, affected files, and migration risks before
  implementation.
- [x] Add one semantic appearance design-token system and an ignored,
  application-level appearance preference.
- [x] Add a compact global shell with the four named workspaces, version,
  active-workspace context, visible appearance control, settings summary, and
  help/methodology access.
- [x] Reorganize One Poem and Other Text into clear input, grouped module
  selection, explicit presets, analysis action, overview, report-family
  navigation, evidence/diagnostics, and export.
- [x] Add a grouped overview that points to VAD/PoetryID, lexical character,
  sound/form, structure, coverage, and cautions without replacing the detailed
  evidence.
- [x] Reframe Projects/Corpus with a project status header and consistent
  workspace/result patterns while preserving schema-4 data and batch behavior.
- [x] Apply the shared shell, tokens, status, empty-state, table, and help
  patterns to Lexicon Explorer without changing its lookup services or fields.
- [x] Standardize focus, contrast, reduced-motion, responsive behavior,
  missing-value language, and chart/table containers.
- [x] Add regression tests proving that appearance and layout state do not
  change analytical requests, results, exports, source texts, or project data.
- [x] Update methodology, architecture, user guidance, testing, changelog,
  roadmap, and both Word guides.
- [x] Run the full suite, synthetic demonstrations, diagnostics,
  source/resource and lock checks, visual browser checks in all appearance
  modes, documentation checks, and rendering where installed tools permit.
- [x] Create the expansion Stage 13 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 10 narrowed lexical style

- [x] Record Stage 8 visible-structure and Stage 9 syntax/lineation as skipped
  without implementing their punctuation, typography, repetition, syntactic,
  enjambment, or end-stopping classifiers.
- [x] Add a resource-free, framework-independent `LexicalStyleModule` over the
  shared `PoemDocument`; do not tokenize the poem again.
- [x] Use normalized observed surface forms for diversity; preserve lemmas in
  the audit without silently substituting them.
- [x] Add configurable MATTR, HD-D, and bidirectional MTLD plus descriptive
  token/type counts and plain TTR.
- [x] Keep MATTR/HD-D missing when the poem is shorter than their configured
  denominators and keep undefined MTLD missing rather than infinite or neutral.
- [x] Add Unicode alphabetic-character word-length statistics and distribution;
  do not count punctuation inside a token as a letter.
- [x] Add one row for every preserved physical line, including blank separators
  with zero lexical tokens, plus stanza word-count summaries.
- [x] Add stable provenance, configuration IDs, coverage, warnings, token audit,
  six CSV/JSON exports, scholar summary, reading guide, and ZIP integration.
- [x] Add an optional, off-by-default One Poem checkbox and dedicated **Lexical
  Style** tab with transparent advanced parameters.
- [x] Add hand-calculated synthetic tests and a local validation command.
- [x] Update methodology, architecture, data model, user guidance, testing,
  changelog, roadmap, and both Word guides.
- [x] Run the complete suite, synthetic demonstrations, diagnostics, source
  checks, lock-file check, Word structural/accessibility checks, and document
  render verification where the installed tools permit.
- [x] Create the expansion Stage 10 source-control checkpoint.

### Expansion Stage 10 exit criteria

- [x] The shared lexical-token word unit and its contraction/hyphenation
  implications are plainly documented.
- [x] Plain TTR is labeled length-sensitive and not promoted as the primary
  cross-text comparison measure.
- [x] MATTR window, HD-D sample size, MTLD threshold, token policy, and missing
  conditions are recorded on every result.
- [x] Line and stanza counts reconcile to the document count, and blank physical
  lines remain visible.
- [x] No literary-quality, intelligence, vocabulary-knowledge, education,
  comprehension, or reader-effect claim is made.
- [x] Existing affective, concreteness, frequency, AoA, pronunciation, meter,
  rhyme, review, database, export, and resource behavior remains unchanged.
- [x] All automated/local software and Word documentation checks pass.
- [x] Create the expansion Stage 10 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 11 project/corpus and Explorer

- [x] Add a verified schema-4 migration that preserves schema-3 projects and
  adds generic immutable module results, metrics, coverage, warnings,
  provenance, and audit artifacts.
- [x] Extend corpus batches with exact optional-module selections and
  serialized configurations; permit optional-module-only batches.
- [x] Run selected concreteness, SUBTLEX-US frequency, Kuperman AoA,
  pronunciation, meter, rhyme/sound, and lexical-style modules through the
  existing One Poem engines over each stored text version.
- [x] Persist full per-work module evidence transactionally and expose
  downloadable work-level audit bundles without copying any research source.
- [x] Add collection summaries that distinguish equal-work, defensible
  observation-weighted, categorical-prevalence, and pooled-token-sequence
  calculations; never average rhyme schemes or imply a corpus-wide meter.
- [x] Add per-work and collection module views to Projects & Corpus plus
  dedicated workbook sheets and methodology records.
- [x] Expand Lexicon Explorer across all installed lexical resources:
  affective lexicons, concreteness, SUBTLEX-US, AoA, and exact CMUdict
  pronunciation/syllable/stress candidates.
- [x] Keep resource absence, source-unrated entries, unmatched searches,
  lemma-derived evidence, pronunciation alternatives, and provenance
  explicitly distinct in Explorer.
- [x] Add schema, repository, corpus aggregation, artifact, Explorer,
  application, UI, workbook, migration, and regression tests using small
  synthetic fixtures.
- [x] Update methodology, architecture, data model, user guidance, testing,
  changelog, roadmap, and both Word guides.
- [x] Run the complete suite, every synthetic demonstration, diagnostics,
  source/resource checks, lock-file check, Word structural/accessibility
  checks, and document render verification where installed tools permit.
- [x] Create the expansion Stage 11 source-control checkpoint.

### Expansion Stage 11 exit criteria

- [x] Project/corpus analysis invokes existing module engines and performs one
  shared preprocessing pass per work; no optional calculation is duplicated.
- [x] Completed work and batch results are immutable and tied to exact active
  text versions, configurations, source hashes, and software/module versions.
- [x] Missing module observations remain missing; failed or incomplete batches
  never replace the latest complete comparison.
- [x] Collection summaries state work and observation counts, preserve work
  boundaries, and label exploratory aggregation methods.
- [x] Lexical-diversity comparisons use matching parameters; pooled values are
  calculated from the ordered pooled token sequence rather than averaged from
  work-level MATTR, HD-D, or MTLD values.
- [x] Meter and rhyme remain work-level candidates/evidence; collection views
  summarize prevalence or distributions without inventing one corpus-wide
  scheme or definitive meter.
- [x] Explorer reports only source-supplied or direct dictionary evidence,
  clearly labels lookup method and missingness, and makes no contextual claim.
- [x] Existing affective, review, One Poem, source-resource, and export behavior
  remains unchanged.
- [x] All automated/local software and Word documentation checks pass, with
  the canonical page-image renderer attempted but unavailable because
  LibreOffice is not installed.
- [x] Create the expansion Stage 11 source-control checkpoint.

## Poetic Fingerprint expansion - Stage 12 PoetryID

- [x] Add a framework-independent PoetryID engine that consumes completed
  normalized VAD results and never tokenizes, loads a lexicon, matches text, or
  recalculates VAD independently.
- [x] Register all 27 canonical low/moderate/high valence, arousal, and
  dominance combinations with stable IDs, names, descriptors, narrative
  summaries, and interpretive cautions.
- [x] Add a versioned default fixed threshold profile plus auditable custom
  fixed thresholds with explicit inclusive boundaries and centroids.
- [x] Keep each VAD lexicon, all-matched/stopword-excluded view, and token/type
  weighting as a separate PoetryID result; never create a consensus profile.
- [x] Retain continuous VAD, categorical levels, categorical assignment,
  Euclidean distances to all 27 centroids, nearest alternatives,
  inverse-distance relative affinities, categorical/centroid agreement,
  boundary proximity, neighbor margin, coverage, and rule-based confidence.
- [x] Keep insufficient or invalid VAD evidence unavailable with a structured
  reason; never insert a neutral score or silently fall back to another source.
- [x] Add optional secondary lexical character from already completed
  concreteness, SUBTLEX-US Zipf, and Kuperman AoA summaries; never let those
  dimensions alter the VAD assignment.
- [x] Add the optional One Poem PoetryID controls and tab with continuous VAD
  first, three dominance maps, threshold scales, neighbors, confidence,
  coverage, lexical character, methodology, cautions, and downloads.
- [x] Add Projects/Corpus PoetryID controls, immutable per-work persistence,
  compatible source/view/weighting distributions, 3x3 map counts, continuous
  work positions, token/type sensitivity, workbook fields, and per-work
  artifact ZIPs through the existing generic schema-4 module tables.
- [x] Add seven UTF-8 CSV/plain-text PoetryID exports. At the scholar's
  direction, PoetryID has no JSON export.
- [x] Add synthetic engine, boundary, missingness, lexical-character, export,
  application, repository, corpus, workbook, UI compile, configuration, and
  regression tests plus a hand-calculated validation command.
- [x] Update methodology, architecture, data model, user guidance, testing,
  changelog, roadmap, and both Word guides.
- [x] Run the complete suite, every synthetic demonstration, diagnostics,
  source/resource checks, lock-file check, Word structural/accessibility
  checks, and document rendering where installed tools permit.
- [x] Create the expansion Stage 12 source-control checkpoint.

### Expansion Stage 12 exit criteria

- [x] Every PoetryID result identifies its exact upstream VAD analysis, source
  hash, adapter version, view, weighting, threshold profile, and configuration.
- [x] Profile names are framed as nearest candidate lexical-affective
  neighborhoods, never as the emotion of a poem, speaker, author, or reader.
- [x] Relative affinity and confidence are explicitly non-probabilistic;
  boundary-sensitive and categorical/centroid-disagreement states remain
  visible.
- [x] Sparse and low-coverage evidence remains unavailable or cautioned, and
  unmatched terms remain missing rather than neutral.
- [x] Corpus distributions never merge incompatible VAD sources, analysis
  views, weightings, or configurations and never declare one corpus identity.
- [x] PoetryID chart data is downloadable as CSV, its report is plain text,
  and no PoetryID JSON is produced.
- [x] Existing VAD, emotion, lexical-semantic, prosody, review, Explorer,
  database, and export behavior remains independently available.
- [x] All automated/local software and Word documentation checks pass, with
  any environment-limited render exception recorded precisely.
- [x] Create the expansion Stage 12 source-control checkpoint.

## Post-release evidence and interface expansion - sentiment, readability, and trajectory

- [x] Add offline VADER document and sentence polarity evidence with published
  conventional thresholds, package provenance, domain cautions, CSV exports,
  and a narrative Word report.
- [x] Add transparent resource-free readability formulas with explicit word,
  sentence, character, syllable, polysyllable, and pronunciation-method
  denominators; keep short-text SMOG missing.
- [x] Reuse approved session pronunciation overrides in readability and retain
  out-of-dictionary heuristic syllables in a default-collapsed attention panel.
- [x] Add source- and token-scope-specific line-level VAD/concreteness
  trajectories without pooling lexicons or filling missing lines with zero.
- [x] Retain the active Affective Evidence report section when the trajectory
  source or token scope changes.
- [x] Add bottom collapse actions to both large front-page configuration
  panels and strengthen dark-sidebar contrast.
- [x] Cover Streamlit's standalone collapsed-sidebar expand control with the
  same contrast-tested secondary-button styling as Installation Check.
- [x] Extend Lexicon Explorer and its printable Word report with every
  meaningful isolated-lookup metric from the new VADER and readability
  engines, while withholding document-level readability formulas.
- [x] Remove provider-specific assistant/product references from tracked source
  and public documentation without rewriting Git history.
- [x] Complete targeted/full automated, export, cross-platform launcher,
  responsive-browser, cloud-entrypoint, and documentation validation in both
  the canonical public and private cloud repositories.
- [x] Create and push matching source-control checkpoints to both repositories.

## Post-release portability - macOS and supported browsers

- [x] Add project-local macOS setup, startup, and diagnostic `.command`
  helpers for Apple silicon and Intel Macs.
- [x] Reuse the universal lockfile, managed Python 3.12, offline ordinary
  startup, loopback-only binding, and disabled telemetry on both platforms.
- [x] Separate core runtime setup diagnostics from optional research-resource
  diagnostics so a public checkout can be installed before licensed datasets.
- [x] Add Safari-safe CSS fallbacks and narrow-layout wrapping without changing
  calculations, exports, or existing Windows launcher behavior.
- [x] Add macOS installation, permission, browser, and troubleshooting
  documentation to the README, beginner guide, architecture, testing guide,
  and comprehensive manual source.
- [x] Run targeted/full automated validation, all synthetic checks, locked
  environment/startup checks, and Word-manual structural/accessibility QA.
- [?] Complete the documented real-Mac Safari/Chrome acceptance checklist;
  Safari and macOS launcher/Gatekeeper behavior cannot be executed on the
  Windows development host.

## Public release 1.0.0

- [x] Promote package, runtime, and offline-lock metadata to version `1.0.0`.
- [x] Add root-level Citation File Format 1.2 metadata for Nicky Bennett.
- [x] Add the canonical GitHub repository URL and 2026-07-24 release date after
  publication; keep DOI and affiliation absent until stable details exist.
- [x] Run public-release metadata tests and the complete automated suite.
- [x] Update release documentation and create the version checkpoint.

## Pre-release repair - startup, widget state, and theme contrast

- [x] Separate fast checksum-aware startup readiness from first-use structural
  parsing without weakening source identity or completed-run provenance.
- [x] Give workspace, lexicon, and preset-controlled widgets one Session State
  owner so Streamlit emits no conflicting default-value warnings.
- [x] Repair text-entry surfaces and primary action-button contrast across
  appearance themes with stable Streamlit selectors.
- [x] Add source-separated VAD-by-part-of-speech rows with both token-weighted
  and type-weighted normalized means, explicit coverage, and mixed-POS phrase
  handling.
- [x] Add resource-loading, widget-state, semantic-token, and rendered contrast
  regression coverage.
- [x] Run targeted, full-suite, synthetic, diagnostic, responsive-browser, and
  cold/warm startup validation.
- [x] Update release documentation and create a source-control checkpoint.

### Pre-release repair exit criteria

- [x] A cold startup hashes configured research resources but does not parse
  whole workbooks or dictionaries before the scholar requests a dependent
  workspace or analysis.
- [x] First use still performs exact adapter-contract validation, and every
  completed result still records the exact source SHA-256.
- [x] No widget is created with both a programmatically supplied Session State
  value and a competing default.
- [x] Editable text and enabled primary action labels meet at least WCAG AA
  normal-text contrast in every appearance theme.
- [x] The one-text Part-of-Speech Profile and detailed audit export report
  token-weighted and type-weighted normalized VAD means without assigning
  neutral values to unmatched evidence or forcing mixed-POS phrases into a
  single grammatical category.
- [x] Existing analyses, projects, exports, resource safeguards, and responsive
  layouts remain unchanged.

## Pre-release repair - Arrow-safe heterogeneous result tables

- [x] Reproduce the Lexicon Explorer Arrow warning with an installed
  SUBTLEX-US result that combines numeric frequency evidence and a textual
  source POS label.
- [x] Convert only heterogeneous display-table values to explicit text while
  retaining typed analytical records, calculations, persistence, and exports.
- [x] Apply the same safeguard to generic Project/Corpus result tables that can
  contain numeric, textual, Boolean, and missing module metrics.
- [x] Add an Arrow-conversion regression fixture covering numeric, textual,
  Boolean, and missing evidence.
- [x] Confirm ordinary Streamlit startup and a real Explorer search complete
  without the reported Arrow conversion traceback.
- [x] Run the full automated suite, focused Arrow fixture, real installed
  Explorer lookup, and clean startup check. At the scholar's direction, stop
  the broader full-resource synthetic rerun because it is disproportionate to
  this display-only repair.
- [x] Create the source-control checkpoint.

## Release polish - profile defaults, parity, and responsiveness

- [x] Prefer mean syllables per complete line on the pronunciation dashboard
  while retaining mean and median in statistical exports.
- [x] Make stale session-only saved-analysis identifiers self-healing after a
  hosted redeploy without discarding the active analysis.
- [x] Include proper nouns by default in the four requested lexical modules
  for every built-in profile while preserving custom-profile state.
- [x] Align full meter/rhythm controls across Single Poem, Compare Poems, and
  Project/Corpus and default built-ins to the side-by-side candidate and
  performance-aware view; preserve VerseMap Standard Profile 1.0.
- [x] Complete major-section bottom collapse controls and Training CTA theme
  contrast.
- [x] Cache the immutable VerseMap reference index by source-file signature
  without changing analysis accuracy or invalidation behavior.

## Cross-cutting later work - Scholarly diagnostics

- [ ] Add anomaly candidates and structured close-reading prompts.
- [ ] Add corpus trends, source-disagreement views, and optional descriptive
  change-over-sequence views.
- [ ] Add additional sensitivity views beyond the completed stopword,
  weighting, phrase-policy, and review-scenario comparisons.

## Cross-cutting later work - Publication support

- [ ] Add polished accessible charts and underlying-data exports.
- [ ] Add methods and reproducibility reports.
- [ ] Add backup/restore, a public-domain demonstration project, full user
  documentation, and accessibility review.

## Decisions deliberately deferred

- definitive primary lexicon;
- universal coverage or minimum-match thresholds;
- Jeffers-specific semantic-shift judgments;
- comparison authors or corpora;
- universal text-length controls;
- negation score adjustment;
- a cross-lexicon consensus score;
- a primary inferential statistical test.

## Human review items

- [?] Confirm the provenance and original documentation of the locally supplied
  Warriner data. The package is a secondary XANEW distribution and does not
  include the original Warriner paper or an independent license file.
- [x] VerseVAD activates Warriner's 102 and NRC VAD v1's 132
  whitespace-containing rows as exact, longest-first phrase candidates at the
  user's request. NRC VAD v2.1 explicitly supports multiword expressions.
- [x] Publication years, approximate dates, and date ranges can be recorded as a
  free text date label at import/edit time; structured date inference is not
  performed.
