# Lời giải: phân loại review Olist bằng embedding

## Cách làm

- `tokenize`: `unicodedata.normalize("NFKD", text.lower())` tách "ã" thành "a" + dấu ngã, bỏ các ký tự
  combining, rồi `re.findall(r"[a-z]+", ...)`. Bỏ dấu gộp "não" / "nao", "péssimo" / "pessimo", rất
  phổ biến trong review gõ trên điện thoại.
- `build_vocab`: `Counter` trên token, lọc `min_freq`, sắp theo `(-tần suất, từ)` để kết quả tất định.
- `BagOfEmbeddings`: `nn.EmbeddingBag(mode="mean", padding_idx=0)` + `nn.Linear(dim, 1)`.
- `train_text_model`: vòng train của bài Basic 02 với `BCEWithLogitsLoss` (ổn định số hơn
  `sigmoid` + `BCELoss`).
- `nearest_words`: cosine trên các hàng đã chuẩn hoá.

## Kết quả thật

38 872 đơn giao xong có lời bình (41% số đơn có review); tỉ lệ review xấu trong nhóm này 23.75%, so
với 12.8% trên mọi review: khách không vui viết nhiều hơn. Theo giai đoạn: train 17 883 (21.9% xấu),
validation 8 562 (32.1%, quý 1/2018 có nhiều đơn trễ), test 12 427 (20.6%). Lời bình ngắn: trung vị 9
từ, dài nhất 45. Vocabulary train (`min_freq=2`) 4 341 mục; 3.8% token validation và 4.0% token test
là từ lạ.

| Model | Val AUC | Val PR-AUC | Test AUC | Test PR-AUC |
| --- | --- | --- | --- | --- |
| TF-IDF + logistic regression (C = 4) | 0.9419 | 0.8631 | 0.9501 | 0.8062 |
| Túi embedding, dim 32 (dừng ở epoch 2) | 0.9352 | 0.8401 | 0.9422 | 0.7647 |

Túi embedding train trong khoảng 1 giây trên CPU nhưng **thua** baseline tuyến tính trên mọi chỉ số.
Đây là kết quả bình thường: văn bản ngắn, tín hiệu nằm ở từ khoá, dữ liệu ít; TF-IDF + LR là baseline
rất mạnh cho phân loại văn bản. Deep learning thắng khi có nhiều dữ liệu hơn, khi thứ tự từ quan
trọng (phủ định: "não recomendo"), hoặc khi dùng model đã pretrain trên lượng văn bản lớn.

Embedding học được: hàng xóm gần nhất của "pessimo" là `vinil, posicao, mensagem, pensando, campos`,
của "otimo" là `solicitada, aquario, serve, ...`: vô nghĩa. Ngược lại, chiếu embedding lên trọng số
của tầng `out` cho ra danh sách rất rõ: kéo về xấu `ninguem, dinheiro, pessima, insatisfeito,
falso, ...`, kéo về tốt `rapida, atenciosa, incrivel, exatamente, parabens, amei, ...`. Model phân
loại nhị phân chỉ cần **một hướng** trong không gian embedding; các hướng còn lại không bị ràng buộc
nên không mang nghĩa. Muốn embedding có cấu trúc ngữ nghĩa thì cần mục tiêu tự giám sát (word2vec,
mục 6 lý thuyết, cho "otimo" gần "maravilhoso", "excelente") hoặc model pretrain.

## Dùng model này ở đâu

Nhãn gần như nằm sẵn trong lời bình, nên đây là model **phân loại nội dung**, không phải dự báo:
hữu ích để tự động gắn cờ review cần CSKH xử lý, đo tỉ lệ phàn nàn theo chủ đề, hoặc phát hiện review
điểm cao nhưng nội dung phàn nàn. Muốn biết trước đơn nào sẽ bị review xấu thì dùng model trên đặc
trưng đơn hàng (module 11, 12).

## Bẫy thường gặp

- Fit vocabulary hay TF-IDF trên toàn bộ dữ liệu: từ chỉ xuất hiện ở test lọt vào model.
- Chia ngẫu nhiên thay vì theo thời gian: validation 2018-Q1 có tỉ lệ xấu 32% so với 22% ở train;
  chia ngẫu nhiên che mất dịch chuyển phân phối này.
- Dùng `sigmoid` rồi `BCELoss`: tràn số khi logits lớn; dùng `BCEWithLogitsLoss`.
- Đọc hàng xóm gần nhất của embedding train cho tác vụ hẹp như thể nó là "nghĩa của từ".
