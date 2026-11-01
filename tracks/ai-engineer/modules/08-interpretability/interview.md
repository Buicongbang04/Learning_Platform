# Câu hỏi phỏng vấn: Interpretability

## Interpretability của LLM là gì, và một AI Engineer (không phải nhà nghiên cứu) dùng nó vào việc gì?

Là tập phương pháp trả lời "model tính ra kết quả này **bằng cách nào**" từ bên trong (activation, trọng số), thay vì chỉ nhìn
input/output. Có ba tầng câu hỏi, mỗi tầng một loại bằng chứng:

| Tầng | Câu hỏi | Phương pháp | Loại bằng chứng |
| --- | --- | --- | --- |
| Đọc | Thông tin X có trong activation không? | probe, attention pattern, logit lens | tương quan |
| Can thiệp | Thành phần này có **cần**, có **đủ** cho hành vi không? | ablation, activation patching | nhân quả, trên phân phối đã thử |
| Phân rã | Activation gồm những "đặc trưng" nào? | sparse autoencoder, transcoder | mô tả, cần kiểm bằng can thiệp |

Việc thực tế: gỡ lỗi model (vì sao fine-tune làm hỏng một khả năng, model dựa vào shortcut nào), giám sát rẻ bằng probe trên
activation (phát hiện prompt độc hại, câu trả lời không chắc chắn), steering (cộng một vector vào residual stream để đổi hành vi),
so hai model trước/sau fine-tune, và trả lời câu hỏi của khách hàng/kiểm toán một cách có căn cứ. Ứng viên tốt nói thêm giới hạn:
phần lớn kết quả mới đúng cho model nhỏ và hành vi hẹp; "giải thích được cả model" chưa ai làm được.

## Vì sao "residual stream" là cách nhìn trung tâm của mechanistic interpretability?

Với Transformer pre-norm, mỗi sublayer **đọc** một bản đã chuẩn hoá của stream và **cộng** kết quả vào stream:

$$
x_L = e_{tok} + e_{pos} + \sum_{l=0}^{L-1}\big(\mathrm{attn}_l + \mathrm{mlp}_l\big)
$$

Hệ quả: stream cuối là **tổng** các đóng góp, nên tách được theo thành phần (direct logit attribution), đọc được ở giữa chừng
bằng cùng unembedding (logit lens), và thay được từng phần (patching một sublayer, một head). Stream giống một "bus" chung: một
head ghi thông tin vào một không gian con, head ở tầng sau đọc từ đó (composition). Post-norm phá tính cộng thuần này vì LayerNorm
nằm trên đường residual.

Bẫy thường gặp khi cài: lấy nhầm stream sau LayerNorm (output của `ln1`) làm residual, hoặc quên rằng LayerNorm cuối không tuyến
tính (DLA phải giữ cố định thang của nó và chỉ là xấp xỉ khi diễn giải).

## Một linear probe trên tầng 6 đạt 95% accuracy cho thuộc tính X. Bạn hỏi lại những gì trước khi tin?

1. **Baseline**: majority bao nhiêu? Probe trên embedding (tầng 0) bao nhiêu? Một bảng tra chỉ dùng token id bao nhiêu? Nhiều thuộc
   tính đoán được phần lớn từ chính token.
2. **Control task** (Hewitt & Liang): gán nhãn ngẫu nhiên cố định cho mỗi loại token rồi train probe y hệt; **selectivity** = task −
   control. Probe đủ mạnh để học thuộc thì 95% không nói gì.
3. **Model khởi tạo ngẫu nhiên**: cùng kiến trúc, chưa train. Nếu nó cũng 93% thì thông tin đến từ kiến trúc/input, không phải học.
4. **Rò rỉ dữ liệu**: chia train/test theo câu/văn bản hay theo token? Chuẩn hoá bằng thống kê của train hay của cả tập?
5. **Độ bất định**: test bao nhiêu mẫu, khoảng tin cậy, đổi seed chia dữ liệu thì lệch bao nhiêu?
6. **Probe tuyến tính hay MLP**: MLP probe có thể tự tính X.

Và câu quan trọng nhất: probe chỉ chứng minh X **giải mã được tuyến tính**, không chứng minh model **dùng** X. Muốn nói "dùng" phải
can thiệp: xoá hướng đó (INLP, amnesic probing, LEACE) hoặc steering theo hướng đó rồi đo hành vi.

## Attention weight có phải là lời giải thích cho quyết định của model không?

Không, ít nhất không một mình. Ba lý do:

- Attention cao vào vị trí j không có nghĩa thông tin từ j quan trọng: output của head là $$\sum_j a_{ij} v_j W_O$$, nếu $$\lVert v_j W_O\rVert$$
  nhỏ thì đóng góp nhỏ. Nhiều head đổ attention vào token đầu ("attention sink") như một chỗ "không làm gì".
