from versevad.diagnostics import run_runtime_self_test, run_self_test


def test_runtime_self_test_does_not_require_research_lexicons() -> None:
    checks = run_runtime_self_test()
    assert len(checks) == 10
    assert all(check.passed for check in checks)
    assert {check.check for check in checks} == {
        "VerseVAD package",
        "Graphical framework",
        "Offline pronunciation preview",
        "Provisional G2P review",
        "English linguistic model",
        "Offline dictionary",
        "Phrase and VAD calculation",
        "Categorical emotion calculation",
        "Emotion intensity calculation",
        "Performance-aware meter safeguards",
    }


def test_local_self_test_checks_model_formulas_and_all_sources() -> None:
    checks = run_self_test()
    assert len(checks) == 15
    assert all(check.passed for check in checks)
    assert {check.check for check in checks} >= {
        "Graphical framework",
        "English linguistic model",
        "Offline dictionary",
        "Phrase and VAD calculation",
        "Categorical emotion calculation",
        "Emotion intensity calculation",
        "Performance-aware meter safeguards",
        "Provisional G2P review",
        "Warriner VAD",
        "NRC VAD v1",
        "NRC VAD v2.1",
        "NRC Emotion",
        "NRC Emotion Intensity",
    }
