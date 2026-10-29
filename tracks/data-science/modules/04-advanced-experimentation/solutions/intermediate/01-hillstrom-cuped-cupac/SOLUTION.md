# Lời giải: CUPED, hồi quy và CUPAC trên Hillstrom

Notebook lời giải: `variance_reduction.ipynb` (chạy được toàn bộ khi đã tải dữ liệu).

## Cách làm

- `cuped_effect` lọc hai nhánh trước, rồi mới tính `theta`. Tính `theta` trên cả ba nhánh cũng
  không làm lệch (covariate có trước random), nhưng làm báo cáo của từng cặp phụ thuộc nhánh thứ ba.
- `regression_effect` dựng công thức `metric ~ treat + ...`, bọc cột chuỗi trong `C()`, dùng SE
  `HC1` vì metric 0/1 và chi tiêu có variance khác nhau giữa các nhóm (heteroskedastic).
- `cupac_covariate` dùng `KFold` + `HistGradientBoostingRegressor`. Fold chỉ phụ thuộc seed và số
  dòng, nên dự đoán của mỗi dòng đến từ model chưa thấy dòng đó.

## Kết quả trên dữ liệu thật

Tương quan lớn nhất giữa một cột hồ sơ và metric là 0.075 (`recency` với `visit`, dấu âm); `history`
chỉ 0.065 với `visit`, 0.022 với `spend`.

Email nữ so với không gửi, metric `visit`:

| Cách | diff | SE | Giảm variance |
| --- | --- | --- | --- |
| Không điều chỉnh | 0.04523 | 0.003234 | |
| CUPED với `history` | 0.04509 | 0.003228 | 0.4% |
| Hồi quy 7 cột hồ sơ | 0.04541 | 0.003192 | khoảng 2.6% |
| CUPAC (gradient boosting, 5 fold) | 0.04554 | 0.003195 | 2.4% |

Với `spend`, cả CUPED và CUPAC đều giảm dưới 0.1%. Ước lượng tác động gần như không đổi qua mọi
cách, đúng như lý thuyết: điều chỉnh bằng covariate trước thí nghiệm không làm lệch, chỉ làm hẹp CI.

## Vì sao ít như vậy

Mức giảm variance bị chặn bởi $$\rho^2$$ (CUPED) hoặc $$R^2$$ của model (CUPAC). Covariate mạnh nhất
luôn là **chính metric đó, của cùng đơn vị, ở kỳ trước**. Hillstrom không có "visit tuần trước",
chỉ có tổng chi tiêu một năm, nên không có gì để CUPED khai thác. Ngược lại, doanh số tháng trước
của cửa hàng Rossmann tương quan 0.99 với tháng này và CUPED giảm 98% variance (mục 2 lý thuyết,
bài Advanced 01).

Bài học khi đi phỏng vấn hay đi làm: đừng hứa "CUPED giảm 50% variance". Đo $$\rho$$ trên dữ liệu
lịch sử trước, rồi mới tính lại MDE.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Có con số | Nêu mức giảm variance của từng cách, cho ít nhất `visit` |
| Giải thích đúng | Chỉ ra giới hạn $$\rho^2$$ / $$R^2$$ và vì sao `history` là covariate yếu |
| Phán đoán | Nói rõ CUPAC không đáng công với `spend` (hoặc lập luận ngược có số liệu) |
| Đề xuất | Covariate cụ thể nên log cho thí nghiệm sau (cùng metric, kỳ trước, cùng khách) |
| Không quá lời | Không nói điều chỉnh "làm tăng tác động"; tác động gần như không đổi |

## Sai lầm hay gặp

- Đưa `segment` (hoặc biến bị email làm thay đổi, như `conversion` khi metric là `spend`) vào
  features của CUPAC: covariate chứa treatment, tác động bị trừ mất.
- Huấn luyện model trên toàn bộ dữ liệu rồi dự đoán lại chính dữ liệu đó: dự đoán "nhớ" outcome,
  $$R^2$$ trông đẹp nhưng covariate không còn là thông tin trước thí nghiệm. Cross-fitting hoặc huấn
  luyện trên kỳ trước là bắt buộc.
- So SE của CUPED với SE của hồi quy nhưng một bên dùng HC1, một bên dùng SE thường: chênh lệch đến
  từ công thức, không phải từ phương pháp.
