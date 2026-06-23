"""Utility functions for the Research Paper Reading Helper app.

The app stores everything in local files so it keeps working without a
database, login, cloud service, or AI API.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from docx import Document


DATA_DIR = Path(".")
SAVED_PAPERS_FILE = DATA_DIR / "saved_papers.json"
VOCABULARY_FILE = DATA_DIR / "vocabulary.csv"
EXPORTS_DIR = DATA_DIR / "exports"

VOCABULARY_COLUMNS = [
    "Term",
    "Simple explanation",
    "Related topic",
    "Example sentence",
    "Source paper title",
]

STARTER_TERMS = [
    {
        "Term": "Apoptosis",
        "Simple explanation": "programmed cell death",
        "Related topic": "Cell biology",
        "Example sentence": "Apoptosis removes damaged cells from the body.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Homeostasis",
        "Simple explanation": "maintenance of a stable internal environment",
        "Related topic": "Physiology",
        "Example sentence": "The body uses homeostasis to keep blood glucose stable.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Osmosis",
        "Simple explanation": "movement of water across a partially permeable membrane",
        "Related topic": "Cell transport",
        "Example sentence": "Water enters cells by osmosis.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Diffusion",
        "Simple explanation": "movement of particles from high concentration to low concentration",
        "Related topic": "Cell transport",
        "Example sentence": "Oxygen moves into cells by diffusion.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Enzyme",
        "Simple explanation": "protein that speeds up a chemical reaction",
        "Related topic": "Biochemistry",
        "Example sentence": "An enzyme helps break down the substrate faster.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "ATP",
        "Simple explanation": "main energy molecule used by cells",
        "Related topic": "Cell metabolism",
        "Example sentence": "Muscle cells use ATP during contraction.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Mitosis",
        "Simple explanation": "cell division that produces two identical daughter cells",
        "Related topic": "Cell biology",
        "Example sentence": "Mitosis is important for growth and tissue repair.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Biomarker",
        "Simple explanation": "measurable sign of a biological condition",
        "Related topic": "Disease testing",
        "Example sentence": "Blood glucose can be used as a biomarker for diabetes.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Inflammation",
        "Simple explanation": "immune response to injury or infection",
        "Related topic": "Immunology",
        "Example sentence": "Inflammation can cause redness, heat, swelling, and pain.",
        "Source paper title": "Starter vocabulary",
    },
    {
        "Term": "Pathogen",
        "Simple explanation": "microorganism that can cause disease",
        "Related topic": "Microbiology",
        "Example sentence": "Some bacteria are pathogens that can infect humans.",
        "Source paper title": "Starter vocabulary",
    },
]


def ensure_storage_files() -> None:
    """Create the local storage files and export folder if they do not exist."""
    EXPORTS_DIR.mkdir(exist_ok=True)

    if not SAVED_PAPERS_FILE.exists():
        SAVED_PAPERS_FILE.write_text("[]", encoding="utf-8")

    if not VOCABULARY_FILE.exists():
        pd.DataFrame(STARTER_TERMS, columns=VOCABULARY_COLUMNS).to_csv(
            VOCABULARY_FILE, index=False
        )


def load_saved_papers() -> list[dict[str, Any]]:
    """Load saved paper reviews from JSON, returning an empty list on errors."""
    ensure_storage_files()
    try:
        data = json.loads(SAVED_PAPERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_paper(paper: dict[str, Any]) -> None:
    """Add or update one paper review in saved_papers.json."""
    ensure_storage_files()
    papers = load_saved_papers()
    existing_index = next(
        (index for index, item in enumerate(papers) if item.get("paper_id") == paper["paper_id"]),
        None,
    )

    if existing_index is None:
        papers.append(paper)
    else:
        papers[existing_index] = paper

    SAVED_PAPERS_FILE.write_text(
        json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_paper(paper_id: str) -> None:
    """Delete a saved paper review by its paper ID."""
    papers = [paper for paper in load_saved_papers() if paper.get("paper_id") != paper_id]
    SAVED_PAPERS_FILE.write_text(
        json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_vocabulary() -> pd.DataFrame:
    """Load the vocabulary CSV and repair missing columns if needed."""
    ensure_storage_files()
    try:
        vocabulary = pd.read_csv(VOCABULARY_FILE).fillna("")
    except (pd.errors.EmptyDataError, OSError):
        vocabulary = pd.DataFrame(columns=VOCABULARY_COLUMNS)

    for column in VOCABULARY_COLUMNS:
        if column not in vocabulary.columns:
            vocabulary[column] = ""
    return vocabulary[VOCABULARY_COLUMNS]


def save_vocabulary(vocabulary: pd.DataFrame) -> None:
    """Save vocabulary terms to vocabulary.csv."""
    ensure_storage_files()
    vocabulary[VOCABULARY_COLUMNS].to_csv(VOCABULARY_FILE, index=False)


def clean_filename(text: str) -> str:
    """Turn a paper title into a safe file-name section."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:80] or "untitled_paper"


def make_paper_id(title: str) -> str:
    """Create a readable unique paper ID using title plus the current time."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{clean_filename(title)}_{stamp}"


def serialise_value(value: Any) -> Any:
    """Convert dates and other non-JSON values into JSON-friendly values."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _line(label: str, value: Any) -> str:
    """Format one labeled summary line."""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if str(item).strip())
    return f"{label}: {value or 'Not entered'}"


