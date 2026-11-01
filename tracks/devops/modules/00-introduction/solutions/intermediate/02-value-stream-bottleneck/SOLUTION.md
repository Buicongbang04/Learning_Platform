# Lời giải: nút thắt trong value stream

Code đầy đủ ở `value_stream.py` cạnh tệp này.

## Kết quả

Bảy PR đã deploy (PR-108 còn đang chờ deploy nên không tính):

| Stage | Median | Mean |
| --- | --- | --- |
| coding | 5 giờ | 5,3 giờ |
| review_wait | **20 giờ** | 18,9 giờ |
| review | 2 giờ | 1,9 giờ |
| merge_wait | 1 giờ | 0,9 giờ |
| deploy_wait | 3 giờ | **36,4 giờ** |

- **Nút thắt là `review_wait`**: PR nằm chờ người review gần một ngày, trong khi review thật chỉ mất 2 giờ.
- Nếu dùng mean, `deploy_wait` thắng vì một PR (PR-103) lỡ release và chờ 10 ngày. Đó là một sự cố quy trình cần
  hỏi riêng, không phải nút thắt chung. Median trả lời "thường thì thời gian mất ở đâu"; outlier cần một câu hỏi
  khác ("vì sao PR này chờ 10 ngày?").
- **Flow efficiency** khoảng 11% (50 giờ làm việc thật trên 442,75 giờ lead time). Con số 10–15% là bình thường ở
  team chưa tối ưu: gần 90% thời gian một thay đổi đứng chờ.
- `PR-106` là hotfix tự merge: không sai về dữ liệu, nhưng cần nằm trong báo cáo audit (ai merge, vì sao không cần
  review, có review sau không).

## Vì sao tỉ lệ gộp chứ không trung bình từng tỉ lệ

Trung bình của tỉ lệ cho mỗi PR trọng số như nhau: một hotfix 2 giờ có tỉ lệ active cao sẽ kéo con số lên ngang một
PR đã chờ hai tuần. Thứ team quan tâm là "trong toàn bộ thời gian thay đổi đi qua hệ thống, bao nhiêu phần trăm có
người làm", nên chia tổng cho tổng.

## Đề xuất cho nút thắt

Thay đổi quy trình trước khi mua công cụ:

- Quy ước review trong vòng 4 giờ làm việc, có người trực review luân phiên mỗi ngày.
- Giới hạn WIP: không mở PR mới khi có PR của đồng đội chờ review quá nửa ngày.
- PR nhỏ hơn (dưới 300 dòng thay đổi): review nhanh hơn và kỹ hơn.

Đo bằng chính bài này: median `review_wait` theo tuần, và change lead time. Nếu `review_wait` giảm mà change failure
rate tăng, review đang bị làm qua loa; cần xem lại.

## Lỗi hay gặp

- Gộp PR chưa deploy vào phép tính: lead time của chúng chưa kết thúc, đưa vào làm số thấp giả.
- Bỏ qua múi giờ: GitHub ghi `Z`, công cụ deploy ghi `+07:00`; so chuỗi thì sai cả ngày.
- Đo đến lúc merge rồi dừng: `deploy_wait` thường là chỗ release train giấu thời gian, và là thứ DevOps sửa được
  trực tiếp bằng continuous deployment.
