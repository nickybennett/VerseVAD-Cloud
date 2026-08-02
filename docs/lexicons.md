# Supplied Lexicon Inventory

Inspection date: 2026-07-22

The source files described below are not distributed with the open-source
VerseVAD repository. For official download pages, exact installation paths,
supported checksums, and source-specific terms, see the
[resource installation guide](resource-installation.md).

This inventory describes the files currently present under `source_lexicons/`.
The files were read and hashed but not modified. Counts below refer to the
selected primary English source file for each adapter, not translations or
alternate layouts bundled in the packages.

## Summary

| VerseVAD ID | Resource and version | Dimensions/categories | Source scale | Primary entries | Unit represented |
|---|---|---|---|---:|---|
| `warriner_vad_2013` | Warriner et al. affective norms (2013; no package version stated) | valence, arousal, dominance | 1–9 rating scale | 13,915 rows | described as English lemmas; 102 rows contain whitespace |
| `nrc_vad_v1` | NRC VAD Lexicon v1 | valence, arousal, dominance | 0–1 | 19,971 rows | described as English words; 132 rows contain whitespace |
| `nrc_vad_v2_1` | NRC VAD Lexicon v2.1 | valence, arousal, dominance | −1–1 | 54,801 rows | 44,728 unigrams and 10,073 whitespace-containing terms |
| `nrc_emotion_v0_92` | NRC Emotion Lexicon v0.92 | 8 emotions plus positive and negative sentiment | binary 0/1 association | 14,154 terms; 141,540 term-category rows | word-level union of sense annotations |
| `nrc_emotion_intensity_v1` | NRC Emotion Intensity Lexicon v1 | intensity for 8 emotions | 0–1 | 5,891 terms; 9,829 term-emotion rows | word-emotion pairs |

Whitespace counts are structural observations, not final phrase-policy
decisions. Hyphenated forms without whitespace are not included in those
counts.

## 1. Warriner et al. affective norms

- **Authors/publisher:** Amy Beth Warriner, Victor Kuperman, and Marc Brysbaert;
  the local package is a secondary XANEW distribution from JULIE Lab.
- **Version/date:** the package states the 2013 paper but provides no dataset
  version or local acquisition date.
- **Dimensions:** valence, arousal, and dominance, with overall means, standard
  deviations, rating counts, and demographic subsets.
- **Scale:** the ratings use a 1–9 scale. The local README does not itself state
  that scale; it is corroborated by the supplied NRC VAD v2 paper's comparison
  of existing lexicons and should be checked against the original Warriner
  publication before a public release.
- **Primary source file:**
  `source_lexicons/XANEW-master/XANEW-master/Ratings_Warriner_et_al.csv`
- **Documentation file:**
  `source_lexicons/XANEW-master/XANEW-master/README.md`
- **Observed structure:** comma-separated file with a header; 13,915 rows and
  13,915 unique source terms; no blank terms, malformed score rows, duplicate
  source-term keys, or out-of-range overall V/A/D means. Ten pairs collapse to
  the same key under case-insensitive lookup while retaining different source
  capitalization and ratings.
- **License stated by package:** Creative Commons
  Attribution-NonCommercial-NoDerivs 3.0 Unported. This is stated by the
  secondary distributor; an independent original license file is not supplied.
- **Required citation:** Warriner, A. B., Kuperman, V., & Brysbaert, M. (2013).
  “Norms of valence, arousal, and dominance for 13,915 English lemmas.”
  *Behavior Research Methods*, 45, 1191–1207.
- **SHA-256:**
  `78ac8107c78e116bb96538fae4faa47281a155f5f8fe39f30bbc6ea3db05b446`
- **Human review:** confirm original provenance, source version, and license
  text. Case-colliding ratings must remain separate: exact source
  capitalization may disambiguate them, while unresolved forms should be
  flagged rather than assigned an arbitrary rating.
- **Adapter status:** implemented and contract-tested. All source
  values remain on the 1–9 scale; separate 0–1 values use
  `(original - 1) / 8`. Phase 4 activates the 102 whitespace entries as exact,
  longest-first phrase candidates under the selected phrase policy. Overall
  standard deviations and rater counts are retained for Lexicon Explorer.

## 2. NRC VAD Lexicon v1

- **Creator/publisher:** Saif M. Mohammad, National Research Council Canada.
- **Version/date:** version 1, released July 2018; README updated August 2022.
- **Dimensions and scale:** valence, arousal, and dominance on 0–1 scales.
- **Primary source file:**
  `source_lexicons/NRC-VAD-Lexicon/NRC-VAD-Lexicon/NRC-VAD-Lexicon.txt`
