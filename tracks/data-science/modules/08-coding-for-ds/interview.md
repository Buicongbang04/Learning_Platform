# Câu hỏi phỏng vấn: Coding cho Data Scientist

## Bạn tiếp cận một bài coding thế nào khi chưa nghĩ ra cách tối ưu ngay?

Một quy trình nói to được, để người phỏng vấn theo kịp và có thể gợi ý đúng chỗ:

1. **Hỏi lại đề**: cỡ input (100 hay 100 triệu?), có trùng không, có số âm / giá trị thiếu không,
   input rỗng thì trả gì, có cần giữ thứ tự không.
2. **Ví dụ nhỏ tự tính tay**, gồm một trường hợp biên.
3. **Brute force + độ phức tạp**: "so mọi cặp là $$O(n^2)$$; với n = $$10^5$$ là $$10^{10}$$ phép,
   không đủ nhanh".
4. **Tìm chỗ lãng phí** của brute force: tra cứu lặp lại (→ hash map), dữ liệu sắp xếp được (→ two
   pointers / binary search), đoạn liên tiếp (→ sliding window), chỉ cần k phần tử lớn nhất (→ heap).
5. Code, rồi **tự chạy ví dụ** từng dòng trước khi nói "xong", và nêu độ phức tạp thời gian, bộ nhớ.

Điều người phỏng vấn DS để ý hơn so với vòng SWE: bạn có hỏi về dữ liệu không. "Mảng có trùng
không?" và "timestamp đã sắp xếp chưa?" là câu hỏi của người làm dữ liệu thật.

## Two sum: hash map hay sắp xếp rồi two pointers? Đánh đổi là gì?

- **Hash map**: một lượt, với mỗi `x` tra `target − x` trong dict giá trị → chỉ số. Thời gian
  $$O(n)$$, bộ nhớ $$O(n)$$. Giữ được chỉ số gốc.
- **Sort + two pointers**: $$O(n \log n)$$ thời gian, $$O(1)$$ bộ nhớ thêm nếu sort tại chỗ, nhưng
  mất chỉ số gốc (phải sort cặp (giá trị, chỉ số)).

Chọn hash map khi cần chỉ số và bộ nhớ không phải vấn đề. Chọn two pointers khi mảng **đã sắp xếp
sẵn** (khi đó nó là $$O(n)$$ và $$O(1)$$ bộ nhớ), hoặc khi đề hỏi **đếm** cặp thoả bất đẳng thức
(`a + b <= budget`), việc mà hash map không làm được.

Trường hợp biên phải nhắc: phần tử không được dùng hai lần (`[3, 4]`, target 6 → không có), giá trị
trùng (`[3, 4, 3]` → (0, 2)), nhiều đáp án thì trả cái nào.

## Tìm 10 sản phẩm bán chạy nhất từ một luồng 1 tỉ sự kiện không vừa bộ nhớ.

Tách hai phần: **đếm** và **chọn top-k**.

- Chọn top-k từ m sản phẩm đã đếm: heap cỡ k, $$O(m \log k)$$ thời gian, $$O(k)$$ bộ nhớ; tốt hơn
  sort cả m sản phẩm khi m lớn.
- Đếm: nếu số sản phẩm khác nhau vừa RAM (vài triệu sản phẩm là vài trăm MB) thì một dict là đủ, dù
  số *sự kiện* là 1 tỉ. Nếu không vừa: chia theo hash của product_id thành nhiều phần (mỗi sản phẩm
  chỉ nằm trong một phần), đếm từng phần, lấy top-k mỗi phần rồi trộn: chính là MapReduce /
  `GROUP BY` trong Spark hoặc warehouse.
- Nếu chấp nhận xấp xỉ và cần chạy streaming: Count-Min Sketch + heap, hoặc thuật toán Space-Saving
  (Misra-Gries): bộ nhớ cố định, sai số có cận.

Câu trả lời senior nói thêm: trong thực tế bạn viết `SELECT product_id, COUNT(*) ... ORDER BY 2 DESC
LIMIT 10` trên warehouse; engine làm đúng việc trên. Biết thuật toán bên dưới giúp bạn hiểu vì sao
query đó rẻ hay đắt.

