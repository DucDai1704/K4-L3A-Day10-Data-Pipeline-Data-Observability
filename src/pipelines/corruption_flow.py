from __future__ import annotations

from datetime import UTC


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow."""
    import json
    from datetime import datetime

    import pandas as pd

    from core.config import load_settings
    from evaluation.metrics import evaluate_pipeline
    from ingestion.cleaning import build_clean_dataframe
    from ingestion.corruption import corrupt_clean_dataframe
    from ingestion.crossref import load_raw_records
    from observability.quality import build_freshness_report, run_data_quality_checks
    from observability.reporting import generate_corruption_report
    from retrieval.index import LocalEmbeddingIndex
    
    settings = load_settings()
    
    # 1. Load baseline metrics va clean dataset
    df_clean = pd.read_json(settings.paths.clean_json)
    with open(settings.paths.baseline_metrics, "r") as f:
        baseline_metrics = json.load(f)
        
    # 2. Tao corrupted dataframe
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    
    # 3. Save corrupted artifacts
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    
    # 4. Rebuild index va evaluate (Corrupted)
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers
    )
    with open(settings.paths.corrupted_metrics, "r") as f:
        corrupted_metrics = json.load(f)
        
    # 5. Run quality checks/freshness tren corrupted data
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")
    
    # 6. Repair lai tu raw records
    raw_records = load_raw_records(settings.paths.raw_api_response)
    df_repaired = build_clean_dataframe(raw_records, datetime.now(UTC))
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    
    # 7. Evaluate repaired dataset
    index_repaired = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers
    )
    with open(settings.paths.repaired_metrics, "r") as f:
        repaired_metrics = json.load(f)
        
    # 8. Run quality checks/freshness tren repaired data
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness_report.json")
    
    # 9. Tao comparison report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness
    )
    
    print("Corruption Flow Pipeline completed successfully!")
