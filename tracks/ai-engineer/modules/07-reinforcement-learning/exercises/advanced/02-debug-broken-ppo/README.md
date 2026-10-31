---
title: Gỡ lỗi một cài đặt PPO hỏng mà không báo lỗi
level: advanced
services: []
files:
  - path: starter/broken.ipynb
    note: 5 bug im lặng, không nói ở đâu
  - path: starter/BUGS.md
    note: Ghi lại từng bug
  - path: tests/test_broken.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/07-reinforcement-learning/exercises/advanced/02-debug-broken-ppo/starter/broken.ipynb
  - uv run pytest tracks/ai-engineer/modules/07-reinforcement-learning/exercises/advanced/02-debug-broken-ppo -q
---

## Mục tiêu

Code RL hỏng hiếm khi báo lỗi: agent vẫn học, chỉ học kém hơn, chậm hơn, hoặc đường cong nói dối. Bài này cho bạn một bản PPO
"gần đúng" và yêu cầu tìm hết chỗ sai bằng phép đo, không bằng đoán. Làm xong bạn có một quy trình khoanh vùng cho mọi cài đặt
policy gradient, và một `BUGS.md` đáng đưa vào portfolio.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian điều tra. Mỗi lần `train_ppo` trên CartPole (150 000 bước) mất khoảng 40 giây trên CPU 4 luồng; cell
train của notebook chạy 3 seed. Thử giả thuyết trên ít bước hơn hoặc trên env tí hon bạn tự viết.

`starter/broken.ipynb` là PPO cho CartPole-v1 cùng cấu trúc với bài Intermediate 02: `ActorCritic`, `ppo_policy_loss`, `gae`,
`collect_rollout` (SyncVectorEnv chế độ SAME_STEP), `ppo_update`, `train_ppo`. Notebook chạy hết, return có tăng, nhưng có
**5 bug im lặng** trong các cell định nghĩa, mỗi bug một chỗ. Đề không nói chúng ở đâu.

1. Tìm và sửa cả 5 bug ngay trong notebook. Không đổi chữ ký hàm và siêu tham số mặc định của `train_ppo`, `ppo_update`: sửa ở
   gốc, không bù triệu chứng bằng cách chỉnh lr, số epoch hay entropy coefficient.
2. Mỗi giả thuyết một phép thử: dùng các con số chẩn đoán của mục 6 lý thuyết (approx KL, clip fraction, entropy, value loss),
   so từng hàm với công thức hoặc với bản bạn đã viết ở bài Basic 03 và Intermediate 02, dựng env tí hon có đáp án biết trước.
   Thêm cell `explore` tuỳ ý.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với **triệu chứng** (con số), **cách phát hiện** (phép thử nào, kết
   quả gì) và **sửa** (dòng trước và sau). Cuối cùng ghi thứ tự gỡ, kết quả CartPole sau mỗi lần sửa, bug nào che bug nào, và
   checklist bạn sẽ chạy trước khi train một agent RL lâu.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Siêu tham số mặc định của `train_ppo` và `ppo_update` không đổi.
- Mỗi hàm làm đúng việc mà tên và docstring của nó nói: test so `ActorCritic`, `gae`, `ppo_policy_loss`, `collect_rollout` và một bước
  `ppo_update` với cài đặt tham chiếu trên dữ liệu nhỏ (giá trị, shape, gradient), và `train_ppo` học được một bandit theo ngữ cảnh.
- `BUGS.md` không còn TODO, ít nhất 5 mục `## Bug N`, ít nhất 300 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`; bản đã sửa đạt mức PPO của bảng mục 5 lý thuyết.

## Gợi ý

### Gợi ý 1

Có những con số không thể sai trên CartPole: return tối đa là 500, entropy ban đầu là $$\ln 2$$, approx KL không âm. Kiểm từng con số
mà notebook in hoặc vẽ với giới hạn lý thuyết của nó trước, rồi mới đi vào từng hàm theo thứ tự dữ liệu chảy: model, rollout, GAE,
loss, cập nhật.

### Gợi ý 2

Với mỗi hàm, tìm một đầu vào mà bạn tính tay được đầu ra: một env reward 1 mỗi bước bị cắt sau 3 bước cho `collect_rollout` và `gae`,
vài ratio cố định cho `ppo_policy_loss`, một batch 8 mẫu với `print(shape)` ở từng dòng của `ppo_update`. Một bug có thể che bug khác:
sửa xong mỗi bug, chạy lại mọi phép thử và ghi kết quả.
