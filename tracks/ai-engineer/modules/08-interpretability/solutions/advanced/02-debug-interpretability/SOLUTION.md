# Hướng làm: kiểm lại một bản phân tích interpretability

Bài không có code lời giải: bản sửa chỉ là 4 dòng, giá trị nằm ở các phép thử có đáp án biết trước và ở việc viết lại kết luận.
Dưới đây là 4 bug, triệu chứng đo được của **từng bug khi chỉ còn mình nó** (3 bug kia đã sửa), phép thử khoanh vùng, cách sửa và kết
luận đúng. Số liệu: GPT-2 small trong lớp `GPT` module 05, CPU 4 luồng, ngày 2026-11-01; mỗi lần chạy cả notebook khoảng 65 giây.

## Bốn bug

| # | Bug | Ở đâu | Triệu chứng khi chỉ còn mình nó |
| --- | --- | --- | --- |
| 1 | Cache lấy output của MLP thay vì output của Block | `cache_streams`: hook trên `block.mlp` | lens tầng cuối trùng top-1 với model chỉ 0.076; probe tầng 1 task 0.925 (đúng: 0.976); bảng patching tầng 4, 8, 11 rải rác |
| 2 | Nhãn control rút theo từng lần xuất hiện, không theo loại token | `probe_with_controls`: `rng.choice(..., size=len(token_ids))` | control 0.596 (≈ majority 0.605), selectivity 0.381 (đúng: 0.860 và 0.117) |
| 3 | Patch lấy giá trị nguồn ở vị trí `pos - 1` | `patch_resid`: `source[:, pos - 1]` | hàng tầng 0: 0.71 ở vị trí 0, 0.52 ở vị trí S2, khác 0 ở hầu hết vị trí (đúng: 1.00 ở S2, 0 ở chỗ khác) |
| 4 | FVU chia cho tổng bình phương không trừ trung bình | `sae_report` | FVU 0.0018 (đúng: 0.104) trên dữ liệu có trung bình 3 ở mọi chiều |

Notebook gốc (đủ 4 bug): lens tầng cuối 0.076, selectivity 0.349, bảng patching rải rác ở mọi tầng, FVU 0.0018. `lens_report` và
`TopKSAE` không có bug. Bản sửa: lens tầng cuối 1.000 và CE giảm đều 9.05 → 3.54; probe task 0.976, control 0.860, selectivity 0.117;
bảng patching chỉ khác 0 ở cột S2 và cột cuối (tầng 0: 1.00 ở S2; tầng 8: 0.69 ở S2, 0.32 ở cuối; tầng 11: 0.97 ở cuối); FVU 0.104.

### Bug 1: điểm đo sai

- **Phép thử.** Ở stream ra khỏi tầng cuối, logit lens phải trùng model **đúng 100%** (`ln_f` rồi `lm_head` chính là đường ra của model).
  Bản lỗi cho 0.076, và đường CE đi lên rồi xuống bất thường (13.44 ở tầng 2, 5.86 ở tầng 10, rồi 8.17 ở tầng 11). Kiểm thêm:
  `streams[l]` phải bằng `streams[l-1] + attn_out + mlp_out`.
- **Sửa.** `block.mlp.register_forward_hook` → `block.register_forward_hook`.
- **Lan sang đâu.** Probe và patching dùng chung cache: probe tầng 1 trên output MLP vẫn đạt 0.925 (con số trông hợp lý, nên rất dễ lọt),
  bảng patching các tầng ≥ 1 thay residual bằng output MLP. Một điểm đo sai làm hỏng mọi thí nghiệm phía sau mà không thí nghiệm nào
  báo lỗi.
- **Kết luận đúng (thay kết luận 1).** Dự đoán hình thành dần: trùng top-1 0.09 ở tầng 0, 0.17 ở tầng 6, 0.60 ở tầng 10, 1.00 ở tầng 11.

### Bug 2: control task không còn là control task

- **Phép thử.** Đặc trưng là one-hot của token id (probe học thuộc được mọi nhãn theo loại token): control task đúng phải đạt rất cao
  trên các loại token đã thấy; bản lỗi chỉ ngang majority. Hoặc kiểm trực tiếp: nhãn control của cùng một token id phải giống nhau.
