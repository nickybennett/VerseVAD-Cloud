# Initial Data Model

This model began as the Phase 0 design. Phase 4 implements persistent local
projects and corpus results. Schema version 2 adds explicit analysis-view and
stopword-methodology fields. Phase 5 schema version 3 adds named review
scenarios, immutable scenario-version snapshots, append-only decision
revisions, semantic-risk candidates, and scenario-version links on batches and
runs. Expansion Stage 11 schema version 4 adds generic optional-module results,
metrics, coverage, warnings, artifacts, and explicit corpus aggregates.
Existing earlier databases migrate transactionally after a verified,
non-overwriting backup is created.

Phase 1 now implements immutable in-memory forms of `TextDocument`,
`TokenRecord`, `LexiconMetadata`, `LexiconValidation`, `VadEntry`, `TokenMatch`,
`CoverageStatistics`, `VadSummary`, `PreprocessingMetadata`, and
`AnalysisResult`. CSV exports carry their stable text, token, analysis,
scenario, source-hash, adapter, recipe, and model identifiers. The engine
records remain immutable in-memory values; Phase 4 persists their declared
aggregate and unmatched-review subset for corpus comparison.

Phase 2 adds immutable emotion-association and emotion-intensity entries and
lexicons, explicit lexicon value kinds and dimensions, span-based
`AffectMatchRecord` values, phrase-policy and match-selection enums, category
and intensity statistics, `Phase2AnalysisResult`, and source-specific
`CrossLexiconComparison` metrics. Match records can link one phrase to multiple
token IDs and can point from a suppressed component or overlap to the selected
phrase responsible for suppression. No consensus-score entity is populated.

Phase 3 adds an immutable `AnalysisRequest` and `WorkspaceAnalysis` plus plain
coverage, VAD, emotion-association, emotion-intensity, match, and unmatched view
records. They are framework-independent application models used by both tests
and the Streamlit page. The workspace contains the preserved `TextDocument`,
selected source-specific results, comparison record, recipe choices, and
request signature. Expansion Stage 1 adds the shared `PoemDocument` to that
workspace. The one-poem workspace remains temporary and in memory; it does not
pretend to be a persistent Phase 4 `Project` or `AnalysisRun`. Download
manifests still carry the stable text version, analysis, scenario, adapter,
recipe, software, source-hash, and inclusion metadata produced by the engine.

Phase 3.1 adds VAD definition, interpretation, contributor, and cumulative-load
view records. The framework-independent application layer also exposes a
lexicon-independent `PartOfSpeechView` over the preserved run's token records.
Phase 4 implements `projects`, `texts`, `text_versions`,
`corpus_batches`, `analysis_runs`, `analysis_metrics`,
`unmatched_observations`, and `unmatched_notes`. Every stored run links to the
active preserved text version, source hashes, adapter versions, recipe,
scenario, software version, selected lexicons, phrase policy, and minimum-match
choice. Phase 4.1 additionally records stopword mode, source/version/hash,
protected words, custom additions/removals, and `analysis_view` on persisted
metrics. Completed corpus batches are immutable; pending or failed batches do
not appear as the current comparison. Excel remains a derived export.

Phase 5 adds `review_scenarios`, `review_scenario_versions`,
`review_decisions`, and `review_candidates`. `corpus_batches` and
`analysis_runs` store the exact `scenario_version_id`. The scenario-version
snapshot stores its active decision-revision IDs, and every completed analysis
manifest retains the resolved rule payload. Flags are non-scoring; exclusions
and mappings remain auditable and scenario-specific. Part-of-speech corpus
profiles are derived locally from current preserved text versions and the
pinned preprocessing model; they do not depend on lexicon matches.

The local source lexicons are not copied into the project database. Their
immutable adapter models are loaded in place from known source paths and hashes.
Lexicon Explorer exposes exact source rows, source values, optional Warriner
standard-deviation/rater fields, normalization formulas, and provenance without
creating a second authoritative copy.

Expansion Stage 2 adds an optional `ConcretenessAnalysisResult` to the
one-poem `WorkspaceAnalysis`. It contains a common `ModuleResult`, exact
configuration, resource status/validation, overall and grouped summaries,
term summaries, and a complete `ConcretenessTokenRating` audit. Phrase-covered
tokens share a stable match-group identity. Missing ratings remain nullable
and never become numeric placeholders. These records are in memory and in
one-poem exports only; schema version 3 remains unchanged.

