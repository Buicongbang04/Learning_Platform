# Lời giải: z-test, khoảng tin cậy và Welch t-test

## z-test hai tỉ lệ: vì sao pooled

Kiểm định hỏi "nếu H0 đúng (hai tỉ lệ bằng nhau) thì chênh lệch này hiếm cỡ nào". Dưới H0 chỉ có
**một** tỉ lệ chung, nên ước lượng tốt nhất của nó là gộp hai nhóm: `p_pool = (x_a + x_b) / (n_a + n_b)`.
SE tính từ `p_pool`. Đây cũng là thứ `proportions_ztest` làm mặc định.

## Khoảng tin cậy: vì sao không pooled

CI trả lời câu hỏi khác: "chênh lệch thật nằm khoảng nào". Ở đây ta **không** giả định H0, nên
mỗi nhóm có variance riêng `p(1 − p)/n`. Hệ quả: có thể gặp trường hợp p-value ≈ 0.05 nhưng CI chạm
sát 0 ở phía bên kia, vì hai SE khác nhau một chút. Với mẫu lớn khác biệt này không đáng kể.

Wald CI kém chính xác khi tỉ lệ rất gần 0 hoặc 1, hoặc mẫu nhỏ (ví dụ conversion 0.1% với vài
nghìn user). Khi đó dùng Newcombe hoặc Agresti-Caffo (`confint_proportions_2indep(method="newcomb")`).

## Welch t-test

Student t-test giả định hai nhóm cùng variance. Trong A/B testing điều này hiếm khi đúng (treatment
thay đổi cả hành vi lẫn độ phân tán), và khi cỡ nhóm khác nhau, Student có thể cho tỉ lệ false
positive sai lệch đáng kể. Welch không cần giả định đó và gần như không mất power khi variance bằng
nhau, nên là mặc định. Test cuối cho thấy hai cách cho p-value khác nhau khi nhóm nhỏ có variance nhỏ.

## Kết quả trên dữ liệu thật

Cookie Cats `retention_7`: z ≈ −3.16, p ≈ 0.0016, CI cho `gate_40 − gate_30` ≈ [−1.33, −0.31] điểm
phần trăm. Dời gate ra xa làm giảm retention.

ab_data sau khi làm sạch: z ≈ −1.31, p ≈ 0.19, CI chứa 0 và hẹp: trang mới gần như chắc chắn không
tốt hơn đáng kể.

## Trong thực tế

Bạn sẽ gọi `statsmodels` hoặc platform tính hộ. Giá trị của việc tự viết là biết SE đến từ đâu: đó
là chỗ CUPED giảm variance (module 04), là chỗ sai khi đơn vị phân tích khác đơn vị random, và là
chỗ cần delta method cho ratio metric.
