# Lời giải: đọc output dig khi sự cố

Code đầy đủ ở `dig_triage.py` cạnh tệp này.

## Cách làm

1. **Ba regex cho phần đầu**: dòng `->>HEADER<<-` lấy `status`, dòng `;; flags:` lấy danh sách cờ (`aa`, `rd`, `ra`),
   dòng `; EDE:` lấy mã lỗi mở rộng. Câu hỏi nằm ở dòng duy nhất của `QUESTION SECTION`.
2. **Một hàm `parse_record`** chuẩn hoá mọi dòng bản ghi: tên chữ thường, bỏ dấu chấm cuối, rdata gộp khoảng trắng. Mọi
   so sánh tên sau đó đều đúng mà không cần nghĩ tới hoa thường.
3. **`kind` đi theo thứ tự trong đề.** Chỗ dễ sai: `NOERROR` không có câu trả lời có ba nghĩa khác nhau (NODATA, referral,
   hoặc chỉ có CNAME tới một tên không có loại bản ghi đó, cũng là NODATA).
4. **TTL phủ định** lấy từ SOA trong `AUTHORITY`: `min(TTL của SOA, MINIMUM)` theo RFC 2308. Đây là thời gian resolver
   nhớ câu "không có".

## Từng fixture nói gì

| Fixture | Kết luận cho người trực ca |
| --- | --- |
| `cname_answer.txt` | Bình thường. TTL hiệu lực 20 giây vì CDN giữ TTL thấp ở bản ghi A, dù CNAME có TTL gần 1 giờ. Muốn đổi CDN thì CNAME mới là thứ bị cache lâu |
| `nxdomain.txt` | `api-v2` không tồn tại. Tạo xong bản ghi thì resolver đã hỏi trước đó vẫn trả NXDOMAIN tới 5 phút |
| `nodata_aaaa.txt` | Tên có, nhưng không có IPv6. Không phải lỗi, trừ khi client chỉ có IPv6. Câu "không có" được nhớ 60 giây |
| `cname_to_nxdomain.txt` | Dangling CNAME: `promo` trỏ tới trang chiến dịch đã xoá. Ngoài lỗi, đây là rủi ro **subdomain takeover**: ai tạo lại `black-friday-2025` trên nền tảng đó sẽ chiếm `promo.olist-shop.com.br` |
| `servfail_dnssec.txt` | EDE 6 (DNSSEC Bogus): DS ở zone cha không khớp DNSKEY của zone. Lỗi ở phía chủ tên miền (đổi khoá hoặc đổi nhà cung cấp DNS mà không cập nhật DS ở registrar), không phải ở resolver. Mọi resolver có validate DNSSEC đều SERVFAIL |
| `refused.txt` | Resolver nội bộ từ chối truy vấn đệ quy cho nguồn này (ACL), hoặc bạn đang hỏi nhầm một authoritative server. Kiểm `/etc/resolv.conf` và ACL `allow-recursion` |
| `referral_glue_ok.txt` | Delegation lành mạnh: NS nằm trong zone con và có glue |
| `referral_missing_glue.txt` | `ns2` nằm trong zone con mà zone cha không có glue: resolver không thể tìm IP của `ns2` (muốn hỏi nó phải biết IP, muốn biết IP phải hỏi nó). Còn `ns1` (glue AAAA) và `ns.provider-dns.example` nên tên miền vẫn chạy, nhưng mất dự phòng. Sửa ở registrar: khai báo glue (host record) cho `ns2` |
| `mx_authoritative.txt` | Câu trả lời từ authoritative (`aa`), không qua cache: TTL là giá trị gốc 3600 |

## Mở rộng

- `dig +trace <tên>` đi từ root xuống, in referral của từng tầng: chỗ chuỗi đứt là chỗ có lỗi (lame delegation, thiếu glue,
  DS sai).
- `dig +norecurse @<ns> <tên>` hỏi thẳng authoritative để loại bỏ cache khỏi phương trình. So sánh với `dig @1.1.1.1` và
  `dig @8.8.8.8` để biết thay đổi đã lan tới đâu.