Expansion Stage 3 adds an optional `FrequencyAnalysisResult` to the one-poem
`WorkspaceAnalysis`. It contains a common `ModuleResult`, exact
`FrequencyConfiguration`, resource status and validation, overall and grouped
summaries, frequency bands, term summaries, and the complete
`FrequencyTokenRating` audit. Unmatched and ineligible Zipf values remain
nullable. The configuration records proper-name policy, exact-before-lemma
lookup, thresholds, coverage warning, ranking limits, and the non-default
`content_words_only` scope. These records remain in memory and in one-poem
exports; schema version 3 is unchanged.

Expansion Stage 4 adds an optional `AoAAnalysisResult` to the one-poem
`WorkspaceAnalysis`. It contains a common `ModuleResult`, exact
`AoAConfiguration`, resource status and validation, overall and grouped
summaries, acquisition-orientation bands, source-response evidence, term
summaries, optional descriptive relationships, and the complete
`AoATokenRating` audit. Unmatched, ineligible, and source-unrated ages remain
nullable. The configuration records proper-name policy, exact-before-lemma
lookup, thresholds, coverage and source-response cautions, ranking limits, and
the non-default contextual `content_words_only` scope. These records remain in
memory and in one-poem exports; schema version 3 is unchanged.

Narrowed Stage 10 adds `LexicalStyleAnalysisResult`. Its typed document summary
retains descriptive-statistics records for lexical-token counts across
nonblank physical lines, lexical-token counts across stanzas, and nonblank
physical-line counts across stanzas. These records provide count, mean,
median, population standard deviation, quartiles, and range without replacing
the detailed line/stanza summaries. Stage 11 persists the corresponding
document metrics through the generic schema-4 optional-module tables.

## Poetic Fingerprint expansion Stages 0-4

Stage 0 adds an immutable, framework-independent common envelope for future
optional modules:

```text
ModuleInput
  TextDocument
  TokenRecord[]
  PreprocessingMetadata
  optional PoemDocument (materialized in Stage 1)

ModuleResult
  module/result/text identities
  ModuleMetric[]
  ModuleCoverage[]
  ModuleWarning[]
  ModuleProvenance
    resource provenance[]
```

Metrics distinguish direct observations, computed summaries, and
interpretations. Coverage records carry eligible, matched, and unmatched counts
and keep empty denominators missing. Module provenance records the source-text
hash, software, preprocessing recipe, pipeline, configuration, scenario, and
explicit lookup and inclusion policies plus exact resource checksums.

This contract does not replace `AnalysisResult`, `Phase2AnalysisResult`, or
`WorkspaceAnalysis` in Stage 0. Existing completed runs remain authoritative.
A later read-time compatibility adapter may expose an existing VAD result
through the common envelope without rewriting it.

Stage 1 materializes the additive design:

```text
PoemDocument
  source: TextDocument
  configuration: PreprocessingConfiguration
  preprocessing: PreprocessingMetadata
  structural_units: StructuralUnit[] (section, stanza, physical line)
  sentences: SentenceUnit[]
  tokens: TokenRecord[]
  dependencies: DependencyRecord[]
  entities: EntityRecord[] (optional; disabled by default)
  orthographic_spans: OrthographicSpan[]
  token_classifications: TokenClassification[]
  coverage: ProcessingCoverage
  warnings: DocumentWarning[]
```

The single section and all physical-line records point to exact substrings of
the original, and the lines must reconstruct it exactly. Lookup normalization,
lemma, POS, morphology, sentence, dependency, and optional entity values remain
separate model-derived fields. Orthographic spans expose hyphenated
expressions, contractions, and apostrophe forms without replacing their token
components. Token classifications retain content/function/other/non-lexical
roles, proper-noun evidence through the source POS tag, and model-vocabulary
availability.

Processing coverage validates all count/rate pairs. Model OOV count/rate must
remain missing when the installed model has no usable vector vocabulary.
Dependency confidence likewise remains missing because the pipeline does not
provide calibrated per-edge confidence.

`WorkspaceAnalysis` now carries the common document, and
`ModuleInput.from_poem_document` supplies the exact same source, tokens, and
preprocessing provenance to later optional modules. `poem_document.json`
exports this record in the local one-poem audit bundle.

Stages 2, 3, and 4 consume that exact immutable document through the common
module input. Their optional result models stay distinct:

