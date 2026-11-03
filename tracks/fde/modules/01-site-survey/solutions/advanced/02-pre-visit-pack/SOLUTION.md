# Lời giải: Gói chuẩn bị trước khi đến ngân hàng

## Hướng làm

1. **Lịch ngược từ 28/11** (đếm ngày làm việc, bỏ thứ Bảy, Chủ nhật):

   | Mốc | Ràng buộc | Hạn muộn nhất |
   | --- | --- | --- |
   | Cài | Cửa sổ thứ Bảy | 28/11 22:00 |
   | CAB duyệt | Họp thứ Ba trước cửa sổ | 24/11 |
   | Nộp hồ sơ change | Thứ Năm tuần trước CAB | 19/11 |
   | Bundle duyệt xong | Trước khi đến 23/11 để kiểm tại chỗ | Gửi duyệt 16/11 ⇒ xong 23/11 (17, 18, 19, 20, 23) |
   | Thẻ ra vào cho 23/11 | 3 ngày làm việc | Đăng ký 18/11 (19, 20, 23) |
   | Kết quả survey | Cần trước khi viết hồ sơ change | Gửi về 16/11 |
   | Script survey duyệt xong | 5 ngày làm việc | Gửi duyệt 05/11 ⇒ xong 12/11 (06, 09, 10, 11, 12) |

   Đây là hạn **muộn nhất**; bài mẫu xin sớm hơn ở chỗ được (thẻ ra vào, VDI) vì một ngày nghỉ hay một câu hỏi lại của
   An ninh thông tin là đủ làm trượt. Hồ sơ change nộp 19/11 trong khi bundle còn đang duyệt tới 23/11: đó là rủi ro có
   chủ ý (CAB duyệt các bước, không duyệt tệp), phải ghi trong hồ sơ rằng việc cài phụ thuộc kết quả duyệt bundle, và
   nếu An ninh thông tin từ chối thì rút change thay vì cài bản chưa duyệt.

   Hệ quả: script survey phải gửi **ngày mai**. Đây là điểm hay bị lỡ nhất: FDE quen "đến nơi rồi chạy survey".
2. **Thứ cần quyền** cho Podman rootless (gợi ý 2): `loginctl enable-linger` để container chạy tiếp sau khi đăng xuất và
   tự lên sau khi khởi động lại; mở cổng `18080/tcp` trên firewalld nếu người dùng truy cập từ máy khác; kiểm
   `/etc/subuid`, `/etc/subgid` có dải cho tài khoản dịch vụ; tạo thư mục dữ liệu trên volume riêng, chủ là tài khoản
   dịch vụ, giữ nguyên ngữ cảnh SELinux mặc định. Mỗi việc IT làm một lần trong cửa sổ, không cần cấp sudo cho FDE.
3. **Survey** gửi kèm mô tả cho người duyệt: đọc tệp nào, chạy lệnh nào, không ghi gì ngoài stdout, không cần mạng (có
   một lần thử kết nối ra ngoài với timeout 5 giây để biết máy có đường ra không), một lần `sudo -n true`.

## Rubric (tự chấm, đạt đủ 10 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| P1 | Thư 13 dòng có chữ, nêu mục đích, mốc 23/11 và 28/11, ba việc cần anh Khoa phản hồi kèm hạn |
| P2 | Checklist: VDI và tài khoản dịch vụ trước 13/11, thẻ ra vào 16/11 (hạn muộn nhất 18/11) |
| P3 | Mục "Thao tác cần quyền quản trị": bốn việc, có lý do; không xin sudo |
| P4 | Mục "Ai quyết việc gì" và dòng báo chặn |
| P5 | Lịch khớp các thời hạn ở bảng trên |
| P6 | Dòng 05/11 và mục "Về script khảo sát" |
| P7 | Dòng 16/11: hai tệp dưới 2 GB, manifest sha256, qua duyệt bảo mật |
| P8 | Dòng 13/11 về dữ liệu pilot |
| P9 | Mục "Câu hỏi" |
| P10 | Không thuật ngữ nội bộ; không hứa thay CAB ("trình CAB 24/11"); mọi dòng có người làm |

