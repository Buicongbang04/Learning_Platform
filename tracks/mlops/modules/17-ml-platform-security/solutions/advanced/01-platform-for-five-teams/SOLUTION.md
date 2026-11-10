# Hướng làm và rubric: nền tảng ML cho 5 đội

Không có một đáp án đúng. Dưới đây là một hướng làm hợp lý cho đề, rồi rubric 100 điểm. Điều được chấm là lập luận: mỗi quyết định có lý
do, có phương án đã loại, và gắn với mục tiêu có số của ban lãnh đạo.

## Hướng làm mẫu (tóm tắt)

**Quyền và không gian tên.** Mỗi đội một namespace Kubernetes (`<team>-prod`, `<team>-train`) với ResourceQuota và LocalQueue Kueue riêng
(module 15), một không gian tên trên registry (`<team>-*`, bài Basic 02), một nhóm trong IdP. Đội chỉ đăng ký và deploy trong không gian
của mình; đội nền tảng là chủ cổng, không phải chủ model. Đội fraud tách hẳn: namespace và node pool riêng trong phạm vi PCI DSS, model
huấn luyện trên dữ liệu thẻ mang tag `data_classification=pci`, cổng deploy từ chối đưa chúng ra ngoài phạm vi đó.

**Golden path.** Template Copier (bài Basic 01) sinh dự án có CI chuẩn: test, huấn luyện tái lập, lưu safetensors hay định dạng gốc của
thư viện, ký trong CI, quét, đăng ký qua cổng. Self-service: đội tự tạo dự án, tự đăng ký model hợp lệ, tự deploy canary trong namespace
của mình. Cần người duyệt: lần đầu một model ra production (model card, SLO), thay đổi quyền, ngoại lệ.

**Chuỗi cung ứng.** Allowlist định dạng + modelscan ở cổng đăng ký (bài Intermediate 01); ký bằng khoá trong KMS của CI, verify ở init
container của pod serving (bài Intermediate 02 và 04); SBOM sinh từ image và lưu cạnh model (bài Intermediate 03). Model gốc từ Hugging Face
của đội search: mirror nội bộ có ghim revision (commit hash), chỉ nhận safetensors, quét khi nhập. Model pickle của pricing: ngoại lệ có
hạn (2 quý), trong thời gian đó chỉ nhận pickle đã qua modelscan và có trong `scanned_files`, kèm kế hoạch chuyển sang định dạng an toàn.

**Chi phí.** Nhãn `team`, `model`, `cost_center` bắt buộc qua admission policy và template; OpenCost cho chi phí theo pod; showback hàng
tháng có dòng idle và `UNALLOCATED` (bài Basic 03). Đòn bẩy giảm 25% (cụm chạy 30%): rightsizing request theo p95 dùng thật; scale-to-zero
và autoscale theo tải cho serving ít lưu lượng (KEDA, module 14); GPU huấn luyện của search qua hàng đợi Kueue thay vì giữ node (8 GPU mà
chỉ dùng 6 giờ mỗi tuần là ứng viên rõ nhất để chuyển sang GPU theo đợt); giảm số node khi đã bin-pack. Ước tính: đưa mức dùng từ 30% lên
khoảng 50% bằng rightsizing và autoscale đã cắt được khoảng 40% số node cần thiết, đủ đạt 25% sau khi trừ headroom.

**Ngoại lệ và lộ trình.** Quý 1: quy ước registry, nhãn chi phí, showback, cổng quét và ký cho model mới; đội ads là đội đầu tiên đi trọn
golden path (đội mới, ít nợ cũ, cần đi nhanh: chỉ số là thời gian tới production). Quý 2: chuyển eta (đội lâu đời, đổi script deploy riêng
lấy cổng chung, giữ quyền tự vận hành trong namespace), chuyển pickle của pricing, chargeback khi `UNALLOCATED` dưới 5%. Chỉ số: % model
production đi qua cổng, % chi phí có chủ, thời gian từ dự án mới tới production, số model pickle còn lại.

**Vận hành nền tảng.** SLO của chính nền tảng (cổng đăng ký khả dụng, thời gian từ merge tới canary), trực luân phiên trong 3 người, runbook
cho "cổng chặn nhầm" (ai được bypass, ghi log, có hạn). Với 3 người: dùng dịch vụ managed cho phần không phải lợi thế (Kubernetes managed,
object storage, có thể registry managed), tự xây lớp mỏng (quy ước, template, cổng).

## Rubric (100 điểm)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Mục tiêu có số và ngoài phạm vi | 10 | Chuyển ba mục tiêu của lãnh đạo thành chỉ số đo được; nói rõ những gì không làm |
| Mô hình quyền | 15 | Không gian tên theo đội ở registry, cluster và dữ liệu; ai duyệt cái gì; tách phạm vi PCI của fraud có cơ chế ép (không chỉ quy ước) |
| Golden path và self-service | 15 | Đường đi cụ thể từ dự án mới tới production; phân biệt rõ tự làm và cần duyệt; template được cập nhật về sau thế nào |
| Chuỗi cung ứng model | 20 | Định dạng an toàn là mặc định; quét và ký ở đúng chỗ; verify gần lúc nạp; xử lý model gốc bên ngoài; kế hoạch có hạn cho pickle cũ |
| Chi phí | 15 | Nhãn bắt buộc có cơ chế ép; showback trước chargeback; idle được hiện ra; ít nhất hai đòn bẩy có ước tính số để đạt 25% |
| Ngoại lệ và lộ trình | 10 | Ngoại lệ có hạn và điều kiện thoát; thứ tự đội có lý do; chỉ số theo quý |
| Vận hành và build vs buy | 10 | SLO của nền tảng, ai trực, cách bypass có kiểm soát; phần mua và phần tự xây hợp với 3 người |
| Giới hạn và rủi ro | 5 | Nêu giả định, rủi ro chính trị (đội lâu đời phản đối), chỗ cần dữ liệu thật |

Mức đạt 70. Trừ điểm: chỉ liệt kê công cụ mà không có quyết định (-15); không ai sở hữu ngoại lệ (-5); "mọi đội phải chuyển ngay trong quý 1"
với 3 kỹ sư nền tảng (-10); chargeback ngay khi chưa đo được chi phí theo đội (-5).

## Câu đào sâu của người review

- Đội eta từ chối bỏ script deploy riêng vì "chạy ổn 3 năm nay". Bạn thuyết phục thế nào, và nếu không được thì sao?
- Cổng quét chặn nhầm một model lúc 2 giờ sáng khi đang có sự cố. Ai được bypass, ghi lại ở đâu, sau đó làm gì?
- Đội search muốn dùng một model mới ra trên Hugging Face ngay hôm nay. Đường nhanh nhất mà vẫn an toàn là gì?
- Giảm 25% chi phí nhưng đội fraud cần headroom cho mùa cao điểm. Bạn tách ngân sách headroom ra sao để nó không bị cắt nhầm?
- Kẻ tấn công có quyền push vào repo của một đội. Lớp nào trong thiết kế của bạn còn chặn được model độc, lớp nào không?
