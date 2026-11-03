---
title: Rà soát bảo mật workflow - tìm lỗi trong một pipeline retrain
level: advanced
services: []
files:
  - path: starter/REVIEW.yaml
    note: Kết quả rà soát, điền findings
  - path: tests/fixtures/vulnerable.yml
    note: Workflow cần rà, đọc kỹ
  - path: tests/test_review.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/advanced/02-workflow-security-review -q
---

## Mục tiêu

Đọc một workflow như người rà soát bảo mật: tìm những chỗ một PR hay một secret bị lộ có thể biến pipeline ML thành đường vào hệ
thống, và nói được cách sửa. Pipeline CI/CD giữ khoá registry, khoá cloud và quyền đẩy model lên production; nó là mục tiêu
đáng giá.

## Đề bài

`tests/fixtures/vulnerable.yml` là workflow `retrain-and-publish` của một đội ML (đừng chạy nó). Nó có **8 lỗi cố ý**; số dòng
tính theo chính tệp đó. Điền `starter/REVIEW.yaml`:

```yaml
findings:
  - line: 12            # số dòng của chỗ có lỗi
    severity: high      # high | medium | low
    risk: "..."         # vì sao nguy hiểm, kịch bản bị lợi dụng (từ 40 ký tự)
    fix: "..."          # cách sửa cụ thể (từ 30 ký tự)
```

Một mục được tính là bắt đúng một lỗi khi số dòng lệch tối đa 1 so với dòng lỗi **và** `risk`/`fix` nêu đúng bản chất (nhắc khái niệm
liên quan, vd. tên cơ chế hay hướng sửa). Hai lỗi nghiêm trọng nhất (chạy mã của PR với đặc quyền, chèn lệnh qua dữ liệu do người ngoài
viết) phải được đánh `high`. Mỗi lỗi chỉ tính một lần.

Không cần liệt kê mọi dòng đáng ngờ: ba dòng trong workflow là đúng (ví dụ action đã ghim sha đầy đủ). Báo tràn lan bị trừ: tối đa 2 mục không
khớp lỗi nào.

## Tiêu chí đạt

- Tìm đúng ít nhất 7 trong 8 lỗi.
- Mỗi mục có `line` là số nguyên, `severity` hợp lệ, `risk` từ 40 ký tự, `fix` từ 30 ký tự.
- Không quá 2 mục không khớp lỗi nào.
- Lỗi chạy mã PR với đặc quyền và lỗi chèn lệnh đánh `high`.
- Tự chấm lập luận bằng rubric trong `solutions/advanced/02-workflow-security-review/SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đi theo ba câu hỏi: ai kích hoạt workflow này (và họ có đáng tin không)? Nó chạy với quyền gì? Dữ liệu nào đi vào lệnh shell,
vào log, vào kho credentials? Mỗi câu thường lộ ra vài lỗi.

### Gợi ý 2

Tách từng lỗi thành ba ý trước khi viết: nguồn không tin cậy là gì, nó chạm tới đặc quyền nào, và nguyên tắc sửa (tách đặc quyền,
quyền tối thiểu, ghim, token ngắn hạn). Một `fix` chỉ nói "hãy cẩn thận" không đạt.
