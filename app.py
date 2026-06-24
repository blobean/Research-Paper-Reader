"""Research Paper Reading Helper.

A local Streamlit summariser for beginner biomedical research paper reading.
"""

from __future__ import annotations

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
    if "paper" not in st.session_state:
        st.session_state.paper = default_paper()
    if "papers" not in st.session_state:
        st.session_state.papers = []
    if "active_paper_index" not in st.session_state:
        st.session_state.active_paper_index = 0


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


def update_paper(field: str, value: Any) -> None:
    """Update one field in the current paper record."""
    st.session_state.paper[field] = serialise_value(value)
    if st.session_state.papers:
        st.session_state.papers[st.session_state.active_paper_index] = st.session_state.paper


def save_current_paper(show_success: bool = True) -> bool:
    """Save the current paper summary locally."""
    paper = st.session_state.paper
    if not paper.get("paper_text", "").strip():
        st.warning("Upload or paste a paper before saving.")
        return False

    if not paper.get("paper_title", "").strip():
        title_source = paper["paper_text"].strip().splitlines()[0][:80]
        paper["paper_title"] = title_source or "Untitled paper"

    if not paper.get("paper_id"):
        paper["paper_id"] = make_paper_id(paper["paper_title"])

    save_paper(paper)
    if show_success:
        st.success("Paper summary saved locally.")
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
    update_paper("sources", assistant["sources"])

    if not paper.get("paper_title", "").strip():
        first_line = assistant["cleaned_text"].splitlines()[0] if assistant["cleaned_text"] else ""
        update_paper("paper_title", first_line[:80] or "Untitled paper")

    st.success(f"Extracted summary points from about {assistant['word_count']} words.")


def paper_input_tab() -> None:
    st.header("Paper Input")
    st.write("Upload a research paper or paste its text. The app summarises the content locally on this computer.")

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

    if st.session_state.papers:
        labels = [
            paper_item.get("paper_title") or paper_item.get("uploaded_file_name") or f"Paper {index + 1}"
            for index, paper_item in enumerate(st.session_state.papers)
        ]
        selected_label = st.selectbox(
            "Active paper",
            labels,
            index=min(st.session_state.active_paper_index, len(labels) - 1),
        )
        selected_index = labels.index(selected_label)
        if selected_index != st.session_state.active_paper_index:
            st.session_state.active_paper_index = selected_index
            sync_active_paper()
            st.rerun()

    paper = st.session_state.paper

    update_paper(
        "paper_title",
        st.text_input("Paper title", value=paper.get("paper_title", "")),
    )
    reviewed = st.date_input(
        "Date reviewed",
        value=date.fromisoformat(paper["date_reviewed"])
        if paper.get("date_reviewed") and len(paper["date_reviewed"]) == 10
        else date.today(),
    )
    update_paper("date_reviewed", reviewed)

    update_paper(
        "paper_text",
        st.text_area(
            "Paper text",
            value=paper.get("paper_text", ""),
            height=360,
            help="Paste the full text, abstract, or selected sections of the paper.",
        ),
    )

    col1, col2, col3, col4 = st.columns(4)
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
        if st.button("Save summary"):
            save_current_paper()
    with col4:
        if st.button("Start new paper"):
            new_paper = default_paper()
            st.session_state.papers.append(new_paper)
            st.session_state.active_paper_index = len(st.session_state.papers) - 1
            st.session_state.paper = new_paper
            st.rerun()

    if paper.get("auto_summary"):
        st.subheader("Short Summary")
        st.write(paper["auto_summary"])

    if paper.get("auto_keywords"):
        st.subheader("Keywords")
        st.write(", ".join(paper["auto_keywords"]))

    if paper.get("auto_key_points"):
        st.subheader("Content Points")
        for point in paper["auto_key_points"]:
            st.markdown(f"- {point}")

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
        st.dataframe(pd.DataFrame(result["matches"]), use_container_width=True, hide_index=True)
        for index, match in enumerate(result["matches"], start=1):
            st.markdown(f"**{index}. {match['section']}**")
            st.caption(f"Matched terms: {match['matched_terms']}")
            st.write(match["snippet"])


def comparison_tab() -> None:
    st.header("Comparison")
    st.write("Compare uploaded papers side by side, including shared themes, unique points, and possible opposing findings.")

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
    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Where they intersect")
        if comparison["shared_keywords"]:
            for keyword in comparison["shared_keywords"][:15]:
                st.markdown(f"- {keyword}")
        else:
            st.caption("No shared keywords found yet. Summarise each paper first for better comparison.")

    with col2:
        st.subheader("Unique themes")
        for title, keywords in comparison["unique_keywords"].items():
            with st.expander(title):
                if keywords:
                    for keyword in keywords[:12]:
                        st.markdown(f"- {keyword}")
                else:
                    st.caption("No unique keywords found.")

    st.subheader("Possible opposing findings")
    if comparison["oppositions"]:
        st.dataframe(pd.DataFrame(comparison["oppositions"]), use_container_width=True, hide_index=True)
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
                "Summary": paper.get("auto_summary", "")[:120],
            }
            for paper in papers
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

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
    st.write(selected_paper.get("auto_summary", "No summary saved."))


def main() -> None:
    st.set_page_config(page_title="Research Paper Reading Helper", layout="wide")
    initialise_session()

    st.title("Research Paper Reading Helper")
    st.write("Upload or paste a research paper, then generate local summary points and extract its sources.")

    tabs = st.tabs(["Paper Input", "Sources", "Recall", "Comparison", "Saved Papers"])
    with tabs[0]:
        paper_input_tab()
    with tabs[1]:
        sources_tab()
    with tabs[2]:
        recall_tab()
    with tabs[3]:
        comparison_tab()
    with tabs[4]:
        saved_papers_tab()

    st.sidebar.title("Local files")
    st.sidebar.write("Saved summaries: `saved_papers.json`")
    st.sidebar.caption("No login, database, cloud service, or AI API is used.")


if __name__ == "__main__":
    main()
