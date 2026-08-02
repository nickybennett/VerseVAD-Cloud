from pathlib import Path

from versevad.ui.profiles import (
    apply_profile_settings,
    delete_custom_profile,
    load_custom_profiles,
    normalize_profile_settings,
    save_custom_profile,
    snapshot_profile_settings,
    update_custom_profile,
)


def test_legacy_candidate_meter_label_is_migrated_without_changing_layer() -> None:
    assert normalize_profile_settings(
        {"meter_analysis_mode": "Candidate meter only (validated default)"}
    ) == {
        "meter_analysis_mode": "Candidate meter only (fixed-template layer)"
    }


def test_profile_snapshot_excludes_text_metadata_and_results() -> None:
    state = {
        "selected_lexicons": ["nrc_vad_v2_1"],
        "include_poetry_id": True,
        "single_stopword_mode": "Exclude stopwords",
        "poem_text": "Private poem",
        "poem_title": "Private title",
        "text_author": "Private author",
        "pronunciation_overrides": "private override",
        "workspace": object(),
    }

    snapshot = snapshot_profile_settings(state)

    assert snapshot == {
        "include_poetry_id": True,
        "selected_lexicons": ["nrc_vad_v2_1"],
        "single_stopword_mode": "Exclude stopwords",
    }


def test_custom_profiles_round_trip_and_apply_without_touching_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profiles.json"
    saved = save_custom_profile(
        "Close reading lab",
        {
            "selected_lexicons": ["nrc_vad_v2_1"],
            "include_concreteness": True,
            "poem_text": "Never save this",
        },
        description="Shared seminar configuration",
        base_profile="Computational Close Reading",
        path=path,
    )
    loaded = load_custom_profiles(path)

    assert saved.name == "Close reading lab"
    assert loaded[saved.name].description == "Shared seminar configuration"
    assert "poem_text" not in loaded[saved.name].settings

    target = {"poem_text": "Keep this poem", "include_concreteness": False}
    apply_profile_settings(target, loaded[saved.name].settings)
    assert target["poem_text"] == "Keep this poem"
    assert target["include_concreteness"] is True

    assert delete_custom_profile(saved.name, path=path)
    assert load_custom_profiles(path) == {}
    assert not delete_custom_profile(saved.name, path=path)


def test_custom_profile_update_can_rename_and_preserves_creation_time(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profiles.json"
    original = save_custom_profile(
        "Seminar",
        {"include_concreteness": True},
        description="First description",
        path=path,
    )

    updated = update_custom_profile(
        "Seminar",
        "Seminar Revised",
        {"include_concreteness": False, "include_meter": True},
        description="Updated description",
        base_profile="Sound and Prosody",
        path=path,
    )
    loaded = load_custom_profiles(path)

    assert updated.created_at == original.created_at
    assert updated.updated_at >= original.updated_at
    assert set(loaded) == {"Seminar Revised"}
    assert loaded[updated.name].description == "Updated description"
    assert loaded[updated.name].base_profile == "Sound and Prosody"
    assert loaded[updated.name].settings == {
        "include_concreteness": False,
        "include_meter": True,
    }


def test_custom_profile_update_rejects_name_collision(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    save_custom_profile("First", {"include_meter": True}, path=path)
    save_custom_profile("Second", {"include_meter": False}, path=path)

    try:
        update_custom_profile(
            "First",
            "Second",
            {"include_meter": True},
            path=path,
        )
    except ValueError as error:
        assert "already uses that name" in str(error)
    else:
        raise AssertionError("Expected a duplicate-name update to fail.")
