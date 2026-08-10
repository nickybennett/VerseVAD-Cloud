# VerseVAD Values and Terminology Guide

## Plain-language definitions, formulas, examples, and interpretation

**Software version:** {{VERSION}}  
**Guide updated:** {{DATE}}  
**Intended reader:** A first-time user with no linguistics or statistics background

> THE CENTRAL RULE: VerseVAD describes lexical evidence found in published word-rating and corpus-frequency resources plus offline rule-based sentiment, formula-based readability, optional dictionary-based pronunciation, fixed candidate-meter, separate performance-aware realization, rhyme, recurring-sound, lexical-diversity, word-length, structural word-count, and PoetryID candidate-profile evidence. These constructs are separate from each other. VerseVAD does not discover the emotion of a poem, diagnose a speaker or cognition, recover an author's intention, measure what an individual reader feels, determine actual reader difficulty, or establish definitive meter, performed rhythm, pronunciation, or rhyme.

[[PAGEBREAK]]

# Contents at a Glance

1. The one-minute mental model
2. A safe reading order
3. Valence, arousal, and dominance
4. Original and normalized scales, concreteness, Zipf frequency, Age of Acquisition, readability, dictionary pronunciation, candidate meter, rhyme, recurring sounds, lexical diversity, word length, structural word counts, and PoetryID
5. Tokens, types, phrases, lemmas, and matches
6. Part-of-speech profiles
7. Coverage and unmatched vocabulary
8. Global lexical scopes
9. Token-weighted and type-weighted statistics
10. Means, medians, and dispersion
11. Comparing report profiles
12. Cumulative normative lexical load
13. Top contributors
14. Emotion, sentiment, and emotion intensity
15. Corpus weighting and long works
16. Review decisions and scenarios
17. Worked examples
18. How to report a result
19. Quick-reference glossary

# 1. The One-Minute Mental Model

VerseVAD performs a documented lookup-and-summary procedure:

1. You provide a literary text.
2. VerseVAD preserves that text exactly.
3. It makes a separate processing representation containing tokens, normalized lookup forms, proposed lemmas, and phrase candidates.
4. It looks for those candidates in one or more installed lexicons.
5. A match inherits the value or association published for that lexicon entry.
6. VerseVAD summarizes only included matches and records everything needed to audit the calculation.
7. You interpret those lexical patterns alongside the original text.

A **lexicon** is a structured list of words or phrases with source-supplied ratings or category associations. A lexicon score belongs to the listed lexical entry under the conditions of the source study. It is not a contextual score freshly measured from your poem.

> EXAMPLE: If `storm` has high normative arousal in a selected lexicon, VerseVAD can report high-arousal lexical evidence when `storm` matches. It cannot determine whether the storm is literal, metaphorical, remembered, negated, mocked, or emotionally calming in this particular poem.

# 2. A Safe Reading Order

For every analysis, read the results in this order:

1. **Confirm the text and lexicons.** Make sure you analyzed the intended version and sources.
2. **Read coverage.** Determine how much eligible vocabulary was represented.
3. **Read warnings.** Note sparse evidence, lemma reliance, review exclusions, or other methodological cautions.
4. **Choose one construct.** VAD ratings, emotion associations, sentiment associations, emotion intensities, normative lexical concreteness, corpus-relative lexical frequency, retrospective normative lexical Age of Acquisition, dictionary pronunciation/lexical stress, candidate-meter fit, rhyme/recurring-sound evidence, lexical-style evidence, and PoetryID candidate profiles are different kinds of evidence.
5. **Choose one lexical scope.** All lexical tokens, stopword-excluded, and content words only answer different questions; do not merge them.
6. **Choose one weighting.** Token weighting answers a repetition-sensitive question; type weighting answers a vocabulary-sensitive question.
7. **Inspect dispersion and contributors.** A mean alone can conceal mixed ratings or one repeated influential word.
8. **Inspect the match evidence.** Verify surprising entries, phrases, lemmas, mappings, and unmatched forms in context.
9. **If analyzing a corpus, compare token- and work-weighted collection profiles.**
10. **Report the denominator and method with the result.**

> NEVER REPORT A BARE NUMBER: A result such as `valence = 0.62` is incomplete without the lexicon, scale, lexical scope, weighting, matched count, coverage, and unit of analysis.

## Interface Terms Are Not Analytical Terms

**Analyze**, **Collections**, **Explore**, and **Learn** are top-level
navigation sections. Single Poem, Compare Poems, Other Text, Lexicon Explorer,
Personal Corpus, and Saved Projects are implemented workspaces. **Affective
Evidence**, **Lexical Character**, **Sound & Form**,
**Structure**, **Evidence & Diagnostics**, and **Export & Help** are report
families used for navigation. A collapsed section retains its result.

**Full Poetic Analysis**, **Computational Close Reading**, **Affect and
Emotion**, **Sound and Prosody**, **Formal Analysis**, and
**Teaching/Introductory** are analysis profiles. A profile is not an
interpretive claim; the exact effective settings remain visible and recorded.
A custom profile stores configuration only, never supplied text or results.

**Classic**, **Dark**, **Lavender**, **Ocean**, **Crimson**, and **Forest** are
appearance preferences. They do not change a score, result ID, coverage value,
project, or export. Missing values remain missing in every appearance.

# 3. Valence, Arousal, and Dominance

Valence, arousal, and dominance are often abbreviated **VAD**. They are three separate dimensions. None is a synonym for “emotion.”

## Valence

**Valence** is normative pleasantness versus unpleasantness associated with a lexical item.

| Normalized location | Plain-language orientation |
|---|---|
| Near 0 | More unpleasant in the source norms |
| Near 0.5 | Near the documented scale midpoint |
| Near 1 | More pleasant in the source norms |

Possible interpretation: “The matched vocabulary has above-midpoint mean normative valence.”

Avoid: “The poem is happy.” A poem can use pleasant words ironically, quote them, negate them, or place them in a disturbing context.

## Arousal

**Arousal** is normative activation, alertness, energy, or intensity associated with a lexical item.

| Normalized location | Plain-language orientation |
|---|---|
| Near 0 | Calmer, quieter, or less activated in the source norms |
| Near 0.5 | Near the documented scale midpoint |
| Near 1 | More activated or energetic in the source norms |

Arousal is not the same as positive feeling. A pleasant word and an unpleasant word can both have high arousal.

Possible interpretation: “The included matched tokens have relatively high mean normative arousal.”

Avoid: “The reader becomes excited.” VerseVAD does not measure a reader.

## Dominance

**Dominance** is normative control, power, agency, or being-in-command associated with a lexical item.

| Normalized location | Plain-language orientation |
|---|---|
| Near 0 | Less control, power, or agency in the source norms |
| Near 0.5 | Near the documented scale midpoint |
| Near 1 | Greater control, power, or agency in the source norms |

Dominance does not identify who controls whom in a poem. Syntax, voice, narrative position, and context still require close reading.

Possible interpretation: “The matched vocabulary trends below the dominance midpoint.”

Avoid: “The speaker is powerless.”

## What a VAD Mean Actually Summarizes

A work-level VAD mean is the arithmetic mean of included lexicon ratings under a declared matching policy, lexical scope, and weighting. It describes the center of those matched ratings. It does not summarize words that did not match, and it does not assign unmatched words a neutral value.

## Lexical Trajectory

The **Lexical Trajectory** chart repeats the selected report profile's lookup
logic line by line. Token weighting retains repeated matched occurrences;
type weighting uses one included lexical type per line. It plots valence,
arousal, and dominance from one selected VAD source, plus concreteness when that
resource is available. Original
concreteness values from 1 to 5 are linearly normalized to 0 to 1 for the
overlay only:

`concreteness_overlay = (source_rating - 1) / 4`

A missing point means that line has no matched evidence for that series. It is
not converted to a midpoint or joined as if evidence existed. The chart shows
descriptive lexical movement across physical lines; it does not measure the
speaker's or reader's emotional state.

# 4. Original and Normalized Scales

The installed VAD lexicons use different original scales.

