# Câu hỏi phỏng vấn: Python cho DA

## Khi nào bạn dùng Python thay vì Excel hoặc SQL cho một phân tích?

Chọn theo việc, không theo thói quen:

- **SQL** khi dữ liệu nằm trong warehouse và việc chính là lọc, join, tổng hợp. Tính ở nơi dữ liệu nằm, chỉ kéo về
  bảng đã thu nhỏ.
- **Excel / Sheets** khi bảng nhỏ, người nhận cần tự sửa giả định, dùng một lần.
- **Python (pandas)** khi có nhiều bước biến đổi nối nhau (làm sạch, ghép nhiều nguồn, reshape, chuỗi thời gian), cần
  vẽ hay thống kê, cần chạy lại định kỳ, hoặc cần review và test như code.

Câu trả lời tốt nêu cả kết hợp: SQL kéo dữ liệu tổng hợp theo ngày, pandas làm resample và chart, kết quả cuối đưa vào
Excel hoặc dashboard cho người nhận. Và nêu một lần mình đã **chuyển** một báo cáo Excel lặp lại hằng tháng sang Python
vì công thức copy-paste bị lệch giữa các tháng.

## Vì sao chọn pandas chứ không phải polars hay DuckDB cho phân tích hằng ngày?

pandas có hệ sinh thái lớn nhất cho phần DA cần: matplotlib/seaborn, statsmodels, scikit-learn, đọc Excel, và gần như
mọi đồng nghiệp đọc được. Ở cỡ dữ liệu phân tích thường gặp (vài trăm nghìn tới vài triệu dòng), pandas chạy dưới vài
giây; tốc độ không phải nút thắt.

Đổi công cụ khi có lý do đo được:

- **DuckDB**: logic là join/aggregate, team quen SQL, dữ liệu là file CSV/Parquet lớn hơn RAM. SQL chạy thẳng trên file.
- **polars**: pipeline nhiều bước trên hàng chục triệu dòng, cần đa luồng và lazy.
- Ba công cụ trao đổi qua Arrow gần như miễn phí, nên kết hợp được: DuckDB cho bước join nặng, pandas cho bước vẽ cuối.

Câu trả lời yếu: "polars nhanh hơn nên dùng polars" mà không nói dữ liệu cỡ nào, ai bảo trì code.

## `count`, `size` và `nunique` khác nhau thế nào trong `groupby`? Cho ví dụ dùng sai.

- `size`: số **dòng** của nhóm, kể cả dòng có giá trị thiếu.
- `count`: số giá trị **khác null** của cột.
- `nunique`: số giá trị **khác nhau** (mặc định bỏ null).

Ví dụ dùng sai thật: báo cáo "số khách mỗi tháng" viết `agg(customers=("Customer ID", "count"))`. Trên Online Retail II
tháng 11/2011, cách đó ra 64 545 (số **dòng hàng** có mã khách) thay vì 1 664 khách khác nhau, sai gần 39 lần. Lỗi này
không báo gì vì cú pháp đúng. Cách bắt: so với một con số đã biết (số khách tháng trước, số trong CRM), và đặt tên cột
theo đúng định nghĩa (`customers` phải là `nunique`).

## Làm sao tránh join làm nhân dòng (fan-out) trong pandas?

Khi khoá bên phải trùng, `merge` nhân mỗi dòng bên trái với số dòng trùng; tổng doanh thu tăng mà không có lỗi.

1. Truyền `validate="many_to_one"` (hoặc `"one_to_one"`): pandas báo `MergeError` ngay khi khoá bên phải trùng.
2. Reconcile: số dòng sau left join phải bằng số dòng trước; tổng doanh thu trước và sau phải bằng nhau.
3. Nếu bảng phải thật sự nhiều-nhiều (khách thuộc nhiều phân khúc), tổng hợp về đúng grain trước khi ghép, hoặc
   phân bổ trọng số, rồi ghi rõ trong báo cáo.

Trong dplyr 1.1, tham số tương đương là `relationship = "many-to-one"`; trong SQL, kiểm `COUNT(*)` trước và sau join.

## Long và wide khác nhau thế nào? Khi nào dùng `pivot`, `pivot_table`, `melt`?

Long (tidy): mỗi dòng một quan sát (`country`, `year`, `co2`). Wide: mỗi dòng một thực thể, mỗi cột một kỳ.

