# M04: Phân tích nhân quả: giao trễ ảnh hưởng review bao nhiêu

## Mục tiêu

Trả lời câu hỏi của Giám đốc Vận hành: **"Nếu giảm giao trễ thì review xấu giảm bao nhiêu?"** bằng một
phân tích nhân quả trên dữ liệu quan sát: DAG, tập điều chỉnh, nhiều ước lượng đối chiếu nhau, chẩn đoán
overlap và balance, phân tích độ nhạy, và một báo cáo nói rõ con số này **dùng được cho quyết định nào
và không dùng được cho quyết định nào**.

Milestone này là bài `modules/06-causal-inference/exercises/advanced/01-olist-late-delivery-review`
đặt trong bối cảnh capstone. Dùng lại `build_orders`, `effect_estimates`, `e_value` của bạn.

## Việc cần làm

1. **Bảng phân tích**: đơn giao xong có review theo định nghĩa dùng chung, mua từ 01/2017 (giai đoạn
   2016 quá ít đơn và gây separation ở propensity). Treatment `late`, outcome `bad_review`.
2. **DAG** bằng mermaid trong `reports/CAUSAL.md`: confounder (vùng khách, cùng bang với seller, tháng
   mua, giá, phí ship, số item, số ngày hứa giao), mediator (thời gian giao thực tế, liên hệ CSKH),
   selection (khách có viết review hay không). Chọn tập điều chỉnh, giải thích vì sao **không** điều
   chỉnh mediator.
3. **Ba ước lượng** của tác động trung bình trên đơn bị trễ (ATT), cùng tập covariate:
   - chênh lệch ngây thơ,
   - linear probability model với robust SE (HC1),
   - IPW chuẩn hoá với propensity từ logistic regression:

   $$
   \widehat{\text{ATT}} = \bar Y_{T=1} - \frac{\sum_{i: T_i = 0} w_i Y_i}{\sum_{i: T_i = 0} w_i}, \quad w_i = \frac{\hat e(x_i)}{1 - \hat e(x_i)}
   $$

4. **Chẩn đoán**: phân phối propensity hai nhóm, ESS của nhóm control sau trọng số, |SMD| trước và sau
   IPW cho từng covariate.
5. **Liều**: tỉ lệ review xấu theo số ngày trễ (từ sớm 3 ngày tới trễ 7 ngày). Có bước nhảy ở đúng
   ngày hẹn không, hay tăng dần? Điều đó nói gì về việc định nghĩa trễ là biến nhị phân?
6. **Độ nhạy**: E-value cho risk ratio; viết bằng lời confounder chưa đo phải mạnh cỡ nào để kéo tác
   động về 0. Thêm phân tích selection: tỉ lệ có review ở đơn trễ và đúng hẹn, và một kịch bản cận
   (ví dụ coi mọi đơn trễ không có review là review xấu, hoặc là review tốt) để thấy con số đổi bao
   nhiêu.
7. **Diễn giải cho capstone**: con số ATT là **trần** của lợi ích nếu một đơn trễ trở thành đúng hẹn.
   Nó **không** phải tác động của việc nhắn tin xin lỗi cho đơn sắp trễ (đơn vẫn trễ). Viết rõ điều này,
   và nêu con số nào M05 cần mà M04 không cho được.
8. **`reports/CAUSAL.md`** (tối đa hai trang, ít nhất 400 từ): câu hỏi, DAG, tập điều chỉnh, bảng ước
   lượng, chẩn đoán, liều, độ nhạy, giới hạn, khuyến nghị.

Số tham chiếu (95 560 đơn mua từ 01/2017, covariate `promised_days`, `log_freight`, `log_price`, `n_items`,
`same_state`, bang khách, tháng mua; bản cài đặt của người soạn):

| Con số | Giá trị |
| --- | --- |
| Tỉ lệ đơn trễ | 8.0% |
| Ngây thơ | +44.9 điểm phần trăm |
| LPM (HC1) | +44.4 điểm, CI 95% [43.2, 45.5] |
| IPW ATT | khoảng +45 điểm |
| Review xấu theo ngày trễ | sớm 1–3 ngày: 11–12%; trễ 1 ngày: 19.6%; trễ 3 ngày: 50.4%; trễ 5 ngày: 64.7% |
| Tỉ lệ có review: đúng hẹn / trễ | 99.5% / 97.9% |

## Kết quả nộp

- `project/notebooks/m04_causal.ipynb`.
- `project/reports/CAUSAL.md` có DAG mermaid.

## Tiêu chí đạt

- [ ] Tập điều chỉnh chỉ gồm biến xác định trước khi đơn trễ; mediator và outcome không bị điều chỉnh.
- [ ] Ba ước lượng có mặt, cùng covariate; ATT nằm khoảng +44 tới +45 điểm và được đối chiếu với nhau.
- [ ] Có chẩn đoán overlap, ESS và balance sau trọng số.
- [ ] Phân tích liều cho thấy review xấu tăng dần theo số ngày trễ, có diễn giải vận hành.
- [ ] E-value tính đúng và được diễn giải bằng lời; selection do "chỉ đơn có review" được nêu và thử kịch bản cận.
- [ ] Báo cáo tách bạch "tác động của giao trễ" với "tác động của tin nhắn chủ động" và chỉ ra M05 cần đo cái sau.
