# Hướng làm: chọn ngôn ngữ cho công cụ vận hành olistctl

Bài Advanced không có một đáp án duy nhất. Hai hướng đều bảo vệ được: **Python cho `olistctl`, giữ Bash cho phần
nhỏ chạy trên VM**, hoặc **Go cho `olistctl`** nếu team chấp nhận chi phí học và build. Chọn "Bash cho mọi thứ, thêm
shellcheck và bats" không đạt: nó không loại được lớp lỗi của sự cố thứ hai và thứ ba, và đi ngược nhu cầu gọi API, xử
lý JSON. Phần dưới gồm cách sắp ràng buộc, một ADR mẫu, các quyết định cần cân nhắc và rubric.

## Sắp ràng buộc

| Ràng buộc | Loại | Hệ quả |
| --- | --- | --- |
| Người trực sửa nóng lúc 3 giờ sáng | Bắt buộc | Ngôn ngữ team đọc được; mã nguồn có trên máy hoặc build lại được trong vài phút |
| Chạy trên VM không cài thêm gói | Bắt buộc cho phần chạy trên VM | Bash, Python 3.12 hệ thống chỉ dùng thư viện chuẩn, hoặc binary tĩnh (Go, Rust) chép lên |
| Ba sự cố: biến rỗng, parse text, lỗi một máy bị bỏ qua | Bắt buộc phải giải quyết | Cần kiểu dữ liệu, ngoại lệ hoặc lỗi tường minh, client API thay cho parse output |
| Gọi API Kubernetes, S3, PagerDuty; JSON lồng nhau | Nên có, tăng dần | Hệ sinh thái thư viện: Python (`kubernetes`, `boto3`, `httpx`) và Go (`client-go`, AWS SDK) mạnh nhất |
| Laptop Ubuntu, macOS, WSL2; runner CI | Nên có | Tránh khác biệt GNU/BSD của Bash; Python qua `uv` hoặc binary Go chạy giống nhau |
| Hai người thạo Python, một người biết Go | Nên có | Python chuyển nhanh nhất; Go cần đào tạo |
| Tối đa hai quý, song song vận hành | Bắt buộc | Chuyển từng phần, không viết lại một lần |

## ADR mẫu

```markdown
# ADR: Ngôn ngữ cho công cụ vận hành olistctl

## 1. Bối cảnh

Bắt buộc: (1) người trực phải đọc và sửa nóng được lúc 3 giờ sáng; (2) phần chạy trên VM không được cài thêm gói,
VM có Python 3.12 hệ thống; (3) phải loại được ba lớp lỗi gây sự cố quý trước: biến rỗng dẫn tới xoá nhầm, parse output
text của công cụ khác, và chạy tiếp khi một trong 12 máy lỗi; (4) chuyển đổi trong tối đa hai quý, song song vận hành.
Nên có: gọi API Kubernetes, object storage, PagerDuty và xử lý JSON lồng nhau; chạy giống nhau trên laptop Ubuntu,
macOS, WSL2 và runner CI; tận dụng hai người thạo Python và việc team phát triển cũng dùng Python.

## 2. Phương án

| Ngôn ngữ | Phân phối và chạy trên máy đích | Xử lý lỗi và kiểm thử | Thư viện cho việc cần làm | Team viết và sửa được | Điểm (1-5) |
| --- | --- | --- | --- | --- | --- |
| Bash | Có sẵn mọi nơi; khác biệt GNU/BSD trên macOS | `set -e` có nhiều ngoại lệ; lỗi ở biến rỗng, tách từ; test bằng bats hoặc pytest + subprocess | Không có client API; parse JSON bằng jq, parse text dễ vỡ | Cả 4 người, nhưng chính là nguồn của 3 sự cố | 2 |
| Python | VM có 3.12 cho script chỉ dùng thư viện chuẩn; olistctl đóng gói bằng uv (lockfile) trên laptop và CI | Ngoại lệ, type hints kiểm bằng mypy, pytest đã dùng ở team phát triển | kubernetes, boto3, httpx, pdpyras; JSON là dict | 2 người thạo, 1 người đọc được; team phát triển hỗ trợ review | 4 |
| Go | Một binary tĩnh chép lên VM, laptop, CI; cross-compile dễ | Lỗi trả về tường minh, kiểu tĩnh; go test có sẵn | client-go, AWS SDK, cobra cho CLI; là ngôn ngữ của Kubernetes | 1 người biết; cần build để sửa nóng | 3 |
| PowerShell 7 | Cài thêm runtime trên VM và macOS | Object pipeline, try/catch; Pester | Mạnh với Windows và Azure, yếu với hệ sinh thái Linux của team | Không ai biết | 1 |

## 3. Quyết định

Chọn: Python cho olistctl, giữ Bash cho các đoạn ngắn chạy trên VM và trong container

Python 3.12 loại được ba lớp lỗi gây sự cố mà không đổi nền tảng: biến chưa gán là lỗi ngay, đường dẫn đi qua pathlib
thay vì nối chuỗi, gọi Kubernetes bằng client thay vì parse output, và mỗi lỗi trên một máy là ngoại lệ được gom lại
rồi báo đủ cả 12 máy. VM đã có Python 3.12, nên phần nhỏ chạy trên VM viết bằng thư viện chuẩn, không cài gì. Hai người
viết thạo ngay, team phát triển review được, người trực đọc và sửa được mà không cần build. Cái giá chấp nhận: olistctl
cần một môi trường Python có phụ thuộc (đóng gói bằng uv, khoá phiên bản), khởi động chậm hơn binary Go vài trăm mili
giây, và một người chỉ viết Bash cần khoảng một tháng làm quen.

## 4. Ranh giới giữa các ngôn ngữ

- Giữ Bash cho entrypoint container, git hook, bước CI dưới khoảng 50 dòng, và lệnh một dòng trong runbook: chỉ nối
  các lệnh có sẵn, không có logic rẽ nhánh phức tạp. Mọi script Bash phải qua shellcheck trong CI.
- Chuyển sang olistctl (Python) mọi thứ gọi API, xử lý JSON, chạy trên nhiều máy, hay xoá dữ liệu: backup/restore,
  deploy lên 12 VM, xoay secret, gom log.
- Phần chạy trên VM (khởi động lại service, gom log cục bộ) là module Python chỉ dùng thư viện chuẩn, được olistctl chép
  lên và chạy qua SSH, không cần cài gì.

## 5. Kế hoạch chuyển đổi

1. Tuần 1–2: dựng khung olistctl (argparse hoặc Typer, logging JSON, exit code chung, pytest, uv lockfile, CI chạy
   test và shellcheck cho phần Bash còn lại).
2. Tuần 3–6: chuyển ba script gây sự cố trước (xoá thư mục, script dùng output kubectl, deploy 12 VM), mỗi script giữ
   giao diện cũ qua một wrapper Bash một dòng gọi olistctl để crontab và runbook không phải đổi cùng lúc.
3. Tuần 7–16: chuyển backup/restore và xoay secret, kèm test restore tự động; đào tạo cặp cho người chỉ viết Bash.
4. Tuần 17–24: rà các script còn lại; script ổn định, ngắn, ít đổi thì giữ Bash và thêm vào danh sách được phép.

## 6. Rủi ro và đánh đổi

- Phụ thuộc Python trên laptop và CI lệch phiên bản: khoá bằng uv lockfile, CI chạy đúng phiên bản đó.
- Chuyển đổi kéo dài làm tồn tại hai bản cùng chức năng: mỗi script chuyển xong thì xoá bản Bash trong cùng PR.
- Người trực chưa quen olistctl lúc sự cố: runbook ghi cả lệnh olistctl và lệnh tay tương đương trong 3 tháng đầu.
- Python hệ thống trên VM thay đổi khi nâng Ubuntu: phần chạy trên VM chỉ dùng thư viện chuẩn và có test trên 3.12 và
  3.13.

## 7. Khi nào xem lại quyết định

- Số VM vượt khoảng 50 hoặc cần chạy trên máy không có Python (container distroless, thiết bị biên): cân nhắc Go cho
  phần agent.
- Thời gian khởi động olistctl trở thành vấn đề (gọi hàng nghìn lần mỗi giờ từ automation khác).
- Phần lớn việc chuyển lên Kubernetes Operator hoặc GitOps (module 11–12): khi đó nhiều chức năng của olistctl không
  còn cần.
```

