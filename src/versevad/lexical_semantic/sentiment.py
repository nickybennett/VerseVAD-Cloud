"""Offline VADER polarity evidence with explicit scope and provenance."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from dataclasses import asdict, dataclass
from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from versevad import __version__
from versevad.core.modules import (
    ModuleCoverage,
    ModuleInput,
    ModuleMetric,
    ModuleProvenance,
    ModuleResult,
    ModuleWarning,
    ResultLayer,
    WarningSeverity,
)


VADER_PACKAGE_VERSION = importlib.metadata.version("vaderSentiment")
VADER_CITATION = (
    "Hutto, C. J., & Gilbert, E. E. (2014). VADER: A Parsimonious "
    "Rule-based Model for Sentiment Analysis of Social Media Text. ICWSM 8(1). "
    "https://doi.org/10.1609/icwsm.v8i1.14550"
)


@dataclass(frozen=True)
class VaderSentimentConfiguration:
    """Published conventional compound-score thresholds."""

    negative_maximum: float = -0.05
    positive_minimum: float = 0.05
    scenario_id: str = "vader-sentiment-v1"

    def __post_init__(self) -> None:
        if not -1 <= self.negative_maximum < self.positive_minimum <= 1:
            raise ValueError("VADER thresholds must be ordered within -1 to 1.")
        if not self.scenario_id.strip():
            raise ValueError("A VADER scenario requires a stable ID.")

    @property
    def configuration_id(self) -> str:
        payload = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        )
        return "vader-config-v1:" + hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:16]


@dataclass(frozen=True)
class VaderScore:
    positive_proportion: float
    neutral_proportion: float
    negative_proportion: float
    compound_score: float
    threshold_label: str

    def __post_init__(self) -> None:
        proportions = (
            self.positive_proportion,
            self.neutral_proportion,
            self.negative_proportion,
        )
        if any(not 0 <= value <= 1 for value in proportions):
            raise ValueError("VADER proportions must be between zero and one.")
        if abs(sum(proportions) - 1) > 0.002:
            raise ValueError("VADER proportions must sum to approximately one.")
        if not -1 <= self.compound_score <= 1:
            raise ValueError("The VADER compound score must be between -1 and 1.")


@dataclass(frozen=True)
class VaderSegmentScore:
    segment_id: str
    ordinal: int
    source_text: str
    line_numbers: tuple[int, ...]
    score: VaderScore


@dataclass(frozen=True)
class VaderSentimentAnalysisResult:
    module_result: ModuleResult
    configuration: VaderSentimentConfiguration
    document_score: VaderScore
    sentence_scores: tuple[VaderSegmentScore, ...]
    package_version: str
    citation: str


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def _label(score: float, configuration: VaderSentimentConfiguration) -> str:
    if score >= configuration.positive_minimum:
        return "positive"
    if score <= configuration.negative_maximum:
        return "negative"
    return "neutral"


def _score(text: str, configuration: VaderSentimentConfiguration) -> VaderScore:
    values = _analyzer().polarity_scores(text)
    return VaderScore(
        positive_proportion=float(values["pos"]),
        neutral_proportion=float(values["neu"]),
        negative_proportion=float(values["neg"]),
        compound_score=float(values["compound"]),
        threshold_label=_label(float(values["compound"]), configuration),
    )


def _metrics(
    document_score: VaderScore,
    sentence_scores: tuple[VaderSegmentScore, ...],
) -> tuple[ModuleMetric, ...]:
    rows = [
        ModuleMetric(
            metric_id=f"vader.document.{name}",
            value=value,
            layer=ResultLayer.COMPUTED_SUMMARY,
            unit=unit,
            denominator=denominator,
            note=note,
        )
        for name, value, unit, denominator, note in (
            (
                "positive_proportion",
                document_score.positive_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "Does not include VADER's rule-based word-order adjustments.",
            ),
            (
                "neutral_proportion",
                document_score.neutral_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "Does not mean that unmatched poetic context is emotionally neutral.",
            ),
            (
                "negative_proportion",
                document_score.negative_proportion,
                "proportion",
                "VADER raw lexical polarity categorization",
                "Does not include VADER's rule-based word-order adjustments.",
            ),
            (
                "compound_score",
                document_score.compound_score,
                "normalized weighted composite (-1 to 1)",
                "complete preserved text",
                "Includes VADER's rule-based adjustments.",
            ),
            (
                "threshold_label",
                document_score.threshold_label,
                "conventional threshold label",
                "document compound score",
                "Uses the configured conventional thresholds; it is not a poem-emotion diagnosis.",
            ),
        )
    ]
    for segment in sentence_scores:
        rows.append(
            ModuleMetric(
                metric_id="vader.sentence.compound_score",
                value=segment.score.compound_score,
                layer=ResultLayer.COMPUTED_SUMMARY,
                scope="sentence",
                scope_id=segment.segment_id,
                unit="normalized weighted composite (-1 to 1)",
                denominator="one model-segmented sentence",
                note=f"Sentence {segment.ordinal}: {segment.source_text}",
            )
        )
    return tuple(rows)


class VaderSentimentModule:
    """Apply the bundled VADER lexicon and rules without a network request."""

    name = "vader_sentiment"
    version = "1.0.0"

    def analyze(self, module_input: ModuleInput) -> ModuleResult:
        return self.analyze_detailed(module_input).module_result

    def analyze_detailed(
        self,
        module_input: ModuleInput,
        configuration: VaderSentimentConfiguration | None = None,
    ) -> VaderSentimentAnalysisResult:
        configuration = configuration or VaderSentimentConfiguration()
        poem = module_input.poem_document
        if poem is None:
            raise ValueError(
                "VADER sentiment analysis requires the shared processing record."
            )
        document_score = _score(module_input.document.original_text, configuration)
        sentence_scores = tuple(
            VaderSegmentScore(
                segment_id=sentence.sentence_id,
                ordinal=sentence.ordinal,
                source_text=sentence.raw_text,
                line_numbers=sentence.line_numbers,
                score=_score(sentence.raw_text, configuration),
            )
            for sentence in poem.sentences
            if sentence.raw_text.strip()
        )
        warnings = (
            ModuleWarning(
                code="vader.domain_caution",
                message=(
                    "VADER was designed and validated for social-media sentiment. "
                    "Poetic ambiguity, persona, irony, quotation, historical usage, "
                    "and lineation can make its polarity evidence misleading."
                ),
            ),
            ModuleWarning(
                code="vader.not_emotion_classification",
                message=(
                    "Positive, neutral, and negative are rule-based polarity outputs, "
                    "not declarations of the poem's emotion or a reader's response."
                ),
                severity=WarningSeverity.INFORMATION,
            ),
        )
        provenance = ModuleProvenance(
            software_version=__version__,
            source_text_sha256=module_input.document.text_sha256,
            preprocessing_recipe=module_input.preprocessing.recipe_id,
            pipeline_name=module_input.preprocessing.pipeline_name,
            pipeline_version=module_input.preprocessing.pipeline_version,
            configuration_id=configuration.configuration_id,
            scenario_id=configuration.scenario_id,
            lookup_policy=(
                f"Offline vaderSentiment {VADER_PACKAGE_VERSION}; complete preserved "
                "text is scored once and model-segmented sentences are scored separately."
            ),
            inclusion_policy=(
                "VADER evaluates the supplied text, including punctuation, casing, "
                "negation, degree modifiers, and contrastive conjunctions. Its pos, "
                "neu, and neg proportions are raw lexical-category ratios; compound "
                "also applies VADER's rules."
            ),
            resources=(),
        )
        identity = json.dumps(
            {
                "text_sha256": module_input.document.text_sha256,
                "configuration": configuration.configuration_id,
                "vader_package": VADER_PACKAGE_VERSION,
                "score": asdict(document_score),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        module_result = ModuleResult(
            result_id="vader-result-v1:"
            + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
            module_name=self.name,
            module_version=self.version,
            text_id=module_input.document.text_id,
            text_version_id=module_input.document.text_version_id,
            metrics=_metrics(document_score, sentence_scores),
            coverage=(
                ModuleCoverage.from_counts(
                    coverage_id="vader.scored_text_segments",
                    eligible_count=1 + len(sentence_scores),
                    matched_count=1 + len(sentence_scores),
                    unit="document and nonblank model-segmented sentences",
                    note=(
                        "This is scorer-output coverage, not lexical match coverage; "
                        "VADER may categorize unrecognized material as neutral."
                    ),
                ),
            ),
            warnings=warnings,
            provenance=provenance,
        )
        return VaderSentimentAnalysisResult(
            module_result=module_result,
            configuration=configuration,
            document_score=document_score,
            sentence_scores=sentence_scores,
            package_version=VADER_PACKAGE_VERSION,
            citation=VADER_CITATION,
        )
