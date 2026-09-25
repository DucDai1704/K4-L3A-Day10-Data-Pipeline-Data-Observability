from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = ["# Phase 1: Baseline pipeline", "", "## Source", "",
             f"- Source: {source_summary['source']}",
             f"- Raw records: {source_summary['raw_records']}",
             f"- Clean records: {source_summary['clean_records']}",
             "", "## Evaluation", "", "| Metric | Value |", "|---|---:|"]
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(f"| {key} | {_format(metrics[key])} |")
    lines += ["", f"Judge method: heuristic fallback for {metrics.get('fallback_judge_count', 0)}/{metrics['samples']} answers.",
              "Retrieval hit rate includes exact-title lookup in the QA layer.",
              "", "## Data quality and freshness", "",
              f"- Quality gate: {'PASS' if quality['success'] else 'FAIL'}",
              f"- GX expectations passed: {sum(c['success'] for c in quality['checks'])}/{len(quality['checks'])}",
              f"- Freshness SLA: {'PASS' if freshness['is_fresh'] else 'FAIL'}",
              f"- Stale rows: {freshness['stale_rows']}/{freshness['total_rows']} ({freshness['stale_ratio']:.1%})",
              f"- Publication range: {freshness['oldest_published']} to {freshness['latest_published']}", ""]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    lines = ["# Corruption and repair comparison", "",
             "All three states use the same 10-question evaluation set and separate Chroma collections. Retrieval hit rate includes exact-title lookup in the QA layer.", "",
             "| Measure | Baseline | Corrupted | Repaired |", "|---|---:|---:|---:|"]
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(f"| {key} | {_format(baseline_metrics[key])} | {_format(corrupted_metrics[key])} | {_format(repaired_metrics[key])} |")
    lines += [f"| Quality gate | PASS | {'PASS' if corrupted_quality['success'] else 'FAIL'} | {'PASS' if repaired_quality['success'] else 'FAIL'} |",
              f"| Freshness SLA | — | {'PASS' if corrupted_freshness['is_fresh'] else 'FAIL'} | {'PASS' if repaired_freshness['is_fresh'] else 'FAIL'} |",
              "", "## Judge method", "",
              f"Heuristic fallback used for {baseline_metrics.get('fallback_judge_count', 0)}, "
              f"{corrupted_metrics.get('fallback_judge_count', 0)}, and "
              f"{repaired_metrics.get('fallback_judge_count', 0)} answers respectively. "
              "These scores are not independent LLM judgments when the mock provider is selected.",
              "", "## Observed violations", ""]
    for check in corrupted_quality["checks"]:
        if not check["success"]:
            lines.append(f"- GX: {check['expectation']} ({check['column'] or 'table'}) failed.")
    semantic = corrupted_quality["semantic_checks"]
    lines += [f"- Missing source IDs: {len(semantic['missing_source_ids'])}.",
              f"- Short titles: {semantic['short_titles']}.",
              f"- Noise rows: {semantic['noise_rows']}.",
              f"- Stale rows: {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']}.",
              "", "The quality gate alerts on the corrupted data. It is indexed only in an isolated collection for this controlled measurement.",
              "Repair reconstructs the clean data from the preserved raw records and rebuilds a separate index.", ""]
    write_text(report_path, "\n".join(lines))


def _format(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)
