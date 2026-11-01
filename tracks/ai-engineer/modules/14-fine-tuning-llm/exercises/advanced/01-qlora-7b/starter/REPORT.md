# QLoRA 7B cho bài trích xuất phản hồi sinh viên: có đáng không?

TODO: viết theo khung trong README của bài (ít nhất 400 từ). Người đọc là trưởng nhóm phải chọn model và phần cứng cho
bài trích xuất này: họ cần số đo trên cùng dữ liệu, không cần cảm nhận chung về model lớn.

## Tóm tắt

TODO: 2–3 câu có số: bạn khuyên cấu hình nào, hơn các cấu hình khác ở thước đo nào và bao nhiêu, đổi lại tốn gì.

## Thiết lập

TODO: dữ liệu (bao nhiêu câu train, câu nào, tập đánh giá), model, cấu hình QLoRA (định dạng 4 bit, double quant,
compute dtype, LoRA r/alpha/lớp đích, optimizer, batch hiệu dụng), phần cứng và GPU có bị chia với việc khác không.

## Ước lượng và đo bộ nhớ

TODO: bảng ước lượng trọng số (bf16, NF4) và số tham số LoRA cho các model; VRAM đo được lúc nạp, lúc train (đỉnh), lúc
sinh. Ước lượng lệch đo bao nhiêu và vì sao.

## Kết quả

TODO: bảng ít nhất 4 dòng: 7B chỉ prompt, 7B QLoRA, 0.5B LoRA trên cùng số câu, và một mốc từ bài Intermediate 03 hoặc
module 11. Cột: JSON đúng định dạng, F1 cảm xúc (150 câu ghim và test đầy đủ), F1 chủ đề, thời gian train, thời gian
đánh giá, VRAM đỉnh. Đọc bảng: chênh lệch nào lớn hơn nhiễu, chênh lệch nào không.

## Khuyến nghị

TODO: chọn gì cho bài toán này và vì sao; điều kiện nào làm bạn đổi lựa chọn (ít dữ liệu nhãn, nhiều nhãn hơn, cần
giải thích, chi phí serve, độ trễ); điều gì bảng của bạn chưa đo.
