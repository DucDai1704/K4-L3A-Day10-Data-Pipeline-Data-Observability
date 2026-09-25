from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records = []
    for item in payload.get("message", {}).get("items", []):
        doi = normalize_whitespace(str(item.get("DOI") or ""))
        titles = item.get("title") or []
        title = _plain_text(titles[0] if isinstance(titles, list) and titles else str(titles))
        published = _date(item, "published", "published-print", "published-online", "created")
        if not doi or not title or not published:
            continue
        authors = [_plain_text(" ".join(filter(None, [a.get("given"), a.get("family")])))
                   for a in item.get("author", [])]
        authors = [a for a in authors if a]
        categories = [_plain_text(s) for s in item.get("subject", []) if _plain_text(s)]
        url = str(item.get("URL") or f"https://doi.org/{doi}")
        links = item.get("link") or []
        pdf = next((link.get("URL") for link in links if "pdf" in link.get("content-type", "").lower()), url)
        records.append(PaperRecord(
            paper_id=doi, title=title, summary=_plain_text(item.get("abstract") or ""),
            authors=authors, categories=categories, primary_category=categories[0] if categories else "",
            published=published, updated=_date(item, "updated", "created") or published,
            abs_url=url, pdf_url=pdf, comment=f"Crossref record {doi}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    paths = settings.paths
    if not settings.refresh_source and paths.raw_api_response.exists():
        records = parse_crossref_payload(read_json(paths.raw_api_response))
        if records:
            write_json(paths.raw_records_json, [asdict(record) for record in records])
            return records

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    try:
        response = session.get("https://api.crossref.org/works", params={
            "query": settings.source_query, "filter": settings.source_filter,
            "rows": settings.max_results,
        }, headers={"User-Agent": "day10-data-observability-lab/0.1"}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        records = parse_crossref_payload(payload)
        if not records:
            raise ValueError("Crossref returned no usable records")
        write_json(paths.raw_api_response, payload)
        write_json(paths.raw_records_json, [asdict(record) for record in records])
        return records
    except (requests.RequestException, ValueError):
        if paths.raw_api_response.exists():
            records = parse_crossref_payload(read_json(paths.raw_api_response))
            if records:
                write_json(paths.raw_records_json, [asdict(record) for record in records])
                return records
        raise


def load_raw_records(path: Path) -> list[PaperRecord]:
    return [PaperRecord(**record) for record in read_json(path)]


def _plain_text(value: str) -> str:
    return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", value or "")))


def _date(item: dict, *fields: str) -> str:
    for field in fields:
        value = item.get(field) or {}
        date_parts = (value.get("date-parts") or []) if isinstance(value, dict) else []
        parts = date_parts[0] if date_parts else []
        if parts:
            try:
                return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1,
                            int(parts[2]) if len(parts) > 2 else 1).isoformat()
            except (ValueError, TypeError):
                pass
        if isinstance(value, dict) and value.get("date-time"):
            return str(value["date-time"])[:10]
    return ""
