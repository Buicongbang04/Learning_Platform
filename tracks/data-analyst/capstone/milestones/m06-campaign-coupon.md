# M06: Hiệu quả campaign/coupon

## Mục tiêu

Trưởng nhóm marketing hỏi: **"Các campaign và coupon của chúng ta có làm khách mua nhiều hơn không, và
loại nào nên làm tiếp?"** Bạn trả lời bằng dữ liệu quan sát, không phải thí nghiệm. Sản phẩm của milestone
là một báo cáo đọc campaign **như một thí nghiệm có giới hạn**: mô tả đúng ai được nhắm, ước lượng thận
trọng có so sánh, chỉ ra vì sao không thể kết luận nhân quả mạnh, và đề xuất thí nghiệm để biết chắc.

> **Giới hạn quan trọng nhất.** Hộ **không được gán ngẫu nhiên** vào campaign: dunnhumby chọn hộ để gửi
> campaign, và dữ liệu cho thấy hộ được chọn đã chi tiêu nhiều hơn hẳn từ trước. Vì vậy mọi chênh lệch
> giữa hộ được gán và hộ không được gán **lẫn hiệu ứng chọn mẫu** với hiệu ứng campaign. Milestone này
> không cho phép kết luận kiểu "campaign X làm tăng doanh thu Y%". Kết luận đạt chuẩn có dạng "chênh lệch
> quan sát được là …; với các giả định …, nó tương thích với hiệu ứng từ … tới …; để biết chắc cần …".

Kiến thức: module 11 (`11-stats-experimentation`) mục 3–4 (thiết kế và đọc A/B), mục 5 (correlation không
phải causation, DiD nhanh); module 13 (`13-business-financial-analytics`, các chủ đề Promotion Analysis,
Root Cause, Unit Economics, What-if). Bài gần nhất ở module 11:
`modules/11-stats-experimentation/exercises/advanced/02-did-campaign-claim` (đọc lại một tuyên bố
"campaign hiệu quả" bằng DiD), `modules/11-stats-experimentation/exercises/intermediate/01-marketing-ab-readout`,
`modules/11-stats-experimentation/exercises/advanced/01-experiment-brief`. Phần promotion analysis, tính
chi phí ưu đãi và kịch bản what-if dùng kiến thức module 13.

## Việc cần làm

1. **Mô tả campaign**: 30 campaign theo loại (TypeA/B/C), độ dài, số hộ được gán, số hộ và số lần dùng
   coupon, tỷ lệ dùng coupon trên lượt gán theo loại. Timeline mermaid `gantt` hoặc biểu đồ các campaign
   theo `DAY`, đánh dấu campaign kéo dài quá ngày 711 và các campaign chồng nhau.
2. **Ai được nhắm?** So sánh hộ có trong `campaign_table` với hộ không có: chi tiêu, số basket, tuần mua
   đầu, tỷ lệ có nhân khẩu học. Viết rõ: hai nhóm khác nhau **trước** mọi campaign, nên so sánh thẳng sau
   campaign là sai.
3. **Một campaign, đọc kỹ**: chọn campaign 18 (TypeA, ngày 587–642, nhiều hộ nhất). Dựng so sánh
   trước/sau:
   - Kỳ trước: 56 ngày ngay trước (531–586); kỳ sau: 587–642. Đơn vị: hộ có giao dịch trước ngày 531.
     Nhóm "được gán" là hộ có trong campaign 18, nhóm so sánh là phần còn lại.
   - Tính chi tiêu trung bình mỗi hộ mỗi kỳ, chênh lệch sau − trước của từng nhóm, và DiD tuyệt đối.
   - Tính lại theo **tỷ lệ** (thay đổi % hoặc log chi tiêu). DiD tuyệt đối và DiD tương đối có cùng dấu
     không? Giải thích vì sao khi hai nhóm có mức nền chênh nhau ~3 lần, lựa chọn thang đo quyết định kết
     luận, và parallel trends khó tin.
   - Kiểm parallel trends bằng chuỗi chi tiêu theo tuần của hai nhóm trong 20 tuần trước campaign.
   - Placebo: chạy cùng phép tính với một "campaign giả" đặt ở hai cửa sổ 56 ngày trước đó. Nếu placebo
     cũng ra chênh lệch cỡ tương tự, con số thật không nói lên điều gì về campaign.
   - Ghi các yếu tố gây nhiễu: phần lớn hộ của campaign 18 cũng thuộc campaign 13 (504–551), nên kỳ "trước"
     không sạch; nhóm so sánh cũng có hộ đang ở campaign khác.
