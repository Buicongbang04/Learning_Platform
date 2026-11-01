---
title: Agent hạ cánh LunarLander, nhiều seed, có video (portfolio)
level: advanced
services: []
files:
  - path: starter/agent.ipynb
    note: 4 hàm chấm, agent tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_agent.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/07-reinforcement-learning/exercises/advanced/01-lunarlander-agent/starter/agent.ipynb
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/advanced/01-lunarlander-agent -q
---

## Mục tiêu

Làm một agent chơi game hoàn chỉnh như một dự án thật: tự cài thuật toán (PPO hoặc DQN của module này), train trên nhiều seed, đánh
giá theo giao thức không tự lừa mình, quay video agent hạ cánh, và viết báo cáo mà người chưa đọc code vẫn tin được con số.
`LunarLander-v3` đủ khó để policy ngẫu nhiên và các cấu hình tệ thất bại rõ ràng, đủ rẻ để train trên CPU laptop.

## Đề bài

**Phần cứng:** CPU · ~480 phút

Thời gian trên là thời gian làm bài (agent, thí nghiệm, báo cáo). Thời gian máy của bản tham chiếu (PPO, 1 triệu bước env mỗi seed, CPU 4 luồng,
PC Xeon E5-2696 v3 dùng chung): khoảng 4.8 phút train mỗi seed cộng 1 tới 2 phút đánh giá 100 episode, khoảng 20 phút cho 3 seed. Laptop
không GPU chạy được nguyên cấu hình này (MLP nhỏ, GPU không giúp gì); máy yếu hơn thì chạy từng seed một qua đêm thay vì giảm số bước:
ở 500 000 bước, return lúc train của bản tham chiếu mới khoảng 100.

1. Trong `starter/agent.ipynb`, viết 4 hàm được chấm ở mục 1 của notebook: `evaluate_policy`, `record_video`, `curve_on_grid`,
   `interquartile_mean`.
2. Tự cài agent (không dùng thư viện RL): gợi ý mặc định là PPO của bài Intermediate 02 với cấu hình cột LunarLander ở mục 6 phần lý
   thuyết. Train **ít nhất 3 seed** cùng cấu hình.
3. Giao thức đánh giá: chọn checkpoint bằng đánh giá định kỳ trên một tập seed riêng (ví dụ 10 episode, seed 20 000..20 009), báo cáo
   trên **100 episode cố định** (seed 10 000..10 099), policy greedy, cả trọng số cuối lẫn checkpoint tốt nhất; so với policy ngẫu
   nhiên và "không làm gì".
4. Quay video bằng `record_video` với `gym.make("LunarLander-v3", render_mode="rgb_array")`: ít nhất một episode của agent tốt nhất,
   nên thêm một episode điểm thấp để thấy agent thất bại kiểu gì. Video và checkpoint để ngoài git (`starter/videos/`,
   `starter/checkpoints/` hoặc nơi khác), hoặc đưa video lên một trang và dán link.
5. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` portfolio tốt** đọc trong 5 phút mà không cần mở code:

- Mở bằng **tóm tắt có số**: "PPO tự viết 9 000 tham số, 3 seed, 100 episode đánh giá: trung bình 2xx, 9x% episode hạ cánh ≥ 200,
  train 1 triệu bước trong N phút trên CPU", kèm link video.
- **Thiết lập tái lập được**: bảng siêu tham số, seed train/chọn/đánh giá, phần cứng, số luồng, wall-clock.
- **Đường cong** theo số bước env, trung bình và độ phân tán giữa seed, có câu đọc hình; chẩn đoán (approx KL, clip fraction,
  entropy) nếu là PPO.
- **Đánh giá trung thực**: bảng từng seed, IQM, tỉ lệ ≥ 200; nói rõ seed nào kém và vì sao (nếu biết).
- **Hành vi**: agent làm gì trong video, thất bại kiểu gì (lơ lửng hết giờ, rơi nghiêng, hạ cánh ngoài cờ).
- **Lỗi đã gặp**: triệu chứng có số, cách phát hiện, cách sửa.
- **Giới hạn**: 3 seed nói được gì, so với thư viện chuẩn thế nào nếu có so, bước tiếp (Atari, action liên tục).

### Mở rộng (không chấm): Atari trên GPU

Cùng PPO, đổi MLP thành CNN kiểu Nature DQN (3 conv + 1 Linear 512), observation tiền xử lý như mục 4 lý thuyết
(`AtariPreprocessing` + `FrameStackObservation` 4 khung), 16 env (bản tham chiếu; ít hơn nếu CPU yếu). Env GPU của repo (`setup/gpu`) chưa có `gymnasium`/`ale-py`; chạy
bằng lớp phủ tạm của uv, không sửa `pyproject.toml`:

```bash
uv run --project setup/gpu --with "gymnasium[box2d]==1.4.0" --with "ale-py==0.12.1" \
  --with "imageio==2.38.1" --with "imageio-ffmpeg==0.6.0" python <script_atari>.py
