from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks bang Great Expectations 1.x."""
    import json

    import great_expectations as gx  # type: ignore
    from great_expectations.expectations.core import (  # type: ignore
        ExpectColumnValueLengthsToBeBetween,
        ExpectColumnValuesToBeUnique,
        ExpectColumnValuesToNotBeNull,
        ExpectTableRowCountToBeBetween,
    )
    
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"batch_{report_name}")
    batch_def.get_batch(batch_parameters={"dataframe": df})
    
    suite = context.suites.add(gx.ExpectationSuite(name=f"suite_{report_name}"))
    
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))
    
    val_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"val_{report_name}",
            data=batch_def,
            suite=suite,
        )
    )
    
    result = val_def.run(batch_parameters={"dataframe": df})
    
    res_dict = {
        "success": result.success,
        "statistics": result.statistics,
    }
    
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(res_dict, f, indent=2)
        
    return res_dict


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Any) -> dict[str, Any]:
    """Tong hop freshness report."""
    import json
    
    if df.empty:
        latest = oldest = ""
        stale_rows = 0
    else:
        latest = str(df["published"].max())
        oldest = str(df["published"].min())
        stale_rows = int((df["age_days"] > 180).sum())
        
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0
    is_fresh = stale_ratio <= 0.25
    
    payload = {
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh
    }
    
    with open(report_path, "w") as f:
        json.dump(payload, f, indent=2)
        
    return payload
