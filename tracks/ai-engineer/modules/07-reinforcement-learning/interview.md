# Câu hỏi phỏng vấn: Reinforcement Learning

## Khi nào nên dùng reinforcement learning thay vì supervised learning hay tối ưu hoá thông thường?

RL giải bài toán **ra quyết định tuần tự**: action hôm nay đổi dữ liệu và trạng thái ngày mai, phản hồi chỉ là một reward (thường thưa,
trễ), và không ai cho biết action đúng. Ba điều kiện để RL đáng giá:

1. Quyết định có hệ quả về sau (không phải một lần phân loại độc lập).
2. Không có nhãn "action đúng" nhưng đo được kết quả.
3. Có chỗ để thử sai rẻ: simulator, game, hoặc log đủ phong phú cho offline RL.

Nếu có nhãn, dùng supervised learning (rẻ, ổn định, đánh giá dễ). Nếu biết mô hình chính xác và không gian nhỏ, dùng planning hoặc
dynamic programming. Nếu chỉ một quyết định độc lập mỗi lần với phản hồi tức thì (chọn banner hiển thị), contextual bandit đủ và an
toàn hơn RL đầy đủ. Ứng viên senior nói thêm cái giá: RL cần rất nhiều tương tác (DQN Nature dùng 200 triệu khung hình mỗi game),
phương sai giữa các seed lớn, và agent tối ưu đúng reward bạn viết chứ không phải ý bạn muốn. Câu hỏi "có baseline nào chưa" luôn
đi trước: trên CartPole, một policy viết tay một dòng (đẩy xe về phía sào đang ngã) đạt 493 trên 500 mà không học gì.

## Viết phương trình Bellman cho Q^π và Q*. Vì sao chúng quan trọng?