- **Documentation:** `README.txt`, `Paper-VAD-ACL2018.pdf`,
  `Paper-Practical-Ethical-Considerations-Lexicons.pdf`, and
  `Paper-Ethics-Sheet-Emotion-Recognition.pdf` in the same package directory.
- **Observed structure:** headerless, four-column tab-separated file; 19,971
  rows and unique terms; no blank terms, malformed rows, duplicate term keys,
  or scores outside 0–1. There are 132 whitespace-containing terms.
- **Terms:** free for non-commercial research and educational purposes;
  attribution and citation required; data redistribution prohibited; commercial
  use requires contacting the author. This is a custom terms-of-use statement,
  not a standard open-source license.
- **Required citation:** Mohammad, S. M. (2018). “Obtaining Reliable Human
  Ratings of Valence, Arousal, and Dominance for 20,000 English Words.”
  *Proceedings of the 56th Annual Meeting of the Association for Computational
  Linguistics*.
- **SHA-256:**
  `fd49023f760155c8377424d96ca18d57c6685891d78ba381e47af6f4a1b148a7`
- **Phrase decision:** the 132 whitespace-containing entries participate as
  exact, longest-first phrase candidates under the selected phrase policy. This
  is a declared VerseVAD processing choice; it does not claim a separate
  phrase-specific validation study.
- **Adapter status:** implemented and contract-tested. Source values and
  normalized values are identical on the 0–1 scale. Exact phrase matches,
  suppressed components, and overlap decisions remain visible in the audit.

## 3. NRC VAD Lexicon v2.1

- **Creator/publisher:** Saif M. Mohammad, National Research Council Canada.
- **Version/date:** version 2.1, released March 2025.
- **Dimensions and scale:** valence, arousal, and dominance on −1–1 scales.
- **Primary source file:**
  `source_lexicons/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1.txt`
- **Documentation:** `README.txt`, `Paper-VAD-v2-2025.pdf`,
  `Paper-VAD-ACL2018.pdf`, and the practical/ethical papers in the same package.
- **Observed structure:** header plus four tab-separated columns; 54,801 rows
  and unique terms; no blank terms, malformed rows, duplicate term keys, or
  scores outside −1–1. Exactly 10,073 primary-file terms contain whitespace.
- **Unit:** English unigrams and multiword expressions. The package provides
  separate `Unigrams/` and `MWE/` layouts in addition to the primary file.
- **Terms:** free for non-commercial research and educational purposes;
  attribution and citation required; data redistribution prohibited; commercial
  use requires contacting the author.
- **Required citations:**
  - Mohammad, S. M. (2025). “NRC VAD Lexicon v2: Norms for Valence, Arousal,
    and Dominance for over 55k English Terms.” arXiv:2503.23547.
  - Mohammad, S. M. (2018). “Obtaining Reliable Human Ratings of Valence,
    Arousal, and Dominance for 20,000 English Words.” *ACL 2018*.
- **SHA-256:**
  `42c718817fc91d5c133581b24b0bb31d2b14a0b16edb19bc6ce6ab70343e5a45`
- **Important family note:** v1 and v2.1 are versions of the same NRC VAD
  family, not independent replications. v2 includes entries collected using a
  different rating procedure as documented by the supplied paper and README.
- **Adapter status:** implemented and contract-tested in Phase 2. Original
  −1–1 values are retained; separate normalized values use
  `(original + 1) / 2`. Its multiword expressions participate in deterministic
  phrase matching.

## 4. NRC Emotion Lexicon v0.92

- **Creators/publisher:** Saif M. Mohammad and Peter D. Turney, National
  Research Council Canada.
- **Version/date:** version 0.92, released 10 July 2011; README updated August
  2022.
- **Categories:** anger, anticipation, disgust, fear, joy, sadness, surprise,
  trust, negative, and positive.
- **Scale:** binary association, 0 or 1. Categories are not intensity scores.
- **Primary source file:**
  `source_lexicons/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt`
- **Documentation:** `README.txt`, `Paper1_NRC_Emotion_Lexicon.pdf`,
  `Paper2_NRC_Emotion_Lexicon.pdf`, and the practical/ethical papers in the same
  package.
- **Observed structure:** headerless three-column, tab-separated long format;
  every one of 14,154 unique terms has ten category rows, for 141,540
  term-category rows. No blank terms, malformed rows, duplicate term-category
  keys, or non-binary values were found.
- **Unit:** word-level associations created by taking the union of associations
  across supplied sense annotations. The package also contains a separate
  sense-level file; it is not the selected primary adapter source.
- **Terms:** free for non-commercial research and educational purposes;
  attribution and citation required; data redistribution prohibited; commercial
  use requires contacting the author.
