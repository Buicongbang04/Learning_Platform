# Hướng làm: từ notebook rối tới project tái lập được

Bài Advanced không có một đáp án duy nhất. Dưới đây là các lỗi của notebook cũ (đã đo trên dữ liệu thật), một cách làm
project, các quyết định cần cân nhắc và rubric.

## Lỗi trong `Untitled_final_v3.ipynb`

| # | Lỗi | Ảnh hưởng trên Online Retail II, sheet 2010-2011 |
| --- | --- | --- |
| 1 | Đường dẫn tuyệt đối `/Users/lan/Downloads/online_retail_II (1).xlsx` | Không ai khác chạy được; không biết tệp đó là phiên bản nào |
| 2 | Gộp tháng bằng `.dt.month` | Tháng 12/2010 (748 269 GBP) và 12/2011 (592 622 GBP, mới tới ngày 9) cộng thành "tháng 12" 1 340 891 GBP của Anh, nên chart kết luận "Dec is best month!!"; tháng tốt nhất thật là 11/2011 (1 325 346 GBP) |
| 3 | Làm sạch thiếu: chỉ `Quantity > 0`, không lọc `Price <= 0` trước khi tính doanh thu | Hai dòng điều chỉnh nợ xấu (A563186, A563187, giá −11 062.06) trừ 22 124 GBP khỏi doanh thu Anh: 9 003 098 thay vì 9 025 222 GBP. (Bỏ hoá đơn `C` thì không đổi gì ở sheet này vì mọi dòng `C` có `Quantity < 0`, nhưng quy tắc phải viết rõ, không dựa vào trùng hợp) |
| 4 | Hai bộ lọc khác nhau cho hai con số trong cùng một bảng: `top` dùng `df` (chưa lọc giá), `orders` dùng `df2` (đã lọc giá) | AOV ghép tử số và mẫu số từ hai định nghĩa |
| 5 | `Invoice.count()` thay vì `nunique()` | Anh "485 123 đơn" thay vì 18 019 hoá đơn; AOV sai khoảng 27 lần |
| 6 | Cell chạy sai thứ tự: cell 7 dùng `orders_per_country` tạo ở cell 8 | "Restart and run all" báo `NameError`; kết quả cũ phụ thuộc vào trạng thái kernel không ai tái tạo được |
| 7 | Ghi đè `df` tại chỗ và gán cột trên lát cắt (`uk = df[...]` rồi `uk['month'] = ...`) | Kết quả phụ thuộc thứ tự và số lần chạy cell; pandas 2 cảnh báo `SettingWithCopyWarning`, pandas 3 (Copy-on-Write) không bao giờ sửa `df` gốc, ai quen cách cũ sẽ hiểu sai |
| 8 | Copy-paste cho từng nước (Anh, Đức) | Sửa lỗi ở một chỗ quên chỗ kia |
| 9 | Ghi `final_v3_FINAL.csv` vào thư mục hiện hành, có `%matplotlib inline` và output trong notebook | Kết quả lẫn với code, không biết sinh từ đâu; output có thể chứa dữ liệu khách hàng |

Con số tham chiếu cho project đúng: 302 dòng (tháng × quốc gia); Anh tháng 12/2010 748 268.98 GBP, 1 447 hoá đơn, 815
khách; tháng 11/2011 1 325 346.21 GBP, 2 490 hoá đơn, 1 505 khách.

## Một cách làm

- `clean.py`: đúng định nghĩa chung của track; `assign` để không sửa đầu vào.
- `metrics.py`: `month = InvoiceDate.dt.to_period("M").dt.to_timestamp()`, `groupby(["month", "Country"])` với `sum`,
  `nunique`, `nunique`; sắp `["month", "revenue"]` tăng/giảm; `reset_index(drop=True)`.
