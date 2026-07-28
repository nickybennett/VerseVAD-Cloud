# VerseVAD Development Instructions

## Mission

Build VerseVAD as local, auditable research software for descriptive affective
lexicon analysis of literary texts. The primary user is a humanities scholar,
not a programmer. Preserve methodological choices instead of hiding them.

## Non-negotiable safeguards

- Treat every file under `source_lexicons/` as immutable source material.
- Never rename, rewrite, clean, merge, or redistribute a supplied lexicon.
- Read source lexicons in place and record SHA-256 hashes. Store derived data
  outside `source_lexicons/` and retain a link to the exact source hash.
- Never commit lexicons, literary corpora, project databases, exports, or
  backups to source control, except the explicitly curated public-domain
  VerseMap reference corpus under `resources/VerseMap_Reference_Corpus/`.
- Do not send texts, lexicons, project data, or results to external services.
- Preserve imported text exactly. Perform normalization only in a separate,
  traceable processing representation.
- Never give unmatched tokens a neutral numeric value.
- Never silently replace an exact surface-form match with a lemma match.

## Scholarly language

Describe results as lexical evidence, for example, "mean normative valence of
matched tokens" or "fear-associated vocabulary." Do not claim to identify the
emotion of a poem, the speaker, the reader, or the author's intention.

Keep these concepts distinct in code, storage, interface copy, and exports:

- original text and text version;
- token occurrence, surface form, normalized form, and lemma;
- lexicon entry and source value;
- matching method and analysis scenario;
- normative rating or association and contextual interpretation.

## Development workflow

- Work in the phases recorded in `PLANS.md`; update the checklist continuously.
- Add tests before marking a calculation or migration complete.
- Use small synthetic fixtures with hand-calculated expected results.
- Keep the analysis engine independent of Streamlit so it can be tested without
  the interface.
- Keep lexicon-specific parsing inside adapters. Adding an adapter must not
  require changes throughout the analysis engine.
- Use stable IDs, transactional database writes, explicit migrations, and
  immutable completed analysis runs.
- Present plain-language errors first and retain technical detail for copying.
- Record active lexicon, source hash, adapter version, preprocessing recipe,
  scenario, software version, and inclusion decisions on every analysis run.

## Completion checks

Before completing a phase:

1. run the full automated test suite;
2. run the synthetic validation examples;
3. verify documentation against current behavior;
4. update `PLANS.md` and `CHANGELOG.md`;
5. report limitations and exact beginner-friendly test steps;
6. create a source-control checkpoint when Git is available.
