# Lời giải: khái niệm drift

1. **three-kinds (c)**: $$P(X)$$ đổi, $$P(y \mid X)$$ giữ nguyên là covariate shift (data drift). Model vẫn đúng ở chỗ nó đã học, chỉ là gặp nhiều ca ở vùng khác. (a) sai vì concept drift là
   đổi $$P(y \mid X)$$; (b) nhầm với label drift ($$P(y)$$ đổi).
2. **drift-not-quality (b)**: drift là tín hiệu, không phải bằng chứng hỏng. Nếu nhãn đã về và MAE không đổi thì model vẫn đúng với phân phối mới. (a) và (d) là phản xạ; (c) vứt bỏ tín hiệu sớm.
   Vẫn nên theo dõi vì MAE có thể trễ.
3. **large-n (d)**: p-value co về 0 khi $$n$$ lớn dù độ lệch nhỏ. Cần thước đo độ lớn cộng tác động; tăng $$n$$ (a) làm vấn đề nặng hơn, hạ ngưỡng (b) chỉ dời vấn đề.
4. **multivariate (b)**: từng phân phối biên giống nhau nhưng quan hệ giữa các feature đổi (vd. tương quan đổi dấu). Classifier phân biệt hai tập bắt được cái mà PSI từng cột bỏ sót. AUC bằng 0.5 nghĩa là không phân biệt được.
5. **label-delay (a, b, c)**: phân phối dự đoán theo baseline cùng thứ, tỉ lệ fallback và MAE trên phần nhãn đã về đều dùng được; (d) so với hôm qua báo động giả theo chu kỳ tuần và độ lệch 3 sigma trên hai điểm vô nghĩa.
6. **seasonal-baseline (d)**: chu kỳ tuần. So cùng thứ trong nhiều tuần loại mùa vụ ra khỏi tín hiệu.
7. **first-step (b)**: verify trước. Rất nhiều "drift" là lỗi dữ liệu hay pipeline (đổi nguồn, thiếu giá trị, đổi lược đồ); kết luận gì về model trước khi loại trừ chúng là nhảy bước.
