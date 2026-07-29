# Testing and Validation Strategy

## Principles

Tests must establish calculation and provenance behavior, not merely that the
program runs. Synthetic fixtures will be small enough to calculate by hand and
will never contain copyrighted poems or redistributed lexicon data.

No phase is complete until its applicable automated tests and manual validation
examples pass.

## Test layers

### Unit tests

Cover pure normalization, token, matching, coverage, aggregation, and formula
functions. These tests should avoid the interface and database when possible.

### Adapter contract tests

Run every adapter against synthetic format fixtures and, locally, against the
user-supplied source file. Verify columns, encoding, keys, duplicates, ranges,
blank terms, malformed rows, category sets, phrase counts, and checksums.

Tests in a distributable repository must not embed restricted source entries.

The Stage 2 workbook contract additionally verifies read-only loading, 39,954
usable entries, 37,058 single words, 2,896 two-word expressions, source rating
and rater-field consistency, normalized-key uniqueness, and exact source hash.

### Integration tests

Exercise text version -> tokenization -> matching -> inclusion -> summary ->
export. Validate stable IDs and drill-down from aggregates to contributing
matches.

### Database and migration tests

Create temporary databases, apply every migration from empty, upgrade from
each supported prior version, verify rollback/failure behavior, and confirm
automatic pre-migration backups.

### Interface smoke tests

Test the beginner path, warnings, disabled actions, empty states, downloads,
and the built-in self-test. Calculation assertions remain in engine tests.
The interface suite also changes the state-backed one-text and corpus section
controls, reruns display selectors, and prepares exports to verify that the
active section is retained rather than reset to the first section.

### Visual checks

Render charts and reports with representative long titles, sparse data,
missing values, grayscale, and color-vision-deficiency checks. Verify that
axes, denominators, lexicons, scenarios, sample sizes, and warnings remain
legible.

## Required synthetic cases

- repeated word showing token versus type weighting;
- exact surface match taking precedence over a different lemma entry;
- regular plural and irregular verb lemma fallbacks;
- participle whose direct entry takes precedence;
- ambiguous form used with different parts of speech;
- apostrophe, possessive, and Unicode punctuation variants;
- longest phrase overlapping shorter phrases and components;
- phrase-preferred, unigram-only, and exploratory double-count modes;
- hyphenated compound direct, variant, component, and unmatched outcomes;
- reviewed mappings at occurrence, text, author, and project scopes;
- semantic-risk exclusion in an alternative scenario;
- stopword and proper-noun sensitivity policies;
- negated emotion term flagged without primary-score inversion;
- repeated influential term and leave-one-type-out contribution change;
- no matches, one match, all excluded, empty line, and empty stanza;
- categorical emotion with multiple associations and explicit denominators;
- emotion prevalence separated from mean matched intensity;
- source-scale normalization at minimum, midpoint, and maximum;
- disagreement between VAD sources without a consensus score;
- low coverage and minimum-match sparse-result warnings;
- malformed, duplicate, blank, out-of-range, and encoding-error lexicon rows;
- backup, restore, interrupted run, export, and migration failure behavior.

## Hand-calculated validation corpus

Phase 1 added an invented VAD text and tiny synthetic lexicon. Phase 2 extends
the validation materials with overlapping phrases, categorical associations,
emotion intensities, all three phrase policies, explicit denominators, and
cross-lexicon results with no consensus score. Phase 3 reuses those engine
fixtures through framework-independent application services and adds UTF-8
import, friendly-view, download-bundle, diagnostic, launcher, and interface
smoke cases.

Stage 2 adds `python -m versevad.concreteness_validation`. It generates a
temporary synthetic workbook and checks one phrase, exact forms, a lemma
fallback, an unmatched form, 5/6 coverage, and a token-weighted source-scale
mean of 4.0. The generated workbook checksum must remain unchanged.

