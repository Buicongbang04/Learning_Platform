# Onboard một model mới lên nền tảng ETA

Golden path cho đội muốn đưa model của mình lên cùng nền tảng với ETA: sinh dự án từ template, train, ký, qua cổng deploy. Ví dụ
dưới đây là model thứ hai của nền tảng, **dự đoán tiền tip** (`tip_amount`) của đội `pricing`.

## Onboarding

Chạy từ một thư mục làm việc trống, với `PLATFORM` là thư mục template (`capstone/project/platform/template`), `TRIPS` là một tháng
TLC (`data/raw/nyc-tlc/yellow_tripdata_2019-03.parquet`), `SIGNING_KEY`/`PUBLIC_KEY` là cặp khoá EC của pipeline phát hành, và
`PYTHONPATH` trỏ `capstone/project/src` (để có `eta.platform`).

```bash
python -m copier copy --defaults --quiet --data project_name="Tip Amount" --data team=pricing --data owner=lan.nguyen@example.com --data cost_center=CC-2041 "$PLATFORM" tip-amount
python -m pytest -q tip-amount
python tip-amount/train.py --data "$TRIPS" --out tip-amount/build
python -m eta.platform sign tip-amount/build/model --key "$SIGNING_KEY" --out tip-amount/build/model.sig
python -m eta.platform gate tip-amount/build/model --signature tip-amount/build/model.sig --public-key "$PUBLIC_KEY"
```

1. Sinh dự án: trả lời thiếu hay sai (owner không phải email, cost center sai dạng, đội lạ) thì Copier dừng, không sinh gì.
2. Test của chính dự án: canh tag bắt buộc, quy ước tên registry, model xuất ra chỉ có safetensors và JSON.
3. Train Ridge trên 300 000 chuyến mẫu, đánh giá trên 20% cuối theo thời gian, xuất `build/model/` (`model.safetensors`,
   `config.json`, `metadata.json` chép tag từ `mlproject.yaml`) và `build/metrics.json`.
4. Ký cả thư mục model; chữ ký nằm ngoài thư mục.
5. Cổng deploy (cần Docker cho modelscan): mã thoát 0 khi được deploy, in lý do khi bị chặn.

## Số đo (2019-03, mẫu 300 000 chuyến, `seed=0`)

| Model | MAE tip (USD) |
| --- | ---: |
| Trung vị của tập train | 1.68 |
| Ridge, 7 feature | 0.72 |

Tip của chuyến trả tiền mặt luôn ghi 0 trong dữ liệu TLC (tài xế không khai báo), nên `payment_type` là feature mạnh nhất; model
này dự đoán "tip được ghi nhận", không phải tip thật của chuyến tiền mặt.
