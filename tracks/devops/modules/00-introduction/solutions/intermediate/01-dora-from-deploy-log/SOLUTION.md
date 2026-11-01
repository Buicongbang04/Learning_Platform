# Lời giải: DORA metrics từ log deploy, commit và incident

Code đầy đủ ở `dora.py` cạnh tệp này.

## Kết quả tuần 1–7/10

| Metric | Giá trị | Mức DORA 2024 |
| --- | --- | --- |
| Deployment frequency | 9 deploy / 7 ngày, khoảng 1,3 deploy/ngày | elite (on demand, nhiều lần mỗi ngày) hoặc high: ranh giới mờ |
| Change failure rate | 2/9, khoảng 22% | gần cụm high (20%) |
| Change lead time (median) | 3 giờ | elite (dưới 1 ngày) |
| Failed deployment recovery time (median) | 80 phút | high (dưới 1 ngày; elite là dưới 1 giờ) |

Một tuần, 9 deploy, 2 failed change: change failure rate thay đổi 11 điểm phần trăm chỉ vì một deploy. Không ai nên
kết luận mức của team từ một tuần; DORA khuyên nhìn xu hướng nhiều tuần, và cỡ mẫu nhỏ thì báo kèm số tuyệt đối.

## Từng quy tắc và lý do

1. **Chỉ đếm production, `success`, không phải rollback.** Staging không phải giá trị tới người dùng. Deploy
   `failed` (pipeline dừng, production không đổi) không phải một thay đổi trên production; nó là tín hiệu tốt của
   pipeline, không phải failed change. Rollback là hành động khôi phục, đếm nó vào deployment frequency làm team có
   nhiều sự cố trông như deploy nhiều hơn.
2. **Cửa sổ so theo thời điểm.** `d00` ghi `2026-09-30T18:00:00Z`, tức 01:00 ngày 1/10 giờ Việt Nam: thuộc tuần
   này. `d12` ghi ngày 7/10 nhưng là 00:30 ngày 8/10 giờ Việt Nam: không thuộc. Cửa sổ của team là theo giờ địa
   phương, nên mọi so sánh phải trên thời điểm có múi giờ. `parse_ts` từ chối timestamp không múi giờ vì đoán múi
   giờ là cách chắc chắn nhất để có số sai không ai phát hiện.
3. **Failed change = bị rollback hoặc gây incident, đếm theo deploy.** `d05` vừa bị rollback (`d06`) vừa có hai
   incident (`i01`, `i04`): vẫn là một failed change. `i03` (Redis hết đĩa) không do thay đổi gây ra, nên không vào
   change failure rate; nó vẫn ảnh hưởng reliability. Hotfix `d09` là một deploy bình thường được đếm; DORA 2024 gọi
   tỉ lệ deploy kiểu này là **rework rate**.
4. **Lead time kết thúc ở deploy sớm nhất không bị rollback.** `c04` có mặt ở `d04` (pipeline lỗi), `d05` (bị
   rollback) và `d07`: chỉ từ `d07` commit mới thật sự chạy trên production, nên lead time là 47 giờ chứ không phải
   27 giờ. Ngược lại, `d08` gây incident nhưng được sửa bằng fix forward (`d09`), `c07` vẫn chạy trên production nên
   lead time của nó kết thúc ở `d08`. Lấy deploy sớm nhất chứa SHA bất kể kết quả sẽ làm lead time trông đẹp hơn
   đúng lúc team đang gặp sự cố.
5. **SHA không khớp thì bỏ qua, không làm sập phép tính.** `d10` mang `deadbee`, SHA từ một nhánh đã force-push hoặc
   deploy chỉ đổi cấu hình. Deploy vẫn được đếm vào frequency; chỉ lead time thiếu một điểm. Trên hệ thống thật,
   đếm tỉ lệ SHA không khớp và báo cùng metric: tỉ lệ cao là dấu hiệu pipeline deploy thứ không đi qua Git.
6. **Khôi phục = sự kiện khôi phục cuối cùng, tính từ lúc deploy xong.** Với `d05`: rollback xong 14:25, `i04` đóng
   14:20, `i01` đóng 14:30, nên 30 phút. Với `d08`: 23:10 tới 01:20 hôm sau, 2 giờ 10 phút, qua nửa đêm. Tính từ
   lúc deploy chứ không từ lúc incident mở, vì thời gian chưa phát hiện cũng là thời gian người dùng chịu lỗi. Còn
   incident chưa đóng thì chưa có thời gian khôi phục, nhưng deploy vẫn là failed change.
7. **Cửa sổ rỗng trả `None`, không trả `0`.** Change failure rate `0` nghĩa là "deploy mà không hỏng lần nào", khác
   hẳn "không deploy". Dashboard hiện `0%` cho tuần nghỉ Tết là cách nhanh nhất để mất niềm tin vào số liệu.

## Lỗi hay gặp

- Tính change failure rate bằng `số incident / số deploy`: incident trùng và incident không do thay đổi làm số phồng.
- Dùng mean cho lead time: một commit nằm chờ 3 tuần kéo mean lên hàng chục giờ; DORA dùng median (hoặc phân phối).
- Lấy lead time từ lúc mở PR hay lúc merge: DORA tính từ commit. Muốn biết thời gian mất ở đâu thì tách stage,
  như bài intermediate 02.
- So team với nhau bằng các con số này: service khác nhau, rủi ro khác nhau. DORA metrics dùng để một team so với
  chính nó theo thời gian.

## Mở rộng

- Thêm `rework_rate`: tỉ lệ deploy không theo kế hoạch do incident gây ra (cần một trường đánh dấu hotfix).
- Báo phân phối (p50, p85) thay vì chỉ median, và số mẫu kèm theo.
- Tính theo từng service rồi mới gộp: `olist-shop-worker` và `olist-shop-api` có nhịp deploy khác nhau.
