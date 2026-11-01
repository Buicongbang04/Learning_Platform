# Lời giải: activation patching trên GPT-2 small

## Cách làm

Ba hàm patch cùng một khuôn: gắn hook lên đúng module, thay một lát activation bằng giá trị từ `source_cache`, chạy forward không
gradient, gỡ hook trong `finally`.

| Hàm | Hook | Thay gì |
| --- | --- | --- |
| `patch_resid_pre` | pre-hook trên `blocks[layer]` | `x[:, pos]` của stream trước `ln1` |
| `patch_head` | pre-hook trên `blocks[layer].attn.proj` | `z[:, pos, head]` sau khi `view(B, T, H, D)` |
| `patch_sublayer` | forward hook trên `blocks[layer].attn` hoặc `.mlp` | toàn bộ output (hook trả tensor thì tensor đó thay output) |

`resid_patching_sweep` là hai vòng lặp gọi `patch_resid_pre` và `normalized_effect`: $$(m_{\text{patched}} - m_{\text{corrupt}}) /
(m_{\text{clean}} - m_{\text{corrupt}})$$. Test dựa vào hai tính chất chính xác: ở tầng 0 hai input chỉ khác ở vị trí $$k$$, nên patch vị trí $$k$$
khôi phục đúng run clean (hiệu ứng 1) và mọi vị trí khác cho 0; attention nhân quả nên stream ở vị trí trước $$k$$ trùng nhau ở mọi tầng.
Cài sai đã thử và bị bắt: logit diff ở vị trí đầu, đảo clean/corrupt trong chuẩn hoá, patch input của `ln1` thay vì input của
Block (chỉ đổi thứ attention đọc, đường residual vẫn mang giá trị cũ), lệch vị trí một ô, patch từ `pos` tới cuối, patch cả mọi head, tách head sai thứ tự, thay input thay vì output của sublayer.

## Kết quả thật

GPT-2 small trong lớp `GPT` module 05, 32 cặp prompt `ioi_prompts(32, seed=0)`, token đầu `<|endoftext|>`, CPU 4 luồng, ngày
2026-11-01; notebook chạy 176 tới 206 giây ở ba lần chạy (PC dùng chung). Kiểm độ bền bằng một bộ 64 prompt khác (seed 0 của script tham chiếu, cùng
template): mọi kết luận dưới đây giữ nguyên, số lệch ở chữ số thứ hai.

Logit difference trung bình: clean 3.57, corrupted −3.82; clean đúng ở 100% prompt; xác suất trung bình của IO 0.386, của S 0.013.

### Residual stream theo (tầng, vị trí)

Chỉ cột S2 (vị trí 10) và cột cuối (14) khác 0:

| `resid_pre` tầng | 0–4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vị trí S2 | 1.00 | 0.99 | 0.99 | 0.95 | 0.68 | 0.05 | −0.01 | 0.00 |
| Vị trí cuối | 0.00 | 0.00 | 0.00 | 0.02 | 0.32 | 0.93 | 0.99 | 0.98 |

Thông tin quyết định nằm ở vị trí S2 tới tầng 7, chuyển sang vị trí cuối ở tầng 8–9. Nghĩa là các tầng đầu tính "S2 là tên đã
xuất hiện" tại chính vị trí S2, và các head tầng 7–8 chép thông tin đó sang vị trí cuối.

### Attention và MLP từng tầng (mọi vị trí)

| Tầng | attn denoise | mlp denoise | attn noise | mlp noise |
| --- | --- | --- | --- | --- |
| 0 | 0.03 | 0.89 | 0.97 | 0.12 |
| 3 | 0.18 | 0.01 | 0.84 | 1.01 |
| 5 | 0.40 | 0.09 | 0.62 | 0.92 |
| 7 | 0.32 | 0.01 | 0.69 | 0.98 |
| 8 | 0.58 | −0.05 | 0.43 | 1.05 |
| 9 | 0.32 | 0.04 | 0.66 | 0.96 |
| 10 | −0.16 | 0.02 | 1.15 | 0.98 |
| 11 | −0.32 | 0.02 | 1.32 | 0.97 |

(Noising: 1 là "không phá gì", thấp là phá nhiều; các tầng 1, 2, 4, 6 nhỏ ở cả hai chiều.) MLP tầng 0 có hiệu ứng 0.89: GPT-2 dùng
MLP0 như phần nối dài của embedding (token S2 được "dịch" sang biểu diễn mà các tầng sau đọc), nên patch MLP0 ở vị trí S2 gần như
bằng patch cả token. Attention tầng 10–11 âm: chúng **đẩy ngược** đáp án.

### 144 head (mọi vị trí)

Dương mạnh nhất: 5.5 = +0.33, 8.6 = +0.31, 9.9 = +0.27, 8.10 = +0.25, 7.9 = +0.21, 3.0 = +0.12, 7.3 = +0.11, 6.9 = +0.11.
Âm mạnh nhất: 10.7 = −0.46, 11.10 = −0.22, 11.2 = −0.08.

Direct logit attribution ở vị trí cuối (run clean): 9.9 = +2.92, 10.7 = −1.83, 9.6 = +1.02, 11.10 = −0.69, 10.6 = +0.40, 10.10 = +0.38,
11.2 = −0.35, 10.0 = +0.33. Từ vị trí cuối, 9.9 đặt 0.78 attention vào IO, 10.7 đặt 0.76, 9.6 đặt 0.63.

Đọc kết quả, đối chiếu với Wang và cộng sự (2022):

- **Name mover** (9.9, 9.6, 10.0): nhìn vào IO từ vị trí cuối và chép tên đó lên logit, DLA dương lớn. 9.9 có cả DLA lớn lẫn hiệu ứng
  patching lớn.
- **Negative name mover** (10.7, 11.10): cũng nhìn IO nhưng đẩy logit của nó **xuống**; patching âm, DLA âm.
- **S-inhibition** (7.3, 7.9, 8.6, 8.10): hiệu ứng patching lớn nhưng DLA nhỏ: chúng không ghi lên logit mà tác động qua head khác
  (báo cho name mover "đừng nhìn S"). DLA một mình bỏ sót cả lớp head này.
- **Induction** (5.5, 6.9) và **duplicate token** (3.0): ở vị trí S2, phát hiện "tên này đã xuất hiện", khớp với bảng residual.
- 9.6 có DLA +1.02 nhưng patch riêng nó chỉ −0.03: patch một head làm các head khác phản ứng theo (các tác giả sau gọi là
  self-repair). Bài này **chưa kiểm chứng** cơ chế đó; điều chắc chắn là "hiệu ứng patching một head" và "đóng góp trực tiếp" là
  hai câu hỏi khác nhau.
- 32 prompt, một template, một kiểu corruption: bản đồ này là bằng chứng cho hành vi **trên phân phối prompt này**. Wang và cộng
  sự dùng nhiều template, corruption "ABC" (thay cả ba tên), path patching và kiểm tính đầy đủ/tối thiểu của mạch. Muốn gọi là "mạch
  IOI" phải làm tiếp những bước đó.

## Bẫy thường gặp

- Prompt không cùng độ dài hoặc tên không phải một token: vị trí lệch giữa các prompt, bảng residual trộn lẫn.
- Dùng xác suất làm thước đo: bão hoà khi model đã chắc chắn, không cộng được qua các thành phần.
- Chỉ nhìn DLA để tìm "head quan trọng": bỏ sót head tác động gián tiếp.
- Chỉ patch theo một chiều. Denoising hỏi "đủ chưa", noising hỏi "cần không"; hai bảng khác nhau ở tầng 3, 5, 7, 8 là thông tin.
