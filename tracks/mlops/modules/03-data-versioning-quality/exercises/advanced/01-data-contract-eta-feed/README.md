---
title: Viết data contract giữa đội data và đội ML cho feed chuyến taxi
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Biến một sự cố "đội data đổi dữ liệu, đội ML không biết" thành một hợp đồng cụ thể, kiểm được bằng máy và có chủ sở hữu.

## Đề bài

Bối cảnh: đội Data Platform cung cấp bảng `trips_clean` (nguồn NYC TLC) cho ba bên dùng: dịch vụ dự đoán ETA, báo cáo doanh thu hằng ngày và
một job huấn luyện lại hằng tuần. Tuần trước đội data đổi `trip_distance` từ dặm sang km và thêm `airport_fee` kiểu chuỗi; ETA lệch 60% suốt hai ngày trước khi ai đó
phát hiện, và job huấn luyện lại vẫn chạy xanh.

Viết một tài liệu `contract.md` (hoặc `contract.yaml` kèm giải thích) ngắn gọn dưới 2 trang gồm:

1. **Schema**: tên cột, kiểu, đơn vị, nullable hay không, giá trị hợp lệ, cho 8 cột ETA cần.
2. **Ngữ nghĩa và SLA**: độ trễ tối đa, múi giờ, tỉ lệ dòng lỗi tối đa được chấp nhận và cách đo, độ đầy đủ theo ngày.
3. **Quy tắc thay đổi**: thế nào là breaking và non-breaking, versioning (SemVer hay theo ngày), thời gian báo trước, đường chuyển tiếp song song hai phiên bản.
4. **Thực thi**: ai chạy kiểm tra, ở đâu (CI của đội data, ở cửa vào pipeline ML, hay cả hai), hành vi khi vi phạm (chặn, cách ly, cảnh báo), công cụ (Pandera, GE, test dbt) và vì sao.
5. **Sở hữu và leo thang**: ai ký, ai trực, vi phạm thì gọi ai trong bao lâu.
6. Một đoạn nói rõ ba kiểu thay đổi của sự cố trên rơi vào mục nào của quy tắc thay đổi và contract này đã chặn chúng ở đâu.

Không có đáp án duy nhất. Tự chấm bằng rubric trong `SOLUTION.md` sau khi viết.

## Tiêu chí đạt

- Đủ sáu mục, mỗi mục có ít nhất một quyết định cụ thể (con số, tên người/vai trò, tên công cụ), không chỉ là lời chung chung.
- Schema có đơn vị cho mọi cột số và nêu rõ cột nào cho phép null.
- Có phân loại breaking / non-breaking kèm ít nhất ba ví dụ thật từ bảng taxi.
- Chỉ ra điểm thực thi ở **phía nhà cung cấp** (trước khi phát hành), không chỉ ở phía người dùng.

## Gợi ý

### Gợi ý 1

Bắt đầu từ sự cố và đi ngược: lỗi nào máy có thể bắt, ở bước nào sớm nhất, và ai là người duy nhất có thể sửa nguồn.

### Gợi ý 2

Hợp đồng không phải tài liệu để đọc mà là thứ chạy được: mỗi dòng nên tương ứng với một kiểm tra hoặc một quy trình có người chịu trách nhiệm.
