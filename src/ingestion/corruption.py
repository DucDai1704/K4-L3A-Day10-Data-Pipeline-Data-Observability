from __future__ import annotations

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import embedding_text


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    if len(df) < 10:
        raise ValueError("At least 10 rows are needed for controlled corruption")
    corrupted = df.copy(deep=True)
    latest = corrupted.sort_values("published", ascending=False).head(max(1, round(len(df) * 0.2)))
    dropped_ids = latest["paper_id"].tolist()
    corrupted = corrupted.loc[~corrupted["paper_id"].isin(dropped_ids)].copy()
    ordered = corrupted.sort_values("paper_id").index.tolist()
    blank_ids = corrupted.loc[ordered[:3], "paper_id"].tolist()
    noise_ids = corrupted.loc[ordered[3:6], "paper_id"].tolist()
    title_ids = corrupted.loc[ordered[:4], "paper_id"].tolist()
    corrupted.loc[ordered[:3], "summary"] = ""
    corrupted.loc[ordered[3:6], "summary"] = "[CORRUPTED_NOISE] " + corrupted.loc[ordered[3:6], "summary"].astype(str)
    corrupted.loc[ordered[:4], "title"] = corrupted.loc[ordered[:4], "title"].astype(str).str.slice(0, 7)
    corrupted["published"] = (pd.to_datetime(corrupted["published"]) - pd.Timedelta(days=365)).dt.date.astype(str)
    corrupted["age_days"] = pd.to_numeric(corrupted["age_days"]) + 365
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(lambda row: embedding_text(row), axis=1)
    duplicated_ids = corrupted.loc[ordered[:2], "paper_id"].tolist()
    corrupted = pd.concat([corrupted, corrupted.loc[ordered[:2]].copy()], ignore_index=True)
    log = {
        "source_rows": len(df), "corrupted_rows": len(corrupted),
        "drop_latest_records": {"count": len(dropped_ids), "paper_ids": dropped_ids},
        "blank_summary": {"count": len(blank_ids), "paper_ids": blank_ids},
        "inject_noise": {"count": len(noise_ids), "paper_ids": noise_ids},
        "truncate_title": {"count": len(title_ids), "paper_ids": title_ids},
        "stale_date": {"count": len(ordered), "days_shifted": 365},
        "duplicate_rows": {"count": len(duplicated_ids), "paper_ids": duplicated_ids},
    }
    write_json(output_log_path, log)
    return corrupted
