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
    settings = load_settings()
    paths = settings.paths
    if not paths.baseline_metrics.exists() or not paths.eval_testset.exists():
        from pipelines.phase1 import main as run_baseline
        run_baseline()
    baseline_metrics = read_json(paths.baseline_metrics)
    import pandas as pd
    clean = pd.read_json(paths.clean_json)
    corrupted = corrupt_clean_dataframe(clean, paths.corruption_log)
    write_csv(corrupted, paths.corrupted_clean_csv)
    corrupted.to_json(paths.corrupted_clean_json, orient="records", indent=2)
    corrupted_quality = run_data_quality_checks(corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted, settings, paths.quality_dir / "corrupted_freshness_report.json")
    # The failing state is isolated for measurement; it never replaces the serving collection.
    corrupted_index = LocalEmbeddingIndex.build(corrupted, settings, paths.corrupted_embeddings_json)
    corrupted_metrics = evaluate_pipeline(settings, corrupted_index, paths.eval_testset,
                                          paths.corrupted_metrics, paths.corrupted_answers).summary

    repaired = build_clean_dataframe(load_raw_records(paths.raw_records_json), now_utc())
    write_csv(repaired, paths.repaired_clean_csv)
    repaired.to_json(paths.repaired_clean_json, orient="records", indent=2)
    repaired_quality = run_data_quality_checks(repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired, settings, paths.quality_dir / "repaired_freshness_report.json")
    if not repaired_quality["success"]:
        raise RuntimeError("Repair failed the quality gate")
    repaired_index = LocalEmbeddingIndex.build(repaired, settings, paths.repaired_embeddings_json)
    repaired_metrics = evaluate_pipeline(settings, repaired_index, paths.eval_testset,
                                         paths.repaired_metrics, paths.repaired_answers).summary
    generate_corruption_report(paths.comparison_report, baseline_metrics, corrupted_metrics,
                               repaired_metrics, corrupted_quality, repaired_quality,
                               corrupted_freshness, repaired_freshness)
    print("Metric                 Baseline  Corrupted  Repaired")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(f"{key:23} {baseline_metrics[key]:8.3f} {corrupted_metrics[key]:10.3f} {repaired_metrics[key]:9.3f}")
    print(f"Quality gate: corrupted {'PASS' if corrupted_quality['success'] else 'FAIL'}, "
          f"repaired {'PASS' if repaired_quality['success'] else 'FAIL'}")