$$
Q^\pi(s,a) = \sum_{s'} P(s' \mid s,a)\Big[R + \gamma \sum_{a'}\pi(a' \mid s')Q^\pi(s',a')\Big], \qquad
Q^*(s,a) = \sum_{s'} P(s' \mid s,a)\Big[R + \gamma \max_{a'} Q^*(s',a')\Big]
$$

Phương trình đầu tuyến tính (giải bằng hệ phương trình hay lặp), phương trình sau phi tuyến vì có $$\max$$. Chúng quan trọng vì gần như
mọi thuật toán là một cách giải xấp xỉ chúng: value iteration lặp vế phải khi biết $$P$$; Q-learning thay kỳ vọng bằng một mẫu
$$r + \gamma\max Q(s')$$; DQN dùng đúng target đó với mạng nơ-ron; actor-critic học $$V^\pi$$ bằng phương trình đầu để làm baseline. Toán tử
Bellman là một γ-contraction, nên lặp hội tụ với tốc độ $$\gamma$$ mỗi vòng: trên FrozenLake 4x4, value iteration cần 145 lần quét với
$$\gamma = 0.9$$ và 571 lần với $$\gamma = 0.99$$ (tol $$10^{-10}$$).

## `terminated` và `truncated` khác nhau thế nào? Nhầm thì chuyện gì xảy ra?

`terminated`: MDP thật sự kết thúc (rơi hố, sào đổ), giá trị trạng thái sau là 0, không bootstrap. `truncated`: lần chạy bị cắt vì lý
do ngoài MDP, thường là time limit; trạng thái sau vẫn có giá trị, target phải là $$r + \gamma V(s')$$ với $$s'$$ là observation **thật** cuối
episode (trong vector env của Gymnasium nằm ở `info["final_obs"]`, không phải observation sau reset).

Coi `truncated` là kết thúc (lỗi của rất nhiều code thời Gym cũ, khi chỉ có một cờ `done`) dạy critic rằng trạng thái ở bước 500 của
CartPole có giá trị gần 0, trong khi trạng thái y hệt ở bước 300 có giá trị gần $$1/(1-\gamma) = 100$$: mâu thuẫn, critic nhiễu, PPO
dao động gần đỉnh. Ngược lại, quên cắt đệ quy GAE ở bước `truncated` thì advantage của episode sau chảy về episode trước. Một test
đơn giản bắt cả hai: env reward 1 mỗi bước, không bao giờ kết thúc, cắt sau 5 bước; Q đúng phải tiến tới $$1/(1-\gamma)$$.

## Q-learning và SARSA khác nhau ở đâu? Cho một ví dụ mà khác biệt đó quan trọng.

Q-learning dùng target $$r + \gamma\max_{a'}Q(s',a')$$: học giá trị của policy **greedy**, bất kể dữ liệu do policy nào sinh ra (off-policy).
SARSA dùng $$r + \gamma Q(s', a')$$ với $$a'$$ là action thật sự sẽ làm: học giá trị của chính policy đang chạy, kể cả phần khám phá
(on-policy).

Ví dụ kinh điển là CliffWalking với ε = 0.1: Q-learning học đường ngắn nhất sát vực (13 bước) nhưng trong lúc train thỉnh thoảng bị ε
đẩy xuống vực (−100), nên return lúc train tệ hơn; SARSA học đường vòng xa vực (15 tới 19 bước) vì giá trị các ô sát vực đã tính cả
rủi ro bị đẩy xuống, và return lúc train cao hơn. Trong thực tế: robot hay hệ thống mà hành vi **trong lúc học** gây hậu quả thì
on-policy an toàn hơn; khi chỉ policy cuối quan trọng hoặc muốn học từ log cũ (replay buffer, offline RL) thì cần off-policy.

## Vì sao DQN cần replay buffer và target network?

Ghép function approximation, bootstrapping và off-policy là "deadly triad" (Sutton và Barto): không có đảm bảo hội tụ, Q có thể nổ.

- **Replay buffer** phá tương quan giữa các mẫu liên tiếp (gradient descent giả định mẫu gần độc lập; 32 khung hình liên tiếp của
  một game gần như giống nhau) và dùng mỗi chuyển nhiều lần. Chỉ làm được vì Q-learning off-policy.
- **Target network** giữ target $$y = r + \gamma\max Q_{\theta^-}(s')$$ đứng yên trong một khoảng: không có nó, mỗi bước cập nhật cũng dịch chính
  target, mạng đuổi theo cái bóng của mình. Hard update chép mỗi C bước; soft (Polyak) update $$\theta^- \leftarrow (1-\tau)\theta^- + \tau\theta$$ mỗi bước.

Số đo của module: cùng code DQN trên CartPole, bỏ target network thì $$\max_a Q(s_0, a)$$ lên cỡ một triệu (giá trị thật tối đa khoảng
99) và policy sụp về một action, return 9; giữ target network với soft update $$\tau = 0.005$$ thì cả 3 seed đạt gần 500. Câu trả lời tốt nhắc thêm hai chi tiết: target tính dưới `no_grad` (semi-gradient), và chỉ lưu `terminated` vào buffer.

## Overestimation bias trong Q-learning đến từ đâu? Double DQN sửa thế nào?

$$\mathbb E[\max_a \hat Q(a)] \ge \max_a \mathbb E[\hat Q(a)]$$: max trên các ước lượng nhiễu bị lệch lên, vì nó chọn đúng những action được ước lượng
cao **do nhiễu**. Ví dụ đo được: 10 action cùng giá trị thật 0, mỗi cái ước lượng từ 5 mẫu nhiễu chuẩn, max ước lượng trung bình 0.687.
Q-learning lấy max ở mọi bước rồi bootstrap nên độ lệch lan và tích luỹ.

Double Q-learning tách việc **chọn** và **đánh giá** cho hai bộ ước lượng độc lập (trong ví dụ trên: −0.002, không lệch). Double DQN
dùng sẵn hai mạng có trong DQN: $$a^* = \arg\max_a Q_\theta(s', a)$$ bằng mạng online, giá trị $$Q_{\theta^-}(s', a^*)$$ bằng target network. Một dòng
code, không tốn thêm tính toán, nên gần như luôn bật.

## Suy ra policy gradient. Vì sao trừ baseline không làm lệch gradient?

$$J(\theta) = \mathbb E_{\tau \sim \pi_\theta}[G(\tau)]$$. Dùng $$\nabla_\theta p_\theta(\tau) = p_\theta(\tau)\nabla_\theta\log p_\theta(\tau)$$ và
$$\log p_\theta(\tau) = \log p(s_0) + \sum_t[\log\pi_\theta(a_t \mid s_t) + \log P(s_{t+1} \mid s_t, a_t)]$$, các số hạng của môi trường không phụ
thuộc $$\theta$$ nên

$$
\nabla_\theta J = \mathbb E_\tau\Big[\sum_t \nabla_\theta\log\pi_\theta(a_t \mid s_t)\,G_t\Big]
$$

(thay $$G(\tau)$$ bằng reward-to-go $$G_t$$ vì reward trước $$t$$ không phụ thuộc $$a_t$$). Không cần mô hình môi trường.

Baseline $$b(s_t)$$ không phụ thuộc action: $$\mathbb E_{a\sim\pi}[\nabla\log\pi(a \mid s)\,b(s)] = b(s)\sum_a\nabla\pi(a \mid s) = b(s)\nabla 1 = 0$$. Không đổi kỳ
vọng, nhưng giảm phương sai mạnh khi $$b \approx \mathbb E[G_t \mid s_t]$$: trên một bandit 3 action reward 10/11/12, phương sai mỗi mẫu của
ước lượng giảm từ 81.6 xuống 0.89, tức cần ít hơn khoảng 90 lần số mẫu cho cùng độ chính xác. Lỗi hay gặp khi cài: để gradient chảy
qua baseline (thiếu `detach`), và baseline phụ thuộc action (khi đó có bias).

## GAE là gì? λ điều khiển cái gì?

$$\hat A_t = \sum_k(\gamma\lambda)^k\delta_{t+k}$$ với $$\delta_t = r_t + \gamma(1-d_t)V(s_{t+1}) - V(s_t)$$, tính bằng một vòng ngược
$$\hat A_t = \delta_t + \gamma\lambda(1 - \text{done}_t)\hat A_{t+1}$$. $$\lambda = 0$$ là TD error một bước (bias cao vì tin critic, phương sai thấp);
$$\lambda = 1$$ là $$G_t - V(s_t)$$ (không bias, phương sai cao); 0.95 là mặc định của PPO. $$\gamma$$ định nghĩa bài toán (tầm nhìn), $$\lambda$$ là núm
bias-variance của **ước lượng**.

Điểm senior: hai mặt nạ khác nhau. Trong $$\delta_t$$, chỉ `terminated` bỏ $$V(s_{t+1})$$; trong đệ quy, mọi kết thúc episode (cả `truncated`)
đều cắt. Và `returns = advantages + values` là target của critic, không phải advantage.

## Giải thích clipped objective của PPO. Nếu đổi `min` thành `max` thì sao?

$$L = \mathbb E[\min(\rho A, \mathrm{clip}(\rho, 1-\epsilon, 1+\epsilon)A)]$$ với $$\rho = \pi_\theta/\pi_{\text{old}}$$. Muốn dùng một batch cho nhiều bước gradient
thì phải sửa bằng importance ratio, và chỉ tin ước lượng khi policy mới còn gần policy cũ. Lấy `min` cho một **cận dưới bi quan**:

- $$A > 0$$: khi $$\rho > 1 + \epsilon$$ objective thành hằng, gradient 0 (đã tăng đủ); khi $$\rho < 1 - \epsilon$$ vẫn còn gradient kéo lên.
- $$A < 0$$: đối xứng, chỉ tắt gradient khi đã giảm đủ ($$\rho < 1 - \epsilon$$).

Phép cắt chỉ chặn việc đi xa hơn theo hướng có lợi, không bao giờ chặn việc sửa sai. Đổi thành `max` đảo ngược logic: action tốt bị
đẩy lên **không giới hạn** (mất trust region), còn action tốt đã bị giảm quá tay thì gradient bị tắt, không kéo lại được. Code vẫn
chạy, loss vẫn giảm, nên chỉ phát hiện được bằng approx KL và clip fraction tăng vọt hoặc test so với cài đặt tham chiếu.

## Reward của agent PPO tăng rồi sụp giữa chừng. Bạn chẩn đoán thế nào?

Đi theo thứ tự rẻ tới đắt, mỗi giả thuyết một con số:

1. **Metric có đúng không**: return log có vượt mức tối đa lý thuyết không (CartPole > 500 là bug log), episode return có được reset.
2. **approx KL và clip fraction** theo từng lần cập nhật: tăng vọt ngay trước khi sụp là bước cập nhật quá lớn: giảm lr, giảm epoch,
   thêm dừng sớm theo KL, kiểm lr có giảm dần.
3. **Entropy**: rơi về 0 là policy sụp tất định, mất khám phá: kiểm dấu entropy bonus, hệ số.
4. **Critic**: explained variance âm hoặc value loss nổ: kiểm shape `(B,)` với `(B, 1)` (broadcasting ra `(B, B)`), reward scale,
   `terminated`/`truncated`.
5. **Advantage**: có chuẩn hoá theo minibatch không, có NaN khi advantage hằng không.
6. Chỉ khi các thứ trên sạch mới nghĩ tới siêu tham số, và luôn so trên ít nhất 3 seed: một seed sụp có thể chỉ là phương sai.

Ứng viên tốt nói thêm: trước khi train dài, chạy trên một env đồ chơi có đáp án biết trước (bandit theo ngữ cảnh, hành lang 5 ô) và
một bài test so từng hàm với cài đặt tham chiếu; phần lớn bug RL là bug "im lặng".

## Bạn báo cáo kết quả của một agent RL thế nào để người khác tin?

- Nhiều seed train (ít nhất 3, tốt hơn 5 tới 10); báo cáo trung bình kèm độ phân tán hoặc IQM với khoảng tin cậy bootstrap
  (`rliable`). Một seed không phải kết quả.
- Episode đánh giá cố định (danh sách seed reset cố định), tách khỏi episode train; nói rõ policy greedy hay lấy mẫu, bao nhiêu episode.
- Chọn checkpoint trên một tập seed đánh giá, báo cáo trên tập khác (giống val/test).
- Đường cong theo số bước env (sample efficiency), kèm wall-clock và phần cứng.
- So với baseline: ngẫu nhiên, heuristic, và nếu có thì một thư viện chuẩn (Stable-Baselines3) cùng ngân sách.
- Video vài episode, cả thành công lẫn thất bại: con số trung bình che hành vi lạ (agent lơ lửng mãi để không bị phạt rơi).

## Mô tả pipeline RLHF. Vì sao cần KL penalty?

SFT model → sinh nhiều câu trả lời cho mỗi prompt → người gán nhãn so sánh từng cặp → reward model học bằng loss Bradley-Terry
$$-\log\sigma(r(x, y_w) - r(x, y_l))$$ → PPO tối ưu policy với reward $$r_\phi(x, y) - \beta\,\mathrm{KL}(\pi_\theta \| \pi_{\text{ref}})$$. Mỗi token là một action;
reward model chấm ở token cuối, KL trải ra từng token. Bốn model trong bộ nhớ: policy, reference, reward model, critic.

KL penalty cần vì reward model là **proxy** học từ nhãn nhiễu và thiên vị. Tối ưu nó không giới hạn sẽ khai thác chỗ sai của nó (reward
hacking): câu dài hơn, giọng tự tin hơn, chiều theo người hỏi. Nghiệm đóng $$\pi^* \propto \pi_{\text{ref}}\exp(r/\beta)$$ cho thấy rõ: $$\beta$$ nhỏ thì
dồn hết xác suất vào câu reward model chấm cao nhất. Trong một thí nghiệm đồ chơi với reward model thiên vị độ dài, chất lượng thật
tăng từ 0.44 lên 0.50 khi $$\beta = 1$$, rồi rơi về 0 khi $$\beta = 0.05$$ trong lúc reward model chấm ngày càng cao. Phải theo dõi cả KL, độ dài
và một đánh giá độc lập.

## PPO-RLHF, DPO và GRPO: khi nào chọn cái nào?

| | PPO-RLHF | DPO | GRPO |
| --- | --- | --- | --- |
| Reward | reward model riêng | ngầm trong policy | kiểm được (đúng/sai) hoặc reward model |
| Model trong bộ nhớ | 4 | 2 | 2 (± reward model) |
| Sinh văn bản khi train | có | không | có, cả nhóm mỗi prompt |
| Khó tune | cao | thấp | vừa |

DPO đảo nghiệm đóng của objective có KL để viết reward theo log-ratio policy/reference, thế vào loss Bradley-Terry: ra một loss
supervised trên cặp ưu tiên. Chọn khi có bộ cặp ưu tiên và muốn ổn định, rẻ. GRPO giữ khung PPO (ratio, clip, KL) nhưng bỏ critic,
advantage là reward chuẩn hoá trong nhóm câu trả lời của cùng prompt. Chọn cho toán, code, reasoning có đáp án kiểm được. PPO với
reward model đầy đủ khi ngân sách lớn và reward phức tạp, không kiểm tự động được. Chi tiết ở module 14 (DPO) và 15 (GRPO).

## Case: một công ty thương mại điện tử muốn dùng RL để định giá động. Bạn thiết kế thế nào?

Câu trả lời mạnh bắt đầu bằng việc đóng khung, không phải chọn thuật toán:

1. **Có thật là RL không?** Nếu giá hôm nay ít ảnh hưởng nhu cầu ngày mai thì đây là contextual bandit (mỗi lần định giá một quyết
   định, reward là lợi nhuận đơn hàng): rẻ, an toàn, đánh giá offline được. RL đầy đủ chỉ khi có trạng thái kéo dài (tồn kho cạn dần,
   khách quay lại, đối thủ phản ứng).
2. **Reward**: lợi nhuận, không phải doanh thu (agent sẽ bán lỗ để tăng doanh thu); phạt biến động giá và vi phạm luật, cam kết; đo
   thêm chỉ số dài hạn (khách quay lại) vì agent tối ưu ngắn hạn sẽ ăn mòn chúng.
3. **Không thử sai trên khách thật từ đầu.** Học offline từ log giá lịch sử (offline RL, off-policy evaluation như importance
   sampling, doubly robust) hoặc dựng simulator nhu cầu từ dữ liệu; policy mới chỉ được thử trong vùng giá an toàn quanh giá hiện tại
   (trust region theo nghĩa nghiệp vụ).
4. **Triển khai**: A/B test theo phần trăm traffic hoặc theo nhóm sản phẩm, guardrail cứng (giá sàn, giá trần, tốc độ đổi giá), kill
   switch, giám sát drift của nhu cầu.
5. **Baseline**: luật giá hiện tại và một mô hình dự báo nhu cầu + tối ưu hoá. RL phải thắng chúng trên metric kinh doanh, không phải
   trên reward của chính nó.

## Case: bạn được giao làm agent chơi một game mới cho một studio, có simulator nhưng mỗi ván mất 2 phút thời gian thực. Lên kế hoạch.

- **Chi phí mẫu là ràng buộc chính.** 2 phút mỗi ván, 1 triệu ván là 4 năm: cần chạy song song nhiều instance (vector env, nhiều máy),
  tăng tốc simulator (headless, bỏ render, chạy nhanh hơn thời gian thực), và chọn thuật toán dùng mẫu hiệu quả (off-policy có replay
  như DQN/SAC, hoặc PPO với nhiều env song song nếu simulator rẻ khi song song hoá).
- **Observation và action**: dùng trạng thái nội bộ của game (vị trí, máu) nếu studio cho, thay vì pixel: nhỏ hơn hàng nghìn lần, học
  nhanh hơn nhiều. Pixel chỉ khi bắt buộc (khi đó tiền xử lý kiểu Atari: xám, thu nhỏ, chồng khung, frame skip).
- **Reward**: điểm game thưa thì cần shaping cẩn thận (tiến độ, sống sót) và xem video thường xuyên để bắt hành vi khai thác lỗi game.
  Curriculum: bắt đầu từ màn dễ hoặc trạng thái gần đích.
- **Tái lập và đánh giá**: seed cho simulator, bộ màn chơi đánh giá cố định, 3 tới 5 seed train, checkpoint theo eval định kỳ, đo
  wall-clock và số ván.
- **Bắt đầu nhỏ**: dựng toàn bộ pipeline với PPO của thư viện chuẩn trên một màn rút gọn để có baseline trong vài giờ, rồi mới tối ưu.
  Code tự viết chỉ đáng khi cần thứ thư viện không có, và phải qua test so với thư viện trên một env chuẩn.
