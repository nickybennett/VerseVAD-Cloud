# Changelog

All notable changes to VerseVAD are recorded here.

## [1.0.0] - 2026-07-24

### Added

- Local Windows and macOS setup, diagnostics, and browser launchers.
- Single Poem, Compare Poems, Other Text, Lexicon Explorer, Saved Projects,
  Personal Corpus, Reference Corpora, Analysis Library, VerseMap, Form
  Library, Corpus Browser, Documentation, and Methodology workspaces.
- Source-specific VAD, emotion association and intensity, VADER sentiment,
  concreteness, SUBTLEX rarity, Age of Acquisition, sensorimotor,
  readability, lexical diversity, structural, POS, pronunciation, meter,
  rhyme, inherited-form, PoetryID, and VerseMap evidence.
- Explicit token/type weighting, stopword scope, content-word scope,
  coverage, eligible counts, warnings, and provenance where applicable.
- Session pronunciation review and overrides with dependent reanalysis.
- CSV statistical exports, narrative Word reports, and full audit bundles.
- Persistent local projects, private Personal Corpus data, explicit saved
  analyses, versioned review scenarios, and contextual research notes.
- Public-domain VerseMap reference corpus and cross-platform reference updater.
- Six persistent high-contrast application themes.
- A Learn → Training workspace with four free learner manuals, four applied
  exercises, and a direct link to the VerseVAD training website; evaluator
  keys, scoring rubrics, and credential materials remain private.

- Offline Open English WordNet 2025+ definitions, examples, synonyms,
  antonyms, and semantic relations near the top of Lexicon Explorer, with the
  complete source sense inventory retained in narrative exports.

### Changed

- Made the comprehensive Word report's primary VAD coverage column follow the
  row's weighting (token coverage for token-weighted profiles and type coverage
  for type-weighted profiles), and clarified pooled lexical-rating versus
  between-work dispersion in corpus reports.
- Corrected comprehensive report module-status classification, corpus VAD
  matched-count reporting, legacy type-weighted denominator metadata, and
  corpus VAD appendix naming/companion-file references across analytical
  workspaces.
- Unified Single Poem, Compare Poems, and Other Text reporting around a shared
  metric-capability contract: categorical associations now expose rates rather
  than invalid dispersion/load statistics; continuous families enforce the
  one-observation dispersion rule; VAD uses explicit midpoint loads and matched
  token/type denominators; and profile-aware charts and lexical contributors
  remain synchronized with their visible scope and weighting.
- Reorganized Complete Audit bundles into numbered analytical domains with a
  richer metric dictionary, coverage summary, structured warnings, resource
  provenance, reproducibility guide, and machine-readable file inventory.
- Expanded comprehensive Word reports with evidence-quality guidance,
  source-specific cross-lexicon comparison, canonical profile labels, and only
  statistically meaningful central tendency, dispersion, and accumulation.
- Corpus/research-project dashboards now apply the universal lexical scope and
  within-poem token/type weighting to both pooled-observation and equal-work VAD
  summaries, expose per-poem and whole-corpus eligible token counts by scope,
  and consolidate repeated warnings without discarding poem-level audit rows.
- Research-project export controls now identify Current View and Complete Audit
  ZIP preparation/downloads explicitly, and the crowded project navigation is a
  persistent dropdown.
- Current View and Complete Audit bundles now include a comprehensive,
  scan-friendly Word report with three-decimal display rounding, explanatory
  metric-family guidance, coverage cautions, analyst/research placeholders, and
  reproducibility information; full-precision and atomic evidence remains in CSV.
- Single Poem, Other Text, Compare Poems, Saved Projects, and Personal Corpus
  now use the same prepare-and-download pattern for a direct comprehensive DOCX
  and a clearly labeled Current View or Complete Audit ZIP.
- Unified compatible lexical reporting around three post-analysis scopes
  (all lexical tokens, stopword-excluded, and content words only) and two
  aggregation weightings (token and type), with one shared report control,
  exact retained-evidence denominators, streamlined dashboards, and explicit
  Current View versus Complete Audit reproducibility bundles.
- Reorganized the public user guide and methodology into task-based guidance
  and auditable metric definitions, formulas, eligibility rules, coverage
  denominators, fixed-profile boundaries, and limitations.
- Replaced the pronunciation dashboard's median syllables-per-line card with
  mean syllables per complete physical line; detailed exports retain both.
- Recovered safely from stale saved-analysis identifiers after a hosted
  redeploy or deletion by detaching only the missing library reference while
  preserving the active text and analysis state.
- Exposed the already-calculated total nonblank physical-line count in the
  Structure report's Structural Count Summary.
- Reworked Compare Poems around actual metric selection, side-by-side poem
  values, max-minus-min range, and separate metric-family tables; within-poem
  dispersion remains visible without an easily confused cross-poem SD column.
- Refined Compare Poems around a consistent means/composites, cumulative-load,
  then dispersion reading order; reduced PoetryID to one active Category Fit
  and Nearest Centroid pair while retaining alternate views in exports.
- Added NRC emotion/polarity association and intensity evidence to both shared
  token scopes, a shared pronunciation-review/reanalysis flow, selectable
  indexed VerseMap reference corpora, and a focused multi-poem PCA dashboard.
- Added shared comparison methodology controls for phrase handling, evidence
  thresholds, lexical modules, PoetryID, pronunciation, meter, and phonology.
- Made Saved Projects and Personal Corpus result explorers show one poem or
  whole corpus, one report/module, and one metric family at a time while
  retaining complete audit records in exports.
