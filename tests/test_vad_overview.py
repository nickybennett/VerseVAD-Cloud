import pandas as pd

from versevad.ui.comparison import _prefer_overview_vad_source
from versevad.ui.vad_overview import preferred_overview_vad_lexicon_id


def test_overview_vad_source_uses_fixed_priority() -> None:
    assert preferred_overview_vad_lexicon_id(
        ("warriner_vad_2013", "nrc_vad_v1", "nrc_vad_v2_1")
    ) == "nrc_vad_v2_1"
    assert preferred_overview_vad_lexicon_id(
        ("warriner_vad_2013", "nrc_vad_v1")
    ) == "nrc_vad_v1"
    assert preferred_overview_vad_lexicon_id(
        ("warriner_vad_2013",)
    ) == "warriner_vad_2013"


def test_comparison_overview_keeps_only_preferred_vad_source() -> None:
    frame = pd.DataFrame(
        {
            "Metric ID": [
                "vad.warriner_vad_2013.valence.mean",
                "vad.nrc_vad_v1.valence.mean",
                "vad.nrc_vad_v2_1.valence.mean",
                "concreteness.mean",
            ]
        }
    )

    filtered = _prefer_overview_vad_source(frame)

    assert filtered["Metric ID"].tolist() == [
        "vad.nrc_vad_v2_1.valence.mean",
        "concreteness.mean",
    ]
