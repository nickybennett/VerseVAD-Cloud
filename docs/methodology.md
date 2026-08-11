# Methodological Commitments

## What VerseVAD measures

VerseVAD will describe the distribution of text tokens and phrases that match
entries in selected affective lexicons. Depending on the resource, an entry may
carry normative valence, arousal, and dominance ratings; categorical emotion or
sentiment associations; or emotion-intensity ratings.

These measurements describe lexical associations under a documented matching
policy. They do not establish the emotion of a poem, the state of a speaker,
the experience of a reader, or an author's intention.

## Units that must remain distinct

- The preserved original is the text supplied by the scholar.
- A text version is one immutable state of that original.
- A token occurrence has a position, structure, context, and surface form.
- A normalized form is a separate processing representation.
- A lemma is a model-assisted base form conditioned on part of speech.
- A lexicon entry is an independently sourced word or phrase with source data.
- A match links an occurrence or span to an entry and records how it matched.
- An aggregate summarizes included matches for a declared analysis scenario.
- Literary interpretation remains a scholarly act outside the numeric score.

## Unified lexical scope and weighting architecture

VerseVAD performs one complete analysis and retains reusable token, type,
phrase, resource-match, structural, and provenance evidence. Compatible report
aggregates are then calculated from that retained evidence. Changing a report
scope or weighting does not rerun Unicode normalization, tokenization, sentence,
line or stanza segmentation, POS tagging, lemmatization, lexicon lookup,
pronunciation, rhyme, meter, corpus ingestion, or VerseMap fitting.

Exactly three configurable lexical scopes exist:

- `ALL_LEXICAL` (**All lexical tokens**) includes every lexicon-eligible word
  token, including stopwords and function words, and excludes punctuation-only
  and nonlexical artifacts.
- `STOPWORD_EXCLUDED` (**Stopword-excluded**) removes forms in the recorded
  list-based stopword resource. POS is not used as a stopword proxy.
- `CONTENT_WORDS` (**Content words only**) retains contextually tagged `NOUN`,
  `VERB`, `ADJ`, and `ADV` tokens under content definition
  `versevad-content-pos-v1`.

Exactly two configurable aggregation weightings exist:

- `TOKEN` (**Token-weighted**) lets every eligible occurrence contribute;
- `TYPE` (**Type-weighted**) contributes each metric's documented type identity
  once. VAD and most resource ratings use matched resource entry; emotion
  intensity uses matched entry plus category; word length uses normalized
  surface; POS-aware lexical summaries may use POS plus normalized lemma.

Compatible modules expose all six scope/weighting combinations from one
completed result. The ordinary initial display is
`STOPWORD_EXCLUDED × TOKEN`. Selected scopes and weightings generate a
cross-product; they do not mutate the evidence.

Compact orientation cards use `STOPWORD_EXCLUDED × TOKEN` even when several
profiles are enabled. This stabilizes headline displays while the accompanying
tables retain and explicitly label the full selected profile cross-product.

### Module-specific content-word reporting exception

The interface label **Content Words Only (Scope Override)** is a post-analysis
reporting exception, not a fourth scope and not a second global scope system.
It is available only for emotional association/intensity, concreteness,
sensorimotor imagery/embodiment, frequency/rarity, and age of acquisition.
When enabled, the affected module uses `CONTENT_WORDS` with the aggregation
weighting or weightings selected globally. Other modules continue to use the
global scope selection. Because all six compatible profiles are reconstructed
from retained evidence, the exception does not repeat preprocessing or lexical
matching.

Current View interfaces and exports label and preserve this exception. A
Current View export records both the affected module and its inherited
weighting. Complete Audit exports ignore the exception for filtering purposes
and continue to include all six compatible profile combinations.

Scope-relative coverage is:

`token coverage = matched eligible token positions / eligible token positions`

`type coverage = matched eligible types / eligible types`

Excluded stopwords and excluded non-content words are outside the denominator
and are not unmatched. If a published multiword expression intersects the
selected lexical scope, the complete matched span is retained for that
phrase-based metric under `retain-complete-matched-expression-v1`. This does
not force its components into unrelated unigram metrics.

### Module capability categories

The versioned central capability registry is authoritative for reports,
exports, and documentation:

- **A — scope and weighting configurable:** VAD mean/dispersion/load,
  emotion-association and intensity summaries, concreteness, frequency/rarity,
  AoA, sensorimotor aggregates, PoetryID, word length, and compatible POS
  summaries.
- **B — scope configurable, weighting not applicable:** Interactive Annotation,
  lexical diagnostics, and sequence-native diversity calculations where the
  method retains its own occurrence sequence.
- **C — weighting configurable, fixed scope:** reserved for a method with a
  documented justification; no ordinary release module currently requires it.
- **D — fixed analytical profile:** VerseMap (`VERSEMAP_REGISTERED_V1`), VV-PRE
  (`VV_PRE_V1`), VADER (`VADER_NATIVE_V1`), published readability formulas
  (`TRADITIONAL_READABILITY_NATIVE_V1`), full-text pronunciation/meter/rhyme
  (`FULL_TEXT_PROSODY_V1`), inherited forms (`INHERITED_FORM_V2`), and full-text
  structure (`FULL_TEXT_STRUCTURE_V1`).

Fixed-profile methods display a notice because applying arbitrary global
scopes would change their named method or break reference comparability.

## Default preprocessing recipe

The default recipe for implementation and testing is:

1. preserve the original text and its line and stanza boundaries;
2. create a Unicode-normalized processing representation without overwriting
   the original;
3. retain capitalization but perform case-insensitive lexicon lookup;
4. exclude punctuation from numeric summaries while keeping it in the audit;
5. attempt exact normalized surface-form matches first;
6. apply conservative apostrophe and possessive normalization;
7. prefer the longest exact phrase when the selected adapter supports phrases;
8. use POS-sensitive lemma fallback only after exact candidates fail;
9. use reviewed mappings only when their scope and approval allow it;
10. do not stem, guess historical substitutions, or infer coined-word meanings;
11. do not automatically invert scores near negation;
12. retain all compatible matched observations once as reusable lexical evidence;
13. derive all-lexical, stopword-excluded, and content-word report scopes from
    that evidence;
14. report token- and type-weighted summaries separately for every compatible
    scope;
15. show matched counts and coverage with every aggregate;
16. preserve all candidate, suppression, exclusion, and match provenance.

This recipe will be versioned. Changes create new analyses rather than altering
completed results.

## Shared poetry-preserving processing

The one-poem workspace creates one immutable `PoemDocument` and reuses its
exact token records for every selected lexicon. This prevents source-specific
analyses in one request from drifting because of repeated tokenization or
model processing.

The shared representation retains two distinct structural layers:

- an exact section, physical lines, and stanza groupings derived from preserved
  characters, blank lines, indentation, and line endings; and
- model sentence and dependency structures, including flags when they cross a
  poetic line or stanza boundary.

Neither layer overwrites the other. NFC normalization is used only for the
separate lookup representation. Original capitalization and punctuation stay
in source/token audit fields. Lemma, part of speech, morphological features,
sentence boundaries, dependencies, and optional named entities remain
model-generated proposals that can be uncertain for poetic, historical,
dialectal, fragmented, or ambiguous language.

Default preprocessing recipe v2 separates alphabetic words joined by a run of
two or more non-apostrophe punctuation marks. For example,
`morrow;—vainly` becomes the analysis tokens `morrow`, `;`, `—`, and `vainly`,
with exact source offsets retained. This prevents stacked punctuation from
creating a false lexical token while leaving contractions, apostrophe forms,
ordinary hyphenation, and abbreviations unchanged.

Leading and trailing whitespace on every physical line is analytically inert.
This includes ordinary spaces, tabs, non-breaking spaces, and other Unicode
whitespace, including mixed indentation. VerseVAD removes those characters
only from the processing representation supplied to statistical and raw-string scoring
methods, then maps tokens and spans back to the preserved source offsets.
Whitespace-only physical lines remain blank stanza separators. The exact
original spacing, indentation, line endings, text checksum, and source display
remain unchanged for audit and Corpus Browser views.

