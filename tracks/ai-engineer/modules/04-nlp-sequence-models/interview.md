# Câu hỏi phỏng vấn: NLP & Sequence Models

## BPE hoạt động thế nào? Vì sao LLM dùng BPE byte-level thay vì từ hay ký tự?

BPE học một danh sách merge: bắt đầu từ đơn vị nhỏ nhất (byte), đếm mọi cặp đứng cạnh nhau trong dữ liệu train, gộp cặp
nhiều nhất thành token mới, lặp tới khi đủ vocab. Encode một chuỗi mới là áp lại các merge theo **đúng thứ tự đã học**
(cặp có thứ hạng thấp nhất trước), không phải khớp tham lam từ trái.

Từ-level cần vocab khổng lồ và vẫn gặp từ lạ (`<unk>`); ký tự-level không có từ lạ nhưng chuỗi dài gấp nhiều lần, attention
đắt theo bình phương độ dài. Subword nằm giữa: từ phổ biến là một token, từ hiếm cắt thành mảnh. Bắt đầu từ **byte** thay
vì ký tự Unicode thì vocab cơ sở đúng 256, mọi chuỗi (emoji, chữ Hán, code, rác) đều mã hoá được, không bao giờ `<unk>`.

Chi tiết ứng viên senior nên nói: pretokenize bằng regex để merge không vượt ranh giới từ; token có thể là nửa ký tự UTF-8
nên phải giải mã sau khi nối bytes; vocab lớn làm chuỗi ngắn đi nhưng embedding và lớp output to lên, token hiếm học ít.

## Tiếng Việt có những vấn đề gì riêng với tokenization?

Bốn vấn đề, đều có số đo trong module:

- **Unicode NFC/NFD**: "ế" có thể là một code point hoặc ba (e + mũ + sắc). "Tiếng Việt có dấu" dài 17 code point ở NFC,
  24 ở NFD. Không chuẩn hoá NFC ở mọi cửa vào thì cùng một chữ thành hai chuỗi byte khác nhau.
- **Kiểu đặt dấu thanh**: "hoà" và "hòa" vẫn khác nhau sau NFC. IWSLT dùng toàn kiểu cũ (808 lần "hoà", 0 lần "hòa"),
  Wikipedia gần như toàn kiểu mới (35 so với 702).
- **Âm tiết khác từ**: khoảng trắng tách âm tiết ("học sinh" là một từ hai âm tiết). Hoặc dùng công cụ tách từ (PhoBERT
  bắt buộc), hoặc để subword/mô hình tự học, hoặc ghép cụm thống kê như word2vec phrases.
- **Thuế token**: cùng nội dung TED, `gpt2` tốn 4.3 lần token cho tiếng Việt so với tiếng Anh, `cl100k_base` 2.38 lần,
  `o200k_base` 1.38 lần. Thuế token nhân thẳng vào chi phí API, độ trễ và chiếm context.

## Một khách hàng phàn nàn chatbot tiếng Việt của bạn "đắt và hay quên ngữ cảnh" hơn bản tiếng Anh. Bạn điều tra thế nào?

Nghi phạm đầu tiên là tokenizer. Đo số token trên **dữ liệu thật** của khách (log hội thoại) cho cả hai ngôn ngữ với
tokenizer của model đang dùng. Nếu tiếng Việt tốn 2-4 lần token thì: chi phí mỗi lượt cao hơn đúng chừng đó, cửa sổ context
chứa ít lượt hội thoại hơn (cắt lịch sử sớm hơn nên "quên"), độ trễ sinh cao hơn.

Hướng xử lý theo thứ tự rẻ dần: đổi sang model có tokenizer đa ngữ tốt hơn (họ o200k, Qwen: khoảng 1.15 token mỗi âm tiết
thay vì 2-3.6); tóm tắt lịch sử hội thoại thay vì giữ nguyên văn; đặt ngân sách token theo ngôn ngữ chứ không theo số lượt.
Kiểm thêm chuẩn hoá: input NFD từ một bộ gõ có thể làm số token tăng vọt và làm model hiểu sai. Báo cáo bằng số: token trung
bình mỗi lượt, chi phí mỗi hội thoại, số lượt giữ được trong context, trước và sau thay đổi.

## Giải thích word2vec skip-gram với negative sampling. Vì sao cần negative sampling?

Skip-gram học hai bảng vector: $$v_c$$ cho từ trung tâm, $$u_o$$ cho từ ngữ cảnh, sao cho $$v_c$$ dự đoán được các từ trong
cửa sổ quanh nó. Bản gốc dùng softmax trên cả vocab, mẫu số tốn $$O(Vd)$$ cho mỗi cặp. Negative sampling thay bằng $$K+1$$
bài phân loại nhị phân: cặp thật nhãn 1, $$K$$ từ ngẫu nhiên nhãn 0:

