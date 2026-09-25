# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | DucDai1704     |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-09-25               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Thế Khang | 2A202602964 | Pipeline Lead & Integrator | `core/`, `phase1.py`, `corruption_flow.py`, toàn bộ modules |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline end-to-end cho cả Phase 1 (Baseline) và Phase 2 (Corruption & Repair). Baseline pipeline thu thập 24 bài báo từ Crossref snapshot, làm sạch và chuẩn hóa schema, nạp vào ChromaDB với MiniLM-L6-v2 embeddings, tạo bộ 10 câu hỏi benchmark, và đánh giá RAG quality đạt hit rate 1.0 và token F1 1.0. Quality Gate sử dụng Great Expectations 1.x phát hiện thành công khi data bị tiêm 6 dạng lỗi (drop records, blank summary, inject noise, truncate title, stale date, duplicate rows) — quality check chuyển từ PASS sang FAIL, freshness từ Fresh sang Stale. Corruption làm suy giảm metrics đáng kể: hit rate giảm 40% (1.0→0.6), token F1 giảm 43% (1.0→0.571). Repair idempotent từ raw backup phục hồi hoàn toàn 100% metrics về baseline. Blocker lớn nhất là Windows cp1252 encoding không hỗ trợ Unicode — đã xử lý bằng ASCII-only output.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (offline snapshot: data/raw/crossref_response.json)
    -> parse_crossref_payload(): extract DOI, title, abstract, authors, subject, dates
    -> PaperRecord dataclass -> save raw records (data/raw/crossref_records.json)
    -> build_clean_dataframe(): normalize text, calc age_days, build text_for_embedding
    -> save clean CSV/JSON (data/clean/)
    -> LocalEmbeddingIndex.build(): MiniLM-L6-v2 encode -> ChromaDB papers-baseline
    -> build_test_set(): 10 questions x 4 types -> data/eval/test_set.json
    -> evaluate_pipeline(): answer questions, calc hit rate + token F1 + judge
    -> run_data_quality_checks(): GX 1.x 6 expectations
    -> build_freshness_report(): age_days > 180 threshold
    -> generate_phase1_report() -> data/reports/phase1_report.md
    -> corrupt_clean_dataframe(): 6 corruption types
    -> re-index corrupted -> evaluate corrupted (metrics degrade)
    -> quality gate FAIL on corrupted data
    -> repair from raw records (idempotent)
    -> re-index repaired -> evaluate repaired (metrics restore)
    -> generate_corruption_report() -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / offline snapshot | Fetch with retry, parse JSON, strip HTML tags, extract DOI/title/abstract/authors/subject/dates | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Nguyễn Thế Khang |