The configuration explicitly groups POS tags as content, function, other, or
non-lexical and records hyphenated expressions, contractions, and apostrophe
forms as exact spans over their retained token components. Named-entity
recognition is disabled by default; enabling it changes the configuration
identity.

Processing coverage is separate from affective-lexicon or other research-
resource coverage. The pinned small English model has no usable vector
vocabulary, so its model-OOV count and rate remain missing. This does not make
tokens neutral and does not say whether they match a lexicon or the planned
local SUBTLEX-US frequency resource. Dependency confidence also remains
missing because the pipeline does not provide a calibrated per-edge value.

### Lexicon eligibility policy

VerseVAD keeps linguistic classification separate from downstream lexical-
resource eligibility. Under `versevad-lexicon-eligibility-v2`, a token whose
observed surface contains a Unicode alphabetic character may participate in
exact VAD, emotion, concreteness, SUBTLEX, AoA, and sensorimotor lookup even
when the language model marks it `NUM` and number-like. Thus `one` retains
`POS=NUM` and `is_numeric=true` but may match a published `one` entry or the
published expression `some one`. Pure numeric literals such as `1`, `27`, and
`3.5` remain in the token audit but outside lexicon denominators.

This is a matching-policy decision, not retokenization or preprocessing.
Original spelling, offsets, lineation, POS, lemma, and number-like status are
unchanged. Audit reasons identify alphabetically spelled number-like tokens
admitted to broad lexical lookup. The global `CONTENT_WORDS` report scope uses
only `NOUN`, `VERB`, `ADJ`, and `ADV`, so a `NUM` token remains outside that
four-tag view even when it was eligible for broad lookup. Interactive
Annotation displays only the evidence
recorded by the completed active module and never performs its own lookup.

## VAD summaries

Token-weighted summaries count every included occurrence. Type-weighted
summaries count each unique matched lexicon entry once within the declared unit.
Unmatched tokens are absent from the numeric mean; they are not assigned 0,
0.5, or another neutral value.

Cross-scale comparison may use a separate normalized score when the adapter's
source scale supports a documented linear transformation. Original scores and
source limits always remain available.

VerseVAD implements these derived transformations:

- Warriner VAD 1-9: `(x - 1) / 8`;
- NRC VAD v1 0-1: identity (`x`);
- NRC VAD v2.1 -1 to 1: `(x + 1) / 2`.

They align each documented minimum, midpoint, and maximum to a common 0-1
display range. They do not make the source vocabularies, sampling designs, or
lexicon versions interchangeable. Comparisons therefore remain source-specific
and appear with coverage and matched counts. Original values are retained, and
VerseVAD creates no pooled or consensus VAD score.

Categorical emotion associations and numeric word-emotion intensities are not
alternate scales for VAD. They retain their own value kinds and denominators
and are never normalized into or averaged with the VAD dimensions.

## VADER rule-based sentiment

VerseVAD applies `vaderSentiment` locally to the complete preserved text and
separately to each model-segmented sentence. It reports the raw positive,
neutral, and negative lexical-category proportions, which sum to approximately
one, and the rule-adjusted compound score on -1 to +1. Conventional labels use
positive at or above +0.05, negative at or below -0.05, and neutral between
those thresholds.

The three proportions do not incorporate all of VADER's word-order rules;
compound does. VADER was designed and validated for social-media sentiment.
Poetic ambiguity, irony, persona, quotation, historical usage, and lineation
can invalidate a straightforward polarity reading. Outputs are therefore
rule-based polarity evidence, not declarations of the poem's emotion, speaker,
author, reader response, or emotional archetype.

## Readability and grade formulas

The resource-free readability module reuses the shared model sentence record
and lexical-token record. Contractions and hyphenated orthographic spans count
as one readability word. Session pronunciation overrides take priority for
syllable counts, followed by the installed `pronouncing` package's bundled
CMUdict. An out-of-dictionary word receives a deterministic vowel-group
heuristic so document formulas remain calculable, but that estimate is labeled
unconfirmed and stays in the word audit.

VerseVAD reports Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog,
Automated Readability Index, Coleman-Liau, and SMOG. SMOG remains missing below
30 model-segmented sentences. The exact word, sentence, syllable, character,
polysyllable, dictionary/override, and heuristic counts accompany the scores.
These formulas were designed for prose. They do not measure literary quality,
actual comprehension, a reader's ability, cognitive status, or a prescriptive
grade requirement.

With `W` words, `S` sentences, `Y` syllables, `C` alphabetic characters, and
`P` polysyllabic words, the implemented formulas are:

- Flesch Reading Ease:
  `206.835 - 1.015(W/S) - 84.6(Y/W)`;
- Flesch-Kincaid Grade:
  `0.39(W/S) + 11.8(Y/W) - 15.59`;
- Gunning Fog:
  `0.4 * ((W/S) + 100(P/W))`;
- Automated Readability Index:
  `4.71(C/W) + 0.5(W/S) - 21.43`;
- Coleman-Liau, where `L = 100C/W` and `T = 100S/W`:
  `0.0588L - 0.296T - 15.8`;
- SMOG: `1.043 * sqrt(P * (30/S)) + 3.1291`, available only when
  `S >= 30` under the default configuration.

Any required zero or missing denominator makes the corresponding result
missing rather than zero.

VerseVAD also reports **VerseVAD Poetic Reading Ease (Experimental)**, or
**VV-PRE**, when Frequency & Rarity, Age of Acquisition, Structural & Lexical
Measures, and readability syllable evidence are all available. Unlike the
traditional formulas, VV-PRE does not use sentence length. It normalizes four
components to 0-100 and combines them as a positive weighted sum:

`VV-PRE = 0.30(frequency ease) + 0.25(AoA ease) + 0.30(line accessibility) + 0.15(word complexity)`

The versioned scoring profile is `vv-pre-content-word-profile-1.0`. Frequency,
AoA, and Word Complexity use token-weighted content-word occurrences
(`NOUN`, `VERB`, `ADJ`, and `ADV`), retaining repeated occurrences. Line
Accessibility uses all lexical words per nonblank line. The fixed calculation
therefore does not change when a user changes the visible scope of the
Frequency or AoA report.

Frequency ease maps mean content-word SUBTLEX-US Zipf 2.5 to 0 and 6.5 to 100.
AoA ease maps mean content-word AoA 12 to 0 and 4 to 100. Line accessibility
maps 15 all-lexical words per nonblank line to 0 and 3 to 100. Word complexity
maps 2.5 estimated syllables per content word to 0 and 1.0 to 100. Values beyond
the anchors are clamped. Missing components are never silently reweighted: the
overall score remains unavailable until all four exist. Reports retain the
profile ID, every raw value, component scope, normalized component, weight,
anchor, source-result identity, eligible count, match count, and coverage.

The declared bands are 85-100 Highly Accessible, 70-84 Accessible, 55-69
Moderately Demanding, 40-54 Demanding, and 0-39 Highly Demanding. VV-PRE
estimates surface-level linguistic accessibility and presentation. It does not
measure thematic, symbolic, interpretive, or literary complexity, actual
comprehension, or a reader's ability.

VV-PRE reports a separate evidence-confidence designation; it does not modify
the numerical score. **High** requires at least 90% coverage for every
component and at least 20 matched token occurrences in both Frequency and AoA.
**Moderate** requires at least 75% component coverage and 10 matched
occurrences. Otherwise confidence is **Limited**. This is a declared
evidence-sufficiency rule, not a statistical confidence interval or probability.

## Line-level lexical trajectory

For one selected VAD source and one visible token scope, VerseVAD groups
included normalized VAD observations by preserved physical line and reports
token-weighted means. Sources are never pooled. If Concreteness was enabled,
its token-weighted source-scale line mean is retained and a display-only
normalization `(rating - 1) / 4` supplies the fourth 0-1 chart series. Missing
line evidence remains missing rather than zero. The all-source/all-scope CSV
retains line text and the VAD/concreteness observation counts.

## Normative lexical concreteness

