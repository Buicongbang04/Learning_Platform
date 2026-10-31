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

Thời gian trên là thời gian làm bài. Thời gian máy của bản tham chiếu, đo trên PC RTX 3060 12GB dùng chung với một tiến
trình khác: Luong (GRU 512, 8 epoch) 2-4 phút mỗi epoch khi GPU không bị tranh, dưới 1.3 GB VRAM; Bahdanau 7-9 phút mỗi
epoch, 2.2 GB VRAM; decode beam 5 cả `tst2013` khoảng 3 phút. Cả ba cấu hình ablation tổng cộng khoảng 2.5 giờ máy. GPU
laptop 4GB đủ bộ nhớ cho cùng cấu hình (tốc độ trên laptop chưa đo lại, ước lượng chậm hơn vài lần). **Không có GPU:** train trên CPU với câu ≤ 25
token, embedding 128, hidden 256, 40-60 nghìn cặp; vẫn làm được mọi phần của bài nhưng BLEU sẽ thấp hơn nhiều (bản tham
chiếu chưa đo cấu hình này; ghi rõ trong `REPORT.md` nếu không đạt ngưỡng test).

**Lưu ý env GPU (torch 2.14):** backward của một số phép `bmm` (gặp ở attention Bahdanau) được chuyển sang kernel Triton,
cần header Python để biên dịch. Nếu gặp lỗi `Python.h: No such file or directory`, cài gói header (`sudo apt install
python3.12-dev` trên Ubuntu), hoặc tắt các kernel Triton đó ở đầu notebook bằng
`torch._native.registry.deregister_op_overrides(disable_dsl_names="triton")` (API nội bộ, bản tham chiếu dùng cách này).

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

- Mở bằng **tóm tắt có số**: "BiGRU 512 + attention <kiểu>, BPE 8k, BLEU <x> trên tst2013 (beam 5, chữ ký ...), <y> phút
  trên <GPU>". Đặt con số vào bối cảnh: model nhỏ train vài giờ không so được với hệ thống production (Google Translate)
  hay Transformer (module 05); nói rõ bạn so với cái gì.
- **Thiết lập tái lập được**: tiền xử lý, tokenizer, kiến trúc, số tham số, optimizer, epoch, seed, phần cứng, thời gian,
  chữ ký sacrebleu.
- **Đường cong học** (train loss, dev perplexity, dev BLEU theo epoch) có câu đọc hình.
- **Ablation trung thực**: chênh lệch nhỏ hơn 0.5 BLEU giữa hai lần chạy khác seed không phải là kết quả.
- **Phân tích lỗi** với ví dụ thật, và giải thích bằng cơ chế (exposure bias, nút thắt, BPE cắt tên riêng...).
- **Giới hạn và bước tiếp**: vì sao Transformer (module 05) thay thế kiến trúc này.

## Tiêu chí đạt

- `beam_search`: beam 1 trùng greedy; beam 2 thoát bẫy mà greedy mắc; chuẩn hoá độ dài đúng công thức (L tính cả `eos`);
  không mở rộng câu đã xong; chạm `max_len` khi chưa đủ câu xong thì xét cả beam sống; beam 4 không cho log-xác suất thấp
  hơn greedy trên model thử của test.
- `starter/tst2013.hyp.vi` có 1 268 dòng, BLEU (sacrebleu, `tokenize="none"`, reference đã `html.unescape`) ≥ 8.0.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng và hình (tệp hình tồn tại).
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Huấn luyện nhanh hơn nhiều khi xếp batch theo độ dài câu nguồn (ít padding) rồi xáo **thứ tự các batch**. Attention Luong
không có input feeding cho phép chạy decoder GRU cả chuỗi một lần khi teacher forcing (Intermediate 03); Bahdanau phải lặp
từng bước nên mỗi epoch chậm hơn vài lần (bản tham chiếu: 2-4 lần). Lưu checkpoint tốt nhất theo dev BLEU (greedy, nhanh) sau mỗi epoch.

### Gợi ý 2

Bọc model thành `step_fn` cho `beam_search` bằng cách mã hoá câu nguồn một lần, rồi với mỗi tiền tố chạy decoder từ
`<bos>` (đơn giản, chậm) hoặc giữ cache state theo tiền tố (nhanh). Beam 5 từng câu một trên GPU cho 1 268 câu mất khoảng
3 phút ở bản tham chiếu. BPE của `tokenizers` với `WhitespaceSplit` + `end_of_word_suffix="</w>"` và decoder
`BPEDecoder` cho lại đúng chuỗi token cách nhau bằng dấu cách như reference.
