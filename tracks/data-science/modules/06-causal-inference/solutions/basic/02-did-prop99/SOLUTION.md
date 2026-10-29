# Lời giải: DiD cho Proposition 99

## Hai cách, một con số

Với một thời điểm can thiệp chung và panel cân (mỗi bang đủ 31 năm), hệ số `treated:post` của hồi
quy two-way fixed effects **bằng đúng** DiD 2×2 trên trung bình. Hồi quy có ích khi cần thêm
covariate, SE, hoặc mở rộng sang event study (thay `post` bằng dummy cho từng năm so với năm gốc).

Cảnh báo: khi các đơn vị được can thiệp ở **thời điểm khác nhau** (staggered adoption) và tác động
thay đổi theo thời gian, two-way fixed effects có thể cho trọng số âm và ra con số vô nghĩa
(Goodman-Bacon 2021). Khi đó dùng Callaway–Sant'Anna hoặc Sun–Abraham.

## Kết quả trên dữ liệu thật

| | 1970–1988 | 1989–2000 | Thay đổi |
| --- | --- | --- | --- |
| California | 116.2 | 60.4 | −55.9 |
| 38 bang khác | 130.6 | 102.1 | −28.5 |
| DiD | | | **−27.35** bao/người/năm |

SE cluster theo bang là 2.85, cho cảm giác rất chắc chắn. **Đừng tin nó**: chỉ có **một** bang được
can thiệp. Cluster-robust SE cần nhiều cluster ở cả hai nhóm; với một cluster treated, nó đánh giá
thấp độ không chắc chắn một cách nghiêm trọng (Conley & Taber 2011). Suy luận đúng hơn là
permutation / placebo: lặp lại phép tính coi từng bang khác là "treated" và xem California có cực
đoan không, chính là cách synthetic control làm (bài Intermediate 02).

## Parallel trends không đứng vững

Trước 1989, California đã giảm nhanh hơn các bang khác 1.23 bao mỗi năm. Khoảng cách
California − trung bình các bang khác đi từ +2.9 (1970) xuống −23.7 (1988) trước khi có luật, rồi
−50.5 năm 2000. DiD trên trung bình coi toàn bộ khoảng cách mở rộng sau 1989 là tác động, trong khi
một phần chỉ là xu hướng sẵn có (California đã có chính sách và văn hoá chống thuốc lá trước đó).

Cách xử lý, từ yếu tới mạnh:

1. Vẽ hai đường theo năm trước khi tính bất cứ thứ gì. Đây là kiểm tra quan trọng nhất.
2. Event study: hệ số từng năm trước can thiệp phải quanh 0.
3. Thêm trend riêng cho nhóm (ngoại suy trend trước sang sau): dễ, nhưng phụ thuộc giả định trend
   tuyến tính tiếp diễn.
4. Chọn nhóm so sánh giống California hơn: synthetic control.

Một pre-trend "không có ý nghĩa thống kê" không chứng minh parallel trends: kiểm định pre-trend
thường thiếu power (Roth 2022). Hãy nhìn độ lớn của pre-trend so với tác động.
