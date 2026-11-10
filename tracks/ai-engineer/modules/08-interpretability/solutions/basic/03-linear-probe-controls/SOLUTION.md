# Lời giải: linear probe có đối chứng

## Cách làm

**`group_split`.** `np.unique(groups)` (đã sắp tăng), hoán vị bằng `default_rng(seed).permutation`, `round(test_frac * n)` nhóm
đầu vào test, `np.isin` đổi nhóm thành mặt nạ mẫu, `np.flatnonzero` trả chỉ số tăng dần. Lý do: token trong cùng một câu chia sẻ
ngữ cảnh, chủ đề, thậm chí chính các token đó; chia ngẫu nhiên theo token để cùng một câu nằm ở cả hai phía, và probe được chấm
trên thứ nó đã thấy gần như nguyên vẹn. Test cuối dựng đúng tình huống đó: nhãn chỉ gắn với nhóm, probe học thuộc train trên 0.9
nhưng không đoán được test khi chia theo nhóm.

**`standardize`.** Mean và std của train áp cho cả test. Tính trên toàn bộ dữ liệu là rò rỉ nhỏ nhưng có thật (test ảnh hưởng tới
phép biến đổi), và ở dữ liệu nhỏ có thể đổi kết luận.

**`train_linear_probe`.** `nn.Linear(d, K)`, loss `cross_entropy` trung bình cộng $$\lambda\lVert W\rVert^2$$ (bias không phạt), LBFGS
`strong_wolfe` full batch. Bài toán lồi nên mọi optimizer hội tụ đều ra cùng nghiệm; LBFGS hội tụ trong vài chục vòng, không có lr
để chỉnh. scikit-learn tối thiểu $$\frac12\lVert W\rVert^2 + C\sum_i \ell_i$$; chia cho $$CN$$ được $$\frac{1}{2CN}\lVert W\rVert^2 + \frac1N\sum_i\ell_i$$, nên
$$C = 1/(2\lambda N)$$ cho cùng nghiệm. Test so xác suất tới $$2 \times 10^{-3}$$, đủ để bắt loss tổng thay trung bình, phạt cả bias hay
quên weight decay.

**`control_labels`.** Hewitt & Liang (2019): mỗi **loại** token nhận một nhãn ngẫu nhiên cố định, rút theo phân phối nhãn thật.
Control task giữ nguyên mọi thứ có thể làm probe "ăn gian" (token id, tần suất, tỉ lệ nhãn) nhưng bỏ đi quan hệ ngôn ngữ thật. Probe
đạt cao trên control task là probe đủ mạnh để học thuộc. **Selectivity** = accuracy task − accuracy control.

**`majority_baseline`, `mean_difference_direction`.** Sàn thấp nhất phải vượt, và probe không cần train: hướng nối hai tâm lớp. Probe
diff-in-means kém tối ưu hơn logistic khi các chiều tương quan, nhưng ít overfit và là hướng thường dùng để steering.

## Kiểm bằng gì

Dữ liệu sinh trong test, so với scikit-learn (chỉ trong test) và với bản tham chiếu từng phần tử của thứ tự rút ngẫu nhiên. Cài sai
đã thử và bị bắt: chia theo token, chuẩn hoá trên cả train lẫn test, loss tổng thay trung bình, phạt bias, bỏ weight decay, control
label rút theo từng token thay vì từng loại, control label rút đều thay vì theo phân phối nhãn, majority hoà lấy nhãn lớn nhất,
diff-in-means không chuẩn hoá.

## Bẫy thường gặp

- Báo accuracy probe mà không có baseline: 0.78 nghe tốt cho tới khi thấy chỉ token id đã cho 0.75 (bài Intermediate 01).
- Dùng MLP probe rồi kết luận "model biểu diễn X": probe đủ mạnh tự tính được X từ input. Probe tuyến tính và selectivity giữ câu
  hỏi ở mức "X có giải mã tuyến tính được không".
