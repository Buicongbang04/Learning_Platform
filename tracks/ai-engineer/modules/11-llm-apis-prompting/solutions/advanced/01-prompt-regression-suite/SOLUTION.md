# Hướng làm: prompt regression suite

Bài không có code lời giải: suite và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả của
một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Phiên bản prompt | dict `{tên: {"messages": hàm dựng messages, "format": schema hoặc None, "num_predict": n, "parse": hàm đọc nhãn}}` | prompt, ràng buộc output và parser đổi cùng nhau; tách chúng ra là nguồn hồi quy hay gặp nhất (đổi định dạng mà quên đổi parser) |
| Khoá cache | `cache_key(messages mẫu với chỗ trống {sentence}, model, tham số sinh + format, id câu)` | sửa một chữ trong prompt tự chạy lại đúng phiên bản đó; đổi model hay `temperature` cũng vậy; không đổi gì thì không gọi model |
| Lưu cache | một tệp JSON, mỗi khoá `{reply, seconds, prompt_tokens, output_tokens}` | độ trễ lưu lúc gọi, không đo lại khi đọc cache; đổi parser hay thước đo không phải gọi lại |
| Tập ghim | 150 câu test, 50 mỗi nhãn, `random_state=0` (như Intermediate 02) | dùng lại được số của bài trước làm baseline; ghi rõ tập cân bằng khác phân phối thật |
| Cổng | `max_drop` 0.02, `class_max_drop` 0.10, không cho thêm câu `None` | 150 câu: đòi "tốt hơn có ý nghĩa" sẽ chặn gần như mọi thay đổi; chặn tụt rõ, tụt quá ngưỡng, hy sinh lớp hiếm, output hỏng |
| Sàn nhiễu | cùng baseline, chạy chỉ CPU (`num_gpu` 0) | chạy lại ngay trên cùng máy cho 0 câu đổi nhãn, nên đánh giá thấp nhiễu thật; đổi phần cứng cho 7 câu |
| Chi phí | token đo được x bảng giá Claude Haiku 5.5 kiểm ngày 2026-11-01 (0.10 / 0.50 USD mỗi MTok), ghi rõ token là của tokenizer Qwen | so tương đối giữa các prompt; con số tuyệt đối là ước lượng |

Lỗi hay gặp: khoá cache chỉ gồm tên phiên bản (sửa prompt mà giữ tên thì dùng lại kết quả cũ, cổng "xanh" sai); cổng chỉ
nhìn macro-F1 (thay đổi hy sinh lớp neutral lọt qua); so ứng viên chạy hôm nay với baseline chạy tuần trước trên máy
khác; báo "tốt hơn" từ một chênh lệch trong sàn nhiễu.

## Kết quả tham chiếu

Bản tham chiếu (giữ ngoài repo) chạy năm ứng viên và baseline trên 150 câu ghim, `qwen2.5:3b` qua Ollama 0.13.5,
`temperature` 0, `seed` 0, ngày 2026-11-01, PC của track (RTX 3060 **dùng chung** với một job train khác: số giây chỉ
để so tương đối, và các phiên bản chạy ở thời điểm khác nhau). Cổng mặc định: `max_drop` 0.02, `class_max_drop` 0.10,
`max_unparsed_increase` 0. Chi phí theo Claude Haiku 5.5 (0.10 / 0.50 USD mỗi MTok, kiểm 2026-11-01), token đếm bằng
tokenizer Qwen nên chỉ là ước lượng.

