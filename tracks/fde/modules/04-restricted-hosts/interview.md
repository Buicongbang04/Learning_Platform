# Câu hỏi phỏng vấn: máy bị khoá và máy cũ

## 1. Khách nói "máy này không ai có root, kể cả anh". Bạn còn làm được gì, và việc gì bạn sẽ xin?

Phần lớn: cài toàn bộ vào `$HOME` theo XDG (`~/.local/opt/<app>/releases/<bản>`, symlink `current`), chạy dịch vụ bằng
`systemd --user`, container bằng Podman rootless, mở cổng ≥ 1024, đọc journal của chính mình. Thứ thật sự cần IT thường
chỉ vài việc nhỏ, mỗi việc một lệnh: bật linger cho user dịch vụ, thêm subuid/subgid nếu thiếu, mở firewall cho một cổng,
đôi khi một boolean SELinux. Tôi gửi từng việc kèm lệnh, lý do và lệnh để họ tự kiểm sau khi làm, thay vì xin sudo. Một
yêu cầu cụ thể được làm trong ngày; "cho em sudo" ở ngân hàng có khi mất một quý và thường bị từ chối.

## 2. Dịch vụ `systemd --user` của bạn chạy ngon lúc bạn ở đó, sáng hôm sau khách báo nó không chạy. Chuyện gì xảy ra?

Nghi ngờ đầu tiên là linger. User manager mặc định chỉ chạy khi user có phiên đăng nhập; phiên cuối đóng là nó dừng và
dừng luôn mọi unit của user. Kiểm `loginctl show-user <user> -p Linger`; nếu `no` thì `loginctl enable-linger` (tự bật
nếu polkit cho, không thì nhờ IT). Tôi kiểm lại bằng đúng kịch bản của khách: đóng mọi phiên SSH, chờ, đăng nhập lại, so
`MainPID`. Nghi ngờ tiếp theo là unit chỉ `start` mà chưa `enable` (`WantedBy=default.target`), hoặc chạy được nhờ biến môi
trường của shell tương tác mà unit không có.

## 3. Giải thích rootless Podman cho một người chỉ quen Docker.

Không daemon chạy root; mọi container chạy dưới uid của bạn trong một user namespace: root trong container là bạn ở ngoài,
các uid khác ánh xạ sang dải subuid khai trong `/etc/subuid`. Image, container nằm trong `~/.local/share/containers`, của
riêng user đó. Mạng qua slirp4netns/pasta nên không bind cổng < 1024 và hiệu năng mạng thấp hơn một chút. Muốn client kiểu
Docker (compose, SDK) nói chuyện với nó thì bật `podman.socket` của user và đặt `DOCKER_HOST` tới socket trong
`$XDG_RUNTIME_DIR`. Đánh đổi: an toàn hơn hẳn (thoát container chỉ được quyền của một user thường), đổi lại là vài giới hạn
cần biết trước (cổng, cgroup v1, NFS home, restart sau reboot).

## 4. Trên một máy RHEL/Rocky, một tiến trình báo "Permission denied" dù `ls -l` cho thấy quyền đủ. Bạn chẩn đoán thế nào?

Tách DAC và MAC, rồi đi từng lớp. DAC: owner, mode, ACL (`getfacl`), đường dẫn cha (`namei -l`), và với container rootless
nhớ rằng root trong container là uid của tôi ở ngoài, uid khác là dải subuid. Ngoài DAC còn mount (`noexec`, `ro`),
capability, seccomp. Nếu những thứ đó ổn và `getenforce` là Enforcing thì so nhãn: `ls -Z` của tài nguyên và `ps -eZ` của
tiến trình, xem domain đó có hợp với type đó không. Không root thì không đọc được `audit.log`, nên tôi suy từ nhãn, thử giả
thuyết trong lab (không ở khách), rồi sửa ở chỗ hẹp nhất: nhãn của tài nguyên thuộc app, hoặc nhờ IT một boolean hay
`semanage fcontext` cụ thể. Không bao giờ đề xuất `setenforce 0`.

## 5. `:z` và `:Z` khác nhau thế nào, và khi nào chúng nguy hiểm?

