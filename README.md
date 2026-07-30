# VerseVAD

VerseVAD is a local scholarly application for transparent analysis of
affective vocabulary in poetry and other literary texts.

It will measure the distribution of words and phrases associated with
normative valence, arousal, dominance, emotion categories, and emotion
intensity. It will **not** determine what a poem "feels," what an author
intended, or what a reader experiences.

Resource-free analysis also includes offline VADER rule-based polarity evidence
and transparent English readability formulas. Both carry visible domain
cautions: VADER is not an emotional-archetype classifier, and prose-oriented
grade formulas do not measure literary quality or a reader's ability.

## Current status

**VerseVAD 1.0.0 is the first public-release version.** The repository includes
GPL-3.0-only licensing and root-level citation metadata for scholarly reuse.
Research lexicons and private texts remain local and excluded from source
control.

**Phase 5: the local one-poem, comparison, corpus, review, and Lexicon Explorer workspaces
are complete.** The one-poem path now explains VAD, shows token/type weighting,
top contributors, and cumulative normative lexical loads. Persistent projects
can import an entire folder as separate works, preserve text versions and
metadata, compare works, create named/versioned review scenarios, and export
CSV research tables with a readable Word report. Flags, exclusions, and approved mappings are scoped,
reversible, auditable, and applied only through an exact scenario version.
Collection VAD reports both a token-weighted volume profile and an
equal-work-weighted profile so long poems do not determine the only result.
It now keeps pooled lexical-rating standard deviation separate from the
standard deviation of poem-level means, and the poem comparison pairs each VAD
mean with its within-poem population standard deviation.

The interface now groups stable workspace routes under **Analyze**,
**Collections**, **Explore**, and **Learn**. Compare Poems accepts a dynamic set
of two through ten poems under one shared analytical design and reports
side-by-side values, equal-poem means, and poem-level dispersion. Hosted custom
analysis profiles last for the browser session and never retain poem text or
results. PoetryID presents category fit as its primary descriptive archetype
and nearest centroid as a secondary candidate.

**Analysis Library** now preserves single-text analyses, comparison sets,
Lexicon Explorer lookups, drafts, and contextual research notes for the current
isolated hosted session. Saves use immutable revisions and reopen as historical
results without silent recalculation. Users can retain full analysis/text or a
non-restorable results-only CSV/Word bundle. Notes remain excluded from exports
unless explicitly selected. Hosted library data are temporary and should be
downloaded before the session ends.

The one-text report uses a persistent dropdown, all large report panels start
collapsed while remaining independently expandable, and the native sidebar
arrow hides or restores the sidebar while the wide workspace resizes. In
Affective Evidence, matched-rating dispersion is a standalone VAD section
immediately below the VAD definitions.

The Affective Evidence report now also includes VADER positive/neutral/negative
proportions and compound score, plus a source-selectable **Lexical Trajectory**
chart of line-level mean valence, arousal, dominance, and—when enabled—
concreteness. Multiple VAD lexicons remain separate in the chart dropdown, and
changing the source retains the current report section. The
**Acquisition & Readability** report combines optional normative AoA evidence
with always-available Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog,
Automated Readability Index, Coleman-Liau, and sentence-qualified SMOG output.
Out-of-dictionary syllables remain explicitly heuristic until a session
pronunciation override is approved.

Scrollable result tables retain Streamlit's fixed header row and pin the
leftmost data column, keeping row meanings visible while scholars move through
long or wide results in every workspace.

The new Language Profile reports model-assigned part-of-speech counts and
relative shares independently of affective-lexicon coverage, both for one poem
and for combined/work-by-work corpus views. It pairs a broad readable profile
with a detailed Universal Dependencies tag breakdown. For one-text results, a
separate source-specific subsection reports matched normalized VAD means by
broad POS using both token and type weighting, with coverage and mixed-POS
phrases kept explicit. Positive/negative sentiment is presented separately
from the eight emotion associations.

