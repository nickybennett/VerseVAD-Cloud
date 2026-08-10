# VerseVAD User Guide

VerseVAD is local-first research software for examining lexical, affective,
sensorimotor, structural, prosodic, formal, and corpus-relative evidence in
poetry. It supports close reading; it does not replace interpretation or claim
to identify a poem's emotion, meaning, quality, speaker, authorial intention,
or reader response.

This guide describes the current interface. For equations, denominators,
preprocessing rules, resources, and limitations, use
[Methodology](methodology.md). For dataset installation, use
[Resource Installation](resource-installation.md).

## The basic workflow

1. Choose a workspace from the top navigation.
2. Supply text or select a stored collection item.
3. Choose an analysis profile, resources, and any genuine model settings.
4. Run the analysis once.
5. Choose a **Report Section**.
6. Use the global **Lexical Scope** and **Aggregation Weighting** controls
   directly beneath the report selector.
7. Read values with their source, denominator, coverage, exclusions, and
   cautions.
8. Save explicitly if the analysis should survive the current session.
9. Export either the visible report perspectives or a complete audit.

VerseVAD retains reusable token and resource evidence from the completed run.
Changing lexical scope or weighting performs lightweight aggregation over that
evidence; it does not repeat tokenization, tagging, lookup, meter, rhyme, or
VerseMap fitting.

## Navigation and session behavior

The top navigation groups workspaces by purpose:

- **Analyze:** Single Poem, Compare Poems, Other Text, and Lexicon Explorer.
- **Collections:** Personal Corpus, Saved Projects, Reference Corpora, and
  Analysis Library.
- **Explore:** VerseMap, Lexicon Explorer, Form Library, and Corpus Browser.
- **Learn:** Documentation, Methodology, and Training.

Each workspace owns independent temporary state. During one browser session,
you can analyze a poem, inspect a lexicon, run a comparison, and return to the
poem without losing it. Running a new Single Poem analysis replaces only the
current Single Poem result. It does not clear Compare Poems, Lexicon Explorer,
or a corpus workspace.

Unsaved state is intentionally temporary. It may disappear after a browser
refresh, Streamlit session expiration, application restart, or closing the
browser. Use **Analysis Management** to save work that must persist.

Use **Clear Workspace** in the sidebar to discard only the active workspace's
temporary inputs, results, report choices, profile selections, annotation
state, filters, and unsaved notes. VerseVAD asks for confirmation when work is
present. Stored corpora, saved analyses, and other workspaces are unaffected.

## Analysis profiles and report profiles

An **analysis profile** selects resources, enabled modules, and genuine
analysis-time settings. Built-in profiles include Full Poetic Analysis,
Computational Close Reading, Affect and Emotion, Sound and Prosody, Formal
Analysis, and Teaching/Introductory. You may customize a built-in profile or
save a named custom profile. Custom profiles are shared across analytical
workspaces in a local installation; hosted custom profiles last only for the
current hosted session.

A **report profile** is a post-analysis combination of lexical scope and
aggregation weighting. It changes how retained evidence is summarized, not
which evidence was collected.

### Lexical scopes

- **All lexical tokens:** every eligible lexical word token, including
  stopwords and function words. Punctuation-only and nonlexical artifacts are
  excluded.
- **Stopword-excluded:** eligible lexical tokens not present in the active,
  recorded list-based stopword resource. POS is not used as a stopword proxy.
- **Content words only:** eligible tokens contextually tagged `NOUN`, `VERB`,
  `ADJ`, or `ADV` by the installed model.

### Aggregation weightings

- **Token-weighted:** every eligible occurrence contributes; repetition can
  change a result.
- **Type-weighted:** each documented metric-specific type identity contributes
  once.

The ordinary default is **Stopword-excluded · Token-weighted**. You may select
one or more scopes and one or both weightings. VerseVAD displays their
cross-product, up to all six combinations. The interface prevents an empty
scope or weighting selection.

Compact orientation displays, including **Report at a Glance**, always use the
ordinary **Stopword-excluded · Token-weighted** profile so their headline values
remain stable and directly comparable. Detailed result tables show every
enabled scope/weighting combination and label each row's profile explicitly.

### Fixed analytical profiles

Some methods require a fixed input definition and therefore do not change with
the global report controls. Their sections display a fixed-profile notice and
versioned profile ID. These include VerseMap, VV-PRE, VADER, traditional
readability formulas, pronunciation, meter, rhyme and recurring-sound
analysis, inherited-form analysis, and full-text structural measures.

