"""Public VerseVAD training catalog and learner-download workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from versevad.ui.design import render_workspace_header


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = PROJECT_ROOT / "resources" / "training"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TRAINING_URL = "https://www.versevad.org/training"


@dataclass(frozen=True)
class TrainingCourse:
    title: str
    level: str
    study_time: str
    prerequisite: str
    description: str
    emphasis: tuple[str, ...]
    manual_filename: str
    assignment_filename: str


COURSES: tuple[TrainingCourse, ...] = (
    TrainingCourse(
        title="VerseVAD Foundations",
        level="Foundational",
        study_time="4–7 hours",
        prerequisite="None",
        description=(
            "Learn how VerseVAD turns matched lexical and formal evidence into "
            "transparent prompts for close reading. The course introduces "
            "coverage, weighting, major metric families, VerseMap, and "
            "responsible interpretive language."
        ),
        emphasis=(
            "Navigate a complete single-poem analysis",
            "Read coverage and missingness before interpreting scores",
            "Connect computational evidence with close reading",
        ),
        manual_filename="VerseVAD_Foundations_Learner_Manual.docx",
        assignment_filename=(
            "VerseVAD_Foundations_Applied_Analysis_Assignment.docx"
        ),
    ),
    TrainingCourse(
        title="Computational Close Reading with VerseVAD",
        level="Analyst Level 1",
        study_time="12–20 hours",
        prerequisite="VerseVAD Foundations or equivalent competence",
        description=(
            "Design evidence-led computational close readings using affective, "
            "lexical, prosodic, comparison, and VerseMap evidence while keeping "
            "method, textual detail, counterevidence, and limitations visible."
        ),
        emphasis=(
            "Design fit-for-purpose analyses and sensitivity checks",
            "Interpret advanced lexical, sound, form, and comparison evidence",
            "Write reproducible VerseVAD-assisted literary analysis",
        ),
        manual_filename="VerseVAD_Analyst_Level_1_Learner_Manual.docx",
        assignment_filename="VerseVAD_Analyst_Level_1_Applied_Assignment.docx",
    ),
    TrainingCourse(
        title="Advanced Corpus and Research Analysis",
        level="Analyst Level 2",
        study_time="24–40 hours",
        prerequisite="Analyst Level 1 or equivalent competence",
        description=(
            "Build and evaluate literary corpora through documented ingestion, "
            "descriptive and standardized analysis, aggregation choices, "
            "VerseMap, reproducibility, data governance, and scholarly reporting."
        ),
        emphasis=(
            "Design, clean, version, and document a research corpus",
            "Interpret corpus distributions, weighting, PCA, and similarity",
            "Defend methodological, ethical, and reproducibility choices",
        ),
        manual_filename="VerseVAD_Analyst_Level_2_Learner_Manual.docx",
        assignment_filename="VerseVAD_Analyst_Level_2_Applied_Assignment.docx",
    ),
    TrainingCourse(
        title="VerseVAD Authorized Instructor Training",
        level="Instructor",
        study_time="15–25 hours plus observed teaching",
        prerequisite=(
            "Analyst Level 1; Analyst Level 2 for advanced corpus instruction"
        ),
        description=(
            "Prepare to teach VerseVAD accurately and accessibly through adult "
            "learning design, software demonstration, close-reading facilitation, "
            "assessment calibration, ethics, support, and version management."
        ),
        emphasis=(
            "Explain metrics without oversimplifying their evidence boundaries",
            "Demonstrate VerseVAD accessibly and recover from problems transparently",
            "Complete an authorization-readiness teaching practicum",
        ),
        manual_filename="VerseVAD_Authorized_Instructor_Learner_Manual.docx",
        assignment_filename=(
            "VerseVAD_Authorized_Instructor_Applied_Assignment.docx"
        ),
    ),
)


@st.cache_data(show_spinner=False)
def _training_document(path_value: str, modified_ns: int) -> bytes:
    del modified_ns
    path = Path(path_value).resolve()
    try:
        path.relative_to(TRAINING_ROOT.resolve())
    except ValueError as error:
        raise OSError("Training document path escaped the packaged catalog.") from error
    return path.read_bytes()


def _download(course: TrainingCourse, filename: str, label: str, key: str) -> None:
    path = (TRAINING_ROOT / filename).resolve()
    if not path.is_file():
        st.warning(
            f"{label} is unavailable in this installation. Visit the VerseVAD "
            "training website for the current course package."
        )
        return
    st.download_button(
        label,
        data=_training_document(str(path), path.stat().st_mtime_ns),
        file_name=path.name,
        mime=DOCX_MIME,
        key=key,
        width="stretch",
    )


def render_training_workspace() -> None:
    """Render the free public learner catalog without evaluator materials."""

    render_workspace_header(
        "Training",
        (
            "Build practical VerseVAD competence through four free, sequenced "
            "courses in transparent computational close reading."
        ),
        kicker="Free learner manuals and applied exercises",
        status="Four-course pathway",
    )

    with st.container(key="training_website_link"):
        st.link_button(
            "Visit the VerseVAD Training Website",
            TRAINING_URL,
            icon=":material/open_in_new:",
            type="primary",
            width="stretch",
        )
    st.caption(
        "Course updates, additional guidance, and training-program information: "
        "www.versevad.org/training"
    )
    st.info(
        "Learner manuals and applied exercises are included free. Evaluator "
        "answer keys, scoring rubrics, completion decisions, certificates, and "
        "instructor authorization are administered separately and are not "
        "packaged with the public application."
    )

    for position, course in enumerate(COURSES, start=1):
        with st.container(border=True):
            st.subheader(f"{position}. {course.title}")
            st.caption(
                f"{course.level} · {course.study_time} · Prerequisite: "
                f"{course.prerequisite}"
            )
            st.write(course.description)
            with st.expander("What you will practice", expanded=False):
                for item in course.emphasis:
                    st.markdown(f"- {item}")
            manual_column, exercise_column = st.columns(2)
            with manual_column:
                _download(
                    course,
                    course.manual_filename,
                    "Download Learner Manual",
                    f"training_manual_{position}",
                )
            with exercise_column:
                _download(
                    course,
                    course.assignment_filename,
                    "Download Applied Exercise",
                    f"training_assignment_{position}",
                )

    st.caption(
        "All course materials describe VerseVAD evidence as support for close "
        "reading—not as a replacement for literary knowledge, interpretation, "
        "or scholarly judgment."
    )


__all__ = ["COURSES", "TRAINING_ROOT", "TRAINING_URL", "render_training_workspace"]
