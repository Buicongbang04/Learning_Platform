---
title: Tự viết AP, mAP và mIoU, đo YOLO trên Penn-Fudan
level: intermediate
services: []
files:
  - path: starter/det_eval.ipynb
    note: 8 hàm TODO
  - path: tests/test_det_eval.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py penn-fudan
  - uv run jupyter lab tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/03-detection-segmentation-eval/starter/det_eval.ipynb
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/intermediate/03-detection-segmentation-eval -q
---

## Mục tiêu

Tự viết bộ đánh giá mà mọi paper detection và segmentation dùng: ghép prediction với ground truth, đường
precision-recall, AP ở từng ngưỡng IoU, mAP@[.5:.95] kiểu COCO, và mIoU. Rồi dùng chính bộ đánh giá đó đo YOLO11n
và YOLO11n-seg pretrain trên COCO (chưa từng thấy Penn-Fudan), để đọc được một con số mAP: nó đo gì, ngưỡng
confidence và NMS ảnh hưởng ra sao, và khi nào lỗi nằm ở nhãn chứ không ở model.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Chạy trọn notebook lời giải trên CPU (YOLO chạy 170 ảnh ba lần, thêm một lần
segmentation) mất khoảng 1 phút trên PC rảnh, tới khoảng 10 phút trên laptop đang bận; lần đầu tải thêm Penn-Fudan (53 MB) và hai tệp weights khoảng 6 MB mỗi tệp vào
`~/.cache/ai-engineer/weights`. Không cần GPU.

Đọc mục 5 và 6 phần lý thuyết. Mở `starter/det_eval.ipynb`:

1. `instance_masks`, `masks_to_boxes`, `load_pennfudan`: đọc 170 ảnh và mask instance, suy ra hộp ground truth theo
   **quy ước cạnh pixel** (pixel `c` chiếm đoạn `[c, c+1)`, hộp của mask phủ cột 3..5 có `x1 = 3`, `x2 = 6`).
2. `match_image`: ghép prediction của một ảnh với ground truth theo luật COCO/VOC (theo score giảm dần, mỗi
   prediction lấy ground truth **chưa bị chiếm** có IoU lớn nhất, đạt ngưỡng thì là TP).
3. `average_precision`: AP all-point (precision làm đơn điệu), `evaluate_detections`: AP50, AP75 và AP trung bình
   10 ngưỡng 0.50:0.95 trên toàn bộ tập.
4. `confusion_matrix`, `iou_from_confusion`: IoU theo lớp tính trên tổng pixel cả tập, mIoU bỏ lớp vắng mặt.

Hàm `box_iou` có sẵn (bạn đã tự viết ở bài Basic 03). Rồi chạy các cell `explore`: đối chiếu hộp suy từ mask với tệp
`Annotation/*.txt`, đo YOLO11n zero-shot, so bộ đánh giá của bạn với `ap_per_class` của ultralytics, đổi ngưỡng
confidence, tắt NMS rồi tự áp NMS ở nhiều ngưỡng, xem các false positive score cao nhất, và đo mIoU của YOLO11n-seg.
Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `instance_masks` theo id tăng dần, xử lý ảnh không có người; `masks_to_boxes` đúng quy ước cạnh pixel.
- `match_image`: prediction trùng lặp là FP; ghép với ground truth tự do có IoU **lớn nhất** (không phải cái đầu tiên
  vượt ngưỡng); IoU đúng bằng ngưỡng là TP; thứ tự theo score quyết định ai chiếm ground truth.
- `average_precision` đúng các giá trị tính tay (có làm đơn điệu, recall tối đa dưới 1, không có prediction, không có
  ground truth trả `nan`); `evaluate_detections` đúng AP50, AP75, AP trên ví dụ có hộp IoU 0.62.
- `confusion_matrix` và mIoU đúng trên ví dụ tay, tính trên tổng pixel, lớp vắng mặt là `nan` và bị bỏ khỏi trung bình.
- Trên dữ liệu thật: 170 ảnh, 423 người, hộp của ảnh đầu khớp giá trị đã biết.
- AP của bạn lệch AP của ultralytics không quá vài phần nghìn (cell `explore`, không chấm tự động).

## Gợi ý

### Gợi ý 1

Ghép trong một ảnh cần một ma trận IoU `(số prediction, số ground truth)` và một mảng đánh dấu ground truth đã bị
chiếm. Khi xét một prediction, đừng chọn trong mọi ground truth: những cái đã bị chiếm phải bị loại khỏi lựa chọn
trước khi lấy cái tốt nhất.

### Gợi ý 2

AP: sau khi sắp theo score, `np.cumsum` của cờ TP cho $$TP_k$$; precision và recall ra ngay. "Làm đơn điệu" nghĩa là
mỗi precision được thay bằng giá trị lớn nhất ở **bên phải** nó (recall lớn hơn hoặc bằng); numpy có phép tích luỹ
max, chỉ cần đảo mảng hai lần. Với mIoU, một ma trận nhầm lẫn `C × C` đếm được bằng một phép đếm trên chỉ số gộp từ
cặp (nhãn thật, dự đoán).
