# Lời giải tham chiếu: capstone dịch vụ ETA (M01–M07)

Bản tham chiếu cho phần chấm được bằng test, cùng cây thư mục với `capstone/project/`:

```bash
SOLUTION=1 uv run pytest tracks/mlops/capstone/project/tests -q -rs
```

Đây là **một** cách qua được hợp đồng trong đề, không phải cách duy nhất. Đọc sau khi đã tự làm; so phần quyết định
dưới đây với lựa chọn của bạn quan trọng hơn so từng dòng code.

## Số đo thật (2019-01, mẫu 200 000 dòng, `seed=0`, test là 20% cuối theo thời gian)

| | MAE (s) | p90 sai số (s) | MAE sân bay (s) |
| --- | --- | --- | --- |
| Baseline trung vị theo cặp zone (notebook) | 243.0 | | |
| Model thô của notebook (zone để dạng số) | 158.8 | 353.2 | 302.0 |
| Lời giải: zone categorical, `HistGradientBoostingRegressor(max_iter=200, max_leaf_nodes=63)` | 147.9 | 326.6 | 289.0 |
| Lời giải qua `dvc repro`, train trên 2019-01 + 2019-02 | 154.8 | 341.7 | 301.5 |

`clean` giữ 192 918 / 200 000 dòng (96,5%). Trên mẫu này: 1 956 dòng thời lượng < 60 s, 539 dòng > 3 giờ, 1 483 dòng
khoảng cách 0, 11 dòng pickup ngoài tháng, 4 713 dòng zone 264/265 (một dòng có thể dính nhiều luật). Model chỉ
"đủ tốt": thắng baseline khoảng 40%, train 3–4 giây. Phần còn lại của capstone là vận hành nó.

Lựa chọn loss: `absolute_error` nghe hợp với MAE nhưng đo ra tệ hơn (150.9 so với 147.9) và chậm hơn; giữ
`squared_error` mặc định. Số nào cũng phải đo, đừng chọn theo tên.

## M01: package `eta`

- **`load_month` đọc bằng `pyarrow` với `columns=`, lấy mẫu trên bảng Arrow** (`rng.choice` không lặp, sắp lại chỉ số
  để giữ thứ tự tệp), rồi mới `to_pandas()`. 5 cột × 7,7 triệu dòng khoảng 300 MB; đọc cả 19 cột rồi `sample` là vài GB.
- **`clean` một mặt nạ boolean, không lọc tuần tự.** Mỗi luật một dòng, đọc như bảng trong đề, và dễ đếm số dòng mỗi
  luật loại. Hằng số (`60`, `10_800`, `100`, `263`) đặt tên ở đầu module vì serving (`MIN_DURATION_S`) và validation
  cùng dùng.
- **`make_features` là hàm duy nhất dựng feature**, nhận cột thô; `build_features` (train) và `/predict` (serve) đều
  gọi nó. Không có bản thứ hai để lệch.
- **Zone qua `OrdinalEncoder(max_categories=250, handle_unknown="use_encoded_value", unknown_value=nan)`** rồi
  `categorical_features=[0, 1]`. HGB chỉ nhận ≤ 255 giá trị categorical; zone hiếm gom vào một mã, zone chưa gặp thành
  `nan` (HGB coi là missing, có nhánh riêng) thay vì lỗi lúc serving.
- **Tái lập:** `random_state` lấy từ `seed` của config; HGB bật early stopping khi > 10 000 dòng và chia validation
  ngẫu nhiên, nên thiếu `random_state` là metric đổi giữa hai lần chạy.
- **Config:** `data_dir` tương đối tính từ thư mục tệp config (lệnh chạy từ đâu cũng ra cùng đường dẫn); khoá lạ trong
  YAML là lỗi ngay, vì gõ sai `sample_row` mà bị bỏ qua thì bạn train cả tháng mà không biết. `ETA_*` ghi đè để
  container và CI đổi tham số mà không sửa tệp.
- **stdout là dữ liệu, stderr là log.** CLI in đúng một dòng JSON ra stdout; log JSON mỗi sự kiện ra stderr. CI đọc
  metric bằng `json.loads`, không cần grep log.

## M02: image và Compose

