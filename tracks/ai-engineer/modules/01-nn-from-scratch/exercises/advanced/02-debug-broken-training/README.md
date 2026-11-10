---
title: Gỡ lỗi vòng train hỏng mà không báo lỗi
level: advanced
services: []
files:
  - path: starter/broken.ipynb
    note: 4 bug im lặng, không nói ở đâu
  - path: starter/BUGS.md
    note: Ghi lại từng bug
  - path: tests/test_broken.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/01-nn-from-scratch/exercises/advanced/02-debug-broken-training/starter/broken.ipynb
  - uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/advanced/02-debug-broken-training -q
---

## Mục tiêu

Luyện kỹ năng mà phần lớn thời gian của AI Engineer dành cho: model không học, không có exception nào, và
bạn phải khoanh vùng bằng phép đo chứ không đoán. Làm xong bạn có một quy trình gỡ lỗi dùng lại được cho
vòng train PyTorch thật.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Thời gian trên là thời gian điều tra; mỗi lần chạy `train` dưới 1 giây.

`starter/broken.ipynb` là MLP numpy (2 tầng ẩn 64 neuron) phân loại 3 nhánh xoắn ốc bằng SGD momentum, kèm
một hàm gradient check. Notebook chạy hết không lỗi nhưng `train(seed)` chỉ đạt khoảng 33% test accuracy và
`gradient_check_passes()` trả `False`. Trong notebook có **4 bug "im lặng"** cố ý, mỗi bug một chỗ. Đề không
nói chúng nằm ở đâu.

1. Tìm và sửa cả 4 bug ngay trong notebook. Không đổi `make_spirals` và siêu tham số mặc định của `train`
   (`epochs=60, lr=0.05, batch_size=32, momentum=0.9`): sửa ở gốc, không bù triệu chứng.
2. Mỗi giả thuyết phải có phép thử. Dùng quy trình ở mục 7 phần lý thuyết: loss ở bước 0 so với $$\ln C$$,
   gradient check theo từng tham số, overfit một batch nhỏ, log loss và norm gradient theo bước, đếm ReLU
   chết, và kiểm từng giả định của pipeline dữ liệu và của tham số. Thêm cell `explore` tuỳ ý.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với **triệu chứng** (con số cụ thể),
   **cách phát hiện** (phép thử nào khoanh vùng, nó cho kết quả gì) và **sửa** (dòng trước và sau). Cuối
   cùng ghi thứ tự bạn gỡ và bug nào che bug nào.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `train(seed)` đạt test accuracy ≥ 0.95 với seed 0, 1, 2 (bản đã sửa: 0.998 tới 1.000).
- `gradient_check_passes()` là `True`, và một gradient check độc lập trong test (MLP khác cỡ, batch khác)
  khớp sai phân hữu hạn trên mọi phần tử mọi tham số.
- `make_spirals` và siêu tham số mặc định của `train` không đổi.
- `BUGS.md` không còn TODO, ít nhất 4 mục `## Bug N`, ít nhất 250 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`: đủ 4 bug, mỗi bug có bằng chứng đo được.

## Gợi ý

### Gợi ý 1

Tách hai câu hỏi: gradient có đúng không (gradient check, không cần train), và vòng train có dùng gradient
đúng cách không (dữ liệu, optimizer, trạng thái giữa các bước). Gradient check qua chưa có nghĩa là vòng train
đúng.

### Gợi ý 2

In tỉ lệ `norm(giải tích) / norm(số)` cho từng tham số: một tỉ lệ nguyên đều nhau ở mọi tham số và chỉ vài
tham số lệch là hai bệnh khác nhau. Sửa xong mỗi bug, chạy lại toàn bộ các phép thử: bug này có thể che
triệu chứng của bug khác. Đọc lại vòng train như đọc một vòng train PyTorch và hỏi: trạng thái nào được giữ
lại giữa hai bước, và có nên giữ không?
