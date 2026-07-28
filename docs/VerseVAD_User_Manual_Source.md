# VerseVAD User Manual

## Local, auditable lexical-evidence analysis for literary texts

**Software version:** {{VERSION}}  
**Manual updated:** {{DATE}}  
**Intended reader:** A first-time user who needs no programming, linguistics, or statistics background

> IMPORTANT: VerseVAD describes **lexical evidence**, offline rule-based polarity, prose-oriented readability formulas, optional dictionary-based pronunciation evidence, transparent candidate-meter comparisons, phonological patterns, lexical-style counts, PoetryID candidate lexical-affective neighborhoods, and inherited-form resemblance. VADER polarity, readability, concreteness, corpus-relative frequency, retrospective Age of Acquisition, pronunciation/lexical stress, meter fit, rhyme/sound evidence, lexical diversity, word length, structural word counts, PoetryID, and inherited-form consistency remain separately documented constructs. VerseVAD does not determine the emotion of a poem, speaker, author, or reader, diagnose cognition, establish definitive meter, performed rhythm, or genre identity, or replace contextual close reading.

[[PAGEBREAK]]

# Contents at a glance

1. Purpose, privacy, and scholarly scope
2. Installation, startup, and shutdown
3. Five-minute first analysis
4. The installed lexicons
5. How text becomes auditable matches
6. Dual VAD reporting and stopwords
7. How to interpret every result
8. Single Poem and Other Text workspaces
9. Project / Corpus workspace
10. Lexicon Explorer
11. Downloads, CSV files, JSON, and Excel
12. Mathematical formulas
13. Glossary
14. Troubleshooting and limitations
15. Reproducibility and updating this manual

> QUICK ORIENTATION: Read **Overview** first, then use the seven report families: **Affective Evidence**, **Lexical Character**, **Sound & Form**, **Structure**, **Evidence & Diagnostics**, and **Export & Help**. Each analytical module is a large collapsible section with a visible status. Download the readable summary for ordinary review and the full audit bundle when you need reproducibility. If a term is unfamiliar, use the separate `VerseVAD_Values_and_Terminology_Guide.docx`, which includes plain-language definitions, formulas, worked examples, and reporting templates.

The report-family and Project / Corpus section controls remember the selected
section during Streamlit refreshes. Changing a lexicon, token/type weighting,
all-matched/stopword-excluded view, or another display control no longer sends
the interface back to the first section. **Prepare downloads** keeps **Export &
Help** selected. Content added during a refresh may shift the precise position
slightly within a long section, but the active section remains stable.

The one-text **Report section** control is a dropdown. All large vertical
sections begin collapsed and can be opened independently, so multiple sections
may remain expanded. Each expanded report section ends with a compact
upward-arrow control in its bottom-right corner, so the section can be collapsed
without returning to its heading. The Additional Optional Models and Analysis
Configuration panels use the same icon control; hovering or focusing it
identifies the section it will collapse. Streamlit's arrow at the top edge of
the left sidebar hides or restores the sidebar; the main workspace automatically
uses the freed width or resizes when the sidebar returns. This behavior is
shared by supported Windows and macOS browsers.

All interactive results tables keep their header row visible during vertical
scrolling and pin the leftmost data column during horizontal scrolling. The
pinned column is the table's first identifying field, such as Work, Lexicon,
Line, Dimension, or Surface. This presentation aid does not change sorting,
formatting, calculations, or exported data.

# 1. Purpose, privacy, and scholarly scope

## What VerseVAD does

VerseVAD compares words and accepted phrases in a literary text with locally installed affective lexicons. Depending on the selected source, it can report:

- normative valence, arousal, and dominance ratings;
- binary emotion and sentiment associations;
- numeric word-emotion intensity ratings;
- offline VADER positive/neutral/negative polarity proportions, compound score,
  and sentence-level evidence with visible domain cautions;
- line-level valence, arousal, dominance, and optional normalized-concreteness
  trajectories for one explicitly selected VAD source;
- resource-free Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog,
  Automated Readability Index, Coleman-Liau, and sentence-qualified SMOG
  evidence with auditable syllable methods;
- token- and type-weighted summaries;
- part-of-speech counts and relative shares over all eligible lexical tokens;
- all-matched and stopword-excluded VAD views;
- coverage and unmatched vocabulary;
- cumulative, length-sensitive normative lexical totals;
- the largest midpoint-centered lexical contributors;
- work-level and collection-level corpus comparisons;
- named, versioned review scenarios for flags, exclusions, and approved mappings;
- source provenance and uncertainty fields in Lexicon Explorer;
- optional normative lexical concreteness statistics, coverage, structural
  summaries, term rankings, and token audit from a local research workbook; and
- optional SUBTLEX-US Zipf frequency statistics, coverage, rarity bands,
  structural summaries, term rankings, and token audit; and
- optional Kuperman retrospective Age of Acquisition statistics, coverage,
  source-response evidence, configurable orientation bands, structural
  summaries, descriptive cross-module relationships, term rankings, and token
  audit; and
- optional exact observed-form CMUdict pronunciation candidates, resolved
  syllables, complete-line totals, lexical-stress sequences, coverage,
  ambiguity evidence, poem-specific scholar overrides, and token/type/line
  audits; and
- optional candidate-meter alignment against five recurring stress patterns
  from monometer through octameter, line fit, deviations, alternatives,
  coverage, and a complete alignment audit, plus an optional separate
  performance-aware realization layer with contextual prominence, phrasing,
  substitutions, stanza recurrence, alternate readings, and scholar
  revisions; and
- optional exact end-rhyme schemes, perfect/identical and
  masculine/feminine/multisyllabic evidence, graded slant and eye rhyme,
  internal rhyme, refrains, phonemic alliteration, assonance, consonance,
  line-ending coverage, and complete line/pair audit evidence; and
- optional surface-form lexical diversity, alphabetic word length, and
  physical-line and stanza word-count evidence with complete token and
  structural audits.

## What VerseVAD does not do

VerseVAD does not infer an author's intention, diagnose a speaker, identify a poem's true emotion, or measure an individual reader's response. It does not resolve irony, metaphor, polysemy, historical sense, narrative distance, quotation, or negation compositionally. It provides inspectable lexical evidence for a scholar to interpret in context.

## Privacy and offline use

Ordinary use runs locally on this computer at `http://127.0.0.1:8501`. VerseVAD does not send literary texts, lexicons, projects, or results to an external generative-AI or hosted text-analysis service. Once the local environment is installed, ordinary analysis does not require a third-party subscription.

The supplied lexicons remain under `source_lexicons/` and must not be renamed, edited, merged, or redistributed. VerseVAD reads them in place, records SHA-256 checksums, and stores derived project data separately.

Optional research resources under `resources/` are also local and excluded from source control. The Stage 2 concreteness workbook and paper, Stage 3 SUBTLEX-US workbook, Stage 4 Kuperman Age of Acquisition workbook and paper, and Stage 5 pinned CMUdict files must retain their exact paths and checksums. VerseVAD reads analysis sources in place and does not copy any complete research source into an export.

## Software and research-source licensing

VerseVAD code and documentation are free and open-source software under
`GPL-3.0-only`. The GPL permits educational, research, personal, and commercial
use of VerseVAD, subject to its source-distribution and copyleft conditions.
VerseVAD is supplied without warranty; the full terms are in `LICENSE`.

The GPL does not relicense the lexicons, workbooks, papers, language model, or
literary texts used with VerseVAD. A public VerseVAD checkout contains no
research datasets. Users must obtain each source from its creator or publisher,
follow its current terms, and must not assume that a permission applying to the
software also applies to the data.

## Installing separately downloaded research resources

The tracked `docs/resource-installation.md` guide is the source of truth for
official download pages, exact destinations, supported SHA-256 values, and
source-specific cautions. The principal official pages are:

- Warriner VAD, concreteness, and Kuperman AoA: the relevant *Behavior
  Research Methods* article and supplementary-material pages;
- NRC VAD: `https://saifmohammad.com/WebPages/nrc-vad.html`;
- NRC Emotion:
  `https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm`;
- NRC Affect Intensity:
  `https://www.saifmohammad.com/WebPages/AffectIntensity.htm`;
- SUBTLEX-US:
  `https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus`;
  and
- CMUdict: `https://github.com/cmusphinx/cmudict`.

VerseVAD never downloads these sources automatically. At startup it checks
each exact path, file size, and supported checksum. A warning lists missing,
malformed, or unsupported files with their expected destinations. Unavailable
affective sources are removed from selectors; optional modules are disabled
only when their own dependency is unavailable. Other installed analyses,
including resource-free lexical style, remain usable.

# 2. Installation, startup, and shutdown

## First-time setup

1. Open the `VerseVAD` folder.
2. On Windows, double-click `setup_windows.bat`. On macOS, open Terminal in
   the folder and run `bash setup_macos.command`.
3. Allow setup to finish. The first setup can use the internet to obtain the
   pinned local runtime and packages.
4. Install the desired research sources using
   `docs/resource-installation.md`. This is intentionally a separate manual
   step.
5. Start VerseVAD, resolve any resource warning by checking the exact
   destination and checksum, and use **Run self-test**.
6. Confirm that the applicable diagnostic lines end in `PASS`.
7. Close the setup window when it finishes.

Setup is project-local. It does not require administrator access or a system-wide Python installation.
The macOS setup supports Apple silicon and Intel Macs running macOS 13 Ventura
or newer without requiring Homebrew. If the `VerseVAD` folder is moved or
renamed, rerun the setup helper for the current operating system.
Setup detects stale absolute virtual-environment paths and rebuilds only the
disposable `.venv`; research sources and project data are not removed.

On macOS, setup also makes the three `.command` helpers executable. If Terminal
reports `Permission denied`, run `chmod u+x setup_macos.command
start_versevad.command diagnose_macos.command` from the VerseVAD folder. See
`docs/macos-installation.md` for exact Finder/Terminal steps, Gatekeeper
guidance, and browser troubleshooting.

## Updating an existing installation

A VerseVAD folder cloned with Git can be updated in place. Close VerseVAD,
inspect tracked local changes, and use GitHub Desktop **Fetch origin** followed
by **Pull origin**, or run `git fetch origin` and `git pull --ff-only origin
main` from the repository. Then rerun `setup_windows.bat` or `bash
setup_macos.command`. The setup helper synchronizes only the locked dependency
changes that are needed. It preserves ignored lexicons, resources, projects,
exports, backups, runtime downloads, caches, and a compatible environment.

Do not delete the working folder or use Git clean or hard reset as an update
method. A folder obtained with GitHub's **Download ZIP** has no Git history and
cannot pull. Use `docs/updating.md` for exact Windows and macOS commands, a
clone check, and the one-time safe migration from a ZIP folder to a real clone.

## Start VerseVAD

1. On Windows, double-click `start_versevad.bat`. On macOS, double-click
   `start_versevad.command`.
2. Keep the visible launcher window open while using VerseVAD.
3. Your default browser should open `http://127.0.0.1:8501`. Current Safari
   and Chrome are supported; Streamlit's browser policy covers the two most
   recent versions of each.
4. If the browser does not open automatically, type that address into a browser on the same computer.

The shared application header contains:

- **Single Poem**
- **Project / Corpus**
- **Other Text**
- **Lexicon Explorer**
- the current VerseVAD version;
- **Light**, **Dark**, and **System** appearance;
- settings and help access.

System appearance follows the browser or operating-system preference. The
selection is stored as an application-level local preference, not in a
project or analysis configuration. Appearance does not change calculations,
result IDs, project data, or exports. Publication-oriented charts remain
light.

## Stop VerseVAD

Close the browser tab, then close the visible launcher window. One-poem results exist only in the current application session unless downloaded. Corpus projects persist in the local SQLite database.

# 3. Five-minute first analysis

1. Open **Single Poem**.
2. Enter a title or working label.
3. Paste a short poem, or upload a UTF-8 `.txt` file.
4. Keep the selected lexicons and default methodology for the first run.
5. Optionally enable **Normative lexical concreteness**, **Frequency & rarity profile (SUBTLEX-US Zipf)**, **Age of Acquisition profile (Kuperman et al. ratings)**, **Pronunciation & prosody foundation (CMUdict)**, and/or **Meter & rhythmic regularity** under **Additional Optional Models**.
6. Keep both affective reporting views enabled.
7. Click **Analyze Poem**.
8. In **Overview**, inspect coverage and warnings.
9. In **Affective Evidence**, compare VAD sources/views, emotion evidence, and PoetryID when selected.
10. In **Lexical Character**, inspect Concreteness, Frequency & Rarity, and Age of Acquisition when selected.
11. In **Sound & Form**, inspect Pronunciation, Meter & Rhythm, Rhyme & Sound, and Inherited Form Analysis when selected.
12. In **Structure**, inspect the language profile and lexical/structural measures.
13. In **Evidence & Diagnostics**, inspect exactly which surface forms, lemmas, or phrases matched.
14. In **Export & Help**, save the readable summary or full audit bundle.

> SAFE PRACTICE: A high or low mean is not self-interpreting. Always read it with the lexicon name, analysis view, weighting, matched count, coverage, and evidence table.

# 4. The installed lexicons

| VerseVAD source | What it supplies | Original scale | Derived comparison |
|---|---|---|---|
| Warriner VAD 2013 | Valence, arousal, dominance; standard deviations and rater counts | 1 to 9 | `(x - 1) / 8` |
| NRC VAD v1 | Valence, arousal, dominance; words and 132 activated whitespace entries | 0 to 1 | `x` |
| NRC VAD v2.1 | Valence, arousal, dominance; unigrams and multiword expressions | -1 to 1 | `(x + 1) / 2` |
| NRC Emotion v0.92 | Eight emotion associations plus positive and negative sentiment | Binary 0 or 1 | Not normalized into VAD |
| NRC Emotion Intensity v1 | Numeric intensity for supplied word-emotion pairs | 0 to 1 | Retained on its own scale |

