# Hướng làm: experiment brief cho voucher khách đang hoạt động

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết sáu hàm, các con số tham chiếu trên bộ thật,
các quyết định thiết kế cần cân nhắc, một bộ khung brief mẫu và rubric chấm.

## Sáu hàm

- **`eligible_customers`**: lọc `invoice_date >= as_of - Timedelta(days=lookback)` và `< as_of`, lấy
  `customer_id` duy nhất, `sorted`, bọc `pd.Index(..., name="customer_id")`. Nửa mở ở `as_of`: hoá đơn lúc 0 giờ
  ngày bắt đầu là kết quả của thí nghiệm, không phải lịch sử dùng để chọn người (chọn người bằng dữ liệu sau khi
  bắt đầu là lỗi kinh điển làm hai nhóm lệch nhau).
- **`outcome_window`**: lọc cửa sổ và khách trong danh sách, `groupby("customer_id")`, rồi
  `reindex(customers, fill_value=0)`. Bước `reindex` là điểm chính: metric "doanh thu/khách" phải chia cho **mọi**
  khách được chia nhóm, kể cả người không mua; tính trên người mua thì voucher làm "giá trị đơn" thay đổi và kết
  luận sai hướng.
- **`assign_arm`**: `hashlib.sha256(f"{salt}:{int(cid)}".encode()).hexdigest()`, lấy 8 ký tự hex đầu,
  `% 10_000`, so với `round(share * 10_000)`. `int(cid)` quan trọng: `customer_id` đọc từ xlsx là `float`
  (`12346.0`), không ép thì chuỗi hash khác và nhóm của cùng một khách đổi theo kiểu dữ liệu.
- **`mean_sample_size`**: `ceil(2 * (z_{1-α/2} + z_{1-β})² * sd² / mde²)`. Khớp `NormalIndPower` với effect size
  `mde / sd`.
- **`readout`**: dòng `purchased` như `diff_ci` ở Intermediate 01 (Wald cho khoảng, tỉ lệ gộp cho p); dòng
  `revenue` là Welch như Basic 03, `clip(upper=cap)` trước nếu có `cap`.
- **`aa_false_positive_rate`**: lặp qua `salts`, mỗi lần `assign_arm(outcome.index, salt)` rồi `readout`, đếm
  `p < alpha`.

## Con số tham chiếu (bộ thật, ngày bắt đầu 2011-09-01)

| Câu hỏi | Con số |
| --- | --- |
| Khách đang hoạt động (mua trong 90 ngày trước 1/9/2011) | **1 923** khách |
| Tỉ lệ mua trong 30 ngày | **37.9%** (1/3/2011: 29.9%; 1/6: 32.4%; 1/8: 31.8%; 1/9/2010: 35.6%) |
| Doanh thu 30 ngày/khách | TB 354 GBP, sd **2 332**, p99 3 674, lớn nhất 75 412 (một khách) |
| Cắt ở p99 | TB 246.7, sd **550.7** (giảm 4.2 lần, phương sai giảm khoảng 18 lần) |
| Guardrail huỷ đơn (baseline) | dòng huỷ bằng 2.9% doanh thu gộp; 183/1 923 khách có ít nhất một dòng huỷ |
| Chia nhóm, salt `welcome-voucher-2011` | treatment 958, control 965, SRM p = 0.87 |
| MDE tỉ lệ mua với 958 khách mỗi nhóm | khoảng **+6.3 điểm %** (37.9% → 44.2%); +5 điểm cần 1 511 mỗi nhóm |
| Doanh thu/khách không cắt | +10%: 68 046 mỗi nhóm; +30%: 7 561. Không khả thi |
| Doanh thu/khách cắt p99 | +20%: 1 956 mỗi nhóm; +30%: 870. MDE với 958 mỗi nhóm khoảng **+29%** |
| Readout chạy thử (A/A, cùng salt) | tỉ lệ mua −0.35 điểm %, p = 0.87; doanh thu không cắt **−186 GBP**, CI [−394; +22], p = 0.08; cắt p99 −5.8, p = 0.82 |
| 200 lần A/A (`aa-0` … `aa-199`) | tỉ lệ mua: **5.5%** p < 0.05; doanh thu cắt p99: 2.5% |

Đọc readout chạy thử: không ai nhận voucher, nhưng doanh thu không cắt cho chênh lệch −186 GBP/khách với p = 0.08,
gần "có ý nghĩa", chỉ vì khách 75 nghìn GBP rơi vào control. Cắt đuôi ở p99 đưa chênh lệch về −5.8. A/A 5.5%
(khoảng tin cậy của tỉ lệ này với 200 lần lặp là khoảng ±3 điểm) nên quy trình không tự tạo hiệu ứng.