| Cleaning          | List PaperRecord, run_date | Normalize whitespace, parse dates, calc age_days, build text_for_embedding, deduplicate by paper_id | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 records) | Nguyễn Thế Khang |
| Embedding/index   | Clean DataFrame | MiniLM-L6-v2 encode 384-dim vectors, ChromaDB PersistentClient, cosine similarity | `data/embeddings/papers_embeddings.json`, ChromaDB `papers-baseline` collection | Nguyễn Thế Khang |
| Evaluation        | Clean DataFrame, ChromaDB index | Build 10 questions (4 types), answer via QA, calc hit rate + token F1 + LLM judge | `data/eval/test_set.json`, `data/results/baseline_metrics.json` | Nguyễn Thế Khang |
| Observability     | Clean DataFrame, Settings | GX 1.x ephemeral: 6 expectations (row count, not null, unique, string length), freshness age_days > 180 | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Nguyễn Thế Khang |
| Corruption/repair | Clean DataFrame, raw records | 6 corruption types (seed=42), repair from raw backup, idempotent rebuild | `data/results/corruption_log.json`, corrupted/repaired metrics, `data/reports/corruption_report.md` | Nguyễn Thế Khang |
| Orchestration     | Settings | Phase 1: 9 steps chain; Phase 2: 11 steps chain | Exit code 0, all artifacts generated | Nguyễn Thế Khang |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | gemini (fallback heuristic judge khi không có API key) |
| `LLM_MODEL`                | gemini-2.5-flash |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Random seed (corruption)     | 42 |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ------------ | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-09-25 15:11 | `data/results/baseline_metrics.json`: hit_rate=1.0, token_f1=1.0 |
| Corruption flow   | Thành công | 2026-09-25 15:12 | `data/reports/corruption_report.md`: bảng 3 trạng thái đầy đủ |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (offline snapshot `data/raw/crossref_response.json`) |
| Query/filter                | `agentic retrieval augmented generation large language model`, filter: `from-pub-date:2026-03-29,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 (offline snapshot, không gọi API live) |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | 3 attempts với exponential backoff (2^attempt seconds), fallback đọc offline snapshot khi API fail |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | str | Có | DOI unique identifier | Skip record nếu thiếu |
| title | str | Có | Tiêu đề bài báo | Skip record nếu rỗng |
| summary | str | Có | Tóm tắt (stripped HTML) | Skip record nếu rỗng |
| authors | list[str] | Không | Danh sách tác giả | Để list rỗng |
| categories | list[str] | Không | Lĩnh vực phân loại | Để list rỗng |
| published | str (YYYY-MM-DD) | Có | Ngày xuất bản | Dùng run_date nếu parse lỗi |
| age_days | int | Computed | Tuổi paper = run_date - published | Tính từ published |
| text_for_embedding | str | Computed | Ghép Title+Authors+Published+Categories+Summary | Tạo từ các trường trên |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Strip HTML tags (`<jats:p>`, etc.) từ abstract | Validity | 24/24 | So sánh raw vs clean summary |
| Normalize whitespace (collapse multi-space) | Consistency | 24/24 | Check clean CSV |
| Deduplicate by paper_id (keep first) | Uniqueness | 0 (không có duplicate trong source) | `papers_clean.csv` có 24 rows = 24 unique DOIs |
| Filter records thiếu title hoặc summary | Completeness | 0 (source data đầy đủ) | Kiểm tra len(df) = len(records) |

**Cách tạo `text_for_embedding`, document ID và `age_days`:**

- `text_for_embedding` = `"Title: {title}\nAuthors: {authors_joined}\nPublished: {published}\nCategories: {categories_joined}\nSummary: {summary}"`. Format cố định giúp embedding model hiểu cấu trúc thông tin.
- Document ID = `"{paper_id}::{index}"` (DOI + running index), đảm bảo unique trong ChromaDB.
- `age_days = (run_date_naive - published_datetime).days` — số ngày từ lúc paper publish đến thời điểm chạy pipeline.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các `question_type`                    | summary, authors, date, categories (round-robin) |
| Ground-truth document ID                 | DOI paper tương ứng (1 paper per question) |
| Embedding model                          | sentence-transformers/all-MiniLM-L6-v2 (384 dimensions) |
| Vector store/collection                  | ChromaDB PersistentClient, 3 collections: papers-baseline, papers-corrupted, papers-repaired |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | gemini / gemini-2.5-flash (fallback heuristic judge khi không có API key) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (cố định, dùng chung cho cả 3 evaluations) |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**

Test set phải giữ nguyên để đảm bảo phép so sánh công bằng. Nếu mỗi trạng thái dùng test set khác, sự khác biệt metrics có thể do câu hỏi khác chứ không do chất lượng data. Cùng test set = cùng biến kiểm soát (controlled variable), chỉ thay đổi biến thí nghiệm (independent variable = chất lượng data). Đây là nguyên tắc thí nghiệm khoa học cơ bản.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 24 records |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có | 24 rows, 17 columns |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có | ChromaDB papers-baseline |
| Evaluation set           | `data/eval/test_set.json` | Có | 10 questions, 4 types |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Perfect scores |
| Quality/freshness        | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có | PASS, Fresh |
| Baseline report          | `data/reports/phase1_report.md` | Có | Markdown với metrics tables |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0000 | 10/10 câu hỏi retrieve đúng paper chứa ground truth (100% accuracy) |
| `mean_token_f1`      |     1.0000 | Token overlap hoàn hảo giữa answer và ground truth |
| `judge_accuracy`     |     1.0000 | 10/10 answers được judge đánh giá correct |
| `mean_judge_score`   |     5.00 | Score trung bình đạt maximum (5/5) |
| Ragas, nếu có        | Skipped | Không chạy vì RUN_RAGAS không được set (tốn thời gian và cần API key) |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| ExpectTableRowCountToBeBetween | Volume | 5-5000 rows | Pass (24 rows) | `data/quality/baseline_quality_report.json` |
| ExpectColumnValuesToNotBeNull (paper_id) | Completeness | 0 nulls | Pass | `data/quality/baseline_quality_report.json` |
| ExpectColumnValuesToNotBeNull (title) | Completeness | 0 nulls | Pass | `data/quality/baseline_quality_report.json` |
| ExpectColumnValuesToNotBeNull (text_for_embedding) | Completeness | 0 nulls | Pass | `data/quality/baseline_quality_report.json` |
| ExpectColumnValuesToBeUnique (paper_id) | Uniqueness | 0 duplicates | Pass | `data/quality/baseline_quality_report.json` |
| ExpectColumnValueLengthsToBeBetween (summary) | Validity | min 30 chars | Pass | `data/quality/baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (`papers_clean.json`) |
| Timestamp mới nhất       | 2026-07-22 |
| Timestamp cũ nhất        | 2026-03-28 |
| Ngưỡng freshness         | 180 ngày |
| Stale rows                 | 1 / 24 (4.17%) |
| Trạng thái baseline      | Fresh (stale ratio 4.17% < 25% threshold) |
| Lý do                     | 23/24 papers published trong vòng 180 ngày, chỉ 1 paper cũ hơn threshold |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop latest records | Xóa 20% papers newest by published date | 4 | Giảm row count | Mất papers → retrieval miss | Đọc lại raw records |
| Blank summary | Xóa summary thành empty string | 3 | summary length < 30 → FAIL | text_for_embedding mất ngữ nghĩa | Rebuild từ raw |
| Inject noise | Thêm 20 ký tự rác đầu/cuối summary | 3 | Summary bị nhiễu | Embedding vector bị skew nhẹ | Rebuild từ raw |
| Truncate title | Cắt title còn < 8 ký tự | 3 | Title mất thông tin | Exact match lookup fail | Rebuild từ raw |
| Stale date | Lùi published 365 ngày | 4 | age_days tăng → Freshness STALE | Freshness flag False | Rebuild từ raw |
| Duplicate rows | Nhân đôi rows | 3 | paper_id not unique → FAIL | Index có duplicate vectors | Rebuild từ raw, deduplicate |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 loại corruption với `corruption_type`, `description`, `affected_paper_ids`, `rows_affected`. Tổng cộng 20 rows bị ảnh hưởng trên nhiều dimensions.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy:**

