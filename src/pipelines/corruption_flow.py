from __future__ import annotations

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
    """Build corruption -> evaluate -> repair -> compare flow.

    1. Load baseline metrics and clean dataset.
    2. Create corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index and evaluate.
    5. Run quality checks/freshness on corrupted data.
    6. Repair from raw records.
    7. Evaluate repaired dataset.
    8. Create comparison report.
    """
    print("=" * 60)
    print("PHASE 2 -- Corruption, Repair & Comparison")
    print("=" * 60)

    settings = load_settings()
    run_date = now_utc()

    # 1. Load baseline metrics and clean data
    print("\n[Step 1] Loading baseline data...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = read_json(settings.paths.clean_json)

    import pandas as pd
    clean_df = pd.DataFrame(clean_df)
    print(f"  -> Loaded {len(clean_df)} clean records and baseline metrics.")

    # 2. Create corrupted dataframe
    print("\n[Step 2] Applying 6 corruption types...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"  -> Corrupted dataframe has {len(corrupted_df)} rows.")
    corruption_log = read_json(settings.paths.corruption_log)
    for entry in corruption_log:
        print(f"    - {entry['corruption_type']}: {entry['description']}")

    # 3. Save corrupted artifacts
    print("\n[Step 3] Saving corrupted data...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)

    # 4. Rebuild index and evaluate on corrupted data
    print("\n[Step 4] Building corrupted ChromaDB index...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    print("\n[Step 5] Evaluating corrupted pipeline...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_eval.summary
    print(f"  -> Corrupted Hit Rate:  {corrupted_metrics['retrieval_hit_rate']:.4f}")
    print(f"  -> Corrupted Token F1:  {corrupted_metrics['mean_token_f1']:.4f}")

    # 5. Quality checks on corrupted data
    print("\n[Step 6] Running quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    print(f"  -> Quality gate: {'PASS' if corrupted_quality['success'] else 'FAIL (corruption detected!)'}")

    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"  -> Freshness: {'OK' if corrupted_freshness['is_fresh'] else 'STALE'}")

    # 6. Repair from raw records (idempotent)
    print("\n[Step 7] Repairing data from raw backup (idempotent repair)...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"  -> Repaired {len(repaired_df)} records from raw backup.")

    # 7. Rebuild index and evaluate repaired data
    print("\n[Step 8] Building repaired ChromaDB index...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    print("\n[Step 9] Evaluating repaired pipeline...")
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_eval.summary
    print(f"  -> Repaired Hit Rate:  {repaired_metrics['retrieval_hit_rate']:.4f}")
    print(f"  -> Repaired Token F1:  {repaired_metrics['mean_token_f1']:.4f}")

    # Quality checks on repaired data
    print("\n[Step 10] Running quality checks on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    print(f"  -> Quality gate: {'PASS' if repaired_quality['success'] else 'FAIL'}")

    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    # 8. Generate comparison report
    print("\n[Step 11] Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"  -> Report saved to {settings.paths.comparison_report}")

    # Print comparison table
    print("\n" + "=" * 60)
    print("COMPARISON TABLE: Baseline vs Corrupted vs Repaired")
    print("=" * 60)
    print(f"{'Metric':<25} {'Baseline':>12} {'Corrupted':>12} {'Repaired':>12}")
    print("-" * 61)
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b = f"{baseline_metrics.get(key, 0):.4f}"
        c = f"{corrupted_metrics.get(key, 0):.4f}"
        r = f"{repaired_metrics.get(key, 0):.4f}"
        print(f"{key:<25} {b:>12} {c:>12} {r:>12}")

    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE -- Corruption & Repair flow finished!")
    print("=" * 60)
