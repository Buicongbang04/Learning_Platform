# M05: Thiết kế A/B test cho can thiệp với đơn rủi ro

## Mục tiêu

Viết tài liệu pre-registration cho một thí nghiệm kiểm chứng ý tưởng: **khi một đơn có nguy cơ, nhắn
tin chủ động cho khách lúc đơn được giao cho vận chuyển** (xin lỗi, báo ngày giao mới, voucher nhỏ). Mọi
con số nền (baseline, traffic, variance) tính từ Olist thật. Olist không có dữ liệu thí nghiệm, nên
milestone dừng ở **thiết kế**: metric, power, MDE, CUPED/CUPAC, kế hoạch phân tích và quy tắc quyết định.
Kỹ năng phân tích kết quả bạn đã luyện trên bộ A/B thật ở module 03 và 04.

Milestone này mở rộng bài `modules/03-ab-testing/exercises/advanced/02-olist-experiment-design` (hàm
`baseline()` và khung `DESIGN.md`) bằng các kỹ thuật tăng độ nhạy của module 04.

**Thời điểm can thiệp.** Tin nhắn gửi **trước khi giao**, nên quyết định ai vào thí nghiệm chỉ được dùng
thông tin có tới lúc giao vận chuyển. Không được chọn tổng thể bằng "đơn trễ" hay "đơn có `late_days` >
0": lúc nhắn tin chưa ai biết điều đó. Mọi covariate dùng cho CUPED/CUPAC cũng phải có trước lúc random.

**Thứ tự trong lộ trình.** Bạn gặp milestone này sau module 04, trước khi có model ở M03. Vì vậy tổng
thể ban đầu được định nghĩa bằng một **luật không ML**, cạnh một kịch bản "dự đoán hoàn hảo" làm cận
trên. Sau M03, quay lại thay bằng số thật của model.

## Việc cần làm

1. **Baseline chung**: chạy `baseline()` của bài module 03 trên Olist thật: tỉ lệ review xấu, tỉ lệ trễ,
   review xấu ở đơn trễ, đơn giao xong mỗi tuần. Dùng traffic **gần đây** (06/2017 – 07/2018), không phải
   trung vị toàn giai đoạn.
2. **Tổng thể thí nghiệm**, so ít nhất hai kịch bản:
   - Luật "còn dưới 5 ngày tới ngày hẹn lúc giao vận chuyển" (có thể thử thêm 3 và 7 ngày): tỉ lệ đơn,
     số đơn mỗi tuần (trung vị và phân vị 10/90), tỉ lệ review xấu, tỉ lệ đơn thật sự trễ trong nhóm.
   - Dự đoán hoàn hảo: chỉ đơn sẽ trễ (cận trên của baseline, không đạt được trong thực tế).
   - Sau M03: top k% điểm của model lúc giao vận chuyển.

   Nhìn số đơn của luật theo tháng. Từ 06/2018 ngày hẹn giao rút ngắn (trung vị số ngày hứa giao của
   đơn mua tháng 6, 7, 8 là 27 → 19 → 13 ngày; nguyên nhân chưa rõ, không phải do đơn chưa giao xong:
   97.5% đơn mua tháng 8 đã giao). Tổng thể của luật vì thế không ổn định. Ghi rõ thí nghiệm chạy trong
   giai đoạn nào, và chọn một trong hai: bỏ 07–08/2018 khỏi phần tính baseline, hoặc chuẩn hoá số ngày
   còn lại theo số ngày hứa giao (ví dụ còn dưới 20% thời gian hứa).
3. **Đơn vị random**: theo đơn hay theo `customer_unique_id`, random lúc nào, hash nhất quán ra sao
   (dùng lại `hash_assign` của `modules/04-advanced-experimentation/exercises/intermediate/02-olist-ratio-aa`).
   Đếm số khách có nhiều hơn một đơn bị gắn cờ để đánh giá rủi ro nhiễm chéo.
4. **Metric**: OEC (định nghĩa chính xác, cửa sổ chờ review chín), ít nhất 2 guardrail (tỉ lệ có review,
   chi phí voucher, khối lượng liên hệ CSKH, tỉ lệ huỷ / trả hàng), metric chẩn đoán. Bàn về selection:
   tin nhắn có thể làm thay đổi **ai** để lại review. Đề xuất cách tính OEC trên **mọi** đơn được random.
5. **Tác động kỳ vọng phải hợp lý.** Tin nhắn không làm đơn hết trễ. Giả sử nó chỉ giúp đơn thật sự trễ
   và giảm xác suất review xấu của chúng $$\Delta$$ điểm (lấy $$\Delta = 0.15$$, giả định cho bài này; module 15 sau này dùng cùng giá trị), thì tác động
   lên tổng thể chỉ là $$\Delta$$ nhân tỉ lệ trễ trong tổng thể. Đừng dùng ATT +44 điểm của M04 làm tác
   động của tin nhắn.
