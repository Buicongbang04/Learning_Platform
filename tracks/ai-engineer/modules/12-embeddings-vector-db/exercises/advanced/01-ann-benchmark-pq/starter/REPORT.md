# Báo cáo: chọn index ANN cho embedding `bge-m3` của Zalo Legal

## Điều kiện đo

<!-- Máy, CPU, số luồng, phiên bản faiss, đo từng câu hay cả lô, số câu hỏi -->

## Bảng đo

| Cấu hình | Tham số | recall ANN@10 | Recall@10 (nhãn) | ms/câu | byte/vector | Dựng (s) |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

## Biên Pareto

<!-- Các cấu hình trên biên, hai biểu đồ (chèn ảnh hoặc mô tả) -->

## PQ tự viết so với FAISS `IndexPQ`

## Ba kịch bản

### (a) Laptop 8 GB, corpus này, p95 dưới 20 ms

### (b) 10 triệu vector trên máy 32 GB, recall ANN@10 ít nhất 0.9

### (c) Recall ANN@10 ít nhất 0.99, cập nhật vài nghìn điều mỗi ngày
