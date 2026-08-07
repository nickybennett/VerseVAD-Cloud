# VerseVAD Architecture

Status: current for VerseVAD 1.0.0.

VerseVAD is a modular Python application with a local Streamlit interface,
framework-independent analysis engines, versioned resource adapters, and
SQLite persistence for collections and explicitly saved research work.

## System boundary

Ordinary local analysis stays on the user's computer. VerseVAD does not send
poems, lexicons, project databases, notes, or results to an external analysis
service. First-time setup may download the pinned Python runtime and software
dependencies. Research datasets are installed separately by the user.

The browser address `127.0.0.1:8501` is a loopback endpoint served by the
local Streamlit process. It is not an Internet-facing address.

## Layered design

```text
Streamlit workspaces and presentation
                |
Application and orchestration services
                |
Shared poetry-preserving PoemDocument
                |
Independent analysis modules
                |
Matching and versioned resource adapters
                |
Immutable source files and local SQLite stores
```

### User interface

`src/versevad/ui/` owns navigation, controls, charts, tables, accessibility,
session state, and download presentation. It does not define statistical
methods or parse lexicons.

The interface routes workspaces under four top-level groups:

- **Analyze:** Single Poem, Compare Poems, Other Text, Lexicon Explorer.
- **Collections:** Personal Corpus, Saved Projects, Reference Corpora,
  Analysis Library.
- **Explore:** VerseMap, Lexicon Explorer, Form Library, Corpus Browser.
- **Learn:** Documentation and Methodology.

### Application services

`versevad.application`, `versevad.comparison`, `versevad.corpus`,
`versevad.explorer`, and related services validate requests, load selected
resources, reuse the shared processed document, call analysis engines, and
construct export-ready view models.

### Shared document processing

The preprocessing layer preserves the exact supplied text and produces a
separate immutable `PoemDocument` containing structural units, model
sentences, tokens, lemmas, POS and dependency annotations, contractions and
orthographic spans, coverage, warnings, and preprocessing provenance.

All enabled modules consume that shared record. Modules must not silently
retokenize or overwrite the preserved original.

Line-leading and line-trailing Unicode whitespace is removed only from the
processing representation used for annotations and raw-string scoring. Tokens and spans are
mapped back to the exact preserved source offsets, so indentation remains
visible and auditable without changing metric values or line/stanza counts.

### Analysis modules

Modules are separated by method and resource family:

- affective matching and summaries;
- concreteness, frequency, AoA, and sensorimotor norms;
- readability and lexical/structural measures;
- pronunciation, meter, rhyme, and recurring sound;
- inherited-form comparison;
- PoetryID;
- VerseMap.

Each module returns typed evidence, coverage, warnings, and provenance.
Missing evidence remains missing. User-interface code renders these records
but does not recalculate them.

### Resource adapters

`src/versevad/adapters/` and module-specific adapters read immutable source
files in place. An adapter owns source validation, original fields, exact
hashes, normalization rules, and supported lookup behavior. Adding a resource
should not require method changes throughout the application.

## Persistence

### Project and Personal Corpus databases

`src/versevad/db/repository.py` implements SQLite schema version 4 for
projects, preserved text versions, immutable completed runs, module evidence,
corpus aggregates, review scenarios, and audit records. Migrations are
transactional and create a verified non-overwriting backup before changing an
older database.

Personal Corpus uses the same repository and engines with a separate ignored
database at `projects/personal_corpus.sqlite3`.

### Analysis Library

`src/versevad/research_library.py` implements schema version 1 for explicitly
saved analyses, immutable save revisions, and anchored research notes. No
analysis is autosaved as a draft. Historical results reopen without silent
recalculation.

### Reference corpora

The bundled public-domain corpus is tracked under
`resources/VerseMap_Reference_Corpus/`. Private user corpora and their indexes
remain under ignored local storage. VerseMap reference records and Standard
Profile 1.0 are versioned and deterministic.

## Cross-platform runtime

Windows and macOS launchers use the same `pyproject.toml`, `uv.lock`, Python
package, resources, and Streamlit application. Platform helpers place managed
runtime files under `.runtime/`, the setup tool under `.tools/`, and the
environment under `.venv/`. These disposable paths are ignored.

The optional eSpeak NG dependency is loaded locally and lazily for
pronunciation previews and provisional unmatched-word G2P suggestions. A
prediction does not become analytical evidence until the scholar approves or
edits it as a session pronunciation override.

## Core invariants

- Preserve original text and lineation exactly.
- Keep normalization and model annotations separate from the source text.
- Never assign a neutral numeric value to unmatched evidence.
- Prefer an exact surface match before any explicit lemma fallback.
- Keep different source lexicons and value kinds separate.
- Record denominators, coverage, missingness, configuration, versions, hashes,
  and warnings.
- Keep completed analytical records immutable.
- Keep analysis methods independent of Streamlit.
- Do not commit private texts, licensed datasets, projects, exports, or
  generated environments.

## Extension points

New analytical modules should implement the common module contract and consume
the existing `PoemDocument`. New resources should receive isolated adapters.
New persisted evidence requires a tested schema migration and backward-
compatibility behavior. New interface views should present existing typed
results rather than duplicate calculation logic.

See [methodology.md](methodology.md), [data-model.md](data-model.md), and
[CONTRIBUTING.md](../CONTRIBUTING.md).