- **Required citations:**
  - Mohammad, S. M., & Turney, P. D. (2013). “Crowdsourcing a Word-Emotion
    Association Lexicon.” *Computational Intelligence*, 29(3), 436–465.
  - Mohammad, S. M., & Turney, P. D. (2010). “Emotions Evoked by Common Words
    and Phrases: Using Mechanical Turk to Create an Emotion Lexicon.”
    *Proceedings of the NAACL-HLT Workshop on Computational Approaches to
    Analysis and Generation of Emotion in Text*, 26–34.
- **SHA-256:**
  `02c661544f4f12ae0c14f9576a10959e8d39a151bb091e455a71a08dcaa2535a`
- **Human review:** none blocking. The word-level union should be described
  clearly in methods reports because it does not disambiguate senses in context.
- **Adapter status:** implemented and contract-tested in Phase 2. Binary values
  remain categorical associations rather than intensities. Every denominator is
  labeled and a token may contribute to multiple categories.

## 5. NRC Emotion Intensity Lexicon v1

- **Creator/publisher:** Saif M. Mohammad, National Research Council Canada.
- **Version/date:** version 1, released March 2020; README updated August 2022.
- **Categories:** anger, anticipation, disgust, fear, joy, sadness, surprise,
  and trust.
- **Scale:** real-valued emotion intensity from 0 to 1 for each supplied
  word-emotion pair.
- **Primary source file:**
  `source_lexicons/NRC-Emotion-Intensity-Lexicon/NRC-Emotion-Intensity-Lexicon/NRC-Emotion-Intensity-Lexicon-v1.txt`
- **Documentation:** `README.txt`, `Paper-lrec2018-word-emotion.pdf`, and the
  practical/ethical papers in the same package.
- **Observed structure:** headerless three-column tab-separated long format;
  9,829 word-emotion pairs across 5,891 unique terms; no blank terms, malformed
  rows, duplicate word-emotion keys, or scores outside 0–1.
- **Unit:** independently scored word-emotion pairs. Absence of a pair must not
  be converted into an intensity of zero in primary means.
- **Terms:** free for non-commercial research and educational purposes;
  attribution and citation required; data redistribution prohibited; commercial
  use requires contacting the author.
- **Required citation:** Mohammad, S. M. (2018). “Word Affect Intensities.”
  *Proceedings of the 11th Language Resources and Evaluation Conference*.
- **SHA-256:**
  `2bed5450b43134e4f849b013424eb76a76e2bdc0ec35df7ec0a0a477031239cb`
- **Human review:** the supplied research paper describes the earlier
  four-emotion release, while the README and current file cover eight emotions.
  Methods reports must cite the paper and record that the analyzed source is
  the later version 1 package.
- **Adapter status:** implemented and contract-tested in Phase 2. Only supplied
  word-emotion pairs enter category-specific means; an absent pair is never
  converted into intensity zero.

## Integrity result

All five primary files passed the Phase 0 structural checks:

- expected primary file present;
- expected columns present where headers exist;
- numeric values parse successfully;
- source-scale range checks pass;
- no blank terms;
- no malformed rows;
- no duplicate source primary keys;
- ten Warriner case-insensitive lookup collisions preserved for explicit
  resolution or review.

Phase 2 adapters repeat these checks during loading, preserve the recorded
source hashes, and stop with a plain-language error before analysis when a
contract fails. The double-clickable Phase 2 test also compares all five hashes
with this inventory before producing exports.

This validates file structure, not the scholarly correctness of individual
ratings or the suitability of a particular match in context.

To repeat the read-only check, run `python scripts/inspect_lexicons.py` once the
project runtime is installed.

## Packaged Open English WordNet dictionary

Lexicon Explorer also provides lexical definitions and relations from Open
English WordNet 2025+. This is a dictionary service, not an affective or
normative-rating lexicon: its senses never affect poem scores, coverage, or
matching in the analytical modules.

The repository packages a pre-indexed, XZ-compressed database built from the
official 2025+ release and read through pinned `wn` 1.1.0. VerseVAD validates
the packaged archive, expands it into the ignored local runtime directory on
first use, and then performs lookups entirely offline. Lexicon Explorer shows
definitions, examples, synonyms, antonyms, and broader or narrower concepts
where the source provides them. It orders senses using the query and the
processing lemma and part of speech, but it does not claim to identify the
contextually correct sense.

Open English WordNet is licensed under CC BY 4.0 and incorporates material
covered by the Princeton WordNet license. The repository retains both license
texts, the official citation record, source and package checksums, and the
storage-transformation notice under `resources/open_english_wordnet/`. See
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for consolidated
attribution.

## Optional local concreteness resource

