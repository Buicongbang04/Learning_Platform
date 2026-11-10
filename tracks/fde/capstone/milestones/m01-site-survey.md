# M01: Khảo sát máy staging của khách

## Mục tiêu

IT phòng pháp chế cấp cho bạn một user `fde` có sudo trên VM staging và nói vài câu qua email: "Ubuntu 22.04, máy không
ra internet, image phải lấy từ registry nội bộ HTTP ở `10.0.2.101:5000`, Docker không có plugin compose. VM sẽ được
cấp 5 GB RAM." Phần còn lại bạn phải tự đọc từ máy, vì câu trả lời của IT thường đúng một nửa.

Milestone này đưa script khảo sát của [module 01](../../modules/01-site-survey/README.md) vào repo của bạn, chạy nó trên
máy của khách, so với yêu cầu của `quillo` và viết **báo cáo khoảng cách** cho IT khách: cài được không, cần họ làm gì,
cần bạn mang gì. Báo cáo này là đầu vào của installer ở M02–M03.

Script chạy trên máy của khách nên phải lịch sự: không cần root, không cài gì, không đọc dữ liệu nghiệp vụ, không dump
biến môi trường hay lịch sử shell, và không bao giờ mang mật khẩu về (proxy có `user:pass@` thì bỏ phần đó).

## Việc cần làm

1. `survey/site_survey.sh`: POSIX `sh`, chạy bằng user thường, in **một object JSON** ra stdout với 13 khoá như bài
   [01-survey-report](../../modules/01-site-survey/exercises/basic/01-survey-report/README.md) của module 01 (cùng tên, cùng
   kiểu, cùng định nghĩa): `os_id`, `os_version`, `kernel_major`, `glibc`, `cpus`, `mem_mb`, `disk_free_gb_max`, `gpu`,
   `proxy_url`, `sudo`, `selinux`, `runtime`, `egress`. Thêm khoá khác bạn thấy cần cho khách này thì cứ thêm.
   Script tự giới hạn thời gian mọi lệnh mạng, xong trong 30 s.
2. `survey/preflight.py`: dùng lại bài [02-preflight](../../modules/01-site-survey/exercises/basic/02-preflight/README.md),
   viết lại trong repo của bạn.

   ```bash
   python3 survey/preflight.py <survey.json> <REQUIREMENTS.yaml>
   ```

   In ra stdout **một danh sách JSON**, mỗi phần tử `{"check": ..., "severity": "blocker"|"warning", "detail": ...}`;
   thoát `1` khi có ít nhất một blocker, ngược lại `0`. Tên `check` như module 01: `os`, `cpus`, `mem`, `disk`,
   `runtime` cho blocker về năng lực, `egress` cho cảnh báo mạng; thêm check khác tuỳ bạn. RAM dưới `min_mem_mb` quá 10%
   là blocker `mem`. `REQUIREMENTS.yaml` lấy từ bản phát hành quillo (`tracks/fde/product/REQUIREMENTS.yaml`, MIT, chép
   vào repo của bạn được). Cần Python 3.10+ và PyYAML.
3. Target `make survey` chạy script trên máy khách qua SSH rồi chạy preflight trên máy bạn, vd.
   `make survey SSH="ssh fde@staging"` (không chấm, nhưng các milestone sau dùng cùng kiểu biến `SSH`).
4. Tự boot máy staging, chạy survey, đọc kết quả, hỏi lại những gì IT nói:

   ```python
   with fdekit.customer_site("lawfirm-staging", memory_mb=5120) as s:   # trong uv run python, ở repo học
       s.vm.put(Path("<repo của bạn>/survey/site_survey.sh"), "/home/fde/site_survey.sh")
       print(s.vm.ssh("sh /home/fde/site_survey.sh").stdout)
   ```

   Lưu kết quả JSON vào repo (vd. `reports/survey-lawfirm-staging.json`).
5. `reports/site-survey.md`: báo cáo cho IT khách. Mở đầu bằng **frontmatter YAML** có `blockers` và `warnings`, mỗi
   danh sách gồm các mục `{check, detail}` (danh sách rỗng ghi `[]`); thêm khoá khác tuỳ bạn (vd. `asks` cho việc cần IT
   làm). Phần thân: tóm tắt một câu "cài được không", bảng máy hiện tại so với yêu cầu, việc cần IT làm (có lý do và
   tác động), thay đổi bạn sẽ làm trên máy họ. Viết cho người IT đọc trong năm phút, không phải cho bạn.

## Kết quả nộp

`survey/site_survey.sh`, `survey/preflight.py`, `reports/site-survey.md` (và JSON survey bạn đo) đã commit.

```bash
uv run pytest tracks/fde/capstone -k m01 -q      # ~60 s, boot một VM 5120 MB
```

## Tiêu chí đạt

- [ ] `test_m01_survey_matches_lawfirm`: test dựng `customer_site("lawfirm-staging", memory_mb=5120)`, chép
  `survey/site_survey.sh` vào `/home/fde/site_survey.sh` và chạy `sh /home/fde/site_survey.sh` bằng user `fde`:
  - thoát `0` trong 30 s, stdout là một object JSON có đủ 13 khoá;
  - giá trị khớp số đo trong cùng VM và hồ sơ khách: `os_id`, `os_version`, `glibc`, `kernel_major` (hai số đầu của
    `uname -r`), `cpus`, `mem_mb` (số nguyên, `MemTotal` tính MB, lệch ≤1), `disk_free_gb_max` (GiB trống ở `/`, lệch
    ≤0,15), `gpu` là `null`, `proxy_url` là `null`, `sudo`, `selinux`, `runtime`, `egress`;
  - test thêm một dòng `https_proxy=http://svc:<chuỗi ngẫu nhiên>@10.0.2.100:3128` vào `/etc/environment` và chạy lại
    với một biến môi trường bí mật `QUILLO_DB_PASSWORD=<chuỗi ngẫu nhiên>`: output không chứa hai chuỗi đó,
    `proxy_url` là `http://10.0.2.100:3128`, các khoá khác vẫn khớp;
  - `preflight.py` trên JSON của lần chạy đầu: thoát `0`, không blocker, có warning `egress`.
- [ ] `test_m01_preflight_report`: `preflight.py` chạy trong sandbox bằng Python 3.12 của repo học, với
  `tracks/fde/product/REQUIREMENTS.yaml`:
  - "sự thật" của máy staging (`fdekit.PROFILES["lawfirm-staging"].facts` với `mem_mb` 5120): thoát `0`, không blocker,
    có warning `egress`;
  - cùng máy nhưng `mem_mb` 2048 (cấu hình mặc định của hồ sơ): thoát `1`, có blocker `mem`;
  - mọi phần tử có `check`, `severity` (`blocker`/`warning`), `detail`;
  - `reports/site-survey.md` có frontmatter YAML: `blockers` là `[]`, `warnings` là danh sách các mục có `check` và
    `detail` không rỗng, trong đó có `check: egress`.
- [ ] Thiếu KVM hoặc golden image thì test skip kèm lệnh `uv run python -m fdekit prepare lawfirm-staging`.
