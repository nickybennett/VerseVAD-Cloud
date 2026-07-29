# Architecture Decision: Local Modular Python Application

Status: accepted; the Phase 5 local workspace and Poetic Fingerprint expansion
Stage 4 Age of Acquisition module have been validated.

Date: 2026-07-23

## Decision

VerseVAD will use a modular Python analysis engine, a local Streamlit interface,
and a SQLite project database. The interface will call the same tested engine
used by scripts and automated tests. Lexicon parsing will be isolated behind
versioned adapters.

The initial technology choices are:

- Python 3.12 as the first supported runtime;
- Streamlit 1.60.0 for the local browser-based graphical interface;
- the Python `sqlite3` module plus explicit, numbered SQL migrations;
- pandas for tabular analysis and interchange;
- spaCy with a pinned English pipeline for POS-sensitive lemmatization;
- eSpeak NG, loaded from a pinned cross-platform wheel, for optional offline
  synthesis of explicit ARPAbet pronunciation previews and review-only
  US-English G2P candidates for unmatched observed forms;
- Altair through Streamlit for current interactive charts;
- openpyxl for reading the user-supplied XLSX normative resources;
- python-docx for local narrative Word reports;
- pytest for engine, adapter, migration, export, and interface smoke tests;
- Jinja templates for local HTML methods reports;
- `uv` as the project-local dependency and Python manager.

No system-wide package installation is required by the architecture.
Project-local Windows and macOS setup helpers obtain the appropriate managed
Python build and activate the same locked project environment. OS-specific
launchers start one platform-neutral local application. A packaged executable
can be evaluated later; it is not an architectural dependency.

Phase 1 selected and locked Python 3.12, spaCy 3.8.14,
`en_core_web_sm` 3.8.0, Click 8.4.2, and pytest 9.1.1 in `uv.lock`. The working
runtime, package cache, and `uv` executable are kept in ignored project-local
directories rather than installed computer-wide.

The pronunciation assistance layer pins `espeakng-loader==0.2.4`, whose lock
entries provide the
bundled eSpeak NG shared library and data for Windows x86-64/ARM64, macOS Intel/
Apple silicon, and supported Linux architectures. It is initialized lazily
when a preview or unmatched-word review needs it. eSpeak NG 1.52.0's `en-us`
text-to-phoneme system produces separated IPA, and VerseVAD maps only its
documented supported inventory to provisional CMUdict-style ARPAbet. The
analytical pronunciation engine does not treat that output as evidence: the
token remains unmatched until the scholar approves or edits the candidate
into a session override. No text or phones are sent to a service.

Phase 2 adds no runtime dependency. Its adapter, phrase, categorical, intensity,
comparison, and CSV-export logic remains in the framework-independent Python
package.

Phase 3 pins Streamlit 1.60.0 and its resolved dependency tree in `uv.lock`.
`versevad.application` owns text validation, lexicon loading, analysis
orchestration, friendly view models, and download construction; the Streamlit
page only presents those services. Workspaces and downloads are in memory in
this phase.

Phase 4 adds the persistent SQLite repository, immutable complete corpus
batches, dual collection weighting, and CSV/DOCX export. Phase 4.1 adds the
versioned dual stopword reporting policy. Phase 5 advances the development
package to `0.6.0.dev0`, migrates the database to schema version 3, and adds
named/versioned review scenarios, append-only decisions, occurrence evidence,
baseline-versus-reviewed batch comparison, a separate sentiment presentation,
and lexicon-independent part-of-speech profiles.

The one-text application layer can derive a separate VAD-by-broad-POS view
from immutable completed `Phase2AnalysisResult` records. It neither reloads a
lexicon nor rematches text. The derivation preserves lexicon and stopword-view
boundaries, reuses the analysis engine's exact stopword-eligible token IDs,
and calculates both occurrence-sensitive and distinct-entry means. Its
dedicated CSV is assembled with the other detailed audit artifacts.