## Valence, arousal, and dominance

**Valence** is the normative pleasantness or unpleasantness associated with a lexical item. Higher normalized values indicate more pleasant norms; lower values indicate more unpleasant norms.

**Arousal** is the normative activation or intensity associated with a lexical item. Higher normalized values indicate more activated or energetic norms; lower values indicate calmer or less activated norms.

**Dominance** is the normative sense of control, power, or agency associated with a lexical item. Higher normalized values indicate greater control or power in the source ratings; lower values indicate less.

These are ratings gathered from participants for lexical items. They are not direct measurements of the present poem, context, or reader.

## Why original and normalized values both matter

Original values preserve what the source publishes. Derived normalized values align the documented minimum, midpoint, and maximum of each VAD scale to 0, 0.5, and 1. This makes visual comparison possible, but it does not make different lexicons interchangeable. Their vocabularies, participants, procedures, dates, and versions still differ. VerseVAD does not create a default consensus score.

NRC VAD v1 and NRC VAD v2.1 are versions of the same lexicon family, not independent replications.

## Phrase coverage

NRC VAD v2.1 explicitly contains multiword expressions. VerseVAD also activates the 102 whitespace-containing rows in the local Warriner source and the 132 whitespace-containing rows in NRC VAD v1 as exact, auditable phrase candidates at the user's request. This is a declared processing choice and does not claim that Warriner or NRC VAD v1 supplied a separate phrase-specific validation study.

## Optional concreteness resource

The one-poem workspace can read the user-supplied Brysbaert, Warriner, and Kuperman (2014) supplementary workbook directly from `resources/`. Its 39,954 rows contain 37,058 single words and 2,896 two-word expressions rated on an original 1-5 concreteness scale. The source paper describes the endpoints as very abstract or language-based and very concrete or experience-based.

Keep these exact local files:

- `resources/brysbaert_warriner_kuperman_concreteness_DATA.xlsx`
- `resources/brysbaert_warriner_kuperman_concreteness_PAPER.pdf`

The workbook's `SUBTLEX` field is retained as source-row provenance. It is not VerseVAD's lexical-frequency module.

## Optional SUBTLEX-US frequency resource

The one-poem workspace can separately read the official SUBTLEX-US workbook at:

`resources/subtlex-us/SUBTLEX-US frequency list with PoS and Zipf information.xlsx`

Its 74,286 word-form rows include corpus frequency, contextual diversity, source POS provenance, and Zipf values. The expected workbook SHA-256 is `3a8cb93a4e28988c2ce722a63f6b8d394acdc42ebe2ab6e1f0e484ee0d4167a7`.

Zipf is a logarithmic, corpus-relative scale: approximately one point represents a tenfold frequency difference. The source is an American film and television subtitle corpus, not poetry. VerseVAD uses no `wordfreq` fallback, and unmatched forms remain missing.

## Optional Kuperman Age of Acquisition resource

The one-poem workspace can separately read the official Springer erratum
supplement at:

`resources/kuperman_2013_erratum_ESM1_official.xlsx`

Its `Sheet1` contains 31,124 unique nonblank word rows: 31,105 with numeric
mean ages and 19 whose numeric mean is unavailable. The expected workbook
SHA-256 is
`3f69a1332359de1cd4a7ccd3c4c3c2e39b388eeb171d6e90544709c3dc1a8a6e`.
The local publisher paper is
`resources/kuperman_stadthagen_gonzalez_brysbaert_2012_aoa_PAPER.pdf`, with
expected SHA-256
`fa72b2dd7980707de710b4dcb346d0368d5e2c21d657824a935ea4b8b8b80e1a`.

The numeric means are adult retrospective estimates of acquisition age in
years. VerseVAD retains source mean/SD, total and numeric response counts,
source frequency when available, and the source `Dunno` field. It separately
labels `OccurNum / OccurTotal` as the numeric-response proportion.

The paper describes target selection using base forms most frequently used as
nouns, verbs, or adjectives. The official supplement nevertheless has ratings
for polyfunctional spellings such as `the`, `and`, `he`, `of`, and `to`.
Source sampling and the contextual grammatical role of a poem occurrence are
therefore separate. The optional contextual `NOUN`/`VERB`/`ADJ`/`ADV` scope
remains available and off by default.

## Optional CMU Pronouncing Dictionary resource

The Stage 5 one-poem module reads official CMUdict files pinned at repository
commit `74790861f652b15e4ac49015a90074ad62a27690`:

- `resources/pronunciation/cmudict.dict`;
- `resources/pronunciation/cmudict.phones`; and
- `resources/pronunciation/cmudict.symbols`.

The files contain North American dictionary pronunciations encoded in
ARPAbet. The adapter validates exact checksums, source counts, alternative
suffixes, phone/symbol inventories, vowel stress, duplicate variants, and
malformed rows without editing them. Every pronunciation alternative remains
auditable.

CMUdict acknowledges possible errors, omissions, and inconsistencies.
Dialect, historical pronunciation, context, poetic elision, and performance
may differ. The module is a pronunciation/syllable/lexical-stress foundation;
it does not classify meter, rhyme, or definitive performed scansion.

# 5. How text becomes auditable matches

## Preserved original and processing representation

VerseVAD preserves the supplied text exactly, including line and stanza breaks. Normalization happens in a separate processing representation. The original text is never silently rewritten.

## Shared poem document

For one-poem analysis, VerseVAD creates one immutable shared document and reuses its exact token sequence for every selected lexicon. It contains:

- the exact original text;
- stanza and physical-line records, including blank separators and line endings;
- separate model sentence records, including line/stanza-crossing flags;
- surface, normalized, lemma, POS, morphology, and character-offset token fields;
- dependency records and optional named-entity records;
- exact spans for hyphenated expressions, contractions, and apostrophe forms;
- content/function/other/non-lexical classifications; and
- processing configuration, provenance, coverage, and warnings.

Poetic lines/stanzas and model sentences are distinct layers. VerseVAD retains both when they disagree. Lemma, POS, morphology, sentence, dependency, and optional named-entity values are statistical-model output, not corrected literary facts.

Named-entity recognition is disabled by default. The installed small English model has no usable vector vocabulary, so model out-of-vocabulary counts remain missing instead of becoming zero or classifying every lexical token as OOV. This model status is separate from affective-lexicon, concreteness, and SUBTLEX-US coverage.

## Main matching order

1. Preserve the original text and structural positions.
2. Create normalized processing forms.
3. Exclude punctuation from numeric summaries while retaining it in the audit.
4. Search for the longest accepted exact phrase without crossing a line or punctuation boundary.
5. Attempt an exact normalized surface-form match.
6. Apply conservative apostrophe and possessive normalization.
7. Attempt POS-sensitive lemma fallback only when exact matching fails.
8. Leave unresolved or unmatched items missing.

An exact surface match is never silently replaced by a lemma match. Lemma matching is explicitly labeled because model-proposed lemmas can be wrong for poetic, historical, or unusual language.

The optional concreteness module has its own recorded sequence over the same tokens: longest exact source-supplied two-word expression within one physical line, exact normalized surface, lemma, then a documented conservative apostrophe or possessive fallback. Model-tagged proper nouns are excluded by default. Unmatched and ineligible tokens retain missing ratings.

The optional frequency module likewise uses exact normalized observed word form before an enabled lemma fallback, followed only by documented conservative apostrophe or possessive fallbacks. This order preserves SUBTLEX-US word-form evidence. Model-tagged proper nouns are excluded by default, and unmatched or ineligible tokens retain missing Zipf values.

The optional Age of Acquisition module uses exact normalized observed word form
before an enabled lemma fallback, followed by documented conservative
apostrophe or possessive fallbacks. A source row whose mean is `NA` remains
visible as `source_entry_without_numeric_rating` but does not enter numeric
summaries. Model-tagged proper nouns are excluded by default. Unmatched,
ineligible, and source-unrated tokens retain missing ages rather than zero.

The optional pronunciation module uses the exact normalized observed form
only. It does not use the model lemma, strip possessive endings, repair
spelling, or predict a pronunciation. One CMUdict candidate resolves directly.
Several candidates resolve only when all agree on syllable count and the full
lexical-stress sequence; otherwise the token remains ambiguous. Unmatched,
ambiguous, and source-vowelless tokens retain missing pronunciation,
syllable, and stress fields.

## Phrase-policy choices

| Policy | Behavior | Interpretive consequence |
|---|---|---|
| Prefer the longest phrase | An accepted phrase contributes one observation; covered component candidates are suppressed but audited | Recommended default |
| Unigrams only | Phrase entries are ignored; individual words can match | Useful sensitivity view |
| Phrase and components | Phrase and independently matched components both contribute | Exploratory and intentionally double-counts the span |

Accepted phrases never cross poetic line or punctuation boundaries. Shorter overlapping phrases and covered components remain visible in the audit.

## Match and audit statuses

An audit row can be included, unmatched, ineligible, suppressed as a phrase component, or suppressed by a longer overlapping phrase. Included matches record the source term, original and normalized values, matching method, token or span location, stopword status, and inclusion in both VAD views.

Unmatched tokens never receive 0, 0.5, a corpus mean, or another invented value.

# 6. Dual VAD reporting and stopwords

## The two result views

Every VAD analysis preserves:

- **All matched observations:** every included lexicon match under the declared phrase policy.
- **Stopwords excluded:** a secondary aggregate derived from the same matches after applying the recorded stopword policy.

The second view changes aggregate inclusion only. It does not retokenize the text, alter source ratings, or change exact-versus-lemma matching priority.

## Standard stopword policy

The standard policy is based on the pinned spaCy English `STOP_WORDS` list. VerseVAD records:

- stopword source and installed library version;
- VerseVAD list-policy version;
- standard and active word counts;
- SHA-256 hashes of the standard and active lists;
- protected words;
- custom additions and removals;
- surface or lemma evidence for each decision.

## Protected terms

VerseVAD protects meaning-changing negations, modals, comparatives, and intensifiers from default exclusion. The current protected set is:

`against, could, least, less, may, might, more, most, must, neither, never, no, nor, not, should, too, very, without`

A protected word remains in both result views unless the scholar deliberately changes the protected list.

## Custom stopwords

In **Stopword settings**, choose **Use custom stopword list** to:

- add one normalized word per line;
- remove a word from the standard list;
- import a UTF-8 plain-text list;
- export the exact active list;
- restore VerseVAD defaults.

A custom addition is a methodological choice, not a claim that the word is universally meaningless. For example, adding `raven` during a test proves that custom exclusion works; `raven` is not a VerseVAD default stopword.

Phrase entries remain intact. VerseVAD does not break a published phrase and remove one component merely because that component appears on the stopword list.

## Content-focused coverage

Ordinary coverage uses all eligible lexical tokens as its denominator. Content-focused coverage uses eligible non-stopword tokens under the active policy. VerseVAD also reports how many matched observations and types were excluded from the secondary view.

# 7. How to interpret every result

## Part-of-speech profile

The **Language Profile** is independent of affective-lexicon matching. It uses all eligible lexical token occurrences and reports the model-assigned universal part-of-speech category, token count, share of lexical tokens, unique normalized types, and example forms.

It presents two levels over the same tokens. **Broad Categories** provide the
main readable chart. **Detailed Model-Tag Breakdown** preserves each Universal
Dependencies tag and its own count/share for audit and methodological defense.
Each level separately sums to approximately 100 percent; do not add the two
levels together.

The displayed **Noun** category combines the model's `NOUN` and `PROPN` tags.
This avoids making a fragile common-versus-proper distinction in poetry while
retaining the original token-level tag in Evidence and audit data. The `ADP`
source tag is displayed with the beginner-facing label **Preposition**; it is
not an adverb.

The displayed **Verb** category combines `VERB` and `AUX`. A form such as
`was` may be tagged `AUX` in an auxiliary or copular construction, but it still
counts under Verb in the simplified profile. The original tag remains
available in Evidence and audit data.

`POS share = token occurrences assigned to one POS / all eligible lexical token occurrences`

Counts answer “how many occurrences received this label?” Shares answer “what proportion of the text's eligible lexical tokens received this label?” The shares sum to 100 percent apart from display rounding.

These labels are generated by the installed English linguistic model. Poetic syntax, fragments, archaisms, unusual capitalization, and deliberate ambiguity can produce uncertain assignments. Treat the profile as descriptive and inspect the token evidence when a grammatical distinction matters.

### VAD means by part of speech

When a one-text analysis includes at least one VAD lexicon, the Language
Profile adds a separate **VAD Means by Part of Speech** table. The grammatical
count/share profile above it remains independent of lexicon matching.

Every VAD source and the all-matched and stopword-excluded views remain
separate. Within each broad POS group, token-weighted means count every
included matched occurrence, while type-weighted means count each distinct
matched lexicon entry once within that source, view, and POS group. The
interface displays normalized 0-to-1 valence, arousal, and dominance means
alongside matched observations, distinct matched types, covered and eligible
token occurrences, coverage, and a sparse-evidence label. Original-scale means
and the normalization formula remain in `vad_by_part_of_speech.csv`.

Unmatched evidence remains missing rather than neutral. An accepted multiword
entry contributes one observation. A phrase whose lexical tokens span more
than one broad POS stays in a **Mixed-POS Phrase** row instead of being forced
into one grammatical category; because that is a span category rather than a
token population, its coverage denominator remains missing.

## Coverage

Coverage answers: “How much eligible vocabulary was represented by this source under this matching policy?” It is not an accuracy score.

Always inspect:

- eligible token count;
- matched token count;
- unmatched token count;
- lexical-token coverage;
- matched observation count;
- unique matched entry count;
- lemma reliance and warnings;
- content-focused coverage for the stopword-excluded view.

