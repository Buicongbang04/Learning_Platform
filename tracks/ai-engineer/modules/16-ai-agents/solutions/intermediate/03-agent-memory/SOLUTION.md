# Lời giải: memory dài hạn

## Cách làm

**`MemoryStore.add`** chuẩn hoá vector một lần lúc ghi, nên cosine là một phép nhân ma trận với mọi ghi nhớ. Trùng
(cosine từ ngưỡng trở lên) thì **cập nhật tại chỗ**: văn bản, thời điểm, nguồn, vector mới, `importance` lấy giá trị
lớn hơn, `id` giữ nguyên (thứ khác trong hệ thống có thể đang trỏ tới id đó). Vượt `capacity` thì xoá ghi nhớ có
`importance * recency_weight(t - m.t)` nhỏ nhất **trừ** cái vừa thêm: nếu không, một ghi nhớ mới có `importance`
thấp bị xoá ngay khi vào, kho không bao giờ nhận được gì mới.

**`search`** tính điểm cho mọi ghi nhớ rồi sắp một lần với khoá `(-score, -t, -id)`: bằng điểm thì mới hơn trước. Với
vài chục nghìn ghi nhớ cách này vẫn đủ nhanh; lớn hơn thì cần ANN index (module 12) và độ mới, độ quan trọng tính lại
trên top vài trăm ứng viên.

**`extract_facts`**: một lời gọi có `json_schema`, gom mọi kiểu hỏng (`LLMError`, JSON hỏng, thiếu khoá, sai kiểu) về
`[]`. Ghi thiếu một thông tin thì lần sau người dùng nhắc lại; làm sập cả lượt hội thoại vì JSON hỏng thì không chấp
nhận được. Prompt có hai ví dụ (một câu có thông tin, một câu nhờ việc): không có ví dụ, `qwen2.5:3b` với schema trả
`{"facts": []}` cho cả câu có thông tin rõ ràng như "Mình bị dị ứng hải sản" (thử trên 3 câu khi viết bài, cả 3 rỗng).

## Kết quả (notebook lời giải, PC của track, `qwen2.5:3b`, `bge-m3`, `temperature` 0)