The optional concreteness module reads the user-supplied Brysbaert, Warriner, and
Kuperman (2014) workbook in place and retains its original 1-5 ratings. It uses
the same shared token and poetic-structure record as the affective analysis but
remains a separate construct and result.

Eligible lexical tokens are matched longest exact two-word expression first,
then exact normalized surface form, lemma, and a documented conservative
apostrophe/possessive fallback. Exact surface evidence always precedes lemma
evidence. Punctuation remains auditable but ineligible. Model-tagged proper
nouns are included by default. The recorded **Exclude model-tagged proper
nouns** option can remove them for a declared sensitivity analysis.

For a source-supplied two-word expression, VerseVAD assigns the expression's
rating to each covered token position for the declared token-weighted
statistics. The token rows share one group identity so this assignment remains
visible. Repetition contributes repeatedly.

The module reports the mean, median, inclusive quartiles, interquartile range,
and population standard deviation among rated tokens, plus token and unique
normalized-surface-type coverage. Empty denominators remain missing. Wholly
unmatched eligible texts have zero coverage and missing rating aggregates.

The default lower band at 2.0 and upper band at 4.0 are configurable VerseVAD
orientation aids. They are not source-published diagnostic categories. Results
must be described as normative lexical concreteness evidence, not imagery
quality, readability, cognition, or a declaration that a poem is concrete or
abstract. See [lexicons.md](lexicons.md) for resource provenance.

## Corpus-relative lexical frequency and rarity

The optional frequency module reads the pinned official SUBTLEX-US workbook in
place and retains its published word-form counts, contextual-diversity fields,
and Zipf values. It remains separate from affective ratings and concreteness.
No `wordfreq` or alternate corpus value is substituted.

By default, model-tagged proper nouns remain eligible alongside other lexical
tokens. The recorded exclusion option can remove them before reusable resource
evidence is retained. Punctuation, pure numeric literals, and other nonlexical
tokens remain in the audit but outside lexical denominators. Alphabetically
spelled number-like forms remain eligible under the shared broad lexical
policy. The global `CONTENT_WORDS` report scope retains exact contextual tags
`NOUN`, `VERB`, `ADJ`, and `ADV`; `PROPN`, `DET`, `ADP`, `CCONJ`, `SCONJ`,
`PRON`, `AUX`, and every other tag are outside that scope. The global scope is
post-analysis aggregation, not a Frequency-only configuration.

This strict scope must not be confused with the broad Language Profile:
the latter groups `VERB` and `AUX` together under **Verb** for a readable
quantity/share view, whereas the frequency restriction deliberately excludes
`AUX`. Both rely on model-generated POS tags that can be uncertain in poetry.

Matching uses exact normalized observed word form first, then an explicitly
enabled normalized lemma only when the observed form is absent, followed by
documented conservative apostrophe or possessive fallbacks. An exact form is
never replaced by a lemma. Unmatched and ineligible tokens have missing
frequency values rather than zero.

The selected-profile mean Zipf value is the primary dashboard summary. The
median remains a secondary, skew-resistant reference. The module also reports
population standard deviation, inclusive quartiles, IQR,
range, configurable bands, token and unique observed-form-type coverage,
physical-line/stanza/POS summaries, term rankings, and a complete audit.
Token weighting retains repetition; type weighting gives each documented type
identity one contribution. Empty denominators remain missing.

Zipf is logarithmic: about one point represents a tenfold corpus-frequency
difference. The default rare-to-very-common bands are configurable VerseVAD
orientation aids, not source-published literary categories. Results must be
described as corpus-relative lexical frequency evidence from an American
subtitle corpus, not difficulty, sophistication, accessibility, intelligence,
literary quality, or reader response. See [lexicons.md](lexicons.md) for
resource provenance.

## Retrospective normative lexical Age of Acquisition

The optional Age of Acquisition module reads the pinned official Kuperman,
Stadthagen-Gonzalez, and Brysbaert supplement in place. Its numeric values are
adult retrospective estimates of the age, in years, at which a source
respondent believed they had learned a word well enough to understand it.
They remain separate from affect, concreteness, frequency, difficulty, grade
level, familiarity, comprehension, intelligence, and reader response.

By default, model-tagged proper nouns remain eligible alongside other lexical
tokens. The recorded exclusion option can remove them explicitly. The global
`CONTENT_WORDS` report scope restricts aggregation to exact contextual model
tags `NOUN`, `VERB`, `ADJ`, and `ADV`; it is not an AoA-only configuration.
The paper describes its target selection as base forms used most frequently
as nouns, verbs, or adjectives, but the official supplement also contains
numeric ratings for polyfunctional spellings such as `the`, `and`, `he`, `of`,
and `to`. Source-list construction and the contextual use of a spelling in a
poem are therefore kept distinct.

Matching uses exact normalized observed form first, then an explicitly enabled
model lemma only when no exact form exists, followed by documented conservative
apostrophe or possessive fallbacks. A source row whose mean is `NA` remains
auditable but missing, as does every unmatched or ineligible token. No missing
value becomes age zero or a neutral age.

The module reports token-weighted mean, median, population standard deviation,
inclusive quartiles, IQR, range, configurable early/middle/later orientation
bands, token and unique observed-form-type coverage, physical-line/stanza/POS
summaries, represented-term rankings, source-response evidence, and a complete
audit. The default early-at-or-below-5 and later-at-or-above-12 thresholds are
VerseVAD orientation aids, not source-published categories.

When Frequency or Concreteness is enabled in the same One Poem run, the module
may report a descriptive Spearman relationship after collapsing repeated
occurrences to unique normalized surface types. It requires at least three
paired types and excludes multiword concreteness assignments. The coefficient
does not establish causation or a reader effect.

Results must be described as retrospective normative lexical AoA evidence
among matched tokens. They are not diagnostic of cognitive impairment or
decline. See [lexicons.md](lexicons.md) for resource provenance.

## Part-of-speech profile

The linguistic profile is independent of lexicon matching. It counts every
eligible lexical token assigned to each universal part-of-speech category by
the pinned English model:

`POS share = category token occurrences / all eligible lexical token occurrences`

One-poem shares use that text's denominator. The combined corpus profile pools
occurrences from current work versions, while the work-by-work table uses each
work's own denominator. Counts, shares, unique normalized types, examples,
model name, and model version remain visible. These model-generated labels can
be uncertain for poetic syntax, archaisms, fragments, and ambiguity.

Two aggregations are reported from the same token records. The broad profile
merges selected tags for readable description. The detailed profile preserves
the model's individual Universal Dependencies tags, counts, and shares. Both
use the same lexical-token denominator and each separately sums to one apart
from display rounding.

For the displayed quantity/share profile, VerseVAD merges source tags `NOUN`
and `PROPN` into one **Noun** category. The original token tag remains in the
audit. Source tag `ADP` is labeled **Preposition** in beginner-facing output;
it remains distinct from `ADV` (**Adverb**).

Source tags `VERB` and `AUX` are likewise merged into **Verb**. This retains
forms of `be` and other auxiliary/copular uses in the broad verb quantity
requested by the user while preserving their original tags in token evidence.

The one-text Language Profile may also join the already completed VAD matches
to these broad POS groups. This is a separate, lexicon-dependent subsection;
it does not change the independent grammatical count/share profile. Lexicons
and selected lexical scopes are never pooled.

Within each lexicon, lexical scope, and broad POS group, the token-weighted VAD mean
uses every included match occurrence and the type-weighted mean uses each
distinct matched lexicon lookup form once. Both appear on the independently
normalized 0-1 scale; the detailed CSV also retains original-scale means and
the normalization formula. Coverage is the number of eligible token positions
covered by the group's included matches divided by eligible token positions in
that POS group. Unmatched positions remain missing, not neutral.

An accepted published phrase contributes one VAD observation, consistent with
the main VAD summary. When all lexical components have the same broad POS, its
observation is assigned to that group and all covered token positions count
toward coverage. A phrase spanning several broad POS groups remains under
**Mixed-POS Phrase**. Because mixed-POS is a property of a matched span rather
than a token population, VerseVAD reports no coverage denominator for that
row. Groups below the configured minimum match requirement are marked sparse.

