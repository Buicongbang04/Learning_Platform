---
title: Báo cáo khoảng cách gửi IT bệnh viện
level: advanced
services: []
files:
  - path: starter/gap-report.md
    note: Khung báo cáo, viết thành tài liệu gửi khách
run: []
---

## Mục tiêu

Biến kết quả survey, preflight và các kiểm tra tại chỗ thành **một trang** IT khách đọc xong biết phải làm gì, trước
ngày nào, và vì sao. Đây là tài liệu quyết định ngày cài có giữ được hay không.

## Đề bài

Khách là Bệnh viện Đa khoa Sông Hồng (hư cấu, như bài kế hoạch tuần đầu ở module 00). Hôm nay thứ Tư 04/11/2026. Ngày
cài `quillo` đã hẹn là **cửa sổ bảo trì thứ Năm 12/11/2026, 20:00–22:00**; mọi thay đổi hệ thống của bệnh viện chỉ làm
trong cửa sổ thứ Năm hằng tuần. Người nhận: anh Tuấn (IT hạ tầng), đồng gửi chị Hà (An toàn thông tin).

Anh Tuấn đã chạy bộ kiểm tra của bạn trên máy sẽ cài, `srv-ai01`:

```json
{"os_id": "ubuntu", "os_version": "20.04", "kernel_major": "5.4", "glibc": "2.31", "cpus": 4, "mem_mb": 15992,
 "disk_free_gb_max": 6.0, "gpu": null, "proxy_url": "http://10.20.0.5:3128", "sudo": true, "selinux": "n/a",
 "runtime": "docker", "egress": "proxy"}
```

```text
$ python preflight.py srv-ai01.json REQUIREMENTS.yaml        (mã thoát 1)
disk    blocker  Còn trống 6.0 GiB ở /, cần tối thiểu 10 GiB
egress  warning  Ra internet qua proxy http://10.20.0.5:3128: cần cấu hình proxy cho runtime và CA nội bộ
$ sh check_ports.sh 18080 22
18080 busy unknown
22 busy unknown
$ sh storage_report.sh
{"runtime": "docker", "data_root": "/var/lib/docker", "data_mount": "/", "data_free_gb": 6.02, "inodes_free_pct": 92}
```

Thêm từ support bundle anh Tuấn gửi: `docker version` server `26.1.3`; `docker compose version` báo
`'compose' is not a docker command`; `timedatectl` báo `System clock synchronized: no`; `curl https://pypi.org` qua proxy
lỗi `SSL certificate problem: unable to get local issuer certificate`.

Viết `starter/gap-report.md` thành báo cáo khoảng cách gửi anh Tuấn và chị Hà. Bài không có test; tự chấm theo rubric
dưới đây (đạt đủ 10 mục mới tính là xong), rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| R1 | Mở đầu bằng kết luận tối đa 3 câu: hiện **chưa** cài được, cần gì, và mốc ngày cụ thể để giữ cửa sổ 12/11 |
| R2 | Có một bảng tóm tắt: hạng mục, hiện trạng (số đo), yêu cầu, mức, ai làm, hạn |
| R3 | Mỗi việc chặn có bằng chứng đo được (con số và lấy từ đâu), yêu cầu cụ thể (con số, đường dẫn), người làm và hạn: việc thay đổi hệ thống xếp vào cửa sổ 05/11, hoặc đầu cửa sổ 12/11 kèm điểm quyết định có cài tiếp hay dời; việc không thay đổi hệ thống có hạn trước 12/11 |
| R4 | Đĩa: đo ở đúng thư mục dữ liệu của Docker, đưa ít nhất hai phương án cho IT chọn, không đề nghị dọn/xoá dữ liệu của bệnh viện |
| R5 | Cổng 18080: nói rõ survey không thấy tiến trình nào giữ cổng, đưa đúng lệnh để IT kiểm, và có phương án thay (đổi cổng sản phẩm) để IT quyết |
| R6 | Proxy và CA đánh giá đúng mức: bản cài là bundle offline nên ngày cài không phụ thuộc internet; phần cần cho sau này thì tách việc IT cấp (tệp CA nội bộ dạng PEM, địa chỉ được phép qua proxy) khỏi việc FDE tự làm (cấu hình proxy/CA cho Docker) |
| R7 | Không đề nghị nới bảo mật: không tắt TLS inspection, không `verify=False`/`--insecure`, không xin `chmod 777` hay cấp quyền rộng hơn cần |
| R8 | Có phần "việc phía chúng tôi" cho những gì FDE tự lo (plugin compose đi kèm bundle, kiểm phiên bản Docker đạt) để IT không phải làm thừa |
| R9 | Có mục câu hỏi hoặc điểm cần xác nhận mà survey không trả lời được (vd. đồng hồ chưa đồng bộ: NTP server nội bộ nào) |
| R10 | Viết cho IT khách: không dùng tên hàm/tệp nội bộ làm thuật ngữ, "blocker" nếu dùng thì giải thích, không đổ lỗi; tổng cộng không quá 60 dòng Markdown |

## Tiêu chí đạt

- `gap-report.md` đạt đủ 10 mục R1–R10 khi tự chấm từng mục.
- Mọi con số trong báo cáo khớp dữ liệu đề cho; mọi việc thay đổi hệ thống rơi vào một cửa sổ thứ Năm (05/11 hoặc
  12/11), mọi việc khác có hạn trước 12/11/2026.

## Gợi ý

### Gợi ý 1

Viết bảng tóm tắt trước rồi mới viết lời: nếu bảng chưa trả lời được "ai làm gì trước ngày nào" thì lời văn cũng không.

### Gợi ý 2

Giữa hôm nay và 12/11 chỉ có một cửa sổ thứ Năm khác, và nó là ngày mai. Nghĩ xem IT có kịp không, và nếu không kịp thì
cửa sổ 12/11 phải chia thế nào.

### Gợi ý 3

IT đọc báo cáo của nhà cung cấp để tìm hai thứ: việc của họ là gì, và có gì làm họ phải đi giải trình với An toàn thông
tin không.
