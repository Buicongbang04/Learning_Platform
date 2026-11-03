# M05: Flow Prefect, batch inference và đồng hồ phát lại theo tháng

## Mục tiêu

Sau M04, train và promote là các lệnh bạn gõ tay. Production không chờ ai gõ: dữ liệu tháng mới về theo lịch, model
chấm cả tháng theo lịch, và **nhãn thật về muộn**. TLC công bố thời gian chuyến của tháng `M` sau khoảng một tháng, nên
ở đầu tháng `M+1` bạn đã có dự đoán của cả tháng `M` nhưng chưa biết chúng đúng hay sai.

Milestone này dựng ba flow Prefect 3 và một **đồng hồ mô phỏng** để phát lại 2019 → 2020 như dữ liệu production:

- `train_flow`: train và đăng ký model, **không train lại** khi dữ liệu và tham số không đổi (cache).
- `batch_score_flow`: chấm cả một tháng bằng champion, ghi log dự đoán cùng định dạng với API (M07).
- `replay_flow`: đẩy đồng hồ qua từng tháng, chấm, rồi tính MAE thật **chỉ cho những tháng đã có nhãn** tại thời
  điểm mô phỏng. Tháng chưa có nhãn thì MAE là `None`, không phải một con số tính từ dữ liệu lẽ ra chưa tồn tại.

Rò nhãn về muộn là lỗi khó thấy nhất của bài này: replay "nhìn trước" nhãn cho ra dashboard đẹp và một quyết định retrain
sai ở M10. Đây là bài tích hợp sau [module 05](../../modules/05-training-pipelines/README.md).

```mermaid
sequenceDiagram
    participant C as Đồng hồ (as_of)
    participant S as batch_score_flow
    participant L as Nhãn (trễ 1 tháng)
    participant Q as Chất lượng
    C->>S: tháng 2019-02: chấm bằng champion
    C->>S: tháng 2019-03: chấm
    L-->>Q: nhãn 2019-02 công bố khi as_of >= 2019-03
    C->>S: tháng 2019-04: chấm
    L-->>Q: nhãn 2019-03 công bố khi as_of >= 2019-04
    Note over Q: as_of = 2019-04: MAE 2019-02, 2019-03 có số; 2019-04 là None
```

## Việc cần làm

Prefect 3.9 đã có trong môi trường `uv` của repo. Không cần server: chạy flow như hàm Python là đủ (Prefect tự mở API tạm
khi cần); test dùng `prefect_test_harness` và `PREFECT_HOME` trong thư mục tạm, không để lại tiến trình nào.

### 1. `eta.clock`: tháng là chuỗi `YYYY-MM`

```python
add_months(month: str, n: int) -> str          # add_months("2019-12", 1) == "2020-01"; n có thể âm hoặc 0
months_between(start: str, end: str) -> list[str]   # gồm cả hai đầu; start > end → ValueError
```

`months_between("2019-11", "2020-02") == ["2019-11", "2019-12", "2020-01", "2020-02"]`. Chuỗi `YYYY-MM` so sánh được
bằng `<`, `>=` như thời gian, nên phần còn lại của bài dùng chuỗi, không cần `datetime`.

### 2. `eta.labels`: nhãn về muộn

```python
LABEL_DELAY_MONTHS = 1
published(month: str, as_of: str, delay: int = LABEL_DELAY_MONTHS) -> bool   # as_of >= add_months(month, delay)
labels_for(month: str, as_of: str, config: Config) -> pd.DataFrame | None
```

- `published("2020-03", "2020-03") is False`, `published("2020-03", "2020-04") is True`, với `delay=2` thì phải tới
  `2020-05`. Trả đúng kiểu `bool`.
- Kiểm cả `month` và `as_of` bằng cùng bộ kiểm của `eta.clock` trước khi so: chuỗi sai dạng (`"2020-3"`, `"2020-13"`,
  `"April"`, `""`) → `ValueError`. So chuỗi chỉ đúng khi cả hai đều đúng dạng `YYYY-MM`; `"2020-3" >= "2020-04"` là
  `True` và sẽ âm thầm "công bố" nhãn.
- `labels_for` trả **`None`** khi `published(month, as_of)` là sai, **kể cả khi tệp dữ liệu có sẵn trên đĩa** (trong
  mô phỏng mọi tệp đều có sẵn; chính hàm này là cổng chặn).
- Đã công bố: DataFrame đúng hai cột `request_id`, `duration_s`, mỗi chuyến sạch của tháng một dòng (`load_month` với
  `config.sample_rows`, `config.seed`, rồi `clean` của M01), `request_id` không trùng.