- `pipeline.py`: `read_excel(raw_path, sheet_name=sheet)` → clean → metric → `out_dir.mkdir(parents=True,
  exist_ok=True)` → `to_csv(index=False, date_format="%Y-%m-%d", float_format="%.2f")`. Có khối `if __name__ ==
  "__main__"` tính đường dẫn từ vị trí tệp (`Path(__file__).resolve().parents[2]`), không từ thư mục hiện hành.
- `tests/conftest.py` thêm `src` vào `sys.path`; ba test: làm sạch, tháng giữ năm, đếm đơn bằng `nunique`.
- `notebooks/01_country_monthly.ipynb`: import hàm, gọi `build` hoặc đọc `data/processed`, vẽ chart với tiêu đề đúng
  ("Tháng 11/2011 cao nhất; tháng 12/2011 mới có 9 ngày").
- `.gitignore`: `data/raw/*`, `data/processed/*` (giữ `.gitkeep` bằng `!`), `.ipynb_checkpoints/`, `__pycache__/`,
  `.env`; `.gitattributes` có `*.ipynb filter=nbstripout`.

## Quyết định cần cân nhắc

- **Có giữ con số cũ không?** Báo cáo cũ đã gửi đi với "tháng 12 tốt nhất". README phải nói rõ số nào đổi và vì sao,
  để Head of Sales không thấy hai con số mâu thuẫn mà không có giải thích.
- **Bao nhiêu cấu trúc là đủ?** Đây là báo cáo lặp lại hằng tháng, có người thứ hai đọc: đáng tách `src/` và test. Không
  cần đóng gói lên PyPI, Docker hay Airflow.
- **CSV hay Parquet trong `processed`?** CSV đọc được bằng mắt và Excel, đủ cho 302 dòng; Parquet khi bảng lớn và chỉ máy
  đọc. Quan trọng hơn là định dạng cố định để chạy lại ra tệp giống hệt.
- **Tháng 12/2011 chưa đủ**: giữ trong bảng nhưng đánh dấu trên chart; không ngoại suy.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Tìm lỗi | 25 | Ít nhất 5 lỗi trong bảng trên, có lỗi 2 (`.dt.month`), 3 hoặc 4 (bộ lọc), 5 (`count`), 6 (thứ tự cell); mỗi lỗi có con số trước/sau |
| Code trong `src` | 20 | Ba hàm đúng, không sửa đầu vào, một định nghĩa làm sạch dùng cho mọi nơi, không đường dẫn tuyệt đối |
| Tái lập | 20 | `build` idempotent, không ghi vào `data/raw`; README "Cách chạy" đủ để chạy từ máy mới (tải dữ liệu, cài môi trường, build, test); môi trường ghim (`uv.lock` hoặc phiên bản) |
| Test | 15 | Ít nhất 3 test trên dữ liệu nhỏ, mỗi test khoá một định nghĩa; ít nhất một test bắt được lỗi `.dt.month` |
| Git hygiene | 10 | `.gitignore` đúng, notebook không output, có nbstripout hoặc hướng dẫn tương đương |
| README cho người đọc | 10 | Câu hỏi, dữ liệu (nguồn, giấy phép, kỳ, định nghĩa), kết quả chính có con số, giới hạn (tháng 12/2011 chưa đủ) |

Từ 70 điểm trở lên là đạt; dưới 50 nghĩa là project vẫn chưa thay được notebook cũ.

## Sai lầm hay gặp

- Chỉ "dọn" notebook (đổi tên biến, xoá cell thừa) mà không sửa lỗi định nghĩa: code đẹp hơn, số vẫn sai.
- Sửa lỗi mà không ghi con số trước/sau: người nhận báo cáo thấy số đổi mà không biết vì sao.
- Viết lại quy tắc làm sạch trong notebook "cho tiện" bên cạnh `src`: hai định nghĩa lại trôi nhau.
- `build` ghi tệp vào cạnh tệp gốc hoặc ghi đè `data/raw`.
- Test chụp ảnh kết quả trên dữ liệu thật thay vì kiểm từng định nghĩa trên dữ liệu nhỏ.