The Poetic Fingerprint expansion Stage 0 adds a framework-independent common
module contract under `versevad.core` and a read-only local resource manager.
It is additive: the validated VAD engine and schema version 3 remain unchanged.
Future modules will return immutable common result envelopes containing
explicit observation/calculation/interpretation layers, coverage, warnings, and
reproducibility provenance. See
[`poetic-fingerprint-stage0.md`](poetic-fingerprint-stage0.md).

Expansion Stage 1 advances the development package to `0.7.0.dev0` and
materializes the planned immutable `PoemDocument`. It retains exact
section/stanza/physical-line structure, separate model sentences, shared
tokens, morphology and dependency annotations, optional entities,
orthographic spans, configuration, coverage, and warnings. A one-poem request
is processed once and the same tokens are reused across all selected lexicons.
The common document is available to Stage 0 module inputs and is exported
locally as explicit `processing_*.csv` tables. Stage 1 does not change database schema 3 or
existing affective calculations. See
[`poetic-fingerprint-stage1.md`](poetic-fingerprint-stage1.md).

Expansion Stage 2 advances the development package to `0.8.0.dev0`. Its
read-only workbook adapter and framework-independent concreteness module
consume the shared document without changing it. The optional one-poem path
adds source-scale descriptive statistics, coverage, structural/POS groups,
term rankings, warnings, provenance, and token-level audit exports. The
Streamlit page only presents these tested application results. Stage 2 remains
in memory and does not change database schema 3. See
[`poetic-fingerprint-stage2.md`](poetic-fingerprint-stage2.md).

Expansion Stage 3 advances the development package to `0.9.0.dev0`. Its
read-only SUBTLEX-US workbook adapter and independent frequency module consume
the same shared document without changing it. The optional one-poem path adds
a primary token-weighted median Zipf value, distribution, coverage,
structural/POS groups, term rankings, warnings, provenance, and token-level
audit exports. A non-default scope restricts eligibility to exact model tags
`NOUN`, `VERB`, `ADJ`, and `ADV`; it does not adopt the Language Profile's
broader `VERB`/`AUX` display grouping. Stage 3 uses no `wordfreq` fallback,
remains in memory, and does not change database schema 3. See
[`poetic-fingerprint-stage3.md`](poetic-fingerprint-stage3.md).

Expansion Stage 4 advances the development package to `0.10.0.dev0`. Its
read-only official Kuperman erratum-supplement adapter and independent Age of
Acquisition module consume the same shared document without changing it. The
optional one-poem path adds age-in-years descriptive statistics, coverage,
configurable orientation bands, structural/POS groups, source-response
evidence, represented-term rankings, warnings, provenance, and a token-level
audit. When the corresponding modules are enabled, it can also report
descriptive unique-surface-type Spearman relationships with Frequency and
Concreteness. The non-default contextual content-word scope uses exact model
tags `NOUN`, `VERB`, `ADJ`, and `ADV`; it remains meaningful even though the
source paper describes content-word sampling. Stage 4 remains in memory and
does not change database schema 3 or add these optional results to Projects &
Corpus. See
[`poetic-fingerprint-stage4.md`](poetic-fingerprint-stage4.md).

The formal centroid/region emotional-profile classifier is deferred; the
existing Emotion Profile workspace must not be represented as though it
already implements that model.

Expansion Stage 11 advances the development package to `0.15.0.dev0` and
migrates project databases to schema version 4. The corpus orchestrator passes
each preserved work through `run_workspace_analysis`, so affective and optional
modules share one `PoemDocument` and the same module engines used by **One
Poem**. A generic repository integration layer serializes each existing
`ModuleResult`, detailed metric, coverage row, warning, provenance record, and
existing exporter artifact without duplicating module calculations.

Schema 4 records selected module configurations on the batch and links every
module result to the immutable run and active text version. The aggregation
layer operates only on persisted module evidence. It supplies equal-work means,
observation-weighted means only for metrics with safe observation counts, and
separately recalculated ordered-pooled-token lexical-style measures. The
Streamlit page and Excel builder consume repository records; they do not become
analysis engines. Lexicon Explorer likewise uses the installed resource
adapters to expose concreteness, SUBTLEX-US, AoA, and CMUdict fields alongside
the affective sources. See
[`poetic-fingerprint-stage11.md`](poetic-fingerprint-stage11.md).

