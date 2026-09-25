# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

- Lớp: K4-L3-DAY10
- Ngày chạy kiểm chứng: 2026-09-25
- Tên nhóm, repository nộp bài: **nhóm cần điền**.
- Thành viên, MSSV, email, vai trò và báo cáo cá nhân: **nhóm cần điền trong `docs/TEAM.md` và các báo cáo cá nhân**.

## 2. Tóm tắt kết quả

Pipeline offline đã xử lý 24 bản ghi Crossref từ snapshot gốc, chuẩn hóa văn bản và ngày xuất bản, rồi tạo chỉ mục ChromaDB bằng MiniLM. Bộ đánh giá cố định gồm 10 câu hỏi thuộc bốn loại summary, authors, date và categories. Trên baseline, quality gate GX đạt 6/6 expectation; freshness đạt với 1/24 bản ghi quá 180 ngày. Hit rate và token F1 đều bằng 1.000. Bộ corruption tiêm đủ sáu lỗi: bỏ 5 bài mới, xóa 3 tóm tắt, chèn nhiễu vào 3 tóm tắt, cắt ngắn 4 tiêu đề, lùi ngày 19 bản ghi và nhân đôi 2 dòng. Gate phát hiện dữ liệu lỗi, trong đó GX báo lỗi độ dài tóm tắt và tính duy nhất. Hit rate giảm xuống 0.300 và token F1 xuống 0.734. Repair dựng lại dữ liệu từ raw records, cho quality gate PASS và khôi phục cả hai chỉ số về 1.000. Lần chạy lại tạo cùng dữ liệu, metrics và báo cáo. Kết quả judge trong lần chạy này là heuristic fallback vì dùng `LLM_PROVIDER=mock`; chưa có kiểm chứng bởi LLM độc lập. Hit rate cũng bao gồm đường tra cứu tiêu đề chính xác của QA.

## 3. Kiến trúc và luồng dữ liệu

`Crossref snapshot -> raw records -> cleaning -> GX/freshness gate -> MiniLM/Chroma -> test set/evaluation -> controlled corruption -> isolated index/evaluation -> raw-based repair -> comparison report`.

