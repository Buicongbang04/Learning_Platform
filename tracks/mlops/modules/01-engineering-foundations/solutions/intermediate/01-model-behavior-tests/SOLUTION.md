# Lời giải: test hành vi model

## Cách làm

Hai phép đo nhỏ, tách khỏi hai hàm `assert_*`:

- `column_order_shift`: dự đoán trên `X` và trên `X[X.columns[::-1]]`, lấy `max |Δ|`.
- `distance_effect`: sao chép `X`, nhân cột khoảng cách, tính `Δ = predict(mới) - predict(cũ)`, trả `(mean(Δ), mean(Δ < 0))`.

Hàm `assert_*` chỉ so các số đó với ngưỡng và đưa số vào thông báo lỗi.

## Vì sao

- Test hành vi bắt lỗi mà MAE không bắt: model theo vị trí cột có MAE tốt trên dữ liệu test (cột đúng thứ tự) và sai hoàn toàn khi service nhận JSON thứ tự khác.
- Model "học ngược" có thể có MAE chấp nhận được nếu tập dữ liệu bị nhiễm nhãn ở một vùng; test hướng bắt nó mà không cần nhãn thật.
- Nhận `predict` thay vì model: cùng test chạy trên scikit-learn, ONNX hay HTTP client của service đang chạy.
- Dùng trung bình và tỉ lệ ngược chiều vì dự đoán từng điểm của model cây có thể nhảy nhẹ; ràng buộc cứng thuộc về lúc train (`monotonic_cst`), test là lưới kiểm.

## Lỗi hay gặp

- Sửa `X` tại chỗ trong hàm đo: test sau đó chạy trên dữ liệu đã bị thay đổi.
- Đặt `tol=0` cho thứ tự cột khi model có tính ngẫu nhiên lúc dự đoán (dropout, sampling): đặt `tol` theo sai số số thực, không theo "bằng nhau".
- Chỉ nhân khoảng cách mà quên rằng các feature khác phụ thuộc vào nó (vd. tốc độ trung bình): với feature dẫn xuất, thay đổi phải áp dụng ở dữ liệu thô, trước `build_features`.
