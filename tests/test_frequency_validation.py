from versevad.frequency_validation import run_synthetic_frequency_validation


def test_hand_calculated_frequency_validation() -> None:
    report, problems = run_synthetic_frequency_validation()

    assert problems == ()
    assert report.eligible_tokens == 6
    assert report.matched_tokens == 5
    assert report.median_zipf == 4.0
    assert report.mean_zipf == 3.4
    assert report.unmatched_tokens == 1
    # The retired module-local content-only switch no longer restricts the
    # retained run. Canonical content scope is reconstructed after analysis.
    assert report.content_scope_eligible_tokens == 9
    assert report.source_unchanged
