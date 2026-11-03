---
title: Đề nghị mạng và chứng chỉ gửi IT/An ninh bệnh viện
level: advanced
services: []
files:
  - path: starter/network-request.md
    note: Khung đề nghị 6 phần
run: []
---

## Mục tiêu

Sau proxy soi TLS, "cho em ra internet" là câu IT không bao giờ duyệt. Thứ được duyệt là một đề nghị cụ thể: đi tới
**đâu**, để làm **gì**, bao lâu một lần, dung lượng bao nhiêu, cần IT/An ninh làm gì, và rủi ro nào ai chấp nhận. Bài này
viết đề nghị đó cho bệnh viện, kèm phần quan trọng nhất mà IT hay quên: CA của proxy phải được tin ở **những chỗ nào** để
mọi thứ chạy mà không ai tắt kiểm chứng chỉ.

## Đề bài

Bệnh viện Đa khoa Sông Hồng (hư cấu, máy giống hồ sơ `hospital`): Ubuntu 20.04, Docker `docker.io` 26, ra ngoài chỉ qua
proxy `proxy.benhvien.internal:3128` có TLS inspection bằng "BV Sông Hồng Root CA". Chính sách của chị Hoa (An ninh):

- Mặc định mọi HTTPS đều bị soi. Bỏ soi (bypass) cho một tên miền phải có lý do, có hạn, và được Ban giám đốc ký.
- Mở một tên miền mới qua proxy (vẫn bị soi) chỉ cần An ninh duyệt, mất ~3 ngày làm việc.
- Máy chủ trong vùng bệnh án không bao giờ ra internet; chỉ máy "cầu nối" `bv-build-01` (vùng DMZ nội bộ) được qua proxy.

Việc của bạn trong 3 tháng tới:

| Việc | Cần gì |
| --- | --- |
| Cài và nâng cấp `quillo` (mỗi tháng một bản, ~1,1 GB) lên `bv-app-01` trong vùng bệnh án | Bundle offline, qua USB/MFT như bài intermediate 02 |
| Team dữ liệu của bệnh viện dựng image connector trên `bv-build-01` (bài intermediate 01): `FROM python:3.12-slim`, `pip install` từ PyPI | Docker Hub, PyPI |
| Thử model lớn hơn (`llm-medium`, ~1,1 GB, Hugging Face) trước khi đóng vào bundle | Hugging Face |
| Bạn hỗ trợ từ xa khi có sự cố | Chưa rõ: bệnh viện chưa có kênh nào |

Viết `starter/network-request.md` gửi chị Hoa và anh Phong (quản trị hệ thống). Bài không có test; tự chấm theo rubric,
đạt đủ 8 mục, rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| P1 | Tóm tắt ≤ 6 dòng: xin gì, cho máy nào, không xin gì, cần duyệt trước ngày nào |
| P2 | Bảng đích: tên miền **cụ thể** (không wildcard rộng kiểu `*.com`), cổng, máy nguồn, mục đích, tần suất, dung lượng ước tính, thời hạn; đủ cho các việc trong đề (kể cả tên miền phụ thật sự được dùng khi kéo image và tải gói) |
| P3 | Với mỗi đích: đề nghị **soi + tin CA** hay **bypass** hay **không cần mạng (offline)**, có lý do; mặc định là soi, bypass chỉ khi có lý do kỹ thuật cụ thể |
| P4 | Danh sách chỗ phải tin CA trên `bv-build-01` và trong image, nêu đúng cơ chế từng chỗ (trust store hệ thống, Docker daemon, trust store trong image, Python `requests`/`certifi`, pip), ai làm, kiểm thế nào |
| P5 | Cam kết không tắt kiểm chứng chỉ ở đâu, kèm cách An ninh tự kiểm được cam kết đó |
| P6 | `bv-app-01` (vùng bệnh án) không cần ra internet: luồng cài/nâng cấp offline được mô tả, kể cả cách kiểm toàn vẹn |
| P7 | Hỗ trợ từ xa: đề xuất có kiểm soát (ai bật, ghi lại, thời hạn) hoặc lý do không cần; không đề xuất đường hầm tự dựng |
| P8 | Rủi ro và ai chấp nhận; cách thu hồi (đóng tên miền khi xong việc); ít nhất 3 câu hỏi cho IT/An ninh |

## Tiêu chí đạt

- `network-request.md` đạt đủ P1–P8 khi tự chấm từng mục.
- Mọi tên miền trong bảng là tên thật mà công cụ dùng (kiểm bằng log proxy hoặc `curl -v` ở máy có mạng), không có tên
  đoán.

## Gợi ý

### Gợi ý 1

Chạy thử từng việc trên máy có mạng sau một proxy bạn xem được log (mitmproxy của lab ghi mọi kết nối) và ghi lại
**mọi** tên miền xuất hiện, không chỉ tên bạn gõ. Kéo một image và cài một gói đều đi qua nhiều tên miền hơn bạn nghĩ.

### Gợi ý 2

Hỏi cho từng việc: việc này có thật sự cần mạng ở **máy đó** không, hay làm ở văn phòng rồi mang vào được?

### Gợi ý 3

Bypass có một cái giá ít ai nói: An ninh mất khả năng nhìn vào lưu lượng đó. Lý do "công cụ của chúng em không chạy" chỉ
đứng được khi bạn chỉ ra được công cụ nào, vì sao không cấu hình CA được (vd. ghim chứng chỉ).
