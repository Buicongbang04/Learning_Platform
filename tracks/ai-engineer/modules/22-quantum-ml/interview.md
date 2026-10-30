# Câu hỏi phỏng vấn: Quantum Machine Learning

## Giải thích qubit và superposition cho một kỹ sư không biết vật lý, không dùng ẩn dụ "vừa 0 vừa 1".

Một qubit là một vector đơn vị $$(\alpha, \beta)$$ trong $$\mathbb{C}^2$$. Đo nó cho 0 với xác suất $$|\alpha|^2$$ và 1 với xác suất $$|\beta|^2$$
(Born rule), rồi trạng thái thành đúng kết quả vừa đo. "Superposition" chỉ có nghĩa là cả hai thành phần khác 0. Khác với
một bit ngẫu nhiên, các thành phần là số phức có **pha**, và gate (ma trận unitary) làm các pha này giao thoa: hai trạng
thái cho cùng phân phối 50/50 khi đo ngay, như $$\frac{|0\rangle + |1\rangle}{\sqrt 2}$$ và $$\frac{|0\rangle - |1\rangle}{\sqrt 2}$$, sau một Hadamard lại cho $$|0\rangle$$ và
$$|1\rangle$$ chắc chắn. Một phân phối xác suất cổ điển không làm được điều đó vì xác suất không âm, không triệt tiêu nhau.

Với $$n$$ qubit, vector có $$2^n$$ thành phần, nhưng mỗi lần đo chỉ đọc ra $$n$$ bit. Đó là lý do "máy lượng tử thử mọi đáp án
song song" là sai: bạn không đọc được mọi đáp án, chỉ lấy mẫu một chuỗi bit từ phân phối mà thuật toán đã khéo léo dồn
xác suất vào đáp án đúng.

## Vì sao mô phỏng máy lượng tử trên máy cổ điển lại khó? Có phải mọi mạch đều khó mô phỏng?

Simulator statevector lưu $$2^n$$ biên độ phức: 30 qubit là 16 GB, 50 qubit là 16 PB. Mỗi gate tốn $$O(2^n)$$ nếu áp vào đúng trục
tensor (dựng ma trận $$2^n \times 2^n$$ bằng Kronecker là sai lầm hay gặp, tốn $$O(4^n)$$).

Nhưng không phải mạch nào cũng khó. Mạch không có gate hai qubit là $$n$$ hệ $$2 \times 2$$ độc lập. Mạch ít entanglement (Schmidt
rank nhỏ qua mọi lát cắt) nén được bằng tensor network / MPS. Mạch chỉ gồm gate Clifford (H, S, CNOT) mô phỏng được trong
thời gian đa thức (định lý Gottesman–Knill). Nhiều khẳng định "lợi thế lượng tử" đã bị bác bỏ bằng các simulator thông minh
như vậy. Khi đánh giá một mô hình QML, câu hỏi đầu tiên là: mạch này có mô phỏng cổ điển hiệu quả được không? Nếu có, mọi
lợi thế (nếu có) là của mô hình, không phải của phần cứng lượng tử.

## Entanglement là gì, đo nó thế nào? Nó có cho phép truyền thông tin nhanh hơn ánh sáng không?

Trạng thái của hai nhóm qubit A, B là entangled khi không viết được thành $$|a\rangle \otimes |b\rangle$$. Xếp biên độ thành ma trận
$$2^{n_A} \times 2^{n_B}$$ thì "là tích" tương đương "ma trận có hạng 1". SVD của ma trận đó cho hệ số Schmidt $$\lambda_k$$; entanglement
entropy $$-\sum \lambda_k^2 \log_2 \lambda_k^2$$ bằng 0 cho trạng thái tích và 1 bit cho Bell state.

Không truyền được thông tin: phân phối biên của mỗi bên không phụ thuộc bên kia làm gì (với Bell state luôn là 50/50). Tương
quan chỉ thấy được khi đem hai bảng kết quả so với nhau, việc cần kênh cổ điển. Với ML, entanglement là điều kiện cần để mô
hình lượng tử khác mô hình cổ điển một cách đáng kể, nhưng không đủ: Bowles et al. (2024) thấy bỏ entanglement khỏi nhiều mô
hình QML phổ biến không làm chúng kém đi.