- **Hai image, multi-stage, venv chép sang stage cuối.** Không cần compiler (mọi thứ có wheel, `--only-binary=:all:`
  bảo đảm điều đó), nên multi-stage ở đây chủ yếu để stage cuối không có pip cache và tệp tạm. Kích thước Docker báo:
  serving khoảng 810 MB, training khoảng 1,04 GB (giải nén; `du -sxm /` trong container nhỏ hơn); `pyarrow` và
  `scipy` là hai phần lớn nhất.
- **`requirements-*.txt` ghim cả cây, sinh từ `uv.lock`** (`uv pip compile -c <uv export>`): image và máy bạn cùng
  scikit-learn 1.9.1, nên pickle của model nạp được. `mlflow-skinny` thay `mlflow` (không kéo server, UI, SQLAlchemy).
- **`ARG GIT_COMMIT` đặt sau bước cài dependency**: đổi commit chỉ làm lại layer cuối.
- **Import lười:** `pyarrow` chỉ import trong `load_month`, `pandera` chỉ trong lệnh `validate`, `mlflow` chỉ khi nạp từ
  registry. Image serving không có `pyarrow`; import ở đầu `data.py` làm API chết lúc khởi động.
- **Compose:** `read_only`, `tmpfs /tmp`, `cap_drop: ALL`, `no-new-privileges`, `mem_limit`, cổng chỉ `127.0.0.1`. Join
  network `mlops_default` của stack thay vì gọi MLflow qua cổng host (stack chỉ bind `127.0.0.1`, container không tới
  được).
- **Host header của MLflow:** MLflow 3 chặn Host header lạ (chống DNS rebinding). Stack chung khai
  `--allowed-hosts=mlflow,mlflow:*,localhost,...`, nên container gọi thẳng `http://mlflow:5000`. Nếu bạn dựng MLflow
  riêng mà quên cờ này, `/health` vẫn 200 nhưng mọi API registry trả 403 `Invalid Host header`: kiểm bằng một API thật,
  đừng chỉ bằng `/health`.
- **Model từ registry chạy được trong image:** MLflow 3.17 lưu sklearn bằng skops, nên image serving (và image training,
  vì `train --register` ghi model) phải có `skops`; thiếu nó thì API nạp `models:/eta@champion` chết lúc khởi động dù
  nạp tệp joblib vẫn chạy.

## M03: DVC và validation

- **`foreach: ${months}` cho `prepare` và `validate`**: thêm tháng là thêm một dòng trong `params.yaml`, mỗi tháng là một
  stage có hash riêng, tháng cũ không chạy lại.
- **`train` phụ thuộc thư mục báo cáo `reports/validation`**, không chỉ dữ liệu. Đó là cạnh duy nhất buộc thứ tự
  `validate → train`; thiếu nó, DVC không biết `train` phải chờ `validate`, có thể chạy `train` trước, và tháng hỏng vẫn vào model.
- **Dependency code đúng thứ stage import:** `cli.py` chỉ import `config`, `logs` ở đầu tệp, phần còn lại import trong
  từng lệnh. Nhờ vậy `prepare` chỉ phụ thuộc `cli`, `config`, `logs`, `data`; `validate` thêm `validate`, `features`
  (và `data` mà `features` import); `train` phụ thuộc `cli`, `config`, `logs`, `data`, `features`, `train`, `lineage`.
  Sửa `train.py` không đọc lại parquet; sửa `data.py` chạy lại cả ba (đúng, vì cách lấy mẫu đổi). Khai cả `src/eta`
  thì đúng nhưng chạy lại thừa; khai thiếu (lỗi hay gặp: quên `cli.py`, `config.py`) thì sửa CLI mà DVC
  báo "didn't change" và giữ kết quả cũ.
- **Params đúng chỗ:** `prepare` chỉ phụ thuộc `sample_rows`, `seed`; `train` phụ thuộc `model_params`, `months`, `seed`.
  Khai cả `params.yaml` làm dependency của mọi stage là lỗi hay gặp: sửa learning rate thì đọc lại 110 MB parquet.
- **Validation trên dữ liệu thô đã lấy mẫu, trước `clean`.** Sau `clean` thì mọi tháng đều "sạch" và validation không
  thấy gì. Ngưỡng 1% cho tỷ lệ thời lượng âm, khoảng cách âm, pickup ngoài tháng: mọi tháng 2019 đều dưới 0,1% (cao nhất
  là khoảng cách âm 0,09% ở 2019-11), nên 1% cách xa nhiễu bình thường hơn 10 lần mà vẫn chặn được sự cố kiểu 5%.
  Zone cho phép tới 265 vì 264/265 là mã hợp lệ của TLC (Unknown); `clean` loại chúng, validation không coi là hỏng.