```

Train nhanh hơn nhiều với `ale_py.vector_env.AtariVectorEnv` (tiền xử lý bằng C++ đa luồng, cùng kết quả với các wrapper trên sau
vài khung đầu); đánh giá và quay video bằng env Gymnasium có wrapper và `render_mode="rgb_array"`. Bản tham chiếu, **đo trên PC RTX 3060
12GB** (GPU dùng chung): Pong, 16 env, 3 triệu bước agent trong 39.6 phút, VRAM đỉnh 0.25 GB; policy greedy −11.1 ± 5.4 trên 10 ván (ngẫu
nhiên −21), học được nhưng chưa thắng. Laptop GPU 4GB: cấu hình này dư bộ nhớ; tốc độ phụ thuộc CPU (env) nhiều hơn GPU, chưa đo trên
laptop, tính trước khoảng 1 giờ cho 3 triệu bước. Không có GPU: chỉ nên chạy vài trăm nghìn bước để kiểm pipeline.

## Tiêu chí đạt

- `evaluate_policy` reset episode `i` bằng `seed + i` trên một env; `record_video` ghi đúng số khung (1 + số bước) ra `.mp4` và `.gif`,
  tạo thư mục cha; `curve_on_grid` lấy đúng cửa sổ nửa mở `(g − window, g]`; `interquartile_mean` khớp định nghĩa.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, nói rõ seed; hình (nếu có) và video cục bộ được link phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`: agent tự cài, ≥ 3 seed, 100 episode đánh giá cố định, trung bình ≥ 200 ở ít nhất 2
  trên 3 seed (bản tham chiếu: 222.2 / 239.5 / 238.7).

## Gợi ý

### Gợi ý 1

LunarLander khác CartPole ở ba chỗ: episode dài tới 1 000 bước và reward lớn nhất đến ở cuối (hạ cánh +100), nên cần $$\gamma$$ lớn hơn
(0.999) và $$\lambda$$ lớn hơn (0.98); reward mỗi bước có độ lớn chênh nhau nhiều (−100 khi rơi, −0.3 mỗi khung bật động cơ); và có
`truncated` thật ở 1 000 bước khi agent học được cách lơ lửng. Dựng toàn bộ pipeline với 100 000 bước trước (vài chục giây), chắc đường
cong có lên, rồi mới chạy dài.

### Gợi ý 2

Đếm số **bước gradient** chứ không chỉ số bước env: 16 env × 512 bước = 8 192 mẫu mỗi lần cập nhật; chia minibatch 256 mẫu thì 4 epoch
chỉ là 128 bước gradient, chia minibatch 64 mẫu là 512 bước. Nếu return lúc train dừng quanh 100 sau nửa triệu bước, thử đổi đúng
một biến này trước khi nghĩ tới thuật toán khác. Giữ `best_state` theo đánh giá định kỳ, và đánh giá cả
policy greedy lẫn lấy mẫu: trên LunarLander hai con số này có thể lệch nhau rất xa.
