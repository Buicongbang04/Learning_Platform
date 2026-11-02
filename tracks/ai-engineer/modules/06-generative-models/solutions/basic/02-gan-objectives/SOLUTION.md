# Lời giải: hàm mục tiêu của GAN

## Cách làm

Mọi loss viết bằng logits qua `softplus`: $$-\log\sigma(l) = \mathrm{softplus}(-l)$$ và $$-\log(1 - \sigma(l)) = \mathrm{softplus}(l)$$.

| Hàm | Viết bằng logits |
| --- | --- |
| `d_loss` | `softplus(-real).mean() + softplus(fake).mean()` |
| `g_loss_saturating` | `-softplus(fake).mean()` |
| `g_loss_nonsaturating` | `softplus(-fake).mean()` |

Ở logit -200, `torch.log(1 - torch.sigmoid(l))` vẫn ổn (bằng 0) nhưng `-torch.log(torch.sigmoid(l))` ra `inf`; softplus cho đúng 200.

**Saturating và non-saturating.** Đạo hàm theo logit: $$-\sigma(l)$$ và $$-(1 - \sigma(l))$$. Tại $$l = -8$$ (D chắc chắn mẫu là giả): $$-0.000335$$ và
$$-0.999665$$. Cả hai cùng dấu (đều đẩy logit của mẫu giả lên) và cùng điểm dừng, nhưng bản gốc chỉ có gradient khi G đã gần lừa được D, tức
học chậm nhất đúng lúc cần học nhanh nhất.

**D tối ưu và JS.** Thay $$D^* = p/(p + q)$$ vào $$V$$:
$$\sum p\log\frac{p}{p + q} + \sum q\log\frac{q}{p + q} = -\log 4 + \mathrm{KL}(p\,\|\,m) + \mathrm{KL}(q\,\|\,m)$$ với $$m = (p + q)/2$$, tức $$-\log 4 + 2\,\mathrm{JS}$$. Test kiểm
đẳng thức này bằng chính hai hàm của bạn và kiểm JS độc lập với một cài đặt khác, nên sai thang (bits thay vì nats) hay thiếu hệ số
$$\tfrac12$$ đều bị bắt. Ô mà $$p = q = 0$$ không đóng góp gì vào $$V$$, chọn $$D^* = 0.5$$ chỉ để có giá trị xác định. Bẫy cài đặt: `torch.where`
tính **cả hai nhánh**, nên `p * log(p)` với `p = 0` ra `0 * -inf = nan` ở nhánh bị bỏ; kẹp `p` trước khi `log`, nếu không gradient (dù không
dùng ở đây) cũng thành `nan`.

**Gradient penalty.** $$\hat x$$ là điểm trên đoạn thẳng giữa một mẫu thật và một mẫu giả (WGAN-GP lập luận critic tối ưu có gradient norm 1
trên các đoạn đó). `alpha` reshape thành `(B, 1, ..., 1)` để broadcast; `fake.detach()` vì penalty chỉ dành cho critic. `create_graph=True` là
điều kiện cần để `gp.backward()` tính được gradient theo tham số critic: test với critic tuyến tính so gradient đó với
$$2(\lVert w\rVert - 1)\,w/\lVert w\rVert$$. Norm lấy **theo từng mẫu** rồi mới trung bình; lấy norm của cả batch là sai (test bắt được).

**Mode coverage.** `cdist` → khoảng cách tới tâm gần nhất và chỉ số tâm; mặt nạ "chất lượng cao" $$< 3\sigma$$; `bincount` chỉ trên các mẫu
chất lượng cao. Đếm mode bằng mọi mẫu (cả mẫu nằm giữa hai tâm) là lỗi hay gặp: một G sinh đám mây mờ phủ cả vòng tròn sẽ được tính là
"phủ 8/8".

## Bẫy thường gặp

- Áp `sigmoid` trong D rồi dùng `BCEWithLogitsLoss` (sigmoid hai lần) hoặc ngược lại dùng `BCELoss` trên logits.
- Gradient penalty không `create_graph=True`: chạy được, penalty in ra đúng, nhưng không có tác dụng gì lên critic.
- Báo mode coverage mà không báo tỉ lệ mẫu chất lượng cao: phủ 8 mode với 30% mẫu tốt khác hẳn phủ 8 mode với 95%.