- **Sửa.** `types, inverse = np.unique(token_ids, return_inverse=True)`; `control = rng.choice(values, size=len(types), p=...)[inverse]`.
- **Kết luận đúng (thay kết luận 2).** Selectivity ở tầng 1 là 0.117, không phải 0.35: probe 768 chiều học thuộc nhãn theo loại token tới
  0.86, nên phần lớn accuracy 0.976 là "dễ"; thông tin ngữ cảnh đóng góp khoảng 0.12 trên control và khoảng 0.23 trên baseline loại token
  (bài Intermediate 01).

### Bug 3: lệch một vị trí trong patching

- **Phép thử.** Hai prompt chỉ khác ở vị trí 10. Patch tầng 0 ở vị trí 10 phải cho đúng 1.00, mọi vị trí khác đúng 0; mọi vị trí trước 10
  phải là 0 ở mọi tầng (attention nhân quả). Bản lỗi cho 0.71 ở vị trí 0 (chèn stream vị trí −1, tức vị trí cuối, vào vị trí đầu).
- **Sửa.** `source[:, pos - 1]` → `source[:, pos]`.
- **Kết luận đúng (thay kết luận 3).** Thông tin nằm ở vị trí S2 tới khoảng tầng 8 (0.69) và chuyển sang vị trí cuối (0.97 ở tầng 11),
  khớp bài Intermediate 02.

### Bug 4: FVU không trừ trung bình

- **Phép thử.** SAE chỉ trả về trung bình (decoder 0, `b_dec` = mean) phải có FVU đúng 1; bản lỗi cho số rất nhỏ vì dữ liệu lệch 3 đơn vị
  ở mọi chiều, nên $$\sum\lVert x\rVert^2$$ lớn hơn phương sai nhiều lần.
- **Sửa.** Mẫu số `acts.pow(2).sum()` → `(acts - acts.mean(0)).pow(2).sum()`.
- **Kết luận đúng (thay kết luận 4).** FVU 0.104 sau 300 bước: tái dựng khá, chưa "gần hoàn hảo". Và ngay cả FVU thấp cũng không đủ để tin
  latent: cần L0, latent chết, CE khi ghép vào model, và kiểm latent bằng can thiệp.

## Bug che nhau

- Bug 1 và bug 3 cùng làm bảng patching rải rác. Sửa bug 3 trước mà chưa sửa bug 1 thì hàng tầng 0 đã đúng (vì tầng 0 dùng khoá `embed`,
  không qua cache lỗi) nhưng các tầng sau vẫn sai: người vội sẽ nghĩ "tầng 0 đúng rồi, các tầng sau là hành vi thật". Phép thử "vị trí
  trước S2 phải bằng 0 ở **mọi** tầng" bắt được.
- Bug 1 làm probe giảm (0.976 → 0.925) còn bug 2 làm selectivity tăng: hai lỗi đẩy con số theo hai chiều, kết hợp lại cho một kết luận
  nghe hợp lý.
- Thứ tự gỡ hợp lý: điểm đo (bug 1) trước, vì mọi thí nghiệm phụ thuộc nó; rồi từng phương pháp với phép thử có đáp án của chính nó.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 20 | mọi test pass mà không đổi chữ ký, docstring, dữ liệu |
| Đủ 4 bug, sửa ở gốc | 20 | mỗi bug sửa đúng dòng gây ra nó; không chỉnh thí nghiệm để che triệu chứng |
| Phép thử có đáp án biết trước | 25 | mỗi bug có một sanity check nêu rõ kết quả mong đợi và kết quả thật bằng số |
| Kết luận viết lại | 20 | bốn kết luận được sửa đúng theo số sau khi sửa, kèm điều chúng không chứng minh |
| Checklist và bug che nhau | 15 | nêu thứ tự gỡ, bug nào che bug nào; checklist dùng lại cho phân tích khác |

Đạt từ 70 điểm. `BUGS.md` chỉ liệt kê dòng đã sửa mà không có phép thử và con số không quá 40 điểm.