## Global lexical scopes and stopword policy

VerseVAD does not treat stopword removal or content-word restriction as neutral
preprocessing. Every compatible module retains broad lexical evidence once and
derives the three canonical scopes described above. A scope changes aggregate
eligibility only; it does not change tokenization, lexicon lookup,
exact-versus-lemma priority, source ratings, or fixed-profile modules.

The standard list is spaCy English `STOP_WORDS`, pinned to the installed spaCy
version and identified by its full active-list SHA-256 hash. VerseVAD protects
meaning-changing negations, modals, comparatives, and intensifiers—including
`no`, `not`, `never`, `without`, `may`, `might`, `must`, `more`, `most`, `too`,
and `very`—from default exclusion. A scholar may add or remove normalized forms
in custom mode; the full resulting list and the changes are recorded with the
analysis.

Recognition may use the normalized surface form or lemma and records which
evidence caused exclusion. This does not silently turn a lemma into a lexicon
match. An activated exact published phrase remains one match and is retained
intact rather than being split because one component is a stopword.

Each scope uses its own eligible token and type denominators. Stopword-excluded
coverage removes recorded stopwords from the denominator. Content-word
coverage includes only contextual `NOUN`, `VERB`, `ADJ`, and `ADV` tokens.
Excluded matched observations remain auditable but are not relabeled as
unmatched. Differences among scopes may be calculated from exported rows, but
VerseVAD does not promote a separate redundant stopword-sensitivity metric.

Top-contributor tables remain separate by profile. A matched entry's signed
midpoint contribution for one normalized VAD dimension is:

`frequency × (normalized rating - 0.5)`

Positive values raise the cumulative midpoint-centered total; negative values
lower it. The ranking is an accounting of normative lexical evidence, not a
claim about causal reader response.

## Emotion and sentiment association summaries

NRC Emotion Lexicon values are binary associations, not intensities. A term may
belong to multiple categories, so category percentages need not total 100%.
Every percentage will state its denominator.

VerseVAD reports the eight emotion categories—anger, anticipation, disgust,
fear, joy, sadness, surprise, and trust—separately from the source's broad
positive and negative sentiment labels. Both constructs use the same documented
association-counting calculations, but the interface and readable summary keep
their headings distinct.

VerseVAD reports, for every association, occurrence count, unique matched entry
count, rate per all lexical tokens, rate among tokens bearing at least one
positive association, rate per unique lexical surface type, line and stanza
distributions, and frequent contributing terms. A source term present in the
word-level lexicon but carrying no positive category association can count as a
lexicon match for coverage but not as an emotion-bearing token.

Because these source values are binary memberships rather than continuous
ratings, VerseVAD does not report an association mean, median, standard
deviation, IQR, or cumulative association load. The valid reader-facing
statistics are counts, proportions, coverage, distributions, and representative
matched terms.

## Emotion intensity summaries

Prevalence and intensity answer different questions and remain separate:

- prevalence describes how often matched emotion-associated vocabulary occurs;
- mean intensity summarizes source intensities only among entries matched for
  that emotion.

A token without a score for an emotion is not an intensity-zero observation in
the primary mean.

VerseVAD defines a matched word-emotion pair as one distinct matched lexicon
entry and category. Matched token occurrences repeat when the same entry occurs
more than once. The token-weighted intensity mean repeats those occurrences;
the type-weighted mean uses each matched entry-category pair once. Prevalence is
the category's matched occurrences divided by all lexical tokens or by tokens
matched anywhere in the intensity lexicon, as labeled.

Emotion intensity is continuous. When at least two included observations are
available, VerseVAD may therefore report dispersion as well as central
tendency. **Cumulative Emotion Intensity Load** is the untransformed sum of the
included source intensity scores. It is length- and repetition-sensitive in the
token-weighted view; VerseVAD does not invent a midpoint-centered or otherwise
normalized intensity load.

## Sensorimotor imagery and embodiment

The optional Lancaster module matches retained lexical evidence to the local
Lancaster Sensorimotor Norms resource. It reports each published dimensional
strength on its source scale and preserves the source's calculated dominant
perceptual, action, and overall sensorimotor domains. VerseVAD does not invent
an independent threshold for whether a domain is “present.”

For a selected report profile with values `x_1 ... x_N`, the dimension mean is
`sum(x_i) / N`, population SD is `sqrt(sum((x_i - mean)^2) / N)`, cumulative
load is `sum(x_i)`, and load per 100 observations is
`100 * sum(x_i) / N`. Token weighting retains repeated occurrences; type
weighting retains one observation per matched resource entry.

Dominant-domain proportion is
`number of included observations whose source dominant domain is d / N`.
Dominant-domain diversity is normalized Shannon entropy:
`-sum(p_d * ln(p_d)) / ln(number of registered domains)`. Values near zero
indicate concentration in fewer dominant domains; larger values indicate a
more even distribution. The Lancaster Minkowski-3 strength and exclusivity
fields are source-derived composites retained as published, not formulas
redefined by VerseVAD. These norms describe lexical associations, not actual
reader sensation, imagery quality, embodiment, or authorial intention.

## Phrase policies

NRC VAD v2.1 explicitly supplies unigrams and multiword expressions. VerseVAD
normalizes exact surface tokens, constructs candidates within a single poetic
line without crossing punctuation, orders candidates by descending token length
and then textual position, and greedily selects non-overlapping spans.
Alphabetically spelled number-like words may participate in those exact spans;
pure numeric literals may not.

The three policies are:

- `phrase_preferred`: selected phrases contribute one summary observation;
  component candidates remain visible but suppressed;
- `unigram_only`: phrase entries are ignored and the same deterministic
  unigram matching proceeds;
- `phrase_and_component_exploratory`: selected phrases and independently matched
  components both contribute, with a warning that this intentionally
  double-counts the span.

Shorter or equal-length phrase candidates that overlap selected spans remain in
the audit as suppressed overlaps. Coverage counts unique lexical token
occurrences covered by included records, so exploratory double-counting does
not inflate the matched-token numerator. A selected phrase contributes one VAD
observation even when it covers multiple tokens.

The local policy activates Warriner's 102 and NRC VAD v1's 132
whitespace-containing source rows as exact phrase candidates at the user's
request. They use the same longest-first selection and visible suppression
records as NRC VAD v2.1. This is a declared VerseVAD processing policy; it does
not claim that either source separately validated these entries under a
phrase-specific rating methodology.

## Cumulative VAD totals

For every VAD dimension, VerseVAD separately reports these interpretable
midpoint-relative totals on the derived 0-1 display scale:

- above-midpoint load: `sum(max(x - 0.5, 0))`;
- below-midpoint load: `sum(max(0.5 - x, 0))`;
- net midpoint load: above minus below, equivalent to `sum(x - 0.5)`;
- absolute midpoint load: above plus below, equivalent to
  `sum(abs(x - 0.5))`.

Each included matched occurrence contributes once; an activated phrase is one
matched observation under the declared phrase policy. Unmatched tokens are
absent and never receive zero or 0.5. These statistics are called cumulative
normative lexical load because they grow with encountered matched vocabulary.
They are not a direct measure of cognitive load or affective impact on a reader.
The raw sum `sum(x)` remains an internal audit field where required for backward
compatibility, but it is not a reader-facing result because it conflates text
length with the arbitrary lower bound of the normalized scale. VerseVAD also
does not create generic cumulative loads for AoA, Zipf frequency,
concreteness, or word length; their means, medians, distributions, and coverage
are the interpretable summaries.

For comparisons between differently sized poems, VerseVAD also divides the
above-, below-, net-, and absolute-midpoint totals by the number of included
matched token occurrences in token weighting or included matched lexical types
in type weighting. The **per matched token/type** value is the resulting rate.
**Per 100 matched tokens/types** is that same rate multiplied by 100; it is a
more readable display scale, not a different statistic. These values are
comparable only when lexicon, token scope, weighting, phrase policy, and other
analysis settings are held constant.

## Mean-centered VAD dispersion

VerseVAD reports two complementary, length-neutral measures of dispersion
around a poem's own VAD mean. If `m` is the poem mean and `N` is the number of
included matched observations:

- **population standard deviation** is
  `sqrt(sum((x_i - m)^2) / N)`;
- **Average Deviation from Poem Mean** is mean absolute deviation (MAD),
  `sum(abs(x_i - m)) / N`.

Population SD squares departures before averaging, so unusually distant
ratings influence it more strongly. MAD weights every departure linearly and
therefore describes the typical absolute distance from the poem mean more
directly. Neither is a duplicate of midpoint load: midpoint load uses the
fixed normalized reference point `0.5`, whereas SD and MAD use the poem's own
mean. Both SD and MAD ignore token and line order, so they measure lexical
dispersion rather than the sequence or timing of affective shifts.

Both measures are available in token-weighted and type-weighted form. The
token-weighted view retains repeated matched occurrences; the type-weighted
view gives each distinct matched lexicon entry one observation. The selected
weighting must be held constant when poems are compared.

With no included observations, central tendency and dispersion are unavailable.
With exactly one observation, mean, median, minimum, and maximum remain valid,
but population SD, quartiles, IQR, and MAD are reported as unavailable rather
than as a misleading zero. Dispersion is reported only when at least two
observations are available.

## Corpus weighting and long works

Every work is analyzed separately before collection aggregation. For a given
lexicon, normalized VAD dimension, lexical scope, and within-poem weighting,
let `m_i` be work `i`'s compatible mean and `n_i` its number of included
matched observations under that profile.

The pooled-observation volume profile is:

`sum(m_i * n_i) / sum(n_i)`

The equal-work volume profile gives every eligible work one score:

`sum(m_i) / number of eligible works`

When token weighting is selected, repeated occurrences remain observations and
long works can therefore contribute more to the first view but not the second.
When type weighting is selected, the pool instead contains each poem's
metric-specific matched type observations. The universal report controls select
the scope and within-poem weighting before either collection aggregation is
computed. VerseVAD reports both collection views plus their signed difference.
Work scores that are
missing because no observations matched remain missing; they are counted as
omitted and do not become neutral values. This collection-level distinction is
separate from the within-work token/type distinction: type-weighted work means
give each distinct matched lexicon entry one contribution.

Eligible token counts are retained separately from matched observations. For
each poem and each of the three lexical scopes, the corpus interface and
`corpus_scope_token_counts.csv` report the token-occurrence denominator before
resource matching. Whole-corpus scope counts are sums of those poem-level
denominators and never arise by concatenating or retokenizing the corpus.

Corpus comparisons use one completed batch. A pending or failed batch can
contain individually complete work runs for recovery and audit, but it never
replaces the latest complete comparison view.

## Versioned review scenarios

The unreviewed baseline remains distinct from every reviewed analysis. A named
scenario contains append-only decision revisions and produces immutable
scenario versions.

- A **flag** records a concern without changing matching or aggregates.
- An **exclusion** retains the published candidate in the audit but omits it
  from that scenario's aggregate.
- An **approved mapping** may map a source form to a verified exact entry in one
  selected lexicon only after exact, apostrophe/possessive, and lemma candidates
  fail.

Decisions use explicit occurrence, work, project, or global-within-scenario-use
scope. The narrowest defensible scope is preferred. Conflicting mappings at the
same applicable scope are rejected rather than guessed. Each decision records
the source form, target when applicable, lexicon, preserved text/version and
token location when applicable, semantic-risk category, rationale, revision,
and active/revoked state.

Creating, revising, revoking, restoring, or restoring an older scenario
snapshot appends a new version. Every completed run records the exact scenario
version and active decision revisions. Batch comparison therefore shows
before-and-after coverage and VAD deltas without rewriting the baseline.
Mapping and exclusion counts remain visible; unmatched-note proposals do not
affect scores unless converted into active scenario decisions.

The unreviewed baseline is the ordinary automatic result. A user selects a
named review scenario only when documented flags, exclusions, or verified exact
mappings should define an alternative auditable batch. Shared warnings are
presentation-deduplicated for whole-corpus inspection, but every original
poem-level warning record remains unchanged in the audit export.

## Comprehensive Word report contract

The Current View and Complete Audit research bundles include a readable DOCX
report in addition to full-precision CSV evidence. The report is generated only
from the completed retained result and never triggers tokenization, matching, or
reanalysis. Suitable displayed numbers are rounded to three decimal places;
companion CSV values retain their available precision.

Current View includes the selected compatible lexical profiles and the active
report family. Disabled or unselected optional families are omitted or marked
not reported. Complete Audit includes every calculated compatible profile,
fixed-profile results, coverage, warnings, resources, and reproducibility
metadata. Atomic or high-volume evidence remains in named companion CSV files
and is inventoried rather than being expanded into an unreadable Word table.
Interpretation bands appear only where the corresponding module already defines
an auditable band; the report does not invent thresholds.

## Lexicon Explorer derivations

Lexicon Explorer resolves an exact normalized entry or phrase before displaying
an explicitly labeled POS-sensitive lemma-derived entry. A user-supplied mapped
lookup is display-only and never changes poem/corpus matching. Similar terms are
suggestions only. If a phrase has no source entry and every component has an
exact VAD entry in one source, the interface may show their arithmetic mean as
a **VerseVAD-derived component average**, never as a published phrase rating.

Cross-lexicon spread is the range of normalized ratings for the displayed
entries. The interface labels ranges up to 0.10 "high" agreement, up to 0.25
"moderate," and larger ranges "low." This is an orientation heuristic, not a
source-provided reliability statistic or inferential test. Warriner standard
deviations and dimension-specific rater counts are displayed from their source
columns; missing uncertainty fields in other resources remain blank.

The Explorer also reuses the local VADER engine on the exact entered string and
the readability engine's word audit. It exposes VADER's three proportions,
compound score, and threshold label, plus word, alphabetic-character, syllable,
polysyllabic, pronunciation-coverage, and syllable-method evidence. It does not
show document-level readability formulas for an isolated lookup because a word
or short phrase is not a defensible readability document.

## Cross-lexicon comparison

### Multi-poem comparison summaries

Compare Poems applies one validated `AnalysisRequest` configuration to every
poem. A displayed numeric row therefore compares like with like: the same
source, lexical scope, weighting, metric definition, and unit. The normal
report shows each available poem value and the observed range:

```text
range = maximum available poem value − minimum available poem value
```

Missing values are omitted from the range and remain visible through coverage
and denominator evidence; they are never replaced with zero or a neutral
rating. Range is a descriptive span, not an effect size, confidence interval,
or significance test. Standard-deviation metric rows remain separately labeled
as **Within-Poem Dispersion** because they describe matched observations inside
each poem. Complete legacy equal-poem summaries and cross-poem dispersion are
retained only in the long-form audit export for reproducibility, not promoted
in the normal report.

The dashboard imposes a presentation order without changing calculations:
headline means or composite scores, method-defined cumulative or
midpoint-relative loads where valid, then within-poem dispersion. PoetryID is
narrowed to the selected lexical scope and weighting,
then to one identified VAD source, and displays category fit before nearest
centroid. All alternate source/view/weighting rows remain auditable in export.

NRC emotion and positive/negative association proportions use eligible lexical
tokens or types as their denominator. The stopword-excluded comparison view is
reconstructed from each immutable match record's explicit stopword-view
inclusion flag; it does not rerun or relabel the all-token aggregate. NRC
emotion-intensity means and population standard deviations are reconstructed
from the retained word-emotion pairs under the same token/type choice. An
absent word-emotion pair remains missing rather than becoming zero.

The Compare Poems VerseMap view projects every poem into one selected,
versioned reference index. The visible table is limited to the two PCA
coordinates and nearest poem/poet-centroid labels. Neighbor selection still
uses full registered standardized feature-space distance, not apparent
two-dimensional screen distance. All Standard Profile inputs, coverage, and
model provenance remain in the export.

Each lexicon is analyzed independently. Numeric VAD means may be displayed on a
separate normalized 0-1 scale alongside source-scale results. NRC VAD v1 and
v2.1 remain labeled as versions of the same family, not independent
replications. Categorical association rates and intensity prevalence/means keep
their different value kinds and denominators. VerseVAD creates no consensus
score or pooled rating.

