# Câu hỏi phỏng vấn: PyTorch chuyên sâu

## Autograd của PyTorch hoạt động thế nào? Vì sao sửa tại chỗ một tensor đôi khi làm backward báo lỗi?

PyTorch dựng graph **động** trong lúc forward chạy: mỗi op trên tensor có `requires_grad=True` tạo một node
(`grad_fn`) trỏ về node của các input, và lưu lại những tensor mà công thức đạo hàm cần (`exp` lưu output, `mul` lưu hai
input, `Linear` lưu input và trọng số). `backward()` đi ngược graph theo thứ tự topo, mỗi node tính vector-Jacobian
product; gradient cộng dồn vào `.grad` của các **leaf** (tham số). Sau backward, saved tensor được giải phóng (trừ khi
`retain_graph=True`).

Mỗi tensor có một **version counter** tăng sau mỗi phép tại chỗ (`add_`, `relu_`, gán chỉ số). Node ghi version của
tensor nó lưu; lúc backward thấy version đã đổi thì báo `one of the variables needed for gradient computation has been
modified by an inplace operation`. Đó là cơ chế an toàn: nếu không có nó, backward sẽ dùng giá trị đã bị sửa và cho
gradient sai im lặng (đúng loại bug của code numpy tự viết ở module 01). Cách chữa: bỏ phép tại chỗ, hoặc `clone()`
trước khi sửa. `inplace=True` của `nn.ReLU` an toàn khi output không bị op khác lưu lại; nó tiết kiệm một tensor.

Ứng viên tốt nói thêm hệ quả về bộ nhớ: những saved tensor đó chính là activation memory, thứ chiếm phần lớn bộ nhớ khi
train CNN và là thứ checkpointing đánh đổi.

## Khi nào bạn tự viết một `torch.autograd.Function`? Cho một ví dụ thật.

Khi đạo hàm "thật" không dùng được hoặc không phải thứ bạn muốn, khi muốn tiết kiệm bộ nhớ, hoặc khi gộp nhiều op:

- **Straight-through estimator**: làm tròn trong quantization-aware training có đạo hàm bằng 0 gần như mọi nơi; forward
  làm tròn, backward cho gradient đi thẳng. Module 10 dùng đúng mẹo này.
- **Gradient reversal**: forward là đồng nhất, backward nhân $$-\lambda$$; dùng trong domain adaptation để feature
  extractor học đặc trưng không phân biệt được miền.
- **Tiết kiệm bộ nhớ**: lưu ít tensor hơn và tính lại phần còn lại trong backward (ví dụ chỉ lưu input của một chuỗi
  activation, giống checkpointing ở mức một op).
- **Kernel gộp**: viết forward/backward bằng Triton hoặc CUDA cho một op ghép (fused attention, fused layernorm).

Hợp đồng: forward chạy với autograd tắt; `ctx.save_for_backward` cho tensor; backward trả đúng một giá trị cho mỗi input
(`None` cho input không cần gradient). Luôn kiểm bằng `torch.autograd.gradcheck` ở float64: float32 quá thô cho sai phân hữu hạn.

## `model.eval()`, `torch.no_grad()` và `torch.inference_mode()` khác nhau thế nào? Khi đánh giá cần cái nào?

- `model.eval()` chỉ đặt `training = False` cho mọi module con: BatchNorm dùng running stats và **không cập nhật** chúng,
  Dropout tắt. Nó không đụng tới autograd.
- `torch.no_grad()` tắt việc dựng graph: không lưu activation, không tốn bộ nhớ cho backward. Nó không đổi BatchNorm.
- `torch.inference_mode()` như `no_grad` nhưng bỏ cả version counter; tensor tạo ra không bao giờ vào graph được (dùng
  sau đó cho train sẽ lỗi). Nhanh hơn chút, hợp cho serving.

Đánh giá cần **cả** `eval()` (đúng hành vi) và `no_grad()`/`inference_mode()` (đúng bộ nhớ, nhanh). Hai bug kinh điển:
quên `eval()` thì accuracy phụ thuộc cỡ batch và running stats bị ghi đè bằng thống kê của tập val (module 01 bài
Intermediate 03 đo: 0.9595 xuống 0.7499 với batch 4); gọi `eval()` trong hàm đánh giá rồi không trả về `train()` thì
phần train sau đó chạy ở chế độ eval mà không báo gì (bài Advanced 02 của module này).