def generate_summary(paper: dict[str, Any], vocabulary: Optional[pd.DataFrame] = None) -> str:
    """Build a plain-language structured summary from the current paper review."""
    results = paper.get("results", [])
    result_lines = []
    for index, result in enumerate(results, start=1):
        if not any(str(value).strip() for value in result.values()):
            continue
        result_lines.append(
            "\n".join(
                [
                    f"Result {index}",
                    _line("Description", result.get("description")),
                    _line("Direction", result.get("direction")),
                    _line("Statistical significance", result.get("significance")),
                    _line("Figure/Table", result.get("figure")),
                    _line("Simple explanation", result.get("explanation")),
                ]
            )
        )

    methods_summary = "\n".join(
        [
            _line("Study type", paper.get("study_type")),
            _line("Sample used", paper.get("sample_used")),
            _line("Sample size", paper.get("sample_size")),
            _line("Variables measured", paper.get("variables_measured")),
            _line("Techniques used", paper.get("techniques_used", [])),
            _line("Controls used", paper.get("controls_used")),
            _line("Equipment used", paper.get("equipment_used")),
            _line("Statistical methods", paper.get("statistical_methods")),
            _line("Ethical approval mentioned", paper.get("ethical_approval")),
            _line("Method notes", paper.get("method_notes")),
        ]
    )

    vocabulary_lines = ["Not entered"]
    if vocabulary is not None and not vocabulary.empty:
        title = paper.get("paper_title", "")
        related_vocab = vocabulary[
            vocabulary["Source paper title"].astype(str).str.lower() == title.lower()
        ]
        if related_vocab.empty:
            related_vocab = vocabulary.head(10)
        vocabulary_lines = [
            f"- {row['Term']}: {row['Simple explanation']}"
            for _, row in related_vocab.iterrows()
            if str(row["Term"]).strip()
        ] or ["Not entered"]

    citation = ", ".join(
        part
        for part in [
            paper.get("authors"),
            f"({paper.get('year')})" if paper.get("year") else "",
            paper.get("paper_title"),
            paper.get("journal_name"),
            paper.get("doi_link"),
        ]
        if part
    )

    sections = [
        ("Research Paper Reading Helper Summary", ""),
        ("Paper title", paper.get("paper_title", "Not entered")),
        ("Full citation-style information", citation or "Not entered"),
        ("One-sentence summary", paper.get("one_sentence_summary", "Not entered")),
        ("Background", paper.get("background_information", "Not entered")),
        ("Research question", paper.get("research_question", "Not entered")),
        ("Aim", paper.get("study_aim", "Not entered")),
        ("Hypothesis", paper.get("hypothesis", "Not entered")),
        ("Study type", paper.get("study_type", "Not entered")),
        ("Methods summary", methods_summary),
        ("Key results", "\n\n".join(result_lines) or "Not entered"),
        ("Discussion summary", paper.get("results_meaning", "Not entered")),
        ("Main conclusion", paper.get("main_conclusion", "Not entered")),
        (
            "Limitations",
            "\n".join(
                [
                    _line("Checklist", paper.get("common_limitations", [])),
                    _line("Authors mentioned", paper.get("author_limitations")),
                    _line("I noticed", paper.get("student_limitations")),
                ]
            ),
        ),
        ("Important vocabulary", "\n".join(vocabulary_lines)),
        ("Questions for revision", paper.get("questions_still_have", "Not entered")),
    ]

    return "\n\n".join(
        f"{heading}\n{'=' * len(heading)}\n{body}" if body else heading
        for heading, body in sections
    )


def _export_path(paper: dict[str, Any], extension: str) -> Path:
    """Create a standard export path for one paper and file extension."""
    ensure_storage_files()
    title = clean_filename(paper.get("paper_title", "untitled_paper"))
    reviewed = paper.get("date_reviewed") or date.today().isoformat()
    return EXPORTS_DIR / f"research_summary_{title}_{reviewed}.{extension}"


def export_summary_txt(summary: str, paper: dict[str, Any]) -> Path:
    """Export a summary as a text file."""
    path = _export_path(paper, "txt")
    path.write_text(summary, encoding="utf-8")
    return path


def export_summary_json(paper: dict[str, Any], summary: str) -> Path:
    """Export a paper review and its generated summary as JSON."""
    path = _export_path(paper, "json")
    payload = {"paper": paper, "summary": summary}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_summary_csv(paper: dict[str, Any], summary: str) -> Path:
    """Export a one-row CSV containing the paper title and generated summary."""
    path = _export_path(paper, "csv")
    row = {
        "paper_id": paper.get("paper_id", ""),
        "paper_title": paper.get("paper_title", ""),
        "date_reviewed": paper.get("date_reviewed", ""),
        "summary": summary,
    }
    pd.DataFrame([row]).to_csv(path, index=False)
    return path


def export_summary_docx(summary: str, paper: dict[str, Any]) -> Path:
    """Export a summary as a Word document."""
    path = _export_path(paper, "docx")
    document = Document()
    document.add_heading("Research Paper Reading Helper Summary", level=1)
    for block in summary.split("\n\n"):
        lines = block.splitlines()
        if len(lines) >= 2 and set(lines[1]) == {"="}:
            document.add_heading(lines[0], level=2)
            text = "\n".join(lines[2:]).strip()
            if text:
                document.add_paragraph(text)
        else:
            document.add_paragraph(block)
    document.save(path)
    return path