6. **Power, cỡ mẫu, thời lượng** cho từng kịch bản, $$\alpha = 0.05$$ hai phía, power 0.8, dùng hàm cỡ mẫu
   của `modules/03-ab-testing/exercises/basic/02-power-sample-size`:

   $$
   n = \frac{\left(z_{1-\alpha/2} + z_{1-\beta}\right)^2 \left[p_0(1-p_0) + p_1(1-p_1)\right]}{(p_0 - p_1)^2}
   $$

   Thời lượng = cỡ mẫu hai nhóm chia số đơn đủ điều kiện mỗi tuần, cộng thời gian chờ giao và chờ
   review. Nếu không khả thi, viết ra MDE đạt được trong 8 tuần và các đòn bẩy: mở rộng tổng thể (baseline
   và tỉ lệ trễ đổi theo), tăng thời lượng, chấp nhận MDE lớn hơn, đổi OEC.
7. **Giảm variance** theo module 04 (`exercises/basic/01-cuped`, README mục 2–3):
   - CUPED với lịch sử review của khách: bao nhiêu phần trăm đơn trong tổng thể có đơn trước đó?
   - CUPAC: một model dự đoán `bad_review` từ covariate có trước lúc random (`promised_days`,
     `handling_days`, `remaining_days`, phí ship, giá, số item, cùng bang), **fit trên giai đoạn trước
     thí nghiệm**, đánh giá $$R^2$$ trên giai đoạn sau. Mức giảm cỡ mẫu là $$1 - \rho^2$$.
8. **Kế hoạch phân tích**: kiểm định cho OEC và guardrail, SRM, multiple testing, segment định trước (theo
   mức điểm rủi ro, theo vùng), có peeking hay không và quy tắc dừng.
9. **Quy tắc quyết định** viết trước: ship, không ship, chạy tiếp; guardrail nào là cứng.
10. **`reports/EXPERIMENT_DESIGN.md`** theo khung 7 mục của bài module 03, thêm mục 8 "Giảm variance" và
    mục 9 "Cập nhật sau M03".

Số tham chiếu (Olist thật, giai đoạn 06/2017 – 07/2018 trừ khi ghi khác; bản cài đặt của người soạn):

| Con số | Giá trị |
| --- | --- |
| Đơn giao xong mỗi tuần | trung vị khoảng 1 259 |
| Đơn trễ mỗi tuần | trung vị 61, tuần tệ nhất 565 |
| Luật "còn dưới 5 ngày", 06/2017 – 07/2018: tổng thể | khoảng 900 đơn (1.1%); theo 61 tuần trọn (thứ Hai – Chủ nhật, theo ngày mua) trung vị 9 đơn mỗi tuần, phân vị 10 là 2, phân vị 90 là 24 |
| Luật "còn dưới 5 ngày", 06/2017 – 07/2018: review xấu / trễ | 40.5% / 64% |
| Luật "còn dưới 5 ngày" chỉ riêng 08/2018 | 1 195 đơn (ngày hẹn rút ngắn từ 06/2018, nguyên nhân chưa rõ) |
| Luật "còn dưới 5 ngày", 06/2017 – 08/2018 (gồm tháng 8) | khoảng 2 100 đơn, review xấu 25%, trễ 51% |
| Dự đoán hoàn hảo (đơn trễ) | review xấu 56.9%, 61 đơn mỗi tuần |
| Luật, $$\Delta = 0.15$$ trên đơn trễ | tác động khoảng 9.5 điểm, khoảng 390 đơn mỗi nhóm, gần 90 tuần |
| Dự đoán hoàn hảo, $$\Delta = 0.15$$ | 171 đơn mỗi nhóm, khoảng 6 tuần |
| CUPAC trong tổng thể luật (fit trước 2018, đo trên 2018) | $$R^2$$ khoảng 0.21 |
| Đơn trong tổng thể luật có đơn có review trước đó | khoảng 3% |

## Kết quả nộp

- `project/notebooks/m05_experiment.ipynb`: baseline, tổng thể theo kịch bản, bảng power, CUPAC.
- `project/reports/EXPERIMENT_DESIGN.md` (ít nhất 800 từ, không còn TODO).

## Tiêu chí đạt

- [ ] Baseline đúng: 12.8% review xấu, 8.1% trễ, review xấu ở đơn trễ trên 50%, traffic gần đây khoảng 1 259 đơn mỗi tuần.
- [ ] Tổng thể chỉ dùng thông tin có tới lúc giao vận chuyển; baseline là của **tổng thể đó**, không phải 12.8%.
- [ ] Kế hoạch ghi rõ giai đoạn tính baseline và chạy thí nghiệm, và hoặc bỏ 07–08/2018, hoặc chuẩn hoá số ngày còn lại theo số ngày hứa giao.
- [ ] Tác động kỳ vọng được suy ra từ cơ chế (chỉ đơn thật sự trễ được giúp), không lấy ATT của M04.
- [ ] Bảng power có ít nhất hai kịch bản tổng thể, có thời lượng, và kết luận thẳng khi không khả thi.
- [ ] CUPED/CUPAC: covariate có trước lúc random, fit trên giai đoạn trước thí nghiệm, mức giảm variance đo trên dữ liệu thật.
- [ ] OEC có cửa sổ chín; có guardrail tỉ lệ có review và nhận ra selection bias.
- [ ] Kế hoạch phân tích có SRM, multiple testing, segment định trước, quy tắc dừng; quy tắc quyết định viết trước.
- [ ] Sau M03, mục "Cập nhật sau M03" có baseline, số đơn mỗi tuần và power tính từ model thật.
