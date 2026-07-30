# Analysis Library, Drafts, and Research Notes

## Purpose

The Analysis Library lets scholars return to a VerseVAD result without
pretending that a later software version produced the same evidence. It also
keeps recoverable drafts and context-specific interpretive notes. It does not
replace Saved Projects or Personal Corpus: those remain collection databases,
while the library preserves particular analytical sessions and revisions.

## Local and hosted behavior

In the downloadable Windows/macOS edition, the library defaults to:

`projects/analysis_library.sqlite3`

The path is ignored by Git and stays on the user's computer. Advanced local
installations can set `VERSEVAD_RESEARCH_LIBRARY_PATH` to another private
location.

In the hosted edition, VerseVAD creates the same schema in the current
session's isolated temporary directory. It is not durable cloud storage. A
session restart, timeout, or redeployment can remove it; download important
reports first.

## Draft lifecycle

Single Poem, Other Text, and Compare Poems create a recoverable draft after
entered text is applied. The draft has a stable ID, so notes can attach before
the user formally saves an analysis. VerseVAD fingerprints the draft payload
and does not add another revision when an ordinary rerun contains no change.

The clear-text menu offers three explicit outcomes:

- keep the recoverable draft and detach the current workspace;
- save a completed full analysis, then clear; or
- delete only the unsaved draft, then clear.

Discarding a draft never deletes an already saved analysis.

## Saving an analysis

**Full analysis and source text** stores the supplied text, immutable calculated
result objects, evidence, warnings, selected profile, customized settings,
resource/result identities, UI state needed to restore the view, and exact
software version. **Save analysis** appends a numbered revision. **Save as
new** creates a separate library item.

**Results only — do not retain source text** stores a readable summary CSV and
narrative Word report. It intentionally omits the restorable result payload and
token-level audit bundle because token evidence can reveal much of a source
text. A results-only save can be downloaded but not reopened as a live
analysis.

An optional project identifier records an association. It does not duplicate,
move, or overwrite project data.

## Opening historical work

Opening a full save restores the original workspace and shows its stored result
without running analytical engines. VerseVAD identifies the version that
created the revision. The user can continue viewing the historical result or
prepare a current-version reanalysis. Preparation restores the inputs and
settings; the user must still choose Analyze or Search explicitly.

## Notes and anchors

A research note stores:

- its parent context and optional analysis/project association;
- module and metric identifiers;
- an anchor type and human-readable anchor label;
- title and body;
- tags;
- creation and modification dates; and
- whether it is marked as available for deliberate note-inclusive exports.

Supported contexts include analyses, drafts, comparison sets, projects,
personal corpora, lexicon lookups, report sections, metrics, charts, passages
or lines, words or phrases, rhyme pairs, and form candidates. The Analysis
Library Notebook retrieves notes by their original object. Project links do
not overwrite the original analysis notebook.

## Export privacy

Research notes are excluded from exports by default. The export control can
include all notes for the active object, analysis-level notes only, or a
selected subset. Note IDs, dates, tags, and anchored references require a
separate metadata checkbox.

Selected notes appear in a clearly labeled **Research Notes** Word appendix.
Full audit bundles also include `research_notes.csv` and
`research_notes.md`. Comparison and Lexicon Explorer exports provide the same
default-private selection and a separate notes CSV when notes are included.

## Storage and safety

The SQLite repository uses foreign keys, immediate transactions, stable
identifiers, a schema version, and immutable revision rows. Saved analysis
payloads are compressed deterministic JSON, not pickle. Restoration accepts
only declared value types and VerseVAD-owned enum/dataclass classes.

This protects against executable serialized data, but the library is not an
encrypted vault. Anyone with access to the local computer and database file
may be able to read retained texts or notes. Use results-only storage or
operating-system disk encryption when source privacy requires it.
