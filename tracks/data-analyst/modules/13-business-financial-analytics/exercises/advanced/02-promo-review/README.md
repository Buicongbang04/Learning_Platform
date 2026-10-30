---
title: Đánh giá chương trình khuyến mãi Rossmann và viết memo cho Commercial Director
level: advanced
services: []
files:
  - path: starter/promo_review.ipynb
    note: 2 hàm TODO + phân tích tự do
  - path: starter/MEMO.md
    note: Memo một trang - tác động, nơi mạnh / yếu, điều kiện có lãi, đề xuất, giới hạn
  - path: tests/test_promo_review.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/advanced/02-promo-review/starter/promo_review.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/advanced/02-promo-review -q
---

## Mục tiêu

Đánh giá một chương trình khuyến mãi như DA làm cho phòng thương mại: đo lift bằng so sánh công bằng, tách lượt khách
và giỏ hàng, tìm nơi khuyến mãi mạnh và yếu, nhìn dấu hiệu kéo cầu từ ngày khác, đổi lift ra điều kiện có lãi với
giả định ghi rõ, và đề xuất thử nghiệm cho phần dữ liệu quan sát không trả lời được.

## Đề bài

Commercial Director hỏi: **"Dashboard ghi ngày khuyến mãi bán nhiều hơn 39%. Khuyến mãi có đáng tiền không? Nên
giữ, mở rộng, hay cắt ở đâu? Giảm giá sâu tới đâu thì vẫn có lãi?"** Dữ liệu: bộ `store-sales` (Rossmann), `train.csv`
và `store.csv`. Không có giá, mức giảm giá hay giá vốn. Mở `starter/promo_review.ipynb`:

1. `promo_lift(train, by=None)`: lift doanh số, lượt khách, chi tiêu mỗi khách của ngày khuyến mãi so với ngày
   thường, chỉ trên ngày mở cửa có bán từ thứ Hai tới thứ Sáu, theo nhóm tuỳ chọn.
2. `breakeven_discount(lift, margin)`: mức giảm giá tối đa để lợi nhuận gộp ngày khuyến mãi không thấp hơn ngày thường.
3. Phân tích tự do trong các cell `explore`: con số dashboard và con số so sánh công bằng, lift theo loại cửa hàng /
   danh mục / thứ, cuối tuần của tuần khuyến mãi, so theo tuần, Promo2, mức giảm giá hoà vốn theo vài giả định
   margin. Chọn 1-3 chart cho memo.
4. Viết `starter/MEMO.md` theo khung có sẵn (200-600 từ, đủ các mục, dòng đầu là headline có con số).

## Tiêu chí đạt

- `promo_lift` đúng trên dữ liệu nhỏ: bỏ cuối tuần, ngày đóng cửa, ngày không bán; lift là tỉ số của trung bình;
  `spc_lift` suy từ hai lift; nhóm theo cột tuỳ chọn. `breakeven_discount` đúng công thức và đúng định nghĩa.
- Trên bộ thật: lift doanh số 38.79%, lượt khách 19.77%, chi tiêu mỗi khách 15.88% (376 875 ngày-cửa hàng có
  khuyến mãi, 319 818 không có); cửa hàng loại b thấp nhất (+20.0%); theo thứ: 57.1%, 44.8%, 36.8%, 32.1%, 22.1%;
  giảm giá hoà vốn khoảng 11.98% doanh số ngày khuyến mãi với margin 30%.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

So sánh công bằng nghĩa là hai nhóm chỉ khác nhau ở khuyến mãi: cùng thứ trong tuần, cùng điều kiện mở cửa. Kiểm
xem con số dashboard (mọi ngày mở cửa) khác con số công bằng bao nhiêu, và **vì sao** hai số gần nhau: đừng kết luận
là phép so sánh ngây thơ "đúng".

### Gợi ý 2

Lift trên ngày không phải tác động thật nếu khách mua trữ trong tuần khuyến mãi rồi mua ít đi tuần sau. Lịch xen kẽ
tuần làm mọi tuần thường đều ngay sau một tuần khuyến mãi: mốc so sánh có bị kéo xuống không? Dữ liệu này có đủ để
biết không? Nếu không, thiết kế thử nghiệm nào trả lời được (module 11)?