- Tính toán, `groupby`, `merge`, vẽ bằng seaborn: long.
- Đọc, so sánh cạnh nhau, tính tăng trưởng giữa hai cột, bảng trong slide: wide.
- `pivot` khi mỗi ô đúng một giá trị; nó báo lỗi khi khoá trùng, và lỗi đó có ích vì báo dữ liệu bẩn.
- `pivot_table(aggfunc=...)` khi **cố ý** cộng nhiều dòng vào một ô. Dùng `pivot_table` cho dữ liệu đáng lẽ duy nhất
  là che giấu lỗi trùng.
- `melt` để quay về long (ví dụ đọc file Excel có mỗi tháng một cột).

## Vì sao tăng trưởng 10 năm +63% không phải 6.3% mỗi năm? Khi nào dùng CAGR?

Tăng trưởng gộp theo lãi kép: tăng 5% mỗi năm trong 10 năm là 1.05 mũ 10, tức +62.9%, không phải +50%. Công thức:

$$
\text{CAGR} = \left(\frac{V_{\text{cuối}}}{V_{\text{đầu}}}\right)^{1/n} - 1
$$

Trên OWID, CO2 của Indonesia tăng 63.1% từ 2014 tới 2024, tức CAGR 5.0%/năm. Dùng CAGR khi so các kỳ dài khác nhau
(3 năm với 10 năm) hoặc đặt mục tiêu theo năm. Lưu ý: CAGR chỉ dùng hai điểm đầu cuối, bỏ qua đường đi giữa; năm đầu
hoặc năm cuối bất thường (COVID 2020) làm CAGR lệch, nên luôn nhìn chuỗi trước khi báo một con số.

## `groupby().pct_change()` có bẫy gì với chuỗi thời gian?

Nó so với **dòng trước** trong nhóm, không phải kỳ trước. Thiếu một năm (hoặc tháng không có giao dịch, nên không có
dòng) thì "tăng trưởng năm" thực ra là qua hai năm. Cách làm đúng:

- Đặt dữ liệu lên lưới đủ kỳ (`reindex` mọi năm, `asfreq`, hoặc `resample` với tháng không có dòng ra 0) rồi mới
  `pct_change`/`shift`.
- Hoặc ghép theo khoá thời gian: `merge` bảng với chính nó trên `year + 1`.
- Kiểm: `groupby(...).year.diff()` có giá trị lớn hơn 1 không.

## Dữ liệu bán hàng theo ngày có nhiều ngày không có giao dịch. Bạn tính "doanh thu trung bình mỗi ngày" thế nào?

Đầu tiên hỏi "ngày không có dòng" nghĩa là gì: bán 0 thật, cửa hàng nghỉ (thứ Bảy, lễ), hay mất dữ liệu. Ba trường
hợp cần ba cách xử lý.

Trên Online Retail II (01/12/2010 – 09/12/2011): 374 ngày lịch nhưng chỉ 305 ngày có đơn; mọi thứ Bảy không có đơn, cộng
16 ngày lễ (Giáng sinh, Phục sinh, các ngày bank holiday). Trung bình trên ngày lịch là 28 521 GBP, trên ngày có bán là
34 973 GBP, chênh 22.6%. Con số nào đúng tuỳ câu hỏi: lập kế hoạch kho theo ngày làm việc thì dùng ngày có bán; so với
một cửa hàng mở 7 ngày thì phải nói rõ khác biệt lịch. Báo cáo luôn ghi mẫu số.

## Khi nào dùng seaborn, khi nào matplotlib, khi nào plotly?

- **seaborn** khi khám phá: dữ liệu long, một lệnh ra chart có nhóm (`hue`) hoặc small multiples (`col`), chart thống kê
  (box, violin, khoảng tin cậy).
- **matplotlib** (API hướng đối tượng `fig, ax`) khi chart đưa người khác: chú thích, màu nhấn, tiêu đề là kết luận,
  kích thước cho slide. seaborn vẽ trên matplotlib nên thường bắt đầu bằng seaborn rồi chỉnh bằng `ax`.
- **plotly** khi cần tương tác (hover, zoom) trong Streamlit hoặc file HTML gửi đi.

