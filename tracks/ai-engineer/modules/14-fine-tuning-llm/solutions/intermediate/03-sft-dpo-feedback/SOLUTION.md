# Lời giải: SFT rồi DPO cho bài trích xuất phản hồi sinh viên

## Cách làm

- **`to_chat`**: system prompt cố định + câu phản hồi; nhãn thì thêm assistant là `json.dumps(..., ensure_ascii=False)` với
  thứ tự khoá cố định. Output mẫu phải **giống hệt từng ký tự** giữa các mẫu: model học đúng một chuỗi, không học năm biến
  thể khoảng trắng.
- **`parse_output`**: strict là `json.loads(text.strip())` rồi kiểm tập khoá bằng **đúng** `{"sentiment", "topic"}` và giá
  trị trong danh sách. Lenient tìm `\{[^{}]*\}` đầu tiên. Hai chế độ cho hai câu hỏi khác nhau: strict là "code của sản phẩm
  có dùng thẳng được output không", lenient là "model có biết nhãn không".
- **`macro_f1`**: F1 từng lớp từ TP/FP/FN, output hỏng (`None`) là FN của lớp thật và không là FP của lớp nào; trung bình
  không trọng số trên các lớp.
- **`generate_batch`**: pad **bên trái** (`padding_side = "left"`), `attention_mask` của tokenizer, greedy, cắt phần prompt
  bằng `enc["input_ids"].shape[1]`. Pad bên phải thì dòng ngắn phải sinh tiếp sau một loạt token pad: kết quả khác hẳn khi
  sinh từng câu (test bắt đúng chuyện này).
- **`preference_pairs`**: so `parse_output(output)` (strict) với nhãn vàng; khác (kể cả output hỏng định dạng) là một cặp,
  `rejected` giữ nguyên output của model. Đúng nghĩa on-policy: cặp dạy model tránh **chính** lỗi nó đang mắc.

## Kết quả (PC của track, RTX 3060 12GB, kernel `ai-gpu`, 16 phút cả notebook)

Thời gian từng pha: đo model gốc 67 giây (150 câu ghim + 3 166 câu test), SFT 8 000 câu 300 giây (500 bước, VRAM đỉnh 1.71
GiB), mỗi lượt DPO khoảng 91 tới 93 giây (136 bước, VRAM đỉnh tới 2.83 GiB), mỗi lượt đánh giá sau train khoảng 50 giây.

| Cấu hình | Ghim: JSON strict | Ghim: F1 cảm xúc | Ghim: F1 chủ đề | Test: JSON strict | Test: F1 cảm xúc | Test: F1 chủ đề |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5B gốc, chỉ prompt | 0.967 | 0.773 | 0.289 | 0.919 | 0.633 | 0.260 |
| 0.5B + SFT LoRA (8 000 câu) | 1.000 | 0.805 | 0.777 | 1.000 | 0.814 | 0.805 |
| + SFT thêm trên pool (3 426 câu) | 1.000 | 0.782 | 0.781 | 1.000 | 0.809 | 0.802 |
| + DPO, lr 5e-5, β 0.1 | 1.000 | 0.167 | 0.051 | 1.000 | 0.033 | 0.024 |
| + DPO, lr 5e-6, β 0.1 | 1.000 | 0.873 | 0.688 | 1.000 | 0.767 | 0.721 |
| `qwen2.5:3b` zero-shot (module 11, chỉ cảm xúc) | | 0.804 | | | | |
| `qwen2.5:3b` JSON Schema (module 11, chỉ cảm xúc) | | 0.852 | | | | |

Model SFT sai 543 trên 3 426 câu của pool (16%), mọi câu sai đều vẫn đúng định dạng: cặp ưu tiên chỉ khác nhau ở **nhãn**.
Chạy lại cả notebook ba lần (kernel GPU không tất định tuyệt đối): F1 cảm xúc của SFT trên ghim 0.796 tới 0.805, trên test
0.809 tới 0.814; số cặp 543 tới 556; DPO lr 5e-6 trên ghim 0.866 tới 0.873, trên test 0.767 tới 0.786. Mọi kết luận dưới
đây đúng ở cả ba lần.

Đọc bảng:

- **Model gốc 0.5B biết định dạng nhưng không biết nhãn chủ đề**: 92% output strict hợp lệ, nhưng tự đặt nhãn chủ đề ngoài
  danh sách (`"teacher"`, `"lưu ý"`), F1 chủ đề 0.26. SFT sửa cả hai: định dạng 100%, F1 chủ đề lên 0.80. Đây là đúng việc
  fine-tune giỏi: hành vi hẹp, nhãn có sẵn.
