---
title: Thiết kế email cho tên miền mới - SPF, DKIM, DMARC từ p=none tới reject
level: advanced
services: []
files:
  - path: starter/PLAN.md
    note: Khung kế hoạch, điền mọi TODO
  - path: tests/test_plan.py
    note: Không sửa; kiểm khung và zone, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/advanced/02-email-domain-rollout-plan -q
---

## Mục tiêu

Thiết kế cấu hình email cho một tên miền từ con số không, với nhiều nguồn gửi thư, sao cho thư thật luôn tới hộp thư
còn thư giả mạo bị chặn, và đi tới `p=reject` mà không làm mất thư hợp lệ trên đường đi.

## Đề bài

Olist Shop mở sàn cho người bán ở tên miền mới `olistmarket.com.br`. Tên miền chưa có bản ghi nào. Các nguồn sẽ gửi thư
nhân danh tên miền này:

- Nhân viên dùng **Google Workspace** (hộp thư `@olistmarket.com.br`, gửi qua Gmail).
- Thư giao dịch (xác nhận đơn, đặt lại mật khẩu) gửi từ ứng dụng qua **Amazon SES**.
- Thư marketing hằng tuần qua một **ESP** (SendGrid, Brevo...), khoảng 400.000 người nhận.
- Hệ thống ticket **Zendesk** trả lời khách từ `suporte@olistmarket.com.br`.

Ràng buộc: thư marketing bị đánh dấu spam không được kéo theo thư đặt lại mật khẩu; SPF không vượt giới hạn tra DNS;
team muốn tới `p=reject` trong khoảng một quý; đối tác ngân hàng đòi thư tới họ phải đi qua TLS đã xác thực.

Viết `starter/PLAN.md`, giữ nguyên các heading `## 1.` tới `## 6.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Nguồn gửi thư | Bảng ít nhất 4 dòng đủ 5 cột |
| 2. Bản ghi DNS | Một khối code mở bằng ` ```zone `, nội dung là zone file hợp lệ (xem dưới) |
| 3. Lộ trình DMARC | Bảng ít nhất 3 dòng đủ 4 cột; cột `Bản ghi _dmarc` chứa `p=none`, `p=quarantine`, `p=reject`, lần đầu xuất hiện theo đúng thứ tự đó |
| 4. Giám sát và báo cáo | Ít nhất 3 gạch đầu dòng |
| 5. Rủi ro và rollback | Ít nhất 3 gạch đầu dòng |
| 6. Ngoài SPF, DKIM, DMARC | Ít nhất 3 gạch đầu dòng |

Khối ` ```zone ` được đọc bằng dnspython với origin `olistmarket.com.br.` (không bắt buộc SOA/NS; chuỗi TXT dài hơn 255
ký tự phải tách thành nhiều chuỗi trong ngoặc kép) và phải thoả:

- Apex có ít nhất một `MX`. Không tên nào vừa có `CNAME` vừa có bản ghi khác; apex không có `CNAME`.
- Apex có **đúng một** TXT bắt đầu bằng `v=spf1`, kết thúc bằng `-all` hoặc `~all`, và có không quá 10 term cần tra DNS
  (`include:`, `a`, `mx`, `exists:`, `ptr`, `redirect=`; test chỉ đếm ở bản ghi apex, phần lồng trong include bạn tự
  tính và ghi ra trong kế hoạch).
- Ít nhất một tên miền con (không bắt đầu bằng `_`) có SPF riêng: envelope sender của ESP hoặc SES.
- Ít nhất 2 selector DKIM dưới `_domainkey`: TXT có `v=DKIM1` và `p=` với khoá base64 (từ 20 ký tự), hoặc `CNAME` tới nhà
  cung cấp.
- Đúng một `_dmarc` TXT `v=DMARC1` ở **giai đoạn đầu**: `p=none` và `rua=mailto:...`.
- `_mta-sts` TXT `v=STSv1; id=...` và `_smtp._tls` TXT `v=TLSRPTv1; rua=...`.

Khoá DKIM thật do nhà cung cấp sinh; trong bài, dùng chuỗi base64 giả bất kỳ hoặc CNAME. Test chỉ kiểm khung và tính hợp
lệ của zone; nội dung được chấm bằng rubric trong `solutions/advanced/02-email-domain-rollout-plan/SOLUTION.md`.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/advanced/02-email-domain-rollout-plan -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi nguồn gửi trong bảng 1 đạt DMARC alignment bằng một cơ chế cụ thể, và bạn nói được điều gì xảy ra với nguồn đó khi
  thư bị forward.
- Mỗi giai đoạn trong bảng 3 có điều kiện chuyển đo được từ báo cáo DMARC, không phải "sau 2 tuần".

## Gợi ý

### Gợi ý 1

Liệt kê trước: với mỗi nguồn, header `From` là tên miền nào, `Return-Path` là tên miền nào (của bạn hay của nhà cung
cấp), chữ ký DKIM mang `d=` nào. DKIM aligned là đường bền nhất vì nó sống sót qua forward; SPF alignment chỉ có khi nhà
cung cấp cho đặt "custom MAIL FROM" trên tên miền con của bạn.

### Gợi ý 2

Tách luồng marketing sang tên miền con (ví dụ `news.olistmarket.com.br`) để reputation của nó tách khỏi tên miền chính.
`p=none` không bảo vệ gì nhưng cho bạn báo cáo `rua` để tìm mọi nguồn gửi chưa được khai báo; chỉ siết khi báo cáo cho
thấy gần như mọi thư hợp lệ đều `pass`. `pct` và `sp` là hai cần gạt để siết từng phần.
