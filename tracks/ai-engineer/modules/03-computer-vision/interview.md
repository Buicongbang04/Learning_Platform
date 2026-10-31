# Câu hỏi phỏng vấn: Computer Vision

## Một tầng conv 3×3 tốn bao nhiêu tham số, phép tính và bộ nhớ? Vì sao người ta nói CNN "rẻ tham số, đắt tính toán"?

Với $$C$$ kênh vào, $$F$$ bộ lọc $$k \times k$$, output $$OH \times OW$$:

- Tham số: $$F(Ck^2 + 1)$$, không phụ thuộc kích thước ảnh (weight sharing).
- Phép nhân-cộng (MAC): $$F \cdot Ck^2 \cdot OH \cdot OW$$, tỉ lệ với số pixel.
- Activation lưu cho backward: $$N \cdot F \cdot OH \cdot OW$$ số mỗi batch.

Một conv 3×3, 64 → 64 kênh trên ảnh 56×56 có 36 928 tham số nhưng 115.6 triệu MAC mỗi ảnh. Một tầng `Linear` có cùng số
tham số chỉ làm 36 928 MAC. Hệ quả thực tế: gấp đôi cạnh ảnh (`imgsz` 320 → 640) thì FLOPs và activation memory gấp bốn
trong khi tham số giữ nguyên; muốn giảm latency của detector, giảm độ phân giải thường hiệu quả hơn cắt tầng. Bộ nhớ
lúc train của CNN bị chi phối bởi activation chứ không phải trọng số, nên batch size và độ phân giải là hai núm bộ nhớ
chính.

Ứng viên tốt nói thêm: FLOPs không phải latency. Depthwise conv ít FLOPs hơn nhiều nhưng ít phép tính trên mỗi byte
đọc (arithmetic intensity thấp), nên trên GPU có thể không nhanh hơn conv thường; phải đo trên phần cứng đích.

## im2col là gì? Thư viện thật tính conv như thế nào?

im2col trải mỗi cửa sổ $$C \times k_h \times k_w$$ thành một dòng của ma trận `cols` shape `(N·OH·OW, C·kh·kw)`; cả tầng conv
thành một phép GEMM `cols @ W.reshape(F, -1).T`. Ưu điểm: dùng được GEMM, phép toán được tối ưu kỹ nhất trên mọi phần
cứng. Nhược điểm: mỗi pixel bị chép vào $$k^2$$ cửa sổ, nên `cols` nặng gấp khoảng 9 lần input với kernel 3×3.

Backward là công thức của tầng Linear áp lên `cols`, cộng thêm `col2im`: rải gradient về ảnh và **cộng** phần chồng nhau.
col2im là adjoint (chuyển vị) của im2col, không phải nghịch đảo; hệ quả là gradient theo input của conv chính là một
transposed convolution.

cuDNN có nhiều thuật toán: implicit GEMM (không dựng `cols` thật), Winograd (giảm số phép nhân cho 3×3), FFT (kernel lớn).
`torch.backends.cudnn.benchmark = True` thử từng thuật toán ở lần gọi đầu cho mỗi shape rồi nhớ cái nhanh nhất: tốt khi
shape input cố định, tệ khi shape đổi liên tục (mỗi shape mới lại benchmark), và làm kết quả kém tất định.

## Receptive field là gì? Làm sao cho neuron cuối nhìn thấy vùng ảnh rộng hơn?

Receptive field là vùng input có thể ảnh hưởng tới một neuron. Đi từ input lên:
$$r_l = r_{l-1} + d_l(k_l - 1)j_{l-1}$$, $$j_l = j_{l-1}s_l$$. Ba cách làm nó nở:

- **Thêm tầng**: mỗi conv 3×3 stride 1 thêm 2 pixel; chậm.
- **Stride/pooling**: nhân "bước nhảy" $$j$$, mọi tầng sau nở nhanh hơn; đổi lại mất độ phân giải.
- **Dilation**: conv 3×3 dilation 1, 2, 4 cho receptive field 15 mà không giảm độ phân giải (DeepLab, WaveNet).

