# Poetic Fingerprint Stage 14 Validation

## Automated coverage

Stage 14 adds regression and synthetic checks for:

- exact preservation of the Stage 6 candidate layer;
- all five base patterns and one-through-eight-foot inventory;
- contextual promotion, demotion, caesura, substitutions, ending allowances,
  alternatives, component scores, and missingness;
- style-profile separation from lexical stress;
- poem/stanza recurrence and generic alternating sequence;
- performance-aware CSV/plain-text exports;
- Single Poem and Project/Corpus use of the same meter module;
- bounded cache hit, miss, invalidation, corruption, eviction, disable, and
  concurrent-suppression behavior;
- PoetryID and pronunciation dependency-specific invalidation;
- on-demand export caching;
- safe corpus cancellation boundaries;
- benchmark harness smoke behavior;
- Streamlit candidate and performance-aware workflows.

The direct synthetic command is:

```powershell
.\.venv\Scripts\python.exe -c "from versevad.performance_meter_validation import run_synthetic_performance_meter_validation as r; print(r())"
```

The repeatable quick benchmark is:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_stage14.py --quick --repetitions 3
```

Add `--memory` for peak traced-memory observations. Timed benchmarks are not
ordinary unit-test gates.

## Beginner-facing interface check

1. Start VerseVAD and open **Single Poem**.
2. Enter a title and four copies of:
   `the stone the stone the stone the stone`
3. Select **Meter & rhythmic regularity**.
4. In advanced methodology, leave **Candidate meter only** selected and
   analyze. Confirm the nearest candidate is **Iambic tetrameter**.
5. Change **Meter analysis layer** to **Performance-aware realization**.
6. Leave **General English Verse** and **Standard** selected, then analyze.
7. Confirm the fixed result is still present and the added section shows:
   rhythmic organization, a primary realized candidate, coverage, confidence,
   stanza recurrence, raw lexical stress, candidate template, realized
   notation, substitutions, and an explanation.
8. Select **Detailed**, rerun, and inspect retained alternate readings and
   separate scoring components.
9. Open **Evidence & Diagnostics** and inspect operation timings and cache
   states.
10. Analyze again without changes. Confirm selected operations say **hit** and
    the result is unchanged.
11. Open **Export & Help**. Confirm no large audit ZIP is constructed until
    **Prepare downloads** is pressed.
12. Prepare downloads and verify the performance-aware ZIP contains the four
    always-added meter files. If a documented scholar revision was supplied,
    also verify the conditional `meter_scholar_revisions.csv`.
13. In **Settings**, inspect cache counts. Clear analysis cache, rerun, and
    confirm results remain unchanged while cache status reports recomputation.
14. Repeat the meter configuration in **Project / Corpus** and confirm each
    work's meter artifact includes the same added files.

## Interface and responsiveness review

The final visual review must cover:

- Single Poem, Project / Corpus, Other Text, and Lexicon Explorer;
- every current appearance theme;
- desktop and approximately 768-pixel-wide layouts;
- the settings popover, advanced meter controls, completed candidate and
  performance-aware reports, diagnostics, and prepared downloads;
- horizontal table/tab containment, header wrapping, focus visibility,
  readable missing values, reduced-motion CSS, and browser console errors.

Record any environment-limited check precisely; do not claim a visual or
document render that did not run.

## Completion record

Completed on 2026-07-24 before the final folder rename:

- all `285` automated tests passed in `58.77` seconds, including fixed-candidate
  equivalence, performance-aware meter, cache, corpus, export, public-release,
  missing-resource, interface, and Word-document regressions;
- all eleven direct synthetic demonstrations passed: Phase 1, Phase 2,
  concreteness, SUBTLEX-US frequency, Kuperman AoA, pronunciation, candidate
  meter, rhyme/sound, lexical style, PoetryID, and performance-aware meter;
- all twelve local diagnostics passed, including the Stage 14 meter safeguard;
- the five immutable affective source files passed read-only inspection with
  their expected SHA-256 values, and installed supplementary-resource
  contracts passed through the complete suite;
- the offline lock remained current at 86 packages and `uv sync --locked
  --offline` completed successfully;
- the repeatable final quick benchmark recorded warm unchanged medians of
  `1.1`, `2.1`, and `1.2` ms for the short Sound/Form, medium Complete, and
  long repeated-line Sound/Form fixtures respectively;
- an offline source distribution and wheel were built. The source archive
  contained 210 public files (886,232 bytes), retained only
  `resources/README.md` from the resource directory, and contained no local
  caches, lexicons, research data, projects, text, databases, or exports. The
  wheel contained the canonical GPL license and no research/private state;
- the in-app browser review covered desktop, 768-pixel, and 390-pixel widths;
  the available appearance themes; all four workspaces; and a completed
  performance-aware result without horizontal page overflow or application
  errors. After the final license/resource-notice additions, the complete
  Streamlit regression suite passed; a final browser reopen was blocked by the
  browser security policy, so no additional visual claim is made for that
  last reopen;
- both Word guides were rebuilt and passed structural/content tests. The
  accessible-callout revision removed the prior layout-table advisories, and
  the bundled accessibility audit reported zero findings for both documents;
  and
- the canonical DOCX renderer was attempted for both guides but could not
  start because LibreOffice/`soffice` is not installed. No page-image visual
  inspection is claimed.
