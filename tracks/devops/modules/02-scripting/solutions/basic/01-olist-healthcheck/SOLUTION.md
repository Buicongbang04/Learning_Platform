# Lời giải: healthcheck Olist Shop theo hợp đồng exit code của Nagios

Script đầy đủ ở `healthcheck.sh` cạnh tệp này.

## Cách làm

1. **Đọc option bằng `getopts ":u:t:"`.** Dấu `:` đầu chuỗi bật chế độ im lặng: option lạ thành `?`, thiếu giá trị
   thành `:`, cả hai rơi vào nhánh `*) usage`. Sau vòng lặp, `shift $((OPTIND - 1))` và kiểm `$# -eq 0` để bắt tham số
   thừa. Giá trị mặc định đặt **trước** `getopts`, nên `-u` tự nhiên thắng biến môi trường.
2. **Bắt mã lỗi của curl mà vẫn giữ `set -e`.** `code="$(curl ...)" || rc=$?`: lệnh đứng bên trái `||` không kích hoạt
   `errexit`. Viết `code="$(curl ...)"` trơn thì curl lỗi làm script chết với exit `7` hoặc `28`, hệ thống giám sát hiểu
   là UNKNOWN (exit lớn hơn 3) hoặc sai nghĩa hoàn toàn.
3. **Không dùng `curl -f`.** Cần body của `503` để biết thành phần nào hỏng. `-w '%{http_code}'` cho mã HTTP, `-o` ghi
   body vào tệp tạm, `trap ... EXIT` xoá tệp đó ở mọi đường thoát.
4. **Thoát sớm.** `/healthz` hỏng thì không gọi `/readyz`: request thứ hai không thêm thông tin, chỉ kéo dài thời gian
   check (hệ thống giám sát cũng có timeout riêng, thường 10–60 giây).
5. **Mọi đường không lường trước là UNKNOWN.** `jq` lỗi (body không phải JSON), trường thiếu (`null`), giá trị lạ, hay
   mã HTTP trái với nội dung đều đi vào một hàm `unknown`. Một check báo OK khi không hiểu response nguy hiểm hơn một
   check báo UNKNOWN.

## Exit code là hợp đồng với người gọi

| Người gọi | Quy ước | Ghi chú |
| --- | --- | --- |
| Shell, `make`, CI | `0` thành công, khác `0` thất bại; `2` thường là lỗi cách dùng | Bash builtins, grep (`2` = lỗi), diff |
| Nagios/Icinga/Zabbix agent | `0` OK, `1` WARNING, `2` CRITICAL, `3` UNKNOWN | Lỗi cách dùng cũng là `3` |
| systemd `ExecStart` | Khác `0` là failed; `SuccessExitStatus=` để coi mã khác là thành công | `Restart=on-failure` dựa vào đây |
| Docker `HEALTHCHECK` | `0` healthy, `1` unhealthy, `2` để dành | Mã khác `0`/`1` không nên dùng |
| Kubernetes `exec` probe | `0` thành công, khác `0` thất bại | Probe HTTP thì `200–399` là thành công |

Cùng một script có thể phải phục vụ hai người gọi. Khi đó viết lõi một lần và bọc mỏng cho từng nơi, đừng ép một
bảng mã lên người gọi kia: dùng script này làm Docker `HEALTHCHECK` cần ánh xạ WARNING thành healthy hay unhealthy,
và đó là quyết định về **readiness** (Kubernetes rút pod khỏi Service) khác với **liveness** (khởi động lại pod).
Đừng gắn kiểm DB vào liveness probe: DB chập chờn sẽ làm mọi pod restart cùng lúc.

## Lỗi hay gặp

- `set -e` và command substitution: `local code=$(curl ...)` **không** làm script dừng khi curl lỗi, vì exit status là
  của `local` (luôn `0`); shellcheck báo SC2155. Tách `local code` và `code=$(...)`.
- Quên `--max-time`: curl mặc định không có timeout tổng, check treo tới khi hệ thống giám sát giết nó, và bạn nhận
  alert "check timed out" thay cho "API treo".
- Dùng `grep '"db":"ok"'` thay cho `jq`: hỏng ngay khi API đổi định dạng JSON (thêm khoảng trắng, đổi thứ tự).
- Proxy của công ty trong `http_proxy` làm request tới `localhost` đi vòng qua proxy; đặt `NO_PROXY=localhost,127.0.0.1`
  cho môi trường chạy check.