| Source | Original scale | VerseVAD normalized formula |
|---|---|---|
| Warriner VAD 2013 | 1 to 9 | `x_normalized = (x_original - 1) / 8` |
| NRC VAD v1 | 0 to 1 | `x_normalized = x_original` |
| NRC VAD v2.1 | -1 to 1 | `x_normalized = (x_original + 1) / 2` |

Normalization maps each documented minimum to 0, midpoint to 0.5, and maximum to 1. This lets VerseVAD display scales in a common numeric range.

Normalization does **not** prove that two sources are interchangeable. Lexicons may differ in vocabulary, participants, data-collection method, date, wording, and sample. VerseVAD therefore:

- preserves the original source value;
- displays the exact normalization formula;
- reports each lexicon separately;
- does not create a default cross-lexicon consensus score.

NRC VAD v1 and NRC VAD v2.1 are versions of one lexicon family, not fully independent replications.

## Normative Lexical Concreteness

The optional one-poem module uses the Brysbaert, Warriner, and Kuperman (2014) source's original 1-to-5 ratings. It does not normalize them into VAD or combine them with affective evidence.

| Source-scale orientation | Meaning in the source task |
|---|---|
| Near 1 | More abstract or language-based |
| Near 5 | More concrete or experience-based |

VerseVAD reports the token-weighted mean, median, inclusive quartiles, interquartile range, and population standard deviation among rated lexical-token positions. It also reports token and unique normalized-surface-type coverage.

The default lower band at or below 2.0 and upper band at or above 4.0 are configurable VerseVAD orientation aids, not validated categories claimed by the paper. A source-supplied two-word expression receives one audit group, while its rating is assigned to both covered token positions for the declared token-weighted statistics. Repetition therefore matters.

Safe wording: “The matched tokens have a mean normative lexical concreteness of 3.7 on the source 1-5 scale, with 72% token coverage.”

Avoid: “The poem is concrete,” “the imagery succeeds,” or “the reader visualizes the poem.” The rating is a decontextualized lexical norm, not a contextual literary or cognitive measurement.

## SUBTLEX-US Zipf Frequency and Rarity

The optional one-poem frequency module uses published SUBTLEX-US word-form
frequencies from an American subtitle corpus. It does not use `wordfreq`, mix
corpora, or treat an absent form as zero.

A **Zipf value** is logarithmic. Approximately one point represents a tenfold
frequency difference in the source corpus. A value of 5 is therefore about ten
times as frequent as 4 and about one hundred times as frequent as 3, within the
same corpus and counting convention.

VerseVAD emphasizes the token-weighted median because a few extremely common
forms can pull the arithmetic mean upward. It also reports mean, population SD,
inclusive quartiles, IQR, range, coverage, configurable bands, structural/POS
summaries, term rankings, and the token audit.

The default bands are VerseVAD orientation aids:

| Zipf interval | Default display label |
|---|---|
| Below 3 | Rare |
| 3 to below 4 | Uncommon |
| 4 to below 5 | Moderately common |
| 5 to below 6 | Common |
| 6 or above | Very common |

The default scope considers all lexical tokens except model-tagged proper
nouns. The optional **Content words only** scope is off by default and includes
only exact model tags `NOUN`, `VERB`, `ADJ`, and `ADV`. It excludes `DET`,
`ADP`, `CCONJ`, `SCONJ`, `PRON`, `AUX`, punctuation, and all other tags.
This differs from the broad Language Profile, where `VERB` and `AUX` are
grouped together under **Verb** for readability.

Exact normalized observed word form takes priority over an enabled lemma
fallback. This distinction matters because SUBTLEX-US supplies word-form
frequencies. Every lemma or conservative fallback remains labeled in the
audit, and unmatched values remain missing.

Safe wording: “The matched tokens had a median SUBTLEX-US Zipf value of 4.3,
using the content-word-only scope, with 78% token coverage.”

Avoid: “The poem is easy,” “the vocabulary is sophisticated,” or “the reader
will understand it.” Corpus-relative word frequency is not a direct measure of
difficulty, accessibility, intelligence, or literary quality.

## Retrospective Normative Lexical Age of Acquisition

The optional one-poem module uses the official Kuperman,
Stadthagen-Gonzalez, and Brysbaert supplement. A source mean is an adult
retrospective estimate of the age, in years, at which respondents believed
they learned a word well enough to understand it. It is not normalized into
VAD or combined into an affective score.

VerseVAD reports token-weighted mean, median, population SD, inclusive
quartiles, IQR, range, token and unique observed-form-type coverage,
configurable acquisition-orientation bands, source-response evidence,
structural/POS summaries, term rankings, and the token audit.

| Source-age interval | Default display label |
|---|---|
| At or below 5 years | Early-acquired |
| Above 5 and below 12 years | Middle range |
| At or above 12 years | Later-acquired |

These thresholds are configurable VerseVAD orientation aids, not categories
validated by the source paper. A source row with `Rating.Mean = NA` remains
auditable but has no numeric age. Unmatched and ineligible forms also remain
missing rather than becoming age zero.

The paper describes target selection from base forms used most frequently as
nouns, verbs, or adjectives. The official supplement nevertheless has numeric
ratings for polyfunctional spellings such as `the`, `and`, `he`, `of`, and
`to`. The global **Content words only** scope therefore remains meaningful. It
uses the poem occurrence's contextual model tag and includes only `NOUN`,
`VERB`, `ADJ`, and `ADV`.

When Frequency or Concreteness is enabled too, VerseVAD can show a descriptive
Spearman rank relationship after collapsing repetitions to unique paired
normalized surface types. It requires at least three paired types, excludes
multiword concreteness assignments, and does not establish causation.

For matched source ages `a_i` across `A` matched token positions:

`mean_aoa = sum(a_i) / A`

`aoa_token_coverage = matched numeric eligible token positions / eligible token positions`

For each source word:

`numeric_response_proportion = OccurNum / OccurTotal`

Source-response evidence describes the source norm; it does not change the
poem's token weighting.

Safe wording: “The matched tokens had a mean retrospective normative lexical
AoA of 7.2 years, with 83% token coverage.”

Avoid: “The poem is for seven-year-olds,” “the vocabulary is difficult,” or
“the author shows cognitive decline.” Age-of-acquisition results are not
grade-level, comprehension, intelligence, reader-response, or cognitive
diagnostic measures.

## Readability and Grade-Level Formulas

Readability is always available and is calculated locally from preserved word,
sentence, character, and estimated syllable counts. VerseVAD reports Flesch
Reading Ease, Flesch-Kincaid Grade, Gunning Fog, Automated Readability Index,
Coleman-Liau, and SMOG when the formula's requirements are met. SMOG remains
missing below 30 sentences.

These formulas were designed primarily for prose. Line breaks, fragments,
unusual punctuation, and poetic syntax can materially affect their inputs.
Grade-level values are formula outputs, not claims about the education,
intelligence, or actual comprehension of a particular reader.

Syllable counting uses a session pronunciation override first, an installed
dictionary candidate second, and a labeled orthographic estimate only when
neither exists. The report therefore includes pronunciation coverage and a
default-collapsed attention list for estimated words. Contractions such as
`you're` and `can't` count as single readability words.

### VerseVAD Poetic Reading Ease (Experimental)

VV-PRE is a 0-100 transparent composite in which higher scores mean greater
estimated surface-level linguistic accessibility. It does not use sentence
length. The versioned `vv-pre-content-word-profile-1.0` uses token-weighted
content-word occurrences (`NOUN`, `VERB`, `ADJ`, and `ADV`) with repetitions
retained for SUBTLEX Zipf frequency, normative AoA, and estimated syllables per
word. Mean words per nonblank line uses all lexical words. Its positive weighted
formula is 30% frequency ease, 25% AoA ease, 30% line accessibility, and 15%
word-complexity ease. The scoring scope is fixed even when a user changes the
visible Frequency or AoA report settings.

The anchors are: Zipf 2.5 to 6.5, AoA 12 to 4 years, 15 to 3 words per line,
and 2.5 to 1.0 syllables per word, each running from 0 to 100 ease and clamped
outside the range. Missing components are not reweighted. VerseVAD stores the
profile ID, raw inputs, component scopes, normalized components, weights,
anchors, match counts, coverage, and source-result identities with the final
score.

