# Lời giải: speculative decoding

## Cách làm

- `greedy_generate`: `reset` cho token đầu, rồi vòng lặp `extend([tok])[-1]`; kiểm điều kiện dừng **trước** khi gọi
  `extend` để không tốn một forward thừa sau token cuối.
- `prompt_lookup_draft`: hai vòng lặp, `n` giảm dần, vị trí bắt đầu duyệt từ phải sang trái và dừng ở lần khớp đầu tiên
  (tức gần cuối nhất). Chặn trên `len(context) - n - 1` để không khớp với chính đuôi.
- `speculative_generate`: một lượt gửi `[t] + đoán` (token đã chắc chắn nhưng chưa vào trạng thái, cộng khối đoán), duyệt
  từng dòng logits, nhận tới chỗ sai đầu tiên, token kế là argmax của dòng ngay sau phần đã nhận, rồi `truncate` về
  `len(prompt) + len(output)`. Giới hạn số token xin đoán bằng số token còn được sinh, và cắt khối đoán trả về dài hơn.

## Kết quả tham chiếu

PC của track, CPU 4 luồng (`nice`, máy có người dùng), Qwen2.5-0.5B-Instruct float32, 4 điều luật Zalo (1 200 tới 1 600 ký
tự, có khoản 2), 128 token tối đa, chạy notebook lời giải khoảng 4 phút. Mỗi ô là min / trung vị / max trên 4 điều luật:

| Tác vụ | $$k$$ | Tăng tốc | Tỉ lệ nhận | Số forward target (greedy: 128) |
| --- | --- | --- | --- | --- |
| Chép nguyên văn khoản 2 | 4 | 2.08 / 2.39 / 2.44 | 0.65 / 0.82 / 0.96 | 28 / 31.5 / 37 |
| Chép nguyên văn khoản 2 | 8 | 2.39 / 3.20 / 3.45 | 0.50 / 0.86 / 0.97 | 16 / 18 / 28 |
| Giải thích tự do | 4 | 1.09 / 1.24 / 1.58 | 0.18 / 0.25 / 0.42 | 56 / 79.5 / 85 |
| Giải thích tự do | 8 | 1.03 / 1.26 / 1.65 | 0.10 / 0.15 / 0.27 | 50 / 75.5 / 83 |

Output trùng greedy ở cả 16 lần chạy. Số đếm (tỉ lệ nhận, số forward) giống hệt ở lần chạy thử trước đó trên cùng máy;
thời gian lệch vài phần trăm.

Đọc bảng:

- **Chép nguyên văn** là đất của prompt lookup: phần lớn token đoán được nhận, số forward target giảm 4 tới 8 lần, tăng
  tốc 2 tới 3.5 lần. Không cần model nháp nào.
- **Giải thích tự do** vẫn nhanh hơn một chút dù chỉ 10% tới 42% token đoán được nhận: ở đây Qwen 0.5B diễn giải bằng cách
  nhắc lại nhiều cụm chữ của điều luật, nên n-gram vẫn trúng ở một số chỗ; và trên CPU, forward 5 tới 9 token của model
  0.5B chỉ tốn cỡ 1.5 lần forward 1 token (mục 5 lý thuyết đo 0.106 s so với 0.072 s), nên đoán sai không đắt.
- **Tăng $$k$$ làm tỉ lệ nhận ở tác vụ tự do giảm ở cả 4 điều luật** (khối dài thì phần đuôi khó khớp hơn), nhưng tăng tốc
  gần như không đổi: mỗi lượt kiểm dài hơn nhưng ít lượt hơn. Tỉ lệ nhận cao không phải mục tiêu; số token mỗi forward và thời
  gian mới là mục tiêu.
- **Model nháp 0.5B cho target 3B** (cell mở rộng, đo ở mục 5 lý thuyết): tác vụ chép tỉ lệ nhận khoảng 0.9 mà chỉ tăng tốc
  khoảng 1.2 lần, tác vụ tự do chậm hơn. Model nháp tốn khoảng 20% target, và forward khối của target 3B trên CPU tốn khoảng 2
  lần forward 1 token: cả hai số hạng ở mẫu của công thức tăng tốc đều xấu.
- Output trùng greedy ở đây vì mọi thứ chạy float32 trên CPU và các phép nhân ma trận cho cùng kết quả bất kể độ dài khối.
  Mục 5 lý thuyết cho thấy với `llama-cpp-python` (kernel lượng tử hoá, khối khác kích thước) output đổi ở 4 trên 6 tác vụ.

## Lỗi hay gặp

- Quên `truncate`: lượt sau dự đoán từ token đoán sai còn nằm trong cache; output lệch khỏi greedy ngay ở lượt đầu đoán sai.
- Lấy token kế từ dòng `a + 1` thay vì dòng `a`, hoặc nối token kế vào trạng thái hai lần.
- Đếm `proposed` theo `k` thay vì số token thực sự gửi kiểm (cuối chuỗi, hàm đoán trả ngắn hơn hoặc rỗng).
- Không cắt khối đoán dài hơn số token còn lại: output vượt `max_new_tokens`.
- Đo tăng tốc gồm cả thời gian nạp model hoặc lần chạy đầu (chưa làm nóng); hoặc so speculative với greedy **không có** KV
  cache, làm tăng tốc phồng lên nhiều lần.
- Với `DynamicCache` của Transformers 5.22, `crop` nhận số âm (số token cần bỏ); số dương báo lỗi.
