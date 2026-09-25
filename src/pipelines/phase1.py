from __future__ import annotations

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
    settings = load_settings()
    paths = settings.paths
    records = fetch_source_records(settings)
    df = build_clean_dataframe(records, now_utc())
    write_csv(df, paths.clean_csv)
    df.to_json(paths.clean_json, orient="records", indent=2)
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality gate; see baseline_quality_report.json")
    build_test_set(df, paths.eval_testset)
    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)
    metrics = evaluate_pipeline(settings, index, paths.eval_testset,
                                paths.baseline_metrics, paths.baseline_answers).summary
    source_label = "Bundled Crossref snapshot" if not settings.refresh_source else settings.source_api
    generate_phase1_report(paths.baseline_report,
                           {"source": source_label, "raw_records": len(records), "clean_records": len(df)},
                           metrics, quality, freshness)
    print(f"Baseline: {len(df)} papers, hit rate {metrics['retrieval_hit_rate']:.3f}, "
          f"token F1 {metrics['mean_token_f1']:.3f}; quality PASS")
