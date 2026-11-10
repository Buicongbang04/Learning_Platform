---
title: Viết postmortem không đổ lỗi cho sự cố ETA đầu mùa COVID
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Viết một postmortem không đổ lỗi bám theo sự kiện và số đo thật: model ETA huấn luyện trên dữ liệu trước lockdown bị tụt chất lượng khi hành vi đi lại đổi. Học cách tách thời gian, nguyên nhân hệ thống và hành động, không tách người.

## Đề bài

Dữ liệu thật để bám: bài notebook `01-tlc-seasonal-vs-covid`. Model ETA huấn luyện trên NYC TLC 2020-02; trên 2020-04 MAE tăng từ 3.10 lên 5.01 phút (+62%), dự đoán cao hơn thực tế trung bình 4.4 phút, PSI cao nhất chỉ 0.152 (`hour`), tỉ lệ `passenger_count` thiếu tăng từ 0.8% lên 8.2%.
Các sự kiện còn lại bạn dựng thành một dòng thời gian hợp lý (ghi rõ chỗ nào là giả định): cảnh báo đầu tiên, thời điểm nhãn về cho thấy MAE tăng, quyết định, thời điểm train lại, thời điểm promote.

Viết `postmortem.md` (tối đa 2 trang) gồm:

1. **Tóm tắt**: một đoạn cho người không chuyên: chuyện gì, tác động, trạng thái hiện tại.
2. **Tác động**: có số (MAE, thời gian, số dự đoán lệch lớn, ai bị ảnh hưởng).
3. **Dòng thời gian**: mốc giờ/ngày, sự kiện, ai làm gì dưới dạng vai trò (on-call, chủ model), không dùng tên người.
4. **Phát hiện**: phát hiện nhờ gì (drift, proxy, nhãn), vì sao không sớm hơn; vai trò của PSI đã báo thấp.
5. **Nguyên nhân gốc và yếu tố góp phần**: chuỗi nguyên nhân hệ thống (bao giờ nhãn về, ngưỡng nào, thiếu cơ chế nào), không dừng ở "thế giới đổi".
6. **Điều gì đã tốt, điều gì may mắn**: những thứ cần giữ.
7. **Hành động**: danh sách có chủ sở hữu (vai trò), hạn, và cách kiểm hoàn thành; phân loại ngăn chặn, phát hiện sớm, giảm thiệt hại.

Không có đáp án duy nhất. Tự chấm bằng rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Có số đo thật từ notebook ở phần tác động và phát hiện; chỗ giả định được đánh dấu.
- Dòng thời gian và nguyên nhân không nêu tên người hay quy lỗi cho một cá nhân; mô tả hệ thống thiếu gì.
- Mỗi hành động có chủ sở hữu (vai trò), hạn và cách kiểm; ít nhất một hành động thuộc "phát hiện sớm" và một thuộc "giảm thiệt hại".
- Phần phát hiện giải thích vì sao PSI 0.152 một mình không đủ và cái gì bù vào.

## Gợi ý

### Gợi ý 1

Hỏi "tại sao" nhiều lần theo hệ thống: vì sao PSI thấp mà chất lượng giảm mạnh, vì sao nhãn chỉ giúp được sau một độ trễ, vì sao không có cơ chế báo sớm hơn.

### Gợi ý 2

Mỗi hành động tốt trả lời được: nếu sự cố giống hệt xảy ra lần nữa, hành động này làm nó nhỏ hơn hay ngắn hơn ở chỗ nào?
