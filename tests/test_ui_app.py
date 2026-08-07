import ast
from pathlib import Path

from streamlit.testing.v1 import AppTest

import versevad.application as application_services
from versevad.comparison import PoemComparisonSet
from versevad.corpus import CorpusAnalysisConfiguration, analyze_corpus
from versevad.db.repository import CorpusTextImport, ProjectRepository
from versevad.preprocessing import SpacyEnglishPreprocessor
from versevad.research_library import ResearchLibraryRepository
from versevad.ui.navigation import ROUTES
from versevad.ui.profile_management import custom_profile_label
from versevad.ui.profiles import load_custom_profiles, save_custom_profile
from versevad.ui.preferences import AppearanceMode, load_preferences
from versevad.ui.inherited_form import render_inherited_form


APP_PATH = Path(__file__).parents[1] / "src" / "versevad" / "ui" / "app.py"
REPORT_SECTIONS = [
    "Overview",
    "Affective Evidence",
    "Lexical Character, Imagery & Embodiment",
    "Sound & Form",
    "Structure",
    "VerseMap",
    "Interactive Annotation",
    "Evidence & Diagnostics",
    "Export & Help",
]
CORPUS_SECTIONS = [
    "Works & Metadata",
    "Language Profile",
    "Analyze & Compare",
    "VerseMap",
    "Review & Scenarios",
    "Export",
    "Project Settings",
]
PERSONAL_CORPUS_SECTIONS = [
    "Poems & Metadata",
    "Poem Detail",
    "Corpus Analysis",
    "Language Profile",
    "VerseMap",
    "Review & Scenarios",
    "Export",
    "Corpus Settings",
]


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def _open_workspace(app: AppTest, workspace: str) -> AppTest:
    """Select a route through the shell's supported AppTest override."""

    app.session_state["_workspace_route_override"] = workspace
    return app.run(timeout=30)


def _section_navigation(app: AppTest, label: str):
    control_type = (
        "selectbox"
        if label.casefold() == "report section"
        else "button_group"
    )
    return next(
        control
        for control in app.get(control_type)
        if control.label == label
    )


def test_every_registered_workspace_opens_without_an_exception(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_DATABASE_PATH",
        str(tmp_path / "projects.sqlite3"),
    )
    monkeypatch.setenv(
        "VERSEVAD_PERSONAL_CORPUS_DATABASE_PATH",
        str(tmp_path / "personal-corpus.sqlite3"),
    )
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()

    for workspace in dict.fromkeys(route.workspace_id for route in ROUTES):
        _open_workspace(app, workspace)
        assert not app.exception, f"{workspace}: {app.exception}"


