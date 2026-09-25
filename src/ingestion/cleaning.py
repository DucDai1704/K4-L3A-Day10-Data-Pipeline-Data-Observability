from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    import re
    
    data = []
    for r in records:
        title = r.title.strip()
        summary = re.sub(r'<[^>]+>', '', r.summary).strip()
        
        authors_joined = ", ".join(r.authors) if r.authors else "Unknown"
        categories_joined = ", ".join(r.categories) if r.categories else "Uncategorized"
        
        # Parse published date
        try:
            pub_date = pd.to_datetime(r.published, utc=True)
            age_days = (run_date.replace(tzinfo=None) - pub_date.replace(tzinfo=None)).days
        except Exception:
            age_days = 0
            
        text_for_embedding = f"Title: {title}\nAuthors: {authors_joined}\nPublished: {r.published}\nCategories: {categories_joined}\nSummary: {summary}"
        
        data.append({
            "paper_id": r.paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "age_days": age_days,
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment
        })
        
    df = pd.DataFrame(data)
    
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first")
        df = df[df["summary_chars"] > 10].copy()
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
        
    return df
