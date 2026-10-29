# Lời giải: Regression Discontinuity bằng local linear

## Vì sao local linear, không phải so trung bình hai bên

So trung bình trong cửa sổ `[−h, 0)` với `[0, h)` lẫn hai thứ: bước nhảy thật và độ dốc của
`E[y | x]` (người điểm cao hơn vốn có doanh thu cao hơn). Local linear ước lượng một đường mỗi bên
và lấy khoảng cách **tại đúng ngưỡng**, nên phần dốc bị loại. Kernel tam giác cho quan sát gần
ngưỡng trọng số lớn hơn, hợp lý vì chúng giống nhau nhất.

Không dùng đa thức bậc cao toàn cục (bậc 3, 4, 5 trên toàn bộ dữ liệu): nó cho trọng số lớn và
dao động tới các điểm xa ngưỡng, rất nhạy với lựa chọn bậc (Gelman & Imbens 2019).

## Bandwidth là đánh đổi bias–variance

Seed 0 của mô phỏng (bước nhảy thật 0.3):

| Bandwidth | Ước lượng | SE | n |
| --- | --- | --- | --- |
| 0.05 | 0.317 | 0.074 | 991 |
| 0.10 | 0.255 | 0.050 | 2 022 |
| 0.20 | 0.254 | 0.035 | 4 102 |
| 0.50 | 0.230 | 0.022 | 10 067 |
| 1.00 | 0.092 | 0.015 | 20 000 |

Bandwidth hẹp: ít bias, SE lớn. Bandwidth rộng: SE nhỏ nhưng đường cong bên phải bị ép thành đường
thẳng, kéo ước lượng về 0.09, **với SE nhỏ nhất**, nghĩa là sai một cách tự tin. Trong thực tế:

- Chọn bandwidth bằng thuật toán tối ưu MSE (Calonico, Cattaneo, Titiunik; gói `rdrobust`) và dùng
  CI "robust bias-corrected" của họ.
- Luôn báo cáo bảng độ nhạy như trên. Kết luận chỉ đứng vững nếu không đổi dấu, không đổi độ lớn
  đáng kể quanh bandwidth đã chọn.
- Vẽ binned scatter (trung bình y theo từng bin của x) trước khi ước lượng gì.

## Manipulation

RDD dựa trên giả định đơn vị **không kiểm soát chính xác** được x quanh ngưỡng. Nếu seller biết
ngưỡng và "làm đẹp" điểm của mình, người ngay trên ngưỡng không còn giống người ngay dưới (họ chủ
động hơn, biết luật hơn), và bước nhảy lẫn cả khác biệt đó. Dấu hiệu: mật độ x bị khuyết bên dưới,
dồn lên bên trên ngưỡng. Mô phỏng có bunching cho p < 1e-10.

Các kiểm tra đi kèm: covariate trước can thiệp (doanh thu năm trước, số năm hoạt động) không được
nhảy tại ngưỡng; placebo cutoff (ngưỡng giả ở chỗ không có chính sách) không được có bước nhảy.

## Kết quả là tác động ở đâu

RDD cho tác động **tại ngưỡng**: seller điểm quanh 0. Nó không nói gì về seller điểm −0.8 nếu được
gói ưu tiên. Đây là đánh đổi cốt lõi: internal validity rất cao, external validity hẹp.
