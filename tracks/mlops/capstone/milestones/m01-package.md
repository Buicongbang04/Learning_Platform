# M01: Từ notebook baseline thành package `eta`

## Mục tiêu

Team DS đưa bạn `capstone/project/notebooks/baseline.ipynb`: đọc mẫu 200 000 chuyến tháng 1/2019, làm sạch bằng bốn
dòng lọc, chia train/test theo thời gian, so một baseline "trung vị theo cặp zone" (MAE khoảng 243 giây) với một model
gradient boosting thô (khoảng 159 giây). Notebook chạy được nhưng không ai vận hành được nó: tham số nằm cứng trong
code, không có hàm nào để test, chạy lại là cách kiểm duy nhất, và phần dựng feature sẽ bị viết lại (lệch) ở chỗ serving.

Milestone này biến notebook thành package Python `eta` trong `capstone/project/src/eta/`, có config tách khỏi code,
log có cấu trúc, CLI chạy được từ máy khác hay từ CI, và test. Mọi milestone sau (image, DVC, registry, serving) gọi lại
đúng các hàm bạn viết ở đây, nên tên hàm và hành vi dưới đây là **hợp đồng**: test chấm đúng những điều được ghi,
không có quy tắc chấm nào nằm ngoài tệp này. Đây là bài tích hợp sau
[module 01](../../modules/01-engineering-foundations/README.md) (cấu trúc `src/`, config, logging, test cho code ML).

Model chỉ cần "đủ tốt". Phần đáng điểm là: cùng dữ liệu và cùng config thì ra cùng số, luật làm sạch đếm được, và
một lệnh duy nhất tái hiện kết quả.

## Việc cần làm

Khung `src/eta/` đã có sẵn tên module, chữ ký hàm và `NotImplementedError`. Bạn điền phần thân, được thêm module và
hàm phụ tuỳ ý.

### 1. `eta.data`: đọc một tháng mà không tràn RAM

- `COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]`.
- `load_month(path: Path, sample_rows: int | None, seed: int) -> pd.DataFrame`:
  - Chỉ đọc 5 cột trong `COLUMNS` (tệp thật có 19 cột, 7,7 triệu dòng; đọc cả tệp vào pandas tốn vài GB). Đọc bằng
    `pyarrow.parquet.read_table(path, columns=COLUMNS)` rồi lấy mẫu trên bảng Arrow là cách gọn.
  - Trả DataFrame có **đúng** các cột `COLUMNS`, đúng thứ tự.
  - Lấy mẫu `sample_rows` dòng **xác định theo `seed`**: gọi hai lần cùng tham số thì `df.equals(...)` là `True`;
    đổi `seed` thì ra mẫu khác.
  - `sample_rows=None` hoặc `sample_rows` lớn hơn số dòng của tệp: trả mọi dòng.

### 2. `eta.features`: luật làm sạch cố định và feature dùng chung

`clean(df: pd.DataFrame, month: str) -> pd.DataFrame` (`month` dạng `YYYY-MM`) giữ một dòng khi thoả **tất cả**:

| Luật | Giữ khi | Bẩn thật gặp ở 2019-01 |
| --- | --- | --- |
| Thời lượng | `60 <= duration_s <= 10_800` (giây, `dropoff - pickup`) | âm, 0, vài giây; chuyến "kéo dài" nhiều ngày |
| Khoảng cách | `0 < trip_distance <= 100` (dặm) | 0, vài trăm dặm |
| Tháng | pickup thuộc tháng `month`: `>= YYYY-MM-01 00:00` và `<` ngày 1 tháng sau | chuyến năm 2008, 2018, tháng 2 |
| Zone | `PULocationID` và `DOLocationID` đều trong `1..263` | 264, 265 (Unknown) |

- Hai biên đều **được giữ**: 60 giây, 10 800 giây, 100 dặm, pickup đúng `2019-01-01 00:00:00`, pickup
  `2019-01-31 23:59` dù dropoff sang tháng 2.
- Kết quả có các cột `COLUMNS` và thêm cột `duration_s` (float, giây). Không sửa DataFrame đầu vào.
- Test có một fixture 12 dòng, mỗi luật loại 1–2 dòng, còn đúng 5 dòng sạch; trên mẫu thật 200 000 dòng của 2019-01,
  luật đúng giữ khoảng 96–97% (test chấp nhận 94–98%, vì cách lấy mẫu của bạn có thể khác bản tham chiếu).

