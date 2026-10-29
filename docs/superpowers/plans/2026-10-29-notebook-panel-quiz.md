# Panel notebook 2 card + trắc nghiệm động — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bài notebook có panel 2 card (Giới thiệu bài + Báo cáo trắc nghiệm động), chấm phía server, và có sẵn bộ câu hỏi cho 50 bài notebook.

**Architecture:** Câu hỏi là dữ liệu (`quiz.yaml` cạnh bài, `quiz-answers.yaml` trong `solutions/`). Một plugin Vite mới (`app/server/quiz.ts`) phục vụ câu hỏi không kèm đáp án và chấm bài. Giao diện dựng từ dữ liệu, không biết trước số câu/số lựa chọn; kết quả lưu ở `progress.json`.

**Tech Stack:** Vite + React + TS (app), `yaml` (đã có trong app), Node 25 `node --test` chạy thẳng `.ts`; Python pytest cho test định dạng câu hỏi.

**Spec:** `docs/superpowers/specs/2026-10-29-notebook-panel-quiz-design.md`

## Global Constraints

- Bài notebook = bài có tệp `.ipynb` trong `starter/`; chỉ bài này đổi giao diện, bài script giữ nguyên.
- Card 1: tên bài, mức, mô tả ngắn, tên notebook, nút "Mở trong VS Code", nút "Chạy test", kết quả test trong card; bài xong khi test pass (cơ chế cũ).
- Card 2: từng câu một, thanh tiến độ "Câu k/N", câu trước/câu sau, nộp ở cuối; chỉ trắc nghiệm `single`/`multi`; trước khi nộp không lộ đúng/sai; nộp xong hiện điểm và đáp án đúng từng câu, không giải thích; làm lại không giới hạn, lưu lần gần nhất; tuỳ chọn, không ảnh hưởng trạng thái xong.
- Không viết cứng theo bài/số câu/số lựa chọn; chạy tốt với 10–18+ câu.
- Câu đúng khi tập lựa chọn trùng khớp tập đáp án.
- Định dạng: `quiz.yaml` = `{questions: [{id, kind: data|knowledge, type: single|multi, prompt, options: [{id, text}]}]}`; `quiz-answers.yaml` = `{<qid>: [optionId, ...]}`.
- Câu `data` có đáp án cố định trên dữ liệu đã ghim; dữ liệu không tái lập / kết quả ngẫu nhiên → chỉ `knowledge`.
- Bản soạn đầu 5–8 câu/bài, chia đôi knowledge/data khi có thể.
- Progress: `quizzes[<exercise.key>] = {answers, correct, total, submittedAt, quizHash}`; hash khác → ẩn kết quả cũ, mời làm lại; không đổi khoá cũ.
- Không thêm thư viện mới. `app/`, `testkit.py`, track AI & DS dùng chung với phiên khác: sửa gọn, commit nhỏ.
- Mọi lệnh uv trong worktree dùng `UV_NO_SYNC=1`.

## Review Focus

1. Bài có 18 câu, câu 6 lựa chọn, câu chọn nhiều → thanh tiến độ và điều hướng không tràn, vẫn tới được câu bất kỳ. (Task 3)
2. Bài notebook không có `quiz.yaml` → card 2 không hiện, không lỗi. (Task 1, Task 3)
3. Bộ câu hỏi bị sửa sau khi đã nộp → kết quả cũ ẩn, mời làm lại. (Task 1, Task 2)
4. Nộp khi còn câu chưa trả lời → nút Nộp tắt, chỉ ra câu còn thiếu *(quyết định: phải trả lời đủ mới nộp)*. (Task 3)
5. `quiz.yaml` hỏng / đáp án thiếu → API trả lỗi rõ, card hiện lỗi, trang không vỡ; test định dạng bắt trước khi commit. (Task 1)

---

### Task 1: Định dạng câu hỏi, API câu hỏi và chấm điểm

**Files:**
- Create: `app/server/quiz.ts` (plugin Vite + hàm thuần), `app/server/quiz.test.ts`
- Modify: `app/vite.config.ts` (đăng ký plugin)
- Create: `tests/test_quiz_files.py` (duyệt mọi `quiz.yaml` trong `tracks/`)
- Create: một bộ câu mẫu tối thiểu cho Task 3 dùng thử: `tracks/data-engineer/modules/00-introduction/exercises/basic/02-web-server-logs/quiz.yaml` + `solutions/.../quiz-answers.yaml` (2–3 câu, Task 5 sẽ thay bằng bộ đầy đủ)