## Các quyết định cần cân nhắc

- **Metric chính**: tỉ lệ mua dễ đo, MDE +6.3 điểm, nhưng không nói voucher có **lời** không (khách mua nhiều
  hơn ở giá thấp hơn). Lựa chọn tốt hơn: **doanh thu theo giá niêm yết (trước khi trừ voucher) trên mỗi khách
  được chia nhóm trong 30 ngày, cắt ở p99 của giai đoạn trước** (ngưỡng ghi số cụ thể trong brief, ví dụ 3 674
  GBP), tỉ lệ mua là metric phụ, chi phí voucher (giá trị giảm giá thực tế) là metric phụ để tính lợi nhuận. Đo
  theo giá niêm yết để metric so được với baseline lịch sử và với control (không ai giảm giá); ngưỡng hoà vốn phía
  dưới tính trên **chính metric này**. Ngưỡng cắt tính từ dữ liệu **trước** thí nghiệm (hoặc từ control), không
  chọn sau khi xem kết quả.
- **Ngưỡng hoà vốn** (ví dụ giả định: biên lợi nhuận gộp 40%, mọi đơn của nhóm treatment đều dùng voucher): gọi
  R là doanh thu theo giá niêm yết. Control lãi 0.4·R_c. Treatment bán giảm 10% nhưng giá vốn giữ nguyên, nên lãi
  (0.4 − 0.1)·R_t = 0.3·R_t. Hoà vốn khi R_t / R_c ≥ 0.4 / 0.3 = **1.33**, tức doanh thu **theo giá niêm yết** tăng
  +33%. Cùng điều kiện đó viết theo doanh thu **sau voucher** R′_t = 0.9·R_t là R′_t / R_c ≥ 1.2, tức +20%: hai con
  số mô tả cùng một ngưỡng trên hai metric khác nhau. Lỗi hay gặp là đo metric sau voucher mà so với ngưỡng +33%
  (hoặc ngược lại); brief phải ghi rõ ngưỡng đi với metric nào. Thực tế không phải đơn nào cũng dùng voucher nên
  ngưỡng thấp hơn.
- **Power so với ngưỡng**: MDE khoảng +29% (metric theo giá niêm yết, cắt p99, 958 khách mỗi nhóm) nhỏ hơn ngưỡng
  +33%: nếu voucher đúng ở mức hoà vốn, thí nghiệm có hơn 80% khả năng thấy hiệu ứng **khác 0**. Nhưng để cận dưới
  của khoảng tin cậy **vượt** +33% thì hiệu ứng thật phải khoảng +60% trở lên; với hiệu ứng nằm giữa 0 và hoà vốn,
  kết quả thường là "chưa kết luận". Nói thẳng với Giám đốc kinh doanh: thí nghiệm một đợt này loại được "voucher vô
  dụng" và "voucher lãi rất rõ", không đo chính xác được vùng quanh hoà vốn. Muốn hơn thì mở rộng đối tượng (nới
  định nghĩa đang hoạt động lên 180 ngày) hoặc lặp lại thí nghiệm ở đợt sau và gộp kết quả.
- **Tỉ lệ chia**: 50/50 cho power cao nhất. Nếu CRM muốn ít khách nhận voucher hơn (rủi ro chi phí), 30/70 làm
  MDE tăng; tính lại và ghi rõ.
- **Thời lượng**: gửi một lần ngày 1/9, đo 30 ngày, đọc sau khi dữ liệu và đơn huỷ của tháng 9 đã ổn định (khoảng
  5/10). Không có "chạy thêm vài tuần cho đủ mẫu": đối tượng cố định ngay từ đầu, muốn nhiều người hơn phải nới
  định nghĩa "đang hoạt động" (ví dụ 180 ngày) và tính lại baseline.
- **Mùa vụ**: tháng 9 là đầu mùa cao điểm (baseline 37.9% so với 30-32% tháng 3-8). Kết quả tháng 9 không tự động
  đúng cho tháng 3. Thêm: voucher có thể chỉ **kéo cầu sớm** (khách đặt hàng Giáng sinh sớm hơn), nên theo dõi
  doanh thu 90 ngày làm metric phụ.
- **Lây nhiễm**: khách sỉ chia sẻ mã voucher cho đồng nghiệp ở nhóm control làm hiệu ứng đo được **nhỏ hơn** thật.
  Mã voucher gắn với tài khoản.
