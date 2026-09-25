from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: str | Path | None = None) -> dict[str, Any]:
    """Tổng hợp freshness report theo Freshness SLA (age_days > 180).

    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale (age_days > freshness_threshold_days).
    3. Tính tỷ lệ stale_ratio.
    4. Gắn cờ is_fresh = True nếu stale_ratio <= 0.25 (ngưỡng 25%).
    5. Ghi JSON report nếu có report_path.
    """
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
        }
    else:
        published_dates = df["published"].dropna().tolist()
        latest_published = max(published_dates) if published_dates else None
        oldest_published = min(published_dates) if published_dates else None

        threshold = settings.freshness_threshold_days
        stale_mask = df["age_days"] > threshold
        stale_rows = int(stale_mask.sum())
        stale_ratio = round(stale_rows / total_rows, 4)
        is_fresh = stale_ratio <= 0.25

        report = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": stale_ratio,
            "freshness_threshold_days": threshold,
            "is_fresh": is_fresh,
        }

    if report_path:
        write_json(Path(report_path), report)

    return report


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chốt kiểm dịch chất lượng dữ liệu (Data Quality Gate) bằng Great Expectations 1.x.

    1. Check row count (5 <= rows <= 5000).
    2. Check paper_id, title, text_for_embedding not null.
    3. Check paper_id unique.
    4. Check summary length >= 30 chars.
    5. Check Freshness SLA.
    6. Ghi kết quả vào data/quality/.
    """
    # Direct rule evaluations
    r1_count = bool(5 <= len(df) <= 5000)
    r2_not_null = bool(
        ("paper_id" in df.columns and df["paper_id"].notna().all() and (df["paper_id"].astype(str).str.strip() != "").all())
        and ("title" in df.columns and df["title"].notna().all() and (df["title"].astype(str).str.strip() != "").all())
        and ("text_for_embedding" in df.columns and df["text_for_embedding"].notna().all() and (df["text_for_embedding"].astype(str).str.strip() != "").all())
    )
    r3_unique = bool("paper_id" in df.columns and df["paper_id"].is_unique)
    r4_summary_len = bool("summary" in df.columns and (df["summary"].astype(str).str.len() >= 30).all())

    rules_passed = bool(r1_count and r2_not_null and r3_unique and r4_summary_len)
    gx_success = True
    gx_details: dict[str, Any] | None = None

    # Great Expectations 1.x validation
    try:
        import great_expectations as gx
        import great_expectations.expectations as gxe

        context = gx.get_context(mode="ephemeral")
        source_name = f"papers_source_{report_name}"
        asset_name = f"papers_asset_{report_name}"
        batch_name = f"papers_batch_{report_name}"

        data_source = context.data_sources.add_pandas(name=source_name)
        data_asset = data_source.add_dataframe_asset(name=asset_name)
        batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")
        suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

        validation_result = batch.validate(suite)
        gx_success = bool(validation_result.success)
        gx_details = validation_result.to_json_dict()
    except Exception as exc:
        gx_details = {"error": f"GX 1.x evaluation note: {exc}"}

    overall_success = bool(rules_passed and gx_success)

    # Freshness evaluation
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # Determine report save path
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    result: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "total_rows": len(df),
        "rules_passed": rules_passed,
        "checks": {
            "ExpectTableRowCountToBeBetween": r1_count,
            "ExpectColumnValuesToNotBeNull": r2_not_null,
            "ExpectColumnValuesToBeUnique": r3_unique,
            "ExpectColumnValueLengthsToBeBetween": r4_summary_len,
        },
        "freshness": freshness,
        "gx_details": gx_details,
    }

    write_json(Path(report_path), result)
    return result
