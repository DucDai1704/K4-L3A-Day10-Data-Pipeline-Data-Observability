# Member Role Report — Đỗ Đức Đại

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đỗ Đức Đại                 |
| MSSV               | [Điền MSSV]               |
| Khóa/Lớp         | K4 — L3A                   |
| Tên nhóm         | Nhóm Data Pipeline & Observability |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator & Architecture Lead |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Cấu hình & Utility | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env`, tham số CLI | Schema cấu hình Settings & Paths | Hoàn thành |
| Baseline Orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw data, clean engine, vector index, GX quality gate | `data/reports/phase1_report.md`, `baseline_metrics.json` | Hoàn thành |
| Corruption Orchestration | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean dataset, corruption suite, raw preservation | `data/reports/corruption_report.md`, 3-state comparison | Hoàn thành |
| Bonus B1 (Dashboard) | `src/observability/dashboard.py`, `script/run_dashboard.py` | Metrics 3 trạng thái, quality reports | `data/reports/dashboard.html` | Hoàn thành |
| Bonus B2 (Self-Healing) | `src/pipelines/auto_heal.py`, `script/run_auto_heal.py` | Batch dữ liệu bẩn / bất thường | `data/results/self_healing_audit.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính
- Thiết lập môi trường ảo Python 3.12 với file mount `.pth` để tương thích Windows encoding (tránh lỗi CP1252 khi đường dẫn có tiếng Việt có dấu).
- Thêm custom JSON serializer trong `write_json` để tuần tự hóa an toàn các kiểu dữ liệu NumPy/Pandas bools.

## 3. Kết quả theo vai trò
- Báo cáo Pha 1 hoàn chỉnh với Hit Rate 100%, F1 1.0000, Judge Score 5.0/5.0 tại `data/reports/phase1_report.md`.
- Báo cáo 3 trạng thái so sánh chi tiết hiện tượng Silent Failure tại `data/reports/corruption_report.md`.
- Giao diện Dashboard trực quan sinh thành công tại `data/reports/dashboard.html`.

## 4. Giải thích phần kỹ thuật đã thực hiện
- **Vấn đề giải quyết:** Điều phối luồng dữ liệu 7 tầng đảm bảo tính Idempotency (chạy lại bao nhiêu lần kết quả vẫn chuẩn xác) và cô lập hoàn toàn giữa 3 trạng thái dữ liệu.
- **Cách triển khai:** Quản lý vòng đời dữ liệu qua các collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`), tự động kích hoạt rollback và phục hồi từ raw records khi phát hiện dữ liệu lỗi.
