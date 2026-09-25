# Báo Cáo Đối Chiếu 3 Trạng Thái — Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Chứng minh hiện tượng **Silent Failure** khi dữ liệu bẩn xâm nhập Vector Database, năng lực phát hiện của Data Quality Gate (Great Expectations 1.x), và khả năng tự hồi phục an toàn (**Idempotent Repair**) từ kho lưu trữ thô ban đầu (Raw Preservation).

---

## 1. Bảng So Sánh Chỉ Số Hiệu Năng RAG (3 Trạng Thái)

| Chỉ số kiểm thử | 1. Baseline (Sạch) | 2. Corrupted (Bị tiêm lỗi) | 3. Repaired (Sau phục hồi) | Biến thiên (B vs C) |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | `-40.0%` (Sụt giảm) |
| **Mean Token F1** | **1.0000** | **0.8506** | **1.0000** | `-0.1494` (Méo mó từ ngữ) |
| **LLM Judge Score** | **5.00 / 5.0** | **4.30 / 5.0** | **5.00 / 5.0** | `-0.70` (Sai lệch nội dung) |
| **Data Quality Gate** | **PASSED** | **FAILED (Báo động)** | **PASSED (Đã phục hồi)** | Phát hiện 100% dị thường |

---

## 2. Chi Tiết 6 Kịch Bản Tiêm Độc Tố Dữ Liệu (Synthetic Corruption Suite)

1. **Drop latest records (20%):** Bỏ rơi các bài báo mới nhất mô phỏng sự cố đứt gãy pipeline nạp dữ liệu.
2. **Blank summary:** Xóa trắng abstract của một số bài báo gây rỗng ngữ cảnh.
3. **Inject noise:** Chèn token rác vô nghĩa phá vỡ không gian vector ngữ nghĩa.
4. **Truncate title:** Rút ngắn tiêu đề < 8 ký tự làm sai lệch kết quả truy vấn theo tên.
5. **Stale date:** Lùi ngày xuất bản về quá khứ 365 ngày vi phạm Freshness SLA.
6. **Duplicate rows:** Nhân đôi bản ghi tạo ghost vectors làm loãng thứ hạng tìm kiếm.

---

## 3. Phân Tích Hiện Tượng "Silent Failure"

- Khi dữ liệu bị tiêm lỗi, hệ thống Retrieval và LLM **vẫn trả về kết quả mượt mà và không bắn ra lỗi runtime Exception**.
- Tuy nhiên, chỉ số **Retrieval Hit Rate** giảm mạnh từ `100.0%` xuống `60.0%`, và điểm **Judge Score** sụt từ `5.00` xuống `4.30`.
- Nếu không có trạm kiểm soát **Great Expectations 1.x**, lỗi này sẽ âm thầm lọt vào Production và gây ảo giác cho người dùng cuối.

---

## 4. Cơ Chế Phục Hồi Dữ Liệu An Toàn (Idempotent Repair)

- **Nguyên lý Idempotency:** Toàn bộ quá trình phục hồi được tái lập trực tiếp từ bản lưu trữ thô gốc `data/raw/crossref_records.json`.
- **Kết quả:** Sau khi phục hồi, toàn bộ chỉ số Retrieval Hit Rate đạt lại **100.0%**, Token F1 đạt **1.0000**, và Quality Gate chuyển trạng thái sang **PASSED**. Chạy lại bao nhiêu lần kết quả vẫn chuẩn xác như ban đầu mà không sinh tác dụng phụ.
