# Design Stage 13 Validation

## Scope

Stage 13 changes interface structure and presentation only. It does not change
lexicon adapters, matching, calculations, stored analytical configuration,
project schema, source text, or established export contents.

## Automated contracts

The Stage 13 tests verify:

- application-level appearance round trips and safe malformed-file fallback;
- semantic Classic, Dark, Lavender, Ocean, Crimson, and Forest token mappings;
- legacy Light/System migration and reduced-motion media rules;
- WCAG-oriented primary/secondary text and focus contrast;
- module presets and their strict exclusion of advanced methodology keys;
- all four workspaces and dynamic Analyze Poem, Analyze Text, and Analyze Corpus
  terminology;
- grouped result-family navigation and collapsible module status sections;
- unchanged single-text analytical values and downloads;
- unchanged Project / Corpus database, review, batch, and deletion behavior;
- unchanged Lexicon Explorer controls and lookup behavior; and
- appearance changes that create no analysis result.

## Beginner interface check

1. Start VerseVAD with `start_versevad.bat`.
2. Confirm that the header shows the VerseVAD wordmark/version, all four
   workspaces, Appearance, Settings, and Help.
3. In **Appearance**, choose Classic, Dark, Lavender, Ocean, Crimson, and
   Forest. Confirm that controls, text, tables, alerts, tooltips, focus
   outlines, and borders remain readable.
4. Return to any color theme, close VerseVAD, reopen it, and confirm the saved
   choice.
5. In **Single Poem**, paste a short poem and enter a title. Confirm the live
   word/line/block orientation counts and optional bibliographic fields.
6. Choose **Literary**, click **Apply preset**, and confirm the visible module
   selections. Confirm that advanced thresholds did not change.
7. Click **Analyze Poem**. Confirm staged progress and the completed Overview.
8. Confirm the seven result families: Overview, Affective Evidence, Lexical
   Character, Sound & Form, Structure, Evidence & Diagnostics, Export & Help.
9. Open and close multiple analytical sections. Confirm that each label says
   Complete or Not selected and that closing a section does not invalidate the
   result.
10. Open **Other Text**. Confirm that the existing text has not been silently
    discarded, the action says **Analyze Text**, and prose cautions mark meter
    and rhyme experimental.
11. Open **Project / Corpus**. Confirm project status metrics, work
    search/author/collection filters, analysis status, corpus preset, and
    **Analyze Corpus**.
12. Open **Lexicon Explorer**. Search an established test word and confirm that
    the same all-resource fields and match methods remain available.

## Narrow-screen check

At approximately 768 CSS pixels:

- workspace navigation remains readable and horizontally accessible;
- body text does not shrink;
- header utilities remain usable;
- controls stack without overlap;
- tables retain horizontal access; and
- no analytical content is hidden solely because of width.

## Completion record

Completed on 2026-07-24:

- `252 passed` in the complete automated suite, including the design,
  appearance-preference, four-workspace, corpus, Explorer, export,
  documentation, and pre-existing analytical regressions;
- all ten direct synthetic demonstrations passed;
- all 11 local diagnostics passed;
- all five immutable affective source lexicons retained their expected hashes
  and passed read-only structural inspection;
- concreteness, SUBTLEX-US, Kuperman AoA, and the three-file CMUdict contracts
  all passed with their expected SHA-256 values;
- the offline dependency lock check passed with 86 resolved packages;
- in-app browser checks covered the four workspaces, a completed Single Poem
  Overview, an all-resource Explorer lookup, every current appearance theme,
  and a 768-pixel viewport with no horizontal page overflow;
- the responsive check found and then verified a fix for compressed header
  utilities, and browser diagnostics reported no interface errors;
- both Word guides rebuilt and passed structural/content tests; accessibility
  inspection reported no high-severity findings and four medium-severity
  layout-table advisories in each document; and
- the canonical DOCX renderer was attempted for both guides but could not run
  because LibreOffice/`soffice` is not installed. No visual-render success is
  claimed.
