# M07: Memo trình bày cho stakeholder

## Mục tiêu

Biến sáu milestone thành **một trang** mà COO và trưởng nhóm CSKH đọc trong ba phút và ra được quyết
định: nên làm gì tiếp với review xấu, tốn bao nhiêu, kỳ vọng được gì, giả định nào quyết định kết quả,
và điều gì chưa biết. Kèm một design doc ngắn cho đội kỹ thuật và README portfolio hoàn chỉnh.

Kiến thức nằm ở module 15: đổi metric ra tiền (README mục 3), monitoring và holdout (mục 5), làm việc
với stakeholder (mục 7). Hai bài là bản thu nhỏ của milestone này:
`modules/15-ml-system-design/exercises/advanced/01-olist-risk-alert-design` (design doc 12 mục) và
`modules/15-ml-system-design/exercises/advanced/02-stakeholder-one-pager` (memo, tornado, break-even).

**Kỳ vọng trung thực.** Module 15 tìm ra trên Olist rằng với bài toán "đơn sẽ trễ", một luật một dòng
("còn dưới 5 ngày tới ngày hẹn lúc giao vận chuyển") **ngang model về tiền**, và kể cả chính sách tốt nhất
cũng chỉ đáng khoảng 100 R$ mỗi tuần với giả định đang dùng. Capstone của bạn dự đoán review xấu, không
phải trễ, nên kết quả có thể khác: hãy để số của bạn quyết định. Nhưng memo phải đặt model cạnh luật
không ML, và nếu giá trị nhỏ thì nói thẳng. Không trích khoảng cách "model gấp đôi luật" tính gộp trên
test: nó chủ yếu do tháng 8/2018, khi ngày hứa giao rút ngắn và luật chọn gần 19% đơn. Chỉ dùng so sánh
tách giai đoạn của M03 (04–07/2018 và 08/2018), ở cùng k. "Ra mắt luật trước, model phải thắng luật trên holdout mới
được thay" hoặc "chạy thí nghiệm nhỏ để đo giá trị thật trước khi đầu tư" là khuyến nghị tốt khi dữ liệu
nói vậy.

## Việc cần làm

1. **Gom số liệu** vào một bảng nguồn trong `reports/NUMBERS.md`: mỗi con số có giá trị, đơn vị, milestone
   và notebook tạo ra nó. Memo chỉ được dùng số trong bảng này.
   - Quy mô vấn đề (M01): review xấu 12.8%, 54.1% ở đơn trễ, mức tăng đầu 2018 đến từ mix.
   - Lợi ích tối đa của logistics (M04): ATT của giao trễ, kèm giới hạn.
   - Năng lực và khối lượng (M02): số đơn mỗi tuần dự báo, số cảnh báo dự kiến ở phân vị lập kế hoạch.
   - Model và luật (M03): precision ở mức k đã chọn, so với luật và với model lúc vừa giao.
   - Thí nghiệm (M05): cỡ mẫu, thời lượng, MDE khả thi.
   - Sẵn sàng vận hành (M06): service, fallback, monitoring.
2. **Đổi ra tiền theo kịch bản** bằng `weekly_value`, `tornado`, `scenarios`, `break_even` của bài
   Advanced 02 module 15. Giá trị mỗi tuần $$G$$ với $$k$$ cảnh báo:

   $$
   G = k \cdot \left( \pi \cdot \Delta \cdot V - c \right)
   $$

   với $$\pi$$ là tỉ lệ đơn trong nhóm được cảnh báo mà tin nhắn có thể giúp, $$\Delta$$ là mức giảm xác
   suất review xấu nhờ tin nhắn, $$V$$ là thiệt hại của một review xấu, $$c$$ là chi phí một tin nhắn.
   Ghi lý do cho từng khoảng giả định. Đặc biệt nói rõ $$\pi$$ là "tỉ lệ review xấu" hay "tỉ lệ đơn
   thật sự trễ" trong nhóm: hai lựa chọn cho kết quả khác nhau vài lần.
3. **Break-even** viết theo cách người kinh doanh trả lời được: "một review xấu có thiệt hơn X R$ không?",
   "tin nhắn có giảm review xấu ở đơn trễ ít nhất Y điểm không?".
