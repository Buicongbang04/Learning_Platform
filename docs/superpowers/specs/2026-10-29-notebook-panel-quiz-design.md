# Thiết kế: panel làm bài notebook 2 card và báo cáo trắc nghiệm động

Ngày: 2026-10-29. Áp dụng cho app học tập (`app/`) và mọi bài tập notebook của các track.

## 1. Mục đích và lý do

Màn Bài tập hiện hiển thị bài notebook như mọi bài khác: danh sách tab tệp (`report.md`,
`*.ipynb`, `test_*.py`) và một trình soạn thảo. Với bài notebook, cách này sai ý người học:
notebook được làm trong VS Code, còn báo cáo viết tay trong `report.md` thì nặng và khó tự kiểm.
Người học muốn:

- một card giới thiệu bài, có sẵn nút mở notebook trong VS Code và nút chạy test;
- phần báo cáo bài học biến thành **bộ câu hỏi trắc nghiệm** về kiến thức của module và về chính
  bộ dữ liệu, làm từng câu một, cuối cùng mới xem điểm và đáp án.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Bài notebook có giao diện riêng gồm 2 card (mục 4.1, 4.2); bài dạng script giữ giao diện hiện tại.
- Trắc nghiệm hiển thị **động từ dữ liệu**: số câu, số lựa chọn, kiểu chọn một / chọn nhiều đều đọc
  từ tệp câu hỏi của bài. Không có giao diện nào viết riêng cho một bài.
- Soạn sẵn bộ câu hỏi cho **mọi bài notebook hiện có**: 7 bài track Data Engineer, 43 bài track
  AI & Data Scientist (đếm ngày 2026-10-29). Người học sẽ review, thêm, sửa sau.

**Ngoài phạm vi**
- Câu tự luận (người học đã bỏ).
- Giải thích đáp án (người học muốn tự tìm hiểu).
- Trắc nghiệm cho bài script, cho màn milestone capstone.
- Chạy hay hiển thị notebook trong app.

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Giao diện hay logic trắc nghiệm viết cứng theo bài, theo số câu, theo số lựa chọn.
- Trắc nghiệm ảnh hưởng tới trạng thái "đã xong" của bài (test pass mới là tiêu chí).
- Hiện đúng/sai hay đáp án trước khi nộp.
- Câu hỏi dữ liệu có đáp án không tái lập được (đáp án đổi theo lần chạy).
- Làm hỏng giao diện bài script hay tiến độ đã lưu.

## 3. Ràng buộc

- Theo `CONTENT_SPEC.md`; cập nhật nó cho định dạng tệp câu hỏi.
- App: Vite + React + TS, component và token sẵn có (`app/src/components/ui.tsx`,
  `app/src/code/Workspace.tsx`, `app/server/workspace.ts`). Không thêm thư viện mới.
- Tiến độ lưu ở `progress.json` qua API sẵn có; thêm khoá mới, không đổi khoá cũ.
- Một phiên khác đang làm track AI & DS và sửa `app/`: sửa gọn, commit nhỏ, đọc bản mới nhất trước khi sửa.

## 4. Thiết kế (người học đã duyệt bố cục qua bản phác thảo)

### 4.1 Card 1: Giới thiệu bài tập

- Tên bài, mức (Basic / Intermediate / Advanced), mô tả ngắn (từ README bài), tên tệp notebook.
- Nút **Mở trong VS Code** (dùng endpoint `POST /api/workspace/open` có sẵn, mở notebook).
- Nút **Chạy test** (dùng endpoint chạy test có sẵn). Kết quả test hiện ngay trong card.
- Bài được đánh dấu xong khi test pass (giữ cơ chế hiện có).
- Đề bài, tiêu chí, gợi ý, lời giải vẫn ở cột trái như hiện nay.

### 4.2 Card 2: Báo cáo bài học (trắc nghiệm, tuỳ chọn)

- Hiện **từng câu một**: thanh tiến độ "Câu k/N", nút câu trước / câu sau, nút Nộp ở câu cuối.
- Kiểu câu: chọn một (radio) hoặc chọn nhiều (checkbox), theo tệp câu hỏi.
- Hai nhóm câu: **kiến thức** của module, và **dữ liệu** (đáp án là số liệu hay sự thật tính trên bộ
  dữ liệu thật của bài; muốn trả lời đúng phải chạy notebook).
- Chưa nộp thì không hiện đúng/sai. Nộp xong hiện **điểm** (số câu đúng / tổng) và **đáp án đúng
  của từng câu**, không kèm giải thích.
- Làm lại được bao nhiêu lần cũng được *(quyết định của người viết thiết kế)*; lưu lần gần nhất.
- Câu chấm đúng khi tập lựa chọn trùng khớp tập đáp án (chọn nhiều: đủ và không thừa)
  *(quyết định của người viết thiết kế)*.

### 4.3 Dữ liệu câu hỏi (động)

*(Định dạng do người viết thiết kế chọn; builder được chỉnh tên trường nếu có lý do.)*