Hai lưu ý mà người phỏng vấn muốn nghe. Thứ nhất, vùng ảnh hưởng **hiệu dụng** (effective receptive field) nhỏ hơn
nhiều so với lý thuyết và tập trung ở giữa (Luo et al. 2016), nên một mạng có receptive field lý thuyết 400 pixel vẫn có
thể "không thấy" ngữ cảnh rộng. Thứ hai, vật to hơn receptive field thì model chỉ thấy từng mảnh: detector giải quyết
bằng feature nhiều tỉ lệ (FPN), phân loại ảnh cần ngữ cảnh toàn cục thì dùng global pooling hoặc attention.

## Vì sao ResNet train được mạng rất sâu? "Degradation" khác overfitting thế nào?

Degradation: mạng plain 56 tầng có lỗi **train** cao hơn mạng 20 tầng. Không phải overfitting (overfit thì lỗi train
thấp, lỗi test cao); đó là vấn đề tối ưu: chồng nhiều tầng phi tuyến khó học nổi cả hàm đồng nhất.

Residual block học phần dư $$F(x)$$ và trả $$\mathrm{ReLU}(F(x) + x)$$. Hai lợi ích: muốn khối thành đồng nhất chỉ cần đẩy
$$F$$ về 0, việc dễ với weight decay; và gradient có đường đi thẳng qua số hạng đồng nhất, không bị nhân dồn qua từng
tầng. Thêm BatchNorm sau mỗi conv giữ phân phối activation ổn định.

Chi tiết hay hỏi tiếp:

- **Projection shortcut** (conv 1×1 stride 2 + BN) khi đổi số kênh hoặc kích thước; identity khi không đổi.
- **Zero-init γ** của BN cuối mỗi khối: lúc khởi tạo mọi khối là đồng nhất, mạng sâu bắt đầu như mạng nông.
- **Pre-activation** (BN → ReLU → conv): đường tắt sạch hoàn toàn, tốt hơn khi trên 100 tầng.
- **Bottleneck** 1×1 → 3×3 → 1×1 cho ResNet-50 trở lên: sâu mà rẻ.

## BatchNorm trong CNN gây ra những vấn đề gì khi fine-tune, khi batch nhỏ và khi deploy?

- **Train và eval khác nhau**: train dùng thống kê của batch hiện tại và cập nhật running mean/var; eval dùng running
  stats. Quên `model.eval()` khi serve thì dự đoán của một ảnh phụ thuộc ảnh khác trong batch, batch 1 cho kết quả rác.
- **Batch nhỏ** (detection, segmentation ảnh lớn, 2–4 ảnh mỗi GPU): thống kê batch nhiễu, accuracy tụt. Cách xử lý:
  GroupNorm, SyncBatchNorm qua nhiều GPU, hoặc đóng băng BN (dùng running stats của pretrain).
- **Fine-tune với backbone đóng băng**: `requires_grad = False` không ngăn BN ở chế độ train cập nhật running stats theo
  dữ liệu mới. Phải đưa các tầng BN về `eval()` sau mỗi lần `model.train()`.
- **Deploy**: BN ở eval là một phép affine, gộp được vào conv trước nó (fold BN) để bớt một kernel; ONNX/TensorRT tự
  làm việc này.

## ViT khác CNN ở đâu? Khi nào bạn chọn ViT?

ViT cắt ảnh thành patch, chiếu tuyến tính (chính là một conv kernel $$P$$ stride $$P$$), thêm CLS token và position
embedding, rồi dùng Transformer encoder. Khác biệt cốt lõi là **inductive bias**: CNN mang sẵn giả định cục bộ và dịch
chuyển đồng biến (conv: dịch input thì feature map dịch theo; pooling/GAP mới biến nó thành bất biến ở output); ViT gần
như không có, mọi quan hệ không gian phải học từ dữ liệu. Vì vậy ViT train từ đầu trên dữ liệu
nhỏ thua CNN cùng cỡ, nhưng với pretrain lớn (JFT, LAION, DINOv2) thì vượt và co giãn tốt hơn.

Chọn trong thực tế:

- Dữ liệu nhỏ, train từ đầu, thiết bị yếu: CNN (ResNet, ConvNeXt, MobileNet).
- Có backbone ViT pretrain tốt (DINOv2, CLIP, SigLIP) và GPU: fine-tune ViT thường thắng; ViT cũng là encoder ảnh của
  hầu hết vision LLM.
- Ảnh độ phân giải cao: chi phí attention $$O(N^2)$$ theo số patch; dùng Swin (attention cửa sổ), patch lớn hơn, hoặc
  FlashAttention.

