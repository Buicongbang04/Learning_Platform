# Hướng làm: đề xuất model churn cho COO

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hàm, các con số tham chiếu với giả định mẫu, các quyết
định cần cân nhắc và rubric chấm đề xuất.

## Hàm `campaign_table`

1. Kiểm đầu vào: cùng độ dài, `save_rate` trong `[0, 1]`, chi phí và giá trị không âm, mỗi `k` là số nguyên trong `[0, n]`
   (từ chối `2.5`, `-1`, `n + 1`).
2. `order = np.argsort(-score, kind="stable")`; `reached = np.concatenate([[0], np.cumsum(y[order])])`, nên `reached[k]`
   là số khách rời trong top-k với mọi `k` chỉ bằng một lần cộng dồn.
3. Mỗi `k`: `capture = reached / tổng khách rời`, `precision = reached / k` (0 khi `k = 0`), `expected_saves = reached ×
   save_rate`, `cost = k × contact_cost`, `expected_value = expected_saves × value_per_save`, `net`, và
   `random_net = k × tỉ lệ rời chung × save_rate × value_per_save − cost`.

Gọi hết khách thì `net = random_net`: model chỉ có giá trị khi **chọn**, tức khi ngân sách nhỏ hơn số khách.

## Con số tham chiếu (tập test 1 761 khách, 467 rời)

Giả định mẫu (ví dụ giả định): 15 USD một lần liên hệ, 600 USD một khách giữ được (cước tháng trung bình 64.76 USD,
khách rời bỏ trung bình 74.44 USD, nhân khoảng 9 tháng), 25% khách sắp rời được gọi sẽ ở lại.

| Gọi | Khách rời trúng | Precision | Net (USD) | Net khi ngẫu nhiên | Chênh |
| --- | --- | --- | --- | --- | --- |
| 100 | 77 | 77.0% | 10 050 | 2 478 | 7 572 |
| 200 | 141 | 70.5% | 18 150 | 4 956 | 13 194 |
| 476 (cỡ quy tắc) | 286 | 60.1% | 35 760 | 11 795 | 23 965 |
| 800 | 390 | 48.8% | 46 500 | 19 823 | 26 677 |
| 1 200 | 454 | 37.8% | 50 100 | 29 734 | 20 366 |
| 1 761 (gọi hết) | 467 | 26.5% | 43 635 | 43 635 | 0 |

- Quy tắc, 476 cuộc gọi: 246 khách rời trúng, net 29 760 USD. Model cùng 476 cuộc: 286 khách, net 35 760 USD, hơn 6 000 USD
  trên 1 761 khách test; nhân 4 cho toàn bộ khách (giả định tỉ lệ giữ nguyên) khoảng 24 000 USD mỗi kỳ.
- Top-476 của model: 99.2% là month-to-month, 89.9% cáp quang, 55.7% trùng danh sách của quy tắc. Model không tìm ra nhóm
  mới, nó **sắp lại** bên trong nhóm month-to-month: 211 khách chỉ quy tắc chọn đều không dùng cáp quang (DSL hoặc không
  internet) và 34% rời; 211 khách chỉ model chọn có 97% cáp quang, 99% đã gắn bó hơn 12 tháng, và 53% rời.

Độ nhạy (ngân sách tối ưu là `k` cho `net` lớn nhất, quét mọi `k`):

| Giả định | Ngân sách tối ưu | Net tối ưu | Net ở 476 cuộc |
| --- | --- | --- | --- |
| 25% giữ được, 600 USD | 1 217 (69%) | 50 595 | 35 760 |
| 10% giữ được, 600 USD | 708 (40%) | 11 580 | 10 020 |
| 40% giữ được, 600 USD | 1 227 (70%) | 91 995 | 61 500 |
| 25% giữ được, 300 USD | 889 (50%) | 17 565 | 14 310 |
| 25% giữ được, 900 USD | 1 227 (70%) | 85 095 | 57 210 |

Hoà vốn ở 476 cuộc: model cần `save_rate` khoảng 4.2%, quy tắc khoảng 4.8%. Kết luận "chiến dịch có lãi" vững với mọi giả
định hợp lý; kết luận "gọi bao nhiêu" thì **không** vững (40% tới 70% khách). Đó là lý do đề xuất pilot ở ngân sách hiện
tại thay vì nhảy ngay tới con số tối ưu trên giấy.

