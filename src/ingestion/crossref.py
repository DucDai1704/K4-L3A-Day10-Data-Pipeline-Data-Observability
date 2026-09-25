from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


import json
import logging

logger = logging.getLogger(__name__)

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        try:
            doi = item.get("DOI", "")
            if not doi:
                continue
                
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Unknown Title"
            
            abstract = item.get("abstract", "")
            
            authors = []
            for a in item.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors.append(name)
                    
            categories = item.get("subject", [])
            primary_category = categories[0] if categories else "Uncategorized"
            
            published_parts = item.get("published", {}).get("date-parts", [[1970, 1, 1]])[0]
            published = f"{published_parts[0]:04d}-{published_parts[1]:02d}-{published_parts[2]:02d}"
            
            updated = item.get("created", {}).get("date-time", "")
            
            url = item.get("URL", "")
            
            records.append(PaperRecord(
                paper_id=doi,
                title=title,
                summary=abstract,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url="",
                comment=""
            ))
        except Exception as e:
            logger.warning(f"Error parsing item {item.get('DOI')}: {e}")
            
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records."""
    # We are using offline snapshot directly for this lab to avoid Crossref rate limits
    logger.info("Using offline snapshot mode for stability...")
    return load_raw_records(settings.paths.raw_api_response)


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        
    records = parse_crossref_payload(payload)
    logger.info(f"Loaded {len(records)} records from {path}")
    return records
