# VerseVAD User Guide

## What is available now

VerseVAD provides four local workspaces: **Single Poem**, **Project / Corpus**,
**Other Text**, and **Lexicon Explorer**. Single-text analyses remain temporary
unless downloaded.
Corpus projects, preserved text versions, metadata, completed results, and
versioned review scenarios persist in the local `projects` database. Single-text
analysis can also enable the optional local normative lexical concreteness
module, the optional SUBTLEX-US Zipf frequency module, and/or the optional
Kuperman retrospective Age of Acquisition module when their exact local
workbooks are installed under `resources/`. **Project / Corpus** can run
and persist these plus pronunciation, meter, rhyme/sound, and lexical-style
modules through the same analysis engines used by **Single Poem**.

Do not rename or edit anything in `source_lexicons`. VerseVAD reads those files
in place and verifies their SHA-256 checksums.

Research data are not included in a public VerseVAD checkout. Before first
analysis, follow the
[resource installation guide](resource-installation.md) for official download
pages, exact destinations, supported checksums, and source-specific terms.
VerseVAD shows a startup warning for every missing or unsupported runtime file,
removes unavailable affective sources from selectors, and disables only the
optional modules whose dependencies are unavailable.

## First-time setup

1. Open the `VerseVAD` folder.
2. On Windows, double-click `setup_windows.bat`. On macOS, open Terminal in the
   folder and run `bash setup_macos.command`.
3. Allow setup to finish. The first setup may take several minutes and needs
   internet access to obtain the pinned local runtime and packages.
4. Install the desired research resources using
   `docs/resource-installation.md`. This is a separate, manual step because the
   data have their own terms and are never bundled or downloaded by VerseVAD.
5. Start VerseVAD and use **Run self-test**. Resolve any resource warning by
   checking the exact destination and supported SHA-256 in the guide.
6. Close the setup window when setup is complete.

Setup does not need administrator access and does not install Python system
wide. VerseVAD keeps its runtime, environment, and package cache inside ignored
folders in this project. The macOS setup supports Apple silicon and Intel Macs
running macOS 13 Ventura or newer.
For detailed first-run permissions and browser troubleshooting, see
[VerseVAD on macOS](macos-installation.md).

## Update an existing installation

If the VerseVAD folder is a Git clone, update it in place with GitHub Desktop's
**Fetch origin** followed by **Pull origin**, or with `git pull --ff-only
origin main`. Close VerseVAD first and inspect any tracked local changes before
pulling. Then rerun the setup helper for the current operating system; it
synchronizes only changed locked dependencies and preserves ignored lexicons,
resources, projects, exports, runtimes, and caches.

A folder obtained with **Download ZIP** has no Git history and cannot be
pulled. See the [safe in-place update guide](updating.md) for clone detection,
exact Windows/macOS commands, and a one-time ZIP-to-clone migration that keeps
the old folder until private data are verified.

## Start and stop VerseVAD

1. On Windows, double-click `start_versevad.bat`. On macOS, double-click
   `start_versevad.command`.
2. Keep the launcher window open. Your browser should open
   `http://127.0.0.1:8501` automatically.
3. If the browser does not open, type that exact address into a browser on this
   computer.
4. When finished, download the results you want to keep, then close the browser
   tab and the launcher window.

Ordinary startup is offline. The `127.0.0.1` address means the app is running
on this computer, not on a public website.

The installed app has no external generative-AI or hosted text-analysis API
dependency. Internet access is needed only if you later reinstall dependencies
or deliberately update the software.

## Appearance

The global header provides **Light**, **Dark**, and **System** appearance modes.
System follows the browser or operating-system preference. VerseVAD saves this
application-level preference locally under ignored private runtime data. It is
not stored in a project, recorded as an analysis setting, or used to calculate
or export a result. Exported charts remain publication-light.

## Analyze a poem

1. Under **Add a Poem**, either paste the text or click **Upload** and choose a
   UTF-8 `.txt` file no larger than 5 MB. A chosen file fills the editable text
   box; VerseVAD preserves that string and its line breaks as the original.
2. Enter a poem title or working label.
3. Under **Module preset**, leave **Custom** to retain the current selections,
   or choose **Essential**, **Literary**, **Sound and Form**, or **Complete** and
   click **Apply preset**. A preset changes module selections only; it does not
   overwrite advanced thresholds or other methodology.
4. Leave all five lexicons selected for a broad first look, or remove sources
   that are outside the current question.
5. Under **Additional Optional Models**, optionally enable **Normative lexical
   concreteness**, **Frequency & rarity profile (SUBTLEX-US Zipf)**, and/or
   **Age of Acquisition profile (Kuperman et al. ratings)**. Any can run with
   the affective sources or by itself.
6. Leave **Analysis configuration and methodology** closed for the default
   phrase-preferred and standard stopword analysis. Open it when you
   deliberately want a different phrase policy, sparse-result threshold, or
   custom stopword additions/removals.
7. Click **Analyze Poem**. The progress panel lists the major selected stages.
8. If you edit the text or change the evidence afterward, click **Analyze
   Poem** again before using the displayed result.

The app never assigns an unmatched token a neutral score. It attempts an exact
normalized surface match before a POS-sensitive lemma fallback and records the
method used.

## Read the result without drowning in CSVs

Use this order:

1. **Overview** — check coverage and matched counts first. A mean based on only
   a few matched observations should be treated cautiously. The displayed 60%
   and 80% coverage bands are orientation aids, not universal scholarly rules.
2. **Affective Evidence** — open the VAD, emotion association/intensity/
   sentiment, Lexical Trajectory, and PoetryID sections. Each large section is
   collapsible and reports whether it is complete or was not selected.
