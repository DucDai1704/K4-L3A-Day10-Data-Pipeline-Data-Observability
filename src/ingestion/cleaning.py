from __future__ import annotations

from datetime import UTC, datetime, timezone
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed và đánh giá.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tính age_days = (run_date - published).days.
    4. Tạo cột helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates và filter row xấu.
    6. Sort dataframe và return.
    """
    if not records:
        return pd.DataFrame()

    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)

    rows: list[dict] = []
    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        title = normalize_whitespace(r.title)
        summary = normalize_whitespace(r.summary)
        authors = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        primary_category = normalize_whitespace(r.primary_category) or (categories[0] if categories else "General")
        published = normalize_whitespace(r.published)
        updated = normalize_whitespace(r.updated) or published

        if not paper_id or not title:
            continue

        # Parse published date for age_days
        try:
            pub_date = datetime.fromisoformat(published)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=UTC)
            age_days = max(0, (run_date - pub_date).days)
        except Exception:
            age_days = 0

        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        ).strip()

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