```text
WorkspaceAnalysis
  poem_document: PoemDocument
  concreteness: ConcretenessAnalysisResult?
  frequency: FrequencyAnalysisResult?
  aoa: AoAAnalysisResult?

FrequencyAnalysisResult
  module_result: ModuleResult
  configuration: FrequencyConfiguration
  resource_status and validation
  summary and frequency bands
  POS, physical-line, and stanza summaries
  term rankings and rare tail
  token_audit: FrequencyTokenRating[]

AoAAnalysisResult
  module_result: ModuleResult
  configuration: AoAConfiguration
  resource_status and validation
  summary, acquisition bands, and source-response evidence
  POS, physical-line, and stanza summaries
  term rankings and optional descriptive relationships
  token_audit: AoATokenRating[]
```

The frequency audit stores poem-specific POS and matching decisions separately
from the source workbook's POS provenance. The optional content-word
denominator includes only `NOUN`, `VERB`, `ADJ`, and `ADV`; `AUX` is explicitly
ineligible in that scope. Exact word-form entries take priority over lemma
entries, and no missing value is serialized as numeric zero.

The AoA audit retains source mean/SD, total and numeric response counts,
derived unknown-response count and numeric-response proportion, source
frequency when available, poem POS, and exact matching decisions. Its
content-word denominator also uses only `NOUN`, `VERB`, `ADJ`, and `ADV`.
Source entries without numeric means retain their source-row identity but do
not contribute to aggregates. Optional relationships are type-level,
descriptive, and nullable when fewer than three paired surface types exist.

These records remain in memory and in the derived JSON exports. Stages 1-4 do
not add schema-3 database tables. The approved possible schema-4 tables remain
documented in
[`poetic-fingerprint-stage0.md`](poetic-fingerprint-stage0.md); any migration
still requires tested transactional backup and compatibility behavior.

## Identity and versioning

All primary entities use stable opaque IDs. Human-readable titles and filenames
are not identifiers. Versioned scholarly objects are append-only once an
analysis uses them.

```text
Project
  +-- Corpus membership and metadata schema
  +-- Text
  |     +-- TextVersion
  |            +-- StructuralUnit (section/stanza/line/sentence)
  |            +-- TokenOccurrence
  +-- PreprocessingRecipeVersion
  +-- AnalysisScenarioVersion
  +-- ReviewDecisionVersion
  +-- AnalysisRun
        +-- MatchRecord
        +-- AggregateResult
        +-- Warning
        +-- ExportRecord
```

## Core entities

### Project

Title, description, principal researcher, language, research notes, creation
and modification timestamps, and active defaults. User-defined metadata fields
belong to a project schema rather than being added as ad hoc database columns.

### Text and TextVersion

`Text` is the continuing scholarly item. `TextVersion` stores the exact imported
content, SHA-256 checksum, import source, encoding, preservation warnings,
created date, and optional predecessor. Existing analyses retain their original
text-version link after later edits.

### StructuralUnit

Represents hierarchical units such as section, stanza, line, and sentence. It
records type, ordinal position, character span, and parent unit. Empty stanzas
or lines may be represented when needed to preserve structure.

### TokenOccurrence

Records text-version ID, character offsets, structural positions, token and
sentence positions, original surface form, lower form, punctuation-stripped
form, normalized form, POS, lemma, morphological features, token flags,
surrounding context, and preprocessing warnings. Model-derived fields record
the pipeline and model version that produced them.

### LexiconSource and LexiconImport

`LexiconSource` describes the scholarly resource, family, version, citation,
license notice, source scale, language, and unit of analysis. `LexiconImport`
records the local file path, checksum, observed format, validation report,
adapter version, and import date. Original values are retained as source data.

### LexiconEntry and LexiconValue

An entry stores the source term and source row identity. Values store a
dimension or category, original value, original limits, optional normalized
value, formula identifier, and source/import link. Categorical association and
numeric intensity are different value kinds.

### PreprocessingRecipeVersion

Captures Unicode, case, punctuation, tokenization, linguistic model,
possessive, phrase, compound, stopword, proper-noun, numeric, and negation
policies. It is immutable after use.

### ReviewDecisionVersion

A typed decision revision: flag, exclusion, or mapping. It stores the source
form, optional verified mapping target, lexicon, project, optional preserved
text/version and token position, occurrence/work/project/global scope,
semantic-risk category, rationale, timestamp, active/revoked state, and stable
decision identity. Revoke and restore operations append revisions rather than
updating prior history.

