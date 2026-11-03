# Lời giải: Sáu yêu cầu của khách, bốn trụ

Lời giải mẫu ở `requests.yaml` cạnh tệp này. `why` và `first_step` của bạn không cần giống câu chữ; test chỉ kiểm độ dài
và tính riêng biệt, còn chất lượng tự so với mẫu.

| Id | Trụ | Nghe giống (`looks_like`) | Ai chốt (`decides`) | Module chấp nhận | Bẫy |
| --- | --- | --- | --- | --- | --- |
| `r1` | `field` | `field` | `it`, `security` | `03-airgapped-proxy`, `08-field-troubleshooting` | "Máy có internet rồi" không có nghĩa container trust CA của proxy TLS inspection. Đây là lỗi môi trường khách, không phải bug sản phẩm |
| `r2` | `customer` | `customer` | `exec` | `13-business-roi` | Muốn trả lời bằng demo hay benchmark tốc độ. COO cần **giờ công** so với baseline đo được để quyết ký mở rộng |
| `r3` | `field` | `customer` | `business-owner`, `security` | `09-production-trust` | Nghe như việc giao tiếp (trụ 2), nhưng khách cần bằng chứng: eval suite trên dữ liệu của họ, đo groundedness và citation, ngưỡng nghiệm thu |
| `r4` | `customer` | `field` | `business-owner`, `exec` | `11-discovery-requirements`, `12-scoping-sequencing` | Nghe như việc prototype (module 10, trụ 1). Việc chính là hỏi HĐQT cần thấy gì, rồi chốt must/should/won't |
| `r5` | `design` | `design` | `cto` | `17-system-design-core`, `18-system-design-fde` | Trả lời bằng tên công nghệ. Việc chính là ước lượng (index, QPS), cô lập dữ liệu theo công ty con và phân quyền trong retrieval |
| `r6` | `cloud` | `cloud`, `field` | `cloud-team`, `security` | `19-cloud-iac`, `c1-aws-byoc` | Coi như việc cài đặt thường (trụ 1). Câu hỏi cốt lõi là mô hình quyền BYOC: cross-account role, quyền tối thiểu, thu hồi được, IaC để khách kiểm |

`r3` và `r4` là hai câu "nghe một đằng, việc một nẻo": nhận ra khoảng cách giữa `looks_like` và `pillar` là kỹ năng chính
của bài.

### Vì sao có tập đáp án chấp nhận

`decides` là **người có quyền chốt việc này phía khách**. Ở công ty thật quyền đó có thể nằm ở hai chỗ, nên test nhận mọi
đáp án bảo vệ được; `why` của bạn phải nói vì sao chọn.

- **`r1`: `it` hoặc `security`.** IT là người đổi trust store và cấu hình proxy trong cửa sổ bảo trì. Nhưng ở nhiều bệnh
  viện, thêm một CA vào trust store của container là thay đổi chính sách bảo mật và cần ATTT duyệt. Cả hai đều chặn được việc.
- **`r2`: chỉ `exec`.** COO hỏi để quyết ký mở rộng; không ai khác chốt ngân sách đó.
- **`r3`: `business-owner` hoặc `security`.** Trưởng phòng pháp chế là chủ nghiệp vụ quyết mở cho 40 luật sư dùng
  (`business-owner`); nếu bạn coi câu hỏi "có bịa không" là rủi ro tuân thủ cần pháp chế/ATTT duyệt như một chốt rủi ro,
  `security` cũng bảo vệ được. `exec` thì không: không có dấu hiệu việc này cần ngân sách mới.
- **`r4`: `business-owner` hoặc `exec`.** Giám đốc khối chốt scope cho buổi demo; nhưng HĐQT là người ra quyết định cuối
  cùng mà buổi demo phục vụ, nên `exec` bảo vệ được nếu `why` nói rõ scope được suy ngược từ điều HĐQT cần thấy.
- **`r5`: chỉ `cto`.** Kiến trúc cho cả tập đoàn và năm công ty con.
- **`r6`: `cloud-team` hoặc `security`.** Trưởng phòng cloud quản lý tài khoản AWS và cấp role (`cloud-team`); điều kiện
  "không giữ quyền admin lâu dài, thu hồi được" thường là chính sách của ATTT mà đội cloud thực thi (`security`).
  `looks_like` chấp nhận `cloud` hoặc `field` vì "chạy hệ thống trong tài khoản của chúng tôi" nghe như một việc cài đặt.

`looks_like` của hai bẫy (`r3` → `customer`, `r4` → `field`) chỉ có một đáp án: đó là cách đọc theo từ khoá mà bài muốn bạn
nhận ra và vượt qua.

## Vì sao `first_step` quan trọng hơn nhãn

Gắn đúng nhãn mới là nửa bài. Bước đầu tiên tốt có ba tính chất:

- **Cụ thể và làm được trong 24 giờ**: "hẹn 30 phút với trưởng nhóm vận hành để đo baseline", không phải "tìm hiểu nhu cầu".
- **Lấy thông tin trước khi hứa**: `r1` xin output đầy đủ và tự tái hiện; `r5` ước lượng trước khi vẽ kiến trúc.
- **Đưa quyết định về đúng người**: `r4` hỏi lại người sẽ đứng trước HĐQT; `r6` gửi bản nháp role cho đội cloud của khách duyệt.

## Mở rộng

Thử viết thêm một yêu cầu thứ bảy nằm **giữa** hai trụ (vd. "khách muốn cài lên K8s của họ nhưng chưa biết có GPU không")
và tự hỏi: việc nào phải làm trước để việc kia có ý nghĩa? Đó là sequencing ở module 12.
