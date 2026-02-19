# Patent Ingestion Pipeline (Google Patents)

A minimal pipeline for converting patent webpages into structured data for AI and analysis workflows.

This repository demonstrates a lightweight approach for retrieving and
structuring patent data from Google Patents webpages for downstream analysis
or AI processing.

The goal is to illustrate an **“acquire once, analyze many”** workflow where
patent content is downloaded, normalized, and stored locally so that
experiments can be repeated without repeated network requests.

This project is intended primarily for **educational and prototyping purposes**
to explore how modern data ingestion pipelines can be built using Python.

---

## Overview

The script performs the following steps:

1. Downloads a Google Patents webpage using an HTTP request.
2. Parses the HTML into a structured document using BeautifulSoup.
3. Extracts key patent fields:
   - Publication number
   - Title
   - Abstract
   - Claims
4. Normalizes text and removes common formatting artifacts.
5. Parses and deduplicates claims by claim number.
6. Saves structured output as JSON for reuse in analysis workflows.

The resulting JSON format is suitable for:

- AI analysis pipelines
- Patent comparison tools
- Research experiments
- Legal tech prototyping
- Educational demonstrations of web parsing and data normalization

---

## Example Output Structure

```json
{
  "publication_number": "US6285999B1",
  "title": "Method for node ranking in a linked database",
  "abstract": "...",
  "claims": [
    {
      "claim_number": 1,
      "text": "A computer implemented method..."
    }
  ]
}
```

---

## Requirements

Install dependencies:

```bash
pip install requests beautifulsoup4 lxml
```

Python 3.9+ recommended.

---

## Usage

Run the script:

```bash
python Scraping_Google_Patents_1.4.py
```

Enter a Google Patents URL when prompted.

Output files are saved to a folder named patent_dump in the project directory:

```
./patent_dump/<publication_number>.json
```

An example patent_dump folder is included in this repository containing output
generated from Google’s PageRank patent:
https://patents.google.com/patent/US6285999B1/en?oq=6285999

---

## Design Philosophy

The project separates core pipeline stages:

```
Acquisition → Normalization → Storage → Analysis
```

This separation improves:

- Reproducibility
- Debugging transparency
- Iteration speed
- Cost control (for AI workflows)
- Architectural clarity

The script focuses on the **acquisition and normalization layer**, which can
serve as the foundation for more advanced analysis systems.

---

## Educational Purpose

This repository is not intended as a production-scale scraper.
Instead, it demonstrates:

- HTML parsing with BeautifulSoup
- Structured data extraction
- Text normalization techniques
- Pipeline architecture concepts
- Preparing technical documents for AI processing

The code is intentionally written to be readable and inspectable so users can
understand how each step works.

---

## Notes

- Google Patents page structure may change over time.
- For large-scale systems, official bulk data sources should be considered.
- This project is intended for experimentation and learning purposes.
