# Corruption and repair comparison

All three states use the same 10-question evaluation set and separate Chroma collections. Retrieval hit rate includes exact-title lookup in the QA layer.

| Measure | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| samples | 10 | 10 | 10 |
| retrieval_hit_rate | 1.000 | 0.300 | 1.000 |
| mean_token_f1 | 1.000 | 0.734 | 1.000 |
| judge_accuracy | 1.000 | 0.800 | 1.000 |
| mean_judge_score | 5 | 3.800 | 5 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | — | FAIL | PASS |

## Judge method

Heuristic fallback used for 10, 10, and 10 answers respectively. These scores are not independent LLM judgments when the mock provider is selected.

## Observed violations

- GX: ExpectColumnValuesToBeUnique (paper_id) failed.
- GX: ExpectColumnValueLengthsToBeBetween (summary) failed.
- Missing source IDs: 5.
- Short titles: 6.
- Noise rows: 3.
- Stale rows: 21/21.

The quality gate alerts on the corrupted data. It is indexed only in an isolated collection for this controlled measurement.
Repair reconstructs the clean data from the preserved raw records and rebuilds a separate index.
