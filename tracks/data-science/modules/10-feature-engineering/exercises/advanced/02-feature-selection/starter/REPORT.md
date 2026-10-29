# Báo cáo: chọn feature cho model review xấu

Người đọc: lead DS duyệt việc rút gọn feature trước khi đưa model vào production. Xoá mọi dòng TODO
khi viết xong. Mọi con số phải đến từ code bạn đã chạy (ghi rõ chạy ở đâu).

## 1. Mô phỏng: chọn feature ngoài CV sai bao nhiêu

TODO: kết quả của `leaky_selection_auc` và `honest_selection_auc` trên dữ liệu nhiễu và dữ liệu có
tín hiệu; giải thích cơ chế bằng lời cho người không làm ML.

## 2. Olist: feature nào thật sự đóng góp

TODO: với pipeline của bài Intermediate 02, permutation importance trên validation (và/hoặc độ ổn
định khi chọn theo các fold thời gian). Feature nào gần như không đóng góp?

## 3. Đề xuất bộ feature rút gọn

TODO: bộ feature đề xuất, AUC validation trước/sau, và điều gì mất/được (độ phức tạp, chi phí tính
feature lúc serving, độ ổn định, khả năng giải thích). Chỉ nhìn test một lần, ở cuối.

## 4. Rủi ro

TODO: tương quan giữa các feature làm permutation importance hiểu sai thế nào; feature yếu hôm nay
có thể quan trọng khi phân phối đổi (ví dụ mùa cao điểm giao trễ); cách theo dõi sau khi rút gọn.
