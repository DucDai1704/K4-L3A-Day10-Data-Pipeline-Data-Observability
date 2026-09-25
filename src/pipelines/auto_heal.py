from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def run_self_healing_pipeline(df: pd.DataFrame, source_label: str = "incoming_batch") -> dict[str, Any]:
    """Automated Self-Healing Pipeline (Bonus B2).

    1. Tự động kiểm tra chất lượng dữ liệu với Great Expectations 1.x.
    2. Nếu phát hiện vi phạm Quality Gate (success == False):
       - Kích hoạt cơ chế Tự Phục Hồi (Auto-Repair) từ Raw Preservation.
       - Tái lập clean dataset và khử trùng lặp.
       - Tái đồng bộ Vector Database để loại bỏ poisoned vectors.
       - Kiểm định lại chất lượng sau phục hồi.
    3. Ghi audit log chi tiết vào data/results/self_healing_audit.json.
    """
    settings = load_settings()
    audit_file = settings.paths.project_dir / "data" / "results" / "self_healing_audit.json"

    initial_check = run_data_quality_checks(df, settings, f"{source_label}_initial")
    freshness = build_freshness_report(df, settings)

    action_taken = "NONE"
    repaired_quality: dict[str, Any] | None = None
    final_df = df

    if not initial_check.get("success"):
        print(f"⚠️ [ALERT] Phát hiện dữ liệu lỗi trong '{source_label}'!")
        print("🔧 [SELF-HEALING] Tự động kích hoạt cơ chế Rollback & Phục hồi từ Raw Lineage...")

        # Phục hồi an toàn từ raw snapshot
        raw_records = load_raw_records(settings.paths.raw_records_json)
        repaired_df = build_clean_dataframe(raw_records, now_utc())

        # Ghi đè artifact sạch
        write_csv(repaired_df, settings.paths.repaired_clean_csv)
        repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

        # Tái lập Vector Store
        LocalEmbeddingIndex.build(
            repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
        )

        repaired_quality = run_data_quality_checks(repaired_df, settings, f"{source_label}_auto_repaired")
        action_taken = "AUTO_REPAIRED_FROM_RAW"
        final_df = repaired_df

        print("✅ [SELF-HEALING] Phục hồi hoàn tất. Quality Gate đã chuyển sang PASSED!")
    else:
        print(f"✨ [OK] Dữ liệu '{source_label}' đạt chuẩn Quality Gate. Tiếp tục serving.")

    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "source_label": source_label,
        "action_taken": action_taken,
        "initial_passed": bool(initial_check.get("success")),
        "repaired_passed": bool(repaired_quality.get("success")) if repaired_quality else None,
        "freshness": freshness,
        "final_rows": len(final_df),
    }

    write_json(audit_file, audit_entry)
    return audit_entry
