# Installing VerseVAD Research Resources

VerseVAD is open-source software, but its research datasets are separate
works with separate licenses or terms. They are intentionally absent from the
public source repository. Download each resource from its official source,
review and follow its terms, and install it locally. VerseVAD never downloads,
uploads, edits, or redistributes these files.

The app remains usable when only some resources are installed. Affective
sources that fail validation are removed from the available-source selector.
Concreteness, frequency, Age of Acquisition, pronunciation, meter, and
rhyme/sound controls are disabled when their dependencies are unavailable.
Resource-free lexical-style analysis remains available.

VerseMap also requires its tracked reference model plus NRC VAD v2.1, NRC
Emotion v0.92, concreteness, SUBTLEX-US, and AoA resources. Its control remains
disabled until those sources are available. VerseMap does not require CMUdict
and does not use pronunciation or Sound & Form evidence.

## Installation procedure

1. Finish the normal VerseVAD software setup.
2. Use the official pages in the tables below. Some publishers ask you to
   accept terms before downloading supplementary material.
3. Extract the downloaded archive if necessary.
4. Create the exact destination folders shown below.
5. Copy the named source file into that destination without renaming, editing,
   cleaning, or converting it.
6. Start VerseVAD. Read the resource warning, if any, and run **Run self-test**
   from the Single Poem or Other Text sidebar.

The app distinguishes:

- **missing** — no regular file exists at the expected path;
- **malformed** — the path is not a readable, sufficiently sized regular file;
- **unsupported version** — the file is readable, but its SHA-256 does not
  match an edition validated by VerseVAD; and
- **available** — the exact expected file is present and its SHA-256 was
  recorded.

VerseVAD does not silently accept a different edition, substitute a package
copy, or assign a neutral value when a source entry is absent.

## Affective lexicons

Install these under `source_lexicons/`. The nested folders are intentional.

| Source | Official source page | Exact destination | Supported SHA-256 |
|---|---|---|---|
| Warriner, Kuperman, and Brysbaert VAD ratings | [Behavior Research Methods article and supplement](https://link.springer.com/article/10.3758/s13428-012-0314-x) | `source_lexicons/XANEW-master/XANEW-master/Ratings_Warriner_et_al.csv` | `78ac8107c78e116bb96538fae4faa47281a155f5f8fe39f30bbc6ea3db05b446` |
| NRC VAD Lexicon v1 | [NRC VAD download page](https://saifmohammad.com/WebPages/nrc-vad.html) | `source_lexicons/NRC-VAD-Lexicon/NRC-VAD-Lexicon/NRC-VAD-Lexicon.txt` | `fd49023f760155c8377424d96ca18d57c6685891d78ba381e47af6f4a1b148a7` |
| NRC VAD Lexicon v2.1 | [NRC VAD download page](https://saifmohammad.com/WebPages/nrc-vad.html) | `source_lexicons/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1.txt` | `42c718817fc91d5c133581b24b0bb31d2b14a0b16edb19bc6ce6ab70343e5a45` |
| NRC Emotion Lexicon v0.92 | [NRC Emotion Lexicon download page](https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm) | `source_lexicons/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt` | `02c661544f4f12ae0c14f9576a10959e8d39a151bb091e455a71a08dcaa2535a` |
| NRC Emotion Intensity Lexicon v1 | [NRC Affect Intensity download page](https://www.saifmohammad.com/WebPages/AffectIntensity.htm) | `source_lexicons/NRC-Emotion-Intensity-Lexicon/NRC-Emotion-Intensity-Lexicon/NRC-Emotion-Intensity-Lexicon-v1.txt` | `2bed5450b43134e4f849b013424eb76a76e2bdc0ec35df7ec0a0a477031239cb` |

The inspected local Warriner source arrived through the secondary XANEW
package and states CC BY-NC-ND 3.0 terms. Confirm that the file obtained from
the official article is the supported source edition and review its current
terms. NRC lexicons are generally available for non-commercial research and
educational use with attribution, prohibit data redistribution, and direct
commercial users to the creator. The current terms on the official download
page control.

You do not need every affective lexicon. VerseVAD analyzes each installed and
selected source independently and never creates a default consensus score.

## Supplementary lexical resources

Install these under `resources/`.

| Module | Official source page | Exact runtime destination | Supported SHA-256 |
|---|---|---|---|
| Concreteness | [Brysbaert, Warriner, and Kuperman article and supplement](https://link.springer.com/article/10.3758/s13428-013-0403-5) | `resources/brysbaert_warriner_kuperman_concreteness_DATA.xlsx` | `1673ead761e28833a40e82c0d20f10782955ced9366d600eafeefee0f2254545` |
| SUBTLEX-US Zipf frequency | [Ghent University SUBTLEX-US page](https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus) | `resources/subtlex-us/SUBTLEX-US frequency list with PoS and Zipf information.xlsx` | `3a8cb93a4e28988c2ce722a63f6b8d394acdc42ebe2ab6e1f0e484ee0d4167a7` |
| Kuperman retrospective Age of Acquisition | [Official erratum and ESM 1 supplement](https://link.springer.com/article/10.3758/s13428-013-0348-8) | `resources/kuperman_2013_erratum_ESM1_official.xlsx` | `3f69a1332359de1cd4a7ccd3c4c3c2e39b388eeb171d6e90544709c3dc1a8a6e` |

The article PDFs are useful local methodological references but are not
runtime dependencies. If retained, the filenames used in this development
workspace are:

- `resources/brysbaert_warriner_kuperman_concreteness_PAPER.pdf`; and
- `resources/kuperman_stadthagen_gonzalez_brysbaert_2012_aoa_PAPER.pdf`.

Review the publisher or source-page terms before downloading or using any
supplement. The GPL license for VerseVAD does not change those terms.

## CMU Pronouncing Dictionary

Download the pinned source files from the official
[cmusphinx/cmudict repository](https://github.com/cmusphinx/cmudict), commit
`74790861f652b15e4ac49015a90074ad62a27690`. Install:

| Exact destination | Supported SHA-256 |
|---|---|
| `resources/pronunciation/cmudict.dict` | `81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22` |
| `resources/pronunciation/cmudict.phones` | `ffb588a5e55684723582c7256e1d2f9fadb130011392d9e59237c76e34c2cfd6` |
| `resources/pronunciation/cmudict.symbols` | `408ccaae803641c6d7b626b6299949320c2dbca96b2220fd3fb17887b023b027` |

Also retain the repository license and README locally as
`resources/pronunciation/CMUDICT_LICENSE.txt` and
`resources/pronunciation/CMUDICT_README.txt`. CMUdict permits unrestricted
research and commercial use with acknowledgment of its Carnegie Mellon origin;
the exact retained license text controls.

Pronunciation, lexical stress, meter, and rhyme/sound all depend on these
three runtime files. The pinned Python packages do not silently replace them.

## Public repository boundary

The tracked `.gitignore` excludes:

- `source_lexicons/`;
- installed files beneath `resources/`;
- literary corpora and imported texts;
- project databases;
- exports and backups; and
- private runtime state.

Before publishing a fork, run `git status` and confirm that no research data,
literary text, database, export, or backup has entered source control. The
VerseVAD code and documentation are licensed under `GPL-3.0-only`; user-supplied
resources remain governed by their own copyright and terms.
