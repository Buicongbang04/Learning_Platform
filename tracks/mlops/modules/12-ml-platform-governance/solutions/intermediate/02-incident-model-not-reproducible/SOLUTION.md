# Lời giải: model production không tái lập được

Mã trong `pipeline.py` cạnh tệp này.

## Nguyên nhân

Dependency **không được ghim**. `requirements.txt` ghi `scalekit>=1.4`, tức một khoảng chứ không phải một bản. Lúc train, `choose` chọn bản mới nhất có trong kho ngày đó (1.4.0); quý sau kho có thêm 1.5.0 và `replay` gọi lại `choose`, ra 1.5.0, bản đổi cách chuẩn hoá (độ lệch chuẩn mẫu và cắt ±2.5σ). Cùng mã, dữ liệu, seed, tham số, khác thư viện nên khác mô hình.

Vì sao audit không thấy: `lockfile_sha256` là hash của `requirements.txt` loose, ổn định giữa hai lần chạy, nên qua được kiểm tra hình dạng (64 ký tự hex). Hash của một tệp không ghim vẫn là "hash của lockfile" về mặt chữ nhưng không chứng minh gì về phiên bản đã chạy. Cảnh báo cho mọi audit hình dạng: nó kiểm cái tag **trông** thế nào, không kiểm nó **nghĩa** là gì.

## Cách sửa

- **Ghi phiên bản đã phân giải lúc train**: hỏi chính tiến trình đã chạy (`scalekit.__version__`) chứ không suy từ spec, ghi thành artifact `requirements.lock` (`scalekit==1.4.0`) và hash **tệp đó** vào `lockfile_sha256`.
- **Dựng lại từ lock, không từ spec**: `replay` đọc `requirements.lock`, dùng đúng bản đó; không có trong kho thì `LookupError` nêu `scalekit==1.4.0` thay vì lặng lẽ dùng bản khác. Run cũ (ghi trước khi sửa) không có `requirements.lock`: `LookupError` nêu đúng tên artifact thiếu, không quay về "bản mới nhất".
- **Kiểm lock với `lockfile_sha256`** trước khi dùng: hash lại tệp đã tải, lệch tag thì `LookupError`. Đó là lúc tag hash thật sự có nghĩa: nó chứng minh tệp đọc lúc dựng lại đúng là tệp đã ghi lúc train. (Test chấm không ép bước này vì cách ghi bản đã chạy là lựa chọn của bạn; nếu bạn ghi lock khác cách, hãy kiểm tương đương.)
- Trong thực tế thay "kho" bằng `uv lock` / `pip freeze` / hash của image đã build (digest, không phải tag). Ghim cả dependency gián tiếp (numpy, scikit-learn) và phiên bản Python, không chỉ gói bạn tự khai báo.

## Điều đáng nhớ

- "Đã log đủ" là một khẳng định cần kiểm bằng **dựng lại thật**, không phải bằng đếm tag. Chạy `replay` định kỳ trên model production (một job hằng tháng, so dự đoán với artifact gốc) bắt lỗi này trước khi cần đến nó lúc 3 giờ sáng.
- Dấu hiệu chẩn đoán: kết quả lặp lại được trong cùng một môi trường nhưng lệch ở môi trường khác thì đầu vào ẩn nằm ngoài những thứ bạn đã log; mọi thứ đã log giống hệt nên đừng đào tiếp vào seed hay dữ liệu.
- Bổ sung audit: thêm kiểm "lockfile có phải bản ghim (`==`) không" thay vì chỉ kiểm độ dài hash.

Lỗi hay gặp: thêm `random_state` mới hay đóng băng dữ liệu (không phải nguyên nhân ở đây, mất thời gian); ghim bằng cách sửa `REQUIREMENTS` thành `==1.4.0` cứng trong mã (tái lập được model này nhưng làm mọi model sau dùng bản cũ mãi); chỉ ghi phiên bản vào tag mà `replay` vẫn chọn "mới nhất".
