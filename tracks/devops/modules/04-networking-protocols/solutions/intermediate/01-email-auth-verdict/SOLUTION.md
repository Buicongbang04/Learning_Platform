# Lời giải: kết luận SPF, DKIM, DMARC cho từng thư

Code đầy đủ ở `email_auth.py` cạnh tệp này.

## Cách làm

1. **`org_domain`** chọn hậu tố có nhiều nhãn nhất khớp tên miền rồi giữ thêm một nhãn. Lối tắt "hai nhãn cuối" sai với
   mọi ccTLD hai cấp: `evil-shop.com.br` và `olist-shop.com.br` sẽ thành "cùng tổ chức" `com.br`, và DMARC relaxed cho
   một tên miền bất kỳ dưới `.com.br` qua mặt bạn. Production dùng Public Suffix List đầy đủ (thư viện `publicsuffix2`,
   `tldextract`) và cập nhật định kỳ.
2. **`spf_check`** là một hàm đệ quy với bộ đếm dùng chung và exception `PermError`. Ba chỗ hay sai:
   - `include` trả `softfail`/`fail` **không** làm cả bản ghi fail, chỉ là "không khớp" rồi đi tiếp. Tên `include` gây
     hiểu nhầm; nghĩa thật là "nếu bản ghi kia pass".
   - `include` tới tên miền không có SPF là `permerror`, không phải "bỏ qua".
   - Giới hạn 10 lượt đếm cả các tầng lồng và chỉ đếm term thực sự được đánh giá. Cùng một bản ghi `toomany.example` cho
     `pass` với IP khớp sớm và `permerror` với IP khớp muộn: lỗi chỉ hiện ra với một phần thư, rất khó đoán.
3. **`evaluate`** chỉ tin những gì MX của bạn ghi: header `Received` trên cùng (IP, HELO) và `Authentication-Results`
   trên cùng mang authserv-id của bạn. Mọi header bên dưới do người gửi hoặc máy trung gian ghi, có thể giả.
4. **DMARC** = (SPF pass **và** aligned) **hoặc** (DKIM pass **và** aligned). Pass mà không aligned không tính.

## Từng thư

| Thư | Kết luận | Bài học |
| --- | --- | --- |
| 01 | pass | Trường hợp chuẩn: cả SPF và DKIM aligned |
| 02 | pass nhờ SPF | ESP ký DKIM bằng `d=esp-mail.example` (mặc định của ESP) nên DKIM không aligned; chỉ còn SPF relaxed qua `bounces.` cứu. Một chân |
| 03 | pass nhờ DKIM | Forward đổi IP gửi nên SPF fail, nhưng chữ ký DKIM của Olist còn nguyên. Đây là lý do DKIM aligned quan trọng hơn SPF |
| 04 | reject | Cùng luồng với thư 02 nhưng qua mailing list: IP đổi (SPF gãy) và list sửa subject, thêm footer (DKIM của ESP gãy, mà vốn cũng không aligned). Sửa: bật domain authentication ở ESP để ký `d=olist-shop.com.br`; về phía người nhận, ARC giúp tin kết quả của list |
| 05 | reject | Giả mạo cổ điển: kẻ tấn công có SPF pass cho tên miền **của họ** ở `Return-Path`, nhưng `From` là Olist. Không aligned. Header `DKIM-Signature d=olist-shop.com.br` có mặt nhưng chữ ký sai |
| 06 | reject | Kẻ tấn công chèn sẵn một `Authentication-Results` mang authserv-id của bạn với `dkim=pass`. Chỉ header trên cùng do MX của bạn ghi là đáng tin; MTA đúng chuẩn còn xoá các header A-R mang authserv-id của mình từ thư đi vào (RFC 8601 mục 5). `Return-Path: <>` làm SPF chạy trên HELO |
| 07 | pass, deliver | Tên miền na ná (`olist-shop-br.com`) có SPF, DKIM, DMARC đầy đủ cho **chính nó**. DMARC chỉ chống giả mạo đúng tên miền, không chống lookalike. Phòng bằng: theo dõi đăng ký tên miền na ná, BIMI/VMC, đào tạo người dùng, cảnh báo "người gửi bên ngoài" |
| 08 | quarantine | `promo.` không có bản ghi DMARC riêng nên dùng `sp=quarantine` của tên miền tổ chức. Không có SPF ở `promo.` và DKIM của ESP không aligned |
| 09 | quarantine với 25%, deliver với 75% | `_dmarc.news` có `pct=25`: chỉ 1/4 thư fail chịu `quarantine`, phần còn lại hạ một bậc. Lỗi gốc: selector DKIM `old2024` đã bị gỡ khỏi DNS trước khi ESP đổi sang khoá mới |
| 10 | reject | `adkim=s; aspf=s`: `bounces.olist-shop.com.br` và `olist-shop.com.br` đều khác `pay.olist-shop.com.br`. Strict alignment đòi ký đúng `d=pay.olist-shop.com.br` và Return-Path đúng tên đó |
| 11 | pass | Hai chữ ký: chữ ký `d=olist-shop.com.br` aligned relaxed với `news.olist-shop.com.br`. Một chữ ký aligned là đủ |
| 12 | pass dù SPF permerror | SPF quá 10 lượt, nhưng DKIM aligned cứu. Đừng để permerror kéo dài: thư của nguồn chỉ có SPF sẽ fail |
| 13 | none | Không có DMARC: người nhận tự quyết theo heuristic. Từ 2024, Gmail và Yahoo đòi bulk sender (trên 5.000 thư/ngày) có DMARC |
| 14 | none, deliver | `_dmarc.mkt` có **hai** bản ghi `v=DMARC1` (agency marketing thêm một bản mà không gỡ bản cũ). RFC 7489 mục 6.6.3: dừng tìm, DMARC không được áp dụng; không tìm tiếp ở `_dmarc.olist-shop.com.br`. Kết quả: thư giả mạo `mkt.` lọt qua dù tên miền tổ chức có `sp=quarantine`. Một bản ghi thừa vô hiệu hoá cả chính sách: kiểm số bản ghi `_dmarc` trong CI của DNS |

## Hai thay đổi cho Olist Shop

- **Thư 04**: bật "domain authentication" ở ESP để chữ ký mang `d=olist-shop.com.br` (thêm CNAME `s1._domainkey`,
  `s2._domainkey` trỏ sang ESP). Khi đó thư bản tin pass DMARC nhờ DKIM, kể cả khi bị forward nguyên vẹn.
- **Thư 09**: xoay khoá DKIM đúng quy trình: công bố selector mới, cho ESP ký bằng selector mới, **giữ** selector cũ
  trong DNS thêm vài ngày tới vài tuần cho thư đang nằm trong hàng đợi, rồi mới gỡ.
