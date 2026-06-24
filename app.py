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
    compare_papers,
    delete_paper,
    ensure_storage_files,
    extract_text_from_upload,
    load_saved_papers,
    make_paper_id,
    recall_answer_question,
    save_paper,
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
        st.session_state.papers = []
    if "active_paper_index" not in st.session_state:
        st.session_state.active_paper_index = 0


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
        st.session_state.papers.pop(index)

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

    st.success(f"Extracted summary points from about {assistant['word_count']} words.")


def render_paper_summary(paper: dict[str, Any]) -> None:
    """Display extracted summary information for one paper."""
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

    tab_labels = [
        paper.get("paper_title") or paper.get("uploaded_file_name") or f"Paper {index + 1}"
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
        if added_count:
            st.success(f"Loaded {added_count} new paper{'s' if added_count != 1 else ''}.")
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Summarise paper", type="primary"):
            run_extraction()
            st.rerun()
    with col2:
        if st.button("Summarise all"):
            for index, paper_item in enumerate(st.session_state.papers):
                st.session_state.active_paper_index = index
                st.session_state.paper = paper_item
                run_extraction()
            sync_active_paper()
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
        st.download_button(
            "Download sources as CSV",
            data=pd.DataFrame({"Source": paper["sources"]}).to_csv(index=False).encode("utf-8"),
            file_name="paper_sources.csv",
            mime="text/csv",
        )


def recall_tab() -> None:
    st.header("Recall")
    st.write("Ask a question about the uploaded paper. The app answers using only the paper text and extracted points.")

    paper = st.session_state.paper
    question = st.text_input(
        "Question",
        placeholder="Example: What did the paper find about apoptosis?",
    )

    if not paper.get("paper_text", "").strip() and not paper.get("auto_summary", "").strip():
        st.info("Upload or paste a paper in the Paper Input tab before using recall.")
        return

    if not question.strip():
        st.caption("Enter a question about the paper to retrieve a local answer.")
        return

    result = recall_answer_question(paper, question)
    if not result["matches"]:
        st.warning(result["answer"])
        return

    st.subheader("Answer")
    st.caption(result["answer"])
    if result.get("main_point"):
        st.markdown("**Short answer**")
        st.info(result["main_point"])

    with st.expander("Detailed answer", expanded=True):
        key_details = result.get("key_details", [])
        if key_details:
            st.markdown("**Key details**")
            for point in key_details:
                st.markdown(f"- {point}")
        else:
            st.caption("No extra details were found beyond the short answer.")

    st.caption(f"Confidence: {result['confidence']}")

    with st.expander("Supporting evidence"):
        render_wrapped_table(result["matches"])
        for index, match in enumerate(result["matches"], start=1):
            st.markdown(f"**{index}. {match['section']}**")
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
    selected_labels = st.multiselect("Papers to compare", labels, default=labels[:2])
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
    st.write("Load, view, or delete locally saved paper summaries.")

    if st.button("Save current paper"):
        save_current_paper()

    papers = load_saved_papers()
    if not papers:
        st.info("No saved papers yet.")
        return

    table = pd.DataFrame(
        [
            {
                "Title": paper.get("paper_title", ""),
                "Date reviewed": paper.get("date_reviewed", ""),
                "Sources": len(paper.get("sources", [])),
                "Summary": paper.get("auto_summary", ""),
            }
            for paper in papers
        ]
    )
    render_wrapped_table(table.to_dict("records"))

    labels = [
        f"{paper.get('paper_title', 'Untitled paper')} ({paper.get('date_reviewed', 'No date')})"
        for paper in papers
    ]
    selected_label = st.selectbox("Saved paper", labels)
    selected_paper = papers[labels.index(selected_label)]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load saved paper"):
            loaded_paper = normalise_paper(selected_paper)
            st.session_state.papers.append(loaded_paper)
            st.session_state.active_paper_index = len(st.session_state.papers) - 1
            st.session_state.paper = loaded_paper
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

    tabs = st.tabs(["Paper Input", "Summary", "Sources", "Recall", "Comparison", "Saved Papers"])
    with tabs[0]:
        paper_input_tab()
    with tabs[1]:
        summary_tab()
    with tabs[2]:
        sources_tab()
    with tabs[3]:
        recall_tab()
    with tabs[4]:
        comparison_tab()
    with tabs[5]:
        saved_papers_tab()

    st.sidebar.title("Local files")
    st.sidebar.write("Saved summaries: `saved_papers.json`")
    st.sidebar.title("AI provider")
    st.sidebar.write("DeepSeek: enabled" if deepseek_is_enabled() else "DeepSeek: set `DEEPSEEK_API_KEY` to enable")
    st.sidebar.caption("Without a DeepSeek key, summarisation stays fully local.")


if __name__ == "__main__":
    main()
