---
title: "Uplift modeling: gửi email nữ cho ai (Hillstrom)"
level: advanced
services: []
files:
  - path: starter/uplift.ipynb
    note: 4 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Giám đốc CRM
  - path: tests/test_uplift.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py hillstrom
  - uv run jupyter lab tracks/data-science/modules/06-causal-inference/exercises/advanced/02-hillstrom-uplift/starter/uplift.ipynb
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/advanced/02-hillstrom-uplift -q
---

## Mục tiêu

Chuyển từ "tác động trung bình" sang "tác động cho từng khách" (CATE): xây mô hình uplift, đánh giá
nó bằng Qini trên dữ liệu thí nghiệm, so với một luật đơn giản, và quyết định chiến lược gửi email
có lợi nhuận, kèm mức độ không chắc chắn.

## Đề bài

Dùng nhánh `Womens E-Mail` và `No E-Mail` của thí nghiệm Hillstrom (module 03). Outcome chính là
`visit`. Mở `starter/uplift.ipynb`:

1. `prepare(df, arm="Womens E-Mail", control="No E-Mail")`: lọc hai nhánh, cột `treatment`, one-hot
   `zip_code` và `channel` (float), bỏ `history_segment`.
2. `t_learner(train, score, features, outcome, make_model, treatment="treatment")`: uplift dự
   đoán cho từng dòng của `score`.
3. `qini_curve(uplift, treatment, outcome)` và `qini_coefficient(...)` theo công thức trong notebook.
4. Phân tích tự do: chia train/test, ít nhất hai loại mô hình cho T-learner (ví dụ logistic,
   gradient boosting), so với xếp hạng theo một cột (`womens`), bảng uplift quan sát theo
   top 20/40/60/100% khách, và một đề xuất chiến lược có quy ra tiền.
5. Viết `REPORT.md` theo khung (tối đa một trang rưỡi).

## Tiêu chí đạt

- `prepare` đúng trên dữ liệu nhỏ; trên Hillstrom thật còn 42 693 khách, tác động trung bình lên
  `visit` ≈ +4.52 điểm %.
- `qini_curve` / `qini_coefficient` đúng trên ví dụ 4 khách tính tay, giữ thứ tự gốc khi hoà; trên
  mô phỏng, xếp hạng đúng cho Qini dương, xếp ngược cho Qini âm, xếp ngẫu nhiên cho Qini gần 0.
- `t_learner` tìm lại uplift chênh +12 điểm % giữa hai nhóm khách trong mô phỏng.
- Xếp hạng theo cột `womens` trên Hillstrom thật có Qini ≈ 0.0039.
- `REPORT.md` không còn TODO, ít nhất 300 từ. Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Q(k) tính được bằng `np.cumsum` trên mảng đã sắp, không cần vòng lặp. Khi `N_c(k) = 0` dùng
`np.divide(n_t, n_c, out=np.zeros_like(n_t), where=n_c > 0)`. Đừng chấm uplift trên chính tập đã
huấn luyện: mô hình học cả nhiễu, Qini trên train luôn đẹp.

### Gợi ý 2

Không có "nhãn uplift" cho từng khách (không ai vừa nhận vừa không nhận email), nên không có
accuracy hay AUC cho uplift. Cách kiểm tra duy nhất là theo **nhóm**: trong top k% khách mô hình
chấm cao nhất, so tỉ lệ visit giữa người được gửi và người không (random vẫn còn nguyên trong từng
nhóm vì xếp hạng chỉ dùng đặc điểm trước thí nghiệm). Với `spend`, hãy xem độ rộng của khoảng tin
cậy trước khi tin vào bất kỳ ngưỡng nào.
