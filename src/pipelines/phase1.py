from __future__ import annotations

import json
from datetime import UTC, datetime

from core.config import load_settings
from core.utils import now_utc, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xây dựng và thực thi Baseline Pipeline end-to-end (Phase 1)."""
    print("=" * 60)
    print(">>> BẮT ĐẦU PHA 1: BASELINE PIPELINE & DATA OBSERVABILITY")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    print(f"[1/7] Cấu hình: Provider={settings.llm_provider}, Model={settings.model_name}")

    # 2. Ingestion & Raw preservation
    records = fetch_source_records(settings)
    print(f"[2/7] Raw Ingestion: Đã thu thập {len(records)} bản ghi từ {settings.source_api}")

    # 3. Data Cleaning & Transformation
    run_date = now_utc()
    clean_df = build_clean_dataframe(records, run_date)
    print(f"[3/7] Cleaning: Tạo clean dataframe với {len(clean_df)} dòng hợp lệ")

    # 4. Save clean artifacts
    write_csv(clean_df, settings.paths.clean_csv)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"      -> Xuất {settings.paths.clean_csv} & {settings.paths.clean_json}")

    # 5. Build Chroma Index
    print(f"[4/7] Indexing: Xây dựng Chroma collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(clean_df, settings, embeddings_output_path=settings.paths.embeddings_json)
    print(f"      -> Đã index {len(clean_df)} tài liệu với model {settings.embedding_model}")

    # 6. Evaluation test set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print(f"[5/7] Benchmark: Sinh bộ test set mới...")
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        print(f"[5/7] Benchmark: Sử dụng test set tại {settings.paths.eval_testset}")

    # 7. Evaluate baseline RAG
    print(f"[6/7] Đánh giá chất lượng RAG Baseline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"      Hit Rate: {bundle.summary['retrieval_hit_rate'] * 100:.1f}%")
    print(f"      Mean Token F1: {bundle.summary['mean_token_f1']:.4f}")
    print(f"      Judge Score: {bundle.summary['mean_judge_score']:.2f} / 5.0")

    # 8. Data Quality & Freshness
    print(f"[7/7] Data Observability Gate (GX 1.x & Freshness SLA)...")
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    print(f"      Quality Gate Status: {'PASSED' if quality['success'] else 'FAILED'}")
    print(f"      Freshness Status: {'FRESH' if freshness['is_fresh'] else 'STALE'} (Stale ratio: {freshness['stale_ratio']*100:.1f}%)")

    # 9. Sinh báo cáo Markdown
    source_summary = {
        "timestamp": now_utc().isoformat(),
        "source": settings.source_api,
        "total_records": len(clean_df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"      -> Xuất báo cáo Markdown: {settings.paths.baseline_report}")
    print("\n>>> PHA 1 HOÀN TẤT THÀNH CÔNG!\n")


if __name__ == "__main__":
    main()