| Phiên bản | macro-F1 | F1 neg / neu / pos | `None` | p50 giây | Token vào / ra | USD / 1 000 câu | Cổng (hiệu [CI 95%]) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| zero-shot (baseline) | 0.804 | 0.862 / 0.723 / 0.825 | 0 | 0.12 | 131 / 2.0 | 0.014 | baseline |
| few-shot | 0.740 | 0.828 / 0.529 / 0.862 | 0 | 0.33 | 284 / 2.0 | 0.029 | chặn: `point_drop`, `class_drop:neutral` (-0.064 [-0.143, +0.021]) |
| JSON schema | 0.852 | 0.887 / 0.804 / 0.866 | 0 | 0.81 | 129 / 8.6 | 0.017 | qua (+0.049 [+0.001, +0.103]) |
| CoT-lite | 0.823 | 0.870 / 0.756 / 0.843 | 0 | 1.86 | 180 / 53.5 | 0.045 | qua (+0.020 [-0.043, +0.084]) |
| sửa vội: bỏ dòng định nghĩa neutral | 0.747 | 0.828 / 0.563 / 0.850 | 0 | 0.08 | 102 / 2.0 | 0.011 | chặn: `point_drop`, `class_drop:neutral` (-0.057 [-0.121, +0.010]) |
| baseline chỉ CPU (sàn nhiễu) | 0.816 | 0.881 / 0.717 / 0.848 | 0 | 0.81 | 131 / 2.0 | 0.014 | qua (+0.012 [-0.022, +0.047]) |

Điều bản tham chiếu rút ra (báo cáo của bạn có thể khác, miễn có số):

- **Sửa vội bị chặn đúng chỗ**: bỏ một dòng system làm prompt rẻ hơn 22% token vào, macro-F1 chỉ tụt 0.057 và khoảng tin
  cậy còn chạm 0, nhưng F1 neutral tụt 0.16 (model đoán neutral 21 lần thay vì 44). Cổng chỉ nhìn macro-F1 với "CI không
  chứa 0" sẽ cho qua.
- **Few-shot bị chặn** cùng lý do: ví dụ neutral không đại diện kéo F1 neutral xuống 0.529.
- **JSON schema và CoT-lite qua cổng, nhưng "qua" không có nghĩa "tốt hơn"**: sàn nhiễu đo bằng cùng baseline chạy chỉ CPU
  là ±0.03 tới 0.04 (7 câu đổi nhãn), và trên CPU lợi thế của JSON schema còn +0.002 (lý thuyết mục 7). CoT-lite tốn 27
  lần token ra và khoảng 15 lần độ trễ cho +0.02 trong nhiễu: cổng cho qua, nhưng quyết định sản phẩm là không dùng.
  Đây là một ca hợp lý để "không đồng ý với cổng": thêm điều kiện chi phí hoặc độ trễ (ví dụ chặn khi p50 tăng quá 3 lần
  mà hiệu chất lượng không vượt sàn nhiễu).
- Chạy lại y hệt ngay sau đó trên cùng máy (GPU) cho 0 câu đổi nhãn với cả zero-shot và CoT-lite; chạy lại zero-shot hơn
  một giờ sau (GPU chia với job khác) cho 2 câu đổi. Muốn đo nhiễu thật phải đổi điều kiện chạy (phần cứng, runtime,
  thời điểm), không chỉ bấm chạy lại.
- `p50` của "sửa vội" (0.08 giây) thấp hơn baseline (0.12): prompt ngắn hơn có góp phần, nhưng hai lượt chạy cách nhau
  khoảng 45 phút trên GPU dùng chung, nên không tách được phần nào do prompt. Muốn so độ trễ, chạy xen kẽ các phiên bản.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Suite | 20 | Phiên bản prompt là dữ liệu (gồm parser); cache theo `cache_key`, sửa prompt tự chạy lại đúng phiên bản; cả bảng sinh bằng một lệnh |
| Cổng và diễn giải | 25 | Cổng áp cho ít nhất 4 ứng viên; giải thích từng ngưỡng; có sàn nhiễu đo được; không gọi chênh lệch trong nhiễu là cải thiện; nêu một ca không đồng ý với cổng |
| Chi phí và độ trễ | 10 | Token vào/ra và p50 cho mọi phiên bản; chi phí 1 000 câu theo bảng giá có ngày kiểm hoặc ghi "giả định" |
| Phân tích lỗi | 20 | Ít nhất 5 câu bị thay đổi bị chặn làm sai, đọc tận mắt, có phân loại (ví dụ lệch, nhãn đáng ngờ, câu mơ hồ) |
| Báo cáo | 10 | Quyết định có số ở đầu, thiết lập tái lập được, có giới hạn |

Đạt từ 70 điểm. Cổng chỉ dựa trên macro-F1 điểm (không khoảng tin cậy, không F1 từng lớp), hoặc khoá cache không gồm nội
dung prompt, không quá 50 điểm.
