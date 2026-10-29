# Hướng làm: Transformer encoder cho review Olist

## Các khối

- Positional encoding: `div = 10000 ** (arange(0, d, 2) / d)`, cột chẵn `sin(pos / div)`, cột lẻ
  `cos(pos / div)`.
- Attention: `qkv(x).view(B, L, 3, h, d/h).permute(2, 0, 3, 1, 4)` tách q, k, v; mask
  `~key_padding_mask[:, None, None, :]`; `F.scaled_dot_product_attention` với `dropout_p` chỉ khi
  `self.training`; ghép head bằng `transpose(1, 2).reshape(B, L, d)`, qua `out`.
- Encoder block pre-LN: `x + drop(attn(ln1(x), mask))`, rồi `x + drop(ffn(ln2(x)))`.
- Classifier: `embed(ids) * sqrt(d) + pe[:L]` (buffer), dropout, các block, LayerNorm cuối, mean pooling
  có mask, `Linear(d, 1)`.

Pre-LN được chọn vì train ổn định hơn post-LN (bản gốc 2017) khi model sâu, thường không cần warmup
dài; đổi lại cần thêm LayerNorm cuối trước head. Nhân embedding với $$\sqrt{d}$$ để biên độ embedding
không bị positional encoding (biên độ 1) lấn át.

## Kết quả tham chiếu trên Olist

Dữ liệu và vocabulary của bài Intermediate 03 (4 341 mục, `max_len` 50). Transformer: `d_model` 64,
4 head, 2 block, `d_ff` 128, dropout 0.1, 344 961 tham số; AdamW lr 1e-3, weight decay 0.01, batch 128,
early stopping patience 2 theo val loss. CPU i7-11800H 8 luồng (máy đang chạy việc khác).

| Model | Val AUC | Val PR-AUC | Test AUC | Test PR-AUC | Test AUC, review có "nao" | Thời gian train |
| --- | --- | --- | --- | --- | --- | --- |
| TF-IDF unigram + LR | 0.9419 | 0.8631 | 0.9501 | 0.8062 | 0.8308 | dưới 1 s |
| TF-IDF unigram + bigram + LR | 0.9457 | 0.8735 | 0.9545 | 0.8169 | 0.8475 | vài giây |
| Túi embedding (dim 32) | 0.9352 | 0.8401 | 0.9422 | 0.7647 | 0.8111 | khoảng 1 s |
| Transformer, seed 0 | 0.9387 | 0.8582 | 0.9472 | 0.7906 | 0.8254 | 77 s |
| Transformer, seed 1 | 0.9351 | 0.8547 | 0.9440 | 0.7800 | 0.8195 | 68 s |
| Transformer, seed 2 | 0.9372 | 0.8516 | 0.9443 | 0.7884 | 0.8199 | 56 s |

19.1% review test có từ "nao", và 59.3% trong số đó là review xấu.

Kết luận đúng từ bảng:

- Transformer train từ đầu **hơn túi embedding một chút nhưng thua cả hai baseline TF-IDF**, trên mọi
  chỉ số, với thời gian train gấp khoảng 100 lần.
- Giả thuyết phủ định **không** được ủng hộ: trên tập "nao", Transformer (0.820–0.825) vẫn thua TF-IDF
  bigram (0.848). Bigram ("nao recebi", "nao chegou") đã bắt được phần lớn cấu trúc phủ định của văn bản
  ngắn; 18 nghìn review không đủ để Transformer tự học ngữ pháp từ đầu.
- Mọi model trên tập "nao" đều kém hơn hẳn toàn tập: đây là vùng khó thật (review hỗn hợp "não é ruim,
  mas..."), đáng là nơi đầu tư tiếp.

## Khuyến nghị tốt cho Olist

Đưa TF-IDF bigram + LR vào dùng (rẻ, giải thích được bằng trọng số từ, train lại trong vài giây). Nếu
cần tốt hơn, bước tiếp theo không phải Transformer to hơn train từ đầu mà là **model đã pretrain trên
tiếng Bồ Đào Nha** (ví dụ BERTimbau trên Hugging Face, hoặc encoder đa ngôn ngữ), fine-tune hoặc dùng
embedding câu + logistic regression; khi đó cần đo lại xem lợi ích có đáng chi phí GPU và độ trễ suy
luận không. Phần này nằm ở track AI Engineer; ở đây chỉ cần nêu đúng hướng và cách đánh giá.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Các khối và test | 20 | Test pass; giải thích pre-LN, vai trò mask, vì sao block không biết thứ tự nếu thiếu positional encoding |
| Thí nghiệm công bằng | 20 | Cùng vocabulary/chia thời gian/tập test cho mọi model; early stopping theo validation; ≥ 3 seed cho Transformer; có baseline TF-IDF (lý tưởng có bigram) |
| Báo cáo số liệu | 15 | AUC và PR-AUC trên val và test, thời gian, số tham số, phần cứng |
| Phân tích phủ định và lỗi | 20 | Kiểm giả thuyết trên tập con có "nao" bằng số; đọc vài lỗi cụ thể và phân loại nguyên nhân (nhãn nhiễu, review hỗn hợp, sai chính tả) |
| Kết luận trung thực | 15 | Không tuyên bố Transformer thắng khi số liệu không ủng hộ; tách được chênh lệch thật với dao động seed |
| Khuyến nghị | 10 | Chọn model theo lợi ích so với chi phí; nêu hướng pretrain và cách đo |

Đạt từ 70 điểm. Báo cáo chỉ có số của Transformer, không có baseline, không quá 35 điểm.
