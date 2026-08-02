from __future__ import annotations

from pathlib import Path

import pytest

from versevad.reference_corpora import (
    ReferenceCorpusDescriptor,
    ReferenceCorpusError,
    add_user_reference_files,
    create_user_reference_corpus,
    delete_user_reference_corpus,
    list_reference_corpora,
    load_corpus_index,
    validate_reference_corpus,
)
from versevad.versemap.model import (
    MODEL_FILENAME,
    ModelFeature,
    POET_PROFILE_FILENAME,
    PROFILE_FILENAME,
    ReferencePoint,
    VerseMapReferenceIndex,
)
from versevad.ui.stage3 import (
    _corpus_browser_vad_diagnostic_frame,
    _corpus_profile_frames,
)


def test_corpus_browser_characteristicity_uses_full_space_centroid_distance() -> None:
    feature = ModelFeature(
        feature_id="vad_valence_mean",
        mean=0.5,
        population_sd=0.1,
        raw_mean=0.5,
        raw_population_sd=0.1,
        weight=1.0,
        loading_1=1.0,
        loading_2=0.0,
        available_reference_count=3,
    )
    points = tuple(
        ReferencePoint(
            point_id=f"poem-{index}",
            point_kind="poem",
            poet_id="poet",
            poet_name="Poet",
            title=title,
            relative_path=f"{title}.txt",
            source_sha256=str(index),
            coordinate_1=value,
            coordinate_2=0.0,
            values=(("vad_valence_mean", value),),
            browser_diagnostics=(
                (
                    "vad_valence_absolute_midpoint_deviation_per_observation",
                    value / 10,
                ),
                (
                    "vad_valence_average_deviation_from_poem_mean",
                    value / 20,
                ),
            ),
            vad_midpoint_matched_observations=10,
        )
        for index, (title, value) in enumerate(
            (("Centroid", 0.5), ("Nearby", 0.6), ("Distant", 0.9)),
            start=1,
        )
    )
    index = VerseMapReferenceIndex(
        source_root=Path("."),
        profile_id="versemap-standard-1.0",
        profile_build_id="test",
        reference_release_id="test",
        reference_release_sha256="test",
        model_id="test",
        explained_variance_1=1.0,
        explained_variance_2=0.0,
        features=(feature,),
        poems=points,
        poets=(),
    )

    summary, poems = _corpus_profile_frames(index)
    diagnostics = _corpus_browser_vad_diagnostic_frame(index.poems)

    assert summary.iloc[0]["Corpus Mean"] == pytest.approx(2 / 3)
    valence_diagnostics = diagnostics.loc[
        diagnostics["Dimension"] == "Valence"
    ]
    assert len(valence_diagnostics) == 3
    assert valence_diagnostics[
        "Average Deviation from Poem Mean"
    ].notna().all()
    by_title = poems.set_index("Poem")
    assert by_title.loc["Centroid", "Centroid Distance"] == pytest.approx(0.0)
    assert (
        by_title.loc["Centroid", "Characteristicity Percentile"]
        > by_title.loc["Distant", "Characteristicity Percentile"]
    )
    assert (
        by_title.loc["Distant", "Distinctiveness Percentile"]
        > by_title.loc["Centroid", "Distinctiveness Percentile"]
    )


def test_private_reference_corpus_lifecycle(tmp_path, monkeypatch) -> None:
    private_root = tmp_path / "reference-corpora"
    monkeypatch.setenv("VERSEVAD_REFERENCE_CORPORA_ROOT", str(private_root))

    descriptor = create_user_reference_corpus(
        "Invented Lyric Corpus",
        (
            ("Selected Folder/Poet A/First.txt", b"First invented poem line."),
            ("Selected Folder/Poet B/Second.txt", b"Second invented poem line."),
        ),
    )

    assert descriptor.display_name == "Invented Lyric Corpus"
    assert not descriptor.built_in
    assert (descriptor.source_root / "Poet A" / "First.txt").is_file()
    assert (descriptor.source_root / "Poet B" / "Second.txt").is_file()
    assert any(
        item.corpus_id == descriptor.corpus_id
        for item in list_reference_corpora()
    )

    result = validate_reference_corpus(descriptor)
    assert not result.errors
    assert result.poem_count == 2
    assert result.poet_count == 2

    updated = add_user_reference_files(
        descriptor,
        (("Poet A/Third.txt", b"A third invented poem."),),
    )
    assert updated.poem_count == 3

    with pytest.raises(ReferenceCorpusError, match="exact corpus name"):
        delete_user_reference_corpus(descriptor, confirmation="wrong")
    delete_user_reference_corpus(
        descriptor,
        confirmation=descriptor.display_name,
    )
    assert not descriptor.source_root.exists()


def test_reference_corpus_rejects_unsafe_or_invalid_uploads(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_REFERENCE_CORPORA_ROOT",
        str(tmp_path / "reference-corpora"),
    )
    with pytest.raises(ReferenceCorpusError):
        create_user_reference_corpus(
            "Unsafe Corpus",
            (("../outside.txt", b"Text"),),
        )
    with pytest.raises(ReferenceCorpusError, match="UTF-8"):
        create_user_reference_corpus(
            "Invalid Corpus",
            (("Poet/invalid.txt", b"\xff\xfe\x00"),),
        )


def test_unchanged_reference_index_is_parsed_once(
    tmp_path,
    monkeypatch,
) -> None:
    for filename in (MODEL_FILENAME, PROFILE_FILENAME, POET_PROFILE_FILENAME):
        (tmp_path / filename).write_text("first\n", encoding="utf-8")
    descriptor = ReferenceCorpusDescriptor(
        corpus_id="test",
        display_name="Test Corpus",
        source_root=tmp_path,
        built_in=False,
        index_available=True,
        poem_count=1,
        poet_count=1,
        release_id="release",
        model_id="model",
    )
    calls: list[object] = []
    sentinel = object()

    def fake_loader(source_root):
        calls.append(source_root)
        return sentinel

    monkeypatch.setattr(
        "versevad.reference_corpora.load_reference_index",
        fake_loader,
    )

    assert load_corpus_index(descriptor) is sentinel
    assert load_corpus_index(descriptor) is sentinel
    assert len(calls) == 1

    (tmp_path / PROFILE_FILENAME).write_text("changed\nrow\n", encoding="utf-8")
    assert load_corpus_index(descriptor) is sentinel
    assert len(calls) == 2
