---
title: "Đọc output kết nối khách dán vào ticket"
level: basic
services: []
files:
  - path: starter/classify_conn.py
    note: Bạn viết hàm classify
  - path: tests/samples
    note: 27 output thật ghi trên VM hospital và bank (mỗi tệp một lần chạy)
  - path: tests/labels.json
    note: Nhãn đúng của từng mẫu
  - path: tests/test_classify_conn.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/basic/03-classify-conn -q
---

## Mục tiêu

Nửa số ticket "không kết nối được" bạn nhận ở hiện trường đến kèm một đoạn output dán vội: `curl -v`, `openssl
s_client`, hoặc `getent hosts`. Đọc đúng đoạn đó trong 30 giây quyết định bạn hỏi tiếp ai: IT mạng, đội proxy, đội PKI
hay chính dịch vụ của bạn. Bài này luyện việc đó trên output thật, rồi đóng gói thành một script nhỏ dùng lại được khi
phân loại hàng loạt ticket.

## Đề bài

Viết `starter/classify_conn.py` (Python 3.12, chỉ thư viện chuẩn): `python classify_conn.py <tệp>` in ra **đúng một
dòng** là tên loại, thoát `0`. Tệp có dòng đầu `$ <lệnh khách đã gõ>`, các dòng sau là stdout+stderr nguyên văn (khách
không gửi mã thoát). Tám loại:

| Loại | Nghĩa (nhìn từ máy chạy lệnh) |
| --- | --- |
| `dns` | Không đổi được tên máy thành địa chỉ: máy không có resolver dùng được hoặc resolver không biết tên đó |
| `route` | Máy không có đường gửi gói tới đích: không có route/gateway tới mạng đó, hoặc máy đích cùng subnet không trả lời |
| `refused` | Tới được máy đích nhưng không có tiến trình nào nghe cổng đó (máy đích chủ động từ chối) |
| `timeout` | Đã gửi đi nhưng không nhận được trả lời trong thời gian chờ (gói bị bỏ dọc đường, đích hay proxy treo) |
| `tls-ca` | Kết nối TLS lên, nhưng chuỗi chứng chỉ server đưa ra không dẫn về CA mà máy này tin |
| `tls-hostname` | Chuỗi chứng chỉ được tin, nhưng chứng chỉ không cấp cho đúng tên/địa chỉ đang gọi |
| `proxy-auth` | Proxy ở giữa đòi xác thực (chưa gửi hoặc gửi sai thông tin đăng nhập proxy) |
| `ok` | Không có lỗi ở tầng kết nối/TLS/proxy (có thể vẫn có lỗi ứng dụng phía sau) |

Mẫu trong `tests/samples/` là output thật, ghi ngày 2026-11-11 bằng `tests/capture_samples.py` trên VM `hospital`
(Ubuntu 20.04, curl 7.68, OpenSSL 1.1.1f, proxy mitmproxy có TLS inspection mà CA chưa được trust) và `bank` (Rocky 8,
egress `none`). Ba nhóm mẫu dựng thêm điều kiện để lỗi xuất hiện, vẫn là chương trình thật: server TLS nội bộ là
`openssl s_server` trong VM với CA tự tạo của lab; proxy đòi xác thực là mitmproxy 12.2.3 chạy `--proxyauth` đặt ở
đúng địa chỉ proxy của bệnh viện; đích "treo" là địa chỉ `10.255.255.1` mà proxy không với tới.

## Tiêu chí đạt

- `test_labels_cover_samples`: nhãn có cho mọi mẫu (kiểm bộ dữ liệu, không kiểm bài của bạn).
- `test_recorded_output` (27 ca): loại bạn in ra nằm trong nhãn đúng của mẫu (`tests/labels.json`).
- `test_other_customer_same_errors`: cùng 27 output nhưng tên máy, địa chỉ IP, cổng và user proxy được đổi ngẫu nhiên
  mỗi lần chạy (như cùng lỗi đó ở một khách khác), tên tệp cũng ngẫu nhiên; mọi ca vẫn phải đúng loại.
- Mỗi lần chạy script ≤ 20 s, stdout đúng một dòng.

## Gợi ý

### Gợi ý 1

Đọc mẫu bằng mắt trước khi viết dòng code nào: với mỗi tệp, tìm dòng cho biết kết nối đi tới **đâu** (đích hay proxy) và
dừng ở **bước** nào (phân giải tên, mở TCP, CONNECT qua proxy, bắt tay TLS, kiểm chứng chỉ, HTTP).

### Gợi ý 2

Một output có thể chứa dấu vết của nhiều bước. Bước sau chỉ xảy ra khi bước trước đã qua, nên thứ tự bạn kiểm quan
trọng. Có mẫu thoát `0` mà vẫn là lỗi, có mẫu không in gì cả.

### Gợi ý 3

Số trong output (errno, mã curl) không phải lúc nào cũng nói đúng điều bạn nghĩ; đối chiếu với câu chữ đi kèm.
