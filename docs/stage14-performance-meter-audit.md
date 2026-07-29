# Stage 14 Performance and Performance-Aware Meter Audit

## Scope and safeguards

Stage 14 combines two related but separately testable changes:

1. a performance-aware realization layer above the validated candidate-meter
   engine; and
2. a measured speed, memory, cache, loading, and responsiveness pass.

The candidate-meter result remains available and unchanged in meaning.
Performance-aware output is an optional transparent interpretation layer.
Optimizations must preserve source text, token evidence, missing values,
coverage, warnings, result ordering, floating-point calculations, project
schema 4 compatibility, exports, and scholarly language.

## Measured baseline

Baseline measurements were collected on 2026-07-24 before implementation on
Windows 11, Python 3.12.13, 12 logical CPUs, the pinned local resources, and
the project virtual environment.

The repeatable scenarios used one process and one shared spaCy preprocessor.
`tracemalloc` was enabled for the memory-oriented run, so its wall times are
intentionally conservative:

| Scenario | Baseline | Tracemalloc peak |
|---|---:|---:|
| spaCy preprocessor cold initialization | 1,634.8 ms | 36.8 MiB |
| short Essential, first resource load | 4,537.8 ms | 73.5 MiB |
| short Essential, warm unchanged | 65.6 ms | 2.3 MiB |
| medium Sound and Form, first CMUdict load | 30,495.1 ms | 147.9 MiB |
| medium Sound and Form, warm unchanged | 12,830.3 ms | 2.3 MiB |
| medium Complete, remaining resources cold | 53,115.7 ms | 93.1 MiB |
| medium Complete, warm unchanged | 14,118.2 ms | 2.9 MiB |
| long Essential, resources warm | 401.5 ms | 10.9 MiB |

A warm Sound and Form profile without `tracemalloc` took 4.54 seconds and
made 11.68 million calls. Meter consumed 4.50 seconds. Its dynamic-programming
alignment made 8,064 alignment calls, and repeated rounded tuple comparison in
the inner matrix accounted for about 2.8 million `round` calls. Pronunciation
and rhyme together consumed less than 40 ms after resources were warm.

These measurements identify repeat meter alignment and unchanged-analysis
recomputation as the primary analytical bottlenecks. They do not justify
lowering candidate counts, dropping pronunciation alternatives, approximating
statistics, or weakening source validation.

## Existing meter architecture

### Pronunciation and lexical stress

- `PronunciationAnalysisResult` retains a token audit, line summaries, source
  candidates, resolved or ambiguous stress patterns, scholar overrides,
  coverage, warnings, configuration, and exact resource provenance.
- Meter consumes that result. It does not tokenize or load CMUdict again.
- `StressSyllable` retains source token ID, surface form, POS, word position,
  syllable position, and CMUdict stress digit `0`, `1`, or `2`.

### Candidate inventory and scoring

- Five primary foot families are compared: iambic, trochaic, anapestic,
  dactylic, and amphibrachic.
- Configured foot counts range from one through eight, producing the validated
  default grid of 40 candidates.
- Spondees and pyrrhics are local substitution evidence, not base candidates.
- Dynamic-programming alignment uses explicit costs for primary and secondary
  stress, content/function-word promotion, extra and omitted syllables,
  feminine endings, catalectic endings, and initial inversion.
- Every analyzable line retains all candidate fits and configured nearest
  alternatives. Missing pronunciation and excess pronunciation combinations
  remain explicit nonclassification states.

### Poem, stanza, schema, UI, and corpus behavior

- The existing poem summary ranks recurring pattern-and-foot-count candidates,
  reports fit, line coverage, variability, deviations, ambiguity, and
  rule-based confidence.
- Stanza number is retained per line, but no stanza-level inference or
  contextual realized-scansion layer currently exists.
- Meter is a schema-4 generic immutable module result with five deterministic
  exports.
- Single Poem and corpus both call the same `MeterModule`.
- The current UI presents candidate summaries, line evidence, alternatives,
  alignment operations, warnings, and provenance.
- Per-work corpus results are committed as each work completes, but a stopped
  batch has no explicit cooperative resume/cancellation API.
- Named common-meter classification remains intentionally excluded following
  the scholar's earlier decision. Stage 14 may report a generic recurring
  alternating tetrameter/trimeter sequence without reintroducing that label.

## Current performance architecture

### Already sound

- Source lexicons and supplementary resources are loaded on first selected
  use, not at process import.
- Affective and optional resource loaders use bounded process-level LRU
  caches and return shared immutable records.
