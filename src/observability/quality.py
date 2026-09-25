from __future__ import annotations

from typing import Any

import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Great Expectations 1.x data quality checks.

    1. Check row count between 5 and 5000.
    2. Check paper_id not null and unique.
    3. Check title and text_for_embedding not null.
    4. Check summary length >= 30.
    5. Check freshness via age_days.
    6. Write results to data/quality/.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Define expectations
    expectations = [
        ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        ExpectColumnValuesToNotBeNull(column="paper_id"),
        ExpectColumnValuesToNotBeNull(column="title"),
        ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        ExpectColumnValuesToBeUnique(column="paper_id"),
        ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    results = []
    all_success = True
    for expectation in expectations:
        result = batch.validate(expectation)
        success = result.success
        results.append({
            "expectation_type": type(expectation).__name__,
            "success": success,
        })
        if not success:
            all_success = False

    report = {
        "report_name": report_name,
        "success": all_success,
        "total_rows": len(df),
        "checks": results,
    }

    # Save report
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build freshness monitoring report.

    1. Find latest and oldest published date.
    2. Count stale rows (age_days > threshold).
    3. Compute is_fresh flag (stale ratio <= 25%).
    4. Write JSON report.
    """
    if df.empty:
        payload: dict[str, Any] = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "threshold_days": settings.freshness_threshold_days,
        }
        write_json(report_path, payload)
        return payload

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "threshold_days": settings.freshness_threshold_days,
    }

    write_json(report_path, payload)
    return payload
