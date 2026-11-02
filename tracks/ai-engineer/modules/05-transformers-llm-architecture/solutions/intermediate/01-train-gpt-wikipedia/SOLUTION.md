# Lời giải: train GPT mini trên Wikipedia tiếng Việt

## Các hàm

| Hàm | Cài đặt | Điểm dễ sai |
| --- | --- | --- |
| `long_articles` | đọc cột `text`, lọc `len(t) >= min_chars` trên chuỗi gốc, rồi NFC | lọc sau NFC thì bài viết ở dạng NFD (dài hơn khi chưa chuẩn hoá) bị loại, tập dữ liệu lệch module 04 |
| `split_articles` | `np.random.RandomState(seed).permutation(n)` | `default_rng(seed)` cho hoán vị khác: tập validation khác, bpc không còn so được với module 04 |
| `get_batch` | `torch.randint(len(data) - block_size, ...)`, `x = data[s:s+T]`, `y = data[s+1:s+T+1]` | cận trên trừ thêm 1 thì không bao giờ lấy cửa sổ cuối |
| `lr_at` | warmup `(step + 1) / warmup`, cosine từ max về min | warmup từ 0 cho bước đầu lr = 0 (bước bị phí); cosine về 0 thay vì `min_lr` |
| `configure_optimizer` | nhóm `dim() >= 2` chịu decay, còn lại 0; `betas=(0.9, 0.95)` | decay cả LayerNorm và bias kéo chúng về 0, không có lý do; beta2 0.999 phản ứng chậm với gradient đổi nhanh của LLM |
| `sliding_windows` | xem dưới | |
| `evaluate_nll` | gom cửa sổ theo độ dài, `cross_entropy(..., reduction="none")`, cộng `n_new` vị trí cuối | cộng cả cửa sổ: target bị đếm nhiều lần; lấy `n_new` vị trí **đầu**: tính lại target cũ với ít ngữ cảnh |
| `nll_to_metrics` | như module 04 | quên $$\ln 2$$ |

`sliding_windows`: giữ `scored` = số target đã tính. Cửa sổ bắt đầu ở `start` (0, stride, 2·stride, ...), kết thúc ở
`end = min(start + block_size, n_tokens - 1)`, đóng góp `end - scored` target cuối, rồi `scored = end`. Với
`n = 21, block = 8, stride = 4`: `(0, 8, 8), (4, 12, 4), (8, 16, 4), (12, 20, 4)`, tổng 20 target. Target đóng góp bởi cửa sổ
thứ hai trở đi nằm ở vị trí `block - stride .. block - 1` của cửa sổ, nên có ít nhất `block - stride` token ngữ cảnh.

## Kết quả của notebook lời giải

Dữ liệu: 5 413 bài dài, train 6 432 422 ký tự (1 825 605 token BPE 8 000), validation 664 568 ký tự (190 923 token, 3.48 ký tự mỗi
token), đúng như module 04.

| Model | Tham số | Ngân sách | Thời gian train | Perplexity theo token | bpc |
| --- | --- | --- | --- | --- | --- |
| GPT mini CPU (`n_embd` 128, 4 tầng) | 1.83 triệu | 1 500 bước × 32 × 128 = 6.1 triệu token | 8.3 phút, CPU 4 luồng | 164.5 | 2.115 |
| GPT mini GPU (`n_embd` 256, 4 tầng) | 5.24 triệu | 3 000 bước × 32 × 128 = 12.3 triệu token | RTX 3060, 3.2 phút | 98.2 | 1.901 |
| LSTM 2 tầng 512 (module 04, Advanced 02) | 9.83 triệu | 3 000 bước × 32 × 128 | 1.9 phút, RTX 3060 | 117.0 | 1.975 |

Ở cùng ngân sách (dòng GPU), Transformer một nửa số tham số đã vượt LSTM. Bản CPU nhỏ hơn và chỉ train một nửa số bước nên còn
kém: so sánh luôn phải kèm ngân sách. Loss theo vị trí trong cửa sổ (bản CPU) giảm từ 5.66 ở vị trí 0 xuống khoảng 5.0-5.1 sau
vài chục vị trí, có nhiễu: model nhỏ dùng ngữ cảnh ngắn là chủ yếu. Văn bản sinh greedy rơi vào vòng lặp ("và các thành viên,
và các thành viên, ..."), temperature 0.8 + top-k 40 ra câu đúng chính tả nhưng ghép tên riêng vô nghĩa, temperature 1.2 sinh
âm tiết không có thật.

## Bẫy thường gặp

- Đánh giá bằng khúc rời không chồng lấn (stride bằng block): token đầu mỗi khúc gần như không có ngữ cảnh, perplexity xấu hơn
  cửa sổ trượt; hai con số đo theo hai cách không so được với nhau.
- Đánh giá trong chế độ train (dropout bật) hoặc quên trả lại chế độ train sau khi đánh giá giữa chừng.
- So perplexity theo token với LSTM byte của module 04: khác tokenizer, chỉ so bằng bpc.