The Poetic Fingerprint Stage 2 concreteness workbook is a separate optional
research resource under `resources/`, not one of the five supplied affective
lexicons above. The inspected Brysbaert, Warriner, and Kuperman (2014)
workbook contains 39,954 ratings on a 1-5 scale, including 2,896 two-word
expressions, and has SHA-256
`1673ead761e28833a40e82c0d20f10782955ced9366d600eafeefee0f2254545`.
Its adapter is read-only and the full workbook is never copied into VerseVAD
exports. See
[`poetic-fingerprint-stage2.md`](poetic-fingerprint-stage2.md) for the exact
source contract, matching policy, citation, calculations, and limitations.

## Optional local SUBTLEX-US frequency resource

Poetic Fingerprint Stage 3 uses a separate optional official SUBTLEX-US
workbook under `resources/`; it is not one of the five affective lexicons and
is not pooled with their values. The inspected `out1g` worksheet contains
74,286 unique word-form rows with Zipf values ranging from approximately 1.593
to 7.621. The analysis workbook is:

`resources/subtlex-us/SUBTLEX-US frequency list with PoS and Zipf information.xlsx`

Its SHA-256 is
`3a8cb93a4e28988c2ce722a63f6b8d394acdc42ebe2ab6e1f0e484ee0d4167a7`.
The adapter is read-only, unmatched values remain missing, and the full
workbook is never copied into exports. VerseVAD does not use `wordfreq` as an
alternate or fallback. See
[`poetic-fingerprint-stage3.md`](poetic-fingerprint-stage3.md) for the exact
source contract, word-form-first matching, optional content-word scope,
calculations, citation, and limitations.

## Optional local Kuperman Age of Acquisition resource

Poetic Fingerprint Stage 4 uses the official Springer erratum supplement for
Kuperman, Stadthagen-Gonzalez, and Brysbaert's retrospective English Age of
Acquisition ratings. The analysis workbook is:

`resources/kuperman_2013_erratum_ESM1_official.xlsx`

Its SHA-256 is
`3f69a1332359de1cd4a7ccd3c4c3c2e39b388eeb171d6e90544709c3dc1a8a6e`.
The inspected `Sheet1` contains 31,124 unique nonblank word rows: 31,105 with
numeric source means from 1.58 through 25.0 years and 19 with unavailable
numeric means. The read-only adapter validates the exact seven-column
contract, response-count relationships, source `NA` and `#N/A` values, ranges,
and lookup-key uniqueness.

The local publisher paper is
`resources/kuperman_stadthagen_gonzalez_brysbaert_2012_aoa_PAPER.pdf`,
with SHA-256
`fa72b2dd7980707de710b4dcb346d0368d5e2c21d657824a935ea4b8b8b80e1a`.
The full workbook is never copied into exports.

The paper describes content-word target selection, but the official supplement
contains rated polyfunctional spellings including `the`, `and`, `he`, `of`,
and `to`. VerseVAD therefore retains a non-default contextual content-word
scope using model tags `NOUN`, `VERB`, `ADJ`, and `ADV`; source sampling and
the grammatical role of a particular poem occurrence remain separate.

The locally supplied `AoA_51715_words.xlsx`,
`AoA_ratings_Kuperman_et_al_BRM_with_PoS.xlsx`, and Biemiller master workbook
remain unchanged as reference/comparison sources. The Stage 4 runtime does not
merge or substitute them. See
[`poetic-fingerprint-stage4.md`](poetic-fingerprint-stage4.md) for the exact
contract, calculations, source-response fields, matching policy, and
limitations.

## Optional local CMU Pronouncing Dictionary resource

Poetic Fingerprint Stage 5 uses official `cmusphinx/cmudict` files pinned at
repository commit `74790861f652b15e4ac49015a90074ad62a27690`. This resource
is a pronunciation dictionary, not an affective or lexical-semantic rating
lexicon, and it is never pooled with VAD, emotion, concreteness, frequency, or
AoA values.

The authoritative analysis-time files are:

- `resources/pronunciation/cmudict.dict`, SHA-256
  `81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22`;
- `resources/pronunciation/cmudict.phones`, SHA-256
  `ffb588a5e55684723582c7256e1d2f9fadb130011392d9e59237c76e34c2cfd6`;
  and
- `resources/pronunciation/cmudict.symbols`, SHA-256
  `408ccaae803641c6d7b626b6299949320c2dbca96b2220fd3fb17887b023b027`.

The pinned dictionary has 135,166 source rows and 126,052 normalized
spellings. Every alternative pronunciation remains auditable. CMUdict
primarily represents North American English and acknowledges possible errors,
omissions, and inconsistencies. Its license permits unrestricted research and
commercial use with requested acknowledgment of Carnegie Mellon University.

See [`poetic-fingerprint-stage5.md`](poetic-fingerprint-stage5.md) for the
exact contract, resolution policy, overrides, calculations, exports, and
limitations.
