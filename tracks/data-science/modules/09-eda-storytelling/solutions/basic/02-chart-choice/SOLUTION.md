# Lời giải: chọn biểu đồ và chuẩn bị dữ liệu cho bar chart

Code: `charts.py`.

## Vì sao các quy tắc như vậy

- **Line cho trend, trục không bắt buộc từ 0**: người đọc nhìn độ dốc, không nhìn độ dài. Cắt trục
  y để thấy biến động là hợp lệ với line (nhưng ghi rõ). Trên 5 chuỗi thì line chồng nhau thành "mì
  spaghetti": small multiples (mỗi chuỗi một ô nhỏ, chung trục) đọc được hơn.
- **Bar luôn từ 0**: độ dài bar là thông tin. Cắt trục làm 12% so với 13% trông như gấp đôi.
- **Sắp giảm dần với nhóm danh định, giữ thứ tự với nhóm có thứ tự**: bang, category không có thứ tự
  tự nhiên nên sắp theo giá trị để đọc thứ hạng; tháng, bucket số ngày giao, số sao mà sắp theo giá
  trị thì mất cấu trúc (bucket "30+" đứng đầu, "0–6" đứng giữa).
- **Bar ngang khi nhiều nhóm**: nhãn dài (tên category) đọc được mà không phải xoay chữ.
- **Strip khi ít điểm**: với dưới 30 quan sát, histogram/box che mất việc chỉ có vài điểm; vẽ từng
  điểm trung thực hơn.
- **Hexbin khi rất nhiều điểm**: scatter 95 nghìn điểm thành vệt mực, không thấy mật độ.
- **Không có pie**: mắt so góc và diện tích kém hơn so độ dài. Stacked bar 100% khi ít phần, bar sắp
  xếp khi nhiều phần.

Ngưỡng 5, 7, 30, 5000 là quy ước của bài để có thể kiểm thử; trong thực tế chúng là gợi ý, không
phải luật. Giá trị của việc viết chúng thành code là **nhất quán**: mọi báo cáo tự động trong team
theo cùng quy tắc, và quy tắc được review như code.

## Kết quả trên Olist thật

`category_share(products, "product_category_name", 5)`:

| Nhóm | count | share |
| --- | --- | --- |
| cama_mesa_banho | 3 029 | 9.2% |
| esporte_lazer | 2 867 | 8.7% |
| moveis_decoracao | 2 657 | 8.1% |
| beleza_saude | 2 444 | 7.4% |
| utilidades_domesticas | 2 335 | 7.1% |
| Khác | 19 619 | 59.5% |

Hai điều đáng chú ý khi vẽ: "Khác" lớn hơn mọi nhóm cộng lại, nên đặt nó ở cuối và tô màu nhạt để
không hút mắt; và nếu dùng `value_counts()` mặc định, 610 sản phẩm thiếu category **biến mất không
báo**, mẫu số của `share` thành 32 341 thay vì 32 951. Lỗi im lặng kiểu này phổ biến hơn lỗi làm
code dừng.

## Sai lầm hay gặp

- Gộp "Khác" rồi sắp lại toàn bảng theo giá trị: "Khác" nhảy lên đầu và trở thành bar nổi nhất.
- Chọn top N theo phần trăm đã làm tròn: thứ tự giữa các nhóm gần nhau có thể đổi.
- Hàm chọn biểu đồ trả về "pie" cho 2 phần: chấp nhận được về mặt nhận thức, nhưng một quy tắc
  nhất quán (stacked bar 100%) giúp người đọc so sánh giữa các báo cáo.