The global controls remain the authority only for compatible lexical
aggregates. A fixed-profile notice is not an error and does not mean that the
control was silently ignored.

## Analyze a poem

1. Open **Analyze → Single Poem**.
2. Optionally upload a UTF-8 `.txt` file or paste the poem. Title, author, and
   workspace name are optional metadata.
3. Choose an analysis profile and enabled lexicons/modules.
4. Open configuration panels only when you need to alter lookup, threshold,
   pronunciation, meter, form, or resource behavior.
5. Select **Analyze Poem** once and allow long first runs to finish.
6. Use the report selector and global report-profile controls.

The supplied source is preserved exactly for display and audit. Leading or
trailing line whitespace is analytically inert, while blank lines remain stanza
separators. Lookup normalization occurs in a separate representation.

### A practical reading order

1. **Overview:** orient yourself to central results and coverage.
2. **Affective Evidence:** VAD, emotional association and intensity, lexical
   trajectory, and PoetryID.
3. **Lexical Character, Imagery & Embodiment:** concreteness, sensorimotor
   evidence, frequency/rarity, AoA, readability, and lexical style.
4. **Sound & Form:** pronunciation, syllables, meter, rhyme, recurring sound,
   and inherited-form candidates.
5. **Structure:** lexical diversity, word length, POS, line, and stanza
   measures.
6. **VerseMap:** fixed-profile corpus-relative position and neighbors.
7. **Interactive Annotation:** token-level inspection in source order.
8. **Evidence & Diagnostics:** coverage, denominators, unmatched evidence,
   warnings, and audit details.
9. **Export & Help:** current-view and complete-audit packages.

Most major panels begin collapsed and include a bottom-center collapse control.
Several panels can remain open at once.

## Interactive Annotation

Interactive Annotation displays the complete source while letting you inspect
the evidence already retained for a token or matched expression.

- Choose an active metric lens and source.
- When several global scopes are selected, choose one **Active annotation
  scope**.
- Scope-excluded words remain visible but are not actively highlighted.
- An unmatched marker means eligible under the active scope but unmatched by
  the active resource. Excluded is not unmatched.
- A multiword match is displayed as an expression and is never partly removed
  by a lexical scope.
- Token/type weighting is not applicable to individual occurrences, so the
  weighting control is disabled with an explanation in this report.

Select a token to keep its evidence in the accompanying panel. Closing the
panel restores the selection prompt.

## Resolve pronunciation

The Overview may offer **Resolve Pronunciation** when Sound & Form evidence is
available. The button opens the pronunciation attention area.

- Select among CMUdict alternatives for ambiguous entries.
- Listen to an available pronunciation when audio playback is supported.
- For an out-of-dictionary word, inspect the clearly labeled provisional G2P
  prediction, approve it, edit its ARPAbet, or leave it unresolved.
- Approved or edited forms become session-only overrides.
- Reanalyze after changing overrides so syllable, stress, meter, rhyme, and
  inherited-form results use the decision.

Unapproved G2P predictions remain unconfirmed and do not masquerade as
dictionary evidence.

## Compare two to ten poems

1. Open **Analyze → Compare Poems**.
2. Add or remove poem cards; the workspace supports two through ten poems.
3. Supply titles and texts.
4. Choose one shared analysis profile and configure it as needed.
5. Run the comparison.
6. Choose global report profiles exactly as in Single Poem.

Tables place poems side by side. **Range (Maximum − Minimum)** is a descriptive
spread across available poem values, not a significance test. Within-poem
population SD remains poem-specific and can compare lexical dispersion when
poems differ in length. Length-normalized midpoint-deviation values and
mean-centered volatility are preferable to raw cumulative loads when length
differs substantially.

Comparison **Evidence & Diagnostics** is the audit layer: it exposes each
metric's coverage, denominator, and methodological note without repeating the
dashboard as another interpretation view.

## Other Text

Other Text uses the same evidence pipeline and report-profile system as Single
Poem but avoids poetry-specific interpretive framing where inappropriate.
Formal modules can still be enabled deliberately when their assumptions fit
the material.

## Saved Projects and corpus analysis

**Collections → Saved Projects** maintains persistent local research projects.
Import each poem as a separate work; do not concatenate a corpus into one text.