## Why this fits VerseVAD

Streamlit supplies accessible tables, controls, progress feedback, downloads,
and charts without requiring a separate JavaScript application. SQLite keeps
projects in a portable local file while supporting transactions and backups.
Python has mature linguistic, tabular, statistical, testing, and export tools.

The important boundary is not the framework; it is separation of concerns:

```text
Streamlit UI / CLI
        |
Application services
        |
Shared PoemDocument ---- Scenario and recipe models
        |
Analysis engine ---- Optional analysis modules
        |
Matching engine ---- Lexicon adapter interface
        |                      |
Token records           Read-only source files
        |
SQLite repositories / immutable exports
```

Streamlit must remain a thin presentation layer. Statistical or matching logic
inside page code would be difficult to test and audit.

The part-of-speech calculation therefore lives in framework-independent
application services. The corpus UI derives project/work profiles from current
preserved text versions using the pinned preprocessor, caches the exact
version/model signature for the active session, and exports the resulting
counts and shares without treating them as affective-lexicon metrics.

For the temporary one-poem path, application services create one
`PoemDocument` and pass a prepared read-only view to every selected lexicon.
Structural, sentence, token, dependency, entity, and coverage records therefore
cannot drift between source-specific analyses in the same request.

## Planned package boundaries

```text
src/versevad/
  core/           common module and local-resource contracts
  adapters/       source-specific parsing and validation
  analysis/       matching, coverage, summaries, comparisons
  db/             schema, repositories, transactions, migrations
  exports/        CSV, Excel, HTML, and chart-data outputs
  ui/             Streamlit pages and plain-language presentation
scripts/          diagnostics, setup helpers, and developer utilities
tests/            unit, integration, migration, and synthetic validation tests
```

## Traceability design

Every completed run will be immutable. A run signature will include:

- software and adapter versions;
- text-version checksum;
- lexicon file checksum and source metadata;
- linguistic pipeline and model version;
- preprocessing recipe version;
- shared preprocessing configuration ID;
- analysis scenario version;
- phrase, stopword, negation, matching, and exclusion policies.

Displayed aggregates will be computed from included match records. A drill-down
will retrieve those same records rather than reconstructing an undocumented
approximation.

## Source-file handling

Adapters open source files read-only. Import creates validated internal records
or a cache keyed by the source checksum; it does not edit or replace the source.
Original and normalized scores are separate fields. For example:

- Warriner 1–9 values can be normalized as `(x - 1) / 8`;
- NRC VAD v1 values already occupy 0–1;
- NRC VAD v2.1 values can be normalized as `(x + 1) / 2`.

These formulas are tested adapter metadata. They never overwrite source values.
The Phase 3 comparison view uses only the separately derived values and labels
the original scales and formulas alongside them.

Future non-affective datasets will be installed locally under an ignored
`resources/` tree or another explicitly configured local root. The common
resource manager records file presence, size, checksum, and support status but
does not replace resource-specific adapter validation.

## Local privacy and networking

The running application will not require a cloud service. Setup may access the
internet to obtain the Python runtime, dependencies, or spaCy model after an
explicit explanation. Runtime analysis will not transmit source texts,
lexicons, projects, or results. Usage telemetry will be disabled where the
selected framework permits it.

## Principal risks and mitigations

### Linguistic analysis of poetry

Modern English POS models will make errors on poetic syntax, archaisms, coined
terms, and unusual punctuation. Exact source-form matching therefore precedes
lemma fallback. POS, lemma, context, warnings, and match method remain visible.
User mappings are reviewed, scoped, reversible, and versioned.

### Phrase overlap

NRC VAD v2.1 contains 10,073 whitespace-containing entries. The local policy
also activates Warriner's 102 and NRC VAD v1's 132 whitespace-containing
entries. The matching engine uses deterministic longest-first candidate
generation and an explicit overlap policy. Phrase and suppressed component
candidates remain auditable.

### Reruns and changing judgments

Edits, mappings, exclusions, and recipes can otherwise make old results
irreproducible. Completed runs will point to immutable versions and will never
be silently updated. New judgments create a new scenario and run.

