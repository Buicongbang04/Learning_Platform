# M06: Đóng gói model bằng MLflow, serve qua FastAPI

## Mục tiêu

Đưa model lúc giao vận chuyển của M03 ra khỏi notebook: huấn luyện tái lập được, theo dõi bằng MLflow,
đăng ký vào Model Registry, phục vụ theo hai đường (batch mỗi giờ cho CSKH và API FastAPI cho app nội
bộ) với **cùng một hàm feature**, và có monitoring drift tối thiểu. Kết quả là thứ một kỹ sư khác chạy
được và tin được.

Kiến thức nằm ở `modules/14-mlops-for-ds`: tracking với MLflow (README mục 2), đóng gói pipeline,
signature và registry (mục 3), batch hay online và FastAPI (mục 4), drift với PSI và KS (mục 5), checklist
từ notebook tới production (mục 7). Các bài tập của module 14 về tracking, serving, parity batch/online
và drift là bản thu nhỏ của milestone này.

## Việc cần làm

1. **Script huấn luyện** `project/serving/train.py`: đọc `data/raw`, dựng bảng bằng
   `olist_cx.tables`, feature bằng `olist_cx.features.features_at("carrier")`, fit một `Pipeline` (tiền
   xử lý + model) trên train, chọn ngưỡng trên validation, chấm trên test. Chạy lại hai lần cho cùng
   metric (cố định seed).
2. **MLflow tracking** (backend SQLite local trong `project/artifacts/`, xem lệnh gợi ý bên dưới): log tham số model,
   mốc chia thời gian, danh sách feature, thời điểm dự đoán `"carrier"`, metric validation và test
   (ROC-AUC, PR-AUC, Brier, precision tại ngưỡng), git commit, biểu đồ calibration, `MODEL_CARD.md`.
3. **Đăng ký model**: log model kèm `signature` và `input_example`, đăng ký tên
   `olist-bad-review-carrier`, gán alias `champion`. Service và batch đều nạp model qua
   `models:/olist-bad-review-carrier@champion`, không nạp file pickle trực tiếp.
4. **Service FastAPI** `project/serving/app.py`:
   - `POST /predict`: nhận một đơn với các trường có tới lúc giao vận chuyển, trả `score`, `flag` (theo
     ngưỡng đã chọn), `model_version`. Schema Pydantic với `extra="forbid"`: request có trường biết sau
     khi giao (ví dụ `order_delivered_customer_date`, `review_score`) phải bị từ chối với mã 422.
   - `GET /health`: trạng thái và phiên bản model đang phục vụ.
   - Fallback: model không nạp được thì trả kết quả của luật "còn dưới 5 ngày" và ghi rõ nguồn.
5. **Batch scoring** `project/serving/batch_score.py`: chấm mọi đơn vừa giao vận chuyển trong một khoảng
   thời gian, ghi `artifacts/scores/run_ts=.../scores.parquet`, idempotent (chạy lại cùng khoảng ghi đè,
   không nhân đôi), áp trần số cảnh báo mỗi tuần theo chính sách của M03.
6. **Parity**: test rằng batch và API cho cùng điểm trên cùng tập đơn (sai khác tuyệt đối tối đa dưới
   1e-9). Đây là cách bắt training-serving skew.
7. **Drift**: so phân phối điểm và các feature chính giữa train và từng tháng của test bằng PSI:

   $$
   \text{PSI} = \sum_{b=1}^{B} (a_b - e_b) \ln \frac{a_b}{e_b}
   $$

   với $$e_b$$, $$a_b$$ là tỉ lệ trong bin $$b$$ của tập tham chiếu và tập hiện tại (bin theo phân vị của
   tập tham chiếu). Log PSI vào MLflow và viết ngưỡng cảnh báo. Nhớ rằng nhãn review về chậm (M01 đo
   được độ chín), nên monitoring sớm dựa vào drift của input và điểm, không dựa vào metric trên nhãn.
8. **Test** trong `project/tests/`: `TestClient` cho `/predict` và `/health`, request leak bị 422, parity,
   idempotency của batch. Test không cần mạng; phần cần dữ liệu thật tự skip khi chưa tải.
9. **`project/serving/README.md`**: cách huấn luyện, mở MLflow UI, chạy service, gọi thử bằng `curl`, chạy
   batch, chạy test.

Lệnh gợi ý:

```bash
export PYTHONPATH=tracks/data-science/capstone/project/src   # để import olist_cx
uv run python tracks/data-science/capstone/project/serving/train.py
uv run mlflow ui --backend-store-uri sqlite:///tracks/data-science/capstone/project/artifacts/mlflow.db
uv run uvicorn serving.app:app --app-dir tracks/data-science/capstone/project --port 8000
uv run pytest tracks/data-science/capstone/project/tests -q
```

## Kết quả nộp

- `project/serving/train.py`, `app.py`, `batch_score.py`, `README.md`.
- Run MLflow có đủ tham số, metric, artifact; model `olist-bad-review-carrier@champion` trong registry.
- Test trong `project/tests/` xanh.
- Bảng PSI theo tháng trong `MODEL_CARD.md` (mục Monitoring).

## Tiêu chí đạt

- [ ] Huấn luyện lại cho cùng metric; metric test khớp M03 (sai khác do seed giải thích được).
- [ ] Service và batch nạp model qua registry alias, không qua đường dẫn file cứng.
- [ ] `/predict` từ chối request có trường biết sau lúc giao vận chuyển (422); `/health` trả phiên bản model.
- [ ] Batch và API cho cùng điểm (test parity xanh); batch chạy lại không tạo bản ghi trùng.
- [ ] Có fallback về luật khi model lỗi, và response nói rõ nguồn điểm.
- [ ] PSI được tính đúng (bin theo tập tham chiếu, xử lý bin rỗng) và có ngưỡng cảnh báo ghi rõ.
- [ ] Người khác làm theo `serving/README.md` chạy được mọi thứ trong 15 phút.
