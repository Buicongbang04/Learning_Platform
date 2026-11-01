# Lời giải: thiết kế email cho olistmarket.com.br

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, rubric, và một kế hoạch
mẫu đã chạy qua test (đặt vào `starter/PLAN.md` thì `test_plan_document` pass).

## Hướng làm

1. **Kiểm kê nguồn gửi trước khi viết bản ghi nào.** Mỗi nguồn trả lời ba câu: `From` là tên miền nào, `Return-Path` của
   ai, DKIM ký bằng `d=` nào. Thiếu một nguồn (Zendesk, công cụ HR, máy in quét gửi mail...) là lý do số một khiến
   `p=reject` chặn thư thật.
2. **Ưu tiên DKIM aligned cho mọi nguồn.** DKIM sống sót qua forward, SPF thì không. Google Workspace, SES (Easy DKIM),
   SendGrid/Brevo (domain authentication) và Zendesk đều cho ký bằng tên miền của bạn qua CNAME hoặc TXT.
3. **SPF alignment là lớp thứ hai.** Dùng "custom MAIL FROM" trên tên miền con (`mail.` cho SES, `em.news.` cho ESP) để
   SPF của nhà cung cấp nằm ở tên miền con, không chiếm lượt tra DNS của apex. SPF apex chỉ cần Google và Zendesk.
4. **Tách marketing sang tên miền con.** `news.olistmarket.com.br` có reputation riêng ở Gmail/Outlook; khiếu nại spam
   của bản tin không kéo theo thư đặt lại mật khẩu. Có thể đặt `sp=` hoặc bản ghi `_dmarc.news` riêng.
5. **Lộ trình DMARC đo bằng báo cáo.** `p=none` với `rua` để thu báo cáo aggregate; chỉ siết khi tỉ lệ thư hợp lệ `pass`
   đủ cao trong một khoảng đủ dài (gồm một chu kỳ bản tin và cuối tháng). `pct` siết dần; `p=reject` cuối cùng.
6. **TLS khi nhận thư**: MTA-STS (policy qua HTTPS ở `mta-sts.<domain>/.well-known/mta-sts.txt`, bắt đầu `mode: testing`)
   và TLS-RPT để thấy lỗi TLS trước khi chuyển `mode: enforce`. Đáp ứng yêu cầu của ngân hàng về chiều thư tới bạn; chiều
   bạn gửi đi do nhà cung cấp quyết định, ghi rõ trong kế hoạch.

## So sánh cách đạt alignment theo nguồn

| Nguồn | SPF aligned | DKIM aligned | Khi bị forward |
| --- | --- | --- | --- |
| Google Workspace | Có (`include:_spf.google.com` ở apex, Return-Path là chính tên miền) | Có (selector `google`, TXT) | DKIM giữ, SPF gãy: vẫn pass |
| SES có custom MAIL FROM | Có (relaxed, `mail.olistmarket.com.br`) | Có (Easy DKIM, 3 CNAME) | DKIM giữ |
| ESP mặc định | Không (Return-Path của ESP) | Không (`d=` của ESP) | Gãy cả hai: fail |
| ESP sau domain authentication | Có (relaxed, `em.news...`) | Có (CNAME `s1`, `s2`) | DKIM giữ trừ khi list sửa nội dung |
| Zendesk | Có nếu bật SPF include | Có (CNAME `zendesk1`, `zendesk2`) | DKIM giữ |

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Kiểm kê nguồn gửi | 15 | Đủ 4 nguồn, mỗi nguồn có From, Return-Path, `d=`, cơ chế alignment cụ thể; nhắc nguồn có thể bị bỏ sót |
| DKIM cho mọi nguồn | 15 | Mọi nguồn ký bằng tên miền của mình; có kế hoạch xoay khoá (selector mới, giữ selector cũ một thời gian) |
| SPF đúng và trong giới hạn | 10 | Một bản ghi apex, đếm cả lượt lồng trong include, ESP/SES nằm ở tên miền con; `~all` hay `-all` có lý do |
| Tách reputation | 10 | Marketing ở tên miền con, lý do rõ |
| Lộ trình DMARC | 20 | Ba giai đoạn trở lên, `pct` hoặc `sp` dùng có chủ đích, điều kiện chuyển đo được (tỉ lệ pass, nguồn lạ = 0, thời gian quan sát gồm chu kỳ gửi), có cách quay lại |
| Giám sát | 10 | Ai đọc báo cáo `rua`, bằng công cụ gì, cảnh báo khi nào; Postmaster Tools; theo dõi bounce và complaint rate |
| MTA-STS, TLS-RPT và phần khác | 10 | MTA-STS từ `testing` sang `enforce`, TLS-RPT; reverse DNS nếu tự vận hành MTA; List-Unsubscribe một chạm cho marketing; BIMI là tuỳ chọn sau `p=quarantine` |
| Rủi ro và rollback | 10 | Rủi ro cụ thể (nguồn bị sót, forward qua mailing list, sai CNAME khi đổi ESP) và cách lùi (hạ `pct`, quay `p=none`, TTL thấp khi đổi) |

