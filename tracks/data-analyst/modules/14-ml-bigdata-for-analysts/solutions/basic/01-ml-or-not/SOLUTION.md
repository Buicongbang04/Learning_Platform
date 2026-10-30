# Lời giải: DA có nên làm ML không?

## Khung quyết định dùng cho cả bài

1. **Quyết định nào sẽ thay đổi, ai dùng?** Không trả lời được thì chưa làm gì cả.
2. **Câu hỏi là "vì sao" hay "nếu làm X thì sao"?** Đó là phân tích (phân rã, phân tầng) hoặc thí nghiệm, không phải
   model dự đoán.
3. **Cần dự đoán hay xếp hạng từng đối tượng?** Thử quy tắc 1–2 dòng trước; đo nó như đo một model.
4. **Model đơn giản hơn quy tắc bao nhiêu, quy ra tiền?** Chỉ khi phần hơn đủ trả chi phí vận hành.
5. **Công cụ theo cỡ dữ liệu và nơi dữ liệu nằm**, không theo độ "xịn".

## Đáp án từng câu

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `ml-type-segments` | c | Không có nhãn, mục tiêu là tìm nhóm: unsupervised clustering. (a) cần nhãn nhóm có sẵn; (b) không có hành động-phần thưởng lặp lại; (d) đoán một con số, không chia nhóm |
| `rl-pricing` | a | Agent chọn hành động (mức giá), nhận phần thưởng (doanh thu), điều chỉnh chính sách: đó là RL, cụ thể là multi-armed bandit. (b) và (d) là supervised (có nhãn lịch sử: huỷ, doanh số); (c) là unsupervised |
| `why-not-ml` | b | "Vì sao" là câu hỏi chẩn đoán (diagnostic analytics): phân rã doanh thu = khách × tần suất × giá trị đơn, drill-down theo nước, sản phẩm, kênh (module 01, 13). Feature importance của model dự báo (a) nói biến nào giúp đoán, không nói vì sao tháng 3 giảm; (c), (d) là dùng công cụ trước khi có câu hỏi |
| `rule-vs-model` | a | Cùng khoảng 30% khách được gọi: quy tắc phủ 54.8%, model phủ 66.2%, hơn 11.4 điểm. (b) so tỉ lệ rời của quy tắc với top 10% của model (khác cỡ danh sách); (c) lấy nhầm 28% là tỉ lệ khách được gọi; (d) bỏ qua cột độ phủ (và tỉ lệ rời của model ở top 30% là 58.4%, không phải 51%) |
| `top-decile-lift` | d | Top 10% có 73.4% rời bỏ, gọi ngẫu nhiên trúng 26.5%: 73.4 / 26.5 = 2.8 lần (lift). (c) lấy nhầm 73.4% làm hệ số |
| `explain-to-business` | b | Cây nông (sâu 2–3) cho luật "nếu… thì…" mà stakeholder đọc được và DA viết lại được thành `CASE WHEN` để kiểm trên warehouse. KNN (a) không có luật để giải thích; mạng nơ-ron (c) là hộp đen; k-means (d) không học từ nhãn churn nên "cụm rủi ro" không phải dự đoán churn |
| `naive-bayes-text` | a | Naive Bayes trên số đếm từ là baseline phân loại văn bản kinh điển: train trong vài giây, chạy tốt với 1 000 nhãn. Đánh giá trên một phần nhãn tay để ra precision/recall từng chủ đề. Transformer từ đầu (d) cần nhiều dữ liệu hơn rất nhiều (dùng model pre-trained thì hợp lý, nhưng đó là bước sau); (b), (c) không dùng nội dung ticket |
| `dl-tabular` | d | Trên bảng nhỏ, Deep Learning hiếm khi thắng model cổ điển (lý thuyết phần 6: MLP 0.828 so với logistic regression 0.841 trên Telco). Yêu cầu so trên cùng test với baseline là cách công bằng để quyết định. (a) sai về sự thật; (b) framework không quyết định chất lượng; (c) đóng cửa với mọi bằng chứng |
| `data-size-tool` | c | 12 GB Parquet, phân tích một lần: DuckDB đọc thẳng tệp, chỉ đọc cột cần, chạy ngoài RAM, nhiều luồng. pandas (b) cần gấp nhiều lần 12 GB RAM sau khi giải nén; Excel (d) giới hạn 1 048 576 dòng mỗi sheet; cụm Spark (a) tốn thời gian dựng và tiền cho việc một máy làm được |
| `mpi-vs-mapreduce` | a, c | MPI là chuẩn gửi nhận thông điệp giữa tiến trình (send, recv, broadcast, allreduce); allreduce cộng gradient giữa GPU trong huấn luyện phân tán. MPI **không** tự chịu lỗi hay tự chia dữ liệu (b sai: đó là điểm mạnh của Spark); DA gần như không viết MPI (d sai) |

## Ghi chú

- Tình huống trong câu hỏi là ví dụ giả định; số Telco là số thật tính ở phần 2–4 lý thuyết.
- Câu `rule-vs-model` là câu quan trọng nhất của bài: model chỉ đáng làm khi hơn quy tắc ở **cùng ngân sách hành động**,
  và phần hơn đó (11 điểm phần trăm khách rời được gọi) mới là thứ đem quy ra tiền.