3. **Lexical Character** — open concreteness, SUBTLEX-US frequency/rarity, and
   Acquisition & Readability. Readability is always available; normative AoA
   appears there when enabled.
4. **Sound & Form** — open pronunciation/syllables/stress, candidate meter, and
   rhyme/recurring-sound evidence.
5. **Structure** — inspect the shared language profile plus lexical diversity,
   word length, the structural count summary, physical-line word counts, and
   stanza word counts.
6. **Evidence & Diagnostics** — inspect surface forms, phrases, lemmas,
   exclusions, approved mappings, coverage, unmatched vocabulary,
   normalization, versions, and warnings.
7. **Export & Help** — download the readable summary, tables, module exports,
   or full audit ZIP, then open the methodology/how-to-read section as needed.

The selected report section is retained when a lexicon, token/type weighting,
all-matched/stopword-excluded view, or other display control refreshes the
Streamlit page. **Prepare downloads** likewise leaves **Export & Help**
selected. The same stateful behavior applies to the six **Project / Corpus**
sections. A long section may shift slightly as its contents change, but the
interface no longer returns to **Overview** or **Works & Metadata** merely
because a control reran the page.

Choose a one-text **Report section** from the dropdown. All large vertical
sections begin collapsed and can be opened independently, so several may remain
open at once. Each expanded report section ends with a compact upward-arrow
control in its bottom-right corner, so it can be collapsed without returning to
its heading. The two large front-page option panels use the same icon control.
Hovering or focusing the icon identifies the section it will collapse. Use
Streamlit's arrow control at the top edge of the left sidebar to hide or restore
it; the main workspace automatically expands into the freed space or resizes
when the sidebar returns. The controls and responsive layout work the same way
on supported Windows and macOS browsers.

Within **Affective Evidence > VAD**, **Dispersion of Matched Ratings** is a
separate section immediately after **What Valence, Arousal, and Dominance
Mean**. Its population standard deviations describe variation among the
matched ratings, independently of the token/type mean comparison that follows.

Within **Affective Evidence > Emotion Association, Intensity & Sentiment**,
VADER reports raw positive, neutral, and negative lexical-polarity proportions
plus a rule-adjusted compound score from -1 to +1. The conventional +/-0.05
threshold label is a polarity aid, not a declaration of the poem's emotion.
VADER was designed for social-media sentiment and can misread poetic ambiguity,
irony, persona, quotation, and historical usage.

**Lexical Trajectory** plots token-weighted mean valence, arousal, and dominance
for each physical line. When Concreteness is enabled, its source 1-5 line mean
is rescaled to 0-1 with `(rating - 1) / 4` for the overlay only. Select one VAD
source from the dropdown; VerseVAD never averages the enabled lexicons together.
Changing the source or token scope retains **Affective Evidence**. Blank and
unmatched lines remain gaps rather than zeroes.

Within **Lexical Character > Acquisition & Readability**, Flesch Reading Ease,
Flesch-Kincaid Grade, Gunning Fog, Automated Readability Index, Coleman-Liau,
and SMOG appear alongside explicit counts and syllable-method coverage. SMOG
remains missing below 30 model-segmented sentences. Prose-oriented readability
formulas do not measure literary quality, actual comprehension, reader ability,
or a required grade. Contractions and hyphenated expressions count as one
orthographic word. Out-of-dictionary syllables are labeled heuristic; review
them in the default-collapsed pronunciation-attention panel and approve/edit a
session override in **Sound & Form > Words Needing Attention** when needed.

In every interactive results table, the header row stays visible while
scrolling vertically and the leftmost data column stays pinned while scrolling
horizontally. The pinned column is the table's first identifying field (for
example, Work, Lexicon, Line, Dimension, or Surface), not an invented value.
Sorting, formatting, and downloadable data are unchanged.

The **Other Text** workspace reuses this sequence with **Analyze Text**
terminology. Meter and rhyme remain available there but are visibly marked as
experimental for non-lineated prose.

### Coverage

Coverage is the number of eligible lexical token occurrences covered by an
included match divided by all eligible lexical token occurrences. It is not an
accuracy score. Different lexicons legitimately cover different vocabularies.

### Part-of-speech profile

The **Shared Processing Record** at the top of Language Profile reports stanza,
physical-line, model-sentence, total-token, and lexical-token counts; recipe
and configuration IDs; the model pipeline; dependency coverage; named-entity
recognition status; and processing cautions. Poetic lines/stanzas and model
sentences are separate layers, so their boundaries can disagree without either
being discarded.

VerseVAD creates this shared record once and reuses the same token sequence for
every selected lexicon. Original text, capitalization, punctuation, blank
lines, and line endings remain preserved. Normalized forms, lemmas, POS,
morphology, sentences, dependencies, and optional named entities are separate
model-assisted fields and may be uncertain for poetic or historical language.

The Language Profile counts all eligible lexical token occurrences by the
installed model's universal part-of-speech tag and divides each count by the
text's full lexical-token count. It also reports unique normalized types and
example forms. Shares sum to 100% apart from display rounding.

The main chart uses broad categories. **Detailed Model-Tag Breakdown** then
reports the unmerged Universal Dependencies tags with their own counts and
shares. These are two views of the same tokens, so do not add them together.

Part-of-speech labels are model-generated. Poetic syntax, fragments, archaic
forms, and deliberate ambiguity can produce uncertain assignments. Inspect
token evidence before making an argument that depends on a fine grammatical
distinction.

VerseVAD combines common-noun (`NOUN`) and proper-noun (`PROPN`) model tags
into the single displayed category **Noun**. Original token tags remain in the
detailed table and evidence/audit data. The `ADP` tag is displayed as
**Preposition**; an adverb is a different category.

