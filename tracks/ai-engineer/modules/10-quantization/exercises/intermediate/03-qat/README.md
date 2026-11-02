---
title: Quantization-aware training cho GPT mini
level: intermediate
services: []
files:
  - path: starter/qat.ipynb
    note: 4 hàm/lớp TODO
  - path: tests/test_qat.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/10-quantization/exercises/intermediate/03-qat/starter/qat.ipynb
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/intermediate/03-qat -q
---

## Mục tiêu

Biến GPT mini thành model QAT (fake quantization trong forward, STE trong backward), fine-tune một chút, đóng băng thành model
int thật, và trả lời bằng thí nghiệm có đối chứng: QAT thắng PTQ bao nhiêu ở 2 bit, và bao nhiêu trong đó là nhờ QAT chứ
không phải nhờ được train thêm.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Thời gian trên là thời gian làm bài. Thời gian máy chạy hết notebook lời giải: khoảng 8 phút trên CPU (4 luồng, checkpoint cấu
hình PC, 120 bước); khoảng 2 phút trên GPU dùng chung (kernel `ai-gpu`, 300 bước, đủ 100 bài validation).

Checkpoint như bài Intermediate 01. Trong `starter/qat.ipynb`:

1. `fake_quant_ste(w, bits, group_size)`: fake quantization đối xứng theo nhóm, gradient đi thẳng (STE).
2. `QATLinear(linear, bits, group_size)`: bọc một `nn.Linear`, dùng chính tham số của nó.
3. `prepare_qat(model, bits, group_size)`: bản sao với mọi `nn.Linear` (trừ `lm_head` dùng chung embedding) thành `QATLinear`.
4. `convert_qat(model)`: bản sao với mọi `QATLinear` thành `nn.Linear` có trọng số đã quantize.

Rồi chạy các cell `explore`: PTQ int2 nhóm 32, QAT, và đối chứng (fine-tune float32 cùng ngân sách rồi PTQ), cùng đường loss.
Cuối cùng làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `fake_quant_ste` đúng giá trị forward theo nhóm, gradient theo `w` bằng đúng gradient phía sau (scale không nhận gradient).
- `QATLinear` dùng chung `Parameter` với lớp được bọc, forward đúng, gradient tới trọng số.
- `prepare_qat` không sửa model gốc, thay đúng 4 lớp mỗi khối, giữ `lm_head` dùng chung, không đổi số tham số; model chuẩn bị
  xong học được qua STE.
- `convert_qat` trả bản sao không còn `QATLinear`, trọng số nằm đúng trên lưới lượng tử, output khớp model QAT.

## Gợi ý

### Gợi ý 1

STE đồng nhất viết gọn được bằng một dòng với `.detach()`: giá trị forward là bản đã quantize, còn đồ thị autograd chỉ thấy
`w`. Kiểm bằng cách so gradient với gradient phía sau trên một tensor nhỏ.

### Gợi ý 2

Thay module con trong một cây `nn.Module`: duyệt `parent.named_children()` cho mọi `parent` trong `model.modules()`, rồi
`setattr(parent, tên, module_mới)`. Lấy danh sách trước khi sửa (`list(...)`), và kiểm `type(child) is nn.Linear` để không bọc
lại thứ đã bọc.