- Ingestion: `src/ingestion/crossref.py`, bảo toàn raw response và raw records.
- Cleaning: `src/ingestion/cleaning.py`, tạo `paper_id`, `age_days`, `summary_chars`, `text_for_embedding`.
- Retrieval: `src/retrieval/`, ba collection độc lập `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- Evaluation: `src/evaluation/`, cùng test set cho cả ba trạng thái.
- Observability: `src/observability/`, GX 1.x, freshness và báo cáo.
- Điều phối: `src/pipelines/`, quality gate baseline chặn index khi FAIL; corrupted collection chỉ để đo tác động.

## 4. Cách tái hiện kết quả

Cần Python 3.11–3.13 và cài dependencies bằng `uv sync` hoặc `python -m pip install -e .`. Mô hình MiniLM cần tải một lần trước khi chạy offline. Chạy tại thư mục gốc:

```bash
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock .venv/bin/python script/run_phase1.py
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock .venv/bin/python script/run_corruption_flow.py
```

Cấu hình lần đo: snapshot 24 bài, MiniLM `sentence-transformers/all-MiniLM-L6-v2`, `top_k=4`, freshness threshold 180 ngày, `LLM_PROVIDER=mock`. Không dùng API key trong báo cáo.

## 5. Ingestion, cleaning và data contract

Snapshot tại `data/raw/crossref_response.json` được parse thành `data/raw/crossref_records.json`. Mỗi bản ghi có DOI làm `paper_id`, title, summary, authors, categories, published, updated và URL. Cleaning bỏ thẻ JATS/XML và khoảng trắng thừa, chuẩn hóa ngày ISO, khử trùng lặp theo DOI, tính `age_days`, rồi ghép 5 phần Title/Authors/Published/Categories/Summary thành `text_for_embedding`. Dữ liệu sạch có 24 dòng tại `data/clean/papers_clean.csv` và `.json`.

## 6. Evaluation setup

`data/eval/test_set.json` chứa 10 câu hỏi cố định: 3 summary, 3 authors, 2 date, 2 categories. Ground truth và DOI đích được lưu cùng mỗi câu. Cả ba trạng thái dùng đúng file này. Token F1 và retrieval hit rate được tính trực tiếp; judge dùng heuristic fallback trong lần chạy mock, thể hiện qua `fallback_judge_count=10` ở mỗi metrics artifact. QA ưu tiên tra cứu tiêu đề chính xác khi câu hỏi chứa tiêu đề trong dấu nháy.

## 7. Kết quả baseline

Các artifact chính: `data/clean/papers_clean.csv`, `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`, `data/results/baseline_metrics.json`, `data/quality/baseline_quality_report.json`, `data/reports/phase1_report.md`. Baseline: hit rate 1.000, token F1 1.000, judge accuracy 1.000, mean judge score 5.000 (heuristic).

## 8. Data quality và freshness

GX 1.x chạy 6 expectations: row count 5–5000, non-null cho `paper_id`, `title`, `text_for_embedding`, uniqueness cho `paper_id`, và summary dài ít nhất 30 ký tự. Gate bổ sung kiểm tra DOI thiếu so với raw source, tiêu đề ngắn, chuỗi nhiễu và freshness. Baseline PASS, 1/24 bài stale (4.2%). Corrupted FAIL: duplicate DOI, summary ngắn, 5 DOI thiếu, 6 dòng có tiêu đề ngắn (gồm bản sao), 3 dòng nhiễu và 21/21 dòng stale. Repaired PASS.

## 9. Corruption scenarios và repair

Chi tiết DOI và số dòng của từng kịch bản nằm tại `data/results/corruption_log.json`. Corrupted dataset được ghi riêng vào `data/clean/papers_clean_corrupted.*` và collection `papers-corrupted`. Repair chỉ đọc `data/raw/crossref_records.json`, chạy lại cleaning rồi index sang `papers-repaired`; không sửa thủ công dữ liệu lỗi. Dataset repaired bằng dataset baseline, metrics repaired bằng metrics baseline. Một lần chạy lại corruption flow giữ nguyên hash của cleaned repaired JSON, repaired metrics và comparison report.

## 10. So sánh baseline, corrupted và repaired

| Chỉ số | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1.000 | 0.300 | 1.000 |
| Mean token F1 | 1.000 | 0.734 | 1.000 |
| Judge accuracy (heuristic) | 1.000 | 0.800 | 1.000 |
| Mean judge score (heuristic) | 5.000 | 3.800 | 5.000 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |

Nguồn số liệu: các file `data/results/*_metrics.json` và `data/quality/*_quality_report.json`. Báo cáo tự sinh: `data/reports/corruption_report.md`.

## 11. Vấn đề tích hợp quan trọng

Entrypoint trong `script/` thêm `src/` vào import path để chạy trực tiếp bằng lệnh README. Mô hình MiniLM dùng cache local trước; nếu cache chưa có, lần đầu sẽ tải qua Hugging Face. Manifest lưu đường dẫn Chroma tương đối để có thể chuyển workspace.

## 12. Giới hạn và hướng cải thiện

Snapshot chỉ có 24 bài, vì vậy các điểm số chưa chứng minh chất lượng trên dữ liệu Crossref live. Judge mock không phải đánh giá LLM độc lập. Cơ chế exact-title lookup làm hit rate cao hơn phép đo vector search thuần. Cần chạy với provider thật và tập câu hỏi lớn hơn nếu dùng kết quả cho quyết định production.

## 13. Checklist trước khi nộp

- [x] Baseline và corruption flow chạy thành công từ snapshot.
- [x] Artifact dữ liệu, metrics, quality và báo cáo được sinh từ pipeline.
- [x] Repair idempotent trên lần chạy kiểm chứng.
- [ ] Điền tên nhóm, repository, thành viên, MSSV và phân công thực tế.
- [ ] Mỗi thành viên viết báo cáo cá nhân và tự nộp link repo lên LMS.
