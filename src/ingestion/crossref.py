from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, write_json


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


def _strip_html(text: str) -> str:
    """Remove HTML/XML tags like <jats:p> from text."""
    return re.sub(r"<[^>]+>", "", text)


def _parse_date_parts(date_obj: dict | None) -> str:
    """Convert Crossref date-parts to ISO date string."""
    if not date_obj:
        return ""
    parts = date_obj.get("date-parts", [[]])[0]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into list of PaperRecord.

    1. Iterate payload["message"]["items"].
    2. Extract DOI, title, abstract, authors, subject, dates, URLs.
    3. Normalize text and skip invalid records.
    4. Return list of PaperRecord.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # Title
        title_list = item.get("title", [])
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not title:
            continue

        # Abstract / summary
        raw_abstract = item.get("abstract", "")
        summary = normalize_whitespace(_strip_html(raw_abstract))
        if not summary:
            continue

        # Authors
        author_list = item.get("author", [])
        authors = []
        for author in author_list:
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)

        # Categories / subjects
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        # Dates
        published = _parse_date_parts(item.get("published"))
        created = item.get("created", {})
        updated = created.get("date-time", published)
        if "T" in updated:
            updated = updated[:10]

        # URLs
        url = item.get("URL", f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {doi}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API with offline fallback.

    1. Build query params from settings.
    2. Call API with retry for 429/503.
    3. Save raw response to settings.paths.raw_api_response.
    4. Parse payload with parse_crossref_payload.
    5. Save records to settings.paths.raw_records_json.
    """
    payload = None

    if settings.refresh_source:
        url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        for attempt in range(3):
            try:
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code in (429, 503):
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                break
            except Exception:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

    # Fallback to offline snapshot
    if payload is None:
        snapshot_path = settings.paths.raw_api_response
        if snapshot_path.exists():
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(
                f"No API response and no offline snapshot at {snapshot_path}"
            )
    else:
        write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)

    # Save records as JSON
    write_json(
        settings.paths.raw_records_json,
        [asdict(r) for r in records],
    )

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map to PaperRecord."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**record) for record in raw]
