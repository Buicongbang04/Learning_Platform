# Hướng làm: đánh giá độ trưởng thành DevOps của team Checkout

Bài Advanced không có một đáp án duy nhất. Phần dưới gồm cách đọc số liệu, một bản đánh giá mẫu, các quyết định cần
cân nhắc và rubric.

## Đọc số liệu

| Metric | Từ ghi chép | Quy đổi | Mức DORA 2024 |
| --- | --- | --- | --- |
| Deployment frequency | 26 deploy/năm | khoảng 0,5 lần/tuần, tức giữa "weekly" và "monthly" | medium |
| Change lead time | median 19 ngày | giữa 1 tuần và 1 tháng | medium |
| Change failure rate | 9/26 | khoảng 35%; cụm gần nhất là low (40%) | low |
| Failed deployment recovery time | median 9 ngày | giữa 1 tuần và 1 tháng | low |

Hai điểm một senior nên ghi:

- **Bảng 2024 là cụm, không phải ngưỡng.** Change failure rate của cụm high (20%) cao hơn cụm medium (10%). Với một
  metric đứng riêng, chọn cụm có giá trị gần nhất và nói rõ cách chọn.
- **Reliability đang đo sai.** Ping 99,95% không thấy 3 lần lỗi thanh toán một phần. Đề xuất SLO theo request cho
  luồng thanh toán (tỉ lệ giao dịch thành công), đo từ metric ứng dụng.

## Bản mẫu

```markdown
## 1. Số liệu DORA

| Metric | Giá trị từ tình huống | Mức (DORA 2024) | Ghi chú đo lường |
| --- | --- | --- | --- |
| Deployment frequency | 26 deploy/năm, khoảng 0,5/tuần | medium | Tin được: đếm từ tag release trong GitLab |
| Change lead time | median 19 ngày | medium | Ước từ Jira; cần đo lại từ commit tới deploy bằng log pipeline |
| Change failure rate | 9/26, khoảng 35% | low | "Trong 48 giờ" bỏ sót lỗi phát hiện muộn; cần gắn incident với release |
| Failed deployment recovery time | median 9 ngày | low | Bị release train và CAB kéo dài; rollback kỹ thuật chỉ mất 2 giờ |

## 2. Đánh giá CALMS

| Trụ cột | Điểm (1-5) | Bằng chứng từ tình huống |
| --- | --- | --- |
| Culture | 2 | Ops là team riêng khác giám đốc, dev xin môi trường bằng ticket 5 ngày, postmortem ghi tên người |
| Automation | 2 | Unit test 45% trong CI nhưng regression tay 3 ngày, rollback chạy tay theo runbook, staging cấu hình tay |
| Lean | 1 | Release train 2 tuần, nhánh release cắt sớm 5 ngày, CAB hằng tuần duyệt cả đổi một biến môi trường |
| Measurement | 2 | Có số deploy và incident nhưng không có SLO, không có metric ứng dụng, ping bỏ sót lỗi thanh toán |
| Sharing | 1 | Dev không xem được log production, script deploy chỉ một người hiểu, action item postmortem không ai nhận |

## 3. Nguyên nhân gốc

1. Kiểm thử phụ thuộc người: regression tay 3 ngày buộc phải gom thay đổi thành release lớn.
2. Khôi phục đắt: rollback tay 2 giờ và cần CAB, nên team chọn sửa trong release sau thay vì rollback.
3. Trách nhiệm vận hành tách khỏi người viết code: dev không thấy log, không trực, không học được từ lỗi.

## 4. Kế hoạch 90 ngày

| Việc | Metric kỳ vọng cải thiện | Cách đo | Rủi ro / đánh đổi |
| --- | --- | --- | --- |
| Tự động hoá rollback một lệnh, diễn tập hai tuần một lần | Failed deployment recovery time | Thời gian từ release lỗi tới khôi phục, lấy từ log pipeline | Migration DB không đảo ngược được; cần quy ước expand/contract |
| Integration test cho 10 luồng thanh toán chính chạy trong CI | Change failure rate, lead time | Tỉ lệ release cần hotfix; số ngày QA tay | Tốn 2 dev trong 6 tuần; test chập chờn làm mất niềm tin |
| CAB chỉ duyệt thay đổi rủi ro cao, thay đổi chuẩn đi qua review ngang hàng | Change lead time, deployment frequency | Số ngày chờ CAB trong lead time | Ban an ninh lo mất kiểm soát; bù bằng audit log tự động |
| SLO tỉ lệ giao dịch thành công 99,5% cho thanh toán, dev xem được dashboard và log | Reliability | Tỉ lệ request thành công theo metric ứng dụng | Thêm việc instrument; cần quyền truy cập log có che dữ liệu thẻ |

## 5. Không làm trong 90 ngày tới

- Chuyển sang Kubernetes: nút thắt là test tay, CAB và rollback, không phải nơi chạy container.
- KPI "deploy hằng ngày": khi change failure rate 35%, deploy nhiều hơn là nhiều sự cố hơn; và KPI sẽ bị chơi gian.
- Tuyển người vào team Ops: thêm người vào hàng đợi ticket không làm hàng đợi biến mất.
```

## Các quyết định cần cân nhắc

- **Thứ tự**: stability trước throughput. Change failure rate 35% và khôi phục 9 ngày nghĩa là deploy nhanh hơn ngay
  bây giờ chỉ làm tăng sự cố. Rollback rẻ và test tự động là điều kiện để rút ngắn release train.
- **CAB**: nghiên cứu Accelerate cho thấy phê duyệt từ bên ngoài team tương quan với lead time dài hơn mà không giảm
  change failure rate. Nhưng CAB không biến mất bằng một mệnh lệnh: thay bằng phân loại thay đổi (chuẩn, thường, khẩn)
  và bằng chứng tự động.
- **Con người**: script deploy chỉ một người hiểu là rủi ro bus factor 1 sắp thành sự thật; ghi lại và đưa vào
  pipeline trước khi anh ấy nghỉ là việc tuần đầu, không chờ kế hoạch lớn.
- **Đo lại trước khi hứa**: số liệu từ Jira và ước lượng phỏng vấn có sai số; kế hoạch tốt có bước đo tự động.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Số liệu DORA | 15 | Quy đổi đúng đơn vị, xếp mức đúng, nêu được giới hạn của bảng cụm và độ tin của từng số |
| CALMS có bằng chứng | 20 | Mỗi điểm dựa trên chi tiết cụ thể trong ghi chép; điểm nhất quán với bằng chứng |
| Nguyên nhân gốc | 20 | Là nguyên nhân (vì sao), không phải triệu chứng; nối được tới ít nhất hai metric |
| Kế hoạch 90 ngày | 25 | Nhỏ, có thứ tự hợp lý (stability trước), mỗi việc có metric, cách đo, rủi ro thật |
| Điều không làm | 10 | Từ chối có lý do Kubernetes và KPI deploy hằng ngày, hoặc lý do tương đương |
| Trình bày cho CTO | 10 | Đọc trong 5 phút, không thuật ngữ thừa, có người chịu trách nhiệm dự kiến |

Dưới 50: thường do kế hoạch là danh sách công cụ cần mua. 50–69: có kế hoạch nhưng không nối với metric. 70–84: đạt.
85 trở lên: thêm được việc khẩn tuần đầu (bus factor), phương án đo lại số liệu, và cách thuyết phục ban an ninh về CAB.