- **Dữ liệu thô nằm ngoài repo DVC.** `data_dir` trong `params.yaml` tương đối với thư mục chứa tệp: ở
  `capstone/project/` là `../../../../data/raw/nyc-tlc` (bốn cấp lên gốc repo), ở bản tham chiếu
  `capstone/solutions/project/` là `../../../../../data/raw/nyc-tlc` (năm cấp). Chép `params.yaml` của lời giải sang
  `project/` thì phải bớt một `../`. DVC hash tệp ngoài repo như dependency ngoài, đủ để biết khi nào tệp đổi. Muốn
  người khác `dvc pull` được cả dữ liệu thô thì phải `dvc add` nó vào repo; capstone không làm vì dữ liệu đã có lệnh
  tải riêng.

## M04: registry và cổng

- **Luật cổng là hàm thuần `decide`**, tách khỏi MLflow: test được bằng bảng, không cần server, và M08 (CI) gọi lại.
  `promote_if_better` chỉ lo đọc metric, gọi `decide`, đặt alias, ghi tag `promotion` và lý do vào version.
- **Hai tiêu chí, ngưỡng khác nhau:** MAE tổng không được tệ hơn (0%), nhóm sân bay được tệ hơn tối đa 5% vì nhóm nhỏ
  (khoảng 6% số chuyến) nên nhiễu hơn. `p90_abs_err` chỉ log; thêm nó vào cổng là quyết định cần lý do.
- **Không promote lại chính champion** (trả `promote=False` với lý do), để lịch sử tag không bị ghi đè.
- **`skops_trusted_types`:** MLflow 3.17 lưu sklearn bằng skops và từ chối `HistGradientBoostingRegressor`; bản này liệt
  kê đúng ba kiểu mà thông báo lỗi nêu. Chuyển sang pickle cũng chạy, nhưng mất lớp kiểm tra khi nạp.
- **`MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false`:** đặt trong test, trong `serve.py` (mặc định) và `compose.yaml`;
  không có thì client xin URL presigned trỏ `minio:9000` và treo.
- **Champion thiếu số đo nào thì cổng đóng** (`mae` hay `mae_airport`, thiếu hay `nan`). Bản đầu bỏ qua tiêu chí sân bay
  khi champion thiếu `mae_airport`; nghĩa là một run log metric hỏng của champion âm thầm tắt một nửa cổng. Không so được
  thì không promote, và `reasons` nói đúng metric nào thiếu để người trực đánh giá lại champion.
- **API nạp theo số version đã phân giải** (`get_model_version_by_alias` rồi `models:/eta/<N>`): `/healthz` báo đúng
  version, không có khoảng trống giữa "đọc alias" và "tải model" mà alias đổi giữa chừng.

## M05: Prefect, đồng hồ mô phỏng, nhãn về muộn

- **Cổng nhãn là một hàm** (`labels.published`), và `labels_for` là đường **duy nhất** tới `duration_s` của tháng đã
  chấm. Replay không đọc nhãn bằng cách khác; vì vậy không có đường tắt nào rò nhãn chưa công bố. Tháng cuối của replay
  luôn `mae = None` với độ trễ 1 tháng: đúng thứ người trực thấy ngoài đời.
- **`request_id` sinh ở một chỗ** (`labels.month_trips`): `"<month>-<vị trí>"` sau `clean` trên mẫu xác định theo
  `seed`. Chấm và nhãn đi qua cùng hàm nên join một-một. Ngoài đời `request_id` do API sinh và đi cùng log; ở mô phỏng nó
  phải tái tạo được.
- **Khoá cache theo nội dung**: `cache_key_fn` băm `data_version` (sha256 tệp) cùng `months`, `sample_rows`, `seed`,
  `model_params`, `mlflow_uri`, `model_name`, `speed_table` và hash mã nguồn (`code_version()`: sha256 các tệp dựng dữ
  liệu, feature, model). Thiếu hash code thì sửa `clean` xong chạy lại vẫn nhận model cũ. Hash tham số mặc định của Prefect chỉ thấy đường dẫn config, không thấy
  tệp dữ liệu đổi. Đánh đổi: xoá version trong registry thì cache vẫn trả số cũ; xoá thư mục kết quả Prefect hoặc đổi
  khoá khi cần train lại có chủ đích.
