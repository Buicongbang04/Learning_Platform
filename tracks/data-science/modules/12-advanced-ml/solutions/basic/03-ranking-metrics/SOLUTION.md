# Lời giải: metric xếp hạng @k

## Cách làm

Mỗi hàm đổi `relevant` sang `set`, duyệt `recommended[:k]` một lần. Với ví dụ trong test
(`a b c d e`, relevant `{b, d, x}`):

| Metric | Giá trị | Tính |
| --- | --- | --- |
| P@5 | 0.4 | 2 hit / 5 |
| R@5 | 0.667 | 2 hit / 3 relevant |
| AP@5 | 0.333 | (1/2 + 2/4) / min(3, 5) |
| NDCG@5 | 0.498 | $$\frac{1/\log_2 3 + 1/\log_2 5}{1 + 1/\log_2 3 + 1/\log_2 4}$$ |

## Mỗi metric trả lời câu hỏi gì

| Metric | Câu hỏi | Nhạy với thứ tự? | Dùng khi |
| --- | --- | --- | --- |
| Precision@k | Trong k ô hiển thị, bao nhiêu ô "trúng"? | Không (trong top k) | Số ô cố định (carousel 10 phim) |
| Recall@k | Bắt được bao nhiêu phần những gì user thích? | Không | Bước candidate generation (lấy 500 ứng viên) |
| AP@k / MAP@k | Hit có nằm ở đầu danh sách không? | Có | So thuật toán xếp hạng, relevance nhị phân |
| NDCG@k | Như AP, giảm theo log; mở rộng được cho relevance nhiều mức (rating 1–5) | Có | Search, feed; chuẩn công nghiệp |
| Hit rate@k | User có ít nhất 1 hit không? | Không | Leave-one-out (mỗi user 1 item test) |

Precision@k bị giới hạn bởi số item relevant: user chỉ có 2 phim trong tập test thì P@10 tối đa là
0.2. Vì thế không so P@10 giữa hai bộ dữ liệu có độ dài lịch sử khác nhau.

## Lỗi hay gặp

- Chia precision cho `len(recommended)` thay vì k: hệ thống trả ít gợi ý hơn được thưởng.
- IDCG tính trên toàn bộ tập relevant thay vì tối đa k item: NDCG không bao giờ đạt 1.
- Lấy trung bình trên user có gợi ý (bỏ user cold start): điểm offline đẹp, online không đẹp.
- Gợi ý lại item user đã tương tác trong train: offline thì không hit (item đó không nằm trong
  test), nhưng nhiều đội quên lọc ở bước serving.