**`request_id` phải khớp giữa chấm và nhãn.** Cả `batch_score_flow` và `labels_for` lấy chuyến của tháng qua **cùng
một hàm** (ví dụ `month_trips(month, config)`), gắn `request_id` theo cùng quy tắc (bản tham chiếu dùng
`"<month>-<vị trí 7 chữ số>"` sau `clean`; mẫu xác định theo `seed` nên vị trí ổn định). Hai hàm tự lấy mẫu riêng là
join hụt.

### 3. `eta.logs.PREDICTION_LOG_COLUMNS`

```python
PREDICTION_LOG_COLUMNS = ["request_id", "ts", "model_version", "variant", "PULocationID", "DOLocationID",
                          "pickup_datetime", "trip_distance", "eta_s"]
```

Một định dạng cho mọi dự đoán: batch (parquet, ở đây) và API (JSON lines, M07). M09 đếm, M10 join nhãn trên đúng các cột
này. `ts` là lúc chấm (chuỗi ISO, UTC), `pickup_datetime` chuỗi ISO giờ địa phương, `variant` của batch là `"batch"`.

### 4. `eta.flows`

```python
train_flow(config_path: str, months: list[str]) -> str
batch_score_flow(month: str, config_path: str, out_dir: str) -> str
replay_flow(start: str, end: str, config_path: str, out_dir: str) -> list[dict]
```

Ba hàm là `@flow` của Prefect; việc nặng đặt trong `@task`.

**`train_flow`**: đọc config, thay `months` bằng tham số, train trên chuyến sạch của các tháng đó (chia theo thời gian như
M01), `log_and_register` (M04) vào `config.mlflow_uri` / `config.model_name`, trả số version. **Không** tự promote.

- **Cache**: task train có `cache_key_fn` tính từ `data_version` (hash nội dung các tệp tháng, hàm `data_version` của M04)
  cộng các tham số quyết định model: `months`, `sample_rows`, `seed`, `model_params`, `mlflow_uri`, `model_name`,
  `speed_table` (M06), cộng **hash mã nguồn train** (nội dung các tệp `eta` dựng dữ liệu, feature và model, ví dụ
  `data.py`, `features.py`, `train.py`, `labels.py`, `zone_features.py`, `registry.py`, `flows.py`). Gọi lại
  `train_flow` cùng config, cùng tháng → trả lại **đúng version cũ** và **không** tạo run MLflow mới. Đổi tháng (tức
  `data_version` đổi) → train lại. Kết quả task phải lưu được (`persist_result=True`).
- Vì sao không để Prefect hash tham số mặc định: tham số là đường dẫn config, không đổi khi nội dung tệp dữ liệu đổi.
  Cache phải theo **nội dung**, không theo tên tệp.
- Vì sao có hash mã nguồn: sửa luật `clean` hay cách dựng feature mà dữ liệu và tham số giữ nguyên thì khoá không đổi,
  cache trả model cũ train bằng code cũ. Hash code làm khoá đổi theo.
- **Cache phải được đối chiếu với registry.** Khoá cache không biết registry: xoá model (hay cả tệp SQLite của MLflow)
  thì cache vẫn trả số version cũ, trỏ vào thứ không còn tồn tại. Sau khi task train trả version, `train_flow` kiểm tra
  bằng `MlflowClient.get_model_version(model_name, version)` rằng version đó còn và tag `data_version` khớp; không còn
  (`MlflowException`) hoặc lệch thì ghi sự kiện `stale_cache` và chạy lại task với
  `train_and_register.with_options(refresh_cache=True)`. Test `test_m05_train_flow_cache_after_registry_reset` xoá
  registered model giữa hai lần gọi và đòi version trả về phải có trong registry.
- `mlflow_uri` dạng `sqlite:///` đường dẫn tương đối được `load_config` tính từ thư mục tệp config (như `data_dir`), để
  cache và registry không phụ thuộc thư mục đang đứng khi chạy.
- Ghi cách xoá cache (xoá thư mục `PREFECT_LOCAL_STORAGE_PATH`, hoặc đổi khoá: đổi tham số, đổi code) vào README.

**`batch_score_flow`**: nạp version đang giữ alias `champion` của `config.model_name` (chưa có champion → báo lỗi rõ ràng),
chấm **mọi chuyến sạch** của `month` (cùng `sample_rows`, `seed` của config), ghi `<out_dir>/predictions_<month>.parquet`
với **đúng** `PREDICTION_LOG_COLUMNS` theo đúng thứ tự, `model_version` là version champion, `variant == "batch"`,
`eta_s > 0` (kẹp tối thiểu 60 s như API). Trả đường dẫn tệp. Ghi ra tệp tạm rồi đổi tên, để lần chạy lỗi giữa chừng không
để lại parquet dở dang.