$$
L = -\log\sigma(u_o^\top v_c) - \sum_{k=1}^{K}\log\sigma(-u_k^\top v_c)
$$

Mỗi bước chỉ chạm $$K+2$$ dòng, $$O(Kd)$$. Gradient theo $$v_c$$ là $$(\sigma(u_o^\top v_c) - 1)u_o + \sum_k \sigma(u_k^\top v_c)u_k$$.

Chi tiết làm word2vec chạy tốt: phân phối nhiễu $$\text{count}^{0.75}$$ (nâng từ hiếm), subsampling từ quá phổ biến, cửa
sổ động. Lỗi cài đặt hay gặp: cập nhật bằng `W[idx] -= ...` khi chỉ số trùng trong batch, numpy chỉ giữ một lần ghi; phải
dùng `np.add.at` hoặc `index_add_`.

## Word2vec trên tiếng Việt cần làm gì khác tiếng Anh? Bạn đánh giá embedding ra sao?

Train trên âm tiết thì vector của "hà" là trộn của Hà Nội, Hà Giang, sông Hà; "Hà Nội" không tồn tại trong vocab. Cần ghép
âm tiết thành từ: công cụ tách từ, hoặc phát hiện cụm thống kê với điểm kiểu PMI
$$(\text{count}(ab) - \delta)N / (\text{count}(a)\text{count}(b))$$. Trên 6.4 triệu âm tiết Wikipedia, ngưỡng 100 cho 13 077
cụm; sau khi ghép, láng giềng của "mèo" là "sói, ngỗng, cá_mập, vẹt, thằn_lằn" thay vì "cộc, nòi, quạ, thằn, sói". Giới hạn:
"trung quốc" không được ghép vì "quốc" quá phổ biến.

Đánh giá: loss không so được giữa hai vocab khác nhau. Dùng láng giềng (định tính), analogy (đúng 11% top 1 cho nước–thủ đô
ở quy mô này, word2vec gốc đạt 50-60% trên hàng tỉ từ), và tốt nhất là tác vụ downstream thật (phân loại, search) với cùng
pipeline, chỉ đổi embedding.

## Vì sao RNN bị vanishing gradient? LSTM giải quyết thế nào, và nó có tự động giải quyết không?

Gradient từ bước $$T$$ về bước $$k$$ là tích $$T-k$$ Jacobian $$\mathrm{diag}(1 - h_t^2)W_{hh}$$. Chuẩn mỗi thừa số nhỏ hơn 1 thì
co theo cấp số nhân. Đo ngay sau khởi tạo: RNN tanh có gradient tại bước 90 nhỏ hơn bước 99 khoảng 400 lần, tại bước 50 là
2e-12.

LSTM thêm cell state cập nhật bằng phép cộng $$c_t = f_t \odot c_{t-1} + i_t \odot g_t$$, nên đạo hàm dọc đường đó chỉ là
$$\mathrm{diag}(f_t)$$, không có $$W_{hh}$$. Nhưng nó **không tự động** sửa được: với khởi tạo mặc định $$f \approx 0.5$$,
gradient sau 50 bước vẫn là 2.5e-10, và trên bài nhớ ký hiệu đầu tiên qua 20 bước, LSTM mặc định thất bại y như RNN (0.116,
đoán mò là 0.125). Đặt bias cổng quên bằng 1 thì học được với 20 bước, bằng 3 thì học được với 50 bước. Điểm cộng: nói được
rằng kiến trúc cho khả năng, khởi tạo quyết định có dùng được khả năng đó hay không.

## Gradient clipping: theo norm hay theo value? Khi nào cần?

RNN dễ **exploding** (tích Jacobian lớn hơn 1), loss vọt lên NaN. `clip_grad_norm_` gom mọi tham số thành một vector, nếu chuẩn
lớn hơn ngưỡng thì nhân cả vector với `max_norm / norm`: giữ nguyên hướng, chỉ thu bước đi. `clip_grad_value_` cắt từng phần tử
nên đổi hướng gradient, hiếm khi là lựa chọn đúng. Clipping không chữa vanishing.

Thực tế: luôn log chuẩn gradient **trước** khi cắt; nó tăng vọt là dấu hiệu sớm của bất ổn. Với Adam, cắt đều cả vector gần
như không đổi bước cập nhật (Adam chuẩn hoá theo độ lớn), nên clipping chủ yếu bảo vệ khỏi những bước gradient bất thường.