## Parameter-shift rule là gì, vì sao không dùng sai phân hữu hạn hay backprop?

Với gate $$e^{-i\theta P/2}$$ ($$P$$ là tích Pauli), kỳ vọng đo được là $$a + b\cos\theta + c\sin\theta$$ theo từng tham số, nên
$$f'(\theta) = \frac{f(\theta+s) - f(\theta-s)}{2\sin s}$$ **chính xác**, thường dùng $$s = \pi/2$$.

- **Sai phân hữu hạn** cần $$\varepsilon$$ nhỏ, nhưng mỗi $$f$$ chỉ ước lượng được từ shots với sai số cỡ $$1/\sqrt{S}$$; chia cho $$2\varepsilon$$ khuếch
  đại nhiễu. Trong module, 1000 shots, $$\varepsilon = 10^{-2}$$: độ lệch chuẩn của gradient 1.65, so với 0.015 của parameter-shift.
- **Backprop** cần giữ và đọc trạng thái trung gian, việc không làm được trên phần cứng (đo phá trạng thái). Trên simulator thì
  được (PennyLane `diff_method="backprop"`) và nhanh hơn nhiều.

Cái giá: $$2P$$ lần chạy mạch cho $$P$$ tham số, mỗi mẫu dữ liệu, mỗi lần nhiều shots. Gate có generator nhiều trị riêng (vd.
controlled rotation) cần luật shift tổng quát với nhiều điểm hơn.

## Data re-uploading là gì và vì sao nó quan trọng?

Nạp input $$x$$ bằng một gate quay $$e^{-ixP/2}$$ chỉ cho mô hình là hàm bậc 1 của $$x$$: $$a + b\cos x + c\sin x$$. Lặp lại khối "encode rồi
layer có tham số" $$L$$ lần cho chuỗi Fourier tới tần số $$L$$ (Schuld, Sweke, Meyer 2021). Số lần nạp đóng vai trò độ rộng/độ
sâu của mạng. Trong module, mạch 2 qubit trên moons: 1 layer đạt 0.62 test, 4 layer 0.98 (một lần chia), vì moons cần
ranh giới cong. Cũng phải để ý light cone: với 1 layer và đo $$Z_0$$, wire 1 không ảnh hưởng gì tới output, nên mô hình chỉ
thấy $$x_0$$.

## Quantum kernel là gì? Nó khác variational classifier ở đâu?

