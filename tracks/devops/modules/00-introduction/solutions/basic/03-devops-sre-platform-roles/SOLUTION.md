# Lời giải: CALMS, SRE và Platform Engineering qua tình huống

| Câu | Đáp án | Nguyên tắc |
| --- | --- | --- |
| `calms-missing-pillar` | b | Culture đi trước Automation |
| `error-budget-exhausted` | c | Error budget policy của SRE |
| `platform-golden-path` | d | Platform as a product, tự phục vụ |
| `devops-team-silo` | a | Anti-pattern "DevOps team" thành silo |
| `metric-as-target` | b | Định luật Goodhart |
| `postmortem-blameless` | c | Postmortem blameless |
| `lean-batch-size` | a | Lean: batch nhỏ, flow liên tục |
| `toil-example` | d | Định nghĩa toil |
| `failed-change-definition` | c | Failed change phải lên tới production |
| `fake-devops-signals` | a, b, d | Dấu hiệu DevOps danh nghĩa |

## `calms-missing-pillar`: Culture

Công cụ chạy tốt nhưng dev và ops vẫn ngăn nhau bằng ticket, ops không cùng lập kế hoạch: đây là "wall of confusion"
mà DevOps sinh ra để xoá. Thêm bước vào pipeline (a) hay đo build (c) không sửa được việc hai nhóm có mục tiêu khác
nhau. (d) sai hướng: Lean muốn batch **nhỏ hơn**. Mua công cụ trước khi đổi văn hoá là lỗi phổ biến nhất khi "chuyển
đổi DevOps".

## `error-budget-exhausted`: dừng tính năng, ưu tiên reliability

Error budget biến tranh cãi "nhanh hay ổn định" thành quy tắc thoả thuận trước: còn budget thì release, hết thì dồn
sức cho reliability tới khi budget hồi lại. Điều kiện là policy phải được product và lãnh đạo ký trước khi có sự cố.
Hạ SLO giữa chừng (a) làm SLO vô nghĩa; SLO chỉ nên đổi theo chu kỳ review, dựa trên mức người dùng thật sự cần. Thêm
người trực (b) chữa triệu chứng. Tắt alert (d) là che mắt.

## `platform-golden-path`: platform team làm golden path

Platform Engineering xây sản phẩm nội bộ (template pipeline, module OpenTofu, base image đã vá) mà team sản phẩm **tự
dùng**, nên sửa một lỗ hổng ở một chỗ là cả 8 team được hưởng. Golden path là đường được khuyến khích, không phải bắt
buộc: team có lý do chính đáng vẫn đi đường khác và tự chịu phần vận hành. Lập team nhận ticket (a) và CAB (b) tạo
hàng đợi. Checklist (c) dựa vào kỷ luật của 8 team, đúng thứ đã thất bại.

## `devops-team-silo`: silo mới

Đổi tên không đổi luồng công việc: dev vẫn chuyền tay cho một nhóm khác, nhóm đó vẫn không viết code ứng dụng. Mô hình
DevOps Topologies gọi đây là anti-type "DevOps team silo". SRE kiểu Google (b) có SLO, error budget, quyền trả lại
pager cho team dev và giới hạn 50% thời gian cho ops. Platform Engineering (c) cung cấp công cụ tự phục vụ, không làm
hộ. Kubernetes (d) không liên quan tới cách tổ chức.

## `metric-as-target`: Goodhart

"Khi một thước đo trở thành mục tiêu, nó không còn là thước đo tốt." Team sẽ chia một thay đổi thành nhiều deploy nhỏ
vô nghĩa, deploy cả khi không có gì mới. DORA nhấn mạnh: metrics dùng để team tự cải thiện, không để xếp hạng team.
Nhìn bốn metric cùng nhau (throughput và stability), không tối ưu một con số.

## `postmortem-blameless`: hệ thống, không phải con người

Một người gõ nhầm là chuyện chắc chắn xảy ra; câu hỏi là vì sao một lệnh xoá bảng chạy được trên production mà không
có review, backup đã kiểm chưa, khôi phục mất bao lâu. Đổ lỗi (a) khiến lần sau mọi người giấu lỗi. Nhắc nhở (b) không
phải action item. Thu quyền của mọi người (d) chặn cả người đang sửa sự cố.

## `lean-batch-size`: batch nhỏ

80 thay đổi mỗi release thì release lỗi buộc phải tìm kim đáy bể. Batch nhỏ: mỗi deploy ít thay đổi, lỗi khoanh vùng
ngay, rollback rẻ. (b) và (c) làm batch to hơn, lead time dài hơn. (d) thêm hàng đợi. Nghiên cứu DORA nhiều năm cho
thấy throughput và stability đi cùng nhau, không đánh đổi nhau.

## `toil-example`: restart worker mỗi sáng

Thủ công, lặp lại, tự động hoá được (hoặc sửa tận gốc), không để lại giá trị lâu dài, tăng theo số worker. Postmortem
(a) và thiết kế (b) để lại giá trị lâu dài; họp kiến trúc (c) là overhead, không phải toil. Google SRE đặt giới hạn
toil dưới 50% thời gian của SRE.

## `failed-change-definition`: pipeline chặn build

Change failure rate đo thay đổi **lên production** rồi gây lỗi cần can thiệp ngay. Pipeline chặn bản lỗi là pipeline
làm đúng việc, không phải failed change. Rollback, hotfix, fix forward (a, b, d) đều là can thiệp sau khi đã lên
production.

## `fake-devops-signals`: a, b, d

- (a) Chức danh không kèm ownership: dev không xem log production nghĩa là không chịu trách nhiệm cho cái mình viết khi
  nó chạy.
- (b) CAB duyệt mọi thay đổi: nghiên cứu DORA cho thấy phê duyệt bên ngoài team không làm giảm change failure rate mà
  làm chậm lead time; thay bằng review ngang hàng và kiểm tra tự động.
- (c) là dấu hiệu **tốt**: "you build it, you run it" trên nền platform chung.
- (d) "Lỗi do con người" là điểm bắt đầu điều tra, không phải kết luận.
