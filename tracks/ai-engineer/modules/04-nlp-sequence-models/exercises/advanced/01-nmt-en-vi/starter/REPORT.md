# Dịch máy Anh-Việt: seq2seq + attention trên IWSLT'15

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp chưa xem
code: họ cần biết bạn làm gì, đạt bao nhiêu, và bạn hiểu vì sao.

## Tóm tắt

TODO: 3-4 câu. Model, tokenizer, BLEU/chrF trên tst2013, thời gian train trên máy gì, phát hiện quan trọng nhất.

## Dữ liệu và tiền xử lý

TODO: số cặp, lọc độ dài, html.unescape, BPE (vocab, token mỗi từ), dev/test dùng thế nào.

## Kiến trúc và thiết lập

TODO: sơ đồ hoặc bảng: encoder, attention, decoder, số tham số; optimizer, lr, batch, dropout, epoch, seed, GPU, thời
gian, chữ ký sacrebleu.

## Đường cong học

TODO: hình (vd. `![Đường cong](curves.png)`) và câu đọc hình: train loss, dev perplexity, dev BLEU theo epoch.

## Ablation

TODO: bảng: không attention / Luong / Bahdanau; greedy / beam 5; biến thể của bạn. Cùng ngân sách epoch. Diễn giải.

## Phân tích lỗi

TODO: BLEU theo nhóm độ dài câu nguồn; 5 ví dụ dịch sai có giải thích; một attention heatmap.

## Giới hạn và bước tiếp theo

TODO: còn thiếu gì, kết quả nói được gì và không nói được gì, vì sao Transformer (module 05) thay thế kiến trúc này.
