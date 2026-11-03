# Câu hỏi phỏng vấn: Khảo sát môi trường khách

## Trước khi đến khách lần đầu, bạn chuẩn bị những gì?

Một checklist gửi trong tuần đầu sau khi ký, mỗi mục gắn với một người phía khách và thời hạn xử lý của họ: quyền truy
cập (tài khoản, đường vào, thẻ ra vào), người liên hệ (IT hạ tầng, an ninh, sponsor, người duyệt change, người trực),
cửa sổ bảo trì và quy trình change, đường đưa phần mềm vào (internet, proxy, registry nội bộ, cổng truyền tệp và giới hạn
kích thước), quy trình duyệt bảo mật cho script và phần mềm, dữ liệu được dùng và ai duyệt, tài nguyên sẽ cấp.

Kèm theo là một script khảo sát chỉ đọc để IT chạy trên đúng máy sẽ cài. Rồi lập lịch ngược từ cửa sổ cài theo các thời
hạn đó; thường sẽ thấy có việc phải gửi ngay ngày mai. Điểm muốn nghe: lịch xếp quanh quy trình của khách, không quanh
lịch của mình.

## Khách nói: "Máy chủ đã sẵn sàng, có Docker rồi, anh cứ đến cài." Bạn làm gì?

Cảm ơn và xin phép gửi một script khảo sát ngắn để IT chạy trước, vì "có Docker" có nhiều nghĩa: client có nhưng daemon
không chạy, user của mình không thuộc nhóm `docker`, bản quá cũ, thiếu plugin compose, thư mục dữ liệu nằm trên phân vùng
8 GB. Script chỉ đọc, không cần root, không cần mạng, in JSON; mình chạy preflight trên kết quả và gửi lại một trang
khoảng cách nếu có.

Không đến cài dựa trên lời "sẵn sàng". Một buổi đến nơi rồi phát hiện đĩa thiếu là một tuần mất, cộng với lòng tin của
khách vào cả hai bên.

## Liệt kê cách đọc OS, kernel, glibc, CPU, RAM, đĩa trên một máy Linux lạ mà không cần root. Chỗ nào hay sai?

OS từ `/etc/os-release` (`ID`, `VERSION_ID`); kernel `uname -r`; glibc `getconf GNU_LIBC_VERSION`; CPU `nproc`; RAM
`MemTotal` trong `/proc/meminfo`; đĩa `df -P -k` và `df -P -i` **tại thư mục dữ liệu của runtime**.

Chỗ hay sai: dùng `lsb_release` (không có trên Rocky tối thiểu); đếm `/proc/cpuinfo` trong container (ra CPU của host);
so `MemTotal` với RAM danh nghĩa (máy 4 GB báo ~3,8 GB); `df -h` để parse; đo `df /` trong khi Docker ghi vào
`/var/lib/docker` trên volume khác hay Podman rootless ghi vào home.

## Vì sao script khảo sát nên viết bằng POSIX sh thay vì bash hay Python?

Vì nó phải chạy trên máy mình không chọn. Khách sẽ gõ `sh survey.sh`; trên Ubuntu `sh` là dash, `[[ ]]` và mảng lỗi cú
pháp. Python không chắc có: RHEL/Rocky 8 tối thiểu chỉ có `platform-python` cho công cụ hệ thống, không có `python3` cho
người dùng; máy appliance có khi không có Python nào. `jq` cũng vậy.

Đánh đổi: sh khó viết JSON và xử lý chuỗi. Giữ script nhỏ, chỉ thu thập, mọi logic (so yêu cầu, quyết định) đưa về phía
mình bằng Python trên laptop. Kiểm bằng `shellcheck -s sh` và chạy thật trên cả hai họ distro.

## Script khảo sát của bạn dùng `set -e`. Có vấn đề gì không?

Có. Với script dò, lệnh thất bại là dữ liệu: không có `getenforce` nghĩa là không có SELinux, `sudo -n true` trả 1 nghĩa
là không có sudo. `set -e` biến dữ liệu đó thành điểm dừng, và khách chỉ thấy lỗi đầu tiên; sửa xong gửi lại thì hỏng ở
chỗ tiếp theo, mỗi vòng một ngày. Tệ hơn, nếu stderr bị chuyển vào tệp, script dừng mà không in gì.

Cách làm: bỏ `set -e` cho phần dò, mỗi lệnh dò trong `if` hoặc `||`, ghi lý do khi một phần không thu được, và chỉ coi
là lỗi những thứ thật sự hỏng (không tạo được thư mục ra).

## Khách gửi lại: "chạy script của anh ra `lsb_release: command not found`". Bạn làm gì?

Không sửa đúng một dòng rồi gửi lại. Lỗi đó nói máy là họ RHEL tối thiểu, nên giả định phía sau còn nữa: `sudo` không có
quyền, `resolvectl` có nhưng resolved không chạy, không có Docker mà là Podman, không có `python3`. Rà toàn bộ script với
ba câu hỏi (lệnh có trong bản tối thiểu không, có cần quyền không, có giả định dịch vụ đang chạy không), dựng một máy
cùng họ (Rocky 8, không sudo, không mạng) để chạy thử, rồi gửi một bản sửa duy nhất kèm sha256 và câu "đã chạy thử trên
Rocky 8.10 không sudo, không mạng".

Đồng thời xin lỗi ngắn gọn vì tốn một vòng của khách; ở ngân hàng mỗi vòng có thể là một lần duyệt change.

## Preflight của bạn phân biệt blocker và warning thế nào?