**Ghi.** 108 lượt, 24 lượt có thông tin. Kho `raw` còn 51 ghi nhớ: 57 lượt chuyện phiếm lặp lại nguyên văn (cùng mẫu
câu, cùng từ điền) có cosine 1.0 với lượt trước và bị gộp. Kho `fact` có 52 ghi nhớ (7 lần gộp). Trích xuất mất 142
giây cho 108 lượt; 8 trong 84 lượt chuyện phiếm vẫn ra "thông tin" (5 trong số đó là cùng câu "Mình đang hơi buồn
ngủ.", trích thành "Người dùng cảm thấy hơi buồn ngủ." và gộp lại một ghi nhớ), 1 trong 24 lượt có thông tin trích
rỗng. "Mực vừa được 3 tuổi hôm qua." thành "Người dùng vừa được 3 tuổi": trích từng lượt một mất ngữ cảnh rằng Mực
là con chó (cách sửa: đưa vài lượt trước, hoặc các ghi nhớ liên quan, vào prompt trích xuất).

**Retrieval** (hit@k trên 18 câu có bằng chứng; nhóm: cũ 6, mới 7, cập nhật 5):

| Kho | k | `w_rec` | cũ | mới | cập nhật | tổng |
| --- | --- | --- | --- | --- | --- | --- |
| raw | 1 | 0 | 6/6 | 7/7 | 1/5 | 14/18 |
| raw | 1 | 0.3 | 4/6 | 7/7 | 3/5 | 14/18 |
| raw | 5 | 0 | 6/6 | 7/7 | 4/5 | 17/18 |
| raw | 5 | 0.3 | 5/6 | 7/7 | 4/5 | 16/18 |
| fact | 1 | 0 | 5/6 | 6/7 | 1/5 | 12/18 |
| fact | 5 | 0 | 6/6 | 6/7 | 5/5 | 17/18 |
| fact | 5 | 0.3 | 6/6 | 6/7 | 5/5 | 17/18 |

Ở hit@1 trọng số độ mới làm đúng cái đã nói ở mục 5 lý thuyết: nhóm cập nhật lên (1 lên 3 câu: ghi nhớ mới thắng ghi
nhớ cũ cùng chủ đề), nhóm cũ xuống (6 xuống 4), tổng không đổi. Ở top-5 hiệu ứng nhỏ (một câu), trong mức một câu hỏi
đổi chỗ. Hai kho ngang nhau ở top-5. Kho fact giới hạn 20 ghi nhớ (importance như nhau, nên chỉ còn độ mới quyết
định) rơi từ 17/18 xuống 8/18 và mất **cả 6** câu nhóm cũ: quên theo độ mới mà không có độ quan trọng xoá đúng thứ
bền vững nhất (tên, dị ứng). Đó là lý do Generative Agents chấm `importance` bằng LLM lúc ghi.

**Trả lời** (20 câu, chấm bằng từ khoá):

| Điều kiện | Đúng / 20 | Token prompt TB | Giây trung vị |
| --- | --- | --- | --- |
| không memory | 1 | 60 | 0.5 |
| toàn bộ lịch sử | 4 | 3 824 | 23.1 |
| memory raw top-5 | 14 | 139 | 0.8 |
| memory fact top-5 | 13 | 124 | 0.8 |

- **Toàn bộ lịch sử** báo 3 824 token prompt dù lịch sử dài hơn nhiều: Ollama đã bỏ các message cũ để vừa 4 096 (mục 3
  lý thuyết), nên cả 6 câu nhóm cũ sai ("Bạn chưa nói mình tên là gì"). Mỗi câu mất khoảng 23 giây, gấp gần 30 lần
  điều kiện memory, trên PC dùng chung. Chúng tôi không đo tách thời gian đó ra từng phần (xử lý prompt dài, việc Ollama
  cắt bớt message); con số tuyệt đối sẽ khác trên máy bạn.
- **Memory** dùng chưa tới 140 token mỗi câu và đúng 13 tới 14 câu. Nhóm cập nhật vẫn kém (1 tới 2 trên 5): retrieval
  có ghi nhớ mới trong top-5, nhưng thường cả ghi nhớ cũ cũng ở đó ("kỹ sư dữ liệu" cạnh "kỹ sư machine learning"), và
  model 3B chọn cái cũ dù prompt ghi "mới nhất ưu tiên". Sửa ở **chính sách ghi** (khi ghi thông tin mâu thuẫn, đánh
  dấu hoặc xoá cái cũ) hiệu quả hơn hy vọng model tự chọn lúc đọc; ghi kèm ngày vào từng ghi nhớ cũng giúp.
- Một lần chạy script tham chiếu trước đó (cùng dữ liệu, cùng cấu hình) cho 5, 14, 14 câu ở ba điều kiện cuối: chênh 1
  câu giữa hai lần chạy, nhỏ hơn nhiều so với khoảng cách giữa các điều kiện.
- Chấm bằng từ khoá có lỗi theo cả hai chiều: câu "không có" được chấm đúng khi câu trả lời chứa "không" (kể cả "Bạn
  chưa nói... không"), câu lạc đề cũng dễ chứa chữ đó. Với nhiều câu hơn, dùng LLM-as-judge có hiệu chuẩn (module 13
  bài Advanced 01, module 20).

## Bẫy thường gặp

- Quên chuẩn hoá vector: cosine thành tích vô hướng thô, văn bản dài thắng chỉ vì vector dài.
- Quên trong `capacity` mà để cái vừa thêm làm ứng viên.
- Gộp trùng bằng ngưỡng quá thấp (0.8 chẳng hạn): "Hôm nay trời nóng" và "Hôm nay trời mưa" có cosine khoảng 0.83 với
  `bge-m3`, gộp chúng là mất thông tin.
- Đặt trọng số độ mới cao để "sửa" câu hỏi cập nhật: hỏng câu hỏi về thông tin cũ (bảng trên).
