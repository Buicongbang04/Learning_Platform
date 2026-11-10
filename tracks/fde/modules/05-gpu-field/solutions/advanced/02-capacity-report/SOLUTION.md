# Lời giải: báo cáo năng lực phần cứng

## Rubric và lý do

| # | Đạt khi | Lỗi hay gặp |
| --- | --- | --- |
| R1 | Ba câu hỏi, ba kết luận có điều kiện ngay đầu báo cáo | Mở đầu bằng mô tả phương pháp; kết luận "tuỳ" |
| R2 | Số đo có máy, image, cờ, ngày, tải khác lúc đo, khoảng | Một con số `23.56 tokens/s` không điều kiện |
| R3 | Số suy ra ghi rõ giả định | Trộn số đo trên VM 2 vCPU với số "chắc khoảng" của GPU |
| R4 | Nói được rủi ro theo ca và điều kiện dừng | Chỉ nhìn RAM lúc cài |
| R5 | V100 đặt vào ma trận: CC 7.0, driver ≤ R580, CUDA ≤ 12.9, toolkit cần nâng, runtime nào chạy | "Card cũ, bỏ" hoặc "card mạnh, dùng" không lý do |
| R6 | ≥ 2 cấu hình có định cỡ, giả định đồng thời, TTFT ước lượng, giá có nguồn hoặc "cần báo giá" | Giá tự đoán; định cỡ chỉ theo trọng số |
| R7 | Runtime cho từng phương án, trả lời thẳng đề xuất Ollama | "Ollama không chuyên nghiệp" |
| R8 | Tổ hợp đã kiểm + lệnh tự kiểm | Không có cách cho IT tự kiểm lại |

## Bài mẫu (đạt R1–R8)