Bẫy hay gặp: `sns.barplot` mặc định vẽ **trung bình** kèm khoảng tin cậy, không phải tổng. Vẽ doanh thu theo nước bằng
`barplot` trên dữ liệu dòng giao dịch mà không đặt `estimator="sum"` là chart sai số.

## Đồng nghiệp gửi code R dùng dplyr. Bạn đọc và chuyển sang pandas thế nào?

Map động từ sang method: `filter` → lọc boolean/`query`, `select` → chọn cột, `mutate` → `assign`, `arrange` →
`sort_values`, `group_by + summarise` → `groupby().agg()`, `left_join` → `merge(how="left")`, `pivot_longer`/
`pivot_wider` → `melt`/`pivot`. Pipe `|>` tương ứng method chaining.

Ba chỗ dễ dịch sai:

- R `mean(x)` có `NA` thì ra `NA` trừ khi `na.rm = TRUE`; pandas bỏ `NaN` mặc định. Dịch máy móc có thể làm "đúng hơn"
  bản R, và hai báo cáo ra hai số.
- `n()` đếm dòng (`size`), `n_distinct()` là `nunique`.
- `group_by` + `mutate` giữ số dòng (giống `transform`), `group_by` + `summarise` thu về một dòng mỗi nhóm (giống `agg`).

Sau khi dịch, chạy cả hai trên cùng dữ liệu và so vài con số tổng; nếu không có R, so với số trong báo cáo cũ.

## Bạn dùng git với notebook thế nào?

- Cài **nbstripout** làm git filter: output và `execution_count` bị bỏ khi `git add`, diff chỉ còn code. Tránh repo phình
  vì ảnh base64 và tránh đẩy dữ liệu khách hàng trong output lên git.
- Review bằng **nbdime** (diff theo cell) hoặc ghép notebook với file `.py` bằng **jupytext** để review như code.
- Logic dùng lại (làm sạch, metric) đưa vào `src/*.py` có test; notebook chỉ gọi hàm và vẽ. Diff của file `.py` dễ đọc
  hơn notebook nhiều.
- CI chạy `nbstripout` rồi `git diff --exit-code` (báo lỗi nếu ai đó commit notebook còn output) và chạy lại notebook từ đầu (`jupyter nbconvert --execute`) để chắc nó tái lập.

## Một phân tích "tái lập được" cần những gì?

Người khác clone repo, tải dữ liệu theo README, chạy một lệnh, ra đúng con số trong báo cáo. Cụ thể:

- Dữ liệu gốc ở `data/raw`, chỉ đọc, ghi rõ nguồn và phiên bản (URL, ngày tải, commit); dữ liệu trung gian ở
  `data/processed`, sinh lại được bằng code.
- Đường dẫn tương đối từ gốc project; môi trường ghim (`uv.lock`); seed cố định nếu lấy mẫu.
- Quy tắc làm sạch và định nghĩa metric ở **một** chỗ (`src/`), có test.
- Notebook chạy "restart and run all" không lỗi, commit không output.
- README: câu hỏi, dữ liệu, cách chạy, kết quả chính và các giới hạn.

Đánh đổi: câu trả lời một lần trong 30 phút không cần cả bộ; báo cáo lặp lại hoặc con số vào quyết định lớn thì cần.

## Case: CEO hỏi "sao báo cáo tháng này ra doanh thu tháng 12 năm ngoái khác báo cáo tháng trước?". Bạn điều tra thế nào?

Một con số **lịch sử** đổi nghĩa là định nghĩa hoặc dữ liệu đầu vào đã đổi, không phải doanh nghiệp đổi.

1. Xem lịch sử git của notebook/SQL báo cáo giữa hai lần chạy: bộ lọc, nguồn, cách ghép có đổi không.
2. Chạy lại cả hai phiên bản trên cùng dữ liệu (nếu tái lập được) và so từng bước: số dòng sau làm sạch, sau ghép.
3. Kiểm nguồn: dữ liệu có bị nạp lại, sửa lùi (đơn huỷ muộn), thêm nguồn mới chồng thời gian không.

Ví dụ thật trên Online Retail II: một PR "thêm dữ liệu 2009-2010 để so YoY" ghép hai sheet mà không bỏ phần trùng
01–09/12/2010, làm doanh thu tháng 12/2010 từ 823 746 thành 1 262 599 GBP (+53%) và YoY tháng 12/2010 từ −0.2% thành
+52.9%. Trả lời CEO: con số nào đúng, vì sao đổi, đã sửa gì để không lặp lại (test reconcile tổng theo tháng với báo cáo
đã chốt).