## Parameter, buffer và tensor thường trong `nn.Module` khác nhau ra sao? Bug nào hay gặp?

`nn.Module.__setattr__` đăng ký: `nn.Parameter` vào `_parameters` (optimizer thấy, `state_dict` lưu, `.to()` chuyển),
buffer qua `register_buffer` vào `_buffers` (`state_dict` lưu nếu `persistent=True`, `.to()` chuyển, optimizer không thấy:
dùng cho running stats, mask, bảng RoPE), module con vào `_modules`. Tensor thường, list và dict Python thì PyTorch không
biết tới.

Bug hay gặp nhất là để layer trong **list Python** thay vì `nn.ModuleList`: forward vẫn chạy, nhưng optimizer không cập
nhật các layer đó, `state_dict` không lưu chúng, `.to(cuda)` không chuyển chúng (lỗi device trên GPU, im lặng trên CPU),
`eval()` không lan tới. Phát hiện: so `sum(p.numel() for p in model.parameters())` với con số tính tay, hoặc nạp
`state_dict` vào một model mới rồi so output. Bug cùng họ: tạo optimizer **trước** khi thay một layer
(`model.head = nn.Linear(...)`), nên layer mới không có trong optimizer.

## Train trên GPU nhưng `nvidia-smi` báo GPU-Util chỉ 30–40%. Bạn chẩn đoán và xử lý thế nào?

Trước hết xác nhận GPU đang **chờ dữ liệu** chứ không phải model quá nhỏ: đo riêng thời gian lấy batch (`next(it)`) và
thời gian bước train (có `torch.cuda.synchronize()`), hoặc xem trace của `torch.profiler` có khoảng trống giữa các
kernel. Nếu thời gian lấy batch cỡ thời gian bước train thì là input-bound.

Xử lý theo thứ tự lợi ích:

1. Không làm lại việc đắt mỗi epoch: decode ảnh, tokenize, resize **một lần**, lưu tensor/memory-map. Đo trên CIFAR-10:
   decode PNG trong `__getitem__` chậm hơn hẳn đọc từ tensor uint8 đã decode (bảng ở mục 3 lý thuyết).
2. `num_workers` > 0, `persistent_workers=True`, `pin_memory=True` + `.to(device, non_blocking=True)`.
3. Augmentation theo batch trên GPU; với tập nhỏ, giữ cả tập trên GPU (CIFAR-10 uint8 chỉ 150 MB).
4. Nếu không phải dữ liệu: model quá nhỏ hoặc batch quá nhỏ nên overhead launch kernel chiếm phần lớn: tăng batch,
   `torch.compile`, CUDA graphs.

Ngoài ra kiểm bug tái lập khi tăng worker: generator numpy tự tạo trong `__init__` bị sao chép sang mọi worker, nên
augmentation lặp lại; chữa bằng `worker_init_fn`.

## fp16 và bf16 khác nhau thế nào? Vì sao fp16 cần loss scaling còn bf16 thì không?

fp16 có 5 bit mũ, 10 bit mantissa: chính xác hơn nhưng phạm vi hẹp (lớn nhất 65 504, normal nhỏ nhất
$$6.1 \times 10^{-5}$$, subnormal tới $$6 \times 10^{-8}$$). bf16 có 8 bit mũ như fp32, chỉ 7 bit mantissa: phạm vi như fp32
nhưng eps là $$7.8 \times 10^{-3}$$.

Gradient theo activation thường rất nhỏ vì loss là trung bình trên batch: đo trên ResNet-9 lúc khởi tạo, batch 256 CIFAR-10,
trung vị của chúng cỡ $$2 \times 10^{-7}$$ và một phần đáng kể rơi dưới ngưỡng subnormal của fp16, thành 0 khi backward
chạy ở fp16. Loss scaling nhân loss với $$S$$ (mặc định bắt đầu $$2^{16}$$) để đẩy gradient lên vùng biểu diễn được, rồi
chia lại ở fp32 trước khi cập nhật; $$S$$ động: gặp inf thì bỏ bước và giảm một nửa, đủ 2000 bước tốt thì tăng gấp đôi.
bf16 có cùng phạm vi mũ với fp32 nên không underflow ở đó, không cần scaler; cái giá là sai số làm tròn lớn hơn, nên
trọng số và các phép giảm vẫn phải ở fp32.

