# Hướng làm: U-Net segmentation người đi bộ, encoder pretrain và hàm serve

Bài không có code lời giải: kiến trúc, vòng train và thí nghiệm là phần của bạn. Dưới đây là các quyết định cần cân nhắc,
kết quả của một bản tham chiếu (giữ ngoài repo) để bạn so, và rubric chấm.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Dữ liệu | 136 ảnh train, 34 ảnh val, `split_names` giống bài Advanced 01; mask mọi người gộp thành lớp 1 | so được với detector của bài Advanced 01 và với YOLO-seg trên cùng ảnh |
| `joint_transform` train | rút một lần tỉ lệ diện tích crop trong `[0.5, 1]` (giữ tỉ lệ khung), vị trí crop, cờ lật từ `generator`; áp cho cả ảnh và mask; resize bilinear có antialias cho ảnh, nearest cho mask | một bộ tham số cho hai tensor là cách duy nhất chắc chắn không lệch; nearest giữ mask chỉ gồm 0/1 |
| Kích thước | 256×256 (ảnh gốc bị co giãn tỉ lệ) | rẻ, 136 ảnh train vài giây mỗi epoch; viền người ở độ phân giải gốc được lấy lại bằng nội suy logits |
| `UNet` | `base=32`: 4 mức encoder 32–256 kênh, đáy 512, upsample `ConvTranspose2d` 2×2 rồi concat skip, hai conv 3×3 + BN + ReLU mỗi mức; 7.76 triệu tham số | đúng bản gốc (Ronneberger 2015) thu nhỏ; BN cho phép lr lớn |
| Encoder pretrain | ResNet-18 ImageNet của torchvision (feature ở 1/2, 1/4, 1/8, 1/16, 1/32), decoder upsample bilinear + concat + hai conv, thêm một mức nối với ảnh gốc; 14.4 triệu tham số | feature ImageNet đã biết "người"; decoder nhỏ tự học |
| Loss | cross-entropy theo pixel + soft Dice lớp người trên cả batch | công thức hay dùng: CE cho gradient ổn định từng pixel, Dice tối ưu thẳng độ chồng; ablation bên dưới cho thấy trên bộ này Dice không thêm gì đo được |
| Optimizer | AdamW, weight decay 1e-4, OneCycleLR theo bước (peak 1e-3, 10% warmup), batch 8, 60 epoch | cùng ngân sách cho mọi cấu hình |
| Đánh giá | `predict_mask` trên 34 ảnh val ở độ phân giải gốc, ma trận nhầm lẫn cộng dồn rồi mới chia (mIoU trên tổng pixel) | đo đúng thứ sản phẩm nhìn thấy, không phải mask 256×256 |
| Serve | BGR → RGB bằng `cv2.cvtColor`, đi qua đúng nhánh eval của `joint_transform`, `eval()` + `no_grad`, nội suy logits về `(H, W)` rồi `argmax`, trả model về chế độ cũ | một đường tiền xử lý cho cả eval và serve là cách phòng skew rẻ nhất |

Những lỗi hay gặp:

- Lật hoặc crop ảnh và mask bằng hai lần gọi ngẫu nhiên riêng: mask lệch ảnh, model vẫn học được "người ở đâu đó", IoU viền
  tụt mà không có lỗi nào. Test kiểm 6 seed.
- Resize mask bằng bilinear: sinh giá trị 0.5 ở viền, ép kiểu `long` thành 0, viền người mỏng dần sau mỗi lần augment.
- Encoder pretrain nhưng chuẩn hoá bằng mean/std của Penn-Fudan hoặc quên chuẩn hoá: feature ImageNet lệch phân phối.
- Đo mIoU trên mask 256×256 rồi báo như độ phân giải gốc; hoặc trung bình IoU theo ảnh.
- `predict_mask` quên `eval()`: BatchNorm dùng thống kê của **một** ảnh, mask phụ thuộc nội dung ảnh theo cách lạ; quên đổi
  BGR sang RGB: model nhìn áo đỏ thành áo xanh. Test dùng một model giả nhạy đúng với hai lỗi này.

## Kết quả tham chiếu

PC RTX 3060, torch 2.14.1+cu126, 60 epoch, batch 8, `size=256`, AdamW + OneCycle peak 1e-3. Đánh giá trên 34 ảnh val ở độ
phân giải gốc qua `predict_mask`, IoU tính trên tổng pixel. Peak VRAM khi train: 1 541 MiB (`UNet`), 1 226 MiB (encoder
ResNet-18). Thời gian train 2–6 phút mỗi lần tuỳ GPU có bị dùng chung không (phần lớn là augmentation trên CPU).

