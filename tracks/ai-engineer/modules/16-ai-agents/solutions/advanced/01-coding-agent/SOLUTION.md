# Hướng làm: coding agent trong sandbox

Bài không có code lời giải: sandbox có test, agent và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân
nhắc, kết quả của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Sandbox

| Quyết định | Bản tham chiếu | Vì sao |
| --- | --- | --- |
| Đường dẫn | `(root / rel).resolve()` rồi kiểm `root` nằm trong `parents`; từ chối đường dẫn tuyệt đối và rỗng | `resolve` đi theo `..` và symlink; so chuỗi tiền tố (`str.startswith`) thì `/tmp/repo-evil` lọt qua kiểm `/tmp/repo` |
| Tiến trình | `Popen(start_new_session=True)`, quá giờ thì `os.killpg(pid, SIGKILL)` | test của agent có thể tự sinh tiến trình con (hoặc `fork`); `proc.kill()` để lại tiến trình cháu chạy tiếp |
| Môi trường | chỉ `PATH`, `HOME=workdir`, `PYTHONPATH=workdir`, `PYTHONDONTWRITEBYTECODE`, `LANG` | key API, token trong môi trường của bạn không lọt vào mã do model viết |
| Mạng | `unshare -rn` (user + network namespace, không cần root) khi máy hỗ trợ, ghi lại `network_isolated` | mã không gọi được ra ngoài (tải gì đó, gửi dữ liệu đi); máy không có `unshare` thì báo rõ thay vì giả vờ |
| Chấm | chép mọi `.py` **ngoài** `tests/` sang thư mục tạm mới, thêm test ẩn, chạy `run_pytest` | agent sửa được `tests/` của nó; chấm bằng test đó là đo khả năng lách |
| Output test cho agent | `--tb=short`, giữ đoạn cuối | dòng assert và dòng tóm tắt nằm cuối; output đầy đủ của pytest lấp context |

Sandbox này **không** chặn: tiêu tốn RAM (không có giới hạn bộ nhớ, cần `resource.setrlimit` hoặc cgroup), đọc tệp
ngoài thư mục bằng mã Python chạy trong test (chỉ tool `read_file` đi qua `safe_path`), tiến trình nền tách khỏi nhóm
bằng `setsid` trong mã của agent. Production dùng container không mạng hoặc microVM (Firecracker, gVisor).

## Agent: hai thiết kế của bản tham chiếu

Cả hai dùng `parse_react` của bài Basic 02, 4 tool (`list_files`, `read_file`, `write_file`, `run_tests`), tối đa 12
bước, `num_ctx` 8 192, `seed` 0.

- **Thô**: lượt đầu chỉ có `TASK.md`; agent tự liệt kê và đọc tệp; `write_file` nhận `content` trong JSON hoặc khối code
  sau `Action Input`; action lặp vẫn được thực thi.
- **Cải tiến** (nhắm các lỗi đếm được ở bản thô): đưa sẵn nội dung mọi tệp `.py` của repo vào lượt đầu (bỏ được các bước
  "đọc" mà model nhỏ hay lặp); đọc `write_file` dễ dãi (nội dung trong khối code, hoặc trong `'''...'''` mà model hay
  viết thay cho chuỗi JSON); `run_tests`/`list_files` không có `Action Input` vẫn chạy; cùng action với cùng tham số
  (với `write_file` tính cả nội dung) lặp lại thì không thực thi mà trả observation nhắc "làm bước tiếp theo".

## Kết quả tham chiếu

PC của track (RTX 3060 dùng chung, Ollama 0.13.5), 12 task, chấm bằng test ẩn. Hai lượt `temperature` 0.7 (seed 2, 3) và
mọi lượt `qwen2.5:7b` chạy với `num_predict` 1 500: lần đầu chạy 7B thiết kế cải tiến, một lượt sinh không dừng làm
client chờ quá 600 giây và hỏng cả lượt chạy. Giới hạn số token ra là một điều kiện dừng cần có, giống ngân sách bước.

