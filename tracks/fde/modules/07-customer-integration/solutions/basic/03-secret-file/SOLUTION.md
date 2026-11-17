# Lời giải: secret qua tệp, không lộ ở đâu

Lời giải ở `push_report.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/03-secret-file -q
```

Đo 2026-11-11 trên máy của repo: 6 test ~9 s (mỗi ca chờ server giả 1,5 s).

## Bản của đồng nghiệp lộ ở đâu

| Chỗ | Cơ chế | Ai thấy |
| --- | --- | --- |
| `curl -H "Authorization: Bearer <token>"` | Đối số nằm trong `/proc/<pid>/cmdline` suốt thời gian `curl` chạy | **Mọi user** trên máy (`ps aux`), trừ khi `/proc` mount với `hidepid=2`; agent giám sát (EDR, auditd `execve`) ghi lại vĩnh viễn |
| `AUDIT_TOKEN` trong env | `/proc/<pid>/environ` của tiến trình và mọi tiến trình con kế thừa | Cùng user, root; `docker inspect`, `systemctl show`, crash report, `env` trong support bundle |
| `logging.debug("token=%s")` | Ghi thẳng vào tệp log | Ai đọc được log, hệ thống gom log (thường giữ lâu hơn token sống) |
| `check=True` + `CalledProcessError` | Thông báo exception chứa **nguyên argv** ⇒ traceback trên stderr có token | journald, email cron, ticket khách dán lên |
| In thân phản hồi lỗi | Dịch vụ lặp lại token trong thông báo lỗi | Như trên |

## Cách làm

1. **Đọc secret từ tệp, kiểm tệp trước khi tin**: `os.open(..., O_NOFOLLOW)` rồi `fstat` trên chính fd (không kiểm đường
   dẫn rồi mới mở: có khoảng hở TOCTOU); phải là tệp thường, không có bit quyền group/other (giống `ssh` từ chối khoá
   `0644`); bỏ `\r\n` cuối, rỗng ⇒ lỗi cấu hình. Thấy `AUDIT_TOKEN` trong env ⇒ từ chối: im lặng dùng nó là để chính
   sách bị vi phạm mà không ai biết.
2. **Không chương trình con**: `urllib.request` gửi header trong tiến trình. Nếu buộc phải dùng `curl` (vd. cần mTLS hay
   proxy phức tạp), đưa header qua tệp hoặc stdin: `curl -H @/run/secrets/header ...` (curl ≥ 7.55) hoặc `curl --config -`
   với cấu hình qua stdin; không bao giờ qua đối số hay env của tiến trình con.
3. **Bộ lọc log** (`logging.Filter`) thay token bằng `***` trong mọi bản ghi: hàng rào cuối cho dòng log ai đó thêm sau
   này. Không ghi header, không ghi thân phản hồi lỗi.
4. **Bắt lỗi ở biên và tự viết thông báo**: `HTTPError` ⇒ chỉ mã và reason; `URLError`/`OSError`/`HTTPException` ⇒ tên
   lớp lỗi + lý do đã lọc token. Không để exception thoát ra (traceback). Mã thoát phân biệt `1` (vận hành: thử lại sau,
   báo động) và `2` (cấu hình: người phải sửa).

## Biến thể đã thử với test

- Bản starter: lộ qua `cmdline` của `curl`, qua log, qua traceback; ca thiếu `AUDIT_TOKEN_FILE` thoát `1` (KeyError)
  thay vì `2`.
- Bỏ `curl`, truyền token cho tiến trình con Python qua `env={"AUDIT_TOKEN": token}`: không còn trong `cmdline` nhưng
  test vẫn bắt được trong `/proc/<pid>/environ` của tiến trình con.

## Ở khách thật

- `*_FILE` là quy ước của nhiều image chính thức (`POSTGRES_PASSWORD_FILE` của image Postgres), Docker/Compose secrets
  mount vào `/run/secrets/<tên>`, Kubernetes mount Secret thành tệp, Vault Agent/CSI driver ghi tệp và có thể xoay token
  mà không restart (đọc lại tệp mỗi lần gửi thay vì cache cả đời tiến trình).
- Env không phải "kém an toàn tuyệt đối" mà là **dễ rò**: kế thừa sang tiến trình con, bị dump trong crash report, support
  bundle, `docker inspect`. Tệp có quyền, có chủ, có đường dẫn để audit.
- Secret còn có thể rò qua core dump (`ulimit -c`), `strace` của người có quyền và swap; mức đó thuộc chính sách hệ thống
  của khách (`prctl(PR_SET_DUMPABLE, 0)`, `hidepid`), ghi vào câu trả lời questionnaire, không cần tự làm trong script.
