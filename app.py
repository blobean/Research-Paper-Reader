"""Research Paper Reading Helper.

A local Streamlit summariser for beginner biomedical research paper reading.
"""

from __future__ import annotations

import html
import os
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from utils import (
    build_reading_assistant,
    check_source_quality,
    compare_papers,
    delete_paper,
    ensure_storage_files,
    extract_text_from_upload,
    format_citation_sources,
    load_saved_papers,
    make_in_text_citation,
    make_paper_id,
    recall_answer_across_papers,
    recall_answer_question,
    save_paper,
    SAVED_PAPERS_FILE,
    serialise_value,
)


def default_paper() -> dict[str, Any]:
    """Return a blank paper record for the summariser."""
    return {
        "paper_id": "",
        "uploaded_file_id": "",
        "uploaded_file_name": "",
        "paper_title": "",
        "date_reviewed": date.today().isoformat(),
        "paper_text": "",
        "auto_summary": "",
        "auto_key_points": [],
        "auto_keywords": [],
        "auto_method_points": [],
        "auto_result_points": [],
        "auto_limitation_points": [],
        "summary_provider": "",
        "sources": [],
    }


def normalise_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """Merge a saved paper into the current simple app shape."""
    normalised = default_paper()
    normalised.update(paper)
    for field in [
        "auto_key_points",
        "auto_keywords",
        "auto_method_points",
        "auto_result_points",
        "auto_limitation_points",
        "sources",
    ]:
        if not isinstance(normalised.get(field), list):
            normalised[field] = []
    return normalised


def initialise_session() -> None:
    """Set up local storage and session state."""
    ensure_storage_files()
    configure_deepseek_from_secrets()
    if "paper" not in st.session_state:
        st.session_state.paper = default_paper()
    if "papers" not in st.session_state:
        st.session_state.papers = [normalise_paper(paper) for paper in load_saved_papers()]
    if "active_paper_index" not in st.session_state:
        st.session_state.active_paper_index = 0
    sync_active_paper()