**Interfaces:**
- Produces: `GET /api/quiz?dir=<exercise dir>` → `200 {questions: QuizQuestion[], quizHash: string}` | `404` khi không có `quiz.yaml` | `400/500 {error}`. Không bao giờ trả đáp án.
- Produces: `POST /api/quiz/grade` body `{dir, answers: Record<qid, string[]>}` → `200 {correct, total, quizHash, results: [{id, correct: boolean, answer: string[]}]}`.
- Produces (TS): `type QuizQuestion = {id: string; kind: "data"|"knowledge"; type: "single"|"multi"; prompt: string; options: {id: string; text: string}[]}`; `gradeQuiz(questions, answerKey, answers)`; `quizHash(rawYaml: string): string` (sha256 rút gọn của nội dung `quiz.yaml`).
- Đường dẫn đáp án: thay `/exercises/` bằng `/solutions/` trong `dir` (cùng quy ước testkit).

- [ ] **Step 1:** Viết `quiz.test.ts`: đúng khi tập trùng khớp (thứ tự không quan trọng); multi thiếu hoặc thừa một lựa chọn → sai; câu bỏ trống → sai; câu không có trong đáp án → lỗi rõ; hash đổi khi nội dung đổi.
- [ ] **Step 2:** Viết `tests/test_quiz_files.py`: với mỗi `quiz.yaml`: id câu duy nhất; ≥1 câu; mỗi câu ≥2 lựa chọn, id lựa chọn duy nhất; `kind`, `type` hợp lệ; có `quiz-answers.yaml` tương ứng; mỗi câu có đáp án, đáp án ⊆ lựa chọn; `single` đúng 1 đáp án, `multi` ≥1; không có khoá thừa trong tệp đáp án. Thêm case tệp hỏng dựng trong `tmp_path` để test chính validator.
- [ ] **Step 3:** `node --test app/server/quiz.test.ts` và `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` → FAIL.
- [ ] **Step 4:** Hiện thực `quiz.ts` (kiểm `dir` theo cùng regex/hàm `exerciseRoot` của `workspace.ts`, dùng lại `assertSameOrigin` nếu có), đăng ký plugin.
- [ ] **Step 5:** Hai lệnh ở Step 3 → PASS; `cd app && pnpm typecheck` sạch; chạy `pnpm dev` cổng trống, `curl` GET bài mẫu (không có trường đáp án), GET bài không có quiz (404), POST grade đúng/sai.
- [ ] **Step 6:** Commit.

### Task 2: Lưu kết quả trắc nghiệm vào tiến độ

**Files:**
- Modify: `app/src/progress.tsx` (thêm `quizzes` vào `TrackProgress` và giá trị mặc định)
- Create: `app/src/code/quiz.ts` (hook client)

**Interfaces:**
- Consumes: API Task 1.
- Produces: `type QuizResult = {answers: Record<string, string[]>; correct: number; total: number; submittedAt: string; quizHash: string}`; `useQuiz(exercise: Exercise, trackId: string)` → `{status: "loading"|"none"|"ready"|"error", error, questions, quizHash, draft, setAnswer(qid, optionIds), submit(), result: QuizResult & {results} | null, retake()}` — `result` là null khi chưa nộp hoặc khi `quizHash` đã lưu khác hash hiện tại.

- [ ] **Step 1:** Hiện thực; `draft` giữ trong state (không lưu), `submit()` gọi grade rồi lưu `quizzes[exercise.key]` qua `api.update`.
- [ ] **Step 2:** `pnpm typecheck` sạch; tiến độ cũ (không có `quizzes`) vẫn đọc được.
- [ ] **Step 3:** Commit.

### Task 3: Panel notebook 2 card

**Files:**
- Create: `app/src/code/NotebookPanel.tsx` (gồm `ExerciseIntroCard`, `QuizCard`)
- Modify: `app/src/pages/ExercisePage.tsx` (bài notebook dùng `NotebookPanel` thay `Workspace`), `app/src/code/Workspace.tsx` (export `OpenInVsCode` và phần hiển thị kết quả test để dùng lại, không đổi hành vi bài script)

**Interfaces:**
- Consumes: `useWorkspace(dir).runTests/result/running` (sẵn có), `OpenInVsCode`, `useQuiz` (Task 2).
- Produces: `isNotebookExercise(exercise): boolean` (starter có `.ipynb`; dựa trên danh sách tệp workspace hoặc `files` frontmatter — chọn nguồn đáng tin hơn sau khi kiểm 50 bài).