Different lexicons can have legitimately different coverage. A broad mean with poor coverage may describe only a narrow subset of the text.

## Token-weighted and type-weighted means

**Token-weighted mean:** every included occurrence contributes. Repetition matters.

**Type-weighted mean:** every distinct matched lexicon entry contributes once within the analyzed work. Repetition does not increase that entry's weight.

The difference between these views can reveal whether repeated vocabulary shifts the profile away from the vocabulary inventory considered once each.

## Population standard deviation

VerseVAD reports population standard deviation for the complete selected matched set. A larger value means the source ratings included in that result are more dispersed around their mean. It does not measure rating uncertainty in the lexicon and is not a confidence interval.

Warriner's source-provided rating standard deviations in Lexicon Explorer are different: they describe participant variation for one lexical entry.

## Stopword sensitivity

Stopword sensitivity is:

`stopwords-excluded statistic - all-matched statistic`

A positive value means the filtered view is higher; a negative value means it is lower. A small difference indicates that this particular statistic changes little under the policy. It is descriptive and is not a universal robustness threshold.

## Cumulative normative lexical load

Cumulative totals are intentionally sensitive to text length and repetition. VerseVAD reports:

- rating total;
- above-midpoint load;
- below-midpoint load;
- net midpoint load;
- absolute midpoint load.

These quantities summarize encountered matched lexical ratings. They are not direct measurements of cognitive load or affective impact on a reader.

## Top contributors

For each dimension and result view, VerseVAD ranks matched entries by signed midpoint-centered contribution:

`frequency * (normalized rating - 0.5)`

Positive values contribute above the normalized midpoint; negative values contribute below it. Frequency makes repetition visible. The table also retains the change in the token mean when all occurrences of that type are removed.

## Normative lexical concreteness

When enabled, **Concreteness Profile** reports token-weighted mean, median, population SD, inclusive quartiles, and interquartile range among source-rated lexical tokens on the original 1-5 scale. It also reports token coverage and unique normalized-surface-type coverage, physical-line and stanza summaries, model-assigned POS summaries, most concrete and most abstract represented source terms, and a complete token audit.

The default bands at or below 2.0 and at or above 4.0 are configurable VerseVAD orientation aids. They are not validated categories claimed by the paper. A matched two-word expression receives one match-group identity, while its source rating is assigned to both covered token positions for the declared token-weighted statistics. Repetition contributes repeatedly.

Read the mean with coverage, dispersion, terms, and structural evidence. The result describes normative lexical concreteness evidence among represented vocabulary. It does not measure imagery quality, readability, cognition, literary value, or whether the poem itself is abstract or concrete.

## Corpus-relative lexical frequency and rarity

When enabled, **Frequency & Rarity** reports the token-weighted median SUBTLEX-US Zipf value as its primary summary. It also reports the mean, population SD, inclusive quartiles, IQR, range, token and unique observed-form-type coverage, configurable bands, physical-line/stanza/POS summaries, lowest/highest terms, a rare-word tail, and a complete token audit.

The default scope considers all lexical tokens except model-tagged proper nouns. **Content words only** is an optional, non-default scope. It includes only exact model tags `NOUN`, `VERB`, `ADJ`, and `ADV`. It excludes determiners (`DET`), prepositions/adpositions (`ADP`), conjunctions (`CCONJ`, `SCONJ`), pronouns (`PRON`), auxiliaries (`AUX`), punctuation, and all other tags. This differs from the broad Language Profile, which groups `VERB` and `AUX` together under **Verb**.

The default rare-to-very-common bands are VerseVAD orientation aids, not diagnostic literary categories. Read the median with the distribution, coverage, scope, unmatched forms, structure, and audit. The result describes corpus-relative lexical frequency evidence from an American subtitle corpus. It does not measure difficulty, sophistication, accessibility, intelligence, literary quality, or reader response.

## Retrospective normative lexical Age of Acquisition

When enabled, **Age of Acquisition** reports token-weighted mean, median,
population SD, inclusive quartiles, IQR, range, token and unique normalized
observed-form-type coverage, configurable early/middle/later bands,
physical-line/stanza/POS summaries, source-response evidence,
earliest/latest represented terms, and a complete token audit.

The numeric values are source mean ages in years, based on adult retrospective
estimates of when respondents believed they had learned a word well enough to
understand it. The default early-at-or-below-5 and later-at-or-above-12 bands
are VerseVAD orientation aids, not categories validated by the paper.
Repetition contributes repeatedly.

The default scope considers all lexical tokens except model-tagged proper
nouns. **AoA content words only** is an optional, non-default contextual scope
using exact model tags `NOUN`, `VERB`, `ADJ`, and `ADV`; it excludes `AUX` and
function-word tags. This remains methodologically useful even though the source
paper describes content-word target selection, because the official supplement
contains rated polyfunctional spellings and a poem occurrence has its own
contextual role.

If Frequency or Concreteness is enabled in the same run, VerseVAD may report a
descriptive Spearman relationship using unique paired normalized surface
types. At least three paired types are required, multiword concreteness
assignments are excluded, and the coefficient does not establish causation,
difficulty, or a reader effect.

Read the mean and median with coverage, dispersion, response counts, source
SDs, structure, represented terms, and the audit. The result describes
retrospective normative lexical AoA evidence. It does not measure grade level,
difficulty, familiarity, comprehension, intelligence, literary value, or
reader response. Age-of-acquisition results are not diagnostic of cognitive
impairment or decline.

## Dictionary pronunciation, syllables, and lexical stress

When enabled, **Pronunciation & Prosody** reports exact observed-form CMUdict
candidates, resolved-token and observed-type coverage, syllables per resolved
word, complete-line syllable totals, word-grouped lexical-stress sequences,
primary/secondary stress counts, stress density, and the complete candidate
audit.

CMUdict stress digits mean:

| Digit | Meaning |
|---|---|
| `0` | Unstressed syllable |
| `1` | Primary lexical stress |
| `2` | Secondary lexical stress |

One dictionary candidate resolves directly. Multiple candidates resolve only
when every candidate agrees on both syllable count and the complete stress
sequence. Phone alternatives remain visible. A difference in syllables or
stress remains ambiguous; no candidate is silently selected.

A physical line receives a syllable total and stress sequence only when every
eligible lexical token resolves. An incomplete line remains missing rather
than displaying a deceptively low partial total.

Advanced settings accept poem-specific scholar overrides:

```text
permit = P ER0 M IH1 T | verb reading in this line
```

Phones must use uppercase symbols from the pinned local CMUdict inventory and
include stressed or unstressed vowels. A note is required. The override is
part of the configuration identity, applies only to the exact observed type in
the current analysis, remains distinct from every dictionary candidate, and is
reversible.

The displayed confidence label is a categorical description of source
resolution, not a probability. Report these results as dictionary-based North
American pronunciation, syllable, and lexical-stress evidence. Do not call
them definitive performed pronunciation, meter, rhyme, or scansion.

## Candidate meter and rhythmic regularity

When enabled, **Meter & Rhythm** automatically uses the retained Stage 5
pronunciation evidence. No affective lexicon is required. It compares five
recurring base patterns:

| Pattern | Stress pattern |
|---|---|
| Iambic | `01` |
| Trochaic | `10` |
| Anapestic | `001` |
| Dactylic | `100` |
| Amphibrachic | `010` |

Each pattern is checked at monometer, dimeter, trimeter, tetrameter,
pentameter, hexameter, heptameter, and octameter: 40 fixed line templates.
Spondees `11` and pyrrhics `00` are reported as local substitutions rather
than ordinary whole-line base candidates.

**Candidate meter only** is the validated default and preserves the Stage 6
result exactly. Two non-default choices add an independent performance-aware
realization or display candidate and performance-aware readings together.
The second layer does not rewrite the dictionary lexical stress or replace the
fixed candidate audit.

The line alignment can report substitutions, initial inversion, feminine
ending, catalexis, and extra or omitted syllables. Multiple retained CMUdict
stress alternatives are explored up to the configured line limit, but the
metrically preferred path is not promoted to a dictionary or performance
fact. A line with missing pronunciation evidence remains unscored.

Read:

- nearest fixed pattern-by-foot-count candidate;
- mean fit, matching-line proportion, line coverage, nearest alternative, and
  candidate margin;
- rule-based confidence and its explanation;
- physical-line stress paths, alignments, and deviations; and
- all 40 fixed candidates, warnings, configuration, and provenance.

When performance-aware analysis is selected, also read:

- raw lexical stress, metrical positions, contextual prominence, and visible
  promotion or demotion decisions syllable by syllable;
- local substitutions, stress clashes and lapses, punctuation-supported
  caesura evidence, selected pronunciation path, and alternate readings;
- candidate fit, contextual fit, syllable-count fit, phrase fit, line-ending
  fit, pronunciation plausibility, stanza/poem consistency, style
  compatibility, substitution penalty, and their visible weights;
- stanza summaries, recurrence, exceptions, rhythmic trajectory, generic
  alternating line-position sequences, and the poem-level rhythmic-
  organization label; and
- strong, moderate, tentative, ambiguous, or insufficient rule-based
  confidence with a plain-language explanation.

The scholar explicitly selects one broad versioned profile: General English
Verse, Traditional Accentual-Syllabic Verse, Romantic / Victorian Verse,
Modernist Verse, Contemporary Formal Verse, Free Verse / Cadential, or Custom
visible weights. VerseVAD never infers a period, movement, tradition, author,
or performance from the text. Summary, Standard, and Detailed control
presentation depth rather than analytical truth.

Recognizing visibly marked contractions such as `o'er` is off by default.
Unmarked syllables are never silently elided. Optional scholar scansion
revisions require a line number, fixed candidate, visible scansion, and note;
the automatic and revised readings remain separate and reversible.

Fit is a configured alignment similarity from 0 to 1, not a probability.
Confidence is a rule-based category, not a calibrated probability. Safe
wording is: “The nearest configured candidate was iambic pentameter under the
selected alignment configuration.” Do not write: “VerseVAD proved the poem is
in iambic pentameter,” “this is the correct scansion,” or “the poet performed
the line this way.”

## Rhyme and phonological patterns

When enabled, **Rhyme & Sound** automatically uses the retained Stage 5
pronunciation evidence. No affective lexicon is required. CMUdict supplies
phones and lexical stress; VerseVAD derives the rhyme and recurring-sound
classifications.

The whole-poem and stanza schemes use only robust perfect or identical rhyme
parts. Letters identify exact groups, `x` identifies an analyzable ungrouped
ending, and `?` identifies an unresolved ending. Slant and eye rhyme remain
separate and never create exact scheme groups.

Read:

- ending coverage, whole-poem scheme, and stanza schemes;
- perfect, identical, masculine, feminine, and multisyllabic pair evidence;
- the conservative graded slant score and its five components;
- spelling-based eye rhyme, exact internal rhyme, and repeated-line refrains;
- phonemic alliteration, assonance, consonance, densities, and dominant sound
  families; and
- line and pair evidence, warnings, configuration, and provenance.

The default slant score weights stressed vowel `0.35`, final consonants `0.25`,
rhyme-part edit similarity `0.25`, stress alignment `0.10`, and syllable
similarity `0.05`, with a default threshold of `0.68`. It is a configurable
heuristic, not a probability. Materially different dictionary alternatives
remain unresolved unless a documented Stage 5 scholar override applies.

Safe wording is: “The dictionary-based ending evidence produced an ABAB exact-
rhyme scheme among four analyzable endings.” Do not claim that VerseVAD proved
how the poem must be pronounced, performed, heard, or intended.

## Inherited-form candidate analysis

When enabled, **Inherited Form Analysis** compares the poem with registry
version 2.0's 169 source-documented profiles. Fifty-eight profiles are
automatically assessable, 27 are partially assessable, and 84 retain defining
requirements for manual scholarly confirmation. A manual profile remains
selectable and keeps its requirement visible and unscored, but it cannot
become an automatic suggestion.

It automatically reuses the shared poem document, pronunciation, meter, and
graded-rhyme results. It does not retokenize, reload CMUdict, or perform an
independent scansion. New form-specific detectors compare ordered refrains,
sestina end-word rotation and envoi, pantoum interstanza repetition, terza-rima
rhyme chains, limerick long/short lines, and ghazal radif/qafia evidence.

Read four distinctions carefully:

- **candidate** is the highest-ranked eligible profile;
- **consistency** is weighted agreement with available profile rules;
- **evidence coverage** is how much possible weighted evidence could be tested;
- **confidence** also considers required features and separation from the
  nearest alternative.

Confidence is low, moderate, or high and is not a probability. Missing
pronunciation, meter, rhyme, or syllable evidence has no feature score and
lowers coverage; it is never converted to mismatch.

Classifications are Strict, Strongly conforming, Modified, Form-derived,
Suggestive resemblance, and No inherited-form match. A candidate must pass
the consistency, total-coverage, required-feature-coverage, and contradiction
rules before VerseVAD calls it a potential match.

Hover over the classification metric or read the visible information box for
the traditional definition plus the poem's strongest agreements and
departures. The ranking table and candidate-evidence selector retain every
profile, expected and detected value, role, weight, feature score, coverage,
and source module. The sources and limitations expander links to the
definition sources.

The haiku profile is deliberately narrow. It tests an English-language 5–7–5
structural convention; it does not treat English syllables as Japanese *on* or
claim to detect kigo, kireji, juxtaposition, or haiku identity. Ghazal
semantic autonomy and optional maqta are not guessed. Sonnet volta evidence is
not guessed.

Safe wording is: “VerseVAD reports a modified Elizabethan-sonnet potential
match with 78% consistency across 86% of the profile's weighted evidence.”
Do not write: “VerseVAD proved that the poem is an Elizabethan sonnet.”

## Lexical diversity, word length, and structural word counts

