# Third-Party Notices

VerseVAD source code and documentation are GPL-3.0-only. Bundled or installed
third-party software and data retain their own licenses.

## Open English WordNet 2025+

VerseVAD redistributes a losslessly compressed, pre-indexed database derived
from Open English WordNet 2025+ for offline Lexicon Explorer lookup.

Copyright (c) 2019-present, the Open English WordNet Team.

Open English WordNet is licensed under Creative Commons Attribution 4.0
International and incorporates material from Princeton WordNet under the
Princeton WordNet license. VerseVAD's technical transformation changes storage
format only; definitions, examples, lemmas, identifiers, and relations are not
rewritten.

- Project: <https://github.com/globalwordnet/english-wordnet>
- License: <https://creativecommons.org/licenses/by/4.0/>
- Packaged license and attribution:
  [`resources/open_english_wordnet/`](resources/open_english_wordnet/)
- Citation: McCrae, John P., Alexandre Rademaker, Francis Bond, Ewa Rudnicka,
  and Christiane Fellbaum. 2019. “English WordNet 2019 — An Open-Source
  WordNet for English.” *Proceedings of the 10th Global WordNet Conference*,
  245–252. <https://aclanthology.org/2019.gwc-1.31>

## `wn` Python library

VerseVAD uses `wn` 1.1.0 to query the packaged Open English WordNet database.
`wn` is distributed under the MIT License. Project and license information:
<https://github.com/goodmami/wn>.

## Other research resources

The affective lexicons, lexical norms, language model, pronunciation data,
and other research resources used by VerseVAD retain their own licenses and
citations. See [`docs/resource-installation.md`](docs/resource-installation.md)
and [`docs/lexicons.md`](docs/lexicons.md). VerseVAD's GPL license does not
relicense those materials.
