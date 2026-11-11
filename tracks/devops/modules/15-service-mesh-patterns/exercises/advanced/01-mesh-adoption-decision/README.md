---
title: Có dùng service mesh cho Olist Marketplace không, và dùng cái nào
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Tài liệu quyết định, 8 phần
  - path: tests/test_decision.py
    note: Kiểm khung tài liệu và phép tính RAM; không sửa
  - path: tests/fixtures/DECISION.good.md
    note: Ví dụ đạt (tổ chức khác)
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/advanced/01-mesh-adoption-decision -q
---

## Mục tiêu

Ra quyết định đưa (hay không đưa) service mesh vào một tổ chức như người làm platform: bắt đầu từ yêu cầu thật, so sánh cả phương án
không dùng mesh, tính tiền bằng RAM và công vận hành, có kế hoạch rollout từng bước với đường quay lui, và nói trước khi nào quyết định
phải xem lại.

## Đề bài

Olist Shop đã lớn thành **Olist Marketplace**:

- 18 service, khoảng 140 pod production trên một cluster Kubernetes 8 node; staging là cluster riêng nhỏ hơn. Phần RAM còn trống ở
  production khoảng **12 GiB** (12288 MiB).
- **PCI DSS**: năm service trong luồng thanh toán (`checkout`, `payments`, `fraud`, `ledger`, `refunds`) phải mã hoá và xác thực hai chiều
  (mTLS) trong 6 tháng; kiểm toán muốn bằng chứng ai gọi ai.
- Team `checkout` muốn canary theo tỉ lệ traffic (5%, 25%, 100%).
- Một connector ERP cũ chạy trên VM ngoài cluster, gọi `ledger` qua HTTP.
- 3 team sản phẩm (khoảng 15 dev), **2 người platform**; chưa ai vận hành Envoy hay Istio.
- Prometheus, Grafana, Loki, Jaeger đã có (module 13), nhưng chưa có số liệu theo từng cặp service.
- Black Friday tải gấp 10 lần ngày thường trong vài giờ.

Viết `starter/DECISION.md`, giữ tám tiêu đề `## 1.` tới `## 8.`:

| Phần | Nội dung | Test kiểm |
| --- | --- | --- |
| 1. Bối cảnh và yêu cầu | Yêu cầu, ràng buộc bạn coi là quan trọng | ≥4 gạch đầu dòng; nhắc mTLS và PCI |
| 2. Phương án | Bảng cột `Phương án`, `mTLS`, `Traffic`, `Observability`, `Vận hành`, `RAM ước tính (MiB)` | ≥4 dòng; có một phương án không dùng mesh (tên chứa "không dùng mesh"); ≥2 công cụ trong Linkerd, Istio, Consul, Cilium, Envoy; RAM là số |
| 3. Quyết định | Chọn gì và vì sao | ≥3 gạch đầu dòng; nêu một phương án đã so sánh |
| 4. Chi phí tài nguyên | Bảng cột `Thành phần`, `Số lượng`, `MiB mỗi cái`, `Tổng (MiB)`, rồi dòng `Tổng: <số> MiB` | ≥3 dòng; mỗi dòng số lượng nhân MiB bằng tổng (sai số 1%); cộng các dòng khớp dòng Tổng; Tổng ≤ 12288 |
| 5. Kế hoạch rollout | Các bước theo thứ tự | ≥5 bước đánh số; có cách quay lui (rollback) |
| 6. Vận hành và trách nhiệm | Ai lo gì sau khi cài | ≥3 gạch đầu dòng; nói ai lo chứng chỉ (trust anchor, issuer) và nâng cấp |
| 7. Rủi ro và đường lui | Điều có thể sai và cách rút | ≥3 gạch đầu dòng; nhắc đường lui (hay gỡ mesh) |
| 8. Khi nào xem lại | Điều kiện kích hoạt xem lại | ≥2 gạch đầu dòng |

Số RAM lấy từ số đo thật khi được: mục 1 và 5 của README module có số đo Linkerd trên `devops-lab` (control plane, mỗi proxy); với
công cụ khác, lấy từ tài liệu chính thức hay benchmark công khai và ghi nguồn. "Không dùng mesh" cũng là một quyết định hợp lệ nếu lập
luận vững. Test còn chạy bộ kiểm trên ba fixture (khung, bản yếu, bản đạt của tổ chức khác) để chứng minh bắt được lỗi.

## Tiêu chí đạt

- Test pass.
- Rubric trong `solutions/advanced/01-mesh-adoption-decision/SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Nếu kiểm toán chỉ cần mã hoá chứ không cần xác thực hai chiều thì quyết định có đổi không?", "Proxy của bạn chọn
  làm p99 tăng 20 ms ở Black Friday thì làm gì trong 10 phút đầu?", "Connector ERP trên VM được bảo vệ thế nào?".

## Gợi ý

### Gợi ý 1

Bắt đầu từ yêu cầu bắt buộc (mTLS cho 5 service trong 6 tháng) rồi mới tới thứ "nên có" (canary, metrics theo cặp). Phương án không
dùng mesh phải được tính nghiêm túc: cái giá của nó nằm ở code của từng service và công xoay chứng chỉ, không ở RAM.

### Gợi ý 2

Rollout an toàn đi theo vùng ảnh hưởng: staging, rồi một namespace, rồi từng service; policy chặn đến sau cùng, khi đã thấy đủ bên gọi
trong metrics. Đường lui phải tập trước, không chỉ viết ra. Mục 4 và 5 của README module có bảng so sánh và các điểm khi nào không nên
dùng mesh.