The Stage 2 completion suite passed `143 passed` on 2026-07-23. The synthetic
demonstration, all 11 diagnostics, source and lock checks, and visual inspection
of the 28-page user manual and 21-page Values and Terminology Guide are
recorded in
[`poetic-fingerprint-stage2-validation.md`](poetic-fingerprint-stage2-validation.md).

Stage 3 adds `python -m versevad.frequency_validation`. It creates a temporary
synthetic SUBTLEX-US-shaped workbook and verifies exact observed-form priority,
lemma fallback, an unmatched form, 5/6 token coverage, token-weighted median
Zipf 4.0, token-weighted mean Zipf 3.4, and an optional scope containing only
model-tagged `NOUN`, `VERB`, `ADJ`, and `ADV`. The generated workbook checksum
must remain unchanged.

Stage 3 also adds local-source contract, malformed-source, source `#N/A`,
Unicode, proper-name, repetition, all-common, empty/unmatched, threshold,
deterministic, configuration, UI, and export coverage. The strict
content-word test verifies that `DET`, `ADP`, `CCONJ`, `SCONJ`, `PRON`, and
`AUX` remain ineligible and missing under that non-default scope.

The Stage 3 completion suite passed `159 passed` on 2026-07-23. All
demonstrations, all 11 diagnostics, source and lock checks, and visual
inspection of the 30-page User Manual and 23-page Values and Terminology Guide
are recorded in
[`poetic-fingerprint-stage3-validation.md`](poetic-fingerprint-stage3-validation.md).

Stage 4 adds `python -m versevad.aoa_validation`. It creates a temporary
official-supplement-shaped workbook and verifies exact observed-form priority,
an explicit lemma fallback, one unmatched form, 5/6 token coverage, mean
source AoA 7.2 years, median source AoA 8.0 years, default bands,
source-response evidence, and an optional contextual scope containing only
model-tagged `NOUN`, `VERB`, `ADJ`, and `ADV`. The generated workbook checksum
must remain unchanged.

Stage 4 also adds pinned-source contract, source `NA`/`#N/A`, malformed-source,
response-relationship, Unicode, proper-name, repetition, empty/unmatched,
threshold, sparse-relationship, deterministic, configuration, application,
UI, and eight-file export coverage. The content-word test verifies that the
paper's source-list sampling statement is not treated as a contextual POS tag
for poem occurrences. Optional Frequency/AoA and Concreteness/AoA Spearman
relationships use unique paired normalized surface types, exclude unsupported
multiword assignments, require at least three pairs, and remain descriptive.

The Stage 4 completion suite passed `172 passed` on 2026-07-23. The synthetic
demonstration and installed-source contract passed. Diagnostics, source and
lock checks, and rebuilt-guide structural validation passed then. The deferred
Word visual review was completed during Stage 5 on 2026-07-24 and is recorded in
[`poetic-fingerprint-stage4-validation.md`](poetic-fingerprint-stage4-validation.md).

## Validation performed

The read-only inspection utility validated all five selected source files for
presence, parseable structure, required columns, score ranges, blank terms,
duplicate primary keys, and malformed rows. SHA-256 checksums were recorded in
`docs/lexicons.md`.

Phase 1 adds 32 passing automated tests. They cover normalization, poem
structure, the pinned POS-sensitive model, exact-first matching, possessives,
lemma fallbacks, repeated words, sparse/no-match behavior, source and
normalized descriptive statistics, case-insensitive source collisions,
Warriner adapter errors and local integration, atomic CSV exports, empty-text
exports, and the hand-calculated demonstration.

Phase 2 brings the full suite to 49 passing tests. The added tests cover all
four new adapters against the local supplied files, exact counts and hashes,
scale normalization, multi-category terms, missing intensity pairs, malformed
source refusal, longest-first phrase selection, overlap and component audit,
line-boundary behavior, all phrase policies, categorical denominators,
token/type intensity statistics, source-specific comparison, seven-file CSV
export, UTF-8 byte-order marks, and safe replacement of prior exports.