def configure_deepseek_from_secrets() -> None:
    """Allow Streamlit secrets to configure the DeepSeek API key."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    try:
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
    except Exception:
        api_key = ""
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = str(api_key)


def deepseek_is_enabled() -> bool:
    """Return whether DeepSeek summarisation is configured."""
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def paper_label(paper: dict[str, Any], index: int = 0) -> str:
    """Return a readable label for a paper."""
    return paper.get("paper_title") or paper.get("uploaded_file_name") or f"Paper {index + 1}"


def paper_search_text(paper: dict[str, Any]) -> str:
    """Collect searchable saved-paper text."""
    fields = [
        paper.get("paper_title", ""),
        paper.get("uploaded_file_name", ""),
        paper.get("auto_summary", ""),
        " ".join(paper.get("auto_key_points", [])),
        " ".join(paper.get("auto_keywords", [])),
        " ".join(paper.get("auto_method_points", [])),
        " ".join(paper.get("auto_result_points", [])),
        " ".join(paper.get("auto_limitation_points", [])),
    ]
    return " ".join(fields).lower()


def paper_category(paper: dict[str, Any]) -> str:
    """Infer a simple research theme category from saved keywords and summaries."""
    searchable = paper_search_text(paper)
    categories = [
        ("Cell Biology", ["cell", "cells", "apoptosis", "mitosis", "protein", "gene", "genes"]),
        ("Immunology", ["immune", "immunity", "inflammation", "inflammatory", "cytokine"]),
        ("Cancer", ["cancer", "tumor", "tumour", "oncology", "carcinoma"]),
        ("Microbiology", ["bacteria", "bacterial", "virus", "viral", "pathogen", "microbiome"]),
        ("Clinical / Patients", ["patient", "patients", "clinical", "cohort", "trial", "participant"]),
        ("Methods / Assays", ["assay", "analysis", "method", "methods", "sequencing", "microscopy"]),
        ("Biomarkers", ["biomarker", "marker", "diagnostic", "indicator"]),
    ]
    for category, terms in categories:
        if any(term in searchable for term in terms):
            return category
    return "Other"


def sync_active_paper() -> None:
    """Keep the selected paper and paper list in sync."""
    if st.session_state.papers:
        index = min(st.session_state.active_paper_index, len(st.session_state.papers) - 1)
        st.session_state.active_paper_index = index
        st.session_state.paper = st.session_state.papers[index]


def replace_active_paper(paper: dict[str, Any]) -> None:
    """Replace the current paper without losing other uploaded documents."""
    if st.session_state.papers:
        st.session_state.papers[st.session_state.active_paper_index] = paper
    else:
        st.session_state.papers.append(paper)
        st.session_state.active_paper_index = 0
    st.session_state.paper = paper


def delete_workspace_paper(index: int) -> None:
    """Delete one paper from the current workspace tabs."""
    if not st.session_state.papers:
        st.session_state.paper = default_paper()
        st.session_state.active_paper_index = 0
        return

    if 0 <= index < len(st.session_state.papers):
        removed_paper = st.session_state.papers.pop(index)
        if removed_paper.get("paper_id"):
            delete_paper(removed_paper["paper_id"])

    if st.session_state.papers:
        st.session_state.active_paper_index = min(index, len(st.session_state.papers) - 1)
        st.session_state.paper = st.session_state.papers[st.session_state.active_paper_index]
    else:
        st.session_state.active_paper_index = 0
        st.session_state.paper = default_paper()


def update_paper(field: str, value: Any) -> None:
    """Update one field in the current paper record."""
    st.session_state.paper[field] = serialise_value(value)
    if st.session_state.papers:
        st.session_state.papers[st.session_state.active_paper_index] = st.session_state.paper


def render_wrapped_table(rows: list[dict[str, Any]]) -> None:
    """Render a full-width wrapping table for long text."""
    if not rows:
        return

    columns = list(rows[0].keys())
    header_style = (
        "background-color:#dbeafe;color:#0f172a;font-weight:800;font-size:16px;"
        "line-height:1.35;border:1px solid #94a3b8;padding:12px;text-align:left;"
    )
    cell_style = (
        "background-color:#ffffff;color:#111827;font-size:15px;line-height:1.45;"
        "border:1px solid #cbd5e1;padding:12px;vertical-align:top;"
        "white-space:normal;overflow-wrap:anywhere;word-break:break-word;"
    )
    header_html = "".join(
        f"<th style=\"{header_style}\">{html.escape(str(column))}</th>"
        for column in columns
    )
    body_html = ""
    for row in rows:
        body_html += "<tr>"
        for column in columns:
            value = html.escape(str(row.get(column, ""))).replace("\n", "<br>")
            body_html += f"<td style=\"{cell_style}\">{value}</td>"
        body_html += "</tr>"

    st.markdown(
        f"""
        <style>
        .wrapped-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        </style>
        <table class="wrapped-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{body_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def save_current_paper(paper_to_save: dict[str, Any] | None = None, show_success: bool = True) -> bool:
    """Save the current paper summary locally."""
    paper = paper_to_save or st.session_state.paper
    if not paper.get("paper_text", "").strip():
        st.warning("Upload or paste a paper before saving.")
        return False

    if not paper.get("paper_title", "").strip():
        title_source = paper["paper_text"].strip().splitlines()[0][:80]
        paper["paper_title"] = title_source or "Untitled paper"

    if not paper.get("paper_id"):
        paper["paper_id"] = make_paper_id(paper["paper_title"])

    save_paper(paper)
    if st.session_state.papers:
        for index, saved_paper in enumerate(st.session_state.papers):
            if saved_paper is paper or saved_paper.get("paper_id") == paper.get("paper_id"):
                st.session_state.papers[index] = paper
                break
    if paper_to_save is None:
        st.session_state.paper = paper
        if st.session_state.papers:
            st.session_state.papers[st.session_state.active_paper_index] = paper
    if show_success:
        st.success(f"Saved '{paper['paper_title']}' locally.")
    return True


