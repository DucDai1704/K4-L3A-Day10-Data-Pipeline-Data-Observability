from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xây dựng và thực thi luồng Tiêm lỗi, Đo lường suy giảm và Phục hồi (Phase 2)."""
    print("=" * 60)
    print(">>> BẮT ĐẦU PHA 2: CORRUPTION, REPAIR & 3-STATE COMPARISON")
    print("=" * 60)

    settings = load_settings()

    # 1. Load clean dataset and baseline metrics
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(f"Chưa tìm thấy {settings.paths.clean_json}. Vui lòng chạy Phase 1 trước.")
    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"[1/6] Đã nạp Baseline Metrics: Hit Rate={baseline_metrics.get('retrieval_hit_rate', 0.0)*100:.1f}%")

    # 2. Tiêm 6 loại lỗi dữ liệu (Data Corruption)
    print(f"[2/6] Synthetic Corruption: Đang tiêm 6 kịch bản lỗi vào dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"      -> Đã xuất {settings.paths.corrupted_clean_csv} ({len(corrupted_df)} dòng)")
    print(f"      -> Nhật ký lỗi tại: {settings.paths.corruption_log}")

    # 3. Build Corrupted Vector Index & Đo lường suy giảm (Silent Failure)
    print(f"[3/6] Indexing dữ liệu bẩn và kiểm thử sự sụt giảm hiệu năng...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"      Corrupted Hit Rate: {corrupted_bundle.summary['retrieval_hit_rate']*100:.1f}%")
    print(f"      Corrupted Token F1: {corrupted_bundle.summary['mean_token_f1']:.4f}")
    print(f"      Corrupted Judge Score: {corrupted_bundle.summary['mean_judge_score']:.2f}")

    # 4. Data Quality Gate trên dữ liệu bẩn
    print(f"[4/6] Data Observability Gate kiểm tra dữ liệu bẩn...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings)
    print(f"      Quality Gate Status: {'PASSED' if corrupted_quality['success'] else 'FAILED (Phát hiện dị thường!)'}")

    # 5. Phục hồi an toàn (Idempotent Repair) từ Raw Data
    print(f"[5/6] Idempotent Repair: Đang phục hồi dữ liệu từ {settings.paths.raw_records_json}...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings)
    print(f"      Repaired Hit Rate: {repaired_bundle.summary['retrieval_hit_rate']*100:.1f}%")
    print(f"      Repaired Token F1: {repaired_bundle.summary['mean_token_f1']:.4f}")
    print(f"      Quality Gate Status: {'PASSED (Đã hồi sinh!)' if repaired_quality['success'] else 'FAILED'}")

    # 6. Xuất báo cáo đối chiếu 3 trạng thái
    print(f"[6/6] Xuất Báo Cáo Đối Chiếu 3 Trạng Thái...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"      -> Báo cáo Markdown: {settings.paths.comparison_report}")
    print("\n>>> PHA 2 HOÀN TẤT THÀNH CÔNG!\n")


if __name__ == "__main__":
    main()