- **Retry ở I/O, không ở train**: `fingerprint` và `score_month` có `retries=2` (đọc tệp, MinIO chập chờn); train lỗi
  thường là lỗi thật (dữ liệu, code), chạy lại y hệt không giúp gì.
- **Ghi parquet qua tệp tạm rồi `replace`**: flow chết giữa chừng không để lại tệp dở mà lần sau tưởng đã xong.
- **Replay không train trên tháng sắp chấm**: chưa có champion thì train trên `start - 1`. Champion cố định suốt M05;
  M10 mới quyết định retrain.

## M06: feature tốc độ zone/giờ và Feast

- **Trung vị, ngưỡng 5 chuyến**: tốc độ từng chuyến trên dữ liệu thật trải từ 3 tới 35 dặm/giờ (p1–p99) nhưng có chuyến
  100 dặm trong 2 phút; trung vị chịu được, trung bình thì không. Mẫu 200 000 dòng 2019-01 cho 1 690 nhóm `(zone, giờ)`
  có ≥ 5 chuyến; 98,6% chuyến 2019-03 có feature từ 2019-02, phần còn lại nhận mặc định.
- **`DEFAULT_SPEED_MPH = 10.1`**: trung vị toàn thành phố 2019-01 (10,14; 2019-02 là 9,86; 2019-07 là 10,15). Tháng
  2020-04 là **15,28**: tín hiệu COVID rõ nhất mà M10 sẽ dùng.
- **`event_timestamp` = đầu tháng sau, TTL 62 ngày ở cả hai phía** (`merge_asof(tolerance=...)` trên host và `ttl` của
  feature view). Lệch TTL giữa hai bên là skew dù code tính feature giống hệt.
- **Hai entity** vì Feast 0.67 từ chối entity nhiều join key (`An entity may only have a single join key`).
- **Feature tuỳ chọn theo dữ liệu**: `make_features` thêm `avg_speed_mph` khi cột có mặt; không có cờ config. Test
  M01–M04 không đổi. **Một đường gắn feature**: `zone_features.prepare(frame, model, table)` (model cần
  `avg_speed_mph` theo `feature_names_in_` thì `attach_speed`, thiếu bảng thì ném `MissingSpeedTable`) dùng chung cho
  `flows.score_month` (bảng từ `Config.speed_table`) và `serve.predict_one` (`ETA_SPEED_TABLE`, CSV vì image serving
  không có `pyarrow`). Bản đầu điền `DEFAULT_SPEED_MPH` cho mọi dòng khi thiếu bảng: model vẫn trả số, chỉ là số sai,
  và không ai biết. Feast online chỉ dùng trong container Feast ở capstone này; parity của nó với `attach_speed` là thứ
  test đo.

MAE thật (mẫu 200 000 dòng/tháng, `seed=0`, `HistGradientBoostingRegressor` mặc định của lời giải):

| Train | Đánh giá | Feature tốc độ | MAE (s) | p90 (s) | MAE sân bay (s) |
| --- | --- | --- | --- | --- | --- |
| 2019-01 | 2019-02 | không | 155.7 | 344.2 | 324.0 |
| 2019-01 | 2019-02 | có (train toàn mặc định vì không có 2018-12; đánh giá dùng 2019-01) | 155.7 | 344.2 | 324.0 |
| 2019-02 | 2019-03 | không | 160.1 | 351.9 | 325.6 |
| 2019-02 (feature 2019-01) | 2019-03 (feature 2019-02) | có | 162.7 | 356.2 | 326.0 |

Đọc bảng: hàng 2 cho đúng con số hàng 1 vì point-in-time làm đúng việc: chuyến tháng 1 không có tháng trước nên feature
là hằng số, model bỏ qua nó. Hàng 4: feature **không** giúp ở 2019 (tệ hơn 2,6 s), vì trung vị theo `(zone, giờ)` của
tháng trước gần như là thứ model đã học được từ zone và giờ. Giá trị của nó là khi đường phố đổi hẳn (2020-03, 2020-04):
lúc đó feature tháng trước mang thông tin mà model cũ không có. Bản tham chiếu giữ champion **không** có feature tốc độ ở
M06 và để M10 đo lại trên 2020. Lệnh đo: train/evaluate của M01 trên `attach_speed(clean(load_month(...)))`.