def run_extraction() -> None:
    """Extract summary points and sources from the current paper text."""
    paper = st.session_state.paper
    if not paper.get("paper_text", "").strip():
        st.warning("Upload or paste a paper before extracting content.")
        return

    assistant = build_reading_assistant(paper["paper_text"])
    update_paper("paper_text", assistant["cleaned_text"])
    update_paper("auto_summary", assistant["short_summary"])
    update_paper("auto_key_points", assistant["key_points"])
    update_paper("auto_keywords", assistant["keywords"])
    update_paper("auto_method_points", assistant["method_points"])
    update_paper("auto_result_points", assistant["result_points"])
    update_paper("auto_limitation_points", assistant["limitation_points"])
    update_paper("summary_provider", assistant.get("summary_provider", "Local extractor"))
    update_paper("sources", assistant["sources"])

    if not paper.get("paper_title", "").strip():
        first_line = assistant["cleaned_text"].splitlines()[0] if assistant["cleaned_text"] else ""
        update_paper("paper_title", first_line[:80] or "Untitled paper")

    save_current_paper(show_success=False)
    st.success(f"Extracted summary points from about {assistant['word_count']} words.")


def render_paper_summary(paper: dict[str, Any]) -> None:
    """Display extracted summary information for one paper."""
    source_quality = check_source_quality(paper.get("sources", []))
    st.subheader("Source checker")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Verdict", source_quality["verdict"])
    metric_col2.metric("Sources", source_quality["source_count"])
    metric_col3.metric("Recent", source_quality["recent_count"])
    metric_col4.metric("DOI clues", source_quality["doi_count"])

    if source_quality["verdict"] == "Good":
        st.success("The source list looks usable. Still check key sources manually.")
    elif source_quality["verdict"] == "Needs checking":
        st.warning("The source list is usable, but it needs manual checking.")
    else:
        st.error("The source list is weak or missing.")

    with st.expander("Source checker details"):
        if source_quality["checks"]:
            st.markdown("**Looks okay**")
            for check in source_quality["checks"]:
                st.markdown(f"- {check}")
        if source_quality["warnings"]:
            st.markdown("**Check manually**")
            for warning in source_quality["warnings"]:
                st.markdown(f"- {warning}")

    if paper.get("auto_summary"):
        if paper.get("summary_provider"):
            st.caption(f"Generated with {paper['summary_provider']}.")
        st.subheader("Reworded Summary")
        st.write(paper["auto_summary"])

    if paper.get("auto_key_points"):
        st.subheader("Key Points")
        for point in paper["auto_key_points"]:
            st.markdown(f"- **{point}**")

    if paper.get("auto_keywords"):
        st.subheader("Keywords")
        st.write(", ".join(paper["auto_keywords"][:8]))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Methods Points")
        if paper.get("auto_method_points"):
            for point in paper["auto_method_points"]:
                st.markdown(f"- {point}")
        else:
            st.caption("No methods points extracted yet.")
    with col2:
        st.subheader("Results Points")
        if paper.get("auto_result_points"):
            for point in paper["auto_result_points"]:
                st.markdown(f"- {point}")
        else:
            st.caption("No results points extracted yet.")
    with col3:
        st.subheader("Limitations Points")
        if paper.get("auto_limitation_points"):
            for point in paper["auto_limitation_points"]:
                st.markdown(f"- {point}")
        else:
            st.caption("No limitations points extracted yet.")


