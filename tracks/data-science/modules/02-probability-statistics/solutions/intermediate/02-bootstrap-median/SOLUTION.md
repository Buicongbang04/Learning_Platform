# Lời giải: bootstrap CI cho median thời gian giao

Notebook lời giải: `bootstrap.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Bootstrap theo lô

Một ma trận `n_boot × n` cho 96 470 đơn là 193 triệu số (khoảng 1.5 GB float64). Chia lô khoảng 5
triệu phần tử (51 mẫu bootstrap mỗi lô với toàn bộ dữ liệu) giữ bộ nhớ dưới 50 MB mà vẫn vector hoá.
Dùng một `rng` cho mọi lô: tạo lại `rng` với cùng seed trong mỗi lô sẽ cho các lô **giống hệt nhau**,
phân phối bootstrap co lại thành 51 giá trị lặp lại, CI sai mà không báo lỗi.

## Kết quả trên Olist thật

Toàn bộ đơn: median 10.22 ngày, bootstrap [10.18, 10.27], chính xác [10.18, 10.27].

| Bang | n | median | CI bootstrap | CI chính xác |
| --- | --- | --- | --- | --- |
| AM | 145 | 25.88 | [24.27, 27.52] | [24.21, 27.52] |
| RR | 41 | 25.01 | [18.04, 30.11] | [17.04, 30.19] |
| AP | 67 | 24.35 | [22.16, 27.46] | [22.16, 27.46] |
| RJ | 12 350 | 12.04 | [11.94, 12.15] | [11.94, 12.16] |
| SP | 40 494 | 7.21 | [7.18, 7.25] | [7.18, 7.25] |

Đọc bảng: thứ tự AM > RR > AP là nhiễu (CI chồng nhau); khác biệt giữa nhóm bang miền Bắc và SP (hơn
ba lần) là thật. Dashboard nên hiện CI hoặc ít nhất là n bên cạnh median, và ẩn / gộp bang dưới một
ngưỡng số đơn.

## Hai loại CI

| | Bootstrap percentile | Chính xác (order statistic) |
| --- | --- | --- |
| Giả định | Mẫu đại diện tổng thể; thống kê "trơn" | Quan sát độc lập, phân phối liên tục |
| Nhiễu Monte Carlo | Có (đổi seed, CI đổi chút) | Không |
| Dùng cho | Mọi thống kê: percentile, trimmed mean, tỉ số | Chỉ median (và percentile, cùng ý tưởng) |
| Mẫu rất nhỏ | Kém: phân phối bootstrap của median rời rạc, độ phủ dưới danh nghĩa | Đúng theo thiết kế (bảo thủ) |

## Bootstrap hỏng khi nào

- **Thống kê cực trị** (max, min): độ phủ 0 trong mô phỏng. Mẫu bootstrap không thể vượt max mẫu gốc.
- **Percentile đuôi với mẫu nhỏ** (p99 trên 200 quan sát): chỉ vài quan sát quyết định thống kê.
- **Dữ liệu phụ thuộc** (chuỗi thời gian, nhiều đơn cùng khách): resample từng dòng phá cấu trúc phụ
  thuộc, CI quá hẹp. Dùng block bootstrap hoặc resample theo cụm (theo khách).
- **Mẫu lệch** (sampling bias): bootstrap đo nhiễu lấy mẫu, không sửa được bias (bài Advanced 02).

## Rubric cho phần nhận xét

| Tiêu chí | Đạt khi |
| --- | --- |
| Không quá lời | Không xếp hạng các bang có CI chồng nhau như thể thứ tự là chắc chắn |
| So sánh phương pháp | Nêu được khác biệt giả định / nhiễu Monte Carlo giữa hai loại CI |
| Giới hạn bootstrap | Giải thích đúng vì sao max thất bại |
| Hành động | Đề xuất cách hiện median trên dashboard (CI, n tối thiểu) |