### Installation complexity

The original Windows target had no ordinary `python` or `git` command on its
PATH. Windows setup uses a checksum-verified project-local `uv` executable.
macOS setup uses the pinned official `uv` installer in unmanaged,
project-local mode and selects the appropriate Apple silicon or Intel build.
Both use a project-managed Python runtime and environment without administrator
access. Their launchers use the locked environment offline and bind Streamlit
only to `127.0.0.1` with usage telemetry disabled. The universal `uv.lock`
retains platform and architecture markers instead of copying a Windows virtual
environment to another operating system.

### Pronunciation alternatives and future prosody

Stage 5 is a framework-independent `PronunciationModule` under
`versevad.prosody`. Its read-only `CMUDictAdapter` owns all source parsing and
validation. The analysis engine consumes `ModuleInput`, not Streamlit, and
returns the shared `ModuleResult` contract plus typed token, observed-type, and
physical-line evidence.

The exact local CMUdict dictionary, phone inventory, and symbol inventory are
the authoritative source. The pinned `pronouncing` library supplies only
stress/syllable utilities; its package-bundled dictionary is not an
analysis-time substitute.

All dictionary alternatives travel together from adapter to result. The module
does not collapse them into one hidden candidate. Scholar overrides are
configuration inputs, not edits to the source or shared poem document.

Stage 5 results are currently in-memory One Poem results and exports. A future
schema-4 module-result design can persist the same module envelope,
configuration ID, three resource hashes, token candidates, override evidence,
and line summaries without changing the adapter or calculation API. Stage 6
candidate-meter and Stage 7 rhyme modules consume explicit alternatives rather
than retrofitting a silently chosen pronunciation.

### Candidate meter

Stage 6 is a framework-independent `MeterModule` under
`versevad.prosody.meter`. It receives the shared `ModuleInput` plus a completed
`PronunciationAnalysisResult`; it never loads a second text representation or
rewrites Stage 5.

The engine separates:

- `MeterConfiguration`: penalties, thresholds, stress-path limit, and stable
  scenario/configuration identity;
- `MeterTemplate`: one pattern and one foot count in the 40-candidate fixed
  grid;
- `MeterLineResult`: coverage status, retained candidate fits, selected stress
  path, alignment operations, and deviations for one physical line;
- `MeterCandidateSummary`: equal-line aggregate for one fixed template;
- `MeterSummary`: nearest candidate kind, alternative, fit, confidence,
  coverage, regularity, variability, and deviation totals.

Dynamic programming is isolated from Streamlit and exports. Application
services activate Stage 5 automatically when meter is selected, then pass the
same immutable poem document to both modules. The UI and exports consume the
result objects rather than recomputing a hidden classification.

Stage 11 now persists Stage 6 through the generic schema-4 module envelope,
including dependency provenance, line fits, candidate grids, and immutable
completed runs. Candidate prevalence remains separate from work-level meter
evidence.

### Rhyme and recurring phonological patterns

Stage 7 is a framework-independent `PhonologicalModule` under
`versevad.phonology`. It receives the same `ModuleInput` and completed
`PronunciationAnalysisResult` as Stage 6. Its typed result separates
configuration, summary, stanza summaries, physical-line ending/sound evidence,
within-stanza ending-pair evidence, internal-rhyme records, and aggregate sound
families.

Application services activate Stage 5 automatically when Stage 7 is selected.
Exact rhyme groups require one robust rhyme part across every retained
pronunciation alternative. Graded slant and eye-rhyme evidence remain outside
the scheme groups. The UI and seven export files read the typed result without
recomputing classifications.

Stage 11 now persists Stage 7 with its Stage 5 dependency configuration, exact
source hashes, method configuration, line/pair audit, coverage, and immutable
result identity.

### Narrowed lexical style

The scholar explicitly skipped the broader Stage 8 visible-structure and Stage
9 syntax/lineation modules. Narrowed Stage 10 is a framework-independent
`LexicalStyleModule` under `versevad.lexical_style`. It consumes the existing
`ModuleInput` and shared `PoemDocument`; it does not run another tokenizer or
load an external lexical resource.