## Tính trung vị chạy của một luồng số. Vì sao không dùng list sắp xếp?

Hai heap: max-heap giữ nửa dưới, min-heap giữ nửa trên, cỡ chênh nhau tối đa 1. Mỗi phần tử: đẩy vào
heap đúng phía, cân lại nếu lệch, trung vị là đỉnh heap lớn hơn (lẻ) hoặc trung bình hai đỉnh (chẵn).
Mỗi bước $$O(\log n)$$, cả luồng $$O(n \log n)$$. Python chỉ có min-heap nên max-heap lưu số âm.

`bisect.insort` vào list sắp xếp tìm vị trí $$O(\log n)$$ nhưng **chèn** là $$O(n)$$ vì phải dời các
phần tử phía sau, tổng $$O(n^2)$$. Nó nhanh với vài chục nghìn phần tử (memmove trong C), nhưng đo
trên 300 nghìn phần tử: hai heap 0.13 giây, `insort` 4.5 giây, và khoảng cách tăng tuyến tính theo n.

Câu hỏi nối tiếp hay gặp: trung vị trong **cửa sổ trượt** (chỉ k phần tử gần nhất). Hai heap cần xoá
phần tử rời cửa sổ: dùng lazy deletion (đánh dấu, xoá khi nó lên đỉnh) hoặc một cấu trúc sắp xếp có
xoá $$O(\log k)$$ như `sortedcontainers.SortedList`.

## Đếm số giao dịch nhiều nhất trong 1 phút bất kỳ để phát hiện gian lận. Thuật toán và điều kiện?

Sắp xếp timestamp theo từng thẻ (nếu chưa sắp), rồi sliding window: con trỏ phải đi qua từng giao
dịch, con trỏ trái tiến lên khi `t[right] − t[left] > 60 giây`; kích thước cửa sổ lớn nhất là đáp
án. Mỗi con trỏ đi một chiều nên $$O(n)$$ sau khi sort.

Điều kiện để sliding window đúng là **tính đơn điệu**: mở rộng cửa sổ chỉ làm "vi phạm" tăng, co lại
chỉ làm giảm. Với khoảng thời gian thì luôn đúng. Với "đoạn con có tổng ≤ budget" thì chỉ đúng khi
giá trị không âm; có số âm (hoàn tiền) thì dùng prefix sum + cấu trúc tra cứu.

Trong SQL bài này là `COUNT(*) OVER (PARTITION BY card ORDER BY ts RANGE BETWEEN INTERVAL 60 SECOND
PRECEDING AND CURRENT ROW)`. Chú ý `RANGE` (theo giá trị thời gian) khác `ROWS` (theo số dòng).

## Binary search trên đáp án là gì? Cho một ví dụ dữ liệu.

Khi đáp án là một con số và câu hỏi "giá trị c đã đủ chưa?" là **đơn điệu** (đủ ở c thì đủ ở mọi
giá trị lớn hơn), ta tìm nhị phân trên c thay vì trên mảng. Chi phí: $$O(\log S)$$ lần kiểm, mỗi lần
$$O(n)$$.

Ví dụ: sức chứa xe tối thiểu mỗi ngày để giao hết các kiện theo thứ tự trong D ngày. Cận dưới là
kiện nặng nhất, cận trên là tổng; kiểm "đủ chưa" bằng cách mô phỏng chất hàng. Ví dụ khác trong công
việc DS: ngưỡng điểm model nhỏ nhất để số cảnh báo mỗi ngày không vượt năng lực đội vận hành (số
cảnh báo giảm đơn điệu theo ngưỡng).

Lỗi hay gặp: `lo = mid` thay vì `mid + 1` gây lặp vô hạn; cận dưới sai; quên kiểm tính đơn điệu
(nếu không đơn điệu thì binary search cho đáp án sai mà không báo lỗi).

## ROW_NUMBER, RANK, DENSE_RANK khác nhau thế nào? Khi nào dùng cái nào?