| Cấu hình | Seed | IoU nền | IoU người | mIoU |
| --- | --- | --- | --- | --- |
| `UNet` từ đầu (7.76 triệu tham số) | 0 | 0.941 | 0.761 | 0.851 |
| `UNet` từ đầu | 1 | 0.930 | 0.731 | 0.830 |
| Encoder ResNet-18 pretrain ImageNet (14.4 triệu) | 0 | 0.954 | 0.808 | 0.881 |
| Encoder ResNet-18 pretrain ImageNet | 1 | 0.957 | 0.818 | 0.887 |
| Encoder ResNet-18 pretrain ImageNet | 2 | 0.956 | 0.816 | 0.886 |
| Ablation: encoder ResNet-18 **không** pretrain | 0 | 0.929 | 0.709 | 0.819 |
| Ablation: pretrain, bỏ augmentation | 0 | 0.950 | 0.791 | 0.871 |
| Ablation: pretrain, bỏ Dice (chỉ cross-entropy) | 0 | 0.957 | 0.821 | 0.889 |
| YOLO11n-seg zero-shot (COCO, conf 0.25, mask gộp) | | 0.951 | 0.807 | 0.879 |

`predict_mask` của encoder pretrain mất khoảng 10 ms/ảnh trên GPU rảnh (tới 27–59 ms khi GPU dùng chung), gồm cả tiền xử lý
trên CPU; YOLO11n-seg với `retina_masks=True` khoảng 88 ms/ảnh trong cùng điều kiện dùng chung.

Đọc kết quả:

- **Pretrain là thay đổi lớn nhất**: cùng kiến trúc, bỏ weights ImageNet thì mIoU tụt từ 0.881–0.887 xuống 0.819, kém cả
  `UNet` từ đầu. Với 136 ảnh, feature học sẵn quan trọng hơn kiến trúc decoder.
- **Dao động giữa seed**: encoder pretrain 0.881–0.887 qua 3 seed; `UNet` từ đầu 0.830–0.851 qua 2 seed, rộng hơn vì train
  từ số 0 trên ít dữ liệu nhạy với khởi tạo. Mọi chênh lệch dưới khoảng 0.01 ở cấu hình pretrain là trong dao động.
- **Augmentation** đáng giá khoảng 1 điểm mIoU (0.871 so với 0.881–0.887), cỡ gần với dao động seed: cần thêm seed để chắc.
- **Dice không giúp ở đây**: bỏ Dice cho 0.889, nằm trong (thậm chí nhỉnh hơn) dải của bản có Dice. Lớp người chiếm 17%
  pixel, không đủ hiếm để cross-entropy bị nền áp đảo. Báo cáo trung thực nói "không thấy lợi ích", không giữ Dice vì
  sách nói vậy.
- **Tự train vừa đủ vượt model có sẵn**: encoder pretrain 0.881–0.887 so với YOLO11n-seg zero-shot 0.879 trên cùng 34 ảnh.
  Khoảng chênh nhỏ; điều YOLO-seg có mà U-Net không có là tách được từng người (instance). Chọn model nào phụ thuộc sản
  phẩm cần gì, và đó là điều báo cáo phải nói.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Pipeline dữ liệu đúng | 10 | Hình batch sau augmentation có mask chồng ảnh; giải thích vì sao mỗi phép giữ nhãn; cùng cách chia với bài Advanced 01 |
| So sánh có đối chứng | 25 | UNet từ đầu, encoder pretrain, YOLO11n-seg zero-shot trên cùng 34 ảnh, cùng thước đo ở độ phân giải gốc; IoU từng lớp và mIoU; kết luận đúng theo số |
| Ablation và dao động | 20 | Ít nhất 2 ablation một-thay-đổi, cùng ngân sách; dao động giữa seed ở cấu hình chính; nói rõ chênh lệch nào trong dao động |
| Serve | 15 | `predict_mask` đo ms/ảnh (thiết bị, warmup); hình mask trên ảnh val tốt và tệ; nêu cách phòng skew đã dùng |
| Chất lượng portfolio | 20 | Tóm tắt có số ở đầu, thiết lập tái lập được, mục ngõ cụt có triệu chứng và cách phát hiện, giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo không có so sánh nào trên cùng tập val, hoặc đo mIoU ở 256×256 mà gọi là độ phân giải gốc, không
quá 50 điểm.
