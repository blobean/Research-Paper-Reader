# Research Paper Reading Helper

Research Paper Reading Helper is a local Streamlit app for a Year 1 Biomedical Science student. It helps you upload or paste one or more research papers, extract beginner-friendly summary points, list sources, ask recall questions, and compare papers.

The app does not use a database, login, cloud deployment, or patient data. It can optionally use the DeepSeek API for faster, higher-quality summaries; if no DeepSeek key is configured, summarisation falls back to the local extractor.

## Summary Features

- Record paper information such as title, authors, journal, DOI, topic, and review date.
- Paste paper text or upload multiple TXT/PDF files.
- Uploaded paper text is stored locally but hidden from the Paper Input view after upload.
- Generate a shorter reworded summary, highlighted key points, and keywords from the paper text.
- Use DeepSeek for summary extraction and paper comparison when `DEEPSEEK_API_KEY` is set, with local extraction as a fallback.
- View summaries in a separate Summary tab, with subtabs for each uploaded paper.
- Delete uploaded paper tabs from the current workspace.
- Save each uploaded paper from its own Paper Input subtab.
- Automatically reopen saved paper reviews when the app starts again after a reboot.
- Pull out clues for methods, results, and limitations to help guide reading.
- Extract sources from the References or Bibliography section when present.
- Edit and download the extracted sources list.
- Ask questions about the paper in the Recall tab and receive local answers with supporting snippets.
- Compare multiple uploaded papers side by side, including DeepSeek-assisted shared themes, differences, takeaways, cautions, unique themes, and possible opposing findings.
- Save, load, view, and delete previous paper summaries.

## Installation

Open a terminal in this folder and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the App

After installing the requirements, run:

```bash
source .venv/bin/activate
streamlit run app.py
```

Streamlit will show a local browser link, usually:

```text
http://localhost:8501
```

## Optional DeepSeek Setup

To use DeepSeek, set your API key before starting Streamlit:

```bash
export DEEPSEEK_API_KEY="your-api-key"
streamlit run app.py
```

You can also add the key to Streamlit secrets at `.streamlit/secrets.toml`:

```toml
DEEPSEEK_API_KEY = "your-api-key"
```

The app calls DeepSeek's OpenAI-compatible API at `https://api.deepseek.com` and defaults to the `deepseek-chat` model. You can override these defaults with:

```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_MAX_CHARS="60000"
```

## Where Data Is Saved

The app creates these local files automatically in this project folder:

- `saved_papers.json` stores saved paper reviews and is loaded again when the app restarts.
- `exports/` stores exported summary files.

Uploaded files are read locally in the app. If `DEEPSEEK_API_KEY` is set, the app sends the paper text excerpt to DeepSeek to generate summary fields. If no key is set or the API call fails, the app uses local summarisation only.

## Sources

The **Sources** tab lists references extracted from the uploaded or pasted paper. If the app cannot find a References or Bibliography section, you can still paste or edit the sources manually. The source list can be downloaded as a CSV file.

## Recall

The **Recall** tab lets you ask natural-language questions about the paper. It checks the paper text, summary points, methods points, results points, limitations points, and sources, then returns a short answer, detailed bullet points, and expandable supporting evidence. Recall also uses simple synonym matching, so terms such as "sample", "participants", "cells", and "cohort" can support the same search. It does not use an AI API.

## Comparison

The **Comparison** tab works after at least two papers have been uploaded. When `DEEPSEEK_API_KEY` is configured, it asks DeepSeek to generate a plain-language comparison overview, shared content points, key differences, takeaways by paper, possible opposing findings, and cautions for fair comparison. If DeepSeek is not configured or the API call fails, it falls back to local side-by-side summaries, common themes, common ideas with evidence from both papers, unique themes for each paper, possible opposing increase/decrease findings, and extracted methods/results/limitations points for each selected paper.

## Notes

This app is designed as a study helper. Do not enter real patient data. For best results, write notes in your own words instead of copying full sections of a paper.
