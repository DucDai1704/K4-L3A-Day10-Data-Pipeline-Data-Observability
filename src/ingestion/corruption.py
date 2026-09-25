from __future__ import annotations

import pandas as pd


from typing import Any

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Any) -> pd.DataFrame:
    """Simulate nhieu dang data corruption."""
    import json
    
    df_corrupt = df.copy()
    
    # 1. Drop mot so latest records (first 2 records)
    if len(df_corrupt) > 2:
        df_corrupt = df_corrupt.iloc[2:].reset_index(drop=True)
        
    # 2. Blank summary o mot so dong (first 2 remaining)
    for i in range(min(2, len(df_corrupt))):
        df_corrupt.at[i, "summary"] = ""
        df_corrupt.at[i, "summary_chars"] = 0
        
    # 3. Inject noise vao text
    for i in range(2, min(4, len(df_corrupt))):
        df_corrupt.at[i, "summary"] = df_corrupt.at[i, "summary"] + " NOISE_12345!@#$ " * 5
        
    # 4. Lam title bi truncate
    for i in range(4, min(6, len(df_corrupt))):
        title = str(df_corrupt.at[i, "title"])
        df_corrupt.at[i, "title"] = title[:7] if len(title) > 7 else title
        
    # 5. Lam published date cu di (age_days > 180)
    for i in range(min(len(df_corrupt), 10)):
        df_corrupt.at[i, "age_days"] = 365
        
    # 6. Add duplicate rows
    if len(df_corrupt) > 0:
        dup = df_corrupt.iloc[[0]].copy()
        df_corrupt = pd.concat([df_corrupt, dup], ignore_index=True)
        
    # 7. Rebuild text_for_embedding
    for i in range(len(df_corrupt)):
        title = df_corrupt.at[i, "title"]
        summary = df_corrupt.at[i, "summary"]
        authors_joined = df_corrupt.at[i, "authors_joined"]
        categories_joined = df_corrupt.at[i, "categories_joined"]
        published = df_corrupt.at[i, "published"]
        
        text_for_embedding = f"Title: {title}\nAuthors: {authors_joined}\nPublished: {published}\nCategories: {categories_joined}\nSummary: {summary}"
        df_corrupt.at[i, "text_for_embedding"] = text_for_embedding

    # 8. Ghi corruption log
    log_payload = {
        "dropped_records": 2,
        "blank_summaries": 2,
        "noise_injected": 2,
        "truncated_titles": 2,
        "stale_dates": 10,
        "duplicates": 1
    }
    
    import pathlib
    pathlib.Path(output_log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w") as f:
        json.dump(log_payload, f, indent=2)
        
    return df_corrupt