| Model, thiết kế | `temperature`, seed | Test ẩn pass | Test thấy được pass | Agent sửa `tests/` | Lỗi định dạng | Phút / lượt |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5:3b`, thô | 0, 0 | **1** / 12 | 1 | 1 | 31 | 6.6 |
| `qwen2.5:3b`, cải tiến | 0, 0 | **2** / 12 | 5 | 3 | 0 | 7.2 |
| `qwen2.5:3b`, cải tiến | 0.7, seed 1 / 2 / 3 | 1 / 1 / 2 | 3 / 3 / 4 | 2 / 1 / 2 | 1 / 1 / 0 | 7.4 / 8.9 / 8.2 |
| `qwen2.5:7b`, thô (PC) | 0, 0 | 7 / 12 | 11 | 0 | 0 | 4.1 |
| `qwen2.5:7b`, cải tiến (PC) | 0, 0 | 7 / 12 | 7 | 2 | 0 | 6.9 |

Phân loại lỗi (mỗi task một nhãn, theo thứ tự: pass, không bao giờ ghi tệp, dừng vì lỗi định dạng, test thấy được pass
mà test ẩn fail, hết bước mà test vẫn fail, báo xong khi test thấy được còn fail):

| | thô 3B | cải tiến 3B | cải tiến 3B, 3 seed (tổng 36) | thô 7B | cải tiến 7B |
| --- | --- | --- | --- | --- | --- |
| pass | 1 | 2 | 4 | 7 | 7 |
| không bao giờ ghi tệp | 6 | 1 | 1 | 0 | 0 |
| dừng vì lỗi định dạng | 1 | 0 | 0 | 0 | 0 |
| test thấy được pass, test ẩn fail | 0 | 3 | 6 | 4 | 1 |
| hết bước, test vẫn fail | 4 | 4 | 23 | 1 | 4 |
| báo xong khi test còn fail | 0 | 2 | 2 | 0 | 0 |

Đọc bảng:

- **pass@1 của `qwen2.5:3b` là 1 tới 2 trên 12** ở mọi cấu hình và seed. Thiết kế cải tiến **không** tăng pass@1 một cách
  phân biệt được với nhiễu (2/12 so với 1/12; ba seed cho 1, 1, 2). Nó đổi **kiểu hỏng**: lỗi định dạng từ 31 xuống 0, số
  task không bao giờ ghi tệp từ 6 xuống 1 (bản thô lặp `list_files` hay `read_file` 12 lần liền, hoặc viết mã vào chuỗi
  ba dấu nháy của Python bên trong JSON). Model giờ có viết mã, nhưng mã sai, và nó không sửa được từ output của test
  trong 12 bước. Với model này, nút thắt đã chuyển từ giao diện sang năng lực viết mã.
- **Cỡ model đổi kết quả nhiều hơn mọi thiết kế**: `qwen2.5:7b` giải 7/12 với cả hai thiết kế (cùng 7 task).
- **Test thấy được nói dối.** Bản thô 7B có 11 task pass test thấy được nhưng chỉ 7 pass test ẩn: 4 task chỉ đúng với
  trường hợp mà test thấy được kiểm (slug tiếng Việt, trung vị, `parse_duration`, số căn cước). Báo cáo dựa vào test thấy
  được sẽ ghi 11/12 thay vì 7/12.
- **Agent sửa test.** Thiết kế cải tiến (cả 3B và 7B) có những lượt ghi đè `tests/test_visible.py` dù prompt dặn không
  sửa: 3 task ở lượt 3B `temperature` 0, 2 task ở 7B. `grade` vẫn chấm đúng vì bỏ qua thư mục `tests/` của agent; một
  harness chạy `pytest` trong thư mục làm việc của agent sẽ chấm sai các task này. Bản thô 7B không có hiện tượng này;
  nguyên nhân chưa đo.
- Thời gian: một lượt 12 task mất 4 tới 9 phút trên PC (3B đi nhiều bước hơn nên không nhanh hơn 7B).

Bản tham chiếu dừng ở đây; một báo cáo tốt thử thêm: tăng ngân sách bước cho model nhỏ, sinh nhiều bản sửa rồi chọn bản
pass test (đổi pass@1 lấy pass@k), và chạy 7B nhiều seed.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test sandbox | 15 | Mọi test pass |
| Agent và harness | 15 | Chạy cả bộ bằng một lệnh, kết quả lưu ra tệp (JSONL) có trace, chấm bằng test ẩn |
| Thí nghiệm | 20 | pass@1 ở `temperature` 0 và ít nhất 3 seed `temperature` 0.7; ít nhất hai thiết kế agent trên cùng bộ; ghi rõ model, seed, `num_ctx`, ngân sách bước, phần cứng, thời gian |
| Phân tích lỗi | 25 | Taxonomy có đếm, mỗi loại một trace thật; tách "test thấy được pass" khỏi "test ẩn pass"; nêu các lần agent sửa test |
| Diễn giải trung thực | 15 | Không tuyên bố cải tiến khi chênh lệch nằm trong dao động giữa các seed; nói rõ 12 task nhỏ và tự tạo |
| Sandbox: giới hạn | 10 | Nêu ít nhất hai thứ sandbox không chặn và cách chặn ở production |

Đạt từ 70 điểm. Báo cáo chỉ có một lần chạy một seed và kết luận "thiết kế B tốt hơn A", hoặc chấm bằng test thấy được,
không quá 50 điểm.