- One `PoemDocument` is created per request and reused by every selected
  module through `PreparedPoemPreprocessor`.
- Pronunciation is computed once and passed to meter and phonology.
- PoetryID consumes completed VAD and lexical results without rematching.
- Corpus analysis is sequential and memory-bounded, and commits each completed
  work before continuing.
- SQLite already indexes project, text, batch, analysis, module-result,
  metric, artifact, review, and aggregate relationships.

### Measured or inspected gaps

- Unchanged requests rerun preprocessing and every selected module.
- Cache invalidation is not modeled at module dependency level.
- Existing LRU resource caches expose no unified timing or diagnostic view.
- Meter rebuilds equivalent templates and repeats the same alignment plans for
  refrains and identical stress/POS signatures.
- Fresh Streamlit sessions contain development-time compatibility reloads for
  corpus, Explorer, and design modules even when no stale module is present.
- Streamlit tabs execute hidden report code. Most importantly, the complete
  audit ZIP is assembled on every completed-result rerun before the user asks
  for it.
- Corpus progress has document counts but no elapsed-time, cache-state, stale
  reason, cooperative cancellation, or resume summary.
- Export functions construct complete in-memory byte payloads. This is
  appropriate for current Streamlit downloads but remains a large-corpus
  limitation.
- CPU-bound parallelism would duplicate large resources in processes, while
  threads do not improve the profiled Python meter loop. No concurrency change
  is justified before the alignment/cache work is measured.

## Implementation plan

### Meter layer

- Extend `src/versevad/prosody/meter.py` with explicit analysis mode, style
  profile, interpretation depth, and optional performance-aware output while
  preserving the candidate layer.
- Add `src/versevad/prosody/performance_meter.py` for contextual syllable
  prominence, promotion/demotion, caesura evidence, stress clash/lapse,
  inspectable component scoring, style reranking, realized scansion,
  stanza summaries, generic alternating patterns, confidence, and cautions.
- Cache reusable alignment plans by stress/POS signature, template, and
  configuration; materialize token-specific audit operations afterward.
- Extend `src/versevad/exports/meter.py`, the Single Poem UI, corpus controls,
  generic schema-4 artifacts, and synthetic validation without changing the
  existing candidate-only export set.

### Performance layer

- Add `src/versevad/performance.py` with bounded, thread-safe, versioned
  preprocessing/module/export caches, deterministic fingerprints, cache
  diagnostics, timing records, and safe clear/disable controls.
- Refactor `src/versevad/application.py` around the explicit dependency graph:
  shared preprocessing; independent affective/lexical/sound/structure modules;
  pronunciation before meter/phonology; completed evidence before PoetryID.
- Cache each module only by its relevant configuration, source/resource
  identity, preprocessing identity, and dependency-result IDs.
- Add cooperative corpus cancellation and exact completed-result reuse where
  safe; retain sequential deterministic persistence unless measurement proves
  a bounded worker pool beneficial.
- Remove unconditional development reload work from ordinary startup.
- Defer full audit-bundle construction until explicitly requested and bound
  derived export caching.
- Add a developer Performance Diagnostics panel with timings, cache hits,
  misses, size estimates, loaded resources, and clear/disable actions.

### Measurement and validation

- Add `scripts/benchmark_stage14.py` with startup, Single Poem, meter/refrain,
  corpus, Explorer-service, project-load, and export scenarios. Store machine-
  readable and Markdown output outside private source/resource directories.
- Add candidate-output equivalence fixtures before changing alignment.
- Add unit, integration, cache-invalidation, corpus, export, UI, and benchmark
  smoke tests. Strict wall-clock budgets remain outside the ordinary test
  suite; correctness and cache-state assertions remain stable.
- Repeat the measured scenarios, report medians and hardware, and document
  remaining bottlenecks honestly.
- Rebuild both Word guides and visually verify all four workspaces, every
  appearance theme, completed reports, meter scansion, corpus tables,
  desktop layout, narrow layout, focus, overflow, and browser diagnostics.

## Explicit non-goals for this pass

- No opaque statistical or machine-learning scansion model.
- No automatic claims about historical period, authorial intention, or a
  uniquely correct performance.
- No silent approximation, truncation, source rewriting, or neutral value for
  missing evidence.
- No hard-coded author-specific, Hopkinsian sprung-rhythm, quantitative,
  classical, or non-English metrical model.
- No reintroduction of a named common-meter classifier.
- No worker-process pool that duplicates large resources without measured
  benefit.
- No claim that synchronous Streamlit can offer instant mid-document
  cancellation; cancellation remains cooperative at safe work boundaries.