- Có nhiều head, nhiều tầng; thông tin đã trộn qua các tầng trước nên "vị trí j" ở tầng 8 không còn là "token j" của input.
- Jain & Wallace (2019) cho thấy có thể đổi attention mà output gần như không đổi trên một số tác vụ phân loại.

Dùng attention pattern để **sinh giả thuyết** (head này trông giống previous-token head), rồi kiểm bằng ablation hoặc patching. Điểm
attention có cấu trúc (previous-token, induction trên dãy lặp lại ngẫu nhiên) là phép đo hành vi của head trên phân phối kiểm soát
được, đáng tin hơn nhìn pattern trên vài câu.

## Induction head là gì? Đo và kiểm nó thế nào?

Một mạch hai head thực hiện "[A][B] ... [A] → [B]": thấy token hiện tại đã xuất hiện, đoán token đứng sau lần xuất hiện trước.

1. Một **previous-token head** ở tầng sớm ghi vào mỗi vị trí "token trước tôi là gì".
2. Một **induction head** ở tầng sau dùng query "tôi là A" so với key "token trước tôi là A" (key được tạo nhờ head bước 1: gọi là
   K-composition), nên nhìn vào vị trí ngay **sau** A cũ, và chép token B ở đó qua OV circuit.

Đo: dãy `[BOS] + r + r` với `r` ngẫu nhiên; điểm induction là attention trung bình từ vị trí t ở nửa sau tới t − half + 1. Kiểm nhân
quả: mean-ablate các head điểm cao, loss trên nửa sau phải vọt lên còn loss nửa đầu không đổi, và tắt cùng số head ngẫu nhiên thì
không. Olsson và cộng sự (2022) cho thấy induction head xuất hiện đột ngột trong train (phase change) cùng lúc với khả năng in-context
learning tăng vọt, nên đây là một cơ chế nền của ICL, dù không phải toàn bộ.

## Zero ablation, mean ablation, resample ablation khác nhau thế nào? Chọn cái nào?

| Cách | Thay activation bằng | Ưu | Nhược |
| --- | --- | --- | --- |
| Zero | 0 | đơn giản | 0 thường nằm ngoài phân phối: model hỏng vì "lạ", không chỉ vì "thiếu"; có thể làm hỏng cả hành vi không liên quan |
| Mean | trung bình trên một tập tham chiếu | giữ thang và hướng trung bình | xoá cả thông tin chung của mọi input; phụ thuộc tập tham chiếu |
| Resample | activation của một input khác (ngẫu nhiên) | đúng phân phối nhất, là nền của causal scrubbing | nhiễu, cần lấy trung bình nhiều lần |

Mặc định chọn mean hoặc resample, báo cáo kèm phép kiểm "phần không liên quan có đổi không" (ví dụ loss nửa đầu của dãy lặp lại).
Luôn so với ablation cùng số thành phần ngẫu nhiên. Và nhớ: các head có thể dự phòng cho nhau, nên tắt một head "không ảnh hưởng"
không chứng minh head đó vô dụng.

## Logit lens là gì? Vì sao phải áp LayerNorm cuối, và tuned lens sửa được gì?

Logit lens (nostalgebraist, 2020) đọc residual stream ở tầng giữa bằng chính đường ra của model: $$\mathrm{softmax}(W_U\,\mathrm{LN}_f(x_l))$$.
Nó cho thấy dự đoán hình thành dần qua các tầng. Phải áp `ln_f` vì unembedding được train để đọc stream **đã chuẩn hoá**: stream giữa
chừng có norm khác hẳn (thường tăng theo tầng, có vài chiều cực lớn), bỏ `ln_f` thì logits sai thang và lệch hướng, cross-entropy vô
nghĩa.

Giới hạn: lens giả định các tầng giữa dùng **cùng hệ toạ độ** với tầng cuối. Với nhiều model (GPT-Neo, Pythia, BLOOM) lens ở tầng sớm
cho rác dù thông tin có ở đó. **Tuned lens** (Belrose và cộng sự, 2023) học thêm một phép biến đổi affine riêng cho mỗi tầng, tối
thiểu KL tới phân phối cuối, nên đọc tầng sớm tốt hơn hẳn. Cả hai vẫn là phép **đọc** (tương quan), không chứng minh tầng đó "quyết
định" gì.

## Mô tả một thí nghiệm activation patching đúng cách. Những lựa chọn nào làm kết quả sai lệch?

1. Cặp prompt **clean** / **corrupted** giống nhau tối đa, khác ở đúng chỗ ta muốn khảo (ví dụ một tên), cùng độ dài token.
2. **Thước đo** tuyến tính, không bão hoà: logit difference giữa đáp án đúng và đáp án của run corrupted. Chuẩn hoá về 0 (corrupted)
   và 1 (clean).