### AnalysisScenarioVersion

Names an immutable snapshot of the active decision revisions in one named
project review scenario. Restoring an older snapshot creates a new version.
An analysis also records recipe, lexicons, minimum-match rule, weighting,
stopword policy, software version, and other calculation inputs separately.

### ReviewCandidate

Stores occurrence-level evidence produced by an analysis for semantic-risk
review, including unmatched forms, case collisions, lemma/possessive/phrase
matches, prior mappings/exclusions, and optionally exact matches. It retains
text/version/token identity, context, proposed lemma, source candidate, match
method, and risk category. Candidate presence does not itself change a score.

### AnalysisRun

Records lifecycle state (`pending`, `running`, `complete`, `failed`, or
`cancelled`), all input-version IDs, software and adapter versions, timestamps,
warnings, and an integrity signature. Results from incomplete runs are never
presented as complete.

### MatchRecord

Links a token occurrence or phrase span to an exact lexicon entry. It records
candidate order, selected/suppressed state, match method, matched form, POS,
source value, normalized value, negation flag, inclusion status, and the review
decision responsible for any change.

### AggregateResult

Stores or caches a declared statistic only when it can link back to the run and
included match set. Dimensions include structural scope, weighting policy,
denominator, count, coverage, estimate, uncertainty, sparse-result status, and
the explicit `all_matched` or `stopwords_excluded` analysis view.

### ExportRecord

Records format, path, checksum, creation time, run/scenario IDs, and the export
schema version. Excel is an export, never the authoritative database.

## Traceability invariant

Every displayed numeric result must support this path:

```text
AggregateResult -> AnalysisRun -> included MatchRecord(s)
 -> TokenOccurrence(s) -> TextVersion -> preserved original text
 -> LexiconEntry/LexiconValue -> LexiconImport -> source checksum
```

The active scenario, recipe, matching method, and review decision must also be
recoverable from that path.

The part-of-speech profile follows a separate non-lexicon path:

```text
PartOfSpeechView -> TokenOccurrence(s) -> TextVersion
 -> preserved original text -> pinned preprocessing model/version
```

The current in-memory Stage 5 pronunciation path is:

```text
PronunciationAnalysisResult -> ModuleResult
 -> PronunciationTokenResult(s) -> TokenOccurrence(s) -> TextVersion
 -> preserved observed form -> CMUDictEntry -> CMUPronunciation candidate(s)
 -> exact dictionary/phone/symbol source hashes
```

`PronunciationTokenResult` separates eligibility, observed lookup form,
dictionary candidates, source line numbers, resolution status, resolved phones,
resolved stress, resolved syllables, categorical confidence label, override
note, and reason. An unresolved row cannot carry resolved syllable or stress
values.

`PronunciationLineSummary` records physical line/stanza identity, exact line
text, eligible/resolved/ambiguous/unmatched counts, coverage, completeness,
syllable total, word-grouped and compact lexical-stress sequences, stress
counts, and density. Incomplete lines keep totals and sequences missing.

`PronunciationConfiguration` contains thresholds, scenario identity, and
poem-specific `PronunciationOverride` records. Each override stores an exact
observed type, validated ARPAbet phones, and a required scholarly note. The
configuration hash changes when any override changes.

Stage 11 now persists these records through the generic schema-4 module tables
while preserving the same distinctions and immutability. The structured JSON
remains the complete per-work artifact.

The current in-memory Stage 6 meter path is:

```text
MeterAnalysisResult -> ModuleResult
 -> MeterLineResult(s) -> CandidateMeterFit(s)
 -> AlignmentOperation(s) -> Stage 5 StressVariant evidence
 -> MeterCandidateSummary(s) -> MeterSummary
```

`CandidateMeterFit` keeps pattern and foot count as separate fields while also
providing a readable label. It retains the base and evaluated templates, the
candidate-specific selected Stage 5 stress path, cost, fit, aligned strings,
operation audit, and deviation counts.

`MeterLineResult` has explicit analyzed, no-lexical-token,
missing-pronunciation, and too-many-variants states. An unanalyzable line has
no candidate fit.

`MeterConfiguration` records every cost and threshold, the minimum/maximum
foot counts, stress-path limit, retained alternatives, scenario ID, and a
stable hash-derived configuration ID. `ModuleProvenance` links the result to
the exact Stage 5 resource hashes and pronunciation configuration.

