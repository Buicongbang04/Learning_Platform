# Lời giải: Sáu yêu cầu của khách, bốn trụ

Lời giải mẫu ở `requests.yaml` cạnh tệp này. `why` và `first_step` của bạn không cần giống câu chữ; test chỉ kiểm độ dài
và tính riêng biệt, còn chất lượng tự so với mẫu.

| Id | Trụ | Nghe giống (`looks_like`) | Ai quyết (`decides`) | Module chấp nhận | Bẫy |
| --- | --- | --- | --- | --- | --- |
| `r1` | `field` | `field` | `it` | `03-airgapped-proxy`, `08-field-troubleshooting` | "Máy có internet rồi" không có nghĩa container trust CA của proxy TLS inspection. Đây là lỗi môi trường khách, không phải bug sản phẩm; người đổi trust store và proxy là IT |
| `r2` | `customer` | `customer` | `exec` | `13-business-roi` | Muốn trả lời bằng demo hay benchmark tốc độ. COO cần **giờ công** so với baseline đo được để quyết ký mở rộng |
| `r3` | `field` | `customer` | `business-owner` | `09-production-trust` | Nghe như việc giao tiếp (trụ 2), nhưng khách cần bằng chứng: eval suite trên dữ liệu của họ, đo groundedness và citation, ngưỡng nghiệm thu. Trưởng phòng pháp chế quyết có mở cho 40 người không |
| `r4` | `customer` | `field` | `business-owner` | `11-discovery-requirements`, `12-scoping-sequencing` | Nghe như việc prototype (module 10, trụ 1). Việc chính là hỏi HĐQT cần thấy gì, rồi chốt must/should/won't với giám đốc khối, người quyết scope và đứng trước HĐQT |
| `r5` | `design` | `design` | `cto` | `17-system-design-core`, `18-system-design-fde` | Trả lời bằng tên công nghệ. Việc chính là ước lượng (index, QPS), cô lập dữ liệu theo công ty con và phân quyền trong retrieval |
| `r6` | `cloud` | `cloud` | `cloud-team` | `19-cloud-iac`, `c1-aws-byoc` | Coi như việc cài đặt thường (trụ 1). Câu hỏi cốt lõi là mô hình quyền BYOC: cross-account role, quyền tối thiểu, thu hồi được, IaC để đội cloud của khách kiểm |

`r3` và `r4` là hai câu "nghe một đằng, việc một nẻo": nhận ra khoảng cách giữa `looks_like` và `pillar` là kỹ năng chính
của bài. `decides` nhắc rằng mọi việc của FDE phục vụ một quyết định của một người cụ thể phía khách; `first_step` tốt
thường đi thẳng tới người đó.

## Vì sao `first_step` quan trọng hơn nhãn

Gắn đúng nhãn mới là nửa bài. Bước đầu tiên tốt có ba tính chất:

- **Cụ thể và làm được trong 24 giờ**: "hẹn 30 phút với trưởng nhóm vận hành để đo baseline", không phải "tìm hiểu nhu cầu".
- **Lấy thông tin trước khi hứa**: `r1` xin output đầy đủ và tự tái hiện; `r5` ước lượng trước khi vẽ kiến trúc.
- **Đưa quyết định về đúng người**: `r4` hỏi lại người sẽ đứng trước HĐQT; `r6` gửi bản nháp role cho đội cloud của khách duyệt.

## Mở rộng

Thử viết thêm một yêu cầu thứ bảy nằm **giữa** hai trụ (vd. "khách muốn cài lên K8s của họ nhưng chưa biết có GPU không")
và tự hỏi: việc nào phải làm trước để việc kia có ý nghĩa? Đó là sequencing ở module 12.
