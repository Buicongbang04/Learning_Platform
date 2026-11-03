# Lời giải: review repo `eta-service-v0`

Không có đáp án duy nhất. Điều đáng chấm là thứ tự ưu tiên: **an toàn và khả năng quay lui trước, tái lập sau, đẹp code cuối cùng**.

## Hướng làm

1. Đọc cây và số liệu `git` trước khi đọc code. 1,9 GiB trong `.git` và không có `.gitignore` nói ngay repo này không có ranh giới giữa code và artifact.
2. Chia phát hiện theo rủi ro: lộ bí mật, không quay lui được, không tái lập, khó bảo trì. Mỗi mục có tệp, triệu chứng, hậu quả.
3. Lập kế hoạch từ bước rẻ và chặn nhiều nhất: đổi mật khẩu, chặn commit thêm artifact, rồi mới tới đóng gói và test.

## Phát hiện mẫu

- [P0] `config.py`: `DB_URL` chứa mật khẩu `admin` của DB production, nằm trong lịch sử git từ lâu. Ai có quyền đọc repo đều đăng nhập được; phải đổi mật khẩu ngay, xoá khỏi code, đọc từ biến môi trường. Dọn lịch sử chỉ là phụ vì mật khẩu đã coi là lộ.
- [P0] `models/model_v7.pkl`, `models/model_v7_final.pkl`: hai model không biết cái nào đang chạy, không gắn với commit hay dữ liệu. README bảo copy `model_v7_final.pkl` sang server bằng tay: không có cách quay lui hay chứng minh server chạy bản nào.
- [P1] `data/trips_2019_01.parquet`, `data/trips_2019_01_clean_v2.parquet` nằm trong git: `.git` 1,9 GiB, clone chậm, không xoá được khỏi lịch sử nếu không viết lại lịch sử. Thiếu `.gitignore`.
- [P1] `train.py`: `df.sample(frac=0.3)` và `train_test_split` không seed, nên hai lần train ra MAE khác nhau; không ghi lại tham số, dữ liệu, phiên bản; `sys.path.append("..")` chạy sai khi đổi thư mục.
- [P1] `config.py`: `DATA_PATH = "/home/hieu/Downloads/..."` và `MODEL_PATH = "/srv/eta/..."` là đường dẫn máy cá nhân và server; code chỉ chạy trên máy của một người.
- [P1] `app.py`: `request.args.to_dict()` đưa chuỗi thẳng vào `DataFrame` không kiểm schema, không giá trị mặc định; cột sai thứ tự hay kiểu sai cho dự đoán sai âm thầm thay vì lỗi 4xx.
- [P1] `final_FINAL_v3.ipynb`: cell 48 train với tham số khác `train.py`, cell 31 sửa dữ liệu tại chỗ; không biết model production đến từ đâu. Output 52 MB làm diff vô nghĩa.
- [P2] `requirements.txt`: không ghim phiên bản; README ghim Python 3.8 "đừng dùng bản khác" nghĩa là đã từng vỡ vì phiên bản mà không ai ghi nguyên nhân.
- [P2] `utils.py`: 1 240 dòng, `from utils import *`, `build_features` lặp ba kiểu; training và serving có thể tính feature khác nhau.
- [P2] `tests/`: chỉ có `__init__.py`; không có chốt an toàn nào khi refactor.

## Kế hoạch mẫu

1. Đổi mật khẩu DB, chuyển `DB_URL` sang biến môi trường, thêm `.gitignore` và `pre-commit` chặn tệp lớn. Kiểm: mật khẩu cũ bị từ chối; `git add -A` sau khi thêm `data/` giả không stage gì.
2. Chụp trạng thái hiện tại: lưu hash của model đang chạy trên server, đánh tag git cho commit đang chạy, ghi lại dữ liệu vào đâu. Kiểm: trả lời được "server đang chạy model nào, train từ commit và dữ liệu nào" bằng một lệnh.
3. Viết test đặc trưng (characterization test) cho `build_features` và `/eta` dựa trên hành vi hiện tại, trước khi sửa. Kiểm: test pass trên code cũ.
4. Đóng gói `src/eta_service/` với `pyproject.toml`, lockfile `uv`, config từ env; chuyển `train.py` thành hàm `train(config)` có seed. Kiểm: hai lần train cùng seed ra cùng MAE; test ở bước 3 vẫn pass.
5. Dùng chung một `build_features` cho training và serving; thêm test hành vi (đổi thứ tự cột, hướng khoảng cách). Kiểm: test bắt được lỗi khi cố tình đảo cột.
6. Dựng Makefile và CI chạy `make lint test`. Kiểm: PR đỏ khi phá test.
7. Chuyển artifact sang registry (module 04), dữ liệu sang DVC (module 03); xoá `data/` và `models/` khỏi lịch sử bằng công cụ viết lại lịch sử chỉ khi cả đội đã nhất trí. Kiểm: `dvc status` sạch, model production tải được theo alias từ registry, `.git` nhỏ hơn 50 MiB sau khi clone mới.

## Thứ tự và lý do (mẫu)

Bước 1 làm ngay trong ngày vì rủi ro không đợi được và rất rẻ. Bước 2 và 3 phải làm trước mọi thay đổi code: không có "chụp lại hiện trạng" và test đặc trưng thì refactor chỉ là đổi hành vi một cách không kiểm soát được. Bước 4 mở khoá 5 và 6 vì không đóng gói thì không có gì để test và để CI chạy. Bước 7 để cuối vì cần module khác và đồng thuận cả đội, mà bước 1-6 đã chặn việc repo xấu thêm.

## Không làm (mẫu)

- Không viết lại thuật toán hay đổi XGBoost sang model khác: chưa có tái lập và test thì không so sánh được tốt hơn hay tệ hơn.
- Không dọn lịch sử git ngay: viết lại lịch sử phá mọi nhánh và clone của đồng nghiệp; chỉ làm sau khi có thoả thuận và sao lưu, còn mật khẩu thì đổi ngay vì xoá khỏi lịch sử không làm nó hết lộ.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Bí mật là P0 và có hành động đổi mật khẩu, không chỉ "xoá dòng" | 2 |
| Nhận ra model đang chạy không truy được nguồn (quay lui, tái lập) | 2 |
| Kế hoạch có thứ tự đúng: test đặc trưng trước refactor; chụp hiện trạng trước thay đổi | 2 |
| Mỗi bước có cách kiểm cụ thể, chạy được | 2 |
| "Không làm" có lý do thực tế, không phải liệt kê vu vơ | 1 |
| Phát hiện cụ thể theo tệp, không chung chung kiểu "code xấu" | 1 |

Lỗi hay gặp: đưa "viết lại bằng framework mới" lên đầu danh sách; bỏ qua training-serving skew vì tập trung vào cấu trúc thư mục; xoá bí mật khỏi code mà quên đổi nó.
