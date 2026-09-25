from __future__ import annotations

import random
from datetime import timedelta

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 types of data corruption on the clean dataframe.

    1. Drop latest records (20% of newest by published date).
    2. Blank summary on some rows.
    3. Inject noise characters into text.
    4. Truncate title to < 8 characters.
    5. Stale date: push published 365 days into the past.
    6. Add duplicate rows.
    7. Rebuild text_for_embedding.
    8. Write corruption log to output_log_path.
    """
    random.seed(42)
    corrupted = df.copy()
    log: list[dict] = []
    n = len(corrupted)

    # --- 1. Drop latest records (20%) ---
    sorted_df = corrupted.sort_values("published", ascending=False)
    n_drop = max(1, int(n * 0.2))
    drop_ids = sorted_df.head(n_drop)["paper_id"].tolist()
    corrupted = corrupted[~corrupted["paper_id"].isin(drop_ids)].copy()
    log.append({
        "corruption_type": "drop_latest_records",
        "description": f"Dropped {n_drop} newest records",
        "affected_paper_ids": drop_ids,
        "rows_affected": n_drop,
    })

    # --- 2. Blank summary on some rows ---
    remaining = corrupted.index.tolist()
    n_blank = max(1, int(len(remaining) * 0.15))
    blank_indices = random.sample(remaining, min(n_blank, len(remaining)))
    blank_ids = corrupted.loc[blank_indices, "paper_id"].tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    corrupted.loc[blank_indices, "summary_chars"] = 0
    log.append({
        "corruption_type": "blank_summary",
        "description": f"Blanked summary for {len(blank_indices)} rows",
        "affected_paper_ids": blank_ids,
        "rows_affected": len(blank_indices),
    })

    # --- 3. Inject noise into text ---
    remaining = corrupted.index.tolist()
    n_noise = max(1, int(len(remaining) * 0.15))
    noise_indices = random.sample(remaining, min(n_noise, len(remaining)))
    noise_ids = corrupted.loc[noise_indices, "paper_id"].tolist()
    noise_chars = "!@#$%^&*()_+=[]{}|;:',.<>?/~`"
    for idx in noise_indices:
        original = corrupted.at[idx, "summary"]
        noise = "".join(random.choices(noise_chars, k=20))
        corrupted.at[idx, "summary"] = f"{noise} {original} {noise}"
    log.append({
        "corruption_type": "inject_noise",
        "description": f"Injected noise characters into {len(noise_indices)} summaries",
        "affected_paper_ids": noise_ids,
        "rows_affected": len(noise_indices),
    })

    # --- 4. Truncate title ---
    remaining = corrupted.index.tolist()
    n_trunc = max(1, int(len(remaining) * 0.15))
    trunc_indices = random.sample(remaining, min(n_trunc, len(remaining)))
    trunc_ids = corrupted.loc[trunc_indices, "paper_id"].tolist()
    for idx in trunc_indices:
        corrupted.at[idx, "title"] = corrupted.at[idx, "title"][:7]
    log.append({
        "corruption_type": "truncate_title",
        "description": f"Truncated {len(trunc_indices)} titles to < 8 chars",
        "affected_paper_ids": trunc_ids,
        "rows_affected": len(trunc_indices),
    })

    # --- 5. Stale date: push published 365 days into past ---
    remaining = corrupted.index.tolist()
    n_stale = max(1, int(len(remaining) * 0.2))
    stale_indices = random.sample(remaining, min(n_stale, len(remaining)))
    stale_ids = corrupted.loc[stale_indices, "paper_id"].tolist()
    for idx in stale_indices:
        try:
            old_date = pd.to_datetime(corrupted.at[idx, "published"])
            new_date = old_date - timedelta(days=365)
            corrupted.at[idx, "published"] = new_date.strftime("%Y-%m-%d")
            corrupted.at[idx, "age_days"] = corrupted.at[idx, "age_days"] + 365
        except Exception:
            pass
    log.append({
        "corruption_type": "stale_date",
        "description": f"Pushed {len(stale_indices)} published dates 365 days into past",
        "affected_paper_ids": stale_ids,
        "rows_affected": len(stale_indices),
    })

    # --- 6. Duplicate rows ---
    remaining = corrupted.index.tolist()
    n_dup = max(1, int(len(remaining) * 0.15))
    dup_indices = random.sample(remaining, min(n_dup, len(remaining)))
    dup_ids = corrupted.loc[dup_indices, "paper_id"].tolist()
    dup_rows = corrupted.loc[dup_indices].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log.append({
        "corruption_type": "duplicate_rows",
        "description": f"Duplicated {len(dup_indices)} rows",
        "affected_paper_ids": dup_ids,
        "rows_affected": len(dup_indices),
    })

    # --- 7. Rebuild text_for_embedding ---
    for idx in corrupted.index:
        row = corrupted.loc[idx]
        corrupted.at[idx, "text_for_embedding"] = (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )

    # --- 8. Write corruption log ---
    write_json(output_log_path, log)

    return corrupted
