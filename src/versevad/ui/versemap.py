"""Responsive Streamlit presentation for VerseMap results."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from versevad.exports.versemap import export_versemap_bundle
from versevad.ui.design import (
    PUBLICATION_CHART_COLORS,
    publication_chart,
    render_dataframe,
)
from versevad.versemap import VerseMapAnalysisResult


_KIND_LABELS = {
    "reference_poem": "Reference poem",
    "reference_poet": "Reference poet centroid",
    "query_poem": "Analyzed poem",
}
_KIND_COLORS = {
    "Reference poem": PUBLICATION_CHART_COLORS[2],
    "Reference poet centroid": PUBLICATION_CHART_COLORS[4],
    "Analyzed poem": PUBLICATION_CHART_COLORS[0],
}


def _map_frame(result: VerseMapAnalysisResult) -> pd.DataFrame:
    rows = [
        {
            "Point ID": result.profile.text_id,
            "Kind": "Analyzed poem",
            "Poet": "",
            "Title": result.profile.title,
            "Poem count": 1,
            "Component 1": result.coordinate_1,
            "Component 2": result.coordinate_2,
        }
    ]
    rows.extend(
        {
            "Point ID": item.point_id,
            "Kind": _KIND_LABELS[item.point_kind],
            "Poet": item.poet_name,
            "Title": item.title,
            "Poem count": item.poem_count,
            "Component 1": item.coordinate_1,
            "Component 2": item.coordinate_2,
        }
        for item in result.map_points
    )
    return pd.DataFrame(rows)


def render_versemap(
    result: VerseMapAnalysisResult | None,
    *,
    show_poem_neighbors: bool = True,
    export_key: str = "single",
    note_workspace: str | None = None,
) -> None:
    st.subheader("VerseMap")
    st.write(
        "VerseMap compares one pinned, coverage-aware profile with a versioned "
        "public-domain reference corpus. Proximity is descriptive: it is not an "
        "authorship, influence, quality, genre, or meaning claim."
    )
    if result is None:
        st.info(
            "Enable VerseMap under Additional Optional Models and analyze the text. "
            "If it is unavailable, run the VerseMap reference updater first."
        )
        return

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Reference poems",
        f"{sum(item.point_kind == 'reference_poem' for item in result.map_points):,}",
    )
    metric_columns[1].metric(
        "Reference poets",
        f"{sum(item.point_kind == 'reference_poet' for item in result.map_points):,}",
    )
    metric_columns[2].metric(
        "Feature weight available",
        f"{result.evidence_weight_coverage:.1%}",
    )
    nearest = (
        result.nearest_poems[0].title
        if show_poem_neighbors and result.nearest_poems
        else (
            result.nearest_poets[0].poet_name
            if result.nearest_poets
            else "Insufficient shared evidence"
        )
    )
    metric_columns[3].metric("Nearest reference", nearest)

    with st.expander("VerseMap Space", expanded=False):
        frame = _map_frame(result).dropna(
            subset=["Component 1", "Component 2"]
        )
        base = (
            alt.Chart(frame)
            .mark_circle(opacity=0.58)
            .encode(
                x=alt.X(
                    "Component 1:Q",
                    title=(
                        "Component 1 "
                        f"({result.explained_variance_1:.1%} reference variance)"
                    ),
                ),
                y=alt.Y(
                    "Component 2:Q",
                    title=(
                        "Component 2 "
                        f"({result.explained_variance_2:.1%} reference variance)"
                    ),
                ),
                color=alt.Color(
                    "Kind:N",
                    scale=alt.Scale(
                        domain=list(_KIND_COLORS),
                        range=list(_KIND_COLORS.values()),
                    ),
                ),
                size=alt.Size(
                    "Kind:N",
                    sort=list(_KIND_COLORS),
                    scale=alt.Scale(
                        domain=list(_KIND_COLORS),
                        range=[36, 150, 240],
                    ),
                    legend=None,
                ),
                tooltip=[
                    "Kind",
                    "Poet",
                    "Title",
                    "Poem count",
                    alt.Tooltip("Component 1:Q", format=".3f"),
                    alt.Tooltip("Component 2:Q", format=".3f"),
                ],
            )
            .properties(height=560)
            .interactive()
        )
        st.altair_chart(publication_chart(base), width="stretch")
        st.caption(
            "The two axes are weighted PCA composites. Neighbor tables use the "
            "full registered feature space, not only distance on this 2D display."
        )

    with st.expander("Nearest Reference Poems and Poets", expanded=False):
        if show_poem_neighbors:
            st.markdown("#### Reference poems")
            if result.nearest_poems:
                render_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Rank": item.rank,
                                "Poem": item.title,
                                "Poet": item.poet_name,
                                "Distance": item.distance,
                                "Shared Evidence Weight": item.shared_weight,
                            }
                            for item in result.nearest_poems
                        ]
                    ),
                    column_config={
                        "Distance": st.column_config.NumberColumn(format="%.3f"),
                        "Shared Evidence Weight": st.column_config.ProgressColumn(
                            min_value=0.0, max_value=1.0, format="%.1%%"
                        ),
                    },
                )
            else:
                st.warning(
                    "No reference poem met the minimum shared-evidence threshold."
                )
        st.markdown("#### Reference poet centroids")
        if result.nearest_poets:
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Rank": item.rank,
                            "Poet": item.poet_name,
                            "Distance": item.distance,
                            "Shared Evidence Weight": item.shared_weight,
                        }
                        for item in result.nearest_poets
                    ]
                ),
                column_config={
                    "Distance": st.column_config.NumberColumn(format="%.3f"),
                    "Shared Evidence Weight": st.column_config.ProgressColumn(
                        min_value=0.0, max_value=1.0, format="%.1%%"
                    ),
                },
            )
        st.caption(
            "Lower distance means closer under Standard Profile 1.0. The number "
            "is not a probability, confidence score, or attribution."
        )

    with st.expander("Profile Dimensions and Coverage", expanded=False):
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "Group": item.group_id.replace("_", " ").title(),
                        "Dimension": item.label,
                        "Poem Value": item.query_value,
                        "Reference Mean": item.reference_mean,
                        "Reference SD": item.reference_population_sd,
                        "Z Score": item.z_score,
                        "Approx. Percentile": item.percentile,
                        "Coverage": item.coverage_rate,
                        "Eligible": item.eligible_count,
                        "Matched": item.matched_count,
                        "Unit": item.unit,
                    }
                    for item in result.feature_comparisons
                ]
            ),
            column_config={
                "Poem Value": st.column_config.NumberColumn(format="%.3f"),
                "Reference Mean": st.column_config.NumberColumn(format="%.3f"),
                "Reference SD": st.column_config.NumberColumn(format="%.3f"),
                "Z Score": st.column_config.NumberColumn(format="%.3f"),
                "Approx. Percentile": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.1%%"
                ),
                "Coverage": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.1%%"
                ),
            },
        )
        st.caption(
            "Percentiles use the normal approximation to the reference z-score. "
            "Missing values stay missing. Coverage and eligible counts travel with "
            "every lexical dimension."
        )

    with st.expander("Methodology and Export", expanded=False):
        st.markdown(
            f"**{result.profile.profile_id}** | {result.profile_build_id} | "
            f"{result.reference_release_id} | {result.model_id}"
        )
        st.write(
            "Feature groups receive equal total weight; dimensions within a group "
            "share that weight. Skewed positive count measures are log-transformed, "
            "then reference-standardized. PCA is used only for the map. Neighbors "
            "are ranked by weighted standardized Euclidean distance over shared "
            f"evidence, requiring at least "
            f"{result.configuration.minimum_shared_weight:.0%} shared weight."
        )
        bundle = export_versemap_bundle(result, text_title=result.profile.title)
        if note_workspace:
            from versevad.exports.research_notes import (
                append_research_notes_to_docx,
                research_notes_csv,
                research_notes_markdown,
            )
            from versevad.ui.research import render_note_export_options

            selected_notes, include_note_metadata = render_note_export_options(
                note_workspace,
                key_prefix=f"versemap_export_notes_{export_key}",
            )
            if selected_notes:
                bundle["versemap_report.docx"] = append_research_notes_to_docx(
                    bundle["versemap_report.docx"],
                    selected_notes,
                    include_metadata=include_note_metadata,
                )
                bundle["research_notes.csv"] = research_notes_csv(
                    selected_notes,
                    include_metadata=include_note_metadata,
                )
                bundle["research_notes.md"] = research_notes_markdown(
                    selected_notes,
                    include_metadata=include_note_metadata,
                )
        st.download_button(
            "Download VerseMap CSV and Word Report",
            data=_zip_bundle(bundle),
            file_name="VerseMap_report_bundle.zip",
            mime="application/zip",
            key=f"versemap_export_{export_key}_{result.module_result.result_id}",
        )


def _zip_bundle(bundle: dict[str, bytes]) -> bytes:
    import io
    import zipfile

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in bundle.items():
            archive.writestr(name, payload)
    return output.getvalue()


__all__ = ["render_versemap"]