- Câu hỏi: `exercises/<level>/<slug>/quiz.yaml`, đáp án tách riêng:
  `solutions/<level>/<slug>/quiz-answers.yaml`. App chỉ đọc tệp đáp án sau khi nộp.

```yaml
# quiz.yaml
questions:
  - id: peak-day
    kind: data            # data | knowledge
    type: single          # single | multi
    prompt: "Ngày nào trong tháng 7/1995 có nhiều request nhất?"
    options:
      - { id: a, text: "1/7" }
      - { id: b, text: "13/7" }
      - { id: c, text: "4/7" }
```

```yaml
# quiz-answers.yaml
peak-day: [b]
```

- Số câu và số lựa chọn bất kỳ (≥1 câu, ≥2 lựa chọn mỗi câu). `prompt` và `text` là markdown ngắn
  (có thể có `code`, số liệu, LaTeX như phần còn lại của app).
- Bài notebook không có `quiz.yaml` thì card 2 không hiện (không lỗi).
- Có kiểm tra định dạng: test chung trong repo duyệt mọi `quiz.yaml` + `quiz-answers.yaml`
  (id duy nhất, mỗi câu có đáp án, đáp án thuộc lựa chọn, `single` đúng một đáp án, `multi` ≥1).
- Câu nhóm `data` phải có đáp án cố định trên dữ liệu đã ghim; bài dùng dữ liệu không tái lập
  (vd. stream Wikimedia người học tự ghi) chỉ có câu `knowledge` *(quyết định của người viết thiết kế)*.
- Mỗi bài khoảng 5–8 câu, chia đôi kiến thức / dữ liệu khi có thể *(quyết định của người viết thiết
  kế; khuôn hiển thị không phụ thuộc con số này)*.

- **Nguồn đáp án câu `data`** *(quyết định của người viết thiết kế)*: tính trên bộ dữ liệu thật đã
  ghim (bản snapshot trong danh mục `data/download_dataset.py` hoặc Olist thật) bằng notebook lời giải
  có sẵn (32 notebook lời giải ở track AI & DS, đủ ở track DE), hoặc bằng script tính riêng nếu bài
  chỉ có `SOLUTION.md`. Kết quả phụ thuộc ngẫu nhiên (huấn luyện model, CNN, embedding) mà không cố
  định được bằng seed thì bài đó chỉ có câu `knowledge`.
- **Chấm ở phía server** *(quyết định của người viết thiết kế)*: endpoint mới trong `app/server`
  nhận lựa chọn, đọc `quiz-answers.yaml`, trả điểm và đáp án; giao diện không tải tệp đáp án trước khi
  nộp. Cột "Lời giải" hiện có chỉ hiển thị `SOLUTION.md`, không liệt kê `quiz-answers.yaml`.

### 4.4 Tiến độ

- `progress.json`, trong track: `quizzes[<exercise.key>] = { answers: {qid: [optionId]}, correct, total, submittedAt, quizHash }`.
  Không đổi các khoá khác.
- Bộ câu hỏi bị sửa sau khi đã nộp (`quizHash` khác) thì kết quả cũ không hiện, card mời làm lại
  *(quyết định của người viết thiết kế)*.
- Điểm trắc nghiệm chỉ hiện trong màn Bài tập, không hiện ở trang module/track/tổng quan
  *(quyết định của người viết thiết kế)*.

### 4.5 Bỏ `report.md` của bài notebook DE

- 7 bài notebook DE có `starter/report.md` (và bản trong `solutions/`); 7 tệp test chấm báo cáo.
  Bỏ các tệp báo cáo và phần test chấm báo cáo; bài script `02-data-modeling/advanced/02-postgres-query-tuning`
  cũng có `report.md` nhưng là sản phẩm của bài script, **giữ nguyên** *(quyết định của người viết thiết kế)*; nội dung insight trong báo cáo cũ dùng làm nguồn
  cho câu hỏi `data`. Cập nhật `CONTENT_SPEC.md` và mục 4 sản phẩm trong
  `docs/superpowers/specs/2026-10-29-data-engineer-roadmap-gaps-design.md` (báo cáo → trắc nghiệm).

## 5. Để builder tự quyết

Tên component, cách nhận diện "bài notebook" (vd. starter có `.ipynb`), API đọc tệp câu hỏi và
đáp án (endpoint mới hay import tĩnh, miễn đáp án không lộ trước khi nộp trong giao diện), bố cục
chi tiết theo token sẵn có, nội dung câu hỏi cụ thể từng bài.

## 6. Kiểm chứng

- App typecheck sạch; một bài notebook hiện đúng 2 card, một bài script giữ giao diện cũ.
- Trắc nghiệm hiển thị đúng với bài nhiều câu, ít câu, câu chọn nhiều, câu nhiều lựa chọn.
- Test định dạng câu hỏi pass cho mọi bài; test bài tập vẫn pass (`SOLUTION=1`) sau khi bỏ báo cáo.
- Đáp án câu `data` khớp số liệu trên dữ liệu thật đã tải (kiểm bằng notebook lời giải).