It also combines main-verb (`VERB`) and auxiliary/copular (`AUX`) tags into
**Verb**. Thus `was` is counted as a verb even when the model uses `AUX` for
its grammatical role.

When at least one VAD lexicon is selected, **VAD Means by Part of Speech**
appears beneath the count/share profile. Each lexicon and the all-matched and
stopword-excluded views remain separate. For every broad POS group it reports
matched observations, distinct matched lexicon entries, covered and eligible
token occurrences, lexical-token coverage, and normalized 0-1 means for
valence, arousal, and dominance under two weighting rules:

- token-weighted means count every included matched occurrence, so repetition
  contributes repeatedly;
- type-weighted means count each distinct matched lexicon entry once within
  that lexicon, analysis view, and POS group.

Unmatched tokens do not receive neutral values. An accepted multiword lexicon
entry contributes one observation. If its lexical tokens cross broad POS
groups, VerseVAD retains it under **Mixed-POS Phrase** rather than assigning
the score to one grammatical category; that row therefore has no token-
coverage denominator. Sparse groups remain visible and are labeled.

### Normative lexical concreteness

Under **Additional Optional Models**, enable **Normative lexical concreteness** to analyze
the poem against the locally supplied Brysbaert, Warriner, and Kuperman (2014)
ratings. You can run it with affective lexicons or by itself. The dedicated
**Concreteness Profile** reports:

- mean, median, population SD, and interquartile range on the original 1-5
  source scale;
- token and unique normalized-surface-type coverage;
- configurable lower and upper orientation bands;
- physical-line, stanza, and model-assigned part-of-speech summaries;
- most concrete and most abstract represented source terms; and
- a token audit with exact, phrase, lemma, fallback, unmatched, and ineligible
  decisions.

The default bands at or below 2.0 and at or above 4.0 are VerseVAD orientation
aids, not categories validated by the paper. A matched two-word expression
assigns its rating to both covered token positions for token-weighted
statistics; the rows share one audit group. Repetition therefore matters.
Model-tagged proper nouns are excluded by default.

Describe the result as normative lexical concreteness evidence among matched
tokens. It does not measure imagery quality, readability, cognition, or
whether the poem itself is abstract or concrete. Always read coverage,
dispersion, terms, and line/stanza evidence before interpreting the mean.
Unmatched tokens remain missing.

### Corpus-relative lexical frequency and rarity

Under **Additional Optional Models**, enable **Frequency & rarity profile (SUBTLEX-US
Zipf)** to analyze observed word forms against the pinned official local
SUBTLEX-US workbook. It can run with affective lexicons and concreteness or by
itself. The dedicated **Frequency & Rarity** tab reports:

- the token-weighted median Zipf value as the primary summary;
- mean, population SD, inclusive quartiles, IQR, minimum, maximum, and range;
- token and unique normalized observed-form-type coverage;
- configurable rare-to-very-common orientation bands;
- physical-line, stanza, and model-assigned POS summaries;
- lowest/highest represented terms and a rare-word tail; and
- a complete audit with source counts, exact/lemma/fallback/unmatched methods,
  eligibility, and reasons.

Zipf is logarithmic: a one-point difference is approximately a tenfold
frequency difference in the source corpus. The default bands (rare below 3,
uncommon 3 to below 4, moderately common 4 to below 5, common 5 to below 6,
and very common at least 6) are VerseVAD orientation aids.

The default frequency scope uses all lexical tokens except model-tagged proper
nouns. The optional **Content words only** setting is off by default. When
enabled, it includes only exact model tags `NOUN`, `VERB`, `ADJ`, and `ADV`.
It excludes determiners, prepositions/adpositions, conjunctions, pronouns,
auxiliaries, punctuation, and all other tags. Proper nouns remain excluded by
the default name policy. This differs from the broad Language Profile, which
groups `VERB` and `AUX` together under **Verb**; the restricted frequency scope
specifically excludes `AUX`.

The module matches the exact normalized observed form before an enabled lemma
fallback. An unmatched form has no Zipf value; it never becomes zero and
VerseVAD does not substitute `wordfreq`. POS and lemma fields are
model-generated and may require inspection for poetry.

Describe the result as corpus-relative lexical frequency evidence in an
American subtitle corpus. Do not turn it into a claim that a poem is easy,
difficult, sophisticated, accessible, intelligent, or high quality.

### Retrospective normative lexical Age of Acquisition

Under **Additional Optional Models**, enable **Age of Acquisition profile (Kuperman et
al. ratings)** to compare the poem's observed vocabulary with the pinned
official local supplement. The ratings are adult retrospective estimates of
the age, in years, at which respondents believed they learned a word well
enough to understand it. The dedicated **Acquisition & Readability** section reports:

- token-weighted mean, median, population SD, inclusive quartiles, IQR,
  minimum, maximum, and range;
- token and unique normalized observed-form-type coverage;
- configurable early-, middle-, and later-acquired orientation bands;
- source total and numeric response counts, source SD, unknown-response count,
  numeric-response proportion, and source frequency when available;
- physical-line, stanza, and model-assigned POS summaries;
- earliest/latest represented terms and a complete token audit; and
- when Frequency or Concreteness is also enabled, descriptive Spearman
  relationships using unique paired surface types.

The default thresholds—early at or below 5 years and later at or above 12
years—are VerseVAD orientation aids, not categories validated by the source
paper. The optional **AoA content words only** setting is off by default. When
enabled, it uses the contextual model tags `NOUN`, `VERB`, `ADJ`, and `ADV`,
excluding `AUX` and function-word tags. Although the paper describes
content-word target selection, the official supplement has ratings for
polyfunctional spellings such as `the`, `and`, `he`, `of`, and `to`; the
source-list rule therefore does not determine the grammatical role of a
particular occurrence in a poem.

