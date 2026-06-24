# Research Paper Reading Helper

Research Paper Reading Helper is a local Streamlit app for a Year 1 Biomedical Science student. It helps you upload or paste research paper text, extract beginner-friendly summary points, and list the sources used in the paper.

The app does not use a database, login, cloud deployment, patient data, or an AI API. Everything is saved on your own computer.

## Summary Features

- Record paper information such as title, authors, journal, DOI, topic, and review date.
- Paste paper text or upload a TXT/PDF file.
- Extract a short local summary, keywords, and reading points from the paper text.
- Pull out clues for methods, results, and limitations to help guide reading.
- Extract sources from the References or Bibliography section when present.
- Edit and download the extracted sources list.
- Ask questions about the paper in the Recall tab and receive local answers with supporting snippets.
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

## Where Data Is Saved

The app creates these local files automatically:

- `saved_papers.json` stores saved paper reviews.

Uploaded files are read locally in the app. The app does not send paper text to an AI API or cloud service.

## Sources

The **Sources** tab lists references extracted from the uploaded or pasted paper. If the app cannot find a References or Bibliography section, you can still paste or edit the sources manually. The source list can be downloaded as a CSV file.

## Recall

The **Recall** tab lets you ask natural-language questions about the paper. It checks the paper text, summary points, methods points, results points, limitations points, and sources, then returns a local extractive answer with supporting snippets. It does not use an AI API.

## Notes

This app is designed as a study helper. Do not enter real patient data. For best results, write notes in your own words instead of copying full sections of a paper.
