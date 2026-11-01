---
title: Probe thiên lệch - counterfactual trên LLM chấm hồ sơ, WEAT trên embedding
level: intermediate
services: []
files:
  - path: starter/bias.ipynb
    note: 6 hàm TODO
  - path: tests/test_bias.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/03-bias-probe/starter/bias.ipynb
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/03-bias-probe -q
---

## Mục tiêu

Đo xem `qwen2.5:3b`, khi được dùng để chấm sơ bộ hồ sơ xin việc, có cho điểm khác nhau chỉ vì tên, giới tính hay quê
quán của ứng viên không, với một thiết kế đủ chặt để con số đáng tin: ghép cặp counterfactual, sàn nhiễu, bootstrap theo
hồ sơ, flip rate ở ngưỡng quyết định, kiểm độ nhạy. Rồi đo liên kết giới tính và nghề nghiệp trong `bge-m3` bằng WEAT có
phép thử đối chứng. Mục 4 lý thuyết giải thích thiết kế.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Cần Ollama với `qwen2.5:3b` và `bge-m3`. Hai nhiệm vụ (chấm điểm phù hợp 1 tới 10, đề xuất lương khởi điểm), mỗi nhiệm
vụ 144 lượt với output JSON ngắn: bản tham chiếu mất khoảng 2 phút mỗi nhiệm vụ trên PC của track (trung vị 0.9 giây mỗi
lượt, Ollama dùng chung).

Trong `starter/bias.ipynb`, cell chấm điểm:

1. `parse_score(reply, lo, hi, key)`: số nguyên trong khoảng từ JSON, mọi trường hợp khác `None`.
2. `paired_diffs(df, attr, a, b, keys)`: ghép cặp chỉ khác thuộc tính `attr`, trả chênh lệch.
3. `cluster_bootstrap_ci(values, clusters, ...)`: khoảng tin cậy bootstrap lấy mẫu lại theo cụm (hồ sơ).
4. `flip_rate(df, attr, a, b, keys, threshold)`: tỉ lệ cặp bị đảo quyết định.
5. `weat_effect_size(X, Y, A, B)` và `weat_p_value(X, Y, A, B, ...)`.

Notebook mô tả chính xác từng hàm. Rồi chạy các cell `explore`: hai nhiệm vụ x 144 biến thể, mỗi nhiệm vụ một bảng so
sánh (giới tính, ba cặp quê quán, sàn nhiễu đổi tên, kiểm độ nhạy mạnh và yếu), WEAT chính và đối chứng. Trả lời các câu hỏi cuối notebook, rồi làm
phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `parse_score` nhận đúng số nguyên trong khoảng (kể cả với khoá và khoảng khác mặc định) và loại `0`, `11`, `7.0`, `"7"`,
  `true`, `null`, thiếu khoá, không phải JSON.
- `paired_diffs` ghép theo khoá (không theo thứ tự dòng), báo lỗi khi khoá trùng hoặc thiếu cặp.
- `cluster_bootstrap_ci` lấy mẫu lại **cụm** đúng như mô tả (test so từng lần rút với cùng seed), cho khoảng rộng hơn khi
  các cặp trong cụm tương quan, tái lập theo seed.
- `flip_rate` đúng ở ba ngưỡng; WEAT đúng ví dụ tính tay, không đổi khi nhân vector với hằng số, p-value một phía.
- Cell `explore` chạy hết và in bảng so sánh, WEAT.

## Gợi ý

### Gợi ý 1

`df[df[attr] == a].set_index(keys)["score"]` cho một Series theo khoá; hai Series như vậy trừ nhau được sau khi
`reindex` cùng thứ tự. `index.has_duplicates` phát hiện khoá trùng.

### Gợi ý 2

Trong bootstrap theo cụm, gom trước giá trị của từng cụm thành một list mảng; mỗi vòng chỉ cần rút chỉ số cụm và
`np.concatenate`. Đừng lấy trung bình của trung bình từng cụm: các cụm có số phần tử khác nhau. Với WEAT, tính một vector
$$s$$ cho mọi từ đích bằng phép nhân ma trận rồi lấy trung bình theo hàng.