## Bài mẫu

```markdown
# Chuẩn bị triển khai pilot quillo tại Ngân hàng Hải Đăng

## Thư gửi anh Khoa

Gửi: anh Khoa (Vận hành hệ thống). Đồng gửi: chị Mai (An ninh thông tin), anh Dũng (Phó khối Pháp chế).

Chào anh Khoa,

Em là kỹ sư triển khai pilot quillo cho Khối Pháp chế. Để kịp cửa sổ thay đổi tối thứ Bảy 28/11, em gửi trước lịch
chuẩn bị và những việc cần bên mình hỗ trợ (chi tiết ở bảng dưới). Em dự kiến đến trụ sở từ thứ Hai 23/11.

Ba việc em cần anh phản hồi:
1. Trước thứ Năm 05/11: chuyển giúp em script khảo sát (đính kèm, có sha256) sang chị Mai để duyệt. Script chỉ đọc
   thông tin máy, không cần mạng, không cần quyền quản trị.
2. Trước thứ Sáu 13/11: tạo tài khoản VDI cho em, xác nhận tài khoản dịch vụ trên máy chủ, và trả lời các câu hỏi ở
   mục "Câu hỏi".
3. Trước thứ Hai 16/11 (hạn muộn nhất của bên mình là 18/11): đăng ký thẻ ra vào cho em từ ngày 23/11.

Em sẽ gửi bản mô tả thay đổi (các bước, cách hoàn tác, bốn thao tác cần quyền quản trị) trước thứ Tư 18/11 để anh nộp
CAB hạn thứ Năm 19/11. Việc nào bị chặn quá một ngày, em sẽ báo anh và anh Dũng ngay.

Cảm ơn anh.

## Checklist và lịch

| Ngày | Việc | Ai làm | Ghi chú |
| --- | --- | --- | --- |
| Thứ Năm 05/11 | Gửi script khảo sát cho An ninh thông tin duyệt | Em gửi, anh Khoa chuyển | Kèm sha256 và mục "Về script khảo sát"; duyệt xong dự kiến 12/11 |
| Thứ Sáu 13/11 | Anh Khoa chạy script trên máy chủ, gửi kết quả về qua MFT | Anh Khoa | Kết quả là một tệp JSON nhỏ, không chứa dữ liệu nghiệp vụ |
| Thứ Sáu 13/11 | Tài khoản VDI cho em; xác nhận tài khoản dịch vụ trên máy chủ | Anh Khoa | Không cần sudo |
| Thứ Sáu 13/11 | Chốt dữ liệu pilot: tập hợp đồng nào, đã được phép dùng chưa | Anh Dũng, chị Mai duyệt | Dữ liệu nằm trên máy chủ ngân hàng, không chép ra máy của em |
| Thứ Hai 16/11 | Đưa bản cài vào qua MFT để An ninh thông tin duyệt | Em | 3,5 GB chia hai tệp dưới 2 GB, kèm manifest sha256 để kiểm sau khi nhận; duyệt xong dự kiến 23/11 |
| Thứ Hai 16/11 | Đăng ký thẻ ra vào từ 23/11 | Anh Khoa | Hạn muộn nhất 18/11; xin sớm để dự phòng |
| Thứ Tư 18/11 | Gửi bản mô tả thay đổi, ghi rõ việc cài phụ thuộc kết quả duyệt bản cài (dự kiến 23/11) | Em | Bản cài chưa được duyệt thì rút change, không cài |
| Thứ Năm 19/11 | Nộp hồ sơ change | Anh Khoa | |
| Thứ Hai 23/11 | Đến trụ sở: kiểm bản cài đã nhận khớp sha256, chạy khảo sát lần cuối, diễn tập trên máy chủ (chỉ đọc) | Em, anh Khoa | |
| Thứ Ba 24/11 | Trình CAB | Anh Khoa | |
| Thứ Bảy 28/11 22:00 | Cài trong cửa sổ, có bước hoàn tác | Em, người trực vận hành | |

### Thao tác cần quyền quản trị (anh Khoa làm hộ trong cửa sổ)

1. `loginctl enable-linger <tài khoản dịch vụ>`: để dịch vụ tiếp tục chạy sau khi đăng xuất và tự khởi động lại.
2. Mở cổng `18080/tcp` trên firewalld, chỉ cho dải mạng của Khối Pháp chế.
3. Kiểm `/etc/subuid` và `/etc/subgid` có dải cho tài khoản dịch vụ (cần để chạy container không quyền root).
4. Tạo thư mục dữ liệu trên volume riêng (tối thiểu 10 GB trống, đề nghị 20 GB), chủ là tài khoản dịch vụ, giữ ngữ cảnh SELinux mặc định.

### Về script khảo sát

Toàn bộ những gì script đụng tới:

- Tệp và biến đọc: `/etc/os-release`, `/proc/meminfo`, biến môi trường `https_proxy`/`HTTPS_PROXY` của phiên rồi
  `/etc/environment` (chỉ dòng proxy; phần tài khoản và mật khẩu trong URL bị bỏ trước khi in),
  `/sys/fs/selinux/enforce` (khi không có `getenforce`); kiểm `/dev/nvidia0` có tồn tại không.
- Lệnh chạy, đều với tài khoản dịch vụ: `uname -r`, `getconf GNU_LIBC_VERSION` (dự phòng `ldd --version`), `nproc` (dự
  phòng `getconf _NPROCESSORS_ONLN`), `df -P -k /`, `getenforce`, `command -v` để dò `docker`, `podman`, `nvidia-smi`; `docker --version`; `nvidia-smi
  --query-gpu=name` nếu có; `sudo -n true` một lần; `curl` hai lần, tối đa 5 giây mỗi lần: thẳng ra
  `https://pypi.org/simple/` và qua proxy đã khai (nếu có) tới `http://pypi.org/simple/`.
