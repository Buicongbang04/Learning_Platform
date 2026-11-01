---
title: Activation patching trên GPT-2 small (indirect object identification)
level: intermediate
services: []
files:
  - path: starter/patching.ipynb
    note: 6 hàm TODO
  - path: tests/test_patching.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/02-activation-patching-ioi/starter/patching.ipynb
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/02-activation-patching-ioi -q
---

## Mục tiêu

Đi từ tương quan sang nhân quả: dựng cặp prompt clean/corrupted chỉ khác một token, chọn một thước đo (logit difference), rồi
patch activation từ run này sang run kia theo tầng, vị trí, sublayer và từng head để tìm đường thông tin đi trong GPT-2 small
khi nó điền tên người nhận ("When Mary and John went to the store, John gave a drink to" → " Mary"). Làm xong bạn biết dựng một
thí nghiệm patching đúng, đọc được bảng kết quả, và nói được nó chứng minh gì, chưa chứng minh gì.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Notebook lời giải chạy khoảng 3 phút trên CPU 4 luồng (176 tới 206 giây, PC dùng chung), nhanh hơn
nhiều nếu chạy bằng kernel `ai-gpu`. Cần bài Basic 01 (`run_with_cache`) và bài Intermediate 01 (`gpt2_into_gpt_mini`); chưa xong
thì notebook tự dùng lời giải. Đọc mục 5 phần lý thuyết. Mở `starter/patching.ipynb`:

1. `logit_diff(logits, io, s)` và `normalized_effect(patched, clean, corrupt)`.
2. `patch_resid_pre(model, idx, source_cache, layer, pos=None)`: thay residual stream đi vào một Block ở một vị trí (hoặc mọi vị
   trí) bằng giá trị trong cache của run kia.
3. `patch_head(model, idx, source_cache, layer, head, pos=None)`: chỉ thay output của một head.
4. `patch_sublayer(model, idx, source_cache, kind, layer)`: thay output của attention hoặc MLP một tầng.
5. `resid_patching_sweep(...)`: bảng hiệu ứng chuẩn hoá theo (tầng, vị trí).

Hàm tạo prompt `ioi_prompts` cho sẵn. Rồi chạy các cell `explore`: 32 cặp prompt, bảng residual, bảng attention/MLP (denoising và
noising), bảng 144 head, direct logit attribution của từng head kèm nơi head đó nhìn. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `logit_diff` chỉ dùng vị trí cuối; `normalized_effect` bằng 0 ở run corrupted và 1 ở run clean.
- Patch residual ở tầng 0 đúng vị trí khác nhau khôi phục **đúng** run clean; vị trí trước chỗ patch không đổi; patch ở vị trí mà
  hai run trùng nhau không đổi gì.
- `patch_head` và `patch_sublayer` khớp bản tính tay trong test (đúng head, đúng vị trí, output chứ không phải input); mọi hook được gỡ.
- `resid_patching_sweep` có hàng tầng 0 bằng 1 đúng ở vị trí khác nhau và 0 ở chỗ khác, cột trước vị trí đó bằng 0 ở mọi tầng.
- Cell `explore` chạy hết; logit difference của run clean dương ở mọi prompt.

## Gợi ý

### Gợi ý 1

Viết `patch_resid_pre` bằng một forward pre-hook trả về input đã sửa (pre-hook trả tuple thì tuple đó thay input). `x[:, pos] =
...` trên một bản clone để không sửa tensor đang dùng ở chỗ khác. Ba hàm patch giống nhau tới 80%: chỉ khác module gắn hook, loại
hook và khoá cache.

### Gợi ý 2

Trước khi chạy trên GPT-2, kiểm hàm của bạn bằng chính tính chất trong test: hai input khác nhau ở một vị trí, patch tầng 0 ở vị trí
đó phải cho logits **giống hệt** run kia. Nếu bảng residual của GPT-2 có giá trị khác 0 ở cột trước vị trí S2, hook của bạn đang
patch sai chỗ.
