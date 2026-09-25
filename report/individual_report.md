# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thế Khang             |
| MSSV               | 2A202602964                    |
| Khóa/Lớp         | K4              |
| Tên nhóm         | DucDai1704     |
| Vai trò chính    | Pipeline Lead & Integrator                 |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-09-25              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Pipeline Orchestration (Phase 1) | `src/pipelines/phase1.py` — hàm `main()` | Settings, raw records | `baseline_metrics.json`, `phase1_report.md`, tất cả artifacts Phase 1 | Hoàn thành |
| Pipeline Orchestration (Phase 2) | `src/pipelines/corruption_flow.py` — hàm `main()` | Clean data, baseline metrics | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| Core Configuration | `src/core/config.py` — `Paths`, `Settings`, `load_settings()` | `.env`, project structure | Settings object cho toàn bộ pipeline | Đã có sẵn (starter code) |
| Raw Ingestion | `src/ingestion/crossref.py` — `fetch_source_records()`, `parse_crossref_payload()`, `load_raw_records()` | Crossref API / offline snapshot | `crossref_records.json`, list `PaperRecord` | Hoàn thành |
| Data Cleaning | `src/ingestion/cleaning.py` — `build_clean_dataframe()` | List `PaperRecord`, run_date | `papers_clean.csv`, `papers_clean.json` (24 records) | Hoàn thành |
| Data Corruption | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()` | Clean DataFrame | Corrupted DataFrame, `corruption_log.json` (6 loại lỗi) | Hoàn thành |
| Evaluation Test Set | `src/evaluation/testset.py` — `build_test_set()` | Clean DataFrame | `test_set.json` (10 câu hỏi) | Hoàn thành |
| Quality Gate (GX 1.x) | `src/observability/quality.py` — `run_data_quality_checks()`, `build_freshness_report()` | DataFrame, Settings | Quality reports, freshness report | Hoàn thành |
| Reporting | `src/observability/reporting.py` — `generate_phase1_report()`, `generate_corruption_report()` | Metrics, quality, freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp end-to-end toàn bộ pipeline | Tất cả modules | Pipeline chạy thành công từ đầu đến cuối, exit code 0 |
| Debug encoding Windows cp1252 | Pipeline output | Sửa Unicode characters thành ASCII cho tương thích Windows console |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement Crossref parser + offline fallback | `src/ingestion/crossref.py` | 24 papers parsed từ snapshot | `python script/run_phase1.py` — Step 1 |
| Implement cleaning pipeline | `src/ingestion/cleaning.py` | 24 clean records với `text_for_embedding` | `data/clean/papers_clean.csv` |
| Implement GX 1.x Quality Gate | `src/observability/quality.py` | 6 expectations, baseline PASS, corrupted FAIL | `data/quality/baseline_quality_report.json` |
| Implement test set builder | `src/evaluation/testset.py` | 10 câu hỏi, 4 loại | `data/eval/test_set.json` |
| Implement 6 corruption types | `src/ingestion/corruption.py` | 6 loại lỗi, tổng 20 rows affected | `data/results/corruption_log.json` |
| Orchestrate Phase 1 + Phase 2 | `src/pipelines/phase1.py`, `corruption_flow.py` | Cả 2 pipeline exit code 0 | `python script/run_phase1.py` và `python script/run_corruption_flow.py` |
| Generate markdown reports | `src/observability/reporting.py` | 2 reports với metrics tables | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |

Artifact chính: Bảng so sánh 3 trạng thái trong `data/reports/corruption_report.md` chứng minh corruption làm suy giảm metrics (hit rate 1.0 → 0.6) và repair phục hồi hoàn toàn (hit rate 0.6 → 1.0).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây dựng một Data Pipeline end-to-end cho hệ thống RAG, bao gồm: thu thập dữ liệu từ Crossref API, làm sạch và chuẩn hóa, nạp vào ChromaDB vector store, đánh giá chất lượng RAG, và đặc biệt là thiết lập hệ thống Data Observability để phát hiện Silent Failure — khi AI trả lời sai nhưng không báo lỗi.

### Cách triển khai

1. **Crossref Ingestion (`crossref.py`):** Parse payload từ Crossref API, strip HTML tags (e.g., `<jats:p>`), chuẩn hóa date-parts thành ISO format. Có cơ chế offline fallback đọc từ `data/raw/crossref_response.json` khi API không khả dụng.

2. **Cleaning (`cleaning.py`):** Normalize whitespace, tính `age_days = (run_date - published).days`, tạo `text_for_embedding` bằng cách ghép Title/Authors/Published/Categories/Summary. Deduplicate theo `paper_id`.

3. **Quality Gate (`quality.py`):** Sử dụng GX 1.x ephemeral context (`gx.get_context(mode="ephemeral")`), áp dụng 6 expectations: row count 5-5000, not-null cho `paper_id`/`title`/`text_for_embedding`, unique `paper_id`, summary length >= 30. Freshness monitoring: flag `is_fresh=False` khi stale_ratio > 25%.

4. **Corruption (`corruption.py`):** Mô phỏng 6 lỗi thực tế với seed=42 để reproducible: drop 20% newest, blank 15% summaries, inject noise chars, truncate titles, stale dates -365 days, duplicate 15% rows. Rebuild `text_for_embedding` sau corruption.

5. **Pipeline Orchestration:** Phase 1 chains: fetch → clean → save → index → test_set → evaluate → quality → freshness → report. Phase 2 chains: load baseline → corrupt → evaluate corrupted → quality check (detect FAIL) → repair from raw → evaluate repaired → comparison report.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref API response hoặc offline snapshot `data/raw/crossref_response.json` |
| Output                         | Metrics JSON (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), Markdown reports, quality reports |
| Module phụ thuộc             | `core.config` (paths, settings), `core.utils` (I/O helpers) |
| Module sử dụng output        | `retrieval.index` (ChromaDB), `evaluation.metrics` (scoring), `retrieval.qa` (answering) |
| Điều kiện lỗi cần xử lý | API timeout/429 → fallback offline; Windows cp1252 encoding → ASCII-only prints; GX 1.x API changes → remove `to_dict()` call |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai pipeline exit code 0, baseline metrics cao, corrupted metrics sụt giảm, repaired metrics phục hồi.
- **Kết quả thực tế:** Baseline hit_rate=1.0, corrupted hit_rate=0.6, repaired hit_rate=1.0. Quality gate: baseline PASS, corrupted FAIL, repaired PASS.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi implement Quality Gate, cần chọn giữa GX 1.x ephemeral context và GX file-based context (tạo thư mục `gx/` với nhiều config files).
- **Các phương án đã cân nhắc:**
  1. File-based context: `gx.get_context(project_root_dir=...)` — tạo cấu trúc thư mục GX chuẩn.
  2. Ephemeral context: `gx.get_context(mode="ephemeral")` — chạy hoàn toàn trên RAM, không tạo file config.
- **Phương án đã chọn:** Ephemeral context.
- **Lý do:** Ephemeral mode nhanh hơn, không tạo file rác trong project, phù hợp cho pipeline CI/CD. Bài lab chỉ cần validate DataFrame tạm thời, không cần lưu trữ lịch sử validation. Trade-off: mất history, nhưng kết quả được lưu riêng vào `data/quality/`.
- **Bằng chứng quyết định phù hợp:** Quality gate hoạt động chính xác — PASS cho baseline (24 records clean), FAIL cho corrupted data (phát hiện blank summary và duplicates).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 2: character maps to <undefined>`
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py` trên Windows PowerShell.
- **Nguyên nhân gốc:** Windows console mặc định dùng cp1252 encoding, không hỗ trợ Unicode characters như `→`, `✅`, `❌`, `⚠️`. Python print() gặp lỗi khi cố encode các ký tự này.
- **Cách xử lý:** Thay toàn bộ Unicode symbols trong print statements bằng ASCII equivalents: `→` → `->`, `✅` → `PASS`, `❌` → `FAIL`, `⚠️` → `(warning)`.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` — exit code 0, output hiển thị đúng trên Windows console.
- **Điều học được:** Khi phát triển cross-platform, tránh sử dụng Unicode emoji/symbols trong console output. Nên dùng ASCII hoặc set `sys.stdout.reconfigure(encoding='utf-8')`.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API trả về JSON payload chứa metadata bài báo → `parse_crossref_payload()` extract DOI, title, abstract, authors, subject, dates → tạo `PaperRecord` dataclass → `build_clean_dataframe()` normalize text, tính `age_days`, tạo `text_for_embedding` (ghép Title/Authors/Published/Categories/Summary) → `LocalEmbeddingIndex.build()` dùng MiniLM-L6-v2 encode text thành 384-dim vectors → lưu vào ChromaDB collection `papers-baseline` với cosine similarity.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `build_test_set()` tạo 10 câu hỏi từ clean data, mỗi câu gắn với `ground_truth_doc_ids` (paper DOI). Khi evaluate, hệ thống hỏi câu hỏi → retrieve top-k docs → so sánh `retrieved_doc_ids` với `ground_truth_doc_ids` (tính hit rate). So sánh answer với ground_truth bằng token F1 và LLM Judge (fallback heuristic khi không có API key).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (GX 1.x) kiểm tra cấu trúc dữ liệu: row count, null values, uniqueness, string length — thuộc về data validity/completeness. Freshness monitoring kiểm tra thời gian: đo `age_days` của từng paper, tính tỷ lệ bài cũ (>180 ngày), flag `is_fresh=False` nếu >25% stale — thuộc về data timeliness. Cả hai cùng là thành phần của Data Observability nhưng đo các chiều khác nhau.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để phép so sánh có ý nghĩa thống kê. Nếu mỗi trạng thái dùng test set khác nhau, sự khác biệt metrics có thể do câu hỏi khác chứ không phải do chất lượng dữ liệu. Cùng test set = cùng biến kiểm soát, chỉ thay đổi biến thí nghiệm (chất lượng data).

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi: (a) `repaired_metrics.json` có hit_rate và token_f1 bằng hoặc gần bằng baseline; (b) Quality gate PASS trên repaired data (`repaired_quality_report.json`); (c) Freshness `is_fresh=True`. Cụ thể: repaired hit_rate=1.0 (= baseline 1.0), repaired token_f1=1.0 (= baseline 1.0), quality PASS, freshness OK.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.0000 |      0.6000 |     1.0000 | Corruption làm mất 40% hit rate do drop records và blank summaries khiến vector search không tìm đúng paper |
| `mean_token_f1`      |     1.0000 |      0.5710 |     1.0000 | Token overlap giảm mạnh vì answers sai paper hoặc trả về noise text |
| `judge_accuracy`     |     1.0000 |      0.6000 |     1.0000 | 4/10 câu trả lời sai hoàn toàn trên corrupted data |
| `mean_judge_score`   |     5.00 |      3.20 |     5.00 | Score trung bình giảm từ perfect (5) xuống 3.2 — vẫn trôi chảy nhưng sai nội dung (Silent Failure) |
| Quality checks         |     PASS |      FAIL |     PASS | GX 1.x phát hiện corruption: blank summaries vi phạm length check, duplicates vi phạm uniqueness |
| Freshness status       |     Fresh |      Stale |     Fresh | Stale dates corruption đẩy tỷ lệ bài cũ vượt ngưỡng 25% |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**
   Drop 4 latest records + blank 3 summaries + inject noise + truncate titles + stale 4 dates + duplicate 3 rows → Quality gate FAIL (blank summary < 30 chars, duplicated paper_id) + Freshness STALE → Hit rate giảm 1.0 → 0.6, Token F1 giảm 1.0 → 0.571.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**
   Đọc lại `crossref_records.json` gốc → `build_clean_dataframe()` tái tạo data sạch → Quality gate PASS + Freshness Fresh → Hit rate phục hồi 0.6 → 1.0, Token F1 phục hồi 0.571 → 1.0. Repair hoàn toàn idempotent.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Drop latest records (4 papers bị xóa) ảnh hưởng rõ nhất vì các câu hỏi trong test set tham chiếu đến paper cụ thể bằng DOI. Khi paper bị xóa khỏi index, retrieval không thể tìm thấy đúng document → hit rate giảm trực tiếp. Blank summary cũng ảnh hưởng đáng kể vì `text_for_embedding` mất thông tin ngữ nghĩa → cosine similarity giảm → retrieve sai paper.