4. **Coupon**: trong hộ được gán campaign 18, so hộ có dùng coupon với hộ không dùng. Vì sao so sánh này
   còn tệ hơn bước 3 (tự chọn: hộ dùng coupon là hộ vốn định mua)? Tính tổng tiền ưu đãi (`COUPON_DISC`,
   `COUPON_MATCH_DISC`) trên các dòng có coupon để đặt cạnh mọi ước lượng lợi ích.
5. **`causal_data` (display, mailer)**: dùng DuckDB, không nạp vào pandas. Bảng này **chỉ có** các cặp
   sản phẩm × cửa hàng × tuần **có** display hoặc mailer, chỉ phủ một phần cửa hàng. Mô tả độ phủ, rồi chọn
   một commodity và so doanh số tuần có mailer với tuần không có, nói rõ đây là tương quan (tuần có mailer
   thường cũng là tuần giảm giá).
6. **Kịch bản và hoà vốn (module 13)**: với một giả định hiệu ứng thật (ví dụ 0%, 2%, 5% chi tiêu của
   hộ được gán trong kỳ campaign), campaign 18 mang lại bao nhiêu doanh thu so với chi phí ưu đãi đã trả?
   Ghi rõ đây là **ví dụ giả định**, không phải ước lượng.
7. **Đề xuất thí nghiệm** cho campaign TypeA kế tiếp: đơn vị random (hộ), holdout bao nhiêu % trong nhóm
   đủ điều kiện, metric chính và guardrail, thời lượng, MDE ước tính từ phương sai chi tiêu hộ trong dữ liệu
   (khung của bài `advanced/01-experiment-brief`).
8. **`reports/CAMPAIGN.md`** (tối đa hai trang): câu hỏi, mô tả, chọn mẫu, ước lượng và độ nhạy với thang
   đo, coupon, display/mailer, kịch bản, giới hạn, khuyến nghị.

Số tham chiếu (bản cài đặt của người soạn):

| Đại lượng | Giá trị |
| --- | --- |
| Campaign TypeA / TypeB / TypeC: số campaign; lượt gán; số hộ | 5; 3 979; 1 513 / 19; 2 655; 1 023 / 6; 574; 397 |
| Tỷ lệ lượt gán có dùng coupon: TypeA / TypeB / TypeC | 16,0% / 7,9% / 7,7% |
| Hộ được gán / không được gán; chi tiêu trung vị (dòng hợp lệ) | 1 584 / 916; 3 444 / 746 |
| Số basket trung vị: được gán / không | 119 / 32 |
| Hộ có nhân khẩu học trong nhóm được gán | 760 / 801 |
| Campaign 18: hộ được gán; hộ dùng coupon | 1 133; 214 |
| Hộ campaign 18 cũng thuộc campaign 13 | 876 |
| Chi tiêu TB mỗi hộ 531–586 → 587–642: được gán | 435,95 → 470,67 (+34,72; +8,0%) |
| Chi tiêu TB mỗi hộ 531–586 → 587–642: nhóm so sánh (1 365 hộ) | 140,12 → 159,92 (+19,80; +14,1%) |
| DiD tuyệt đối | +14,92 mỗi hộ trong 56 ngày (DiD tương đối thì **ngược dấu**) |
| `causal_data`: số dòng; số cửa hàng; tuần | 36 786 524; 115 / 582; 9..101 |
| `causal_data`: dòng có display / có mailer / không có cả hai | 42,8% / 68,6% / 0% |
| Tổng `COUPON_DISC` / số dòng có `COUPON_DISC < 0` | -42 611,54 / 36 422 |

## Kết quả nộp

- `project/notebooks/m06_campaign.ipynb`, `project/sql/m06/*.sql`.
- `project/src/dunnhumby_da/campaign.py` với `pre_post(con, campaign, pre_days, post_days) -> DataFrame`
  (chi tiêu mỗi hộ hai kỳ, cờ được gán), có test trên fixture nhỏ.
- `project/reports/CAMPAIGN.md`.

## Tiêu chí đạt

- [ ] Báo cáo nói rõ campaign **không ngẫu nhiên**, có bảng so sánh hộ được gán và không được gán trước campaign.
- [ ] Không có câu nào khẳng định campaign hay coupon "làm tăng" doanh thu một lượng cụ thể.
- [ ] DiD được tính cả tuyệt đối lẫn tương đối, có kiểm parallel trends và nêu chồng lấn campaign 13.
- [ ] So sánh hộ dùng / không dùng coupon được gọi đúng tên là selection.
- [ ] `causal_data` được đọc bằng DuckDB; nêu rõ bảng chỉ chứa tuần có khuyến mãi và độ phủ cửa hàng.
- [ ] Kịch bản hoà vốn ghi "ví dụ giả định", đặt cạnh chi phí ưu đãi thật.
- [ ] Có đề xuất thí nghiệm với holdout ngẫu nhiên, metric, thời lượng và MDE.
