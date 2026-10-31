# Hướng làm: mô hình DevOps, SRE và Platform cho công ty 60 kỹ sư

Bài Advanced không có một đáp án duy nhất. Phần dưới gồm hướng tư duy, một đề xuất mẫu, các quyết định cần cân nhắc và
rubric.

## Hướng tư duy

1. **Vấn đề không phải thiếu người vận hành, mà là luồng công việc.** 4 người trực cho 8 team là một hàng đợi duy nhất
   (ticket 6 ngày), và một rủi ro con người (2 người sắp nghỉ). Thêm người vào hàng đợi không sửa được hàng đợi.
2. **Ownership về team sản phẩm** ("you build it, you run it"), nhưng chỉ làm được khi cognitive load giảm: platform
   team cung cấp golden path tự phục vụ (template pipeline, base image, module hạ tầng).
3. **SRE đặt ở nơi đắt nhất**: checkout và payment chiếm 80% doanh thu. Một nhóm SRE nhỏ làm việc cùng hai team đó
   (SLO, error budget, capacity, game day), không nhận on-call toàn công ty.
4. **Trả lời CEO**: SRE kiểu Google 10 người cần 10 kỹ sư giỏi cả phần mềm lẫn vận hành, không tuyển thêm được, và
   Google cũng chỉ đặt SRE cho service đủ quan trọng; mọi service khác do team phát triển tự vận hành. Lập 10 người
   từ 60 người hiện có lấy đi gần 1/6 sức làm sản phẩm để tạo một silo mới.

## Đề xuất mẫu

```markdown
## 1. Hiện trạng và vấn đề

- Một hàng đợi ticket 6 ngày cho mọi deploy và hạ tầng: tính năng chậm ra thị trường, team sản phẩm bị chặn.
- 4 người trực on-call cho toàn bộ hệ thống, 2 người xin nghỉ: rủi ro mất người hiểu hệ thống, sự cố kéo dài.
- 5 cách deploy và 23 repo phải vá riêng: lỗ hổng tồn tại lâu, chi phí bảo trì nhân theo số team.
- Checkout và payment không có SLO hay error budget: không biết khi nào nên dừng tính năng để sửa độ ổn định.

## 2. Mô hình đề xuất

| Team | Loại | Số người | Sở hữu | On-call |
| --- | --- | --- | --- | --- |
| 8 team sản phẩm (mỗi dòng một team trong bản thật) | stream-aligned | 6 | Service của mình từ code tới production | Team tự trực service của mình, giờ hành chính trước, 24/7 sau khi qua thí điểm |
| Platform | platform | 5 | Golden path: pipeline mẫu, base image, module OpenTofu, cluster, observability stack | Trực cho nền tảng chung, không trực ứng dụng |
| SRE checkout/payment | enabling | 3 | SLO, error budget policy, capacity, game day cho checkout và payment | Tầng hai cho checkout và payment, cùng trực với hai team đó |

## 3. Ranh giới trách nhiệm

| Việc | Team sản phẩm | Platform | SRE |
| --- | --- | --- | --- |
| Deploy service | Tự bấm qua pipeline mẫu | Duy trì pipeline mẫu | Đặt điều kiện canary cho checkout |
| On-call ứng dụng | Trực chính | Không | Tầng hai cho checkout/payment |
| SLO | Đề xuất và chịu trách nhiệm | Cung cấp công cụ đo | Huấn luyện, review SLO của checkout/payment |
| Hạ tầng mới | Tự tạo qua module có sẵn | Viết và vá module | Review capacity |
| Vá base image | Cập nhật phiên bản trong repo | Phát hành base image đã vá | Không |
| Postmortem | Viết và nhận action item | Tham gia khi lỗi do nền tảng | Điều phối với sự cố lớn, theo dõi action item |

## 4. Lộ trình chuyển đổi

1. Tháng 1: platform team gom 5 cách deploy thành một pipeline mẫu; thí điểm với team catalog. Sang bước 2 khi catalog
   tự deploy không cần ticket trong 4 tuần.
2. Tháng 2–3: chuyển on-call catalog và search cho chính hai team, có runbook và alert đã dọn. DevOps team cũ vẫn là
   tầng hai. Sang bước 3 khi số page ngoài giờ mỗi tuần ổn định.
3. Tháng 4–6: SRE cùng checkout/payment đặt SLO và error budget policy; lần lượt chuyển các team còn lại; dừng nhận
   ticket deploy.

## 5. Rủi ro và cách đo thành công

| Rủi ro hoặc mục tiêu | Dấu hiệu / metric | Cách xử lý |
| --- | --- | --- |
| Team sản phẩm quá tải on-call | Số page ngoài giờ mỗi người mỗi tuần, khảo sát | Dọn alert không hành động được, giờ hành chính trước |
| Platform thành hàng đợi mới | Thời gian chờ ticket platform, tỉ lệ việc tự phục vụ | Đo platform như sản phẩm: adoption, khảo sát developer |
| Mất tốc độ trong lúc chuyển | Lead time và deployment frequency từng team | Chuyển từng team, giữ tầng hai cũ tới khi ổn |
```

Bản thật nên tách 8 team sản phẩm thành 8 dòng; bản mẫu gộp để ngắn (test chấp nhận cả hai, miễn tổng số người không
vượt 60).

## Các quyết định cần cân nhắc

- **Platform team bao nhiêu người**: đủ để làm sản phẩm (4–6 người), không lớn tới mức thành bộ phận vận hành mới.
  Đo platform bằng mức độ team sản phẩm tự dùng được, không đo bằng số ticket đóng.
- **SRE là enabling hay team riêng trực tầng hai**: nhóm nhỏ, làm việc cùng team có rủi ro cao nhất, có quyền trả lại
  pager khi service vượt error budget nhiều lần (cách Google làm). Không làm SRE cho mọi thứ.
- **On-call chuyển thế nào**: giờ hành chính trước, có shadow, alert phải "actionable" trước khi giao.
- **Người của DevOps team cũ đi đâu**: phần lớn vào platform (họ hiểu hạ tầng nhất), một người vào SRE. Không giải tán.
- **Không big bang**: mỗi bước có điều kiện chuyển tiếp đo được.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Chẩn đoán | 15 | Vấn đề viết theo hậu quả kinh doanh, nhận ra hàng đợi và rủi ro con người là gốc |
| Mô hình team | 25 | Loại team đúng nghĩa Team Topologies; ownership rõ; quy mô khả thi với 60 người |
| Ranh giới trách nhiệm | 20 | Không việc nào "mọi người cùng lo"; platform không làm hộ, SRE không trực mọi thứ |
| Lộ trình | 20 | Từng bước, có điều kiện chuyển tiếp đo được, có lưới an toàn khi chuyển on-call |
| Rủi ro và metric | 10 | Rủi ro thật (quá tải on-call, platform thành hàng đợi) và metric phát hiện sớm |
| Trả lời CEO | 10 | Lập luận có số liệu từ đề, đưa ra phương án thay thế chứ không chỉ từ chối |

Dưới 50: thường do đề xuất "lập team SRE" hoặc "thêm người vào DevOps team". 70–84: đạt. 85 trở lên: có cách đo
platform như sản phẩm và kế hoạch cho người của team cũ.