## Quyết định cần cân nhắc

- **Go có đáng không?** Go thắng ở phân phối (một binary, không runtime), hiệu năng khởi động, chạy song song
  (goroutine) và là ngôn ngữ của hệ sinh thái Kubernetes (operator, plugin `kubectl`). Thua ở tốc độ viết cho việc
  nhỏ, sửa nóng (phải build), và ở đây chỉ một người biết. Hợp lý khi viết agent chạy trên hàng trăm máy, operator
  Kubernetes, hay công cụ phát hành cho người ngoài team.
- **Python có sẵn trên VM là con dao hai lưỡi.** Python hệ thống thuộc về distro: đừng `pip install` vào đó (PEP 668
  chặn, và đúng vậy). Phần chạy trên VM dùng thư viện chuẩn; phần cần thư viện chạy từ laptop hoặc CI.
- **Viết lại tất cả là bẫy.** Script ổn định, ngắn, ít đổi không có lý do để chuyển; chi phí chuyển và rủi ro hành vi
  khác đi lớn hơn lợi ích.
- **Ngôn ngữ không thay được kỷ luật.** Python vẫn có `subprocess.run(..., shell=True)`, vẫn có thể bỏ qua exit code.
  ADR tốt nêu kèm quy tắc (lint, review, test bắt buộc).
- **Node, Ruby, Rust, PowerShell** đều có chỗ dùng (bảng ở mục 7 của lý thuyết); ADR tốt loại chúng bằng lý do gắn với
  tình huống, không bỏ qua.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Ràng buộc | 15 | Tách bắt buộc và nên có; gắn ba sự cố với ba lớp lỗi cụ thể |
| So sánh | 20 | Ít nhất Bash, Python, Go; mỗi ô là nhận định cho tình huống này, kiểm chứng được |
| Quyết định | 20 | Thoả mọi ràng buộc bắt buộc; lý do đi từ bảng; nêu cái giá đã chấp nhận |
| Ranh giới | 15 | Nói rõ cái gì giữ Bash và vì sao; có xử lý phần chạy trên VM |
| Kế hoạch | 15 | Từng bước theo rủi ro, giữ giao diện cũ trong lúc chuyển, có mốc thời gian vừa hai quý |
| Rủi ro và xem lại | 15 | Rủi ro thật kèm cách giảm; tín hiệu xem lại đo được |

Từ 70 điểm là đạt. Chọn Bash cho mọi thứ, hoặc một kế hoạch "viết lại tất cả trong một lần", thì tối đa 50 điểm.