Với giá trị (100, 100, 90): `ROW_NUMBER` cho 1, 2, 3; `RANK` cho 1, 1, 3; `DENSE_RANK` cho 1, 1, 2.

- **Khử trùng lặp** (giữ đúng một dòng mỗi nhóm, như review mới nhất mỗi đơn của Olist): `ROW_NUMBER`,
  kèm cột phá hoà trong `ORDER BY` để kết quả xác định (deterministic).
- **"Top 3 sản phẩm mỗi danh mục"**: hỏi lại đề. Nếu đồng hạng được tính cùng hạng và vẫn lấy đủ 3
  *mức* thì `DENSE_RANK`; nếu "tối đa 3 dòng" thì `ROW_NUMBER`.
- `RANK` hợp với bảng xếp hạng kiểu thể thao (hai người đồng hạng nhất thì không có hạng nhì).

Trên Olist: 99 224 dòng review cho 98 673 đơn. Dùng `RANK` để "giữ review mới nhất" thì hai review
cùng timestamp đều được giữ, và mọi join sau đó nhân dòng.

## Viết query retention theo cohort tháng. Những lỗi nào hay gặp?

Các bước: (1) bảng `(khách, tháng)` không trùng từ đơn hợp lệ; (2) cohort = tháng nhỏ nhất của mỗi
khách; (3) join lại, `month_index = DATE_DIFF('month', cohort, month)`; (4) đếm khách theo `(cohort,
month_index)`; (5) chia cho cỡ cohort (dòng `month_index = 0`).

Lỗi hay gặp, đều có trên Olist thật:

- **Sai đơn vị khách**: Olist cấp `customer_id` mới cho mỗi đơn (99 441 id cho 96 096 người). Tính theo
  `customer_id` thì retention bằng 0.
- **Không phân biệt 0 với chưa quan sát được** (right-censoring): cohort 2018-07 chưa thể có dữ liệu
  tháng thứ 2.
- **Trung bình không trọng số**: trung bình cộng cột tháng 1 trên Olist ra 4.96% vì cohort 2016-12 chỉ
  có 1 khách và khách đó quay lại (100%). Trung bình có trọng số đúng là 0.48%.
- Đếm đơn thay vì đếm khách khác nhau ở mỗi ô.
- Dùng đơn huỷ / chưa giao để xác định cohort.

## Doanh thu trong dashboard lớn hơn số kế toán báo 27%. Bạn nghi gì đầu tiên?

**Join nhân dòng (fan-out).** Trên Olist: tổng `payment_value` là 16 008 872.12; join `order_items`
với `order_payments` rồi cộng thì ra 20 308 134.71, thổi phồng 26.9%. Lý do: một đơn có nhiều món và
nhiều khoản thanh toán; mỗi khoản thanh toán lặp lại theo số món.

Cách kiểm: đếm số dòng trước và sau mỗi join; so `COUNT(*)` với `COUNT(DISTINCT order_id)`; đối chiếu
tổng với một nguồn độc lập. Cách sửa: gộp về đúng grain trước khi join (tổng thanh toán theo đơn,
tổng doanh thu món theo đơn, rồi mới join ở grain đơn). Trong pandas: `merge(validate="one_to_one")`
hoặc `"many_to_one"` để lỗi hiện ra ngay.

Các nghi phạm khác: đơn huỷ/hoàn tiền không bị loại, khác múi giờ khi cắt ngày, tiền tệ, tính cả phí
vận chuyển.

## `NOT IN` và `NOT EXISTS` khác nhau thế nào?

Khác nhau khi subquery có NULL. `x NOT IN (1, 2, NULL)` tương đương `x <> 1 AND x <> 2 AND x <> NULL`;
vế cuối là UNKNOWN nên cả biểu thức không bao giờ TRUE, và query trả **rỗng** mà không báo lỗi.
`NOT EXISTS` so từng dòng bằng điều kiện join nên không bị ảnh hưởng.