## Padding và packing trong RNN: lỗi gì xảy ra nếu bỏ qua?

Batch câu dài ngắn khác nhau phải pad. Đưa thẳng vào LSTM rồi lấy `output[:, -1]` thì với câu ngắn đó là state sau khi đọc
một đống `<pad>`: kết quả của một câu phụ thuộc nó nằm chung batch với câu nào, train và serve (batch 1) ra khác nhau. Lỗi này
im lặng vì accuracy vẫn ổn khi câu thường ngắn. `pack_padded_sequence(..., enforce_sorted=False)` làm LSTM dừng ở độ dài thật
của từng câu; `h_n` lúc đó là state đúng. Test đơn vị nên có: logits của một câu không đổi khi ghép với câu dài hơn.

Với BiLSTM còn một bẫy: chiều ngược phải bắt đầu từ token thật cuối cùng chứ không từ padding; packing lo việc này.

## Trên UIT-VSFC, BiLSTM đạt accuracy 0.904, TF-IDF + logistic regression 0.898. Bạn nói gì với quản lý?

Accuracy gần như bằng nhau vì 95% câu thuộc hai lớp dễ (negative, positive); lớp neutral chỉ chiếm 4% train. Thước đo đúng
là macro-F1: 0.716 so với 0.755, và gần như toàn bộ khác biệt đến từ F1 lớp neutral (0.31 so với 0.42). Câu hỏi kinh doanh
là: sản phẩm có quan tâm phát hiện phản hồi trung tính không? Nếu không, TF-IDF train vài giây, chạy CPU micro giây mỗi
câu là lựa chọn tốt hơn. Nếu có, BiLSTM hơn nhưng vẫn sai 112/167 câu neutral, và đọc lỗi cho thấy nhiều câu neutral là mảnh
câu hoặc nhãn gây tranh cãi: đầu tư vào nhãn và dữ liệu trước khi đầu tư vào model lớn hơn.

## So sánh attention Bahdanau và Luong.

| | Bahdanau (2015) | Luong (2015) |
| --- | --- | --- |
| Score | additive: $$v^\top\tanh(W_q q + W_k k_j)$$ | multiplicative: dot $$q^\top k_j$$, general $$q^\top W k_j$$ |
| Query | state cũ $$s_{t-1}$$, tính **trước** bước RNN | state mới $$s_t$$, tính **sau** bước RNN |
| Context dùng ở | input của RNN và lớp output | $$\tilde h_t = \tanh(W_c[s_t; c_t])$$ rồi output |
| Train teacher forcing | phải lặp từng bước | decoder RNN chạy cả chuỗi một lần, attention một phép `bmm` |

Hệ quả thực tế: Luong (không input feeding) train nhanh hơn vì song song hoá được theo thời gian; Bahdanau đưa context vào
chính RNN nên decoder "biết" mình đã nhìn đâu, thường hội tụ nhanh hơn theo số epoch (thử trên CPU với 46k cặp câu ngắn,
epoch 1: loss 4.51 so với 5.24) nhưng mỗi epoch chậm hơn vài lần. Dot-product attention chia cho $$\sqrt{d}$$ của
Transformer là hậu duệ trực tiếp của Luong dot.

## Teacher forcing là gì, exposure bias là gì, và beam search giúp được gì?

Teacher forcing: lúc train, input của decoder ở bước $$t$$ là token **đúng** của bước $$t-1$$, nên mọi bước tính song song được
và gradient ổn định. Lúc inference, input là token **model tự sinh**; một lỗi sớm đưa model vào trạng thái nó chưa từng thấy
khi train và lỗi chồng lỗi: đó là exposure bias. Biểu hiện: lặp từ, bịa nội dung sau một từ sai.

Greedy chọn argmax mỗi bước nên không sửa được lựa chọn tồi ban đầu. Beam search giữ $$k$$ tiền tố tốt nhất, cộng
log-xác suất, chuẩn hoá theo độ dài $$\text{score}/((5+L)/6)^\alpha$$ để không thiên vị câu ngắn. Trên bản tham chiếu
Anh-Việt của module, beam 5 nâng BLEU tst2013 từ 9.8 (greedy) lên 11.6, đổi lại decode chậm hơn khoảng 4 lần. Beam không
chữa exposure bias; scheduled sampling và các phương pháp train theo chuỗi mới nhắm vào đó.

## Perplexity là gì? Vì sao không so perplexity của hai model dùng hai tokenizer khác nhau?

