# Lời giải tham chiếu: capstone dịch vụ ETA (M01–M13)

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
  tệp dữ liệu đổi. Khoá không biết registry, nên `train_flow` đối chiếu: cache trả version mà registry không còn (hay
  tag `data_version` lệch) thì log `stale_cache` và train lại với `refresh_cache=True`; xoá `data/replay-mlflow.db` rồi
  `make replay` lại vẫn đúng. Muốn train lại có chủ đích thì xoá thư mục kết quả Prefect hoặc đổi khoá.
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

## M08: CI, CT, CD bằng act

- **Ba workflow, chỉ `run:`**: `ci.yml` (lint → test → build `dist/eta.pyz`), `ct.yml` (validate → train → gate →
  announce), `cd.yml` (verify → deploy). Không `uses:` nên act chạy được ngoại tuyến với `mlops-act-runner:1`.
- **Dependency trong runner**: runner chỉ có Python và uv. Test cài một lần các gói (cùng phiên bản `uv.lock`) vào
  `~/.cache/mlops-ex/eta-ci-<hash>`, mount chỉ đọc vào container cùng đường dẫn (`container_options="-v ..."` của
  `act_run`), và repo tạm có symlink `.ci-deps` trỏ tới đó. Workflow chỉ cần `PYTHONPATH: .ci-deps:src` và một bước
  `test -d .ci-deps || pip install --target .ci-deps -r requirements-ci.txt` cho GitHub thật. Không chép 300 MB vào mỗi
  repo tạm (`/tmp` là tmpfs).
- **Ruff 0.17 bật rất nhiều luật mặc định** (BLE, UP, PLW...): project khai báo `[tool.ruff.lint] select = ["E", "F",
  "W", "I", "B"]`, `line-length = 160`. Không có cấu hình thì bản tham chiếu có khoảng 10 lỗi lint chỉ vì luật mặc định.
- **Version qua output của job**, không qua tệp: act `--bind` dùng chung thư mục nên tệp cũng "chạy", nhưng trên GitHub
  thật mỗi job một máy (chính là sự cố "deploy nhầm model" của module 08). Input/output đi vào lệnh qua `env:`.
- **Cổng = `eta.cli promote` của M04**, exit 3 khi từ chối; act báo `exitcode '3': failure` và job `announce`
  (`needs: [train, gate]`) không chạy. CD không đọc output của CT: `verify` hỏi registry (`eta.cli champion --expect`),
  nên chỉ version đang mang alias `champion` mới deploy được, dù ai bấm nút.
- **Path filter**: act bỏ qua `paths`, test dùng `cikit.triggers` của module 08. `ct` chỉ theo `params.yaml`, `dvc.lock`,
  `src/eta/train.py`; đổi `features.py` không train lại tự động (đánh đổi: thay đổi feature thường đi kèm đổi
  `train.py` hoặc `params.yaml`; nếu không, chạy tay `workflow_dispatch`).
- Thời gian thật trên máy tham chiếu (bốn act run): CI test hỏng rồi xanh 12 s; CT có champion không thể thắng 28 s; CT
  registry trống 35 s; CD sai/đúng version 19 s. Cả M08 khoảng 100 s.

## M09: metric, alert, dashboard

- **Đếm ở middleware**: 422 do FastAPI trả trước endpoint nên chỉ middleware thấy; endpoint ghi `request.state.variant`
  (`scope["state"]` dùng chung). Exception chưa bắt được đếm `status="500"` trong `finally`.
- **`eta_model_info` là Gauge = 1 với `version`, `variant`**, `clear()` khi install, reload và tắt (registry dùng chung trong
  tiến trình, nhiều app trong test).
- **Không traffic**: `sum(rate(5xx)) / sum(rate(all))` là 0/0 = NaN, so sánh `> 0.05` với NaN là false nên không bắn.
  Không "sửa" bằng `or vector(0)` ở mẫu số: đó mới là chỗ sinh alert giả hoặc che lỗi.
- **`absent(eta_model_info{job="eta-api"})`**, không `absent(eta_requests_total)`: counter có label chưa có series cho tới
  request đầu tiên, service vừa khởi động sẽ bị báo mất metric.
- **`EtaPredictionShift`**: `abs(median_now / median_offset_7d - 1) > 0.3`, cửa sổ 1 giờ, `for: 1h`. Test promtool dùng
  `interval: 30m`: với `interval: 1h` cửa sổ `[1h]` chỉ chứa một mẫu (range selector của Prometheus 3 mở bên trái) nên
  `rate` rỗng.
- Dashboard 7 panel, provisioning trong `monitoring/grafana/provisioning/`, profile `monitoring` của `compose.yaml` project
  (Prometheus 29190, Grafana 23100, đã kiểm `ss -ltn`).

## M10: phát lại 2019-07..2020-06 trên dữ liệu thật

Cấu hình (giống test và `params.replay.yaml`): champion train trên 2019-06 (80% đầu theo thời gian), mẫu 50 000 chuyến
mỗi tháng, `seed=0`, `max_iter=100`; tham chiếu drift là dự đoán trên 2019-06; `as_of = 2020-06`. Chạy khoảng 30 s.

