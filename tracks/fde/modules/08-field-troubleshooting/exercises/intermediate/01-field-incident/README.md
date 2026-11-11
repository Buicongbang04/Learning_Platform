---
title: "Hiện trường: sự cố ở bệnh viện, chỉ có bundle và vài lệnh nhờ khách gõ"
level: intermediate
services: []
files:
  - path: starter/incident.yaml
    note: Báo cáo chẩn đoán của bạn
  - path: tools/ask_customer.py
    note: Nhờ IT bệnh viện gõ một lệnh trên máy của họ (trong lúc cảnh đang chạy)
  - path: tools/quillo-support.sh
    note: Support bundle của quillo (đội sản phẩm phát hành), IT khách chạy để gửi bạn
  - path: tests/test_field_incident.py
    note: Không sửa; chạy thẳng tệp này để dựng cảnh điều tra
  - path: tests/fieldkit.py
    note: Không sửa; quy tắc lệnh khách đồng ý gõ nằm ở đây và ở README này
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare hospital
  - nice -n 15 uv run python -m fdekit derive 08-field-troubleshooting-hospital
  - uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/01-field-incident -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Bệnh viện chạy quillo 1.0.0 trên máy `hospital` (Ubuntu 20.04, Docker, compose ở `/home/fde/quillo-1.0.0`) từ hai tháng
nay. Bạn không có VPN vào mạng bệnh viện. Sáng nay IT bệnh viện mở ticket, gửi kèm support bundle (họ chạy
`quillo-support.sh` như hướng dẫn cài đặt), và đồng ý gõ giúp **vài** lệnh chỉ đọc qua cuộc gọi. Bạn cần trả lời: chuyện
gì đang xảy ra, vì sao, bằng chứng đâu, và ai phải làm gì tiếp theo. Có nhiều sự cố đã từng xảy ra ở khách này; mỗi lần
dựng cảnh, test chọn ngẫu nhiên một sự cố theo seed.

## Đề bài

**Bước 1: dựng cảnh và điều tra.** Từ gốc repo:

```bash
PYTHONPATH=. uv run python tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/01-field-incident/tests/test_field_incident.py
# --seed N để dựng lại đúng một cảnh
```

Lệnh in **seed**, ticket của IT bệnh viện, nơi lưu bundle (`.fde-lab/08-field-incident/bundle/` đã giải nén và
`bundle.tar.gz`), rồi giữ máy của khách chạy cho tới khi bạn nhấn Enter (~2 phút để dựng). Trong lúc đó, nhờ khách gõ
lệnh bằng:

```bash
uv run python tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/01-field-incident/tools/ask_customer.py "df -h"
```

IT bệnh viện gõ lệnh bằng tài khoản vận hành của họ (`fde`, có sudo), trong thư mục cài quillo, và dán lại output **đã
che secret**. Họ chỉ gõ:

- **một** lệnh đơn: không `|`, `;`, `&`, `>`, `<`, `$`, backtick, `\`; có thể bắt đầu bằng `sudo`;
- chương trình chỉ đọc: `df`, `du`, `free`, `uptime`, `uname`, `ps`, `ss`, `getent`, `ls`, `stat`, `cat`, `head`,
  `tail`, `grep`, `wc`, `find`, `id`, `date`, `hostname`, `lsblk`, `findmnt`, `dmesg`, `ip`, `journalctl`, `systemctl`,
  `docker`, `curl`, `openssl`, `nproc`, `mount`;
- với giới hạn: `docker` chỉ `ps`, `logs`, `inspect`, `images`, `info`, `version`, `stats --no-stream`, `top`, `port`,
  `events --until …`, `compose ps|logs|config|images|top|ls|version|port`, `network|volume|image|container ls/inspect`,
  `system df|info`, không `-f`/`--follow`; `systemctl` chỉ `status`, `show`, `is-active`, `is-failed`, `is-enabled`,
  `list-units`, `list-timers`, `cat`; `journalctl` không `-f`, `--vacuum…`, `--rotate`, `--flush`; `ip` chỉ xem;
  `find` không `-exec`, `-delete`, `-fprint…`; `curl` chỉ GET/HEAD tới `127.0.0.1`/`localhost`, không ghi tệp, không
  gửi dữ liệu; `openssl` chỉ `s_client`, `x509`, `version` và không ghi tệp; `ss` không `-K`; `mount` không đối số;
  `hostname` chỉ cờ xem; `tail`/`dmesg`/`journalctl`/`docker … logs` không theo dõi (kể cả cờ gộp như `-tf`),
  `dmesg` không xoá; `grep` không đệ quy; `date` không đặt giờ (`-s`, `--set`); `docker compose` không `-o`/`--output`; `journalctl`
  không `--setup-keys`, `--update-catalog`, `--new-id128`; `curl` chỉ nhận đích dạng `http(s)://127.0.0.1…` hoặc
  `http(s)://localhost…`, không `--resolve`, `-x`/`--proxy`, `--connect-to`; `grep` không `-d recurse`;