3. **Denoising**: chạy corrupted, thay một activation bằng giá trị clean: "thành phần này đủ để khôi phục không?". **Noising**:
   ngược lại: "thành phần này có cần không?". Hai câu hỏi khác nhau, nên làm cả hai.
4. Độ mịn: residual theo (tầng, vị trí) để thấy thông tin đi đâu; rồi sublayer, head; rồi path patching để tách đường trực tiếp
   khỏi đường qua head khác.

Sai lệch hay gặp: corruption ngoài phân phối (nhiễu Gaussian lên embedding như causal tracing của ROME có thể tạo kết luận khác so với
thay token), thước đo xác suất (bão hoà), chỉ một template prompt, không báo độ bất định, và self-repair: patch một head làm head
phía sau bù lại, nên hiệu ứng từng head không cộng lại thành hiệu ứng cả nhóm. Khi có hàng nghìn thành phần, **attribution patching**
xấp xỉ hiệu ứng bằng gradient $$(a_{clean} - a_{corrupt}) \cdot \nabla_a m$$ chỉ với hai lần forward và một lần backward, rồi patch thật
những ứng viên hàng đầu.

## Superposition là gì, và sparse autoencoder giải quyết nó ra sao?

Model biểu diễn **nhiều đặc trưng hơn số chiều** bằng cách đặt chúng theo các hướng gần trực giao; khi đặc trưng thưa (ít khi cùng bật),
nhiễu giao thoa nhỏ và đáng đổi lấy dung lượng (Elhage và cộng sự, 2022). Hệ quả: một neuron hay một chiều bật cho nhiều khái niệm
không liên quan (polysemantic), nên đọc từng neuron không hiệu quả.

SAE học một từ điển $$W_{dec}$$ có $$m \gg d$$ hàng, mỗi activation được tái dựng bằng ít hàng: $$\hat x = f(x)W_{dec} + b_{dec}$$ với $$f$$ thưa.
Độ thưa đến từ phạt L1 (nhân norm hàng decoder để không ăn gian bằng cách thu nhỏ $$f$$ và phóng to decoder) hoặc từ TopK (giữ đúng
k latent lớn nhất; Gao và cộng sự 2024: dễ chỉnh hơn, ít latent chết hơn khi kết hợp kỹ thuật phụ, đánh đổi tái dựng/độ thưa tốt
hơn). Hi vọng: mỗi latent ứng với một đặc trưng đơn nghĩa, đọc được bằng ví dụ kích hoạt mạnh nhất và can thiệp được.

## Bạn đánh giá một SAE thế nào? Báo cáo "SAE khôi phục 97% loss" cần hỏi lại gì?

Ba trục, luôn báo cùng nhau:

- **Tái dựng**: FVU (fraction of variance unexplained) so với phương sai **quanh trung bình**.
- **Độ thưa**: L0 trung bình; tỉ lệ latent **chết** (không bật trên một tập lớn) và latent bật quá dày.
- **Trung thành với model**: ghép SAE vào chỗ activation, đo cross-entropy; "loss recovered" =
  $$\frac{CE_{abl} - CE_{SAE}}{CE_{abl} - CE_{gốc}}$$.

Câu hỏi lại cho "97%": baseline ablation là zero hay mean (zero ablation residual stream làm $$CE_{abl}$$ rất tệ nên tỉ lệ đẹp hơn
nhiều)? L0 bao nhiêu (so FVU mà không so L0 là vô nghĩa)? Đo trên dữ liệu nào, có tách khỏi dữ liệu train SAE không? Vị trí đầu
(attention sink, norm cực lớn) có bị loại không? Và CE tăng tuyệt đối bao nhiêu nat: 0.1 nat trên một tầng là đáng kể nếu ghép SAE
ở nhiều tầng cùng lúc. Cuối cùng, diễn giải latent bằng top activation dễ thiên lệch: phải xem cả mức kích hoạt yếu, kiểm bằng can
thiệp, và biết các hiện tượng feature splitting, feature absorption.

## Case: model phân loại đơn xin vay của ngân hàng bị nghi dựa vào tên hoặc quê quán người nộp. Bạn dùng interpretability thế nào để kiểm, và kết luận được tới đâu?

Bắt đầu bằng **hành vi**, rẻ và có sức thuyết phục nhất: tập counterfactual chỉ đổi tên/quê quán (giữ nguyên mọi trường khác), đo
chênh lệch điểm; đây đã là một phép patching ở mức input. Nếu có chênh lệch:

1. **Patching** từ bản counterfactual vào bản gốc theo (tầng, vị trí) để biết thông tin tên đi vào quyết định qua đâu; theo head/MLP
   để khoanh thành phần.