The Poetic Fingerprint expansion through Stage 12 is also complete. Stage 0 added
framework-independent module contracts and read-only local resource validation.
Stage 1 now adds one reusable, poetry-preserving `PoemDocument` with exact
section/stanza/line structure, separate model sentences, shared token and
linguistic records, explicit configuration, coverage, and warnings. Each
one-poem request is processed once for all selected lexicons, the Language
Profile exposes the shared processing record, and the full audit ZIP includes
the complete `processing_*.csv` representation. Stage 2 adds optional local normative lexical
concreteness analysis from the user-supplied Brysbaert, Warriner, and Kuperman
workbook, with exact/lemma/phrase audits, token/type coverage, descriptive
statistics, structural views, configurable orientation bands, and six
dedicated exports. Current affective calculations remain unchanged. Stage 3
adds an optional local SUBTLEX-US Zipf frequency and rarity
profile with exact-word-form priority, token/type coverage, a primary
token-weighted median, descriptive distribution and structural views, seven
audit exports, and a non-default content-word scope limited to model-tagged
`NOUN`, `VERB`, `ADJ`, and `ADV`. Unmatched forms stay missing and `wordfreq`
is not used. Stage 4 adds an optional local Kuperman retrospective Age of
Acquisition profile with token/type coverage, source-response evidence,
descriptive statistics on the original age-in-years scale, configurable
orientation bands, structural/POS views, eight audit exports, and optional
descriptive type-level relationships with enabled frequency and concreteness
results. Its contextual content-word scope is also non-default: the source
paper describes content-word sampling, but the official supplement contains
rated polyfunctional spellings whose use in a particular poem still depends
on context. Stage 5 adds optional exact observed-form CMUdict pronunciation,
syllable, and lexical-stress evidence. It retains every dictionary
alternative, leaves materially different alternatives and absent forms
missing, supports documented poem-specific ARPAbet overrides, withholds totals
for incomplete lines, and adds line/type/token audit exports. Stage 6 adds
transparent candidate-meter alignment against five recurring stress patterns
at monometer through octameter, explicit deviations, and retained pronunciation
paths. Fit and rule-based confidence are not probabilities or definitive
scansion; the short-lived common-meter comparison was removed at the user's
direction. Stage 7 adds robust exact end-rhyme schemes, perfect/identical and
masculine/feminine/multisyllabic evidence, graded slant and eye-rhyme
comparisons, internal rhyme, exact refrains, phonemic alliteration, assonance,
consonance, coverage, and line/pair audit evidence. These are local
dictionary-, spelling-, and text-based observations, not definitive performed
rhyme or dialect. At the scholar's direction, the broader visible-structure
and syntax/lineation stages were skipped. Narrowed Stage 10 adds normalized
observed surface-form diversity with configurable MATTR, HD-D, and
bidirectional MTLD, Unicode alphabetic-character word length, and lexical-token
counts for every preserved physical line and stanza. The Structure report also
summarizes average words per nonblank line, average words per stanza, and
average nonblank lines per stanza, each paired with its within-poem population
standard deviation. Stage 11 ports all seven
optional modules to Project / Corpus through the same tested engines, adds
generic immutable schema-4 storage and auditable collection summaries, and
retains pooled lexical-diversity calculations separately from equal-work
summaries. Stage 12 adds PoetryID as a transparent dependent classifier over
completed source-specific normalized VAD. It retains all 27 categorical
profiles and centroid distances, nearest alternatives, non-probabilistic
relative affinities and confidence, coverage/boundary evidence, optional
concreteness/frequency/AoA character, Single Poem maps/scales, and compatible
corpus distributions. Every source, all-matched/stopword-excluded view, and
token/type weighting remains separate. PoetryID uses CSV data and a narrative
Word report. The one-text and corpus interfaces request both token scopes by
default, and the one-text result provides independent VAD source, token-scope,
and weighting selectors.

The optional **Sensorimotor Imagery & Embodiment** module reads the verified
Lancaster Sensorimotor Norms in place and reports six perceptual modalities,
five action effectors, source SDs, published composites, exclusivity, dominant
dimensions, token/type and stopword views, cumulative and length-normalized
loads, structural trajectories, and complete match coverage. These
context-free lexical norms support questions for close reading; they do not
declare a poem's imagery, embodiment, intention, or reader response. The same
engine and CSV/Word audit artifacts are available to one-text, corpus, and
Lexicon Explorer workflows.

The private cloud deployment repository bundles the checksum-pinned Lancaster
CSV under `resources/Lancaster_Sensorimotor_Norms/`, so hosted users do not
need to install that resource. The public/local repository continues to omit
the dataset and documents its user-supplied installation separately.

**Compare Poems** provides a session-only contrastive workspace for two
through ten texts analyzed under one shared configuration. It places
source-specific means, within-poem population standard deviations, cumulative
and per-100 lexical loads, sensorimotor evidence, structure, sound, PoetryID,
and VerseMap evidence side by side when their modules are enabled. Its
equal-poem mean gives every poem one vote; poem-level population SD describes
variation among available poem values. Long-form CSV and narrative Word
exports preserve every poem's denominator, coverage, and missing values. The
workspace does not present its summaries as significance tests, rankings, or
substitutes for close reading. Its report navigation mirrors Single Poem,
with default-collapsed subsections and automatically fitted point plots.