Feature:

- `FEATURES = ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "trip_distance"]`; `pickup_hour` là giờ
  (0–23), `pickup_dow` là thứ trong tuần (thứ Hai = 0) của pickup.
- `build_features(df) -> tuple[pd.DataFrame, pd.Series]`: `X` có đúng các cột `FEATURES` theo thứ tự đó, `y` là
  `duration_s`, cùng số dòng với `df`.
- Viết phần dựng feature thành **một** hàm nhận các cột thô (pickup time, zone, khoảng cách) mà cả training lẫn serving
  (M02) cùng gọi. Viết lại logic ấy ở API là cách nhanh nhất để có training-serving skew.

### 3. `eta.train`: train và đánh giá tái lập được

- `train(X, y, params: dict) -> sklearn.pipeline.Pipeline`: `Pipeline` kết thúc bằng `HistGradientBoostingRegressor`,
  hai cột zone là **categorical** (không phải số: zone 132 không "lớn hơn" zone 48). `params` là tham số của
  `HistGradientBoostingRegressor` (ví dụ `max_iter`, `learning_rate`, `random_state`), ghi đè giá trị mặc định của bạn.
  - Bẫy: `HistGradientBoostingRegressor` chỉ nhận categorical có tối đa 255 giá trị, trong khi có 263 zone. Một cách là
    `OrdinalEncoder(max_categories=...)` gom zone hiếm, `handle_unknown="use_encoded_value"` cho zone chưa gặp.
  - Mặc định của bạn phải đủ tốt khi chỉ truyền `{"random_state": 0}` (xem mục 6).
- `evaluate(model, X, y) -> dict[str, float]` trả **đúng ba khoá**, giá trị kiểu `float`:
  - `mae`: sai số tuyệt đối trung bình (giây);
  - `p90_abs_err`: phân vị 90 của sai số tuyệt đối;
  - `mae_airport`: MAE trên các chuyến có zone đón **hoặc** trả là 132 (JFK) hoặc 138 (LaGuardia); `nan` nếu không
    có chuyến nào. Chuyến sân bay dài, đắt và hay bị phàn nàn; M04 dùng số này làm một tiêu chí riêng.
- Train hai lần cùng `X`, `y`, `params` thì `evaluate` ra **giống hệt** (so `==`, không làm tròn).
- Trên dữ liệu giả của test (6 000 chuyến, `max_iter=50`), MAE phải thấp hơn sai số của việc luôn đoán trung vị.
- Chia train/test **theo thời gian**: sắp theo pickup, 20% chuyến cuối làm test. Chia ngẫu nhiên cho số đẹp hơn thật.

### 4. `eta.config`: config tách khỏi code

- `Config` (dataclass) có các trường: `data_dir: Path`, `months: list[str]`, `sample_rows: int | None = 200_000`,
  `seed: int = 0`, `model_params: dict`, `mlflow_uri: str`, `model_name: str = "eta"` (khung đã khai báo sẵn).
- `load_config(path: Path) -> Config` đọc YAML có đúng các khoá trên:

```yaml
data_dir: ../../../../data/raw/nyc-tlc
months:
  - "2019-01"
sample_rows: 200000
seed: 0
model_params:
  max_iter: 200
  learning_rate: 0.1
mlflow_uri: http://127.0.0.1:25000
model_name: eta
```

- `data_dir` tương đối được tính từ **thư mục chứa tệp config**, không phải thư mục bạn đứng khi chạy lệnh.
- Biến môi trường ghi đè YAML: `ETA_DATA_DIR`, `ETA_MONTHS` (nhiều tháng cách nhau bằng dấu phẩy:
  `ETA_MONTHS=2019-02,2019-03`), `ETA_SAMPLE_ROWS`, `ETA_SEED`, `ETA_MODEL_PARAMS` (JSON), `ETA_MLFLOW_URI`,
  `ETA_MODEL_NAME`. Test kiểm `ETA_SAMPLE_ROWS`, `ETA_SEED` và `ETA_MONTHS`; container ở M02 dùng `ETA_DATA_DIR`.
