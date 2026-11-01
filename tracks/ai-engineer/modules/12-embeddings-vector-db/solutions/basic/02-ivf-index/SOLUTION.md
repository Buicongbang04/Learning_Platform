# Lời giải: IVF index tự viết

## Cách làm

**`assign`.** `np.argmin(sq_dists(x, centroids), axis=1)`: `argmin` trả lần xuất hiện **đầu tiên** của giá trị nhỏ nhất,
nên bằng khoảng cách thì chỉ số nhỏ thắng.

**`kmeans`.** Khởi tạo đúng quy tắc (`rng.choice(len(x), n_clusters, replace=False)`, phải `.copy()` để không sửa `x`), rồi
`n_iter` vòng: `labels = assign(x, centroids)`; với mỗi cụm có điểm, centroid là trung bình. Cụm rỗng giữ centroid cũ thay
vì `mean` của mảng rỗng (ra `NaN` kèm cảnh báo, và `NaN` làm mọi khoảng cách tới centroid đó thành `NaN`).

**`IVFIndex.train`** gọi `kmeans`, tạo `nlist` mảng id rỗng. **`add`** gán cụm cho cả lô một lần, id mới là
`len(self.vectors) + chỉ số trong lô`; `np.flatnonzero(labels == c)` cho id của cụm `c` theo thứ tự tăng, nối vào danh sách
cũ (id cũ luôn nhỏ hơn id mới nên danh sách vẫn tăng dần).

**`search`.** Sort ổn định khoảng cách tới centroid, lấy `nprobe` cụm đầu; ghép các danh sách rồi **sort theo id** trước khi
tính khoảng cách; sort ổn định khoảng cách, lấy `k`. Bước sort theo id là để quy tắc "bằng khoảng cách thì id nhỏ trước"
không phụ thuộc thứ tự probe (test cuối dựng tay đúng trường hợp đó). `n_scanned` là số ứng viên.

## Chi phí và tham số

Một query tốn $$n_{\text{list}}$$ phép tính khoảng cách tới centroid cộng khoảng $$n_{\text{probe}} \cdot N / n_{\text{list}}$$ tới
vector (nếu các cụm đều cỡ nhau):

$$
C(n_{\text{list}}) \approx n_{\text{list}} + n_{\text{probe}}\,\frac{N}{n_{\text{list}}}
$$

nhỏ nhất khi $$n_{\text{list}} = \sqrt{n_{\text{probe}} N}$$; quy tắc kinh nghiệm của FAISS là $$n_{\text{list}}$$ cỡ
$$4\sqrt{N}$$ tới $$16\sqrt{N}$$ cho corpus lớn. Trên test 2 000 vector ngẫu nhiên, `nlist = 32`, `nprobe = 1` chỉ quét
khoảng 1/32 dữ liệu và bỏ sót nhiều láng giềng: dữ liệu ngẫu nhiên đều không có cụm, láng giềng thật của một query nằm rải
qua nhiều ô Voronoi. Embedding thật có cấu trúc cụm (văn bản cùng chủ đề) nên cùng `nprobe` cho recall cao hơn hẳn; bài
Intermediate 01 đo IVF này trên vector `bge-m3`.

## Bẫy thường gặp

- Sort ứng viên theo thứ tự probe rồi sort ổn định theo khoảng cách: kết quả đúng tập nhưng sai thứ tự khi bằng nhau.
- Đếm `n_scanned` bằng `k` hoặc bằng số kết quả trả về: che mất chi phí thật, chính là thứ IVF muốn giảm.
- Id của lần `add` thứ hai bắt đầu lại từ 0: hai vector khác nhau cùng id, sai im lặng.
- Train centroid trên một mẫu không đại diện (ví dụ 1 000 điều đầu của corpus, toàn một văn bản): cụm lệch, vài danh sách
  khổng lồ, `nprobe = 1` hoặc chậm như quét hết hoặc sót nhiều. Train trên mẫu ngẫu nhiên.
