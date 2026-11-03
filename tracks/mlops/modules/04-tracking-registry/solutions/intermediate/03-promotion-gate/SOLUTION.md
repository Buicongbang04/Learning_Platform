# Lời giải: cổng promotion trên registry

Mã trong `gate.py`.

## Cấu trúc

`decide` là hàm thuần (bài Basic 02), còn `gate_and_promote` là lớp mỏng quanh nó làm các việc có tác dụng phụ: đọc số đo,
ghi bản ghi quyết định, dời alias. Tách như vậy cho phép test logic quyết định không cần server, và test lớp registry bằng
hàm `decide` giả.

## Quyết định thiết kế

- **Số đo lấy từ run, không từ tham số gọi hàm.** Nếu người gọi tự truyền số, họ truyền được số đẹp. Cổng đọc số do chính
  job train ghi, qua `run_id` của version, nên bằng chứng nằm trong registry.
- **Lineage là điều kiện cứng, không phải lý do trong `decide`.** Model train từ cây bẩn hay không rõ dữ liệu có thể có
  metric rất đẹp; nhưng không tái lập được thì không có cách điều tra khi nó hỏng. Chặn bằng quy tắc riêng, nêu lý do rõ.
- **Ghi cả quyết định từ chối.** Tag `promotion.decision = rejected` kèm lý do là tài liệu cho lần sau: người train biết cần
  sửa gì, và audit thấy cổng đã chạy.
- **Ghi tag quyết định trước khi dời alias.** Lệch pha giữa "đã quyết định" và "đã áp dụng" luôn xảy ra; nếu một trong hai
  phải mất thì mất phần áp dụng (làm lại được), không mất phần bằng chứng.
- **Tag `previous_<alias>` và `superseded_by`** cho hai hướng truy vết: từ version mới biết lùi về đâu (rollback, bài trung
  cấp 01), từ version cũ biết ai thay nó.
- **Từ chối tự so sánh với chính champion.** Gate chạy lại trên champion đang chạy thường là lỗi gọi (một job lặp), nên báo
  lỗi thay vì lặng lẽ "promote" lại.

## Giới hạn

Hai job gate chạy song song cho hai challenger có thể cùng thấy champion cũ và cuối cùng version nào dời alias sau thắng.
Registry của MLflow không có compare-and-set trên alias; cần khoá ở tầng ứng dụng (một job promote tại một thời điểm, như
`concurrency` của GitHub Actions ở module 08) hoặc kiểm lại alias ngay trước khi ghi.