Chọn: GPU Ampere trở lên dùng bf16 (đo trên RTX 3050, fp16 và bf16 nhanh ngang nhau); GPU cũ (V100, T4) chỉ có fp16 nhanh
thì fp16 + GradScaler.

## Mixed precision tiết kiệm bộ nhớ ở đâu? Vì sao peak memory không giảm đúng một nửa?

`torch.autocast` không đổi dtype của tham số: trọng số, gradient và trạng thái AdamW vẫn fp32 (16 byte mỗi tham số như
trước). Thứ giảm là **activation** lưu cho backward, phần lớn ở 16 bit. Không giảm đúng một nửa vì: trạng thái train
không đổi; một số op vẫn ở fp32 theo danh sách của autocast (softmax, loss, norm trên CUDA); có thêm bản cache 16 bit của
trọng số trong khối autocast; chỉ số của max-pool là int64. Đo trên RTX 3050, ResNet-9 W=32 batch 256: peak 515 MiB ở fp32
và 312 MiB ở fp16/bf16 (giảm khoảng 40%), bước train nhanh gấp 2 lần nhờ Tensor Core.

Muốn giảm cả trạng thái train thì phải đổi cách lưu: optimizer 8-bit, bf16 thuần cho trọng số (cẩn thận với cập nhật
nhỏ bị làm tròn mất), LoRA, hoặc sharding (ZeRO/FSDP).

## Ước lượng bộ nhớ để full fine-tune một model 7B bằng AdamW. Đưa nó vào một GPU 24GB bằng cách nào?

Trạng thái train với AdamW và mixed precision kiểu PyTorch: 4 (trọng số fp32) + 4 (gradient) + 8 (hai moment) = 16 byte mỗi
tham số; với 7.6 tỉ tham số là khoảng 113 GiB, **chưa** tính activation. Kiểu Megatron (bf16 weights + fp32 master) cũng 16
byte. Nên full fine-tune 7B không vào được một GPU 24GB, dù có AMP.

Các cách, theo mức độ thay đổi:

- **LoRA**: đóng băng 7B (bf16, khoảng 14 GiB), chỉ train adapter vài chục triệu tham số; trạng thái optimizer gần như
  bằng 0. **QLoRA**: base model 4-bit (khoảng 4–5 GiB), vào được cả GPU 12GB. Module 14 làm việc này.
- Optimizer nhẹ: Adam 8-bit (bitsandbytes) giảm phần moment từ 8 xuống 2 byte; Adafactor.
- Gradient checkpointing mỗi block Transformer để activation không tỉ lệ với số tầng; batch nhỏ + gradient accumulation.
- Nhiều GPU: ZeRO-3/FSDP chia trạng thái train cho $$n$$ GPU; offload optimizer sang CPU (chậm).

Ứng viên tốt bắt đầu bằng phép tính 16 byte/tham số trước khi kể công cụ, và hỏi lại: có thật sự cần full fine-tune không.

## Gradient accumulation có tương đương train với batch lớn không? Những chỗ nào lệch?

Về gradient: tương đương nếu loss mỗi micro-batch được nhân trọng số **theo số mẫu** ($$b_j / B$$), không phải chia cho
số micro-batch (sai khi micro-batch cuối nhỏ hơn). `zero_grad` một lần trước cả chuỗi, `step` một lần sau cùng.

Những chỗ lệch:

- **BatchNorm**: thống kê tính trên micro-batch, không trên batch lớn; running stats cập nhật $$k$$ lần. Đo ở bài
  Intermediate 02: gradient của 4 × 64 lệch khoảng 28% so với batch 256 với BatchNorm, nhưng chỉ $$8 \times 10^{-7}$$ với
  GroupNorm. Transformer (LayerNorm/RMSNorm) không gặp vấn đề này.
- Thời gian: không nhanh hơn; batch nhỏ dùng GPU kém hiệu quả hơn.
- Scheduler và số bước: đếm theo bước optimizer, không theo micro-batch.
- Với AMP: `scaler.scale(loss)` mỗi micro-batch, `unscale_`/clip/`step`/`update` một lần ở cuối.
- Phân tán (DDP): dùng `no_sync()` cho các micro-batch trừ cái cuối để không all-reduce $$k$$ lần.

## Activation checkpointing đánh đổi gì? Bạn chọn checkpoint ở đâu?

