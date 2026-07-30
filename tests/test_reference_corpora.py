from __future__ import annotations

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
    POET_PROFILE_FILENAME,
    PROFILE_FILENAME,
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
