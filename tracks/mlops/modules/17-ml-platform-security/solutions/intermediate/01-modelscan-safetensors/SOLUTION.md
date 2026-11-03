# Lời giải: pickle, safetensors và modelscan

`model_io.py` cạnh tệp này là bản tham khảo.

**Vì sao pickle nguy hiểm.** Pickle không phải định dạng dữ liệu mà là một chương trình nhỏ cho máy ảo của module `pickle`. Opcode
`GLOBAL`/`STACK_GLOBAL` nạp một hàm bất kỳ theo tên (`builtins.exec`, `os.system`), `REDUCE` gọi nó với tham số trong tệp. `__reduce__` cho
phép bất kỳ đối tượng nào tự mô tả "để dựng lại tôi, hãy gọi hàm này". `joblib.load`, `torch.load(weights_only=False)` và nhiều loader
khác đều đi qua pickle. Ca `test_loading_a_pickle_runs_code` cho thấy: chỉ `pickle.loads` là đủ để code chạy, không cần gọi gì trên đối
tượng.

**safetensors an toàn vì thiết kế.** Tệp chỉ gồm một header JSON (tên, dtype, shape, offset) và một khối byte; loader không có cách nào gọi
hàm. Model tuyến tính chỉ cần hai tensor, nên lưu được trọn vẹn; với model cây (LightGBM, XGBoost) dùng định dạng gốc của thư viện (văn
bản hoặc JSON), với mạng nơ-ron dùng safetensors hoặc ONNX.

**Ba ca cho thấy giới hạn của máy quét:**

- Payload gọi `pathlib.Path.write_text`: modelscan 0.8.8 dò theo danh sách các module/hàm nguy hiểm (`builtins.exec`, `os`, `subprocess`,
  `socket`...); `pathlib` không có trong danh sách, nên báo sạch. Mọi máy quét dạng denylist đều có khe hở như vậy (`numpy.load`,
  `torch` internals, các hàm ghi tệp khác...).
- Pickle đặt tên `model.safetensors`: modelscan chọn scanner theo **đuôi tệp**, coi đây là safetensors (không có gì để quét), trả 3.
- Pickle đặt đuôi `.bin`: không scanner nào nhận đuôi này, tệp bị bỏ qua.

Vì vậy cổng có hai lớp độc lập: **allowlist theo nội dung** (nhận diện bằng byte, không bằng đuôi; chỉ nhận định dạng không chứa code) là
lớp chính, **máy quét** là lớp phụ cho đường chuyển tiếp còn nhận pickle. Khi nhận pickle, đòi bằng chứng là máy quét **đã đọc** tệp
(`scanned_files`), không chỉ "không thấy gì".

**Đường chuyển tiếp vẫn là rủi ro.** Với `allow_pickle=True`, payload `pathlib` được quét, sạch, và lọt qua cổng (test
`test_known_residual_risk_of_the_pickle_path` ghi lại điều này). Kết quả quét sạch không phải bằng chứng an toàn. Vì vậy pickle nhận theo
đường này chỉ được nạp hoặc chuyển sang safetensors trong sandbox cô lập (container không mạng, không mount secret, không quyền ghi
registry), mỗi model có người chịu trách nhiệm, và cả đường chuyển tiếp có hạn chót bỏ (vd. hai quý), sau đó cổng chỉ còn allowlist.

**Fail closed.** Máy quét lỗi, không hỗ trợ định dạng, báo cáo hỏng, báo có issue mà danh sách rỗng, hay có `errors` (vd. modelscan không
parse được tệp `joblib` có mảng numpy): mọi trường hợp "không chắc" đều là chặn. Một cổng cho qua khi máy quét lỗi sẽ cho qua đúng những
tệp mà kẻ tấn công cố tình làm hỏng để máy quét lỗi.

**Symlink.** Thư mục model do người khác tạo có thể chứa symlink tới `/etc/...` hay tới khoá; cổng không đọc, không đi theo, và chặn.

**Ở nơi làm việc.** Đặt cổng ở chỗ model đi vào registry (không chỉ lúc deploy), chạy máy quét trong sandbox không mạng như
`mlopskit.modelscan_run`, và có kế hoạch có hạn để chuyển mọi model pickle cũ sang định dạng an toàn. Hugging Face Hub hiển thị kết quả
quét pickle và khuyến khích safetensors; `torch.load` từ PyTorch 2.6 mặc định `weights_only=True`.
