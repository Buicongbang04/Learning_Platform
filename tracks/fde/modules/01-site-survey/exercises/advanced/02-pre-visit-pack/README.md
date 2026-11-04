---
title: Gói chuẩn bị trước khi đến ngân hàng
level: advanced
services: []
files:
  - path: starter/pre-visit.md
    note: Khung thư + checklist gửi khách
run: []
---

## Mục tiêu

Ở khách khắt khe, phần lớn thời gian của một lần cài nằm **trước** ngày đến: quyền truy cập, duyệt bảo mật, duyệt
change, đường đưa phần mềm vào. Bài này luyện viết gói chuẩn bị gửi IT khách sao cho không mốc nào bị lỡ vì bạn hỏi
muộn.

## Đề bài

Khách: Ngân hàng Hải Đăng (hư cấu). Sales đã ký pilot `quillo` cho Khối Pháp chế. Hôm nay thứ Tư 04/11/2026. Mục tiêu:
cài trong **cửa sổ thay đổi thứ Bảy 28/11/2026, 22:00–02:00**; bạn đến trụ sở chuẩn bị từ **thứ Hai 23/11**.

Những gì sales và anh Khoa (Vận hành hệ thống) đã cho biết:

- Máy chủ "tương thích RHEL 8", không ra internet, tài khoản dịch vụ không có sudo, SELinux bật theo chính sách, Podman
  được phép dùng. Chưa ai nói máy có bao nhiêu RAM, đĩa, hay dữ liệu đặt ở đâu.
- Mọi script hay phần mềm đưa vào phải qua **An ninh thông tin** (chị Mai) duyệt, mất **5 ngày làm việc**.
- Thay đổi hệ thống phải qua **CAB** họp sáng thứ Ba hằng tuần; hồ sơ change nộp muộn nhất **thứ Năm tuần trước** đó.
  Cửa sổ thay đổi: tối thứ Bảy.
- Cấm USB. Tệp đưa vào qua cổng truyền tệp nội bộ (MFT), có quét mã độc, tối đa **2 GB mỗi tệp**.
- Khách đến làm việc phải đăng ký thẻ ra vào trước **3 ngày làm việc**; laptop ngoài không được cắm mạng ngân hàng, làm
  việc qua máy VDI do ngân hàng cấp.
- Người liên quan: anh Khoa (Vận hành), chị Mai (An ninh thông tin), anh Dũng (Phó khối Pháp chế, sponsor), thư ký CAB.

Bundle `quillo` khoảng 3,5 GB (image, model, cấu hình). Script survey của bạn là `site_survey.sh` (bài Basic 01).

Viết `starter/pre-visit.md` gồm hai phần: (1) thư gửi anh Khoa, đồng gửi chị Mai và anh Dũng; (2) checklist chi tiết kèm
lịch ngược. Bài không có test; tự chấm theo rubric (đạt đủ 10 mục), rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| P1 | Thư ngắn (không quá 20 dòng, không tính checklist): mục đích, các mốc chính, việc cần anh Khoa phản hồi và hạn cụ thể |
| P2 | Quyền truy cập: tài khoản VDI, tài khoản trên máy chủ, thẻ ra vào; mỗi thứ có hạn đúng với thời gian xử lý của ngân hàng |
| P3 | Không xin sudo, root, tắt SELinux hay mở internet. Thay vào đó liệt kê ít nhất hai thao tác cụ thể cần quyền mà IT làm hộ trong cửa sổ, kèm lý do |
| P4 | Người liên hệ và kênh: ai quyết việc gì (vận hành, an ninh, sponsor, CAB), và gặp chặn thì báo ai |
| P5 | Lịch ngược từ 28/11 tôn trọng đủ ba thời hạn: duyệt bảo mật 5 ngày làm việc, hồ sơ CAB trước thứ Năm, thẻ ra vào 3 ngày làm việc; ngày và thứ khớp lịch 2026 |
| P6 | Survey: gửi script cho An ninh thông tin duyệt trước khi chạy, mô tả chỉ đọc, không cần mạng, không cần root, nói rõ có một lần thử `sudo -n` có thể sinh log, kèm sha256, và kênh gửi kết quả về |
| P7 | Đưa phần mềm vào: qua MFT, chia tệp dưới 2 GB, manifest sha256 để kiểm sau khi nhận, bundle cũng qua duyệt bảo mật |
| P8 | Dữ liệu pilot: dữ liệu nào, ai duyệt, không rời ngân hàng, không nằm trên máy của FDE |
| P9 | Câu hỏi survey không trả lời được: tài nguyên sẽ cấp (CPU, RAM, đĩa), dữ liệu đặt ở volume nào, phiên bản Podman, NTP, cổng `18080`, ai trực trong cửa sổ |
| P10 | Viết cho người ngân hàng: không thuật ngữ nội bộ của đội bạn, không hứa thay khách ("CAB chắc sẽ duyệt"), mọi việc có người làm |

## Tiêu chí đạt

- `pre-visit.md` đạt đủ 10 mục P1–P10 khi tự chấm từng mục.
- Mọi mốc ngày khớp đúng thứ trong tuần của tháng 11/2026 và không mốc nào vi phạm thời hạn xử lý đề cho.

## Gợi ý

### Gợi ý 1

Viết lịch ngược trước: bắt đầu từ 28/11, lùi theo từng thời hạn của ngân hàng. Bạn sẽ thấy một số việc phải gửi đi ngay
tuần này.

### Gợi ý 2

Podman rootless không cần sudo để chạy container, nhưng có vài thứ chỉ root cấu hình được để container sống sót sau khi
bạn đăng xuất và nhận kết nối từ máy khác.

### Gợi ý 3

Người duyệt bảo mật muốn biết script làm gì **trước** khi đọc nó: liệt kê lệnh và tệp nó đọc, nói rõ thứ nó không làm.
