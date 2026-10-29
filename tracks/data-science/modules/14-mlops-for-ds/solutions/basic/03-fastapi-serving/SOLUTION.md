# Lời giải: serve bằng FastAPI

## Cách làm

**Schema là hợp đồng.** Pydantic chặn dữ liệu sai ở cửa: giá âm, loại thanh toán chưa từng thấy,
batch rỗng đều bị trả 422 kèm thông báo chỉ rõ trường nào sai. Không có lớp này, model vẫn trả về
một con số cho `price = -10` hoặc `payment_type = "bitcoin"` (OneHotEncoder với
`handle_unknown="ignore"` coi nó là "không thuộc loại nào"), và lỗi upstream trở thành dự đoán sai
một cách im lặng. Ràng buộc nên phản ánh **miền giá trị hợp lệ của nghiệp vụ**, không phải khoảng
giá trị thấy trong tập train: giá 50 000 BRL hiếm nhưng hợp lệ, chặn nó là sai.

`payment_type` được giới hạn bằng `Literal`, trong khi `customer_state` chỉ kiểm độ dài. Đó là đánh
đổi: danh sách loại thanh toán ít khi đổi và giá trị lạ gần như chắc là lỗi; danh sách bang thì
ổn định nhưng nếu muốn chặt hơn có thể liệt kê đủ 27 bang.

**Một lần gọi model cho cả batch.** Gọi `predict_proba` từng dòng thì chi phí Python cố định mỗi
lần gọi (kiểm tra đầu vào của scikit-learn, ColumnTransformer) nhân lên theo số đơn. Trên pipeline
của module, chấm một dòng tốn khoảng 3 ms còn chấm 32 nghìn dòng trong một lần chỉ khoảng 20 ms.

**Đúng cột, đúng thứ tự.** `X[FEATURES]` bảo đảm tên và thứ tự cột như lúc train. ColumnTransformer
chọn cột theo tên nên thứ tự sai vẫn chạy được, nhưng model nhận mảng numpy (hoặc ONNX, bài
Advanced 01) thì thứ tự sai cho kết quả sai mà không báo lỗi.

**Model là tham số.** `create_app(model, ...)` tách việc nạp model khỏi việc phục vụ. Production
nạp model một lần lúc khởi động (từ MLflow registry, xem README module), test truyền model giả.
Không nạp model trong hàm xử lý request: mỗi request đọc lại tệp từ đĩa.

## Chạy thử như server thật

```bash
# trong một tệp run.py: app = create_app(joblib.load("model.joblib"), model_version="3")
uv run uvicorn run:app --port 8000
curl -X POST localhost:8000/predict -H 'content-type: application/json' -d @request.json
```

Đóng gói thành Docker image và đưa vào CI/CD là phần bạn đã làm ở track Data Engineer
(`tracks/data-engineer/modules/08-devops-for-data`).

## Sai lầm hay gặp

- Trả `numpy.float64` hoặc `numpy.bool_` trong response: FastAPI (qua Pydantic) có thể từ chối
  serialize hoặc trả kiểu lạ. Ép về `float`, `bool`.
- Bỏ `model_version` khỏi response: khi có sự cố sẽ không biết dự đoán nào đến từ model nào.
- Đặt ngưỡng cứng trong code: ngưỡng là quyết định kinh doanh (chi phí liên hệ khách so với lợi
  ích), thay đổi độc lập với model.
