# Hướng làm: panel Grunfeld

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, các số tham chiếu và rubric.

## 1. Within estimator

- Demean bằng `groupby(entity).transform("mean")`: đúng cho cả panel không cân bằng (mỗi entity trừ
  trung bình của chính nó, dù có bao nhiêu kỳ).
- OLS không hằng số trên dữ liệu đã demean (hằng số bị demean thành 0).
- **Bậc tự do**: OLS thông thường chia SSR cho $$n - k$$; đúng phải là $$n - N - k$$ vì demean đã
  ước lượng ngầm $$N$$ trung bình. Trên Grunfeld: 220 − 11 − 2 = 207. Dùng $$n - k$$ thì SE nhỏ đi
  hệ số $$\sqrt{207/218} \approx 0.974$$: SE `value` 0.0110 thay vì 0.0113. Với panel nhiều entity
  ít kỳ (1 000 khách × 3 tháng), sai lệch thành lớn: $$\sqrt{(3000-1000-k)/(3000-k)} \approx 0.82$$.
- Biến không đổi trong entity: sau demean toàn 0, ma trận suy biến. Raise lỗi rõ ràng thay vì để
  `lstsq` trả hệ số 0 im lặng.

Kết quả: `value` 0.1101 (SE 0.0113), `capital` 0.3100 (SE 0.0165), trùng LSDV và `PanelOLS`.

## 2. Hausman

Trên Grunfeld: H = 3.97, p = 0.138 (FE và RE cổ điển của `linearmodels`).

Một chi tiết đáng nói trong báo cáo: $$\widehat V_{FE} - \widehat V_{RE}$$ chỉ dương xác định **theo
kỳ vọng**. Khi RE gần như trùng FE (θ gần 1: T lớn, hoặc variance của hiệu ứng riêng lớn), ma trận
hiệu này rất nhỏ và nhiễu, H có thể nổ dù H0 đúng. Lúc thiết kế test của bài này, với 100 entity × 8
kỳ, độ lệch chuẩn hiệu ứng riêng 2 và hiệu ứng **không** tương quan với x, một seed cho H = 67.6
(p ≈ 0). Cách xử lý chuẩn: tính cả hai ma trận với **cùng** một ước lượng $$\sigma_\varepsilon^2$$
(tuỳ chọn `sigmamore` / `sigmaless` của Stata), hoặc dùng bản robust: correlated random effects
(Mundlak), kiểm định các hệ số của trung bình theo entity bằng cluster SE.

## 3. Bảng kết quả tham chiếu

| Model | value | capital | SE |
| --- | --- | --- | --- |
| Pooled OLS | 0.1145 (0.0055) | 0.2275 (0.0242) | cổ điển |
| FE | 0.1101 (0.0113) | 0.3100 (0.0165) | cổ điển |
| FE | 0.1101 (0.0144) | 0.3100 (0.0501) | cluster công ty |
| RE | 0.1093 (0.0099) | 0.3080 (0.0164) | cổ điển |
| Two-way FE | 0.1167 (0.0113) | 0.3514 (0.0470) | cluster công ty |

- F test fixed effects: F(10, 207) = 49.2, p ≈ 0.
- RE: θ = 0.859, 71% variance ở cấp công ty.

## 4. Các quyết định cần cân nhắc trong báo cáo

- **FE hay RE**: Hausman không bác bỏ, nhưng 11 công ty là quá ít để test có power, và giả định RE
  khó tin về kinh tế. Chọn FE làm chính và báo RE như robustness là lựa chọn dễ bảo vệ nhất. Chọn RE
  cũng chấp nhận được **nếu** lập luận rõ (hiệu quả hơn, hai bộ hệ số gần như trùng).
- **SE**: cluster theo công ty là mặc định cho panel, nhưng chỉ 11 cluster: cluster SE bị lệch nhỏ;
  báo cáo kèm cảnh báo hoặc wild cluster bootstrap.
- **Time effects**: two-way FE đổi hệ số `capital` từ 0.31 lên 0.35. Năm 1935–1954 có suy thoái và
  chiến tranh, cú sốc chung là confounder hợp lý.
- **Nhân quả**: `value` phản ánh kỳ vọng thị trường về cơ hội đầu tư; hệ số là quan hệ trong công ty
  theo thời gian, không phải "tăng giá cổ phiếu thì công ty đầu tư thêm".
- **Động học**: đầu tư có quán tính; model tĩnh bỏ qua. Biến trễ của y + FE gây Nickell bias (cỡ
  1/T, với T = 20 là nhỏ).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| `within_estimator` và `hausman` đúng | 20 | Qua mọi test, có xử lý bậc tự do và biến không đổi |
| Bảng model đầy đủ | 15 | Pooled, FE, RE, two-way FE, ghi rõ loại SE |
| Chọn model có lập luận | 20 | Dùng F test, Hausman **và** lập luận về giả định; nêu giới hạn của Hausman ở N = 11 |
| SE | 15 | Cluster theo công ty, nhận ra vấn đề ít cluster |
| Diễn giải | 15 | Hệ số bằng lời; giải thích vì sao `capital` đổi giữa pooled và FE; không nói nhân quả |
| Giới hạn và bước tiếp | 15 | Ít nhất 3 giới hạn thật (động học, ít cluster, sai số đo lường, cú sốc chung) kèm hướng xử lý |

Đạt từ 70 điểm là báo cáo đủ chuẩn để đưa cho nhóm nghiên cứu.
