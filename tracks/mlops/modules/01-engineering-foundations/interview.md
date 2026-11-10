# Câu hỏi phỏng vấn: nền tảng kỹ thuật cho ML code

## Vì sao dùng `src/` layout cho một package ML thay vì để package cạnh `tests/`?

Với layout phẳng, `pytest` chạy ở gốc repo import được package mà chưa cần cài, nên `pyproject.toml` thiếu dependency hoặc thiếu module không bao giờ lộ ra. Với `src/`, import chỉ chạy khi package đã cài (hoặc có `PYTHONPATH=src`), nên test thấy đúng thứ người dùng và CI thấy. Đánh đổi: phải cài editable (`uv sync`) trước khi test, đổi lại là tránh lỗi "chạy trên máy tôi".

## `pyproject.toml` và `uv.lock` khác nhau thế nào, cái nào commit?

`pyproject.toml` khai báo khoảng phiên bản chấp nhận được; `uv.lock` ghim đúng phiên bản và hash của toàn bộ cây dependency. Ứng dụng (job train, service) commit cả hai và CI dùng `uv sync --frozen` để lỗi khi hai tệp lệch nhau. Thư viện dùng chung thường chỉ cần khoảng rộng để không ép người dùng. Không có lockfile thì sáu tháng sau cùng code cho kết quả khác vì pandas hay scikit-learn đã lên bản mới.

## Notebook của đồng nghiệp chạy được trên máy họ nhưng không chạy nổi trên máy bạn. Bạn làm gì, theo thứ tự nào?

Chạy lại từ đầu "Restart and Run All" để thấy trạng thái ẩn; tìm đường dẫn cứng, biến toàn cục, phụ thuộc không khai báo. Chép số hiện tại (MAE, số dòng sau lọc) làm tham chiếu. Chuyển từng cell thành hàm thuần có tham số, viết test đặc trưng khớp số tham chiếu trước khi đổi gì, rồi đóng gói và thêm CLI. Chốt là số tham chiếu không đổi sau refactor.

## Bạn tách cấu hình khỏi code như thế nào, và thứ gì không được vào cấu hình?

Ba lớp: mặc định trong code, YAML theo môi trường, biến môi trường thắng cuối cùng, nạp qua một hàm kiểm kiểu. Khoá lạ là lỗi, đường dẫn tương đối trong YAML tính từ thư mục YAML. Thứ đổi giữa các môi trường (đường dẫn, URI) vào config; thứ định nghĩa hành vi (danh sách feature, luật làm sạch) ở code để được review. Bí mật không vào YAML trong Git mà lấy từ env hoặc secret manager.

## Vì sao log JSON thay vì dòng văn bản, và bạn đưa gì vào mỗi dòng?

Máy đọc được: lọc theo `run_id`, đếm lỗi, vẽ MAE theo thời gian mà không cần regex dễ vỡ. Mỗi dòng có thời gian UTC, mức, logger, thông điệp, `run_id` và số liệu có nghĩa. Không log bí mật hay dữ liệu cá nhân; che theo tên trường chỉ là lưới an toàn, không bắt được bí mật nằm trong chuỗi thông điệp.

## Sự cố: hai lần train cùng seed ra hai MAE khác nhau. Bạn điều tra thế nào?

Liệt kê nguồn ngẫu nhiên và nguồn thứ tự không xác định. Thử rẻ trước: chạy hai lần trong một tiến trình sau khi đổi trạng thái `random` và `np.random` toàn cục giữa hai lần; nếu khác thì có nguồn không nằm dưới `seed`. Giả lập môi trường khác (đổi thứ tự `os.listdir`, số luồng). Cuối cùng bisect bằng hash dữ liệu sau `load`, `split`, `fit`. Nguyên nhân hay gặp: `random.shuffle` không bị `np.random.seed` ảnh hưởng, `os.listdir` thứ tự tuỳ hệ tệp, model không có `random_state`. Sửa bằng bộ sinh cục bộ và `sorted` danh sách tệp; thư viện không được đổi random toàn cục.

## Sự cố: một tệp parquet 400 MB đã bị commit và push lên `main`. Xử lý ra sao?

Trước hết xác nhận nó có chứa bí mật hay dữ liệu nhạy cảm không; nếu có thì coi là lộ và xoay khoá. Xoá bằng `git rm` không làm `.git` nhẹ đi vì lịch sử còn bản đó. Muốn lấy lại dung lượng phải viết lại lịch sử (`git filter-repo`), cần thống nhất với cả đội vì mọi clone và nhánh phải được cập nhật. Sau đó thêm `.gitignore`, pre-commit `check-added-large-files`, và chuyển dữ liệu sang DVC. Quan trọng hơn cả là chặn lần sau.

## Test cho code ML khác test phần mềm thường ở đâu?