The optional **Lexical Style** module uses the shared poetry-preserving
processing record and requires no external dataset. The broader planned
visible-structure and syntax/lineation modules were skipped at the scholar's
direction.

One counted word is one shared-preprocessing lexical token. Punctuation and
numeric tokens are excluded. This word unit may differ from an editor's
orthographic convention for a contraction or hyphenated expression, so the
token audit preserves exact surfaces, offsets, and inclusion reasons.

Lexical diversity uses normalized observed surface forms. Lemmas remain
separate audit evidence and never silently replace the forms present in the
poem. The module reports:

- descriptive lexical-token, normalized surface-type, and plain TTR values;
- MATTR across every overlapping configured token window;
- HD-D as the expected distinct-type proportion in a configured
  without-replacement sample;
- forward/reverse and mean MTLD at a configured TTR threshold;
- Unicode alphabetic-character word-length statistics and distribution;
- average words per nonblank physical line, average words per stanza, and
  average nonblank physical lines per stanza, each with its population
  standard deviation;
- one lexical-token count row for every preserved physical line, including
  blank separators with zero; and
- lexical-token and nonblank-line counts for every stanza.

Defaults are MATTR window 50, HD-D sample 42, and MTLD threshold 0.72. MATTR
and HD-D remain missing when the text is shorter than their configured
denominator. Undefined MTLD remains missing rather than becoming infinity or
zero.

Safe wording is: “Using a 50-token MATTR window, the normalized observed
surface forms produced MATTR = [value].” Do not treat lexical diversity or
word length as proof of literary quality, vocabulary knowledge, intelligence,
education, comprehension, or reader ability.

## Eight emotion associations

NRC Emotion values are binary, multi-label associations. VerseVAD reports the eight emotions—anger, anticipation, disgust, fear, joy, sadness, surprise, and trust—in their own section. An entry can be associated with several categories, so percentages do not need to total 100 percent. Read the labeled denominator.

“Fear-associated vocabulary” is appropriate wording. “The poem is afraid” is not.

## Positive and negative sentiment associations

Positive and negative are broad sentiment labels in NRC Emotion. VerseVAD analyzes them with the same documented occurrence-counting logic but reports them separately from the eight emotions. They are not endpoints of the VAD valence scale, and their rates need not sum to 100 percent.

## Emotion intensity

NRC Emotion Intensity supplies numeric values only for particular word-emotion pairs. VerseVAD keeps:

- prevalence of matched pairs;
- token-weighted mean intensity among supplied pairs;
- type-weighted mean intensity among supplied pairs.

An absent word-emotion pair is missing, not an intensity of zero.

# 8. Single Poem and Other Text Workspaces

## Add a poem

Paste text or upload one UTF-8 `.txt` file up to 5 MB. Enter a title or working
label. Optional author, date/year, and source/edition notes are available under
bibliographic metadata. The live word, physical-line, and text-block counts
are orientation only; the actual analysis uses the shared linguistic
tokenizer. **Clear text** requires confirmation. The optional workspace name
is blank by default, is not required, and labels the temporary session if
supplied; it does not create a persistent corpus project.

**Other Text** reuses this interface and the same analysis engines with
**Analyze Text** terminology. Pronunciation, meter, and rhyme remain available,
but meter and rhyme are visibly marked experimental for non-lineated prose.

## Choose evidence

Select one or more affective lexicons and/or enable the optional normative
lexical concreteness, SUBTLEX-US frequency, Kuperman Age of Acquisition,
CMUdict pronunciation/prosody-foundation, candidate-meter, rhyme/sound,
Lexical Style, PoetryID, or Inherited Form Analysis modules. The controls are grouped as **Core
Analysis**, **Lexical Character**, **Structural and Lexical Measures**,
**PoetryID**, and **Sound and Form**.

The optional **Essential**, **Literary**, **Sound and Form**, and **Complete**
presets change module selections only after **Apply preset** is clicked.
**Custom** retains the current manual selection. Presets never overwrite
advanced thresholds, filtering, phrase policy, stopwords, pronunciation
overrides, or other methodology.

VAD, categorical association, intensity, concreteness, corpus-relative
frequency, retrospective lexical AoA, dictionary pronunciation/lexical stress,
configured meter fit, rhyme/sound evidence, lexical diversity/word counts, and
PoetryID candidate profiles, and inherited-form resemblance answer different questions and remain separate.
PoetryID requires an enabled VAD source and reuses its completed result;
selecting meter or rhyme automatically runs its pronunciation dependency.
Inherited Form Analysis automatically reuses pronunciation, meter, and graded
rhyme evidence without independently rescanning the poem.

The same nine optional modules are also available in **Project / Corpus**.
Single Poem and Other Text results remain temporary unless downloaded; corpus runs persist the
same module result envelopes, configurations, coverage, warnings, provenance,
and audit artifacts against exact text versions.

Under **Analysis configuration and methodology**, choose:

- phrase policy;
- minimum matched observations for sparse-result warnings;
- whether to display all-matched results;
- whether to display stopword-excluded results;
- concreteness lower and upper orientation thresholds;
- whether concreteness excludes model-tagged proper nouns;
- whether source-supplied concreteness phrases are activated; and
- the concreteness low-coverage caution threshold;
- the four frequency orientation thresholds;
- whether frequency excludes model-tagged proper nouns;
- whether frequency permits lemma fallback;
- the frequency low-coverage caution threshold; and
- whether frequency uses the non-default **Content words only** scope;
- AoA early and later orientation thresholds;
- whether AoA excludes model-tagged proper nouns;
- whether AoA permits lemma fallback;
- the AoA low-coverage caution threshold; and
- whether AoA uses the non-default contextual **Content words only** scope;
- the MATTR overlapping-window size;
- the HD-D without-replacement sample size;
- the MTLD TTR threshold;
- the lexical-diversity short-text caution threshold;
- PoetryID VAD sources, token/type weightings, and analysis views;
- default or custom-fixed PoetryID VAD thresholds;
- PoetryID minimum VAD observations and token/type coverage; and
- optional secondary PoetryID concreteness, frequency, and AoA character;
- poem-specific `word = ARPAbet phones | note` pronunciation overrides;
- the pronunciation resolved-token coverage caution threshold;
- minimum complete pronunciation lines; and
- minimum resolved pronunciation tokens for sparse-result warnings;
- the meter line-fit threshold;
- the poem candidate-fit threshold;
- the candidate-margin threshold; and
- the maximum retained stress paths evaluated per line.

Under **Stopword settings**, inspect or change the secondary-view policy. The all-matched result is always preserved even when only one view is displayed.

## Overview report family

Read coverage before means. The Overview begins with a grouped at-a-glance
summary for affective evidence, lexical character, sound/form, and structure.
It then shows ordinary and content-focused coverage, matched counts, active
methodology, excluded stopword counts, interpretive framing, and warnings.

## Structure report family: Language Profile section

The **Shared Processing Record** first reports stanzas, physical lines, model sentences, total and lexical tokens, recipe/configuration IDs, model pipeline, dependency coverage, named-entity status, and processing cautions. It is the common local representation used by every selected lexicon.

The tab then reports part-of-speech counts and relative shares for all eligible lexical tokens, independently of lexicon coverage. It also shows unique normalized types and example forms. The denominator is displayed, and a caution explains that the labels are model-generated.

## Affective Evidence: VAD section

This tab contains:

- parallel normalized VAD charts;
- definitions of valence, arousal, and dominance;
- a separate **Dispersion of Matched Ratings** section immediately after those
  definitions, reporting population standard deviations among matched ratings;
- token- and type-weighted values for each analysis view;
- plain-language midpoint interpretations;
- stopword-sensitivity differences;
- cumulative normalized totals;
- top midpoint-centered contributors;
- original source scales and normalization formulas.

## Affective Evidence: Emotion Association, Intensity, and Sentiment section

The eight emotion associations, positive/negative NRC sentiment associations,
numeric emotion intensities, and VADER rule-based polarity appear as separate
constructs. VADER reports raw positive/neutral/negative proportions and a
rule-adjusted compound score. Its conventional threshold label is not a
declaration of the poem's emotion, and its social-media design can misread
poetic ambiguity, irony, persona, quotation, and historical usage. Do not
compare these values as though they were alternate VAD scales.

## Affective Evidence: Lexical Trajectory section

This default-collapsed section plots token-weighted mean normalized valence,
arousal, and dominance by preserved physical line for one selected VAD source.
When Concreteness was enabled, it adds a fourth line using `(rating - 1) / 4`
for overlay display while retaining the original 1-5 mean in the table and
export. Multiple VAD lexicons remain separate in the source dropdown. Changing
the source or token scope retains Affective Evidence. Missing line evidence
remains a gap rather than zero.

## Lexical Character: Concreteness section

This tab appears as the dedicated home for the optional result. It shows overall 1-5 source-scale statistics, token/type coverage, configured bands, warnings, line and stanza patterns, model-assigned POS groups, represented term extremes, a token audit, and source/configuration provenance. Exact surface, exact phrase, lemma, documented fallback, unmatched, and ineligible rows stay distinct.

The source workbook is read-only. If it is missing, changed, malformed, or unsupported, the checkbox is unavailable and VerseVAD presents a plain-language status instead of partially activating the module.

## Lexical Character: Frequency & Rarity section

This tab appears when the optional SUBTLEX-US module is enabled. It emphasizes the token-weighted median Zipf value and shows the mean, IQR, token/type coverage, configured bands, warnings, line and stanza patterns, model-assigned POS groups, lowest/highest represented terms, rare tail, complete token audit, and source/configuration provenance.

The page identifies whether the default all-lexical-token scope or the non-default `NOUN`/`VERB`/`ADJ`/`ADV` scope was used. Exact observed form, lemma, documented fallback, unmatched, and ineligible decisions stay distinct. The source workbook is read-only; a missing, changed, malformed, or unsupported source prevents activation.

## Lexical Character: Acquisition and Readability section

The always-available readability subsection reports Flesch Reading Ease,
Flesch-Kincaid Grade, Gunning Fog, Automated Readability Index, Coleman-Liau,
and SMOG with the exact word, sentence, syllable, character, and pronunciation-
coverage denominators. SMOG remains missing below 30 model-segmented sentences.
Contractions and hyphenated expressions count as one orthographic word.
Out-of-dictionary syllables use a clearly labeled heuristic until the user
approves or edits a session pronunciation override. These prose-oriented
formulas do not measure literary quality, reader ability, actual comprehension,
or a required grade.

The normative AoA subsection appears when the optional Kuperman module is enabled. It shows
source-age mean, median, dispersion, range, token/type coverage, configured
early/middle/later bands, source-response evidence, warnings, line and stanza
patterns, model-assigned POS groups, earliest/latest represented terms,
complete token audit, and source/configuration provenance. When corresponding
modules are enabled, it also shows descriptive type-level relationships with
Frequency and Concreteness.

The page identifies whether the default all-lexical-token scope or the
non-default contextual `NOUN`/`VERB`/`ADJ`/`ADV` scope was used. Exact observed
form, lemma, documented fallback, source-unrated, unmatched, and ineligible
decisions stay distinct. It always displays the required non-diagnostic
caution. The source workbook is read-only; a missing, changed, malformed, or
unsupported source prevents activation.

## Sound & Form: Pronunciation, Syllables, and Stress section

This tab appears when the optional CMUdict module is enabled. It shows
resolved-token coverage, syllables per resolved word, median syllables per
complete line, lexical stress density, complete-line coverage, physical-line
totals and stress sequences, words needing attention, every candidate
pronunciation, scholar overrides, warnings, and three-file source provenance.

Use **Words Needing Attention** to find out-of-dictionary and materially
ambiguous forms. For an ambiguous dictionary entry, select a retained CMUdict
candidate, use its **Hear** speaker control when useful, and choose **Apply
Approved Pronunciations and Reanalyze**. The selection is copied into the
editable session override field and dependent meter, rhyme/sound, and
inherited-form evidence is recomputed.

An out-of-dictionary word remains visibly **unmatched**. VerseVAD displays a
local eSpeak NG 1.52.0 US-English G2P candidate as **provisional—not
confirmed**. **Leave explicitly unresolved** is the default and keeps
pronunciation-dependent evidence missing. You may instead approve the
prediction or edit its ARPAbet directly, choose **Approve or edit for this
session**, and apply it. Only this explicit action creates a source-labeled
session override and recomputes dependent evidence. Removing the override and
analyzing again reverses it.

The speaker controls synthesize the exact displayed ARPAbet sequence locally
with bundled eSpeak NG. The robotic preview is an orientation aid, not a human
recording, dialect authority, or context-sensitive performance.

The North American dictionary warning remains visible. `0`, `1`, and `2` are
lexical-stress digits, not metrical beats. The Stage 5 tab does not report
candidate meter or rhyme.

## Sound & Form: Meter & Rhythm section

This tab appears when **Meter & rhythmic regularity** is enabled. It reports
the nearest fixed template, fit, matching lines, coverage, alternative,
candidate margin, rule-based confidence, rhythmic variation, physical-line
evidence, all 40 fixed candidates, warnings, and configuration provenance.

Do not mistake a metrically preferred stress path for a change to the Stage 5
pronunciation result.

In performance-aware or comparison mode, the same section adds the declared
profile and depth, poem/stanza organization, realized line readings, scoring
components, promotion/demotion and substitution evidence, caesurae,
clashes/lapses, alternate readings, recurrence/trajectory, and any separately
recorded scholar revisions. These are inspectable candidate realizations, not
performed scansion facts.

## Sound & Form: Rhyme & Recurring Sound section

This tab appears when **Rhyme & phonological patterns** is enabled. It reports
the whole-poem and stanza exact-rhyme schemes with ending coverage, then
separately shows perfect, identical, masculine, feminine, multisyllabic,
graded slant, eye, internal-rhyme, refrain, alliteration, assonance, and
consonance evidence.