| Tháng | PSI `trip_distance` | PSI giờ đón | PSI `eta_s` | MAE (s) | p90 sai số (s) | MAE sân bay (s) | bias (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019-07 | 0.0006 | 0.0018 | 0.0016 | 194.2 | 430.5 | 405.5 | +41.5 |
| 2019-08 | 0.0015 | 0.0012 | 0.0042 | 192.6 | 420.8 | 405.1 | +72.6 |
| 2019-09 | 0.0006 | 0.0019 | 0.0003 | 201.5 | 452.9 | 441.2 | -9.8 |
| 2019-10 | 0.0010 | 0.0045 | 0.0002 | 195.7 | 449.6 | 421.5 | -8.9 |
| 2019-11 | 0.0019 | 0.0012 | 0.0010 | 196.4 | 449.1 | 437.5 | -4.9 |
| 2019-12 | 0.0023 | 0.0022 | 0.0019 | 212.3 | 497.3 | 460.5 | -21.8 |
| 2020-01 | 0.0041 | 0.0055 | 0.0009 | 199.1 | 443.1 | 526.7 | +102.7 |
| 2020-02 | 0.0062 | 0.0044 | 0.0026 | 181.1 | 403.1 | 470.7 | +65.1 |
| 2020-03 | 0.0047 | 0.0147 | 0.0023 | 207.0 | 462.1 | 517.9 | +103.9 |
| 2020-04 | 0.0161 | 0.1772 | 0.0157 | 371.8 | 806.8 | 905.2 | +340.6 |
| 2020-05 | 0.0448 | 0.1071 | 0.0483 | 362.2 | 786.2 | 844.7 | +321.2 |
| 2020-06 | 0.0184 | 0.1113 | 0.0321 | chưa có nhãn | | | |

Điều số liệu nói:

- **PSI `trip_distance` không bao giờ vượt 0.1**, kể cả tháng 4/2020 (0.016). Drift thật nằm ở **giờ đón** (0.177 ở
  2020-04) và ở **quan hệ khoảng cách → thời gian** (concept drift): MAE gần gấp đôi, bias từ khoảng 0 lên +341 s (model
  đoán dài hơn thực tế gần 6 phút vì đường vắng). Giám sát chỉ PSI feature sẽ bỏ lỡ sự cố.
- Mùa lễ 2019-12: MAE +8.1% so với 2019-11, PSI rất nhỏ, tháng 1 trở lại 199 s.

Thí nghiệm hỗ trợ quyết định (cùng mẫu và tham số, `eta.experiments`; mỗi thí nghiệm từ chối chạy nếu nhãn của tháng
dùng tới chưa công bố tại `--as-of`). Tái lập sau `make replay`:

```bash
make experiments
python -m eta.cli experiment late-slice --config params.replay.yaml --month 2020-03 --as-of 2020-04
python -m eta.cli experiment retrain --config params.replay.yaml --train-month 2019-11 --month 2019-12 --as-of 2020-01
python -m eta.cli experiment retrain --config params.replay.yaml --train-month 2020-03 --month 2020-04,2020-05 --as-of 2020-06
```

| Thí nghiệm | Champion (2019-06) | Model so sánh |
| --- | --- | --- |
| 2020-03 `late-slice`: train trên 80% đầu tháng 3, đánh giá trên 20% cuối (9 741 chuyến từ 2020-03-12; as_of 2020-04) | 283.6 s | 240.8 s (-15%) |
| 2019-12 `retrain`: train trên 2019-11, đánh giá trên 2019-12 (as_of 2020-01) | 212.3 s | 208.1 s (-2%) |
| Kiểm chứng sau sự việc `retrain`: train trên cả 2020-03, đánh giá trên 2020-04 / 2020-05 (as_of 2020-06) | 371.8 / 362.2 s | 270.5 / 258.1 s |

Quyết định tham chiếu (`project/reports/decisions/`). Cả hai dùng cùng một mốc so sánh: dải MAE cả tháng của nửa sau 2019
là 192.6 tới 212.3 s.

- **2019-12: `keep`** (as_of 2020-01). MAE 212.3 s (+8.1% so với tháng 11) nằm trong dải, PSI nhỏ, 2020-01 quay lại
  199 s; train lại chỉ được 2%: không đáng rủi ro của một lần promote.
- **2020-03: `retrain`** (as_of 2020-04). Số **cả tháng không đủ kết luận**: 207.0 s vẫn trong dải trên, và bias +104 s
  không mới (2020-01 đã +103 s); nửa đầu tháng còn giao thông bình thường nên làm loãng tác động. Bằng chứng quyết định là
  **lát cuối tháng** từ 2020-03-12 (NYC ban bố khẩn cấp 12/3, đóng trường 16/3, lệnh PAUSE 22/3): champion 283.6 s, cao hơn
  34% so với đỉnh 212 s của dải, trong khi challenger train trên đầu tháng 3 đạt 240.8 s (-15%). Rollback vô nghĩa (mọi
  version đều trước COVID). Kiểm chứng sau sự việc: bản train lại giảm MAE tháng 4 từ 372 xuống 270 s.
- Người chỉ nhìn số cả tháng và chọn `keep` cho 2020-03 vẫn qua test (tỉ lệ 1.14 nằm giữa hai luật), nhưng mất điểm
  rubric nếu không xét lát cuối tháng; đó là chỗ phân biệt mức Đạt và Tốt.
- Không chọn được `keep` cho 2020-04 dù quyết định muộn: MAE +79.6% vượt luật 50% của test.

Rubric cho quyết định và tài liệu (test chỉ kiểm cấu trúc, số và hai luật nhất quán):

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Lý do 2020-03 | Nêu MAE trước/sau và PSI, kết luận khớp số | So số cả tháng với cùng dải mốc dùng cho tháng khác; thấy số cả tháng bị loãng và dùng lát cuối tháng; thí nghiệm tái lập được (`eta.cli experiment`) chỉ với nhãn đã có tại `as_of`; tách concept drift khỏi drift đầu vào; nói vì sao không rollback |
| Tháng thứ hai | Quyết định có số, khớp luật | Chọn tháng drift/mùa vụ và chứng minh `keep` bằng thí nghiệm train lại không đáng |
| `as_of` | Sau khi nhãn công bố | Giải thích chi phí của việc chờ nhãn và tín hiệu proxy dùng được trước đó (PSI giờ đón, `EtaPredictionShift`, bias) |
| Runbook | Mỗi alert đủ bốn phần | Lệnh kiểm tra chạy được, nhánh hành động theo kết quả kiểm, tiêu chí leo thang bằng số/thời gian |
| Postmortem | Đủ năm phần, có số | Không đổ lỗi, dòng thời gian theo `as_of`, việc cần làm đo được (feature giao thông gần đây, alert bias, CT theo chất lượng) |

## M11: cloud tuỳ chọn, dọn theo tag

Bản tham chiếu chọn AWS (`project/cloud/`): bucket S3 cho model, Lambda 128 MB trả `/healthz` (đọc `head_object`, không nạp
model nên không cần sklearn trong Lambda), log group 3 ngày, budget 1 USD có cảnh báo `ACTUAL > 50%` và `FORECASTED > 100%`.
Không test nào chạm cloud; bản này chưa được `apply` trong lúc viết (không có tài khoản trong môi trường dựng bài), nên
`main.tf` chỉ được kiểm bằng test tĩnh. Lần chạy thật đầu tiên nên `terraform validate` và `terraform plan` trước.

- **Tag ở từng resource, không dùng `default_tags`.** Cả hai đều qua test; viết tường minh để người đọc thấy ngay tài
  nguyên nào mang tag, và để test chỉ ra đúng resource quên tag. Tài nguyên con (`public_access_block`, `role_policy`,
  `function_url`, `lambda_permission`) không nhận tag và bị xoá theo cha.
- **Dọn theo tag, không theo tiền tố tên.** Tên `eta-mlops-...` có thể do người khác hay chính bạn tạo tay (bucket thử
  nghiệm có dữ liệu); tag do IaC gắn nên là bằng chứng "Terraform của bài này tạo ra nó". So sánh đúng từng ký tự:
  `Project` hay `eta-mlops-staging` không khớp. Inventory giả của test có đủ năm bẫy đó.
- **IAM role dưới path `/eta-mlops/`.** API Resource Groups Tagging không luôn trả IAM role, nên `teardown.sh` liệt kê thêm
  bằng `aws iam list-roles --path-prefix /eta-mlops/` rồi lấy tag của từng role; role vẫn chỉ bị chọn khi có tag đúng.
- **`--dry-run` không gọi CLI khi đã có inventory, kể cả lệnh đọc.** "Dry-run" mà vẫn gọi cloud thì không chạy được ở CI,
  và một lỗi đảo nhánh `if` là xoá thật; test thay `aws` bằng script ghi log để chứng minh không có lời gọi nào.
- **Không cờ thì từ chối.** Lệnh xoá cần `--yes`; gặp loại tài nguyên chưa biết thì dừng trước khi xoá bất cứ gì, để
  không bao giờ dọn dở dang. Thứ tự: Lambda, log group, bucket (`rb --force`), role (gỡ policy trước), budget cuối.
- **Một lệnh xoá lỗi không dừng cả lượt.** Không dùng `set -e` cho vòng xoá: dừng ở bucket lỗi thì role và budget còn đó;
  chạy hết, in `FAILED: <type> <id>` ra stderr, exit 1 (cùng bài học với bài kế hoạch dọn của module 12).
- **Đọc output `aws` bằng Python, theo vùng.** Mỗi lệnh đọc gọi với `--output json` và `json.loads` cả output (JSON của
  CLI nhiều dòng, không ghép tay thành JSON Lines được). `get-resources` là thao tác có paginator trong botocore nên CLI
  tự gộp mọi trang; tự truyền `--pagination-token` lại tắt việc đó, nên script không tự phân trang.
  Tagging API theo vùng: `--region` (mặc định `us-east-1` như `var.region`, đổi bằng `--region` hay `ETA_AWS_REGION`),
  không dựa vào vùng mặc định của CLI, nếu không dry-run in 0 dòng trong khi Lambda vẫn chạy ở vùng khác. IAM role và
  budget là toàn cục nên liệt kê riêng: `iam list-roles --path-prefix` + `list-role-tags`, và `sts get-caller-identity`
  → `budgets describe-budgets --account-id` + `budgets list-tags-for-resource`. Lệnh xoá Lambda và log group lấy vùng
  từ ARN của chính tài nguyên (inventory có thể trộn vùng), `--region` chỉ là dự phòng. Đường này kiểm bằng `aws` giả
  trong `tests/test_mlops_capstone_cloud.py` ở gốc repo.
- **Không tin chuỗi trong inventory.** Trước khi xoá, mỗi tài nguyên được kiểm: `name` không bắt đầu bằng `-` (sẽ bị
  CLI đọc thành cờ) và chỉ gồm ký tự an toàn, vùng trong ARN dạng `us-east-1`, account của budget đủ 12 chữ số; sai thì
  `WARN: bỏ qua` và `--yes` exit khác 0 vì tài nguyên vẫn còn. Danh sách policy của role đọc bằng `read -a`, không để
  shell glob.
- **Lambda URL `NONE`** cho tiện thử, kèm hai `aws_lambda_permission` công khai (`InvokeFunctionUrl` và `InvokeFunction`, AWS đòi cả hai từ cuối 2025). Quyền `InvokeFunction` cho `"*"` **phải** có `invoked_via_function_url = true` (điều kiện `lambda:InvokedViaFunctionUrl`, provider AWS từ 6.28): thiếu nó thì bất kỳ tài khoản AWS nào cũng gọi thẳng `Invoke` được, không qua URL. `budget.md` ghi rủi ro và cách chuyển sang
  `AWS_IAM`.

Rubric M11 (tuỳ chọn, không tính vào mức junior):

| Mục | Đạt | Tốt |
| --- | --- | --- |
| IaC | Mọi resource có tag, không khoá trong repo | `plan` sạch, giải thích từng tài nguyên con không nhận tag bị xoá theo đâu |
| Dọn | `--dry-run` đúng danh sách | Giải thích vì sao tag an toàn hơn tiền tố; thứ tự xoá theo phụ thuộc; chạy thật rồi dry-run in 0 dòng |
| Chi phí | Có ngưỡng USD và alarm | Bảng free tier từng dịch vụ, rủi ro URL công khai, budget tạo trước tài nguyên đầu tiên |

## M12: kind, KServe, Argo Workflows

Bản tham chiếu ở `project/k8s/` và `project/argo/`. Không đổi dòng nào của `src/eta` hay hai Dockerfile: chuyển sang K8s là
việc của manifest.

- **Nguồn model: image model riêng + init container.** Cluster kind không tới được MLflow trên máy (stack bind `127.0.0.1`,
  node ở network Docker khác); `storageUri: s3://` cần kéo image `kserve/storage-initializer` và Secret S3 mỗi namespace.
  Image `busybox:1.37` + `model.joblib` nặng khoảng 3 MB, `kind_load` mất vài giây, trong khi image serve 820 MB và image
  train 1,04 GB chỉ nạp một lần mỗi phiên test (khoảng 6 giây mỗi image, nhờ cache layer). Modelcar (`storageUri: oci://`)
  là cùng ý tưởng nhưng chỉ nhận một model; canary của ETA cần hai. Phía người build còn một lý do: image model là đơn vị phát hành
  bất biến (tag = version, rollback là đổi tag), build ra từ `model.joblib` đã chốt nên pod không phụ thuộc MLflow còn sống hay
  registry còn nguyên lúc pod khởi động lại.
- **Canary trong app, không ở KServe.** Đã thử `canaryTrafficPercent: 20` trên cluster: KServe RawDeployment nhận trường,
  InferenceService vẫn Ready, nhưng chỉ có một Deployment và không chia gì. Port-forward cũng chỉ vào một pod. Dùng lại
  `route()` của M07 cho kết quả xác định, test tính trước từng request.
- **Biến release trong `env` của pod template**, không trong ConfigMap. Bản thử đặt `ETA_CANARY_WEIGHT` trong ConfigMap:
  bước 0.25 → 0.5 không sinh pod mới, test báo đúng request lệch nhánh. Đổi champion sang image của challenger (version vẫn
  ghi v1) cũng bị bắt: pod Ready, `model_version` đúng chữ, nhưng `eta_s` là của model kia.
- **Không có challenger = challenger trùng champion, weight 0.** Template không có điều kiện (`envsubst`), nên mọi release cùng
  một hình dạng pod; chi phí là nạp model hai lần (vài trăm KB).
- **Bảo mật pod:** `runAsNonRoot`, `readOnlyRootFilesystem` (thêm `emptyDir` cho `/tmp`), `drop: [ALL]`, `seccompProfile:
  RuntimeDefault`, `automountServiceAccountToken: false` (SA `default` của namespace test có quyền executor Argo); init
  container có limits riêng nhỏ. Các bước Workflow cũng `runAsNonRoot`, `seccompProfile: RuntimeDefault`,
  `allowPrivilegeEscalation: false`, `drop: [ALL]` (không `readOnlyRootFilesystem` vì CLI ghi ra `/tmp/out`). Liveness gọi `/healthz`, readiness `/readyz`, startupProbe cho
  tới 120 giây nạp model.
- **Workflow:** DAG ba task; `validate` là `script` Python: kiểm `month` bằng regex, rồi chạy `prepare` và `validate` dạng
  mảng (`subprocess.run([...])`, không shell, parameter đi qua `env`), xuất `sample` (parquet đã lấy mẫu) làm artifact cho
  `train`, nên `train` đọc đúng dữ liệu đã kiểm. Bản đầu ghép `{{workflow.parameters.month}}` vào `sh -c`: ai submit được
  Workflow là chạy được lệnh tuỳ ý trong container. `train` cũng là `script` kiểm lại `month` (template có thể bị tái dùng
  không có `validate` phía trước), nhận artifact ở đường dẫn cố định rồi symlink thành `<month>.parquet` cho `--input`;
  tiến trình con chết vì signal (OOM) thoát `128 + signal` kèm thông báo, không phải mã âm khó đọc. `gate` là `script` Python gọi `decide` + `Policy()`
  của M04, thoát `EXIT_REJECTED`. Input artifact `metrics` để `archive: none` (đọc được trên MinIO) nên cần `mode: 0444`:
  không có thì user 10001 gặp `PermissionError`. `retryStrategy` `OnError` chỉ ở `validate`, `train`; `gate` không retry.
- **Số đo** (laptop 16 nhân, image đã cache): `-k m12` 6 test khoảng 2 phút; Workflow thành công khoảng 30 giây, Workflow
  dừng ở `validate` khoảng 12 giây; bốn release canary cộng 160 request khoảng 26 giây.

Rubric M12:

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Nguồn model | Chạy được, nêu vì sao chọn | So ít nhất ba cách (bảng mục 1), nêu điều kiện chuyển sang `storageUri` + object storage |
| Release | Bảng bốn bước với thời gian rollout | Tiêu chí dừng canary bằng số (M09: tỉ lệ fallback, p95 theo `variant`), rollback bằng manifest trong git |
| Canary hạ tầng | Biết `canaryTrafficPercent` cần Serverless | Phác kế hoạch Knative hoặc Gateway API, cách đo tỉ lệ khi không còn `route()` trong app |

## M13: đánh giá junior, tháng lạ 2019-10

Tháng lạ sinh bằng `solutions/assessment/strange_month.py` (người học nhận tệp qua `etakit.py assessment`): mẫu 400 000
chuyến của 2019-10 thật (`SEED = 1313`), cài **ba** lỗi:

| `cause` | Cách cài | Công cụ lộ ra | Số đo (mẫu 50 000, `seed=0`) | Tháng 2019-09 |
| --- | --- | --- | --- | --- |
| `clock_error` | `VendorID == 1`, pickup 15–17/10: đảo pickup và dropoff | `eta.cli validate` exit 1, `negative_duration_share > 1%` | 3.59% dòng thời lượng âm | 0% |
| `unit_change` | `trip_distance` × 1.609344 (km) cả tháng | PSI/KS `trip_distance` của M10 | PSI 0.265, KS 0.223, median 2.67 | PSI 0.0016, median 1.68 |
| `timezone_shift` | Hai cột thời gian + 4 giờ (UTC thay cho EDT) cả tháng | PSI giờ đón của M10 | PSI 0.331, giờ đông nhất 22 | PSI 0.0005, giờ 18 |

Phát lại `2019-09..2019-11` (champion train trên 2019-08, `as_of = 2019-11`): MAE 2019-10 là 308.0 s (2019-09: 204.0 s),
bias +163.2 s (2019-09: -72.2 s), PSI `eta_s` 0.136. Đối chứng với tệp 2019-10 thật cùng pipeline: mọi PSI dưới 0.005,
MAE 197.8 s, validate qua. Chạy test khoảng 30 giây (dựng dữ liệu 2 s, phát lại 15–20 s).

Tác động từng lỗi (đảo ngược lỗi trên bản sao rồi phát lại):

| Bản sao | MAE (s) | bias (s) |
| --- | --- | --- |
| Nguyên trạng | 308.0 | +163.2 |
| Chỉ sửa khoảng cách | 261.9 | -134.2 |
| Chỉ sửa giờ | 318.4 | +242.0 |
| Sửa cả hai | 198.9 | -75.1 |

Hai lỗi kéo bias ngược chiều nhau và che bớt nhau. `clock_error` gần như không đổi MAE vì `clean` loại dòng thời lượng âm;
tác động của nó là chặn pipeline (đúng việc của validation).

Bẫy có chủ ý trong tập nhãn: `outside_month` (0.67% chuyến rơi sang 1/11, dưới ngưỡng 1% của validate; đó là hệ quả của
lệch giờ, không phải chuyến của tháng khác), `concept_drift` (MAE và bias tăng thật, nhưng do dữ liệu), `duplicate_rows`
(0.004%, như nhiễu thường). Quyết định đúng là `keep` champion và `quarantine: true`: luật test ép "lỗi dữ liệu thì không
`retrain`", và `rollback` vô nghĩa vì champion không đổi.

Vì sao chọn ba lỗi này: mỗi lỗi lộ ra ở một công cụ khác nhau (validate, PSI khoảng cách, PSI giờ), nên người học phải chạy
đủ pipeline; một người chỉ chạy validate thấy một lỗi và dừng là bài học chính. Lỗi `missing_zone` bị loại khi thiết kế vì
không công cụ nào của M03/M10 đo theo zone, chỉ đoán được.

Giới hạn đã biết: người học có thể dò đáp án bằng cách chạy test nhiều lần với từng nhãn (test chỉ báo **số** nhãn còn thiếu và
số nhãn thừa, không báo tên, nên dò từng nhãn tốn nhiều lần chạy), hoặc so với tệp gốc của TLC. Không ép được; rubric dưới đây là nơi chấm thật.

Rubric M13 (chấm `diagnosis.yaml` và `docs/assessment.md`; test chỉ kiểm nhãn, số và luật nhất quán):

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Quy trình | Chạy validate và replay, có bảng summary | Validate trước, phát lại có tháng đối chứng trước và sau, xác minh từng giả thuyết trên mẫu thô |
| `clock_error` | Trích `negative_duration_share` từ validate | Khoanh được hãng (`VendorID 1`) và ba ngày; không tự đảo cột khi chưa có xác nhận của nguồn |
| `unit_change` | PSI `trip_distance` cao, median tăng | Thấy tỉ lệ median ≈ 1.609 nên kết luận km; nêu PSI `eta_s` tăng là hệ quả, không phải nguyên nhân |
| `timezone_shift` | PSI giờ đón cao, giờ đông nhất dời | Độ lệch đúng 4 giờ khớp UTC−4 (EDT); chuyến sớm nhất ngày 1 gần 4 giờ sáng; giải thích 0.67% chuyến sang 1/11 là hệ quả |
| Loại trừ | Không có nhãn thừa | Nêu rõ đã loại `outside_month`, `concept_drift`, `seasonal_drift` bằng số nào |
| Tác động | MAE và bias trước/sau | Đo tác động từng lỗi bằng bản sao đảo ngược; thấy hai lỗi bù trừ bias |
| Quyết định | `keep` + `quarantine: true` | Tách quyết định cho model và cho dữ liệu; nói batch tháng đó hoãn, realtime không ảnh hưởng |
| Phòng ngừa | Có đề xuất check | Check mới có ngưỡng bằng số (median khoảng cách, PSI giờ đón, tỉ lệ theo hãng) và chỗ đặt trong DVC/runbook |

Mức Đạt cần mọi ô cột Đạt; mức Tốt cần ít nhất năm ô cột Tốt.

## M14: K8s chịu tải, Kueue, quota tách serving và training

Bản tham chiếu ở `project/k8s/` (`cluster.yaml`, `serving.yaml`, `training.yaml`, `retrain-job.yaml`, `eta.yaml` cập
nhật) và một gauge mới trong `project/src/eta/serve.py`. Số đo ở mục "Chịu tải trên K8s (M14)" của `project/README.md`.

- **Metric: số request đang xử lý.** CPU cần metrics-server (cluster không có), RPS và p95 cần Prometheus trong cluster
  để tính `rate()`/quantile. `eta_requests_in_flight` đọc thẳng từ `/metrics` bằng trigger `metrics-api`
  (`format: prometheus`), không label (luật M09). KEDA đọc qua Service nên mỗi lần chỉ thấy một pod: `metricType: Value`
  (`AverageValue` sẽ chia số đọc được cho số replica như thể đó là tổng). `targetValue: "1"` theo định luật Little (60
  req/s × 15 ms ≈ 1); bản thử `"2"` có lần dừng ở 2 replica.
- **`autoscalerClass: external`.** Đã thử: với `none`, `kubectl scale --replicas=2` bị KServe kéo về `minReplicas` ngay;
  với `external` số replica giữ nguyên kể cả khi apply lại InferenceService. Test M12 nhận cả hai, nên M12 vẫn xanh.
- **Readiness dưới tải.** Bản thử `limits.cpu: 500m`: pod bão hoà trả `/readyz` chậm hơn `timeoutSeconds` mặc định 1
  giây, bị rút khỏi Service, KEDA không đọc được metric qua Service rỗng và HPA không bao giờ scale (p95 4–6 giây, lỗi
  3%). Bản cuối giữ `limits.cpu: "1"` và nới readiness (`timeoutSeconds: 3`, `failureThreshold: 3`): readiness là "phục
  vụ được", không phải "đang bận".
- **Scale down chậm, scale up nhanh.** `scaleUp` không chờ, tối đa +4 pod mỗi 15 giây; `scaleDown` chờ 120 giây, bớt một
  pod mỗi 30 giây, vì mẫu in-flight của pod mới Ready thường là 0. Không scale về 0: cold start 10–25 giây trên laptop.
- **Quota.** Serving đủ cho `maxReplicaCount + 1` pod (rolling update) theo request/limit hiệu lực của pod
  (max(tổng container chính, init lớn nhất)); `count/jobs.batch: "0"`. Training bằng đúng quota ClusterQueue: nhỏ hơn
  thì Workload được admit mà pod bị `exceeded quota` (bản thử 500m: Job kẹt, test giờ fail ngay khi thấy event này).
- **Kueue.** ClusterQueue 1500m/1536Mi, Job 1 CPU/768Mi: đúng một Job một lúc; `StrictFIFO`. Job qua nhãn
  `kueue.x-k8s.io/queue-name` (cluster chỉ quản lý `batch/v1` Job, `manageJobsWithoutQueueName: false`). PriorityClass
  `eta-training` `preemptionPolicy: Never`: retrain chờ, không đẩy ai.
- **Kiểm bộ chấm (mutation):** valueLocation sai tên → fail ở kiểm `/metrics`; valueLocation `eta_model_info` (hằng 1) →
  1 replica; quota serving 300m → 2 replica và event `exceeded quota`; `autoscalerClass: none` → 1 replica, p95 2,8 giây;
  Job thiếu nhãn hàng đợi → không có Workload; ClusterQueue đủ hai Job → 2 Job admit cùng lúc; serving thiếu
  `count/jobs.batch` → Job lạc được nhận; quota training 500m → fail ngay vì `exceeded quota`; Job `sleep` thay vì train
  → không có `"mae"` trong log. Bản đúng viết khác (`minReplicaCount: 2`, `maxReplicaCount: 6`, quota tương ứng, URL
  `eta-predictor.<ns>`) qua contract.

Rubric M14:

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Chọn metric | Nêu metric và vì sao không dùng CPU | So bốn metric (bảng mục 1), tính `targetValue` từ sức chịu một pod đo được |
| Kết quả tải | Bảng replica theo thời gian, p95 hai pha | Giải thích độ trễ scale (chu kỳ HPA, cold start), nêu khi nào cần `minReplicaCount` > 1 |
| Quota và ưu tiên | Phép tính quota hai namespace | Nêu điều gì xảy ra khi node hết chỗ (ai bị đẩy, ai chờ), và giới hạn của cách lấy mẫu một pod |

## M15: retrain bằng Ray Tune, checkpoint, chịu worker bị kill

Bản tham chiếu ở `project/src/eta/distributed.py`; số đo ở mục "Retrain phân tán (M15)" của `project/README.md`.

- **Ray Tune theo cấu hình, không data-parallel.** GBDT dựng cây tuần tự; data-parallel GBDT (LightGBM/XGBoost
  distributed, allreduce histogram) chỉ đáng khi dữ liệu vượt RAM một worker và kéo theo đổi model, đổi serve. Các trial
  độc lập nên Tune chạy chúng song song, mỗi trial 1 CPU (`OMP_NUM_THREADS=1` do Ray đặt).
- **Checkpoint theo đợt cây.** `HistGradientBoostingRegressor(warm_start=True, early_stopping=False)`, mỗi đợt
  `set_params(model__max_iter=k)` rồi `fit`; checkpoint là thư mục tạm chứa `model.joblib`, `tune.report` chép nó vào
  `storage_path`. Trial mở đầu bằng `tune.get_checkpoint()`. Model cuối tắt `warm_start` trước khi trả về để lần `fit`
  sau (nếu có) không cộng dồn cây.
- **Worker phải import được `eta`.** Lần đầu thiếu `PYTHONPATH`: cả 4 trial `ActorDiedError` với
  `ModuleNotFoundError: No module named 'eta'`. Test đặt `PYTHONPATH=<project>/src` trước `ray_local`; image train đã có
  `PYTHONPATH=/app/src`.
- **Đo ở test:** kill ở 60 cây (sau 3 report), chạy lại từ 80 cây trên `pid` mới, 7 report sau khi chạy lại; cả lần
  retrain 25–30 giây; `mae` 33,8 so với 34,5 của model một tiến trình.
- **Kiểm bộ chấm (mutation):** bỏ đọc checkpoint → chạy lại từ 20 cây, fail; `max_failures=0` → retrain raise, mọi test
  fail; `max_concurrent_trials=1` → không có hai trial chồng nhau; checkpoint chỉ ở cuối → không kill được ai, fail;
  `metrics` đo trên `train` → lệch `evaluate` trên `valid`; đăng ký thẳng bằng MLflow không qua `log_and_register` → thiếu
  tag lineage. Bản đúng viết khác (tìm ngẫu nhiên 3 mẫu, checkpoint mỗi hai đợt, `num_to_keep=1`) pass cả bốn test.

Rubric M15:

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Lý do kiến trúc | Nêu vì sao không data-parallel GBDT | Ngưỡng dữ liệu/RAM để chuyển sang LightGBM distributed, kèm cái giá (serve, cổng M04) |
| Chịu lỗi | Log một lần kill và số cây trước/sau | Nêu nơi đặt checkpoint khi node chết thật (object storage), và `max_failures` khác gì retry của Job K8s |
| Hiệu năng | Thời gian `workers=2` | So `workers=1` và `workers=2` trên máy mình, giải thích vì sao không gấp đôi đúng |

## M16: feature real-time từ stream Kafka phát lại

Đường đi: `trip_events` (event time là lúc trả khách, vì tốc độ của chuyến chỉ biết khi chuyến kết thúc) → `replay` theo `SimClock`
→ topic `mlopskit.kafka_topic()` → `consume` (`ZoneSpeedWindows`: hỏng → trùng → trễ → cộng, watermark `max(ts) - 120`, đóng ngay
khi watermark qua `window_end`) → `on_close` → `feast_push.push` (offline mọi dòng, online dòng mới nhất mỗi zone nếu không cũ hơn)
→ `export_online` (snapshot JSON ghi nguyên tử) → API (`OnlineSpeed`, cùng luật sẵn sàng/TTL với `attach_live_speed`).

Quyết định:

- **Lúc trả khách, không phải lúc đón**: feature là tốc độ, chỉ tính được khi chuyến kết thúc. Lấy lúc đón làm event time thì cửa sổ
  08:00–08:15 chỉ đủ dữ liệu sau khi chuyến dài nhất của nó kết thúc (tới 3 giờ sau), watermark vô nghĩa.
- **Tỉ số của tổng**, không phải trung bình tốc độ từng chuyến: cộng dồn được trong stream, chuyến 0,1 dặm trong 60 giây không kéo lệch.
- **Sẵn sàng = `window_end + LATENESS_S`** khi dựng feature train: serving chỉ thấy cửa sổ sau khi watermark qua nó. Lấy `window_end`
  thì train thấy feature sớm hơn serving 2 phút, một dạng skew nhỏ nhưng có thật. Feast vẫn ghi `event_timestamp = window_end` (thời
  điểm của sự thật), điều kiện sẵn sàng nằm ở một hàm dùng chung.
- **Snapshot cho API** thay vì gọi Feast: image serving không có Feast (M06). Freshness đo tới lúc API đọc được.
- **Mặc định là `DEFAULT_SPEED_MPH`, trạng thái trả về trong response**: bài học trực tiếp của M18 (model điền 0 khi feature null).
- Message hỏng chỉ tăng `invalid`: consumer của M18 chết ở một message hỏng.

Số đo: replay 1 giờ dữ liệu ở `speedup=1800` mất khoảng 2 giây; freshness p50 592 s, p95 994 s, max 1 076 s ở `speedup=60` (ngưỡng
2 160 s). Cả nhóm test M16 chạy khoảng 1,5 phút (phần lớn là `test_m16_live_freshness`).

Mutation test của bộ chấm (đã chạy khi viết bài, mọi biến thể sai fail): `late` dùng `<` thay `<=`; không trừ lateness; không loại
trùng; không kiểm message hỏng; chỉ đóng cửa sổ lúc `flush`; tốc độ lệch 0,01%; event time là lúc đón (cả ở `trip_events` và
`zone_speed_batch`); `replay` không chờ đồng hồ; `attach_live_speed` bỏ lateness hoặc TTL tính từ lúc sẵn sàng; `push` không so thời
điểm online hoặc ghi online mọi dòng; API mặc định 0 hoặc bỏ TTL; `freshness` dùng percentile kiểu `lower`; `features.py` không nhận
`speed_15m_mph`. Lời giải đúng viết khác vẫn pass: consumer dùng thẳng `consumer_timeout_ms=idle_ms` như module 16; `push` so `>` thay
`>=`.

Giới hạn đã biết: một partition, một consumer; freshness đo trên một máy, xử lý 1 giây thật thành 60 giây mô phỏng nên máy tải nặng
làm số xấu đi (ngưỡng dư 2 lần). Snapshot chỉ giữ cửa sổ mới nhất mỗi zone: request "trong quá khứ" (phát lại) có thể nhận `stale` ở
chỗ point-in-time chọn được cửa sổ cũ hơn; chạy thật không xảy ra.

Rubric M16:

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Event time và watermark | Test xanh | Giải thích lúc trả khách, đo số sự kiện trễ khi đổi `LATENESS_S` 60/120/300 |
| Freshness | Có p50/p95 trong README | Tách thời gian chờ cửa sổ và thời gian xử lý; nêu alert freshness (ngưỡng, `for`) nối với SLO freshness của M18 |
| Nhiều partition, consumer chết | Nêu watermark theo partition | Chỉ chỗ commit offset sau push, push idempotent, cách bỏ qua message hỏng có log và đếm |
| Skew | Feature train và API cùng luật | Giải thích vì sao sẵn sàng là `window_end + lateness`, đo được bao nhiêu chuyến đổi giá trị nếu bỏ lateness |

## M17: nền tảng, ký, quét, chi phí

Template `platform/template/` giữ luật của module 17 bài Basic 01, thêm `train.py` (Ridge, safetensors), `metadata.json` chép tag vào
thư mục model để tag **được ký**. Cổng `deploy_gate` gộp bốn kiểm, báo đủ mọi lý do (gọi `scan` cả khi chữ ký đã sai), không nạp tệp
nào. `docs/onboarding.md` có 5 lệnh: copier, pytest của dự án sinh ra, train, ký, cổng.

Vì sao **Ridge + safetensors**: trọng số là hai tensor, nạp lại bằng `safetensors.numpy` và một phép nhân ma trận, không cần pickle,
không cần sklearn lúc serve; allowlist của cổng chỉ cần safetensors và JSON. LightGBM định dạng văn bản không chứa code nhưng là định
dạng riêng mà modelscan không đọc và allowlist phải thêm luật nhận diện; ONNX cần thêm runtime. MAE 0.72 USD so với 1.68 của trung vị
là đủ cho bài toán; tip của chuyến tiền mặt luôn ghi 0 nên `payment_type` gánh phần lớn.

Báo cáo chi phí tháng 11/2019 (`reports/cost.yaml`): `eta` 308.82, `eta/unlabelled` 5.29, `pricing-tip-amount` 32.66,
`unallocated` 4.59, idle 246.42 trên năng lực 351.36 USD. Idle lớn hơn cả chi phí trực tiếp (100.34), chủ yếu GPU node 240 giờ chỉ dùng
11 giờ: đó là con số mang tới buổi họp ngân sách, không phải chi phí của model nào.

Mutation test của bộ chấm (mọi biến thể sai fail): bỏ allowlist (pickle `.bin` qua được modelscan lọt cổng); bỏ quét; `verify` trả
`True` khi lỗi; bỏ kiểm tag; gọi `scan` hai lần; cho ký vào trong thư mục model; owner có default; cost center có default; test sinh ra
không kiểm tag; `train.py` xuất thêm `model.joblib`; idle âm khi dùng vượt; không bỏ khoảng trắng namespace; `unallocated` nhận phần
idle; sửa tay một số trong `reports/cost.yaml`; khối onboarding 6 lệnh hoặc có `&&`. Không bắt được: cổng nhận `returncode` 1 khi
không có issue (modelscan thật không trả như vậy; module 17 Intermediate 02 kiểm ca này bằng bản quét giả).

Giới hạn đã biết: lệnh cuối (cổng qua CLI) không chạy trong test vì sandbox không có Docker; test gọi `deploy_gate` với
`mlopskit.modelscan_run` thay vào. Log sử dụng là số dựng sẵn (`platform/make_usage.py`), không phải log cụm thật.

Rubric M17:

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Golden path | Test xanh, 5 lệnh | Giải thích `copier update` kéo thay đổi template về dự án cũ; đề xuất cách đưa luật mới (tag thứ tư) tới mọi dự án |
| Định dạng model | safetensors có lý do | So sánh với LightGBM text/ONNX bằng rủi ro và chi phí vận hành |
| Cổng | Bốn kiểm | Nêu ai giữ khoá riêng (CI có quyền ký, người không), phân phối khoá công khai, quy trình khi lộ khoá, so với Sigstore keyless |
| Chi phí | Báo cáo khớp | Hai đề xuất giảm idle có số tiết kiệm; giải thích showback trước chargeback và vì sao giữ dòng `unallocated` |

## M18: đánh giá senior, sự cố queens 2019-11-14

Sự cố sinh bằng `solutions/assessment/senior_incident.py` (người học nhận tệp qua `etakit.py incident`): mọi chuyến thật của
2019-11-14 ở ba borough là request, nhãn là thời gian chuyến thật. `v41` là trung vị theo cặp zone và giờ của 2019-10. `v42`
nhân `v41` với tỉ số tốc độ điển hình của zone (2019-10) trên tốc độ 15 phút gần nhất tính từ chuyến đã kết thúc trong ngày,
chặn trong [0.6, 2.5]. Script chạy khoảng 3 giây, không có số ngẫu nhiên. Chuỗi sự kiện:

| Giờ | Sự kiện | Ở đâu thấy |
| --- | --- | --- |
| 13:05 | `mdl-731`: queens lên `v42` 100% traffic, bỏ canary | `deploys.log`, chat |
| 15:20 | Consumer partition queens chết ở một message hỏng | `freshness.csv` (`age_s` tăng đều), chat lúc 16:32 |
| 15:35 | Feature cũ quá 900 giây | `freshness.csv` |
| 15:50 | Hết TTL 30 phút, online store trả null, `v42` điền 0 nên tỉ số chạm 2.5 | Tỉ lệ tệ queens từ 6% lên 95% |
| 16:21 | Support báo tài xế JFK/LGA thấy ETA gấp hai, gấp ba | chat (`detected_at`) |
| 16:40 | Restart consumer, chết lại ở cùng offset | chat |
| 17:00 | `mdl-733` rollback queens về `v41` | `deploys.log` (16:59:52), chat |
| 17:18 | Alert chất lượng cũ (1h và 5m trên 50%, `for` 10m, theo lúc nhãn về) mới bắn | `alerts.log` |
| 18:27 | Bỏ qua offset hỏng, feature tươi lại | `freshness.csv`, `deploys.log` (`ops-77`) |

Số đo (khung 5 phút, request queens trung bình khoảng 90 mỗi khung buổi chiều):

| Trường | Giá trị | Ghi chú |
| --- | --- | --- |
| Request/ngày, đỉnh/phút | manhattan 236 990 / 321, queens 15 631 / 35, brooklyn 2 461 / 9 | Sau khi bỏ chuyến dưới 60 s, trên 3 giờ, khoảng cách 0 |
| Tỉ lệ tệ thường ngày | manhattan 3.1%, queens khoảng 6%, brooklyn 9.5% | `v42` khi feature tươi (13:05–15:20) 5.3%, `v41` buổi sáng 8.3%: không có `model_regression` |
| `started_at`, `mitigated_at` | 15:50, 17:00 | Khung tệ nhất ngoài sự cố của queens là 32%; manhattan không khung nào quá 9%, brooklyn 16% |
| `affected_requests`, `bad_predictions` | 1 242, 1 176 (94.7%) | |
| `quality_budget_consumed_pct` | 2.51 | Budget queens 46 893 dự đoán tệ / 30 ngày |
| `stale_minutes`, `freshness_budget_consumed_pct` | 172, 39.81 | 15:35 tới 18:26 |
| `severity` | SEV1 | 14 khung trên 60% |
| Nhãn về sau (trung vị) | queens 37 phút, manhattan 12 phút | Lý do alert chất lượng luôn đến muộn |

Alert của lời giải chạy trên dữ liệu sự cố: `ETAMarketFeatureStale` bắn cho queens lúc 15:46, sớm hơn support 35 phút và trước khi
người dùng bị ảnh hưởng 4 phút; `ETAMarketQualityFastBurn` bắn lúc 17:15, sau rollback. Đó là bài học chính: với ML, SLO chất lượng
là tín hiệu trễ (bằng thời gian nhãn về), SLO freshness của feature là tín hiệu dẫn trước. Partition brooklyn kẹt 23 phút buổi sáng
(cũ quá 900 giây trong 8 phút) không làm alert freshness bắn, đúng vì 8 phút chỉ tiêu 1.9% budget.

Vì sao chọn kịch bản này: ba mốc của sự cố cách nhau rõ (thay đổi 13:05, hỏng ngầm 15:20, người dùng bị ảnh hưởng 15:50) nên
người kết luận theo "thay đổi gần nhất" chọn sai `cfg-514` hoặc `cfg-515`; budget chất lượng chỉ tiêu 2.5% dù cả market hỏng 70
phút, nên người xếp severity theo phần trăm budget sẽ hạ nhầm thành SEV2; người phát hiện là support, không phải alert, nên
`detected_at` phải đọc cả chat; hành động đầu tiên (restart) không có tác dụng và hành động chấm dứt tác động (rollback model) khác
hành động sửa gốc (bỏ offset). Mỗi điều là một việc mà người dẫn sự cố mức senior phải phân biệt. Kịch bản khác bài module 18:
dữ liệu là chuyến thật, nhiều market, và tác động phải tính từ log dự đoán và nhãn chứ không đọc sẵn từ một cột lỗi.

Bẫy trong tập nhãn: `config_change` (`cfg-515` ở brooklyn 2 phút trước tác động; `cfg-514` là thay đổi gần nhất trên service
queens), `model_regression` (xem tỉ lệ tệ của `v42` khi feature tươi), `label_delay` (alert đến muộn nhưng nhãn về đúng lúc trả
khách), `traffic_spike`, `upstream_data_change` (không có bằng chứng nào).

Mutation test của bộ chấm (đã chạy khi viết bài): mọi biến thể sai hợp lý sau đều fail, thông báo không lộ giá trị đúng: thêm
`config_change` hoặc bỏ `unsafe_default`; `mitigated_at` là giờ rollback 17:02; `detected_at` là giờ alert 17:18; `trigger` là
`cfg-514`; severity SEV2; `decision: restart`; tác động tính từ 15:20; phần trăm budget chia cho cả ba market; `stale_minutes` cộng
brooklyn; thêm brooklyn vào `affected_markets`; budget chất lượng với SLO 95%; burn rate không `by (market)`; freshness chỉ cửa sổ
5m; `LabelsMissing` kiểu `or vector(0)` toàn cục; ngưỡng nhanh 14.4; slow burn chỉ cửa sổ 30m; fast burn chỉ cửa sổ 1h; postmortem
nêu tên, có cụm đổ lỗi, thiếu mốc phát hiện, thiếu loại hành động `phát hiện`; design doc dùng số request chưa làm sạch, thiếu
fallback, thiếu một SLO. Các lời giải đúng viết khác đều pass: handle có `@`, phần trăm nhiều chữ số, ngày không ngoặc, rule viết
inline bằng `increase` với `and on (market)` và `for: 0m`, `LabelsMissing` bằng `count by`, số có dấu phân cách hàng nghìn.

Giới hạn đã biết: người học có thể dò `causes` bằng cách chạy test nhiều lần (test chỉ báo số nhãn thiếu và thừa), hoặc đọc
script sinh. Không ép được; rubric dưới đây là nơi chấm thật. `detected_at` cần phán đoán (tin nhắn nào là "báo triệu chứng");
đề nói rõ chat là một nguồn, và trong ngày chỉ có một tin như vậy trước alert.

Rubric M18 (chấm bốn tệp; test chỉ kiểm khung, số và nhãn):

| Mục | Đạt | Tốt |
| --- | --- | --- |
| Điều tra | Tính được mọi số của `incident.yaml` | Script tái lập một lệnh; xem theo market trước khi xem theo thời gian; tách ba mốc 13:05, 15:20, 15:50 và giải thích khoảng 30 phút là TTL |
| Nguyên nhân | Bốn nhãn đúng | Chuỗi nhân quả có thứ tự; loại từng bẫy bằng một số (tỉ lệ tệ của brooklyn quanh 15:48, `v42` khi feature tươi, độ trễ nhãn) |
| Severity và tác động | SEV1, số khớp | Giải thích vì sao 2.5% budget vẫn là SEV1; tính phần tệ "thừa" so với 6% thường ngày (khoảng 1 100) |
| Dẫn sự cố | Vai trò đúng | Nhận xét IC chặn giả thuyết `cfg-515`, chọn rollback (đảo ngược được) khi restart thất bại, giữ sự cố mở tới khi feature tươi |
| SLO và alert | Test xanh | Tính được alert của mình bắn lúc nào trên dữ liệu sự cố (15:46) và so với 16:21; giải thích burn rate tối đa 10 với SLO 90% |
| Postmortem | Không đổ lỗi, đủ phần | Mỗi nhãn có ít nhất một hành động; hành động có cách kiểm đo được; nói rõ điều may mắn (`v41` còn và không đọc feature) |
| Design doc | Đủ 11 phần | Cell theo market, fallback không phải 0, cổng canary có freshness, onboard bằng template; số ở phần 8 truy về phần 1 và 2; thừa nhận market nhỏ có ít nhãn |

Mức Đạt cần mọi ô cột Đạt; mức Tốt cần ít nhất năm ô cột Tốt.

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
| CI/CD (M08) | Ba workflow xanh/đỏ đúng chỗ | Thời gian từng workflow, giải thích ranh giới CI/CT/CD và vì sao CD đọc registry |
| Monitoring (M09) | Dashboard và bảng alert | Giải thích 0/0, chọn `absent` trên metric luôn có, ảnh dashboard khi chạy k6 |
| Drift và sự cố (M10) | Bảng summary 12 tháng | Xem rubric riêng ở mục M10 |
| Cloud (M11, tuỳ chọn) | `--dry-run` đúng, có budget | Xem rubric riêng ở mục M11 |
| Kubernetes (M12) | Test xanh, README có lệnh và bảng release | Xem rubric riêng ở mục M12 |
| Đánh giá junior (M13) | Ba nhãn đúng, `keep` + cách ly | Xem rubric riêng ở mục M13 |
| K8s chịu tải (M14) | Test xanh, README có metric, bảng replica, quota | Xem rubric riêng ở mục M14 |
| Retrain phân tán (M15) | Test xanh, README có lý do và log kill | Xem rubric riêng ở mục M15 |
| Feature real-time (M16) | Test xanh, freshness trong README | Xem rubric riêng ở mục M16 |
| Nền tảng (M17) | Test xanh, báo cáo chi phí | Xem rubric riêng ở mục M17 |
| Đánh giá senior (M18) | Bốn nhãn đúng, SEV1, alert theo market | Xem rubric riêng ở mục M18 |