def render_summary_section() -> None:
    """Display summaries, using subtabs when multiple papers are loaded."""
    papers_with_content = [
        paper
        for paper in (st.session_state.papers or [st.session_state.paper])
        if paper.get("paper_text") or paper.get("auto_summary")
    ]
    if not papers_with_content:
        return

    if len(papers_with_content) == 1:
        render_paper_summary(papers_with_content[0])
        return

    active_paper_id = st.session_state.paper.get("paper_id")
    if active_paper_id:
        papers_with_content = sorted(
            papers_with_content,
            key=lambda paper: paper.get("paper_id") != active_paper_id,
        )

    tab_labels = [
        paper_label(paper, index)
        for index, paper in enumerate(papers_with_content)
    ]
    summary_tabs = st.tabs(tab_labels)
    for tab, paper in zip(summary_tabs, papers_with_content):
        with tab:
            render_paper_summary(paper)


def paper_input_tab() -> None:
    st.header("Paper Input")
    st.write("Upload a research paper or paste its text. The app can use DeepSeek for faster summaries when configured, with local extraction as a fallback.")

    sync_active_paper()
    paper = st.session_state.paper
    uploaded_files = st.file_uploader("Upload research paper files", type=["txt", "pdf"], accept_multiple_files=True)
    if uploaded_files:
        added_count = 0
        existing_file_ids = {item.get("uploaded_file_id") for item in st.session_state.papers}
        for uploaded_file in uploaded_files:
            uploaded_file_id = f"{uploaded_file.name}:{uploaded_file.size}"
            extracted_text = extract_text_from_upload(uploaded_file)
            if extracted_text.startswith("PDF reading requires") or extracted_text.startswith("Could not read"):
                st.warning(f"{uploaded_file.name}: {extracted_text}")
                continue
            if uploaded_file_id in existing_file_ids:
                continue
            new_paper = default_paper()
            new_paper["uploaded_file_id"] = uploaded_file_id
            new_paper["uploaded_file_name"] = uploaded_file.name
            new_paper["paper_title"] = uploaded_file.name.rsplit(".", 1)[0]
            new_paper["paper_text"] = extracted_text
            st.session_state.papers.append(new_paper)
            st.session_state.active_paper_index = len(st.session_state.papers) - 1
            st.session_state.paper = new_paper
            existing_file_ids.add(uploaded_file_id)
            added_count += 1
            save_current_paper(new_paper, show_success=False)
        if added_count:
            st.success(f"Loaded and saved {added_count} new paper{'s' if added_count != 1 else ''}.")
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Summarise paper", type="primary"):
            run_extraction()
            st.session_state.requested_page = "Summary"
            st.rerun()
    with col2:
        if st.button("Summarise all"):
            for index, paper_item in enumerate(st.session_state.papers):
                st.session_state.active_paper_index = index
                st.session_state.paper = paper_item
                run_extraction()
            sync_active_paper()
            st.session_state.requested_page = "Summary"
            st.rerun()
    with col3:
        if st.button("Start new paper"):
            new_paper = default_paper()
            st.session_state.papers.append(new_paper)
            st.session_state.active_paper_index = len(st.session_state.papers) - 1
            st.session_state.paper = new_paper
            st.rerun()

    papers_to_show = st.session_state.papers or [st.session_state.paper]
    tab_labels = [
        paper_item.get("paper_title") or paper_item.get("uploaded_file_name") or f"Paper {index + 1}"
        for index, paper_item in enumerate(papers_to_show)
    ]
    previous_active_index = min(st.session_state.active_paper_index, len(papers_to_show) - 1)
    paper_tabs = st.tabs(tab_labels)
    for index, (tab, paper_item) in enumerate(zip(paper_tabs, papers_to_show)):
        with tab:
            st.session_state.active_paper_index = index
            st.session_state.paper = paper_item
            update_paper(
                "paper_title",
                st.text_input("Paper title", value=paper_item.get("paper_title", ""), key=f"title_{index}"),
            )
            reviewed = st.date_input(
                "Date reviewed",
                value=date.fromisoformat(paper_item["date_reviewed"])
                if paper_item.get("date_reviewed") and len(paper_item["date_reviewed"]) == 10
                else date.today(),
                key=f"date_{index}",
            )
            update_paper("date_reviewed", reviewed)

            if paper_item.get("paper_text"):
                word_count = len(paper_item["paper_text"].split())
                st.caption(f"Uploaded paper text stored locally ({word_count} words).")
            else:
                st.caption("No paper text uploaded for this tab yet.")
            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("Save this paper", key=f"save_tab_{index}"):
                    save_current_paper(paper_item)
            with action_col2:
                if st.button("Delete this paper tab", key=f"delete_tab_{index}"):
                    delete_workspace_paper(index)
                    st.success("Paper tab deleted from this workspace.")
                    st.rerun()
    st.session_state.active_paper_index = previous_active_index
    sync_active_paper()


