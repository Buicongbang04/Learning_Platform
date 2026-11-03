# Lời giải tham chiếu: capstone dịch vụ ETA (M01–M04)

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
- **Host header của MLflow:** server MLflow 3 trả 403 cho Host `mlflow:5000`. Bản này chọn đổi tên host thành IP phía
  client (`ETA_MLFLOW_PIN_IP=1` trong `serve.py`) vì không được sửa stack chung. Cách đúng lâu dài là thêm
  `--allowed-hosts` vào lệnh server; ghi vào README như một việc nợ.

## M03: DVC và validation

- **`foreach: ${months}` cho `prepare` và `validate`**: thêm tháng là thêm một dòng trong `params.yaml`, mỗi tháng là một
  stage có hash riêng, tháng cũ không chạy lại.
- **`train` phụ thuộc thư mục báo cáo `reports/validation`**, không chỉ dữ liệu. Đó là cạnh duy nhất buộc thứ tự
  `validate → train`; thiếu nó, DVC không biết `train` phải chờ `validate`, có thể chạy `train` trước, và tháng hỏng vẫn vào model.
- **Params đúng chỗ:** `prepare` chỉ phụ thuộc `sample_rows`, `seed`; `train` phụ thuộc `model_params`, `months`, `seed`.
  Khai cả `params.yaml` làm dependency của mọi stage là lỗi hay gặp: sửa learning rate thì đọc lại 110 MB parquet.
- **Validation trên dữ liệu thô đã lấy mẫu, trước `clean`.** Sau `clean` thì mọi tháng đều "sạch" và validation không
  thấy gì. Ngưỡng 1% cho tỷ lệ thời lượng âm, khoảng cách âm, pickup ngoài tháng: mọi tháng 2019 đều dưới 0,1% (cao nhất
  là khoảng cách âm 0,09% ở 2019-11), nên 1% cách xa nhiễu bình thường hơn 10 lần mà vẫn chặn được sự cố kiểu 5%.
  Zone cho phép tới 265 vì 264/265 là mã hợp lệ của TLC (Unknown); `clean` loại chúng, validation không coi là hỏng.
- **Dữ liệu thô nằm ngoài repo DVC** (`../../../../data/raw/nyc-tlc`): DVC hash nó như dependency ngoài, đủ để biết
  khi nào tệp đổi. Muốn người khác `dvc pull` được cả dữ liệu thô thì phải `dvc add` nó vào repo; capstone không làm vì
  dữ liệu đã có lệnh tải riêng.

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
- **API nạp theo số version đã phân giải** (`get_model_version_by_alias` rồi `models:/eta/<N>`): `/healthz` báo đúng
  version, không có khoảng trống giữa "đọc alias" và "tải model" mà alias đổi giữa chừng.

## Rubric phần tự đánh giá

| Mục | Đạt | Tốt |
| --- | --- | --- |
| README M01 | Lệnh train, MAE so với baseline | Thêm số dòng mỗi luật loại, giải thích vì sao chia theo thời gian |
| Test của người học | Có test cho `clean` và config | Ca biên từng luật, test tái lập, test không đọc dữ liệu thật |
| Image (M02) | Hai image chạy được, non-root | Đo cache khi sửa `src/`, có số trivy, giải thích phần nào chiếm dung lượng |
| Ngưỡng validation (M03) | Có ngưỡng, mọi tháng 2019 qua | Lý do bằng số đo thật, nói rõ đánh đổi chặt/lỏng |
| Remote DVC | `dvc push` thành công | Xoá cache, `dvc pull` lại đúng, khoá ở `config.local` |
| Registry (M04) | Có ≥2 version, một lần promote | Runbook rollback có thời gian đo, model card nêu giới hạn đã biết |
