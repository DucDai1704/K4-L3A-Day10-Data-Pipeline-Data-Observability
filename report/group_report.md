# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 — L3A                   |
| Tên nhóm         | K4-L3-DAY10-DataPipeline   |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đỗ Đức Đại | [MSSV] | Trưởng nhóm / Pipeline Integrator | `core/config.py`, `script/run_phase1.py`, `src/pipelines/phase1.py`, Dashboard, Self-healing |
| 2 | Đặng Quốc Hiệp | [MSSV] | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/clean/` |
| 3 | Nguyễn Việt Dũng | [MSSV] | RAG & Vector Index | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, ChromaDB |
| 4 | Nguyễn Thế Khang | [MSSV] | Observability & Evaluation | `src/observability/quality.py` (GX 1.x), `src/evaluation/testset.py`, reporting, tests |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn diện 100% yêu cầu kỹ thuật của bài Lab Day 10 bao gồm 7 Checkpoints chuẩn hóa (CP0 – CP6) và 3 tiêu chí Bonus nâng cao (Interactive Dashboard, Automated Self-Healing, Pytest Suite).

Hệ thống Data Pipeline được thiết kế đa tầng với khả năng xử lý bài báo khoa học từ Crossref REST API (có cơ chế Offline Fallback sang raw snapshot). Dữ liệu được chuẩn hóa schema (`age_days`, `text_for_embedding`), kiểm soát chất lượng qua trạm kiểm dịch **Great Expectations 1.x (Ephemeral Context)** và cơ chế **Freshness SLA** trước khi lập chỉ mục vector trên ChromaDB với mô hình `sentence-transformers/all-MiniLM-L6-v2`.

Trong Baseline Flow, hệ thống đạt hiệu năng tuyệt đối với **100% Retrieval Hit Rate**, **Token F1 1.0000** và **LLM Judge Score 5.00/5.0**. Khi kích hoạt Synthetic Corruption Suite (tiêm 6 kịch bản lỗi: drop records, blank summary, noise injection, truncate title, stale date, duplicate rows), hệ thống đã bộc lộ hiện tượng **Silent Failure**: retrieval hit rate sụt giảm xuống **60.0%**, Token F1 giảm xuống **0.8506** mà không gây runtime crash. Data Quality Gate đã phát hiện và chặn đứng 100% lỗi. Thông qua cơ chế **Idempotent Repair** từ kho lưu trữ thô ban đầu, toàn bộ chỉ số đã được phục hồi hoàn hảo về mức **100% Hit Rate** và **1.0000 F1**.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (hoặc Snapshot Offline data/raw/)
    ├── 1. Raw Ingestion & Preservation -> data/raw/crossref_records.json
    ├── 2. Transformation & Cleaning   -> data/clean/papers_clean.csv
    ├── 3. Data Observability Gate      -> Great Expectations 1.x & Freshness SLA
    ├── 4. Vector Embedding & Index     -> sentence-transformers + ChromaDB
    ├── 5. Evaluation Baseline RAG      -> Hit Rate, Token F1, LLM Judge Score
    ├── 6. Synthetic Corruption Suite   -> 6 kịch bản lỗi dữ liệu thực tế
    └── 7. Idempotent Repair & Compare  -> Tái sinh từ Raw & Báo cáo 3 trạng thái
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST / Offline JSON | Fetch, retry/backoff, parse JATS, bảo toàn raw | `data/raw/crossref_records.json` | Đặng Quốc Hiệp |
| Cleaning          | Raw records    | Chuẩn hóa chuỗi, regex JATS, tính `age_days`, deduplicate | `data/clean/papers_clean.csv` | Đặng Quốc Hiệp |
| Embedding/index   | Clean DataFrame| MiniLM-L6-v2, tạo text chunk, persist ChromaDB | `data/chroma/`, collection `papers-baseline` | Nguyễn Việt Dũng |
| Evaluation        | Clean data + Index | Sinh 10 câu hỏi test 4 khía cạnh, đo Hit rate & F1 | `data/eval/test_set.json`, `baseline_metrics.json` | Nguyễn Thế Khang |
| Observability     | Clean/Corrupted DF | GX 1.x Expectation Suite & Freshness SLA (&le;180 days) | `data/quality/*_quality_report.json` | Nguyễn Thế Khang |
| Corruption/repair | Clean DF / Raw records | Tiêm 6 loại lỗi, đo suy giảm, hồi phục idempotent | `corruption_log.json`, `repaired_metrics.json` | Đỗ Đức Đại & Đặng Quốc Hiệp |
| Orchestration     | Toàn bộ modules | Điều phối `run_phase1.py` và `run_corruption_flow.py` | `phase1_report.md`, `corruption_report.md` | Đỗ Đức Đại |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini`            |
| `LLM_MODEL`                | `gemini-2.5-flash`  |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 bài báo          |
| Retrieval `top_k`           | 4                   |
| Freshness threshold          | 180 ngày (ngưỡng stale &le; 25%) |

### Lệnh cài đặt

```bash
uv sync --no-install-project
```

### Lệnh chạy

1. Chạy Baseline Pipeline (CP3):
```bash
python script/run_phase1.py
```

2. Chạy Corruption Flow & Idempotent Repair (CP4 - CP5):
```bash
python script/run_corruption_flow.py
```

3. Tạo Dashboard HTML (Bonus B1):
```bash
python script/run_dashboard.py
```

4. Kiểm thử Automated Self-Healing (Bonus B2):
```bash
python script/run_auto_heal.py
```

5. Chạy bộ Pytest tự động (Bonus B3):
```bash
python -m pytest tests/test_pipeline.py -v
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | :---: | :---: | :--- |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-25 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (Exit code 0) | 2026-09-25 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |
| Pytest suite      | Thành công (7/7 passed)  | 2026-09-25 | `7 passed in 30.08s` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 |
| Số record nhận được    | 24 bài báo khoa học |
| Cơ chế retry/backoff      | 3 lần thử, exponential backoff (1s, 2s, 4s), tự động fallback sang `data/raw/crossref_response.json` |

### Quy tắc cleaning

1. **Khử thẻ JATS/HTML:** Sử dụng regex lọc sạch `<jats:p>`, `<jats:title>`, `<p>`, `<b>` khỏi Abstract và Title.
2. **Chuẩn hóa khoảng trắng:** Strip khoảng trắng thừa, thay thế newline kép thành newline đơn.
3. **Tính `age_days`:** Tính chênh lệch ngày giữa thời điểm ingest và ngày xuất bản (`published_date`).
4. **Tạo `text_for_embedding`:** Ghép có cấu trúc:
   ```text
   Title: <title>
   Authors: <author_1>, <author_2>
   Published Date: <YYYY-MM-DD>
   Summary: <abstract>
   ```
5. **Deduplication:** Khử trùng lặp dựa trên DOI (`paper_id`).

---

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi chuẩn hóa          |
| Các `question_type`                    | `summary` (4 câu), `authors` (2 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID                 | Gán trực tiếp `paper_id` từ clean dataset tương ứng |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Vector store/collection                  | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 4                             |
| LLM provider/model                       | `gemini-2.5-flash`            |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`     |

---

## 7. Kết quả baseline

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | **100.0%** | 10/10 câu hỏi tìm thấy đúng tài liệu đích trong Top-4 |
| `mean_token_f1`      | **1.0000** | Câu trả lời của AI trùng khớp hoàn hảo với ground-truth |
| `judge_accuracy`     | **100.0%** | Giám khảo Gemini công nhận 100% câu trả lời chính xác |
| `mean_judge_score`   | **5.00 / 5.0** | Đạt điểm tuyệt đối về độ chính xác ngữ nghĩa |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check Name | Quality Dimension | Ngưỡng kỳ vọng | Kết quả Baseline | Trạng thái |
| :--- | :--- | :--- | :---: | :---: |
| `ExpectTableRowCountToBeBetween` | Completeness | 5 <= N <= 5000 | 24 dòng | PASS |
| `ExpectColumnValuesToNotBeNull` | Validity | `paper_id`, `title`, `text_for_embedding` không rỗng | 0 giá trị null | PASS |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` (DOI) duy nhất | Không trùng | PASS |
| `ExpectColumnValueLengthsToBeBetween` | Completeness | Độ dài `summary` >= 30 ký tự | Đạt ngưỡng | PASS |

### Freshness SLA

- **Ngưỡng SLA:** Bài báo trong vòng 180 ngày, tỷ lệ bài cũ (`age_days > 180`) không vượt quá 25%.
- **Kết quả Baseline:** 1 bài cũ / 24 bài (tỷ lệ stale: **4.2%**).
- **Kết luận:** **FRESH (Đạt chuẩn SLA)**.

---

## 9. Corruption Scenarios và Phục Hồi (Idempotent Repair)

| Corruption | Cách tạo | Record bị tác động | Quality Signal kỳ vọng | Tác động thực tế đến RAG | Cách repair |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **1. Drop latest** | Xóa 20% bài mới nhất | 4 bài | Row count giảm | Mất tài liệu, Hit Rate giảm | Load lại từ raw preservation |
| **2. Blank summary** | Set `summary = ""` | 2 bài | Length violation | Mất context, câu trả lời rỗng | Re-parse từ raw snapshot |
| **3. Inject noise** | Chèn ký tự rác | 2 bài | Schema anomaly | Phá vỡ vector similarity | Làm sạch lại từ text gốc |
| **4. Truncate title** | Cắt `< 8` ký tự | 2 bài | Length check | Tìm kiếm theo tên bị trượt | Lấy lại title gốc từ raw |
| **5. Stale date** | Lùi ngày 365 ngày | 5 bài | Freshness Alert | Vi phạm Freshness SLA | Re-calculate `age_days` |
| **6. Duplicate rows** | Nhân đôi bản ghi | 2 bài | Unique violation | Trùng lặp vector, loãng Top-K | Deduplicate by `paper_id` |

---

## 10. Bảng So Sánh Đối Chiếu 3 Trạng Thái

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Thay đổi do lỗi (B vs C) | Mức độ phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`retrieval_hit_rate`** | **100.0%** | **60.0%** | **100.0%** | **-40.0%** (Sụt giảm nặng) | 100% phục hồi |
| **`mean_token_f1`** | **1.0000** | **0.8506** | **1.0000** | **-0.1494** (Sai lệch từ) | 100% phục hồi |
| **`judge_accuracy`** | **100.0%** | **80.0%** | **100.0%** | **-20.0%** (Mất điểm) | 100% phục hồi |
| **`mean_judge_score`** | **5.00 / 5.0** | **4.30 / 5.0** | **5.00 / 5.0** | **-0.70** (Giảm điểm) | 100% phục hồi |
| **Quality Gate Status** | **PASSED** | **FAILED** | **PASSED** | Báo động đỏ | Hoàn toàn sạch |
| **Freshness Status** | **FRESH** | **STALE ALERT** | **FRESH** | Cảnh báo vi phạm | Đạt SLA |

### Hai kết luận nhân quả thực nghiệm:
1. **Dữ liệu bẩn dẫn đến Silent Failure:** Khi các trường `summary` bị xóa rỗng và title bị cắt ngắn, hệ thống RAG vẫn chạy bình thường nhưng Hit Rate sụt từ 100% xuống 60%. Nếu không có Data Quality Gate, lỗi này sẽ âm thầm lọt vào Production.
2. **Tính tất định của Idempotent Repair:** Phục hồi từ Raw Preservation đảm bảo tái tạo 100% trạng thái dữ liệu nguyên bản, giúp đưa các chỉ số Hit Rate và F1 về lại mức hoàn hảo mà không sinh tác dụng phụ hay phụ thuộc vào sửa tay.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy trên Windows với đường dẫn tiếng Việt có dấu (`D:\AI_ThựcChiến\...`), lệnh `pip install -e .` bị lỗi `UnicodeDecodeError: 'cp1252' codec can't decode byte`. Đồng thời `write_json` gặp lỗi `TypeError: Object of type bool_ is not JSON serializable` do Great Expectations và Pandas trả về `np.bool_`.
- **Nguyên nhân:** Windows PowerShell mặc định dùng bảng mã CP1252 gây lỗi encoding, và các phương thức `.all()` / `.is_unique` của Pandas trả về kiểu dữ liệu NumPy scalar thay vì native Python bool.
- **Cách xử lý:** 
  1. Thiết lập file `.pth` trong `.venv` để mount trực tiếp `src/` vào `sys.path`.
  2. Bổ sung `_default_serializer` trong `src/core/utils.py` để serialize an toàn mọi kiểu dữ liệu NumPy/Pandas.
  3. Bổ sung ép kiểu `bool()` cho toàn bộ các quy tắc trong `src/observability/quality.py`.
- **Cách xác minh:** Toàn bộ 7 bài test trong `tests/test_pipeline.py` chạy thành công mượt mà (`7 passed in 30.08s`).

---

## 12. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Giao diện Dashboard HTML tương tác sinh thành công tại `data/reports/dashboard.html`.
- [x] Cơ chế Tự phục hồi tự động đã được kiểm chứng tại `data/results/self_healing_audit.json`.
- [x] Toàn bộ test suite Pytest đạt 100% (7/7 passed).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay commit.
