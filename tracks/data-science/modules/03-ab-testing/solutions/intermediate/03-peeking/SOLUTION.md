# Lời giải: peeking và biên O'Brien-Fleming

Notebook lời giải: `peeking.ipynb`.

## Kết quả mô phỏng

| Số lần nhìn | False positive khi bác bỏ ở lần đầu p < 0.05 |
| --- | --- |
| 1 | ~5% |
| 2 | ~8% |
| 5 | ~14% |
| 10 | ~18% |
| 20 | ~24% |

Nhìn hằng ngày trong một thí nghiệm 3 tuần là ~21 lần nhìn: cứ 4 thí nghiệm không có tác động thì
khoảng 1 thí nghiệm được tuyên bố "thắng".

## Vì sao

Dưới H0, chuỗi z theo thời gian là một bước ngẫu nhiên (random walk) được chuẩn hoá. Ở mỗi thời
điểm nó vượt ±1.96 với xác suất 5%, nhưng xác suất nó vượt ±1.96 **ở ít nhất một thời điểm** trong
nhiều thời điểm thì lớn hơn nhiều. Các lần nhìn tương quan với nhau (dùng chung dữ liệu cũ), nên
tăng chậm hơn 1 − 0.95^K, nhưng vẫn tăng không giới hạn khi nhìn liên tục.

## O'Brien-Fleming

Biên `c · sqrt(K/k)` với K = 5: [4.57, 3.23, 2.64, 2.28, 2.04]. Lần đầu (20% dữ liệu) chỉ dừng khi
bằng chứng áp đảo; lần cuối gần như kiểm định thông thường (2.04 thay vì 1.96).

Hiệu chỉnh nhanh: thay vì mô phỏng lại cho mỗi `c`, tính một lần thống kê
`max_k |z_k| / sqrt(K/k)` cho mỗi thí nghiệm; `c` là phân vị 95% của nó. Lời giải vẫn dùng `brentq`
để minh hoạ cách giải tổng quát, nhưng trên mảng đã tính sẵn nên tức thì.

Cái giá: biên cuối 2.04 > 1.96 nên cần thêm khoảng 2–3% mẫu để giữ cùng power (với K = 5). Cái
được: thí nghiệm có tác động lớn dừng sớm, thời gian chạy trung bình giảm đáng kể.

## Trong thực tế

- Thư viện chuẩn cho group sequential là `rpact` / `gsDesign` (R) hoặc spending function Lan-DeMets.
  Mô phỏng như bài này là cách kiểm tra nhanh và dễ giải thích.
- Platform hiện đại (Statsig, Eppo, Optimizely) dùng always-valid inference: confidence sequence
  hoặc mSPRT, cho phép nhìn bất cứ lúc nào.
- Theo dõi SRM và guardrail an toàn hằng ngày là đúng và cần thiết. Peeking chỉ là vấn đề khi
  dùng metric chính để **tuyên bố thắng** sớm.

## Rubric cho hai câu hỏi tự trả lời

- Câu 1 đạt khi: tách theo dõi an toàn (được làm hằng ngày) khỏi ra quyết định trên metric chính
  (chỉ ở mốc định trước hoặc bằng phương pháp always-valid).
- Câu 2 đạt khi: nói được cái giá (biên cuối chặt hơn, cần thêm mẫu một chút) và cái được (dừng
  sớm khi tác động lớn).