Bands are 85-100 Highly Accessible, 70-84 Accessible, 55-69 Moderately
Demanding, 40-54 Demanding, and 0-39 Highly Demanding. These are declared
experimental orientations, not findings about interpretation, symbolism,
literary merit, actual comprehension, or reader ability.

Evidence confidence is reported separately and never changes the score. High
requires at least 90% coverage across all components and 20 matched Frequency
and AoA token occurrences. Moderate requires 75% coverage and 10 matches.
Otherwise the designation is Limited. This is a transparent evidence-
sufficiency label, not a statistical confidence interval or probability.

## Dictionary Pronunciation, Syllables, and Lexical Stress

The optional pronunciation module uses exact observed-form pronunciations
from pinned official CMUdict files. It is not a rating scale and is not
combined with VAD, emotion, concreteness, frequency, or AoA.

One dictionary candidate resolves directly. Several candidates resolve only
when they agree on syllable count and the full stress sequence. A materially
different alternative remains ambiguous until the scholar documents a
poem-specific ARPAbet override. Out-of-dictionary forms remain missing in the
analysis. **Words Needing Attention** may show a local eSpeak NG US-English
G2P candidate labeled **provisional—not confirmed**, but the form stays
unmatched until the scholar explicitly approves or edits the ARPAbet into a
session-only override. **Leave explicitly unresolved** is the default.

| Stress digit | Dictionary meaning |
|---|---|
| `0` | Unstressed syllable |
| `1` | Primary lexical stress |
| `2` | Secondary lexical stress |

`pronunciation_token_coverage = resolved eligible tokens / eligible lexical tokens`

`complete_line_coverage = complete physical lines / physical lines containing lexical tokens`

`lexical_stress_density = (primary + secondary stressed syllables) / resolved syllables`

A line is complete only when every eligible word resolves. Its syllable total
and stress sequence otherwise remain missing.

Safe wording: “Under the selected override configuration, CMUdict supplied
dictionary syllable and lexical-stress evidence for 92% of eligible token
occurrences; 8 of 10 physical lines were complete.”

Avoid: “The poem is iambic,” “this is the poet's pronunciation,” or “the
performance stresses these syllables.” The module supplies North American
dictionary evidence, not meter, rhyme, or definitive performed scansion.

## Candidate Meter and Fit

The optional candidate-meter module consumes retained pronunciation and stress evidence
without rewriting the pronunciation result. It compares five base patterns:
iambic `01`, trochaic `10`, anapestic `001`, dactylic `100`, and
amphibrachic `010`. Each is checked at one through eight feet (monometer
through octameter), producing 40 fixed line candidates.

A **candidate meter** is the nearest configured fixed stress template. It is
not a definitive classification, correct scansion, or performed rhythm.

Spondees `11` and pyrrhics `00` are local substitutions, not ordinary
whole-line base candidates. The audit can also report initial inversion,
feminine ending, catalexis, and extra or omitted syllables.

For one line and template:

`meter_line_fit = max(0, 1 - selected_alignment_cost / max(observed_syllables, template_syllables, 1))`

`meter_line_coverage = analyzable eligible physical lines / eligible physical lines`

`matching_line_proportion = lines meeting the configured fit threshold / analyzable lines`

Fit is a configured similarity from 0 to 1, not a probability. The
rule-based confidence category uses analyzable-line count, coverage, fit,
candidate margin, and matching-line proportion; it is not a calibrated
probability.

A missing or out-of-dictionary word makes its physical line unscored. It does
not receive fit zero or a partial “known-word” scansion. Materially different
dictionary stress alternatives can be explored as candidate paths, but the
metrically preferred path is not promoted to a dictionary or performance
fact.

Safe wording: “The nearest configured candidate was iambic pentameter, with
mean fit 0.91 across 8 analyzable lines.”

Avoid: “VerseVAD proved the poem is in iambic pentameter,” “fit 0.91 means a
91% probability,” or “this is the poet's intended scansion.”

## Performance-Aware Meter Realization

The performance-aware layer keeps the complete fixed candidate result and adds
an inspectable contextual reading. Built-in profiles display both layers by
default; candidate-only and performance-aware-only modes remain available. It can label syllable-level metrical
positions, promotion and demotion, substitutions, stress clashes and lapses,
punctuation-supported caesurae, selected pronunciation paths, alternate
realizations, stanza recurrence, poem trajectory, and rhythmic organization.
It does not rewrite CMUdict lexical stress or claim to recover a performance.

The scholar explicitly selects General English Verse, Traditional
Accentual-Syllabic Verse, Romantic / Victorian Verse, Modernist Verse,
Contemporary Formal Verse, Free Verse / Cadential, or Custom visible weights.
These are versioned sensitivity profiles, not inferred historical labels.
Summary, Standard, and Detailed change presentation depth.

Each realized reading retains visible components for candidate, contextual,
syllable-count, phrase, line-ending, pronunciation, stanza/poem consistency,
and style compatibility evidence, plus a substitution penalty:

`realization_score = bounded weighted component evidence - visible substitution penalty`

The exact exported weights are part of the configuration. The score ranks
configured readings; it is not a probability or an independently validated
likelihood. Strong, moderate, tentative, ambiguous, and insufficient labels
are rule-based descriptions.

Visibly marked contraction recognition is off by default. Unmarked syllables
are never silently elided. A scholar may record a separate revision with a
line number, fixed candidate, visible scansion, and note; the automatic reading
remains unchanged.

Safe wording: "Under the scholar-selected General English Verse profile, the
optional realization layer ranked an iambic pentameter reading first and
reported two local promotions; the fixed candidate and dictionary stress audit
remain available."

Avoid: "VerseVAD discovered the correct scansion," "the poem is historically
Modernist because that profile scored highest," or "the performer stresses
these syllables."

## Rhyme and Recurring Phonological Patterns

The optional rhyme and recurring-sound module consumes retained phones and
stress without rewriting the pronunciation result. CMUdict supplies the
dictionary evidence; VerseVAD derives the classifications.

Exact whole-poem and stanza schemes use robust perfect or identical rhyme
parts. Letters identify exact groups, `x` identifies an analyzable ungrouped
ending, and `?` identifies an unresolved ending. Slant and eye rhyme remain
separate.

`ending_coverage = analyzable eligible line endings / eligible line endings`

`rhyme_density = analyzable line endings in an exact within-stanza pair / analyzable line endings`

`slant_similarity = 0.35(stressed_vowel) + 0.25(final_consonants) + 0.25(rhyme_part_edit) + 0.10(stress_alignment) + 0.05(syllable_similarity)`

The default slant threshold is `0.68`. The conservative minimum across retained
pronunciation combinations controls the label; the maximum is also reported.
This is a configurable heuristic, not a probability.

The module also reports perfect, identical, masculine, feminine, multisyllabic,
eye, and internal-rhyme evidence; exact repeated-line refrains; phonemic
alliteration from repeated initial consonants; assonance from repeated stressed
vowels; and consonance from repeated consonants.

Safe wording: “The dictionary-based ending evidence produced an ABAB exact-
rhyme scheme among four analyzable endings.”

Avoid: “VerseVAD proved these words rhyme in every dialect,” “the slant score
is a probability,” or “this sound pattern proves the poet's intention.”

## Lexical Diversity, Word Length, and Structural Word Counts

The optional one-poem lexical-style module uses the shared tokenizer but does
not depend on an external lexicon. Its lexical-style word unit is an eligible
lexical token represented by its normalized observed surface form. It never
silently substitutes a lemma for diversity counting.

Plain type-token ratio is:

`TTR = distinct normalized observed forms / normalized observed-form tokens`

Because plain TTR changes strongly with sample length, VerseVAD also reports:

- **MATTR**, the mean TTR across every overlapping window of a configured size;
- **HD-D**, the expected distinct-type proportion in a configured
  without-replacement sample;
