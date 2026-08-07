# VerseVAD

VerseVAD is free, open-source research software for transparent computational
analysis of poetry and other literary texts. It combines affective lexicons,
lexical-semantic norms, language profiles, readability, prosody, rhyme,
inherited-form evidence, corpus comparison, and VerseMap in a local
browser-based interface.

VerseVAD reports **descriptive lexical and formal evidence**. It does not
determine what a poem feels, what an author intended, what a reader
experiences, or whether an interpretation is correct.

Version: **1.0.0**

License: **GPL-3.0-only**

Repository: <https://github.com/VerseVAD/VerseVAD>

## What VerseVAD includes

- Single-poem and other-text analysis with source-specific evidence,
  transparent coverage, and downloadable CSV and Word reports.
- Side-by-side comparison of two to ten poems under one shared configuration.
- Persistent local projects, a private Personal Corpus, read-only Corpus
  Browser, and explicit Analysis Library saves.
- Valence, arousal, dominance, emotion association and intensity, VADER
  sentiment, concreteness, SUBTLEX-US rarity, Age of Acquisition,
  sensorimotor norms, readability, lexical diversity, and structural measures.
- One global post-analysis profile system for compatible lexical metrics:
  All lexical tokens, Stopword-excluded, or Content words only, crossed with
  Token-weighted or Type-weighted aggregation. All six perspectives are
  reconstructed from retained evidence without rerunning linguistic analysis.
- Offline Open English WordNet definitions, examples, synonyms, antonyms, and
  semantic relations in Lexicon Explorer.
- CMUdict-based pronunciation review, session overrides, syllable and stress
  evidence, candidate meter, rhyme and recurring-sound evidence.
- A source-documented inherited-form registry and cautious candidate ranking.
- VerseMap comparison against the bundled public-domain reference corpus or
  locally maintained user corpora.
- Exact source hashes, match decisions, denominators, warnings, software and
  model versions, plus Current View and Complete Audit research bundles with
  human-readable reproducibility and file-inventory records.

The interface is organized under **Analyze**, **Collections**, **Explore**, and
**Learn**. Learn includes a **Training** page with four free learner manuals
and applied exercises. See the [documentation index](docs/index.md) for the
complete user, methodology, resource, training, and contributor documentation.

## Install and start

VerseVAD supports Windows and macOS. Setup creates an environment inside the
VerseVAD folder; it does not require a system-wide Python installation or
administrator access. Internet access is required during first-time setup to
download the pinned runtime and dependencies. Ordinary local analysis is
offline.

### Windows

1. Clone or download this repository.
2. Double-click `setup_windows.bat`.
3. Install any research datasets you are licensed to use by following
   [the resource installation guide](docs/resource-installation.md).
4. Double-click `start_versevad.bat`.

### macOS

Open Terminal, then run:

```bash
cd ~/Documents/VerseVAD
bash setup_macos.command
./start_versevad.command
```

If macOS blocks the launcher as coming from an unidentified developer, follow
the one-time instructions in the
[macOS installation guide](docs/macos-installation.md).

Both launchers open `http://127.0.0.1:8501`. That loopback address is local to
the computer running VerseVAD; it is not a public website. Keep the launcher
window open while using the application.

`pyproject.toml` declares the direct dependencies and `uv.lock` pins the full
cross-platform environment. A separate `requirements.txt` is intentionally
unnecessary when using the supplied setup helpers.

## Research resources

The public repository does not redistribute most research lexicons,
normative datasets, or papers. Their licenses remain separate from
VerseVAD's GPL license. Users download the resources they are permitted to use
and place the unchanged files at the documented paths.

VerseVAD never substitutes zero for an absent rating. At startup and in
Installation Check, missing or malformed resources are reported plainly;
modules backed by installed resources remain usable.

See:

- [Resource installation, filenames, links, and license boundaries](docs/resource-installation.md)
- [Research resource inventory and provenance](docs/lexicons.md)
- [Bundled and user-maintained VerseMap corpora](docs/versemap-reference-corpus.md)

The public-domain VerseMap reference corpus is the explicit tracked exception
under `resources/VerseMap_Reference_Corpus/`. Private poetry, projects,
personal corpora, exports, downloaded lexicons, environments, and caches are
excluded by `.gitignore`.

## Documentation

Start with [docs/index.md](docs/index.md). It organizes the maintained
documentation by task:

- installation and safe updates;
- workspaces and interpretation;
- methods, formulas, limitations, and terminology;
- resources, provenance, and licensing;
- architecture, data model, testing, and contribution guidance; and
- printable Word manuals.

## Free training pathway

Open **Learn → Training** inside VerseVAD to download the four free learner
manuals and applied exercises:

- VerseVAD Foundations;
- Computational Close Reading with VerseVAD (Analyst Level 1);
- Advanced Corpus and Research Analysis (Analyst Level 2); and
- VerseVAD Authorized Instructor Training.

Current program information is available at
<https://www.versevad.org/training>. Public application packages do not include
evaluator answer keys, scoring rubrics, completion records, certificates, or
authorization materials.

## Privacy and scholarly use

Local VerseVAD does not send poems, lexicons, project data, notes, or results
to an external analysis service. Analysis Library saves, projects, and
Personal Corpus data are stored in ignored local SQLite files. Research notes
are excluded from quick exports unless the user explicitly includes them.

Outputs should be described as evidence—for example, “mean normative valence
of matched content-word tokens”—rather than as declarations about a poem,
author, speaker, or reader. Coverage, eligible-token counts, missingness, and
configuration choices belong in any responsible interpretation.

## Development and testing

The analysis engine is independent of Streamlit and is covered by synthetic,
hand-checkable tests. From an installed checkout:

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

macOS:

```bash
./.venv/bin/python -m pytest -p no:cacheprovider -q
```

See [testing.md](docs/testing.md) for focused commands, optional-resource
testing, diagnostics, and the release checklist. See
[CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff). GitHub can
render it through **Cite this repository**.

Creator: **Nicky Bennett**

## License

VerseVAD source code and documentation are licensed under the
[GNU General Public License v3.0 only](LICENSE). The GPL permits use,
modification, and redistribution, including commercial use, subject to its
terms.

The GPL does not grant permission to redistribute or commercially use
third-party lexicons, datasets, papers, language models, or literary texts.
Those materials remain governed by their own licenses and terms.

VerseVAD packages Open English WordNet 2025+ under CC BY 4.0, including
underlying Princeton WordNet attribution. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the complete packaged
[license files](resources/open_english_wordnet/).
