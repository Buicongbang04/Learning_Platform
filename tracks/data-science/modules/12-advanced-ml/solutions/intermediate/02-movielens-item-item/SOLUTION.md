# Lời giải: item-item CF trên MovieLens

Notebook lời giải: `itemcf.ipynb` (chạy được toàn bộ khi đã tải `movielens`).

## Cách làm

- **Split**: sort theo `userId, timestamp, movieId`, `cumcount(ascending=False)` cho thứ tự từ cuối;
  dòng nào có thứ tự từ cuối nhỏ hơn $$\lceil 0.2 n_u \rceil$$ vào test.
- **Popularity**: đếm rating mỗi phim trong train, sort `(n giảm, movieId tăng)`. Với mỗi user chỉ
  cần duyệt `k + |đã xem|` phim đầu là chắc chắn đủ k phim chưa xem.
- **Item-item**: không tạo ma trận độ giống $$S = \tilde X^\top \tilde X$$ (8 230 × 8 230 phim có
  trong train, khoảng 540 MB ở float64). Vì

  $$
  \text{score}(u, \cdot) = S\, h_u = \tilde X^\top (\tilde X h_u)
  $$

  nên mỗi user chỉ cần hai phép nhân ma trận thưa với vector. Toàn bộ 610 user chạy khoảng một giây trên laptop.
  Ở quy mô lớn, hệ thống thật vẫn tính trước **top-N hàng xóm** của mỗi item (offline, bằng Spark
  hoặc ANN) rồi lưu vào key-value store để serving nhanh.

## Kết quả trên dữ liệu thật

| | precision@10 | recall@10 | coverage (số phim khác nhau) |
| --- | --- | --- | --- |
| Popularity | 0.0748 | 0.0389 | 98 |
| Item-item | 0.0970 | 0.0554 | 473 |
| Popularity, chỉ tính phim ≥ 4 sao | 0.0581 | 0.0498 | 98 |
| Item-item, chỉ tính phim ≥ 4 sao | 0.0588 | 0.0608 | 473 |

Ví dụ user 1 (185 rating trong train, lịch sử gần nhất có *Apocalypse Now*, *American History X*):
item-item gợi ý *The Terminator*, *Groundhog Day*, *Mars Attacks!*, *Back to the Future Part II*,
*Die Hard* và trúng 5/10; popularity trúng 4/10.

## Đọc kết quả

- Popularity là baseline **mạnh**: 7.5% gợi ý trúng mà không cần biết gì về user. Một hệ thống mới
  không thắng được popularity thì chưa nên ra production.
- Item-item thắng về precision (+30% tương đối) và đa dạng hơn rất nhiều (coverage gấp 4.8 lần).
  Coverage thấp nghĩa là "người giàu càng giàu": phim phổ biến được gợi ý nhiều, được xem nhiều,
  lại càng phổ biến (feedback loop).
- Với relevance "chấm ≥ 4 sao", hai cách gần ngang nhau: ma trận nhị phân dự đoán **xem gì**,
  không dự đoán **thích gì**. Chọn metric theo mục tiêu sản phẩm.
- Offline precision chỉ là proxy. Một phim không nằm trong test không có nghĩa user không thích nó
  (user chưa biết tới phim đó). Quyết định cuối cùng vẫn cần A/B test (module 03).

## Rubric cho phần nhận xét

| Tiêu chí | Đạt khi |
| --- | --- |
| So sánh đủ ba chiều | Nêu cả precision/recall và coverage, không chỉ một con số |
| Đọc kết quả ≥ 4 sao | Nhận ra khác biệt giữa "xem" và "thích" |
| Cold start | Có chiến lược riêng cho user mới (popularity theo ngữ cảnh, onboarding) |
| Giới hạn offline | Nhắc tới việc cần A/B test hoặc bias của dữ liệu quan sát |

## Lỗi hay gặp

- Chia ngẫu nhiên theo dòng thay vì theo thời gian: model được "xem trước tương lai", precision
  cao giả tạo.
- Quên loại phim đã xem: precision vẫn đúng (phim đã xem không nằm trong test) nhưng danh sách lãng
  phí chỗ.
- Tạo ma trận độ giống dày cho toàn bộ catalog: hết RAM khi số item lên vài trăm nghìn.
- Lấy trung bình precision chỉ trên user có gợi ý: item-item không gợi ý được cho user lạ, nên con
  số bị thổi phồng nếu bỏ họ ra.
