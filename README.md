# Research Paper Reading Helper

Research Paper Reading Helper is a local Streamlit app for a Year 1 Biomedical Science student. It helps you input research paper text, extract useful content points, and turn the paper into beginner-friendly summaries covering the abstract, study purpose, methods, results, discussion, limitations, vocabulary, and final revision summary.

The app does not use a database, login, cloud deployment, patient data, or an AI API. Everything is saved on your own computer.

## Summary Features

- Record paper information such as title, authors, journal, DOI, topic, and review date.
- Paste paper text or upload a TXT/PDF file.
- Extract a short local summary, keywords, and reading points from the paper text.
- Pull out clues for methods, results, and limitations to help guide reading.
- Paste and summarise the abstract.
- Summarise the study purpose, aim, expected finding, and importance.
- Break down study methods, techniques, samples, controls, and ethics.
- Write up to five key results in simple words.
- Understand the discussion and conclusion.
- Summarise limitations and future research improvements.
- Build a local biomedical vocabulary list.
- Generate and export a structured final summary.
- Save, load, view, and delete previous paper reviews.

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
- `vocabulary.csv` stores vocabulary terms.
- `exports/` stores exported summaries.

Uploaded files are read locally in the app. The app does not send paper text to an AI API or cloud service.

If `vocabulary.csv` does not exist, the app starts it with beginner biomedical terms such as apoptosis, homeostasis, osmosis, diffusion, enzyme, ATP, mitosis, biomarker, inflammation, and pathogen.

## Exporting Summaries

Go to the **Final Summary and Export** tab, click **Generate Final Summary**, then choose an export option:

- `.txt`
- `.csv`
- `.json`
- `.docx`

Exported files are saved in the `exports/` folder. File names are cleaned so paper titles with spaces or special characters can still be used safely.

## Notes

This app is designed as a study helper. Do not enter real patient data. For best results, write notes in your own words instead of copying full sections of a paper.
