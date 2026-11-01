# Lời giải: probe thiên lệch counterfactual và WEAT

## Cách làm

**`parse_score`**: `json.loads(reply)[key]` trong `try` bắt `ValueError`, `KeyError`, `TypeError` (`json.JSONDecodeError`
là con của `ValueError`; `TypeError` cho trường hợp JSON là list hay số), rồi loại `bool` **trước** khi kiểm `int` vì
`isinstance(True, int)` là `True`.

**`paired_diffs`** và **`flip_rate`** dùng chung một hàm ghép: lọc hai phía, `set_index(keys)["score"]`, báo lỗi khi khoá
trùng hoặc hai tập khoá khác nhau, `reindex` phía `b` theo thứ tự phía `a`. Ghép theo khoá chứ không theo vị trí dòng:
dữ liệu đọc từ JSONL có thể đổi thứ tự khi chạy tiếp một lần dở.

**`cluster_bootstrap_ci`**: gom giá trị theo cụm (thứ tự `np.unique`), mỗi vòng rút chỉ số cụm có hoàn lại, nối mọi giá trị
của các cụm đã rút rồi lấy trung bình (không lấy trung bình của trung bình cụm, vì các cụm có cỡ khác nhau).

**WEAT**: chuẩn hoá L2 từng dòng, $$s(w) = \overline{\cos(w, A)} - \overline{\cos(w, B)}$$ bằng hai phép nhân ma trận, effect
size chia cho độ lệch chuẩn mẫu của $$s$$ trên $$X \cup Y$$; p-value hoán vị một phía với `(đếm + 1) / (n_perm + 1)` để không
bao giờ ra đúng 0.

## Kết quả thật

PC của track, `qwen2.5:3b`, `temperature` 0, ngày 2026-11-01. Mỗi nhiệm vụ 144 lượt, không lượt nào JSON hỏng, trung vị
0.9 giây mỗi lượt.

**Nhiệm vụ chấm điểm (1 tới 10, ngưỡng mời phỏng vấn 7).** Điểm trung bình theo mức hồ sơ: mạnh 7.75 (7 tới 8), vừa 3.75
(3 tới 4), yếu 1.00. Mọi biến thể của cùng một hồ sơ nhận **đúng cùng một điểm**: 

| So sánh | Δ trung bình [CI 95%] | Flip rate | Tỉ lệ cặp lệch điểm |
| --- | --- | --- | --- |
| nam - nữ (72 cặp) | 0.00 [0.00, 0.00] | 0 | 0 |
| ba cặp quê quán (48 cặp mỗi cặp) | 0.00 [0.00, 0.00] | 0 | 0 |
| tên 1 - tên 2 cùng nhóm (72 cặp) | 0.00 [0.00, 0.00] | 0 | 0 |
| kiểm độ nhạy: mạnh - yếu (48 cặp) | 6.75 [6.25, 7.00] | | 1.00 |

**Nhiệm vụ đề xuất lương (triệu đồng/tháng, ngưỡng 15).** Trung bình theo mức hồ sơ: mạnh 7.2, vừa 6.0, **yếu 24.2** (5
tới 50): model đề xuất 40 tới 50 triệu cho hai hồ sơ yếu (sinh viên cao đẳng kế toán từng bán hàng, hướng dẫn viên du lịch) và 6 tới 8
triệu cho hồ sơ mạnh nhất.

| So sánh | Δ trung bình [CI 95%] | Flip rate | Tỉ lệ cặp lệch |
| --- | --- | --- | --- |
| nam - nữ | -0.46 [-1.71, 0.44] | 0.03 | 0.24 |
| Hà Nội - Nghệ An | 0.19 [-0.10, 0.65] | 0 | 0.06 |
| Hà Nội - Cần Thơ | -2.04 [-5.92, 0.42] | 0.04 | 0.08 |
| Nghệ An - Cần Thơ | -2.23 [-5.98, 0.08] | 0.04 | 0.08 |
| tên 1 - tên 2 cùng nhóm | 0.65 [-0.07, 1.81] | 0.03 | 0.10 |
| kiểm độ nhạy: mạnh - yếu | **-17.0** [-31.4, -2.6] | | 0.81 |

WEAT_RESULTS

## Đọc kết quả

- **Kiểm độ nhạy trước mọi thứ.** Nhiệm vụ chấm điểm qua kiểm độ nhạy rất rõ (mạnh hơn yếu 6.75 điểm, mọi cặp). Nhiệm vụ
  lương **trượt** kiểm độ nhạy: hồ sơ yếu được đề xuất lương **cao hơn** hồ sơ mạnh trung bình 17 triệu. Một probe mà
  model không phân biệt được ứng viên giỏi với ứng viên không liên quan thì mọi "chênh lệch theo nhóm" của nó là nhiễu
  của một hàm hỏng, không phải thiên lệch. Các Δ quê quán khoảng 2 triệu ở bảng lương đều đến từ vài hồ sơ yếu nơi model
  nhảy giữa 6 và 40 triệu; khoảng tin cậy chứa 0, và sàn nhiễu đổi tên cùng nhóm (10% cặp lệch) cùng cỡ với chênh lệch
  giới tính (24% cặp lệch nhưng Δ trung bình -0.46, CI chứa 0).
- **Chấm điểm: không thấy thiên lệch, và đó là một kết luận có giới hạn.** Ở `temperature` 0 với prompt này, `qwen2.5:3b`
  bỏ qua hoàn toàn tên, giới tính, quê quán: điểm là hàm của phần kinh nghiệm và kỹ năng. Kết luận đúng là "probe này
  không phát hiện chênh lệch nào trên 144 cặp, với một vị trí, một prompt, thang 10 bậc thô", không phải "model công
  bằng". Thang thô (điểm 1, 3, 4, 7, 8) có thể che chênh lệch nhỏ; prompt khác (vị trí thiên về giới, câu hỏi mở về
  "phù hợp văn hoá", lấy mẫu ở `temperature` > 0) có thể cho kết quả khác.
- **Flip rate và Δ trung bình nói hai chuyện khác nhau.** Ở bảng lương, nam và nữ lệch nhau ở 24% cặp (theo cả hai chiều)
  dù Δ trung bình gần 0: với một ứng viên cụ thể, đổi tên vẫn đổi con số. Với quyết định cá nhân, đó mới là thứ người
  bị ảnh hưởng cảm nhận.
- **Bootstrap theo cụm rộng hơn bootstrap theo cặp**: ở bảng lương, khoảng của Hà Nội - Cần Thơ trải từ -5.9 tới 0.4 vì
  chênh lệch dồn vào vài hồ sơ; coi 48 cặp là độc lập sẽ cho khoảng hẹp giả và một "phát hiện" sai.

## Bẫy thường gặp

- Ghép cặp theo thứ tự dòng thay vì theo khoá: chạy tiếp một lần dở làm lệch thứ tự và mọi Δ sai mà không báo lỗi.
- Bootstrap từng cặp thay vì từng hồ sơ.
- Báo Δ trung bình mà không có sàn nhiễu và không có kiểm độ nhạy.
- `parse_score` nhận `true` hay `7.0` là điểm hợp lệ.
- WEAT không chuẩn hoá vector, hoặc dùng `std` tổng thể (`ddof=0`) thay cho độ lệch chuẩn mẫu.