## Các quyết định cần cân nhắc

- **So cùng ngân sách.** Mọi so sánh model với quy tắc phải ở cùng số cuộc gọi; so model ở ngưỡng 0.5 với quy tắc là so hai
  chính sách khác cỡ.
- **Giả định nào yếu nhất?** `save_rate` không có trong dữ liệu và không model nào đo được; nó chỉ đo được bằng thí nghiệm.
  Giá trị một khách giữ được có thể ước lượng từ cước và tenure; chi phí liên hệ có từ đội CSKH.
- **Uplift so với propensity.** Model xếp hạng khả năng rời, không xếp hạng khả năng *được giữ lại nhờ cuộc gọi*. Khách điểm
  cao nhất có thể đã quyết rời (gọi vô ích); khách điểm trung bình có thể dễ thuyết phục hơn. Nêu được điều này là dấu hiệu
  của DA senior; bước sau pilot có thể là uplift modeling (DS module 06).
- **Ngoại suy từ test ra toàn công ty**: tập test là mẫu 25% ngẫu nhiên của cùng một ảnh chụp. Hiệu quả thật trên tháng sau
  thường thấp hơn (dữ liệu trôi), nên báo khoảng thay vì một con số, và nói rõ phép nhân 4.
- **Chi phí vận hành**: model cần chạy lại mỗi kỳ, theo dõi precision của danh sách, người chịu trách nhiệm khi dữ liệu đầu
  vào hỏng. 24 000 USD mỗi kỳ (giả định) có trả được chi phí đó không?
- **Pilot**: nhóm đối chứng ngẫu nhiên **trong số khách model chọn** (không phải so với khách không được chọn, vì hai nhóm
  khác rủi ro). Metric chính: tỉ lệ rời sau 60–90 ngày; guardrail: chi phí ưu đãi, phàn nàn. Cỡ mẫu: với tỉ lệ rời khoảng
  60% trong danh sách và mức giảm cần phát hiện 10 điểm, khoảng 400 khách mỗi nhóm (module 11).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm và số đúng | 10 | Test pass; số trong đề xuất khớp notebook |
| So với quy tắc và ngẫu nhiên ở cùng ngân sách | 20 | Có số khách rời trúng và net của cả ba ở cùng số cuộc gọi; nói được model hơn bao nhiêu |
| Giả định và độ nhạy | 20 | Ghi rõ từng giả định tiền; ít nhất hai kịch bản; điểm hoà vốn hoặc khoảng ngân sách tối ưu; chỉ ra giả định yếu nhất |
| Hiểu model đang làm gì | 15 | Nhận ra model chủ yếu sắp lại trong nhóm month-to-month, hoặc kiểm precision theo nhóm; không bán model như "AI tìm ra khách mới" |
| Rủi ro và giới hạn | 15 | Ít nhất ba: một ảnh chụp/không chia thời gian, tương quan không phải tác động (uplift), gọi khách không định rời, xuống cấp và chi phí vận hành |
| Pilot | 10 | Có nhóm đối chứng ngẫu nhiên trong danh sách, metric chính, thời gian, cỡ mẫu sơ bộ, tiêu chí quyết định |
| Viết cho COO | 10 | Headline là quyết định có con số; không thuật ngữ không giải thích (ROC-AUC, odds); đọc trong ba phút |

Từ 70 điểm trở lên là đề xuất có thể gửi COO.

## Sai lầm hay gặp

- Báo ROC-AUC 0.84 làm lý do chính để dùng model: COO không quyết định bằng ROC-AUC.
- Chọn ngân sách tối ưu trên giấy (gọi 70% khách) mà không nói nó phụ thuộc vào `save_rate` chưa ai đo.
- Coi `expected_saves` là số khách chắc chắn giữ được, hoặc quên trừ chi phí gọi khách không định rời.
- Đề xuất đo tác động bằng cách so tỉ lệ rời của khách được gọi với khách không được gọi (hai nhóm rủi ro khác nhau).
- Nhân kết quả tập test lên toàn công ty mà không nói đó là ngoại suy.