2. **Probe** thuộc tính được bảo vệ (vùng miền) ở các tầng, có control task và baseline; nếu giải mã được mạnh, thử **xoá** hướng đó
   (LEACE/INLP) rồi đo lại cả accuracy và chênh lệch counterfactual.
3. Nếu có SAE cho model, tìm latent bật theo tên/vùng miền và kiểm bằng ablation latent.

Kết luận được: "trên tập counterfactual này, đổi tên làm điểm lệch X, đi qua các thành phần Y; xoá hướng Z giảm chênh lệch còn W
với chi phí accuracy V". Không kết luận được: model "không còn thiên lệch" nói chung (proxy khác như trường học, số điện thoại vẫn có
thể mang thông tin). Về quy trình: báo cáo cho pháp chế/rủi ro kèm giới hạn, và sửa ở dữ liệu/đặc trưng đầu vào thường bền hơn sửa
trong activation.

## Case: thiết kế hệ thống giám sát dùng probe trên activation để phát hiện prompt độc hại (jailbreak) cho một LLM tự host. So với một classifier trên văn bản riêng?

Thiết kế:

- **Hook** residual stream ở vài tầng giữa (chọn bằng thí nghiệm probe theo tầng) trong chính lần forward phục vụ người dùng: chi phí
  thêm chỉ là một phép nhân vector, không thêm lần gọi model.
- **Dữ liệu**: prompt độc hại/lành tính có nhãn, chia theo nguồn/chiến dịch tấn công (không theo câu) để đo tổng quát hoá sang kiểu
  tấn công mới; có tập "khó" (lành tính nhưng nhạy cảm) để đo false positive.
- **Probe** tuyến tính hoặc diff-in-means trên activation trung bình theo token (hoặc token cuối); hiệu chỉnh ngưỡng theo chi phí lỗi;
  log điểm để theo dõi drift.
- **Vận hành**: khi đổi checkpoint (fine-tune, quantize) phải train lại probe, vì hệ toạ độ activation đổi; giữ classifier văn bản
  làm lớp thứ hai.

So sánh: probe rẻ, dùng được "hiểu biết" của chính model, nghiên cứu cho thấy probe đơn giản bắt được nhiều hành vi khó thấy từ văn
bản; nhưng gắn chặt với một checkpoint, khó giải thích cho người vận hành, và kẻ tấn công biết probe có thể tối ưu để né (adversarial
trên activation). Classifier văn bản độc lập với model, dễ cập nhật, dễ kiểm định, nhưng tốn thêm một model và không thấy trạng thái
bên trong. Thực tế dùng cả hai, đo cả recall trên tấn công mới lẫn false positive trên câu hỏi nhạy cảm hợp lệ.

## Steering vector (activation addition) là gì? Rủi ro khi dùng trong sản phẩm?

Lấy hiệu trung bình activation giữa hai tập prompt đối lập (ví dụ "trả lời lịch sự" và "trả lời cộc lốc"), hoặc một hướng probe/latent
SAE, rồi **cộng** $$\alpha v$$ vào residual stream ở một tầng khi sinh. Không cần train, đổi được phong cách, chủ đề, mức từ chối
(Turner và cộng sự 2023; representation engineering của Zou và cộng sự 2023).

Rủi ro: $$\alpha$$ lớn làm hỏng chất lượng chung (đo perplexity, benchmark), hiệu ứng phụ khó lường trên chủ đề khác, không bền qua các
phiên bản model, và có thể bị dùng để gỡ guardrail (hướng "từ chối" trong model mở bị xoá để jailbreak). Trong sản phẩm, steering là
một tham số cần A/B test và eval hồi quy như mọi thay đổi model, không phải công tắc miễn phí.

## Khi nào bạn dùng TransformerLens hoặc nnsight thay vì tự viết hook, và khi nào interpretability không đáng làm?

Tự viết hook (như module này) để hiểu chính xác mỗi tensor nằm đâu, và khi model không được thư viện hỗ trợ. Dùng thư viện khi làm
thật: **TransformerLens** chuẩn hoá tên hook, gộp LayerNorm, có sẵn nhiều model nhỏ; **nnsight** can thiệp model Hugging Face bất kỳ,
chạy được từ xa với model lớn; **SAELens** và **Neuronpedia** cho SAE đã train sẵn và dashboard latent. Luôn kiểm thư viện bằng phép
thử tổng quát (logits khi nạp phải khớp model gốc; tổng các thành phần bằng stream cuối).

Không đáng làm khi câu hỏi trả lời được bằng eval hành vi (tập kiểm, counterfactual), khi model là API đóng (không có activation),
khi quyết định không đổi dù kết quả thế nào, hoặc khi đội không có thời gian làm đủ đối chứng: một kết quả interpretability thiếu
đối chứng dễ gây tự tin sai hơn là không có gì.
