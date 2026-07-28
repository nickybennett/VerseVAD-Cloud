# Local Poetic Fingerprint Resources

This directory contains locally installed research resources used by optional
VerseVAD modules. Those licensed datasets remain ignored by source control.
The one explicit exception is the redistributable public-domain VerseMap
reference corpus under `VerseMap_Reference_Corpus/`, which is tracked together
with its deterministic manifest and release record.

For public-release download links, exact affective-lexicon locations,
installation steps, source-term cautions, and troubleshooting, see
[`docs/resource-installation.md`](../docs/resource-installation.md). VerseVAD
does not download these files automatically, and its GPL license does not
relicense any research dataset.

Current and planned local layout:

```text
resources/
  VerseMap_Reference_Corpus/
    Poet Name/
      Poem title.txt
    _versemap_manifest.csv
    _versemap_release.txt
  brysbaert_warriner_kuperman_concreteness_DATA.xlsx
  brysbaert_warriner_kuperman_concreteness_PAPER.pdf
  subtlexus1.zip
  subtlex-us/
    SUBTLEX-US frequency list with PoS and Zipf information.xlsx
  kuperman_2013_erratum_ESM1_official.xlsx
  kuperman_stadthagen_gonzalez_brysbaert_2012_aoa_PAPER.pdf
  pronunciation/
    cmudict.dict
    cmudict.phones
    cmudict.symbols
    CMUDICT_LICENSE.txt
    CMUDICT_README.txt
```

For the folder convention, provenance guidance, validation rules, and
Windows/macOS update commands, see
[`docs/versemap-reference-corpus.md`](../docs/versemap-reference-corpus.md).
The updater never edits a poem. Do not place private or copyrighted user
corpora in this tracked folder.

The two concreteness filenames are exact. Keep both directly inside
`resources/`; do not rename or edit them. VerseVAD currently requires the
workbook for the optional Stage 2 one-poem module and retains the paper beside
it as the local methodological reference. The workbook is expected at SHA-256
`1673ead761e28833a40e82c0d20f10782955ced9366d600eafeefee0f2254545`;
the paper is expected at
`7bafeef31b771965dbbbe2dea0227e210c8f4d054461343505f829ecfa036b63`.

The Stage 3 frequency module requires the exact workbook path shown above.
Keep it under `resources/subtlex-us/`; do not rename or edit it. Its expected
SHA-256 is
`3a8cb93a4e28988c2ce722a63f6b8d394acdc42ebe2ab6e1f0e484ee0d4167a7`.
The preserved official download archive `resources/subtlexus1.zip` has
SHA-256
`458128f90a28c4f396cb2a5b23ac93c56f745ee8cfca9be2afedad4091d15090`;
the adapter does not read the archive at analysis time.

Do not place the five existing VAD and emotion lexicons here. They remain
immutable under `source_lexicons/` and continue to be read in place by their
existing adapters.

Each resource adapter must:

1. read its source file in place;
2. compute and record a SHA-256 checksum;
3. record the resource name, edition or version, citation, usage notice, and
   adapter version;
4. keep original source values separate from derived values;
5. report missing, malformed, and unsupported resources in plain language;
6. leave unmatched tokens missing rather than assigning a neutral or zero
   value; and
7. avoid copying a licensed dataset into exports, backups, or source control.

The curated VerseMap reference corpus is not an adapter resource and is not an
exception to any lexicon rule above. Only its specifically unignored folder is
tracked; all other locally installed `resources/` data remain excluded.

The implemented frequency module uses only the pinned official SUBTLEX-US
Zipf workbook. VerseVAD does not use `wordfreq` as a fallback or alternate
frequency source. Absent word forms remain unmatched with missing values.

The optional Stage 4 Age of Acquisition module uses only the official
Springer erratum supplement
`resources/kuperman_2013_erratum_ESM1_official.xlsx`, expected at SHA-256
`3f69a1332359de1cd4a7ccd3c4c3c2e39b388eeb171d6e90544709c3dc1a8a6e`.
The locally retained publisher paper
`resources/kuperman_stadthagen_gonzalez_brysbaert_2012_aoa_PAPER.pdf` is
expected at SHA-256
`fa72b2dd7980707de710b4dcb346d0368d5e2c21d657824a935ea4b8b8b80e1a`.
Keep both filenames unchanged.

The locally supplied `AoA_51715_words.xlsx`,
`AoA_ratings_Kuperman_et_al_BRM_with_PoS.xlsx`, and
`Master file with all values for test based AoA measures Biemiller.xlsx` are
retained unchanged as comparison/reference resources. They are not combined
with, substituted for, or read by the Stage 4 adapter. The 51,715-word file is
a derived multi-source compilation; the `with_PoS` file adds a column to the
official Kuperman rows; and the Biemiller file represents a distinct
test-based construct.

The Kuperman paper describes its target selection as base forms used most
frequently as nouns, verbs, or adjectives. The official supplement nonetheless
contains rated polyfunctional spellings such as `the`, `and`, `he`, `of`, and
`to`. VerseVAD therefore keeps the optional contextual
`NOUN`/`VERB`/`ADJ`/`ADV` scope available and off by default; source selection
and a particular poem occurrence's model POS are not treated as equivalent.

The optional Stage 5 pronunciation/prosody-foundation module uses the exact
files under `resources/pronunciation/`, pinned from the official
`cmusphinx/cmudict` repository at commit
`74790861f652b15e4ac49015a90074ad62a27690`. Keep every filename unchanged.
Expected SHA-256 values are:

- `cmudict.dict`:
  `81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22`;
- `cmudict.phones`:
  `ffb588a5e55684723582c7256e1d2f9fadb130011392d9e59237c76e34c2cfd6`;
- `cmudict.symbols`:
  `408ccaae803641c6d7b626b6299949320c2dbca96b2220fd3fb17887b023b027`;
- `CMUDICT_LICENSE.txt`:
  `bd4ce8e44170a5f9f481310ca85c51de3c4f851a65e679b40e603b143bd3542a`;
  and
- `CMUDICT_README.txt`:
  `00c34e7564f1f6a68de02e12c123d801471da92bc3091f7d89b605f238bf8554`.

The exact local CMUdict files are authoritative at analysis time. The pinned
`pronouncing` and `cmudict` Python packages provide utilities and dependency
provenance; VerseVAD does not silently substitute the package-bundled
dictionary. Absent or materially ambiguous observed forms remain missing.
