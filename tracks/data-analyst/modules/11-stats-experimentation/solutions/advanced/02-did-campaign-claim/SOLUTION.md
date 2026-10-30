# Hướng làm: kiểm tra claim "chiến dịch ở Đức tăng 68% khách" bằng DiD

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, các con số tham chiếu, các quyết định
cần cân nhắc, headline mẫu và rubric chấm memo.

## Ba hàm

- **`weekly_active`**: lọc `[start, end)`, thêm cột `week = invoice_date.dt.to_period("W-SUN")`; với mỗi nhóm
  lọc `country.isin(...)`, `groupby("week")["customer_id"].nunique()`; ghép bằng `pd.DataFrame(dict)`,
  `reindex(columns=list(groups))`, `fillna(0).astype(int)`, `sort_index()`. Đếm **khách khác nhau** chứ không đếm
  dòng hay hoá đơn: một khách sỉ mua 40 dòng một tuần vẫn là một khách.
- **`did_table`**: `post = weekly.index.start_time >= cutoff`; trung bình hai giai đoạn; `did_log` là chênh lệch
  của hai log-tỉ số. Tuần chứa mốc (29/8-4/9) bắt đầu trước 1/9 nên thuộc giai đoạn trước; cách khác là bỏ hẳn tuần
  đó, nói rõ trong memo.
- **`did_regression`**: `gap = log(treated) - log(control)`, `post` 0/1, `smf.ols("gap ~ post")` với HAC. Hệ số
  `post` là "khoảng cách log sau trừ trước". Đây là DiD trên **trung bình của log**, nên khác DiD 2×2 (log của
  trung bình): +10.5% so với +7.4%. Cả hai hợp lệ, báo một con số chính và nói con số kia chỉ khác cách lấy trung
  bình.

## Con số tham chiếu

| Bước | Con số |
| --- | --- |
| Panel | 39 tuần (28/2-27/11/2011): 27 trước, 12 sau; Đức 2-19 khách/tuần (TB 7.8), đối chứng 9-42 (TB 19.6) |
| Con số của agency | Đức 6.44 → 10.83 khách/tuần: **+68.1%** (đúng về số học) |
| Cùng giai đoạn, đối chứng | 16.67 → 26.08: **+56.5%** |
| Cùng mùa năm 2010, Đức (không có chiến dịch) | **+45.6%**; đối chứng +68.6% |
| DiD 2×2 | **+7.4%** (log 0.072) |
| Hồi quy khoảng cách log, HAC 4 tuần | **+10.5%**, CI 95% trên log [−0.065; +0.265] tức khoảng **−6% tới +30%**, p = 0.24 |
| Placebo mốc giả 1/6/2011 (chỉ dữ liệu trước) | DiD −10.2%; hồi quy −15.8%, p = 0.31 |
| Placebo cùng mùa 2010, mốc 1/9/2010 | DiD **−13.6%**; hồi quy −11.5%, p = 0.30 |
| Xu hướng trước | độ dốc khoảng cách log +0.004/tuần, p = 0.65: không thấy hai nhóm đi lệch nhau trước 1/9 |
| Độ nhạy (cell explore "độ nhạy của phương pháp") | sai số chuẩn 0.0843 trên log, MDE (alpha 0.05, power 0.8) = 2.80 × 0.0843 = 0.236 log, tức khoảng **+27%**: hiệu ứng nhỏ hơn thì nhiều khả năng không thấy |
| So cùng nước, năm trước | 1.681 / 1.456 − 1 = +15.5% (không trừ được xu hướng tăng của công ty giữa hai năm) |

**Câu chuyện đúng**: 68% là thật nhưng gần như toàn bộ là mùa vụ cuối năm: các nước châu Âu khác (không có chiến
dịch) cũng tăng 57%, và năm 2010 Đức tăng 46% ở cùng giai đoạn. Trừ phần chung, ước lượng còn khoảng +7% tới +10%,
khoảng tin cậy từ −6% tới +30%, và placebo ở nơi không có chiến dịch cho "hiệu ứng" cỡ ±10-15%. Dữ liệu **không
cho thấy** chiến dịch tạo thêm khách; nó cũng không loại trừ được một hiệu ứng vừa phải (dưới khoảng 30%), vì Đức
chỉ có 6-11 khách mỗi tuần.

