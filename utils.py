"""Utility functions for the Research Paper Reading Helper app.

The app stores everything in local files so it keeps working without a
database, login, cloud service, or AI API.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from docx import Document


DATA_DIR = Path(".")
SAVED_PAPERS_FILE = DATA_DIR / "saved_papers.json"
VOCABULARY_FILE = DATA_DIR / "vocabulary.csv"
EXPORTS_DIR = DATA_DIR / "exports"

STOPWORDS = {
    "about",
    "after",
    "also",
    "among",
    "and",
    "are",
    "because",
    "been",
    "between",
    "both",
    "but",
    "can",
    "could",
    "did",
    "does",
    "during",
    "each",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "however",
    "into",
    "may",
    "more",
    "most",
    "not",
    "our",
    "patients",
    "paper",
    "research",
    "result",
    "results",
    "show",
    "showed",
    "study",
    "such",
    "than",
    "that",
    "the",
    "their",
    "these",
    "this",
    "those",
    "through",
    "using",
    "was",
    "were",
    "which",
    "while",
    "with",
}

SECTION_ALIASES = {
    "abstract": ["abstract", "summary"],
    "introduction": ["introduction", "background"],
    "methods": ["methods", "materials and methods", "methodology", "experimental procedures"],
    "results": ["results", "findings"],
    "discussion": ["discussion"],
    "conclusion": ["conclusion", "conclusions"],
    "limitations": ["limitations", "strengths and limitations"],
}

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


def extract_text_from_upload(uploaded_file: Any) -> str:
    """Read text from an uploaded TXT or PDF file.

    PDF support uses pypdf. If pypdf is not installed, the app returns a clear
    message instead of crashing.
    """
    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()
    if file_name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if file_name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return "PDF reading requires pypdf. Install it with: pip install pypdf"

        try:
            import io

            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages).strip()
        except Exception as error:
            return f"Could not read this PDF: {error}"

    return data.decode("utf-8", errors="ignore")


def clean_paper_text(text: str) -> str:
    """Normalise whitespace from pasted or uploaded paper text."""
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Split paper text into readable sentence-like chunks."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 25]


def extract_sections(text: str) -> dict[str, str]:
    """Extract common paper sections using simple local heading detection."""
    cleaned = clean_paper_text(text)
    sections = {key: "" for key in SECTION_ALIASES}
    if not cleaned:
        return sections

    heading_pattern = re.compile(
        r"(?im)^\s*(abstract|summary|introduction|background|methods|materials and methods|"
        r"methodology|experimental procedures|results|findings|discussion|conclusion|"
        r"conclusions|limitations|strengths and limitations)\s*$"
    )
    matches = list(heading_pattern.finditer(cleaned))

    if not matches:
        sentences = split_sentences(cleaned)
        sections["abstract"] = " ".join(sentences[:8])
        return sections

    for index, match in enumerate(matches):
        raw_heading = match.group(1).lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        content = cleaned[start:end].strip()
        for section, aliases in SECTION_ALIASES.items():
            if raw_heading in aliases:
                sections[section] = content
                break
    return sections


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    """Find likely important biomedical keywords using local word frequency."""
    words = re.findall(r"\b[A-Za-z][A-Za-z-]{3,}\b", text.lower())
    filtered = [
        word.strip("-")
        for word in words
        if word not in STOPWORDS and not word.endswith("ing") and len(word) > 3
    ]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def summarise_text(text: str, sentence_count: int = 4) -> str:
    """Create a short extractive summary from the most informative sentences."""
    sentences = split_sentences(text)
    if not sentences:
        return ""

    keywords = set(extract_keywords(text, limit=20))
    scored = []
    for position, sentence in enumerate(sentences):
        words = re.findall(r"\b[A-Za-z][A-Za-z-]{3,}\b", sentence.lower())
        keyword_hits = sum(1 for word in words if word in keywords)
        result_hits = len(
            re.findall(
                r"\b(increased|decreased|significant|associated|correlated|reduced|higher|lower|improved)\b",
                sentence.lower(),
            )
        )
        score = keyword_hits + (2 * result_hits) - (position * 0.02)
        scored.append((score, position, sentence))

    best = sorted(scored, reverse=True)[:sentence_count]
    ordered = sorted(best, key=lambda item: item[1])
    return " ".join(sentence for _, _, sentence in ordered)


def extract_key_points(text: str, limit: int = 8) -> list[str]:
    """Return bullet-style reading points from the paper text."""
    summary = summarise_text(text, sentence_count=limit)
    return split_sentences(summary)[:limit]


def find_sentences_with_terms(text: str, terms: list[str], limit: int = 5) -> list[str]:
    """Find sentences that mention any of the provided terms."""
    sentences = split_sentences(text)
    found = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term.lower() in lowered for term in terms):
            found.append(sentence)
        if len(found) >= limit:
            break
    return found


def build_reading_assistant(paper_text: str) -> dict[str, Any]:
    """Create local reading support from a pasted or uploaded paper.

    This is intentionally simple and transparent. It extracts useful points; it
    does not claim to replace careful reading or expert judgement.
    """
    cleaned = clean_paper_text(paper_text)
    sections = extract_sections(cleaned)
    source_for_summary = sections.get("abstract") or cleaned

    method_terms = ["sample", "participants", "cells", "mice", "assay", "measured", "analysis"]
    result_terms = [
        "increased",
        "decreased",
        "significant",
        "associated",
        "correlated",
        "higher",
        "lower",
        "reduced",
        "improved",
    ]
    limitation_terms = ["limitation", "limited", "bias", "small sample", "future", "not assess"]

    return {
        "cleaned_text": cleaned,
        "word_count": len(re.findall(r"\b\w+\b", cleaned)),
        "sections": sections,
        "keywords": extract_keywords(cleaned),
        "short_summary": summarise_text(source_for_summary, sentence_count=3),
        "key_points": extract_key_points(cleaned, limit=8),
        "method_points": find_sentences_with_terms(sections.get("methods") or cleaned, method_terms, limit=5),
        "result_points": find_sentences_with_terms(sections.get("results") or cleaned, result_terms, limit=5),
        "limitation_points": find_sentences_with_terms(cleaned, limitation_terms, limit=5),
    }


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
        ("Extracted short summary", paper.get("auto_summary", "Not entered")),
        ("Extracted content points", "\n".join(f"- {point}" for point in paper.get("auto_key_points", [])) or "Not entered"),
        ("One-sentence summary", paper.get("one_sentence_summary", "Not entered")),
        ("Background", paper.get("background_information", "Not entered")),
        ("Central study focus", paper.get("research_question", "Not entered")),
        ("Aim", paper.get("study_aim", "Not entered")),
        ("Expected finding", paper.get("hypothesis", "Not entered")),
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
                    _line("Author-stated limitations", paper.get("author_limitations")),
                    _line("Additional limitations", paper.get("student_limitations")),
                ]
            ),
        ),
        ("Important vocabulary", "\n".join(vocabulary_lines)),
        ("Revision notes", paper.get("questions_still_have", "Not entered")),
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
