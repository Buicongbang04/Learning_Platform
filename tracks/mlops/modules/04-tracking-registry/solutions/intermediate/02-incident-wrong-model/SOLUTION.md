# Lời giải: service nạp "version mới nhất"

## Nguyên nhân

`_pick()` chọn `max(version)` trong registry: "model mới nhất thì chắc là model tốt nhất". Quy ước của đội lại là model được
duyệt = version giữ alias `champion`. Hai thứ này trùng nhau cho tới khi có người đăng ký một version thử nghiệm: version 3
(chưa duyệt, train từ nhánh dở) thành "mới nhất" và lần restart kế tiếp nạp nó. Service không có chỗ nào kiểm duyệt, nên
không bao giờ báo lỗi: HTTP 200, độ trễ như cũ, chỉ có con số sai.

Vì sao rollback bản service không giúp: lỗi không nằm ở mã service mà ở trạng thái registry mà mã đó đọc. Bất kỳ bản nào
chọn "mới nhất" đều nạp v3.

Vì sao không ai thấy sớm: alert chỉ nhìn tỉ lệ lỗi và latency (RED), không nhìn phân phối dự đoán. Một alert so trung bình dự
đoán 1 giờ với trung bình 7 ngày (module 09) bắt được chuyện này trong vài phút.

## Cách sửa

Phân giải model theo alias: `client.get_model_version_by_alias(name, "champion")`, rồi nạp đúng `models:/<tên>/<version>`
(xem `service.py`). Ba hành vi đi kèm:

- **Không fallback.** Không có alias thì `LookupError`, không "lấy version mới nhất cho chắc". Fallback chính là lỗi cũ trong
  hình dạng khác: service khởi động được nhưng phục vụ model chưa duyệt. Thà không lên (readiness fail, orchestrator giữ bản
  cũ) còn hơn lên sai.
- **`refresh()` lỗi thì giữ model cũ.** Ném lỗi trước khi đụng tới `self.model`; một lỗi mạng tạm tới registry không được xoá
  model đang phục vụ tốt.
- **Trả `model_version` trong response và log**: người điều tra lúc 14:10 phải thấy được ngay version nào đang phục vụ.

## Rộng hơn bài này

- Quyền đổi alias là quyền promote production; cho nó đi qua cổng (bài trung cấp 03) và hạn chế ai được ghi.
- Ghim theo digest/số version trong manifest triển khai là một phương án khác (GitOps: đổi version = commit). Nó đổi tính
  tức thì lấy tính audit; alias phù hợp khi muốn đổi model không cần deploy. Module 07 và 08 đi tiếp ý này.
- Test hồi quy nên là chính ba tình huống trong bài: thêm version, rollback alias, mất alias.
