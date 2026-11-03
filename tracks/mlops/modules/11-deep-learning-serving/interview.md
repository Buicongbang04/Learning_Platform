# Câu hỏi phỏng vấn: Deploy model Deep Learning

## Serving model ảnh khác serving model tabular ở những điểm nào?

Artifact lớn (hàng chục tới hàng trăm MB) nên nạp và khởi động lạnh tốn giây; đầu vào là ảnh phải decode, resize, chuẩn hoá, nên tiền xử lý là một phần của model và là nguồn skew lớn nhất; chi phí mỗi dự đoán cao nên batch quyết định throughput; phần cứng là GPU với bộ nhớ hữu hạn, nên batch size, độ phân giải và precision tranh nhau cùng một ngân sách; đầu ra là mask phải phóng về kích thước gốc và mã hoá. Hệ quả vận hành: kiểm đầu vào trước khi decode, warmup trước khi báo ready, đo bộ nhớ theo batch, và benchmark theo batch size thay vì một con số duy nhất.

## Bạn export model PyTorch sang ONNX. Làm sao biết artifact đúng?

Ba lớp kiểm: `onnx.checker.check_model`; đọc graph để kiểm opset tối thiểu và trục batch là `dim_param` (động) ở cả input và output; chạy cùng input qua PyTorch và ONNX Runtime trên **nhiều batch size** và so `max |a - b|` với `atol` (FP32 CPU cỡ `1e-4`). Với FP16 hoặc INT8 không so logits mà so trên nhiệm vụ (mIoU của mask) với ngưỡng ghi trong model card. Bước này chạy trong CI lúc export và lúc service khởi động; fail thì không nhận traffic. Chạy nhiều batch size vì lỗi quên `dynamic_axes` chỉ lộ ra với batch khác batch lúc export.

## `dynamic_axes` dùng để làm gì, và quên nó thì chuyện gì xảy ra?

Exporter TorchScript ghi lại graph từ một lần chạy với input mẫu; trục nào không khai báo động bị ghi thành hằng số. Quên `dynamic_axes` cho trục batch thì model chạy đúng với batch lúc export, nhưng ONNX Runtime từ chối batch khác ("Got invalid dimensions"). Lỗi này thường chỉ xuất hiện khi bật dynamic batching trên production. Khai báo trục động cho cả input và output, dùng batch mẫu khác 1, và có test chạy ít nhất hai batch size.

## Sự cố: sau khi đổi base image, p95 của service phân đoạn tăng gấp mười, không có lỗi nào. Bạn điều tra thế nào?

Nghi đầu tiên: ONNX Runtime không nạp được CUDA Execution Provider (base image mới có CUDA/cuDNN khác phiên bản `onnxruntime-gpu` cần) và đã **lặng lẽ** chạy hết trên CPU: nó chỉ ghi cảnh báo vào log. Kiểm `session.get_providers()` trong process đang chạy, `nvidia-smi` thấy GPU 0% và process không chiếm bộ nhớ GPU, log khởi động có dòng cảnh báo nạp provider. Sửa: ghim cặp CUDA/cuDNN với `onnxruntime-gpu`, và quan trọng hơn là chặn tái diễn: log provider lúc khởi động, `/readyz` đỏ khi cấu hình đòi GPU mà provider đầu không phải CUDA, metric "provider đang dùng", test GPU trong CI kiểm `get_providers()[0]`.

## Dynamic batching hoạt động thế nào, và chọn tham số ra sao?

Request đến được đưa vào hàng đợi kèm một future; một task nền lấy request đầu, chờ thêm tới khi đủ `max_batch_size` hoặc hết `max_wait_ms` kể từ request đầu, chạy model một lần ngoài event loop, rồi trả từng output vào đúng future. `max_batch_size` chọn ở đầu gối đường cong throughput theo batch; `max_wait_ms` khoảng 5–10% ngân sách p95. Theo dõi histogram kích thước batch thực tế và thời gian chờ trong hàng đợi; batch trung bình gần 1 nghĩa là batching chỉ cộng thêm latency.

## Viết benchmark latency cho model trên GPU, những lỗi nào làm số sai?

Không warmup (lần đầu gồm cấp phát, chọn thuật toán cuDNN, nạp kernel); đo cả việc tạo dữ liệu; báo trung bình thay vì p50/p95; tính throughput bằng `batch / p50` (bỏ đuôi); với PyTorch CUDA không `synchronize` trước khi dừng đồng hồ (đo thời gian **xếp** kernel chứ không phải chạy); không ghi số luồng, phiên bản, kích thước input; chạy khi máy đang tải nặng mà không lặp lại. Benchmark model đơn lẻ và load test HTTP trả lời hai câu hỏi khác nhau, cần cả hai.

## Model chạy được batch 8 trên laptop 4 GB. Bạn ước lượng batch tối đa trên card production như thế nào?

Tách bộ nhớ thành CUDA context, trọng số, activation (tỉ lệ batch × độ phân giải), workspace, cache. Ước lượng activation từ graph để sàng lọc, nhưng con số dùng thật phải đo trên đúng loại card: `torch.cuda.max_memory_allocated` theo từng batch, hoặc `nvidia-smi` với ONNX Runtime. Lấy batch lớn nhất vừa khoảng 80% phần trống (biên cho phân mảnh, workspace, request ảnh lớn bất thường). Không nhân tỉ lệ bộ nhớ 3050/T4 rồi tin: kernel, layout và allocator khác nhau.

## FP16 có luôn giảm nửa bộ nhớ và gấp đôi tốc độ không?

