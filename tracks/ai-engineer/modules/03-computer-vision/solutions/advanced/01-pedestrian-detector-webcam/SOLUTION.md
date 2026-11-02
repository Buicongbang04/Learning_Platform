# Hướng làm: detector người đi bộ fine-tune trên Penn-Fudan và app webcam

Bài không có code lời giải: chuyển dữ liệu, thí nghiệm và app là phần của bạn. Dưới đây là các quyết định cần cân nhắc,
kết quả của một bản tham chiếu (giữ ngoài repo) để bạn so, và rubric chấm.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Hộp ground truth | suy từ mask, quy ước cạnh pixel (`x2 = cột phải nhất + 1`), chuẩn hoá `cx, cy, w, h` | cùng hệ toạ độ liên tục với output YOLO; tệp `Annotation` vẽ tay lệch mask ở 16/423 hộp |
| Chia dữ liệu | `random.Random(0).sample` 34 tên trên danh sách đã sắp, phần còn lại train | tái lập, không phụ thuộc thứ tự `iterdir`; bài Advanced 02 dùng đúng cách chia này |
| Ảnh trong dataset YOLO | symlink tới ảnh gốc | không nhân đôi 50 MB; ultralytics đọc qua symlink bình thường |
| Model | `yolo11n.pt` pretrain COCO, giữ một lớp `person` | COCO đã có người; fine-tune chỉ cần chỉnh cho miền ảnh và quy ước hộp |
| Train | 30 epoch, `imgsz=512`, batch 8, `seed=0`, `deterministic=True`, augmentation mặc định (mosaic, HSV, lật, scale) | ảnh Penn-Fudan cạnh dài 253–1 017 pixel, 512 giữ người nhỏ mà rẻ hơn 640 |
| Đánh giá | bộ đánh giá của bài Intermediate 03 cho **cả hai** model, cùng 34 ảnh, `conf=0.001`, NMS iou 0.7; bootstrap 300 lần theo ảnh cho khoảng 95% của từng model, **paired bootstrap** 1 000 lần (cùng tập ảnh rút lại cho cả hai model) cho khoảng 95% của ΔAP | so công bằng; khoảng riêng của hai model chồng nhau chưa nói được gì, khoảng của hiệu thì có; 34 ảnh có 90 người nên một hai hộp đã đổi AP vài điểm |
| Ngưỡng app | conf 0.25 | đủ cao để không nhấp nháy hộp, recall vẫn gần mức tối đa trên tập val |
| Nguồn video | `cv2.VideoCapture` cho camera/tệp, đọc thư mục ảnh theo tên | người không có webcam kiểm bằng thư mục ảnh val hoặc một tệp video bất kỳ |
| Phát hình | MJPEG qua `http.server` (có sẵn), không `imshow` | env dùng OpenCV headless, chạy được trên server không màn hình |
| FPS | EMA của `1/dt` giữa hai khung, đồng hồ tiêm được | FPS từng khung nhảy loạn; test được bằng đồng hồ giả |

Những lỗi hay gặp:

- Chia `W` cho trục y hoặc ghi `x1, y1` thay vì tâm: train vẫn chạy, mAP thấp khó hiểu. Vẽ ngược nhãn lên ảnh trước khi train.
- So "mAP sau fine-tune" (ultralytics `val` trên tập val) với "mAP zero-shot" đo ở chỗ khác (cả 170 ảnh, `imgsz` khác,
  `classes` khác): hai con số không so được.
- Đo zero-shot mà quên `classes=[0]`: model COCO trả cả xe đạp, ô tô; chúng thành false positive.
- `yolo train` kiểm AMP bằng cách tải `yolo26n.pt` vào thư mục `weights/` **của thư mục đang đứng**: chạy từ gốc repo là có
  một tệp lạ trong cây git. Chạy từ thư mục ngoài repo, hoặc thêm `weights/` vào danh sách bỏ qua của bạn.
- `VideoWriter` sai `(rộng, cao)` hoặc khung không đúng cỡ: tệp ra rỗng mà không báo lỗi.
- FPS tính bằng `1 / thời_gian_model`: bỏ quên đọc khung, vẽ, mã hoá JPEG; FPS thật của app thấp hơn.

## Kết quả tham chiếu

Bản tham chiếu theo đúng bảng trên: ultralytics 8.4.178, torch 2.14.1+cu126, PC RTX 3060 (GPU dùng chung với một bài
train khác), seed 0. Train 30 epoch mất 239 s ở `imgsz=512` và 378 s ở `imgsz=640`, khoảng 1 GB VRAM. Đánh giá trên 34 ảnh
val (90 người) bằng bộ đánh giá của bài Intermediate 03, `conf=0.001`, khoảng 95% bootstrap 300 lần theo ảnh;
precision/recall ở IoU 0.5, conf 0.25:

| Model | `imgsz` đo | AP50 | AP75 | AP50-95 (khoảng 95%) | Precision / recall @0.25 |
| --- | --- | --- | --- | --- | --- |
| YOLO11n zero-shot | 640 | 0.995 | 0.967 | **0.897** (0.863–0.926) | 0.776 / 1.000 |
| YOLO11n zero-shot | 512 | 0.996 | 0.935 | 0.877 (0.843–0.916) | 0.783 / 1.000 |
| Fine-tune, train `imgsz=512` | 512 | 0.984 | 0.938 | 0.813 (0.777–0.855) | 0.888 / 0.967 |
| Fine-tune, train `imgsz=640` | 640 | 0.985 | 0.914 | 0.821 (0.771–0.870) | 0.944 / 0.944 |

`yolo train` tự báo trên cùng 34 ảnh: mAP50 0.992 / mAP50-95 0.817 (512) và 0.981 / 0.825 (640): gần số của bộ đánh giá
tự viết, nhưng chỉ có nghĩa khi đặt cạnh zero-shot đo cùng cách.

Paired bootstrap 1 000 lần theo ảnh của hiệu (fine-tune trừ zero-shot @640):

| Fine-tune | ΔAP50 (khoảng 95%) | ΔAP75 | ΔAP50-95 |
| --- | --- | --- | --- |
| train 512, đo 512 | −0.011 (−0.036 tới +0.004) | −0.029 (−0.077 tới +0.016) | **−0.084** (−0.117 tới −0.051) |
| train 640, đo 640 | −0.010 (−0.024 tới −0.000) | −0.053 (−0.086 tới −0.019) | **−0.077** (−0.107 tới −0.043) |

Đọc kết quả:

- **Fine-tune không thắng zero-shot, và hiệu có thật**: ΔAP50-95 âm trong cả 1 000 lần rút lại. Nhưng AP50 gần như bằng
  nhau: model fine-tune vẫn tìm thấy người, chỉ có hộp **kém khít** hơn (AP75, AP50-95 giảm). Đó là quan sát, chưa phải
  nguyên nhân: 30 epoch trên 136 ảnh với mosaic và lr mặc định là nghi phạm hàng đầu, cần ablation (freeze backbone, lr
  nhỏ, tắt mosaic, ít epoch) mới tách được.
- **Precision tăng, recall giảm, phù hợp với nhãn thiếu**: zero-shot tìm thấy cả 90 người có nhãn nhưng precision theo nhãn
  chỉ 0.776 vì nó cũng báo người không được gán nhãn (bài Intermediate 03). Sau fine-tune precision lên 0.888/0.944, một
  phần vì model bớt báo những người đó, và recall trên nhãn xuống 0.967/0.944, phù hợp với việc model học ức chế người bị che
  hoặc ở mép ảnh. Vì AP đo trên chính bộ nhãn thiếu đó, hiệu ứng này không giải thích được AP giảm; nó là lý do không nên
  khoe precision. Một camera đường phố cần thấy mọi người.
- **Hướng làm đáng thử** nếu vẫn muốn fine-tune: gán nhãn bổ sung người bị thiếu (hoặc đánh dấu vùng bỏ qua), freeze
  backbone (`freeze=10`), lr nhỏ hơn, ít epoch hơn, hoặc lấy dữ liệu thật từ camera đích. Hoặc dùng zero-shot và đầu tư vào
  app, tracker, ngưỡng conf.

Độ trễ YOLO11n (trung vị 50 khung sau 10 khung warmup, ảnh val): CPU Xeon 4 luồng 17.7 ms (`imgsz` 320) và 32.3 ms (640) cho
riêng model, GPU 11.9 và 12.1 ms (model nano trên GPU bị chi phối bởi khởi chạy kernel, không đổi theo `imgsz`). Cả vòng app
trên video 640×480 dựng từ 34 ảnh val (102 khung, đọc, detect, vẽ, ghi mp4): **54 FPS** GPU ở `imgsz` 640, **40 FPS** CPU ở
`imgsz` 320. Bản tham chiếu của `app.py` và `prepare_data.py` qua toàn bộ test của bài.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Dữ liệu đúng | 10 | Nhãn YOLO được kiểm bằng hình vẽ ngược; chia train/val tái lập, ghi seed; không rò rỉ ảnh val vào train |
| Fine-tune có kỷ luật | 15 | Ghi đủ thiết lập (model, `imgsz`, epoch, batch, seed, GPU, thời gian); ít nhất một biến thể có lý do; không chọn gì theo tập val rồi báo cáo trên chính nó mà không nói |
| Đánh giá có đối chứng | 25 | Zero-shot và fine-tune qua **cùng** bộ đánh giá trên **cùng** 34 ảnh; AP50 và AP50-95; độ bất định (bootstrap hoặc nhiều seed) và kết luận trung thực theo nó; phân tích FP/FN có hình, nhận ra lỗi nhãn |
| App chạy được | 20 | Chạy với webcam hoặc tệp video/thư mục ảnh; MJPEG trên trình duyệt hoặc tệp video ra; FPS hiển thị; có ảnh chụp/video |
| Độ trễ | 10 | ms/khung theo thiết bị và ít nhất hai `imgsz`, có warmup và điều kiện máy; tách thời gian model khỏi cả vòng app |
| Chất lượng portfolio | 10 | Tóm tắt có số ở đầu, mục ngõ cụt có triệu chứng và cách phát hiện, giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo chỉ có con số mAP do `yolo train` in ra mà không so với zero-shot trên cùng tập, không quá 50 điểm.