Quy tắc: tìm "dòng ở A không có ở B" thì dùng `NOT EXISTS` hoặc `LEFT JOIN B ... WHERE B.key IS NULL`
(anti-join). Trên Olist, "đơn không có review" ra 768 đơn với cả ba cách vì cột `order_id` của bảng
review không có NULL, nhưng code phải đúng cả khi dữ liệu ngày mai có NULL.

## Tìm chuỗi ngày đăng nhập liên tiếp dài nhất của mỗi user (gaps-and-islands).

```sql
WITH days AS (
    SELECT DISTINCT user_id, CAST(event_time AS DATE) AS d FROM logins
), grouped AS (
    SELECT user_id, d,
           d - CAST(ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d) AS INTEGER) AS grp
    FROM days
)
SELECT user_id, MAX(streak) AS longest
FROM (SELECT user_id, grp, COUNT(*) AS streak FROM grouped GROUP BY 1, 2)
GROUP BY 1;
```

Ý tưởng: trong một chuỗi ngày liên tiếp, ngày tăng 1 và số thứ tự cũng tăng 1, nên hiệu là hằng số.
Bắt buộc `DISTINCT` trước (hai lần đăng nhập cùng ngày làm hỏng phép trừ). Biến thể cho phép khoảng
trống ("nghỉ tối đa 1 ngày vẫn tính là liên tục"): `LAG` lấy ngày trước, cờ `is_new = d − prev > 2`,
`SUM(is_new) OVER (...)` ra số thứ tự đợt. Trên Olist, áp cho seller theo tháng: 2 970 seller tạo 5 183
chuỗi tháng liên tiếp, gộp còn 3 914 đợt khi cho phép nghỉ 1 tháng.

## Viết funnel cho vòng đời đơn hàng. "Tuần tự", "chặt" nghĩa là gì?

- **Funnel độc lập**: đếm mỗi bước riêng. Dễ viết nhưng có thể cho tỉ lệ > 100% và không trả lời
  "rơi ở đâu".
- **Tuần tự**: đơn chỉ tính ở bước k nếu đã qua mọi bước trước (`COUNT(*) FILTER (WHERE b1 AND b2 AND
  ... AND bk)`). Số đơn giảm dần, tỉ lệ so với bước trước có nghĩa.
- **Chặt**: thêm điều kiện thời gian, mốc sau không sớm hơn mốc trước.

Trên Olist (99 441 đơn), bước "giao cho hãng vận chuyển": funnel tuần tự 97 644, funnel chặt 96 285.
1 359 đơn có mốc giao cho hãng **trước** mốc duyệt thanh toán. Chỗ rơi lớn nhất của cả funnel là
review: chỉ 78.9% đơn đã giao và có review được 4–5 sao. Trả lời tốt nêu cả hai: con số và câu hỏi
"1 359 đơn kia là lỗi log hay quy trình thật?" cần hỏi đội vận hành.

## Notebook pandas của đồng nghiệp chạy 2 giờ. Bạn làm gì?

1. **Đo trước, đừng đoán**: `%time` từng cell, `%prun` / `line_profiler` cho hàm chậm. Thường 90%
   thời gian nằm ở một hai chỗ.
2. **Vòng lặp theo dòng** (`iterrows`, `apply(axis=1)`, `for` trên DataFrame): thay bằng phép toán trên
   cột, `np.where`/`np.select`, `merge`, `groupby().transform`. Trên Olist, phép trừ hai cột ngày nhanh
   hơn `iterrows` hàng trăm tới hàng nghìn lần; bảng điểm seller viết lại nhanh hơn 16–23 lần.
3. **Đọc ít hơn**: `usecols`, lọc sớm, Parquet thay CSV.
4. **dtype**: `category` cho cột ít giá trị (cột `order_status` từ 1.69 MB xuống 0.10 MB), downcast số
   nguyên. Bộ nhớ ít hơn thì ít swap và cache tốt hơn.
5. **Join nhân dòng** ngoài ý muốn làm dữ liệu phình ra: kiểm số dòng sau mỗi `merge`.
6. Nếu vẫn chậm: polars lazy hoặc DuckDB cho phần biến đổi nặng.

