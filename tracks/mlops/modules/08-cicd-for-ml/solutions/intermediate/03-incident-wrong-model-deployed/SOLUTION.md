# Lời giải: pipeline xanh, model deploy sai

## Nguyên nhân

Job `deploy` chọn đầu vào bằng `ls store | sort | tail -1`, tức là "thư mục đứng cuối khi sắp xếp theo tên", chứ không phải "thư
mục của lần chạy này". Tên thư mục là `run-<số>`. Sắp xếp theo chữ, không theo số: `run-10` và `run-11` đứng **trước** `run-8`
và `run-9`. Chín lần chạy đầu (`run-1` đến `run-9`) thứ tự chữ trùng thứ tự số nên "cuối cùng" luôn là mới nhất, mọi thứ đúng. Từ
lần thứ 10, `run-9` luôn đứng cuối và job `deploy` đưa model của lần chạy 9 lên mãi mãi, trong khi `train` đã sinh model mới.
Mọi bước đều thành công vì không bước nào kiểm "model này có phải model vừa train".

Vì sao rollback workflow không giúp: lỗi nằm ở logic chọn của bước, và kho chứa dữ liệu của mọi lần chạy.
Vì sao không ai thấy sớm: lúc đầu đúng nên không ai nghi; và pipeline xanh là tín hiệu duy nhất đội theo dõi.

## Cách sửa

Nhận model theo **định danh của lần chạy này** (`store/run-${{ github.run_number }}`), không theo thứ tự hay thời gian. Nếu thư
mục đó không có thì thoát 1: thà deploy đỏ còn hơn deploy sai trong im lặng. Fallback "lấy cái mới nhất cho chắc" chính là lỗi cũ trong
hình dạng khác. Test `test_deploy_fails_when_this_run_published_no_model` ép điều này.

Các cách sửa khác cũng đúng nếu cùng nguyên tắc: truyền `model_id` từ job `train` sang job `deploy` bằng job output
(`$GITHUB_OUTPUT`, `needs.train.outputs.model_id`) rồi tìm đúng mục đó; hoặc upload/download artifact có tên theo `run_id`.

## Bài học

- **Chọn theo định danh, không theo "mới nhất".** Sắp xếp tên, `ls -t` (thời gian sửa, đổi khi ai đó chạm vào tệp), `latest` tag
  đều là cách chọn ngầm; chúng đúng cho tới khi không đúng, và không báo lỗi khi sai.
- **Kiểm ở đầu ra, không chỉ ở mã thoát.** Một bước cuối "đọc lại thứ vừa deploy và so `model_id` với thứ vừa train" biến lớp
  lỗi này thành pipeline đỏ. Ghi `model_id` vào log và response của service để người trực đối chiếu được.
- **Giả định "cùng thư mục" chỉ đúng trên máy bạn.** `act --bind` cho các job chung một thư mục; GitHub thật thì không. Bài kiểm
  "không đọc `models/`" nhắc điều đó: kiểm local phải gần runner thật nhất có thể.
- **Test hồi quy** là chính bộ số lần chạy 11, 12, 100 trên cùng một kho, cộng ca "không có model của lần chạy này".