Phase 3 brings the full suite to 62 passing tests. Its 13 added tests cover
UTF-8 and CRLF-preserving `.txt` import, invalid and oversized input errors,
plain request validation, all readable view models, match and unmatched
drill-down, scholar-summary and guide encoding, complete in-memory audit ZIPs,
eleven installation/source diagnostics, Streamlit empty and successful states,
all six result tabs, three download controls, and the offline/local-only Windows
helpers.

Phase 3.1 and Phase 4 bring the full suite to 78 passing tests. The added tests
cover VAD definitions and interpretation, leave-one-type-out contributors,
hand-calculated cumulative midpoint loads, Warriner exact phrase activation and
uncertainty fields, folder decoding, SQLite migrations and closed connections,
text version preservation, extensible metadata, immutable batch publication,
persistent unmatched notes, mixed-length token/work collection means, an
end-to-end two-work corpus run, corpus CSV/DOCX bundle structure, Lexicon Explorer
exact/phrase/lemma/mapped/component behavior, and all three Streamlit workspace
entry paths.

Phase 4.1 brings the full suite to 87 passing tests. The added coverage verifies
dual all-matched/stopword-excluded aggregation; pinned, protected, and custom
stopword behavior; exact phrase retention; midpoint-centered contribution
formulas; both result views in CSV/DOCX/SQLite; schema-version-2
migration; exact-confirmation project deletion; top workspace tabs; stale
Explorer recovery; and the comprehensive Word manual's package structure,
required content, page geometry, real numbering, and fixed-DXA table geometry.

Phase 4.2 brings the full suite to 89 passing tests. The two added tests verify
that NRC VAD v1's 132 source-supplied whitespace entries are active, that the
former inactive-entry caution is absent, and that both a synthetic phrase
fixture and the locally supplied `alarm clock` entry follow exact,
longest-first phrase matching with auditable component suppression.

Phase 5 brings the full suite to 100 passing tests. The added coverage verifies
schema-2-to-3 migration with a verified non-overwriting backup; named review
scenarios and immutable versions; append-only flag, exclude, map, revoke,
restore, and restored-snapshot revisions; occurrence/work/project/global
scope resolution; exact-target mapping after ordinary matching fails;
review-excluded aggregation; semantic-risk candidates; pinned immutable corpus
batches; baseline-versus-reviewed deltas; real-source end-to-end mapping;
separate emotion and sentiment presentation; universal part-of-speech counts
and lexical-token shares; workbook construct/POS/review sheets; title-case
interface navigation; and structural/content validation for both Word guides.
The final POS cases verify that the broad Noun category merges `NOUN`/`PROPN`,
the broad Verb category merges `VERB`/`AUX`, and the detailed view retains all
four source tags as separately countable evidence.

Poetic Fingerprint expansion Stage 0 brings the full suite to 115 passing
tests. Its 15 tests cover the common framework-independent module protocol,
immutable metrics/coverage/warnings/provenance/results, structural metric
identity, missing denominators, invalid counts and checksums, read-only resource
hashing, missing/malformed/unsupported resource states, configured-root path
containment, deterministic validation order, and refusal to publish unavailable
resources as completed provenance.

Both hand-calculated demonstrations and all 11 local diagnostics were rerun
after Stage 0. See
[`poetic-fingerprint-stage0-validation.md`](poetic-fingerprint-stage0-validation.md)
for results, limitations, and exact beginner steps.

Poetic Fingerprint expansion Stage 1 brings the full suite to 129 passing
tests. Its added coverage verifies exact source reconstruction from section,
stanza, and physical-line records; `CRLF`, indentation, blank separators,
model sentences/dependencies across poetic lines, em dashes, Unicode
normalization separation, apostrophes, contractions, hyphenated expressions,
content/function classifications, capitalization, one-word and
punctuation-free lines, archaic forms, repeated refrains, NER disabled by
default and explicitly enabled, missing small-model OOV coverage, empty and
deterministic documents, immutable module-input integration, invalid
configuration/coverage refusal, one preprocessing pass across multiple
lexicons, the audit JSON, and the visible Shared Processing Record.

