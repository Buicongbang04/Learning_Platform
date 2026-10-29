# Lời giải: phân tích thí nghiệm Cookie Cats

Notebook lời giải: `analysis.ipynb` (chạy được toàn bộ khi đã tải dữ liệu).

## Hiểu dữ liệu

- 90 189 dòng, mỗi `userid` một dòng: đơn vị random là người chơi, khớp đơn vị phân tích.
- `sum_gamerounds` lệch phải cực mạnh (median 16, max 49 854). Người chơi 49 854 ván trong 14 ngày
  (khoảng 2 ván mỗi phút, 24/24) gần như chắc là bot hoặc lỗi log. Metric retention dạng 0/1 không
  bị ảnh hưởng nhiều, nhưng phân tích trên số ván phải loại hoặc winsorize.
- Cỡ nhóm 44 700 / 45 489: p SRM ≈ 0.0086 (bài Basic 03).

## Bootstrap nhanh cho metric 0/1

Bootstrap resample n phần tử có hoàn lại từ một mảng 0/1 có tỉ lệ p̂; số phần tử bằng 1 trong mẫu
mới có phân phối đúng `Binomial(n, p̂)`. Vì vậy `rng.binomial(n, p̂, n_boot) / n` **chính là**
bootstrap, không phải xấp xỉ. Với metric liên tục thì vẫn phải resample chỉ số; trên dữ liệu lớn
dùng Poisson bootstrap hoặc tính song song.

Lời giải giữ đường dự phòng resample chỉ số cho metric không phải 0/1, để `bootstrap_diff_ci` dùng
được cả với `sum_gamerounds`.

## Kết quả

| Metric | gate_30 | gate_40 | Chênh lệch | CI 95% |
| --- | --- | --- | --- | --- |
| retention_1 | 44.82% | 44.23% | −0.59 điểm % | khoảng [−1.24, +0.06] |
| retention_7 | 19.02% | 18.20% | −0.82 điểm % | khoảng [−1.33, −0.31] |

Quyết định theo quy tắc: `keep_gate_30`.

## Rubric cho phần khuyến nghị

| Tiêu chí | Đạt khi |
| --- | --- |
| Kết luận rõ | Nói thẳng nên làm gì ở câu đầu |
| Độ lớn và độ chắc chắn | Có chênh lệch và CI, bằng ngôn ngữ người đọc hiểu được |
| Cơ chế | Đưa ra giả thuyết vì sao, không chỉ con số |
| Giới hạn | Nhắc SRM, doanh thu in-app không được đo, retention dài hạn |
| Không quá lời | Không nói "chứng minh", không ngoại suy cho mọi game |

## Sai lầm hay gặp

- Kiểm định trên `retention_1` rồi kết luận "không có tác động", trong khi metric gần giá trị dài
  hạn hơn là `retention_7`. Chọn OEC trước khi nhìn dữ liệu.
- Dùng t-test trên `sum_gamerounds` mà không xử lý outlier.
- Bỏ qua SRM vì "p-value của metric rất nhỏ rồi".