## M07: serving production

- **Readiness tách khỏi liveness**: `/healthz` luôn 200 (kubelet không giết pod đang nạp model), `/readyz` 503 tới khi
  warmup xong và 503 lại khi tắt (load balancer rút traffic trước khi tiến trình dừng). Nạp đồng bộ trong `lifespan`: đơn
  giản, và `up --wait` của Compose chờ đúng `/readyz`.
- **Bộ model bất biến** (`Models(champion, challenger)`, dataclass frozen): mỗi request lấy một tham chiếu lúc vào;
  reload tạo bộ mới, warmup, rồi gán một lần. Không request nào thấy champion mới với challenger cũ.
- **Định tuyến sha256, không `hash()`**: `hash()` của Python có salt theo tiến trình; hai replica sẽ định tuyến khác
  nhau cho cùng `request_id`.
- **Shadow trong `BackgroundTasks`**: chạy sau khi response đã gửi, nên shadow chậm không cộng vào độ trễ; mọi exception
  bị bắt và đếm. Canary lỗi thì chấm lại bằng champion trong cùng request (người dùng nhận ETA, `eta_fallback_total` cho
  người trực thấy).
- **Thiếu bảng feature thì không sẵn sàng**: lifespan bắt `MissingSpeedTable`, app sống (`/healthz` 200) nhưng `/readyz`
  503 kèm lý do; `/admin/reload` là đường phục hồi. Bảng feature nằm trong bộ `Models` bất biến cùng hai model.
- **Không có timeout cho canary**: canary lỗi thì fallback, canary chậm thì chậm thật; dừng canary theo p95/p99 tách theo
  `variant` (M09). Timeout trong endpoint đồng bộ cần thread pool riêng và vẫn không huỷ được predict đang chạy.
- **`ETA_ADMIN_TOKEN` bắt buộc khi API không chỉ bind localhost**: `/admin/reload` đổi model đang chạy.
- **Challenger warmup lỗi vẫn sẵn sàng**: readiness chỉ phụ thuộc champion; challenger hỏng hiện ra ở counter, không
  làm sập dịch vụ.
- **Reload lỗi giữ model cũ** và trả 5xx: rollback không bao giờ được làm mất model đang chạy tốt.
- **k6**: pha warmup 3 s rồi 40 req/s trong 15 s (`constant-arrival-rate`, khoảng 600 request), ngưỡng p95 < 200 ms,
  lỗi < 1%, thêm p99 < 500 ms cho pha ổn định và `checks > 99%`. Trong test chạy xong khoảng 25 s gồm cả build image
  (đã cache). `prometheus-client==0.26.0` thêm vào `requirements-serve` (cùng bản với `uv.lock`).

## Rubric phần tự đánh giá

| Mục | Đạt | Tốt |
| --- | --- | --- |
| README M01 | Lệnh train, MAE so với baseline | Thêm số dòng mỗi luật loại, giải thích vì sao chia theo thời gian |
| Test của người học | Có test cho `clean` và config | Ca biên từng luật, test tái lập, test không đọc dữ liệu thật |
| Image (M02) | Hai image chạy được, non-root | Đo cache khi sửa `src/`, có số trivy, giải thích phần nào chiếm dung lượng |
| Ngưỡng validation (M03) | Có ngưỡng, mọi tháng 2019 qua | Lý do bằng số đo thật, nói rõ đánh đổi chặt/lỏng |
| Remote DVC | `dvc push` thành công | Xoá cache, `dvc pull` lại đúng, khoá ở `config.local` |
| Registry (M04) | Có ≥2 version, một lần promote | Runbook rollback có thời gian đo, model card nêu giới hạn đã biết |
| Replay (M05) | Bảng 5 tháng, tháng cuối không có MAE | Giải thích vì sao không retrain mù theo lịch, có deployment Prefect có lịch |
| Feature (M06) | Bảng MAE có/không có feature | Quyết định giữ/bỏ có lý do bằng số, nêu khi nào không cần feature store |
| Serving (M07) | Số k6, runbook rollback | Quy trình canary có tiêu chí dừng bằng số, đo p99 có và không có warmup |
