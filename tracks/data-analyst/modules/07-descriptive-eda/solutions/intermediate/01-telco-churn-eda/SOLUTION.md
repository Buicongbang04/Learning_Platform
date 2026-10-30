# Lời giải: EDA có câu hỏi trên Telco churn

## Cách làm

1. **`clean_telco`**: `raw.copy()`; `TotalCharges.astype(str).str.strip().replace("", np.nan)` rồi
   `pd.to_numeric(..., errors="raise")`. Không dùng `errors="coerce"`: nó biến mọi chuỗi lạ thành NaN và giấu lỗi
   dữ liệu mới. `SeniorCitizen.map({0: "No", 1: "Yes"})`, `churned = Churn.eq("Yes")`.
2. **`add_tenure_band`**: `pd.cut(tenure, [-1, 6, 12, 24, 48, 72], labels=TENURE_BANDS)`; `pd.cut` với `labels`
   trả categorical có thứ tự, cận phải tính vào nhóm, và `-1` làm `0` rơi vào nhóm đầu.
3. **`rate_table`**: `groupby(col, observed=True)[target]`, `size()` và `sum()`, các tỉ lệ tính từ chính bảng
   (`lift` chia cho `churned.sum() / n.sum()`), `sort_values("rate", ascending=False)`. `observed=True` bỏ nhóm
   categorical không còn khách (nếu không, nhóm rỗng ra `n = 0` và `rate` NaN).
4. **`compare_numeric`**: `groupby(target)[col]` rồi `count`, `mean`, `median`, `std`, hiệu hai `quantile`, `skew`.
   `count` (không phải `size`) để `n` là số giá trị thật được dùng trong các thống kê.

## Vòng EDA và con số tham chiếu

| Bước | Phát hiện |
| --- | --- |
| Hiểu dữ liệu | 7 043 khách, 1 869 rời bỏ (26.5%). 11 ô `TotalCharges` trống, cả 11 có `tenure = 0` và chưa rời bỏ: khách mới chưa có hoá đơn đầu tiên |
| Hợp đồng | Month-to-month: 3 875 khách, churn 42.7%, **88.6%** số khách rời. Một năm 11.3%, hai năm 2.8% |
| Tenure | 0–6 tháng: churn 52.9%, 42.0% số khách rời; 49–72 tháng: 9.5% |
| Internet | Cáp quang 41.9% (69.4% số khách rời), DSL 19.0%, không internet 7.4% |
| Thanh toán | Electronic check 45.3% (57.3% số khách rời); ba cách còn lại 15–19% |
| Nhân khẩu | Người cao tuổi 41.7% nhưng chỉ 25.5% số khách rời; giới tính 26.9% / 26.2%, không khác |
| Biến số | tenure median 38 / 10 tháng; cước tháng median 64.43 / 79.65 USD; TotalCharges median 1 683.60 / 703.55 USD |
| Phân tầng | Trong **mọi** nhóm tenure, khách rời có TotalCharges cao hơn (25–48 tháng: 2 896 so với 2 193) và cước tháng cao hơn (25–48 tháng: 89.10 so với 64.20) |
| Phân khúc | Month-to-month + cáp quang: 2 128 khách, churn 54.6%, **62.2%** số khách rời. Month-to-month + tenure ≤ 12: 1 994 khách, 51.4%, 54.8% |

## Vì sao như vậy

- **Ô trống là thông tin.** Cả 11 ô cùng một đặc điểm (tenure 0) thì đó là quy tắc nghiệp vụ, không phải lỗi. Để
  NaN và ghi phạm vi ("TotalCharges tính trên 7 032 khách đã có hoá đơn") trung thực hơn điền 0 hay xoá dòng.
- **Ưu tiên theo `share_of_churned`, không theo `rate`.** Mục tiêu của Head of Retention là giảm **số** khách rời.
  Người cao tuổi churn cao nhưng chỉ là một phần tư số khách rời; month-to-month là gần chín phần mười.
- **Phân tầng đảo chiều kết luận về TotalCharges.** Tổng thể: khách rời có TotalCharges thấp hơn. Trong từng nhóm
  tenure: cao hơn. Biến gây nhiễu là tenure: khách rời phần lớn là khách mới, và khách mới thì chưa kịp trả nhiều.
  Đọc đúng là "khách rời bỏ trả **cước tháng cao hơn**", ngược hẳn "khách chi ít thì bỏ đi".
- **Đề xuất**: nhắm month-to-month dùng cáp quang. Đủ lớn (62% số khách rời), đủ rõ để nhận diện, và hai đặc
  điểm (không cam kết, cước cao) gợi ý giả thuyết hành động: ưu đãi chuyển sang hợp đồng 12 tháng, hoặc kiểm chất
  lượng/giá dịch vụ cáp quang. Headline mẫu: **"62% khách rời bỏ là khách month-to-month dùng cáp quang; nhóm
  2 128 khách này rời với tỉ lệ 55%"**.
- **Điều chưa biết**: mọi bảng là tương quan trên một thời điểm chụp. Khách chọn hợp đồng hai năm vì đã định ở
  lại lâu (self-selection); ép chuyển hợp đồng không chắc cho ra 2.8%. Cần thử nghiệm ngẫu nhiên ưu đãi chuyển
  hợp đồng trên nhóm mục tiêu (module 11), và dữ liệu theo thời gian để biết khách rời sau bao lâu kể từ lần đổi
  giá, sự cố dịch vụ.

## Đáp án trắc nghiệm

- `blank-totals` (c): tenure 0, chưa có hoá đơn; để NaN, ghi phạm vi. Không ai trong 11 khách đã rời (b sai).
- `m2m-share` (d) 88.6%. (a) 43% là tỉ lệ churn của nhóm; (b) 55% là tỉ trọng của nhóm trong mọi khách.
- `high-rate-small-share` (a) người cao tuổi: 41.7% churn, 25.5% số khách rời. Cáp quang (b) và electronic check
  (c) chiếm phần lớn số khách rời; 49–72 tháng (d) churn thấp nhất.
- `tenure-median` (b) 38 và 10. (a) là mean làm tròn; (c) 29 là median chung, 1 là mode của khách rời.
- `totalcharges-confound` (c): cao hơn ở mọi nhóm tenure; chênh lệch tổng do tenure gây ra.
- `target-segment` (a). (b) là cả nhóm month-to-month, (c) là month-to-month + tenure ≤ 12, (d) là cả nhóm cáp quang.
- `gender` (b): một dòng ghi "không liên quan" là một phát hiện hữu ích (loại bỏ giả thuyết), không cần chart.
- `causal-next` (d): tương quan, có self-selection; cần thử nghiệm.
