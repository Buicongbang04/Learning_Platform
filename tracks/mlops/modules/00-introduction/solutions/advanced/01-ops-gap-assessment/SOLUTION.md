# Lời giải mẫu: đánh giá khoảng cách vận hành ShipFast ETA

Không có đáp án duy nhất. Bản dưới đây là một bản đạt; chấm bằng rubric ở cuối. Test chỉ kiểm cấu trúc và
vài ràng buộc cơ học (đủ phần, đủ cột, 1-3 dòng P0, mốc 30/60/90); chất lượng lập luận do rubric và bạn tự chấm.

## Bản mẫu

```markdown
# Đánh giá khoảng cách vận hành: ShipFast ETA

## 1. Tóm tắt và mức trưởng thành

Theo thang của Google, ShipFast ETA đang ở mức 0: training là notebook chạy tay mỗi tháng trên laptop, phát hành bằng
`scp` một tệp pickle, không có pipeline tự động, không có kiểm tra dữ liệu hay model. Backend có CI nhưng chỉ cho code API,
nên theo thang Microsoft hệ thống nhỉnh hơn mức 0 một chút. Rủi ro lớn nhất với kinh doanh là mất 5 ngày (3 ngày xác nhận
cộng 2 ngày quay lại) để xử lý một ETA sai 40%: không ai biết model sai cho tới khi điều phối viên phàn nàn, và không có
đường quay lui nhanh. Nên ưu tiên khả năng phát hiện và quay lui trước, không phải tự động hoá training.

## 2. Bảng khoảng cách

| Khu vực | Hiện trạng (bằng chứng) | Rủi ro | Ưu tiên | Việc đầu tiên | Công cụ |
| --- | --- | --- | --- | --- | --- |
| rollback | Mất 2 ngày quay về model cũ vì không còn pickle cũ, phải train lại | Mỗi model xấu kéo dài nhiều ngày | P0 | Lưu mọi model đã phát hành với số version, giữ 3 bản gần nhất | MLflow Model Registry (file store, rồi Postgres) |
| monitoring | Chỉ có health check HTTP 200; sai 40% sau khuyến mãi mất 3 ngày mới xác nhận | Model sai mà không ai biết | P0 | Log mỗi dự đoán (id đơn, version, đầu vào, ETA) và job hằng ngày nối với thời gian giao thực để tính MAE | Log JSON vào Postgres, Prometheus + Grafana sau |
| versioning | Hai DS dùng hai bản CSV khác nhau; tên tệp `orders_final_v3_NEW.csv` | Không tái lập được, không biết model train từ dữ liệu nào | P1 | Ghi hash dữ liệu và git commit vào mỗi run | DVC với remote S3/MinIO |
| training | Một notebook, không seed, chạy tay trên laptop, lần cuối cách 7 tuần | Kết quả không lặp lại, model cũ dần | P1 | Chuyển notebook thành script `train.py` có seed và config, chạy bằng một lệnh | uv, pyproject, MLflow Tracking |
| serving | Flask trên VM, `scp` pickle, restart tay; 8 request/giây cao điểm | Phát hành thủ công dễ sai, không biết version đang chạy | P1 | Trả `model_version` trong response và nạp model theo alias từ registry | FastAPI trong container |
| ci-cd | CI chỉ cho API, không chạm model; scikit-learn nâng bản làm hỏng model 40 phút | Lỗi môi trường chỉ lộ khi production | P1 | Ghim phiên bản dependency, thêm bước test load model trong CI | uv lock, GitHub Actions |
| security | Chuỗi kết nối Postgres cứng trong notebook, nằm trong Git | Lộ mật khẩu DB | P0 | Xoay mật khẩu, đưa vào biến môi trường, quét lịch sử Git | gitleaks, `.env` không commit |
| data | CSV 2,1 GB xuất tay qua Google Drive | Dữ liệu cũ, không có kiểm tra chất lượng | P2 | Viết schema kiểm tra tối thiểu (khoảng thời gian, giá trị âm) | Pandera |

## 3. Cố ý chưa làm

- Kubernetes và Kubeflow: 8 request/giây trên một VM là đủ; không ai chuyên hạ tầng, nên chi phí vận hành vượt lợi ích.
- Feature store và orchestrator đầy đủ: chưa có bằng chứng skew hay pipeline phức tạp; xem lại khi có từ 3 model hoặc khi
  training cần nhiều bước phụ thuộc nhau, vì cron cộng MLflow đủ cho hiện tại và vừa ngân sách 300 USD/tháng.

## 4. Lộ trình 30/60/90 ngày

| Mốc | Việc | Tiêu chí hoàn thành |
| --- | --- | --- |
| 30 ngày | Registry giữ mọi version, log dự đoán, job MAE hằng ngày, xoay mật khẩu DB | Quay lui về version trước trong dưới 15 phút, có biểu đồ MAE theo ngày |
| 60 ngày | Ghim môi trường, `train.py` có seed, DVC cho dữ liệu, serving trả version | Hai người train cùng dữ liệu ra cùng MAE; response có model_version |
| 90 ngày | Training theo lịch có cổng so với model đang chạy, CI build image và test load model | Model mới chỉ lên production khi qua cổng, có bản ghi quyết định |

## 5. Giả định và rủi ro của kế hoạch

- Giả định thời gian giao thực tế đáng tin và có trong bảng `orders` trong vòng vài giờ sau khi giao; nếu trễ nhiều ngày thì
  cần thêm tín hiệu drift để biết sớm.
- Rủi ro: chị Mai là điểm nghẽn duy nhất của việc train; cần một người thứ hai chạy được quy trình trước ngày 60.
```

## Rubric (tổng 20 điểm, đạt từ 14)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Bằng chứng bám đề | 4 | Mỗi khoảng cách trích đúng một chi tiết trong đề (7 tuần, 40 phút, 5 ngày...), không bịa chi tiết ngoài đề |
| Xếp hạng ưu tiên | 5 | P0 là các việc giảm thiệt hại ngay (quay lui, phát hiện, lộ mật khẩu), không phải tự động hoá cho đẹp; có lý do cho thứ tự |
| Việc đầu tiên nhỏ và kiểm được | 4 | Mỗi "việc đầu tiên" làm được trong vài ngày, có tiêu chí hoàn thành quan sát được |
| Phù hợp nguồn lực | 4 | Công cụ vừa ngân sách 300 USD/tháng và đội không có hạ tầng; có phần "cố ý chưa làm" với điều kiện xem lại |
| Nhận ra giới hạn kế hoạch | 3 | Nêu giả định (độ trễ nhãn, người điểm nghẽn) và cách kiểm |

Lỗi hay gặp: đề xuất Kubernetes + feature store cho 8 request/giây; liệt kê công cụ mà không nói rủi ro nào nó giảm; đặt
tất cả là P0; bỏ qua chuyện lộ mật khẩu vì "không phải việc ML"; coi CI của backend là đã có CI cho ML.
