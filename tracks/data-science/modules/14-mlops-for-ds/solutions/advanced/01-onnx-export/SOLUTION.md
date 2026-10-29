# Hướng làm: xuất model sang ONNX

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, kết quả tham khảo trên Olist và
rubric chấm.

## Hướng làm

**Xuất.** `to_onnx` với `initial_types` một input mỗi cột. Gộp mọi cột số vào một tensor
`[None, 10]` cũng được, nhưng khi đó hợp đồng phụ thuộc thứ tự cột, một nguồn lỗi im lặng khi phía
Go thêm hay đổi chỗ một trường. Input theo tên cột đổi lỗi im lặng thành lỗi rõ ràng ("missing
input: delay_days"). Tắt ZipMap để output là ma trận `[n, 2]` thay vì list các dict, thứ mà runtime
ở ngôn ngữ khác đọc rất vất vả.

**Chấm.** Cột số chuyển `float32`, NaN giữ nguyên để imputer trong graph xử lý. Cột chuỗi điền
`"missing"` trước khi đưa vào: converter không hỗ trợ `SimpleImputer` trên cột chuỗi với
`missing_values=np.nan` (`NotImplementedError: The converter is implemented when the missing values
are string`), nên bước điền thiếu cho cột chuỗi phải nằm **ngoài** model, và trở thành một phần của
hợp đồng.

**Parity.** So xác suất trên cả tập test, không chỉ vài dòng. Với logistic regression, sai lệch chỉ
do `float32` (cỡ 1e-7). Với cây, một số ít dòng có giá trị nằm sát ngưỡng chia và rẽ nhánh khác:
trong thử nghiệm 12 seed của bài, random forest có một seed với 0.4% dòng lệch tới 0.033. Đó là lý
do test đòi 99% chứ không đòi 100%, và lý do một số đội train model cây trên dữ liệu đã ép
`float32` ngay từ đầu.

## Kết quả tham khảo trên Olist (pipeline của module, C = 1.0, tập test 31 994 đơn)

| Đo | scikit-learn | onnxruntime |
| --- | --- | --- |
| Sai lệch xác suất lớn nhất | | 1.6e-7 |
| Nhãn (ngưỡng 0.5) khớp | | 100% |
| Chấm 1 dòng (trung bình 300 lần) | khoảng 3 ms | khoảng 0.02 ms |
| Chấm cả tập test một lần | khoảng 20 ms | khoảng 9 ms |
| Kích thước model | | khoảng 2.3 KB |

Con số độ trễ phụ thuộc máy; tỉ lệ mới đáng chú ý. Chấm một dòng bằng scikit-learn tốn gần như
toàn bộ thời gian vào chi phí cố định (kiểm tra đầu vào, DataFrame, ColumnTransformer), không phải
phép tính. ONNX loại phần đó: nhanh hơn khoảng 150 lần cho một dòng, nhưng chỉ khoảng 2 lần cho
batch lớn, nơi phép tính chiếm phần lớn.

## Các quyết định thiết kế cần cân nhắc

- **ONNX hay service Python riêng?** ONNX đáng khi: độ trễ chặt (gọi model trong vòng lặp xử lý
  request, p99 vài ms), không muốn vận hành thêm một service Python, hoặc cần chạy trên thiết bị
  (mobile, edge). Không đáng khi: feature cần logic Python phức tạp (truy vấn, text processing) mà
  phải viết lại ở Go, hoặc team không có ai duy trì phần chuyển đổi.
- **Phần nào ở trong graph, phần nào ở ngoài.** Mọi thứ ở ngoài graph (điền `"missing"`, tính
  `delay_days` từ timestamp) phải được viết lại ở phía Go, và là nguồn training-serving skew (bài
  Intermediate 02). Đưa càng nhiều vào graph càng tốt; cái gì không đưa được thì ghi rõ trong hợp
  đồng và có test parity end-to-end.
- **Version hợp đồng.** Lưu tệp `.onnx` cùng một tệp mô tả (tên/kiểu input, quy tắc điền thiếu,
  tên output, ngưỡng) trong cùng version của model registry. Đổi tên hay kiểu input là thay đổi
  phá vỡ: tăng major version, phía Go phải cập nhật trước.
- **Kiểm trong CI.** Mỗi lần đăng ký model mới: xuất ONNX, chạy parity trên một tập "golden" vài
  nghìn dòng (cả trường hợp biên: bang lạ, thiếu dữ liệu), lưu output kỳ vọng. Phía Go có test
  chấm cùng tập golden và so với output đã lưu. Hai bên kiểm cùng một tệp, không ai cần chạy code
  của bên kia.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Code đúng | 20 | Test pass; input theo tên cột; ZipMap tắt |
| Parity có phân tích | 15 | Số liệu trên Olist thật; giải thích được nguồn sai lệch (float32, cây) |
| Độ trễ đo đúng | 15 | Có warm-up, nhiều lần lặp, tách 1 dòng và batch; diễn giải chi phí cố định |
| Giới hạn converter | 15 | Nêu được bước không chuyển được và cách xử lý (đưa ra ngoài graph, viết lại, đổi transformer) |
| Hợp đồng với service | 20 | Tên, kiểu, thứ tự, điền thiếu, output, ngưỡng; có cách version và kiểm trong CI |
| Khuyến nghị | 15 | Đánh đổi rõ: độ trễ, vận hành, skew, ai duy trì; không mặc định "ONNX luôn tốt hơn" |

Từ 70 điểm: đủ để gửi đội backend bắt đầu tích hợp.