Stage 14 extends, rather than replaces, that path:

```text
MeterAnalysisResult
 -> existing MeterSummary + MeterLineResult(s) + CandidateMeterFit(s)
 -> optional PerformanceAwareMeterResult
    -> PerformancePoemSummary
    -> StanzaMeterSummary(s)
    -> PerformanceLineResult(s)
       -> primary/alternate RealizedScansion
          -> RealizedSyllable(s) + MetricalSubstitution(s)
          -> RealizationScores + CaesuraEvidence(s)
    -> RhythmTrajectoryPoint(s)
```

`MeterAnalysisMode`, `MeterStyleProfile`, and
`MeterInterpretationDepth` are stored in `MeterConfiguration`. Profile
definitions include an explicit label, version, tolerances, preferences, and
note. `RealizedSyllable.lexical_stress` remains source evidence while
`metrical_position` and `adjustment` are interpretation fields.

`PerformanceAwareMeterResult` is optional. Candidate-only results therefore
retain their prior shape and five-file bundle, while performance-aware results
add four audit files. The common `ModuleResult` adds document metrics for
organization, primary realized candidate, mean realized score, and
non-probabilistic confidence; schema 4 stores them generically.

`CacheEntryMetadata` records cache schema, creation timestamp, dependency
fingerprint, and approximate shallow size. `AnalysisPerformanceReport`
contains operation timings, cache status/reason, and cache snapshots. It is
ephemeral session diagnostics and is not written as an analytical module
result.

The current in-memory Stage 7 path is:

```text
PhonologicalAnalysisResult -> ModuleResult
 -> PhonologicalLineResult(s) -> RhymePairResult(s)
 -> RhymeStanzaSummary(s) + SoundFamilySummary(s) -> PhonologicalSummary
 -> Stage 5 PronunciationTokenResult evidence
```

`PhonologicalLineResult` retains the exact physical line, end word, candidate
phones and rhyme parts, resolution state, stanza/poem scheme labels, refrain
identity, internal-rhyme pairs, phoneme sequences, repetitions, densities, and
reason. `RhymePairResult` keeps exact/slant/eye relationship fields, rhyme
types, five similarity components, conservative and maximum scores, evidence
label, and note. Unresolved endings never carry a fabricated scheme group or
neutral similarity.

`PhonologicalConfiguration` records the slant threshold and weights, vowel-
family score, repetition and eye-rime thresholds, coverage warning, pair cap,
scenario ID, and stable configuration ID. Provenance links the result to the
exact Stage 5 source hashes and pronunciation configuration.

The current narrowed Stage 10 path is:

```text
LexicalStyleAnalysisResult -> ModuleResult
 -> LexicalTokenAudit(s)
 -> StructuralWordCountSummary line/stanza rows
 -> WordLengthDistributionRow(s) -> LexicalStyleSummary
 -> TokenOccurrence(s) + PoemDocument structural units
```

`LexicalTokenAudit` preserves token ID and position, exact surface, normalized
observed surface type, separate lemma, model POS, source offsets, line/stanza
identity, inclusion, alphabetic-character length, and reason. An excluded token
or unavailable character length cannot carry a fabricated zero.

`LexicalStyleSummary` records token/type counts, descriptive surface TTR,
MATTR and its window/count, HD-D and its sample size, forward/reverse and mean
MTLD plus threshold, complete word-length statistics, physical/nonblank line
counts, stanza count, and structural word-count distributions.

`LexicalStyleConfiguration` records the MATTR window, HD-D sample, MTLD
threshold, short-text caution, scenario ID, and stable configuration ID.
`ModuleProvenance` records that no external lookup occurred and pins the exact
text hash, preprocessing recipe/model, token policy, and software version.

Stage 11 persists these same Stage 10 result envelopes through the generic
schema-4 module tables without duplicating the module calculations.

## Expansion Stage 11 schema 4

Earlier module sections describe the state when each One Poem stage was
introduced. Stage 11 now persists those same result envelopes for corpus runs;
it does not alter or replace the detailed One Poem records.

`corpus_batches` adds `module_names_json` and
`module_configuration_json`. Optional-module-only batches are valid.

`module_results` provides one generic parent row per run and module. It stores
the module and result versions, configuration and scenario IDs, exact source
text hash, serialized provenance, and stable result identity.