Không. Trọng số và activation giảm nửa trên lý thuyết, nhưng cuDNN có thể chuyển layout NCHW sang NHWC để dùng Tensor Core và cấp buffer tạm; số đo thật với model conv nhỏ: FP16 NCHW gần bằng FP32, FP16 + `channels_last` mới giảm gần nửa. Tốc độ chỉ tăng nhiều khi có Tensor Core và kích thước kênh bội số của 8. Thêm nữa, FP16 có thể làm lệch mask ở lớp hiếm; phải kiểm mIoU. Câu trả lời đúng là "đo trên card thật".

## Dynamic quantization và static quantization khác nhau thế nào? Bạn chọn cái nào cho model phân đoạn?

Dynamic: trọng số lưu INT8, activation được lượng tử hoá lúc chạy theo min/max của chính input đó; không cần dữ liệu hiệu chỉnh, lợi nhiều với MatMul (transformer). Static: thang activation được hiệu chỉnh trước trên vài trăm mẫu đại diện, graph có node QDQ; nhanh hơn, giữ chất lượng tốt hơn với Conv và chạy được trên TensorRT, nhưng cần tập hiệu chỉnh đúng phân phối. Với SegFormer trên CPU: thử dynamic trước vì rẻ; nếu mIoU giảm quá ngưỡng hoặc không nhanh hơn thì static với ảnh train làm tập hiệu chỉnh. Luôn so mIoU và IoU lớp viền, không chỉ kích thước tệp.

## Vì sao chọn ONNX Runtime thay vì serve thẳng bằng PyTorch?

Một artifact chạy được trên CPU, CUDA, TensorRT, OpenVINO bằng cách đổi provider; không kéo cả PyTorch (vài GB) vào image CPU; tối ưu graph sẵn (fuse, constant folding); gọi được từ C++, Go, Java, C#; có quantization. Cái giá: phải export và kiểm sai số, một số op mới hay control flow export khó, debug trên graph khó hơn trên code Python. Nếu model đổi liên tục và đội thuần PyTorch, serve PyTorch (TorchScript hay `torch.compile`) có thể đơn giản hơn ở giai đoạn đầu.

## Khi nào bạn dùng Triton Inference Server thay vì FastAPI + ONNX Runtime?

Khi có nhiều model chung một GPU (Triton quản lý instance, bộ nhớ, lịch chạy), cần dynamic batching và metrics Prometheus chuẩn mà không tự viết, cần gRPC hoặc ensemble (tiền xử lý, model, hậu xử lý thành pipeline), hoặc muốn backend TensorRT. Không nên khi chỉ có một model nhỏ, đội chưa quen vận hành Triton, hay logic tiền xử lý phức tạp viết bằng Python sẽ nằm trong Python backend chậm. Lưu ý Triton là server, có thể chạy ONNX Runtime bên trong; so "Triton vs ONNX Runtime" là so nhầm tầng.

## TensorRT nhanh hơn, vì sao không phải lúc nào cũng dùng?

Engine TensorRT được build cho **một** kiến trúc GPU, một phiên bản TensorRT và một dải shape khai báo lúc build; đổi card, driver hay dải shape là build lại, và build mất vài phút tới hàng chục phút. Một số op không hỗ trợ phải chạy chỗ khác. INT8 cần hiệu chỉnh. Vì vậy TensorRT hợp với batch job lớn và service ổn định trên phần cứng cố định; với đội nhỏ, nhiều loại card, hay model đổi thường xuyên, ONNX Runtime CUDA (hoặc TensorRT EP với cache engine) là điểm cân bằng tốt hơn.

## Thiết kế hệ thống: phân đoạn ảnh thú cưng cho app di động (đỉnh 250 req/s sau push) và job đêm 2 triệu ảnh

Tách hai luồng vì yêu cầu khác nhau. **Online**: API gateway giới hạn kích thước ảnh, service stateless (decode, kiểm, batcher có trần, ONNX Runtime CUDA FP16 đã verify), hàng đợi có giới hạn và trả 503 khi đầy, autoscale theo độ dài hàng đợi và GPU utilization; tính số GPU từ throughput đo được ở batch tối ưu chia hệ số an toàn, quyết định giữ máy cho đỉnh hay chấp nhận xếp hàng ngắn; warmup trước `/readyz`; canary theo `model_version` trên mỗi response. **Batch**: 2 triệu ảnh trong 4 giờ là khoảng 139 ảnh/giây; chia shard, job idempotent có checkpoint, batch lớn nhất vừa bộ nhớ, có thể TensorRT FP16/INT8 vì shape cố định, chạy trên instance spot. **Chung**: model registry (MLflow) với tiền xử lý đi kèm artifact, verify trong CI, metrics (latency theo phân vị, kích thước batch, lỗi theo loại, provider, bộ nhớ GPU), và đánh giá chất lượng định kỳ trên mẫu có nhãn.

## Service nhận ảnh thì cần kiểm những gì trước khi chạy model?

Kích thước body (413) trước khi đọc hết; header ảnh hợp lệ (400); định dạng cho phép; cạnh ngắn và cạnh dài trong khoảng lấy từ phân phối dữ liệu thật (422); số pixel tối đa để chặn decompression bomb (`Image.MAX_IMAGE_PIXELS`); chuyển mode về RGB (ảnh xám, RGBA, CMYK, có EXIF xoay). Kiểm trên header trước khi decode pixel và trước khi resize, vì decode ảnh khổng lồ đã đủ làm hết RAM. Mỗi lỗi một mã rõ để client biết sửa gì.