Blocker là thứ **người khác** phải làm trước ngày cài: nới đĩa, cấp thêm RAM, đổi OS, xác nhận cổng đang bị dịch vụ khác
chiếm. Warning là thứ FDE tự xử lý được trong buổi cài nếu đã chuẩn bị: proxy, CA nội bộ, SELinux enforcing (nhãn `:Z`),
thiếu plugin compose (mang theo bundle). Không báo những gì không ảnh hưởng (GPU khi yêu cầu ghi optional).

Hệ quả: blocker không đồng nghĩa với "nghiêm trọng". SELinux enforcing nghe đáng sợ nhưng là warning; đĩa thiếu 4 GB
nghe nhỏ nhưng là blocker vì cần change của IT.

## Máy khách không có sudo. Đó có phải là blocker không?

Tuỳ runtime. Podman rootless chạy container hoàn toàn ở user thường, nên không có sudo không phải phát hiện; chỉ vài việc
một lần cần root (`loginctl enable-linger` để container sống sau khi đăng xuất, mở cổng firewalld, dải `subuid`) và IT
làm hộ trong cửa sổ. Với Docker thì khác: user phải thuộc nhóm `docker`, tương đương root, mà ngân hàng thường từ chối;
khi đó cần IT chạy hộ bước cài hoặc chuyển sang Podman nếu sản phẩm hỗ trợ.

Điều không làm: xin sudo "cho tiện". Ở khách khắt khe, đề nghị đó làm người duyệt nghi phần còn lại.

## Survey báo đĩa còn 18 GB nhưng cài vẫn hết chỗ giữa chừng. Bạn nghĩ tới những nguyên nhân nào?

Đo sai chỗ: 18 GB là của `/`, còn Docker ghi vào `data-root` trên một volume khác (xem `docker info --format
'{{.DockerRootDir}}'`), Podman rootless ghi vào home có quota. Hết inode chứ không hết dung lượng (`df -i`), nhất là image
Python nhiều tệp nhỏ. Bước giải nén bundle dùng `/tmp` trên tmpfs nhỏ hoặc trên phân vùng khác. Image cũ và mới cùng nằm
trên đĩa trong lúc nâng cấp nên cần gấp đôi. Và dữ liệu khác lấp đầy giữa ngày survey và ngày cài.

Cách phòng: đo ở thư mục dữ liệu của runtime và ở thư mục tạm của installer, đo cả inode, chạy lại preflight ngay trước
khi cài.

## Làm sao biết cổng 18080 có trống không khi bạn không có root? Nếu nó đang bị dùng thì sao?

`ss -H -t -l -n -p`, so phần cổng sau dấu `:` cuối cùng (không `grep ":18080"` vì dễ khớp nhầm). User thường thấy socket
nhưng chỉ thấy tên tiến trình của chính mình; tiến trình của user khác hiện như không có chủ.

Nếu bận và không rõ là gì: báo "đang có tiến trình nghe, không xem được là gì", đưa IT lệnh
`sudo ss -tlnp 'sport = :18080'`, và đưa phương án đổi cổng sản phẩm để IT chọn. Không tự `kill`, không đoán ("chắc
Jenkins").

## Khách hỏi: "Script này có an toàn để chạy trên máy production không?" Bạn trả lời thế nào?

Bằng tài liệu chứ không bằng lời hứa: script chỉ đọc (liệt kê tệp nó đọc và lệnh nó chạy), không ghi gì ngoài stdout,
không cài gì, không gửi dữ liệu đi đâu, chạy bằng user thường. Nói trước hai chỗ có thể gây chú ý: một lần thử kết nối ra
ngoài có timeout (firewall có thể ghi log), một lần `sudo -n true` (có thể ghi log bảo mật). Kèm sha256 để họ chạy đúng
bản đã duyệt, và đề nghị họ đọc script, nó ngắn.

Nếu họ không cho chạy script: gửi danh sách lệnh để IT tự chạy và chép output. Chậm hơn nhưng vẫn là dữ liệu.

## Bạn gửi báo cáo khoảng cách cho IT khách. Cấu trúc nó thế nào? Điều gì làm báo cáo bị bỏ qua?

Kết luận ba câu ở đầu (cài được chưa, cần gì, trước ngày nào, điểm quyết định nếu không kịp); bảng tóm tắt (hạng mục, số
đo, yêu cầu, mức, ai làm, hạn); việc cần khách làm, mỗi việc có bằng chứng, con số và phương án để chọn; việc phía mình;
câu hỏi còn mở.

Bị bỏ qua khi: mở đầu bằng bảng 13 trường thô; hạn "trước ngày cài" không gắn cửa sổ bảo trì; dùng thuật ngữ nội bộ; đổ
lỗi; hoặc đề nghị nới bảo mật (tắt TLS inspection, tắt SELinux), thứ làm an ninh thông tin chặn cả báo cáo.

## Preflight chạy trên máy lab với 2048 MB RAM luôn báo blocker RAM. Bạn có nên hạ ngưỡng trong code không?

Không. Ngưỡng là của sản phẩm (`REQUIREMENTS.yaml` đi kèm bản phát hành), không phải của lab. Lab nhỏ hơn yêu cầu thì
preflight báo đúng là nhỏ hơn. Nếu muốn chạy thử trên lab, truyền một tệp yêu cầu khác cho lab, giữ preflight đọc yêu
cầu từ tệp chứ không chép số vào code.

Liên quan: RAM danh nghĩa và `MemTotal` lệch nhau; nên có biên (dưới 90% mới là blocker) và ghi trong `detail` để IT
khách không bị chặn nhầm khi máy đúng 4 GB.
