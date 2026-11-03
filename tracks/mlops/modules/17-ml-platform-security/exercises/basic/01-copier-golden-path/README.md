---
title: Golden path bằng Copier - template sinh dự án model có tag bắt buộc
level: basic
services: []
files:
  - path: starter/template/copier.yml
    note: 4 TODO - câu hỏi, validator, tệp câu trả lời
  - path: starter/template/project/mlproject.yaml.jinja
    note: Thêm registry_name và tags
  - path: starter/template/project/model.py.jinja
    note: Thêm nhánh classification
  - path: starter/template/project/tests/test_contract.py.jinja
    note: Test của dự án sinh ra, thêm kiểm tag và tên registry
  - path: tests/test_template.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/01-copier-golden-path -q
---

## Mục tiêu

Viết "golden path" đầu tiên của nền tảng: một template Copier mà đội nào cũng dùng để mở dự án model mới. Dự án sinh ra đã có sẵn
metadata đúng quy ước (owner, team, cost center, tên trên registry), có test của chính nó, và nhớ câu trả lời để sau này `copier update`
kéo thay đổi của template về.

## Đề bài

`starter/template/` là template Copier: `copier.yml` (câu hỏi) và `project/` (nội dung dự án, tệp `.jinja` được render rồi bỏ đuôi).
Hoàn thành để lệnh sau sinh ra dự án hợp lệ, không hỏi gì thêm:

```bash
uv run copier copy --defaults --data project_name="Tip Amount" --data team=pricing \
  --data owner=lan.nguyen@example.com --data cost_center=CC-2041 starter/template /tmp/tip-amount
```

Câu hỏi và luật mà test kiểm:

| Câu hỏi | Luật |
| --- | --- |
| `project_name` | bắt buộc, không rỗng |
| `project_slug` | mặc định từ `project_name`: bỏ khoảng trắng hai đầu, chữ thường, khoảng trắng thành `-` ("Tip Amount" thành `tip-amount`); phải khớp `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` |
| `team` | chỉ một trong `eta`, `pricing`, `fraud`, `search`, `ads` |
| `owner` | bắt buộc, **không có default**, là email (`ten@mien.tld`) |
| `cost_center` | bắt buộc, **không có default**, đúng dạng `CC-` và 4 chữ số |
| `model_kind` | `regression` (mặc định) hoặc `classification` |

Câu trả lời sai hoặc thiếu thì `copier copy` phải dừng với lỗi và không sinh dự án. Dự án sinh ra phải có:

- `mlproject.yaml` với `name` (= slug), `registry_name` (= `<team>-<slug>`), `model_kind`, và `tags` gồm đúng ba khoá `owner`,
  `team`, `cost_center` mang giá trị đã trả lời.
- `.copier-answers.yml` (tệp câu trả lời của Copier, có `_src_path` và các câu trả lời).
- `model.py` với hàm `train(X, y)` trả model sklearn đã fit: hồi quy khi `regression`, phân loại (dự đoán nhãn 0/1) khi
  `classification`.
- `tests/` mà `python -m pytest -q` trong thư mục dự án chạy **pass ít nhất 2 test**, và **fail** khi `mlproject.yaml` mất một
  trong ba tag bắt buộc. Tức là template sinh ra cả test canh quy ước, không chỉ test model.

Test chạy `copier copy` và test của dự án sinh ra trong sandbox `bwrap`, **không** có `--trust`: template không được dùng tính năng
mà Copier coi là không an toàn (`_tasks`, `_migrations`, `_jinja_extensions`). Test cũng đọc tệp cấu hình (`copier.yml` hoặc `copier.yaml`, đúng một tệp) để kiểm điều này.

Tệp Python trong template đặt tên đuôi `.py.jinja` (kể cả khi không có biến), để pytest của repo không thu thập test của template.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/01-copier-golden-path -q` pass.
- Bạn giải thích được vì sao golden path đặt test canh quy ước **trong dự án sinh ra** chứ không chỉ kiểm lúc sinh.
- Bạn biết `copier update` dùng `.copier-answers.yml` thế nào, và vì sao template có `_tasks` cần cờ `--trust`.

## Gợi ý

### Gợi ý 1

Validator của Copier là một chuỗi Jinja: render ra chuỗi rỗng là hợp lệ, ra chữ là thông báo lỗi. Copier có sẵn filter
`regex_search`: `"{% if not (cost_center | regex_search('^CC-[0-9]{4}$')) %}cost_center phải dạng CC-1234{% endif %}"`. Danh sách
lựa chọn dùng khoá `choices`.

### Gợi ý 2

Tệp câu trả lời là một tệp trong `project/` tên `{{ _copier_conf.answers_file }}.jinja`, nội dung `{{ _copier_answers | to_nice_yaml }}`.
Trong `mlproject.yaml.jinja`, viết giá trị bằng `{{ owner | tojson }}` để chuỗi lạ không làm hỏng YAML.