1. Create a project and import `.txt` works.
2. edit work metadata when needed;
3. choose works, sources, modules, and one shared analysis profile;
4. run a complete corpus batch;
5. select **Whole Corpus** or one poem;
6. choose an analysis report and global report profiles;
7. use filters, VerseMap, review scenarios, or exports.

Whole-corpus summaries preserve work boundaries. Equal-poem summaries give each
included poem one contribution. Pooled token summaries give longer works more
influence and are labeled accordingly. The universal lexical-scope and
token/type-weighting controls filter both summaries; corpus-level pooling versus
equal-work aggregation remains a separate comparison. An expandable scope-count
table reports eligible token occurrences for every poem and the whole corpus
under all-lexical, stopword-excluded, and content-word-only scopes. Read the
summaries with poem counts, matched-observation counts, eligible-token counts,
and coverage.

Shared corpus warnings are consolidated by warning code, message, severity, and
technical detail, with the number of affected poems and representative titles.
The complete poem-by-poem warning records remain available in a collapsed audit
table and in exports.

Research Projects are loadable in their own analysis area and available to
corpus comparison tools. The latest completed internally consistent batch is
used until a new batch completes.

## Personal Corpus

**Collections → Personal Corpus** is a locally stored, private collection for
adding, editing, removing, and inspecting your own poems. Application code is
public, but the user's corpus database and imported poetry are ignored by Git.

The report interface supports whole-corpus summaries and poem-specific
selection. Global lexical scope and weighting work as elsewhere. VerseMap
always uses its fixed Standard Profile regardless of visible report choices.

## Reference Corpora and Corpus Browser

**Reference Corpora** inventories the built-in public-domain VerseMap corpus
and any valid user-supplied local corpora. It is the maintenance location for
creating, validating, updating, and removing user corpora.

**Corpus Browser** is read-only. Use it to inspect metadata, coverage,
distributions, sortable poem-level profile values, characteristicity,
distinctiveness, and corpus-relative standardized deviations. A poem's
standardized deviation is `(poem value − corpus mean) / corpus SD`; positive
and negative signs show direction. Characteristic poems are closer to the
registered corpus center; distinctive poems are farther away. These are
descriptive profile distances, not judgments of quality or authorship.

## VerseMap

VerseMap uses a versioned fixed feature registry, scaler, PCA projection,
missing-value policy, and full-space distance method. The visible axes are PCA
display coordinates. Neighbor ranking uses the full registered feature space,
not only visible two-dimensional distance.

In Single Poem, VerseMap emphasizes nearby reference poems and poet centroids.
In corpus contexts, it can show collection poems and corpus or poet centroids.
Choose a built-in or validated user corpus where the workspace permits it.

Do not read proximity as influence, imitation, authorship, quality, or a
probability. Read the feature table and evidence coverage before interpreting
distance.

## Lexicon Explorer

Use **Lexicon Explorer** to inspect a word or phrase across installed resources
without running a poem analysis. Results may include dictionary definitions,
VAD, emotional associations and intensities, concreteness, SUBTLEX frequency,
AoA, sensorimotor strengths, pronunciation alternatives, syllables, and stress.
Resource absence remains explicit. A Word report can be downloaded.

Explorer results do not change active poem or comparison analyses.

## Form Library and inherited-form results

**Form Library** presents the definitions, evidence requirements, importance
weights, automatic/partial/manual status, sources, and limitations used by
Inherited Form Analysis.

An inherited-form result is a candidate comparison, not a declaration of form.
Read:

- **Consistency:** agreement among evaluable weighted requirements.
- **Evidence coverage:** proportion of possible weighted evidence that the
  installation and poem allowed VerseVAD to evaluate.
- **Confidence:** a rule-based summary of consistency, coverage, required-rule
  contradictions, and separation from alternatives; not a probability.

If no candidate reaches the reporting threshold, the dashboard shows only the
ten nearest candidates. The complete registry remains manually selectable.

## Analysis Library and research notes

VerseVAD does not autosave analyses. To retain one:

1. complete the analysis;
2. open **Analysis Management**;
3. enter a required saved-analysis title;
4. choose the privacy/storage option;
5. save explicitly.

Saving may retain complete evidence and text or results without text, according
to the offered privacy choice. It also records the selected analysis profile,
custom settings, global display state, report section, versions, warnings, and
notes. Loading a saved item replaces only its target workspace. If temporary
work is already present there, VerseVAD asks before replacement.

Historical results are immutable. Continue viewing the saved result or prepare
its inputs/settings for reanalysis under the current version; VerseVAD does not
silently recalculate it.

