"""Research Paper Reading Helper.

A local Streamlit study tool for Year 1 Biomedical Science students.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from utils import (
    VOCABULARY_COLUMNS,
    clean_filename,
    delete_paper,
    ensure_storage_files,
    export_summary_csv,
    export_summary_docx,
    export_summary_json,
    export_summary_txt,
    generate_summary,
    load_saved_papers,
    load_vocabulary,
    make_paper_id,
    save_paper,
    save_vocabulary,
    serialise_value,
)


STUDY_TYPES = [
    "Human study",
    "Animal study",
    "Cell study",
    "Laboratory experiment",
    "Clinical trial",
    "Review article",
    "Systematic review",
    "Meta-analysis",
    "Case study",
    "Other",
]

TECHNIQUES = [
    "PCR",
    "qPCR",
    "ELISA",
    "Western blot",
    "Gel electrophoresis",
    "Microscopy",
    "Flow cytometry",
    "Cell culture",
    "Gram staining",
    "Blood test",
    "Histology",
    "Immunohistochemistry",
    "Questionnaire",
    "Statistical analysis",
    "Other",
]

LIMITATIONS = [
    "Small sample size",
    "Short study duration",
    "Cell model may not represent humans",
    "Animal model may not fully represent humans",
    "Possible bias",
    "No control group",
    "Limited data",
    "Confounding variables",
    "Single location or population",
    "Self-reported data",
    "Weak statistical analysis",
    "Missing information",
    "Other",
]

RESULT_DIRECTIONS = ["Increased", "Decreased", "No change", "Mixed result", "Not sure"]
SIGNIFICANCE_OPTIONS = ["Yes", "No", "Not mentioned", "Not sure"]
ETHICS_OPTIONS = ["Yes", "No", "Not sure"]


def default_paper() -> dict[str, Any]:
    """Return a blank paper review used when the app first opens."""
    return {
        "paper_id": "",
        "paper_title": "",
        "authors": "",
        "year": "",
        "journal_name": "",
        "doi_link": "",
        "course_module": "",
        "topic": "",
        "date_reviewed": date.today().isoformat(),
        "abstract_text": "",
        "one_sentence_summary": "",
        "background_information": "",
        "main_keywords": "",
        "problem_studied": "",
        "research_question": "",
        "study_aim": "",
        "hypothesis": "",
        "research_importance": "",
        "study_type": STUDY_TYPES[0],
        "sample_used": "",
        "sample_size": "",
        "variables_measured": "",
        "techniques_used": [],
        "controls_used": "",
        "equipment_used": "",
        "statistical_methods": "",
        "ethical_approval": "Not sure",
        "method_notes": "",
        "results": [
            {
                "description": "",
                "direction": "Not sure",
                "significance": "Not sure",
                "figure": "",
                "explanation": "",
            }
            for _ in range(5)
        ],
        "results_meaning": "",
        "answer_to_question": "",
        "main_conclusion": "",
        "comparison_previous_studies": "",
        "biomedical_importance": "",
        "real_life_use": "",
        "personal_understanding": "",
        "common_limitations": [],
        "author_limitations": "",
        "student_limitations": "",
        "questions_still_have": "",
        "future_improvements": "",
    }


def normalise_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """Merge saved paper data into the current app shape.

    This keeps older or partial saved reviews from breaking tabs that expect
    all fields to exist.
    """
    normalised = default_paper()
    normalised.update(paper)

    blank_results = default_paper()["results"]
    saved_results = normalised.get("results", [])
    if not isinstance(saved_results, list):
        saved_results = []

    fixed_results = []
    for index in range(5):
        result = blank_results[index].copy()
        if index < len(saved_results) and isinstance(saved_results[index], dict):
            result.update(saved_results[index])
        fixed_results.append(result)
    normalised["results"] = fixed_results

    if not isinstance(normalised.get("techniques_used"), list):
        normalised["techniques_used"] = []
    if not isinstance(normalised.get("common_limitations"), list):
        normalised["common_limitations"] = []

    return normalised


def initialise_session() -> None:
    """Set up files and Streamlit session values."""
    ensure_storage_files()
    if "paper" not in st.session_state:
        st.session_state.paper = default_paper()
    if "final_summary" not in st.session_state:
        st.session_state.final_summary = ""


def update_paper(field: str, value: Any) -> None:
    """Update one field in the current paper review."""
    st.session_state.paper[field] = serialise_value(value)


def update_result(index: int, field: str, value: Any) -> None:
    """Update one field for one key result."""
    st.session_state.paper["results"][index][field] = value


def save_current_paper(show_success: bool = True) -> bool:
    """Validate and save the current paper review."""
    paper = st.session_state.paper
    if not paper.get("paper_title", "").strip():
        st.warning("Please enter a paper title before saving.")
        return False

    if not paper.get("abstract_text", "").strip() and not paper.get(
        "one_sentence_summary", ""
    ).strip():
        st.warning("Add an abstract or at least one note before saving.")
        return False

    if not paper.get("paper_id"):
        paper["paper_id"] = make_paper_id(paper["paper_title"])

    save_paper(paper)
    if show_success:
        st.success("Paper review saved locally.")
    return True


def help_box(text: str) -> None:
    """Show a consistent beginner guidance expander."""
    with st.expander("Need help understanding this section?"):
        st.write(text)


def paper_information_tab() -> None:
    st.header("1. Paper Information")
    st.write("Start with the basic details so you can find this paper again later.")
    help_box("Use the information from the first page of the paper. If something is missing, leave it blank or write Not mentioned.")

    paper = st.session_state.paper
    update_paper("paper_title", st.text_input("Paper title", value=paper["paper_title"]))
    update_paper("authors", st.text_input("Authors", value=paper["authors"]))

    col1, col2 = st.columns(2)
    with col1:
        update_paper("year", st.text_input("Year", value=paper["year"]))
        update_paper("journal_name", st.text_input("Journal name", value=paper["journal_name"]))
        update_paper("course_module", st.text_input("Course/module", value=paper["course_module"]))
    with col2:
        update_paper("doi_link", st.text_input("DOI or link", value=paper["doi_link"]))
        update_paper("topic", st.text_input("Topic", value=paper["topic"]))
        reviewed = st.date_input(
            "Date reviewed",
            value=date.fromisoformat(paper["date_reviewed"])
            if paper["date_reviewed"] and len(paper["date_reviewed"]) == 10
            else date.today(),
        )
        update_paper("date_reviewed", reviewed)

    if st.button("Save paper information"):
        save_current_paper()


def abstract_notes_tab() -> None:
    st.header("2. Abstract Notes")
    st.write("Paste the abstract and write your first simple understanding of the paper.")
    help_box(
        "The abstract is a short summary of the whole paper. Do not try to understand every detail first. "
        "Try to identify the problem, method, result, and conclusion."
    )

    paper = st.session_state.paper
    update_paper("abstract_text", st.text_area("Paste the abstract", value=paper["abstract_text"], height=220))
    update_paper(
        "one_sentence_summary",
        st.text_area("My one-sentence summary", value=paper["one_sentence_summary"], height=100),
    )
    update_paper(
        "background_information",
        st.text_area("Important background information", value=paper["background_information"], height=120),
    )
    update_paper("main_keywords", st.text_area("Main keywords", value=paper["main_keywords"], height=90))

    if not paper["abstract_text"].strip() and not paper["one_sentence_summary"].strip():
        st.info("Tip: add either the abstract or your own first notes before saving.")


def research_question_tab() -> None:
    st.header("3. Research Question and Aim")
    st.write("Break the purpose of the study into smaller questions.")
    help_box(
        "The research question is what the researchers are trying to answer. "
        "The aim is what they plan to do. The hypothesis is what they expect to find."
    )

    paper = st.session_state.paper
    update_paper("problem_studied", st.text_area("What problem is being studied?", value=paper["problem_studied"]))
    update_paper("research_question", st.text_area("What is the main research question?", value=paper["research_question"]))
    update_paper("study_aim", st.text_area("What is the aim of the study?", value=paper["study_aim"]))
    update_paper("hypothesis", st.text_area("What is the hypothesis, if mentioned?", value=paper["hypothesis"]))
    update_paper("research_importance", st.text_area("Why is this research important?", value=paper["research_importance"]))


def methods_tab() -> None:
    st.header("4. Methods Breakdown")
    st.write("Focus on what the researchers used, measured, and compared.")
    help_box(
        "The methods section explains how the researchers performed the study. Focus on what sample they used, "
        "what they measured, and how they measured it."
    )

    paper = st.session_state.paper
    update_paper(
        "study_type",
        st.selectbox("Study type", STUDY_TYPES, index=STUDY_TYPES.index(paper["study_type"]) if paper["study_type"] in STUDY_TYPES else 0),
    )
    update_paper("sample_used", st.text_input("Sample used", value=paper["sample_used"]))
    update_paper("sample_size", st.text_input("Sample size", value=paper["sample_size"]))
    update_paper("variables_measured", st.text_area("Variables measured", value=paper["variables_measured"]))
    update_paper("techniques_used", st.multiselect("Techniques used", TECHNIQUES, default=paper["techniques_used"]))
    update_paper("controls_used", st.text_area("Controls used", value=paper["controls_used"]))
    update_paper("equipment_used", st.text_area("Equipment used", value=paper["equipment_used"]))
    update_paper("statistical_methods", st.text_area("Statistical methods mentioned", value=paper["statistical_methods"]))
    update_paper(
        "ethical_approval",
        st.radio(
            "Ethical approval mentioned?",
            ETHICS_OPTIONS,
            index=ETHICS_OPTIONS.index(paper["ethical_approval"]) if paper["ethical_approval"] in ETHICS_OPTIONS else 2,
            horizontal=True,
        ),
    )
    update_paper("method_notes", st.text_area("Method notes", value=paper["method_notes"], height=120))


def results_tab() -> None:
    st.header("5. Results Breakdown")
    st.write("Choose up to five important results and explain each one in simple words.")
    help_box(
        "Do not copy the whole results section. Pick the most important findings. Look for words such as increased, "
        "decreased, significant, no difference, associated with, or correlated with."
    )

    for index in range(5):
        result = st.session_state.paper["results"][index]
        with st.expander(f"Result {index + 1}", expanded=index == 0):
            update_result(index, "description", st.text_area("Description", value=result["description"], key=f"description_{index}"))
            col1, col2 = st.columns(2)
            with col1:
                update_result(
                    index,
                    "direction",
                    st.selectbox(
                        "Direction of change",
                        RESULT_DIRECTIONS,
                        index=RESULT_DIRECTIONS.index(result["direction"]) if result["direction"] in RESULT_DIRECTIONS else 4,
                        key=f"direction_{index}",
                    ),
                )
            with col2:
                update_result(
                    index,
                    "significance",
                    st.selectbox(
                        "Was it statistically significant?",
                        SIGNIFICANCE_OPTIONS,
                        index=SIGNIFICANCE_OPTIONS.index(result["significance"]) if result["significance"] in SIGNIFICANCE_OPTIONS else 3,
                        key=f"significance_{index}",
                    ),
                )
            update_result(index, "figure", st.text_input("Related figure/table number", value=result["figure"], key=f"figure_{index}"))
            update_result(
                index,
                "explanation",
                st.text_area("Student explanation in simple words", value=result["explanation"], key=f"explanation_{index}"),
            )


def discussion_tab() -> None:
    st.header("6. Discussion and Conclusion")
    st.write("Explain what the results mean and what message the authors want the reader to take away.")
    help_box("The discussion section explains the meaning of the results. The conclusion gives the main message of the paper.")

    paper = st.session_state.paper
    update_paper("results_meaning", st.text_area("What do the results mean?", value=paper["results_meaning"]))
    update_paper("answer_to_question", st.text_area("How do the results answer the research question?", value=paper["answer_to_question"]))
    update_paper("main_conclusion", st.text_area("What is the main conclusion?", value=paper["main_conclusion"]))
    update_paper(
        "comparison_previous_studies",
        st.text_area("Did the authors compare their findings with previous studies?", value=paper["comparison_previous_studies"]),
    )
    update_paper("biomedical_importance", st.text_area("Why is this important in biomedical science?", value=paper["biomedical_importance"]))
    update_paper("real_life_use", st.text_area("How could this research be useful in real life?", value=paper["real_life_use"]))
    update_paper("personal_understanding", st.text_area("What do I personally understand from this paper?", value=paper["personal_understanding"]))


def limitations_tab() -> None:
    st.header("7. Limitations and Critical Thinking")
    st.write("Think about what the study can show clearly and what it cannot prove yet.")
    help_box("Critical thinking does not mean attacking the paper. It means understanding what the study can and cannot prove.")

    paper = st.session_state.paper
    update_paper("common_limitations", st.multiselect("Common limitations checklist", LIMITATIONS, default=paper["common_limitations"]))
    update_paper("author_limitations", st.text_area("Limitations mentioned by the authors", value=paper["author_limitations"]))
    update_paper("student_limitations", st.text_area("Limitations I noticed", value=paper["student_limitations"]))
    update_paper("questions_still_have", st.text_area("Questions I still have", value=paper["questions_still_have"]))
    update_paper("future_improvements", st.text_area("What could be improved in future research?", value=paper["future_improvements"]))


def vocabulary_tab() -> None:
    st.header("8. Vocabulary Builder")
    st.write("Save difficult biomedical words in your own simple language.")
    help_box("A good vocabulary note is short and understandable. Try writing the explanation as if you were teaching a classmate.")

    vocabulary = load_vocabulary()

    with st.form("add_vocabulary_form", clear_on_submit=True):
        st.subheader("Add a new term")
        term = st.text_input("Term")
        explanation = st.text_area("Simple explanation")
        topic = st.text_input("Related topic")
        example = st.text_area("Example sentence")
        source_title = st.text_input(
            "Source paper title",
            value=st.session_state.paper.get("paper_title", ""),
        )
        submitted = st.form_submit_button("Add term")

    if submitted:
        if not term.strip():
            st.warning("Please enter a term before adding it.")
        else:
            new_row = pd.DataFrame(
                [
                    {
                        "Term": term.strip(),
                        "Simple explanation": explanation.strip(),
                        "Related topic": topic.strip(),
                        "Example sentence": example.strip(),
                        "Source paper title": source_title.strip(),
                    }
                ],
                columns=VOCABULARY_COLUMNS,
            )
            vocabulary = pd.concat([vocabulary, new_row], ignore_index=True)
            save_vocabulary(vocabulary)
            st.success("Vocabulary term saved.")

    vocabulary = load_vocabulary()
    search = st.text_input("Search saved terms")
    filtered = vocabulary
    if search.strip():
        search_text = search.lower()
        filtered = vocabulary[
            vocabulary.apply(
                lambda row: search_text in " ".join(row.astype(str)).lower(),
                axis=1,
            )
        ]

    st.subheader("Saved vocabulary")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if not vocabulary.empty:
        terms = [f"{row['Term']} - {row['Simple explanation']}" for _, row in vocabulary.iterrows()]
        selected = st.selectbox("Delete a term", terms)
        if st.button("Delete selected vocabulary term"):
            selected_index = terms.index(selected)
            vocabulary = vocabulary.drop(vocabulary.index[selected_index]).reset_index(drop=True)
            save_vocabulary(vocabulary)
            st.success("Vocabulary term deleted.")
            st.rerun()

    csv_bytes = vocabulary.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Export vocabulary as CSV",
        data=csv_bytes,
        file_name="vocabulary.csv",
        mime="text/csv",
    )


def final_summary_tab() -> None:
    st.header("9. Final Summary and Export")
    st.write("Generate a structured revision summary from all sections.")

    if st.button("Generate Final Summary"):
        vocabulary = load_vocabulary()
        st.session_state.final_summary = generate_summary(st.session_state.paper, vocabulary)
        st.success("Final summary generated.")

    if st.session_state.final_summary:
        st.text_area("Generated final summary", value=st.session_state.final_summary, height=520)
    else:
        st.info("Click Generate Final Summary when you are ready.")

    st.subheader("Export options")
    if not st.session_state.paper.get("paper_title", "").strip():
        st.warning("Enter a paper title before exporting.")
        return

    if not st.session_state.final_summary:
        st.caption("Generate the summary first to enable export.")
        return

    col1, col2, col3, col4 = st.columns(4)
    export_actions = [
        ("TXT", export_summary_txt, col1),
        ("CSV", export_summary_csv, col2),
        ("JSON", export_summary_json, col3),
        ("DOCX", export_summary_docx, col4),
    ]

    for label, export_function, column in export_actions:
        with column:
            if st.button(f"Export as .{label.lower()}"):
                try:
                    if label == "CSV":
                        path = export_function(st.session_state.paper, st.session_state.final_summary)
                    elif label == "JSON":
                        path = export_function(st.session_state.paper, st.session_state.final_summary)
                    else:
                        path = export_function(st.session_state.final_summary, st.session_state.paper)
                    st.success(f"Exported to {path}")
                except Exception as error:
                    st.error(f"Export failed: {error}")

    safe_name = clean_filename(st.session_state.paper.get("paper_title", "summary"))
    st.download_button(
        "Download summary text from browser",
        data=st.session_state.final_summary.encode("utf-8"),
        file_name=f"research_summary_{safe_name}_{st.session_state.paper.get('date_reviewed', date.today().isoformat())}.txt",
        mime="text/plain",
    )


def saved_papers_tab() -> None:
    st.header("10. Saved Papers")
    st.write("Load, review, or delete paper notes saved on this computer.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save current paper review"):
            save_current_paper()
    with col2:
        if st.button("Start a new blank paper"):
            st.session_state.paper = default_paper()
            st.session_state.final_summary = ""
            st.success("Started a new blank paper review.")
            st.rerun()

    papers = load_saved_papers()
    if not papers:
        st.info("No saved papers yet.")
        return

    table_rows = [
        {
            "Paper ID": paper.get("paper_id", ""),
            "Title": paper.get("paper_title", ""),
            "Authors": paper.get("authors", ""),
            "Year": paper.get("year", ""),
            "Topic": paper.get("topic", ""),
            "Date reviewed": paper.get("date_reviewed", ""),
        }
        for paper in papers
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    labels = [
        f"{paper.get('paper_title', 'Untitled paper')} ({paper.get('date_reviewed', 'No date')})"
        for paper in papers
    ]
    selected_label = st.selectbox("Select a saved paper", labels)
    selected_paper = papers[labels.index(selected_label)]

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Load selected paper"):
            fresh = normalise_paper(selected_paper)
            st.session_state.paper = fresh
            st.session_state.final_summary = generate_summary(fresh, load_vocabulary())
            st.success("Selected paper loaded.")
            st.rerun()
    with col2:
        if st.button("View selected summary"):
            st.session_state.final_summary = generate_summary(selected_paper, load_vocabulary())
    with col3:
        if st.button("Delete selected paper"):
            delete_paper(selected_paper.get("paper_id", ""))
            st.success("Selected paper deleted.")
            st.rerun()

    if st.session_state.final_summary:
        st.text_area("Selected paper summary", value=st.session_state.final_summary, height=420)


def main() -> None:
    st.set_page_config(page_title="Research Paper Reading Helper", layout="wide")
    initialise_session()

    st.title("Research Paper Reading Helper")
    st.write(
        "A local study tool for Year 1 Biomedical Science students to break research papers into clear, manageable sections."
    )

    tabs = st.tabs(
        [
            "Paper Information",
            "Abstract Notes",
            "Research Question and Aim",
            "Methods Breakdown",
            "Results Breakdown",
            "Discussion and Conclusion",
            "Limitations and Critical Thinking",
            "Vocabulary Builder",
            "Final Summary and Export",
            "Saved Papers",
        ]
    )

    with tabs[0]:
        paper_information_tab()
    with tabs[1]:
        abstract_notes_tab()
    with tabs[2]:
        research_question_tab()
    with tabs[3]:
        methods_tab()
    with tabs[4]:
        results_tab()
    with tabs[5]:
        discussion_tab()
    with tabs[6]:
        limitations_tab()
    with tabs[7]:
        vocabulary_tab()
    with tabs[8]:
        final_summary_tab()
    with tabs[9]:
        saved_papers_tab()

    st.sidebar.title("Local files")
    st.sidebar.write("Saved reviews: `saved_papers.json`")
    st.sidebar.write("Vocabulary: `vocabulary.csv`")
    st.sidebar.write("Exports folder: `exports/`")
    st.sidebar.caption("No login, database, cloud service, or AI API is used.")


if __name__ == "__main__":
    main()