- Lần thử `sudo -n` có thể ghi một dòng vào log bảo mật, lần thử `curl` có thể làm tường lửa ghi log; mong chị Mai biết
  trước.
- Không ghi tệp, không cài gì, không gửi dữ liệu đi đâu; kết quả là 13 trường JSON in ra màn hình; địa chỉ duy nhất trong đó là địa chỉ proxy (nếu có), không có IP hay tên của máy.

### Ai quyết việc gì

Anh Khoa: tài khoản, máy chủ, hồ sơ change. Chị Mai: duyệt script, bản cài, dữ liệu. Anh Dũng: phạm vi pilot, tập dữ
liệu. CAB: cửa sổ 28/11. Bị chặn quá một ngày: em báo anh Khoa và anh Dũng.

### Câu hỏi

- Máy chủ được cấp bao nhiêu CPU, RAM; dữ liệu đặt ở volume nào, còn trống bao nhiêu (tối thiểu 2 CPU, 4 GB RAM,
  10 GB trống; đề nghị 20 GB để còn chỗ cho bản nâng cấp).
- Phiên bản Podman đang cài (cần từ 4.0).
- Máy chủ đồng bộ giờ với NTP nội bộ nào.
- Cổng `18080` có đang dùng cho dịch vụ khác không; người dùng truy cập từ dải mạng nào.
- Ai trực vận hành trong cửa sổ 28/11.
```

## Lỗi hay gặp

- Gửi survey khi đã đến nơi: mất nguyên tuần chờ An ninh thông tin duyệt.
- Xin sudo "cho tiện": ở ngân hàng câu trả lời là không, và đề nghị đó làm người duyệt nghi phần còn lại.
- "Tắt SELinux trong lúc cài": không bao giờ.
- Một tệp bundle 3,5 GB: MFT từ chối, mất thêm một vòng.
- Lịch không tính thời gian xử lý của khách: hồ sơ CAB nộp thứ Hai 23/11 sẽ không kịp cửa sổ 28/11.
- Viết thư dài hai trang: người nhận chỉ đọc đoạn đầu; phần chi tiết để ở checklist.