- **SRM và kiểm tra trước khi đọc**: SRM p < 0.001 thì dừng; tỉ lệ email gửi thành công giống nhau ở hai nhóm;
  readout chỉ mở một lần vào ngày định trước.

## Khung brief mẫu (rút gọn)

- **Quyết định**: gửi voucher 10% cho mọi khách đang hoạt động vào mùa cao điểm hay không. Giả thuyết: voucher
  làm doanh thu sau giảm giá trên mỗi khách tăng đủ để bù chi phí giảm giá.
- **Đối tượng**: 1 923 khách có mua trong 90 ngày trước 1/9/2011; chia 50/50 theo hash `welcome-voucher-2011`
  (958 / 965).
- **Metric**: chính là doanh thu theo giá niêm yết/khách trong 30 ngày, cắt ở 3 674 GBP; phụ là chi phí voucher, tỉ lệ mua (baseline
  37.9%) và doanh thu 90 ngày; guardrail là tỉ lệ doanh thu bị huỷ (baseline 2.9%, ngưỡng +1 điểm) và giá trị đơn
  trung bình.
- **Sample size**: MDE khoảng +29% doanh thu (giá niêm yết, cắt đuôi), +6.3 điểm tỉ lệ mua; hoà vốn cần khoảng
  +33% trên chính metric này (tương đương +20% nếu đo sau voucher; biên 40%, ví dụ giả định). Đủ để thấy một hiệu ứng
  cỡ hoà vốn khác 0, không đủ để chứng minh đã vượt hoà vốn.
- **Quy tắc**: SRM hoặc guardrail hỏng thì điều tra; CI trên < ngưỡng hoà vốn thì không gửi rộng; CI dưới > 0 và
  ước lượng ≥ hoà vốn thì gửi; còn lại chưa kết luận, không gửi rộng, thiết kế lần sau với đối tượng lớn hơn.
- **Readout chạy thử**: bảng A/A ở trên, ghi rõ "không ai nhận voucher", nêu bài học về khách 75 nghìn GBP.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm và số liệu | 15 | Sáu hàm pass test; brief dùng đúng các con số baseline, sd, p99 từ notebook |
| Câu hỏi và quyết định | 10 | Nêu rõ quyết định, người quyết, giả thuyết có cơ chế |
| Đối tượng và chia nhóm | 10 | Định nghĩa "đang hoạt động" có ngày, số khách, đơn vị chia nhóm, hash + salt, vì sao cố định đối tượng trước |
| Metric và guardrail | 20 | Metric chính tính trên mọi khách được chia nhóm, xử lý đuôi dài bằng ngưỡng đặt trước, phân biệt tỉ lệ mua với doanh thu; guardrail có baseline và ngưỡng |
| Sample size | 15 | MDE thật cho cả hai metric, so với ngưỡng hoà vốn tính trên đúng metric chính (ghi rõ giả định biên lợi nhuận); nói thẳng metric nào không khả thi và thí nghiệm phân biệt được điều gì |
| Kiểm tra và quy tắc | 15 | SRM, không peeking, một ngày đọc kết quả; quy tắc ship/không ship/chưa kết luận viết theo CI và ngưỡng, trước khi có dữ liệu |
| Readout chạy thử | 10 | Bảng A/A có số; giải thích chênh lệch doanh thu không cắt đuôi; tỉ lệ false positive gần 5% |
| Rủi ro | 5 | Ít nhất hai rủi ro cụ thể: mùa vụ, kéo cầu sớm, lây nhiễm mã, khách sỉ |

Từ 70 điểm trở lên là brief có thể trình Giám đốc kinh doanh.

## Sai lầm hay gặp

- Tính doanh thu trung bình chỉ trên khách có mua: bỏ người không mua làm metric đo "giá trị đơn", không đo tác
  động lên doanh thu.
- Chọn ngưỡng cắt đuôi hoặc chọn metric chính sau khi xem kết quả.
- Dùng baseline tháng 3-8 để tính cỡ mẫu cho thí nghiệm tháng 9, hoặc ngược lại dùng kết quả tháng 9 cho cả năm.
- Nói "+20% doanh thu cần 949 khách mỗi nhóm" khi tính MDE tương đối trên trung bình **không cắt** (354) nhưng độ
  lệch chuẩn **đã cắt**: phải dùng trung bình và độ lệch chuẩn của cùng một metric (đã cắt: 246.7 và 550.7, cần
  1 956 khách mỗi nhóm).
