# Báo cáo công việc — ai-dnn

**Ngày:** 2026-09-25

**Phạm vi:** bản triển khai trên `main`, commit `ce0fead` (`Implement data observability pipeline and verified artifacts`).
**Nhánh tham chiếu đã kiểm tra:** `origin/feat/gun` tại `7b32e2c` sau khi fetch từ `origin`.

Báo cáo này ghi nhận phần việc trong commit `ce0fead`. Các kết quả của `origin/feat/gun` được nêu riêng để tránh gán số liệu hoặc quyền sở hữu của nhánh đó cho `ai-dnn`.

## 1. Công việc đã thực hiện

| Khối | Thay đổi trong `ce0fead` | Bằng chứng |
|---|---|---|
| Ingestion | Parse Crossref JSON, bỏ thẻ JATS/HTML, lưu raw response và records; dùng snapshot offline, retry khi gọi API live | `src/ingestion/crossref.py`, `data/raw/` |
| Cleaning | Chuẩn hóa text và ngày, khử DOI trùng, tính `age_days`, tạo `text_for_embedding` gồm 5 phần | `src/ingestion/cleaning.py`, `data/clean/papers_clean.csv` |
| Quality gate | GX 1.x với 6 expectations; thêm kiểm tra DOI thiếu, tiêu đề ngắn, nhiễu và freshness SLA | `src/observability/quality.py`, `data/quality/*_quality_report.json` |
| Retrieval và evaluation | MiniLM, ChromaDB collections riêng; 10 câu hỏi thuộc 4 loại; ghi hit rate, token F1 và provenance của heuristic judge | `src/retrieval/`, `src/evaluation/`, `data/eval/test_set.json`, `data/results/*_metrics.json` |
| Corruption và repair | Tiêm 6 loại lỗi vào bản sao, đánh giá trong collection cô lập, dựng lại dữ liệu từ raw records | `src/ingestion/corruption.py`, `src/pipelines/`, `data/results/corruption_log.json` |
| Tích hợp và báo cáo | Hai entrypoint chạy trực tiếp, báo cáo baseline/3 trạng thái, hướng dẫn offline và báo cáo nhóm theo artifacts | `script/`, `data/reports/`, `README.md`, `report/group_report.md` |

Các quyết định chính: baseline chỉ được index khi quality gate PASS; corrupted collection chỉ dùng cho phép đo; repair đọc lại raw records thay vì sửa tay; manifest Chroma dùng đường dẫn tương đối. Index được upsert để chạy lại không sinh thêm segment directory. Lần đầu MiniLM cần tải mô hình, các lần sau dùng cache local.

## 2. Kết quả kiểm chứng trên `main`

Đã chạy hai entrypoint với snapshot 24 bản ghi và `LLM_PROVIDER=mock`, `HF_HUB_OFFLINE=1` sau khi tải MiniLM lần đầu:

```bash
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock .venv/bin/python script/run_phase1.py
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock .venv/bin/python script/run_corruption_flow.py
```

| Chỉ số / tín hiệu | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1.000 | 0.300 | 1.000 |
| Mean token F1 | 1.000 | 0.734 | 1.000 |
| Judge accuracy (heuristic) | 1.000 | 0.800 | 1.000 |
| Mean judge score (heuristic) | 5.000 | 3.800 | 5.000 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |

Nguồn: `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, các quality reports và `data/reports/corruption_report.md` trên `main`. Baseline có 24 dòng, 1 dòng stale. Corruption bỏ 5 bài mới, xóa 3 summary, chèn nhiễu vào 3 summary, cắt 4 title, lùi ngày 19 bản ghi và nhân đôi 2 dòng. Quality gate phát hiện bản ghi thiếu, summary ngắn, DOI trùng, tiêu đề ngắn, nhiễu và 21/21 dòng stale. Dataset repaired bằng dataset baseline; metrics repaired bằng metrics baseline. Một lần chạy lại giữ nguyên hash của repaired JSON, repaired metrics và comparison report; số thư mục segment Chroma không tăng. `git diff --check` và `compileall` đã qua.

`fallback_judge_count=10` ở cả ba trạng thái: điểm judge của lần đo này là heuristic fallback, không phải đánh giá độc lập của LLM. QA có đường tra cứu tiêu đề chính xác nên hit rate không phải chỉ số vector search thuần.

## 3. Kiểm tra `origin/feat/gun`

`origin/feat/gun` là một hướng triển khai riêng: tính từ merge base `77a0fda`, nhánh có 4 commit riêng còn `main` có commit `ce0fead`. Nhánh này có dashboard (`src/observability/dashboard.py`), auto-healing (`src/pipelines/auto_heal.py`), pytest (`tests/test_pipeline.py`), roster và 4 role reports. Không merge nhánh trong phạm vi báo cáo này.

Artifacts trên nhánh ghi baseline hit rate/F1 là 1.000/1.000, corrupted là 0.600/0.851, repaired là 1.000/1.000. **Không so sánh trực tiếp mức suy giảm với `main`:** hai `data/eval/test_set.json` đều có 3 summary, 3 authors, 2 date, 2 categories nhưng không trùng câu hỏi nào hoặc DOI đích nào; `corruption_log.json` cũng áp dụng số lượng/bản ghi lỗi khác nhau. Hai nhánh cần thống nhất test set và corruption protocol trước khi so hiệu năng hoặc gộp báo cáo.

Hai điểm cần sửa trong `report/group_report.md` của feature branch trước khi nộp:

1. Mục Evaluation setup ghi **4 summary, 2 authors**, còn artifact `data/eval/test_set.json` có **3 summary, 3 authors**.
2. Bảng corruption ghi **5 stale-date records**, còn `data/results/corruption_log.json` ghi **3**.

`docs/TEAM.md` và bốn role reports trên feature branch có tên và vai trò của Đỗ Đức Đại, Đặng Quốc Hiệp, Nguyễn Việt Dũng và Nguyễn Thế Khang; MSSV/email vẫn là placeholder. Bốn commit riêng trên feature branch đều ghi tác giả `QuocHiep123`, nên lịch sử đó chưa tự chứng minh cả bốn người có commit cá nhân. Đây là ghi nhận về commit metadata, không phải kết luận về công sức của từng người.

## 4. Giới hạn và việc còn lại

- Phép đo trên `main` dùng snapshot offline 24 bài và mock judge; cần bộ câu hỏi lớn hơn và LLM judge thật để đánh giá ngoài lab.
- Nhánh `origin/feat/gun` chưa được chạy lại trong lần kiểm tra này; nhận xét về số liệu của nhánh dựa trên artifacts đã commit.
- Báo cáo nhóm và báo cáo cá nhân cần được chủ sở hữu xác nhận, bổ sung MSSV/email và phần đóng góp thực tế. Không gán commit `ai-dnn` cho các thành viên được liệt kê trên feature branch.