def test_final_library_and_learning_workspaces_are_live_and_have_sidebars(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    monkeypatch.setenv(
        "VERSEVAD_REFERENCE_CORPORA_ROOT",
        str(tmp_path / "reference-corpora"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()

    for workspace in (
        "Reference Corpora",
        "VerseMap",
        "Form Library",
        "Corpus Browser",
        "Documentation",
        "Methodology",
        "Training",
    ):
        _open_workspace(app, workspace)
        assert not app.exception, f"{workspace}: {app.exception}"
        assert any(heading.value == workspace for heading in app.title)
        assert "Quick Navigation" in {
            panel.label for panel in app.expander
        }
        assert not any(
            "scheduled implementation stage" in message.value
            for message in app.info
        )


def test_hosted_reference_corpora_are_read_only(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("VERSEVAD_CLOUD_DEPLOYMENT", "1")
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    monkeypatch.setenv(
        "VERSEVAD_REFERENCE_CORPORA_ROOT",
        str(tmp_path / "reference-corpora"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()
    _open_workspace(app, "Reference Corpora")
    section = _section_navigation(app, "Report Section")
    section.set_value("Create & Maintain")
    app.run(timeout=30)

    assert not app.exception
    assert any(
        "provides the built-in corpus read-only" in message.value
        for message in app.info
    )
    assert "Create and Validate Corpus" not in {
        button.label for button in app.button
    }
    assert "Delete Permanently" not in {
        button.label for button in app.button
    }


def test_analysis_library_does_not_expose_legacy_drafts(
    tmp_path,
    monkeypatch,
) -> None:
    library_path = tmp_path / "analysis-library.sqlite3"
    monkeypatch.setenv("VERSEVAD_RESEARCH_LIBRARY_PATH", str(library_path))
    repository = ResearchLibraryRepository(library_path)
    repository.save_revision(
        parent_type="draft",
        workspace_id="Single Poem",
        title="Recoverable draft",
        software_version="1.0.0",
        payload={
            "kind": "text_draft",
            "workspace_id": "Single Poem",
            "ui_state": {
                "poem_title": "Recoverable draft",
                "poem_text": "A restored line.",
                "module_preset": "Custom",
                "apply_module_preset": False,
                "load_match_evidence": False,
            },
        },
        storage_mode="draft",
        status="draft",
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()
    _open_workspace(app, "Analysis Library")
    section = next(
        field for field in app.selectbox if field.label == "Library Section"
    )

    assert not app.exception
    assert list(section.options) == ["Saved Analyses", "Notebook"]
    assert "Recover draft" not in {button.label for button in app.button}


def test_analysis_library_deletes_the_selected_item_by_id(
    tmp_path,
    monkeypatch,
) -> None:
    library_path = tmp_path / "analysis-library.sqlite3"
    monkeypatch.setenv("VERSEVAD_RESEARCH_LIBRARY_PATH", str(library_path))
    repository = ResearchLibraryRepository(library_path)
    item, _, _ = repository.save_revision(
        parent_type="analysis",
        workspace_id="Single Poem",
        title='"The Red Wheelbarrow"',
        author="William Carlos Williams",
        software_version="1.0.0",
        payload={"kind": "historical_test"},
        storage_mode="full",
        status="saved",
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()
    _open_workspace(app, "Analysis Library")

    confirmation = next(
        checkbox
        for checkbox in app.checkbox
        if checkbox.label
        == 'Permanently delete this saved item: "The Red Wheelbarrow"'
    )
    assert not _button(app, "Delete permanently").disabled
    confirmation.set_value(True)
    app.run(timeout=30)
    _button(app, "Delete permanently").click()
    app.run(timeout=30)

    assert not app.exception
    assert all(
        saved.item_id != item.item_id
        for saved in repository.list_items()
    )


def test_saved_ui_state_rejects_action_and_upload_widget_keys() -> None:
    from versevad.ui.research import (
        _is_nonrestorable_ui_state_key,
        _is_restorable_ui_state_key,
    )

    assert _is_nonrestorable_ui_state_key("one_poem_restore_stopwords")
    assert _is_nonrestorable_ui_state_key("one_poem_import_stopwords")
    assert _is_nonrestorable_ui_state_key("uploaded_poem")
    assert _is_nonrestorable_ui_state_key("future_action_without_known_name")
    assert not _is_nonrestorable_ui_state_key(
        "one_poem_custom_stopword_additions"
    )
    assert _is_restorable_ui_state_key(
        "compare_poem-3_text",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "compare_analysis_profile",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "compare_config_minimum_matches",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "compare_config_meter_analysis_mode",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "compare_config_pronunciation_overrides",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "compare_versemap_reference_corpus",
        "Compare Poems",
    )
    assert _is_restorable_ui_state_key(
        "interactive_annotation_settings",
        "Single Poem",
    )
    assert not _is_restorable_ui_state_key(
        "compare_poem-3_upload",
        "Compare Poems",
    )
    assert not _is_restorable_ui_state_key(
        "standalone_versemap_upload",
        "VerseMap",
    )


def test_historical_analysis_ignores_legacy_nonrestorable_widget_state(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    library_path = tmp_path / "analysis-library.sqlite3"
    monkeypatch.setenv("VERSEVAD_RESEARCH_LIBRARY_PATH", str(library_path))
    analysis = application_services.run_workspace_analysis(
        application_services.AnalysisRequest(
            project_name="",
            title="Historical restore validation",
            original_text="Bright leaves turn in the evening air.",
            lexicon_ids=(),
        ),
        preprocessor=SpacyEnglishPreprocessor(),
    )
    repository = ResearchLibraryRepository(library_path)
    repository.save_revision(
        parent_type="analysis",
        workspace_id="Single Poem",
        title="Historical restore validation",
        software_version="1.0.0",
        payload={
            "kind": "workspace_analysis",
            "workspace_id": "Single Poem",
            "analysis": analysis,
            "ui_state": {
                "poem_title": "Historical restore validation",
                "poem_text": "Bright leaves turn in the evening air.",
                "module_preset": "Custom",
                "minimum_matches": 7,
                "concreteness_abstract_max": 2.5,
                "one_poem_restore_stopwords": False,
                "one_poem_import_stopwords": None,
                "uploaded_poem": None,
                "future_action_without_known_name": True,
                "download_summary": False,
            },
            "metadata": {},
        },
        storage_mode="full",
        status="saved",
    )

    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    _open_workspace(app, "Analysis Library")
    caplog.clear()
    _button(app, "Open historical result").click()
    app.run(timeout=60)
    _open_workspace(app, "Single Poem")

    assert not app.exception
    assert app.session_state["workspace"].request.title == (
        "Historical restore validation"
    )
    assert app.session_state["one_poem_restore_stopwords"] is False
    assert app.session_state["one_poem_import_stopwords"] is None
    assert app.session_state["uploaded_poem"] is None
    assert "future_action_without_known_name" not in app.session_state
    assert "download_summary" not in app.session_state
    assert app.session_state["minimum_matches"] == 7
    assert app.session_state["concreteness_abstract_max"] == 2.5
    assert "created with a default value" not in caplog.text

    caplog.clear()
    _open_workspace(app, "Single Poem")
    assert "created with a default value" not in caplog.text
    _button(app, "Continue viewing historical result").click()
    app.run(timeout=60)

    assert not app.exception
    assert app.session_state["workspace"].request.title == (
        "Historical restore validation"
    )
    assert app.session_state["poem_text"] == (
        "Bright leaves turn in the evening air."
    )
    assert "_historical_analysis" not in app.session_state
    assert len(repository.list_items()) == 1

    app.session_state["_historical_analysis"] = {
        "workspace": "Single Poem",
        "saved_version": "1.0.0",
    }
    app.run(timeout=60)
    _button(app, "Prepare reanalysis with current version").click()
    app.run(timeout=60)

    assert not app.exception
    assert app.session_state["workspace"] is None
    assert app.session_state["poem_title"] == "Historical restore validation"
    assert app.session_state["poem_text"] == (
        "Bright leaves turn in the evening air."
    )
    assert "_historical_analysis" not in app.session_state
    assert len(repository.list_items()) == 1


def test_historical_comparison_restores_custom_profile_and_configuration(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    library_path = tmp_path / "comparison-library.sqlite3"
    profile_path = tmp_path / "analysis-profiles.json"
    monkeypatch.setenv("VERSEVAD_RESEARCH_LIBRARY_PATH", str(library_path))
    monkeypatch.setenv("VERSEVAD_ANALYSIS_PROFILES_PATH", str(profile_path))
    profile_label = custom_profile_label("Historical Comparison")
    save_custom_profile(
        "Historical Comparison",
        {"minimum_matches": 9, "include_lexical_style": True},
        path=profile_path,
    )
    analyses = tuple(
        application_services.run_workspace_analysis(
            application_services.AnalysisRequest(
                project_name="",
                title=title,
                original_text=text,
                lexicon_ids=(),
                minimum_match_requirement=9,
                include_lexical_style=True,
            ),
            preprocessor=SpacyEnglishPreprocessor(),
        )
        for title, text in (
            ("First", "Bright birds sing.\nNight falls."),
            ("Second", "Dark winds rise.\nMorning comes."),
        )
    )
    repository = ResearchLibraryRepository(library_path)
    repository.save_revision(
        parent_type="comparison",
        workspace_id="Compare Poems",
        title="Historical comparison",
        software_version="1.0.0",
        payload={
            "kind": "comparison_set",
            "workspace_id": "Compare Poems",
            "comparison": PoemComparisonSet(
                comparison_set_id="historical-comparison",
                analyses=analyses,
            ),
            "ui_state": {
                "compare_poem_ids": ["poem_1", "poem_2"],
                "compare_next_poem_number": 3,
                "compare_poem_1_title": "First",
                "compare_poem_1_text": "Bright birds sing.\nNight falls.",
                "compare_poem_2_title": "Second",
                "compare_poem_2_text": "Dark winds rise.\nMorning comes.",
                "compare_analysis_profile": profile_label,
                "compare_lexicons": [],
                "compare_modules": ["lexical_style"],
                "compare_config_minimum_matches": 9,
                "compare_config_lexical_style_mattr_window": 25,
            },
        },
        profile_name=profile_label,
        storage_mode="full",
        status="saved",
    )

    app = AppTest.from_file(str(APP_PATH), default_timeout=75).run()
    _open_workspace(app, "Analysis Library")
    caplog.clear()
    _button(app, "Open historical result").click()
    app.run(timeout=75)
    _open_workspace(app, "Compare Poems")

    assert not app.exception
    assert app.session_state["compare_analysis_profile"] == profile_label
    assert app.session_state["compare_config_minimum_matches"] == 9
    assert app.session_state["compare_config_lexical_style_mattr_window"] == 25
    _open_workspace(app, "Compare Poems")
    profile = next(
        field for field in app.selectbox if field.label == "Analysis profile"
    )
    assert profile.value == profile_label
    assert "created with a default value" not in caplog.text


def test_interface_starts_with_beginner_input_workflow() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Single Poem"]
    assert "Paste the poem exactly as you want it analyzed" in [
        area.label for area in app.text_area
    ]
    text_inputs = {field.label: field for field in app.text_input}
    assert "Poem title or working label" in text_inputs
    assert text_inputs["Workspace name"].value == ""
    assert "Analyze Poem" in [button.label for button in app.button]
    assert "Apply / Restore" in [button.label for button in app.button]
    assert "Appearance" in [field.label for field in app.selectbox]
    assert "Run self-test" in [button.label for button in app.button]
    assert "Concreteness profile (Brysbaert et al. ratings)" in [
        field.label for field in app.checkbox
    ]
    assert "Sensorimotor imagery & embodiment (Lancaster norms)" in [
        field.label for field in app.checkbox
    ]
    assert "Frequency & rarity profile (SUBTLEX-US Zipf)" in [
        field.label for field in app.checkbox
    ]
    assert "Additional Optional Models" in [
        heading.value for heading in app.subheader
    ]
    assert "3. Analysis Configuration and Methodology" in [
        heading.value for heading in app.subheader
    ]
    assert "Choose Additional Optional Models" in [
        panel.label for panel in app.expander
    ]
    assert "Show Configuration Controls" in [
        panel.label for panel in app.expander
    ]
    assert not app.tabs


def test_inherited_form_report_uses_fragment_scoped_widget_reruns() -> None:
    assert hasattr(render_inherited_form, "__wrapped__")


def test_bottom_controls_use_client_side_collapse_without_app_rerun() -> None:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    collapse_function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_render_bottom_collapse_button"
    )
    calls = [
        node
        for node in ast.walk(collapse_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
    ]
    assert any(node.func.attr == "html" for node in calls)
    assert not any(node.func.attr == "rerun" for node in calls)
    html_call = next(node for node in calls if node.func.attr == "html")
    assert any(
        keyword.arg == "unsafe_allow_javascript"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in html_call.keywords
    )


def test_pronunciation_fragment_approval_requests_full_app_rerun() -> None:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    review_function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_render_pronunciation_attention_contents"
    )
    reruns = [
        node
        for node in ast.walk(review_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
        and node.func.attr == "rerun"
    ]
    assert len(reruns) == 1
    assert any(
        keyword.arg == "scope"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == "app"
        for keyword in reruns[0].keywords
    )
    apply_button = next(
        node
        for node in ast.walk(review_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "button"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value
        == "Apply Approved Pronunciations and Reanalyze"
    )
    assert all(
        keyword.arg not in {"on_click", "args"}
        for keyword in apply_button.keywords
    )


def test_single_text_completion_renders_before_sidebar_refresh_rerun() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    status_complete = source.index(
        'analysis_status.update(\n                    label="Analysis complete"'
    )
    render_complete = source.index(
        "st.success(completion_notice)",
        status_complete,
    )
    queue_refresh = source.index(
        '"_single_text_post_analysis_refresh_pending"',
        render_complete,
    )
    report_rendering = source.index(
        'workspace = st.session_state.get("workspace")',
        queue_refresh,
    )
    deferred_refresh = source.rindex(
        '"_single_text_post_analysis_refresh_pending"'
    )

    assert status_complete < render_complete < queue_refresh < report_rendering
    assert report_rendering < deferred_refresh


def test_interface_state_migration_and_preset_emit_no_widget_default_warning(
    caplog,
) -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    caplog.clear()
    app.run(timeout=30)
    assert "created with a default value" not in caplog.text

    preset = next(
        field for field in app.selectbox if field.label == "Analysis profile"
    )
    preset.set_value("Affect and Emotion")
    app.run(timeout=30)
    caplog.clear()
    _button(app, "Apply / Restore").click()
    app.run(timeout=30)

    assert not app.exception
    assert "created with a default value" not in caplog.text


def test_saving_custom_analysis_profile_defers_selectbox_state_update(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_ANALYSIS_PROFILES_PATH",
        str(tmp_path / "analysis-profiles.json"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()
    profile_name = next(
        field
        for field in app.text_input
        if field.label == "Custom profile name"
    )
    profile_name.input("My Close Reading")
    app.run(timeout=30)
    _button(app, "Add as New").click()
    app.run(timeout=45)

    assert not app.exception
    preset = next(
        field for field in app.selectbox if field.label == "Analysis profile"
    )
    assert preset.value == custom_profile_label("My Close Reading")
    _open_workspace(app, "Other Text")
    other_text_profile = next(
        field for field in app.selectbox if field.label == "Analysis profile"
    )
    assert custom_profile_label("My Close Reading") in other_text_profile.options
    for label in ("Add as New", "Update Selected", "Delete Selected"):
        assert label in [button.label for button in app.button]
    _open_workspace(app, "Compare Poems")
    compare_profile = next(
        field for field in app.selectbox if field.label == "Analysis profile"
    )
    saved_label = custom_profile_label("My Close Reading")
    assert saved_label in compare_profile.options
    for label in ("Add as New", "Update Selected", "Delete Selected"):
        assert label in [button.label for button in app.button]

    compare_profile.set_value(saved_label)
    app.run(timeout=45)
    _button(app, "Apply / Restore").click()
    app.run(timeout=45)
    minimum_matches = next(
        field
        for field in app.number_input
        if field.label == "Minimum evidence before a result is marked non-sparse"
    )
    minimum_matches.set_value(7)
    app.run(timeout=45)
    _button(app, "Update Selected").click()
    app.run(timeout=45)

    stored = load_custom_profiles(tmp_path / "analysis-profiles.json")
    assert stored["My Close Reading"].settings["minimum_matches"] == 7

    _button(app, "Delete Selected").click()
    app.run(timeout=45)
    assert not app.exception
    assert load_custom_profiles(tmp_path / "analysis-profiles.json") == {}
    assert "created with a default value" not in caplog.text


def test_interface_warns_and_filters_when_research_resources_are_absent(
    tmp_path,
    monkeypatch,
) -> None:
    readiness = application_services.installed_resource_readiness(
        source_root=tmp_path / "source_lexicons",
        resource_root=tmp_path / "resources",
    )
    monkeypatch.setattr(
        application_services,
        "installed_resource_readiness",
        lambda: readiness,
    )

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    assert not app.exception
    assert any(
        "Resource setup needs attention" in warning.value
        for warning in app.warning
    )
    lexicons = next(
        field for field in app.multiselect if field.label == "Lexicons"
    )
    assert lexicons.options == []
    lexical_style = next(
        field
        for field in app.checkbox
        if field.label
        == "Lexical diversity, word length & structural word counts"
    )
    assert not lexical_style.disabled


def test_interface_opens_persistent_corpus_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VERSEVAD_DATABASE_PATH", str(tmp_path / "versevad.sqlite3"))
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Saved Projects")
    assert not app.exception
    assert [title.value for title in app.title] == ["Saved Projects"]
    assert "Project title" in [field.label for field in app.text_input]
    assert "Create project" in [button.label for button in app.button]


def test_interface_opens_compare_poems_workspace() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Compare Poems")

    assert not app.exception
    assert [title.value for title in app.title] == ["Compare Poems"]
    assert [area.label for area in app.text_area].count(
        "Paste the poem exactly as it should be analyzed"
    ) == 2
    assert "Analyze 2 Poems" in [button.label for button in app.button]
    assert "Add Another Poem" in [button.label for button in app.button]
    assert "Phrase policy" in [field.label for field in app.selectbox]
    assert "MATTR window" in [field.label for field in app.number_input]
    assert "Meter analysis level" in [field.label for field in app.selectbox]
    number_labels = [field.label for field in app.number_input]
    for label in (
        "Meter line-fit threshold",
        "Poem candidate-fit threshold",
        "Candidate margin",
        "Maximum stress paths",
        "Realization candidates per line",
        "Retained realized alternatives",
    ):
        assert any(item.startswith(label) for item in number_labels)
    assert "Recognize visibly marked contractions" in [
        field.label for field in app.checkbox
    ]
    assert "Shared scholar scansion revisions" in [
        field.label for field in app.text_area
    ]
    module_selector = next(
        field
        for field in app.multiselect
        if field.label == "Additional modules"
    )
    if "sensorimotor" in module_selector.options:
        assert "sensorimotor" in module_selector.value

    profile = next(
        field
        for field in app.selectbox
        if field.label == "Analysis profile"
    )
    for label in ("Add as New", "Update Selected", "Delete Selected"):
        assert label in [button.label for button in app.button]
    profile.set_value("Teaching/Introductory")
    app.run(timeout=30)
    _button(app, "Apply / Restore").click()
    app.run(timeout=30)
    assert not app.exception

    _button(app, "Add Another Poem").click()
    app.run(timeout=30)
    assert not app.exception
    assert [area.label for area in app.text_area].count(
        "Paste the poem exactly as it should be analyzed"
    ) == 3
    assert "Analyze 3 Poems" in [button.label for button in app.button]


def test_compare_poems_analyzes_two_and_three_poem_sets(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    _open_workspace(app, "Compare Poems")

    titles = [
        field
        for field in app.text_input
        if field.label == "Title or working label"
    ]
    poems = [
        area
        for area in app.text_area
        if area.label == "Paste the poem exactly as it should be analyzed"
    ]
    for field, value in zip(titles, ("First", "Second"), strict=True):
        field.input(value)
    for field, value in zip(
        poems,
        (
            "Bright birds sing.\nNight falls.",
            "Dark winds rise.\nMorning comes.",
        ),
        strict=True,
    ):
        field.input(value)
    next(
        field
        for field in app.multiselect
        if field.label == "Affective lexicons"
    ).set_value([])
    next(
        field
        for field in app.multiselect
        if field.label == "Additional modules"
    ).set_value(["lexical_style"])
    app.run(timeout=60)
    _button(app, "Analyze 2 Poems").click()
    app.run(timeout=90)

    assert not app.exception
    report = next(
        field for field in app.selectbox if field.label == "Report Section"
    )
    assert report.value == "Overview"

    report.set_value("Structure")
    app.run(timeout=60)
    assert not app.exception
    assert "Metric to chart" in [field.label for field in app.selectbox]

    _button(app, "Add Another Poem").click()
    app.run(timeout=60)
    titles = [
        field
        for field in app.text_input
        if field.label == "Title or working label"
    ]
    poems = [
        area
        for area in app.text_area
        if area.label == "Paste the poem exactly as it should be analyzed"
    ]
    titles[-1].input("Third")
    poems[-1].input("Rain meets stone.\nSilence stays.")
    app.run(timeout=60)
    _button(app, "Analyze 3 Poems").click()
    app.run(timeout=90)

    assert not app.exception
    report = next(
        field for field in app.selectbox if field.label == "Report Section"
    )
    assert report.value == "Overview"


def _populate_lexical_style_corpus(database_path: Path) -> str:
    repository = ProjectRepository(database_path)
    project = repository.create_project("Readable Corpus Reports")
    repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "First",
                "first.txt",
                "first.txt",
                "Bright birds sing.\nNight falls.",
            ),
            CorpusTextImport(
                "Second",
                "second.txt",
                "second.txt",
                "Dark winds rise.\nMorning comes.",
            ),
        ),
    )
    analyze_corpus(
        repository,
        project.project_id,
        lexicon_ids=(),
        preprocessor=SpacyEnglishPreprocessor(),
        module_configuration=CorpusAnalysisConfiguration(
            include_lexical_style=True
        ),
    )
    return project.project_id


def test_saved_and_personal_corpora_use_scope_and_report_selectors(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    cases = (
        (
            "Saved Projects",
            "VERSEVAD_DATABASE_PATH",
            tmp_path / "projects.sqlite3",
            "Analyze & Compare",
        ),
        (
            "Personal Corpus",
            "VERSEVAD_PERSONAL_CORPUS_DATABASE_PATH",
            tmp_path / "personal.sqlite3",
            "Corpus Analysis",
        ),
    )
    for workspace, variable, database_path, section_name in cases:
        monkeypatch.setenv(variable, str(database_path))
        project_id = _populate_lexical_style_corpus(database_path)
        app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
        app.session_state["_workspace_route_override"] = workspace
        if workspace == "Saved Projects":
            app.session_state["active_corpus_project"] = project_id
            app.session_state[
                f"corpus_project_section_{project_id}"
            ] = section_name
        else:
            app.session_state[
                f"personal_corpus_report_section_{project_id}"
            ] = section_name
        app.run(timeout=90)

        assert not app.exception
        assert any(
            field.label == "Corpus analysis profile"
            for field in app.selectbox
        )
        for label in ("Add as New", "Update Selected", "Delete Selected"):
            assert label in [button.label for button in app.button]
        scope = next(
            field
            for field in app.selectbox
            if field.label == "Result Scope"
        )
        report = next(
            field
            for field in app.selectbox
            if field.label == "Analysis Report"
            and "Structure" in field.options
        )
        assert list(scope.options) == [
            "Whole Corpus",
            "First",
            "Second",
        ]
        assert "Structure" in report.options
        assert not any(
            "Work, line, and stanza results" in block.value
            for block in app.markdown
        )
        scope.set_value(scope.options[1])
        app.run(timeout=90)
        assert not app.exception
        assert any(
            field.label == "Lexical scope" for field in app.multiselect
        )
        assert any(
            field.label == "Aggregation weighting"
            for field in app.multiselect
        )


def test_collections_opens_isolated_personal_corpus(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "personal_corpus.sqlite3"
    monkeypatch.setenv(
        "VERSEVAD_PERSONAL_CORPUS_DATABASE_PATH",
        str(database_path),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    _open_workspace(app, "Personal Corpus")

    assert not app.exception
    assert [title.value for title in app.title] == ["Personal Corpus"]
    assert database_path.is_file()
    report = _section_navigation(app, "Report Section")
    assert report.options == PERSONAL_CORPUS_SECTIONS
    assert report.value == "Poems & Metadata"
    assert "Add One or More Poems" in [
        panel.label for panel in app.expander
    ]
    assert "Edit a Poem" in [panel.label for panel in app.expander]
    assert "Delete a Poem" in [panel.label for panel in app.expander]


def test_personal_corpus_edits_versions_and_deletes_exactly_one_poem(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "personal_corpus.sqlite3"
    monkeypatch.setenv(
        "VERSEVAD_PERSONAL_CORPUS_DATABASE_PATH",
        str(database_path),
    )
    repository = ProjectRepository(database_path)
    project = repository.create_project("My Personal Corpus")
    original = repository.import_texts(
        project.project_id,
        (
            CorpusTextImport(
                "Editable Poem",
                "editable.txt",
                "editable.txt",
                "Bright.",
            ),
        ),
    )[0]

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Personal Corpus")

    poem_text = next(
        area for area in app.text_area if area.value == "Bright."
    )
    poem_text.input("Bright, then dark.")
    _button(app, "Save Poem Changes").click()
    app.run(timeout=30)

    updated = repository.get_text(original.text_id)
    assert updated.original_text == "Bright, then dark."
    assert updated.text_version_id != original.text_version_id

    confirmation = next(
        field
        for field in app.text_input
        if field.label.startswith("Type the exact poem title to confirm")
    )
    confirmation.input("Editable Poem")
    app.run(timeout=30)
    delete = _button(app, "Delete This Poem")
    assert not delete.disabled
    delete.click()
    app.run(timeout=30)

    assert not app.exception
    assert repository.list_texts(project.project_id) == ()
    assert any(
        'Deleted "Editable Poem"' in message.value
        for message in app.success
    )


def test_corpus_workspace_exposes_phase5_review_scenarios(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "versevad.sqlite3"
    monkeypatch.setenv("VERSEVAD_DATABASE_PATH", str(database_path))
    repository = ProjectRepository(database_path)
    project = repository.create_project("Review interface project")
    repository.import_texts(
        project.project_id,
        (CorpusTextImport("Poem", "poem.txt", "poem.txt", "Bright."),),
    )
    repository.create_review_scenario(
        project.project_id,
        "Conservative review",
    )

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Saved Projects")

    assert not app.exception
    project_navigation = _section_navigation(app, "Project section")
    assert project_navigation.options == CORPUS_SECTIONS
    assert project_navigation.value == "Works & Metadata"
    project_navigation.set_value("Review & Scenarios")
    app.run(timeout=30)
    assert _section_navigation(app, "Project section").value == (
        "Review & Scenarios"
    )
    assert not app.tabs
    assert "Review scenario" in [field.label for field in app.selectbox]
    assert "Scenario to edit" in [field.label for field in app.selectbox]
    assert "Create review scenario" in [button.label for button in app.button]


def test_interface_deletes_only_exactly_confirmed_project(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "versevad.sqlite3"
    monkeypatch.setenv("VERSEVAD_DATABASE_PATH", str(database_path))
    repository = ProjectRepository(database_path)
    disposable = repository.create_project("Disposable project")
    keeper = repository.create_project("Keep this project")

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Saved Projects")
    active_project = next(
        field for field in app.selectbox if field.label == "Active project"
    )
    active_project.set_value(disposable.project_id)
    app.run(timeout=30)

    confirmation = next(
        field
        for field in app.text_input
        if field.label.startswith("Type the exact project title to confirm")
    )
    delete_button = _button(app, "Delete this project")
    assert delete_button.disabled

    confirmation.input("Disposable project")
    app.run(timeout=30)
    delete_button = _button(app, "Delete this project")
    assert not delete_button.disabled
    delete_button.click()
    app.run(timeout=30)

    assert not app.exception
    assert any(
        'Project "Disposable project" was deleted' in message.value
        for message in app.success
    )
    assert [project.project_id for project in repository.list_projects()] == [
        keeper.project_id
    ]


def test_interface_recovers_from_a_stale_deleted_project_selection(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "versevad.sqlite3"
    monkeypatch.setenv("VERSEVAD_DATABASE_PATH", str(database_path))
    repository = ProjectRepository(database_path)
    disposable = repository.create_project("Deleted outside this rerun")
    keeper = repository.create_project("Remaining project")

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Saved Projects")
    app.session_state["active_corpus_project"] = disposable.project_id

    repository.delete_project(
        disposable.project_id,
        confirmation_title=disposable.title,
    )
    app.run(timeout=30)

    assert not app.exception
    active_project = next(
        field for field in app.selectbox if field.label == "Active project"
    )
    assert active_project.value == keeper.project_id


def test_interface_opens_lexicon_explorer() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Lexicon Explorer")
    assert not app.exception
    assert [title.value for title in app.title] == ["Lexicon Explorer"]
    assert "Word or phrase" in [field.label for field in app.text_input]
    assert "Optional user-supplied mapping" in [field.label for field in app.text_input]
    assert "Search installed lexicons" in [button.label for button in app.button]


def test_lexicon_explorer_offers_printable_word_report() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    app.session_state["_workspace_route_override"] = "Lexicon Explorer"
    app.run(timeout=60)

    query = next(
        field for field in app.text_input if field.label == "Word or phrase"
    )
    query.input("bright")
    _button(app, "Search installed lexicons").click()
    app.run(timeout=60)

    assert not app.exception
    assert "Dictionary Senses" in [
        heading.value for heading in app.subheader
    ]
    assert "Rule-Based Sentiment and Readability Evidence" in [
        heading.value for heading in app.subheader
    ]
    downloads = {
        button.label: button
        for button in app.get("download_button")
    }
    assert "Download printable Word report" in downloads
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        hear = next(button for button in app.button if button.label == "Hear")
        hear.click()
        app.run(timeout=60)
        assert not app.exception
        assert app.get("audio")


def test_interface_reuses_single_text_workflow_for_other_text() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _open_workspace(app, "Other Text")

    assert not app.exception
    assert [title.value for title in app.title] == ["Other Text"]
    assert "Text title or working label" in [
        field.label for field in app.text_input
    ]
    assert "Paste the text exactly as you want it analyzed" in [
        field.label for field in app.text_area
    ]
    assert "Analyze Text" in [button.label for button in app.button]
    assert any(
        "experimental" in message.value.lower() for message in app.info
    )


def test_other_text_handles_protected_contractions_with_sensorimotor_enabled(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    _open_workspace(app, "Other Text")
    title = next(
        field
        for field in app.text_input
        if field.label == "Text title or working label"
    )
    text = next(
        field
        for field in app.text_area
        if field.label == "Paste the text exactly as you want it analyzed"
    )
    sensorimotor = next(
        field
        for field in app.checkbox
        if field.label
        == "Sensorimotor imagery & embodiment (Lancaster norms)"
    )
    title.input("Contraction coverage")
    text.input(
        "You're not going to believe that I can't do this. It won't work."
    )
    sensorimotor.set_value(True)
    app.run(timeout=60)
    _button(app, "Analyze Text").click()
    app.run(timeout=90)

    assert not app.exception
    assert not any(
        "matched count cannot exceed" in error.value.lower()
        for error in app.error
    )


def test_interface_persists_application_appearance_without_analysis_state(
    tmp_path,
    monkeypatch,
) -> None:
    preferences_path = tmp_path / "ui_preferences.json"
    monkeypatch.setenv("VERSEVAD_PREFERENCES_PATH", str(preferences_path))
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    appearance = next(
        field for field in app.selectbox if field.label == "Appearance"
    )
    assert appearance.options == [
        "Classic",
        "Dark",
        "Lavender",
        "Ocean",
        "Crimson",
        "Forest",
    ]
    appearance.set_value("Ocean")
    app.run(timeout=30)

    assert not app.exception
    assert load_preferences(preferences_path).appearance is AppearanceMode.OCEAN
    assert app.session_state["workspace"] is None


def test_interface_shows_plain_language_input_error() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _button(app, "Analyze Poem").click()
    app.run()
    assert not app.exception
    assert any("Enter a title" in error.value for error in app.error)


def test_clear_text_uses_widget_callback_without_session_state_error(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.text_area[0].input("Temporary poem text.")
    app.run(timeout=30)

    clear_button = _button(app, "Clear Workspace Text")
    assert not clear_button.disabled
    clear_button.click()
    app.run(timeout=30)

    assert not app.exception
    assert app.text_area[0].value == ""
    assert _button(app, "Clear Workspace Text").disabled


def test_affective_tables_render_when_no_tokens_match_the_lexicon(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "VERSEVAD_RESEARCH_LIBRARY_PATH",
        str(tmp_path / "analysis-library.sqlite3"),
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Empty evidence stress test")
    app.text_area[0].input("A\nB\nC\nD\nE")
    app.multiselect[0].set_value(["nrc_vad_v2_1"])
    _button(app, "Analyze Poem").click()
    app.run(timeout=60)
    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Affective Evidence")
    app.run(timeout=60)

    assert not app.exception
    assert any(
        expander.label == "Cumulative Lexical Load"
        for expander in app.expander
    )


def test_interface_analyzes_pasted_poem_and_builds_readable_views() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    title = next(field for field in app.text_input if field.label == "Poem title or working label")
    title.input("Interface validation poem")
    app.text_area[0].input("A bit of bright joy and fear in the dark night.")
    app.multiselect[0].set_value(
        ["nrc_vad_v2_1", "nrc_emotion_v0_92", "nrc_emotion_intensity_v1"]
    )
    _button(app, "Analyze Poem").click()
    app.run(timeout=60)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert any(
        field.label == "Saved analysis title" for field in app.text_input
    )
    report_navigation = _section_navigation(app, "Report section")
    assert report_navigation.options == REPORT_SECTIONS
    assert report_navigation.value == "Overview"
    report_navigation.set_value("Interactive Annotation")
    app.run(timeout=60)
    assert not app.exception
    assert len(app.get("bidi_component")) == 1
    report_navigation = _section_navigation(app, "Report section")
    assert not app.tabs
    collapsible_report_sections = {
        "VAD · Complete",
        "Emotion Association, Intensity & Sentiment · Complete",
        "Lexical Trajectory · Complete",
        "PoetryID · Not selected",
        "Concreteness · Not selected",
        "Frequency & Rarity · Not selected",
        "Acquisition & Readability · Complete",
        "Pronunciation, Syllables & Stress · Not selected",
        "Meter & Rhythm · Not selected",
        "Rhyme & Recurring Sound · Not selected",
        "Language Profile · Complete",
        "Lexical & Structural Measures · Not selected",
        "Token Evidence, Coverage & Diagnostics · Complete",
        "Export Report & Data",
        "Methodology & How to Read",
    }
    report_expanders = {
        expander.label: expander
        for expander in app.expander
        if expander.label in collapsible_report_sections
    }
    assert report_expanders.keys() == collapsible_report_sections
    assert all(not expander.proto.expanded for expander in report_expanders.values())
    assert ("Lexicons analyzed", "3") in [
        (metric.label, metric.value) for metric in app.metric
    ]
    assert not {
        "Download readable summary",
        "Download CSV reading guide",
        "Download narrative report",
        "Download current-view bundle",
    } <= {button.label for button in app.get("download_button")}
    report_navigation.set_value("Export & Help")
    app.run(timeout=60)
    assert _section_navigation(app, "Report section").value == "Export & Help"
    _button(app, "Prepare downloads").click()
    app.run(timeout=60)
    assert _section_navigation(app, "Report section").value == "Export & Help"
    downloads = app.get("download_button")
    assert {button.label for button in downloads} >= {
        "Download readable summary",
        "Download CSV reading guide",
        "Download current-view bundle",
    }
    assert any(
        "REPRODUCIBILITY_README.txt" in message.value
        and "FILE_INVENTORY.txt" in message.value
        for message in app.info
    )
    profile_controls = {field.label: field for field in app.multiselect}
    assert profile_controls["Lexical scope"].value == ["Stopword-excluded"]
    assert profile_controls["Aggregation weighting"].value == ["Token-weighted"]


def test_lexical_trajectory_source_change_retains_affective_report_section() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Trajectory state poem")
    app.text_area[0].input("Bright stone.\nDark night.")
    app.multiselect[0].set_value(["nrc_vad_v1", "nrc_vad_v2_1"])
    _button(app, "Analyze Poem").click()
    app.run(timeout=60)

    assert any(
        caption.value == "NRC VAD Lexicon v2.1"
        for caption in app.caption
    )
    assert _button(app, "Resolve Pronunciation").disabled

    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Affective Evidence")
    app.run(timeout=60)
    source = next(
        field
        for field in app.selectbox
        if field.label == "Trajectory VAD source"
    )
    assert set(source.options) == {
        "NRC VAD Lexicon v1",
        "NRC VAD Lexicon v2.1",
    }
    display_by_value = {
        "nrc_vad_v1": "NRC VAD Lexicon v1",
        "nrc_vad_v2_1": "NRC VAD Lexicon v2.1",
    }
    replacement = next(
        value for value in display_by_value if value != source.value
    )
    source.set_value(display_by_value[replacement])
    app.run(timeout=60)

    assert not app.exception
    assert _section_navigation(app, "Report section").value == "Affective Evidence"
    assert next(
        field
        for field in app.selectbox
        if field.label == "Trajectory VAD source"
    ).value == replacement


def test_interface_renders_poetry_id_maps_scales_and_non_json_downloads() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("PoetryID interface validation")
    app.text_area[0].input("joy love peace light happy calm strong")
    app.multiselect[0].set_value(["nrc_vad_v1"])
    app.run(timeout=60)
    poetry_id_sources = next(
        field
        for field in app.multiselect
        if field.label == "PoetryID VAD sources"
    )
    assert poetry_id_sources.value == ["nrc_vad_v1"]
    poetry_id = next(
        field
        for field in app.checkbox
        if field.label == "PoetryID lexical-affective profile"
    )
    assert not poetry_id.disabled
    poetry_id.set_value(True)
    app.run(timeout=60)
    _button(app, "Analyze Poem").click()
    app.run(timeout=60)

    assert not app.exception
    assert any(
        heading.value == "PoetryID" for heading in app.subheader
    )
    selectors = {field.label: field for field in app.selectbox}
    assert "PoetryID VAD source" in selectors
    profile_controls = {field.label: field for field in app.multiselect}
    assert profile_controls["Lexical scope"].options == [
        "All lexical tokens",
        "Stopword-excluded",
        "Content words only",
    ]
    assert profile_controls["Aggregation weighting"].options == [
        "Token-weighted",
        "Type-weighted",
    ]
    report_navigation = _section_navigation(app, "Report section")
    report_navigation.set_value("Affective Evidence")
    app.run(timeout=60)
    lexical_scope = next(
        field
        for field in app.multiselect
        if field.label == "Lexical scope"
    )
    lexical_scope.set_value(["Stopword-excluded"])
    app.run(timeout=60)
    assert _section_navigation(app, "Report section").value == (
        "Affective Evidence"
    )
    report_navigation = _section_navigation(app, "Report section")
    report_navigation.set_value("Export & Help")
    app.run(timeout=60)
    _button(app, "Prepare downloads").click()
    app.run(timeout=60)
    labels = {button.label for button in app.get("download_button")}
    assert "Download current-view bundle" in labels
    assert not any(label.endswith(".json") for label in labels)


def test_interface_runs_optional_lexical_style_without_a_resource() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Lexical style interface validation")
    app.text_area[0].input("red blue red\ngreen blue\n\nyellow red")
    app.multiselect[0].set_value([])
    lexical_style = next(
        field
        for field in app.checkbox
        if field.label
        == "Lexical diversity, word length & structural word counts"
    )
    lexical_style.set_value(True)
    app.run(timeout=60)
    _button(app, "Analyze Poem").click()
    app.run(timeout=60)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert any("Lexical Diversity" in heading.value for heading in app.subheader)
    assert any(
        "Structural Count Summary" in heading.value for heading in app.subheader
    )
    assert any("Words by Physical Line" in heading.value for heading in app.subheader)
    assert any("Words by Stanza" in heading.value for heading in app.subheader)
    metrics = [(metric.label, metric.value) for metric in app.metric]
    assert ("Lexical tokens", "7") in metrics
    assert ("Nonblank physical lines", "3") in metrics
    assert ("Average words per nonblank line", "2.333") in metrics
    assert ("Average words per stanza", "3.500") in metrics
    assert ("Average nonblank lines per stanza", "1.500") in metrics
    assert ("SD words per nonblank line", "0.471") in metrics
    assert ("SD words per stanza", "1.500") in metrics
    assert ("SD nonblank lines per stanza", "0.500") in metrics


def test_interface_runs_optional_concreteness_profile_if_resource_is_present() -> None:
    resource = (
        APP_PATH.parents[3]
        / "resources"
        / "brysbaert_warriner_kuperman_concreteness_DATA.xlsx"
    )
    if not resource.is_file():
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Concreteness interface validation")
    app.text_area[0].input("Stone and justice.\n\nThe grasshopper jumps.")
    app.multiselect[0].set_value([])
    concreteness = next(
        field
        for field in app.checkbox
        if field.label == "Concreteness profile (Brysbaert et al. ratings)"
    )
    assert not concreteness.disabled
    concreteness.set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert _section_navigation(app, "Report section").options == (
        REPORT_SECTIONS
    )
    assert not app.tabs
    assert any(
        heading.value == "Normative Lexical Concreteness"
        for heading in app.subheader
    )
    assert ("Lexicons analyzed", "0") in [
        (metric.label, metric.value) for metric in app.metric
    ]


def test_interface_runs_sensorimotor_profile_if_resource_is_present() -> None:
    resource = (
        APP_PATH.parents[3]
        / "resources"
        / "Lancaster_Sensorimotor_Norms"
        / "Lancaster_sensorimotor_norms_for_39707_words.csv"
    )
    if not resource.is_file():
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=120).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Sensorimotor interface validation")
    app.text_area[0].input("Stone sings in the dark night.\nHands touch water.")
    app.multiselect[0].set_value([])
    sensorimotor = next(
        field
        for field in app.checkbox
        if field.label == "Sensorimotor imagery & embodiment (Lancaster norms)"
    )
    assert not sensorimotor.disabled
    sensorimotor.set_value(True)
    app.run(timeout=120)
    _button(app, "Analyze Poem").click()
    app.run(timeout=120)

    assert not app.exception
    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Lexical Character, Imagery & Embodiment")
    app.run(timeout=120)
    assert any(
        heading.value == "Sensorimotor Imagery & Embodiment"
        for heading in app.subheader
    )
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Coverage"] != "—"
    assert metrics["Matched Observations"] != "0"


def test_interface_runs_optional_frequency_profile_and_content_scope_if_present() -> None:
    resource = (
        APP_PATH.parents[3]
        / "resources"
        / "subtlex-us"
        / "SUBTLEX-US frequency list with PoS and Zipf information.xlsx"
    )
    if not resource.is_file():
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Frequency interface validation")
    app.text_area[0].input("The stone runs swiftly and the bright grass bends.")
    app.multiselect[0].set_value([])
    frequency = next(
        field
        for field in app.checkbox
        if field.label == "Frequency & rarity profile (SUBTLEX-US Zipf)"
    )
    assert not frequency.disabled
    frequency.set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    content_scope = [
        field for field in app.multiselect if field.label == "Lexical scope"
    ][-1]
    content_scope.set_value(["Content words only"])
    app.run(timeout=90)
    assert app.session_state["single_poem_report_profiles_scopes"] == [
        "Content words only"
    ]
    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Lexical Character, Imagery & Embodiment")
    app.run(timeout=90)
    assert _section_navigation(app, "Report section").options == (
        REPORT_SECTIONS
    )
    assert not app.tabs
    assert any(
        heading.value == "SUBTLEX-US Lexical Frequency & Rarity"
        for heading in app.subheader
    )
    median_metric = next(
        metric for metric in app.metric if metric.label == "Median Zipf (primary)"
    )
    assert median_metric.value != "—"
    assert next(
        field for field in app.multiselect if field.label == "Lexical scope"
    ).value == ["Content words only"]


def test_interface_runs_optional_aoa_profile_and_contextual_scope_if_present() -> None:
    resource = (
        APP_PATH.parents[3]
        / "resources"
        / "kuperman_2013_erratum_ESM1_official.xlsx"
    )
    if not resource.is_file():
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("AoA interface validation")
    app.text_area[0].input("The stone and slowly bending grass.")
    app.multiselect[0].set_value([])
    aoa = next(
        field
        for field in app.checkbox
        if field.label
        == "Age of Acquisition profile (Kuperman et al. ratings)"
    )
    assert not aoa.disabled
    aoa.set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    content_scope = [
        field for field in app.multiselect if field.label == "Lexical scope"
    ][-1]
    content_scope.set_value(["Content words only"])
    app.run(timeout=90)
    assert app.session_state["single_poem_report_profiles_scopes"] == [
        "Content words only"
    ]
    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Lexical Character, Imagery & Embodiment")
    app.run(timeout=90)
    assert any(
        heading.value == "Normative Lexical Age of Acquisition"
        for heading in app.subheader
    )
    mean_metric = next(
        metric for metric in app.metric if metric.label == "Mean normative AoA"
    )
    assert mean_metric.value != "â€”"
    assert next(
        field for field in app.multiselect if field.label == "Lexical scope"
    ).value == ["Content words only"]
    assert any(
        "not diagnostic of cognitive impairment" in warning.value
        for warning in app.warning
    )


def test_interface_runs_optional_pronunciation_and_override_workflow() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Pronunciation interface validation")
    app.text_area[0].input("The permit rings.\nStone.")
    app.multiselect[0].set_value([])
    pronunciation = next(
        field
        for field in app.checkbox
        if field.label == "Pronunciation & prosody foundation (CMUdict)"
    )
    assert not pronunciation.disabled
    pronunciation.set_value(True)
    app.run(timeout=90)
    overrides = next(
        field
        for field in app.text_area
        if field.label == "Poem-specific pronunciation overrides"
    )
    overrides.input(
        "the = DH AH0 | unstressed article in this reading\n"
        "permit = P ER0 M IH1 T | verb reading"
    )
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert any(
        heading.value == "Dictionary Pronunciation, Syllables & Lexical Stress"
        for heading in app.subheader
    )
    coverage = next(
        metric for metric in app.metric if metric.label == "Resolved coverage"
    )
    assert coverage.value == "100.0%"
    mean_line_syllables = next(
        metric for metric in app.metric if metric.label == "Mean syllables / line"
    )
    assert mean_line_syllables.value == "2.500"
    assert any(
        "CMUdict supplies North American dictionary pronunciations"
        in warning.value
        for warning in app.warning
    )


def test_interface_applies_dictionary_candidate_from_words_needing_attention() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    ).input("Pronunciation resolution validation")
    app.text_area[0].input("The permit rings.")
    app.multiselect[0].set_value([])
    next(
        field
        for field in app.checkbox
        if field.label == "Pronunciation & prosody foundation (CMUdict)"
    ).set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    attention = next(
        panel
        for panel in app.expander
        if panel.label == "Words Needing Attention"
    )
    assert not attention.proto.expanded
    candidate = next(
        field
        for field in app.selectbox
        if field.label == "Pronunciation for permit"
    )
    candidate.set_value("P ER0 M IH1 T")
    app.run(timeout=90)
    _button(app, "Apply Approved Pronunciations and Reanalyze").click()
    app.run(timeout=90)

    assert not app.exception
    assert "permit = P ER0 M IH1 T" in app.session_state[
        "pronunciation_overrides"
    ]
    permit_tokens = [
        token
        for token in app.session_state["workspace"].pronunciation.token_audit
        if token.normalized_form == "permit"
    ]
    assert permit_tokens
    assert all(token.resolved for token in permit_tokens)
    assert {
        token.resolved_phones
        for token in permit_tokens
    } == {
        "P ER0 M IH1 T"
    }
    assert {
        override.term
        for override in app.session_state[
            "workspace"
        ].request.pronunciation_configuration.overrides
    } == {"permit"}
    assert all(
        override.phones_text == "P ER0 M IH1 T"
        for override in app.session_state[
            "workspace"
        ].request.pronunciation_configuration.overrides
    )
    assert any(
        "pronunciation choice(s) applied" in message.value
        for message in app.success
    )


def test_interface_keeps_g2p_unmatched_until_user_approves_edit() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    ).input("G2P review validation")
    app.text_area[0].input("Quorvax rings.")
    app.multiselect[0].set_value([])
    next(
        field
        for field in app.checkbox
        if field.label == "Pronunciation & prosody foundation (CMUdict)"
    ).set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    resolve_pronunciation = _button(app, "Resolve Pronunciation")
    assert not resolve_pronunciation.disabled
    resolve_pronunciation.click()
    app.run(timeout=90)

    assert _section_navigation(app, "Report section").value == "Sound & Form"
    pronunciation_panel = next(
        panel
        for panel in app.expander
        if panel.label.startswith("Pronunciation, Syllables & Stress")
    )
    assert pronunciation_panel.proto.expanded
    attention_panel = next(
        panel
        for panel in app.expander
        if panel.label == "Words Needing Attention"
    )
    assert attention_panel.proto.expanded
    out_of_dictionary = next(
        field
        for field in app.toggle
        if field.label == "Show Out-of-Dictionary Words"
    )
    assert out_of_dictionary.value

    predicted = next(
        field
        for field in app.text_input
        if field.label == "Provisional ARPAbet for Quorvax (editable)"
    )
    assert predicted.value == "K W AO1 R V AE0 K S"
    decision = next(
        field
        for field in app.radio
        if field.label == "Decision for Quorvax"
    )
    assert decision.value == "Leave explicitly unresolved"
    assert "quorvax =" not in app.session_state["pronunciation_overrides"]

    predicted.input("K W AO1 R V AH0 K S")
    decision.set_value("Approve or edit for this session")
    app.run(timeout=90)
    _button(app, "Apply Approved Pronunciations and Reanalyze").click()
    app.run(timeout=90)

    assert not app.exception
    assert "Quorvax = K W AO1 R V AH0 K S" in app.session_state[
        "pronunciation_overrides"
    ]
    assert "User edited and approved" in app.session_state[
        "pronunciation_overrides"
    ]
    quorvax_tokens = [
        token
        for token in app.session_state["workspace"].pronunciation.token_audit
        if token.normalized_form == "quorvax"
    ]
    assert quorvax_tokens
    assert all(token.resolved for token in quorvax_tokens)
    assert {
        token.resolved_phones
        for token in quorvax_tokens
    } == {
        "K W AO1 R V AH0 K S"
    }
    assert {
        override.term
        for override in app.session_state[
            "workspace"
        ].request.pronunciation_configuration.overrides
    } == {"Quorvax"}
    assert all(
        override.phones_text == "K W AO1 R V AH0 K S"
        for override in app.session_state[
            "workspace"
        ].request.pronunciation_configuration.overrides
    )
    assert any(
        "pronunciation choice(s) applied" in message.value
        for message in app.success
    )


def test_interface_runs_fixed_meter_workflow() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Fixed meter interface validation")
    tetrameter = "the stone the stone the stone the stone"
    app.text_area[0].input("\n".join((tetrameter,) * 4))
    app.multiselect[0].set_value([])
    meter = next(
        field
        for field in app.checkbox
        if field.label == "Meter & rhythmic regularity"
    )
    assert not meter.disabled
    meter.set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert any(
        heading.value == "Candidate Meter & Rhythmic Regularity"
        for heading in app.subheader
    )
    nearest = next(
        metric for metric in app.metric if metric.label == "Nearest candidate"
    )
    assert nearest.value == "Iambic tetrameter"
    assert any(
        "nearest configured candidates" in warning.value.lower()
        for warning in app.warning
    )


def test_interface_runs_optional_performance_aware_meter_workflow() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Performance-aware interface validation")
    line = "the stone the stone the stone the stone"
    app.text_area[0].input("\n".join((line,) * 4))
    app.multiselect[0].set_value([])
    meter = next(
        field
        for field in app.checkbox
        if field.label == "Meter & rhythmic regularity"
    )
    meter.set_value(True)
    app.run(timeout=90)
    mode = next(
        field
        for field in app.selectbox
            if field.label == "Meter analysis level"
    )
    mode.set_value("Performance-aware realization")
    app.run(timeout=90)
    depth = next(
        field
        for field in app.selectbox
        if field.label == "Interpretation detail"
    )
    depth.set_value("Detailed")
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any(
        heading.value == "Performance-Aware Realization"
        for heading in app.subheader
    )
    organization = next(
        metric
        for metric in app.metric
        if metric.label == "Rhythmic organization"
    )
    assert organization.value == "Accentual Syllabic"
    assert any(
        "does not recover one mandatory performance" in warning.value
        for warning in app.warning
    )
    assert any(
        caption.value.startswith("Scansion notation:")
        for caption in app.caption
    )


def test_interface_runs_rhyme_and_sound_workflow() -> None:
    resource_root = APP_PATH.parents[3] / "resources" / "pronunciation"
    if not all(
        (resource_root / filename).is_file()
        for filename in ("cmudict.dict", "cmudict.phones", "cmudict.symbols")
    ):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("Rhyme interface validation")
    app.text_area[0].input(
        "The bright cat\nA silver night\nThe soft hat\nA quiet light"
    )
    app.multiselect[0].set_value([])
    rhyme = next(
        field
        for field in app.checkbox
        if field.label == "Rhyme & phonological patterns"
    )
    assert not rhyme.disabled
    rhyme.set_value(True)
    app.run(timeout=90)
    _button(app, "Analyze Poem").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Analysis complete" in message.value for message in app.success)
    assert any(
        heading.value == "Rhyme & Recurring Phonological Patterns"
        for heading in app.subheader
    )
    scheme = next(
        metric for metric in app.metric if metric.label == "Whole-poem scheme"
    )
    assert scheme.value == "ABAB"
    assert any(
        "dictionary- and spelling-based" in warning.value
        for warning in app.warning
    )


def test_interface_reports_complete_experimental_poetic_reading_ease() -> None:
    resource_root = APP_PATH.parents[3] / "resources"
    required = (
        resource_root
        / "subtlex-us"
        / "SUBTLEX-US frequency list with PoS and Zipf information.xlsx",
        resource_root / "kuperman_2013_erratum_ESM1_official.xlsx",
    )
    if not all(path.is_file() for path in required):
        return

    app = AppTest.from_file(str(APP_PATH), default_timeout=120).run()
    title = next(
        field
        for field in app.text_input
        if field.label == "Poem title or working label"
    )
    title.input("VV-PRE interface validation")
    app.text_area[0].input("Bright birds sing.\nThe quiet stone shines.")
    app.multiselect[0].set_value([])
    required_checkboxes = {
        "Frequency & rarity profile (SUBTLEX-US Zipf)",
        "Age of Acquisition profile (Kuperman et al. ratings)",
        "Lexical diversity, word length & structural word counts",
    }
    for field in app.checkbox:
        if field.label in required_checkboxes:
            field.set_value(True)
    app.run(timeout=120)
    _button(app, "Analyze Poem").click()
    app.run(timeout=120)

    assert not app.exception
    navigation = _section_navigation(app, "Report section")
    navigation.set_value("Lexical Character, Imagery & Embodiment")
    app.run(timeout=120)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["VV-PRE"].endswith(" / 100")
    assert metrics["Interpretation"] in {
        "Highly Accessible",
        "Accessible",
        "Moderately Demanding",
        "Demanding",
        "Highly Demanding",
    }
    assert metrics["Evidence Confidence"] == "Limited"
    assert any(
        "VerseVAD Poetic Reading Ease (Experimental)" in heading.value
        for heading in app.markdown
    )


def test_windows_helpers_are_local_and_telemetry_disabled() -> None:
    root = APP_PATH.parents[3]
    launcher = (root / "start_versevad.bat").read_text(encoding="utf-8")
    setup = (root / "scripts" / "setup_windows.ps1").read_text(encoding="utf-8")
    config = (root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "127.0.0.1" in launcher
    assert "--offline" in launcher
    assert "gatherUsageStats false" in launcher
    assert "UV_PYTHON_INSTALL_DIR" in setup
    assert 'UV_PYTHON_PREFERENCE = "only-managed"' in setup
    assert "UV_PYTHON_PREFERENCE=only-managed" in launcher
    assert "ExpectedUvHash" in setup
    assert "The VerseVAD folder moved" in setup
    assert "Refusing to rebuild an environment outside" in setup
    assert "ANEW VAD Study" not in launcher
    assert "ANEW VAD Study" not in setup
    assert "gatherUsageStats = false" in config