Không lưu activation trong một đoạn, chỉ lưu input của đoạn; khi backward chạy lại forward của đoạn. Bộ nhớ activation
từ $$O(n)$$ xuống khoảng $$O(\sqrt n)$$ nếu chia $$\sqrt n$$ đoạn, đổi lại thêm khoảng một lần forward cho mỗi đoạn (bài
Intermediate 02 đo trên GPU dùng chung: bước fp32 batch 256 từ 765 ms lên 826 ms với 4 đoạn, 1 156 ms với 1 đoạn).

Chọn đoạn cỡ vừa, thường một block Transformer hoặc một stage ResNet:

- Một đoạn bao cả mạng: lúc backward tính lại, toàn bộ activation lại nằm trong bộ nhớ, peak gần như không giảm (đo ở bài
  Intermediate 02: W=64 batch 256 fp32, 1 054 MiB không checkpoint, 1 043 MiB với 1 đoạn, 739 MiB với 4 đoạn).
- Từng layer nhỏ: giữ input của mọi layer, có thể **nhiều** hơn không checkpoint.
- Tránh đoạn có BatchNorm (cập nhật running stats hai lần) và op không tất định nếu cần tái lập.

Dùng `use_reentrant=False`: giữ trạng thái RNG cho Dropout, hỗ trợ `autograd.grad` và input không cần gradient.

## So sánh BatchNorm, LayerNorm, GroupNorm, RMSNorm. Vì sao Transformer không dùng BatchNorm?

| | Chuẩn hoá trên | Phụ thuộc batch | Train/eval khác nhau | Dùng ở |
| --- | --- | --- | --- | --- |
| BatchNorm | mỗi kênh, qua (N, H, W) | có | có (running stats) | CNN batch vừa và lớn |
| LayerNorm | mỗi mẫu, qua các feature | không | không | Transformer (BERT, GPT-2) |
| GroupNorm | mỗi mẫu, mỗi nhóm kênh | không | không | CNN batch nhỏ (detection, segmentation, diffusion U-Net) |
| RMSNorm | như LayerNorm, không trừ mean, không bias | không | không | LLM hiện đại (LLaMA, Qwen, Mistral) |

Transformer không dùng BatchNorm vì: chuỗi có độ dài thay đổi và padding làm thống kê theo batch nhiễu; batch mỗi GPU nhỏ
khi model lớn; train/eval khác nhau gây lệch, nhất là khi sinh từng token với batch 1; và thống kê theo batch phá vỡ tính
độc lập giữa các mẫu (rò rỉ thông tin giữa chuỗi trong batch). RMSNorm thắng LayerNorm vì rẻ hơn (bỏ một phép giảm)
mà chất lượng tương đương.

## Vì sao residual connection giúp train mạng sâu? Pre-norm và post-norm khác nhau thế nào?

Với $$y = x + f(x)$$, Jacobian là $$I + \partial f/\partial x$$: gradient luôn có một đường cộng thẳng về các tầng trước,
không bị nhân liên tiếp qua mọi tầng như mạng plain. Mạng có thể bắt đầu gần phép đồng nhất và học "phần sai khác". He et
al. cho thấy mạng plain sâu hơn train **tệ hơn** cả trên tập train (degradation), không phải do overfit.

Nhưng residual không tự đủ: mỗi block cộng thêm phương sai, nên không có normalization hoặc khởi tạo phù hợp thì activation
nổ theo độ sâu (đo ở mục 6 lý thuyết với 20 tầng conv residual không norm, He init: logits có độ lệch chuẩn cỡ $$4 \times 10^{3}$$,
loss ban đầu cỡ 6 900). Các cách giữ: normalization trong nhánh, zero-init tầng cuối của nhánh (γ của BN cuối, hoặc
projection như GPT-2 thu nhỏ theo $$1/\sqrt{2L}$$).

- **Post-norm** (Transformer gốc, BERT): $$\mathrm{LN}(x + f(x))$$. Đường tắt bị chuẩn hoá ở mỗi block; mạng sâu cần warmup
  cẩn thận, dễ phân kỳ.
- **Pre-norm** (GPT-2 trở đi, LLaMA): $$x + f(\mathrm{LN}(x))$$. Đường tắt sạch từ đầu tới cuối, train ổn định với lr lớn,
  không cần warmup dài (Xiong et al. 2020); cần một norm cuối trước head. Đổi lại, các tầng sâu đóng góp ít dần.

## Case: train ổn định 2 000 bước rồi đột nhiên `CUDA out of memory`, hoặc bộ nhớ tăng dần theo epoch. Bạn điều tra thế nào?

