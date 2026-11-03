# Câu hỏi phỏng vấn: data versioning và chất lượng dữ liệu

## Vì sao không để dữ liệu trong Git, hay dùng Git LFS cho mọi thứ?

Git nén và lưu lịch sử mọi phiên bản trong `.git`, nên repo phình theo từng lần đổi dữ liệu và `clone` chậm. Git LFS giải bài toán kích thước nhưng chỉ lưu tệp;
nó không biết pipeline, không băm theo stage, không có `dvc repro` để tái lập. DVC giữ trong Git chỉ một con trỏ (md5, size) còn dữ liệu nằm ở cache và remote S3. Đánh đổi: thêm bước `dvc push/pull` vào quy trình.

## `dvc.lock` là gì và vì sao phải commit nó?

`dvc.yaml` khai báo cách chạy; `dvc.lock` ghi kết quả thật: md5 của từng dep và out ở lần chạy cuối. Commit cả hai cùng code thì checkout commit đó dựng lại đúng dữ liệu. Xoá `dvc.lock` thì mọi stage coi như chưa chạy.
Nó là hợp đồng tái lập: PR review đọc diff `dvc.lock` để thấy dữ liệu đã đổi.

## `dvc repro` quyết định chạy hay bỏ qua stage dựa trên gì?

Hash của `cmd`, `deps` và các khoá `params` được khai trong `dvc.yaml`, so với `dvc.lock`. Khớp thì in "didn't change, skipping"; lệch thì chạy lại stage đó và mọi stage phụ thuộc vào đầu ra của nó.

## Sự cố: pipeline huấn luyện xanh nhưng metric offline tụt 8% sau một đêm. Bạn điều tra từ phía dữ liệu thế nào?

Đi từ rộng tới hẹp, mỗi bước loại một giả thuyết. `git log -p dvc.lock` và `dvc diff <rev cũ>` cho biết dữ liệu có đổi giữa hai lần train hay không, `dvc params diff` cho biết tham số nào đổi,
`dvc status` và `dvc dag` cho biết pipeline có đang đúng như khai báo. Nếu dữ liệu đổi: `dvc diff` chỉ ra tệp nào, rồi chạy bộ luật kiểm chất lượng trên hai phiên bản để thấy tỉ lệ vi phạm nào nhảy. Nếu dữ liệu không đổi: so run MLflow
của hai lần train (code, tham số, seed, môi trường). Giữ nguyên tắc chỉ đổi một yếu tố mỗi lần thử, và cuối cùng thêm kiểm tự động để lần sau máy báo thay con người.

## Sự cố: `dvc pull` báo missing cache dù Git đủ commit. Nguyên nhân thường gặp?

Quên `dvc push` trước khi push Git, hoặc remote bị dọn (`dvc gc --cloud`, lifecycle S3) quá tay. Xác định bằng `dvc status -c` (so cache với remote). Phòng ngừa: hook/CI bắt buộc `dvc push` trước merge,
chính sách retention giữ mọi object được tham chiếu bởi nhánh chính và tag release, job đêm kiểm `dvc status -c` trên các tag.

## Vì sao khoá S3 không được nằm trong `.dvc/config`?

Tệp này được commit, khoá sẽ vào lịch sử Git mãi mãi. Dùng biến môi trường `AWS_*`, `~/.aws/credentials`, role của CI, hoặc `dvc remote modify --local` (ghi vào `.dvc/config.local`, đã bị `.gitignore`). Nếu lỡ commit: xoay khoá ngay, không chỉ xoá tệp.

## Vì sao chọn DVC mà không chọn lakeFS hoặc Delta Lake?

Vì vấn đề. Đội ML 3 GB một tháng cần mỗi lần train gắn với một phiên bản dữ liệu: DVC + remote S3, gần như không phải vận hành. lakeFS cần server và KV store, đáng khi nhiều đội cùng ghi vào một lake lớn và cần branch/commit nguyên tử.
Delta đáng khi bảng được ghi liên tục và cần ACID, time travel theo thời điểm. Chọn công cụ nặng cho vấn đề nhỏ là chi phí vận hành vô ích.