- **MTLD**, the mean of forward and reverse sequential factor-length estimates
  at a configured TTR threshold.

`MATTR(w) = mean(TTR of every overlapping w-token window)`

For type frequency `f`, text length `N`, and sample size `s`:

`P(type observed) = 1 - C(N - f, s) / C(N, s)`

`HD-D = sum(P(type observed) for each type) / s`

Defaults are MATTR window 50, HD-D sample 42, and MTLD threshold 0.72. MATTR
and HD-D remain missing when the text is shorter than their configured
denominator. Undefined MTLD remains missing. These missing values are not
converted to zero.

Word length is the count of Unicode alphabetic characters in the preserved
surface token. Internal apostrophes and hyphens therefore do not add
characters. Physical blank lines remain in the line table with word count
zero. Stanzas are nonblank line blocks separated by one or more blank lines;
consecutive blank lines do not create empty stanzas.

Safe wording: “Using normalized observed surface forms and a 50-token MATTR
window, the text had MATTR 0.74 across 181 eligible lexical tokens.”

Avoid: “The poem has a vocabulary richness of 74%,” comparisons made under
different settings, or treating line and stanza word counts as interpretations
of poetic form.

## PoetryID Candidate Lexical-Affective Profiles

PoetryID is a dependent interpretation layer over a completed normalized VAD
summary. It does not tokenize the poem, load a VAD lexicon, match words, or
calculate VAD again. Every result names its exact VAD source, lexical scope,
aggregation weighting, thresholds, and upstream
analysis.

Each normalized dimension is classified as low, moderate, or high. Under the
default fixed profile:

- low means `score <= 0.40`;
- high means `score >= 0.60`;
- moderate means the score lies between those boundaries.

Three dimensions with three levels produce `3 x 3 x 3 = 27` canonical
candidate profiles. Custom fixed boundaries are available. Corpus-tertile and
z-score boundaries are not implemented.

PoetryID also retains continuous evidence. For VAD point `(V, A, D)` and
candidate centroid `(Vc, Ac, Dc)`:

`distance = sqrt((V - Vc)^2 + (A - Ac)^2 + (D - Dc)^2)`

All 27 distances remain available. Inverse-distance similarities are
normalized across the 27 profiles for comparison. These **relative
affinities are not probabilities**.

The categorical profile and nearest continuous centroid may differ near a
boundary. PoetryID preserves both. Its confidence label considers distance,
neighbor margin, threshold proximity, agreement, and coverage; it is a
rule-based evidence label, not a calibrated probability.

Optional concreteness, SUBTLEX-US Zipf frequency, and AoA character uses
already completed module summaries on their native scales. It never changes
the VAD profile.

Safe wording: "Under the default fixed thresholds, the token-weighted NRC VAD
v1 evidence was nearest categorically to The Survivor profile, with low
valence, moderate arousal, and high dominance."

Avoid: "The poem is a Survivor," "the speaker feels defiant endurance," or
"the affinity is the probability that this is the poem's emotion."

# 5. Tokens, Types, Phrases, Lemmas, and Matches

## Token

A **token** is one occurrence in the text. In `dark dark night`, there are three lexical token occurrences: two occurrences of `dark` and one of `night`.

## Type

A **type** is one distinct matched lexicon entry within the declared unit of analysis. If both occurrences of `dark` match the same entry, `dark` contributes two tokens but one type.

## Surface Form

The **surface form** is what appears in the preserved text, such as `burning`.

## Normalized Form

The **normalized form** is a separate lookup representation produced by documented rules. It never replaces the original text.

## Lemma

A **lemma** is a model-proposed base form conditioned on part of speech, such as `burning -> burn`. VerseVAD tries a lemma only after the eligible exact candidates fail. A lemma-derived match is labeled because the proposal may be wrong for poetic, historical, ambiguous, or unusual language.

## Phrase

A **phrase match** links a multi-token span such as `broken heart` to one source entry. Under the recommended longest-phrase policy, the phrase contributes one observation and covered component candidates are suppressed but retained in the audit.

## Exact, Lemma-Derived, and Approved-Mapping Matches

| Match method | Meaning |
|---|---|
| Exact word | The normalized surface form directly matched a source entry |
| Exact phrase | The accepted multiword span directly matched a source entry |
| Possessive or apostrophe normalization | A conservative documented normalization matched |
| Lemma-derived | The model-proposed lemma matched only after exact candidates failed |
| Approved user mapping | A scenario-pinned review decision mapped the form to a verified exact source entry |

An approved mapping is not a published claim that the two forms are equivalent. It is a scholar-authored methodological decision, recorded with scope, rationale, revision, and scenario version.

# 6. Part-of-Speech Profiles

A **part of speech** is a grammatical category such as noun, verb, adjective, or adverb. VerseVAD uses the installed English linguistic model's universal POS labels.

The **Language Profile** is deliberately independent of the affective lexicons. Its denominator is every eligible lexical token, not only tokens that found a VAD or emotion entry.

VerseVAD reports two defensible levels:

- **Broad Categories** provide the readable quantity/share profile requested
  for interpretation.
- **Detailed Model Tags** preserve the installed model's Universal
  Dependencies distinctions and their separate counts and shares.

The broad and detailed shares each sum to 100 percent apart from rounding.
They are two aggregations of the same token occurrences and must not be added
together.

`POS_share_c = token occurrences assigned to category c / all eligible lexical token occurrences`

For each category, VerseVAD reports:

- the source POS tag or merged source tags;
- a plain-language category label;
- token count;
- share of all eligible lexical tokens;
- number of unique normalized types;
- example forms;
- the lexical-token denominator.

Common tags include:

| Source tag(s) | Plain-language category |
|---|---|
| NOUN + PROPN | Noun; common and proper nouns are combined |
| VERB + AUX | Verb; main, auxiliary, and copular uses are combined |
| ADJ | Adjective |
| ADV | Adverb |
| PRON | Pronoun |
| DET | Determiner |
| ADP | Preposition |
| CCONJ | Coordinating conjunction |
| SCONJ | Subordinating conjunction |
| PART | Particle |
| INTJ | Interjection |
| NUM | Numeral |
| X | Other or uncertain |

In a one-poem result, shares use that poem's lexical-token count. In the corpus **All Works Combined** profile, counts are pooled across current work versions, so longer works contribute more. The work-by-work table uses each work's own denominator and is usually better for comparing relative grammatical composition across differently sized works.

Part-of-speech assignments are model-generated rather than lexicon-published. Poetic syntax, fragments, archaisms, unusual capitalization, and deliberate ambiguity can cause errors. Inspect token evidence when a category distinction matters to the argument.

VerseVAD intentionally merges the model's `NOUN` and `PROPN` tags into one
displayed **Noun** category. Capitalization is unusually variable in poetry,
and the common/proper distinction is not necessary for the requested
quantity/share profile. The original source tag remains available in
the detailed model-tag table, token-level evidence, and audit data.

VerseVAD also merges `VERB` and `AUX` into one displayed **Verb** category.
Forms of `be`, such as `was`, may receive `AUX` when they function as an
auxiliary or copula; they are still verbs in the beginner-facing quantity/share
profile. The original tag remains in token evidence.
The detailed model-tag table still reports `VERB` and `AUX` separately.

The global **Content words only** report scope uses a narrower rule than this
broad display. It includes exact tags `NOUN`, `VERB`, `ADJ`, and `ADV` only;
`AUX` and `PROPN` are not automatically included. Always report which scope
was used.

## VAD by part of speech

In one-text results, the Language Profile can add VAD evidence to the broad
POS groups without changing the grammatical count/share denominator. Results
remain separate for every VAD source and selected global lexical scope.

The **token-weighted POS mean** counts every included matched occurrence in
the group. The **type-weighted POS mean** counts each distinct matched lexicon
entry once within that source, scope, and group. Repetition can therefore make
the two means differ. Both are normative lexical VAD means, not measurements
of the emotion of the grammatical category or poem.

