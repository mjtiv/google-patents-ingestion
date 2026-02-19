
"""
Google Patents Scraper — Single Patent Acquisition Utility
---------------------------------------------------------

This script retrieves structured patent information from a Google Patents
webpage and converts it into a normalized JSON representation suitable for
downstream analysis, storage, or AI processing pipelines.

The primary goal is to provide a lightweight “acquire once, analyze many”
workflow. Patent content is pulled a single time from the web, cleaned and
structured locally, and then reused for repeated analysis without requiring
additional network requests.

Currently extracted fields include:

    • Publication number
    • Title
    • Abstract (normalized and label-cleaned)
    • Claims (parsed, deduplicated, and stored with claim numbers)
    • Source metadata

Claims are post-processed to remove duplicate DOM artifacts commonly present
in Google Patents pages. Each claim is stored as a structured object:

    {
        "claim_number": <int>,
        "text": <str>
    }

This structured format enables easier comparison across patent families,
dependency analysis, and efficient AI model ingestion.

Architecture Philosophy
-----------------------

The script is intentionally separated into two conceptual stages:

    1. Acquisition Layer
       Web retrieval and normalization of patent content.

    2. Analysis Layer (external to this script)
       AI processing, comparison, or legal analysis performed on saved files.

By separating acquisition from analysis, experiments can be repeated without
re-scraping data, improving reliability, reproducibility, and cost control.

Usage
-----

Run the script and provide a Google Patents URL when prompted:

    python scrape_google_patents.py

Output files are saved to:

    ./patent_dump/<publication_number>.json

Dependencies
------------

    pip install requests beautifulsoup4 lxml

Notes
-----

• Google Patents page structure may change over time.
• This script is intended for research, experimentation, and prototyping.
• For large-scale or production systems, consider official bulk data sources.

"""



import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def clean_text(s: str) -> str:
    """
    Normalize whitespace in extracted text.

    This helper is used to clean text pulled from HTML nodes where spacing,
    line breaks, and tabs are often inconsistent due to DOM formatting.

    Behavior:
        • Converts multiple whitespace characters (spaces, tabs, newlines)
          into a single space.
        • Safely handles None or empty input by treating it as an empty string.
        • Removes leading and trailing whitespace.

    Example:
        "  A   method \n for   scoring\tlinks  "
        → "A method for scoring links"

    Parameters
    ----------
    s : str
        Raw text string extracted from HTML or metadata.

    Returns
    -------
    str
        Cleaned, normalized string suitable for storage or downstream parsing.
    """
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def normalize_abstract(text: str) -> str:
    """
    Takes the abstract section of a patent and removes the
    leading "Abstract" label. Google Patents often embeds the
    word "Abstract" before the actual abstract content, which
    needs to be stripped for clean downstream processing.

    The function also normalizes whitespace to ensure
    consistent formatting.

    Parameters
    ----------
    text : str
        Raw abstract text extracted from the webpage.

    Returns
    -------
    str
        Cleaned abstract text without the leading label.
    """

    if not text:
        return ""

    # Normalize whitespace and remove extra spacing characters
    text = clean_text(text)

    # Remove leading "Abstract" label (case-insensitive)
    text = re.sub(r"^\s*Abstract[:\s-]*", "", text, flags=re.IGNORECASE)

    return text


