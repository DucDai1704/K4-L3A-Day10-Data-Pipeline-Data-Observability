from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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


def _clean_abstract(raw_abstract: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", raw_abstract)
    return normalize_whitespace(cleaned)


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload thành list PaperRecord.

    1. Duyệt `payload["message"]["items"]`.
    2. Lấy DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuẩn hóa text và bỏ record không hợp lệ.
    4. Trả về list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            continue

        raw_title = item.get("title", "")
        if isinstance(raw_title, list):
            title = normalize_whitespace(raw_title[0]) if raw_title else ""
        else:
            title = normalize_whitespace(str(raw_title))
        if not title:
            continue

        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full = f"{given} {family}".strip()
            if full:
                authors.append(full)

        categories: list[str] = [normalize_whitespace(c) for c in item.get("subject", []) if c]
        primary_category = categories[0] if categories else "General"

        pub = item.get("published", {})
        date_parts = pub.get("date-parts", [[]])[0] if isinstance(pub, dict) else []
        if len(date_parts) >= 3:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-{date_parts[2]:02d}"
        elif len(date_parts) == 2:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-01"
        elif len(date_parts) == 1:
            published = f"{date_parts[0]:04d}-01-01"
        else:
            created = item.get("created", {}).get("date-time", "")
            published = created[:10] if created else "2026-01-01"

        updated = published
        url = item.get("URL", f"https://doi.org/{doi}")

        record = PaperRecord(
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
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi source API hoặc đọc snapshot fallback, lưu raw response, parse thành records."""
    payload: dict[str, Any] | None = None

    if settings.refresh_source:
        try:
            api_url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "Day10-DataPipeline-Observability/1.0 (mailto:student@university.edu)"}
            resp = requests.get(api_url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError("Raw Crossref API response not found and live API unreachable.")

    records = parse_crossref_payload(payload)

    serializable = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, serializable)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item.get("authors", []),
                categories=item.get("categories", []),
                primary_category=item.get("primary_category", "General"),
                published=item["published"],
                updated=item.get("updated", item["published"]),
                abs_url=item.get("abs_url", f"https://doi.org/{item['paper_id']}"),
                pdf_url=item.get("pdf_url", f"https://doi.org/{item['paper_id']}"),
                comment=item.get("comment", f"Crossref record {item['paper_id']}"),
            )
        )
    return records
