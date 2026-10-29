# Lời giải: batch và online dùng chung logic feature

## Cách làm

**Một hàm feature duy nhất.** `make_features` nhận một DataFrame; đường online bọc payload thành
DataFrame một dòng rồi gọi đúng hàm đó. Chi phí là vài trăm micro giây tạo DataFrame mỗi request,
không đáng kể so với lợi ích: không có cách nào để hai đường lệch nhau.

**Chuẩn hoá kiểu ngay ở cửa vào.** `pd.to_datetime` cho cột thời gian (datetime hay chuỗi ISO đều
thành datetime, `None` thành `NaT`), `astype("float64")` cho cột số. JSON không có kiểu datetime,
và số nguyên trong JSON thành `int` của Python: nếu không ép kiểu, cùng một đơn có thể đi qua
pipeline với kiểu khác nhau ở hai đường.

**Idempotent bằng thay cả phân vùng.** Job batch chạy lại là chuyện thường (lỗi upstream, backfill,
người vận hành bấm nhầm). Append thì chạy lại là nhân đôi dòng; thay cả phân vùng `run_date=...`
thì chạy bao nhiêu lần cũng ra cùng kết quả. Lời giải ghi vào thư mục tạm rồi đổi tên, để người
đọc bảng không bao giờ thấy phân vùng ghi dở. Đây là cùng nguyên tắc với pipeline ở track Data
Engineer (`tracks/data-engineer/modules/05-batch-pipelines`).

## Training-serving skew trông như thế nào ngoài đời

| Nguồn skew | Ví dụ với model này |
| --- | --- |
| Hai bản cài feature | Batch tính `delay_days` bằng SQL `DATE_DIFF` (theo ngày nguyên), online tính bằng Python theo giờ: đơn giao 15:00 đúng ngày hẹn là 0 ở một bên, 0.625 ở bên kia |
| Kiểu dữ liệu | `n_items` là `int` ở online, `float` ở batch; đa số model không quan tâm, ONNX và MLflow schema thì có |
| Giá trị thiếu | Batch đọc NULL thành NaN, online nhận chuỗi rỗng `""` |
| Múi giờ | Batch lưu UTC, app CSKH gửi giờ địa phương (Brasília là UTC−3): `delay_days` lệch 0.125 |
| Dữ liệu tại thời điểm chấm | Online chấm lúc tổng đài viên mở đơn, khi có thể chưa có ngày giao; batch chấm sau khi đơn giao |

Dòng cuối là lỗi nghiêm trọng nhất và không test nào trong bài bắt được: model được train với
"thời điểm dự đoán là lúc đơn vừa giao". Gọi nó cho đơn **chưa giao** (để can thiệp trước khi
giao) là dùng sai model: cần một model khác, train tại thời điểm mua hoặc lúc giao cho hãng vận
chuyển, không dùng `delivery_days` hay `delay_days`.

## Kiểm parity trong thực tế

Test của bài là phiên bản nhỏ của cách làm ở production: lấy một mẫu request online đã log, chấm
lại bằng đường batch, so score. Chạy kiểm tra này định kỳ (hằng ngày trên vài trăm request) và
cảnh báo khi chênh lệch vượt một ngưỡng nhỏ. Feature store (track MLOps) giải bài toán này ở quy mô
lớn bằng cách định nghĩa feature một lần cho cả hai đường.

## Sai lầm hay gặp

- Ghi `score` dạng `numpy.float64` vào response JSON.
- Dùng `datetime.now()` bên trong logic feature: batch chạy lại hôm sau cho kết quả khác.
- Chạy batch với `mode="append"` vì "lần đầu chạy thì đúng".