Matching uses exact normalized observed form before an enabled lemma fallback.
Source entries whose mean is `NA`, unmatched forms, and ineligible forms remain
missing rather than becoming age zero. The relationship coefficients require
at least three paired types and do not establish causation.

Describe the result as retrospective normative lexical AoA evidence among
matched tokens. It is not a grade-level, difficulty, familiarity,
comprehension, intelligence, literary-quality, reader-response, or cognitive
diagnostic measure. Age-of-acquisition results are not diagnostic of cognitive
impairment or decline.

### Comparing the three VAD scales

VerseVAD retains every original source rating and creates a separate derived
0-1 value for comparison:

- Warriner VAD, source scale 1-9: `(x - 1) / 8`;
- NRC VAD v1, source scale 0-1: identity, so the derived value equals `x`;
- NRC VAD v2.1, source scale -1 to 1: `(x + 1) / 2`.

This aligns endpoints and midpoints; it does not prove that the lexicons are
interchangeable. Vocabulary coverage, collection methods, versions, and source
families still differ. NRC VAD v1 and v2.1 are versions of one family, not two
independent replications. VerseVAD therefore shows separate rows and creates no
default consensus score.

NRC VAD v1's 132 whitespace-containing source entries participate as exact,
longest-first phrase candidates under the selected phrase policy, just as
Warriner's 102 activated whitespace entries do. This preserves source entries
without claiming a separate phrase-specific validation methodology.

Higher normalized valence, arousal, or dominance means a higher mean normative
rating for the matched lexical observations on that dimension. It does not mean
that the poem, speaker, author, or reader has "more emotion."

### Token/type means and cumulative load

A token-weighted mean counts every included occurrence, so repetition matters.
A type-weighted mean counts each distinct matched lexicon entry once within the
work, so it describes the matched vocabulary rather than repetition. VerseVAD
shows valence, arousal, and dominance for both.

Cumulative normative lexical load is intentionally length-sensitive. The
rating total sums normalized ratings. Above- and below-midpoint loads sum
distance on either side of 0.5; net load permits cancellation; absolute load
sums distance in either direction. These are totals of encountered matched
lexical ratings, not measurements of cognitive or emotional load on a reader.

Top contributors use a leave-one-matched-type-out calculation: VerseVAD removes
all occurrences of one matched entry and reports the change in the token mean.
The primary ranking uses `frequency × (normalized rating - 0.5)`, so repetition
and distance from the normalized midpoint remain visible. This makes rating and
repetition effects inspectable without claiming a causal effect on
interpretation.

### All matched versus stopwords excluded

The VAD page shows both views by default:

- **All matched observations** retains every included lexicon match.
- **Stopwords excluded** removes entries recognized by the declared stopword
  policy while retaining protected terms such as `not`, `never`, and `without`.

The second view uses a content-focused coverage denominator containing eligible
non-stopword tokens. Published phrase entries stay intact. Open the methodology
settings to see the pinned list source, version, active count, and hash; select
custom mode to add or remove words, import a plain-text list, or download the
active list as CSV. Every exclusion and its surface/lemma reason remains visible under
**Evidence** and in the audit exports.

### Associations versus intensity

NRC Emotion associations are binary and multi-label. VerseVAD reports anger,
anticipation, disgust, fear, joy, sadness, surprise, and trust in **Eight
Emotion Associations**. It reports positive and negative separately under
**Positive and Negative Sentiment Associations**. One occurrence may
contribute to several categories, so percentages need not total 100%. Always
read the labeled denominator.

NRC Emotion Intensity supplies numeric ratings for particular word-emotion
pairs. VerseVAD keeps prevalence separate from the mean rating among supplied
matched pairs. A missing pair is not counted as an intensity of zero. Neither
of these constructs is normalized into, pooled with, or averaged into VAD.

## Build and compare a corpus

1. Choose **Project / Corpus** in the workspace navigation across the top.
2. Create a project. It is stored in `projects/versevad.sqlite3` by default.
3. Under **Works & Metadata**, choose a folder containing UTF-8 `.txt` files.
   Each file is a separate work and subfolder paths are retained. Re-importing
   changed content creates a new preserved version under the same work ID.
4. Edit author, collection, date label, genre, notes, or custom JSON metadata.
5. Use **Language Profile** to compare part-of-speech count and relative share
   in the combined project and work by work.
6. Under **Analyze & Compare**, select works, affective lexicons, and any
   **Additional analysis modules**. Choose an unreviewed baseline or exact
   scenario version, then click **Analyze Corpus**.
   VerseVAD processes one work at a time and publishes the dashboard only when
   the entire selected batch completes.
7. Filter a completed comparison by collection, author, or genre.
8. Under **Review & Scenarios**, create a named scenario and record reversible,
   versioned flags, exclusions, or mappings with a rationale and explicit
   occurrence/work/project/global scope.
9. Rerun with that scenario and compare the new immutable batch with the
   unreviewed baseline.
10. Download the CSV and Word research bundle under **Export**.

Additional modules are off by default. Frequency and AoA each retain a
non-default **content words only** setting under **Advanced batch methodology**.
Meter or rhyme automatically includes their pronunciation dependency.

The **Additional Module Results** section keeps work, line, stanza, token, type,
and distribution evidence at its original scope. Equal-work collection means
are always labeled. Observation-weighted means appear only where a defensible
observation count exists for every included work. Lexical-style pooled results
are recalculated from the ordered pooled token sequence and are not averages of
work-level MATTR, HD-D, or MTLD. Meter and rhyme remain work-level candidates;
VerseVAD does not invent one corpus-wide meter or rhyme scheme.

