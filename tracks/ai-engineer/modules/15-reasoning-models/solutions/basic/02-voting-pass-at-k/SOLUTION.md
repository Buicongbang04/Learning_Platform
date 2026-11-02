# Lời giải: self-consistency, best-of-N, pass@k

## Cách làm

`weighted_vote` cộng trọng số vào một `dict` theo thứ tự duyệt, bỏ `None`. `dict` giữ thứ tự chèn, nên "đáp số xuất
hiện sớm nhất trong các đáp số có tổng lớn nhất" là khoá **đầu tiên** đạt giá trị lớn nhất. `majority_vote` là
`weighted_vote` với mọi trọng số bằng 1. Quy tắc hoà phải **tất định** và không phụ thuộc giá trị đáp số: dùng
`max(sorted(...))` thì hoà nghiêng về đáp số có chuỗi lớn hơn, một thiên vị nhỏ nhưng có thật khi k chẵn.

`best_of_n` chọn chỉ số có `(điểm, -chỉ số)` lớn nhất: điểm cao nhất, hoà thì lời giải đứng trước. Nếu lời giải được
verifier chấm cao nhất không có đáp số, kết quả là `None`: đừng lén lùi về lời giải kế tiếp, vì như thế là đổi verifier
mà không nói.

`pass_at_k` dùng dạng tích của Chen và cộng sự (2021):

$$
\frac{\binom{n-c}{k}}{\binom{n}{k}} = \prod_{i=n-c+1}^{n}\left(1 - \frac{k}{i}\right)
$$

Mỗi thừa số trong (0, 1], không có giai thừa lớn nên không tràn số. Khi `n - c < k`, mọi tập k lời giải đều chứa ít nhất
một lời giải đúng: trả 1.0.

`maj_at_k` chia n lời giải thành `n // k` khối liên tiếp. Vì các lời giải được lấy mẫu độc lập cùng phân phối, mỗi khối
là một lần "chạy self-consistency với k mẫu"; trung bình các khối giảm phương sai so với chỉ dùng k lời giải đầu, mà
không cần trộn ngẫu nhiên (kết quả tất định, test được).

## Vì sao không dùng công thức "có hoàn lại"

$$1 - (1 - c/n)^k$$ coi k lần rút là độc lập có hoàn lại. Với n = 4, c = 2, k = 2 nó cho 0.75, trong khi rút 2 lời giải
**khác nhau** từ 4 thì xác suất có ít nhất một lời giải đúng là 5/6. Công thức có hoàn lại luôn thấp hơn, và chệch nhiều
nhất đúng ở chỗ cần đo: k gần n.

## maj@k và pass@k đo hai thứ khác nhau

- **pass@k** (coverage) là trần của mọi cách chọn: nếu có một verifier hoàn hảo (với toán là so đáp án, với code là chạy
  test) thì best-of-k đạt đúng pass@k. Nó tăng đơn điệu theo k.
- **maj@k** là thứ bạn đạt được **không** cần verifier. Nó chỉ tăng khi đáp án đúng là đáp án phổ biến nhất; câu hỏi mà
  model sai "một cách nhất quán" thì bỏ phiếu càng nhiều càng chắc sai. Test cuối mô phỏng trường hợp thuận lợi: đúng
  45%, sai phân tán, nên maj@16 gần 1.
- Khoảng cách giữa hai đường cong là giá trị tối đa mà một verifier tốt hơn (hay một reward model) có thể mang lại. Bài
  Intermediate 01 đo khoảng cách đó trên Qwen2.5-0.5B.

## Bẫy thường gặp

- Tính `None` là một phiếu: câu trả lời bị cắt cụt nhiều thì "None" thắng.
- Hoà lấy theo `Counter.most_common`: Python giữ thứ tự gặp đầu, nhưng code dễ đổi sang `sorted` mà không biết.
- So maj@k của k = 1 với greedy: một mẫu ở temperature 0.7 thường **kém hơn** greedy. Self-consistency phải thắng
  greedy, không chỉ thắng một mẫu.
