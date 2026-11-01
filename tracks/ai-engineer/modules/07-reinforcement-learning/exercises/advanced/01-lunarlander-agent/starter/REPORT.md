# Agent hạ cánh LunarLander

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp chưa xem code: họ cần
biết agent làm được gì, đạt bao nhiêu điểm trên bao nhiêu seed, và bạn hiểu vì sao.

## Tóm tắt

TODO: 3–4 câu có số: thuật toán, kích thước model, điểm đánh giá (trung bình, IQM, tỉ lệ episode ≥ 200) trên 100 episode cố định
cho từng seed, thời gian train và phần cứng. Link video.

## Bài toán và thiết lập

TODO: env, observation, action, reward; cấu hình agent (bảng siêu tham số); seed train, seed chọn checkpoint, seed đánh giá;
phần cứng, số luồng, wall-clock.

## Đường cong học

TODO: hình đường cong theo số bước env (trung bình và độ phân tán giữa seed) và câu đọc hình; chẩn đoán PPO (approx KL, clip
fraction, entropy) nếu có.

## Đánh giá

TODO: bảng từng seed (trọng số cuối và checkpoint tốt nhất): trung bình, độ lệch chuẩn, IQM, tỉ lệ ≥ 200, so với policy ngẫu nhiên
và "không làm gì". Nói rõ policy greedy hay lấy mẫu.

## Video và hành vi

TODO: link video (vd. `[Video](videos/best.mp4)`), mô tả agent làm gì tốt, thất bại kiểu gì (xem vài episode điểm thấp nhất).

## Lỗi đã gặp

TODO: ít nhất 2 lỗi thật: triệu chứng (con số), cách phát hiện, cách sửa.

## Giới hạn và bước tiếp theo

TODO: điều kết quả nói được và không nói được, so với thư viện chuẩn (nếu có), Atari hoặc action liên tục.
