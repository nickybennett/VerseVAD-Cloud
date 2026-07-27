# Phase 3.1 and Phase 4 Validation

Date: 2026-07-22

## Outcome

VerseVAD now has three top-level local workspace tabs: one poem, persistent
projects/corpus, and Lexicon Explorer. The project database defaults to
`projects/versevad.sqlite3`; source lexicons remain read-only in their original
location. Pending and failed corpus batches do not replace the latest complete
comparison. Ordinary use makes no external AI or text-analysis service request.

The completed Phase 4.1 validation includes 87 automated tests, both synthetic
demonstrations, all 11 local diagnostic checks, and an isolated live-browser
pass covering header navigation, dual VAD reporting, excluded-match evidence,
Lexicon Explorer, and safe project deletion.

The hand-calculated mixed-length fixture contains ten `bright` matches in one
work and one `dark` match in a second. Their normalized valence values are
0.875 and 0.250. VerseVAD reproduces:

- token-weighted volume mean: `(10 × 0.875 + 1 × 0.250) / 11 = 9 / 11 =
  0.818181…`;
- work-weighted volume mean: `(0.875 + 0.250) / 2 = 0.5625`.

The difference is deliberate evidence that long-work weighting and equal-work
weighting answer different questions.

## Beginner test 1: VAD explanation and cumulative load

1. Double-click `start_versevad.bat`.
2. Leave **One poem** selected in the top workspace tabs.
3. Enter a title and paste `Bright bright dark.`
4. Select Warriner or NRC VAD and click **Analyze this text**.
5. Open **VAD profile**.

Confirm that the page defines valence, arousal, and dominance; shows all three
token- and type-weighted means; explains the selected lexicon's means relative
to 0.5; lists top raising/lowering matched entries; and provides cumulative
rating and midpoint-load totals. Every section should describe normative
lexical evidence, not the poem's emotion or a measured reader response.

## Beginner test 2: Warriner phrases

1. In **One poem**, paste a line containing a multiword entry known to the
   supplied Warriner source.
2. Select Warriner and keep **Prefer the longest phrase** selected.
3. Analyze, then open **Evidence**.

Confirm that a selected Warriner phrase is labeled `exact_phrase` and that
overlapping component candidates are visible as suppressed components. The old
warning saying Warriner's 102 whitespace entries cannot contribute should not
appear. `source_lexicons` must remain unchanged and the self-test must still
verify the known SHA-256 hash.

## Beginner test 2A: NRC VAD v1 phrases

1. In **One poem**, paste `The alarm clock sounded.`
2. Select NRC VAD v1 and keep **Prefer the longest phrase** selected.
3. Analyze, then open **Evidence**.

Confirm that `alarm clock` is one included `exact_phrase`, its component words
are visible as suppressed components, and the old caution about 132 inactive
whitespace entries does not appear. The source checksum must remain unchanged.

## Beginner test 3: import and compare a folder

1. Create a small test folder outside `source_lexicons` with two UTF-8 files:
   `long.txt` and `short.txt`.
2. Put a repeated line or repeated vocabulary in `long.txt`; put a short lyric
   in `short.txt`.
3. Choose **Projects & corpus**, create a project, and under **Works & metadata**
   choose the test folder.
4. Confirm that both files appear as separate works. Add a collection label to
   each and save the metadata.
5. Under **Analyze & compare**, select both works and at least one VAD lexicon,
   then click **Analyze selected works**.
6. Wait for the complete-batch message.

Confirm that **Collection VAD** reports a token-weighted volume mean, a
pooled lexical-rating SD, work-weighted volume mean, across-poem mean SD,
poem-mean median/range, and the signed difference between means for valence,
arousal, and dominance. Under **Compare Individual Works**, switch the
within-work control between token and type and confirm that every poem row
shows VAD means beside within-poem population SDs. Confirm that
cumulative-load rows remain separate from means. Use collection, author, or
genre filters to narrow the completed batch.

## Beginner test 4: unmatched quality-control notes

1. Open **Unmatched QC** after the corpus batch completes.
2. Choose one word/lexicon/work observation.
3. Set its status to **needs mapping**, enter a short note, and save.
4. Switch to another workspace and return.

Confirm that the note persists. The interface must state that the note does not
change analysis results. Reanalysis may change which observations are current,
but the note remains keyed to project, work, lexicon, and normalized form.

## Beginner test 5: CSV and Word bundle

1. Open **Export** and download the corpus CSV and Word bundle.
2. Extract the ZIP, open `corpus_report.docx`, and inspect
   `corpus_vad_profiles.csv` and `corpus_vad_metrics.csv`.

Confirm that the narrative report names pooled lexical-rating SD and
across-poem mean SD separately. Confirm that the profiles CSV contains both
dispersion levels and poem-mean summary fields, while the metrics CSV retains
the work-level `vad_mean` and `vad_standard_deviation` rows. The bundle
includes text/version IDs and hashes but does not duplicate the complete
literary texts.

## Beginner test 6: Lexicon Explorer

1. Choose **Lexicon Explorer**.
2. Search `blood`; inspect original and normalized VAD, emotion results,
   uncertainty when available, and provenance.
3. Search an inflected form such as `burning`; verify exact and lemma-derived
   results are separately labeled.
4. Search a phrase; verify an exact phrase is distinguished from a derived
   component average.
5. Search a misspelling; verify nearby terms remain suggestions rather than
   substituted matches.
6. Optionally search `o'er` with user mapping `over`; verify the mapping is
   labeled lookup-only.

The installed resources do not include a separate ANEW lexicon. Explorer shows
the three installed VAD sources (Warriner and two NRC versions) plus NRC Emotion
and NRC Emotion Intensity.

## Beginner test 7: dual VAD reporting

1. In **One poem**, paste `It was not very dark, but it was bright.` and analyze
   it with at least one VAD lexicon.
2. Open **Overview** and **VAD profile**.
3. Confirm that **All matched observations** and **Stopwords excluded** are
   separately labeled and that the sensitivity table is filtered minus full.
4. Open **Evidence**, choose the excluded-only control, and inspect each
   stopword reason.
5. Confirm that `not` and `very` are marked as protected and remain in the
   filtered view, while ordinary matched stopwords such as `was` are excluded.
6. Download the ZIP and confirm the manifest/JSON include stopword source,
   version, active-list hash, protected terms, and both result views.

## Beginner test 8: custom stopword and safe deletion

1. Open the methodology settings, select custom stopwords, add a deliberately
   chosen test word, reanalyze, and confirm its exclusion is audited.
2. Remove that test word or restore the defaults when finished.
3. In a disposable corpus project, open **Project settings**.
4. Confirm that the delete button remains unavailable until the exact,
   case-sensitive project title is entered.
5. Delete the disposable project and confirm that another project, if present,
   remains untouched.

## Limitations

- Corpus aggregation is descriptive; it does not provide inferential tests or
  confidence intervals.
- Collection token weighting uses included matched observations. An activated
  multiword expression contributes one observation under the phrase policy.
- Work weighting gives one eligible poem-level mean per work; works without a
  score are omitted and counted, never neutralized.
- Quality-control mappings are documentation only in Phase 4. Scenario-bound
  mappings that change future analyses remain Phase 5 work.
- Lexicon Explorer cannot resolve polysemy, historical sense, metaphor, irony,
  or contextual meaning.
- Excel is a derived export. SQLite plus preserved source files and hashes are
  the local authoritative research state.
