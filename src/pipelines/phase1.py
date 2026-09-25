from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build the baseline pipeline end-to-end.

    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Create or load evaluation set.
    7. Evaluate.
    8. Run quality checks and freshness report.
    9. Create markdown report.
    """
    print("=" * 60)
    print("PHASE 1 -- Baseline Pipeline")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    run_date = now_utc()

    # 2. Load or fetch raw records
    print("\n[Step 1] Fetching/loading raw records...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"  -> Loaded {len(records)} raw records.")

    # 3. Clean data
    print("\n[Step 2] Cleaning data...")
    df = build_clean_dataframe(records, run_date)
    print(f"  -> Cleaned {len(df)} records.")

    # 4. Save clean CSV/JSON
    print("\n[Step 3] Saving clean data...")
    write_csv(df, settings.paths.clean_csv)
    # Save as JSON (records oriented) for downstream use
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
    print(f"  -> Saved to {settings.paths.clean_csv}")
    print(f"  -> Saved to {settings.paths.clean_json}")

    # 5. Build Chroma index
    print("\n[Step 4] Building ChromaDB index...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"  -> Collection '{settings.baseline_collection_name}' built with {len(df)} documents.")

    # 6. Create evaluation test set
    print("\n[Step 5] Generating evaluation test set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    print(f"  -> Test set has {len(test_set)} questions.")

    # 7. Evaluate
    print("\n[Step 6] Evaluating baseline pipeline...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = eval_bundle.summary
    print(f"  -> Retrieval Hit Rate: {metrics['retrieval_hit_rate']:.4f}")
    print(f"  -> Mean Token F1:     {metrics['mean_token_f1']:.4f}")
    print(f"  -> Judge Accuracy:    {metrics['judge_accuracy']:.4f}")
    print(f"  -> Mean Judge Score:  {metrics['mean_judge_score']:.2f}")

    # 8. Run quality checks and freshness
    print("\n[Step 7] Running data quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")
    print(f"  -> Quality gate: {'PASS' if quality['success'] else 'FAIL'}")

    print("\n[Step 8] Building freshness report...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"  -> Is Fresh: {'Yes' if freshness['is_fresh'] else 'No'}")
    print(f"  -> Stale rows: {freshness['stale_rows']} / {freshness['total_rows']}")

    # 9. Create markdown report
    print("\n[Step 9] Generating phase 1 report...")
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "total_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )
    print(f"  -> Report saved to {settings.paths.baseline_report}")

    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETE -- Baseline pipeline finished successfully!")
    print("=" * 60)
