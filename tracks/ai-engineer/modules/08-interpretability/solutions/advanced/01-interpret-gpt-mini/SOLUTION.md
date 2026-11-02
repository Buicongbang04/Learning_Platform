# Hướng làm: mổ xẻ GPT mini tiếng Việt của bạn

Bài không có code lời giải cho pipeline: model, nhiệm vụ và thuộc tính probe là của bạn. Hai hàm được chấm ngắn; giá trị của bài nằm
ở một báo cáo mà mỗi kết luận đứng vững trước câu hỏi "đối chứng đâu, khoảng tin cậy đâu, điều này không chứng minh gì". Dưới đây là
các quyết định cần cân nhắc, kết quả của bản tham chiếu trên checkpoint của module 05, và rubric.

## Hai hàm được chấm

- `top_examples`: sắp chỉ số phẳng theo `(-value, index)`, duyệt lần lượt, bỏ giá trị không dương, bỏ hàng đã dùng khi
  `one_per_row`, dừng khi đủ k. Một ngữ cảnh dài lặp một cụm (bảng số liệu, danh sách tên xã) có thể chiếm hết top-k nếu không giới
  hạn mỗi hàng một ví dụ.
- `bootstrap_ci`: một lệnh `integers(0, n, (n_boot, n))`, trung bình theo hàng, `np.quantile` hai đầu. Đơn vị mẫu lại phải là đơn vị
  **độc lập**: cặp prompt, ngữ cảnh hoặc câu, không phải token (token trong cùng ngữ cảnh tương quan, khoảng tin cậy theo token hẹp
  giả tạo).

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Model | checkpoint cấu hình PC của module 05 (6 tầng × 384, 6 head, bpc 1.347) | model của người học; bản laptop 4 tầng cũng làm được, ít cơ chế hơn |
| Văn bản đánh giá | `tst2012.vi` + `tst2013.vi` (75 079 token BPE), 80 ngữ cảnh 128 token | khác miền với Wikipedia lúc train: kiểm tra trên dữ liệu model chưa thấy |
| Bản đồ head | dãy ngẫu nhiên lặp lại half 50 (seed 0), previous-token trên văn bản | cùng phép đo với bài Intermediate 01 để so với GPT-2 |
| Probe | cảm xúc câu UIT-VSFC (bỏ trung tính) trung bình theo câu; token đã xuất hiện | một thuộc tính ngữ nghĩa có nhãn thật, một thuộc tính cần ngữ cảnh |
| Patching | chép chuỗi: dãy 30 token lặp hai lần, đổi token thứ 12 của bản 1 | model nhỏ không làm được IOI tiếng Anh; nhiệm vụ phải là thứ model làm đúng |
| SAE | TopK k = 32, 3 072 latent, residual vào tầng 3, 500 nghìn token `train.vi` | tầng giữa; TopK dễ chỉnh ở ngân sách nhỏ (bài Intermediate 03) |

## Kết quả tham chiếu

CPU 4 luồng, PC dùng chung, ngày 2026-11-01; phần SAE chạy trên CPU (thu activation 90 giây,
train SAE 143 giây).

**Bản đồ head.** Induction: 5.5 = 0.62, 5.0 = 0.55, rồi 4.1 = 0.20; previous-token (văn bản): 3.4 = 0.70, 2.1 = 0.48; không head
duplicate nào trên 0.03. Loss dãy lặp lại: bản 1 là 12.60 nat, bản 2 là 5.75 nat (GPT-2 small: 13.24 và 0.22). Mean ablation head induction
mạnh nhất, hai, ba head: loss bản 2 lên 8.69, 11.70, 12.14; bản 1 chỉ lên tối đa 12.87. Hai head ngẫu nhiên (điểm induction dưới 0.1),
5 lần: 5.79, 6.30, 8.54, 9.19, 5.95. Kết luận: hai head tầng cuối cần cho việc chép, mạnh hơn trung bình một cặp head bất kỳ; nhưng hai
trong năm cặp ngẫu nhiên cũng làm hỏng nhiều (có thể chúng chứa head previous-token mà mạch cần), nên không viết "chỉ hai head này".

**Logit lens** (`tst2013.vi`): trùng top-1 với model 0.23, 0.20, 0.30, 0.44, 0.58, 1.00 qua 6 tầng; CE 5.72 tới 3.61.

**Probe cảm xúc** (4 000 câu train, 1 500 câu test, majority 0.538): embedding trung bình 0.904, các tầng 0.892–0.905; model khởi tạo
ngẫu nhiên 0.897 ở embedding, 0.843–0.867 ở các tầng. Cảm xúc nằm ở từ vựng; các tầng đã train giữ thông tin tốt hơn tầng ngẫu nhiên
nhưng không thêm gì đo được.

**Probe token đã xuất hiện** (10 160 token, majority 0.704, tra theo loại token 0.777): model đã train 0.787–0.809 qua các tầng, selectivity
từ −0.074 tới +0.006; model ngẫu nhiên 0.764–0.789. Khác hẳn GPT-2 (0.98 ở tầng 0): GPT mini không có head duplicate-token, và thông tin
này không đọc được tuyến tính rõ hơn token id. Đây là một kết quả âm có giá trị, nên báo cáo kèm giải thích.

**Patching** (20 dãy, logit difference clean 8.26, corrupted −6.64): residual vào tầng 0–5 ở vị trí của token bị đổi 1.00, 0.98, 0.98,
0.96, 0.97, 0.88; ở vị trí dự đoán 0 cho tới tầng 5 (0.11); mọi ô khác dưới 0.05. Patch head: 5.5 = 0.42, 5.0 = 0.38, còn lại dưới 0.06.
Patching xác nhận bằng can thiệp điều điểm attention gợi ý.

**SAE** (tầng 3): FVU 0.156, L0 32, latent chết 0.7%, CE 4.023 lên 4.215 khi ghép SAE (perplexity tăng khoảng 21%), recovered 0.963 so với
zero ablation, 0.947 so với mean ablation.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | 2 hàm pass mọi test |
| Sanity check và tái lập | 15 | ghi checkpoint, dữ liệu, seed; có phép kiểm có đáp án biết trước (lens tầng cuối khớp model, patching tầng 0 khôi phục đúng 1, tổng thành phần bằng stream cuối) |
| Head và logit lens | 15 | bản đồ head có số, ablation mean so với head ngẫu nhiên và với phần không liên quan; so với GPT-2 small |
| Probe | 15 | đủ majority, baseline token/embedding, control task hoặc tương đương, model khởi tạo ngẫu nhiên, chia theo câu; khoảng tin cậy |
| Patching | 15 | cặp clean/corrupted khác một token, model làm đúng run clean, thước đo logit difference chuẩn hoá, bảng theo tầng × vị trí và theo head, bootstrap theo cặp |
| SAE | 15 | FVU, L0, latent chết, CE với cả hai baseline; ít nhất 10 latent đọc bằng `top_examples`, có cả latent không đặt tên được |
| Diễn giải trung thực | 15 | bảng kết luận: mỗi dòng có bằng chứng, đối chứng và câu "không chứng minh"; báo cả kết quả âm; không viết kết luận nhân quả từ bằng chứng tương quan |

Đạt từ 70 điểm. Báo cáo chỉ có điểm attention và top activation mà không có can thiệp hay đối chứng nào không quá 40 điểm.
