# Lời giải: run tái lập được

Mã nằm trong `repro.py` cạnh tệp này.

## Ba thứ cần ghim

Tái lập có ba chân: **code** (git commit, module 04), **dữ liệu** (fingerprint) và **ngẫu nhiên + môi trường** (seed, phiên bản
thư viện). Bài này lo hai chân sau và thêm chân thứ tư là **bằng chứng**: hash của artifact. Không có hash artifact thì "tái
lập" chỉ là lời hứa; có hash thì `verify` biến nó thành phép so sánh.

## Các quyết định

- **Seed tường minh qua `random_state`, không `np.random.seed`.** Trạng thái toàn cục bị mọi thư viện dùng chung; test cố tình đổi
  nó để bắt lời giải dựa vào nó.
- **`n_jobs=1`.** Với random forest, mỗi cây có seed riêng nên song song vẫn tất định; nhưng nhiều thuật toán (cộng dồn số
  thực, GPU) thì không. Quy tắc an toàn: khi cần tái lập bit-từng-bit, giảm song song trước, tối ưu tốc độ sau và đo lại hash.
- **Fingerprint theo nội dung, kể cả thứ tự dòng.** Hash theo đường dẫn hay mtime nói dối: `touch` đổi mtime mà dữ liệu không đổi,
  `cp` đổi đường dẫn. Thứ tự dòng đổi có thể làm đổi kết quả train (shuffle theo vị trí), nên coi là dữ liệu khác. Với dữ liệu
  lớn dùng DVC (module 03) để băm theo khối; ý tưởng giữ nguyên.
- **Manifest ghi tham số đã gộp mặc định.** Nếu chỉ ghi phần ghi đè, đổi `DEFAULT_PARAMS` trong code sau này làm manifest cũ
  mất nghĩa. Ghi giá trị hiệu lực.
- **`verify` trả `False` thay vì ném lỗi** khi tệp mất: hàm này sống trong cổng kiểm tra, nơi câu trả lời cần là "không đạt".

## Lỗi hay gặp

- Hash `model.pkl` rồi kết luận "tái lập được" trong khi chỉ chạy một lần: phải train hai lần và so.
- Quên rằng tên cột, kiểu dữ liệu và thứ tự cột cũng là một phần của dữ liệu.
- Ghi phiên bản `scikit-learn` nhưng không ghi `numpy`/`python`: ba thứ này cùng ảnh hưởng tới byte của pickle.
- Coi hash khác là lỗi ngay. Khác phiên bản thư viện có thể cho hash khác mà dự đoán như nhau; manifest giúp bạn biết **vì sao**
  khác thay vì đoán.
