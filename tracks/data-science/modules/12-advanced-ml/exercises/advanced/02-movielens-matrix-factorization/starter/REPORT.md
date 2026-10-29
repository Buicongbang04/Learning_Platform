# Recommender cho trang chủ: popularity, item-item hay matrix factorization?

Người đọc: Product Manager trang chủ và Engineering Manager. Tối đa một trang rưỡi.

## Kết luận

TODO: một câu: dùng gì cho user đã có lịch sử, dùng gì cho user mới.

## So sánh offline trên MovieLens (20% rating mới nhất mỗi user làm test)

TODO: bảng RMSE (với MF và baseline bias) và precision@10, recall@10, coverage (với popularity,
item-item, MF). Giải thích vì sao RMSE tốt hơn không đồng nghĩa với top-10 tốt hơn.

## Cold start

TODO: user mới, phim mới (bao nhiêu % rating trong test thuộc phim chưa có trong train?), chiến
lược cho từng trường hợp.

## Rủi ro và giới hạn của đánh giá offline

TODO: popularity bias, feedback loop, khác biệt giữa "xem" và "thích", vì sao vẫn cần A/B test.

## Kế hoạch tiếp theo

TODO: thí nghiệm online sẽ chạy (metric chính, guardrail), và cải tiến model đáng thử.