Lỗi hay gặp: đổi độ phân giải lúc fine-tune mà không nội suy position embedding; quên position embedding (attention hoán
vị đồng biến nên model thành "túi patch").

## Bạn có 2 000 ảnh có nhãn cho bài phân loại 20 lớp. Chọn linear probe, fine-tune hay train từ đầu?

Gần như không bao giờ train từ đầu với 2 000 ảnh. Thứ tự làm:

1. **Linear probe** trên một backbone pretrain tốt: trích feature một lần, train một tầng Linear (logistic regression)
   trong vài giây. Đây là baseline và là phép đo backbone có hợp miền dữ liệu không.
2. Nếu probe còn xa mục tiêu và có GPU: **fine-tune** toàn bộ với lr backbone nhỏ hơn head khoảng 10 lần, warmup, augmentation,
   weight decay không áp cho bias/BN, early stopping theo validation.
3. Miền rất khác ImageNet (ảnh y tế, vệ tinh, công nghiệp): thử backbone pretrain tự giám sát trên miền gần hơn, hoặc
   fine-tune sâu hơn; probe kém là tín hiệu sớm.

Những thứ phải đúng dù chọn gì: cùng `Normalize` và cách resize/crop với lúc pretrain (`weights.transforms()`), tách
validation trước khi nhìn test, và chia theo nhóm nếu có ảnh gần trùng (cùng bệnh nhân, cùng sản phẩm) để tránh rò rỉ.

## Augmentation: nguyên tắc chọn là gì? Detection và segmentation có gì khác?

Mỗi phép augmentation là một khẳng định "nhãn không đổi dưới phép này". Lật ngang ảnh mèo đúng; lật chữ "b" thành "d",
lật ảnh X-quang, xoay biển báo rẽ trái thì sai. Augmentation màu cần nhẹ tay khi màu là tín hiệu.

- Chỉ áp lúc **train**; eval tất định.
- **Detection/segmentation** phải biến đổi cả hộp và mask cùng ảnh, bằng đúng một phép (cùng crop, cùng lật). Crop làm
  vật bị cắt nửa: bỏ hộp quá nhỏ còn lại, hoặc ràng buộc crop giữ vật.
- **Mosaic** (ghép 4 ảnh) và copy-paste là mặc định của YOLO; tắt mosaic vài epoch cuối (`close_mosaic`) để phân phối
  ảnh khớp ảnh thật.
- **Mixup/CutMix** làm nhãn mềm, có ích với model lớn train lâu, ít có ích với vài epoch.

Kiểm tra bắt buộc: vẽ một batch sau augmentation (ảnh và nhãn chồng lên nhau) trước khi train lâu. Đó là cách rẻ nhất để
bắt lỗi mask lệch ảnh.

## Giải thích IoU và NMS. Ngưỡng NMS đánh đổi gì? Vì sao một số detector mới bỏ NMS?

IoU là diện tích giao chia diện tích hợp. NMS: sắp hộp theo score, giữ hộp cao nhất, loại mọi hộp cùng lớp có IoU với nó
lớn hơn ngưỡng, lặp với phần còn lại. Hộp bị loại không được quyền loại hộp khác; NMS phải chạy theo lớp (batched NMS) để
người đứng cạnh xe đạp không loại nhau.

Ngưỡng thấp gộp hai người đứng sát nhau làm một (mất recall trong đám đông); ngưỡng cao để lại hộp trùng (mất
precision, AP ở ngưỡng IoU cao giảm vì hộp trùng thành false positive). Biến thể: Soft-NMS giảm score thay vì xoá; NMS theo
DIoU tính cả khoảng cách tâm.

NMS-free (DETR, YOLOv10, YOLO26) gán mỗi vật đúng một prediction lúc train (ghép một-một kiểu Hungarian), nên lúc chạy
không cần NMS. Lợi ích: latency ổn định (NMS chậm đi trong đám đông, khó export và chạy trên một số accelerator), pipeline
đơn giản hơn khi deploy.

## mAP@0.5 và mAP@[.5:.95] khác nhau thế nào? Những lỗi hay gặp khi đọc con số mAP?

Gộp prediction của cả tập, sắp theo score, ghép với nhãn theo IoU ≥ t (mỗi nhãn ghép một lần), tính đường
precision-recall, làm đơn điệu rồi lấy diện tích: đó là AP ở ngưỡng t. AP50 đo "có tìm thấy vật không"; AP@[.5:.95]
trung bình 10 ngưỡng, thưởng hộp **khít**. mAP là trung bình qua các lớp.