Read the physical-line table before interpreting a scheme. It preserves the
end word, candidate phones and rhyme parts, resolution status, scheme labels,
repeated sounds, densities, and reason. The within-stanza pair table preserves
the rhyme types, five slant components, conservative and maximum scores,
eye-rhyme evidence, and caution label.

An unresolved line ending appears as `?` and reduces coverage. It receives no
neutral value or fabricated rhyme label. Add a Stage 5 override only when you
can document the intended pronunciation.

## Sound & Form: Inherited Form Analysis section

This section appears when **Inherited-form candidate analysis** is enabled. It
reuses the poem's preserved line and stanza structure plus the existing
pronunciation, meter, and rhyme results; it does not rescan those layers
independently. Registry version 2.0 ranks 169 source-documented automatic,
partial, and manual profiles.

Read **Potential match**, **Classification**, **Consistency**, **Evidence
coverage**, **Required evidence**, **Confidence**, and **Nearest alternative**
together. A suggestion appears only when the configured consistency and
coverage minimums are met and no available required feature severely
contradicts the profile. Confidence is rule-based and non-probabilistic.

Hover over the suggested match or its classification to read the form's
traditional definition, followed by poem-specific **Agreement** and
**Departures**. A no-match result displays only the ten nearest profiles.
**All Inherited Forms** keeps every registry entry selectable, including
obviously distant and manual-confirmation forms, and exposes each feature's
role, weight, score, coverage, observed evidence, and explanation. The sources
and limitations panel documents the profile definitions and boundary
decisions. If the evidence is insufficient or conflicting, VerseVAD reports
**No inherited-form match** rather than forcing the nearest profile into a
suggestion.

## Structure: Lexical and Structural Measures section

This tab appears when **Lexical diversity, word length & structural word
counts** is enabled. It reports token/type totals, MATTR, HD-D, MTLD,
alphabetic-character word-length statistics and distribution, and detailed
word counts for each physical line and stanza.

The **Structural Count Summary** shows:

- average words per nonblank physical line and its population standard
  deviation;
- average words per stanza and its population standard deviation; and
- average nonblank physical lines per stanza and its population standard
  deviation.

The standard deviations describe dispersion across all corresponding units in
the poem, so VerseVAD uses population rather than sample standard deviation.
Blank stanza-separator lines remain visible in the detailed line table but do
not enter the words-per-line or lines-per-stanza denominators.

Read the displayed parameters and token policy before comparing results.
Physical blank lines remain visible with word count zero. A missing MATTR or
HD-D normally means the text is shorter than the configured window or sample;
the module does not change the denominator silently.

The line and stanza tables also show local surface-type counts, descriptive
TTR, and mean/median alphabetic word length. These local TTR values are not
length-resistant comparison statistics.

## Affective Evidence: PoetryID section

This tab appears when **PoetryID lexical-affective profile** is enabled with
at least one selected VAD source. PoetryID consumes the completed normalized
VAD result; it does not tokenize, load a lexicon, match words, or calculate VAD
again.

Both token scopes are selected by default. Use the separate **PoetryID VAD
source**, **PoetryID token scope**, and **PoetryID weighting** selectors to read
one combination at a time. **All matched tokens (including stopwords)** includes
only tokens that matched the selected VAD lexicon; unmatched vocabulary stays
missing. **Stopwords excluded** applies the pinned VerseVAD stopword policy.
The tab presents:

- continuous normalized valence, arousal, and dominance before any label;
- the low/moderate/high categorical levels and candidate profile;
- the separately retained nearest Euclidean centroid;
- rule-based confidence, threshold proximity, matched counts, and coverage;
- three threshold scales and three 3x3 valence-by-arousal maps, one per
  dominance level;
- nearest alternatives plus all 27 centroid distances and relative affinities;
- optional secondary concreteness, SUBTLEX-US Zipf, and AoA character; and
- methodology, cautions, unmatched terms, and downloads.

The default fixed boundaries are `low <= 0.40`, `high >= 0.60`, with moderate
between them. Custom fixed boundaries are available. Relative affinities and
confidence labels are not probabilities. Profile names are interpretive
labels for normative lexical neighborhoods, not declarations of the poem's
emotion, speaker psychology, authorial intent, or reader response.

## Evidence & Diagnostics

Filter by lexicon, match status, or stopword status. The excluded-only control isolates matched observations omitted from the stopword-excluded view. Inspect normalized form, lemma, match method, matched entry, source values, and the exact stopword reason.

The unmatched-vocabulary table supports quality control. It does not silently guess replacements.

## Export & Help: Export Report and Data

Download:

- a readable scholar summary CSV;
- the CSV reading guide;
- the full audit ZIP.

Single-text results are temporary, so download anything you need before closing the application. Preparing downloads leaves **Export & Help** selected during the refresh.

## Export & Help: Methodology and How to Read

Use this section as an in-application reminder of the recommended reading
order, terminology, and scholarly limits.

# 9. Project / Corpus Workspace

## Create a project

Open **Project / Corpus**, expand **Create a research project**, and enter a title. Description and researcher fields are optional. Projects persist locally in `projects/versevad.sqlite3` unless an alternate database path is configured.

After selecting a project, the status header shows active-work count,
repository schema, researcher, last-modified date, and local-save context.

## Import a folder

1. Put each work in a separate UTF-8 `.txt` file.
2. Choose the folder under **Works & Metadata**.
3. VerseVAD imports each file as a separate work and retains relative subfolder paths.
4. Reimporting changed content creates a new preserved text version rather than rewriting the version used by earlier analyses.

Never use `source_lexicons/` as a corpus folder.

## Edit metadata

Select one work and edit the available fields:

- title;
- author;
- collection;
- date label;
- genre;
- notes;
- custom JSON metadata.

Metadata filters affect presentation and grouping, not lexical scores.
The work list can be searched across title, author, collection, and date, then
filtered by author or collection. Its **Analysis status** column distinguishes
Not run, Complete, and Complete with warnings. Column headers provide sorting.

## Run a corpus batch

Under **Analyze & Compare**:

1. Select the works.
2. Leave the corpus preset at **Custom**, or choose and explicitly apply
   Essential, Literary, Sound and Form, or Complete.
3. Select affective lexicons and/or **Additional analysis modules**.
4. Choose phrase and sparse-result settings.
5. For Frequency or AoA, optionally enable the non-default content-word-only
   scope under **Advanced batch methodology**.
6. Choose the stopword policy.
7. Choose **Unreviewed baseline** or an exact named review-scenario version.
8. Click **Analyze Corpus**.

VerseVAD analyzes every work separately. The new comparison is published only after the entire selected batch completes. Pending or failed batches never replace the latest complete comparison.

Additional modules are off by default because pronunciation, meter, and rhyme
can add substantial processing time to a large collection. Selecting meter or
rhyme automatically includes the pronunciation dependency. The corpus path
calls the same tested modules as Single Poem and does not duplicate their
calculations.

## Filter and compare

Filter the completed batch by collection, author, or genre. Select one or both analysis views. Compare work-level token- or type-weighted means without mixing those weightings silently.

## Long and short works

VerseVAD reports two collection profiles:

- **Token-weighted volume profile:** every included matched observation receives equal weight. Longer works contribute more because they contain more of the volume.
- **Work-weighted volume profile:** every eligible work-level token mean receives equal weight, regardless of length.

Neither is universally correct. Their difference can itself be important evidence.

VerseVAD reports two different population standard deviations beside these
means:

- **Pooled lexical-rating SD** describes the spread of all included matched
  token ratings around the token-weighted volume mean. It is reconstructed
  from each poem's matched count, mean, and within-poem population SD. If any
  required SD is unavailable or inconsistent, this corpus value remains
  unavailable.
- **Across-poem mean SD** describes the spread of poem-level token means around
  the work-weighted volume mean. It answers how much the included poem means
  vary, not how much individual word ratings vary inside each poem.

The same table reports the poem-mean median, minimum, and maximum. **Compare
Individual Works** places each poem's normalized valence, arousal, and
dominance means beside its own within-poem population SD for the selected
source, analysis view, and token/type weighting. None of these SDs is a
confidence interval, source-rater uncertainty, or a declaration of the poem's
emotion.

## Cumulative corpus results

Length-sensitive cumulative totals remain separate from means. Use them when the number and repetition of matched ratings across a work or volume is substantively relevant, while retaining the warning that they are normative lexical totals rather than measured reader impact.

## Additional module corpus results

Choose one enabled module under **Additional Module Results**. VerseVAD shows
compatible collection summaries followed by the original work, line, stanza,
token, type, or distribution rows. Equal-work means and observation-weighted
means are separate. An observation-weighted mean appears only when every
included work supplies a defensible count for that metric.

Lexical-style pooled TTR, MATTR, HD-D, MTLD, and mean word length are
recalculated from the ordered pooled token evidence and are not averages of
work-level diversity scores. Meter and rhyme remain work-level
candidates/evidence; no corpus-wide definitive meter or rhyme scheme is
created.

Inherited-form corpus results likewise remain poem-specific. The comparison
table shows each work's potential match, classification, consistency, evidence
coverage, confidence, nearest alternative, and margin. It is designed for
poem-to-poem comparison and does not assign one inherited form to the corpus as
a whole.

PoetryID corpus views group only matching source, all-matched or
stopword-excluded view, token/type weighting, module version, and
configuration. They show profile prevalence, three map-count tables,
continuous work-level VAD positions, a per-poem comparison of categorical and
nearest-centroid results, and token/type sensitivity without declaring one
corpus-wide identity. The comparison table keeps both profile names, their
agreement, nearest and categorical centroid distances, rule-based confidence,
and continuous VAD coordinates together for each work.

Both PoetryID token scopes are selected by default in new batch settings. They
remain separate in stored results, comparisons, and exports.

Coverage, unmatched evidence, warnings, configuration IDs, and denominators
remain visible. **Download module audit ZIP** reconstructs and checksum-checks
the persisted CSV/DOCX bundle for one work and module.

## Corpus Language Profile

The **Language Profile** tab reports:

- **All Works Combined:** pooled POS token counts and shares, in which long works contribute more because they contain more tokens.
- **Work-by-Work Comparison:** each work's POS count, within-work share, unique normalized types, examples, and denominator.

This profile is calculated from the current preserved version of every work and does not depend on which affective lexicon was selected. Use within-work shares when comparing works of different lengths; retain raw counts when quantity itself matters.

## Review decisions and named scenarios

Phase 5 lets you test explicit scholarly decisions without rewriting an earlier result. Start with an unreviewed baseline, then open **Review & Scenarios** and create a named scenario.

The available actions are:

- **Flag:** records a concern or interpretive note without changing a score.
- **Exclude:** preserves the published candidate in the audit but omits it from that scenario's aggregates.
- **Map:** after exact, possessive/apostrophe, and lemma candidates fail, maps a form to a verified exact entry in one selected lexicon. The method is labeled `approved_user_mapping`.

Choose the narrowest defensible scope:

- **Occurrence:** one token position in one preserved text version.
- **Work:** eligible occurrences in one selected work.
- **Project:** eligible occurrences across the project.
- **Global within scenario use:** eligible occurrences wherever that scenario is evaluated.

Every decision requires a rationale and becomes an append-only revision. Revoking, restoring, or restoring an older snapshot creates a new scenario version. Completed batches stay pinned to the exact scenario version and decision revisions used at calculation time.

### Beginner-safe review workflow

1. Run and retain an unreviewed baseline.
2. Create a clearly named scenario.
3. Inspect one candidate's text context, lexicon, match method, and risk label.
4. Choose flag, exclude, or map.
5. Select the narrowest scope that fits the evidence.
6. Write a rationale another scholar could evaluate.
7. Return to **Analyze & Compare**, select that scenario version, and rerun.
8. Compare the reviewed batch with the baseline under **Compare Two Immutable Analysis Batches**.
9. Inspect coverage changes, VAD deltas, match evidence, and unmatched vocabulary.
10. Export the workbook and preserve its methodology and **Review Decisions** sheet.

Conflicting same-scope mappings are rejected. A mapping target must exist as an exact entry in the selected installed lexicon. A proposed mapping in the older unmatched-note form remains documentation only; it does not change a calculation unless converted into an active scenario decision.

## Unmatched quality-control notes

The legacy unmatched-quality-control panel remains available beneath **Review & Scenarios**. It stores status, research note, and possible mapping text locally. These notes support research bookkeeping but do not alter completed or future analyses by themselves.

## Compare immutable batches

Under **Analyze & Compare**, choose two completed batches to see like-for-like coverage and VAD deltas. Because each batch remains tied to its exact text versions, lexicons, recipe, stopword policy, software version, scenario version, and decision revisions, this comparison can show how an explicit review scenario changed the result without erasing the baseline.

## Export

After a complete batch, download the corpus CSV and Word bundle. It includes
both collection weighting views, both stopword views, work-level data,
cumulative totals, coverage, separately labeled
emotion/sentiment/intensity constructs, unmatched notes, text/version
provenance, review decisions when applicable, the recorded methodology, and
`corpus_report.docx`. Optional-module results, structure, coverage, provenance,
and warnings remain in separately named CSV tables.

## Delete a project

1. Select the project.
2. Open **Project Settings**.
3. Read the permanent-deletion warning.
4. Type the project title exactly, including capitalization.
5. Click **Delete this project**.

The button remains unavailable until the title matches exactly. Deletion removes only that project's local works, versions, batches, analyses, metrics, and notes. It does not affect other projects or source lexicons. This deletion is permanent unless you have a separate backup.

# 10. Lexicon Explorer

## Basic lookup

1. Open **Lexicon Explorer**.
2. Enter one word or phrase.
3. Optionally enter a user-supplied mapping.
4. Click **Search installed lexicons**.
5. Select **Download printable Word report** to save the complete current
   lookup with its evidence, notices, comparisons, and provenance.

## Match labels

