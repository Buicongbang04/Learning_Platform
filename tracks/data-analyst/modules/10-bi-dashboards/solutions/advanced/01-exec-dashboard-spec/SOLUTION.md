# Hướng làm: spec và bản dựng dashboard điều hành

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết `spec_lint.py`, một spec mẫu cho yêu cầu A có số
thật, các quyết định cần cân nhắc và rubric chấm.

## `spec_lint.py`

- **`parse_kpi_table`**: `split_sections(md).get("KPI")`; không có thì `[]`. Tìm dòng đầu bắt đầu bằng `|`, đọc
  liên tiếp các dòng bảng; tách ô bằng `line.strip().strip("|").split("|")` rồi `strip()` từng ô; dòng đầu là
  header; bỏ dòng mà mọi ô khớp `:?-{3,}:?`; mỗi dòng còn lại thành `{header[i]: ô[i]}` (thiếu ô thì chuỗi rỗng).
- **`lint_spec`**: duyệt `SECTIONS`: thiếu thì "Thiếu phần `## X`", nội dung `strip()` rỗng thì "Phần X chưa có nội
  dung", chứa `TODO` thì "Phần X còn TODO" (mỗi phần tối đa một lỗi). Có phần KPI thì kiểm cột thiếu (một lỗi liệt
  kê các cột), số KPI ngoài 3-7, tên trùng theo `strip().lower()`, và mỗi ô rỗng của cột bắt buộc một lỗi nêu tên
  KPI và tên cột.

Linter không chấm được chất lượng; nó chặn những lỗi khiến spec không dùng được (KPI không có owner, không có so
sánh). Phần còn lại chấm theo rubric.

## Spec mẫu (yêu cầu A, Online Retail II)

- **Người dùng và quyết định**: Giám đốc thương mại và 4-5 trưởng thị trường, họp tháng ngày làm việc thứ ba của
  tháng sau (khi số tháng trước đã đủ). Quyết định: phân bổ ngân sách khuyến mãi và nhân sự chăm khách giữa UK và
  các thị trường nước ngoài; thị trường nào cần kế hoạch giữ khách. Không phải người dùng chính: kho, kế toán (cần
  dashboard riêng theo ngày, theo hoá đơn).
- **Câu hỏi**: (1) Tháng vừa rồi doanh thu cao hơn hay thấp hơn cùng tháng năm trước, ở UK và ngoài UK? (2) Thay
  đổi đến từ số khách hay từ giá trị mỗi khách? (3) Thị trường nước ngoài nào tăng, nào giảm mạnh nhất? (4) Khách
  lớn nào của thị trường đó ngừng mua? Câu "vì sao Germany giảm" để dành cho ad-hoc.
- **KPI** (định nghĩa chung của track):

  | KPI | Định nghĩa | Công thức | Grain | So sánh | Refresh | Owner |
  | --- | --- | --- | --- | --- | --- | --- |
  | Doanh thu | Doanh thu gộp, dòng hợp lệ | `SUM(revenue)` | tháng × thị trường | cùng tháng năm trước | hằng ngày 6h | Sales Ops |
  | Khách mua | Khách có mã, ≥ 1 hoá đơn hợp lệ trong tháng | `COUNT(DISTINCT customer_id)` | tháng × thị trường | cùng tháng năm trước | hằng ngày 6h | Sales Ops |
  | Doanh thu mỗi khách | Doanh thu của khách có mã / số khách | `SUM(revenue) FILTER (customer_id IS NOT NULL) / COUNT(DISTINCT customer_id)` | tháng × thị trường | cùng tháng năm trước | hằng ngày 6h | Sales Ops |
  | Tỉ trọng ngoài UK | Doanh thu ngoài UK / tổng | `SUM(revenue) FILTER (country <> 'United Kingdom') / SUM(revenue)` | tháng | cùng tháng năm trước | hằng ngày 6h | Giám đốc thương mại |

- **Bố cục**: hàng 1 bốn tile (tháng đủ gần nhất, delta so cùng kỳ); hàng 2 trend 24 tháng tách UK / ngoài UK
  (hai đường, không stacked); hàng 3 bar xếp hạng thay đổi doanh thu so cùng kỳ của các nước ngoài UK; hàng 4 bảng
  khách lớn có doanh thu giảm (drill-down).
- **Bộ lọc**: Tháng (mặc định tháng đủ gần nhất), Thị trường (mặc định tất cả). Không có bộ lọc sản phẩm: câu hỏi
  là thị trường, sản phẩm thuộc dashboard merchandising.
- **Refresh**: nạp 5h sáng, cache 12 giờ và xoá sau khi nạp; tile ghi "dữ liệu tới 09/12/2011 12:50"; tháng 12/2011
  không vào KPI, trend vẽ nét đứt hoặc bỏ.