Trừ điểm: nhảy thẳng `p=reject` (−20); SPF gộp mọi nhà cung cấp ở apex vượt 10 lượt tra (−10); dùng `+all` hoặc `?all`
(−10); không có `rua` (−10).

## Kế hoạch mẫu

`````markdown
# Kế hoạch email cho olistmarket.com.br

## 1. Nguồn gửi thư

| Nguồn | Tên miền From | Envelope sender (Return-Path) | DKIM d= | Đạt DMARC alignment nhờ |
| --- | --- | --- | --- | --- |
| Google Workspace (nhân viên) | olistmarket.com.br | olistmarket.com.br | olistmarket.com.br (selector google) | DKIM và SPF, cả hai strict |
| Amazon SES (giao dịch) | olistmarket.com.br | mail.olistmarket.com.br (custom MAIL FROM) | olistmarket.com.br (Easy DKIM, 3 selector) | DKIM; SPF relaxed qua tên miền con |
| ESP (marketing) | news.olistmarket.com.br | em.news.olistmarket.com.br | news.olistmarket.com.br (s1, s2) | DKIM; SPF relaxed |
| Zendesk (hỗ trợ) | olistmarket.com.br | olistmarket.com.br | olistmarket.com.br (zendesk1, zendesk2) | DKIM; SPF qua include ở apex |

SPF apex: `include:_spf.google.com` tốn 4 lượt (bản ghi của Google lồng thêm 3 include); `include:mail.zendesk.com`
dự trù 2 lượt, đếm lại bằng công cụ kiểm SPF trước khi thêm. Tổng dự kiến 6/10, còn chỗ cho một nguồn mới.

## 2. Bản ghi DNS

```zone
$ORIGIN olistmarket.com.br.
$TTL 3600
@                         IN MX     1 smtp.google.com.
@                         IN TXT    "v=spf1 include:_spf.google.com include:mail.zendesk.com -all"
google._domainkey         IN TXT    "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAolistmarketFAKEKEY"
abc123._domainkey         IN CNAME  abc123.dkim.amazonses.com.
def456._domainkey         IN CNAME  def456.dkim.amazonses.com.
ghi789._domainkey         IN CNAME  ghi789.dkim.amazonses.com.
zendesk1._domainkey       IN CNAME  zendesk1._domainkey.zendesk.com.
zendesk2._domainkey       IN CNAME  zendesk2._domainkey.zendesk.com.
mail                      IN MX     10 feedback-smtp.sa-east-1.amazonses.com.
mail                      IN TXT    "v=spf1 include:amazonses.com -all"
news                      IN TXT    "v=spf1 -all"
em.news                   IN CNAME  u1234.wl.esp.example.
s1._domainkey.news        IN CNAME  s1.domainkey.u1234.wl.esp.example.
s2._domainkey.news        IN CNAME  s2.domainkey.u1234.wl.esp.example.
_dmarc                    IN TXT    "v=DMARC1; p=none; rua=mailto:dmarc-rua@olistmarket.com.br; fo=1"
_dmarc.news               IN TXT    "v=DMARC1; p=none; rua=mailto:dmarc-rua@olistmarket.com.br"
_mta-sts                  IN TXT    "v=STSv1; id=20261101T0900"
_smtp._tls                IN TXT    "v=TLSRPTv1; rua=mailto:tls-rpt@olistmarket.com.br"
mta-sts                   IN CNAME  olistmarket-mta-sts.pages.example.
```

## 3. Lộ trình DMARC

| Giai đoạn | Bản ghi _dmarc | Thời lượng | Điều kiện sang giai đoạn sau |
| --- | --- | --- | --- |
| Quan sát | v=DMARC1; p=none; rua=mailto:dmarc-rua@olistmarket.com.br; fo=1 | Tối thiểu 4 tuần, gồm 4 lần gửi bản tin | 99% thư từ 4 nguồn đã biết pass DKIM aligned; không còn nguồn hợp lệ chưa khai báo trong báo cáo 14 ngày liền |
| Siết một phần | v=DMARC1; p=quarantine; pct=25; rua=mailto:dmarc-rua@olistmarket.com.br | 2 tuần, rồi pct=50 và pct=100 mỗi bước 1 tuần | Không có ticket "không nhận được thư" mới; tỉ lệ fail của nguồn hợp lệ dưới 0,5% |
| Chặn | v=DMARC1; p=reject; rua=mailto:dmarc-rua@olistmarket.com.br | Lâu dài | Đọc báo cáo hằng tuần; mọi nguồn mới phải qua checklist trước khi gửi |

TTL của `_dmarc` để 300 giây trong suốt lộ trình để lùi được nhanh.

## 4. Giám sát và báo cáo

- Báo cáo aggregate (`rua`) đổ vào công cụ phân tích DMARC (parsedmarc + dashboard, hoặc dịch vụ), cảnh báo khi có IP gửi
  lạ chiếm hơn 1% lượng thư hoặc tỉ lệ pass của một nguồn đã biết giảm dưới 98%.
- Google Postmaster Tools và Microsoft SNDS cho tên miền chính và `news`: reputation, spam rate (giữ dưới 0,1%, không bao
  giờ chạm 0,3%).
- Bounce và complaint từ SES và ESP về webhook, tự gỡ địa chỉ hard bounce; báo cáo TLS-RPT đọc hằng tuần.

## 5. Rủi ro và rollback

- Nguồn gửi bị sót (công cụ HR, hoá đơn) bị chặn khi tới quarantine: quét báo cáo trước mỗi bước, có kênh báo "không nhận
  được thư"; lùi bằng hạ `pct` hoặc về `p=none` (TTL 300).
- Mailing list sửa nội dung làm hỏng DKIM: chấp nhận cho bản tin; thư giao dịch không gửi tới list; theo dõi ARC ở phía nhận.
- Đổi ESP làm sai CNAME DKIM: thêm selector mới song song, chỉ gỡ selector cũ sau khi báo cáo cho thấy không còn dùng.

## 6. Ngoài SPF, DKIM, DMARC

- MTA-STS bắt đầu `mode: testing`, chuyển `enforce` sau 2 tuần TLS-RPT sạch; đáp ứng yêu cầu TLS của ngân hàng cho thư tới.
- List-Unsubscribe và List-Unsubscribe-Post một chạm cho mọi thư marketing, xử lý huỷ trong 2 ngày.
- Xoay khoá DKIM 6 tháng một lần bằng selector mới; BIMI cân nhắc sau khi đã ở `p=quarantine` trở lên.
`````
