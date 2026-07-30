from pathlib import Path

from versevad.ui.profiles import (
    apply_profile_settings,
    delete_custom_profile,
    load_custom_profiles,
    save_custom_profile,
    snapshot_profile_settings,
)


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