Use **Download module audit ZIP** to obtain one persisted work/module bundle.
The corpus export ZIP adds separate CSV tables for collection summaries, work
results, structure, coverage, provenance, warnings, methodology, review
decisions, and part-of-speech evidence, plus `corpus_report.docx`.

To delete a project, open **Project Settings**, read the warning, and type the
project title exactly—including capitalization—before clicking **Delete this
project**. This permanently removes only that project and its locally stored
works, versions, analyses, and notes. Other projects and source lexicons are
not touched.

### Long and short works in one collection

VerseVAD reports two collection VAD views:

- **Token-weighted volume profile:** pools included matched observations. Long
  poems contribute more because they contain more of the volume's vocabulary.
- **Work-weighted volume profile:** averages eligible work-level token means.
  Every poem contributes one score regardless of length.

Neither is the universally correct view; they answer different questions. The
dashboard and corpus CSV/Word bundle show their signed difference. A divergence may be
an important result. A work with no eligible score is reported as omitted and
never assigned a neutral value.

The collection table also reports two different population standard
deviations:

- **Pooled lexical-rating SD:** the spread of all included matched token
  ratings around the token-weighted volume mean. VerseVAD reconstructs it
  exactly from each poem's matched-observation count, mean, and within-poem
  population SD. It stays unavailable if a required poem-level SD is missing.
- **Across-poem mean SD:** the spread of included poem-level token means around
  the work-weighted volume mean. Use it to describe how much poem means differ
  within the selected corpus.

Median, lowest, and highest poem means provide additional context. Under
**Compare Individual Works**, one row per poem and analysis view shows
valence, arousal, and dominance means beside their within-poem population SDs.
These SDs describe normative lexical-rating spread. They are not confidence
intervals, uncertainty in the source ratings, or declarations about emotion.

### Corpus part-of-speech views

**All Works Combined** pools lexical-token occurrences, so longer works
contribute more to the combined grammatical profile. **Work-by-Work
Comparison** reports each work's count and within-work share separately. Use
the latter when comparing relative grammatical composition across differently
sized works. Broad and detailed profile levels are both available.
`corpus_part_of_speech.csv` includes the same rows and a **Profile Level**
field.

### Review scenarios

A **flag** records a concern without changing scores. An **exclude** decision
keeps the candidate in the audit but omits it from that scenario's aggregates.
A **map** decision links a form to a verified exact entry in one installed
lexicon only after exact, apostrophe/possessive, and lemma candidates fail.

Use the narrowest defensible scope and provide a scholarly rationale. Every
change, revoke, restore, or restored snapshot creates a new append-only
scenario version. Completed corpus batches stay linked to the exact scenario
version and decision revisions used, so the baseline is never overwritten.

## Use Lexicon Explorer

1. Choose **Lexicon Explorer** in the workspace tabs across the top.
2. Enter one word or phrase. VerseVAD searches every installed source.
3. Read **How it matched** before reading values: exact entry, exact phrase,
   lemma-derived entry, or user-supplied mapped lookup are distinct.
4. Leave **Original and normalized** selected to retain source ratings and the
   separate derived 0-1 comparison together.
5. Expand variation/provenance panels when investigating a surprising entry.
6. Select **Download printable Word report** to save the complete lookup,
   including available evidence, comparisons, notices, and source provenance.

The **Additional Lexical Evidence** section searches installed concreteness,
SUBTLEX-US, Kuperman AoA, and CMUdict resources. It reports source-supplied
ratings and response fields, Zipf and accompanying frequency/contextual-
diversity fields, and every exact pronunciation candidate with ARPAbet phones,
syllable count, and lexical-stress digits. Available-but-unmatched,
source-entry-without-numeric-rating, and resource-unavailable are distinct
states. Missing evidence never becomes zero or neutral.

The **Rule-Based Sentiment and Readability Evidence** section reports VADER
positive, neutral, and negative proportions and compound score for the exact
entered string. It also reports applicable word-level counts, syllable evidence,
polysyllabic status, and pronunciation coverage. These are local calculations,
not source ratings. Document-level Flesch, grade, Fog, ARI, Coleman-Liau, and
SMOG values are intentionally reserved for complete poem or text analysis.

Warriner standard deviations and rater counts appear where supplied. Empty
uncertainty cells mean the source did not provide those fields. Cross-lexicon
"agreement" is a labeled VerseVAD range heuristic, not a source reliability
statistic. A component average appears only when a phrase has no published VAD
entry in that source and all component words do; it is clearly labeled as a
derived value. Similar-word suggestions are never substituted automatically.

An optional user mapping can display, for example, `o'er → over`, but it is a
lookup-only fallback and does not alter poem or corpus analysis. Persistent,
scenario-controlled mappings are created separately under **Review &
Scenarios**.

The Explorer Word report is a printable record of the current lookup. It
includes affective ratings and associations, original and normalized VAD,
source uncertainty where available, supplementary lexical evidence,
pronunciation alternatives, local VADER and word-level readability evidence,
derived comparisons, missing-resource statuses, and provenance. It does not
alter or replace the CSV audit exports produced by poem and corpus analyses.

Each CMUdict alternative also has a **Hear** speaker control. The preview is
generated locally from that exact ARPAbet sequence with bundled eSpeak NG
formant synthesis; no query or audio is sent elsewhere. The synthetic voice is
an orientation aid, not a human recording, dialect authority, or
context-sensitive performance.

## Downloads and the audit bundle

The easiest download has a filename ending in `_scholar_summary.csv`. It
contains compact part-of-speech, coverage, normalized VAD,
emotion-association, sentiment-association, and intensity rows with plain
labels and denominator notes. `VerseVAD_CSV_reading_guide.csv` explains what
each detailed file is for.

