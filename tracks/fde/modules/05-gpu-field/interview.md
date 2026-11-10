# Câu hỏi phỏng vấn: GPU ở máy khách

## 1. Khách nói "máy em có card NVIDIA mà chạy container GPU không được". Bạn hỏi gì, theo thứ tự nào?

Đi từ dưới lên, mỗi tầng một lệnh và một câu trả lời có/không: `lspci -nn | grep -i nvidia` (card có thật không),
`lsmod | grep nvidia` và `cat /proc/driver/nvidia/version` (module có nạp không), `nvidia-smi` (driver và GPU), rồi
`nvidia-ctk --version` và `docker info` (toolkit, runtime), cuối cùng `docker run --rm --gpus all <image của mình>
nvidia-smi` (cả chuỗi). Tầng đầu tiên trả lời "không" là chỗ hỏng; tôi không đoán ở tầng trên khi tầng dưới chưa xác
nhận. Tôi xin output nguyên văn ra tệp, không xin ảnh chụp, và ghi lại phiên bản từng tầng vào hồ sơ khách vì đó là dữ liệu
cho lần nâng cấp sau.

## 2. `nvidia-smi` báo "CUDA Version: 12.4". Khách hỏi vậy image CUDA 12.8 có chạy không. Bạn trả lời thế nào?

Con số đó là bản CUDA **cao nhất driver hỗ trợ đầy đủ**, không phải CUDA đã cài. Image 12.8 trên driver nhánh 550 chạy
được nhờ minor version compatibility (cùng major 12, driver ≥ 525.60.13), với hai giới hạn: tính năng cần driver mới trả
lỗi `cudaErrorCallRequiresNewerDriver`, và PTX không được JIT trên driver cũ, nên binary phải có sẵn mã cho đúng kiến trúc
card. Với một image dựng sẵn như llama.cpp CUDA thì thường chạy; tôi xác nhận bằng cách chạy thật trên máy khách (hoặc trên
máy có cùng nhánh driver) chứ không hứa trước, và ghi "chạy nhờ minor compatibility" vào ma trận hỗ trợ như một điều kiện.

## 3. Phân biệt backward, minor version và forward compatibility của CUDA. Khi nào forward compatibility cứu được khách?

Backward: driver mới chạy ứng dụng CUDA cũ, luôn có. Minor version: trong cùng một major (từ CUDA 11), ứng dụng dựng
với minor mới hơn chạy được trên driver đạt mức tối thiểu của major đó, có giới hạn tính năng. Forward: gói
`cuda-compat` cho phép CUDA của major mới chạy trên driver cũ hơn, nhưng chỉ cho GPU data center, vài SKU RTX chứng nhận
và Jetson, trên nhánh driver còn hỗ trợ. Nó cứu được khách có A100 bị khoá driver vì quy trình chứng nhận; không cứu được
khách dùng GeForce: với họ câu trả lời là nâng driver, hoặc dùng image CUDA thấp hơn.

## 4. Khách có hai server V100 và muốn "lên CUDA 13 cho mới". Bạn tư vấn gì?

V100 là compute capability 7.0. CUDA 13 bỏ hỗ trợ Maxwell, Pascal, Volta (CC < 7.5), và nhánh driver R580 là nhánh cuối
cùng còn hỗ trợ các card đó (LTS tới giữa 2028). Nên với V100, tổ hợp đúng là driver nhánh 580 + CUDA tối đa 12.9, và mọi
image tôi giao cho khách phải dựng với CUDA 12.x. Tôi ghi điều đó vào báo cáo cùng mốc 2028: sau đó card không còn bản vá
driver, đó là dữ liệu cho kế hoạch mua sắm của họ, không phải việc tôi tự quyết.

## 5. Vì sao `nvidia-smi` trong container báo "No running processes found" mà Memory-Usage gần đầy?

Bảng Processes chỉ hiện tiến trình trong PID namespace của người gọi. Trong container, tiến trình của container khác hay
của host không hiện, nhưng bộ nhớ chúng giữ vẫn được tính. Vì vậy tôi kết luận "GPU bận" từ con số bộ nhớ trống so với
nhu cầu của model, không từ danh sách tiến trình; muốn biết ai giữ thì chạy `nvidia-smi` trên host (hoặc nhờ người có
quyền host) và hỏi lịch dùng của họ.

## 6. Khách bảo "GPU A100 của bọn em trống, nvidia-smi chỉ thấy 38 MiB". Bạn kiểm thêm gì trước khi hứa chạy model 30B?

Cột `MIG M.`. A100/H100 có thể đang ở chế độ MIG: bảng chính trông gần như trống nhưng GPU đã bị chia thành các instance
cứng, mỗi instance có bộ nhớ riêng (vd. `1g.10gb`, `3g.20gb`). Tôi xin bảng `MIG devices` và hỏi instance nào dành cho
mình. Một model 30B Q4 cần ~20 GB thì không vừa instance 10 GB, và việc đổi profile MIG cần dừng mọi workload trên card,
đó là quyết định của đội hạ tầng chứ không phải yêu cầu "tắt giúp em".

## 7. Ước lượng nhanh: Qwen2.5-7B Q4_K_M có vừa RTX 3060 12 GB cho 4 người dùng, mỗi người context 8k không?

Trọng số theo tệp thật ~4,5 GB (Q4_K_M thực tế ~4,9 bit/tham số, không phải 4). KV cache: 2 × 28 lớp × 4 KV head × 128
× 8192 token × 4 chuỗi × 2 byte ≈ 1,75 GB. Cộng overhead CUDA và compute buffer ~0,5–1 GB: tổng ~7–7,5 GB, vừa và còn chỗ.
Điểm hay bị quên là GQA: tính KV theo `hidden_size` như model cũ sẽ ra gấp 7 lần và kết luận sai là không vừa. Sau ước
lượng tôi vẫn đo thật, vì overhead phụ thuộc phiên bản runtime và cờ batch.

