---
title: "Sự cố: SLO xanh nhưng người dùng phàn nàn"
level: intermediate
services: []
files:
  - path: starter/slis.py
    note: Code tính SLI đang chạy ở production, tìm và sửa
  - path: tests/fixtures/slis.original.py
    note: Bản gốc, test hồi quy dùng
  - path: tests/test_slis.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/03-incident-green-slo-complaints -q
---

## Mục tiêu

Chẩn đoán một SLO báo "đạt" trong khi người dùng đang gặp sự cố, và sửa cách đo để con số trên dashboard là trải nghiệm của
người dùng chứ không phải của một thành phần nào đó.

## Đề bài

Thứ Hai, 18:00. Trong hai giờ qua:

- Bộ phận hỗ trợ nhận hơn 300 phản ánh "app quay vòng mãi rồi báo không lấy được giờ xe tới". Điểm đánh giá trên store giảm.
- Đội mobile báo client ghi nhận khoảng 4-5% yêu cầu ETA thất bại, và nhiều yêu cầu thành công chậm thấy rõ. Client hủy yêu cầu sau
  1 giây.
- Dashboard SLO của service ETA: khả dụng 99.92% (mục tiêu 99.5%), tỉ lệ trả lời trong 300 ms là 100% (mục tiêu 99%). Cả hai xanh,
  không alert nào bắn, error budget gần như nguyên vẹn.
- Không có deploy nào trong ngày. Log ứng dụng gần như không có dòng lỗi.

`starter/slis.py` là code đang tính hai SLI đó từ trace phân tán. Mỗi trace là một yêu cầu: `{"id", "spans": [...]}`, mỗi span có
`name`, `parent` (tên span cha, `None` nếu không có), `status` (mã HTTP) và `duration_ms`. Test sinh 20 000 trace của buổi chiều hôm
nay (và của một ngày bình thường) cùng với kết quả mà **client** ghi nhận cho từng yêu cầu.

Sửa `starter/slis.py`. Giữ nguyên chữ ký hàm, giá trị trả về và `TARGETS`. Luật mà test kiểm:

- `availability(traces)` và `latency_ok(traces)` trả `(giá trị, số sự kiện trong mẫu số)`. Giá trị phải bằng đúng tỉ lệ client ghi
  nhận: tỉ lệ yêu cầu thành công (mã dưới 500) trên mọi yêu cầu client gửi, và trong các yêu cầu thành công, tỉ lệ trả lời trong
  300 ms. Số sự kiện là mẫu số tương ứng.
- `slo_report` báo không đạt cả hai SLO cho buổi chiều hôm nay, và đạt cả hai cho ngày bình thường với giá trị khớp client.
- Không có trace nào thì giá trị `None`, số sự kiện 0 và không đạt.
- Test hồi quy chứng minh bản gốc (`tests/fixtures/slis.original.py`) báo xanh trên đúng dữ liệu của buổi chiều hôm nay, trong khi
  client thấy dưới 97% ở cả hai chỉ số.

Ghi lại một câu nguyên nhân gốc và một thay đổi để loại sự cố cùng loại không lặp lại; đối chiếu với `SOLUTION.md` sau khi xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/03-incident-green-slo-complaints -q` pass.
- Bạn giải thích được vì sao log ứng dụng gần như không có lỗi trong khi client thấy 4-5% thất bại.
- Bạn nêu được một cách kiểm tra định kỳ để phát hiện SLI lệch khỏi trải nghiệm thật trước khi khách hàng phàn nàn.

## Gợi ý

### Gợi ý 1

So số sự kiện trong mẫu số của dashboard với số yêu cầu client gửi. Nếu khác nhau, những yêu cầu nào đã không được đếm?

### Gợi ý 2

In vài trace mà client ghi nhận là thất bại. Với từng span trong trace đó, span ấy "nghĩ" yêu cầu thành công hay thất bại, và mất bao lâu?