## Context and close reading

Negation, irony, metaphor, quotation, speaker attribution, narrative distance,
and historical sense are not solved by lexicon matching. VerseVAD can flag
contexts for review, but flags do not change primary scores. Scholar-approved
exclusions or mappings create explicit alternative scenarios with visible
before-and-after results.

## Sparse and uncertain results

Aggregates with few matched items will be marked sparse or unstable. Missing
data remains missing rather than becoming zero. Coverage, lemma reliance,
mapping reliance, exclusions, and semantic-risk dependence are part of the
result, not merely diagnostics hidden elsewhere.

The interface labels coverage below 60% as limited orientation, 60-80%
as moderate orientation, and at least 80% as broad orientation. These bands are
reading aids only, not validated universal thresholds or exclusion rules. The
exact numerator, denominator, and rate remain primary.

## Descriptive statistical definitions

VerseVAD reports descriptive statistics on the included matched observations.
Its standard deviation is the population standard deviation (`ddof = 0`),
because it describes the complete selected match set rather than estimating a
larger sampled population. Quartiles use the inclusive method. A single
observation has zero dispersion and quartiles equal to that observation. An
empty match set has missing statistics, not zeros.

Confidence intervals are deliberately deferred until the resampling unit and
dependence structure can be declared for the requested comparison. No
inferential meaning should be attached to the current descriptive summaries.

## Metric formula and denominator reference

The equations below summarize cross-cutting calculations. Module-specific
sections above and the resource manifests remain authoritative for source
scales, matching order, thresholds, and limitations.

- Arithmetic mean: `sum(x_i) / N` over included observations.
- Population variance: `sum((x_i - mean)^2) / N`; population SD is its square
  root. VerseVAD uses `ddof=0`.
- Mean absolute deviation from the poem mean:
  `sum(abs(x_i - mean)) / N`.
- Inclusive quartiles use the inclusive interpolation method; IQR is
  `Q3 - Q1`; range is `maximum - minimum`.
- Token/type coverage is matched eligible tokens/types divided by eligible
  tokens/types. Scope exclusions are outside both numerator and denominator.
- Type-token ratio is `distinct normalized surface types / lexical tokens`.
  MATTR is the arithmetic mean of TTR across all overlapping fixed-length
  windows. HD-D sums each type's hypergeometric probability of appearing in a
  without-replacement sample and divides by sample size. MTLD averages forward
  and reverse factor lengths at the configured TTR threshold.
- Mean words per nonblank line is lexical tokens on nonblank physical lines
  divided by nonblank physical lines. Mean words per stanza is lexical tokens
  divided by stanzas. Mean nonblank lines per stanza is nonblank physical lines
  divided by stanzas. Their displayed SDs use the complete observed line or
  stanza population.
- Mean alphabetic word length is total Unicode alphabetic characters divided
  by included lexical observations. POS share is category token count divided
  by all eligible lexical-token occurrences in that profile.
- Emotion-association proportion is associated included observations divided
  by eligible lexical observations. Because one term may carry several
  associations, category proportions need not sum to one. Emotion-intensity
  means include only recorded word-category intensity pairs; absence is not
  intensity zero.
- Rarity is derived from the retained SUBTLEX Zipf value with the report's
  explicitly labeled orientation; a one-point Zipf difference is approximately
  tenfold frequency. No absent word is assigned Zipf zero.
- Pronunciation coverage is resolved eligible pronunciation items divided by
  eligible items. Syllables per line sum resolved syllables on each nonblank
  line; mean syllables per line is the arithmetic mean across those lines.
  Stress density is stressed resolved syllables divided by all resolved
  syllables.
- Meter line fit is `max(0, 1 - alignment_cost / max(observed_syllables,
  template_syllables, 1))`. Rhythmic regularity and trajectory summarize the
  distribution and sequence of those line-level fits under the documented
  candidate/performance profile; they are not scansion probabilities.
- Rhyme coverage is analyzable eligible line endings divided by eligible line
  endings. Alliteration, assonance, consonance, internal rhyme, and refrain
  rates use their labeled eligible line, token, phone, or pair denominators;
  the detailed audit identifies the actual denominator for each row.
- Corpus equal-poem mean is `sum(poem means) / included poems`. A pooled
  observation mean is `sum(poem_mean_i * observation_count_i) /
  sum(observation_count_i)`. Corpus-relative standardized deviation is
  `(poem value - corpus mean) / corpus SD`; when corpus SD is zero, the
  standardized value remains unavailable.
- Euclidean profile or centroid distance is
  `sqrt(sum((standardized_feature_i - centroid_i)^2))` over the registered
  available feature space. VerseMap PCA coordinates are linear projections of
  registered standardized features for visualization; nearest-neighbor search
  continues to use full registered feature-space distance. Characteristicity
  increases as centroid distance decreases; distinctiveness increases as it
  increases. Exact registry, scaling, missingness, and percentile rules are in
  [VerseMap Standard Profile 1.0](versemap-standard-profile.md).
- Inherited-form consistency is the coverage-weighted mean of available rule
  scores. Evidence coverage is effective available rule weight divided by
  total possible rule weight. Match percentage and confidence remain separate
  because agreement without adequate evidence is not strong support.

Every exported numeric row retains its metric ID, unit or scale, scope,
weighting where applicable, observation count, eligible count, coverage, and
source/configuration identity. Interface rounding never changes exported
precision.

## Capitalization collisions

Case-insensitive lookup can collapse source entries that have different
capitalization and ratings. The Warriner file contains ten such pairs. The
adapter retains every source entry. Exact source capitalization may resolve the
pair; otherwise the occurrence is left unmatched for review. VerseVAD does not
average the candidates or select the first row.

## Pronunciation, syllable, and lexical stress

The pronunciation module uses exact observed-form entries from official CMUdict files pinned at
one upstream commit. Case and apostrophe style are normalized for lookup, but
the observed surface, normalized form, lemma, and every dictionary candidate
remain separate. No lemma, possessive-base, spelling repair, or pronunciation
prediction is substituted automatically.

The shared linguistic model may internally split a contraction into components
such as `you` + `'re`, `ca` + `n't`, or `wo` + `n't`. The module instead consumes
the complete contraction span preserved during preprocessing and performs one
exact lookup for the observed spelling, such as `you're`, `can't`, or `won't`.
The component tokens remain visible in the token audit but are marked
`not_eligible`, preventing fragments such as `'re` and `n't` from appearing as
out-of-dictionary words or inflating pronunciation denominators. A
leading-apostrophe form such as `'tis` is joined only when the complete form has
exact dictionary evidence or an explicit session override, so an opening
quotation mark is not mistaken for a contraction. If a preserved complete
contraction has no entry, that complete spelling—not its model-token
fragments—remains unmatched and enters the ordinary review-only G2P flow.

One dictionary candidate resolves directly. Multiple candidates resolve only
when every candidate agrees on both syllable count and the complete lexical-
stress digit sequence; phone-string alternatives remain visible. A difference
in syllables or stress is materially consequential and remains ambiguous until
a poem-specific scholar override supplies validated ARPAbet phones and a
required rationale. Confidence labels describe this categorical resolution
status and are not probabilities.

The one-text **Words Needing Attention** interface is collapsed by default and
lets the scholar explicitly select one of those retained materially different
dictionary candidates. The selection is serialized into the same reversible
session-only override configuration and is labeled as a user selection from
dictionary evidence, not as an automatically preferred candidate. Dependent
pronunciation, meter, rhyme/sound, and inherited-form results are then
recomputed.

Unmatched, ambiguous, and source-vowelless observations have missing
pronunciation, syllable, and stress values. A physical line receives a total
and stress sequence only when every eligible lexical token resolves. This
prevents partial coverage from creating deceptively short lines.