## 8. Khách không có GPU và ngân sách năm nay không cho mua. Bạn còn đề xuất được gì?

Chạy CPU với model nhỏ và quantization hợp lý: sinh token bị giới hạn bởi băng thông RAM, nên model 0,5–3B Q4 trên CPU
server vài core cho được 10–50 tokens/s, đủ cho hỏi đáp tài liệu với ít người dùng. Tôi đo trên chính máy họ với đúng cấu
hình sẽ chạy, đặt threads bằng số core vật lý, giới hạn context và số chuỗi song song theo RAM trống thật (không theo RAM
danh nghĩa), và nói rõ đánh đổi chất lượng của model nhỏ bằng một phép đo trên tài liệu của họ. Kèm theo là con số "nếu
có GPU X thì được Y", để quyết định mua năm sau có dữ liệu.

## 9. Bạn benchmark thế nào để con số đưa khách đứng vững?

Đúng máy, đúng image và cờ production, đúng độ dài prompt/câu trả lời và số người dùng đồng thời. Có request khởi động
không tính, độ dài sinh cố định (`n_predict` + `ignore_eos`), tắt cache prompt, chạy vài lần và báo khoảng chứ không báo
một con số hai chữ số thập phân. Tách tốc độ xử lý prompt và tốc độ sinh vì chúng trả lời hai câu hỏi khác nhau. Ghi kèm
điều kiện đo: thời điểm, tải khác trên máy, phiên bản. Và đo bộ nhớ bằng RSS đỉnh của tiến trình, cẩn thận với số của
cgroup vì page cache được tính cho cgroup đọc tệp đầu tiên.

## 10. Benchmark trên máy production của khách thì có rủi ro gì, bạn giảm rủi ro thế nào?

Rủi ro là chính benchmark làm hại thứ đang chạy: chiếm CPU, RAM, VRAM của dịch vụ khách đang dùng, để lại container, đổi
cấu hình. Tôi xin khung giờ, đọc tài nguyên trống ngay trước mỗi bước và không chạy bước nào mà ước tính không vừa, chạy
model từ nhỏ tới lớn, luôn dọn container kể cả khi bị ngắt (Ctrl-C, mất SSH), không bao giờ dùng quyền root hay đổi giới
hạn hệ thống, và kiểm lại dịch vụ của khách sau khi xong. Bước nào bị bỏ qua thì báo cáo nói rõ là bỏ qua và vì sao, thay
vì im lặng hay ghi một con số đo trong điều kiện xấu.

## 11. Khi nào bạn chọn vLLM, khi nào llama.cpp, khi nào Ollama cho một khách on-prem?

llama.cpp khi không có GPU, GPU nhỏ hoặc cần đóng gói đơn giản cho máy air-gapped: một binary/image và một tệp GGUF ghim
sha256, chạy cả CPU lẫn GPU, offload một phần lớp. vLLM khi có GPU data center và nhiều người dùng đồng thời: PagedAttention
và continuous batching cho thông lượng cao hơn hẳn, tensor parallel nhiều GPU; đổi lại image lớn, phụ thuộc chặt phiên bản
CUDA/driver và yêu cầu compute capability tối thiểu. Ollama tốt cho demo và máy dev; tôi tránh đưa nó vào production ở
khách vì model mặc định kéo từ internet không ghim và khó trả lời "đang chạy đúng bản nào".

## 12. Khách gửi output `Failed to initialize NVML: Driver/library version mismatch`. Bạn nói gì với IT của họ?

Gói driver trên đĩa đã được nâng (thường do cập nhật tự động) trong khi module kernel cũ vẫn đang chạy: thư viện NVML mới
không nói chuyện được với module cũ. Kiểm bằng `cat /proc/driver/nvidia/version` so với phiên bản gói. Cách sửa là
reboot trong khung giờ bảo trì (hoặc gỡ và nạp lại module khi không tiến trình nào dùng GPU). Tôi đề xuất thêm: ghim gói
driver (hold) và đưa việc nâng driver vào quy trình thay đổi có reboot, để lần sau không xảy ra giữa giờ làm việc.

## 13. Khách hỏi "tại sao không cứ để Docker tự kéo image mới nhất của llama.cpp cho nhanh?"

Vì "mới nhất" là một mục tiêu di động: bản build đổi mỗi ngày, cùng một tag có thể trỏ tới image khác, và một bản mới có
thể đòi driver mới hơn hay đổi cờ mặc định. Thứ tôi giao là một tổ hợp đã đo: image theo tag build cụ thể (và digest),
model theo sha256, cờ chạy tường minh. Ở máy air-gapped hay sau proxy thì kéo image còn không làm được; ở máy mở thì nó
làm số đo hôm nay không còn đúng tuần sau.

## 14. Bạn viết báo cáo năng lực phần cứng cho khách gồm những gì?

Ba phần theo thứ tự: máy hiện tại làm được gì (model, tốc độ sinh và xử lý prompt, số người dùng đồng thời, RAM/VRAM
đỉnh, điều kiện đo), giới hạn và rủi ro (RAM trống khi có tải khác, driver/toolkit cũ và CVE kèm phiên bản sửa, card hết
vòng đời, nhiệt/nguồn nếu thấy), và lựa chọn nâng cấp có con số (thêm RAM, GPU cụ thể với VRAM và tokens/s ước lượng,
model nhỏ hơn với đánh đổi chất lượng). Mỗi khuyến nghị có lý do và có cách kiểm sau khi làm. Tôi tách rõ cái đã đo với
cái suy ra, vì khách sẽ dùng báo cáo để xin ngân sách.
