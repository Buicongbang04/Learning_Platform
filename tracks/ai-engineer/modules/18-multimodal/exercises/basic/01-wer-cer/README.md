---
title: WER và CER cho tiếng Việt, tự viết và đối chiếu jiwer
level: basic
services: []
files:
  - path: starter/asr_metrics.py
    note: 4 hàm TODO
  - path: tests/test_asr_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/basic/01-wer-cer -q
---

## Mục tiêu

Tự viết hai thước đo mà mọi thí nghiệm speech của module dùng (Whisper trên FLEURS, vòng TTS → STT): Word Error Rate
và Character Error Rate. Làm xong bạn biết vì sao cùng một bản nhận dạng có thể cho WER khác nhau tuỳ cách chuẩn hoá và
cách lấy trung bình, và vì sao với tiếng Việt nên báo cả CER.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/asr_metrics.py`, chỉ dùng thư viện chuẩn, viết:

1. `normalize_vi(text) -> str`: chuẩn hoá Unicode về **NFC**, chữ thường, thay mọi ký tự dấu câu và ký hiệu (nhóm
   Unicode `P*` và `S*`) bằng khoảng trắng, rồi gộp mọi khoảng trắng liên tiếp thành một dấu cách, bỏ ở hai đầu. Giữ
   nguyên dấu thanh và chữ số ("60.000" thành "60 000").
2. `edit_counts(ref, hyp) -> dict`: với hai danh sách token, trả `{"S": ..., "D": ..., "I": ..., "N": len(ref)}` của
   **một** alignment có tổng $$S + D + I$$ nhỏ nhất (khoảng cách Levenshtein, mỗi phép giá 1). Khi có nhiều alignment
   tối ưu, chọn cái nào cũng được, miễn số đếm nhất quán với alignment đó.
3. `wer(refs, hyps) -> float`: WER **mức corpus** theo mục 3 lý thuyết,
   $$\mathrm{WER} = \frac{\sum_u (S_u + D_u + I_u)}{\sum_u N_u}$$, token là từ (tách theo khoảng trắng) sau
   `normalize_vi` ở **cả hai** phía.
4. `cer(refs, hyps) -> float`: cùng công thức, token là **ký tự** của chuỗi đã chuẩn hoá, tính cả dấu cách.

Ném `ValueError` khi số câu hai bên khác nhau, hoặc tổng số token tham chiếu (sau chuẩn hoá) bằng 0. WER không bị chặn
ở 1: model chèn nhiều từ thừa thì WER vượt 1.

## Tiêu chí đạt

- `normalize_vi` khớp các ví dụ của test (NFD, ngoặc kép cong, gạch nối, chữ hoa có dấu).
- `edit_counts` khớp ví dụ tính tay, và trên 200 cặp ngẫu nhiên tổng $$S + D + I$$ bằng của `jiwer`, số đếm khớp độ
  dài hai chuỗi.
- `wer` là trung bình mức corpus, không phải trung bình WER từng câu; `wer` và `cer` khớp `jiwer.wer`/`jiwer.cer`
  trên văn bản đã chuẩn hoá.
- Đầu vào sai ném `ValueError`.

## Gợi ý

### Gợi ý 1

`unicodedata.category(ch)` trả mã hai chữ như `"Po"`, `"Ps"`, `"Sc"`, `"Zs"`; chữ đầu là nhóm. Chuẩn hoá NFC **trước**
khi xét từng ký tự: ở dạng NFD dấu thanh là ký tự riêng (nhóm `M`), xét trước thì dễ xoá nhầm.

### Gợi ý 2

Bảng quy hoạch động $$(n + 1) \times (m + 1)$$ có thể lưu ở mỗi ô cả tổng lỗi lẫn bộ ba $$(S, D, I)$$ đi kèm; so
sánh các bộ theo tổng trước. Hàng 0 và cột 0 là trường hợp chỉ có insertion hoặc chỉ có deletion.
