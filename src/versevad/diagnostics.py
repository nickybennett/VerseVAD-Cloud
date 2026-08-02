"""Local installation diagnostics shared by the interface and OS launchers."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

from versevad import __version__
from versevad.analysis.phase2 import analyze_lexicon
from versevad.application import LEXICON_SPECS, load_lexicon
from versevad.dictionary import lookup_open_english_wordnet
from versevad.phase2_validation import (
    PHASE2_PHRASE_TEXT,
    phase2_synthetic_emotion_lexicon,
    phase2_synthetic_intensity_lexicon,
    phase2_synthetic_vad_lexicon,
)
from versevad.performance_meter_validation import (
    run_synthetic_performance_meter_validation,
)
from versevad.preprocessing import SpacyEnglishPreprocessor, create_text_document
from versevad.prosody.audio import synthesize_arpabet_wav
from versevad.prosody.g2p import predict_arpabet


@dataclass(frozen=True)
class DiagnosticCheck:
    check: str
    passed: bool
    detail: str


def run_runtime_self_test() -> tuple[DiagnosticCheck, ...]:
    """Check the installed runtime without requiring separately licensed data."""

    checks = [DiagnosticCheck("VerseVAD package", True, f"Version {__version__}")]
    try:
        import streamlit

        checks.append(
            DiagnosticCheck("Graphical framework", True, f"Streamlit {streamlit.__version__}")
        )
    except Exception as error:  # pragma: no cover - exercised only on broken installs
        checks.append(DiagnosticCheck("Graphical framework", False, str(error)))

    try:
        dictionary = lookup_open_english_wordnet(
            "poem",
            lemma="poem",
            processing_pos="NOUN",
        )
        checks.append(
            DiagnosticCheck(
                "Offline dictionary",
                dictionary.available and bool(dictionary.senses),
                (
                    "Packaged Open English WordNet 2025+ definitions are "
                    "available locally."
                ),
            )
        )
    except Exception as error:
        checks.append(DiagnosticCheck("Offline dictionary", False, str(error)))

    try:
        preview = synthesize_arpabet_wav("T EH1 S T")
        checks.append(
            DiagnosticCheck(
                "Offline pronunciation preview",
                preview.startswith(b"RIFF") and len(preview) > 44,
                "Bundled eSpeak NG generated a local ARPAbet WAV preview.",
            )
        )
    except Exception as error:
        checks.append(
            DiagnosticCheck(
                "Offline pronunciation preview",
                False,
                str(error),
            )
        )

    try:
        prediction = predict_arpabet("quorvax")
        checks.append(
            DiagnosticCheck(
                "Provisional G2P review",
                prediction.phones_text == "K W AO1 R V AE0 K S",
                (
                    "Bundled eSpeak NG generated a local review-only ARPAbet "
                    "candidate without resolving an analysis token."
                ),
            )
        )
    except Exception as error:
        checks.append(
            DiagnosticCheck(
                "Provisional G2P review",
                False,
                str(error),
            )
        )

    try:
        preprocessor = SpacyEnglishPreprocessor()
        checks.append(
            DiagnosticCheck(
                "English linguistic model",
                True,
                f"{preprocessor.metadata.pipeline_name} {preprocessor.metadata.pipeline_version}",
            )
        )
    except Exception as error:
        checks.append(DiagnosticCheck("English linguistic model", False, str(error)))
        return tuple(checks)

    try:
        phrase = analyze_lexicon(
            create_text_document("self-test-phrase", "Self-test", PHASE2_PHRASE_TEXT),
            phase2_synthetic_vad_lexicon(),
            preprocessor,
        )
        assert phrase.vad_summary is not None
        phrase_mean = phrase.vad_summary.token_weighted_original.valence.mean
        passed = (
            phrase.coverage.phrase_match_count == 1
            and phrase_mean is not None
            and math.isclose(phrase_mean, 5.4)
        )
        checks.append(
            DiagnosticCheck(
                "Phrase and VAD calculation",
                passed,
                "Hand-calculated phrase count and mean reproduced."
                if passed
                else "The hand-calculated phrase result did not reproduce.",
            )
        )
    except Exception as error:
        checks.append(DiagnosticCheck("Phrase and VAD calculation", False, str(error)))

    try:
        emotion = analyze_lexicon(
            create_text_document("self-test-emotion", "Self-test", "Joy joy fear stone."),
            phase2_synthetic_emotion_lexicon(),
            preprocessor,
        )
        joy = next(item for item in emotion.category_statistics if item.category == "joy")
        passed = joy.associated_token_count == 2 and joy.proportion_of_lexical_tokens == 0.5
        checks.append(
            DiagnosticCheck(
                "Categorical emotion calculation",
                passed,
                "Hand-calculated joy count and denominator reproduced."
                if passed
                else "The hand-calculated categorical result did not reproduce.",
            )
        )
    except Exception as error:
        checks.append(DiagnosticCheck("Categorical emotion calculation", False, str(error)))

    try:
        intensity = analyze_lexicon(
            create_text_document(
                "self-test-intensity", "Self-test", "Rage rage fear stone."
            ),
            phase2_synthetic_intensity_lexicon(),
            preprocessor,
        )
        anger = next(item for item in intensity.intensity_statistics if item.category == "anger")
        passed = anger.token_weighted.mean is not None and math.isclose(
            anger.token_weighted.mean, 0.6
        )
        checks.append(
            DiagnosticCheck(
                "Emotion intensity calculation",
                passed,
                "Hand-calculated matched intensity mean reproduced."
                if passed
                else "The hand-calculated intensity result did not reproduce.",
            )
        )
    except Exception as error:
        checks.append(DiagnosticCheck("Emotion intensity calculation", False, str(error)))

    try:
        meter_report, meter_problems = (
            run_synthetic_performance_meter_validation()
        )
        passed = not meter_problems
        checks.append(
            DiagnosticCheck(
                "Performance-aware meter safeguards",
                passed,
                (
                    "Fixed candidates, generic alternating recurrence, and "
                    "unchanged lexical stress reproduced."
                    if passed
                    else " ".join(meter_problems)
                ),
            )
        )
    except Exception as error:
        checks.append(
            DiagnosticCheck(
                "Performance-aware meter safeguards",
                False,
                str(error),
            )
        )
    return tuple(checks)


def run_self_test() -> tuple[DiagnosticCheck, ...]:
    """Run safe read-only checks without sending data or changing source files."""

    checks = list(run_runtime_self_test())

    for spec in LEXICON_SPECS:
        try:
            lexicon = load_lexicon(spec.lexicon_id)
            checks.append(
                DiagnosticCheck(
                    spec.display_name,
                    True,
                    f"{lexicon.validation.usable_entries:,} entries; source checksum verified.",
                )
            )
        except Exception as error:
            checks.append(DiagnosticCheck(spec.display_name, False, str(error)))
    return tuple(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use concise setup-compatible output; checks remain local and read-only.",
    )
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help=(
            "Check the application runtime and synthetic formulas without "
            "requiring separately installed research lexicons."
        ),
    )
    arguments = parser.parse_args()
    checks = (
        run_runtime_self_test()
        if arguments.runtime_only
        else run_self_test()
    )
    heading = (
        "VerseVAD core runtime diagnostics"
        if arguments.runtime_only
        else "VerseVAD local diagnostics"
    )
    print(heading)
    print("No texts or lexicons were sent anywhere, and source files were not changed.")
    for check in checks:
        marker = "PASS" if check.passed else "FAIL"
        print(f"[{marker}] {check.check}: {check.detail}")
    passed = all(check.passed for check in checks)
    print("All checks passed." if passed else "One or more checks failed; report the lines above.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
