# Hướng làm và rubric: chọn embedding model, nén vector, migrate index

Bài mở. Dưới đây là hướng làm, bảng tham chiếu đo bằng bản lời giải giữ ngoài repo, một kế hoạch migrate mẫu và rubric.

## Hướng làm

**Hàm.** `quantize_int8`: `scale = abs(x).max(axis=0) / 127`, thay 0 bằng 1, `clip(round(x / scale), -127, 127)` kiểu `int8`.
`binarize`: `np.packbits(x > 0, axis=1)`. `hamming_topk`: `unpackbits(db ^ q).sum(1)` rồi sort ổn định (hoặc bảng popcount
256 phần tử, nhanh hơn). `rescore`: tích vô hướng với vector gốc trên tập ứng viên đã sắp theo chỉ số, sort ổn định giảm dần.

**Đo.** Mọi biến thể của `bge-m3` lấy từ cache, không embed lại: cắt chiều thì chuẩn hoá lại cả câu hỏi lẫn tài liệu; int8 thì
giải nén rồi nhân ma trận; nhị phân thì Hamming, có và không rescoring top-100. Pool cho model thứ hai: mọi điều của 144 văn bản
chứa đáp án của 300 câu cộng 5 000 điều ngẫu nhiên khác (`default_rng(0)`), tổng 12 135 điều; văn bản cắt 2 000 ký tự vì
`nomic-embed-text` qua Ollama trả HTTP 400 khi vượt context.

## Bảng tham chiếu

PC của track, Ollama trên GPU dùng chung, 300 câu ghim (`.superpowers/scratch/logs/adv02_ref.log`):

| Cấu hình | Phạm vi | Chiều | byte/vector | Recall@10 | MRR@10 |
| --- | --- | --- | --- | --- | --- |
| `bge-m3` float32 | corpus 61 425 | 1 024 | 4 096 | 0.905 | 0.707 |
| `bge-m3` cắt 512 chiều, chuẩn hoá lại | corpus | 512 | 2 048 | 0.898 | 0.701 |
| `bge-m3` cắt 256 chiều | corpus | 256 | 1 024 | 0.878 | 0.644 |
| `bge-m3` int8 theo từng chiều | corpus | 1 024 | 1 024 | 0.905 | 0.707 |
| `bge-m3` nhị phân, Hamming | corpus | 1 024 | 128 | 0.863 | 0.635 |
| `bge-m3` nhị phân + rescore top-100 bằng float32 | corpus | 1 024 | 128 (+4 096 trên đĩa) | 0.905 | 0.707 |
| `bge-m3` | pool 12 135 | 1 024 | 4 096 | 0.938 | 0.768 |
| `nomic-embed-text`, không tiền tố | pool | 768 | 3 072 | 0.087 | 0.036 |
| `nomic-embed-text`, `search_query: ` / `search_document: ` | pool | 768 | 3 072 | 0.130 | 0.059 |

Throughput trên cùng 2 000 ký tự đầu mỗi điều, lô 32: `nomic-embed-text` 68 văn bản/giây, `bge-m3` 26 văn bản/giây. Hamming
bằng `unpackbits` trong numpy: 48 ms/câu trên 61 425 vector (chậm hơn nhân ma trận float32; thư viện thật dùng popcount phần cứng).

Điều cần thấy:

- **Int8 miễn phí**: cùng Recall@10 và MRR@10 tới ba chữ số, bộ nhớ chia 4. **Nhị phân + rescoring** cũng về đúng số của
  float32 với 128 byte RAM mỗi vector (vector gốc trên đĩa). Nhị phân thuần mất 0.04 Recall@10 và 0.07 MRR.
- **Cắt chiều** `bge-m3` (không train kiểu Matryoshka): 512 chiều gần như không mất, 256 chiều mất 0.06 MRR. Int8 cùng 1 024
  byte tốt hơn hẳn cắt còn 256 chiều float32: nén độ chính xác ít hại hơn bỏ chiều với model này.
