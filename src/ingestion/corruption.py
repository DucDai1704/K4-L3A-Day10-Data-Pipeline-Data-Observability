from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Mô phỏng 6 dạng lỗi dữ liệu thực tế (Synthetic Data Corruption Suite).

    1. Drop latest records: Mất 20% các bài báo mới nhất.
    2. Blank summary: Xóa rỗng trường tóm tắt ở một số dòng.
    3. Inject noise: Chèn ký tự rác vào trường tóm tắt.
    4. Truncate title: Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự.
    5. Stale date: Lùi ngày xuất bản về quá khứ (+365 ngày tuổi) làm mốc meo dữ liệu.
    6. Duplicate rows: Nhân bản các dòng để tạo lỗi trùng lặp bản ghi.
    7. Rebuild text_for_embedding & summary_chars.
    8. Ghi corruption log vào output_log_path.
    """
    if len(df) < 6:
        raise ValueError("DataFrame must have at least 6 records for the corruption suite.")

    corrupted = df.copy()
    total_original = len(corrupted)
    log_entries: list[dict[str, Any]] = []

    # 1. Drop latest records (20% of dataset)
    n_drop = max(1, int(len(corrupted) * 0.20))
    dropped_rows = corrupted.iloc[:n_drop]
    dropped_ids = dropped_rows["paper_id"].tolist()
    corrupted = corrupted.iloc[n_drop:].copy().reset_index(drop=True)
    log_entries.append(
        {
            "type": "drop_latest_records",
            "description": f"Dropped {n_drop} newest records (20%)",
            "count": n_drop,
            "paper_ids": dropped_ids,
        }
    )

    # 2. Blank summary on 2 records
    blank_indices = [0, 1] if len(corrupted) > 1 else [0]
    blank_ids: list[str] = []
    for idx in blank_indices:
        corrupted.loc[idx, "summary"] = ""
        blank_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "type": "blank_summary",
            "description": "Erased abstract/summary to empty string",
            "count": len(blank_indices),
            "paper_ids": blank_ids,
        }
    )

    # 3. Inject noise into summary on 2 records
    noise_indices = [2, 3] if len(corrupted) > 3 else [0]
    noise_ids: list[str] = []
    for idx in noise_indices:
        original_summary = str(corrupted.loc[idx, "summary"])
        corrupted.loc[idx, "summary"] = f"###CORRUPTED_NOISE_GARBAGE### %$^&*! {original_summary}"
        noise_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "type": "inject_noise",
            "description": "Injected gibberish noise tokens into summary",
            "count": len(noise_indices),
            "paper_ids": noise_ids,
        }
    )

    # 4. Truncate title on 2 records (< 8 characters)
    trunc_indices = [4, 5] if len(corrupted) > 5 else [0]
    trunc_ids: list[str] = []
    for idx in trunc_indices:
        corrupted.loc[idx, "title"] = str(corrupted.loc[idx, "title"])[:5]
        trunc_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "type": "truncate_title",
            "description": "Truncated title to < 8 characters",
            "count": len(trunc_indices),
            "paper_ids": trunc_ids,
        }
    )

    # 5. Stale date on 3 records (push back 365 days)
    stale_indices = [idx for idx in [6, 7, 8] if idx < len(corrupted)]
    stale_ids: list[str] = []
    for idx in stale_indices:
        old_pub = str(corrupted.loc[idx, "published"])
        try:
            old_dt = datetime.fromisoformat(old_pub)
            new_dt = old_dt - timedelta(days=365)
            corrupted.loc[idx, "published"] = new_dt.strftime("%Y-%m-%d")
        except Exception:
            corrupted.loc[idx, "published"] = "2024-01-01"
        corrupted.loc[idx, "age_days"] = int(corrupted.loc[idx, "age_days"]) + 365
        stale_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "type": "stale_date",
            "description": "Shifted published date back 365 days (stale data)",
            "count": len(stale_indices),
            "paper_ids": stale_ids,
        }
    )

    # 6. Duplicate rows (duplicate first 2 rows)
    dup_rows = corrupted.iloc[[0, 1]].copy() if len(corrupted) > 1 else corrupted.iloc[[0]].copy()
    dup_ids = dup_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries.append(
        {
            "type": "duplicate_rows",
            "description": "Duplicated rows to create ghost records and violate uniqueness",
            "count": len(dup_rows),
            "paper_ids": dup_ids,
        }
    )

    # 7. Rebuild summary_chars and text_for_embedding
    corrupted["summary_chars"] = corrupted["summary"].apply(lambda s: len(str(s)))
    for idx in range(len(corrupted)):
        title = corrupted.loc[idx, "title"]
        authors = corrupted.loc[idx, "authors_joined"]
        published = corrupted.loc[idx, "published"]
        categories = corrupted.loc[idx, "categories_joined"]
        summary = corrupted.loc[idx, "summary"]
        corrupted.loc[idx, "text_for_embedding"] = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Published: {published}\n"
            f"Categories: {categories}\n"
            f"Summary: {summary}"
        ).strip()

    # 8. Save corruption log
    log_payload = {
        "timestamp": datetime.now().isoformat(),
        "total_original_rows": total_original,
        "total_corrupted_rows": len(corrupted),
        "corruptions": log_entries,
    }
    write_json(Path(output_log_path), log_payload)

    return corrupted