- Versioned VV-PRE as `vv-pre-content-word-profile-1.0`: Frequency, AoA, and
  Word Complexity now use token-weighted `NOUN`/`VERB`/`ADJ`/`ADV`
  occurrences with repetition retained, while Line Accessibility continues to
  use all lexical words per nonblank line. Profile identity and component scope
  are retained in the interface, provenance, and exports.
- Consolidated the interface under Analyze, Collections, Explore, and Learn.
- Standardized report navigation, default-collapsed sections, bottom collapse
  controls, frozen table identifiers, and three-decimal interface display.
- Kept full analytical precision in exports while making front-end tables and
  charts easier to read.
- Made category fit the primary PoetryID archetype and nearest centroid the
  secondary candidate.
- Limited inherited-form no-match results to the ten nearest profiles while
  retaining an inspectable complete registry.
- Reorganized public documentation around maintained user, methodology,
  resource, architecture, data-model, testing, and contributor references.
- Made proper-noun inclusion the default for Concreteness, Sensorimotor,
  Frequency, and AoA across first launch and every built-in profile while
  retaining explicit exclusion controls and custom-profile choices.
- Made side-by-side fixed/performance-aware meter analysis the built-in-profile
  default and aligned its full configuration across Single Poem, Compare
  Poems, and Project/Corpus; VerseMap remains pinned to Standard Profile 1.0.
- Cached immutable VerseMap reference indexes by file signature so corpus-map
  reruns avoid reparsing unchanged model CSVs without masking updates.
- Unified custom analysis profiles across every analytical profile selector;
  profiles can now be added, updated or renamed, and deleted from Single Poem,
  Other Text, Compare Poems, Saved Projects, and Personal Corpus analysis.
- Added length-normalized VAD midpoint-deviation rates and one nonredundant
  mean-centered volatility measure—mean absolute deviation—for valence,
  arousal, and dominance across poem, comparison, project, personal-corpus,
  and Corpus Browser reports. Population SD remains available as the
  complementary extreme-sensitive dispersion measure.

- Kept the Interactive Annotation evidence panel beside the poem while a user
  scrolls, with an internal panel scrollbar for long evidence and a stacked
  non-sticky layout on narrow screens.
- Versioned broad lexical eligibility as `versevad-lexicon-eligibility-v2`:
  alphabetically spelled number-like words can participate in VAD, emotion,
  concreteness, SUBTLEX, AoA, sensorimotor, and phrase lookup while retaining
  their original `NUM` and number-like annotations; pure numeric literals
  remain excluded. Narrow content-POS sensitivity views remain unchanged.
- Pinned VerseMap build 1.1.0 to the new eligibility policy and rebuilt its
  reference profiles so submitted and reference poems use the same rules.

### Fixed

- Render completed Single Poem and Other Text results before the automatic
  Analysis Management sidebar refresh, preventing long analyses from appearing
  indefinitely stuck at “Analyzing…” until the user clicks again.
- Split punctuation-stacked word joins such as Poe's `morrow;—vainly` into
  separate lexical and punctuation tokens without changing the source text,
  contractions, apostrophe forms, abbreviations, or character offsets. The
  auditable default preprocessing recipe is now version 2.
- Saved Compare Poems analyses now restore their selected built-in or custom
  profile together with the exact advanced shared configuration used at save
  time; missing custom-profile definitions fall back explicitly to Custom
  without discarding the saved settings.
- Historical-result actions now preserve data deliberately: continuing keeps
  the restored immutable result visible, while preparing reanalysis clears
  only computed output and retains text, metadata, settings, and the saved
  library revision.
- Hosted theme choices now persist per browser across refreshes without using
  one shared server-side preference for every visitor.
- Restored analytical settings no longer duplicate widget defaults or emit
  Streamlit warnings such as the `minimum_matches` warning.
- Eliminated the equivalent default-plus-session-state warning from stopword
  policy selectors restored from saved analyses or shared profiles.
- Replaced historical-save widget-key heuristics with an allowlist of durable
  analytical state. Legacy action, upload, download, audio, and future
  unregistered widget values are ignored instead of being assigned through
  Streamlit session state.
- Streamlit widget-state conflicts when restoring historical saved analyses.
- Saved-analysis deletion, explicit-save controls, and duplicate-click flows.
- Empty and sparse-result table failures.
- Contraction handling in pronunciation review.
- Theme contrast, chart tooltip, button-label, metric-card overflow, and
  responsive navigation issues.
- Training-site primary-link contrast in every persistent theme, including
  nested label and icon colors.
- Corpus and multi-poem result presentation and comparison edge cases.
- Missing bottom-center collapse controls on major Compare Poems and corpus
  report panels.

- Interactive Annotation evidence no longer disappears above the viewport
  when selecting words late in a long poem.
- Interactive Annotation now follows active-lens match granularity for
  alphabetically spelled number words, including shared NRC v2.1 expression
  evidence such as `some one` and separate SUBTLEX unigram evidence.

### Data and licensing

- VerseVAD code and documentation are GPL-3.0-only.
- Most licensed lexicons and normative resources are intentionally excluded
  from the public repository and installed separately by each user.
- The bundled VerseMap reference corpus contains curated public-domain texts.
- The bundled Open English WordNet 2025+ resource remains under CC BY 4.0 and
  the Princeton WordNet license; both license texts and full attribution are
  retained with the packaged data and in `THIRD_PARTY_NOTICES.md`.
