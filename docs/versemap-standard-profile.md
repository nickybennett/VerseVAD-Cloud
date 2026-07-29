# VerseMap Standard Profile 1.0

VerseMap is an optional comparative layer for positioning an analyzed poem
relative to a versioned public-domain reference corpus. It reports descriptive
proximity under one pinned computational profile. It does **not** identify
authorship, influence, genre, quality, intention, meaning, or reader response.

## Inclusion policy

Standard Profile 1.0 fixes these choices:

- token weighting;
- repeated word occurrences retained;
- stopwords removed for lexical measures;
- model-tagged `NOUN`, `VERB`, `ADJ`, and `ADV` used for lexical measures;
- POS-aware normalized lemmas used for lexical-diversity measures;
- NFC Unicode normalization and lowercase normalized lookup;
- original spelling, punctuation, lineation, and stanza boundaries preserved;
- count-based measures divided by their documented token, line, or stanza
  denominator;
- fixed source editions, adapters, tokenizer, feature registry, transforms,
  and group weights; and
- eligible counts, matched counts, and coverage retained with every lexical
  observation.

Missing evidence remains missing. It is never entered as a neutral score or
zero. Repeating a matched word therefore affects token-weighted lexical values,
as intended.

VerseMap 1.0 deliberately uses **no pronunciation, syllable, stress, meter,
rhyme, refrain, alliteration, assonance, consonance, or other Sound & Form
evidence**. Pronunciation ambiguity cannot change a VerseMap position. Those
analyses remain independently available in VerseVAD for close reading.

## Registered dimensions

| Group | Dimensions |
|---|---|
| VAD | NRC VAD v2.1 content-word token mean and population SD for valence, arousal, and dominance |
| Emotion association | NRC Emotion v0.92 content-token association prevalence for anger, anticipation, disgust, fear, joy, sadness, surprise, and trust |
| Concreteness | Brysbaert et al. content-token mean and population SD |
| Lexical norms | `7.0 - mean SUBTLEX-US Zipf` lexical rarity and mean Kuperman et al. AoA years |
| Lexical character | MATTR (50), HD-D (42), bidirectional MTLD (0.72), and mean alphabetic content-word length over POS-aware normalized lemmas |
| Content POS | noun, verb, adjective, and adverb proportions among eligible content tokens |
| Structure | mean and population SD of words per nonblank line, mean words per stanza, and mean nonblank lines per stanza |

Emotion associations are multi-label. Their proportions need not sum to one.
Lexical rarity is reversed from frequency so larger displayed values mean rarer
diction.

## Weighting, standardization, and map coordinates

Each feature group receives equal total weight. Dimensions within a group
divide that group weight equally. Positive, right-skewed length measures use a
fixed `log1p` transform; other measures remain on their recorded scale.
Reference-poem values are then z-standardized with the stored reference mean
and population standard deviation.

The two plotted axes are a deterministic weighted principal-component
projection fitted to the reference poems. Their labels report explained
reference variance. They are composite display axes, not independently named
literary traits.

Nearest poems and poet centroids are ranked in the complete registered feature
space, not by two-dimensional map distance. Distance is weighted standardized
Euclidean distance over dimensions present for both points:

```text
sqrt(sum(weight * squared z difference) / sum(shared weight))
```

A comparison requires at least 60% shared registered weight. Lower distance is
nearer. Distance is not a probability, confidence score, attribution, or claim
of historical relationship.

For a corpus project, each work is analyzed independently. The displayed
project map centroid is the arithmetic mean of completed work coordinates.
Project-level poet rankings average the works' full-space distances to each
reference poet centroid, so a long poem does not automatically determine the
only project result.

## Version and provenance

Every result stores the profile, corpus release, and fitted model identities;
the profile-build identity that pins the extraction implementation;
raw feature values; reference means and standard deviations; z-scores;
approximate percentiles; feature weights; eligible and matched counts;
coverage; and nearest-neighbor distances with shared feature weight.

The tracked `_versemap_profiles.csv`, `_versemap_poet_profiles.csv`, and
`_versemap_model.csv` files form the derived analytical release. Changing a
source poem, source edition, feature definition, source dataset, adapter,
transform, or weight requires incrementing the profile or profile-build
identity, rebuilding, and committing the derived release.