The full audit ZIP contains the friendly CSV files,
`VerseVAD_analysis_report.docx`, module-specific `*_report.docx` files, and:

- `phase2_match_audit.csv`, `phase2_coverage.csv`,
  `phase2_vad_summary.csv`, `phase2_emotion_associations.csv`,
  `phase2_emotion_intensity.csv`, `phase2_cross_lexicon_comparison.csv`, and
  `phase2_manifest.csv` for affective evidence and reproducibility;
- `vad_by_part_of_speech.csv` for source- and view-specific token- and
  type-weighted VAD means by broad POS;
- `processing_source.csv`, `processing_configuration.csv`,
  `processing_structure.csv`, `processing_sentences.csv`,
  `processing_tokens.csv`, `processing_dependencies.csv`,
  `processing_entities.csv`, `processing_orthographic_spans.csv`,
  `processing_coverage.csv`, and `processing_warnings.csv` for the exact shared
  processing representation;
- module CSV sets for concreteness, frequency, AoA, pronunciation, meter,
  rhyme/sound, lexical style, and PoetryID when enabled.

In **Structure > Lexical & Structural Measures**, the **Structural Count
Summary** reports average words per nonblank physical line, average words per
stanza, and average nonblank physical lines per stanza. Each average is paired
with the population standard deviation across all corresponding units in that
poem. Blank lines that separate stanzas remain visible as zero-count rows in
the detailed line table but are not included in words-per-line or
lines-per-stanza denominators.

CSV files use UTF-8 with a byte-order mark so current versions of Excel usually
open them correctly. VerseVAD does not generate JSON, TXT, or XLSX analysis
exports. `processing_source.csv` contains the original text, so protect the
full bundle as research material. Optional-module CSV files retain
poem-specific evidence and source-row provenance without copying the complete
licensed lexicon workbooks. The full ZIP is the reproducibility record; the
Word reports and scholar summary are the reading aids.

## Pronunciation & Prosody foundation

In **Single Poem**, select **Pronunciation & prosody foundation (CMUdict)** and
analyze. No affective lexicon is required for a pronunciation-only run.

The dedicated tab reports exact observed-form dictionary coverage, syllables
per resolved word, complete-line syllable totals, lexical-stress sequences,
stress density, ambiguous alternatives, out-of-dictionary forms, warnings,
and provenance. `0`, `1`, and `2` mean unstressed, primary lexical stress, and
secondary lexical stress. They are dictionary lexical stresses, not a meter
classification.

VerseVAD retains every CMUdict alternative. A word resolves automatically only
when there is one candidate or all candidates agree on syllable count and the
full stress sequence. Otherwise it remains visibly ambiguous. Missing and
ambiguous values are not set to zero.

Contractions are analyzed as the complete spelling preserved in the poem.
Thus `you're`, `can't`, `won't`, and `'tis` receive one exact pronunciation
lookup apiece. Internal tokenizer components such as `'re`, `ca`, `wo`, and
`n't` remain auditable but are not counted as pronunciation words and do not
appear as separate out-of-dictionary forms.

Expand the default-collapsed **Words Needing Attention** panel to review
materially ambiguous words. They have a selector for every retained dictionary
candidate, and each displayed ARPAbet sequence has a **Hear** speaker control.
Choose only when the poem's context supports that reading, then select **Apply
Approved Pronunciations and Reanalyze**. VerseVAD copies the choice into the
editable session override field and recalculates pronunciation, meter,
rhyme/sound, and inherited-form evidence once.

Words absent from CMUdict remain visibly **unmatched**. Inside **Words Needing
Attention**, turn on the default-off **Show Out-of-Dictionary Words** control
to reveal their local US-English eSpeak NG G2P candidates, each labeled
**provisional—not confirmed**. Choose **Leave explicitly unresolved** to keep
all pronunciation-dependent evidence missing, which is the default.
Alternatively, approve the prediction or edit its ARPAbet directly, choose
**Approve or edit for this session**, and apply it. Only that explicit approval
creates a source-labeled session override and recalculates dependent evidence.
Playing **Hear** does not approve the candidate.

To document a context-sensitive, dialectal, historical, performed, or
poetically elided reading, open **Advanced methodology settings** and enter:

```text
word = UPPERCASE ARPAbet phones | brief scholarly note
```

For example:

```text
permit = P ER0 M IH1 T | verb reading in this line
```

The note is required. Symbols and stress are validated against the pinned local
CMUdict inventory. The override applies to the exact observed word type in the
current analysis, remains separate from dictionary candidates, and can be
reversed by removing it and analyzing again.

Audible previews use bundled eSpeak NG formant synthesis entirely on the local
computer. They pronounce the displayed phone sequence but are not recordings
and should not be treated as evidence for dialect, historical realization, or
performed scansion.

A line total and stress sequence appear only when every eligible word on that
physical line resolves. This prevents partial coverage from making a line look
shorter than it is.

Always retain the visible warning: CMUdict primarily represents North American
dictionary pronunciation. Dialect, historical pronunciation, context,
performance, and poetic elision may differ. Stage 5 does not classify meter,
rhyme, or definitive performed scansion.

## Meter & Rhythm

In **Single Poem**, select **Meter & rhythmic regularity** and analyze. The option
is off by default. It automatically runs the local pronunciation foundation,
so no affective lexicon is required.

The module compares iambic, trochaic, anapestic, dactylic, and amphibrachic
base patterns at monometer through octameter. Spondees and pyrrhics are local
substitution labels, not ordinary whole-line base candidates.

Open **Meter & Rhythm** to read:

