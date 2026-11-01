---
title: Sự cố - PR refactor đòi xoá và tạo lại bucket export
level: intermediate
services: [localstack-devops]
files:
  - path: starter/infra/main.tf
    note: Cấu hình của PR 812
  - path: starter/ci/plan-guard.sh
    note: Guard cho CI, chưa làm gì
  - path: tests/fixtures/v1/main.tf
    note: Cấu hình production trước PR
  - path: tests/fixtures/incident/main.tf
    note: Bản PR lúc sự cố, test dùng để tái hiện triệu chứng
  - path: tests/fixtures/plans/bucket-replaced.json
    note: Plan JSON mẫu cho guard (cùng thư mục còn 4 tệp khác)
  - path: tests/test_incident_recreate.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/intermediate/03-incident-buckets-recreated -q
---

## Mục tiêu

Đọc một plan đáng ngờ như người on-call: tìm vì sao một thay đổi "chỉ đổi cách viết" lại đòi xoá tài nguyên có dữ liệu, sửa mà không
lùi lại thiết kế, và thêm một chốt chặn tự động để lần sau CI tự dừng trước khi có người apply.

## Đề bài

PR 812 "Chuẩn hoá export bucket" của Olist Shop chỉ sửa `infra/main.tf` (là `starter/infra/main.tf`). Production đang chạy theo
`tests/fixtures/v1/main.tf`; ba bucket `orders`, `payments`, `reviews` chứa file export hằng ngày mà team BI đọc. Bằng chứng:

- Job plan của PR in `Plan: 6 to add, 0 to change, 6 to destroy.` Các dòng `will be destroyed` đều có địa chỉ dạng
  `aws_s3_bucket.exports[0]`; các dòng `will be created` có dạng `aws_s3_bucket.exports["orders"]`. Tên bucket trong cả hai nhóm
  giống hệt nhau.
- Tác giả PR nói không đổi tên bucket nào và `tofu validate` sạch. Một người đề xuất apply với `-target` từng bucket một.
- Postmortem tháng trước: khi bỏ dataset `payments` khỏi danh sách, plan đòi thay thế bucket `reviews`; may mà reviewer thấy.
- Team muốn giữ cách viết mới vì lý do ở gạch đầu dòng trên.
- CI hiện không có bước nào dừng một plan xoá bucket; reviewer phải tự đọc.

Việc của bạn:

1. Sửa `starter/infra/` để áp lên state production hiện tại không tạo hay xoá bucket nào, giữ `for_each` theo `export_names`.
2. Viết `starter/ci/plan-guard.sh <plan.json>` (bash, có thể dùng `jq`): đọc output của `tofu show -json <tệp plan>`, nếu có tài
   nguyên kiểu `aws_s3_bucket`, `aws_dynamodb_table` hay `aws_kms_key` mà `change.actions` chứa `delete` (xoá hay thay thế) thì in
   địa chỉ và hành động của chúng rồi thoát `1`; ngược lại thoát `0`. Biến môi trường `ALLOW_DESTROY` chứa danh sách địa chỉ cách
   nhau bằng dấu cách được phép xoá (người duyệt ghi lý do trong PR); địa chỉ khác vẫn bị chặn.
3. Viết postmortem ngắn (không chấm tự động): nguyên nhân gốc, vì sao `validate` không bắt được, vì sao `-target` là ý tồi ở đây.

**Cách test chấm.** Qua `TofuLab` trên `localstack-devops`: apply `tests/fixtures/v1`, ghi một file vào mỗi bucket, thay bằng
`starter/infra/` của bạn, `init`, `plan -out` + `show -json`. Plan còn tạo hay xoá thì test không apply. Sau đó apply, plan lại,
và plan thử với `export_names = ["orders", "reviews"]` (không apply). Guard chạy trong sandbox trên 5 plan JSON mẫu trong
`tests/fixtures/plans/` và trên hai plan thật vừa sinh. Một test chạy bản lúc sự cố (`tests/fixtures/incident`) trên state v1 và
đòi nó tái hiện đúng triệu chứng. Cả bài khoảng 1,5 phút.

## Tiêu chí đạt

- Plan sau khi sửa không có `create` hay `delete`; apply xong file trong cả ba bucket còn nguyên.
- State có đúng 6 địa chỉ theo khoá tên (`aws_s3_bucket.exports["orders"]`...), plan lại `No changes`.
- Bỏ `payments` khỏi danh sách thì plan chỉ xoá `aws_s3_bucket.exports["payments"]` và
  `aws_s3_bucket_versioning.exports["payments"]`, không đụng gì khác.
- Guard: `safe-moves.json` và `parameter-deleted.json` thoát 0; `bucket-replaced.json`, `table-replaced.json`,
  `payments-deleted.json` thoát 1 và in địa chỉ; `payments-deleted.json` với `ALLOW_DESTROY` chứa đúng địa chỉ đó thoát 0;
  `table-replaced.json` với `ALLOW_DESTROY` chứa địa chỉ khác vẫn thoát 1. Trên plan thật: plan đã sửa thoát 0, plan bỏ `payments`
  (không `ALLOW_DESTROY`) thoát 1.

## Gợi ý

### Gợi ý 1

So địa chỉ của cùng một bucket trong state cũ và trong cấu hình mới. OpenTofu so khớp tài nguyên theo **địa chỉ**, không theo tên
bucket hay ID. `tofu state list` trên state v1 và đọc lại tài liệu về `count` và `for_each` trong mục 2 của module.

### Gợi ý 2

Trong plan JSON, mỗi phần tử của `resource_changes` có `address`, `type` và `change.actions` (`["create"]`, `["delete"]`,
`["delete","create"]` khi thay thế, `["no-op"]`...). `jq --argjson` và `index` đủ để lọc; nhận danh sách cho phép bằng
`jq -n --arg list "$ALLOW_DESTROY" '$list | split(" ")'` để không phải lo shell tách chữ hay glob dấu `[`.