Số thật cho tháng 11/2011 so với 11/2010: tổng 1 509 496.33 so với 1 470 272.48 (**+2.7%**, trong khi so tháng
trước là +30.7% vì mùa vụ); UK 1 325 346.21 (+3.9%); ngoài UK 184 150.12 (**-5.4%**, tỉ trọng 12.2%) dù số khách ngoài
UK tăng từ 121 lên 159. Một tile tổng duy nhất che mất chuyện thị trường nước ngoài giảm doanh thu mỗi khách: đó
là lý do tách UK và ngoài UK.

## Bản dựng

- **Metabase** hợp nếu giám đốc và trưởng thị trường muốn tự click drill-through; dùng lại khung của Intermediate
  02 (field filter tháng và thị trường, `validate_layout`).
- **Superset** hợp nếu cần chart phức tạp hơn hoặc RLS cho từng trưởng thị trường (mỗi người chỉ thấy nước mình).
- **Streamlit** hợp cho yêu cầu B nếu muốn thêm kịch bản "giảm ca khi dự báo mưa", nhưng mất self-serve.

Ba con số đối chiếu tối thiểu: tổng doanh thu tháng đủ gần nhất (1 509 496.33), một breakdown (ví dụ ngoài UK
184 150.12), một ô khi lọc (Germany tháng 11/2011: 28 025.02), mỗi số kèm SQL hoặc pandas độc lập.

## Các quyết định cần cân nhắc

- **So cùng kỳ hay so tháng trước**: dữ liệu bán lẻ quà tặng có mùa vụ mạnh (tháng 11 cao nhất năm); so tháng
  trước gần như luôn "tăng" vào quý 4. Dashboard điều hành nên lấy cùng kỳ năm trước làm so sánh chính.
- **Thị trường áp đảo**: UK chiếm 85% doanh thu; xếp hạng nước theo doanh thu tuyệt đối chỉ cho thấy UK. Xếp hạng
  theo **thay đổi** so cùng kỳ, hoặc tách UK.
- **Khách vãng lai**: không có `customer_id`; KPI theo khách chỉ tính khách có mã, ghi rõ trong định nghĩa.
- **Kỳ chưa đủ**: mốc từ dữ liệu, không gõ cứng.
- **Ít KPI**: 3-5 tile; mỗi tile gắn với một câu hỏi. KPI không đổi quyết định nào thì bỏ (ví dụ "số dòng hàng").
- **Yêu cầu B**: grain giờ; KPI như lượt TB mỗi giờ theo khung giờ × loại ngày, tỉ lệ giờ vượt ngưỡng công suất,
  ảnh hưởng thời tiết so trong cùng tháng; lưu ý giờ thiếu trong `hour.csv` (ví dụ 29/10/2012 chỉ có giờ 0) và tuần
  cuối chỉ có một ngày.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Người dùng và quyết định | 15 | Nêu người dùng, nhịp dùng, quyết định cụ thể thay đổi nhờ dashboard; nói rõ ai không phải người dùng |
| Câu hỏi và KPI | 20 | 3-5 câu hỏi gắn quyết định; 3-7 KPI có định nghĩa, công thức đúng grain (đếm distinct, tỉ lệ tổng/tổng), so sánh, owner; dùng định nghĩa chung của track |
| Bố cục, bộ lọc, drill-down | 15 | KPI → trend → breakdown → chi tiết; bộ lọc ít, có mặc định, nối vào mọi card; đường drill-down có chủ đích |
| Refresh, cache, kỳ chưa đủ | 10 | Lịch nạp, TTL cache không dài hơn chu kỳ nạp, hiện "dữ liệu tới lúc", kỳ chưa đủ không đặt cạnh kỳ đủ |
| Bản dựng | 20 | Script idempotent trong `starter/`, dashboard khớp spec, ảnh chụp; lý do chọn công cụ theo người dùng/quyền/duy trì |
| Đối chiếu số | 10 | Ba con số khớp SQL/pandas độc lập, ghi cả hai giá trị |
| `spec_lint.py` | 10 | Test pass; thông báo lỗi chỉ đúng phần/KPI/cột |

Từ 70 điểm trở lên là đạt; dưới 50 điểm ở hai mục đầu thì dashboard chưa nên dựng.

## Sai lầm hay gặp

- Bắt đầu từ "dữ liệu có gì" và đưa lên 15 tile.
- KPI không có so sánh, hoặc so tháng trước trên dữ liệu mùa vụ.
- Bar chart doanh thu theo 43 nước: một cột UK và 42 cột gần bằng 0.
- Spec nói "lọc theo nước" nhưng một card không nối bộ lọc.
- Không đối chiếu số trước khi gửi link.