`module_metrics`, `module_coverage`, and `module_warnings` retain the common
module contract without flattening away layer, scope, scope ID, unit,
weighting, denominator, missingness, unmatched items, or technical detail.
Metric values use JSON so numeric, categorical, boolean, and structured values
remain distinguishable.

`module_artifacts` stores the bytes produced by the existing module exporters,
plus filename, size, and SHA-256. Download reconstruction verifies the checksum
and uses deterministic ZIP metadata.

`corpus_module_aggregates` stores explicitly calculated batch-level values with
their aggregation method, work counts, observation count, configuration, unit,
and note. It does not replace the underlying work rows. Ordered pooled lexical
diversity is calculated from the persisted token-audit sequence.

## Transaction and backup rules

- Database migrations run inside transactions where SQLite permits it.
- A verified, non-overwriting backup is created before supported schema
  upgrades.
- Analysis completion is one atomic state transition.
- Restores never overwrite an open project without explicit confirmation.
- Cached results are disposable and keyed by all relevant input versions.

## Expansion Stage 12 PoetryID records

`PoetryIDConfiguration` records one exact `ThresholdProfile`, selected
weighting modes and analysis views, selected VAD lexicon IDs, requested
secondary lexical dimensions, evidence and coverage minimums, confidence and
boundary rules, distance metric, epsilon, and scenario ID. Its complete
serialized form produces a deterministic configuration ID.

`VadEvidence` adapts one completed source-specific VAD result. It identifies
the upstream analysis, lexicon/version/adapter/hash, view, weighting,
continuous normalized means and dispersion, VAD observation counts, source
coverage counts/rates, exclusions, and unmatched terms.

`PoetryIDAssignment` retains continuous VAD; three `VadLevel` values; the
categorical and nearest-centroid `PoetryArchetype`; categorical/centroid
agreement; assigned distance; all 27 `ArchetypeNeighbor` records; a
`ConfidenceAssessment`; inherited `PoetryIDCoverage`; and deterministic
narrative text.

`PoetryIDUnavailable` records the source, view, weighting, stable reason, and
plain-language message for evidence that cannot support an assignment.
`LexicalCharacterResult` retains native-scale descriptive statistics,
coverage, thresholds, weighting, source module, configuration ID, and display
orientation without entering the VAD calculation.

`PoetryIDAnalysisResult` wraps these typed records plus the common immutable
`ModuleResult`. Schema 4 stores the common result without a migration; the
seven CSV/TXT artifacts are checksummed and persisted like other module
artifacts. Corpus compatibility keys include module/configuration identity,
metric, scope ID, and weighting.

## Expansion Stage 13 UI preferences

`UiPreferences` is deliberately not an analytical or project record. Version 1
contains only:

- `version` (currently `2`);
- `appearance`, one of `Classic`, `Dark`, `Lavender`, `Ocean`, `Crimson`, or
  `Forest`.

It is stored by default at `data/private/ui_preferences.json`, which is outside
source control and separate from every project database. A malformed or absent
file safely resolves to `Classic`. Version-1 `Light` and `System` values also
migrate to `Classic`. Saves use a temporary sibling followed by an atomic
replacement.

Module presets, workspace navigation, expanded report sections, search text,
and filters remain Streamlit session state. They do not alter schema 4.

## Expansion Stage 15 inherited-form records

`FormProfile` stores profile ID/name, family, tradition, original concise
definition, tooltip definition, rules, source URLs, limitations, and registry
version. `FormRule` stores rule/feature IDs, label, role, weight, expected
wording, and typed parameters.

`InheritedFormConfiguration` stores selected profile IDs, suggestion and
coverage minimums, required-feature coverage minimum, confidence and margin
thresholds, modified-refrain floor, scenario ID, and deterministic
configuration ID.

`FormFeatureEvidence` stores expected and detected values, role, weight,
score-or-missing, evidence coverage, explanation, and contributing source
module IDs. `FormCandidateResult` stores rank, profile identity/definition,
tooltip, consistency, total and required evidence coverage, required agreement
and contradiction count, next-candidate margin, confidence, classification,
suggestion status, narrative, and all feature evidence.

`InheritedFormAnalysisResult` wraps status, registry version, ordered
candidates, best candidate, nearest alternative, exact configuration, and the
common `ModuleResult`. The common metrics persist per-work best candidate,
classification, consistency, coverage, confidence, runner-up, margin, and all
candidate ranks/scores. Schema 4 stores these generically; the seven generated
artifacts are checksummed through `module_artifacts`.