- Viết tệp này thành `capstone/project/params.yaml`: M03 dùng chính tệp đó làm `params` của DVC.

### 5. `eta.cli` và logging

```text
python -m eta.cli train --config <yaml> [--model-out model.joblib] [--metrics-out metrics.json]
```

- Đọc config, với mỗi tháng gọi `load_month` (tệp `<data_dir>/yellow_tripdata_<YYYY-MM>.parquet`) rồi `clean`, chia
  theo thời gian, `build_features`, `train` với `{"random_state": seed, **model_params}`, `evaluate` trên phần test.
- **stdout chỉ có kết quả**: dòng cuối là một object JSON chứa ít nhất `mae`, `p90_abs_err`, `mae_airport`. Mọi log đi
  ra **stderr**, dạng JSON mỗi dòng một sự kiện (số dòng trước/sau `clean` mỗi tháng, thời gian train, metric). Nhờ
  vậy CI đọc stdout bằng `json.loads`, còn người trực grep được log.
- `--model-out` lưu Pipeline bằng `joblib.dump` (M02 nạp tệp này), `--metrics-out` ghi metric ra tệp.
- Exit 0 khi xong. Không ghi tệp nào ngoài những gì được yêu cầu, không gọi MLflow (đó là việc của M04).

Test chạy lệnh trên **trong sandbox**: chỉ thư mục tạm của test ghi được, môi trường dựng lại từ đầu với
`PYTHONPATH=<project>/src`, `mlflow_uri` trỏ vào một cổng không có gì.

### 6. Thắng baseline trên dữ liệu thật

Test lấy `load_month(<2019-01>, 200_000, 0)`, `clean`, chia 20% cuối theo thời gian, rồi train bằng
`train(X, y, {"random_state": 0})`, và đòi MAE thấp hơn baseline trung vị theo cặp zone tính trên cùng tập test
(khoảng 243 giây). Bản tham chiếu đạt khoảng 148 giây. Cần bộ `nyc-tlc`: `uv run python data/download_dataset.py nyc-tlc`.

### 7. Test và công cụ của chính bạn

- `pyproject.toml` cho package (tên, phiên bản Python, dependency trực tiếp có ghim) và một `Makefile` với vài đích
  `test`, `train`. Lưu ý: có `pyproject.toml` rồi thì `uv run` đứng trong `capstone/project/` coi đây là một project
  riêng và tạo venv mới; trong `Makefile` và khi gõ tay, dùng `uv run --project <gốc repo>` (từ `capstone/project/` là
  `../../../..`) để chạy bằng môi trường chung của repo. Đừng thêm `[tool.pytest.ini_options]` vào `pyproject.toml` này:
  pytest sẽ lấy nó làm cấu hình thay cho cấu hình ở gốc repo, và test chấm không import được `testkit`.
- Test của bạn cho từng luật `clean` (bạn tự nghĩ ca biên), cho `load_month` và cho `load_config`. Test chấm ở
  `capstone/project/tests` không thay được test của bạn: nó chỉ kiểm hợp đồng.

Chạy test chấm:

```bash
uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m01
```

## Kết quả nộp

- `capstone/project/src/eta/`: `data.py`, `features.py`, `train.py`, `config.py`, `cli.py` (và module phụ nếu có).
- `capstone/project/params.yaml`.
- `capstone/project/pyproject.toml`, `Makefile`, test của bạn.
- Một đoạn trong `capstone/project/README.md`: lệnh train, MAE của bạn trên 2019-01 so với baseline, và số dòng bị
  từng luật `clean` loại trên mẫu 200 000 dòng.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m01` pass, không skip.
- [ ] `load_month` chỉ đọc 5 cột và lấy mẫu xác định; `clean` theo đúng bảng luật, giữ biên.
- [ ] Dựng feature nằm trong một hàm dùng chung cho train và serving.
- [ ] Zone là categorical; train lại cùng config ra cùng metric.
- [ ] CLI in JSON metric ra stdout, log JSON ra stderr, exit 0.
- [ ] MAE trên 2019-01 thấp hơn baseline trung vị theo cặp zone.
- [ ] (Tự đánh giá) Có test của riêng bạn cho từng luật làm sạch và cho config; `make test` chạy được.