Quan trọng không kém: viết test so kết quả mới với cũ (`assert_frame_equal`) trước khi thay, và hỏi
có cần chạy nhanh không: notebook chạy mỗi tháng một lần có thể không đáng tối ưu.

## groupby: `agg`, `transform`, `apply` khác nhau thế nào?

- `agg`: mỗi nhóm thành **một dòng** (sum, mean, count, nhiều hàm cùng lúc với named aggregation).
- `transform`: trả kết quả **cùng index với dữ liệu gốc** (mỗi dòng nhận giá trị của nhóm mình), dùng
  cho tỉ trọng trong nhóm, chuẩn hoá theo nhóm, điền thiếu bằng trung bình nhóm.
- `apply`: gọi hàm Python tuỳ ý trên từng nhóm (một DataFrame con). Linh hoạt nhất, chậm nhất: chi
  phí cố định mỗi nhóm cộng với việc không tối ưu được.

Ví dụ thật: tỉ trọng doanh thu từng món trong doanh thu seller trên 112 650 dòng `order_items`:
`groupby().apply` khoảng 1.3 giây, `price / groupby().price.transform("sum")` khoảng 0.01 giây. Chỉ
dùng `apply` khi logic thật sự không biểu diễn được bằng `agg`/`transform` (ví dụ fit một model nhỏ mỗi
nhóm).

## pandas, polars hay DuckDB? Bạn chọn thế nào?

Không có câu trả lời duy nhất; tiêu chí là cỡ dữ liệu, kiểu logic, và ai đọc code.

- **pandas**: dữ liệu vừa RAM, khám phá, vẽ, đưa vào sklearn/statsmodels. Hệ sinh thái lớn nhất.
- **polars**: pipeline biến đổi nhiều bước trong Python cần nhanh; đa luồng, lazy với optimizer
  (projection và predicate pushdown).
- **DuckDB**: logic thuần join/aggregate, team mạnh SQL, file Parquet/CSV lớn hơn RAM (out-of-core).

Đo trên bảng điểm seller của Olist nhân 10 lần (1.13 triệu món): pandas đã vector hoá 3.2 giây,
polars 0.50 giây, DuckDB 0.28 giây. Nhưng ở cỡ Olist gốc, pandas cũng chỉ 0.3 giây. Ba công cụ đổi
dữ liệu cho nhau qua Arrow gần như miễn phí, nên có thể dùng DuckDB cho bước join nặng và pandas cho
bước cuối. Đổi công cụ có chi phí (học API, review code, thư viện xung quanh), nên chỉ đổi khi thời
gian hoặc bộ nhớ thật sự là nút thắt.

## Case: Dashboard ghi "retention tháng 1 trung bình 5%", bạn tính lại ra 0.48%. Bạn trình bày với PM thế nào?

Đây là câu hỏi về **giao tiếp** nhiều hơn SQL. Trên Olist thật đúng là có hai con số này: trung bình
cộng cột tháng 1 của ma trận cohort là 4.96%, trung bình có trọng số là 0.48%.

1. Giải thích bằng ví dụ, không bằng công thức: "Cohort tháng 12/2016 chỉ có 1 khách, khách đó quay
   lại nên ô của nó là 100%. Trung bình cộng coi ô 1 khách nặng ngang ô 7 059 khách của tháng 11/2017."
2. Đưa con số đúng kèm định nghĩa: "Trong 100 khách mới, khoảng 0.5 người có đơn ở tháng kế tiếp; tính
   cả đời thì 3% khách mua từ hai lần."
3. Nói hệ quả kinh doanh: quyết định dựa trên 5% (ví dụ ngân sách cho chương trình giữ khách) có thể
   sai cả chục lần.
4. Sửa tận gốc: định nghĩa metric một chỗ (semantic layer / dbt metric), có test, ghi rõ trong
   dashboard; kiểm các dashboard khác dùng cùng logic.

Không đổ lỗi người làm dashboard; nói về định nghĩa và cách tránh lặp lại.

## Case: Tỉ lệ "duyệt thanh toán → giao cho hãng vận chuyển" tuần này giảm 2 điểm phần trăm. Bạn điều tra thế nào?