def summary_tab() -> None:
    st.header("Summary")
    if not st.session_state.papers and not st.session_state.paper.get("paper_text"):
        st.info("Upload or paste a paper in the Paper Input tab first.")
        return
    render_summary_section()


def sources_tab() -> None:
    st.header("Sources")
    st.write("Sources are extracted from the paper's References or Bibliography section when that section is present.")

    paper = st.session_state.paper
    sources_text = "\n".join(paper.get("sources", []))
    edited_sources = st.text_area(
        "Sources used in the paper",
        value=sources_text,
        height=420,
        help="One source per line. You can edit this list after extraction.",
    )
    update_paper(
        "sources",
        [line.strip() for line in edited_sources.splitlines() if line.strip()],
    )

    if paper.get("sources"):
        citation_style = st.selectbox(
            "Citation format",
            ["Original", "APA", "MLA", "Vancouver", "Harvard"],
            help="Best-effort formatting from the extracted reference text.",
        )
        formatted_sources = format_citation_sources(paper["sources"], citation_style)

        st.subheader("Formatted citations")
        for source in formatted_sources:
            st.markdown(f"- {source}")

        st.subheader("Specific in-text citation")
        source_labels = [
            f"{index}. {source[:120]}{'...' if len(source) > 120 else ''}"
            for index, source in enumerate(paper["sources"], start=1)
        ]
        selected_source_label = st.selectbox("Source to cite", source_labels)
        selected_source_index = source_labels.index(selected_source_label)
        in_text_citation = make_in_text_citation(
            paper["sources"][selected_source_index],
            citation_style,
            selected_source_index + 1,
        )
        st.code(in_text_citation)
        st.caption("This is best-effort because extracted sources are plain text.")

        download_col1, download_col2 = st.columns(2)
        with download_col1:
            st.download_button(
                "Download formatted citations as TXT",
                data="\n\n".join(formatted_sources).encode("utf-8"),
                file_name=f"paper_sources_{citation_style.lower()}.txt",
                mime="text/plain",
            )
        with download_col2:
            st.download_button(
                "Download formatted citations as CSV",
                data=pd.DataFrame(
                    {
                        "Citation format": citation_style,
                        "Formatted source": formatted_sources,
                        "Original source": paper["sources"],
                    }
                ).to_csv(index=False).encode("utf-8"),
                file_name=f"paper_sources_{citation_style.lower()}.csv",
                mime="text/csv",
            )

        st.download_button(
            "Download original sources as CSV",
            data=pd.DataFrame({"Source": paper["sources"]}).to_csv(index=False).encode("utf-8"),
            file_name="paper_sources.csv",
            mime="text/csv",
        )