Lỗi hay gặp:

- Đo AP với ngưỡng confidence của app (0.25): cắt mất đuôi đường PR, AP thấp giả. Đo với conf rất thấp (0.001).
- So hai con số từ hai bộ đánh giá khác nhau (all-point so với 101 điểm COCO, khác quy tắc ghép, khác cách xử lý vùng
  "crowd/ignore").
- Nhãn thiếu: người thật không được gán nhãn biến dự đoán đúng thành false positive. Xem tận mắt các FP score cao nhất
  trước khi kết luận model kém.
- Quy ước hộp khác nhau (pixel rời rạc +1 hay toạ độ liên tục) làm AP ở ngưỡng cao thấp đi dù model đúng.
- mAP trung bình che lớp hiếm kém; luôn xem AP theo lớp và theo kích thước vật (small/medium/large).

## So sánh detector two-stage, one-stage anchor-based và anchor-free. Làm sao để detect vật nhỏ tốt hơn?

- **Two-stage** (Faster/Mask R-CNN): RPN đề xuất vùng, RoIAlign cắt feature, head phân loại và chỉnh hộp. Chính xác, chậm
  hơn, dễ thêm nhánh (mask, keypoint).
- **One-stage anchor-based** (YOLOv3–v5, RetinaNet): mỗi ô feature có vài anchor cỡ cố định, dự đoán độ lệch. Phải chọn
  anchor theo dữ liệu; focal loss xử lý mất cân bằng nền/vật.
- **Anchor-free** (FCOS, YOLOv8/11): mỗi ô dự đoán khoảng cách tới bốn cạnh, gán nhãn theo chất lượng dự đoán (Task Aligned
  Assigner). Ít siêu tham số, là mặc định hiện nay cho bài toán thời gian thực.

Vật nhỏ: tăng `imgsz` (đắt theo bình phương), dùng tầng feature độ phân giải cao (P2), cắt ảnh lớn thành tile khi suy
luận (SAHI) rồi gộp kết quả, augmentation không thu nhỏ vật quá mức, kiểm anchor/stride có hợp cỡ vật không, và đo AP
theo kích thước để biết đã cải thiện thật.

## Semantic, instance, panoptic segmentation khác nhau thế nào? Vì sao U-Net cần skip connection? Đo bằng gì?

Semantic: mỗi pixel một lớp, không phân biệt hai người. Instance: mỗi vật đếm được một mask riêng. Panoptic: cả hai (vật
đếm được có id, "stuff" như trời, đường chỉ có lớp).

Mạng phân loại thu nhỏ ảnh 16–32 lần để có ngữ nghĩa; segmentation cần trả về đúng pixel. U-Net nối feature cùng độ phân
giải từ nhánh mã hoá sang nhánh giải mã: tầng sâu biết "đây là người", tầng nông biết "viền ở pixel này". Không có skip,
mọi chi tiết phải đi qua đáy 1/16 và viền ra nhòe, khối vuông.

Thước đo: IoU theo lớp tính trên tổng pixel cả tập rồi trung bình (mIoU); Dice ($$2TP/(2TP + FP + FN)$$) tương đương đơn điệu
với IoU. Pixel accuracy gần như vô nghĩa khi nền chiếm phần lớn ảnh. Loss: cross-entropy theo pixel cộng Dice loss để lớp
nhỏ không bị nền áp đảo. Instance segmentation đo bằng mask AP; panoptic bằng PQ.

## Case: triển khai detector người cho camera an ninh, 8 luồng 1080p, 15 FPS mỗi luồng, trên một máy có một GPU tầm trung. Bạn thiết kế thế nào?

Ngân sách: 8 × 15 = 120 khung/giây, tức khoảng 8 ms cho mỗi khung nếu xử lý tuần tự trên một GPU. Thiết kế:

1. **Giải mã video** bằng phần cứng (NVDEC qua FFmpeg/GStreamer/DeepStream), không giải mã trên CPU rồi chép sang GPU.
2. **Model**: YOLO bản n/s fine-tune trên dữ liệu camera thật; `imgsz` 640 hoặc nhỏ hơn nếu người không quá nhỏ trong
   khung. Export TensorRT fp16 (rồi INT8 với tập calibration nếu cần), **batch** khung từ nhiều luồng vào một lần gọi.