> **1. Tóm tắt.** (1) Lên `llm-medium` trên máy hiện tại: **được ở ca ngày, không được ở ca đêm** khi job tổng hợp chạy
> (máy không đủ RAM cho cả quillo, job và medium); muốn dùng medium cả ngày cần thêm RAM lên ≥ 8 GB hoặc dời job khỏi máy.
> (2) 40 người giờ cao điểm, chữ đầu tiên trong 2 giây: **cần một GPU**; phương án đề xuất là một NVIDIA L4 24 GB chạy vLLM
> với model 7B 4-bit (mục 4), điều kiện là giả định đồng thời ở mục 4 đúng. (3) Ollama: **không dùng cho production**, chỉ
> nên dùng để demo (mục 4).
>
> **2. Máy hiện tại.** Đo 2026-11-11 trên chính máy xưởng (`factory`, Debian 12, 2 vCPU, 3 GB, không GPU) bằng image
> `ghcr.io/ggml-org/llama.cpp:server-b11718`, cờ `-c 4096 -np 1 -t 2`, 3 lần sinh 64 token, quillo đang chạy
> (`bench.py`, báo cáo `report-ca-ngay.json`, `report-ca-dem.json`):
>
> | Model | Sinh (tokens/s) | RAM đỉnh | Ca ngày | Ca đêm |
> | --- | --- | --- | --- | --- |
> | `llm-small` (0,5B Q4_K_M) | 35–50 | ~625 MB | chạy | chạy |
> | `llm-medium` (1,5B Q4_K_M) | 19–25 | ~1,6–1,75 GB | chạy | không đủ RAM, không đo |
>
> Sai số giữa các lần đo trên máy này ±30%. Suy ra (chưa đo): 4 người hỏi cùng lúc thì mỗi người nhận khoảng một nửa tốc
> độ trên (đo một lần với medium: 22 → ~11 tokens/s mỗi người khi 4 người); 15 người ở hai ca hiếm khi quá 2–3 câu hỏi
> cùng lúc (giả định, cần lấy log `/metrics` của quillo một tuần để kiểm).
>
> **3. Giới hạn và rủi ro.** RAM trống của máy đổi theo ca: ~2,2 GB ca ngày, ~1,4 GB khi job tổng hợp chạy. Khi RAM trống
> xuống vài trăm MB, máy không báo lỗi mà chậm toàn bộ (đã tái hiện: tokens/s giảm 4–8 lần, job và quillo cùng chậm). Nếu
> lên medium ở ca ngày: theo dõi `MemAvailable` (cảnh báo dưới 512 MB) và `quillo_ask_seconds`; điều kiện dừng là p95 thời
> gian trả lời gấp đôi mức hiện tại trong 15 phút, khi đó quay về small bằng `hw_config.py` cấu hình cũ.
> Server 2 × V100 16 GB (driver 535, toolkit 1.14): V100 là compute capability 7.0, nên chỉ dùng được CUDA ≤ 12.9 và
> driver tối đa nhánh R580 (nhánh cuối hỗ trợ Volta, LTS tới giữa 2028); vLLM bản hiện tại cần CC ≥ 7.5 nên **không** chạy;
> llama.cpp CUDA (image CUDA 12.8.1) chạy được trên driver 535 nhờ minor version compatibility (nhánh 535 nằm
> trong danh sách `NVIDIA_REQUIRE_CUDA` của image miễn). Toolkit 1.14 dính
> CVE-2024-0132, CVE-2025-23266, CVE-2026-24260 (thoát container): phải nâng lên ≥ 1.19.1 trước khi dùng. Kết luận: dùng
> được làm phương án tạm (llama.cpp, model 7B 4-bit vừa một card 16 GB, card thứ hai dự phòng) tới khi có GPU mới, kèm ghi chú vòng đời 2028; không
> nên mua thêm card cùng thế hệ.
>
> **4. Phương án.** Giả định: 40 người giờ cao điểm, tối đa 8 câu hỏi đang được sinh cùng lúc, context 4 096 token, chữ
> đầu tiên ≤ 2 s khi prompt RAG ~3 000 token.
>
> | Phương án | Model | Định cỡ VRAM (basic 02) | Runtime | Ghi chú |
> | --- | --- | --- | --- | --- |
> | A: 1 × NVIDIA L4 24 GB trong server mới | Qwen2.5-7B-Instruct AWQ/Q4 | trọng số ~4,5–5,5 GB + KV 8 × 4k = 896 MB + overhead ~1 GB ≈ 7,5 GB; còn chỗ tăng context hoặc số người | vLLM (continuous batching cho 8 chuỗi) | 72 W, tản nhiệt thụ động: hợp phòng máy xưởng |
> | B: 1 × RTX 4000 Ada 20 GB trong máy trạm | Qwen2.5-7B-Instruct Q4_K_M | ≈ 6,4 GB tương tự | llama.cpp server `-np 8` | Rẻ và dễ mua hơn, thông lượng nhiều người thấp hơn vLLM |
> | C: tạm thời dùng 2 × V100 | Qwen2.5-7B Q4_K_M | vừa một card 16 GB | llama.cpp | Xem mục 3 |
>
> Thời gian tới chữ đầu: GPU tầm này xử lý prompt hàng nghìn token/giây với model 7B, nên 3 000 token mất dưới 1–2 giây
> (ước lượng, **phải đo** bằng `bench.py`/công cụ benchmark của vLLM trên chính card trước khi ký). Giá: **cần báo giá** từ
> nhà cung cấp phần cứng của tập đoàn cho A và B (phòng mua sắm lấy, chúng tôi gửi cấu hình kỹ thuật ở phụ lục); báo cáo này
> không đưa giá tự đoán.
> Ollama: tiện để demo trên một laptop, nhưng mặc định kéo model từ internet theo tag không ghim (máy xưởng đi qua proxy,
> và chúng tôi cần chứng minh đang chạy đúng model đã đánh giá), cấu hình qua biến môi trường rải rác, thông lượng nhiều
> người kém vLLM. Cho production đề xuất llama.cpp (máy hiện tại, phương án B, C) hoặc vLLM (phương án A).
>
> **5. Phụ lục cho IT.** Tổ hợp đã kiểm: image `ghcr.io/ggml-org/llama.cpp:server-b11718` (trong bundle quillo 1.0.0),
> `qwen2.5-0.5b-instruct-q4_k_m.gguf` sha256 `74a4da8c…a9db`, `qwen2.5-1.5b-instruct-q4_k_m.gguf` sha256
> `6a1a2eb6…407e`; với GPU: image `…:server-cuda-b11718` (CUDA 12.8.1), driver ≥ 570.26, hoặc nhánh 535/550/560/565
> (minor version compatibility, được `NVIDIA_REQUIRE_CUDA` của image miễn; nhánh khác bị toolkit chặn), toolkit ≥ 1.19.1. Tự kiểm: `nvidia-smi > gpu.txt 2>&1` và `diagnose_gpu.py gpu.txt 6000`;
> `cuda_compat.py host.json`; `python3 bench.py --image … --out report.json llm-small=… llm-medium=…` ở ca ngày và ca đêm.

Bài mẫu tách số đã đo (mục 2, có nguồn là hai báo cáo `bench.py`) với số ước lượng (đồng thời, VRAM, thời gian tới chữ
đầu), mỗi ước lượng nói cách kiểm. Không có giá nào tự đoán.