Across every workspace, interface tables, chart tooltips, and numeric result
displays use at most three decimal places. This is a presentation rule only:
CSV and Word exports retain the underlying analytical precision.

Stage 15 adds **Inherited Form Analysis** to Sound & Form. Registry version
2.0 contains 169 source-documented profiles spanning fixed forms, stanza
forms, refrain and linked forms, syllabic and accentual structures, historical
traditions, modern invented forms, and contextual or visual forms that require
manual scholarly confirmation. Fifty-eight profiles are automatically
assessable, 27 are partially assessable, and 84 remain manual. The module
reuses completed pronunciation, meter, and rhyme evidence; it does not rescan
or duplicate those engines. Results separate candidate form, consistency,
evidence coverage, runner-up margin, and a non-probabilistic confidence band.
Missing evidence remains missing. The main no-match view shows only the ten
nearest profiles, while **All Inherited Forms** can compare the poem with any
registry entry and expose definitions, requirements, weights, sources,
limitations, and poem-specific evidence. Single Poem and Project / Corpus
share the same engine, persisted metrics, six CSV audit tables, and one
narrative Word report.

VerseMap adds an optional, versioned comparative space to **Single Poem** and
**Project / Corpus**. Standard Profile 1.0 compares content-word VAD means and
dispersion, emotion-association prevalence, concreteness, SUBTLEX rarity, AoA,
lexical diversity and word length, content-POS proportions, and normalized
line/stanza structure. It intentionally excludes all pronunciation and Sound &
Form evidence. Single Poem maps the analyzed poem alongside reference poems
and poet centroids; corpus projects map their works against reference poet
centroids and report work-level plus equal-work project proximity. Map axes are
weighted PCA composites, while neighbor ranking uses the complete,
coverage-aware feature space. Results include CSV data and a narrative Word
report and never make authorship, influence, quality, or meaning claims.

State-backed report and project-section navigation preserves the selected
section across Streamlit refreshes. Changing a view, weighting, lexicon, or
token scope therefore keeps the current report family active, and preparing
downloads remains in **Export & Help**. The wrapping controls are shared by
Windows, Safari, and Chrome rather than relying on browser-specific scripting.

Every VAD analysis also reports two clearly labeled lexical views: all matched
tokens and stopwords excluded. The stopword-excluded view uses a pinned,
versioned English list, protects meaning-changing terms such as `not`, `never`,
and `without`, supports auditable custom additions/removals, and preserves
published phrase matches intact. Neither view assigns a value to unmatched
tokens.

Lexicon Explorer searches all installed affective sources plus concreteness,
Lancaster sensorimotor norms, SUBTLEX-US, Kuperman AoA, and CMUdict for exact
entries, phrases, explicitly
labeled lemma-derived or user-mapped lookups, ratings, frequency fields,
pronunciation/stress candidates, emotion associations/intensities, Warriner
uncertainty fields, source provenance, and derived normalized comparisons. It
also reports local VADER polarity for the entered word or phrase and applicable
word-level readability evidence—character count, syllable estimate and method,
polysyllabic status, and pronunciation coverage—while reserving document-level
readability formulas for analyzed poems or texts.
CMUdict alternatives include on-demand offline speaker previews of their exact
ARPAbet sequences; the same local preview and session selection workflow is
available for ambiguous words under **Words Needing Attention**. A word absent
from CMUdict remains unmatched, but the same panel can show a clearly labeled
provisional US-English G2P candidate. The default is to leave it unresolved;
only an explicit approve/edit action copies ARPAbet into the session override
configuration and permits dependent analysis to use it.
Each completed lookup can be downloaded as a printable narrative Word report
containing all available evidence and provenance shown for that query.
Warriner's 102 and NRC VAD v1's 132
whitespace-containing source entries now participate as exact phrase candidates
under the selected policy.

See:

- [Implementation plan](PLANS.md)
- [Architecture decision](docs/architecture.md)
- [Poetic Fingerprint Stage 0 reconciliation](docs/poetic-fingerprint-stage0.md)
- [Poetic Fingerprint Stage 0 validation](docs/poetic-fingerprint-stage0-validation.md)
- [Poetic Fingerprint Stage 1 shared processing](docs/poetic-fingerprint-stage1.md)
- [Poetic Fingerprint Stage 1 validation](docs/poetic-fingerprint-stage1-validation.md)
- [Poetic Fingerprint Stage 2 concreteness](docs/poetic-fingerprint-stage2.md)
- [Poetic Fingerprint Stage 2 validation](docs/poetic-fingerprint-stage2-validation.md)
- [Poetic Fingerprint Stage 3 frequency and rarity](docs/poetic-fingerprint-stage3.md)
- [Poetic Fingerprint Stage 3 validation](docs/poetic-fingerprint-stage3-validation.md)
- [Poetic Fingerprint Stage 4 Age of Acquisition](docs/poetic-fingerprint-stage4.md)
- [Poetic Fingerprint Stage 4 validation](docs/poetic-fingerprint-stage4-validation.md)
- [Poetic Fingerprint Stage 5 prosody foundation](docs/poetic-fingerprint-stage5.md)
- [Poetic Fingerprint Stage 5 validation](docs/poetic-fingerprint-stage5-validation.md)
- [Poetic Fingerprint Stage 6 candidate meter](docs/poetic-fingerprint-stage6.md)
- [Poetic Fingerprint Stage 6 validation](docs/poetic-fingerprint-stage6-validation.md)
- [Poetic Fingerprint Stage 7 rhyme and phonological patterns](docs/poetic-fingerprint-stage7.md)
- [Poetic Fingerprint Stage 7 validation](docs/poetic-fingerprint-stage7-validation.md)
- [Poetic Fingerprint Stage 10 narrowed lexical style](docs/poetic-fingerprint-stage10.md)
- [Poetic Fingerprint Stage 10 validation](docs/poetic-fingerprint-stage10-validation.md)
- [Poetic Fingerprint Stage 11 project/corpus and Explorer](docs/poetic-fingerprint-stage11.md)
- [Poetic Fingerprint Stage 11 validation](docs/poetic-fingerprint-stage11-validation.md)
- [Poetic Fingerprint Stage 12 PoetryID](docs/poetic-fingerprint-stage12.md)
- [Poetic Fingerprint Stage 12 validation](docs/poetic-fingerprint-stage12-validation.md)
- [Poetic Fingerprint Stage 14 performance-aware meter and optimization](docs/poetic-fingerprint-stage14.md)
- [Poetic Fingerprint Stage 14 validation](docs/poetic-fingerprint-stage14-validation.md)
- [Stage 14 performance report](docs/stage14-performance-report.md)
- [Stage 15 inherited-form analysis](docs/inherited-form-stage15.md)
- [Stage 15 inherited-form validation](docs/inherited-form-stage15-validation.md)
- [VerseMap reference-corpus maintainer workflow](docs/versemap-reference-corpus.md)
- [VerseMap Standard Profile 1.0](docs/versemap-standard-profile.md)
- [Public resource installation guide](docs/resource-installation.md)
- [macOS installation and browser guide](docs/macos-installation.md)
- [Safe in-place update guide](docs/updating.md)
- [Lexicon inventory](docs/lexicons.md)
- [Methodological commitments](docs/methodology.md)
- [Data model](docs/data-model.md)
- [Testing strategy](docs/testing.md)
- [Beginner user guide](docs/user-guide.md)
- [Analysis Library, drafts, and research notes](docs/research-library.md)
- [Private Streamlit Community Cloud deployment](docs/streamlit-community-cloud.md)
- [Comprehensive Word user manual](docs/VerseVAD_User_Manual.docx)
- [Values and terminology Word guide](docs/VerseVAD_Values_and_Terminology_Guide.docx)
- [Phase 5 validation and test steps](docs/phase5-validation.md)
- [Phase 3 validation and test steps](docs/phase3-validation.md)
- [Phase 4 validation and test steps](docs/phase4-validation.md)

## Privacy and source materials

Ordinary analysis will run locally. Runtime code must not upload literary
texts, lexicons, projects, or results.

The installed application does not call an external generative-AI or text-analysis
API. After setup, ordinary analysis does not depend on a third-party subscription.
Internet access is needed only when installing or deliberately updating software
dependencies.

The research datasets are not part of VerseVAD and are not distributed in the
public repository. This separate private deployment repository contains only
the checksum-pinned runtime copies that its owner is authorized to host.
Third-party sources retain their own licenses and are not relicensed by the
VerseVAD GPL.

Users download each desired source from its official page and place the
unchanged file at the exact documented path. On startup, VerseVAD reports
missing, malformed, and unsupported resources; affected sources or modules
remain unavailable while installed analyses continue to work. See the
[resource installation guide](docs/resource-installation.md) for official
links, filenames, supported SHA-256 values, and license cautions.