**Kết quả nào khác với kỳ vọng ban đầu?**

Kỳ vọng inject noise sẽ ảnh hưởng mạnh hơn, nhưng thực tế MiniLM embedding khá robust với noise characters — vector similarity vẫn cao đủ để retrieve đúng paper nếu summary gốc vẫn còn (noise chỉ thêm vào đầu/cuối). Ngược lại, drop records ảnh hưởng tuyệt đối vì không có data thì không thể retrieve.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw data preservation (lineage) là bảo hiểm quan trọng nhất. Nhờ lưu `crossref_records.json` nguyên gốc, repair chỉ cần đọc lại file này và chạy lại cleaning — hoàn toàn idempotent, không phụ thuộc API bên ngoài.

2. **Data quality/observability:** Great Expectations 1.x với ephemeral context là cách tiếp cận nhẹ nhưng hiệu quả để dựng Quality Gate. 6 expectations đơn giản (row count, not null, unique, string length) đã đủ phát hiện corruption trước khi data vào vector store — ngăn Silent Failure.

3. **Ảnh hưởng của data đến RAG agent:** AI agent không biết data bị lỗi — nó vẫn trả lời tự tin nhưng sai (Silent Failure). Metrics sụt giảm 40% chỉ vì data corruption, không phải do model yếu. Điều này chứng minh "Garbage In → Garbage Out" và tầm quan trọng của Data Observability trong production AI.

### Nếu có thêm thời gian

Tích hợp LLM Judge thực (với API key) thay vì fallback heuristic để đánh giá answer quality chính xác hơn. Cách đo: so sánh judge_accuracy và mean_judge_score giữa heuristic fallback và LLM-based judge trên cùng test set, kỳ vọng LLM judge phân biệt tốt hơn giữa partially correct và fully correct answers.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thế Khang
**Ngày xác nhận:** 2026-09-25