def recall_tab() -> None:
    st.header("Recall")
    st.write("Ask a question across one or more uploaded papers. The app gives a direct answer from paper text and extracted points.")

    papers = st.session_state.papers or [st.session_state.paper]
    available_papers = [
        paper
        for paper in papers
        if paper.get("paper_text", "").strip() or paper.get("auto_summary", "").strip()
    ]
    if not available_papers:
        st.info("Upload or paste a paper in the Paper Input tab before using recall.")
        return

    labels = [
        paper.get("paper_title") or paper.get("uploaded_file_name") or f"Paper {index + 1}"
        for index, paper in enumerate(available_papers)
    ]
    selected_labels = st.multiselect("Papers to search", labels, default=labels)
    selected_papers = [
        available_papers[labels.index(label)]
        for label in selected_labels
    ]
    question = st.text_input(
        "Question",
        placeholder="Example: What did the paper find about apoptosis?",
    )

    if not selected_papers:
        st.warning("Select at least one paper to search.")
        return

    if not question.strip():
        st.caption("Enter a question to retrieve a local answer from the selected papers.")
        return

    if len(selected_papers) == 1:
        result = recall_answer_question(selected_papers[0], question)
    else:
        result = recall_answer_across_papers(selected_papers, question)
    if not result["matches"]:
        st.warning(result["answer"])
        return

    st.subheader("Direct answer")
    if result.get("main_point"):
        st.success(result["main_point"])
    st.caption(f"{result['answer']} Confidence: {result['confidence']}.")

    with st.expander("Why this answer", expanded=False):
        key_details = result.get("key_details", [])
        if key_details:
            for point in key_details:
                st.markdown(f"- {point}")
        else:
            st.caption("No extra details found beyond the direct answer.")

    with st.expander("Evidence from the paper"):
        for index, match in enumerate(result["matches"], start=1):
            paper_label = match.get("paper_title")
            heading = f"{paper_label} - {match['section']}" if paper_label else match["section"]
            st.markdown(f"**{index}. {heading}**")
            st.caption(f"Matched terms: {match['matched_terms']}")
            st.write(match["snippet"])


