# Lời giải: client World Bank API cho slide chọn thị trường

## Cách làm

- `get_json`: một vòng `for attempt in range(max_retries + 1)`. Ba nhánh: lỗi mạng (`httpx.TransportError`) và
  status trong `{429, 500, 502, 503, 504}` thì nghỉ rồi thử lại (`Retry-After` nếu có, không thì `2 ** attempt`), hết
  lượt thì `ApiError`; status `>= 400` khác thì `ApiError` ngay; status 2xx thì parse JSON và kiểm body: mảng có phần tử
  đầu chứa `message` là lỗi tham số của World Bank, báo `ApiError` kèm nội dung, không thử lại.
- `fetch_indicator`: path ghép mã nước bằng `;`, `date="start:end"`; lặp `page` từ 1 tới `meta["pages"]`, nối
  `data or []` (trang rỗng là `None`); cuối cùng `len(records) == int(meta["total"])`, lệch thì báo lỗi. Đối chiếu
  `total` bắt được lỗi phân trang (offset lệch, trang trùng) mà không cần biết nguyên nhân.
- `to_tidy`: list comprehension trên bản ghi có `countryiso3code` khác rỗng, ép kiểu rõ (`int` cho năm, `float` cho giá
  trị, `None` thành `NaN`), sắp và đánh lại index.
- `online_population`: lọc năm, `pivot_table(..., aggfunc="first", dropna=False)` để giữ cột toàn `NaN`, đổi tên, chèn
  `country`, tính cột mới, `sort_values(na_position="last")`. Không `fillna(0)`: "không có số liệu" khác "không có ai".
- `redact`: `urlsplit` → `parse_qsl(keep_blank_values=True)` → thay giá trị → `urlencode(safe="*")` → `urlunsplit`.
  Không dùng regex trên cả URL: dễ che nhầm path hoặc bỏ sót tham số viết hoa.

## Con số trên API thật (lastupdated 2026-10-08)

| Nước | Dân số 2023 (triệu) | % dùng internet 2015 → 2023 | GDP/người 2023 (USD) | Dân số online 2023 (triệu) |
| --- | --- | --- | --- | --- |
| Indonesia | 281.2 | 22.1 → 69.2 | 4 876 | 194.6 |
| Philippines | 114.9 | 36.9 → 77.9 | 3 804 | 89.5 |
| Việt Nam | 100.4 | 45.0 → 78.1 | 4 323 | 78.4 |
| Thái Lan | 71.7 | 39.3 → 89.5 | 7 211 | 64.2 |
| Malaysia | 35.1 | 71.1 → 97.7 | 11 386 | 34.3 |
| Campuchia | 17.4 | 6.4 → 68.9 | 2 430 | 12.0 |
| Singapore | 5.9 | 79.0 → 94.3 | 86 383 | 5.6 |
| Lào | 7.7 | 18.2 → 64.4 | 2 067 | 4.9 |
| Brunei | 0.5 | 71.2 → 99.0 | 32 891 | 0.5 |
| Myanmar | 54.1 | 10.9 → (thiếu 2021–2023) | 1 233 | không tính được |

Mỗi chỉ số 90 bản ghi (10 nước × 9 năm), 2 request với `per_page=50`. World Bank sửa số liệu theo đợt, nên số ở lần
chạy sau có thể lệch nhẹ; vì vậy notebook lưu `lastupdated` cạnh JSON thô.

Đọc cho slide: quy mô online lớn nhất là Indonesia, nhưng GDP/người của Indonesia, Philippines, Việt Nam gần nhau
(3 800–4 900 USD); Thái Lan và Malaysia nhỏ hơn về quy mô nhưng sức mua gấp 1.5–2.5 lần. "Dân số online" là chỉ số quy
mô, không phải chỉ số hấp dẫn: slide nên đặt nó cạnh sức mua, chi phí logistics, quy định TMĐT, đối thủ.

## Giải thích trắc nghiệm

- **requests-per-indicator (b)**: 90 bản ghi, 50 mỗi trang, `pages = 2`. Với `per_page=1000` chỉ cần 1 request; giảm
  `per_page` khi response quá lớn hoặc API giới hạn kích thước trang.
- **largest-online (c)**: 281.2 triệu × 69.2% ≈ 194.6 triệu.
- **vn-internet (a)**: 45.0% (2015) lên 78.1% (2023).
- **richest-not-largest (d)**: Singapore có GDP/người 86 383 USD, cao nhất, nhưng dân số online chỉ 5.6 triệu, thứ 7
  trên 9 nước có số liệu.
- **missing-value (b)**: `0` là một số khẳng định sai; trung bình nước khác là bịa; bỏ nước khỏi bảng che mất một
  thị trường 54 triệu dân. Để trống và ghi chú nguồn thiếu.
- **error-in-200 (c)**: lỗi tham số không tự hết khi gửi lại; trả body cho hàm gọi (b) làm lỗi xuất hiện ở chỗ khó
  hiểu (`ValueError: not enough values to unpack`); trả rỗng (d) làm bảng thiếu âm thầm.
- **redact-why (d)**: log, metadata, ticket được nhiều người và nhiều hệ thống đọc; key lộ ra phải thu hồi và cấp lại.
- **lastupdated (a)**: số liệu kinh tế vĩ mô được sửa (GDP ước tính lại, dân số điều chỉnh theo điều tra mới). Slide
  ghi "World Bank, cập nhật 2026-10-08" thì ai cũng kiểm lại được.