The completion suite passed `129 passed` on 2026-07-23. Both hand-calculated
demonstrations, all 11 diagnostics, and the rendered Word-manual inspection are
recorded in
[`poetic-fingerprint-stage1-validation.md`](poetic-fingerprint-stage1-validation.md).

The full suite passes with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

A live local browser validation also exercised the beginner path using all five
private source files: start the app, paste a three-line invented poem, analyze,
read Overview and the normalized VAD view, open normalization details, and run
the in-app self-test. It produced no application error, the VAD chart remained
bounded to 0-1, and all 11 self-test checks passed. File import is verified at
the service and Streamlit smoke-test layers; the manual browser pass deliberately
used paste input to avoid copying any private literary file.

The Phase 4 browser pass verified clean navigation between all three workspaces,
a five-source `blood` lookup with provenance and normalized spread, a complete
one-poem analysis with definitions/token-type/cumulative/contributor sections,
all three download controls, and the absence of the former inactive-Warriner-
phrase warning. A real two-work NRC VAD corpus pipeline generated an Excel
workbook; it was re-imported, key ranges inspected, and the collection-profile
sheet rendered for visual review using the spreadsheet validation tooling.

The Phase 4.1 browser pass used an isolated temporary database and verified the
top workspace tab bar, a complete five-source one-poem analysis, both VAD
views, definitions, stopword sensitivity, cumulative totals, midpoint-centered
contributors, the excluded-match evidence filter, a fresh `kiss` Lexicon
Explorer lookup, and exact-case project deletion with a visible success
confirmation. The temporary database was removed afterward.

Poetic Fingerprint expansion Stage 5 adds adapter, engine, validation, export,
application, and Streamlit coverage for exact pinned CMUdict files; unique,
prosodically agreeing, materially ambiguous, vowelless, unmatched, and
scholar-override states; Unicode apostrophes; proper names; possessive
non-substitution; repeated words; empty input; incomplete lines; deterministic
results; and invalid-source refusal. CSV and JSON checks confirm that every
candidate remains visible and unresolved values remain blank. The
hand-calculated command is:

```powershell
.\.venv\Scripts\python.exe -m versevad.pronunciation_validation
```

See
[`poetic-fingerprint-stage5-validation.md`](poetic-fingerprint-stage5-validation.md)
for exact expected values, installed-source checks, beginner interface steps,
and limitations.

The Stage 5 completion suite passed `185 passed` on 2026-07-24. Phase 1,
Phase 2, Concreteness, SUBTLEX-US Frequency, Kuperman AoA, and pronunciation
synthetic validations all passed, as did all 11 diagnostics, the installed
CMUdict contract, the 86-package offline lock check, and `git diff --check`.
Both rebuilt Word guides passed structural tests and complete visual
inspection: 37 User Manual pages and 26 Values and Terminology Guide pages.

Poetic Fingerprint expansion Stage 6 adds pure meter-alignment, application,
UI, export, and synthetic-validation tests. The direct synthetic
command is:

```powershell
.\.venv\Scripts\python.exe -m versevad.meter_validation
```

It checks the 40 fixed templates, exact iambic pentameter, feminine ending,
initial inversion, catalectic ending, exact trochaic tetrameter, and
missing-pronunciation refusal. The full suite additionally
covers every base pattern, spondaic/pyrrhic local substitutions, secondary
stress, function-word promotion, stress-path limits, deterministic ranking,
meter-only workspace activation, UI, all five exports plus JSON, and regression
behavior.

The Stage 6 completion suite passed `204 passed` on 2026-07-24. Phase 2,
Concreteness, SUBTLEX-US Frequency, Kuperman AoA, pronunciation, and
candidate-meter synthetic validations all passed, as did all 11 diagnostics,
the five-lexicon read-only source inspection, the installed CMUdict contract,
the 86-package offline lock check, and `git diff --check`. Both rebuilt Word
guides passed structural tests and complete visual inspection: 40 User Manual
pages and 28 Values and Terminology Guide pages.

