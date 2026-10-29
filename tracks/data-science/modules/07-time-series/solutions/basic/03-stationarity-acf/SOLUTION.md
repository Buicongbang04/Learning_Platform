# Lời giải: sai phân, ACF, ADF + KPSS

## Vì sao cần cả hai kiểm định

ADF có H0 là "có unit root" (không dừng); KPSS có H0 là "dừng". Một kiểm định "không bác bỏ" không
chứng minh H0 đúng, chỉ là chưa đủ bằng chứng. Dùng cả hai, hai giả thuyết ngược nhau, ta có bốn
trường hợp:

- Cả hai cùng nói dừng (ADF bác bỏ, KPSS không bác bỏ): dừng.
- Cả hai cùng nói không dừng: sai phân.
- Cả hai không bác bỏ: trend-stationary, nghĩa là dừng quanh một xu hướng xác định; trừ xu hướng
  thay vì sai phân (sai phân một chuỗi trend-stationary tạo ra MA unit root, làm model kém đi).
- Cả hai bác bỏ: difference-stationary theo bảng của statsmodels; thực tế hay gặp khi chuỗi dài
  và có thay đổi cấu trúc. Sai phân rồi kiểm lại.

Trên Olist (2017-01-09 tới 2018-08-19): chuỗi gốc ADF p = 0.069, KPSS p ≤ 0.01: không dừng. Sau sai
phân bậc 1: ADF p < 0.001, KPSS p ≥ 0.1: dừng. Khớp với hình: xu hướng tăng mạnh suốt 2017.

## Vì sao test chỉ đòi 15/20

Ở α = 0.05, mỗi kiểm định bác bỏ nhầm 5% số lần **theo thiết kế**. Với white noise, kết luận
`stationary` cần KPSS không bác bỏ nhầm (95%) và ADF bác bỏ đúng (power gần 100% với n = 1000): khoảng
95% số chuỗi. Trên 10 khối 20 seed của bản tham chiếu, số lần đúng thấp nhất là 16/20. Đòi 20/20 là
đòi kiểm định không bao giờ sai, không phải kiểm tra code.

## ACF

`acf` của statsmodels dùng mẫu số chung `sum(z^2)` cho mọi lag (không chia cho T − k), nên ACF luôn
là một dãy xác định dương. Sai lầm hay gặp: dùng `np.corrcoef(y[k:], y[:-k])`, cho kết quả gần nhưng
không bằng vì mỗi lag dùng trung bình và độ lệch chuẩn riêng.

## Phép ngược của sai phân

Model dự báo trên chuỗi đã sai phân thì phải cộng dồn lại. Với sai phân mùa vụ bậc 7, mức của bước
k cần mức của bước k − 7, lấy từ lịch sử khi k ≤ 7 và từ chính các mức vừa dựng khi k > 7. SARIMAX
làm bước này tự động khi bạn khai báo `d`, `D` trong model thay vì tự sai phân trước; đó là lý do nên
khai báo trong model (dự báo và khoảng dự báo ở mức gốc, không lo sai pha).
