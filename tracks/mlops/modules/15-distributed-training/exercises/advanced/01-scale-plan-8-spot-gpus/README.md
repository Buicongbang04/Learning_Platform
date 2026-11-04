---
title: Kế hoạch scale huấn luyện lên 8 GPU spot
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Viết kế hoạch đưa một job huấn luyện đang chạy trên 1 GPU on-demand lên 8 GPU spot, như một senior viết trước khi xin ngân sách:
có số đo, có ước tính chi phí và thời gian, có kế hoạch chịu thu hồi, có tiêu chí dừng. Không có test; tự chấm bằng rubric trong
`SOLUTION.md` sau khi viết xong.

## Đề bài

Bối cảnh: model dự đoán thời gian giao hàng (transformer nhỏ, 350 triệu tham số) huấn luyện lại mỗi tuần trên 1 GPU A100 80 GB
on-demand. Mỗi lần mất 60 giờ, dữ liệu tăng 8% mỗi tháng, và đội sản phẩm muốn huấn luyện lại hai lần mỗi tuần. Đo trên 1 GPU:

- 1 400 mẫu/giây, GPU utilization trung bình 55%, bộ nhớ đỉnh 41 GB, batch 64.
- DataLoader `num_workers=4`, ảnh và bảng đọc từ S3 dưới dạng 2 triệu tệp nhỏ.
- Checkpoint hiện tại: chỉ lưu model cuối job, 1.4 GB.
- Bảng giá dùng chung với bài Basic 03 (`exercises/basic/03-gpu-cost-estimate/prices.yaml`). Tỉ lệ thu hồi spot ước tính 0.03 lần mỗi
  giờ mỗi node; một node có 8 GPU.

Viết `PLAN.md` (tối đa 3 trang) gồm:

1. **Mục tiêu có số**: thời gian đồng hồ, ngân sách mỗi lần huấn luyện, chất lượng không kém bản 1 GPU (tiêu chí cụ thể).
2. **Việc phải làm trước khi thêm GPU**, dựa trên số đo ở trên (có ít nhất một việc không liên quan tới số GPU).
3. **Chiến lược song song** và lý do (DDP, FSDP hay khác), thay đổi batch size và learning rate.
4. **Kế hoạch đo hiệu suất scale** theo từng mức (1, 2, 4, 8 GPU) và ngưỡng hiệu suất nào thì dừng ở mức thấp hơn.
5. **Checkpoint và resume**: lưu gì, mỗi bao lâu (có tính), ghi ở đâu, làm sao biết resume đúng; xử lý thông báo thu hồi.
6. **Ước tính chi phí và thời gian** cho on-demand và spot (dùng hàm của bài Basic 03), có giả định hiệu suất scale ghi rõ.
7. **Rủi ro và tiêu chí rollback** về 1 GPU on-demand.
8. **Vận hành**: alert khi job treo hay chậm, ai trực, chi phí theo dõi ở đâu.

## Tiêu chí đạt

- `PLAN.md` đủ 8 mục, mọi con số có nguồn (số đo, giá, hay giả định ghi rõ).
- Tự chấm theo rubric `SOLUTION.md` đạt từ 70/100.
- Bạn bảo vệ được kế hoạch trước câu hỏi "vì sao không thuê luôn 16 GPU cho nhanh".

## Gợi ý

### Gợi ý 1

GPU utilization 55% trên 1 GPU là tín hiệu đầu tiên cần đọc: thêm 7 GPU nữa cùng chờ dữ liệu thì chỉ nhân chi phí. Xem lại mục 6 README module.

### Gợi ý 2

8 GPU trong **một** node: một lần thu hồi là mất cả node. Tỉ lệ thu hồi của job bằng tỉ lệ của node, không nhân 8; nhưng nếu dùng 8 node
1 GPU thì nhân 8.