Only matched evidence enters either mean. Unmatched tokens remain missing,
never 0 or neutral. An accepted published phrase contributes one observation.
If its lexical components cross broad POS groups, VerseVAD reports it under
**Mixed-POS Phrase** rather than assigning the rating to one category. That
span-based row has no grammatical token-coverage denominator. Every ordinary
POS row reports its matched and eligible token occurrences, coverage, and
sparse-evidence status.

# 7. Coverage and Unmatched Vocabulary

**Coverage** asks how much eligible vocabulary was represented by the selected lexicon under the declared policy.

`coverage = matched eligible lexical token positions / eligible lexical token positions`

Coverage is not:

- an accuracy score;
- the proportion of the poem that is emotional;
- the proportion of words the software understands;
- evidence that a high-coverage lexicon is universally better.

Report both the percentage and its counts. `80% coverage (80 of 100 eligible lexical token positions)` is more informative than `80%`.

## Unmatched

An **unmatched** token received no accepted entry. Its rating remains missing. VerseVAD never gives it 0, 0.5, the work mean, or an automatically guessed synonym.

Unmatched vocabulary is a quality-control resource. It can reveal:

- spelling or OCR problems;
- contractions and archaic forms;
- names and places;
- specialist vocabulary;
- poetic compounds;
- inflections missed by lemmatization;
- genuine limits in source coverage.

## Review Exclusions and Coverage

A review exclusion says that a published candidate should not contribute to a chosen scenario. The candidate remains auditable. Primary coverage can still identify it as published lexical evidence while separately reporting that the review scenario excluded it from aggregation. Always read coverage together with review-exclusion counts.

# 8. Global Lexical Scopes

## Stopword

A **stopword** is a form selected for exclusion from the recorded
stopword-excluded scope. Examples in general-purpose lists can include
articles, prepositions, pronouns, auxiliaries, and conjunctions.

“Stopword” does not mean meaningless. Function words can be central to rhythm,
voice, negation, syntax, deixis, and style. VerseVAD therefore retains evidence
once and supports three report scopes: **All lexical tokens**,
**Stopword-excluded**, and **Content words only** (`NOUN`, `VERB`, `ADJ`, and
`ADV`). Scope changes do not repeat tokenization or lookup.

## Protected Words

VerseVAD protects a documented set of negations, modals, comparatives, and intensifiers from default exclusion. Examples include `not`, `never`, `no`, `without`, `might`, `more`, `most`, `too`, and `very`.

## Custom Stopword

A **custom stopword** is a word the user deliberately adds to the active
stopword list for a specific analytical purpose. For example, adding `raven`
would exclude it from the stopword-excluded aggregate while preserving it in
the all-lexical result and audit.

This is a methodological decision, not a declaration that the word is universally unimportant.

## Scope-Relative Coverage

`coverage = matched eligible positions / eligible positions in the selected scope`

Excluded stopwords and excluded non-content words are outside the selected
denominator and are not unmatched. A complete matched expression is preserved
when it intersects the selected scope.

# 9. Token-Weighted and Type-Weighted Statistics

## Token-Weighted

In a **token-weighted** statistic, every included occurrence contributes.

`mean_token = sum(x_i) / N`

where `x_i` is the rating of included occurrence `i` and `N` is the number of included matched observations.

Question answered: “What affective ratings does a reader encounter across the matched words and accepted phrases, including repetition?”

Use token weighting when repetition and textual exposure matter.

## Type-Weighted

In a **type-weighted** statistic, every distinct matched lexicon entry contributes once.

`mean_type = sum(x_t) / T`

where `x_t` is the rating for distinct matched entry `t` and `T` is the number of distinct included matched entries.

Question answered: “What is the profile of the distinct matched vocabulary inventory if repeated entries count only once?”

Use type weighting to reduce the influence of repetition.

## Interpreting Their Difference

If token- and type-weighted means are close, repetition changes the reported center little. If they diverge, repeated entries shift the token-weighted profile away from the distinct-vocabulary profile.

Neither weighting is automatically superior. They answer different questions and should be named explicitly.

# 10. Means, Medians, and Dispersion

## Mean

The **mean** is the arithmetic average of the included values.

`mean = sum(values) / number_of_values`

A mean identifies a center. It does not show whether the values cluster tightly or contain strong values on both sides.

## Median

The **median** is the middle value after sorting. For an even number of values, it is the mean of the two middle values. It is less sensitive than the mean to a small number of extreme values.

For concreteness, VerseVAD applies the same mean and median definitions to the
source 1-5 ratings assigned to included lexical-token positions. Empty or
wholly unmatched inputs have missing aggregates, never a neutral midpoint.

## Dispersion of Matched Ratings

**Dispersion** describes how spread out the included matched ratings are around their center.

VerseVAD reports **population standard deviation** for the complete selected matched set:

`SD_population = sqrt(sum((x_i - mean)^2) / N)`

A standard deviation near 0 means the included ratings are tightly clustered. A larger standard deviation means they are more dispersed.

On the normalized 0-to-1 scale, possible population SD values are bounded, but there is no universal literary threshold for “small” or “large.” Compare like with like: same construct, lexicon, scale, view, weighting, and unit of analysis.

## What Dispersion Does Not Mean

Work-level dispersion is not:

- the uncertainty of the work mean;
- a confidence interval;
- statistical significance;
- disagreement among lexicon raters;
- ambiguity in the poem.

Lexicon Explorer may show a **source-provided standard deviation** for one Warriner entry. That value describes participant variation around that entry's source mean. It is a different quantity from dispersion across the matched entries in one poem.

# 11. Comparing Report Profiles

VerseVAD presents selected scope/weighting combinations directly rather than
adding a redundant sensitivity score. A researcher may calculate a contrast
from two explicitly named rows:

`profile difference = comparison profile value - reference profile value`

The sign indicates direction. There is no universal threshold at which such a
difference becomes robust, significant, or important. The same lexicon,
metric, scale, phrase policy, and other settings must be held constant.

# 12. Cumulative Normative Lexical Load

**Cumulative normative lexical load** is VerseVAD's family of explicitly
defined length- and repetition-sensitive sums. It is not generated for every
numeric variable. VAD uses midpoint-relative loads, emotion intensity uses the
raw sum of supplied intensity scores, and sensorimotor dimensions use their
documented source-scale accumulation. VerseVAD does not report generic
cumulative loads for AoA, Zipf frequency, concreteness, or word length.

The word **load** here means an accumulated numeric total. It does not mean experimentally measured cognitive load, emotional burden, or effect on a reader.

Let `x_i` be an included normalized rating and let the normalized midpoint be 0.5.

## Above-Midpoint Load

`above = sum(max(x_i - 0.5, 0))`

This adds only distances above the midpoint. Values at or below 0.5 contribute zero.

For valence, it summarizes accumulated above-midpoint pleasantness ratings. For arousal, it summarizes accumulated above-midpoint activation ratings. For dominance, it summarizes accumulated above-midpoint control or agency ratings.

## Below-Midpoint Load

`below = sum(max(0.5 - x_i, 0))`

This adds only distances below the midpoint and reports the amount as a positive magnitude. Values at or above 0.5 contribute zero.

For valence, it summarizes accumulated below-midpoint unpleasantness distance. For arousal, it summarizes accumulated below-midpoint calmness or lower activation distance. For dominance, it summarizes accumulated below-midpoint lower control or agency distance.

## Net Midpoint Load

`net = above - below = sum(x_i - 0.5)`

Positive net load means above-midpoint distances outweigh below-midpoint distances. Negative net load means below-midpoint distances outweigh above-midpoint distances. A value near zero can mean ratings cluster near 0.5, or that strong positive and negative distances cancel. Read it with absolute load and dispersion.

## Absolute Midpoint Load

`absolute = above + below = sum(abs(x_i - 0.5))`

Absolute load adds distance from the midpoint regardless of direction. A larger value means more accumulated off-midpoint lexical evidence, produced by text length, repetition, stronger distances, or some combination.

## How to Compare Cumulative Loads

Use cumulative loads when length and repetition are part of the research question. For works of radically different lengths:

- report matched observations or lexical-token count;
- do not treat a larger load as automatically more intense;
- compare means alongside cumulative totals;
- consider a per-token statistic if the question requires length adjustment;
- compare the same lexicon, dimension, view, and matching policy.