def comparison_tab() -> None:
    st.header("Comparison")
    st.write("Compare uploaded papers side by side, including shared themes, unique points, and possible opposing findings. DeepSeek assists when configured.")

    if len(st.session_state.papers) < 2:
        st.info("Upload at least two papers in the Paper Input tab to use comparison.")
        return

    labels = [
        paper.get("paper_title") or paper.get("uploaded_file_name") or f"Paper {index + 1}"
        for index, paper in enumerate(st.session_state.papers)
    ]
    st.subheader("Choose papers")
    if "comparison_selected_labels" not in st.session_state:
        st.session_state.comparison_selected_labels = labels[:2]
    st.session_state.comparison_selected_labels = [
        label for label in st.session_state.comparison_selected_labels if label in labels
    ]

    select_col1, select_col2, select_col3 = st.columns([1, 1, 3])
    with select_col1:
        if st.button("Select all papers"):
            st.session_state.comparison_selected_labels = labels
            st.rerun()
    with select_col2:
        if st.button("Clear selection"):
            st.session_state.comparison_selected_labels = []
            st.rerun()

    selected_labels = st.multiselect(
        "Papers to compare",
        labels,
        default=st.session_state.comparison_selected_labels,
        help="Choose two or more uploaded or saved papers for this comparison.",
    )
    st.session_state.comparison_selected_labels = selected_labels
    st.caption(f"{len(selected_labels)} of {len(labels)} papers selected.")
    selected_papers = [
        st.session_state.papers[labels.index(label)]
        for label in selected_labels
    ]
    if len(selected_papers) < 2:
        st.warning("Select at least two papers.")
        return

    comparison = compare_papers(selected_papers)

    if comparison.get("comparison_provider"):
        st.caption(f"Comparison generated with {comparison['comparison_provider']}.")

    if comparison.get("comparison_summary"):
        st.subheader("AI comparison overview")
        st.write(comparison["comparison_summary"])

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Shared content points")
            for point in comparison.get("shared_themes", []) or ["No shared AI themes returned."]:
                st.markdown(f"- {point}")
        with col2:
            st.subheader("Key differences")
            for point in comparison.get("key_differences", []) or ["No AI differences returned."]:
                st.markdown(f"- {point}")

        if comparison.get("paper_takeaways"):
            st.subheader("Takeaways by paper")
            for title, takeaways in comparison["paper_takeaways"].items():
                with st.expander(title):
                    for takeaway in takeaways or ["No takeaways returned."]:
                        st.markdown(f"- {takeaway}")

        if comparison.get("study_cautions"):
            st.subheader("Comparison cautions")
            for caution in comparison["study_cautions"]:
                st.markdown(f"- {caution}")

    st.subheader("Side-by-side details")
    detail_rows = []
    for paper in selected_papers:
        detail_rows.append(
            {
                "Paper": paper.get("paper_title", "Untitled paper"),
                "Short summary": paper.get("auto_summary", "Not summarised yet"),
                "Keywords": ", ".join(paper.get("auto_keywords", [])[:10]),
                "Sources": len(paper.get("sources", [])),
            }
        )
    render_wrapped_table(detail_rows)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Common themes")
        if comparison["common_themes"]:
            for theme in comparison["common_themes"][:8]:
                st.markdown(f"- **{theme['theme']}**")
                st.caption(f"Shared idea terms: {theme['shared_terms']}")
        else:
            st.caption("No common themes found yet. Summarise each paper first for better comparison.")

    with col2:
        st.subheader("Unique themes")
        for title, keywords in comparison["unique_keywords"].items():
            with st.expander(title):
                if keywords:
                    for keyword in keywords[:12]:
                        st.markdown(f"- {keyword}")
                else:
                    st.caption("No unique keywords found.")

    st.subheader("Common ideas with evidence")
    if comparison["common_ideas"]:
        for idea in comparison["common_ideas"][:6]:
            with st.expander(f"{idea['theme']} ({idea['papers']})"):
                st.markdown("**Shared terms**")
                st.write(idea["shared_terms"])
                st.markdown("**Paper A idea**")
                st.write(idea["paper_a_idea"])
                st.markdown("**Paper B idea**")
                st.write(idea["paper_b_idea"])
    else:
        st.caption("No overlapping idea snippets found.")

    st.subheader("Possible opposing findings")
    if comparison.get("possible_oppositions"):
        for point in comparison["possible_oppositions"]:
            st.markdown(f"- {point}")
    elif comparison["oppositions"]:
        render_wrapped_table(comparison["oppositions"])
    else:
        st.caption("No obvious opposing increase/decrease result language found.")

    st.subheader("Extracted points by paper")
    for paper in selected_papers:
        with st.expander(paper.get("paper_title", "Untitled paper")):
            st.markdown("**Methods points**")
            for point in paper.get("auto_method_points", []) or ["No methods points extracted."]:
                st.markdown(f"- {point}")
            st.markdown("**Results points**")
            for point in paper.get("auto_result_points", []) or ["No results points extracted."]:
                st.markdown(f"- {point}")
            st.markdown("**Limitations points**")
            for point in paper.get("auto_limitation_points", []) or ["No limitations points extracted."]:
                st.markdown(f"- {point}")


