# Lời giải: Beta-Binomial cho category ít đơn

## Dữ liệu

71 category, 94 455 đơn giao xong có review (1 369 đơn bị bỏ vì sản phẩm không có category hoặc
không có bản dịch). Số đơn mỗi category chênh từ 2 (`security_and_services`) tới 9 072
(`bed_bath_table`).

## Prior từ dữ liệu

`fit_beta_prior` cho a ≈ 30.5, b ≈ 208.9: prior mean 12.75%, `a + b ≈ 240`. Nghĩa là: ngoài nhiễu
Binomial, các category của Olist **khá giống nhau**; prior mạnh như thể đã thấy 240 đơn. Một
category cần vài trăm đơn thì dữ liệu riêng mới "thắng" prior.

## Tỉ lệ thô so với posterior

| Category | n | xấu | Thô | Posterior mean | CI 95% |
| --- | --- | --- | --- | --- | --- |
| security_and_services | 2 | 1 | 50.0% | 13.1% | [9.1%, 17.6%] |
| fashion_male_clothing | 105 | 24 | 22.9% | 15.8% | [12.2%, 19.9%] |
| office_furniture | 1 236 | 270 | 21.8% | 20.4% | [18.4%, 22.5%] |
| bed_bath_table | 9 072 | 1 427 | 15.7% | 15.6% | [14.9%, 16.4%] |

Theo tỉ lệ thô, `security_and_services` đứng đầu và `fashion_male_clothing` thứ hai. Theo posterior,
`office_furniture` đứng đầu rõ rệt; hai category nhỏ tụt xuống vì phần lớn chênh lệch của chúng là
nhiễu. Đội category nên làm việc với nội thất văn phòng trước (hàng cồng kềnh, giao lâu, lắp đặt
khó), không phải với một category 2 đơn.

`fashion_male_clothing` vs `bed_bath_table`: thô 22.9% vs 15.7% trông khác hẳn, nhưng posterior
15.8% vs 15.6%, `prob_greater` khoảng 0.52: không có bằng chứng category thời trang nam tệ hơn.

## Các quyết định cần cân nhắc

- **Prior từ đâu.** Empirical Bayes dùng chính dữ liệu, nhanh và hợp lý khi có nhiều nhóm (ở đây 71).
  Với vài nhóm, ước lượng prior rất nhiễu; khi đó dùng prior từ kinh nghiệm hoặc mô hình phân cấp
  đầy đủ (PyMC, Stan) để tính cả bất định của prior.
- **Method of moments vs MLE của Beta-Binomial.** MoM đơn giản, đủ tốt khi có nhiều nhóm; MLE (tối
  ưu số như bài Basic 02) hiệu quả hơn. Khác biệt nhỏ so với khác biệt giữa "có shrinkage" và "không".
- **Khi tau2 ≤ 0.** Dữ liệu không cho thấy category khác nhau thật: kết luận đúng là "dùng tỉ lệ chung
  cho mọi category", không phải lỗi cần sửa.
- **Equal-tailed vs HPD.** Với posterior gần đối xứng (a, b lớn) hai loại gần như trùng.

## Sai lầm hay gặp

- Lọc "category có ít nhất 30 đơn" rồi xếp hạng thô: bỏ mất thông tin và ngưỡng 30 là tuỳ tiện;
  category 31 đơn vẫn bị nhiễu lấn át.
- Diễn giải CI tần suất như xác suất ("95% khả năng p nằm trong khoảng"): chỉ credible interval
  Bayesian mới được nói vậy, và chỉ khi tin prior.
- Dùng prior quá mạnh không có cơ sở, rồi mọi category trông giống nhau. Luôn báo cáo prior đã dùng.