## Midpoint Deviation per Matched Token or Type

VerseVAD divides the directional midpoint loads by the included matched
token-occurrence count under token weighting or matched lexical-type count
under type weighting when the research question requires comparison across
differently sized poems:

`midpoint_deviation_per_match = midpoint_load / N`

The **per 100 matched tokens/types** value is exactly
`100 * midpoint_deviation_per_match`.
It is the same rate on a more readable scale. It does not add information and
should not be interpreted as a separate measure.

## Average Deviation from Poem Mean

**Average Deviation from Poem Mean** is the mean absolute deviation (MAD) of
the included ratings around that poem's own mean:

`MAD = sum(abs(x_i - mean)) / N`

MAD and population standard deviation are both length-neutral measures of
within-poem lexical dispersion, but they are not duplicates. MAD weights every
departure linearly and gives the typical absolute distance from the poem mean.
Population SD squares departures and is therefore more sensitive to unusually
distant ratings. Midpoint-deviation rates answer a different question again:
they measure distance from the fixed normalized midpoint `0.5`, not from the
poem's own center.

Neither MAD nor population SD preserves token or line order. A poem can have
high dispersion without alternating between high and low ratings in sequence.
Use Lexical Trajectory to inspect where shifts occur.

# 13. Top Contributors

Top contributors identify distinct matched entries that pull a token-weighted mean above or below the normalized midpoint.

`contribution_t = frequency_t * (rating_t - 0.5)`

| Contribution | Meaning |
|---|---|
| Positive | The entry contributes above the midpoint |
| Negative | The entry contributes below the midpoint |
| Larger absolute value | Greater combination of repetition and midpoint distance |

A contributor can rank highly because it is repeated, because its rating is far from 0.5, or both.

VerseVAD also retains a leave-one-type-out effect:

`effect_t = mean_token - mean_without_all_occurrences_of_t`

This describes how much the reported token mean changes if every occurrence of that matched type is omitted. It is descriptive and is not a causal effect.

# 14. Emotion, Sentiment, and Emotion Intensity

## Eight Emotion Associations

NRC Emotion provides binary associations for:

- anger;
- anticipation;
- disgust;
- fear;
- joy;
- sadness;
- surprise;
- trust.

An association means the source marks the entry as associated with that category. It is not a probability, intensity, or contextual diagnosis.

`emotion_rate = associated token occurrences / eligible lexical tokens`

One entry can carry several associations, so the eight rates do not need to sum to 100 percent.

## Positive and Negative Sentiment Associations

Positive and negative are broad **sentiment** labels in NRC Emotion. VerseVAD reports them in a separate section from the eight emotion categories.

They use the same occurrence-counting logic:

`sentiment_rate = associated token occurrences / eligible lexical tokens`

Positive and negative are not endpoints of the VAD valence scale, and they are not replacements for the eight emotions. A source entry can have multiple labels; rates need not sum to 100 percent.

## VADER Rule-Based Polarity

VADER is a separate, always-available rule-based sentiment model. It reports
positive, neutral, and negative proportions that sum to approximately 1, plus
a rule-adjusted **compound score** from -1 to 1. VerseVAD labels compound scores
at or above 0.05 positive, at or below -0.05 negative, and values between those
thresholds neutral.

The proportions summarize lexical-polarity allocation; the compound score also
uses VADER's word-order, punctuation, capitalization, negation, and modifier
rules. VADER was developed for social-media sentiment, so poetic ambiguity,
irony, lineation, historical usage, and figurative language may be misread.
Treat the result as one contextualized rule-based signal, not an emotional
diagnosis or a substitute for VAD or NRC emotion evidence.

## Emotion Intensity

NRC Emotion Intensity provides numeric values only for particular word-emotion pairs.

**Prevalence** asks how often supplied pairs occur:

`prevalence = matched pair occurrences / eligible lexical tokens`

**Token-weighted mean intensity** averages the supplied values across matched occurrences:

`intensity_mean_token = sum(pair intensity for each occurrence) / matched pair occurrences`

**Type-weighted mean intensity** averages distinct entry-category pairs once:

`intensity_mean_type = sum(distinct supplied pair intensities) / distinct matched pairs`

An absent word-emotion pair is missing. VerseVAD does not turn absence into zero intensity.

# 15. Corpus Weighting and Long Works

Corpus collections can contain radically different work lengths. VerseVAD therefore reports two collection profiles.

## Token-Weighted Collection Profile

Every included matched observation receives equal weight. Long works contribute more because they contain more of the analyzed volume.

For eligible work `i`, let `m_i` be its token-weighted mean and `n_i` its included matched count:

`mean_collection_token = sum(m_i * n_i) / sum(n_i)`

Question answered: “What matched affective vocabulary does a reader encounter across all included observations in this collection?”

## Work-Weighted Collection Profile

Every eligible work-level token mean receives equal weight:

`mean_collection_work = sum(m_i) / K`

where `K` is the number of works with a nonmissing eligible score.

Question answered: “What is the average work-level profile when each work contributes equally?”

## Divergence

`divergence = mean_collection_work - mean_collection_token`

A divergence shows that work length changes the collection-level result. Report both profiles for mixed-length collections. Works without an eligible score remain missing and are counted; they are never assigned 0.5.

## Additional-module collection summaries

For concreteness, Frequency, AoA, pronunciation, meter, rhyme/sound,
lexical-style, and PoetryID corpus results, VerseVAD groups only matching
module versions, configuration IDs, metric IDs, units, scope IDs, and
weightings.

An **equal-work module mean** gives each eligible work value one vote. An
**observation-weighted module mean** appears only when every included work has
a defensible count for that exact metric. It is not supplied for medians,
dispersion, rhyme schemes, categorical candidates, MATTR, HD-D, or MTLD.

**Ordered pooled-token lexical diversity** is a separate calculation. VerseVAD
concatenates stored included normalized-surface tokens in stable work order and
recalculates TTR, MATTR, HD-D, and MTLD under one configuration. It does not
average work-level diversity values and call that pooled.

PoetryID profile prevalence is calculated only within one compatible VAD
source, lexical scope, weighting, and threshold configuration. Its map counts,
continuous work positions, and token/type differences do not create one
corpus-wide emotional identity.

Lexicon Explorer's additional concreteness, SUBTLEX-US, AoA, pronunciation,
syllable, and stress fields remain source or dictionary evidence. **Unmatched**
means the available resource has no accepted entry. **Resource unavailable**
means the expected local source could not be validated. **Source unrated**
means a source row exists but its numeric rating is missing.

# 16. Review Decisions and Scenarios

Review scenarios let a scholar document and test explicit alternatives without overwriting the baseline.

## Flag

A **flag** marks an occurrence or form for attention. It does not change matching or scores.

## Exclude

An **exclude** decision preserves the candidate in the audit but prevents it from contributing to the selected scenario's aggregate.

## Map

A **map** decision maps a source form to a verified exact entry in one installed lexicon. Mapping occurs only after exact, possessive/apostrophe, and lemma candidates fail. It is labeled `approved_user_mapping`.

## Scope

| Scope | Where the decision applies |
|---|---|
| Occurrence | One recorded token position in one preserved text version |
| Work | Eligible occurrences in the selected preserved work |
| Project | Eligible occurrences across works in the selected project |
| Global within scenario use | Eligible occurrences wherever that scenario is evaluated |

Broader scope carries greater methodological risk. Use the narrowest defensible scope.

## Scenario

A **review scenario** is a named, versioned set of decision revisions. A scenario version is pinned to an analysis run. Editing, revoking, restoring, or restoring an older snapshot creates a new version; it does not rewrite a completed run.

## Safe Review Workflow

1. Run an unreviewed baseline.
2. Open **Review & Scenarios**.
3. Create a clearly named scenario.
4. Inspect the evidence, context, match method, lexicon, and candidate risk.
5. Choose flag, exclude, or map.
6. Use the narrowest defensible scope.
7. Write a rationale another scholar could evaluate.
8. Rerun the corpus with that exact scenario version.
9. Compare the new immutable batch with the baseline.
10. Export the workbook and retain the **Review Decisions** sheet and methodology.