For an out-of-dictionary form, the default-hidden **Show Out-of-Dictionary
Words** subsection may generate a review-only US-English pronunciation with
the bundled eSpeak NG 1.52.0 G2P/text-to-phoneme system and a documented
IPA-to-ARPAbet mapping.
The row retains `unmatched` status, and its pronunciation, syllable, stress,
line, meter, rhyme/sound, and inherited-form evidence remain missing. The user
may leave it explicitly unresolved, approve the provisional ARPAbet, or edit
the ARPAbet before approval. Only the latter two actions serialize a
source-labeled session override and trigger dependent recomputation. Thus a
prediction is not a fallback, match, or confirmed pronunciation.

Candidate speaker controls synthesize the explicit displayed ARPAbet sequence
locally with eSpeak NG. Hearing a prediction does not approve it. The synthetic
preview is an orientation aid rather than source evidence, a human recording,
or a dialect/performance judgment.

Stress digits are CMUdict lexical evidence: `0` unstressed, `1` primary, and
`2` secondary. Stress density divides primary plus secondary stressed
syllables by all resolved syllables. It is not a measure of metrical fit or
performed emphasis.

CMUdict primarily represents North American English. Dialect, historical
pronunciation, performance, context, and poetic elision can differ. VerseVAD
therefore reports dictionary-based pronunciation, syllable, and lexical-stress
evidence, not the poem's definitive sound or meter.

## Candidate meter and rhythmic regularity

The meter module consumes retained pronunciation and stress evidence without changing its
pronunciation decisions. For every analyzable physical line it compares five
recurring base patterns—iambic `01`, trochaic `10`, anapestic `001`,
dactylic `100`, and amphibrachic `010`—at one through eight feet. Spondees
`11` and pyrrhics `00` are local substitution labels, not additional
whole-line base candidates.

Deterministic dynamic-programming alignment has explicit configuration costs
for stress-position mismatch, secondary-stress flexibility, function-word
promotion, extra or omitted syllables, feminine and catalectic endings, and
initial inversion. Line fit is `max(0, 1 - cost / max(observed syllables,
template syllables, 1))`. Fit is a configured similarity, not a probability.

The estimator explores materially different retained CMUdict stress paths up
to a declared per-line limit. The candidate-specific selected path is
auditable but is not promoted to a dictionary or performance fact. A line with
missing pronunciation evidence or excessive combinations remains unscored.

Poem-level reporting retains candidate kind, pattern, foot count, nearest
alternative, mean/median fit, line coverage, matching-line proportion,
variation, deviations, and rule-based confidence. The output language is
“nearest configured candidate” or “candidate meter,” never definitive meter,
correct scansion, performed rhythm, or authorial intention.

### Optional performance-aware realization

Built-in analysis profiles display the fixed candidate and performance-aware
layers together by default; the fixed estimator and its result remain
unchanged. When a performance-aware layer is selected, VerseVAD reranks a bounded set of retained meter
candidates using separately visible fixed-fit, contextual-prominence,
syllable-count, phrasing, ending, pronunciation, poem/stanza recurrence, and
declared-profile components. The overall score is a configured heuristic, not
a probability.

Every realized position preserves its source lexical-stress digit and records
any proposed promotion, demotion, secondary-stress flexibility,
extrametrical syllable, or omitted position separately. Initial inversion,
headless opening, feminine ending, catalexis, local spondaic/pyrrhic movement,
stress clash/lapse, and punctuation-supported caesura are inspectable
interpretations. Unmarked written syllables are never silently elided.

Broad profiles are scholar-selected and versioned. They adjust visible
tolerances; VerseVAD does not infer period, movement, author, or a uniquely
correct performance. Poem/stanza recurrence, trajectory, and organization
labels are rule-based textual descriptions. Stable alternating line-position
recurrence is described generically; no named stanza-form classifier is
added.

Performance optimization does not change analytical inclusion or floating-
point formulas. Cache keys contain source, preprocessing, configuration,
resource/engine, and upstream-result fingerprints relevant to one module.
Invalid entries are discarded and recomputed. Cache state and timing are
diagnostic evidence, not analytical metrics.

## Rhyme and phonological patterns

The rhyme and phonology module consumes retained phones and stress without changing any
pronunciation decision. A line-ending rhyme part begins at the last
primary-stressed vowel, or the last secondary-stressed/marked vowel when
necessary, and continues to the word end. Exact scheme groups require one
agreed rhyme part across all retained alternatives. `x` marks an analyzable
ungrouped ending and `?` an unresolved ending; no missing ending receives a
neutral value.

Perfect, identical, masculine, feminine, multisyllabic, graded slant, eye, and
internal-rhyme evidence remain separate fields. Slant similarity is:

`0.35(stressed vowel) + 0.25(final consonants) + 0.25(rhyme-part edit) + 0.10(stress alignment) + 0.05(syllable similarity)`

The default classification threshold is `0.68`. The conservative minimum
across retained pronunciation combinations controls the label; the maximum is
also retained. This is a configurable heuristic rather than a probability.
Slant and spelling-based eye rhyme do not create exact scheme groups.

Phonemic alliteration uses repeated initial consonants, assonance repeated
stressed vowels, and consonance repeated consonants within physical lines.
Exact repeated physical lines supply refrain evidence independently of
CMUdict. Coverage is analyzable eligible line endings divided by eligible line
endings.

Results describe local dictionary-, spelling-, and text-based evidence, not a
definitive rhyme, performed reading, dialect, perceptual sound effect, or
authorial intention.

## Lexical diversity, word length, and word counts

This module does not report typography, punctuation, approximate-refrain,
syntactic-complexity, enjambment, or end-stopping classification.

One word-count unit is one shared-preprocessing lexical token. Punctuation and
numeric tokens are excluded. Physical blank lines remain in the line audit
with count zero because they are observed structural separators. This token
policy may differ from an editor's orthographic convention for contractions or
hyphenated expressions, so the exact surfaces and token IDs remain auditable.

Lexical-diversity types are normalized observed surface forms. Lemmas are
retained separately and are never substituted. Plain TTR is descriptive and
length-sensitive. MATTR averages TTR across every overlapping configured
window. HD-D sums each type's hypergeometric probability of appearing at least
once in a configured without-replacement sample and divides by the sample
size. MTLD averages forward and reverse token-sequence factorization at a
configured TTR threshold.

The defaults are MATTR window 50, HD-D sample 42, and MTLD threshold 0.72.
MATTR or HD-D remains missing when the poem is shorter than its configured
denominator; an undefined bidirectional MTLD also remains missing. Results are
comparable only when token policy and all parameters agree. Short poems can
remain unstable even when a formula is available.

Word length counts Unicode alphabetic characters in the exact lexical-token
surface. Apostrophes, hyphens, and other punctuation do not add to the count.
A lexical token with no alphabetic characters remains in structural word
counts but receives no length rather than length zero.

The structural summary calculates the arithmetic mean and population standard
deviation of lexical-token counts across nonblank physical lines, lexical-token
counts across stanzas, and nonblank physical-line counts across stanzas.
Population standard deviation is used because the displayed units are the
complete set observed in the analyzed poem, not a sample drawn from that poem.
Blank structural separator lines remain in the detailed line audit with zero
words but do not enter either nonblank-line denominator. Empty sets remain
missing rather than becoming zero.

The module reports textual observations, not literary quality, vocabulary
knowledge, intelligence, education, comprehension, reader effect, or
authorial intention.

## Project/corpus aggregation and all-resource lookup

The corpus path invokes the existing workspace orchestration once per preserved
work. Every enabled optional module therefore consumes the same shared
preprocessing representation and retains its original configuration,
provenance, coverage, warnings, and audit artifacts.

Collection means group only records with matching module version,
configuration ID, metric ID, unit, and weighting. Every numeric document metric
can receive an equal-work descriptive mean. An observation-weighted mean is
available only when the integration layer has a defensible observation count
for that exact metric in every included work. Medians, dispersion, schemes,
categorical labels, and length-resistant diversity measures are not treated as
though weighting their work-level values created a pooled result.

For lexical style, separately labeled pooled TTR, MATTR, HD-D, MTLD, and mean
alphabetic word length are recalculated from the ordered sequence of included
normalized-surface token evidence stored for each work. Work count, omitted
work count, token count, configuration, and aggregation method remain visible.
Meter and rhyme remain work-level candidates/evidence; VerseVAD does not
declare a collection's definitive meter or rhyme scheme.