- không mở đường dẫn có `.env`, `.ssh`, `oidc`, `shadow`, `sudoers`, `secret`, `environ`, `private`, `*.key`, `*.pem`,
  `.bash_history` (xét mọi đối số của lệnh).

Mỗi lệnh chạy tối đa 30 s. Trước khi dán output, khách che token quản trị và mật khẩu database của bản cài quillo.
**Mỗi seed khách gõ giúp tối đa 4 lệnh**, tính cả các lần dựng lại cảnh với cùng seed; lệnh thứ 5 bị từ chối (lệnh bị từ
chối vì sai quy tắc không tính). Mọi lệnh bạn nhờ được ghi kèm seed vào `.fde-lab/08-field-incident/ask-log.jsonl` (chỉ
ghi nối, không bị xoá khi dựng lại cảnh); muốn điều tra lại từ đầu thì dùng một seed khác.

**Bước 2: nộp và chấm.** Viết `starter/incident.yaml` cho đúng cảnh của seed đó:

```yaml
cause: <một nguyên nhân trong bảng dưới>
summary: <đoạn giải thích cơ chế: vì sao nguyên nhân này sinh ra đúng triệu chứng trong ticket, ≥ 40 ký tự>
evidence:                        # 2–6 mục
  - source: bundle:<đường dẫn tệp trong bundle, vd. quillo/logs/api.log>
    text: <đoạn trích ≥ 6 ký tự, nằm nguyên trong MỘT dòng của tệp đó>
  - source: customer:<số thứ tự lệnh trong customer_commands, đếm từ 1>
    text: <đoạn trích nằm nguyên trong một dòng output của lệnh đó>
customer_commands:               # tối đa 4 lệnh, theo đúng quy tắc ở trên
  - <lệnh>
next_steps:                      # ít nhất 1: ai làm gì, kiểm lại thế nào
  - <việc>
```

| `cause` | Nghĩa |
| --- | --- |
| `disk-full` | Hết chỗ (block hoặc inode) trên filesystem mà một thành phần cần ghi |
| `memory-pressure` | Thiếu RAM: tiến trình bị OOM kill, swap/page cache thrash |
| `dns` | Không phân giải được tên cần thiết |
| `firewall-blocked` | Kết nối bị chặn hoặc bỏ gói giữa hai thành phần |
| `proxy-misrouting` | Cấu hình proxy (có, thiếu hay sai) làm một kết nối không đi đúng đường cần đi |
| `tls-trust` | Chứng chỉ không được tin (CA chưa trust, sai tên, hết hạn) |
| `credentials` | Mật khẩu, token, khoá sai hoặc hết hạn |
| `permission` | Quyền tệp, SELinux, `noexec`, user không đủ quyền |
| `resource-limit` | Giới hạn của OS/runtime: `ulimit`, quota, giới hạn tiến trình/kết nối |
| `config-error` | Cấu hình sai (sản phẩm, runtime, hệ thống) không thuộc các loại trên |
| `product-bug` | Lỗi trong mã của sản phẩm, tái hiện được trên máy sạch |

Rồi chấm bằng đúng seed của cảnh bạn đã điều tra:

```bash
FDE_08_INCIDENT_SEED=<seed> uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/01-field-incident -q
```

Test boot lại máy của bệnh viện, dựng lại **đúng sự cố của seed đó** (cùng nguyên nhân, cùng diễn biến), lấy bundle mới
bằng `quillo-support.sh`, chạy lại từng lệnh trong `customer_commands` qua đúng kênh của `ask_customer.py`, rồi chấm.
Bundle và output dựng lại khác lần bạn điều tra ở những phần đổi theo lần chạy (thời gian, PID, id container, cổng,
kích thước, tên tài liệu), nên đoạn trích bằng chứng chỉ được chứa phần ổn định của dòng. Chưa đặt
`FDE_08_INCIDENT_SEED` thì test skip. Mỗi lần chấm ~50 s trên máy của repo.