An unmatched-note proposal is documentation only. Only an active, scenario-pinned mapping decision changes an analysis.

# 17. Worked Examples

## Example A: Token and Type Weighting

Suppose a text has these included normalized valence matches:

`bright = 0.8, bright = 0.8, dark = 0.2`

Token-weighted mean:

`(0.8 + 0.8 + 0.2) / 3 = 0.6`

Type-weighted mean:

`(0.8 + 0.2) / 2 = 0.5`

Interpretation: repetition of `bright` shifts the occurrence-sensitive token mean above the distinct-vocabulary mean.

## Example B: Dispersion

For the token values `0.8, 0.8, 0.2`, the token mean is `0.6`.

`SD = sqrt(((0.8 - 0.6)^2 + (0.8 - 0.6)^2 + (0.2 - 0.6)^2) / 3)`

`SD = sqrt((0.04 + 0.04 + 0.16) / 3) = sqrt(0.08) = approximately 0.283`

Interpretation: the matched values are meaningfully spread around the mean in this small synthetic example. Do not treat `0.283` as an uncertainty estimate.

## Example C: Cumulative Load

For `0.8, 0.8, 0.2`:

`rating_total = 1.8`

`above = (0.8 - 0.5) + (0.8 - 0.5) = 0.6`

`below = (0.5 - 0.2) = 0.3`

`net = 0.6 - 0.3 = 0.3`

`absolute = 0.6 + 0.3 = 0.9`

Interpretation: above-midpoint distance outweighs below-midpoint distance by 0.3, while total off-midpoint distance is 0.9. The numbers are lexical sums, not a measured reader response.

## Example D: Comparing Lexical Scopes

Suppose All lexical tokens / Token-weighted arousal is `0.48` and Stopword-excluded / Token-weighted arousal is `0.54`.

`scope difference = 0.54 - 0.48 = +0.06`

Interpretation: under this recorded stopword policy, the stopword-excluded
arousal mean is 0.06 higher on the normalized scale. This is a researcher-made
contrast between two report profiles, not a separate VerseVAD metric or an
inferential test.

## Example E: Corpus Weighting

One long work has 100 included matches and mean valence `0.70`. One short work has 10 included matches and mean valence `0.30`.

`token-weighted collection mean = ((100 * 0.70) + (10 * 0.30)) / 110 = approximately 0.664`

`work-weighted collection mean = (0.70 + 0.30) / 2 = 0.50`

Interpretation: the long work dominates the token-weighted profile. The work-weighted profile gives both works one vote. The difference is part of the finding.

## Example F: What a Complete Interpretation Looks Like

Better report:

“Using NRC VAD v2.1 on the normalized 0-to-1 scale, the All lexical tokens / Token-weighted mean normative valence was 0.61 across 84 included observations, with 78% lexical-token coverage. The All lexical tokens / Type-weighted mean was 0.54, indicating that repetition shifted the occurrence-sensitive profile upward. Population SD was 0.19. The largest above-midpoint contributors were `bright` and `love`; the strongest below-midpoint contributor was `death`. These are normative lexical patterns rather than a determination of the poem's emotional state.”

Incomplete report:

“The poem's valence is 0.61, so it is positive.”

## Example G: Zipf Frequency and Scope

Suppose the matched token Zipf values are `2, 4, 4, 5, 6`.

`median = 4`

`mean = (2 + 4 + 4 + 5 + 6) / 5 = 4.2`

Interpretation: the represented token occurrences center at Zipf 4 in
SUBTLEX-US, while the very common form pulls the mean slightly higher. Report
coverage and whether the default or content-word-only scope supplied the
denominator. Do not infer that the poem has a particular reading level.

## Example H: Age of Acquisition and Missing Values

Suppose the matched source mean ages are `3, 3, 8, 8, 14`, and one additional
eligible token is unmatched.

`mean = (3 + 3 + 8 + 8 + 14) / 5 = 7.2 years`

`median = 8 years`

`token coverage = 5 / 6 = approximately 83.3%`

Using the default bands, two matched occurrences are early-acquired, two are
in the middle range, and one is later-acquired. The unmatched token does not
receive age zero and does not enter the mean. Report whether the default or
contextual content-word-only scope supplied the denominator.

Interpretation: the represented token occurrences have a mean retrospective
normative lexical AoA of 7.2 years in the source ratings. This is not a claim
about the text's grade level, reader difficulty, or anyone's cognition.

## Example I: Pronunciation Alternatives and Complete Lines

Suppose an invented dictionary gives `stone` one pronunciation with one
syllable and stress `1`; gives `wind` two different phone strings that both
have one syllable and stress `1`; gives `permit` alternatives with stress
`01` and `12`; and gives `rings` one syllable with stress `1`.

```text
stone wind
permit rings
```

The first line resolves as 2 syllables and `1 | 1`. `wind` has a prosodic
consensus even though both phone strings remain visible. The second line is
incomplete because `permit` has materially different stress alternatives, so
its line total and sequence remain missing.

If the scholar documents:

```text
permit = P ER0 M IH1 T | verb reading in this line
```

the second line resolves as 3 syllables and `01 | 1`. The override is not a
probability or a change to CMUdict; it is an explicit, reversible analysis
decision with a rationale.

## Example J: Exact, Slant, and Eye-Rhyme Evidence

Suppose an invented four-line stanza ends:

```text
cat
night
hat
bright
```

The retained dictionary rhyme parts for `cat/hat` agree, as do those for
`night/bright`, so the exact scheme is `ABAB`. Both pairs are masculine
perfect-rhyme evidence. If a later pair such as `sit/seat` reaches the
configured slant threshold, it is labeled as graded slant evidence but does not
create an exact scheme group. If `love/move` shares spelling evidence but not
an exact pronunciation rhyme part, it is labeled as eye rhyme separately.

Interpretation: the local dictionary and spelling evidence supports an ABAB
exact-rhyme scheme plus separately labeled graded or orthographic
relationships. The result does not establish every dialect, performed reading,
perceptual effect, or authorial intention.

## Example K: Lexical Diversity and Structural Word Counts

Suppose the preserved text is:

```text
red blue red
green blue

yellow red
```

The lexical-style token sequence has 7 normalized observed surface-form tokens
and 4 types. Therefore:

`TTR = 4 / 7 = approximately 0.571`

With an intentionally small three-token MATTR window for this worked example,
the five window TTR values are `2/3, 1, 1, 1, 1`, so:

`MATTR(3) = 14 / 15 = approximately 0.933`

With HD-D sample size 3:

`HD-D(3) = 86 / 105 = approximately 0.819`

Alphabetic word lengths are `3, 4, 3, 5, 4, 6, 3`, giving mean and median word
length 4. Line word counts are `3, 2, 0, 2`; stanza word counts are `5, 2`.
The blank line remains visible with count zero and separates the two stanzas.

Interpretation: these are explicit lexical-form and structural counts under the
recorded settings. The deliberately short MATTR and HD-D denominators make the
arithmetic inspectable; compare real analyses only when their configurations
and token policies agree.

# 18. How to Report a Result

Include these elements for every numeric claim:

- text, work, or collection being analyzed;
- exact lexicon or research resource and version;
- original or normalized scale;
- construct: VAD, emotion association, sentiment association, emotion intensity, normative lexical concreteness, corpus-relative lexical frequency, retrospective normative lexical Age of Acquisition, dictionary pronunciation/syllable/lexical-stress evidence, or candidate-meter fit;
- lexical scope when applicable: all lexical tokens, stopword-excluded, or
  content words only;
- weighting: token, type, token-weighted collection, or work-weighted collection;
- phrase policy when relevant;
- report-profile scope and weighting for every compatible lexical metric;
- pronunciation override configuration and complete-line denominator when relevant;
- meter configuration, nearest-candidate kind, analyzable-line denominator,
  and fit threshold when relevant;
- rhyme/sound configuration, analyzable-ending denominator, scheme notation,
  and slant threshold when relevant;