Poetic Fingerprint expansion Stage 7 adds exact-scheme, rhyme-type, graded-
slant, eye, internal-rhyme, refrain, recurring-sound, coverage, application,
UI, export, and synthetic-validation tests. The direct synthetic command is:

```powershell
.\.venv\Scripts\python.exe -m versevad.phonology_validation
```

It checks ABAB with two exact pairs, masculine/feminine/multisyllabic labels,
graded slant and eye evidence outside exact schemes, internal rhyme,
alliteration, assonance, consonance, unresolved ending coverage, deterministic
output, and unchanged synthetic source files. See
[`poetic-fingerprint-stage7-validation.md`](poetic-fingerprint-stage7-validation.md)
for exact beginner steps and limitations.

The Stage 7 completion suite passed `215 passed` on 2026-07-24. Every
synthetic demonstration, all 11 diagnostics, the five-source read-only
inspection, the installed three-file CMUdict contract, the 86-package offline
lock check, and `git diff --check` passed. Both rebuilt Word guides passed
structural, required-content, table-geometry, numbering, and accessibility
checks and opened/paginated in Microsoft Word at 42 and 28 pages. Page-image
visual inspection could not be completed because LibreOffice is absent and
the local Word PDF exporter stalled before creating a PDF.

The narrowed Stage 10 suite adds pure lexical-diversity, structural word-count,
application, UI, export, and synthetic-validation tests. The direct command is:

```powershell
.\.venv\Scripts\python.exe -m versevad.lexical_style_validation
```

The hand-calculated fixture checks `4/7` surface TTR, MATTR `14/15`, HD-D
`86/105`, mean/median alphabetic word length 4, physical-line word counts
`3, 2, 0, 2`, and stanza counts `5, 2`. It also checks average words per
nonblank line `7/3` with population SD `sqrt(2/9)`, average words per stanza
`3.5` with population SD `1.5`, and average nonblank lines per stanza `1.5`
with population SD `0.5`. A separate repeated-token fixture checks
bidirectional MTLD 4 at threshold 0.72.

Automated coverage also verifies missing short-window/sample results,
all-unique undefined MTLD, invalid configuration refusal, surface/lemma
separation, punctuation/numeric exclusion, line/stanza reconciliation,
resource-free module behavior, CSV and Word exports, Project / Corpus metric
persistence, the One Poem interface, and
unchanged existing modules. See
[`poetic-fingerprint-stage10-validation.md`](poetic-fingerprint-stage10-validation.md)
for exact beginner steps and limitations.

The Stage 10 completion suite passed `225 passed` on 2026-07-24. All nine
direct synthetic demonstrations, all 11 diagnostics, read-only source/resource
checks, the 86-package offline lock check, and `git diff --check` passed. Both
rebuilt Word guides passed structural/content and accessibility checks and
opened/paginated in Microsoft Word at 44 and 30 pages. The canonical page-image
renderer was attempted but remains unavailable because LibreOffice is not
installed; the already observed local Word PDF-export stall was not repeated.

Stage 11 adds schema-4 migration, generic repository persistence, optional-
module-only corpus, safe aggregation, pooled lexical-style, deterministic
artifact ZIP, expanded Explorer, corpus workbook, and interface tests. Its
hand-calculated fixtures are documented in
[`poetic-fingerprint-stage11-validation.md`](poetic-fingerprint-stage11-validation.md).
The Stage 11 completion suite passed `230 passed` on 2026-07-24. All nine
direct synthetic demonstrations, all 11 diagnostics, read-only source/resource
checks, the 86-package offline lock check, and `git diff --check` passed. Both
rebuilt Word guides passed structural and accessibility checks with no
high-severity findings. The canonical page-image renderer was attempted for
both documents but could not start because LibreOffice is not installed.

## Stage 12 PoetryID