1. nearest fixed pattern-by-foot-count candidate;
2. mean fit, matching lines, analyzable-line coverage, nearest alternative,
   candidate margin, and rule-based confidence;
3. each physical line's nearest fixed template;
4. retained stress path, alignments, substitutions, inversions, endings, and
   extra/omitted syllables; and
5. all 40 fixed candidates, warnings, and provenance.

Fit is a configured 0–1 alignment similarity, not a probability. Confidence is
a rule-based reading aid, not a calibrated probability. A word without usable
pronunciation evidence makes its line unscored; it does not receive a low,
zero, or neutral fit.

Use language such as “the nearest configured candidate was iambic pentameter
under the selected alignment configuration.” Do not write “VerseVAD proved
the poem is in iambic pentameter” or treat a metrically preferred dictionary
alternative as the poet's performed pronunciation.

### Optional performance-aware reading

**Candidate meter only** remains the default. To explore possible realized
readings, choose **Performance-aware realization** or **Compare candidate and
performance-aware readings**, then declare a broad interpretation profile and
Summary, Standard, or Detailed output.

Read the added section in this order:

1. rhythmic organization, primary/secondary candidate, coverage, and
   rule-based confidence;
2. declared profile and stanza recurrence;
3. raw lexical stress beside the candidate template and realized notation;
4. proposed promotion, demotion, caesura, ending, and substitution evidence;
5. retained alternate readings and separate score components; and
6. line-by-line rhythmic trajectory.

Notation uses `x` for weak, `/` for strong, `^` for proposed promotion, `v`
for proposed demotion, `2` for secondary-stress flexibility, `||` for a
punctuation-supported caesura, and `|` for a candidate foot boundary.

The profile is selected by you; VerseVAD does not infer a period or movement.
The realized reading is not one mandatory performance. Leave visibly marked
contraction recognition off unless the preserved spelling and your method
justify it. No unmarked syllable is silently removed. A recurring alternating
sequence may be reported generically, but no named stanza form is assigned.

The same settings are available per Project/Corpus batch. Corpus summaries
show compatible work-level prevalence and do not declare one corpus-wide
meter.

## Rhyme & Sound

In **Single Poem**, select **Rhyme & phonological patterns** and analyze. Stage 5
runs automatically, so no affective lexicon is required.

Open **Rhyme & Sound** to read the exact whole-poem and stanza schemes beside
ending coverage. Letters identify robust perfect/identical groups, `x` an
analyzable ungrouped ending, and `?` an unresolved ending. Then inspect the
separately labeled perfect, identical, masculine, feminine, multisyllabic,
graded slant, eye, internal-rhyme, refrain, alliteration, assonance, and
consonance evidence.

The slant score is a configured phone-and-stress similarity heuristic, not a
probability. Slant and eye rhyme never silently create exact scheme groups.
Materially different or absent dictionary endings remain unresolved unless a
documented Stage 5 scholar override applies.

Use language such as “the dictionary-based ending evidence produced an ABAB
exact-rhyme scheme among four analyzable endings.” Do not write that VerseVAD
proved how the poem must be pronounced, performed, heard, or intended.

## Lexical Style

In **Single Poem**, select **Lexical diversity, word length & structural word
counts** and analyze. The option is off by default and requires no external
dataset.

Open **Lexical Style** to read:

1. lexical-token and normalized observed surface-type counts;
2. MATTR with its configured overlapping-window size;
3. HD-D with its configured without-replacement sample size;
4. bidirectional MTLD with its configured type-token-ratio threshold;
5. alphabetic-character word-length statistics and distribution;
6. lexical-token word count for every preserved physical line, including
   blank separator rows with zero; and
7. lexical-token word count and nonblank line count for every stanza.

The module uses the shared preprocessing token unit. Punctuation and numeric
tokens are excluded, but a contraction or hyphenated expression may follow the
shared model-token policy rather than an editor's orthographic convention.
Inspect the token audit when that distinction matters.

MATTR and HD-D remain missing when the poem is shorter than the configured
window or sample. MTLD can also remain missing when no finite bidirectional
factorization exists. Do not compare poems using different parameters or
token policies. Plain TTR is shown only as a length-sensitive descriptive
value.

Use language such as “using a 50-token MATTR window, the poem's normalized
observed surface forms produced MATTR = [value].” Do not describe lexical
diversity or word length as proof of literary quality, intelligence,
vocabulary knowledge, education, reader comprehension, or authorial intention.

## Diagnostics and troubleshooting

The global **Settings** popover controls reuse of unchanged analyses and
lightweight timings. **Evidence & Diagnostics** shows each selected operation,
cache hit/miss reason, wall time, and bounded cache counts. Clearing a cache or
releasing a loaded resource cannot delete a project, source file, or saved
result; the next relevant action simply recomputes or reloads it.

The export section waits for **Prepare downloads**. This avoids rebuilding a
large ZIP during unrelated interface reruns. An unchanged prepared export is
reused safely, and the active section remains **Export & Help** while the
downloads are prepared.

Under **Installation Check**, click **Run self-test** in the app sidebar at any
time. A fully provisioned installation shows `12/12 checks passed`. You can
also double-click `diagnose_windows.bat` on Windows or
`diagnose_macos.command` on macOS.

If startup fails:

1. close any earlier VerseVAD launcher window;
2. run the Windows or macOS diagnostic launcher and note any `FAIL` line;
3. rerun the setup helper for the current operating system if the local
   environment is missing;
4. copy or photograph the complete plain-language error for support.

Invalid encoding, non-text files, blank text, missing titles, and missing
lexicon selections produce a plain-language message without analyzing anything.

## Core terms and limitations

