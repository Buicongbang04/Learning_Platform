# Lời giải: sampling trên logits

## Cách làm

**`softmax`** chia logits cho $$T$$, trừ `max`, rồi `exp` và chuẩn hoá. Trừ `max` đưa logit lớn nhất về 0 nên `exp`
không tràn (logit 1 000 cho `inf` nếu không trừ, rồi `inf / inf = nan`), và `exp(-inf) = 0` tự xử lý token đã lọc.

**`greedy`** là `int(np.argmax(logits))`: `argmax` trả chỉ số đầu tiên khi bằng nhau, đúng yêu cầu.

**`top_k_filter`** lấy giá trị lớn thứ $$k$$ bằng `np.sort(out)[-k]` rồi đặt `-inf` cho mọi logit **nhỏ hơn** nó.
So sánh `<` (không phải lấy đúng $$k$$ chỉ số bằng `argsort`) giữ mọi token bằng logit thứ $$k$$, giống
`TopKLogitsWarper` của Hugging Face.

**`top_p_filter`** sắp xác suất giảm dần bằng `np.argsort(-probs, kind="stable")`, lấy `cumsum`, và
`np.searchsorted(cum, p)` cho vị trí đầu tiên tổng $$\ge p$$; số token giữ là vị trí đó cộng 1. Lỗi hay gặp: giữ
các token có `cum < p`, bỏ mất token làm tổng chạm $$p$$ (với $$p = 0.75$$ chỉ còn 1 token thay vì 2).

**`apply_repetition_penalty`** lấy `np.unique(generated)` để mỗi token phạt một lần, rồi
`np.where(v > 0, v / penalty, v * penalty)`. Chỉ chia (bỏ nhánh âm) làm logit âm **tăng** về phía 0, tức là
thưởng cho lặp lại thay vì phạt.

**`apply_presence_frequency`** đếm bằng `np.bincount(generated, minlength=V)` và trừ
`presence * (count > 0) + frequency * count`.

**`sample_next`** theo thứ tự penalty, greedy nếu $$T = 0$$ (trả trước khi đụng `rng`, nên trạng thái `rng` không
đổi), chia $$T$$, top-k, top-p, softmax, `rng.choice`.

## Vì sao thứ tự này

- **Penalty trước greedy**: repetition penalty phải tác động cả khi giải mã greedy, nếu không greedy lặp vòng
  ("Hà Nội là Hà Nội là...") đúng ở chỗ penalty được dùng để chữa.
- **Temperature trước top-p**: Hugging Face áp `TemperatureLogitsWarper` rồi mới `TopKLogitsWarper`,
  `TopPLogitsWarper`. Hệ quả: temperature cao vừa làm phẳng phân phối vừa **mở rộng** nucleus, hai hiệu ứng cộng
  dồn. Test `test_temperature_applied_before_top_p` bắt đúng chỗ này: đảo thứ tự thì token thứ 3 không bao giờ
  được chọn.
- Top-k trước top-p: top-p tính trên phân phối đã chuẩn hoá lại trong $$k$$ token còn lại.

## Đối chiếu với model thật

`generation_config.json` của `Qwen/Qwen2.5-0.5B-Instruct` ghi `temperature 0.7, top_p 0.8, top_k 20,
repetition_penalty 1.1`: nhà phát hành khuyên sampling khá "chặt". Hai kiểu penalty khác nhau về bản chất:

| | Repetition penalty (HF, CTRL) | Presence / frequency (OpenAI) |
| --- | --- | --- |
| Phép toán | nhân/chia logit | trừ một hằng số |
| Phụ thuộc số lần lặp | không (một lần) | frequency: có, tuyến tính |
| Giá trị "tắt" | 1.0 | 0.0 |
| Ollama | `repeat_penalty` (mặc định 1.1 trong `llama.cpp` trên `repeat_last_n` = 64 token cuối) | `presence_penalty`, `frequency_penalty` |

Penalty phạt **mọi** token đã xuất hiện, kể cả dấu câu và từ chức năng ("của", "là"), nên đặt cao (1.5 trở lên) làm
câu văn tiếng Việt méo đi nhanh hơn tiếng Anh.