- **`nomic-embed-text` gần như vô dụng cho tiếng Việt có dấu** (Recall@10 0.087 so với 0.938 của `bge-m3` trên cùng pool),
  tiền tố chỉ cứu chút ít. Nó nhanh hơn 2.6 lần, nhưng nhanh và sai thì không có giá trị.
- Chẩn đoán (mục 1 lý thuyết): tokenizer của `nomic-embed-text` không có các âm tiết tiếng Việt có dấu, nên "rất", "không",
  "hơi" thành cùng một token và các câu chỉ khác nhau ở đó có cosine đúng bằng 1; bỏ dấu thì model phân biệt lại được. Văn bản
  luật gần như toàn âm tiết có dấu, nên phần lớn nội dung biến thành cùng một token. Kiểm thêm: đếm `prompt_eval_count` của
  Ollama, hoặc so cosine giữa hai điều luật khác chủ đề (rất cao).

## Kế hoạch migrate mẫu (A: model cũ, B: model mới)

1. **Chuẩn bị**: B là index riêng, tên chứa phiên bản model và tiền xử lý (ví dụ `zalo_bge-m3_nfc_v2`); bộ đọc đi qua một
   alias (`zalo_current`). Tiêu chí chuyển viết **trước**: trên tập 300 câu ghim, Recall@10 của B không thấp hơn A quá sàn nhiễu
   (300 câu: một câu là 0.0033; đặt ngưỡng tụt tối đa 0.01), MRR@10 không tụt, p95 không vượt ngân sách.
2. **Ghi kép**: mọi upsert, xoá từ lúc bắt đầu đi vào cả A và B (cùng id ổn định), để B không thiếu dữ liệu mới trong lúc backfill.
3. **Backfill**: embed toàn bộ nguồn bằng B, idempotent theo id và hash nội dung, có checkpoint. Ước lượng: 61 425 điều ở 26
   văn bản/giây là khoảng 40 phút; 10 triệu chunk là khoảng 4.5 ngày trên một GPU như của track, nên chia nhiều worker hoặc
   GPU lớn hơn, và đặt ưu tiên thấp để không ảnh hưởng lưu lượng thật.
4. **Kiểm**: chạy tập ghim trên B; **shadow read** một phần lưu lượng (truy vấn cả A và B, chỉ trả kết quả A, ghi lại độ trùng
   top-10 và độ trễ). Query phải embed bằng **model của index đang đọc**: không bao giờ query B bằng vector của A.
5. **Chuyển**: đổi alias sang B (một thao tác nguyên tử), theo dõi tỉ lệ click/không tìm thấy, p95.
6. **Rollback**: đổi alias về A; A vẫn nhận ghi kép nên không mất dữ liệu. Sau một khoảng an toàn (vài ngày), dừng ghi kép,
   xoá A, xoá cache embedding của model cũ.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Hàm | 10 | Test pass; nhị phân + rescoring tốt hơn hẳn nhị phân thuần |
| Bảng chất lượng | 25 | Đủ dòng ở bước 2, cùng 300 câu, pool mô tả rõ (cỡ, seed, xử lý văn bản dài), có MRR lẫn Recall |
| Chi phí | 15 | byte/vector và dung lượng cả corpus của từng cách lưu, throughput hai model đo cùng điều kiện |
| Chẩn đoán | 15 | Nguyên nhân cụ thể có bằng chứng (cặp câu, tokenizer, số token), không dừng ở "model không hợp" |
| Lựa chọn | 10 | Chọn model và cách lưu bằng số, nói đánh đổi (RAM, đĩa, độ trễ, chất lượng) |
| Kế hoạch migrate | 25 | Không trộn vector hai model; ghi kép hoặc tương đương; tiêu chí chuyển định lượng đặt trước; shadow read hoặc đánh giá offline; rollback; ước lượng backfill từ throughput đo được |
