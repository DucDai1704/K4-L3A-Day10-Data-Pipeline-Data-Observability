from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path: Any,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    report = f"""# Baseline Phase Report
    
## Source Summary
- Total Records: {source_summary.get('total_records', 0)}

## Data Quality & Freshness
- Quality Success: {quality.get('success', False)}
- Is Fresh: {freshness.get('is_fresh', False)}
- Stale Rows: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}

## Evaluation Metrics
- Hit Rate: {metrics.get('retrieval_hit_rate', 0):.2f}
- Token F1: {metrics.get('mean_token_f1', 0):.2f}
- Judge Accuracy: {metrics.get('judge_accuracy', 0):.2f}
- Mean Judge Score: {metrics.get('mean_judge_score', 0):.2f}
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)


def generate_corruption_report(
    report_path: Any,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    report = f"""# Corruption vs Repair Report

| Metric | Baseline (Clean) | Corrupted (Dirty) | Repaired (Restored) |
|---|---|---|---|
| Hit Rate | {baseline_metrics.get('retrieval_hit_rate', 0):.2f} | {corrupted_metrics.get('retrieval_hit_rate', 0):.2f} | {repaired_metrics.get('retrieval_hit_rate', 0):.2f} |
| Token F1 | {baseline_metrics.get('mean_token_f1', 0):.2f} | {corrupted_metrics.get('mean_token_f1', 0):.2f} | {repaired_metrics.get('mean_token_f1', 0):.2f} |
| Judge Accuracy | {baseline_metrics.get('judge_accuracy', 0):.2f} | {corrupted_metrics.get('judge_accuracy', 0):.2f} | {repaired_metrics.get('judge_accuracy', 0):.2f} |
| Quality Success | True | {corrupted_quality.get('success', False)} | {repaired_quality.get('success', False)} |
| Is Fresh | True | {corrupted_freshness.get('is_fresh', False)} | {repaired_freshness.get('is_fresh', False)} |

"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