1. **Dữ liệu có đúng không**: pipeline có trễ không (đơn tuần này chưa kịp cập nhật mốc giao cho hãng
   là nguyên nhân phổ biến nhất của "giảm" ở cuối kỳ), có đổi định nghĩa / schema không, có lỗi thứ
   tự timestamp (trên Olist có 1 359 đơn giao cho hãng trước khi được duyệt).
2. **Cửa sổ thời gian công bằng**: so các đơn đã có đủ thời gian (ví dụ đơn duyệt từ 7 ngày trước) với
   cùng độ "chín" ở tuần trước.
3. **Chia nhỏ**: theo seller, bang của seller, danh mục, hãng vận chuyển, phương thức thanh toán. Một
   seller lớn ngừng hoạt động có thể kéo cả tỉ lệ xuống (mix shift).
4. **Bên ngoài**: lễ, đình công vận tải, thay đổi chính sách.
5. **Kết luận theo tác động**: 2 điểm trên bao nhiêu đơn, ảnh hưởng gì tới giao trễ và review xấu
   (đơn trễ có 54.1% review xấu, so với 12.8% chung).

Trả lời tốt đi từ "con số có thật không" trước "vì sao".

## Case: Chỉ 3% khách Olist mua lần hai. Đội growth hỏi nên đầu tư vào giữ khách hay thu hút khách mới.

Dữ liệu: 93 350 khách có đơn giao xong, 3.0% có từ hai đơn; retention tháng 1 khoảng 0.5%.

Khung trả lời:

1. **Hiểu vì sao thấp trước khi kết luận "giữ khách kém"**: Olist bán qua sàn đối tác, khách quay lại
   có thể mua qua kênh khác (dữ liệu không thấy); danh mục chủ yếu là đồ bền (nội thất, điện gia dụng)
   nên tần suất mua tự nhiên thấp. So retention theo danh mục để tách hai yếu tố.
2. **Tìm đòn bẩy**: khách có trải nghiệm đơn đầu tốt (giao đúng hẹn, review 5 sao) có quay lại nhiều
   hơn không? Đây là tương quan; muốn biết nhân quả cần thí nghiệm hoặc phương pháp của module 06.
3. **Lượng hoá**: tăng repeat rate từ 3% lên 4% đem lại bao nhiêu đơn so với chi phí; so với chi phí
   thu hút một khách mới (CAC). Với tần suất mua tự nhiên thấp, mỗi điểm phần trăm repeat rất đắt.
4. **Đề xuất kiểm chứng rẻ**: thí nghiệm nhỏ (voucher mua lần hai cho danh mục tiêu dùng lặp lại),
   metric chính là đơn thứ hai trong 90 ngày, guardrail là biên lợi nhuận.

Câu trả lời senior không chọn phe ngay mà đưa ra cách để dữ liệu chọn.

## Case: Take-home 8 tiếng với bộ dữ liệu đơn hàng. Bạn nộp gì?

- **Notebook chạy lại được từ đầu** (`Restart & Run All`), đường dẫn tương đối, phiên bản thư viện
  ghi rõ, dữ liệu đọc từ nguồn gốc. Người chấm luôn thử chạy lại.
- **Một trang tóm tắt ở đầu**: câu hỏi, câu trả lời, con số chính, khuyến nghị, hạn chế. Người chấm
  bận đọc phần này trước.
- **Kiểm chất lượng dữ liệu** có ghi lại: trùng khoá, thiếu, timestamp sai thứ tự, đơn vị khách đúng.
- **Code có cấu trúc**: hàm nhỏ cho logic lặp lại, không vòng lặp theo dòng trên dữ liệu lớn, vài
  `assert` cho giả định quan trọng.
- **Ranh giới rõ**: "tôi không làm X vì thời gian; nếu có thêm tôi sẽ làm Y".

Chia thời gian gợi ý: 1 giờ hiểu dữ liệu, 4 giờ phân tích chính, 1.5 giờ viết, 1.5 giờ dọn và chạy lại
từ đầu. Nộp ít mà chắc tốt hơn nhiều mà rời rạc.
