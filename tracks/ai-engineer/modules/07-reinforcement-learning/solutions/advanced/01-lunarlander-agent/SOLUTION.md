# Hướng làm: agent hạ cánh LunarLander (portfolio)

Bài không có code lời giải: agent là thiết kế của bạn. Dưới đây là cài đặt 4 hàm được chấm, các quyết định thiết kế cần cân nhắc, kết
quả của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Bốn hàm được chấm

| Hàm | Cài đặt | Điểm dễ sai |
| --- | --- | --- |
| `evaluate_policy` | một env, `reset(seed=seed + i)`, cộng reward tới `terminated or truncated` | reset cùng một seed cho mọi episode: 100 episode thành 1 episode lặp lại |
| `record_video` | một khung `env.render()` sau reset, một khung sau mỗi `step`, `imageio.mimsave(path, frames, fps=fps, macro_block_size=1)` | thiếu khung đầu; `macro_block_size` mặc định 16 làm ffmpeg tự đổi kích thước 600x400 thành 608x400 và in cảnh báo |
| `curve_on_grid` | trung bình return có `end_step` trong `(g − window, g]`, rỗng thì `nan` | cửa sổ đóng hai đầu đếm trùng episode ở biên |
| `interquartile_mean` | sắp xếp, bỏ `floor(n/4)` mỗi đầu, trung bình phần giữa (bằng `scipy.stats.trim_mean(x, 0.25)`) | dùng `np.percentile` rồi lọc theo giá trị: sai khi có giá trị trùng ở biên |

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Thuật toán | PPO (code bài Intermediate 02) | ổn định trên nhiều seed hơn DQN, dùng lại được nguyên code đã test |
| Mạng | actor và critic tách rời, MLP 64-64 tanh, 9 797 tham số | observation 8 số; mạng lớn hơn không giúp, chỉ chậm |
| Thu dữ liệu | 16 env × 512 bước = 8 192 mẫu mỗi lần cập nhật | gradient ít nhiễu; LunarLander có episode dài tới 1 000 bước |
| Cập nhật | 4 epoch × 128 minibatch (64 mẫu), lr $$3\times10^{-4}$$ giảm tuyến tính, clip 0.2, entropy 0.01, clip norm 0.5 | 512 bước gradient mỗi lần cập nhật; minibatch 256 mẫu (128 bước) không tới 200 sau 1 triệu bước (xem dưới) |
| $$\gamma$$, $$\lambda$$ | 0.999, 0.98 | phần thưởng hạ cánh đến ở cuối episode dài |
| `truncated` | bootstrap từ `final_obs` | agent sớm học lơ lửng tới 1 000 bước: coi đó là kết thúc sẽ dạy critic sai |
| Chọn checkpoint | eval 10 episode (seed 20 000..20 009) mỗi 100 000 bước, giữ bản tốt nhất | đường cong PPO có lúc tụt; seed chọn khác seed báo cáo |
| Báo cáo | 100 episode greedy, seed 10 000..10 099 | cố định, tách khỏi seed chọn checkpoint |

## Kết quả tham chiếu

PPO, 1 triệu bước env mỗi seed, CPU 4 luồng (Xeon E5-2696 v3, máy dùng chung), torch 2.14.1 CPU. Đánh giá policy greedy trên 100
episode cố định (seed 10 000..10 099):

| Seed | Trung bình ± độ lệch chuẩn | IQM | Episode ≥ 200 | Checkpoint tốt nhất (trung bình, ≥ 200) | Policy lấy mẫu | Số episode train | Train |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 222.2 ± 23.0 | 222.2 | 83% | 222.3, 80% | 162.3 | 2 097 | 282 s |
| 1 | 239.5 ± 20.8 | 240.3 | 98% | 230.7, 92% | 230.8 | 2 402 | 285 s |
| 2 | 238.7 ± 21.6 | 238.6 | 97% | 236.6, 94% | 246.9 | 2 914 | 294 s |

Gộp 300 episode: 233.5, IQM 234.1, 92.7% trên 200. Mốc so sánh trên cùng 100 episode: policy ngẫu nhiên −194.3 ± 120.8, policy "không
làm gì" −131.5 ± 44.0.

Return lúc train (trung bình các episode kết thúc trong 50 000 bước trước mốc), seed 0 / 1 / 2:

| Mốc | 50k | 250k | 450k | 650k | 850k |
| --- | --- | --- | --- | --- | --- |
| Return | −143 / −140 / −134 | 50 / 44 / 32 | 100 / 77 / 101 | 127 / 114 / 172 | 139 / 191 / 211 |