The Explorer distinguishes:

- exact entry;
- exact published phrase;
- lemma-derived entry;
- user-mapped entry;
- VerseVAD-derived component average;
- suggestion only;
- no match.

It never substitutes a merely similar word automatically.

## Display modes

Use original values to see the source's published scale. Use normalized values for the separately derived 0-1 comparison. Keeping both visible is recommended.

## Cross-lexicon spread

For entries found in multiple VAD sources, VerseVAD reports the range of normalized ratings and a descriptive agreement label. This is a VerseVAD orientation heuristic, not a source-provided reliability statistic or inferential test.

## Rating uncertainty and provenance

Where Warriner supplies them, the Explorer shows dimension-specific standard deviations and rater counts. A high source standard deviation indicates greater participant disagreement around that entry's mean.

The provenance panel identifies the lexicon, version, source scale, adapter, imported file, checksum, and source details. Empty uncertainty fields mean the source did not provide those values.

## Additional lexical evidence

The Explorer also checks installed concreteness, SUBTLEX-US, Kuperman AoA, and
CMUdict resources. It reports source-supplied concreteness fields; Zipf,
frequency, contextual diversity, and source POS fields; AoA ratings and
response evidence; and every exact CMUdict pronunciation candidate with
ARPAbet phones, syllable count, and lexical-stress digits.

Every displayed CMUdict candidate includes a **Hear** speaker control. It
synthesizes that exact ARPAbet sequence locally with eSpeak NG; no query or
audio is sent to a service. The preview is not a recording or an additional
source of pronunciation evidence.

**Matched**, **Source unrated**, **Unmatched**, and **Resource unavailable** are
different statuses. A missing field remains missing. Pronunciation alternatives
remain separate and are dictionary candidates rather than a context-sensitive
performance or dialect judgment.

## Rule-based sentiment and readability evidence

The Explorer calculates VADER positive, neutral, and negative proportions and
compound score for the exact entered string. It also reports applicable
word-level readability evidence: word and alphabetic-character counts,
estimated syllables, polysyllabic status, pronunciation coverage, and the
method used for each syllable estimate. These are local derived values rather
than additional published lexicon ratings.

Document-level Flesch Reading Ease, grade, Fog, ARI, Coleman-Liau, and SMOG
values are intentionally not reported for an isolated lookup. Use a complete
poem or Other Text analysis for those formulas.

## Phrase and component behavior

An exact phrase entry is shown as published lexical evidence. If no phrase entry exists but all component words have exact VAD entries in one source, VerseVAD may show their arithmetic mean as a clearly labeled **derived component average**. It never presents that calculation as a published phrase rating.

## User mapping

A mapping such as `o'er -> over` is lookup-only. It lets you inspect the mapped entry while preserving the distinction between queried and mapped forms. It does not change poem or corpus analysis.

## Printable Word report

The Explorer can export the current lookup as a narrative `.docx` report. The
report includes query processing, match methods, affective ratings and
associations, original and normalized VAD, source uncertainty where available,
derived component averages and cross-lexicon spread, concreteness, frequency,
AoA, every pronunciation variant, local VADER and word-level readability
evidence, missing-resource statuses, notices, suggestions, and source
provenance. It is designed for reading and printing; poem and corpus CSV audit
exports remain separate.

# 11. Downloads, CSV files, and Word reports

## One-poem downloads

| File | Best use |
|---|---|
| Scholar summary CSV | Readable overview with plain labels |
| CSV reading guide | Meaning and recommended use of each detailed file |
| Narrative Word report | Readable interpretation, denominators, and cautions |
| Full audit ZIP | Reproducibility, inspection, and machine-readable records |

The ZIP contains the summary, guide, comprehensive
`VerseVAD_analysis_report.docx`,
module-specific Word reports, and the following detailed CSV files.

| Audit file | Contents |
|---|---|
| `phase2_match_audit.csv` | Token/span positions, forms, lemmas, match methods, source values, inclusion/suppression, and stopword decisions |
| `phase2_coverage.csv` | Ordinary and content-focused denominators, counts, and rates |
| `phase2_vad_summary.csv` | Original and normalized VAD statistics for both views and both weightings |
| `phase2_emotion_associations.csv` | Eight-emotion and positive/negative source associations, retained as labeled categories for audit |
| `phase2_emotion_intensity.csv` | Pair prevalence and matched-pair intensity statistics |
| `phase2_cross_lexicon_comparison.csv` | Source-specific metrics placed side by side without a consensus score |
| `phase2_manifest.csv` | Software, source hashes, adapters, recipe, scenario, stopword policy, and inclusion metadata |
| `processing_*.csv` | Exact original text, poetic/model structure, shared tokens and annotations, orthographic spans, processing configuration/provenance, coverage, and warnings |
| `vader_sentiment_summary.csv` | Document positive/neutral/negative proportions, compound score, thresholds, package version, and citation |
| `vader_sentiment_sentences.csv` | Model-sentence polarity proportions, compound scores, labels, line numbers, and text |
| `vader_sentiment_report.docx` | Narrative VADER findings, method, denominators, domain cautions, and companion-file guide |
| `readability_summary.csv` | Formula scores plus word, sentence, syllable, character, polysyllable, and pronunciation-method counts |
| `readability_word_audit.csv` | Every readability word's line, characters, syllables, dictionary/override/heuristic method, and polysyllable status |
| `readability_report.docx` | Narrative readability findings, denominators, prose-domain cautions, and companion-file guide |
| `lexical_trajectory.csv` | Every VAD source and token scope by physical line, with VAD means, normalized/source-scale concreteness means, and match counts |
| `concreteness_summary.csv` | Overall source-scale statistics, thresholds, token/type coverage, and source identity when the module is enabled |
| `concreteness_by_structure.csv` | Physical-line and stanza summaries with eligible/rated counts and coverage |
| `concreteness_by_pos.csv` | Model-assigned part-of-speech summaries |
| `concreteness_terms.csv` | Represented source terms, ratings, repetition, ranks, and source-row fields |
| `concreteness_token_audit.csv` | Every token's eligibility, matching method, group, source row, rating or missing value, and reason |
| `concreteness_report.docx` | Narrative concreteness findings, denominators, coverage, cautions, and companion-file guide |
| `frequency_summary.csv` | Median-first Zipf summary, dispersion, range, scope, bands, token/type coverage, and source identity |
| `frequency_distribution.csv` | Distribution-ready Zipf values and configured band counts/proportions |
| `frequency_by_structure.csv` | Physical-line and stanza summaries with eligible/matched counts and coverage |
| `frequency_by_pos.csv` | Model-assigned part-of-speech summaries |
| `frequency_terms.csv` | Represented source terms, Zipf values, corpus counts, repetition, ranks, and source-row fields |
| `frequency_token_audit.csv` | Every token's eligibility, POS, matching method, source row, Zipf value or missing value, and reason |
| `frequency_report.docx` | Narrative frequency findings, denominators, coverage, cautions, and companion-file guide |
| `aoa_summary.csv` | Source-age statistics, thresholds, coverage, response cautions, and source identity |
| `aoa_distribution.csv` | Distribution-ready ages and configured early/middle/later band counts and proportions |
| `aoa_by_structure.csv` | Physical-line and stanza summaries with eligible/matched counts and coverage |
| `aoa_by_pos.csv` | Model-assigned part-of-speech summaries |
| `aoa_terms.csv` | Represented source terms, ages, response evidence, repetition, ranks, and source-row fields |
| `aoa_relationships.csv` | Optional descriptive unique-surface-type relationships with enabled Frequency and Concreteness results |
| `aoa_token_audit.csv` | Every token's eligibility, POS, matching method, source row, age or missing value, source-response evidence, and reason |
| `aoa_report.docx` | Narrative AoA findings, denominators, coverage, cautions, and companion-file guide |
| `pronunciation_summary.csv` | Syllable/stress summaries, token/type/line coverage, ambiguity, configuration, and required scope warning |
| `pronunciation_lines.csv` | Every physical line's exact text, coverage, completeness, syllable total or missing value, and lexical-stress sequence |
| `pronunciation_types.csv` | Observed forms, token occurrences, statuses, candidate phones, and resolved prosodic fields |
| `pronunciation_token_audit.csv` | Every token's eligibility, exact candidates, source lines, resolved fields or missing values, categorical resolution label, override note, and reason |
| `pronunciation_report.docx` | Narrative pronunciation findings, denominators, coverage, cautions, and companion-file guide |
| `meter_summary.csv` | Nearest fixed candidate kind and label, fit, coverage, confidence, and deviations |
| `meter_candidates.csv` | All 40 fixed pattern-by-foot-count candidates with rank, fit, variation, and matching lines |
| `meter_lines.csv` | Every physical line's status, nearest fixed template, selected stress path, alignment, and deviations |
| `meter_alignment_operations.csv` | Every selected syllable-to-template operation, cost, word, model POS, and ending flag |
| `meter_report.docx` | Narrative meter/scansion findings, denominators, coverage, cautions, and companion-file guide |
| `meter_realizations.csv` | Performance-aware line readings, syllable decisions, substitutions, component scores, alternatives, and confidence |
| `meter_stanzas.csv` | Stanza-level primary/alternate candidates, realized score, regularity, line-position pattern, and exceptions |
| `meter_rhythm_trajectory.csv` | Ordered line-by-line rhythmic trajectory and recurrence evidence |
| `meter_scholar_revisions.csv` | Conditional audit of explicit scholar revisions; created only when at least one revision is supplied |
| `rhyme_summary.csv` | Whole-poem scheme, ending coverage, rhyme density, pair counts, refrain/internal-rhyme counts, and recurring-sound densities |
| `rhyme_stanzas.csv` | Stanza schemes, ending coverage, exact/slant pair counts, rhymed lines, and density |
| `rhyme_lines.csv` | Every physical line's end word, status, pronunciation/rhyme parts, scheme labels, refrain, internal-rhyme and recurring-sound evidence |
| `rhyme_pairs.csv` | Within-stanza ending pairs with relationship, rhyme types, graded similarity components, eye-rhyme evidence, and cautions |
| `rhyme_internal.csv` | Exact dictionary rhyme parts recurring between eligible words within one physical line |
| `phonological_sounds.csv` | Recurring initial consonants, stressed vowels, and consonants with occurrence and line counts |
| `rhyme_report.docx` | Narrative rhyme/sound findings, denominators, coverage, cautions, and companion-file guide |
| `inherited_form_summary.csv` | Suggested candidate, classification, consistency, total and required evidence coverage, confidence, nearest alternative, and margin |
| `inherited_form_candidates.csv` | All 169 ranked profiles with definitions, assessment modes, scores, coverage, contradictions, margins, and suggestion status |
| `inherited_form_features.csv` | Candidate-by-feature rule roles, weights, scores, local coverage, observed evidence, and explanations |
| `inherited_form_profiles.csv` | Versioned profile definitions, traditions, rules, weights, and source references |
| `inherited_form_methodology.csv` | Active thresholds, configuration, scoring explanations, limitations, and safe interpretive wording |
| `inherited_form_manifest.csv` | Module/version identity, text/configuration IDs, dependent resource provenance, and warnings |
| `inherited_form_report.docx` | Narrative potential-match report with traditional definition, agreement, departures, alternatives, sources, and cautions |
| `lexical_style_summary.csv` | Token/type and configured MATTR, HD-D, MTLD, word-length, and structural-count summaries |
| `lexical_style_word_lengths.csv` | Exact alphabetic-character lengths with token counts and proportions |
| `lexical_style_lines.csv` | Every preserved physical line with blank status, lexical-token count, surface types, local TTR, and word length |
| `lexical_style_stanzas.csv` | Every preserved stanza with nonblank-line count, lexical-token count, surface types, local TTR, and word length |
| `lexical_style_token_audit.csv` | Every token's exact/normalized surface, separate lemma, structural IDs, inclusion, alphabetic length or missing value, and reason |
| `lexical_style_report.docx` | Narrative lexical-style findings, denominators, cautions, and companion-file guide |
| `poetry_id_summary.csv` | Source/view/weighting-specific continuous VAD, categorical and nearest-centroid candidates, confidence, boundary, and coverage evidence |
| `poetry_id_neighbors.csv` | All 27 ranked centroid distances and inverse-distance relative affinities, explicitly not probabilities |
| `poetry_id_lexical_character.csv` | Optional native-scale concreteness, SUBTLEX-US Zipf, and AoA token/type character |
| `poetry_id_methodology.csv` | Exact threshold profile, centroids, distance rule, evidence minimums, configuration, and cautions |
| `poetry_id_archetype_map.csv` | All 27 canonical level combinations, centroids, descriptors, summaries, and cautions |
| `poetry_id_vad_scales.csv` | Chart-ready continuous scores, levels, boundaries, centroids, and boundary distances |
| `poetry_id_report.docx` | Readable candidate-profile, VAD, confidence, narrative, and caution report |
| `*_manifest.csv` | Exact optional-module configuration, provenance, resource identity, coverage records, and warnings |

CSV files use UTF-8 with a byte-order mark for compatibility with current
Excel versions. VerseVAD does not generate JSON, TXT, or XLSX analysis
exports. The `processing_*.csv` set preserves the complete shared processing
representation, and `processing_source.csv` includes the original text, so
protect the full bundle as research material. Optional-module CSV exports
retain poem-specific provenance without copying any complete licensed
research source. Word reports provide a readable orientation; the CSV files
remain the complete tabular evidence.

## Corpus CSV and Word bundle

