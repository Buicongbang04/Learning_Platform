---
title: Giải thích model churn cho đội retention
level: advanced
services: []
files:
  - path: starter/explain.ipynb
    note: 2 hàm chấm điểm + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Giám đốc retention
  - path: tests/test_explain.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-science/modules/11-classic-ml/exercises/advanced/01-churn-explain/starter/explain.ipynb
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/advanced/01-churn-explain -q
---

## Mục tiêu

Giải thích một model thật cho người ra quyết định: model dựa vào gì, vì sao một khách cụ thể có điểm cao, và quan
trọng nhất là những gì giải thích **không** cho phép kết luận.

## Đề bài

Bộ Telco churn, model random forest có sẵn trong notebook (ROC-AUC test khoảng 0.845). Mở `starter/explain.ipynb`:

1. `permutation_importance_df(model, X, y, score_fn, n_repeats=5, seed=0)`: tự cài permutation importance trên
   cột **thô** (hoán vị một biến phân loại nguyên khối), không sửa `X`, sắp giảm dần.
2. `group_shap(values, original_features)`: gộp SHAP của các cột one-hot về biến gốc (tên dài nhất khớp được).
3. Phân tích tự do theo 5 bước gợi ý trong notebook: permutation so với MDI, feature tương quan
   (`TotalCharges`, `tenure`, `MonthlyCharges`), SHAP gộp, giải thích từng khách, câu hỏi "nếu… thì…".
4. Viết `starter/REPORT.md` theo khung có sẵn, cho Giám đốc retention (không làm ML).

## Tiêu chí đạt

- Permutation importance: đúng cấu trúc, feature nhiễu gần 0, feature yếu nhưng thật có importance dương, tái
  lập được với seed, không sửa dữ liệu đầu vào; thấy được hiện tượng hai feature gần trùng nhau chia importance.
- `group_shap` cộng đúng, không nhầm `Internet` với `InternetService`, tổng SHAP mỗi dòng không đổi.
- `REPORT.md` không còn TODO, ít nhất 350 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`shuffled = X.copy(); shuffled[col] = X[col].to_numpy()[rng.permutation(len(X))]`. Với `group_shap`, sắp tên
gốc theo độ dài giảm dần rồi lấy tên đầu tiên mà `name == f or name.startswith(f + "_")`; rồi
`values.T.groupby(owner).sum().T`.

### Gợi ý 2

`shap.TreeExplainer(model[-1])(Xt).values` có dạng `(n, số cột, 2)` với random forest phân loại: lấy `[..., 1]`
cho lớp churn. Kiểm tra additivity: giá trị nền cộng tổng SHAP mỗi dòng phải bằng xác suất dự đoán.