## Tiêu chí đạt

`test_incident_report[seed]`:

- Nhật ký `.fde-lab/08-field-incident/ask-log.jsonl` của seed đó có **không quá 4** lệnh khách đã gõ, và **mọi** lệnh
  trong `customer_commands` có trong nhật ký đó (nguyên văn): bạn chỉ dẫn được lệnh mình đã thật sự nhờ khách gõ.
- `incident.yaml` đúng định dạng: `cause` thuộc bảng trên, `summary` ≥ 40 ký tự, `next_steps` là danh sách chuỗi
  không rỗng, `customer_commands` ≤ 4 lệnh và lệnh nào cũng được khách chấp nhận theo quy tắc trên, `evidence` có 2–6
  mục, mỗi mục có `source` dạng `bundle:<tệp>` hoặc `customer:<số>` trỏ tới một lệnh có trong `customer_commands`,
  `text` ≥ 6 ký tự trên một dòng.
- Trên cảnh dựng lại: mỗi `text` nằm nguyên trong một dòng của nguồn (tệp bundle, hoặc output lệnh đã che secret).
- `cause` giải thích được sự cố của seed đó (mỗi sự cố có tập nguyên nhân chấp nhận được; với vài sự cố có nhiều hơn một
  cách gọi tên hợp lý).
- Ít nhất một bằng chứng là **dấu vết trực tiếp của nguyên nhân** (thứ mà khi nguyên nhân biến mất thì nó cũng biến
  mất), không chỉ là triệu chứng (mã lỗi HTTP, trạng thái health, "không có trích dẫn"). Test so phần dấu vết trong
  đoạn trích theo nguồn:
  - dấu vết về **tài nguyên** (mức dùng đĩa, lỗi hết chỗ…) được tính từ tệp tài nguyên hay log của dịch vụ liên quan
    trong bundle, hoặc từ output lệnh nhờ khách gõ;
  - dấu vết về **cấu hình** (biến môi trường, cấu hình của runtime…) chỉ được tính khi đến từ output lệnh nhờ khách gõ,
    và không tính cấu hình chung của cả máy vốn đã có sẵn ở khách này dù có sự cố hay không (vd. biến proxy hệ thống
    viết trong `/etc/environment` dạng `tên="giá trị"`); tên biến/khoá cấu hình được so không phân biệt hoa thường
    (`http_proxy` hay `HTTP_PROXY`), các dấu vết khác so đúng chữ;
  - không tính phần dấu vết mà chính câu lệnh của bạn đã chứa và output chỉ in lại (vd. thông báo lỗi lặp lại tham số
    bạn gõ), dù đoạn trích dài hơn phần đó. Đường dẫn tệp/thư mục (bắt đầu bằng `/`) là ngoại lệ: trích
    `/đường/dẫn` từ output `du`, `ls`, `df` có tham số chính là đường dẫn đó vẫn được tính. Hệ quả: dòng log hãy trích từ
    log trong bundle, không từ output `grep "<lỗi>" …` nhờ khách gõ; và đừng đưa tên biến/khoá vào câu lệnh
    (`grep -i proxy …`) khi muốn dùng output làm dấu vết cấu hình: dùng lệnh in cả cấu hình (vd. `docker inspect`,
    `cat <tệp cấu hình>`).

## Gợi ý

### Gợi ý 1

Đọc ticket hai lần: khách nói gì **vẫn chạy**, gì **không chạy**, từ lúc nào, sau việc gì? Rồi mở bundle với đúng những
câu hỏi đó, trước khi mở log dài nhất.

### Gợi ý 2

Trước khi nhờ khách gõ, viết ra hai giả thuyết và lệnh nào phân biệt được chúng. Lệnh nào bạn không nói trước được kết
quả sẽ thay đổi kết luận thế nào thì đừng nhờ.

### Gợi ý 3

Bundle là ảnh chụp những gì công cụ thu thập **được thiết kế để thu**. Thứ quyết định nằm ngoài danh sách đó thì phải hỏi
đúng thứ đó.