## Case: bạn nhận một notebook 80 cell của người đã nghỉ việc, báo cáo tháng phải chạy lại tuần sau. Bạn làm gì?

Ưu tiên chạy được trước, đẹp sau:

1. **Chạy lại nguyên trạng** với dữ liệu tháng trước và so với báo cáo đã gửi. Ra đúng số thì có baseline để refactor
   an toàn; ra khác thì phải hiểu vì sao trước khi sửa gì.
2. Tìm phụ thuộc ẩn: đường dẫn tuyệt đối, file tay đặt trên máy, cell chạy không theo thứ tự, biến bị ghi đè.
3. Tách quy tắc làm sạch và metric thành hàm trong `src/`, viết test bằng chính con số đã đối chiếu ở bước 1.
4. Viết README: nguồn, cách chạy, định nghĩa metric. Thêm nbstripout.
5. Chỉ sau đó mới cải tiến (đổi định nghĩa, thêm chart), mỗi thay đổi một PR có ghi con số đổi bao nhiêu.

Không viết lại từ đầu trước hạn: rủi ro ra số khác báo cáo cũ mà không giải thích được.

## Case: marketing muốn "bảng tăng trưởng phát thải 10 năm của 10 nước lớn nhất" cho báo cáo ESG. Bạn làm và kiểm thế nào?

1. Làm rõ: phát thải nào (CO2 sản xuất hay theo tiêu dùng, có tính thay đổi sử dụng đất không), "lớn nhất" theo tổng
   hay đầu người, năm nào.
2. Dữ liệu OWID: bỏ dòng tổng (World, châu lục, nhóm thu nhập có `iso_code` rỗng). Cộng cả cột năm 2024 ra 245 672 Mt,
   gấp 6.4 lần World (38 599 Mt).
3. Tính bằng long → wide: `pivot` theo năm, tăng trưởng 10 năm và CAGR. Trong 10 nước lớn nhất năm 2024, Đức giảm
   27.8%, Indonesia tăng 63.1% (5.0%/năm).
4. Kiểm: tổng 218 nước gần bằng World (chênh chủ yếu là hàng không và hàng hải quốc tế), con số khớp chart trên trang
   OWID.
5. Ghi giới hạn: số liệu năm gần nhất có thể được sửa lùi; CO2 sản xuất không tính phát thải "nhập khẩu" qua hàng hoá.

## Hàm báo cáo dùng lại cần test gì?

Test các **định nghĩa**, không chỉ cú pháp:

- Làm sạch: đơn huỷ, số lượng âm, giá 0 bị loại; `Invoice` trộn số và chữ.
- Đếm đúng: số đơn là số hoá đơn khác nhau, số khách là `nunique`.
- Biên: kỳ không có dữ liệu, nhóm chỉ xuất hiện ở một kỳ (outer join), kỳ trước bằng 0 (tăng trưởng không xác định).
- Không sửa DataFrame đầu vào.
- Một test trên dữ liệu thật với con số đã đối chiếu (ví dụ tổng doanh thu quý).

Test tốt **phải fail** khi có lỗi: thử cố ý làm hỏng hàm (bỏ bộ lọc đơn huỷ, đổi `nunique` thành `count`) và chắc test
bắt được. Bài Intermediate 01 chấm đúng như vậy.

## Làm sao để một notebook không lộ dữ liệu cá nhân khi đưa lên git hoặc gửi cho người khác?

- Không commit `data/raw` (`.gitignore`), không commit output (nbstripout): bảng `head()` trong output là dữ liệu thật.
- Không in email, số điện thoại, mã khách trong cell; khi cần ví dụ thì dùng mã đã băm hoặc dữ liệu tổng hợp.
- Không đặt khoá API, mật khẩu trong notebook; dùng biến môi trường và file `.env` đã ignore.
- Lỡ commit: coi như đã lộ, báo người phụ trách và đổi khoá; xoá khỏi lịch sử git chỉ là bước phụ.
- Khi dùng LLM hỗ trợ viết code: chỉ gửi schema và vài dòng giả, không gửi dữ liệu khách hàng.