Phân biệt ba nguyên nhân bằng số đo:

1. **Rò rỉ**: in `torch.cuda.memory_allocated()` mỗi N bước. Tăng đều theo bước là có thứ giữ graph: cộng dồn loss tensor
   (`total += loss` thay vì `loss.item()`), lưu output/logits vào list không `detach()`, đánh giá không có `no_grad()`
   (mỗi batch val giữ toàn bộ activation tới khi biến bị ghi đè), hook giữ tensor. Kiểm `type(total)` và `total.grad_fn`.
2. **Đỉnh bất thường**: một batch đặc biệt lớn (chuỗi dài nhất, ảnh lớn nhất) hoặc bước đánh giá/lưu checkpoint chạy
   cùng lúc với activation của train. Bật `torch.cuda.memory._record_memory_history()`, để chạy tới OOM, dump snapshot và
   xem trên `pytorch.org/memory_viz`: stack trace cho biết block lớn nhất được cấp ở đâu.
3. **Phân mảnh**: `memory_reserved` lớn hơn nhiều so với `memory_allocated`, shape thay đổi liên tục. Chữa bằng
   `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, gom batch theo độ dài (bucketing), padding về vài kích thước cố định.

Sau khi biết nguyên nhân mới chọn cách chữa (mục 5 lý thuyết); giảm batch size mà chưa đo chỉ đẩy lỗi ra xa hơn.

## Case: loss ra NaN chỉ khi bật AMP fp16, fp32 thì bình thường. Bạn làm gì?

Giả thuyết theo thứ tự hay gặp:

1. **Tràn ở forward**: một activation hay logit vượt 65 504 ở fp16 (attention score không chia $$\sqrt d$$, exp không trừ
   max, tổng lớn). Gắn forward hook kiểm `isfinite` để tìm layer đầu tiên ra inf; xem op đó có trong danh sách fp32 của
   autocast không. Chữa: ép op đó về fp32 (`with torch.autocast(..., enabled=False)` cục bộ, `.float()`), hoặc chuyển bf16.
2. **Dùng sai GradScaler**: thiếu scaler (gradient underflow thành 0, thường là "không học" chứ không NaN), clip trước
   `unscale_`, gọi `optimizer.step()` trực tiếp thay vì `scaler.step(optimizer)` (bước có inf không bị bỏ qua, trọng số
   thành NaN ngay).
3. **Loss tính ở fp16**: tự viết loss bằng `log(softmax(...))` trong khối autocast; dùng `F.cross_entropy` trên logits
   `.float()`.
4. **Epsilon quá nhỏ** cho fp16: `1e-8` trong một mẫu số tự viết thành 0 ở fp16; Adam `eps=1e-8` không sao vì trạng thái
   optimizer ở fp32.

Kiểm bằng cách log `scaler.get_scale()`: scale tụt liên tục về rất nhỏ là gradient tràn ở mọi bước, dấu hiệu của lỗi thật
chứ không phải vài bước đầu tràn bình thường. Nếu GPU hỗ trợ, chuyển sang bf16 thường xoá cả lớp vấn đề này.

## Bạn đọc kết quả `torch.profiler` thế nào để biết nên tối ưu chỗ nào?

Xem ba câu hỏi (theo khung "compute-bound, memory-bound, overhead-bound" của Horace He):

- **GPU có bận không?** Trên trace (Perfetto), khoảng trống giữa các kernel là GPU chờ CPU: dữ liệu (mục 3) hoặc overhead
  Python/launch kernel với model nhỏ (tăng batch, `torch.compile`, CUDA graphs).
- **Kernel nào chiếm thời gian?** Bảng `key_averages()` sắp theo `self_cuda_time_total`. Conv/matmul chiếm phần lớn là
  compute-bound: AMP, `channels_last`, TF32 giúp. Các op từng phần tử (BN, activation, cộng) chiếm nhiều là memory-bound:
  gộp kernel (`torch.compile`) giúp. Thấy kernel đổi layout (`nchwToNhwc`) là thiếu `channels_last` (đo ở bài Intermediate 02:
  gần 9% thời gian GPU).
- **Bộ nhớ cấp ở đâu?** `profile_memory=True`, sắp theo `self_cuda_memory_usage`: op nào sinh tensor lớn nhất.

Luôn bỏ vài bước đầu (warmup: cuDNN chọn thuật toán, allocator khởi động) và chỉ profile vài bước, vì profiler làm chậm.