## License

VerseVAD source code and documentation are free and open-source software
licensed under
[GNU General Public License v3.0 only](LICENSE) (`GPL-3.0-only`). You may use,
study, modify, and distribute VerseVAD, including commercially, subject to the
GPL. Distributed derivative versions must provide corresponding source and
retain the GPL terms. VerseVAD is provided without warranty.

The GPL covers VerseVAD itself. It does not grant permission to redistribute
or commercially use third-party lexicons, datasets, papers, language models,
or literary texts. Those materials remain governed by their own licenses and
terms.

## Start the graphical application

VerseVAD has project-local setup and launchers for Windows and macOS. Both use
the same cross-platform `uv.lock`, Python package, resources, project database,
and browser interface. Setup may use the internet to download the pinned
runtime and dependencies; ordinary startup is offline.

`pyproject.toml` is the direct dependency manifest and `uv.lock` is the
complete, exact cross-platform dependency lock. Together they replace a
traditional `requirements.txt`; do not install packages manually before using
the supplied setup helper.

### Windows

On the first run, double-click `setup_windows.bat`. For ordinary use,
double-click `start_versevad.bat`.

### macOS

On the first run, open Terminal in the VerseVAD folder and run:

```bash
bash setup_macos.command
```

The setup supports Apple silicon and Intel Macs running macOS 13 Ventura or
newer, requires no administrator access or system-wide Python installation,
and makes the `.command` launchers executable. For ordinary use, double-click
`start_versevad.command`, or run:

```bash
./start_versevad.command
```

Safari or Chrome opens the same local address,
`http://127.0.0.1:8501`. Keep the small launcher window open while working.
Streamlit supports the two most recent Safari and Chrome versions; update an
older browser before troubleshooting VerseVAD. See the
[macOS installation and browser guide](docs/macos-installation.md) for
first-run permissions, diagnostics, and browser checks.

For later releases, do not replace a working installation. A Git clone can be
updated in place with GitHub Desktop or `git pull`; ignored lexicons, research
resources, projects, exports, and runtime files remain local. Follow the
[safe in-place update guide](docs/updating.md), including its separate check
for a folder originally obtained with **Download ZIP**.

On either operating system, ordinary startup and analysis use the installed
local files and do not upload the poem or results.

In the app, use the shared workspace navigation across the top. The same header
also provides persistent **Classic**, **Dark**, **Lavender**, **Ocean**,
**Crimson**, and **Forest** appearance themes. The saved choice returns when
VerseVAD is closed and reopened:

1. **Single Poem** accepts pasted text or one `.txt` file and provides readable
   results plus the audit bundle.
2. **Project / Corpus** creates persistent local projects, imports a folder of
   `.txt` works, analyzes complete affective and optional-module batches,
   compares collection and part-of-speech views, records versioned review
   scenarios, and exports CSV data plus narrative Word reports.
3. **Other Text** reuses the single-text report pattern for prose and other
   non-poetic material while marking poetry-specific sound/form modules as
   experimental.
4. **Lexicon Explorer** looks up one word or phrase in every installed
   affective and supplementary lexical resource while preserving original
   fields, missingness, alternatives, and match provenance.

See the [beginner user guide](docs/user-guide.md) for interpretation and
troubleshooting, or open the
[comprehensive Word manual](docs/VerseVAD_User_Manual.docx) for every feature,
term, output, and formula in one document. The companion
[values and terminology guide](docs/VerseVAD_Values_and_Terminology_Guide.docx)
adds beginner-focused worked examples and reporting templates.

## Development-only inspection

The Phase 0 inspection script uses only the Python standard library and never
writes to `source_lexicons/`:

```powershell
python scripts\inspect_lexicons.py
```

Nontechnical users do not need to run this inspection command routinely.

## Test the Phase 1 engine

Double-click `test_phase1.bat`. A console window will run an invented,
hand-calculated example and pause so the result can be read. Success is shown as
`VerseVAD Phase 1 validation passed.` The generated CSV files are placed in
`phase1_demo_output/`, which is excluded from source control.

See [the Phase 1 validation report](docs/phase1-validation.md) for the expected
numbers, limitations, and removal instructions.

## Test Phase 2

Double-click `test_phase2.bat`. The test verifies all five source checksums,
reproduces the hand-calculated phrase, category, and intensity examples, then
runs one short invented text independently through all five lexicons. It writes
the auditable CSV files to
`phase2_demo_output/` and creates no consensus score. See
[the Phase 2 validation report](docs/phase2-validation.md).
