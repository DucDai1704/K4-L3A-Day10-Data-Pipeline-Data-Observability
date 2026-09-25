# Member Role Report — Đặng Quốc Hiệp

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đặng Quốc Hiệp             |
| MSSV               | [Điền MSSV]               |
| Khóa/Lớp         | K4 — L3A                   |
| Tên nhóm         | Nhóm Data Pipeline & Observability |
| Vai trò chính    | Data Foundation & Recovery Lead |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Ingestion Engine   | `src/ingestion/crossref.py` | Crossref REST API / Offline Snapshot | `data/raw/crossref_records.json` (24 bài) | Hoàn thành |
| Data Cleaning & Normalization | `src/ingestion/cleaning.py` | List `PaperRecord` raw | `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| Synthetic Corruption Suite | `src/ingestion/corruption.py` | Clean DataFrame | `data/clean/papers_clean_corrupted.csv`, `corruption_log.json` | Hoàn thành |
| Idempotent Repair Logic | `src/pipelines/corruption_flow.py` | Raw records preservation | `data/clean/papers_clean_repaired.csv` | Hoàn thành |

## 3. Kết quả theo vai trò
- Module Ingestion thu thập thành công 24 bài báo khoa học chuẩn, hỗ trợ cơ chế Offline Fallback an toàn phòng khi mất mạng hoặc API limit.
- Pipeline làm sạch khử hoàn toàn các thẻ JATS/HTML tag rác, tính toán chuẩn xác trường `age_days` phục vụ Freshness SLA và xây dựng trường `text_for_embedding` giàu ngữ cảnh.
- Bộ 6 kịch bản tiêm lỗi dữ liệu thực tế (drop records, blank summary, inject noise, truncate title, stale date, duplicate rows) chứng minh hiện tượng Silent Failure.

## 4. Giải thích phần kỹ thuật đã thực hiện
- **Vấn đề giải quyết:** Xử lý dữ liệu thô phi cấu trúc từ Crossref API, làm sạch các định dạng XML/JATS đặc thù học thuật, và đảm bảo khả năng phục hồi dữ liệu từ bản gốc nguyên vẹn.
- **Cách triển khai:** Áp dụng nguyên lý Data Lineage và Raw Preservation: bản raw data được ghi lại ngay khi nạp (`data/raw/crossref_records.json`) trước khi trải qua bất kỳ biến đổi nào. Khi xảy ra sự cố tiêm lỗi, toàn bộ clean dataset được tái tạo từ bản raw này một cách tất định.
