# Member Role Report — Nguyễn Thế Khang

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thế Khang           |
| MSSV               | [Điền MSSV]               |
| Khóa/Lớp         | K4 — L3A                   |
| Tên nhóm         | Nhóm Data Pipeline & Observability |
| Vai trò chính    | Observability & Evaluation Lead |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Data Quality Gate | `src/observability/quality.py` | DataFrames (clean, corrupted, repaired) | Great Expectations 1.x reports (`data/quality/`) | Hoàn thành |
| Freshness SLA Monitor | `src/observability/quality.py` | DataFrame cột `age_days` | `freshness_report.json` (SLA 180 ngày) | Hoàn thành |
| Benchmark Testset Generator | `src/evaluation/testset.py` | Clean DataFrame | 10 câu hỏi chuẩn hóa (`data/eval/test_set.json`) | Hoàn thành |
| Metrics Engine & Reports | `src/evaluation/metrics.py`, `reporting.py` | Answers vs Ground Truth | Báo cáo Markdown & Metrics JSON | Hoàn thành |
| Bonus B3 (Pytest Suite) | `tests/test_pipeline.py` | Toàn bộ pipeline modules | 7/7 bài kiểm thử tự động PASSED 100% | Hoàn thành |

## 3. Kết quả theo vai trò
- Thiết lập trạm kiểm soát dữ liệu sử dụng chuẩn mới **Great Expectations 1.x (Ephemeral Context)** với các kỳ vọng `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`.
- Giám sát độ tươi (Freshness Check): phát hiện bài báo cũ (`age_days > 180`), duy trì tỷ lệ stale chỉ **4.2%** (đạt chuẩn &le;25%).
- Khi tiêm dữ liệu lỗi, Quality Gate phát hiện 100% vi phạm và gióng cờ cảnh báo `FAILED`. Sau khi phục hồi, Quality Gate xác nhận `PASSED`.
- Bộ test Pytest chạy tự động kiểm thử toàn diện toàn bộ pipeline, đạt tỉ lệ hoàn hảo 7/7 test passed trong 30.08 giây.

## 4. Giải thích phần kỹ thuật đã thực hiện
- **Vấn đề giải quyết:** Xây dựng cơ chế Data Observability và bộ thước đo định lượng để sớm phát hiện suy giảm chất lượng dữ liệu, chặn đứng Silent Failure trước khi dữ liệu độc hại xâm nhập Vector Store.
- **Cách triển khai:** Kết hợp giữa Great Expectations 1.x Fluent API và logic kiểm định nghiệp vụ tùy biến, ép kiểu kết quả sang native Python bools để tương thích tuyệt đối với JSON serialization và Pytest assertions.
