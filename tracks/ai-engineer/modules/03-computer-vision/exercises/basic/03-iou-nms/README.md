---
title: Hộp bao, IoU và Non-Maximum Suppression
level: basic
services: []
files:
  - path: starter/boxes.py
    note: 6 hàm TODO
  - path: tests/test_boxes.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/basic/03-iou-nms -q
---

## Mục tiêu

Tự viết ba viên gạch mà mọi detector dùng sau bước forward: đổi định dạng hộp, ma trận **IoU** vector hoá,
và **NMS** (thường và theo lớp), khớp từng chỉ số với `torchvision.ops`. Bài Intermediate 03 dùng chúng để
tính mAP, bài Advanced 01 để hiểu vì sao detector trả đúng một hộp cho mỗi người.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 5 phần lý thuyết (IoU, NMS). Trong `starter/boxes.py`, hộp là mảng `(N, 4)` số thực:

1. `cxcywh_to_xyxy(boxes)`, `xyxy_to_cxcywh(boxes)`: đổi giữa (tâm, kích thước) và (góc trên trái, góc dưới phải).
2. `box_area(boxes)`: diện tích hộp xyxy; hộp suy biến ($$x_2 \le x_1$$ hoặc $$y_2 \le y_1$$) có diện tích 0.
3. `box_iou(a, b)`: ma trận IoU `(N, M)` bằng broadcasting, không vòng lặp Python. Hợp bằng 0 thì IoU là 0.
4. `nms(boxes, scores, iou_threshold)`: greedy NMS, trả chỉ số `int64` các hộp được giữ theo score giảm dần.
   Một hộp bị loại khi IoU với hộp đang giữ **lớn hơn hẳn** ngưỡng (bằng ngưỡng thì giữ), như torchvision.
5. `batched_nms(boxes, scores, classes, iou_threshold)`: NMS riêng từng lớp, hộp khác lớp không loại nhau; trả
   chỉ số theo score giảm dần.

Chỉ dùng numpy.

## Tiêu chí đạt

- Đổi định dạng khớp `torchvision.ops.box_convert`, đổi đi đổi lại ra hộp ban đầu.
- `box_iou` khớp `torchvision.ops.box_iou` tới `1e-12`; đúng các giá trị tay (1/7, 1, 0, 0.25); hộp suy biến cho 0
  mà không cảnh báo chia 0; 1 500 × 1 500 hộp dưới 3 giây.
- `nms` khớp `torchvision.ops.nms` từng chỉ số trên 200 hộp với ngưỡng 0, 0.3, 0.5, 0.7, 1; IoU đúng bằng 0.5 với
  ngưỡng 0.5 thì giữ cả hai; không có hộp nào thì trả mảng `int64` rỗng.
- Chuỗi A > B > C (A loại B, C chỉ chồng B): C được giữ.
- `batched_nms` khớp `torchvision.ops.batched_nms` trên 150 hộp 4 lớp.

## Gợi ý

### Gợi ý 1

Phần giao của hai hộp cũng là một hộp: nghĩ xem góc trên trái và góc dưới phải của nó lấy từ hai hộp ra sao, và chuyện gì
xảy ra với chiều rộng khi hai hộp không chạm nhau. Để có mọi cặp `(i, j)` mà không vòng lặp, thêm một trục dài 1 vào mỗi
mảng sao cho numpy broadcast thành `(N, M, ...)`. Hợp bằng 0 thì phép chia phải được chặn trước, không phải sửa `nan` sau.

### Gợi ý 2

NMS là vòng lặp trên danh sách đã sắp theo score: mỗi vòng chốt một hộp và loại bớt phần còn lại. Câu hỏi quyết định
đúng sai: một hộp đã bị loại có còn được quyền loại hộp khác không? Với `batched_nms`, nghĩ cách để hộp khác lớp không
bao giờ "nhìn thấy" nhau, rồi nhớ trả chỉ số theo đánh số gốc.
