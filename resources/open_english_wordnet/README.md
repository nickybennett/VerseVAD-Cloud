# Open English WordNet 2025+

VerseVAD packages Open English WordNet 2025+ for offline dictionary lookup in
Lexicon Explorer. Ordinary lookups do not contact an external API.

## Packaged artifact

- `oewn-2025-plus-wn.db.xz` is a lossless XZ-compressed SQLite database built
  by `wn` 1.1.0 from the official Open English WordNet 2025+ WN-LMF release.
- VerseVAD expands this file into its ignored `.runtime/` directory on first
  dictionary use. The packaged source remains unchanged.
- Packaged artifact SHA-256:
  `c5f6259591247d1bf1a81454553599d4c5eb41a7f9d668de46e41ab3b8f5806f`.
- Expanded `wn.db` SHA-256:
  `6c3c5f0376be143775026ce3f39c802359a1a51d431e7dc0c97df0f3e5058201`.
- Official compressed WN-LMF source SHA-256:
  `31f4af16c54b532fd5484d4cc33aee588a31bb5b70683ae8197842fde5b586bc`.
- Official source URL:
  <https://en-word.net/static/english-wordnet-2025-plus.xml.gz>.

The database transformation changes storage format only. VerseVAD does not
rewrite definitions, examples, sense identifiers, lemmas, or semantic
relations.

## Attribution and license

Open English WordNet is copyright the Open English WordNet Team and is
released under Creative Commons Attribution 4.0 International. It is derived
from Princeton WordNet, whose underlying license also applies. Retain:

- `OPEN_ENGLISH_WORDNET_LICENSE.md`;
- `PRINCETON_WORDNET_LICENSE.txt`; and
- `citation.bib`.

Canonical citation:

> McCrae, John P., Alexandre Rademaker, Francis Bond, Ewa Rudnicka, and
> Christiane Fellbaum. 2019. “English WordNet 2019 — An Open-Source WordNet
> for English.” *Proceedings of the 10th Global WordNet Conference*, 245–252.

Project: <https://github.com/globalwordnet/english-wordnet>

License: <https://creativecommons.org/licenses/by/4.0/>

Dictionary senses are decontextualized lexical entries. Their presence and
source ordering do not establish which sense is active in a poem, phrase, or
historical usage.