| File | Contents |
|---|---|
| `corpus_report.docx` | Narrative collection overview, VAD means, pooled and across-poem dispersion, denominators, and cautions |
| `corpus_project.csv` and `corpus_works.csv` | Project metadata plus work IDs, version IDs, paths, and hashes |
| `corpus_vad_metrics.csv` and `corpus_vad_profiles.csv` | Work-level VAD means/SDs and token-/work-weighted collection means with pooled and across-poem dispersion |
| `corpus_part_of_speech.csv` | Broad and detailed combined/work-level POS evidence |
| `corpus_module_*.csv` | Additional-module results, metrics, aggregates, coverage, and warnings |
| `corpus_unmatched_qc.csv` | Persistent review statuses, notes, and proposed mappings |
| `corpus_review_decisions.csv` and `corpus_methodology.csv` | Active decision revisions and reproducibility settings |

The corpus bundle is a derived report, not the authoritative database. It does
not duplicate the complete literary texts.

# 12. Mathematical formulas

Let `x_i` be the normalized VAD value for included matched observation `i`, `N` the number of included observations, `x_t` the value for distinct matched entry `t`, `T` the number of distinct matched entries, and `f_t` the frequency of entry `t`.

## Normalization

| Source scale | Formula |
|---|---|
| Warriner 1 to 9 | `x_normalized = (x_original - 1) / 8` |
| NRC VAD v1 0 to 1 | `x_normalized = x_original` |
| NRC VAD v2.1 -1 to 1 | `x_normalized = (x_original + 1) / 2` |

## Work-level means and dispersion

**Token-weighted mean**

`mean_token = sum(x_i) / N`

**Type-weighted mean**

`mean_type = sum(x_t) / T`

**Population standard deviation**

`SD_population = sqrt(sum((x_i - mean_token)^2) / N)`

The type-weighted dispersion uses the analogous formula over distinct entries.

## Corpus VAD means and dispersion

Let poem `j` contribute `n_j` included matched token observations, token mean
`m_j`, and within-poem population standard deviation `s_j`. Let `K` be the
number of included poems.

**Token-weighted volume mean**

`M_token = sum(n_j * m_j) / sum(n_j)`

**Pooled lexical-rating population standard deviation**

`SD_pooled = sqrt(sum(n_j * (s_j^2 + (m_j - M_token)^2)) / sum(n_j))`

This reconstruction combines within-poem and between-poem rating variation. It
is reported only when every included poem supplies a compatible `s_j` and
count.

**Work-weighted volume mean**

`M_work = sum(m_j) / K`

**Across-poem mean population standard deviation**

`SD_poem_means = sqrt(sum((m_j - M_work)^2) / K)`

The first SD describes matched lexical ratings pooled across the volume. The
second describes variation among poem means. Neither estimates uncertainty in
the original human ratings.

## Coverage

**Ordinary lexical-token coverage**

`coverage = matched eligible lexical token occurrences / eligible lexical token occurrences`

**Content-focused coverage**

`content_coverage = matched eligible non-stopword token occurrences / eligible non-stopword token occurrences`

Phrase coverage counts unique covered token positions, so exploratory phrase-and-component double counting does not inflate the coverage numerator.

## Concreteness statistics and coverage

Let `c_i` be the original 1-5 concreteness rating assigned to rated lexical-token position `i`, and let `R` be the number of rated token positions.

`mean_concreteness = sum(c_i) / R`

`SD_population = sqrt(sum((c_i - mean_concreteness)^2) / R)`

`concreteness_token_coverage = rated eligible lexical-token positions / eligible lexical-token positions`

`concreteness_type_coverage = rated unique normalized-surface types / eligible unique normalized-surface types`

The module also reports median, inclusive quartiles, and interquartile range. A source-supplied two-word expression assigns its rating to each of its two covered token positions for these token-weighted formulas; both audit rows retain one shared match-group ID. Empty denominators remain missing.

**SUBTLEX-US token coverage**

`frequency_token_coverage = matched eligible lexical-token positions / eligible lexical-token positions`

**SUBTLEX-US observed-form type coverage**

`frequency_type_coverage = matched unique normalized observed forms / eligible unique normalized observed forms`

The frequency module uses the token-weighted median Zipf value as its primary
summary. Empty eligible denominators remain missing; unmatched forms never
receive zero.

## Age of Acquisition statistics and coverage

Let `a_i` be the source mean acquisition age in years assigned to matched
lexical-token position `i`, and let `A` be the number of matched token
positions with numeric source means.

`mean_aoa = sum(a_i) / A`

`SD_population = sqrt(sum((a_i - mean_aoa)^2) / A)`

`aoa_token_coverage = matched numeric eligible lexical-token positions / eligible lexical-token positions`

`aoa_type_coverage = matched numeric unique normalized observed forms / eligible unique normalized observed forms`

The module also reports median, inclusive quartiles, IQR, range, and configured
band proportions. Source entries with unavailable means remain auditable but
do not enter `A`. Empty eligible denominators remain missing, and unmatched
forms never receive age zero.

For a source entry:

`numeric_response_proportion = OccurNum / OccurTotal`

`unknown_response_count = OccurTotal - OccurNum`

These source-response fields do not change the poem's token weighting. When a
cross-module relationship is available, Spearman's rank coefficient is
computed over unique paired normalized surface types, with a minimum of three
paired types.

## Pronunciation coverage and stress density

Let `P` be eligible lexical token occurrences, `R` resolved occurrences, `L`
eligible physical lines containing lexical tokens, `C` complete lines, `S`
resolved syllables, and `S1`/`S2` primary/secondary stressed syllables.

`pronunciation_token_coverage = R / P`

`complete_line_coverage = C / L`

`lexical_stress_density = (S1 + S2) / S`

An observation resolves only from one dictionary pronunciation, prosodically
agreeing alternatives, or a validated scholar override. Empty denominators and
incomplete-line totals remain missing.

## Lexical diversity, word length, and structural counts

Let `N` be included shared-preprocessing lexical tokens and `V` normalized
observed surface types.

`surface_TTR = V / N`

For configured MATTR window `w`:

`MATTR(w) = mean(TTR of every overlapping w-token window)`

For type frequency `f`, text length `N`, and configured HD-D sample `s`:

`P(type observed) = 1 - C(N-f, s) / C(N, s)`

`HD-D = sum(P(type observed) for each type) / s`

MTLD counts token-sequence factors ending when cumulative TTR reaches the
configured threshold, adds a proportional final factor, calculates forward
and reverse values, and reports their mean.

`mean_alphabetic_word_length = sum(Unicode alphabetic characters per represented lexical token) / represented length observations`

`line_word_count = included lexical tokens assigned to the preserved physical line`

`stanza_word_count = included lexical tokens assigned to the preserved stanza`

Plain TTR is length-sensitive. MATTR, HD-D, and MTLD are comparable only under
matching parameters and token policies. Unavailable values remain missing.

## Part-of-speech share

`POS_share_c = token occurrences assigned to category c / all eligible lexical token occurrences`

The combined corpus profile pools occurrences from all current works. A work-level profile uses only that work's denominator.

## Stopword sensitivity

`sensitivity = stopwords_excluded_value - all_matched_value`

## Cumulative normalized totals

**Rating total**

`rating_total = sum(x_i)`

**Above-midpoint load**

`above = sum(max(x_i - 0.5, 0))`

**Below-midpoint load**

`below = sum(max(0.5 - x_i, 0))`

**Net midpoint load**

`net = above - below = sum(x_i - 0.5)`

**Absolute midpoint load**

`absolute = above + below = sum(abs(x_i - 0.5))`

## Midpoint-centered contribution

`contribution_t = f_t * (x_t - 0.5)`

The leave-one-type-out mean change retained in the audit is:

`effect_t = mean_token - mean_token_without_all_occurrences_of_t`

## Corpus weighting

For eligible work `i`, let `m_i` be its token-weighted mean and `n_i` its included matched-observation count.

**Token-weighted volume profile**

`mean_volume_token = sum(m_i * n_i) / sum(n_i)`

**Equal-work-weighted volume profile**

`mean_volume_work = sum(m_i) / K`

where `K` is the number of eligible works with a nonmissing score.

**Reported divergence**

`divergence = mean_volume_work - mean_volume_token`

Works with no eligible score are omitted and counted; they are not assigned a neutral value.

## Emotion and sentiment association rates

For one category:

`rate_all_lexical = associated token occurrences / all eligible lexical tokens`

`rate_bearing = associated token occurrences / tokens bearing at least one positive association`

Because one token can belong to several categories, category rates need not sum to 100 percent. The eight emotions and positive/negative sentiment use the same formula but remain separately labeled constructs.

## Emotion intensity means

`intensity_mean_token = sum(supplied pair intensity for each matched occurrence) / matched pair occurrences`

`intensity_mean_type = sum(supplied pair intensity for distinct entry-category pairs) / distinct matched pairs`

Missing pairs do not enter either numerator or denominator.

## Candidate-meter fit and coverage

For one retained stress path and one template:

`meter_line_fit = max(0, 1 - selected_alignment_cost / max(observed_syllables, template_syllables, 1))`

For an exact alignment, cost is zero and fit is `1.0`. Mismatch, insertion,
omission, inversion, feminine-ending, catalectic-ending, secondary-stress, and
function-word-flexibility costs are recorded configuration choices.

`meter_line_coverage = analyzable physical lines / eligible physical lines`

`meter_matching_line_proportion = lines at or above the configured fit threshold / analyzable physical lines`

Missing pronunciation produces a missing line fit, not zero. Fit is a
similarity and confidence is rule-based; neither is a probability.

For the optional performance-aware layer, the exported overall realization
score is a bounded weighted combination of the visible component scores minus
the visible substitution penalty. Its exact weights depend on the declared
style profile and configuration. It is a ranking heuristic, not a probability
or independently validated likelihood.

## Rhyme, slant, and recurring-sound formulas

`ending_coverage = analyzable eligible line endings / eligible line endings`

`rhyme_density = analyzable line endings in an exact within-stanza pair / analyzable line endings`

`slant_similarity = 0.35(stressed_vowel) + 0.25(final_consonants) + 0.25(rhyme_part_edit) + 0.10(stress_alignment) + 0.05(syllable_similarity)`

For multiple retained pronunciations, the minimum combination score controls
the conservative relationship and the maximum is also retained. The default
slant threshold is `0.68`. This configured similarity is not a probability.

Alliteration and assonance densities divide supported words participating in a
repeated within-line sound by supported words. Consonance density divides
repeated consonant occurrences by resolved consonant occurrences.

## Inherited-form candidate formulas

For profile rule `i`, let `w_i` be its documented importance weight, `s_i` its
graded agreement score from 0 to 1, and `c_i` its local evidence coverage from
0 to 1. Only rules with available evidence enter the consistency numerator and
denominator.

`effective_weight_i = w_i * c_i`

`candidate_consistency = sum(effective_weight_i * s_i) / sum(effective_weight_i)`

`evidence_coverage = sum(effective_weight_i for available rules) / sum(w_i for all configured rules)`

`required_evidence_coverage = sum(effective_weight_i for available required rules) / sum(w_i for all required rules)`

Missing evidence therefore lowers coverage; it is never silently scored as
agreement or contradiction. A candidate can be suggested only when consistency
is at least `0.55`, overall evidence coverage is at least `0.35`, required
evidence coverage is at least `0.70`, and no available required rule scores
below `0.20`. Moderate and high confidence additionally require stronger
consistency, coverage, and separation from the next-ranked candidate. These
configured indices and labels are comparative heuristics, not probabilities.

## Worked synthetic example

Suppose normalized valence matches are `bright = 0.875` repeated ten times in one work and `dark = 0.250` once in a second work.

`token-weighted volume mean = (10 * 0.875 + 1 * 0.250) / 11 = 0.818181...`

`equal-work-weighted volume mean = (0.875 + 0.250) / 2 = 0.5625`

The divergence is substantial because the long work dominates the token-weighted view but receives only one work-level vote in the equal-work view.

# 13. Glossary