Perplexity $$= \exp(\frac{1}{N}\sum -\log p(x_i \mid x_{<i}))$$ với $$N$$ là số **token**: "model phân vân giữa trung bình bao
nhiêu lựa chọn mỗi token". Đổi tokenizer thì $$N$$ đổi và mỗi token mang lượng thông tin khác: model byte-level có perplexity
theo token rất nhỏ (mỗi byte dễ đoán) dù có thể tệ hơn model BPE có perplexity lớn. So công bằng phải quy về đơn vị độc
lập tokenizer: tổng NLL chia cho số **ký tự** hoặc **byte** của văn bản, đổi sang bit:

$$
\text{bpc} = \frac{\sum_i -\log p(x_i \mid x_{<i})}{n_{\text{chars}} \ln 2}
$$

Bài Advanced 02 đo đúng điều này trên Wikipedia tiếng Việt. Bẫy thêm: model word-level có `<unk>` "gian lận" vì đoán `<unk>`
dễ; tập đánh giá khác nhau; có hay không có token đặc biệt trong tổng.

## BLEU tính thế nào và có những bẫy gì khi báo cáo?

BLEU là trung bình nhân của precision n-gram (1 tới 4) đã "cắt" theo số lần xuất hiện trong reference, nhân với brevity
penalty $$\min(1, e^{1 - r/c})$$ phạt bản dịch ngắn. Tính trên **cả corpus** chứ không trung bình BLEU từng câu.

Bẫy: tokenization trước khi tính (cùng hai câu ví dụ, sacrebleu tokenize 13a cho 68.05, `none` cho 65.34); có lowercase hay
không; một hay nhiều reference; detokenize hay không. Luôn dùng sacrebleu và báo cáo **chữ ký** (`nrefs:1|case:mixed|tok:13a|
...|version:2.6.0`). BLEU dựa trên trùng chuỗi nên phạt cách diễn đạt đúng mà khác chữ; với tiếng Việt (âm tiết ngắn) nên báo
cáo thêm chrF, và cho quyết định quan trọng thì dùng metric học được (COMET) hoặc đánh giá người.

## Case: thiết kế hệ dịch tài liệu kỹ thuật Anh-Việt nội bộ cho một công ty, dữ liệu song ngữ có 50 nghìn cặp câu.

Đóng bài toán: loại tài liệu (thuật ngữ dày đặc, định dạng markdown/code), độ trễ chấp nhận được (batch theo đêm hay tương
tác), bảo mật (có được gửi ra API ngoài không), ngân sách.

Lựa chọn theo thứ tự nên thử: (1) LLM có sẵn qua API hoặc model mở (Qwen) với prompt + bảng thuật ngữ, đo trên 500 câu dev;
(2) model dịch mở đã train sẵn (NLLB, MarianMT) fine-tune trên 50k cặp; (3) tự train seq2seq từ đầu chỉ khi có lý do đặc
biệt: 50k cặp quá ít (bản tham chiếu của module với 133k cặp chỉ đạt BLEU 11.6). Thành phần bắt buộc: chuẩn hoá NFC + kiểu
dấu thanh thống nhất; giữ nguyên code, URL, tên biến (che bằng placeholder trước khi dịch rồi trả lại); bảng thuật ngữ ép
buộc; đánh giá bằng sacrebleu + chrF có chữ ký, cộng đánh giá người trên mẫu nhỏ; giám sát độ dài output (bịa nội dung,
cắt cụt). Chi phí: đếm token bằng tokenizer thật của model trên tài liệu thật, nhớ thuế token tiếng Việt khi output là tiếng
Việt.

## Case: bạn phải chọn giữa LSTM và Transformer cho một bài toán chuỗi mới. Bạn cân nhắc gì?

Transformer (module 05) thắng gần như mọi bài NLP vì train song song theo thời gian, mỗi vị trí nhìn trực tiếp mọi vị trí
khác (đường đi gradient độ dài 1), và scale tốt với dữ liệu, model. LSTM vẫn hợp lý khi: chạy streaming từng bước với bộ nhớ
cố định (state $$O(H)$$ thay vì KV cache lớn dần), thiết bị nhúng, chuỗi cảm biến dài vô hạn, dữ liệu nhỏ và cần model nhỏ.
Các kiến trúc mới (Mamba, RWKV, xLSTM) cố lấy cả hai: train song song như Transformer, inference như RNN.

Quyết định bằng số: độ dài chuỗi, yêu cầu độ trễ mỗi bước, bộ nhớ, lượng dữ liệu, và một baseline rẻ (TF-IDF, GBDT trên
feature) để biết model sâu có đáng không. Bài UIT-VSFC của module là ví dụ: baseline TF-IDF chỉ kém BiLSTM 0.04 macro-F1.