The typed result separates configuration, document summary,
alphabetic-character distribution, physical-line summaries, stanza summaries,
token audit, coverage, warnings, and provenance. Lexical diversity uses
normalized observed surface forms while keeping lemmas separate. Line and
stanza word counts are direct projections of the same token IDs and structural
IDs already present in the poem document. A third typed descriptive-statistics
field aggregates each stanza's existing nonblank-line count; no interface or
export path retokenizes text or independently recomputes these structural
means and population standard deviations.

Application services, the One Poem interface, the scholar summary, and six
exports consume the typed result rather than recalculating diversity or
counts. Stage 11 invokes this same module in the project/corpus runner and
persists its envelope, configuration, structural summaries, and audit without
implementing a second calculation path.

### Interface scale

The final specification contains many specialist views. Progressive disclosure
will keep a basic create-import-analyze-review-export path visible while moving
advanced scenario and statistical controls behind clearly labeled sections.

## Rejected alternatives

- A cloud-hosted application conflicts with private-text and local-first goals.
- A spreadsheet as the authoritative store cannot reliably preserve versioned
  provenance and transactions.
- A large JavaScript web stack would add packaging and maintenance cost before
  demonstrating methodological value.
- A single monolithic notebook is difficult for beginners to operate and hard
  to test, migrate, or audit.
- A default cross-lexicon consensus would conceal source and family differences.

## Expansion Stage 12 PoetryID

Expansion Stage 12 advances the development package to `0.16.0.dev0`.
`versevad.poetry_id` contains a framework-independent archetype registry,
configuration, engine, and result adapters. The integration layer accepts
immutable `Phase2AnalysisResult`, `ConcretenessAnalysisResult`,
`FrequencyAnalysisResult`, and `AoAAnalysisResult` objects; it never imports a
lexicon adapter or resource manager. `versevad.ui.poetry_id` is presentation
only.

The application runs PoetryID after its selected upstream VAD and optional
lexical-semantic modules. One shared `PoemDocument` and one set of VAD results
therefore support both the ordinary VAD interface and PoetryID. The PoetryID
`ModuleResult` records upstream analysis IDs in metrics and includes every
selected source resource hash in provenance.

Project/corpus persistence reuses schema 4's generic module-result, metric,
coverage, warning, provenance, and artifact tables. No schema 5 migration is
needed. Corpus aggregation includes `scope_id` and weighting in compatible
numeric and categorical keys so separate VAD sources and views cannot merge.
The corpus workbook exposes the same scope identity.

PoetryID's export boundary is intentionally different from older module
bundles: it emits six CSV files and one narrative DOCX report, with no PoetryID
JSON. Existing module exports are unchanged.

## Expansion Stage 13 interface architecture

Expansion Stage 13 adds a presentation-only layer under `versevad.ui.design`
and `versevad.ui.preferences`. `design` owns semantic **Classic**, **Dark**,
**Lavender**, **Ocean**, **Crimson**, and **Forest** tokens,
publication-light chart defaults, the shared application shell,
workspace headers, status/empty-state patterns, module presets, and report
section helpers. `preferences` owns one ignored application-level JSON file for
appearance. Preference version 2 migrates legacy `Light` and `System` values
to `Classic`; invalid or absent values also resolve safely to `Classic`.
Neither module imports an analysis engine, repository, adapter, or lexicon.

The shell exposes **Single Poem**, **Project / Corpus**, **Other Text**, and
**Lexicon Explorer** through one navigation pattern. Single Poem and Other Text
share the existing `AnalysisRequest` construction and result objects. The
Project / Corpus page continues to use schema 4 and the same corpus
orchestrator. Explorer continues to call the same `explore_lexicons` service;
its lookup and matching behavior did not change.

Fifteen single-text result tabs are reorganized into seven report families.
Within a family, each analytical module has a large native expander with a
visible completion/not-selected state. This changes navigation and visual
hierarchy only: the framework-independent result objects, exports, and stable
provenance remain unchanged.

Module presets write only existing module-selection widget keys after an
explicit **Apply** action. They never write threshold, matching, filtering,
pronunciation, or confidence settings. Appearance, collapse state, navigation,
and other presentation state remain outside analytical configuration IDs.

