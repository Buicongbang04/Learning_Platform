---
title: Detector người đi bộ fine-tune trên Penn-Fudan và app webcam (portfolio)
level: advanced
services: []
files:
  - path: starter/prepare_data.py
    note: 4 hàm TODO, chuyển Penn-Fudan sang định dạng YOLO
  - path: starter/app.py
    note: 6 hàm/lớp TODO, app webcam/video, phần phát MJPEG có sẵn
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_pedestrian.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py penn-fudan
  - uv run python tracks/ai-engineer/modules/03-computer-vision/exercises/advanced/01-pedestrian-detector-webcam/starter/prepare_data.py --out ~/.cache/ai-engineer/pennfudan-yolo
  - uv run --project setup/gpu yolo detect train data=$HOME/.cache/ai-engineer/pennfudan-yolo/data.yaml model=yolo11n.pt epochs=30 imgsz=512 batch=8 seed=0 project=$HOME/.cache/ai-engineer/runs name=pennfudan
  - uv run python tracks/ai-engineer/modules/03-computer-vision/exercises/advanced/01-pedestrian-detector-webcam/starter/app.py --weights $HOME/.cache/ai-engineer/runs/pennfudan/weights/best.pt --source 0 --port 8000
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/advanced/01-pedestrian-detector-webcam -q
---

## Mục tiêu

Đi trọn con đường từ bộ dữ liệu có nhãn tới một sản phẩm chạy được: chuyển nhãn sang định dạng YOLO, fine-tune một
detector, đo nó **đúng cách** so với model chưa fine-tune, rồi đóng gói thành app nhận webcam hoặc tệp video, vẽ hộp và
FPS, phát qua trình duyệt. Kết quả là một bài portfolio: "detector người đi bộ, mAP bao nhiêu trên tập val, chạy bao
nhiêu FPS trên phần cứng nào, và đây là vì sao".

## Đề bài

**Phần cứng:** GPU 4GB · ~420 phút

Thời gian trên là thời gian làm bài (dữ liệu, thí nghiệm, app, báo cáo). Fine-tune YOLO11n 30 epoch ở `imgsz=512` mất
vài phút trên GPU 4GB rảnh (dưới 2 GB VRAM với batch 8); mỗi lần chạy lại cũng vậy. Không có GPU: train trên CPU với
`imgsz=320`, 15 epoch (khoảng 15–30 phút tuỳ máy) vẫn cho model dùng được trong app; ghi rõ cấu hình trong báo cáo.

Đọc mục 5 và 7 phần lý thuyết. Bài dùng lại IoU/NMS của bài Basic 03 và bộ đánh giá AP của bài Intermediate 03.

1. **Dữ liệu** (`starter/prepare_data.py`): `mask_to_yolo_lines` (hộp suy từ mask theo quy ước cạnh pixel, chuẩn hoá
   về `[0, 1]`), `mask_to_polygon_lines` (cho task segment), `split_names` (chia train/val tái lập theo seed),
   `write_yolo_dataset` (ảnh là symlink tới ảnh gốc, nhãn `.txt`, `data.yaml`). Chạy với mặc định: 136 ảnh train,
   34 ảnh val. Bài Advanced 02 dùng đúng cách chia này.
2. **Fine-tune**: YOLO11n pretrain COCO trên tập train (lệnh ở phần `run`, hoặc API `YOLO(...).train(...)`), thêm ít
   nhất một biến thể có lý do (`imgsz`, số epoch, augmentation, freeze backbone, YOLO11s...). Ghi seed.
3. **Đánh giá có đối chứng** trên đúng 34 ảnh val, cùng một bộ đánh giá: YOLO11n zero-shot (lớp `person` của COCO) so với
   bản fine-tune; AP50, AP50-95, precision/recall ở ngưỡng confidence bạn chọn cho app. 34 ảnh là ít: ước lượng độ bất
   định (bootstrap theo ảnh, hoặc nhiều seed) trước khi nói "tốt hơn".
4. **App** (`starter/app.py`): `parse_source`, `iter_frames` (camera, tệp video hoặc thư mục ảnh), `draw_detections`,
   `FpsMeter`, `run` (vòng đọc → detect → vẽ → ghi/phát), `make_detector`. Phần phát MJPEG qua HTTP có sẵn. App phải
   chạy được với webcam **và** với một tệp video hoặc thư mục ảnh (người không có webcam vẫn kiểm được).
5. **Độ trễ**: đo ms/khung của model (CPU và GPU nếu có, ít nhất hai `imgsz`) và FPS của cả vòng app; tách thời gian
   model khỏi đọc khung, vẽ, mã hoá JPEG.
6. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Test trên CPU, không cần ultralytics: nhãn YOLO đúng quy ước và đúng thứ tự instance; đa giác nằm trong hộp của
  mask; `split_names` tái lập, đã sắp, không giao nhau; `write_yolo_dataset` ghi đúng cấu trúc và `data.yaml`;
  `draw_detections` vẽ tại chỗ, không tô lòng hộp, kẹp hộp tràn ảnh; `FpsMeter` đúng công thức EMA với đồng hồ giả;
  `run` đọc tệp video và thư mục ảnh, ghi video đủ số khung, dừng ở `max_frames`, báo `RuntimeError` khi nguồn hỏng;
  `app.py` không import ultralytics ở đầu tệp.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, mọi hình được nhắc tới đều tồn tại.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`: bảng zero-shot so với fine-tune trên cùng 34 ảnh val có độ bất định,
  bảng độ trễ có điều kiện đo, video hoặc ảnh chụp app đang chạy.

## Gợi ý

### Gợi ý 1

Trước khi train, mở vài tệp nhãn đã sinh và vẽ ngược hộp lên ảnh (nhân lại với W, H): nhầm `cx, cy` với `x1, y1` hay
chia W cho trục y vẫn train được, chỉ ra mAP thấp khó hiểu. Đo zero-shot trước: YOLO pretrain COCO đã biết "person",
nên câu hỏi đáng giá không phải "fine-tune có học không" mà "fine-tune thêm được bao nhiêu, ở ngưỡng IoU nào, và có
chắc không".

### Gợi ý 2

ultralytics in mAP ra sau mỗi lần `val`; để so công bằng hãy chạy cả hai model qua cùng một hàm đánh giá (bộ đánh giá
của bạn ở bài Intermediate 03, hoặc `model.val(data=..., split="val")` cho cả hai với cùng `imgsz`, `conf=0.001`).
Trong app, `cv2.VideoWriter` cần `(rộng, cao)` của khung đầu tiên; một `on_frame` đẩy JPEG cho trình duyệt là đủ, đừng
`imshow` (bản headless không có cửa sổ). Đo FPS bằng một đồng hồ đơn điệu và làm mượt bằng EMA, không chia cho thời
gian của một khung.
