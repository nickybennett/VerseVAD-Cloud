# VerseVAD Documentation

This is the documentation home for VerseVAD 1.0.0. The pages below describe
the current release rather than its implementation history.

## Start here

- [Project overview](../README.md) — scope, major features, privacy, license,
  and quick installation.
- [User guide](user-guide.md) — workspace-by-workspace operation and
  interpretation.
- [Resource installation](resource-installation.md) — official download
  locations, exact filenames, folders, validation, and license boundaries.
- [macOS installation](macos-installation.md) — first setup, Gatekeeper,
  Safari/Chrome, launchers, and diagnostics.
- [Updating VerseVAD](updating.md) — safe GitHub Desktop and terminal updates
  that preserve local resources and projects.

## Use the workspaces

| Need | Documentation |
|---|---|
| Analyze one poem or another text | [User guide](user-guide.md#analyze-a-poem) |
| Compare two to ten poems | [User guide](user-guide.md#compare-two-to-ten-poems) |
| Build or analyze a project/corpus | [User guide](user-guide.md#build-and-compare-a-corpus) |
| Maintain a private Personal Corpus | [User guide](user-guide.md#maintain-a-personal-corpus) |
| Look up a word or phrase | [User guide](user-guide.md#use-lexicon-explorer) |
| Save and reopen an analysis | [Analysis Library and research notes](research-library.md) |
| Inspect or update comparison corpora | [VerseMap reference corpora](versemap-reference-corpus.md) |
| Understand VerseMap features and PCA | [VerseMap Standard Profile 1.0](versemap-standard-profile.md) |
| Review inherited poetic forms | [Inherited Form Registry](inherited-form-registry-v2.md) |
| Download free VerseVAD courses | **Learn → Training** in the application or [VerseVAD Training](https://www.versevad.org/training) |
| Export CSV, Word, or audit reports | [User guide](user-guide.md#downloads-and-the-audit-bundle) |

## Understand the evidence

- [Methodology](methodology.md) — calculation rules, weighting, formulas,
  coverage, limitations, and interpretive cautions for every metric family.
- [Research resources and provenance](lexicons.md) — source scales, adapters,
  checksums, normalization, and known resource constraints.
- [Values and terminology guide (Word)](VerseVAD_Values_and_Terminology_Guide.docx)
  — worked examples and reporting language.
- [PoetryID archetype framework](VerseVAD_Poetic_Archetype_Framework_Expanded.docx)
  and [secondary lexical dimensions](VerseVAD_Poetic_Archetype_Framework_Expanded_with_Secondary_Lexical_Dimensions.docx)
  — the research framework behind PoetryID.

Always report the selected lexicon, lexical scope, token/type weighting,
eligible denominator, match coverage, fixed-profile ID where applicable, and
important warnings. A normative
lexical score is evidence about matched vocabulary, not a direct measurement
of a poem's emotion, meaning, quality, author, speaker, or reader.

## Printable manual

- [VerseVAD User Manual (Word)](VerseVAD_User_Manual.docx)
- [Manual source](VerseVAD_User_Manual_Source.md)
- [Values and Terminology Guide (Word)](VerseVAD_Values_and_Terminology_Guide.docx)
- [Values and Terminology Guide source](VerseVAD_Values_and_Terminology_Guide_Source.md)

The Markdown guides are convenient for GitHub and website linking. The Word
manual is the printable, single-document reference.

## Free training courses

The application packages four learner manuals and four applied exercises under
**Learn → Training**. The pathway progresses through Foundations, Analyst
Level 1, Analyst Level 2, and Authorized Instructor Training. Evaluator answer
keys, scoring rubrics, candidate records, certificates, and authorization
materials are administered separately and are not included in the public
repository. See <https://www.versevad.org/training> for current program
information.

## Develop or extend VerseVAD

- [Contributing](../CONTRIBUTING.md) — contribution rules and pull-request
  expectations.
- [Architecture](architecture.md) — component boundaries, data flow,
  persistence, privacy, and extension points.
- [Data model](data-model.md) — stable identities, immutable results, database
  schemas, and saved-analysis records.
- [Testing](testing.md) — diagnostics, focused tests, complete suite, optional
  resource validation, and release checks.
- [VerseMap corpus maintenance](versemap-reference-corpus.md) — deterministic
  reference-index updates on Windows and macOS.
- [Changelog](../CHANGELOG.md) — release-level changes.

## Licensing and citation

VerseVAD code and documentation are
[GPL-3.0-only](../LICENSE). Third-party lexicons, datasets, papers, language
models, and literary texts retain their own licenses. See
[CITATION.cff](../CITATION.cff) for citation metadata.

The redistributable Open English WordNet 2025+ dictionary is packaged under
CC BY 4.0 with Princeton WordNet attribution. See the complete
[third-party notices](../THIRD_PARTY_NOTICES.md) and packaged
[license files](../resources/open_english_wordnet/).

Canonical repository: <https://github.com/VerseVAD/VerseVAD>
