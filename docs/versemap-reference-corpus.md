# VerseMap Reference Corpus

VerseMap's curated comparison corpus lives in:

```text
resources/
  VerseMap_Reference_Corpus/
    Emily Dickinson/
      Poem title.txt
    Walt Whitman/
      Another poem.txt
```

Each immediate subfolder represents one poet. Each UTF-8 `.txt` file under
that folder represents one comparison work. Subfolders within a poet folder
are allowed, but keeping one flat folder per poet is simplest. The filename
stem is the fallback display title.

This corpus is the one deliberate source-control exception under `resources/`.
The poems must be suitable for redistribution. Locally installed research
lexicons, user projects, personal corpora, and private texts remain ignored.
Public-domain authorship alone does not establish that a modern transcription
or edition is redistributable, so retain source and edition information. A
plain `_source.md` file inside each poet folder is recommended; the updater
ignores non-`.txt` files.

## Routine update workflow

1. Add a folder named for the poet under
   `resources/VerseMap_Reference_Corpus/`.
2. Put one complete poem in each UTF-8 `.txt` file. Preserve its spelling,
   punctuation, stanza breaks, and lineation.
3. Run the updater.
4. Review its errors and warnings.
5. Review `git status`, then commit and push the poet folder, source release,
   and derived Standard Profile index together.

The ordinary VerseVAD launcher does not rebuild the reference release.
Updating is an explicit maintainer action.

### Windows

After VerseVAD has been set up, double-click:

```text
update_versemap_reference.bat
```

Or run this in PowerShell from the VerseVAD folder:

```powershell
.\.tools\uv\uv.exe run --frozen --offline versevad-update-versemap
```

### macOS

After VerseVAD has been set up, double-click
`update_versemap_reference.command`. If macOS has not yet granted that copied
launcher permission, Control-click it once and choose **Open**.

Or run this in Terminal from the VerseVAD folder:

```bash
bash update_versemap_reference.command
```

### Verification only

This command checks whether the tracked release files are current without
changing anything:

```text
versevad-update-versemap --check
```

Use it through the local `uv run --frozen --offline` command shown above.

## What the updater does

The updater:

- discovers immediate poet folders and their `.txt` files;
- requires every poem to be nonempty UTF-8;
- detects path and stable-ID collisions that would fail on Windows or macOS;
- records exact source-byte and canonical-text SHA-256 hashes;
- assigns stable poet and poem IDs;
- records file size plus inventory-only line, character, and rough word
  counts;
- flags identical text, repeated titles, unusually short fragments, and
  unusually long possible collections;
- writes a deterministic CSV manifest and a short deterministic release
  record;
- extracts the pinned, sound-free
  [VerseMap Standard Profile 1.0](versemap-standard-profile.md) for each poem;
- reuses an unchanged poem profile by stable poem ID and source SHA-256;
- checkpoints every 25 poems so an interrupted build can resume;
- fits deterministic weighted PCA display coordinates; and
- creates per-poet centroids with exact model and coverage metadata.

It creates or updates:

```text
resources/VerseMap_Reference_Corpus/_versemap_manifest.csv
resources/VerseMap_Reference_Corpus/_versemap_release.txt
resources/VerseMap_Reference_Corpus/_versemap_profiles.csv
resources/VerseMap_Reference_Corpus/_versemap_poet_profiles.csv
resources/VerseMap_Reference_Corpus/_versemap_model.csv
```

The updater never edits or renames a source poem. It normalizes only line-ending
differences in a separate in-memory representation when computing the release
identity. Standard Profile extraction reads the shared processing
representation while original spelling, Unicode, punctuation, and lineation
remain unchanged.

Errors stop the update without changing the generated release files. Warnings
do not exclude a poem. Long works, dramatic poems, fragments, and epigrams can
all be legitimate; warnings ask the maintainer to confirm that the file
boundary is intentional.

The rough word count in the source manifest is only an inventory check. It is
not a VerseMap analytical result and does not replace VerseVAD's shared
tokenizer.

## Local and cloud repositories

The source folders and five generated release/index files are ordinary tracked
repository files. Once the same commit is present in the public local-use
repository and the private cloud repository, both deployments see the same
reference release. No absolute computer path is stored.

The derived analytical files are tied to the release ID and pinned profile.
They do not contain the installed research lexicons themselves. User poems,
personal corpora, projects, and project databases remain local and are never
added to the reference release.
