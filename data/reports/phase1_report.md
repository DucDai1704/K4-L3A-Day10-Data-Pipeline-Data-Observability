# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability

> **Thời gian khởi tạo:** 2026-09-25T07:59:08.553212+00:00  
> **Nguồn dữ liệu:** Crossref REST API  
> **Tổng số bản ghi xử lý:** 24 bài báo  

---

## 1. Trạm Kiểm Soát Dữ Liệu (Data Observability & Quality Gate)

Hệ thống tích hợp bộ quy tắc **Great Expectations 1.x** (Ephemeral Context) và cơ chế giám sát **Freshness SLA**:

| Tiêu chí kiểm định | Quy chuẩn | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :---: |
| **Row Count** | 5 <= N <= 5000 dòng | 24 dòng | PASS |
| **Non-null Columns** | `paper_id`, `title`, `text_for_embedding` | Không có giá trị rỗng | PASS |
| **Uniqueness** | Mỗi `paper_id` là duy nhất | Không trùng lặp | PASS |
| **Summary Length** | Tối thiểu 30 ký tự | Đạt ngưỡng tối thiểu | PASS |
| **Freshness SLA** | Tỷ lệ bài cũ (`age_days > 180`) <= 25% | Tỷ lệ stale: 4.2% | FRESH (Đạt SLA) |

**Kết luận Quality Gate:** `PASSED (Đạt tiêu chuẩn)`

---

## 2. Kết Quả Đo Lường Baseline RAG Benchmark

Đánh giá trên bộ test 10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`):

| Chỉ số đánh giá | Giá trị Baseline | Diễn giải nghiệp vụ |
| :--- | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | Tỷ lệ câu hỏi mà ChromaDB truy xuất đúng bài báo đích trong Top-4 |
| **Mean Token F1** | **1.0000** | Độ trùng khớp câu chữ giữa câu trả lời của AI và đáp án chuẩn |
| **LLM Judge Score** | **5.00 / 5.0** | Điểm số thẩm định ngữ nghĩa của mô hình giám khảo |
| **LLM Judge Accuracy** | **100.0%** | Tỷ lệ câu trả lời được giám khảo công nhận đúng thực chất |

---

## 3. Kiến Trúc Lưu Trữ & Vector Index
- **Mô hình nhúng:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Vector Database:** ChromaDB Persistent Client
- **Collection Name:** `papers-baseline`