Lexicon Explorer performs read-only local lookup in the packaged Open English
WordNet 2025+ dictionary, affective lexicons, concreteness, SUBTLEX-US,
Kuperman AoA, and CMUdict. Dictionary senses are grouped by source part of
speech and retain definitions, examples, identifiers, synonyms, antonyms, and
available broader/narrower relations. VerseVAD does not rank those senses by
context or claim to perform word-sense disambiguation. Source entries and
fields remain separate. Exact, lemma-derived, and user-mapped evidence is labeled;
CMUdict alternatives remain separate. Resource-unavailable,
available-but-unmatched, and source-entry-without-numeric-rating states remain
distinct. Explorer evidence is decontextualized and does not resolve poetic
sense, performance, dialect, metaphor, irony, or reader response.

## PoetryID dependent classification

PoetryID consumes only completed normalized VAD summaries. It does not
re-tokenize, reload a VAD source, rematch text, or calculate a second VAD
result. Each assignment retains the exact upstream analysis ID, lexicon ID and
name, lexicon version, adapter version, source SHA-256, lexical scope, and
weighting.

Version 1 classifies each normalized dimension using a versioned fixed profile:
low when `score <= low_max`, high when `score >= high_min`, and moderate
otherwise. The built-in boundaries are 0.40 and 0.60. A custom-fixed profile
may set separate boundaries for valence, arousal, and dominance. The low,
moderate, and high centroids default to the midpoint of each configured region.
Corpus tertiles and z scores are not implemented because they require a
separately specified and versioned reference-corpus policy.

The three classified levels select one of 27 canonical profiles. Separately,
PoetryID calculates Euclidean distance from the continuous normalized VAD point
to every profile centroid:

`distance = sqrt((V - Vc)^2 + (A - Ac)^2 + (D - Dc)^2)`

For display, inverse-distance similarity is calculated as
`1 / (distance + epsilon)` and normalized across all 27 candidates. These
relative affinities are not probabilities. Categorical and nearest-centroid
profiles are both retained when they differ.

Rule-based confidence considers categorical/centroid agreement, assigned
centroid distance, the nearest-neighbor margin, distance to the low/high
thresholds, and source VAD coverage. Labels are high confidence, moderate
confidence, boundary sensitive, or low confidence; none is a calibrated
probability.

Token- and type-weighted assignments have separate configurable evidence
minimums and coverage requirements. Missing/invalid VAD, too few observations,
or inadequate coverage produces a structured unavailable state. Unmatched
items never receive a midpoint or neutral value.

Optional concreteness, frequency, and age-of-acquisition character is adapted
from completed module summaries on each source's native scale. Token and type
statistics remain separate. These secondary descriptors never modify the VAD
levels, profile, distances, affinities, or confidence.

Corpus summaries group PoetryID only when module version, configuration,
source/view scope, and weighting match. Profile prevalence, 3x3 map counts,
continuous work positions, and token/type differences remain descriptive
work-level evidence and do not create a corpus-wide identity.

PoetryID exports six UTF-8 CSV files and one narrative DOCX report
and no JSON file.

## Interface-only invariants

The interface design does not define a new analytical method. Classic, Dark,
Lavender, Ocean, Crimson, and Forest appearance; active workspace; preset-menu
choice; expanded/collapsed sections; search text; and project-list filters are
presentation state. They do
not participate in tokenization, matching, weighting, thresholds, confidence,
result IDs, cached analysis, project records, or exports.

A module preset is a visible convenience for selecting modules. It is applied
only after an explicit action and never overwrites advanced methodology. The
result and its exports continue to record the exact effective analysis
configuration rather than a preset label.

Publication-oriented chart rendering remains light and stable regardless of
the application appearance. Interface charts use the same underlying data in
all appearance modes. The lexical-evidence language, missing-value rules,
coverage cautions, and per-module methodology remain unchanged.

### Interactive Annotation presentation contract

Interactive Annotation is a client-side inspection layer over an immutable
completed Single Poem analysis. Its payload is assembled by joining existing
module audit records to the shared preprocessing tokens by stable token ID.
The displayed poem is reconstructed only from the preserved original string
and those tokens' recorded character offsets. No client or interface code
retokenizes the string, repeats a lexicon lookup, substitutes a missing value,
or changes a score, denominator, coverage value, result ID, or export.

Only one continuous variable controls token color at a time. Colors use the
documented absolute source direction and a fixed midpoint; they are not
rescaled to the poem's observed minimum and maximum. VAD colors use normalized
0–1 values while the detail panel retains the source value and native scale.
The fixed VAD source priority is NRC VAD v2.1, NRC VAD v1, and Warriner, and a
user may select another enabled source. Unmatched status is evaluated against
the active continuous lens. Valence, arousal, and dominance therefore share
the selected VAD lexicon's token match status, while concreteness, frequency,
and AoA each retain their own source-relative status. Excluded, unavailable,
and unmatched remain distinct states.

Alphabetically spelled number-like words remain selectable when the completed
active analysis recorded them as lexicon-eligible. Consequently, the two tokens
in an NRC v2.1 `some one` phrase expose the shared expression evidence, while a
SUBTLEX lens may expose separate `some` and `one` unigram evidence. The client
does not infer either representation.

Expression evidence retains its original match ID, lookup form, source rows,
and complete participating-token list. Attaching the evidence to each
participating token is a navigation convenience and never converts it into
separate unigram observations. Lancaster annotation uses the module's recorded
dominant perceptual and action domains as compact markers and exposes the
complete existing dimensional vector in details; it does not invent a new
domain threshold. POS is contextual metadata rather than a competing default
visual encoding.

Layer choices, active lens, selected VAD source, and unmatched-underlining
choice are presentation state. Full saved analyses may restore them, but they
remain outside analytical configuration and have no effect on historical
result identity or recalculation.

## Inherited-form candidate ranking

Inherited Form Analysis is a rule-based candidate-ranking system over 169
versioned, source-documented profiles in registry version 2.0. It is not a
trained classifier. Each profile declares required, preferred, and optional
features with visible weights, expectations, sources, limitations, and an
assessment mode:

- **automatic** means the encoded defining evidence can support a suggestion;
- **partial** means VerseVAD can compare important observable structure while
  explicitly leaving other conventions to interpretation; and
- **manual** means a defining contextual, visual, linguistic, thematic, or
  compositional requirement cannot be responsibly inferred. These profiles
  remain fully selectable but can never become automatic suggestions.

For each available feature, its rule weight is multiplied by its evidence
coverage. Consistency is the weighted mean of the available feature scores;
evidence coverage is the effective available weight divided by total possible
profile weight. Missing pronunciation, meter, rhyme, or syllable evidence has
no score and lowers coverage. It is never converted to mismatch or a neutral
value.

A potential match must meet the configured consistency threshold, overall
coverage minimum, required-feature coverage minimum, and contradiction rule.
Classification—Strict, Strongly conforming, Modified, Form-derived,
Suggestive resemblance, or No inherited-form match—describes conformity.
Confidence—low, moderate, or high—also considers coverage, required-feature
contradictions, and the coverage-adjusted margin over the next automatically
suggestible profile. Neither value is a probability.

Rhyme-scheme comparison balances expected-rhyme and expected-difference
relationships so numerous non-rhyming line pairs cannot overwhelm the
diagnostic rhymes. Exact/perfect and identical evidence receives full credit;
graded slant and eye evidence can receive partial credit. Meter is consumed
from the existing fixed or performance-aware result and is never independently
rescanned.

Suggested candidates expose a tooltip containing the traditional definition
and poem-specific agreements and departures. Complete source URLs,
limitations, weights, detected values, scores, and coverage remain visible in
the evidence table and exports. If nothing qualifies, the concise ranking is
limited to ten nearest profiles. The **All Inherited Forms** selector and full
CSV exports retain all 169 entries, including obviously distant and
manual-confirmation forms. See
[`inherited-form-registry-v2.md`](inherited-form-registry-v2.md) for the
expanded registry policy.
