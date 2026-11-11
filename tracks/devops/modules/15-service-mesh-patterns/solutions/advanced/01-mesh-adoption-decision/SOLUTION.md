# Lời giải: có dùng service mesh cho Olist Marketplace không

Bài không có một đáp án duy nhất. `DECISION.md` trong thư mục này là một lời giải qua test (chọn Linkerd cho năm service PCI trước),
không phải đáp án bắt buộc. Rubric dưới đây chấm lập luận.

## Hướng làm

1. **Tách bắt buộc khỏi nên có.** mTLS có xác thực hai chiều cho 5 service trong 6 tháng là bắt buộc; canary và metrics theo cặp là
   nên có. Phương án nào không đạt phần bắt buộc thì loại.
2. **Tính giá thật của "không dùng mesh".** cert-manager cấp chứng chỉ được, nhưng TLS hai chiều phải cấu hình trong code hay server
   của từng service (nhiều ngôn ngữ), xoay chứng chỉ không làm rớt kết nối, và kiểm toán cần log danh tính bên gọi. Với 5 service và
   2 người platform, đây là vài tháng công.
3. **So mesh theo ràng buộc của tổ chức này.** 2 người platform chưa quen Envoy, 12 GiB còn trống: Linkerd (ít cấu hình, proxy 3-4 MiB
   đo được trên `devops-lab`) hay Istio ambient (RAM không tỉ lệ với số pod nhưng mới hơn, ít kinh nghiệm) là hai ứng viên mạnh. Istio
   sidecar mạnh ở L7 nhưng tốn RAM gấp nhiều lần và cần người chuyên. Consul hợp khi nhiều VM; ở đây chỉ một VM.
4. **VM**: không nhất thiết đưa vào mesh. Ingress có mTLS ở cổng vào (chứng chỉ client), cộng AuthorizationPolicy cho `ledger` chỉ nhận
   từ Ingress là đủ cho một connector.
5. **RAM**: số proxy nhân RAM mỗi proxy, cộng control plane, cộng dự phòng cho lúc tải cao (proxy dùng thêm bộ nhớ theo số kết nối),
   cộng CNI theo số node.
6. **Rollout**: staging, một namespace, từng service; đo p99 thêm, tỉ lệ thành công; policy chặn đến sau cùng; rollback đã tập.
7. **Vận hành**: trust anchor giữ ngoài cluster, issuer xoay theo lịch, cảnh báo hạn chứng chỉ; nâng cấp proxy cần restart pod.

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Yêu cầu | 1 | Phân biệt bắt buộc và nên có; nhắc PCI, mTLS, VM, 2 người platform, giới hạn RAM |
| Phương án không mesh | 1 | Được phân tích nghiêm túc, chi phí nằm ở code và vận hành chứng chỉ |
| So sánh công cụ | 2 | Ít nhất hai mesh, so theo ràng buộc của tổ chức này (không chép bảng tính năng chung chung); RAM có nguồn |
| Quyết định | 1 | Rõ ràng, khớp phần so sánh, xử lý được VM |
| Chi phí | 1 | Phép tính đúng, có dự phòng cho Black Friday, nằm trong 12 GiB |
| Rollout | 2 | Theo vùng ảnh hưởng, có số đo để đi tiếp, policy chặn đến sau, rollback cụ thể đã tập |
| Vận hành và rủi ro | 1 | Ai giữ trust anchor, lịch xoay, nâng cấp; injector chết, chứng chỉ hết hạn; đường lui |
| Khi nào xem lại | 1 | Điều kiện đo được (số pod, nhu cầu L7, cluster thứ hai), không chung chung |

Dưới 7 điểm: thường là bỏ qua phương án không mesh, rollout một bước, hay không nói ai giữ chứng chỉ gốc.

## Lỗi hay gặp

- Chọn Istio vì "phổ biến nhất" mà không tính 2 người platform phải vận hành nó.
- Bật policy deny cho cả namespace ngay ngày đầu: mọi bên gọi chưa được liệt kê bị chặn, sự cố tự gây.
- Quên rằng nâng cấp proxy sidecar cần restart pod, nên lịch nâng cấp đụng lịch deploy của team sản phẩm.
- Tính RAM chỉ cho control plane, quên proxy trong từng pod.
