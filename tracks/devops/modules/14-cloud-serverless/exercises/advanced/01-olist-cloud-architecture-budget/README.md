---
title: Chọn nhà cung cấp và kiến trúc cho Olist Shop với 300 USD mỗi tháng
level: advanced
services: []
files:
  - path: starter/ARCHITECTURE.md
    note: Tài liệu quyết định, 8 phần
  - path: tests/test_architecture.py
    note: Kiểm khung tài liệu và phép cộng chi phí; không sửa
  - path: tests/fixtures/ARCHITECTURE.good.md
    note: Ví dụ đạt (hệ thống khác)
run:
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/advanced/01-olist-cloud-architecture-budget -q
---

## Mục tiêu

Ra một quyết định cloud như tech lead: so sánh nhà cung cấp và kiểu kiến trúc theo ràng buộc thật (độ trễ, luật dữ liệu, người vận hành,
tiền), ghi lại vì sao chọn, chi phí từng khoản, ai chịu trách nhiệm phần nào, và đường lui khi quyết định sai.

## Đề bài

Olist Shop rời máy chủ thuê hiện tại. Ràng buộc:

- **Ngân sách** 300 USD mỗi tháng cho production và staging (không tính lương); Black Friday được vượt 20% trong một tuần.
- **Team**: 3 dev, 1 DevOps bán thời gian, không có ca trực đêm cố định.
- **Tải**: 3 triệu request API mỗi tháng, trung bình 1 đến 2 request/giây, đỉnh 40 request/giây; job tính doanh thu 40 phút mỗi đêm;
  event payment qua hàng đợi như bài Intermediate 01.
- **Dữ liệu**: Postgres 30 GB, tăng 2 GB mỗi tháng; ảnh sản phẩm 150 GB, khoảng 1 TB tải ra mỗi tháng.
- **Khách** ở Brazil, chủ yếu São Paulo: p95 dưới 300 ms. LGPD: ưu tiên dữ liệu cá nhân nằm ở Brazil.
- **RPO** 1 giờ, **RTO** 4 giờ.

Viết `starter/ARCHITECTURE.md`, giữ tám tiêu đề `## 1.` tới `## 8.`:

| Phần | Nội dung | Test kiểm |
| --- | --- | --- |
| 1. Bối cảnh và ràng buộc | Ràng buộc bạn coi là quan trọng | ≥4 gạch đầu dòng; nhắc 300 (USD) và RPO/RTO |
| 2. Phương án | Bảng cột `Phương án`, `Nhà cung cấp`, `Chi phí/tháng (USD)`, `Vận hành`, `Rủi ro` | ≥3 dòng; ≥3 nhà cung cấp khác nhau trong AWS, Azure, GCP, DigitalOcean, Alibaba, Hetzner, Contabo, Heroku, Cloudflare, Vercel, Netlify; chi phí là số |
| 3. Quyết định | Chọn gì, ở region nào, vì sao | ≥3 gạch đầu dòng; nhắc một nhà cung cấp đã so sánh và chữ "region" |
| 4. Kiến trúc | Sơ đồ và luồng | Có khối ` ```mermaid ` |
| 5. Chi phí ước tính | Bảng cột `Hạng mục`, `Đơn giá`, `Lượng`, `Thành tiền (USD)`, rồi dòng `Tổng: <số> USD` | ≥5 hạng mục; thành tiền là số; tổng các hạng mục khớp dòng Tổng (sai số 2%); Tổng ≤ 300; có hạng mục egress |
| 6. Trách nhiệm chung | Shared responsibility cho kiến trúc đã chọn | ≥3 gạch đầu dòng; nói phần của "nhà cung cấp" và phần của team |
| 7. Rủi ro, lock-in và đường lui | Điều có thể sai và cách rút | ≥3 gạch đầu dòng; nhắc lock-in và đường lui |
| 8. Khi nào xem lại | Điều kiện kích hoạt xem lại quyết định | ≥2 gạch đầu dòng |

Số tiền viết không có dấu phân cách hàng nghìn (`222,50` hay `222.50`). Giá lấy từ trang giá hay calculator của nhà cung cấp, ghi tháng lấy
giá; số gần đúng là được, rubric chấm cách lập luận chứ không chấm từng xu. Test còn chạy bộ kiểm tài liệu trên ba fixture (khung, bản yếu,
bản đạt của một hệ thống khác) để chứng minh bắt được lỗi.

## Tiêu chí đạt

- Test pass.
- Rubric trong `solutions/advanced/01-olist-cloud-architecture-budget/SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Nếu ngân sách giảm còn 150 USD, bạn bỏ gì trước?", "Region bạn chọn chết cả ngày thì sao?", "Sáu tháng nữa muốn rời nhà
  cung cấp này thì mất bao lâu?".

## Gợi ý

### Gợi ý 1

Bắt đầu từ ràng buộc loại trừ: nhà cung cấp nào không có region ở Brazil? Với các phương án còn lại, chi phí lớn thường nằm ở thứ chạy cả
ngày (database, load balancer, máy, NAT) chứ không ở request; region São Paulo của các hãng lớn đắt hơn region Mỹ đáng kể.

### Gợi ý 2

Serverless không tự động rẻ: tải đều cả ngày thì container hay VM thường rẻ hơn; job 40 phút không chạy được trên Lambda. Egress (dữ liệu ra
Internet) là khoản hay bị quên; CDN của nhiều hãng có phần miễn phí. Mục 6 của README module có bảng so sánh nhà cung cấp.
