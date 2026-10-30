# Lời giải: unit economics đơn hàng và bảng kịch bản

## Cách làm

- **`order_table`**: ép `Invoice` sang `str` trước khi lọc (Excel trộn `int` và `str`, `startswith("C")` trên số
  lỗi hoặc bỏ sót), lọc dòng hợp lệ, `groupby("Invoice")` với `size` cho `lines` và `first` cho quốc gia, mã khách.
- **`unit_economics`**: hai loại chi phí khác nhau về bản chất. Giá vốn đi theo **số lượng hàng**, nên tính trên
  doanh thu gốc; phí thanh toán đi theo **số tiền thu**, nên tính trên doanh thu mới; chi phí xử lý đi theo **số
  đơn và số dòng**. Gộp chung thành "60% doanh thu" là lỗi hay gặp: khi tăng giá, giá vốn tự tăng theo và lợi ích
  của việc tăng giá bị đánh giá thấp.
- **`pnl`**: cộng các khoản rồi nhân `1 + volume_change`; margin là tỉ số nên không đổi theo số đơn.
- **`breakeven_order_value`**: contribution của đơn giá trị R là `R(1 − cogs − fee) − cost_per_order −
  cost_per_line × lines`; cho bằng 0 rồi giải R.
- **`scenario_table`**: với mỗi kịch bản ghi đè giả định, gọi `unit_economics` với `price_change`, bỏ đơn dưới
  ngưỡng (sau khi đổi giá, vì khách thấy giá mới), rồi `pnl` với `volume_change`. Dòng `base` là dict rỗng.
- **`breakeven_volume_change`**: contribution tỉ lệ thuận với số đơn, nên `C_hiện_tại / C_giá_mới − 1`. Với giả
  định của bài nó tương đương công thức quen thuộc `−p(1 − fee) / (m + p(1 − fee))`, m là contribution margin.

## Kết quả trên bộ thật

| Chỉ tiêu | Giá trị |
| --- | --- |
| Đơn, doanh thu | 19 960 đơn; 10 666 702.54 GBP; median 303.84 GBP / đơn, 15 dòng |
| Gross profit (giả định 60%) | 4 266 681 GBP (40%) |
| Phí thanh toán, chi phí xử lý | 213 334 và 292 206 GBP |
| Contribution | 3 761 141 GBP (35.26%), 188.4 GBP / đơn |
| Đơn contribution âm | 1 023 (5.1%), tổng −4 380 GBP |
| Theo nhóm giá trị | < 25 GBP: 1 064 đơn, −4.1 GBP / đơn; 25–50: +5.1; 1 000+: 1 842 đơn mang 1.89 triệu |
| Theo thị trường | Export 1 941 đơn, 307.6 GBP / đơn; UK 18 019 đơn, 175.6 GBP / đơn |
| Hoà vốn | 15 dòng: 30.92 GBP |

| Kịch bản | Contribution | So với base |
| --- | --- | --- |
| Giá +5%, mất 8% đơn | 3 941 104 | +179 964 |
| Đơn tối thiểu 25 GBP (khách bỏ đi) | 3 765 479 | +4 338 |
| Cước mỗi đơn 8 → 10 GBP | 3 721 221 | −39 920 |
| Giá vốn 60% → 63% | 3 441 140 | −320 001 |

Tăng giá 2% / 5% / 10% được mất tới 5.3% / 12.2% / 21.7% số đơn. Với giá vốn 55% / 65%, ngưỡng của mức +5% là
10.9% / 13.9%.

**Câu trả lời cho CFO**: đơn nhỏ có lỗ thật nhưng không đáng kể (dưới 0.2% contribution); đặt đơn tối thiểu gần
như không đổi lợi nhuận mà có rủi ro mất khách mới (đơn nhỏ thường là đơn đầu tiên). Đòn bẩy lớn là giá vốn và giá
bán: tăng giá 5% được phép mất khoảng 12% số đơn (11–14% tuỳ giá vốn thật). Muốn biết khách có bỏ đi nhiều như vậy
không thì cần thử nghiệm giá (module 11), không trả lời được bằng bảng kịch bản.

## Đáp án trắc nghiệm

- `negative-orders` **c**: 1 023 đơn (5.1%) nhưng tổng chỉ −4 380 GBP. "Tỉ lệ đơn lỗ" và "tiền lỗ" là hai câu
  hỏi khác nhau; 190 nghìn là contribution trung bình mỗi đơn nhân sai đơn vị.
- `breakeven-median` **a**: (8 + 0.25 × 15) / (1 − 0.60 − 0.02) = 11.75 / 0.38 ≈ 30.9 GBP. 11.75 là chi phí xử lý,
  quên chia cho margin; 304 là giá trị đơn median.
- `min-order` **b**: bỏ 1 064 đơn, mất 12 433 GBP doanh thu nhưng contribution tăng 4 338 GBP. Lợi ích nhỏ vì đơn
  nhỏ lỗ ít (trung bình 4 GBP mỗi đơn).
- `price-breakeven` **d**: 12.2%. 5% là nhầm "tăng bao nhiêu thì được mất bấy nhiêu"; 8% là giả định của một kịch
  bản trong bảng, không phải điểm hoà vốn.
- `tornado` **a**: giá vốn ±20% (48% – 72%) đổi contribution ±1.28 triệu, gấp khoảng 30 lần các giả định khác.
  Việc nên làm trước: hỏi phòng mua hàng con số giá vốn thật.
- `export-uk` **b**: đơn xuất khẩu lớn hơn nhiều (median cao hơn), nên với cùng 8 GBP mỗi đơn contribution mỗi đơn
  cao hơn. Giả định "8 GBP mỗi đơn" cho cả đơn quốc tế gần như chắc chắn sai: cước quốc tế cao hơn (bộ dữ liệu có
  dòng `POST` thu cước chủ yếu ở đơn ngoài UK). Nên tách giả định theo thị trường trước khi kết luận.
- `cogs-fixed` **c**: giá vốn là tiền mua hàng; tăng giá bán không làm hàng mua vào đắt hơn.
- `present-assumption` **b**: con số đúng **với giả định**, nên phải đi kèm giả định và khoảng khi giả định quan
  trọng nhất thay đổi.

## Lỗi hay gặp

- Tính giá vốn trên doanh thu mới khi tăng giá: ngưỡng hoà vốn ra khoảng 5.1% thay vì 12.2%.
- Đếm "đơn lỗ" mà không đếm tiền: báo CFO "5% đơn đang lỗ" dễ dẫn tới chính sách đơn tối thiểu không đáng.
- Trình bày một con số duy nhất từ giả định, không có độ nhạy.