Chẩn đoán: approx KL lớn nhất 0.014 / 0.011 / 0.012, clip fraction lớn nhất 0.20 / 0.20 / 0.22, entropy cuối 0.79 / 0.82 / 0.86 (ban
đầu $$\ln 4 = 1.39$$), explained variance cuối 0.93 / 0.64 / 0.83.

Điều đáng đưa vào báo cáo:

- **Ablation một biến.** Cùng mọi thứ, minibatch 256 mẫu (128 bước gradient mỗi lần cập nhật thay vì 512) cho policy greedy −18.3 /
  31.8 / 136.5 sau 1 triệu bước: không seed nào giải được. Approx KL và clip fraction của hai cấu hình gần như nhau, nên chẩn đoán
  không chỉ ra vấn đề; thí nghiệm đổi đúng một biến mới chỉ ra.
- **Checkpoint tốt nhất không tốt hơn trọng số cuối** ở đây (lr giảm về 0 nên cuối train ổn định), nhưng eval 10 episode để chọn
  checkpoint nhiễu: seed 1 chọn được bản kém hơn bản cuối (230.7 so với 239.5).
- **Greedy và lấy mẫu lệch nhau**: seed 0 lấy mẫu chỉ 162. Ở lần chạy hỏng thì greedy tệ hơn lấy mẫu. Luôn nói rõ.
- **Video** (seed 1, trọng số cuối): episode tốt nhất 276 điểm, 378 bước, hạ thẳng giữa hai cờ; episode tệ nhất 168 điểm, 631 bước,
  chạm đất sát cờ phải rồi trượt ra ngoài.

### Mở rộng Atari (không chấm)

PPO cùng code, CNN Nature (3 conv + Linear 512, actor và critic chung thân, khởi tạo orthogonal), 16 env `AtariVectorEnv` cho Pong
(sticky action 0.25, no-op 30, không clip reward vì Pong chỉ có ±1), 128 bước mỗi rollout, 4 epoch × 4 minibatch 512 mẫu, clip 0.1,
lr $$2.5\times10^{-4}$$ giảm tuyến tính, entropy 0.01, 3 triệu bước, seed 0. RTX 3060 12GB dùng chung: 39.6 phút, khoảng 1 260 bước mỗi
giây, VRAM đỉnh 0.25 GB. Return lúc train: −20.6 (100k), −19.2 (500k), −12.4 (1M), −12.2 (2M), −10.3 (3M); greedy trên 10 ván:
−11.1 ± 5.4, từ −19 tới −3. Học được nhưng chưa thắng ở ngân sách này.

`AtariVectorEnv` không trả `final_obs`; bản tham chiếu đếm số lần `truncated` trong cả 3 triệu bước: 0 (giới hạn 108 000 khung không bao
giờ chạm với Pong), nên coi `truncated` như kết thúc là chấp nhận được ở **game này**. Với game có time limit thật thì không. Báo cáo Atari
tốt nói rõ một seed, ngân sách, và so với mốc ngẫu nhiên; đừng gọi −11 là "chơi được Pong".

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | 4 hàm được chấm pass, `REPORT.md` đạt kiểm tra định dạng |
| Agent tự cài đúng | 20 | thuật toán tự viết, xử lý đúng `terminated`/`truncated`, có chẩn đoán (approx KL, clip fraction, entropy hoặc Q-value) |
| Kết quả | 20 | ≥ 3 seed cùng cấu hình; trung bình ≥ 200 trên 100 episode cố định ở ít nhất 2 seed; so với policy ngẫu nhiên và "không làm gì" |
| Giao thức đánh giá | 15 | seed chọn checkpoint tách khỏi seed báo cáo; nói rõ greedy hay lấy mẫu; IQM hoặc độ phân tán; đường cong theo số bước env |
| Video và hành vi | 15 | video agent tốt nhất (và nên có một episode thất bại); mô tả hành vi, kiểu thất bại |
| Chất lượng portfolio | 20 | tóm tắt có số ở đầu, bảng siêu tham số và phần cứng, mục lỗi đã gặp có triệu chứng và cách phát hiện, giới hạn và bước tiếp |

Đạt từ 70 điểm. Báo cáo chỉ có một seed, hoặc báo cáo điểm của chính các episode dùng để chọn checkpoint, không quá 50 điểm.
