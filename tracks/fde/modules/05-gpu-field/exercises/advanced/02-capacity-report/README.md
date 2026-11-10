---
title: Báo cáo năng lực phần cứng và đề xuất runtime cho khách
level: advanced
services: []
files:
  - path: starter/capacity-report.md
    note: Khung báo cáo 5 phần
run: []
---

## Mục tiêu

Ban giám đốc nhà máy không đọc JSON benchmark. Họ cần một trang trả lời: máy hiện tại làm được gì, giới hạn ở đâu, muốn
hơn thì mua gì và tốn bao nhiêu, chọn runtime nào. Bài này viết báo cáo đó từ số đo thật của module, theo cách một FDE ký
tên chịu trách nhiệm cho từng con số.

## Đề bài

Khách: nhà máy (máy `factory`: Debian 12, 2 vCPU, 3 GB RAM, không GPU, đang chạy quillo 1.0.0 với `llm-small` cho ~15
người ở hai ca). Họ hỏi ba việc: (1) lên `llm-medium` được không; (2) nếu năm sau có ngân sách thì nên mua gì để 40 người
dùng đồng thời giờ cao điểm với câu trả lời bắt đầu hiện ra trong 2 giây; (3) phòng IT tập đoàn đề xuất "cài Ollama cho
nhanh", có nên không. Kho của tập đoàn còn một server cũ có 2 × Tesla V100 16 GB (driver 535, toolkit 1.14) có thể điều
về.

Dữ liệu bạn có: báo cáo `bench.py` của bài intermediate 01 (ca ngày và ca đêm), cấu hình `hw_config.py` chọn cho
`factory` (bài intermediate 02), công cụ của bài basic 01–03, số đo trong README module (phần 4 và 5) và (nếu làm) số đo
GPU trên PC của bạn ở bài advanced 01.

Viết `starter/capacity-report.md` gửi khách (kèm phụ lục kỹ thuật cho IT). Bài không có test; tự chấm theo rubric, đạt đủ
8 mục, rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| R1 | Phần đầu một đoạn trả lời thẳng ba câu hỏi của khách, mỗi câu một kết luận có điều kiện ("được, nếu …") |
| R2 | Năng lực hiện tại có số đo (tokens/s, RAM đỉnh, số người đồng thời) **kèm điều kiện đo** (máy, image, cờ, ngày, tải khác lúc đo) và khoảng sai số, không phải một con số trơ |
| R3 | Phân biệt rõ số đã đo với số suy ra/ước lượng (công thức định cỡ, số người dùng đồng thời), mỗi số suy ra nói nó dựa trên giả định gì |
| R4 | Rủi ro vận hành của máy hiện tại khi lên model lớn hơn (RAM trống theo ca, ảnh hưởng tới dịch vụ khác trên cùng máy) và cách giám sát/điều kiện dừng |
| R5 | Đánh giá server V100 bằng ma trận tương thích của module: CUDA/driver/toolkit nào chạy được, rủi ro bảo mật của toolkit, vòng đời card; kết luận có dùng hay không và vì sao |
| R6 | Phương án mua sắm: ít nhất hai cấu hình (GPU cụ thể, VRAM, model đề xuất), định cỡ VRAM bằng công thức (trọng số + KV cho số chuỗi đồng thời + overhead), thời gian tới token đầu ước lượng kèm giả định, giá có nguồn và ngày tra hoặc ghi rõ "cần báo giá" và ai lấy |
| R7 | Đề xuất runtime (llama.cpp / vLLM / Ollama) cho từng phương án, trả lời thẳng đề xuất "cài Ollama" của IT với lý do vận hành, không chê chung chung |
| R8 | Phụ lục cho IT: tổ hợp đã kiểm cần giữ (image + tag build, model + sha256, driver/toolkit tối thiểu), lệnh để họ tự kiểm lại máy (`nvidia-smi`, `cuda_compat.py`, `bench.py`) |

## Tiêu chí đạt

- `capacity-report.md` đạt đủ R1–R8 khi tự chấm từng mục.
- Mọi con số đo được có nguồn (bài nào, lần chạy nào); mọi phiên bản có nguồn và ngày tra; không có giá tự đoán.

## Gợi ý

### Gợi ý 1

Viết phần R1 cuối cùng, sau khi các phần khác đã có số. Đọc lại nó như một giám đốc chỉ đọc đoạn đó.

### Gợi ý 2

"40 người dùng đồng thời giờ cao điểm" và "40 request đang được sinh cùng lúc" là hai con số khác nhau. Bạn giả định tỉ lệ
nào, và hỏi khách thế nào để kiểm giả định đó?

### Gợi ý 3

V100 không phải "cũ nên bỏ": đặt nó vào bảng tương thích và bảng định cỡ trước khi kết luận.
