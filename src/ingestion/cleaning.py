from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    for record in records:
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        if pd.isna(published):
            continue
        authors = [clean_text(a) for a in record.authors if clean_text(a)]
        categories = [clean_text(c) for c in record.categories if clean_text(c)]
        row = {
            "paper_id": clean_text(record.paper_id), "title": clean_text(record.title),
            "summary": clean_text(record.summary), "authors_joined": ", ".join(authors),
            "categories_joined": ", ".join(categories), "published": published.date().isoformat(),
            "updated": str(record.updated)[:10], "abs_url": record.abs_url or "",
            "pdf_url": record.pdf_url or "", "primary_category": clean_text(record.primary_category),
        }
        if not row["paper_id"] or not row["title"]:
            continue
        row["age_days"] = max(0, (run_date.date() - published.date()).days)
        row["summary_chars"] = len(row["summary"])
        row["text_for_embedding"] = embedding_text(row)
        rows.append(row)
    if not rows:
        raise ValueError("No usable paper records")
    return (pd.DataFrame(rows).drop_duplicates(subset="paper_id", keep="first")
            .sort_values("paper_id").reset_index(drop=True))


def clean_text(value: str) -> str:
    return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", value or "")))


def embedding_text(row: dict) -> str:
    return (f"Title: {row['title']}\nAuthors: {row['authors_joined']}\n"
            f"Published: {row['published']}\nCategories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}")