- lexical-style word unit, MATTR window, HD-D sample size, MTLD threshold, and
  eligible token denominator when relevant;
- matched observations or relevant denominator;
- coverage;
- scenario name and exact scenario version if reviewed;
- statistic and value;
- dispersion when relevant;
- influential contributors or unmatched limitations;
- a lexical-evidence caution.

## Reporting Template

“Using **[lexicon or resource and version]**, **[text or collection]** had
**[statistic] = [value]** for **[construct/dimension]** on the **[scale]**,
using **[lexical scope or fixed profile]** and **[weighting when applicable]**
across **[matched count/denominator]**, with **[coverage]** coverage.
**[Dispersion, contributors, response evidence, profile contrast, PoetryID
boundary/neighbor evidence, or corpus divergence]**. The result describes
matched lexical evidence and is interpreted alongside the text.”

# 19. Quick-Reference Glossary

| Term | Plain-language meaning in VerseVAD |
|---|---|
| Affective lexicon | A source list connecting words or phrases to ratings or associations |
| Age of Acquisition rating | Adult retrospective source estimate, in years, of when a listed word was learned well enough to understand |
| Analysis run | One immutable calculation tied to exact inputs and methods |
| Lexical scope | All lexical tokens, stopword-excluded, or content words only |
| Additional module result | Generic persisted result from the VADER, readability, concreteness, frequency, AoA, pronunciation, meter, rhyme/sound, lexical-style, or PoetryID engine |
| AoA orientation band | Configurable early/middle/later VerseVAD display aid, not a source-validated category |
| Arousal | Normative activation or energy associated with a lexical item |
| Association | Binary source label linking an entry to an emotion or sentiment |
| Candidate meter | Nearest configured fixed stress template; not definitive meter or performed rhythm |
| Concreteness orientation band | Configurable VerseVAD display aid, not a validated source-paper category |
| Concreteness rating | Source-supplied 1-5 normative rating from abstract/language-based toward concrete/experience-based |
| Complete pronunciation line | Physical line whose every eligible lexical token has resolved syllable and lexical-stress evidence |
| Content words only | Global contextual report scope limited to exact model tags NOUN, VERB, ADJ, and ADV |
| Coverage | Share of eligible lexical token positions represented by matches |
| Corpus-relative frequency | Frequency evidence tied to a named corpus rather than a universal property of a word |
| Equal-work module mean | Arithmetic mean of compatible eligible work-level module values |
| Cumulative normative lexical load | Length- and repetition-sensitive sums of normalized ratings or midpoint distances |
| Dominance | Normative control, power, or agency associated with a lexical item |
| Eligible token | Lexical token allowed into the denominator under the declared recipe |
| Exclude decision | Scenario decision that retains evidence but omits it from aggregation |
| Flag decision | Scenario note that does not alter a score |
| Graded slant evidence | Configured similarity across stressed vowel, final consonants, rhyme-part edit, stress alignment, and syllable count; not a probability |
| Identical rhyme | Complete retained phonological endings agree, including repeated words or homophonic complete endings |
| Internal rhyme | Exact dictionary rhyme parts recur between eligible words within one physical line |
| HD-D | Expected distinct-type proportion in a configured without-replacement token sample |
| Lemma | Model-proposed base form conditioned on part of speech |
| Lexical-style word unit | Eligible lexical token represented by its normalized observed surface form, without lemma substitution |
| MATTR | Mean type-token ratio across all overlapping token windows of a configured size |
| Lexical stress digit | CMUdict `0` unstressed, `1` primary, or `2` secondary lexical stress; not a metrical beat |
| Map decision | Scenario decision linking a form to a verified exact source entry |
| Match observation | One included token occurrence or accepted phrase span |
| Mean | Arithmetic average |
| Meter fit | Configured 0-1 stress-alignment similarity; not a probability |
| Meter line coverage | Analyzable eligible physical lines divided by all eligible physical lines |
| Declared meter style profile | Scholar-selected versioned realization weights; never an inferred period, movement, author, or tradition |
| Performance-aware realization | Optional contextual reranking and annotated reading above the unchanged fixed candidate layer; not performed scansion |
| Rhythmic organization | Rule-based accentual-syllabic, accentual, syllabic, locally metrical, mixed, no-stable-pattern, or insufficient-evidence description |
| Median | Middle sorted value |
| MTLD | Mean forward/reverse sequential factor-length estimate at a configured TTR threshold |
| Normalized VAD | Documented linear transformation to the common 0-to-1 display range |
| Ordered pooled-token result | Metric recalculated from the stable concatenated sequence of stored included token evidence |
| Numeric-response proportion | For the AoA source, numeric responses divided by total responses; preserved separately from the source's `Dunno` label |
| Part-of-speech profile | Model-assigned grammatical counts and shares over all eligible lexical tokens |
| Phrase match | Multi-token span linked to one source entry |
| Perfect rhyme | Robust line-ending rhyme parts agree while complete retained endings are not identical |
| Population standard deviation | Spread of the complete selected value set around its mean |
| PoetryID | Dependent 27-profile description over one completed source/view/weighting-specific normalized VAD result |
| PoetryID centroid | Configured continuous VAD coordinate representing one low/moderate/high profile combination |
| PoetryID confidence | Rule-based label from distance, neighbor margin, boundary proximity, agreement, and coverage; not a probability |
| Relative affinity | Inverse-distance comparison normalized across all 27 PoetryID centroids; not a probability |
| Pronunciation candidate | One exact CMUdict phone sequence retained for an observed spelling |
| Pronunciation coverage | Resolved eligible lexical-token occurrences divided by all eligible lexical-token occurrences |
| Provisional G2P candidate | Local out-of-dictionary ARPAbet suggestion for review; remains unmatched and unused until explicitly approved or edited into a session override |
| Readability formula | Prose-oriented calculation from declared word, sentence, character, or syllable counts; not an observed reader outcome |
| Resource unavailable | Expected local resource is missing or fails validation; distinct from an unmatched word |
| Prosodic consensus | Multiple dictionary candidates whose phone strings differ but syllable count and full stress sequence agree |
| Review scenario | Named, versioned set of scholar-authored decision revisions |
| Rhyme scheme | Letter sequence formed only from robust perfect/identical groups; `x` is analyzable and ungrouped, `?` unresolved |
| Rule-based meter confidence | Configured category from evidence count, coverage, fit, margin, and matching lines; not a calibrated probability |
| Scholar pronunciation override | Poem-specific validated ARPAbet phones with a required note, kept distinct from dictionary candidates |
| Sentiment | Broad positive, neutral, or negative orientation reported separately from eight emotions and VAD dimensions |
| Source value | Original value published by one lexicon |
| Source-unrated AoA entry | A source word row whose mean is unavailable; retained in the audit with no numeric age |
| Stopword | Common function word selected for exclusion from the secondary aggregate |
| Scope contrast | A descriptive comparison between two explicitly named lexical scopes, such as All lexical tokens and Stopword-excluded; not a separate metric |
| Surface form | Exact form in the preserved text |
| Token | One occurrence in the text |
| Token-weighted | Every included occurrence contributes |
| Type | One distinct matched lexicon entry in the declared unit |
| Type-weighted | Every distinct matched entry contributes once |
| Unmatched | No accepted entry; value remains missing |
| VADER compound score | Rule-adjusted sentiment signal from -1 to 1, interpreted with the documented conventional thresholds |
| Alphabetic word length | Number of Unicode alphabetic characters in the preserved surface token |
| Source POS tag(s) | Model-generated grammatical tag; displayed Noun merges NOUN/PROPN and Verb merges VERB/AUX |
| Valence | Normative pleasantness or unpleasantness associated with a lexical item |
| Work-weighted | Every eligible work-level mean contributes equally |
| Zipf value | Logarithmic SUBTLEX-US word-form frequency value; about one point represents a tenfold corpus-frequency difference |

> FINAL CHECK: If you cannot identify the lexicon or resource, scale, view or frequency scope, weighting, denominator, coverage, and scenario behind a number, return to the result or export before interpreting it.
