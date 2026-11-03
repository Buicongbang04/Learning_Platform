# Lời giải: model card

Mã nằm trong `modelcard.py` cạnh tệp này.

## Vì sao sinh tự động

Model card viết tay bằng Notion lệch khỏi model sau lần retrain đầu tiên. Card sinh từ `info` (lấy từ tag, metric và
artifact của run) có `run_id` và `git_commit` đúng với version đang chạy, và có thể được đính vào model version trong registry
như một artifact, nên ai mở version trong UI cũng thấy.

## Các quyết định

- **Slice tệ nhất đứng đầu.** Người đọc thường chỉ đọc vài dòng đầu của bảng; đặt chỗ yếu lên trước để nó không bị chôn.
  Tỉ lệ so với MAE tổng (`1.65x`) dễ đọc hơn số tuyệt đối vì không phải nhớ MAE tổng.
- **`worst_slices` bỏ slice nhỏ, bảng thì không.** Hàm xếp hạng phục vụ cảnh báo, nên phải lọc nhiễu; bảng là tài liệu, nên
  liệt kê hết và để người đọc thấy slice `rare` 20 chuyến với MAE 900 (kèm cột `n`).
- **Từ chối card không có hạn chế.** Mọi model đều có hạn chế (dữ liệu trước COVID, không biết giao thông thời gian thực).
  Một card không nêu được hạn chế nào thường nghĩa là chưa ai nghĩ về nó; ép viết là cách rẻ nhất để buộc việc đó xảy ra.
- **Linter báo mọi lỗi cùng lúc.** CI chỉ báo lỗi đầu tiên thì người viết phải push 5 lần để sửa 5 lỗi.
- **Kiểm commit hash 40 ký tự hex** thay vì chỉ "có chữ git_commit": giá trị `unknown` hay `HEAD` là lỗi hay gặp khi script
  train chạy ngoài repo.

## Mở rộng nên làm sau

Đính card vào model version bằng `client.log_artifact(run_id, "MODEL_CARD.md")` hoặc `set_model_version_tag`, và cho cổng
promotion (bài trung cấp 03) chạy `card_problems` như một điều kiện cứng.