Repair thực hiện idempotent: đọc lại `data/raw/crossref_records.json` (bản gốc chưa bao giờ bị sửa đổi), chạy lại `build_clean_dataframe()` để tái tạo clean data từ đầu. Không cố sửa/patch data hỏng, mà replace toàn bộ bằng data tái tạo từ raw source. Đây là nguyên tắc Raw Preservation / Data Lineage — raw snapshot là "bảo hiểm dữ liệu" đảm bảo reproducibility.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    0.6000 |   1.0000 |                  -0.4000 |           100% | 40% câu hỏi miss do papers bị xóa/corrupt |
| `mean_token_f1`        |   1.0000 |    0.5710 |   1.0000 |                  -0.4290 |           100% | Token overlap giảm vì answers sai paper |
| `judge_accuracy`       |   1.0000 |    0.6000 |   1.0000 |                  -0.4000 |           100% | 4/10 answers hoàn toàn sai |
| `mean_judge_score`     |   5.0000 |    3.2000 |   5.0000 |                  -1.8000 |           100% | Score giảm nhưng AI vẫn trả lời tự tin (Silent Failure) |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |            PASS → FAIL |      FAIL → PASS | GX 1.x phát hiện blank summary + duplicates |
| Freshness status         |    Fresh |     Stale |    Fresh |           Fresh → Stale |     Stale → Fresh | Stale dates đẩy tỷ lệ papers cũ vượt 25% threshold |

Kết luận nhân quả:

1. **[Drop 4 latest records + Blank 3 summaries]** → **[Quality gate FAIL: summary < 30 chars, paper_id not unique]** → **[Hit rate giảm 1.0 → 0.6, Token F1 giảm 1.0 → 0.571]**. Drop records trực tiếp xóa papers khỏi index khiến retrieval không tìm thấy. Blank summary làm mất ngữ nghĩa trong text_for_embedding.

2. **[Repair: đọc lại raw records → clean lại → rebuild index]** → **[Quality gate PASS: tất cả 6 expectations pass, Freshness Fresh]** → **[Hit rate phục hồi 0.6 → 1.0, Token F1 phục hồi 0.571 → 1.0]**. Idempotent repair hoàn toàn thành công nhờ raw preservation.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` khi chạy pipeline trên Windows PowerShell.
- **Nguyên nhân:** Windows console mặc định dùng cp1252 encoding, không hỗ trợ Unicode emoji/arrows. Python print() cố encode `→`, `✅`, `❌` → crash.
- **Cách xử lý:** Thay tất cả Unicode characters trong pipeline output bằng ASCII equivalents: `→` → `->`, `✅ PASS` → `PASS`, `❌ FAIL` → `FAIL`.
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` — exit code 0, output hiển thị đúng.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| LLM Judge dùng heuristic fallback (không có API key) | Judge accuracy dựa trên token F1 thay vì đánh giá ngữ nghĩa → có thể sai với paraphrase | Cấu hình API key → so sánh heuristic vs LLM judge scores trên cùng test set |
| Test set 10 câu hỏi (nhỏ) | Statistical significance thấp, 1 câu sai = 10% drop | Tăng lên 50+ câu hỏi với nhiều edge cases → đo standard deviation |
| Corruption seed cố định (42) | Kết quả deterministic nhưng chỉ test 1 scenario | Chạy với nhiều seeds → báo cáo mean ± std của metrics degradation |
| Không có automated CI/CD test | Regression có thể xảy ra khi sửa code | Thêm pytest cho từng module, chạy trong GitHub Actions |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