- [ ] **Step 1:** Card 1 theo Global Constraints, kết quả test dùng lại hiển thị sẵn có.
- [ ] **Step 2:** Card 2: một câu một lúc; radio cho `single`, checkbox cho `multi`; thanh tiến độ + dãy ô số câu bấm để nhảy (ô đã trả lời khác màu, xuống dòng khi nhiều câu); nút Nộp chỉ bật khi đủ câu, nếu chưa đủ thì liệt kê câu còn thiếu; sau nộp: điểm `x/N`, từng câu hiện lựa chọn của người học và đáp án đúng (không giải thích); nút Làm lại. Không có quiz → không render card 2.
- [ ] **Step 3:** `pnpm typecheck`; tạm thêm một `quiz.yaml` 18 câu (có câu 6 lựa chọn, câu multi) vào bài mẫu, chụp màn hình 1440 và 375 (Playwright như các lần trước) — không tràn ngang, điều hướng dùng được; mở một bài script (vd. `02-data-modeling/basic/01-normalize-orders`) — giao diện cũ; gỡ bộ 18 câu tạm.
- [ ] **Step 4:** Commit.

### Task 4: Bỏ `report.md` ở 7 bài notebook DE

**Files:**
- Delete: `starter/report.md` và `solutions/.../report.md` của 7 bài notebook DE (5 bài module 00 basic/intermediate, `06/intermediate/04-nyc-taxi-real`, `07/advanced/03-hybrid-wikimedia`; giữ `02-data-modeling/advanced/02-postgres-query-tuning`)
- Modify: test của 7 bài (bỏ phần chấm báo cáo), README bài (bỏ `report.md` khỏi `files` và đề bài), `SOLUTION.md` liên quan, `CONTENT_SPEC.md`, `docs/superpowers/specs/2026-10-29-data-engineer-roadmap-gaps-design.md` (4 sản phẩm: báo cáo → trắc nghiệm)

- [ ] **Step 1:** Ghi lại số liệu insight trong các `report.md` lời giải ra `docs/superpowers/plans/quiz-data-notes.md` (nguồn cho Task 5) trước khi xoá.
- [ ] **Step 2:** Xoá/sửa; `SOLUTION=1 UV_NO_SYNC=1 uv run pytest <7 thư mục bài> -q` pass; starter vẫn fail không lỗi collect.
- [ ] **Step 3:** Commit.

### Task 5: Bộ câu hỏi 7 bài notebook DE

**Files:** `quiz.yaml` + `quiz-answers.yaml` cho 7 bài (thay bộ mẫu Task 1).

- [ ] **Step 1:** Mỗi bài 5–8 câu; câu `knowledge` từ README module và đề bài; câu `data` từ số liệu đã ghim (ghi chú Task 4, test real-data đã pin, chạy notebook lời giải khi cần); `07/advanced/03` chỉ `knowledge`. Phương án nhiễu hợp lý (cùng đơn vị, gần đúng).
- [ ] **Step 2:** `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` pass; đối chiếu từng đáp án `data` với nguồn số liệu, ghi nguồn vào báo cáo task.
- [ ] **Step 3:** Commit.

### Task 6–8: Bộ câu hỏi 43 bài notebook AI & Data Scientist

Task 6: module 01–05 · Task 7: module 06–10 · Task 8: module 11–15 (bài notebook trong các module đó).

**Files:** `quiz.yaml` + `quiz-answers.yaml` cho từng bài notebook (chỉ thêm tệp mới, không sửa nội dung track).

- [ ] **Step 1:** Như Task 5 Step 1; câu `data` lấy từ notebook lời giải có sẵn (`solutions/**.ipynb`) chạy trên dữ liệu thật đã tải hoặc từ số liệu đã pin trong test; bài huấn luyện model/ngẫu nhiên không cố định được → chỉ `knowledge`.
- [ ] **Step 2:** `tests/test_quiz_files.py` pass; liệt kê bài nào chỉ có `knowledge` và vì sao.
- [ ] **Step 3:** Commit.

### Task 9: Tài liệu và kiểm toàn bộ

**Files:** `CONTENT_SPEC.md` (mục định dạng câu hỏi, nếu Task 4 chưa đủ), `README.md` (dòng mô tả panel notebook nếu cần)

- [ ] **Step 1:** `UV_NO_SYNC=1 uv run pytest tests -q`; `SOLUTION=1 UV_NO_SYNC=1 uv run pytest tracks -q` không fail; `node --test app/server/quiz.test.ts`; `cd app && pnpm typecheck`.
- [ ] **Step 2:** Đếm: 50 bài notebook đều có `quiz.yaml` (`find`).
- [ ] **Step 3:** Commit (không push).