def saved_papers_tab() -> None:
    st.header("Saved Papers")
    st.write("Search saved papers by title, keyword, summary point, method, result, or limitation.")

    if st.button("Save current paper"):
        save_current_paper()

    papers = [normalise_paper(paper) for paper in load_saved_papers()]
    if not papers:
        st.info("No saved papers yet.")
        return

    search_query = st.text_input(
        "Search saved papers",
        placeholder="Try a keyword, topic, method, result, or paper title",
    )
    query_terms = [
        term.lower()
        for term in search_query.split()
        if term.strip()
    ]
    filtered_papers = [
        paper
        for paper in papers
        if not query_terms or all(term in paper_search_text(paper) for term in query_terms)
    ]
    if not filtered_papers:
        st.warning("No saved papers matched that search.")
        return

    category_names = sorted({paper_category(paper) for paper in filtered_papers})
    category_tabs = st.tabs(["All"] + category_names)
    category_groups = {"All": filtered_papers}
    for category in category_names:
        category_groups[category] = [
            paper for paper in filtered_papers if paper_category(paper) == category
        ]

    selected_paper = filtered_papers[0]
    for tab, category in zip(category_tabs, category_groups):
        with tab:
            category_papers = category_groups[category]
            st.caption(f"{len(category_papers)} saved paper{'s' if len(category_papers) != 1 else ''}")
            table = pd.DataFrame(
                [
                    {
                        "Title": paper_label(paper, index),
                        "Category": paper_category(paper),
                        "Keywords": ", ".join(paper.get("auto_keywords", [])[:8]),
                        "Date reviewed": paper.get("date_reviewed", ""),
                        "Summary": paper.get("auto_summary", ""),
                    }
                    for index, paper in enumerate(category_papers)
                ]
            )
            render_wrapped_table(table.to_dict("records"))

    labels = [
        f"{paper_label(paper, index)} ({paper_category(paper)})"
        for index, paper in enumerate(filtered_papers)
    ]
    selected_label = st.selectbox("Open saved paper", labels)
    selected_paper = filtered_papers[labels.index(selected_label)]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open in Summary", type="primary"):
            loaded_paper = normalise_paper(selected_paper)
            existing_index = next(
                (
                    index
                    for index, paper in enumerate(st.session_state.papers)
                    if paper.get("paper_id") == loaded_paper.get("paper_id")
                ),
                None,
            )
            if existing_index is None:
                st.session_state.papers.append(loaded_paper)
                st.session_state.active_paper_index = len(st.session_state.papers) - 1
            else:
                st.session_state.papers[existing_index] = loaded_paper
                st.session_state.active_paper_index = existing_index
            st.session_state.paper = loaded_paper
            st.session_state.requested_page = "Summary"
            st.rerun()
    with col2:
        if st.button("Delete saved paper"):
            delete_paper(selected_paper.get("paper_id", ""))
            st.success("Saved paper deleted.")
            st.rerun()

    st.subheader("Saved summary preview")
    render_paper_summary(normalise_paper(selected_paper))


def main() -> None:
    st.set_page_config(page_title="Research Paper Reading Helper", layout="wide")
    initialise_session()

    st.title("Research Paper Reading Helper")
    st.write("Upload or paste a research paper, then generate summary points and extract its sources.")

    page_names = ["Paper Input", "Summary", "Sources", "Recall", "Comparison", "Saved Papers"]
    if "active_page" not in st.session_state or st.session_state.active_page not in page_names:
        st.session_state.active_page = page_names[0]
    if st.session_state.get("requested_page") in page_names:
        st.session_state.active_page = st.session_state.requested_page
        st.session_state.navigation_page = st.session_state.requested_page
        del st.session_state.requested_page
    elif st.session_state.get("navigation_page") in page_names:
        st.session_state.active_page = st.session_state.navigation_page

    st.sidebar.title("Navigation")
    active_page = st.sidebar.radio(
        "Go to",
        page_names,
        index=page_names.index(st.session_state.active_page),
        key="navigation_page",
    )
    st.session_state.active_page = active_page

    if active_page == "Paper Input":
        paper_input_tab()
    elif active_page == "Summary":
        summary_tab()
    elif active_page == "Sources":
        sources_tab()
    elif active_page == "Recall":
        recall_tab()
    elif active_page == "Comparison":
        comparison_tab()
    elif active_page == "Saved Papers":
        saved_papers_tab()

    st.sidebar.title("Local files")
    st.sidebar.write(f"Saved summaries: `{SAVED_PAPERS_FILE}`")
    st.sidebar.title("AI provider")
    st.sidebar.write("DeepSeek: enabled" if deepseek_is_enabled() else "DeepSeek: set `DEEPSEEK_API_KEY` to enable")
    st.sidebar.caption("Without a DeepSeek key, summarisation stays fully local.")


if __name__ == "__main__":
    main()
