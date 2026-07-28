from __future__ import annotations

import csv
import io
from pathlib import Path

from versevad.versemap.reference import (
    MANIFEST_FILENAME,
    RELEASE_FILENAME,
    build_reference_release,
    update_reference_release,
)


def _write_complete_poem(path: Path, lead: str = "A") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{lead} one two three four five\n"
        "Six seven eight nine ten\n"
        "Eleven twelve thirteen fourteen fifteen\n"
        "Sixteen seventeen eighteen nineteen twenty\n",
        encoding="utf-8",
    )


def _manifest_rows(payload: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


def test_release_identity_ignores_bom_and_line_ending_differences(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "reference"
    poem = source_root / "Poet Name" / "Poem.txt"
    poem.parent.mkdir(parents=True)
    poem.write_bytes(
        b"\xef\xbb\xbfOne two three four five\r\n"
        b"Six seven eight nine ten\r\n"
        b"Eleven twelve thirteen fourteen fifteen\r\n"
        b"Sixteen seventeen eighteen nineteen twenty\r\n"
    )

    first = build_reference_release(source_root)
    first_row = _manifest_rows(first.manifest_bytes)[0]
    poem.write_text(
        "One two three four five\n"
        "Six seven eight nine ten\n"
        "Eleven twelve thirteen fourteen fifteen\n"
        "Sixteen seventeen eighteen nineteen twenty\n",
        encoding="utf-8",
    )
    second = build_reference_release(source_root)
    second_row = _manifest_rows(second.manifest_bytes)[0]

    assert not first.errors
    assert first.release_id == second.release_id
    assert first_row["canonical_text_sha256"] == second_row["canonical_text_sha256"]
    assert first_row["source_sha256"] != second_row["source_sha256"]
    assert second_row["physical_line_count"] == "4"
    assert second_row["poet_name"] == "Poet Name"


def test_poem_id_is_path_stable_while_release_tracks_text_change(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "reference"
    poem = source_root / "Poet" / "Stable Name.txt"
    _write_complete_poem(poem)
    first = build_reference_release(source_root)

    _write_complete_poem(poem, lead="Changed")
    second = build_reference_release(source_root)

    assert _manifest_rows(first.manifest_bytes)[0]["poem_id"] == _manifest_rows(
        second.manifest_bytes
    )[0]["poem_id"]
    assert first.release_id != second.release_id


def test_duplicate_and_size_checks_are_nonblocking_warnings(tmp_path: Path) -> None:
    source_root = tmp_path / "reference"
    first = source_root / "Poet" / "First.txt"
    duplicate = source_root / "Another Poet" / "Copy.txt"
    first.parent.mkdir(parents=True)
    duplicate.parent.mkdir(parents=True)
    first.write_text("Tiny poem\n", encoding="utf-8")
    duplicate.write_text("Tiny poem\n", encoding="utf-8")

    result = build_reference_release(source_root)
    warning_codes = {warning.code for warning in result.warnings}
    rows = _manifest_rows(result.manifest_bytes)

    assert not result.errors
    assert warning_codes == {"duplicate_text", "suspiciously_short"}
    assert all("duplicate_text" in row["warning_codes"] for row in rows)
    assert all("suspiciously_short" in row["warning_codes"] for row in rows)


def test_invalid_utf8_and_empty_poems_block_generated_writes(tmp_path: Path) -> None:
    source_root = tmp_path / "reference"
    poet = source_root / "Poet"
    poet.mkdir(parents=True)
    (poet / "Invalid.txt").write_bytes(b"\xff\xfe\xfa")
    (poet / "Empty.txt").write_text(" \n\n", encoding="utf-8")

    result, current = update_reference_release(source_root)
    error_codes = {error.code for error in result.errors}

    assert not current
    assert error_codes == {"empty_poem", "no_poems", "not_utf8"}
    assert not (source_root / MANIFEST_FILENAME).exists()
    assert not (source_root / RELEASE_FILENAME).exists()


def test_update_and_check_mode_detect_stale_generated_files(tmp_path: Path) -> None:
    source_root = tmp_path / "reference"
    poem = source_root / "Poet" / "Poem.txt"
    _write_complete_poem(poem)

    result, current_before_write = update_reference_release(source_root)
    checked_result, current_after_write = update_reference_release(
        source_root, check=True
    )
    _write_complete_poem(poem, lead="Different")
    changed_result, current_after_change = update_reference_release(
        source_root, check=True
    )

    assert not current_before_write
    assert current_after_write
    assert checked_result.release_id == result.release_id
    assert not current_after_change
    assert changed_result.release_id != result.release_id


def test_tracked_reference_manifest_is_current() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source_root = repository_root / "resources" / "VerseMap_Reference_Corpus"

    result, current = update_reference_release(source_root, check=True)

    assert not result.errors
    assert current