4. **`reports/MEMO.md`** (250–700 từ) gửi COO và trưởng nhóm CSKH:
   - Mục đầu "Khuyến nghị": một hành động, ai làm, khi nào, tốn bao nhiêu.
   - Con số theo ba kịch bản (bi quan, cơ sở, lạc quan), bằng R$ mỗi tuần và mỗi năm.
   - Giả định quyết định kết quả và điểm hoà vốn.
   - Điều chưa biết và cách biết (thí nghiệm M05, hoặc phương án nhỏ hơn nếu M05 không khả thi).
   - Rủi ro: quá tải CSKH, tin nhắn gây lo lắng cho đơn cuối cùng vẫn đúng hẹn, selection của review, drift.
   - Không có ROC-AUC trong memo; nếu cần chất lượng model, dùng "trong 10 đơn được nhắn, khoảng N đơn ...".
5. **`reports/DESIGN.md`** rút gọn từ khung 12 mục của bài Advanced 01 module 15 (tối thiểu: đóng khung,
   thời điểm dự đoán, baseline luật, metric offline và online, serving, monitoring, holdout, phương án
   đã loại). Dẫn tới M03, M05, M06 thay vì chép lại.
6. **Trình bày**: 5 slide hoặc 5 phút nói (tuỳ chọn ghi hình): vấn đề, điều đã biết, điều chưa biết,
   khuyến nghị, việc cần COO duyệt. Chuẩn bị câu trả lời cho ba câu hỏi khó: "Sao không dùng deep
   learning?", "Sao không ra mắt luôn cho mọi đơn?", "Con số +44 điểm nghĩa là tin nhắn giảm được 44 điểm
   phải không?".
7. **README portfolio** (`project/README.md`): khuyến nghị cuối trong hai câu, sơ đồ, bảng con số chính có
   link tới notebook, mục Decisions, Quick start, giới hạn.

Ví dụ tầm cỡ để tự kiểm (số của người soạn, giả định của module 15: $$\Delta = 0.15$$, $$V = 30$$ R$,
tin nhắn 0.5 R$): top 5% điểm của model lúc giao vận chuyển là khoảng 63 cảnh báo mỗi tuần, precision review
xấu 0.342, trong đó khoảng 18% đơn thật sự trễ. Nếu tin nhắn chỉ giúp đơn trễ thì giá trị khoảng 20 R$ mỗi
tuần (hoà vốn khi một review xấu thiệt khoảng 18 R$); nếu nó giúp mọi đơn sẽ bị review xấu thì khoảng 65 R$
mỗi tuần. Cả hai đều nhỏ so với chi phí vận hành một hệ thống ML. Memo tốt thấy điều đó và đề xuất bước
tiếp theo tương xứng.

## Kết quả nộp

- `project/reports/NUMBERS.md`, `MEMO.md`, `DESIGN.md`.
- Slide hoặc bản ghi trình bày (tuỳ chọn).
- `project/README.md` hoàn chỉnh; repo portfolio tách riêng nếu bạn chọn công khai.

## Tiêu chí đạt

- [ ] Câu đầu của memo là một hành động, không phải một metric model.
- [ ] Mọi con số trong memo có trong `NUMBERS.md` và truy được về notebook.
- [ ] Model được đặt cạnh luật không ML về tiền, theo so sánh tách giai đoạn của M03; kết luận đi theo số, kể cả khi luật thắng hoặc ngang.
- [ ] Ba kịch bản có R$ mỗi tuần; giả định nhạy nhất được chỉ ra bằng tornado; có điểm hoà vốn bằng lời.
- [ ] Memo tách bạch tác động của giao trễ (M04) với tác động chưa biết của tin nhắn (cần M05).
- [ ] Nếu thí nghiệm M05 không khả thi ở quy mô hiện tại, memo nói thẳng và đề xuất phương án thay thế cụ thể.
- [ ] 250–700 từ, người không chuyên đọc hiểu, không có thuật ngữ ML không giải thích.
- [ ] README portfolio có khuyến nghị, Quick start chạy được và mục giới hạn.
