# Từ GPT-2 tới Llama: ablation trên GPT mini tiếng Việt

TODO: viết theo khung dưới đây (ít nhất 500 từ).

## Tóm tắt

TODO: 3-4 câu. Bản đầy đủ hơn GPT-2 bao nhiêu bpc, thành phần nào đóng góp rõ, thành phần nào chưa phân biệt được với nhiễu,
KV cache nhanh hơn bao nhiêu lần.

## Thiết lập

TODO: dữ liệu, tokenizer, kích thước model, số bước, batch, learning rate, seed, phần cứng, cách đánh giá (cửa sổ trượt, bpc).

## Ablation

TODO: bảng: cấu hình, tham số, bpc seed 0, bpc seed 1 (ít nhất cho vài dòng), chênh lệch so với bản đầy đủ, thời gian.
Diễn giải: chênh lệch nào lớn hơn độ dao động giữa các seed.

## KV cache

TODO: bảng thời gian sinh có và không cache; công thức và bảng bộ nhớ cache cho vài model thật (MHA so với GQA).

## Giới hạn

TODO: quy mô nhỏ, một ngân sách, số seed; điều gì có thể đổi ở quy mô lớn.