Cả hai đổi nhãn SELinux của nguồn bind mount sang `container_file_t`. `:z` là nhãn dùng chung (mọi container đọc được),
`:Z` là nhãn riêng có category MCS của đúng container đó, container khác không đọc được. Nguy hiểm khi nguồn là thư mục
không phải của riêng app: `:Z` lên `$HOME`, `/etc`, `/var/lib/<dịch vụ khác>` đổi nhãn của chúng và làm hỏng dịch vụ
khác (có khi cả SSH nếu đụng `~/.ssh`). Quy tắc của tôi: chỉ đổi nhãn thư mục do bundle tạo ra, nằm trong thư mục của app.

## 6. Khách là ngân hàng, SELinux chặn một việc và bạn không có quyền đọc log audit. Bạn viết gì cho IT?

Một yêu cầu họ trả lời được trong một lượt: máy, user, thời điểm (UTC) tái hiện, lệnh tái hiện, nhãn tiến trình (`ps -eZ`)
và nhãn tệp/cổng liên quan (`ls -Z`), thông báo lỗi nguyên văn; xin họ chạy `ausearch -m AVC,USER_AVC -ts <thời điểm>` và
gửi lại đúng các dòng AVC kèm `audit2why`. Tôi nói trước cách sửa tôi đề xuất (đổi nhãn tệp của app, hoặc một boolean cụ
thể) và vì sao nó hẹp nhất có thể; tôi không xin module policy sinh tự động từ `audit2allow`, vì nó cho phép đúng thứ đang
bị chặn kể cả khi thứ đó sai.

## 7. Khách nói "cài xong rồi nhưng từ máy khác không vào được web". Bạn tách lỗi ứng dụng với lỗi firewall thế nào khi không có root?

Từ hai đầu. Trên máy: `ss -ltn` xem tiến trình nghe đúng cổng và đúng địa chỉ (`127.0.0.1` thì máy khác không bao giờ vào
được), `curl` tới chính IP của máy. Từ máy client: `curl -v`/`nc -vz`. Bị từ chối ngay (`No route to host`,
`Connection refused` dù máy đang nghe) thường là host firewall reject; treo tới timeout là có thứ drop trên đường. Rồi gửi
IT yêu cầu mở cổng: nguồn cụ thể, đích, cổng/giao thức, mục đích, thời hạn, người chịu trách nhiệm, lệnh kiểm.

## 8. Binary bạn mang tới báo `version 'GLIBC_2.34' not found`. Giải thích và nêu cách tránh ở lần sau.

Binary được liên kết với phiên bản symbol của glibc trên máy dựng; glibc tương thích ngược (chạy binary cũ trên glibc mới)
nhưng không tương thích xuôi. Máy khách có glibc cũ hơn máy dựng. Lần sau: dựng trên OS cũ nhất phải hỗ trợ (hoặc trong
container `manylinux`/`rockylinux:8`), với wheel thì chọn thẻ manylinux đúng glibc đích khi tải, hoặc dùng binary tĩnh
(musl). Và đưa `ldd --version` vào checklist khảo sát để biết trước khi đi.

## 9. App cần Python 3.12, máy khách chạy Ubuntu 20.04 với Python 3.8 và IT không cho cài gói. Bạn làm gì?

Không đụng Python hệ thống (nó là của distro, công cụ hệ thống dựa vào nó). Mang runtime riêng: python-build-standalone
(relocatable, cần glibc ≥ 2.17) giải nén vào `$HOME`, venv tạo bằng chính runtime đó **tại chỗ cuối cùng**, wheelhouse tải
cho đúng `cp312` và thẻ manylinux của máy đích, cài `--no-index --require-hashes`. Lệnh chạy là script console của venv với
shebang tuyệt đối, chạy được cả khi `PATH` tối thiểu. Tôi ghi vào báo cáo rằng runtime đó là trách nhiệm vá của chúng tôi,
và Ubuntu 20.04 đã hết standard support, khách cần kế hoạch nâng.

## 10. Installer qua QA ở lab, đến khách thì dừng giữa chừng với một dòng lỗi. Quy trình của bạn?