Headline mẫu: **"68% của agency chủ yếu là mùa vụ: các nước khác cũng tăng 57%, phần còn lại (+7%) nằm trong
nhiễu"**.

## Các quyết định cần cân nhắc

- **Nhóm đối chứng**: các nước châu Âu khác (cùng loại khách, cùng mùa vụ Giáng sinh, không bị nhắm). Không lấy
  Anh: thị trường nội địa, số khách gấp hàng chục lần Đức, có thể chịu tác động của chiến dịch khác. Có thể thử đối chứng hẹp
  hơn (Pháp, Hà Lan, Bỉ) để xem kết luận có đổi không; Áo và Thuỵ Sĩ nói tiếng Đức nên có thể bị "tràn" quảng cáo,
  thử bỏ chúng ra khỏi đối chứng.
- **Thang đo**: log/tỉ lệ thay vì số tuyệt đối. DiD tuyệt đối: Đức +4.4 khách, đối chứng +9.4 khách, ra "−5 khách"
  chỉ vì đối chứng lớn hơn. Song song trên thang tỉ lệ hợp lý hơn cho mùa vụ.
- **Metric**: khách mua mỗi tuần (metric của agency). Doanh thu nhiễu hơn nhiều (một khách sỉ Đức đổi lịch là đủ
  đảo kết luận); nếu dùng doanh thu thì phải cắt đuôi và báo số khách bên cạnh.
- **Suy luận với một nhóm được tác động**: khoảng tin cậy HAC dựa trên 39 tuần và giả định về tương quan theo
  thời gian; placebo (mốc giả, năm trước, hoặc lần lượt coi từng nước đối chứng là "được tác động") cho thước đo
  nhiễu thực tế hơn. Memo nên dựa vào cả hai.
- **Tuần chứa mốc**: tuần 29/8-4/9 trộn trước và sau; thử bỏ tuần đó để kiểm độ nhạy.
- **Đề xuất cho lần sau**: geo experiment (chọn ngẫu nhiên một nửa số nước/vùng để chạy, nửa còn lại làm đối
  chứng), hoặc giữ holdout khách không thấy quảng cáo như bộ `marketing-ab`. Quyết định ngân sách: không tăng gấp
  đôi dựa trên báo cáo này; giữ hoặc giảm, kèm điều kiện đo được.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm và số liệu | 15 | Ba hàm pass test; memo dùng đúng con số từ notebook |
| Phản biện con số của agency | 15 | Xác nhận 68% đúng số học; chỉ ra so trước/sau trộn mùa vụ, dẫn số của đối chứng và của Đức năm 2010 |
| DiD | 20 | Nêu nhóm đối chứng và lý do; ước lượng 2×2 và hồi quy có khoảng tin cậy, nói bằng lời dễ hiểu; giải thích vì sao dùng thang log |
| Độ tin cậy | 20 | Xu hướng trước (chart hoặc độ dốc), ít nhất một placebo có số, nói rõ phương pháp phát hiện được hiệu ứng từ cỡ nào |
| Kết luận đúng mực | 15 | Không nói "chiến dịch vô dụng" và không nói "chiến dịch có hiệu quả"; nói "không có bằng chứng, không loại trừ hiệu ứng dưới khoảng 30%" |
| Khuyến nghị | 10 | Quyết định ngân sách cụ thể và cách đo lần sau (geo experiment, holdout), có người làm và thời điểm |
| Giới hạn | 5 | Ít nhất hai giới hạn cụ thể (cỡ mẫu nhỏ, khách sỉ, tràn sang Áo/Thuỵ Sĩ, sự kiện riêng từng nước, chiến dịch là giả định) |

Từ 70 điểm trở lên là memo có thể gửi Giám đốc marketing.

## Sai lầm hay gặp

- Chấp nhận 68% vì "đã so trước và sau".
- Lấy DiD tuyệt đối (−5 khách) rồi kết luận chiến dịch làm **giảm** khách.
- Đọc p = 0.24 thành "chiến dịch không có tác dụng".
- Chọn nhóm đối chứng sau khi thử nhiều nhóm và giữ nhóm cho kết quả đẹp nhất (cũng là p-hacking).