**`replay_flow`**: đồng hồ chạy `now` qua `months_between(start, end)`:

1. Chưa có champion → `train_flow` trên tháng **trước** `start` (`add_months(start, -1)`) rồi đặt alias `champion`. Không
   bao giờ train trên tháng sắp chấm.
2. Mỗi `now`: chấm tháng `now` bằng champion hiện tại (như `batch_score_flow`).
3. Cuối cùng, nhìn từ `as_of = end`: tháng nào `published(month, end)` thì join log dự đoán với `labels_for` theo
   `request_id`, MAE = trung bình `|duration_s - eta_s|`; tháng chưa công bố thì `mae = None`.

Trả list, mỗi tháng một dict: `{"month", "model_version", "n_scored", "mae", "as_of"}` theo thứ tự tháng, `as_of == end`,
`mae` là `float` hoặc `None`. Ghi thêm `replay.json` cạnh các tệp parquet để M10 đọc lại. Ở M05 champion cố định suốt
replay; quyết định retrain/rollback là việc của M10.

**Dữ liệu 2019 và 2020 ở hai thư mục** (`data/raw/nyc-tlc`, `data/raw/nyc-tlc-2020`). Để replay qua năm, tạo một thư
mục chứa symlink tới cả hai rồi đặt `data_dir` vào đó, ví dụ:

```bash
mkdir -p data/replay && ln -sf "$PWD"/../../../../data/raw/nyc-tlc*/yellow_tripdata_20*.parquet data/replay/
```

### 5. Test chấm làm gì

- `test_m05_months_between`: các ví dụ ở mục 1, kể cả qua năm, `n` âm, và `ValueError` khi `start > end`.
- `test_m05_labels_not_before_publication`: các ca `published` ở mục 2 (kể cả `ValueError` khi sai dạng); `labels_for` trả `None` trước công bố dù tệp có
  sẵn; sau công bố trả đúng hai cột, đủ số chuyến sạch, `request_id` không trùng, `duration_s >= 60`.
- `test_m05_train_flow_cached` (`prefect_test_harness`, MLflow SQLite trong thư mục tạm): gọi `train_flow` hai lần cùng
  tham số → cùng version, đúng **1** run trong experiment `model_name`; gọi với tháng khác → run thứ 2.
- `test_m05_train_flow_cache_after_registry_reset`: `train_flow` một lần, `delete_registered_model`, gọi lại cùng tham
  số → version trả về phải có trong registry (cache cũ bị phát hiện và train lại).
- `test_m05_batch_score_columns`: đặt champion, chấm 2019-02, kiểm tên tệp, đúng cột và thứ tự, số dòng bằng số chuyến
  sạch, `request_id` không trùng, `model_version`, `variant == "batch"`, `eta_s > 0`.
- `test_m05_replay_mae_late`: 4 tháng giả 2019-01..04, `replay_flow("2019-02", "2019-04", ...)`: ba dict đúng thứ tự,
  `as_of == "2019-04"`, có parquet mỗi tháng, tháng cuối `mae is None`, hai tháng trước có `mae` bằng đúng MAE test tự
  tính từ parquet join `labels_for(month, "2019-04")` (join một-một, đủ dòng).

Test dùng tệp giả 1 500 chuyến/tháng và `max_iter: 20`; cả milestone chạy dưới một phút.

```bash
uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m05
```

## Kết quả nộp

- `capstone/project/src/eta/clock.py`, `labels.py`, `flows.py`, `PREDICTION_LOG_COLUMNS` trong `logs.py`.
- Một lần replay thật `2019-02 → 2019-06` (mẫu 200 000 dòng/tháng) và bảng `replay.json` trong README: tháng, version,
  số chuyến, MAE, `as_of`.
- Mục "Orchestration" trong README: cách chạy ba flow, khoá cache gồm những gì, cách xoá cache, và một deployment Prefect
  có lịch (ví dụ `train_flow.serve(cron="0 3 1 * *")`) kèm giải thích vì sao **không** retrain mù theo lịch.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m05` pass, không skip.
- [ ] Không có đường nào tính MAE từ nhãn chưa công bố tại `as_of`.
- [ ] Chạy lại cùng dữ liệu, cùng tham số không train lại; đổi dữ liệu thì train lại; registry mất version thì train lại.
- [ ] Log batch và log API (M07) cùng một tập cột, join được với nhãn theo `request_id`.
- [ ] (Tự đánh giá) Replay thật 5 tháng có bảng kết quả và nhận xét MAE theo tháng.
- [ ] (Tự đánh giá) Có retry cho bước đọc dữ liệu và ghi tệp, giải thích vì sao bước train không cần retry.
