---
title: Lab cloud tuỳ chọn - kế hoạch dọn có kiểm tĩnh, dry-run và cảnh báo chi phí ẩn
level: intermediate
services: []
files:
  - path: starter/teardown.py
    note: 3 hàm TODO
  - path: tests/test_teardown.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/intermediate/03-cloud-lab-teardown-plan -q
---

## Mục tiêu

Lab cloud (SageMaker, Vertex AI, Azure ML) là phần **tuỳ chọn** của module; hoá đơn bất ngờ thì không tuỳ chọn. Bài này luyện phần chấm được trên máy: sinh kế hoạch dọn an toàn từ danh sách tài nguyên của lab, in dry-run trước, và cảnh báo thứ nào còn tính tiền. Không có test nào cần tài khoản, khoá hay mạng cloud.

## Đề bài

Lý do chấm được mà không cần cloud: test (1) kiểm **tĩnh** các lệnh sinh ra (so chuỗi với bảng lệnh bên dưới) và (2) chạy script thật bằng `bash` với các CLI `aws`, `gcloud`, `az` **giả** do test dựng trong thư mục tạm, chỉ ghi lại tham số. Bạn không chạy lệnh nào với tài khoản cloud thật, và test không kiểm lệnh đúng với bản CLI nào. Trước khi tự dọn lab thật, đối chiếu từng lệnh với tài liệu của nhà cung cấp.

Danh sách tài nguyên (`inventory`) là list dict `{"provider", "type", "name", "region", "tags"}`. Trong `starter/teardown.py`:

1. `plan_teardown(inventory, lab) -> list[dict]`: mỗi bước `{"resource": name, "type": type, "command": "..."}`. Luật mà test ép:
   - **Chỉ** động tới tài nguyên có `tags["lab"] == lab`. Thiếu tag hay tag lab khác thì bỏ qua hoàn toàn, kể cả khi tên giống lab. Không bao giờ dọn theo tên, theo vùng hay theo loại.
   - Thứ tự theo bảng `ORDER` trong starter: endpoint trước endpoint-config trước model; notebook, NAT gateway; bucket và resource group cuối cùng. Cùng loại giữ thứ tự trong `inventory`.
   - `name` phải khớp `SAFE_NAME` (chữ thường, số, `-`, `_`, tối đa 63 ký tự), không thì `ValueError` nêu tên; loại không có trong bảng lệnh thì `ValueError` nêu loại. Không chèn tên vào lệnh trước khi kiểm.
   - Lệnh theo loại (`R` là `region`, `N` là `name`):

     | type | command |
     | --- | --- |
     | `sagemaker-endpoint` | `aws sagemaker delete-endpoint --endpoint-name N --region R` |
     | `sagemaker-endpoint-config` | `aws sagemaker delete-endpoint-config --endpoint-config-name N --region R` |
     | `sagemaker-model` | `aws sagemaker delete-model --model-name N --region R` |
     | `sagemaker-notebook` | hai bước, theo thứ tự: `aws sagemaker stop-notebook-instance --notebook-instance-name N --region R` rồi `aws sagemaker delete-notebook-instance --notebook-instance-name N --region R` |
     | `nat-gateway` | `aws ec2 delete-nat-gateway --nat-gateway-id N --region R` |
     | `s3-bucket` | `aws s3 rb s3://N --force` |
     | `vertex-endpoint` | `gcloud ai endpoints delete N --region=R --quiet` |
     | `vertex-model` | `gcloud ai models delete N --region=R --quiet` |
     | `gcs-bucket` | `gcloud storage rm --recursive gs://N` |
     | `azureml-endpoint` | `az ml online-endpoint delete --name N --resource-group G --yes` với `G` là `inventory[i]["resource_group"]` (thiếu thì `ValueError`) |
     | `azure-resource-group` | `az group delete --name N --yes --no-wait` |

   - Không có wildcard (`*`), `--all`, hay `--force` ngoài `s3 rb` trong lệnh nào.
2. `render_script(steps) -> str`: script bash bắt đầu bằng `#!/usr/bin/env bash`, có hàm `run`, mỗi bước là một dòng `run <command>`. Mặc định (không đặt `DRY_RUN`) **chỉ in** `DRY-RUN: <command>` và không gọi CLI nào; `DRY_RUN=0` mới chạy thật. Một bước lỗi **không dừng** các bước sau: script ghi `FAILED: <command>` ra stderr, chạy hết, và thoát mã khác 0 nếu có bước lỗi (dọn dở dang còn tệ hơn báo lỗi). Mã sinh ra không chèn chuỗi nào mà test chưa kiểm qua `plan_teardown`.
3. `leftover_warnings(inventory, lab) -> list[dict]`: `{"resource", "why"}` cho tài nguyên **không** có tag `lab` đúng nhưng tên bắt đầu bằng `lab` (có thể do ai đó tạo tay: kế hoạch không động tới nên người dùng phải tự kiểm; `why` chứa chữ `tag`). Trả theo thứ tự `inventory`; rỗng khi mọi thứ trông giống lab đều đã có tag.

## Tiêu chí đạt

- Test pass.
- Giải thích được vì sao dọn theo tag của lab, không theo tên hay theo loại, và vì sao script mặc định dry-run.
- Liệt kê được ít nhất ba chi phí ẩn của lab ML trên cloud (NAT gateway, endpoint quên tắt, bucket và log giữ lại, snapshot đĩa notebook, dữ liệu egress) và cách ghi chúng vào lệnh dọn hay cảnh báo.
- Trước khi làm lab thật: có budget alarm (nhớ nó chỉ **báo**, không dừng chi tiêu) và đã kiểm free tier hiện hành của nhà cung cấp.

## Gợi ý

### Gợi ý 1

Lọc theo tag trước, sắp xếp theo `ORDER.index(type)` (sắp xếp ổn định giữ thứ tự cùng loại), rồi mới sinh lệnh. Kiểm `SAFE_NAME.fullmatch` cho mọi tài nguyên của lab trước khi sinh bất cứ lệnh nào, để lỗi không để lại kế hoạch dở.

### Gợi ý 2

Hàm `run() { if [ "${DRY_RUN:-1}" = "0" ]; then "$@" || { echo "FAILED: $*" >&2; FAILED=1; }; else echo "DRY-RUN: $*"; fi; }` và `exit "${FAILED:-0}"` ở cuối. Đặt `FAILED=0` đầu script.