## Pandera và Great Expectations, bạn chọn gì và khi nào?

Pandera khi luật nằm trong code Python của pipeline và dữ liệu là DataFrame: schema như code, test được trong unit test, ít chi phí. Great Expectations khi cần Data Docs cho người không viết code, chạy trên SQL/Spark,
hoặc cần quản lý bộ expectation tập trung cho nhiều đội. Tốc độ không phải lý do chọn; vấn đề là ai đọc kết quả và dữ liệu sống ở đâu.

## Khi validation thất bại, chặn hay cách ly hay cảnh báo?

Theo loại lỗi. Lỗi hợp đồng (thiếu cột, đổi đơn vị, ngày ngoài tháng ở quy mô lớn) thì chặn cả lô, vì dữ liệu sau đó không đáng tin. Dòng lẻ bẩn (distance 0, thời lượng âm) thì cách ly (quarantine) kèm bộ đếm và ngưỡng: vượt ngưỡng thì nâng thành chặn.
Mã hợp lệ nhưng đáng ngờ (zone Unknown) thì cảnh báo và theo dõi tỉ lệ theo thời gian.

## Data contract khác schema validation ở đâu?

Validation là cơ chế kiểm tra; contract là thoả thuận có chủ sở hữu: schema kèm đơn vị và ngữ nghĩa, SLA, quy tắc thay đổi (breaking/non-breaking, báo trước, chạy song song hai phiên bản), người trực. Schema không bắt được đổi dặm sang km vì kiểu vẫn là float.
Phải kiểm ở cả hai phía: CI của nhà cung cấp trước khi phát hành, và cửa vào của người dùng.

## Một model production đang cho kết quả lạ. Làm sao chỉ ra nó học từ dữ liệu nào?

Từ model version lấy run MLflow, đọc `git_commit` và hash dữ liệu (md5 trong `dvc.lock`) đã ghi tự động. Checkout commit, `dvc pull`, `dvc repro --dry` phải báo up to date. Nếu thiếu tag này thì lineage bị đứt: ghi tag
trong code huấn luyện, không dựa vào người nhớ điền. `dvc diff` giữa hai commit cho thấy dữ liệu khác nhau ở đâu.

## Thiết kế hệ thống: dịch vụ ETA taxi huấn luyện lại hằng tuần từ dữ liệu của đội khác. Bạn đặt data versioning và quality ở đâu?

Cửa vào: đội data phát hành bảng theo contract có version và kiểm ở CI của họ. Cửa vào pipeline ML: Pandera ghim phiên bản contract, chặn lô vi phạm, cách ly dòng lỗi, đẩy metric tỉ lệ lỗi.
Pipeline `dvc.yaml` (prepare, split, train) với `dvc.lock` commit cùng code, remote S3 có retention. Mỗi run MLflow ghi `git_commit` và hash dữ liệu. Cổng promotion so với model đang chạy. Sự cố thì rollback model bằng alias, rollback dữ liệu bằng commit cũ.

## Làm sao kiểm dữ liệu bị drift so với kiểm dữ liệu bị lỗi?

Lỗi là vi phạm luật xác định (ngày ngoài tháng, thời lượng âm): kiểm được bằng schema. Drift là phân phối đổi nhưng vẫn hợp lệ (số chuyến sụt giữa tháng 3/2020 vì COVID): cần so sánh thống kê với một tham chiếu (PSI, KS) và ngưỡng.
Schema không bắt được drift, và drift monitor không thay được schema.

## Retention và garbage collection của dữ liệu version hoá nên thiết kế thế nào?

Giữ mọi object được tham chiếu bởi nhánh chính và tag release (model đang chạy, model cần tái lập theo quy định); `dvc gc` chỉ chạy với danh sách rev rõ ràng; lifecycle S3 chỉ dọn tiền tố tạm. Với Delta, `VACUUM` retention phải
không nhỏ hơn cửa sổ điều tra đã cam kết. Giám sát bằng job kiểm các tag release còn dựng lại được, vì chính sách tốt mà không kiểm vẫn hỏng âm thầm.
