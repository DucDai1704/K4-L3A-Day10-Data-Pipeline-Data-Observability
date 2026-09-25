from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a DataFrame ready for embedding.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Compute age_days.
    4. Create helper columns:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates and filter bad rows.
    6. Sort dataframe and return.
    """
    if not records:
        return pd.DataFrame()

    rows = []
    for rec in records:
        title = normalize_whitespace(rec.title)
        summary = normalize_whitespace(rec.summary)
        authors = [normalize_whitespace(a) for a in rec.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in rec.categories if normalize_whitespace(c)]

        # Parse published date
        try:
            published_dt = datetime.strptime(rec.published, "%Y-%m-%d")
        except (ValueError, TypeError):
            published_dt = run_date

        # Compute age_days
        run_date_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
        age_days = (run_date_naive - published_dt).days

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        # Build text_for_embedding
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {rec.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": rec.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(rec.primary_category),
                "published": rec.published,
                "updated": rec.updated,
                "abs_url": rec.abs_url,
                "pdf_url": rec.pdf_url,
                "comment": rec.comment,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Filter out rows with empty title or summary
    df = df[df["title"].str.len() > 0]
    df = df[df["summary"].str.len() > 0]

    # Sort by published date descending
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    return df
