---
title: Benchmark sinh ảnh với diffusers - bước, guidance, thời gian, VRAM, CLIP score
level: advanced
services: []
files:
  - path: starter/imagegen.ipynb
    note: 3 hàm TODO, benchmark của bạn
  - path: starter/BENCHMARK.md
    note: Báo cáo khuyến nghị cấu hình
  - path: tests/test_imagegen.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/18-multimodal/exercises/advanced/02-image-gen-benchmark/starter/imagegen.ipynb
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/advanced/02-image-gen-benchmark -q
---

## Mục tiêu

Đánh giá một model sinh ảnh như đánh giá một service trước khi đưa vào sản phẩm: một lưới cấu hình, mỗi cấu hình có chất
lượng (CLIP score và mắt bạn), thời gian, VRAM, đo đúng cách (seed ghim, khởi động trước, đồng bộ GPU), và một khuyến nghị có
điều kiện. Lý thuyết diffusion và guidance ở module 06; ở đây là mức sản phẩm.

## Đề bài

**Phần cứng:** GPU 4GB · ~240 phút

Thời gian trên là thời gian làm bài. `stabilityai/sd-turbo` (bản fp16, tải 2.5 GB) đạt đỉnh khoảng 3.0 GiB VRAM ở 512×512
fp16, vừa GPU 4GB; chạy GPU bằng kernel `ai-gpu` (`setup/gpu`). Chỉ có CPU (env gốc): một ảnh 512×512 mất khoảng 14 giây
ở 1 bước và 24 giây ở 4 bước với 4 luồng (mục 5 lý thuyết): giảm lưới xuống 2 cấu hình và 4 prompt. Phần mở rộng không
chấm trên PC 12GB: thêm một model lớn hơn (ví dụ `stabilityai/sdxl-turbo`, chưa đo trong track; kiểm VRAM và giấy phép
trên model card trước khi tải).

1. Trong `starter/imagegen.ipynb` viết `clip_score`, `time_call`, `pareto_front` (test kiểm trên dữ liệu nhỏ).
2. Benchmark trong các cell `explore` của bạn:
   - 8 prompt cho một sản phẩm bạn chọn (ví dụ ảnh minh hoạ cho app tài chính của bài Advanced 01), 2 seed mỗi prompt;
   - lưới ít nhất: số bước 1, 2, 4 với `guidance_scale=0.0`, cộng 1 và 4 bước với guidance bật (`guidance_scale=2.0`);
   - mỗi cấu hình: CLIP score trung bình và độ lệch (`openai/clip-vit-base-patch32`), giây mỗi ảnh (`time_call`, đồng bộ
     CUDA), VRAM đỉnh (`torch.cuda.max_memory_allocated` sau `reset_peak_memory_stats`);
   - một **đường nền** cho CLIP score: điểm của ảnh với prompt của một ảnh **khác**, để biết khoảng cách giữa "khớp" và "không
     khớp" là bao nhiêu điểm;
   - cùng 8 prompt viết bằng tiếng Việt ở cấu hình bạn khuyên dùng: CLIP score (vẫn chấm bằng prompt tiếng Anh) và ảnh;
   - lưu ảnh, xếp lưới so sánh, tự xem; `pareto_front` theo (giây, CLIP score).
3. Viết `starter/BENCHMARK.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một BENCHMARK.md tốt**:

- Khuyến nghị cấu hình **cho một yêu cầu cụ thể** (ví dụ "dưới 1 giây trên GPU 4GB", "chạy CPU trong lúc người dùng chờ"),
  có số, ở đầu.
- Bảng đủ cột, và câu đọc bảng tách chênh lệch thật khỏi nhiễu: so chênh lệch CLIP score giữa cấu hình với độ lệch chuẩn
  giữa các ảnh và với khoảng cách tới đường nền.
- Nói thẳng CLIP score **không đo** được gì (đẹp, đúng chi tiết, chữ trong ảnh), kèm ví dụ từ ảnh bạn xem.
- Giấy phép và an toàn nội dung của model (SD-Turbo: không safety checker, không dùng thương mại).

## Tiêu chí đạt

- Mọi test pass.
- Đo đúng cách: seed ghim, khởi động trước khi đo, đồng bộ CUDA, VRAM đỉnh đo bằng PyTorch chứ không ước lượng.
- `BENCHMARK.md` không còn TODO, ít nhất 400 từ, có bảng và lưới ảnh (đường dẫn tới ảnh bạn lưu ngoài repo, hoặc mô tả).
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Nạp pipeline một lần (`AutoPipelineForText2Image.from_pretrained(..., torch_dtype=torch.float16, variant="fp16")`), tắt
thanh tiến trình, truyền `generator=torch.Generator(device).manual_seed(seed)` mỗi lần gọi. Ảnh đầu tiên luôn chậm (khởi
tạo kernel CUDA): đó là lý do `time_call` có `warmup`.

### Gợi ý 2

`CLIPModel.get_image_features` và `get_text_features` cho embedding chưa chuẩn hoá; ghép cặp ảnh với đúng prompt của nó
(lặp prompt theo số seed). Đường nền: dịch vòng mảng prompt đi vài vị trí. Đừng commit ảnh sinh ra vào repo.