**Token** means one occurrence. **Type** means a unique matched lexical entry.
**Surface form** is the form in context. **Lemma** is a model-proposed base form
and can be wrong for poetic, historical, or unusual language. **Exact match**
links the normalized surface directly to a source entry and takes priority over
lemma fallback.

VerseVAD describes lexical evidence. It does not resolve negation, irony,
metaphor, voice, authorial intention, historical sense, or reader response.
Those remain matters for contextual inspection and scholarly interpretation.
The part-of-speech profile is model-generated grammatical evidence and can
also require correction through close inspection.

## Older validation demonstrations

`test_phase1.bat` and `test_phase2.bat` remain available on Windows as invented,
hand-calculated engine demonstrations. On macOS, the same demonstrations can be
run from Terminal with `./.tools/uv/uv run --frozen --offline
versevad-phase1-demo` or `versevad-phase2-demo`. Their generated
`phase1_demo_output` and `phase2_demo_output` folders can be deleted safely and
recreated by rerunning the corresponding demonstration.

## PoetryID

PoetryID is optional and requires at least one selected VAD lexicon. Enable
**PoetryID Lexical-Affective Profile**, select the VAD sources, token/type
weightings, and all-matched or stopword-excluded views, then analyze. Both token
scopes are selected by default. In the result, use the separate **PoetryID VAD
source**, **PoetryID token scope**, and **PoetryID weighting** selectors. **All
matched tokens (including stopwords)** includes only tokens that matched the
chosen VAD lexicon; unmatched vocabulary remains missing. **Stopwords
excluded** applies the pinned VerseVAD stopword policy. Every combination
remains separate; no consensus score is calculated.

Read the PoetryID tab in this order:

1. continuous normalized valence, arousal, and dominance;
2. low/moderate/high levels and the categorical candidate profile;
3. the separately retained nearest Euclidean centroid;
4. confidence, boundary proximity, matched counts, and coverage;
5. the VAD threshold scales and three dominance maps;
6. nearest alternatives and all 27 distances;
7. optional secondary concreteness, SUBTLEX-US Zipf frequency, and AoA
   character;
8. methodology, cautions, CSV data, and a narrative Word report.

Profile names are interpretive labels for normative lexical neighborhoods.
They do not identify the emotion of the poem, speaker, author, or reader.
Relative affinities and confidence labels are not probabilities.

The default fixed boundaries are 0.40 and 0.60. Custom fixed boundaries are
available under advanced methodology. Corpus-relative thresholds are not
implemented.

In **Project / Corpus**, add PoetryID to a batch after selecting at least one
VAD lexicon. The module view shows compatible profile distributions, 3x3 map
counts, continuous work positions, a per-poem comparison of categorical and
nearest-centroid results, and token/type sensitivity. The comparison table
reports both profile names, whether they agree, the nearest and categorical
centroid distances, rule-based confidence, and the poem's continuous VAD
coordinates. Filter to one source/view/weighting combination before
interpreting a distribution or comparison.

PoetryID downloads are six CSV files and one narrative Word report.

## Inherited Form Analysis

Enable **Inherited Form Analysis (comprehensive profile registry)** under the
default-collapsed **Additional Optional Models** panel. VerseVAD automatically
reuses its pronunciation, meter, and graded rhyme results, even when those
dependency checkboxes were not separately selected. The module does not
rescan the poem.

Registry version 2.0 contains 169 source-documented profiles: 58 automatic,
27 partial, and 84 manual. Manual profiles include forms whose defining
context, visual layout, language-specific practice, theme, or compositional
procedure VerseVAD cannot responsibly infer. They remain selectable and keep
their defining requirement visible and unscored, but they cannot become
automatic suggestions.

Read the result in this order:

1. **Potential match** names the highest candidate that met both the
   consistency and evidence minimums. It is not a definitive form identity.
2. **Classification** ranges from Strict and Strongly conforming through
   Modified, Form-derived, Suggestive resemblance, and No inherited-form
   match.
3. **Consistency** is agreement with the available weighted rules.
4. **Evidence coverage** is the share of possible weighted profile evidence
   that VerseVAD could evaluate. Missing pronunciation, meter, or rhyme stays
   missing.
5. **Confidence** uses consistency, coverage, required-feature contradictions,
   and separation from the runner-up. It is not a probability.
6. **Nearest alternative** keeps related or overlapping forms visible.

Hover over the classification metric or read the blue information box to see
the candidate's traditional definition and the poem's main agreements and
departures. When nothing qualifies, **Ten Nearest Profiles** shows only the
ten closest candidates. Use **All Inherited Forms** to select any of the 169
profiles—even one that is obviously not a match—and inspect expected/detected
values, roles, weights, scores, coverage, source modules, assessment mode,
sources, and limitations.

The haiku entry is deliberately named **English-Language 5–7–5 Haiku
Profile**. It tests three lines and 5/7/5 syllables; it does not equate haiku
with that classroom rule or claim to detect Japanese *on*, kigo, kireji,
juxtaposition, or aesthetic identity. The ghazal profile does not guess
couplet semantic autonomy or maqta; sonnet profiles do not guess a semantic
volta.

In **Project / Corpus**, add Inherited Form Analysis to the batch. Open
**Additional Module Results**, select `inherited_form`, and use the per-poem
table to compare potential match, classification, consistency, coverage,
confidence, nearest alternative, and margin. Results remain work-level; no
single form is assigned to the collection.

Downloads contain the complete registry, not only the ten candidates displayed
in a no-match view:

- `inherited_form_summary.csv`;
- `inherited_form_candidates.csv`;
- `inherited_form_features.csv`;
- `inherited_form_profiles.csv`;
- `inherited_form_methodology.csv`;
- `inherited_form_manifest.csv`; and
- `inherited_form_report.docx`.

No inherited-form JSON export is produced.
