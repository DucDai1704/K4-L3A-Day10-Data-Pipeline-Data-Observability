from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import read_json, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name="papers_source")
    asset = source.add_dataframe_asset(name="papers_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)]
    for column in ("paper_id", "title", "text_for_embedding"):
        expectations.append(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
    expectations.extend([
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ])
    checks = []
    for expectation in expectations:
        result = batch.validate(expectation)
        checks.append({"expectation": type(expectation).__name__,
                       "column": getattr(expectation, "column", None),
                       "success": bool(result.success), "result": result.result})

    missing_ids = []
    if settings.paths.raw_records_json.exists():
        expected = {row["paper_id"] for row in read_json(settings.paths.raw_records_json)}
        missing_ids = sorted(expected - set(df["paper_id"].dropna().astype(str)))
    semantic_checks = {
        "missing_source_ids": missing_ids,
        "short_titles": int((df["title"].fillna("").astype(str).str.len() < 8).sum()),
        "noise_rows": int(df["summary"].fillna("").astype(str).str.contains("[CORRUPTED_NOISE]", regex=False).sum()),
        "blank_text_rows": int(df["text_for_embedding"].fillna("").astype(str).str.strip().eq("").sum()),
    }
    freshness = _freshness(df, settings)
    success = (all(check["success"] for check in checks)
               and not missing_ids and not any(semantic_checks[key] for key in ("short_titles", "noise_rows", "blank_text_rows"))
               and freshness["is_fresh"])
    payload = {"success": bool(success), "gx_success": all(check["success"] for check in checks),
               "checks": checks, "semantic_checks": semantic_checks, "freshness": freshness,
               "row_count": len(df)}
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    payload = _freshness(df, settings)
    write_json(report_path, payload)
    return payload


def _freshness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    dates = pd.to_datetime(df["published"], errors="coerce")
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    stale = int((ages > settings.freshness_threshold_days).sum())
    total = len(df)
    ratio = stale / total if total else 1.0
    return {"latest_published": dates.max().date().isoformat() if dates.notna().any() else None,
            "oldest_published": dates.min().date().isoformat() if dates.notna().any() else None,
            "stale_rows": stale, "total_rows": total, "stale_ratio": ratio,
            "threshold_days": settings.freshness_threshold_days,
            "is_fresh": bool(total and ratio <= 0.25 and dates.notna().all())}
