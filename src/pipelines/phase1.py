from __future__ import annotations

from datetime import UTC


def main() -> None:
    """Xay dung baseline pipeline end-to-end."""
    import json
    from datetime import datetime

    from core.config import load_settings
    from evaluation.metrics import evaluate_pipeline
    from evaluation.testset import build_test_set
    from ingestion.cleaning import build_clean_dataframe
    from ingestion.crossref import fetch_source_records
    from observability.quality import build_freshness_report, run_data_quality_checks
    from observability.reporting import generate_phase1_report
    from retrieval.index import LocalEmbeddingIndex
    
    # 1. Load settings
    settings = load_settings()
    
    # 2. Load hoac fetch raw records
    raw_records = fetch_source_records(settings)
    
    # 3. Clean data
    df = build_clean_dataframe(raw_records, datetime.now(UTC))
    
    # 4. Save clean CSV/JSON
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    
    # 5. Build Chroma index
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json
    )
    
    # 6. Tao hoac load evaluation set
    settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
    build_test_set(df, settings.paths.eval_testset)
    
    # 7. Evaluate
    settings.paths.baseline_metrics.parent.mkdir(parents=True, exist_ok=True)
    evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers
    )
    
    # 8. Run quality checks va freshness report
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    run_data_quality_checks(df, settings, "baseline")
    build_freshness_report(df, settings, settings.paths.freshness_report)
    
    # 9. Tao markdown report
    with open(settings.paths.baseline_metrics, "r") as f:
        metrics = json.load(f)
    with open(settings.paths.baseline_quality_report, "r") as f:
        quality = json.load(f)
    with open(settings.paths.freshness_report, "r") as f:
        freshness = json.load(f)
        
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary={"total_records": len(df)},
        metrics=metrics,
        quality=quality,
        freshness=freshness
    )
    
    print("Phase 1 Baseline Pipeline completed successfully!")