3. **Bỏ bớt khung**: detect mỗi 2–3 khung, tracker (ByteTrack) nội suy và giữ id ở giữa; tracker còn giảm nhấp nháy hộp.
4. **Pipeline bất đồng bộ**: đọc, suy luận, hậu xử lý, ghi kết quả ở các luồng/tiến trình riêng nối bằng hàng đợi có giới hạn;
   khi quá tải thì bỏ khung cũ nhất chứ không để độ trễ tăng dần.
5. **Đo**: p50/p99 latency mỗi giai đoạn, số khung bị bỏ, GPU-Util; tách service time khỏi queue time.
6. **Chất lượng**: tập đánh giá lấy từ chính các camera (đêm, mưa, ngược sáng), đo AP theo điều kiện, theo dõi phân phối
   score và số hộp mỗi giờ để phát hiện camera lệch hay bị che.

Đánh đổi cần nói rõ: độ phân giải với vật nhỏ ở xa, bỏ khung với sự kiện ngắn, INT8 với mất vài điểm AP.

## Case: model phân loại đạt 95% trên tập test nhưng sau khi đưa vào app điện thoại chỉ còn khoảng 70%. Bạn điều tra thế nào?

Nghi ngờ đầu tiên là **train/serve skew** chứ không phải model. Kiểm theo thứ tự rẻ nhất:

1. **Cùng một ảnh, hai pipeline**: lấy vài ảnh trong tập test, chạy qua code serving thật, so logits với lúc đánh giá.
   Lệch thì lỗi nằm ở tiền xử lý, không cần nhìn model.
2. **Thứ tự kênh** (OpenCV BGR so với PIL RGB), **layout** (`reshape` thay `permute` từ HWC sang CHW), **chuẩn hoá** (mean/std
   khác, quên chia 255), **resize** (thuật toán nội suy khác, có hay không antialias, thiếu center crop/letterbox).
3. **Dữ liệu thật khác dữ liệu train**: xoay EXIF của ảnh điện thoại, JPEG nén lại, ảnh mờ, ánh sáng yếu, khung hình
   khác (người dùng chụp gần hơn). Thu một mẫu ảnh thật, gán nhãn, đo riêng.
4. **Chế độ model**: quên `eval()`, model lượng tử hoá/convert (ONNX, Core ML, TFLite) lệch số so với bản PyTorch; so
   output hai bản trên cùng input.

Cách phòng: một hàm `preprocess` duy nhất dùng cho train, eval và serve; test hồi quy "ảnh từ tệp qua pipeline serving cho
cùng logits"; log thống kê input (mean từng kênh, kích thước) ở production và so với lúc train; giữ một tập "ảnh thật từ
app" trong bộ đánh giá.

## Case: nhà máy muốn phát hiện lỗi bề mặt sản phẩm, có 50 000 ảnh chưa nhãn và chỉ khoảng 200 ảnh lỗi. Bạn bắt đầu thế nào?

1. **Làm rõ bài toán**: chỉ cần "có lỗi hay không" (phân loại), vị trí (detection), hay hình dạng (segmentation)? Chi phí
   bỏ sót và báo nhầm khác nhau thế nào? Điều đó quyết định thước đo (recall ở precision cố định, không phải accuracy).
2. **Baseline rẻ**: anomaly detection chỉ cần ảnh tốt (PatchCore, PaDiM trên feature backbone pretrain) vì ảnh tốt nhiều,
   ảnh lỗi ít. Đo trên 200 ảnh lỗi cộng một tập ảnh tốt đã kiểm.
3. **Gán nhãn hiệu quả**: SAM hoặc model baseline đề xuất vùng, người duyệt sửa; active learning chọn ảnh model không chắc
   chắn để gán tiếp.
4. **Model có giám sát** khi đủ nhãn: detector/segmenter nhỏ fine-tune từ pretrain, augmentation sát thực tế (đổi sáng, xoay
   nhẹ theo cách đặt sản phẩm), copy-paste lỗi lên ảnh tốt nếu hợp lý.
5. **Đánh giá đúng**: chia theo lô sản xuất/ngày để tránh rò rỉ, tập test cố định có ảnh khó, kiểm tận mắt các false
   negative. Theo dõi drift khi đổi camera, đèn hay dây chuyền.
