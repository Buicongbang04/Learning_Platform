# Lời giải: delta method cho ratio metric

## Cách làm

Metric $$R = \bar Y / \bar X$$ với $$Y$$ là tử số, $$X$$ là mẫu số tính **theo user**. Khai triển Taylor
bậc một của $$g(\bar Y, \bar X) = \bar Y / \bar X$$ quanh giá trị kỳ vọng cho:

$$
\mathrm{var}(R) \approx \frac{1}{n\,\mu_X^2}\left(\sigma_Y^2 - 2R\,\sigma_{XY} + R^2\sigma_X^2\right)
$$

`ratio_delta` dùng đúng công thức này với `np.cov` (ddof=1). Không cần vòng lặp, chạy trong vài
mili giây với hàng triệu user, nên các experimentation platform dùng nó thay cho bootstrap.

`ratio_diff_ci` cộng variance hai nhánh (độc lập vì random), rồi làm z-test. `relative_lift_ci`
áp delta method lần thứ hai cho $$R_B / R_A$$:

$$
\mathrm{var}\!\left(\frac{R_B}{R_A}\right) \approx \frac{\mathrm{var}(R_B)}{R_A^2} + \frac{R_B^2\,\mathrm{var}(R_A)}{R_A^4}
$$

## Vì sao cách ngây thơ sai

`naive_binomial_se` coi 10 lượt xem của một user là 10 phép thử độc lập. Nhưng user thích click thì
click nhiều ở mọi lượt, user không thích thì không click lần nào: các lượt xem trong cùng user
**tương quan dương**. Thông tin thật ít hơn nhiều so với số lượt xem, nên SE ngây thơ quá nhỏ (test
thấy khoảng 0.58 lần SE đúng) và A/A báo "có ý nghĩa" khoảng 25% số lần thay vì 5%.

Tỉ số $$\mathrm{var}_{\text{đúng}} / \mathrm{var}_{\text{ngây thơ}}$$ gọi là **design effect**. Trên
Olist thật (bài Intermediate 02), với metric giá trung bình mỗi sản phẩm, design effect chỉ khoảng
1.17 vì 97% khách chỉ có một đơn; với dữ liệu mô phỏng trong test (mỗi user khoảng 10 lượt xem,
CTR khác nhau nhiều giữa các user) nó khoảng 3. Càng nhiều quan sát trên mỗi đơn vị random và
đơn vị càng khác nhau, design effect càng lớn.

## Kiểm bằng bootstrap

Bootstrap đúng cách phải resample **user** (cả cặp `num`, `den` đi cùng nhau), không resample lượt
xem. Test làm đúng như vậy và delta method khớp trong vài phần trăm. Khi metric phức tạp tới mức
không viết được đạo hàm (percentile của tỉ số, tỉ số của tỉ số), bootstrap theo user là phương án
dự phòng.

## Bẫy thường gặp

- Lấy trung bình các tỉ lệ của từng user (`mean(num / den)`): đó là một metric **khác** (mỗi user
  có trọng số bằng nhau) và chia cho 0 khi user không có lượt xem. Chọn metric nào là quyết định sản
  phẩm; nhưng phải ghi rõ, và SE phải khớp metric đã chọn.
- Áp delta method khi đơn vị random là pageview: khi đó các pageview thật sự độc lập theo thiết kế,
  công thức binomial là đúng. Delta method cần thiết khi **đơn vị phân tích nhỏ hơn đơn vị random**.
- Mẫu số có thể bằng 0 ở cả nhánh (metric hiếm): delta method xấp xỉ bậc một kém khi $$\bar X$$ nhỏ;
  kiểm lại bằng bootstrap.
