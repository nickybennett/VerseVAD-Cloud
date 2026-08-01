from __future__ import annotations

from versevad.ui.training import COURSES, TRAINING_ROOT


def test_public_training_package_contains_only_learner_documents() -> None:
    root = TRAINING_ROOT
    expected = {
        filename
        for course in COURSES
        for filename in (course.manual_filename, course.assignment_filename)
    }

    assert len(COURSES) == 4
    assert len(expected) == 8
    assert {path.name for path in root.glob("*.docx")} == expected
    assert all(path.is_file() for path in (root / name for name in expected))
    assert not any(
        marker in path.name.casefold()
        for path in root.iterdir()
        for marker in ("answer", "key", "rubric")
    )


def test_training_download_paths_remain_under_public_resource_root() -> None:
    root = TRAINING_ROOT.resolve()
    for course in COURSES:
        for filename in (course.manual_filename, course.assignment_filename):
            assert (root / filename).resolve().parent == root
