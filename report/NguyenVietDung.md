# Member Role Report — Nguyễn Việt Dũng

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Việt Dũng           |
| MSSV               | [Điền MSSV]               |
| Khóa/Lớp         | K4 — L3A                   |
| Tên nhóm         | Nhóm Data Pipeline & Observability |
| Vai trò chính    | RAG & Vector Index Specialist |
| Repository         | https://github.com/DucDai1704/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Embedding Pipeline | `src/retrieval/embeddings.py` | `text_for_embedding` từ clean dataset | 384-dim dense vectors (`papers_embeddings.json`) | Hoàn thành |
| Vector Store Indexing | `src/retrieval/index.py` | Embeddings & Metadata | ChromaDB 3 Collections: `papers-baseline`, `papers-corrupted`, `papers-repaired` | Hoàn thành |
| QA Retrieval Engine | `src/retrieval/qa.py` | Query test & ChromaDB client | Top-4 relevant documents & answer synthesis | Hoàn thành |

## 3. Kết quả theo vai trò
- Tích hợp thành công mô hình nhúng `sentence-transformers/all-MiniLM-L6-v2` chạy mượt mà trên môi trường CPU/GPU.
- Xây dựng hệ thống quản lý 3 Vector Collections độc lập, bảo đảm không bị rò rỉ dữ liệu bẩn giữa các giai đoạn đánh giá.
- Hệ thống Retrieval đạt độ chính xác **100.0% Hit Rate** trong Baseline Flow trên bộ câu hỏi benchmark 10 bài báo.

## 4. Giải thích phần kỹ thuật đã thực hiện
- **Vấn đề giải quyết:** Lưu trữ và truy xuất thông tin ngữ nghĩa hiệu quả cao cho RAG, đồng thời đo lường định lượng mức độ ảnh hưởng của dữ liệu độc hại đến không gian vector.
- **Cách triển khai:** Đóng gói class `LocalEmbeddingIndex` với Persistent Chroma Client. Khi thực hiện truy vấn, thuật toán Similarity Search lấy Top-K tài liệu gần nhất dựa trên Cosine Distance. Khi dữ liệu bị tiêm lỗi, thứ hạng vector bị xáo trộn làm Hit Rate giảm xuống 60%, chứng minh tính nhạy cảm của Vector Store đối với chất lượng dữ liệu đầu vào.