Thêm ba lớp: test dữ liệu (luật dữ liệu có đếm dòng bị loại), test có tính ngẫu nhiên (có seed, bằng nhau trong dung sai, thứ tự tệp), và test hành vi model (invariance, directional). Test độ chính xác nên dùng ngưỡng có biên thay vì bằng đúng một con số, và lớp tốn kém (train trên dữ liệu thật) chuyển ra khỏi PR sang chạy hằng đêm.

## Giải thích test invariance và directional bằng ví dụ ETA. Vì sao directional đo trên trung bình?

Invariance: đảo thứ tự cột của JSON không được đổi dự đoán; nó bắt model chọn cột theo vị trí. Directional: tăng `trip_distance` thì ETA không giảm. Model cây có vùng phẳng và dao động nhỏ nên đòi mọi điểm đơn điệu sẽ làm test đỏ ngẫu nhiên; đo trung bình thay đổi cộng tỉ lệ ngược chiều với ngưỡng cho từng số. Muốn đảm bảo cứng thì ràng buộc lúc train (`monotonic_cst`) và dùng test làm lưới kiểm.

## MAE giữa hai lần chạy chênh 0,04 phút. Cải tiến có thật không?

Không biết nếu chưa đo nhiễu. Cùng code, đổi seed chia dữ liệu đã cho chênh cỡ đó, nên cải tiến nhỏ hơn mức nhiễu không phân biệt được với may rủi. Cách làm: lặp nhiều seed hoặc dùng cross-validation, so phân phối chứ không so một số, hoặc đánh giá trên tập test cố định và dùng khoảng tin cậy (bootstrap).

## Vì sao Makefile cho một dự án Python, khi đã có `uv run`?

`uv run` chạy một lệnh; Makefile đặt tên cho tập lệnh của dự án (`make test`, `make train`) để người mới và CI dùng cùng một lối vào. Nó tài liệu hoá cách chạy bằng chính mã chạy được, cho phép ghi đè biến (`make train SEED=7`) và `make -n` để xem trước. Đánh đổi: phụ thuộc `make` (có ở Linux và macOS), thay thế bằng `just` hoặc `taskfile` nếu cần chạy trên Windows.

## Git flow nào hợp với đội ML nhỏ, và thí nghiệm dài ngày đặt ở đâu?

Trunk-based hoặc nhánh ngắn: PR nhỏ, CI xanh mới merge, nhánh sống dưới vài ngày. Thí nghiệm dài ngày không nằm trong nhánh dài mà được ghi bằng tracking (tham số, commit hash, phiên bản dữ liệu); nhánh chỉ chứa code đáng merge. Model production phải truy được về một commit và một phiên bản dữ liệu.

## Vì sao chọn pre-commit, và nó có thay được CI không?

pre-commit chạy kiểm rẻ (định dạng, tệp lớn, YAML) trước khi commit nên phản hồi tức thì và ngăn rác vào lịch sử. Nó chạy trên máy từng người nên ai cũng bỏ qua được bằng `--no-verify`; CI chạy lại cùng cấu hình mới là chốt thật. Ghim `rev` bằng tag để kết quả không đổi theo ngày.

## Khi nào chọn Go thay vì Python quanh một hệ ML?

Khi cần binary tĩnh nhỏ, khởi động nhanh, nhiều kết nối đồng thời, ví dụ gateway trước model, sidecar, CLI nội bộ; không cần hệ sinh thái ML. Model và pipeline train vẫn ở Python; service Go gọi model qua HTTP hoặc ONNX. Đánh đổi là hai ngôn ngữ trong một đội: chỉ chọn khi lợi ích về tải hay vận hành rõ ràng.

## Thiết kế: bạn nhận một repo ML không test, không lock, model đang phục vụ production. Kế hoạch tuần đầu?

Ngày 1: xử lý rủi ro không đợi được (bí mật, quyền truy cập), chụp hiện trạng (hash model đang chạy, commit nào, dữ liệu nào). Tiếp: test đặc trưng khớp hành vi hiện tại trước khi sửa, đóng gói và khoá phiên bản, đưa config ra ngoài, `build_features` dùng chung cho train và serve, thêm test hành vi và CI. Cố ý không làm: đổi thuật toán hay dọn lịch sử Git khi chưa có thoả thuận. Mỗi bước có cách kiểm cụ thể.

## Bạn xây CI cho repo ML dưới 10 phút cho PR. Lớp nào ở đâu?

PR: unit, data test trên mẫu nhỏ, test hành vi với model nhỏ trên dữ liệu tổng hợp, contract API. Hằng đêm: train trên mẫu dữ liệu thật với seed cố định, so MAE với ngưỡng và model đang chạy. Trước release: build image và smoke test. Ngoài CI hoàn toàn (nói rõ): concept drift, tải thật, nhãn về muộn; chúng thuộc giám sát. Flaky: tối đa một retry, cách ly có hạn, có người chịu trách nhiệm.