## Expansion Stage 14 meter and performance architecture

Expansion Stage 14 advances the package to `0.18.0.dev0`. The existing
`versevad.prosody.meter` candidate layer remains the upstream, validated
calculation. `versevad.prosody.performance_meter` is a dependent interpretation
layer over retained candidate alignments and the shared `ModuleInput`. It never
tokenizes, reloads CMUdict, or edits lexical stress.

After Stage 14 and the final pre-release repair pass, the package is promoted
to the first public-release version, `1.0.0`. This release marker does not
change analytical formulas, database schema, source identities, or existing
result semantics.

`versevad.performance` owns bounded thread-safe preprocessing, module-result,
visualization-data, and export caches plus stable dependency fingerprints,
entry validation, timing records, diagnostics, and explicit cache management.
The existing source-hash-keyed immutable resource caches remain inside their
adapters/modules and are exposed through the same diagnostic view. No cache is
the authoritative research record.

The application orchestrator keys each module only by relevant dependencies.
For example, meter includes its configuration and pronunciation result ID;
PoetryID includes its configuration and completed VAD/lexical result IDs.
Appearance and export controls enter neither key. Custom injected test modules
bypass shared result caching.

Schema 4 requires no migration: added meter metrics use the generic module
tables, and added audit files use checksummed artifacts. Single Poem, Other
Text, and corpus work-level analysis call the same `MeterModule`.

Normal application startup no longer executes session-revision reloads unless
`VERSEVAD_DEV_HOT_RELOAD=1` is explicitly set or a genuine API-compatibility
check fails. Complete exports are constructed only after a user action and are
then cached by immutable analysis identity.

## Implementation references

- [Streamlit: run an app locally](https://docs.streamlit.io/develop/concepts/architecture/run-your-app)
- [Python: `sqlite3` transaction control](https://docs.python.org/3/library/sqlite3.html)
- [spaCy: models and versioned pipelines](https://spacy.io/usage/models)
- [uv: managed Python installations](https://docs.astral.sh/uv/guides/install-python/)
- [PyInstaller manual](https://pyinstaller.org/en/stable/index.html)

## Expansion Stage 15 inherited-form architecture

`versevad.inherited_form.profiles` owns the core records and registry
validation; `versevad.inherited_form.expanded_profiles` owns the source-backed
version-2 expansion. Together they expose one 169-profile registry.
`versevad.inherited_form.engine` owns feature extraction, ranking,
classification, confidence, module metrics, coverage, warnings, and
provenance. Streamlit and exporters consume typed results; they do not contain
independent form-recognition rules.

```text
ModuleInput(PoemDocument)
 + PronunciationAnalysisResult
 + MeterAnalysisResult
 + PhonologicalAnalysisResult
 -> InheritedFormEngine
 -> InheritedFormAnalysisResult
    -> best_candidate / nearest_alternative
    -> FormCandidateResult(s)
       -> FormFeatureEvidence(s)
    -> ModuleResult
```

The application orchestrator runs pronunciation, meter, and phonology when
Inherited Form Analysis is selected, even if those dependency checkboxes are
not separately selected. Their immutable result IDs enter the inherited-form
cache key. The engine does not load CMUdict or rescan meter/rhyme.

Single Poem renders the result in `versevad.ui.inherited_form`. Project /
Corpus persists the same common `ModuleResult` through schema 4 and adds a
per-poem comparison over generic stored metrics. `versevad.exports.inherited_form`
produces six UTF-8 CSV files and a deterministic narrative DOCX report. The
repository stores all seven artifacts with size and SHA-256; no schema
migration and no JSON artifact are required.

The engine ranks the full registry but the main no-match presentation renders
only ten nearest candidates. The separate all-form selector and exports consume
the full typed result. Manual profiles retain unscored defining requirements
and are excluded from automatic suggestions.

Adding a later form should ordinarily require a new registry record plus a
feature detector only when shared evidence cannot express the form. Every
added profile must include sources, definitions, assessment mode, limitations,
weights, tolerances, exact fixtures, and near-miss coverage.