Tái hiện trên máy giống khách nhất có thể (cùng OS, cùng baseline bảo mật), chạy đúng lệnh khách chạy, đọc **toàn bộ**
output và mã thoát (126 "không chạy được" khác 127 "không thấy lệnh" khác lỗi của chính chương trình). Rồi so hai máy theo
danh sách khảo sát: tuỳ chọn mount của mọi thư mục installer đụng tới, giới hạn tài nguyên của phiên, SELinux, phiên bản
công cụ, quyền. Mỗi khác biệt là một giả thuyết; kiểm từng cái, sửa trong installer sao cho chạy được **trong** giới hạn
của khách, và thêm preflight để lần sau lỗi đó hiện ra sớm với thông báo có số liệu. Chỉ xin khách đổi cấu hình khi không
còn cách nào khác, và khi đó xin đúng một thay đổi.

## 11. Soft limit và hard limit khác nhau thế nào, và một tiến trình thật sự nhận giới hạn từ đâu?

Soft là giới hạn đang áp, hard là trần mà tiến trình không đặc quyền tự nâng soft tới được; hạ thì ai cũng hạ được, nâng
hard cần root. Phiên đăng nhập lấy giới hạn qua `pam_limits` (`/etc/security/limits.conf`, `limits.d/`); service hệ thống
lấy từ systemd (`DefaultLimitNOFILE=` trong `system.conf`, `LimitNOFILE=` của unit) và **không** đọc `limits.conf`; unit
`systemd --user` lấy từ `user.conf` của user manager. Muốn biết chắc thì đọc `/proc/<pid>/limits` của đúng tiến trình. Hai
máy cùng soft 1024 có thể cư xử khác hẳn nếu hard khác nhau, vì nhiều runtime tự nâng soft lên hard khi khởi động. Khi
không được nâng, chương trình phải tự thích nghi với giới hạn nó đọc được.

## 12. Khách muốn chạy sản phẩm trên "máy Linux" mà hoá ra là WSL2 trên laptop Windows. Bạn xử lý thế nào?

Nhận ra sớm (`uname -r` có `microsoft-standard-WSL2`, `/proc/version`, `WSL_DISTRO_NAME`), rồi nói rõ phạm vi: dùng được
để demo hay thử, không dùng để chạy thật. Lý do cụ thể: máy tắt theo phiên Windows, systemd tuỳ cấu hình, RAM bị giới hạn,
mạng NAT không lộ ra mạng công ty, tệp trên `/mnt/c` chậm và không có quyền POSIX, VPN công ty hay làm hỏng DNS, Docker
Desktop cần license. Rồi giúp khách xin một VM Linux thật, kèm yêu cầu tối thiểu.

## 13. Bạn sẽ đưa gì vào ma trận hỗ trợ OS/runtime gửi khách, và vì sao không chỉ chép phần yêu cầu tối thiểu của sản phẩm?

Mức hỗ trợ có nghĩa vận hành (ai sửa, nhanh thế nào), bảng OS với ngày hết hỗ trợ có nguồn và glibc, bảng runtime với điều
kiện và giới hạn đã biết (Podman rootless trên cgroup v1 không giới hạn được RAM, Docker cũ thiếu compose), cách sống với
SELinux/không root/noexec, phạm vi WSL, chính sách báo trước khi bỏ một nền tảng, cách khách tự kiểm máy. Yêu cầu tối thiểu
của sản phẩm thường là thứ product **mong** chạy được, không phải thứ ai đó đã kiểm; ma trận gửi khách là cam kết, nên mỗi
dòng "được hỗ trợ" phải có CI hoặc bằng chứng hiện trường đứng sau.

## 14. Khi nào bạn nói "máy này không đủ điều kiện, tôi không cài"?

Khi muốn chạy phải hạ một lớp bảo vệ mà khách không chủ động chấp nhận bằng văn bản (tắt SELinux, chạy container
privileged, tắt kiểm chứng chỉ), khi OS đã hết hỗ trợ mà khách không có kế hoạch, hoặc khi phần cứng không đạt mức tối thiểu
đã đo. Tôi nói bằng văn bản, kèm điều kiện để cài được và đường đi tới đó; không âm thầm cài một bản sẽ chết ở lần nâng
cấp đầu tiên rồi để khách phát hiện.
