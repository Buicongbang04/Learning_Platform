# Lời giải: khoảng tin cậy và độ phủ

## CI t cho trung bình

`mean ± t_{1−α/2, n−1} · s/√n`. Dùng phân phối t thay vì z vì `s` cũng là ước lượng có nhiễu; với
n = 8, `t_{0.975, 7} = 2.36` so với 1.96, CI rộng hơn khoảng 20%. Với n vài trăm trở lên, hai cách
gần như trùng. CI t giả định trung bình mẫu xấp xỉ chuẩn: với dữ liệu lệch phải nặng như giá trị
đơn Olist, giả định đó cần n rất lớn (bài Intermediate 01 đo cụ thể).

## Vì sao Wald hỏng

Wald dùng `p̂` để ước lượng SE. Khi p nhỏ và n nhỏ, xác suất k = 0 lớn (với p = 2%, n = 50 là
`0.98^50 ≈ 36%`), và khi đó SE = 0, CI = [0, 0], không chứa p thật. Độ phủ thật:

| p, n | Wald | Wilson |
| --- | --- | --- |
| 2%, 50 | ≈ 63% | ≈ 92% |
| 12.8%, 400 | ≈ 94.5% | ≈ 95% |

Wilson lấy CI bằng cách **đảo ngược kiểm định score**: tập các p mà kiểm định
`(p̂ − p)/sqrt(p(1−p)/n)` không bác bỏ. SE tính theo p ứng viên chứ không theo p̂, nên không thoái
hoá ở 0. Tâm của Wilson bị kéo về 0.5 một chút, giống như cộng thêm `z²/2 ≈ 2` thành công và 2 thất
bại (ý tưởng của Agresti-Coull, và là trực giác dẫn sang prior Beta trong bài Intermediate 03).

## Trên số thật Olist

- `fashion_male_clothing` 24/105: Wald [0.148, 0.309], Wilson [0.159, 0.318].
- `fashion_childrens_clothes` 0/7: Wald [0, 0] (vô nghĩa), Wilson [0, 0.354].
- Toàn sàn 12 272/95 824: Wald và Wilson cùng khoảng [0.126, 0.130].

## Khi nào dùng gì

- Tỉ lệ, n lớn và p không quá gần 0/1 (`n·p̂` và `n·(1−p̂)` đều trên vài chục): Wald đủ, dễ giải thích.
- Mặc định an toàn cho tỉ lệ: Wilson (`statsmodels.stats.proportion.proportion_confint(method="wilson")`).
- Cần đảm bảo độ phủ **ít nhất** 95% (y tế, pháp lý): Clopper-Pearson (`method="beta"`), bảo thủ.
- Muốn đưa kiến thức có sẵn vào (các category khác): Bayesian Beta-Binomial.

Thói quen senior: mỗi khi dùng một CI cho tình huống lạ (mẫu nhỏ, tỉ lệ hiếm, metric lệch), viết
một mô phỏng độ phủ 10 dòng như hàm `coverage` trước khi tin nó.
