# Lời giải: tự viết AP, mAP và mIoU, đo YOLO trên Penn-Fudan

## Cách làm

**Mask → hộp.** `np.unique(mask)` bỏ 0 cho các id theo thứ tự tăng, `mask[None] == ids[:, None, None]` cho cả khối
`(K, H, W)` trong một phép. Với mỗi mask, `np.nonzero` cho toạ độ pixel; hộp là `(x_min, y_min, x_max + 1, y_max + 1)`:
cộng 1 ở góc dưới phải vì pixel `c` chiếm đoạn `[c, c+1)`. `torchvision.ops.masks_to_boxes` trả `x_max` không cộng 1,
lệch 1 pixel so với hệ toạ độ liên tục mà YOLO trả ra; với người nhỏ nhất của bộ (hộp 7×20 pixel), thiếu 1 pixel ở cạnh
phải và cạnh dưới đã làm IoU với hộp đúng chỉ còn 0.83, đủ để đổi kết quả ở các ngưỡng 0.9–0.95.

**Ghép.** Ma trận IoU `(P, G)` một lần, mảng `taken` cho ground truth đã bị chiếm. Duyệt prediction theo score giảm dần
(`argsort` stable), che các cột đã chiếm bằng `np.where(taken, -1, iou[i])`, lấy `argmax`; IoU ≥ ngưỡng thì TP và đánh dấu
cột đó. Hai lỗi kinh điển mà test bắt: ghép với ground truth **đầu tiên** vượt ngưỡng thay vì tốt nhất, và quên che cột
đã chiếm (hai prediction cùng một người đều thành TP, AP vượt 1 khi có nhiều trùng lặp).

**AP.** Sắp theo score, `tp_cum = cumsum(tp)`, precision `tp_cum / k`, recall `tp_cum / n_gt`. Làm đơn điệu:
`np.maximum.accumulate(precision[::-1])[::-1]`. Diện tích: `sum(diff([0, *recall]) * precision)`. Bước recall chỉ khác 0
ở các TP, nên tổng chỉ cộng precision tại những điểm recall tăng. `evaluate_detections` ghép lại cho từng ngưỡng (một
prediction có thể là TP ở 0.5 mà FP ở 0.75) rồi tính AP trên cờ TP của **cả tập**: không lấy trung bình AP theo ảnh.

**mIoU.** `np.bincount(gt * C + pred, minlength=C*C).reshape(C, C)` đếm ma trận nhầm lẫn trong một phép. IoU lớp
`c` là `cm[c, c] / (tổng hàng c + tổng cột c − cm[c, c])`; mẫu bằng 0 thì `nan` và `np.nanmean` bỏ qua. Cộng ma trận
nhầm lẫn của mọi ảnh rồi mới chia: trung bình IoU theo ảnh thiên vị ảnh ít pixel người.

## Kết quả thật

Penn-Fudan: 170 ảnh, 423 người (2.49 người/ảnh, nhiều nhất 8), ảnh cao 311–581 và rộng 253–1 017 pixel; chiều cao người từ
20 tới 376 pixel, trung vị 286. Đối chiếu với `Annotation/*.txt` (toạ độ đếm từ 1, góc dưới phải bao gồm pixel cuối, nên
trừ 1 ở góc trên trái): **407/423** hộp trùng khít hộp suy từ mask; 16 hộp còn lại lệch vì người gán nhãn vẽ hộp tay
khác viền mask.

YOLO11n pretrain COCO (lớp 0 `person`), chưa thấy Penn-Fudan, `imgsz=640`, CPU, ultralytics 8.4.178, trên cả 170 ảnh:

| Đo | AP50 | AP75 | AP50-95 | Số hộp |
| --- | --- | --- | --- | --- |
| conf 0.001, NMS iou 0.7 (cách đo đúng) | 0.965 | 0.936 | 0.861 | 8 870 |
| `ap_per_class` của ultralytics, cùng cờ TP | 0.962 | | 0.860 | |
| chỉ giữ conf ≥ 0.25 | 0.965 | | 0.859 | 670 |
| chỉ giữ conf ≥ 0.5 | 0.958 | | 0.853 | 537 |

NMS tự áp lên 27 443 hộp thô (YOLO chạy với `iou=1.0`, `max_det=3000`):

| NMS iou | AP50 | AP50-95 | Số hộp |
| --- | --- | --- | --- |
| 0.3 | 0.958 | 0.853 | 3 254 |
| 0.5 | 0.965 | 0.858 | 5 261 |
| 0.7 | 0.965 | 0.861 | 8 866 |
| 0.9 | 0.963 | 0.862 | 17 029 |
| không NMS | 0.230 | 0.215 | 27 443 |

YOLO11n-seg zero-shot, conf ≥ 0.25, mask mọi người gộp thành mask "người", `retina_masks=True`: IoU nền 0.943, IoU người
0.770, **mIoU 0.857**; pixel accuracy 0.952 vì nền chiếm 83% số pixel.

Đọc kết quả:

- **Penn-Fudan dễ với detector COCO**: AP50 0.965 nghĩa là gần như mọi người đều được tìm thấy; khoảng cách tới AP50-95 0.861
  là độ khít của hộp, một phần do quy ước hộp từ mask khác cách COCO gán nhãn.
- **Hai bộ đánh giá lệch vài phần nghìn**: all-point và nội suy 101 điểm cho diện tích hơi khác nhau. So hai model thì phải
  cùng một bộ đánh giá.
- **Ngưỡng conf 0.25 gần như không đổi AP ở đây** vì model rất tự tin trên ảnh dễ (đuôi PR dưới 0.25 gần như toàn false
  positive). Trên tập khó (COCO, ảnh đêm, vật nhỏ) phần recall nằm ở score thấp lớn hơn nhiều; quy tắc vẫn là đo với
  conf 0.001.
- **Không NMS thì AP sụp** từ 0.965 xuống 0.230: mỗi người có hàng chục hộp score cao gần trùng, chỉ một cái là TP, phần
  còn lại là FP ở đầu danh sách, precision rơi ngay từ đầu đường PR. Từ 0.5 tới 0.9 thì gần như không đổi: Penn-Fudan ít
  người đứng chồng lên nhau, nên ngưỡng NMS chưa phải nút thắt.
- **False positive score cao nhất (0.85–0.90) đều là người thật** không được gán nhãn: người bị cắt ở mép ảnh, người
  đi xe đạp, người lái xe nâng, người bị che một nửa. Đó là lỗi nhãn, không phải lỗi model: AP đo trên nhãn thiếu
  thấp hơn chất lượng thật. Luôn nhìn tận mắt các FP score cao trước khi kết luận.
- **Pixel accuracy 0.952 nghe tốt hơn mIoU 0.857** chỉ vì nền chiếm đa số: một model đoán "toàn nền" đã được 0.83.

Thời gian YOLO trên CPU không ghi ở đây vì lúc đo máy đang chạy nhiều việc khác; xem bảng độ trễ ở mục 7 lý thuyết.

## Bẫy thường gặp

- Đo AP với ngưỡng confidence của app, hoặc với `max_det` nhỏ: cắt đuôi PR.
- Tính AP từng ảnh rồi lấy trung bình: ảnh một người có AP 0 hoặc 1, trọng số như ảnh tám người.
- Precision không làm đơn điệu: AP thấp hơn chuẩn và dao động theo thứ tự hộp có score bằng nhau.
- `n_gt` chỉ đếm người ở những ảnh có prediction: người bị bỏ sót hoàn toàn biến mất khỏi mẫu, recall đẹp giả.
- mIoU tính theo ảnh, hoặc gộp lớp vắng mặt vào trung bình như IoU 0.