def scrape_google_patents(url: str) -> dict:

    """
    Retrieve and parse patent data from a Google Patents webpage.

    High-Level Workflow
    -------------------
    1. Download the webpage HTML using an HTTP request.
    2. Parse the HTML into a structured document object using BeautifulSoup.
       This converts raw page text into searchable elements (tags, attributes,
       metadata, etc.).
    3. Locate specific patent fields (title, publication number, abstract,
       claims) by targeting known HTML metadata tags and CSS selectors.
    4. Clean and normalize extracted text using helper functions.
    5. Parse and deduplicate claims by claim number to remove duplicate DOM
       artifacts commonly present on Google Patents pages.
    6. Package the extracted data into a structured dictionary for downstream
       storage or analysis.

    Notes
    -----
    • BeautifulSoup is an HTML parser, not a downloader. The page is first
      retrieved using the `requests` library, then parsed into a searchable
      structure.
    • Selectors such as meta tags, itemprop attributes, and CSS classes are
      identified by inspecting the webpage structure using browser developer
      tools.
    • The function is designed for single-patent acquisition to support an
      “acquire once, analyze many” workflow.

    Parameters
    ----------
    url : str
        Google Patents URL for the patent to retrieve.

    Returns
    -------
    dict
        Structured patent data including title, publication number, abstract,
        claims, and source metadata.
    """

    headers = {
        # Mimic a normal browser a bit (helps reduce trivial blocks)
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Title (usually solid)
    title = ""
    t = soup.find("meta", attrs={"name": "DC.title"})
    if t and t.get("content"):
        title = clean_text(t["content"])
    elif soup.title:
        title = clean_text(soup.title.get_text())

    # Publication number (best-effort)
    pub_num = ""
    pub = soup.find("meta", attrs={"scheme": "citation_patent_number"})
    if pub and pub.get("content"):
        pub_num = clean_text(pub["content"])

    # Abstract (often in itemprop="abstract" or a section)
    abstract = ""
    abs_node = soup.find(attrs={"itemprop": "abstract"})
    if abs_node:
        abstract = normalize_abstract(abs_node.get_text(" ", strip=True))
    else:
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            abstract = normalize_abstract(md["content"])

    # Claims (Google Patents often uses "claim" classes / itemprop, but it varies)
    claims = []
    claim_nodes = soup.select("[itemprop='claims'] .claim") or soup.select(".claims .claim") or soup.select(".claim")
    # Keep it conservative: only grab text that looks like a claim (starts with a number)
    for node in claim_nodes:
        txt = clean_text(node.get_text(" ", strip=True))
        if re.match(r"^\d+\.\s", txt) or re.match(r"^\d+\s", txt):
            claims.append(txt)

    # If that didn’t work, try grabbing claim text blocks
    if not claims:
        alt = soup.select("[itemprop='claims']") or soup.select("section#claims") or []
        for node in alt:
            txt = clean_text(node.get_text(" ", strip=True))
            # crude split heuristic (works sometimes)
            parts = re.split(r"(?=(?:\s|^)\d+\.\s)", " " + txt)
            parts = [clean_text(p) for p in parts if re.match(r"^\d+\.\s", clean_text(p))]
            if parts:
                claims = parts
                break

    # ---- Parse and deduplicate claims by claim number ----
    parsed_claims = []
    seen_nums = set()

    for c in claims:
        m = re.match(r"^(\d+)\.\s*(.*)", c)
        if not m:
            continue

        num = int(m.group(1))
        text = m.group(2).strip()

        if num not in seen_nums:
            parsed_claims.append({
                "claim_number": num,
                "text": text
            })
            seen_nums.add(num)

    claims = parsed_claims


    data = {
        "source": "google_patents",
        "source_url": url,
        "publication_number": pub_num,
        "title": title,
        "abstract": abstract,
        "claims": claims,
        "raw_html_bytes": len(r.content),
    }
    return data


if __name__ == "__main__":
    # Example: "https://patents.google.com/patent/US1234567A/en"
    url = input("Google Patents URL: ").strip()

    out_dir = Path("patent_dump")
    out_dir.mkdir(parents=True, exist_ok=True)

    data = scrape_google_patents(url)

    # Choose a filename
    slug = data["publication_number"] or "patent"
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", slug)
    out_path = out_dir / f"{slug}.json"

    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")
    print(f"Title: {data['title']}")
    print(f"Abstract chars: {len(data['abstract'])}")
    print(f"Claims extracted: {len(data['claims'])}")

