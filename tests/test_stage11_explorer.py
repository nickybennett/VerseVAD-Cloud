from __future__ import annotations

import pyarrow as pa

from versevad.adapters.cmudict import CMUDictEntry, CMUPronunciation
from versevad.adapters.concreteness import ConcretenessEntry
from versevad.adapters.kuperman_aoa import KupermanAoAEntry
from versevad.adapters.subtlex_us import SubtlexUsEntry
from versevad.explorer import (
    LexiconExplorerResult,
    SupplementaryEvidenceValue,
    SupplementaryExplorerEntry,
    SupplementaryExplorerResource,
    explore_loaded_lexicons,
)
from versevad.ui.explorer import _supplementary_evidence_frame


class _Lookup:
    def __init__(self, entry):
        self.entry = entry

    def lookup(self, _value):
        return self.entry


def _resource(kind: str, entry) -> SupplementaryExplorerResource:
    return SupplementaryExplorerResource(
        resource_id=f"{kind}-resource",
        resource=kind.title(),
        construct=kind,
        state="available",
        status_message="Available locally.",
        lexicon=_Lookup(entry),
        source_file=f"{kind}.data",
        source_sha256="a" * 64,
        version="synthetic-v1",
        adapter_version="1.0.0",
        citation="Synthetic test source.",
    )


def test_explorer_reports_every_available_supplementary_source(
    preprocessor,
) -> None:
    resources = (
        _resource(
            "concreteness",
            ConcretenessEntry(
                source_term="stone",
                lookup_form="stone",
                source_row=2,
                is_multiword=False,
                mean=4.8,
                standard_deviation=0.4,
                unknown_count=1,
                rater_count=30,
                percent_known=96.7,
                subtlex_count=100,
            ),
        ),
        _resource(
            "frequency",
            SubtlexUsEntry(
                source_term="stone",
                lookup_form="stone",
                source_row=3,
                frequency_count=500,
                contextual_diversity_count=200,
                lowercase_frequency_count=480,
                lowercase_contextual_diversity_count=195,
                frequency_per_million=10.5,
                log10_frequency=2.7,
                contextual_diversity_percent=42.0,
                log10_contextual_diversity=2.3,
                dominant_source_pos="Noun",
                dominant_source_pos_frequency=450,
                dominant_source_pos_proportion=0.9,
                all_source_pos="Noun.Verb",
                all_source_pos_frequencies="450.50",
                zipf_value=4.25,
            ),
        ),
        _resource(
            "aoa",
            KupermanAoAEntry(
                source_term="stone",
                lookup_form="stone",
                source_row=4,
                occurrence_total=25,
                numeric_response_count=24,
                frequency_per_million=10.0,
                mean_age=5.5,
                standard_deviation=1.2,
                source_dunno_value=1.0,
            ),
        ),
        _resource(
            "pronunciation",
            CMUDictEntry(
                source_term="stone",
                lookup_form="stone",
                pronunciations=(
                    CMUPronunciation(
                        source_term="stone",
                        lookup_form="stone",
                        variant_number=1,
                        phones=("S", "T", "OW1", "N"),
                        stress_pattern="1",
                        syllable_count=1,
                        source_line=5,
                    ),
                ),
            ),
        ),
    )

    result = explore_loaded_lexicons(
        "stone",
        (),
        preprocessor,
        supplementary_resources=resources,
    )

    assert {row.construct for row in result.supplementary_entries} == {
        "concreteness",
        "frequency",
        "aoa",
        "pronunciation",
    }
    values = {
        (row.construct, value.field): value.value
        for row in result.supplementary_entries
        for value in row.values
    }
    assert values[("concreteness", "Mean rating")] == 4.8
    assert values[("frequency", "Zipf value")] == 4.25
    assert values[("aoa", "Mean AoA")] == 5.5
    assert values[("pronunciation", "ARPAbet phones")] == "S T OW1 N"
    assert values[("pronunciation", "Lexical stress")] == "1"
    assert all(row.match_method == "exact entry" for row in result.supplementary_entries)
    assert result.vader_sentiment is not None
    assert result.vader_sentiment.document_score.threshold_label == "neutral"
    assert result.readability is not None
    assert result.readability.summary.word_count == 1
    assert result.readability.summary.syllable_count == 1
    assert result.readability.word_audit[0].syllable_method.startswith(
        "bundled CMUdict"
    )


def test_explorer_keeps_unmatched_and_unavailable_resources_explicit(
    preprocessor,
) -> None:
    resources = (
        SupplementaryExplorerResource(
            resource_id="missing",
            resource="Missing Resource",
            construct="concreteness",
            state="missing",
            status_message="Expected local file was not found.",
            lexicon=None,
            source_file="expected.xlsx",
            source_sha256="",
            version="v1",
            adapter_version="1.0.0",
            citation="Source citation.",
        ),
        SupplementaryExplorerResource(
            resource_id="no-entry",
            resource="Available Resource",
            construct="frequency",
            state="available",
            status_message="Available locally.",
            lexicon=_Lookup(None),
            source_file="frequency.xlsx",
            source_sha256="b" * 64,
            version="v1",
            adapter_version="1.0.0",
            citation="Source citation.",
        ),
    )

    result = explore_loaded_lexicons(
        "nonceword",
        (),
        preprocessor,
        supplementary_resources=resources,
    )

    by_resource = {
        row.resource_id: row for row in result.supplementary_entries
    }
    assert by_resource["missing"].status == "resource_unavailable"
    assert by_resource["no-entry"].status == "unmatched"
    assert all(row.values == () for row in result.supplementary_entries)


def test_supplementary_display_values_are_arrow_safe_text() -> None:
    result = LexiconExplorerResult(
        query="bright",
        normalized_query="bright",
        processing_lemma="bright",
        processing_pos="ADJ",
        entries=(),
        supplementary_entries=(
            SupplementaryExplorerEntry(
                resource_id="frequency-resource",
                resource="SUBTLEX-US",
                construct="frequency",
                status="matched",
                status_message="Available locally.",
                matched_term="bright",
                match_method="exact entry",
                variant_label="",
                source_rows=(2,),
                values=(
                    SupplementaryEvidenceValue(
                        field="Zipf value",
                        value=4.25,
                        unit="SUBTLEX-US Zipf",
                    ),
                    SupplementaryEvidenceValue(
                        field="Dominant source POS",
                        value="Adjective",
                    ),
                    SupplementaryEvidenceValue(
                        field="Multiword source entry",
                        value=False,
                    ),
                    SupplementaryEvidenceValue(
                        field="Unavailable field",
                        value=None,
                    ),
                ),
                source_file="SUBTLEXus74286wordstextversion.txt",
                source_sha256="a" * 64,
                source_hashes=(),
                version="synthetic-v1",
                adapter_version="1.0.0",
                citation="Synthetic test source.",
            ),
        ),
        component_averages=(),
        comparisons=(),
        suggestions=(),
        notices=(),
    )

    frame = _supplementary_evidence_frame(result)

    assert frame["Value"].tolist() == ["4.25", "Adjective", "False", "—"]
    assert all(isinstance(value, str) for value in frame["Value"])
    pa.Table.from_pandas(frame)
