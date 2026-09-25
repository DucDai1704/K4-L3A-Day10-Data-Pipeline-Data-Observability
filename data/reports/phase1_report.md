# Phase 1: Baseline pipeline

## Source

- Source: Bundled Crossref snapshot
- Raw records: 24
- Clean records: 24

## Evaluation

| Metric | Value |
|---|---:|
| samples | 10 |
| retrieval_hit_rate | 1.000 |
| mean_token_f1 | 1.000 |
| judge_accuracy | 1.000 |
| mean_judge_score | 5 |

Judge method: heuristic fallback for 10/10 answers.
Retrieval hit rate includes exact-title lookup in the QA layer.

## Data quality and freshness

- Quality gate: PASS
- GX expectations passed: 6/6
- Freshness SLA: PASS
- Stale rows: 1/24 (4.2%)
- Publication range: 2026-03-28 to 2026-07-22