- **So với prompt của model 3B, SFT không thắng ở F1 cảm xúc**: 0.805 trên 150 câu ghim, ngang zero-shot của `qwen2.5:3b`
  (0.804) và thấp hơn JSON Schema (0.852). Chênh 0.05 với JSON Schema chưa chắc là nhiễu: module 11 đo hiệu cùng cỡ giữa
  JSON Schema và zero-shot bằng bootstrap theo cặp được +0.049 [+0.001, +0.103], khoảng tin cậy vừa chạm 0 (và biến mất khi
  chạy trên CPU). Ở đây chưa chạy bootstrap theo cặp giữa model SFT và model 3B, nên kết luận thận trọng: fine-tune **không
  hơn**, và có thể kém JSON Schema của model 3B một chút. Cái được là model nhỏ hơn 6 lần, định dạng tuyệt đối, và F1
  chủ đề mà prompt của module 11 chỉ đạt 0.676 khi trích 5 trường một lượt.
- **Vì sao tập ghim và tập test cho hai câu chuyện khác nhau**: tập ghim cân bằng (một phần ba neutral), tập test thật chỉ
  5% neutral, train cũng khoảng 4%. Model SFT học tỉ lệ của train nên ít khi đoán neutral: tốt trên test, kém trên ghim.
- **DPO lr 5e-6 dịch ranh giới về phía lớp hiếm**: cặp ưu tiên là các câu model sai, và lớp neutral sai với tỉ lệ cao nhất.
  Đếm trên một lần chạy SFT khác cùng cấu hình (556 cặp): 83 trong 133 câu neutral của pool thành cặp (62%), so với 300/1 604
  câu negative và 173/1 689 câu positive (phần lớn sai ở chủ đề); neutral chiếm 15% số cặp dù chỉ 4% pool.
  F1 cảm xúc tăng trên ghim (0.805 → 0.873), **giảm** trên test (0.814 → 0.767), F1 chủ đề giảm ở cả hai. Không phải cải
  thiện mà là đổi trade-off; nếu sản phẩm cần bắt câu neutral thì có thể đáng, nếu cần F1 trên lưu lượng thật thì không.
- **DPO lr 5e-5 phá hỏng model**: `rewards/margins` vẫn tăng (0.008 lên 0.346), `rewards/accuracies` 0.80, nhưng
  `logps/chosen` rơi từ -2.1 xuống -11.0: model hạ xác suất của **cả** câu đúng, chỉ là hạ câu sai nhanh hơn. Kết quả: mọi câu
  thành `{"sentiment": "neutral", "topic": "others"}`. Bài học: reward ngầm là thước đo **tương đối**, không thay được thước đo tác vụ; theo dõi
  `logps/chosen`; learning rate của DPO nhỏ hơn SFT nhiều lần (giá trị mặc định của `DPOConfig` trong TRL 1.17 là 1e-6).
  Thêm một số hạng SFT vào loss (`loss_type=["sigmoid", "sft"]` của TRL, kiểu RPO) ở cùng lr 5e-5 giữ được xác suất của câu
  đúng và F1 cảm xúc (0.788 trên ghim, 0.811 trên test, một lần chạy thử ngoài notebook), nhưng F1 chủ đề vẫn rơi xuống 0.600
  trên ghim và 0.619 trên test: chữa được sụp đổ, không biến DPO thành cải thiện.
- **Đối chứng công bằng**: SFT thêm trên đúng pool đó (nhãn vàng của cả 3 426 câu) không thêm gì (0.809 trên test). Với bài
  phân loại có nhãn, SFT đã khai thác gần hết tín hiệu; DPO chỉ đáng khi có thứ "câu A tốt hơn câu B" mà nhãn đúng/sai không
  tả được.
- **Giới hạn của cặp on-policy**: nhãn vàng của UIT-VSFC có nhiễu (cặp in ra đầu tiên của notebook: "cô dạy nhanh quá, khó
  hiểu dẫn đến chán nản" có nhãn vàng positive, model SFT đoán negative). DPO đẩy model về phía nhãn vàng ở mọi cặp, kể cả
  khi nhãn sai.

Một chi tiết bộ nhớ: `SFTConfig` và `DPOConfig` của TRL 1.17 **bật gradient checkpointing mặc định**, nên VRAM đỉnh ở
trên thấp. Tắt nó (`gradient_checkpointing=False`) với batch 16 thì một lần chạy thử ở bài Advanced 01 vượt 7 GiB và hết
bộ nhớ trên GPU đang dùng chung.

## Bẫy thường gặp

- Pad phải khi sinh theo batch; hoặc decode cả prompt rồi parse.
- Đo F1 bằng parser lenient rồi báo "JSON đúng 100%".
- DPO trên model chưa SFT, hoặc truyền `peft_config` mà không merge adapter SFT trước (reference khi tắt adapter là model
  gốc, không phải model SFT).
- So DPO với model SFT mà không có đối chứng "SFT thêm trên cùng dữ liệu".
- Chỉ đo trên tập ghim cân bằng: bỏ qua phân phối thật mà model sẽ gặp.