Notes attach to an analysis, comparison, poem, corpus, project, result, word,
line, chart, or other recorded context. Notes are excluded from quick exports
unless the export controls explicitly include them.

## Read coverage and missingness

Always distinguish:

- total lexical tokens;
- eligible tokens under the selected scope;
- matched and unmatched eligible tokens;
- eligible, matched, and unmatched types;
- stopword or non-content exclusions;
- phrase matches.

For example, “84 of 96 eligible content-word tokens matched” is not the same
as 84 of all tokenizer outputs. Punctuation and scope-excluded words do not
inflate the unmatched count. Missing aggregate values mean the calculation was
unavailable; they never mean neutral or zero.

## Understand common statistics

- **Mean:** arithmetic average of included observations.
- **Median:** middle value after sorting.
- **Population SD:** root-mean-square distance from the text's mean; large
  departures receive extra influence.
- **Mean absolute deviation from the text mean:** average absolute distance
  from the text's own mean; more linear than SD.
- **Method-defined cumulative load:** reported only for compatible continuous
  families. VAD uses midpoint-relative loads; emotion intensity and
  sensorimotor dimensions retain their documented source-scale sums. Generic
  cumulative AoA, Zipf, concreteness, association, and word-length loads are
  not reported.
- **Midpoint-deviation load:** summed distance above or below normalized 0.5.
  Per-observation or per-100 versions support comparisons across different
  lengths.
- **Coverage:** matched eligible evidence divided by eligible evidence.

Do not compare values across different sources, scales, scopes, or weightings
as if they were interchangeable.

## Export Current View and Export Complete Audit

**Export Current View** includes only the selected lexical profile combinations
and the fixed-profile results present in the chosen report section. It is the
compact option for a focused analysis.

**Export Complete Audit** includes all six compatible lexical profiles, all
fixed-profile results, compatible sections, coverage, exclusions, evidence,
and provenance retained by the run. Exporting does not rerun the analysis.

Every analytical workspace exposes a principal scan-friendly comprehensive Word
report: `00_START_HERE/VerseVAD_Analysis_Report.docx` for Single Poem and Other Text,
`VerseVAD_comprehensive_comparison_report.docx` for Compare Poems, and
`corpus_report.docx` for Saved Projects and Personal Corpus. The interface also
offers the report as a direct DOCX download after preparation. Reports include
text or collection metadata, analyst and research-question placeholders,
primary means, secondary medians, dispersion, cumulative and midpoint loads,
coverage, plain-language explanations, cautions, module-status information, and
a reproducibility appendix. Current View reports omit or mark unselected and
disabled sections as not reported. Complete Audit reports include every
calculated compatible profile and identify high-volume evidence retained in the
companion files. Report displays round suitable numeric values to three decimal
places; this does not alter stored or exported data.

Complete Audit ZIPs use numbered domain folders and include clean CSV tables,
comprehensive or module-specific Word reports,
`08_REPRODUCIBILITY/REPRODUCIBILITY_README.txt`, and
`08_REPRODUCIBILITY/FILE_INVENTORY.csv`. CSV values retain
available precision even though the interface rounds most numbers to three
decimal places. JSON is not required.

## Themes and browsers

Classic, Dark, Lavender, Ocean, Crimson, and Forest are designed for high
contrast in current Safari and Chrome. A local installation stores the chosen
theme locally and reopens with it. Hosted persistence depends on browser cookie
and storage policy and can be lost in private browsing or when site data is
cleared.

## Privacy and resource boundaries

VerseVAD does not send supplied texts, lexicons, project data, or results to an
external analysis service. Local and cloud deployments differ in persistence:
local project, corpus, profile, and library storage can persist on disk;
community-hosted session data is temporary unless the deployment provides a
separate persistent service.

Some research datasets cannot be redistributed with the public repository.
The installation check explains what is missing. Follow
[Resource Installation](resource-installation.md) for official sources, exact
filenames, paths, validation, citations, and licensing responsibilities.

## Reporting responsibly

Record the software version, source lexicon or dataset, lexical scope,
weighting, denominator, coverage, preprocessing recipe, fixed-profile ID where
applicable, warnings, and scholar overrides. Prefer language such as “mean
normative valence among matched content-word tokens” or “fear-associated
vocabulary.” Treat model annotations, historical spelling, polysemy, irony,
context, proper names, sparse coverage, and pronunciation ambiguity as reasons
for inspection—not as errors to hide.