Run the hand-calculated classifier example:

```powershell
.\.venv\Scripts\python.exe -m versevad.poetry_id_validation
```

The example places `(0.2, 0.5, 0.8)` exactly at The Survivor centroid under
the default fixed profile, checks all 27 distances and affinity normalization,
and verifies that the PoetryID bundle contains seven CSV files and one DOCX
report with no JSON, TXT, or XLSX.

Automated tests cover the complete registry, threshold inclusivity, custom
configuration round trips, distance ranking, categorical/centroid agreement,
boundary and coverage confidence, structured unavailability, token/type
separation, all-matched/stopword-excluded separation, independent source/scope/
weighting result controls, native-scale lexical character, exact upstream VAD
identity, non-JSON exports, generic project persistence, compatible corpus
distributions, workbook fields, and regressions.

See
[`poetic-fingerprint-stage12-validation.md`](poetic-fingerprint-stage12-validation.md)
for the final completion record and beginner interface checks.

## Stage 13 design and interface

Stage 13 adds tests for:

- missing, malformed, saved, and reloaded application appearance preferences;
- semantic Classic/Dark/Lavender/Ocean/Crimson/Forest tokens, legacy
  preference migration, visible focus, reduced motion, and measured contrast;
- Essential, Literary, Sound and Form, Complete, and Custom presets, including
  the rule that advanced methodology keys are never changed;
- the four-workspace shell and distinct Analyze Poem, Analyze Text, and Analyze
  Corpus actions;
- Other Text reuse without a second analytical engine;
- grouped result navigation and module completion/not-selected sections;
- Project / Corpus status, work search/filter fields, and schema-4 regression;
- unchanged Explorer lookup controls and all-resource behavior;
- appearance persistence without creating analysis state; and
- all pre-existing analytical values, exports, source hashes, and project
  behavior through the complete regression suite.

The visual validation procedure checks Single Poem, Project / Corpus, Other
Text, and Lexicon Explorer at desktop and narrow widths in Classic, Dark,
Lavender, Ocean, Crimson, and Forest appearances. It inspects focus visibility,
contrast, header wrapping,
table access, empty states, and a completed-result overview. See
[`design-stage13-validation.md`](design-stage13-validation.md).

The Stage 13 completion suite passed `252 passed` on 2026-07-24. All ten
direct synthetic demonstrations, all 11 diagnostics, the five-source
read-only inspection, all six supplementary resource contracts, the
86-package offline lock check, interface browser checks, documentation tests,
and `git diff --check` passed. Both rebuilt Word guides passed structural and
accessibility checks with no high-severity findings. The canonical page-image
renderer was attempted but remains unavailable because LibreOffice/`soffice`
is not installed; no visual-render success is claimed.

## Stage 14 performance-aware meter and optimization

Stage 14 adds exact pre-refactor candidate fixtures before changing alignment
internals. Tests compare pattern, foot count, cost, fit, evaluated alignment,
deviation counts, candidate ranking, and poem summary values.

Performance-aware tests cover source-stress preservation, declared profile
separation, contextual adjustments, punctuation-supported caesura, retained
alternatives, component scores, stanza recurrence, generic alternating
sequence, missing evidence, exports, corpus persistence, and Streamlit
presentation.

Cache tests cover unchanged reuse, dependency-specific PoetryID and
pronunciation invalidation, debugging disablement, invalid-entry recovery,
LRU eviction, duplicate concurrent requests, preprocessing/module identity,
and export identity. Timing assertions inspect states and deterministic data;
ordinary tests do not impose unstable wall-clock limits.

