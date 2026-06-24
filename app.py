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
    delete_paper,
    ensure_storage_files,
    extract_text_from_upload,
    load_saved_papers,
    make_paper_id,
    recall_keyword_matches,
    save_paper,
    serialise_value,
)


def default_paper() -> dict[str, Any]:
    """Return a blank paper record for the summariser."""
    return {
        "paper_id": "",
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


def update_paper(field: str, value: Any) -> None:
    """Update one field in the current paper record."""
    st.session_state.paper[field] = serialise_value(value)


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

    paper = st.session_state.paper
    uploaded_file = st.file_uploader("Upload research paper file", type=["txt", "pdf"])
    if uploaded_file is not None:
        extracted_text = extract_text_from_upload(uploaded_file)
        if extracted_text.startswith("PDF reading requires") or extracted_text.startswith("Could not read"):
            st.warning(extracted_text)
        else:
            update_paper("paper_text", extracted_text)
            if not paper.get("paper_title"):
                update_paper("paper_title", uploaded_file.name.rsplit(".", 1)[0])
            st.success("Uploaded paper text added.")

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

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Summarise paper", type="primary"):
            run_extraction()
            st.rerun()
    with col2:
        if st.button("Save summary"):
            save_current_paper()
    with col3:
        if st.button("Start new paper"):
            st.session_state.paper = default_paper()
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
    st.write("Search the uploaded paper, extracted summary points, and sources using keywords.")

    paper = st.session_state.paper
    query = st.text_input(
        "Keyword search",
        placeholder="Example: apoptosis, ELISA, sample size, limitation",
    )

    if not paper.get("paper_text", "").strip() and not paper.get("auto_summary", "").strip():
        st.info("Upload or paste a paper in the Paper Input tab before using recall.")
        return

    if not query.strip():
        st.caption("Enter one or more keywords to find matching information.")
        return

    matches = recall_keyword_matches(paper, query)
    if not matches:
        st.warning("No matching information found for those keywords.")
        return

    st.success(f"Found {len(matches)} matching item{'s' if len(matches) != 1 else ''}.")
    st.dataframe(pd.DataFrame(matches), use_container_width=True, hide_index=True)

    st.subheader("Matched snippets")
    for index, match in enumerate(matches, start=1):
        with st.expander(f"{index}. {match['section']} - {match['matched_terms']}"):
            st.write(match["snippet"])


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
            st.session_state.paper = normalise_paper(selected_paper)
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

    tabs = st.tabs(["Paper Input", "Sources", "Recall", "Saved Papers"])
    with tabs[0]:
        paper_input_tab()
    with tabs[1]:
        sources_tab()
    with tabs[2]:
        recall_tab()
    with tabs[3]:
        saved_papers_tab()

    st.sidebar.title("Local files")
    st.sidebar.write("Saved summaries: `saved_papers.json`")
    st.sidebar.caption("No login, database, cloud service, or AI API is used.")


if __name__ == "__main__":
    main()
