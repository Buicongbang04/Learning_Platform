# Lời giải: chiến lược test cho dịch vụ ETA

Không có đáp án duy nhất. Câu hỏi thiết kế: **mỗi loại lỗi ML rẻ nhất bị bắt ở đâu, và PR có còn nhanh không?**

## Hướng làm

1. Liệt kê lỗi thật của một dịch vụ ETA: logic feature sai, dữ liệu bẩn lọt vào, model kém đi, model nhạy với thứ tự cột, API đổi schema, container không lên.
2. Gán mỗi loại lỗi cho lớp rẻ nhất bắt được nó. Lớp nào cần train đầy đủ hay dữ liệu thật thì ra khỏi PR.
3. Tính ngân sách: tổng lớp `pr` phải vừa `pr_budget_seconds` (tối đa 600). Đo thật bằng `pytest --durations`, không đoán.
4. Viết chính sách flaky và nói rõ cái gì không bắt được.

## Mẫu

```yaml
service: eta-taxi-nyc
pr_budget_seconds: 600
layers:
  - name: feature-unit
    kind: unit
    what: Hàm build_features trên vài chuyến cố định, kiểm giờ, thứ trong tuần, xử lý thiếu giá trị
    catches: Đổi múi giờ làm feature giờ đón lệch 5 tiếng nhưng model vẫn train được
    runs_on: pr
    budget_seconds: 20
  - name: data-rules
    kind: data
    what: Luật làm sạch trên mẫu nhỏ có đủ 4 loại lỗi thật của NYC TLC, đếm số dòng bị loại
    catches: Thời lượng âm hoặc ngày ngoài tháng lọt vào tập train sau khi sửa luật làm sạch
    runs_on: pr
    budget_seconds: 30
  - name: behavior
    kind: model-behavior
    what: Model nhỏ train trên dữ liệu tổng hợp; đảo thứ tự cột không đổi dự đoán, tăng khoảng cách không giảm ETA
    catches: Preprocessing đổi sang truyền mảng numpy theo vị trí làm dự đoán sai khi cột đổi thứ tự
    runs_on: pr
    budget_seconds: 60
  - name: api-contract
    kind: contract
    what: Schema request và response của /predict, mã 422 cho input sai, trường bắt buộc
    catches: Đổi tên trường PULocationID làm client cũ nhận lỗi sau deploy
    runs_on: pr
    budget_seconds: 40
  - name: quality-gate
    kind: model-quality
    what: Train trên mẫu 200 000 chuyến của một tháng với seed cố định, so MAE với ngưỡng và với model champion
    catches: Đổi tham số hay feature làm MAE tăng 10 phần trăm mà test đơn vị vẫn xanh
    runs_on: nightly
    budget_seconds: 280
  - name: smoke
    kind: smoke
    what: Build image, chạy container, gọi /healthz và một /predict thật
    catches: Dockerfile thiếu thư viện nên container thoát ngay sau khi build thành công
    runs_on: release
    budget_seconds: 240
flaky_policy:
  max_retries: 1
  quarantine: true
  owner: người viết test
  deadline_days: 7
gaps:
  - risk: Concept drift trên dữ liệu production sau khi triển khai
    reason: Test trước merge chỉ thấy dữ liệu đã có; drift cần monitoring sau triển khai (module 09, 10)
  - risk: Độ trễ p99 dưới tải thật
    reason: Cần load test trên hạ tầng giống production, quá chậm và không ổn định cho PR
  - risk: Nhãn về muộn làm số đo chất lượng lệch
    reason: Chỉ biết sau khi chuyến kết thúc; xử lý bằng đánh giá có độ trễ ở giám sát, không phải ở CI
```

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Mỗi lỗi ML rơi vào đúng lớp (unit cho logic, data cho dữ liệu bẩn, behavior cho bất biến model, quality cho hồi quy chất lượng) | 3 |
| `catches` là lỗi thật, cụ thể, và lớp khác không bắt được | 2 |
| Ngân sách PR thực tế (đo bằng `--durations`), train nặng ra khỏi PR | 2 |
| Chính sách flaky: retry tối đa 1, cách ly có hạn sửa và người chịu trách nhiệm | 1 |
| `gaps` trung thực: nói rõ drift, tải, nhãn muộn không bắt được ở CI | 2 |

Lỗi hay gặp: dồn mọi thứ vào "train rồi so accuracy" mà không có test hành vi; nhét quality gate vào PR làm CI 25 phút nên người ta tắt nó; để `retries: 3` khiến test flaky sống mãi; không có gaps vì tin rằng CI bắt được hết.