Use:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_stage14.py --quick --repetitions 3
```

for repeatable medians, or add `--memory` for traced peak memory. See
[`stage14-performance-report.md`](stage14-performance-report.md) and
[`poetic-fingerprint-stage14-validation.md`](poetic-fingerprint-stage14-validation.md).

## Pre-release startup, theme, and VAD/POS repair

The repair suite adds regression coverage for lightweight checksum-only
startup readiness, single-owner Streamlit widget state, stable semantic
selectors, cross-theme contrast, and the source/view-specific VAD-by-POS table.
The hand-calculated POS fixture repeats one adjective so its token-weighted
and type-weighted normalized VAD means differ, preserves an unmatched POS
group with missing means, and retains a cross-POS published phrase in an
explicit mixed group. The audit ZIP test verifies
`vad_by_part_of_speech.csv`.

The completed suite passed `289 passed` on 2026-07-24. All eleven direct
synthetic validation modules and all twelve local diagnostics passed.
Checksum readiness for all eleven installed resources took 0.0434 seconds in
the final focused measurement without parsing the complete workbooks or
dictionary. Rendered browser checks measured Light text-entry/primary-button
contrast at approximately 15.6:1/11.8:1 and Dark contrast at
14.4:1/9.3:1. At a 390 by 844 viewport the completed Structure report,
responsive navigation, and VAD-by-POS audit table produced no page-level
horizontal overflow.

## Version 1.0.0 release metadata

Public-release tests require the package metadata, runtime `__version__`,
offline lock, and `CITATION.cff` to agree on `1.0.0`. They also verify the
GPL-3.0-only license, Nicky Bennett authorship, exact canonical GitHub
repository, exact 2026-07-24 release date, absence of an invented DOI
placeholder, public-package exclusions, and the complete local-resource
installation contract.

The release suite passed `291 passed` on 2026-07-24. All eleven direct
synthetic validation modules, all twelve diagnostics, and the 86-package
offline lock check passed with the runtime reporting VerseVAD `1.0.0`.

## Pre-release Arrow display repair

The regression fixture builds one heterogeneous Lexicon Explorer evidence
table containing a numeric Zipf value, textual SUBTLEX-US part-of-speech
label, Boolean field, and missing field. It requires the presentation-only
`Value` column to contain explicit strings and verifies direct conversion to a
PyArrow table. The underlying Explorer result remains typed. Generic
Project/Corpus module tables use the same display-only conversion because
their metrics may also legitimately mix numbers, text, Booleans, and missing
values.

The end-to-end check opens Lexicon Explorer against the installed local
resources, searches for `bright`, and verifies that the result renders eight
dataframes with no application exception or Arrow conversion traceback.
Ordinary headless Streamlit startup is checked separately so a use-time table
warning cannot be mistaken for a launch warning.

The completed automated suite passed `292 passed` on 2026-07-24, including the
new direct PyArrow regression. The focused Explorer test passed `3 passed`, and
the real installed-resource search completed normally. At the scholar's
direction, the unrelated full-resource synthetic demonstration rerun was
stopped rather than continuing to traverse every installed lexicon for this
display-only repair.

## macOS and browser compatibility

Cross-platform tests require the macOS setup, startup, and diagnostic helpers
to resolve their own checkout path, keep `uv`, Python, and caches
project-local, preserve the locked/offline launch policy, bind only to
`127.0.0.1`, and avoid Windows path syntax. The setup contract also requires
the pinned official `uv` installer, explicit Python 3.12 selection, safe
rebuilding of only the checkout-local `.venv`, and a runtime-only diagnostic
that can pass before separately licensed lexicons are installed.

Responsive stylesheet tests cover Safari-prefixed sticky positioning and
momentum scrolling, explicit text-size adjustment, safe overflow, 520-pixel
header/workspace wrapping, 16-pixel narrow-screen text inputs, and wrapping
download/primary buttons. Live browser validation should cover all four
workspaces at desktop, tablet, and narrow viewports, confirm no page-level
horizontal overflow, and check the browser console. Because Safari is not
available on the Windows development host, final release acceptance also
requires a short real-Mac pass in current Safari and Chrome following
`docs/macos-installation.md`.

The Windows-host completion pass on 2026-07-26 reached 100% with no failures
across 297 automated tests, passed all eleven direct synthetic validations and
all twelve full local diagnostics, and confirmed an 88-package locked/offline
environment dry run. A temporary loopback server returned HTTP 200 with no
application warning or traceback. The focused launcher, browser-style,
release, manual, and Streamlit interface set passed 35 tests. The in-app
browser-control surface was unavailable during this pass, and Safari cannot
run on Windows, so no Safari or pixel-level Chrome visual claim is made. The
real-Mac checklist remains explicit rather than being represented as
automatically complete.

## Corpus VAD dispersion and in-place update documentation

The corpus VAD regression fixture uses two invented poems with hand-calculated
normalized valence statistics. It verifies the pooled population variance
identity
`sum(n_j * (s_j^2 + (m_j - M)^2)) / sum(n_j)`, the distinct population
standard deviation across poem means, median, minimum, maximum, and exact
pairing of every work mean with its matching within-work SD. A second fixture
removes one work-level SD and confirms that the pooled SD stays missing while
the across-poem SD remains available.

Export regression coverage checks that `corpus_vad_profiles.csv` contains both
dispersion levels and that `corpus_report.docx` names them separately. The
existing complete Streamlit and cross-platform suites cover the shared
Windows/macOS Python path and responsive corpus tables. `docs/updating.md`
documents GitHub Desktop and terminal pulls without changing ignored
lexicons, resources, projects, or operating-system-specific environments.

The completion pass on 2026-07-26 passed all `300` automated tests, including
`58` focused application, release, manual, responsive-style, cross-platform,
and Streamlit tests. Ten lightweight direct synthetic demonstrations passed;
the separate full five-source Phase 2 demonstration was intentionally not
repeated, following the scholar's earlier request to avoid another
unnecessary complete lexicon traversal. All runtime-only diagnostic checks
passed, and the 88-package locked/offline dry run would make no environment
changes. The rebuilt Word manual passed package/content checks and its
accessibility audit reported zero findings. PNG visual rendering was
unavailable because LibreOffice is not installed on the Windows host.

## Project / Corpus deletion rerun repair

The deletion regression set verifies exact case-sensitive title confirmation,
project-scoped database cascades, callback-based deletion before the next
full-page render, success messaging, selection of a remaining project, and
recovery from a deliberately stale deleted-project ID. The completion pass on
2026-07-26 passed all `301` automated tests. The focused deletion set passed
three tests, and the broader Project/Corpus, design, and cross-platform
interface set passed thirty tests.

## Stage 15 inherited-form validation

Focused tests cover:

- exactly 169 unique, source-documented profiles, tooltip definitions, source
  URLs, and automatic/partial/manual assessment modes;
- exact villanelle refrain positions and stanza architecture;
- exact sestina end-word rotation and envoi;
- exact pantoum ordered repetition;
- an exact Shakespearean fixture whose existing phonology and meter results
  are `ABABCDCDEFEFGG` and iambic pentameter;
- a deliberately modified refrain receiving graded rather than binary credit;
- missing required syllable evidence lowering coverage and preventing an
  unsupported 5–7–5 haiku suggestion;
- explicit profile subsets and deterministic configuration identity;
- automatic pronunciation/meter/rhyme dependency execution;
- per-poem project persistence and seven checksummed artifacts;
- six CSV files plus deterministic narrative DOCX, with no JSON;
- traditional-definition tooltip content;
- ten-row concise no-match presentation plus an all-169-profile inspector and
  complete profile/candidate exports; and
- Single Poem, Project / Corpus, design, application, and existing module
  regressions.

Run the lightweight direct validation with:

```powershell
.\.venv\Scripts\python.exe -m versevad.inherited_form_validation
```

or on macOS:

```bash
.venv/bin/python -m versevad.inherited_form_validation
```

The command constructs invented villanelle, sestina, pantoum, and
under-supported haiku fixtures. It does not traverse installed research
lexicons. Full completion evidence is recorded in
[`inherited-form-stage15-validation.md`](inherited-form-stage15-validation.md).
