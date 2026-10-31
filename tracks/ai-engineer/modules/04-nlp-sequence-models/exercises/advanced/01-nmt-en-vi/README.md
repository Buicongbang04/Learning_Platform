---
title: Dịch máy Anh-Việt với BPE, attention và beam search (portfolio)
level: advanced
services: []
files:
  - path: starter/nmt.ipynb
    note: 1 hàm chấm (beam_search), còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_nmt.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv sync --project setup/gpu
  - uv run jupyter lab tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/advanced/01-nmt-en-vi/starter/nmt.ipynb
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/advanced/01-nmt-en-vi -q
---

## Mục tiêu

Xây một hệ dịch máy thần kinh Anh-Việt hoàn chỉnh trên toàn bộ IWSLT'15 (133 317 cặp câu TED): tokenizer BPE, seq2seq với
attention, chọn checkpoint theo dev, beam search có chuẩn hoá độ dài, đánh giá bằng sacrebleu, ablation và phân tích lỗi.
Đây là bài portfolio: `REPORT.md` phải đọc được với người chưa mở notebook, và mọi kết luận phải có số.

## Đề bài

**Phần cứng:** GPU 4GB · ~600 phút

Thời gian trên là thời gian làm bài. Thời gian máy: bản tham chiếu (GRU 512, Luong, 8 epoch) mất khoảng 45 phút train trên
RTX 3050 Laptop 4GB dùng chung với tiến trình khác (5-7 phút mỗi epoch, dưới 1.5 GB VRAM), cộng 2 phút decode. Mỗi cấu hình
ablation tốn thêm chừng đó. **Không có GPU:** train trên CPU với câu ≤ 25 token, embedding 128, hidden 256, dữ liệu
40-60 nghìn cặp; vẫn làm được mọi phần của bài, nhưng BLEU sẽ thấp hơn ngưỡng của test (ghi rõ trong `REPORT.md`).

1. Trong `starter/nmt.ipynb`, viết `beam_search` theo đặc tả trong notebook (hàm duy nhất được test chấm). Nó nhận một
   `step_fn` trả log-xác suất, nên test chạy trên model giả, không cần GPU.
2. Dựng pipeline của bạn (bố cục gợi ý trong notebook): `html.unescape`, BPE (`tokenizers`, vocab cỡ 8k mỗi ngôn ngữ),
   seq2seq attention (tái dùng Intermediate 03, lớn hơn), train trên GPU, chọn checkpoint theo BLEU trên `tst2012`.
3. Decode `tst2013` (1 268 câu) bằng model tốt nhất, ghi **đúng một dòng mỗi câu** vào `starter/tst2013.hyp.vi` (chữ hoa
   giữ nguyên, token cách nhau bằng dấu cách như reference). Báo cáo BLEU (`tokenize="none"`) và chrF kèm chữ ký sacrebleu.
4. Ablation, mỗi dòng cùng ngân sách epoch: không attention vs Luong vs Bahdanau; greedy vs beam 5; ít nhất một biến thể
   của bạn (vocab BPE, độ sâu, dropout, alpha...). Phân tích lỗi: BLEU theo nhóm độ dài câu nguồn, 5 bản dịch sai đáng chú
   ý (bịa nội dung, lặp từ, bỏ sót), một attention heatmap.
5. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` portfolio tốt** đọc trong 5 phút:

- Mở bằng **tóm tắt có số**: "GRU 512 + attention Luong, BPE 8k, BLEU 11.6 trên tst2013 (beam 5), 45 phút trên GPU
  laptop 4GB". Đặt con số vào bối cảnh: model nhỏ train một giờ không so được với hệ thống production (Google Translate)
  hay Transformer (module 05); nói rõ bạn so với cái gì.
- **Thiết lập tái lập được**: tiền xử lý, tokenizer, kiến trúc, số tham số, optimizer, epoch, seed, phần cứng, thời gian,
  chữ ký sacrebleu.
- **Đường cong học** (train loss, dev perplexity, dev BLEU theo epoch) có câu đọc hình.
- **Ablation trung thực**: chênh lệch nhỏ hơn 0.5 BLEU giữa hai lần chạy khác seed không phải là kết quả.
- **Phân tích lỗi** với ví dụ thật, và giải thích bằng cơ chế (exposure bias, nút thắt, BPE cắt tên riêng...).
- **Giới hạn và bước tiếp**: vì sao Transformer (module 05) thay thế kiến trúc này.

## Tiêu chí đạt

- `beam_search`: beam 1 trùng greedy; beam 2 thoát bẫy mà greedy mắc; chuẩn hoá độ dài đúng công thức (L tính cả `eos`);
  không mở rộng câu đã xong; trả beam sống khi chạm `max_len`; beam 4 không bao giờ cho log-xác suất thấp hơn greedy.
- `starter/tst2013.hyp.vi` có 1 268 dòng, BLEU (sacrebleu, `tokenize="none"`, reference đã `html.unescape`) ≥ 8.0.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng và hình (tệp hình tồn tại).
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Huấn luyện nhanh hơn nhiều khi xếp batch theo độ dài câu nguồn (ít padding) rồi xáo **thứ tự các batch**. Attention Luong
không có input feeding cho phép chạy decoder GRU cả chuỗi một lần khi teacher forcing (Intermediate 03); Bahdanau phải lặp
từng bước nên chậm hơn khoảng 2-3 lần mỗi epoch. Lưu checkpoint tốt nhất theo dev BLEU (greedy, nhanh) sau mỗi epoch.

### Gợi ý 2

Bọc model thành `step_fn` cho `beam_search` bằng cách mã hoá câu nguồn một lần, rồi với mỗi tiền tố chạy decoder từ
`<bos>` (đơn giản, chậm) hoặc giữ cache state theo tiền tố (nhanh). Beam 5 từng câu một trên GPU cho 1 268 câu mất khoảng
1.5 phút ở bản tham chiếu. BPE của `tokenizers` với `WhitespaceSplit` + `end_of_word_suffix="</w>"` và decoder
`BPEDecoder` cho lại đúng chuỗi token cách nhau bằng dấu cách như reference.