| Term | Meaning in VerseVAD |
|---|---|
| Affect match | A documented link between a token occurrence or phrase span and one lexicon entry |
| Analysis run | One immutable calculation with declared text version, lexicons, recipe, scenario, and software version |
| Analysis view | `all_matched` or `stopwords_excluded` |
| Age of Acquisition rating | Adult retrospective source estimate, in years, of when a listed word was learned well enough to understand |
| AoA orientation band | Configurable VerseVAD early/middle/later display aid, not a source-validated category |
| Arousal | Normative activation associated with a lexical item |
| Association | Binary lexicon membership for an emotion or sentiment category |
| Approved user mapping | Scenario-pinned link from a form to a verified exact source entry, applied only after ordinary matching fails |
| Candidate meter | Nearest configured fixed stress template; not definitive meter or performed rhythm |
| Declared meter style profile | Scholar-selected versioned realization weights; never an inferred period, movement, author, or tradition |
| Concreteness rating | Source-supplied 1-5 normative rating for how abstract/language-based or concrete/experience-based a lexical item was judged |
| Concreteness orientation band | Configurable VerseVAD display aid, not a validated source-paper category |
| Content words only | Optional Frequency or AoA contextual scope limited to exact model tags NOUN, VERB, ADJ, and ADV; off by default |
| Coverage | Proportion of eligible token positions represented by included matches |
| Corpus-relative frequency | Frequency evidence tied to a named source corpus rather than a context-free property of a word |
| Cumulative load | Length-sensitive sum of normalized lexical ratings or midpoint distances |
| Dominance | Normative control, power, or agency associated with a lexical item |
| Eligible token | A lexical token allowed into the matching denominator under the declared recipe |
| Exact match | Direct match from normalized surface form to a source entry |
| Exclude decision | Scenario decision that retains the candidate in the audit but omits it from that scenario's aggregates |
| Flag decision | Scenario decision that records concern without changing matching or scores |
| Form candidate | A documented inherited-form profile compared with the poem's available structural, syllabic, metrical, rhyme, and repetition evidence |
| Form consistency | Coverage-adjusted weighted agreement between the available poem evidence and one inherited-form profile; not a probability |
| Form evidence coverage | Available coverage-adjusted rule weight divided by all configured rule weight for a form profile |
| Required form evidence coverage | Available coverage-adjusted weight for required rules divided by all required-rule weight for a form profile |
| Graded slant evidence | Configured similarity across stressed vowel, final consonants, rhyme-part edit, stress alignment, and syllable count; not a probability |
| Identical rhyme | Complete retained phonological endings agree, including repeated words or homophonic complete endings |
| Internal rhyme | Exact dictionary rhyme parts recur between eligible words within one physical line |
| HD-D | Expected distinct-type proportion in a configured without-replacement token sample |
| Lemma | Model-proposed base form conditioned on part of speech |
| Lemma-derived match | Match obtained from the lemma only after exact candidates fail |
| Lexical-style word unit | Eligible lexical token represented by its normalized observed surface form, without lemma substitution |
| MATTR | Mean type-token ratio across all overlapping token windows of a configured size |
| Lexicon entry | A word or phrase and its source-supplied value or association |
| Perfect rhyme | Robust line-ending rhyme parts agree while complete retained endings are not identical |
| Rhyme scheme | Letter sequence formed only from robust perfect/identical groups; `x` is analyzable and ungrouped, `?` unresolved |
| Match observation | One included matched token occurrence or accepted phrase span |
| Normalized form | Separate processing form used for lookup; it does not replace the original text |
| Normalized VAD | Documented linear transformation to the common 0-1 display range |
| Numeric-response proportion | For the AoA source, numeric responses divided by total responses; preserved separately from the source's `Dunno` label |
| Phrase match | One accepted multi-token span linked to one source entry |
| Part-of-speech profile | Model-assigned grammatical counts and shares over all eligible lexical tokens, independent of lexicon coverage |
| Population SD | Dispersion of the complete selected matched set around its mean |
| Pronunciation candidate | One exact CMUdict phone sequence retained for an observed spelling |
| Pronunciation coverage | Resolved eligible lexical-token occurrences divided by all eligible lexical-token occurrences |
| Prosodic consensus | Multiple exact dictionary candidates whose phone strings differ but syllable count and full lexical-stress sequence agree |
| Meter fit | Configured 0-1 stress-alignment similarity; not a probability |
| Meter line coverage | Analyzable eligible physical lines divided by all eligible physical lines |
| Performance-aware realization | Optional contextual reranking and annotated reading above the unchanged fixed candidate layer; not performed scansion |
| Rhythmic organization | Rule-based accentual-syllabic, accentual, syllabic, locally metrical, mixed, no-stable-pattern, or insufficient-evidence description |
| MTLD | Mean forward/reverse sequential factor-length estimate at a configured TTR threshold |
| Rule-based meter confidence | Configured category from evidence count, coverage, fit, candidate margin, and matching lines; not a calibrated probability |
| Protected word | A word retained despite appearing in the underlying standard stopword list |
| Scholar pronunciation override | Poem-specific validated ARPAbet phones with a required note, kept distinct from dictionary candidates |
| Source value | The original value published by the lexicon |
| Review scenario | Named, versioned set of append-only decision revisions pinned to an analysis |
| Source-unrated AoA entry | A source word row whose mean is unavailable; retained in the audit with no numeric age |
| Sentiment association | Broad positive or negative NRC Emotion label, reported separately from eight emotion categories |
| Stopword | A common function word selected for exclusion from the secondary aggregate under the active policy |
| Surface form | The exact form appearing in the preserved text |
| Token | One occurrence in the text |
| Token-weighted | Every included occurrence contributes |
| Source POS tag(s) | Model-generated tag; Noun merges NOUN/PROPN and Verb merges VERB/AUX |
| Type | One distinct matched lexicon entry within the declared unit |
| Type-weighted | Every distinct matched entry contributes once |
| Unmatched | No accepted lexicon entry was assigned; the value remains missing |
| Complete pronunciation line | Physical line whose every eligible lexical token has resolved syllable and lexical-stress evidence |
| Lexical stress digit | CMUdict `0` unstressed, `1` primary, or `2` secondary lexical stress; not a metrical beat |
| Valence | Normative pleasantness or unpleasantness associated with a lexical item |
| Work-weighted | Every eligible work-level mean contributes equally |
| Zipf value | Logarithmic SUBTLEX-US word-form frequency value; about one point represents a tenfold source-corpus frequency difference |
| Alphabetic word length | Number of Unicode alphabetic characters in the preserved surface token |

# 14. Troubleshooting and limitations

## Run the self-test

Under **Installation Check**, click **Run self-test** in the sidebar. A fully
provisioned installation reports `12/12 checks passed`. You can also
double-click `diagnose_windows.bat` on Windows or `diagnose_macos.command` on
macOS.

## Browser page shows old-code errors

Close older VerseVAD launcher windows and browser tabs, then restart with the
launcher for the current operating system. A forced browser refresh or fresh
private/incognito tab can clear stale page state. In Chrome on macOS, the hard
refresh shortcut is Command-Shift-R. If no browser opens, manually visit
`http://127.0.0.1:8501` in Safari or Chrome while the launcher remains open.
The application also contains a runtime revision guard for known stale-module
problems.

## No matches or very sparse results

Confirm that the intended lexicon is selected, inspect unmatched vocabulary, and review phrase/matching methods. Do not interpret a missing result as neutral. Sparse warnings are prompts for caution, not automatic invalidation.

## File will not import

Confirm that it is a plain-text `.txt` file encoded as UTF-8 and within the displayed size limit. Word documents, PDFs, and rich-text files are not one-poem imports.

## Corpus comparison did not update

Only a complete batch becomes the latest comparison. Read the error, correct the input or configuration, and rerun the selected batch. An interrupted or failed batch does not overwrite the prior complete result.

## Lexicon Explorer returns no exact entry

Inspect separately labeled lemma, mapping, component, and suggestion sections. Similarity is not equivalence, and VerseVAD will not silently substitute a nearby word.

## Core methodological limitations

- Lexical norms are not contextual interpretations.
- Negation is flagged or protected but is not compositionally inverted.
- Irony, metaphor, voice, quotation, polysemy, and historical sense require close reading.
- Cross-lexicon normalization aligns scales but not study populations or procedures.
- Cumulative totals are not measured psychological load.
- Coverage is not accuracy.
- Descriptive agreement labels are not inferential reliability tests.
- Part-of-speech labels are model-generated and may be uncertain for poetic or historical language.
- Sentence boundaries, dependency labels, and optional named entities are model-generated and may cross or disagree with poetic lines and stanzas.
- Dependency confidence and small-model OOV rates remain missing when the installed model does not supply defensible values.
- Current corpus comparisons are descriptive and do not provide confidence intervals or hypothesis tests.
- Review mappings are scholar-authored scenario decisions, not source-published equivalences.
- Broad project or global review scopes require extra caution; prefer the narrowest defensible scope.
- Concreteness ratings are decontextualized lexical norms and do not measure imagery quality, readability, cognition, or literary value.
- Concreteness orientation thresholds are VerseVAD aids rather than validated source categories.
- Default concreteness proper-name exclusion depends on a model tag that can be uncertain for poetic capitalization and syntax.
- Corpus concreteness results persist by work with their exact configuration, coverage, warnings, provenance, and audit bundle.
- SUBTLEX-US describes American subtitle usage, not poetry, historical English, or a universal language.
- Zipf bands are VerseVAD orientation aids and do not measure difficulty, sophistication, accessibility, intelligence, or literary quality.
- Frequency POS scope and proper-name exclusion depend on model-generated tags; the non-default content-word scope excludes `AUX`.
- An unmatched frequency form remains missing; VerseVAD does not substitute `wordfreq`.
- Corpus frequency results persist by work; equal-work and safe observation-weighted summaries remain separately labeled.
- Kuperman AoA values are adult retrospective estimates, not directly observed acquisition dates, grade levels, or contextual difficulty scores.
- The source paper's content-word sampling rule and a poem occurrence's contextual model POS are separate evidence.
- AoA proper-name, POS, and lemma decisions can be uncertain for poetic language.
- AoA source SD and response counts describe source-rating evidence, not the poem's distribution.
- AoA early/middle/later thresholds are VerseVAD orientation aids rather than source-validated categories.
- Optional AoA relationships are descriptive, require at least three paired surface types, and do not establish causation.
- Age-of-acquisition results are not diagnostic of cognitive impairment or decline.
- Corpus AoA results persist by work with source-unrated and unmatched evidence kept distinct.
- CMUdict primarily represents North American dictionary pronunciation and
  can omit or misrepresent dialectal, historical, contextual, performed, or
  poetically elided forms.
- Materially different CMUdict alternatives remain ambiguous; strict handling
  can make a line incomplete until a scholar documents an override.
- Pronunciation overrides apply to an exact observed type within the current
  one-poem analysis, not to one individual occurrence.
- Stage 5 may show a local, review-only G2P candidate for an unmatched form,
  but never applies it through hidden pronunciation selection. The word stays
  unmatched until explicit approval; its own tab does not classify meter or
  rhyme.
- Corpus pronunciation results persist by work. The current corpus controls use
  the recorded default pronunciation configuration rather than offering
  project-wide scholar overrides.
- Stage 6 meter starts from dictionary lexical stress; contextual promotion,
  demotion, dialect, historical pronunciation, elision, and performance may
  support a different scansion.
- Meter costs, thresholds, fit, and confidence are transparent heuristics, not
  a probability model or validation against every poetic tradition.
- Stage 14 performance-aware scores, style compatibility, promotion/demotion,
  caesura, organization, recurrence, and confidence are transparent heuristics.
  They do not establish the performed rhythm, correct scansion, literary
  period, authorial intention, or universal metrical tradition.
- Broad style profiles are scholar-selected sensitivity settings. Comparing
  profiles can reveal model dependence; it cannot discover which profile the
  poem historically belongs to.
- Corpus meter results persist as work-level candidates; categorical
  prevalence does not declare one corpus-wide meter.
- Stage 7 starts from North American dictionary phones and spelling; dialect,
  historical pronunciation, performance, and poetic elision can change rhyme
  and recurring-sound evidence.
- Slant, eye, internal-rhyme, alliteration, assonance, and consonance methods
  are transparent descriptive heuristics, not probabilities or claims about
  authorial intention or perceptual effect.
- Corpus rhyme/sound results persist as work-level evidence; scheme prevalence
  does not declare one corpus-wide rhyme scheme.
- Registry version 2.0 compares 169 encoded, source-documented profiles. This
  broad registry still does not claim a universal, closed taxonomy of every
  named, historical, regional, community, or contemporary poetic practice.
- Form suggestions are non-probabilistic rule-based affinities. They do not
  establish authorial intention, historical membership, literary value, or a
  definitive genre label.
- Free verse, nonce forms, hybrids, translations, adaptations, and materially
  variant traditions may appropriately receive no suggestion or only
  form-derived/suggestive resemblance.
- The narrow English-language 5-7-5 haiku profile is not a universal definition
  of Japanese haiku, and its result must be read with the displayed
  tradition-specific limitation.
- Form evidence inherits the limitations and missingness of structural,
  CMUdict pronunciation, meter, rhyme, spelling, and repeated-line analysis.

# 15. Reproducibility and updating this manual

Every analysis should retain the active lexicon or optional research resource, source checksum, adapter version, software version, preprocessing recipe and configuration ID, phrase policy, stopword policy, scenario, and inclusion decisions. Completed corpus runs remain linked to preserved text versions. A concreteness result additionally retains its orientation thresholds, proper-name and phrase policies, low-coverage threshold, source-row matches, and exact workbook checksum. A frequency result retains its Zipf-band thresholds, proper-name policy, exact-before-lemma rule, optional content-word scope, low-coverage threshold, source-row matches, and exact SUBTLEX-US workbook checksum. An AoA result retains early/later thresholds, proper-name policy, exact-before-lemma rule, optional contextual content-word scope, coverage and source-response cautions, source-row matches, optional relationship methods, and the exact official erratum-supplement checksum. A pronunciation result retains every dictionary candidate, three exact source checksums, package and adapter versions, exact observed-form policy, thresholds, scholar overrides and notes, configuration identity, missingness, and physical-line completeness. A meter result retains the linked pronunciation configuration, every penalty and threshold, all fixed candidates, candidate-specific stress paths, line coverage, alignment operations, deviations, fit, confidence explanation, and dependency resource hashes. Performance-aware meter additionally retains analysis mode, declared profile/version, interpretation depth, bounded candidate/alternative limits, visible-elision policy, component weights/scores, syllable-level adjustments, alternates, stanza/poem recurrence, trajectory, organization, and separately preserved scholar revisions. A Stage 7 result retains the linked pronunciation configuration, exact resource hashes, rhyme/sound thresholds and weights, line-ending coverage, stanza/line/pair evidence, sound families, warnings, and immutable result/configuration identities.

A Stage 15 result retains the exact profile registry and version, rule weights
and roles, active thresholds, dependent pronunciation/meter/rhyme provenance,
candidate ranking, feature-level evidence and coverage, contradictions,
alternatives, confidence explanation, sources, limitations, configuration
identity, and warnings.

The companion definitions guide is maintained from:

`docs/VerseVAD_Values_and_Terminology_Guide_Source.md`

and generated as:

`docs/VerseVAD_Values_and_Terminology_Guide.docx`

This manual is maintained from:

`docs/VerseVAD_User_Manual_Source.md`

Rebuild it with:

`<bundled Python> scripts/build_user_manual.py`

The generated file is:

`docs/VerseVAD_User_Manual.docx`

When VerseVAD gains or changes a feature, update the Markdown source and rebuild, render, and visually inspect the Word file before treating the manual as current.

> FINAL READING RULE: Report the lexicon, result view, weighting, matched count, coverage, and relevant evidence with every numeric claim. Describe lexical norms and associations; reserve claims about meaning and experience for contextual scholarly argument.