Dùng mạch làm feature map cố định $$x \mapsto |\varphi(x)\rangle$$, kernel $$k(x, x') = |\langle\varphi(x)|\varphi(x')\rangle|^2$$, rồi train SVM cổ điển với
`kernel="precomputed"`. Không có tham số trong mạch nên không có barren plateau, bài toán tối ưu lồi. Trên phần cứng, mỗi
phần tử là xác suất ra toàn 0 của mạch $$U(x')^\dagger U(x)$$, ước lượng bằng shots; ma trận train $$N \times N$$ cần $$N(N-1)/2$$ mạch, nên
không dùng được cho tập lớn (10 740 mạch cho một fold Iris 120/30).

VQC train tham số bằng gradient, rẻ hơn khi dự đoán (một mạch mỗi mẫu) nhưng tối ưu không lồi và có thể gặp plateau.
Schuld (2021) chỉ ra nhiều VQC thực chất là mô hình kernel với kernel do encoding quyết định, nên câu hỏi "encoding nào"
quan trọng hơn "ansatz nào".

## Kernel concentration là gì? Bạn phát hiện và xử lý thế nào?

Với feature map biểu cảm trên nhiều qubit, hai điểm bất kỳ gần như trực giao: các phần tử ngoài đường chéo tập trung quanh
một giá trị nhỏ với độ lệch giảm theo hàm mũ của số qubit (Thanasilp et al. 2022). Kernel thành gần ma trận đơn vị, SVM
thuộc lòng train. Trong module, breast cancer, scale 1.0: trung bình ngoài đường chéo 0.546 ở 2 qubit, 0.058 ở 10 qubit;
train accuracy 0.899 lên 0.993, test 0.888 xuống 0.819.

Phát hiện: in phân phối phần tử ngoài đường chéo (mean, std), so train và test accuracy, đo kernel-target alignment. Xử
lý: giảm bandwidth (scale input) như chỉnh $$\gamma$$ của RBF, dùng kernel "projected" lên vài qubit, ít layer encoding hơn.
Lưu ý: khi đã chỉnh để kernel hết co, nó thường gần một kernel trơn mà phương pháp cổ điển cũng làm được. Trên phần cứng
thì tệ hơn: phân biệt giá trị kernel nhỏ cần số shots tăng theo bình phương nghịch đảo.

## Barren plateau là gì? Những yếu tố nào gây ra nó?

Phương sai của gradient theo tham số, lấy trên khởi tạo ngẫu nhiên, giảm theo hàm mũ của số qubit: landscape gần như
phẳng, cần số shots hàm mũ chỉ để biết đi hướng nào (McClean et al. 2018). Nguyên nhân đã biết:

- **Ansatz quá biểu cảm** (đủ sâu để gần một 2-design ngẫu nhiên).
- **Cost global** (quan sát trên mọi qubit): trong module, $$\langle Z_0 \cdots Z_{n-1}\rangle$$ có phương sai gradient giảm khoảng một nửa mỗi qubit
  thêm, kể cả mạch 1 layer; cost local $$\langle Z_0 \rangle$$ với mạch nông gần như không đổi (Cerezo et al. 2021).
- **Entanglement quá mức** giữa phần nhìn thấy và phần ẩn, và **nhiễu**: depolarizing đủ sâu làm mọi trạng thái tiến về hỗn
  hợp hoàn toàn, gradient về 0 (Wang et al. 2021).

Biện pháp: cost local, mạch nông, khởi tạo có cấu trúc (gần identity), kiến trúc có inductive bias. Cerezo et al. (2023)
đặt ra câu hỏi khó chịu: nhiều kiến trúc chứng minh được là không có plateau thì cũng mô phỏng cổ điển hiệu quả được.

## "Dequantization" nghĩa là gì? Cho một ví dụ.

Là tìm một thuật toán cổ điển đạt cùng kết quả với chi phí tương đương thuật toán lượng tử, xoá lợi thế được tuyên bố.
Ví dụ nổi tiếng: Tang (2019) đưa ra thuật toán recommendation cổ điển dùng lấy mẫu theo độ dài hàng (giống giả định truy
cập dữ liệu của bản lượng tử), chỉ chậm hơn đa thức, xoá "tăng tốc hàm mũ" của thuật toán Kerenidis–Prakash.

Ví dụ nhỏ trong module: kernel của angle embedding (mỗi qubit một RY, không entanglement) là tích các kernel một qubit,
mỗi cái có công thức đóng. Tính bằng một dòng numpy cho kết quả khớp simulator tới $$10^{-15}$$, nhanh hơn khoảng 200 lần ở 16
qubit, và vẫn chạy được ở 40 "qubit" mà simulator không bao giờ chạy nổi. Đó là một kernel cổ điển viết dưới dạng mạch.

## Shots ảnh hưởng thế nào tới thiết kế hệ thống QML?

Mỗi kỳ vọng có sai số $$\sqrt{(1 - \langle P\rangle^2)/S}$$, nên sai số giảm 10 lần cần shots tăng 100 lần. Hệ quả:

- **Chi phí**: một bước gradient VQC 16 tham số trên 200 mẫu cần $$33 \times 200$$ mạch, khoảng 6.6 triệu lần đo với 1000 shots.
- **Thuật toán**: gradient là ngẫu nhiên, nên optimizer phải chịu được nhiễu (SGD, Adam với lr nhỏ, hoặc phân bổ shots thích
  nghi); tiêu chí dừng không thể dựa vào "loss không đổi tới $$10^{-6}$$".
- **Đánh giá**: accuracy trên simulator chính xác là trần trên; phải báo kết quả có shots. Trong module, kernel Iris ước lượng
  từ 10 shots cho test 0.900 so với 0.953 khi chính xác.
- **Nhiễu nhân với shots**: depolarizing làm kernel co về một hằng (độ tương phản 0.080 còn 0.036 trong module); bản thân phép
  co gần như không đổi accuracy của SVM, nhưng tín hiệu nhỏ đi thì cần nhiều shots hơn để giữ thứ tự giữa các phần tử.

## NISQ là gì? Error correction thay đổi bức tranh thế nào?

NISQ (Preskill 2018): vài chục tới vài trăm qubit vật lý, gate có lỗi (cỡ $$10^{-3}$$ với gate hai qubit tốt nhất), không sửa lỗi.
Mạch chỉ chạy được tới độ sâu mà lỗi tích luỹ còn chấp nhận được, nên thuật toán phải nông, thường là variational. Error
correction mã hoá một qubit logic vào nhiều qubit vật lý và phát hiện/sửa lỗi liên tục; chỉ có lợi khi lỗi vật lý dưới một
ngưỡng. Google (2024) lần đầu cho thấy lỗi logic giảm khi tăng kích thước surface code. Đó là cột mốc kỹ thuật quan trọng,
nhưng số qubit logic cần cho Shor hay cho các thuật toán QML có tăng tốc chứng minh được còn cách hiện tại vài bậc độ lớn.
Với AI Engineer, thông số đáng theo dõi là số qubit **logic** và tỉ lệ lỗi logic, không phải số qubit vật lý trong thông cáo
báo chí.

## Bạn benchmark một mô hình QML thế nào để kết quả đáng tin?

- **Baseline mạnh và được tuning cùng ngân sách**: SVM RBF, gradient boosting, MLP có chỉnh siêu tham số; không dùng siêu tham
  số mặc định cho bên cổ điển rồi grid search cho bên lượng tử. Trong module, MLP 16 mặc định đạt 0.812 trên moons, MLP 32-32
  đạt 0.968: chọn baseline nào quyết định kết luận.
- **Nhiều lần chia hoặc k-fold, báo mean ± std và khoảng tin cậy của chênh lệch theo cặp** trên cùng fold. Một lần chia 100 điểm
  test có dao động cỡ 2 điểm phần trăm: VQC thắng SVM ở seed 0 (0.98 so với 0.96) nhưng thua trung bình 5 lần chia (0.946 so với 0.968).
- **Ablation**: bỏ entanglement, thay mạch bằng kernel cổ điển tương đương; nếu kết quả không đổi, "quantum" không đóng góp gì.
- **Báo chi phí**: thời gian, số mạch, số shots, và kết quả có nhiễu nếu nhắm phần cứng.
- **Nhiều bộ dữ liệu** và báo cả nơi mô hình thua (Bowles et al. 2024 là mẫu tốt).

## Case: một vendor chào "quantum ML phát hiện gian lận nhanh và chính xác hơn 30%". Bạn đánh giá thế nào?

Tách thành các câu hỏi kiểm chứng được, theo thứ tự rẻ tới đắt:

1. **"Hơn 30%" so với cái gì?** Yêu cầu baseline cụ thể, siêu tham số, chia dữ liệu, metric (accuracy vô nghĩa với gian lận mất
   cân bằng; cần PR-AUC, recall ở precision cố định), số lần chạy và khoảng tin cậy. Rất thường baseline là logistic
   regression mặc định hoặc mô hình cổ điển chưa tuning.
2. **Chạy ở đâu?** Simulator thì "nhanh hơn" không thể đúng: simulator là máy cổ điển chạy chậm hơn theo $$2^n$$. Phần cứng thật thì
   hỏi số qubit, độ sâu mạch, số shots, độ trễ hàng đợi, chi phí mỗi lần dự đoán. Gian lận cần quyết định trong vài chục mili
   giây cho mỗi giao dịch; một quantum kernel cần $$N_{train}$$ mạch cho **mỗi** dự đoán.
3. **Phần lượng tử có cần không?** Yêu cầu ablation: cùng pipeline với kernel cổ điển tương đương, hoặc mạch bỏ entanglement. Mạch
   có mô phỏng cổ điển hiệu quả được không (ít qubit, ít entanglement, chỉ gate một qubit)?
4. **Tự kiểm**: đòi dữ liệu và code để chạy lại trên tập của công ty với baseline của mình (gradient boosting đã tuning), cùng
   fold, báo khoảng tin cậy của chênh lệch.

Kết luận thường là: không đầu tư, ghi lại tiêu chí xem lại (mô hình chạy trên phần cứng thật, thắng baseline tuning ngoài khoảng
tin cậy, chi phí mỗi dự đoán chấp nhận được). Viết memo như bài Advanced: khuyến nghị trước, bằng chứng có số sau.

## Case: CTO muốn "chuẩn bị cho kỷ nguyên lượng tử" với ngân sách R&D nhỏ. Bạn đề xuất kế hoạch gì?

Tách theo mức độ chắc chắn của tác động:

- **Chắc chắn và cấp bách nhất: mật mã.** Máy lượng tử đủ lớn sẽ phá RSA/ECC bằng Shor; dữ liệu bị ghi lại hôm nay có thể bị giải
  mã sau ("harvest now, decrypt later"). Việc đúng là kiểm kê nơi dùng mật mã khoá công khai và lên lộ trình post-quantum
  cryptography theo chuẩn đã công bố. Việc này của team bảo mật, không phải team ML, nhưng là câu trả lời có giá trị nhất.
- **Theo dõi QML với chi phí thấp**: một người dành vài ngày mỗi năm chạy lại một benchmark cố định (dữ liệu nội bộ đã ẩn danh,
  baseline cố định, mã nguồn mở như PennyLane) trên simulator và, nếu rẻ, trên một máy cloud; ghi kết quả vào cùng một bảng để
  thấy xu hướng. Tiêu chí kích hoạt đầu tư lớn hơn phải viết trước: ví dụ mô hình lượng tử thắng baseline tuning ngoài khoảng
  tin cậy trên dữ liệu kiểu của mình, chạy trên phần cứng thật, với chi phí mỗi dự đoán trong ngân sách.
- **Nếu công ty có dữ liệu lượng tử thật** (hoá học, vật liệu, dược): đây là nơi đáng hợp tác với nhóm nghiên cứu, bắt đầu từ
  mô phỏng.
- **Không làm**: mua "nền tảng quantum AI" cho bài toán bảng/văn bản/ảnh, tuyển team lượng tử riêng khi chưa có bài toán phù hợp.

## Một ứng viên nói "quantum ML sẽ thay deep learning trong 5 năm". Bạn phản biện thế nào?

Không phản biện bằng niềm tin ngược lại, mà bằng các rào cản có số: (1) chi phí đọc kết quả bằng shots tăng theo bình phương độ
chính xác; (2) nạp dữ liệu cổ điển vào mạch tốn ít nhất tuyến tính theo kích thước dữ liệu, mỗi lần chạy mạch, không có QRAM
thực tế; (3) barren plateau làm việc train mô hình lớn khó; (4) nhiều mô hình tránh được plateau lại mô phỏng cổ điển được;
(5) benchmark công khai lớn nhất (Bowles et al. 2024) cho thấy baseline cổ điển thường thắng trên dữ liệu cổ điển. Deep learning
thắng nhờ dữ liệu lớn, phần cứng song song rẻ và backprop; QML hiện ngược lại ở cả ba. Điều có thể đúng là QML hữu ích cho
dữ liệu vốn lượng tử, hoặc những bài toán có cấu trúc đại số đặc biệt, và lĩnh vực có thể bất ngờ: vì thế module này "cập nhật
dần", và câu trả lời tốt là nói rõ điều kiện nào sẽ làm bạn đổi ý.
