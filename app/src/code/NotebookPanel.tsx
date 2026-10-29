import { useState } from "react";
import { Check, ChevronLeft, ChevronRight, CircleCheck, CircleX, ClipboardList, FileText, LoaderCircle, NotebookPen, RotateCcw, Send, X } from "lucide-react";
import { LEVEL_LABEL, type Exercise } from "../content";
import { Markdown } from "../components/Markdown";
import { badge, button, card, Checkbox, cx, ErrorBlock, LoadingBlock, ProgressBar } from "../components/ui";
import { OpenInVsCode, PassedBanner, RunOutput, RunSummary } from "./Workspace";
import { useWorkspace } from "./workspace";
import { useQuiz, type QuizQuestion } from "./quiz";
import { scoreOf } from "./quizResult";
import { starterFilesOf, writtenReportOf } from "./starterFiles";

/** Notebook của bài (starter/*.ipynb) theo `files` trong frontmatter README; null nếu là bài script. */
export function notebookOf(exercise: Exercise): string | null {
  return exercise.files.find((file) => file.path.startsWith("starter/") && file.path.endsWith(".ipynb"))?.path ?? null;
}

export function isNotebookExercise(exercise: Exercise): boolean {
  return notebookOf(exercise) !== null;
}

const KIND_LABEL = { knowledge: "Kiến thức", data: "Dữ liệu" } as const;
const INLINE_MD = "min-w-0 [&_p]:m-0";

function ExerciseIntroCard({ exercise, done, onMarkDone }: { exercise: Exercise; done: boolean; onMarkDone: () => void }) {
  const ws = useWorkspace(exercise.dir);
  const result = ws.result;
  const starters = starterFilesOf(exercise);
  const multi = starters.length > 1;

  return (
    <section aria-labelledby="nb-intro-title" className={cx(card, "overflow-hidden")}>
      <div className="flex flex-col gap-3 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className={badge.neutral}>{LEVEL_LABEL[exercise.level]}</span>
          {done && (
            <span className={badge.done}>
              <Check className="size-3.5" aria-hidden />
              Đã xong
            </span>
          )}
        </div>
        <div>
          <p className="text-xs font-medium tracking-wide text-muted uppercase">Giới thiệu bài tập</p>
          <h2 id="nb-intro-title" className="mt-1 text-lg font-semibold text-balance">
            {exercise.title}
          </h2>
        </div>
        {exercise.goal && <Markdown className="text-muted [&_p]:text-sm">{exercise.goal}</Markdown>}
        {multi ? (
          <ul aria-label="Tệp cần làm" className="grid gap-2">
            {starters.map((file) => {
              const Icon = file.path.endsWith(".ipynb") ? NotebookPen : FileText;
              return (
                <li key={file.path} className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-xl bg-code px-3 py-2">
                  <Icon className="size-4 shrink-0 text-muted" aria-hidden />
                  <div className="flex min-w-0 flex-1 basis-40 flex-col">
                    <code className="min-w-0 truncate font-mono text-[13px]" title={file.path}>
                      {file.path}
                    </code>
                    {file.note && <span className="truncate text-xs text-muted">{file.note}</span>}
                  </div>
                  <OpenInVsCode path={`${exercise.dir}/${file.path}`} className="min-h-8 shrink-0 px-3 py-1" showLabel />
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="flex min-w-0 items-center gap-2 rounded-xl bg-code px-3 py-2 text-sm">
            <NotebookPen className="size-4 shrink-0 text-muted" aria-hidden />
            <code className="min-w-0 truncate font-mono text-[13px]" title={starters[0].path}>
              {starters[0].path}
            </code>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {!multi && <OpenInVsCode path={`${exercise.dir}/${starters[0].path}`} showLabel />}
          <button type="button" className={button.primary} disabled={Boolean(ws.running) || ws.status !== "ready"} onClick={ws.runTests} title={`uv run pytest ${exercise.dir}`}>
            {ws.running === "test" ? <LoaderCircle className="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden /> : <Check className="size-4 shrink-0" aria-hidden />}
            {ws.running === "test" ? "Đang chạy…" : "Chạy test"}
          </button>
        </div>
        {ws.status === "error" && (
          <p role="alert" className="text-sm text-error-text">
            Không mở được tệp bài tập: {ws.error}
          </p>
        )}
        {!result && ws.status === "ready" && (
          <p className="text-sm text-muted">{multi ? "Làm bài trong notebook và viết báo cáo, lưu lại rồi bấm Chạy test để kiểm tra." : "Làm bài trong notebook, lưu lại rồi bấm Chạy test để kiểm tra."}</p>
        )}
      </div>

      {result && (
        <div className="border-t border-border-strong" aria-live="polite" aria-busy={Boolean(ws.running) || undefined}>
          <div className="flex h-11 items-center gap-2 px-4">
            {ws.running ? <span className="text-sm text-muted">Đang chạy…</span> : <RunSummary result={result} />}
            <span className="flex-1" />
            {!ws.running && (
              <button type="button" className={button.icon} aria-label="Xoá kết quả" onClick={ws.clearResult}>
                <X className="size-4" aria-hidden />
              </button>
            )}
          </div>
          {!done && <PassedBanner result={result} onMarkDone={onMarkDone} text="Notebook của bạn đã qua toàn bộ test." />}
          <div className="max-h-80 overflow-auto border-t border-border-strong bg-code-frame">
            <RunOutput output={result.output} />
          </div>
        </div>
      )}
    </section>
  );
}

function isAnswered(draft: Record<string, string[]>, id: string) {
  return (draft[id]?.length ?? 0) > 0;
}

function OptionRow({ question, option, selected, onToggle }: { question: QuizQuestion; option: QuizQuestion["options"][number]; selected: boolean; onToggle: (checked: boolean) => void }) {
  return (
    <label
      className={cx(
        "flex cursor-pointer items-start gap-3 rounded-xl border px-3.5 py-2.5 transition-colors",
        selected ? "border-primary bg-primary-light" : "border-border-strong hover:bg-item-hover",
      )}
    >
      <span className="mt-0.5 inline-flex shrink-0">
        {question.type === "multi" ? (
          <Checkbox checked={selected} onChange={onToggle} />
        ) : (
          <input
            type="radio"
            name={`quiz-${question.id}`}
            checked={selected}
            onChange={(event) => onToggle(event.target.checked)}
            className="size-5 cursor-pointer appearance-none rounded-full border-[1.5px] border-border-strong bg-surface outline-hidden transition-colors not-checked:hover:border-foreground checked:border-[6px] checked:border-primary focus-visible:border-foreground"
          />
        )}
      </span>
      <Markdown className={INLINE_MD}>{option.text}</Markdown>
    </label>
  );
}

function QuestionChips({ questions, current, draft, onJump }: { questions: QuizQuestion[]; current: number; draft: Record<string, string[]>; onJump: (index: number) => void }) {
  return (
    <nav aria-label="Chọn câu" className="flex flex-wrap gap-1.5">
      {questions.map((question, index) => {
        const answered = isAnswered(draft, question.id);
        const active = index === current;
        return (
          <button
            key={question.id}
            type="button"
            onClick={() => onJump(index)}
            aria-current={active ? "step" : undefined}
            aria-label={`Câu ${index + 1}${answered ? ", đã trả lời" : ", chưa trả lời"}`}
            className={cx(
              "inline-flex size-8 cursor-pointer items-center justify-center rounded-lg border text-xs font-medium tabular-nums outline-hidden transition-colors focus-visible:ring-2 focus-visible:ring-primary",
              answered ? "border-primary bg-primary-light text-primary" : "border-border-strong text-muted hover:bg-item-hover hover:text-foreground",
              active && "ring-2 ring-primary ring-offset-1 ring-offset-surface",
            )}
          >
            {index + 1}
          </button>
        );
      })}
    </nav>
  );
}

function QuizForm({ quiz }: { quiz: ReturnType<typeof useQuiz> }) {
  const { questions, draft, setAnswer } = quiz;
  const [current, setCurrent] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const total = questions.length;
  const index = Math.min(current, total - 1);
  const question = questions[index];
  const missing = questions.map((item, position) => ({ id: item.id, number: position + 1 })).filter((item) => !isAnswered(draft, item.id));
  const isLast = index === total - 1;
  const chosen = draft[question.id] ?? [];

  const toggle = (optionId: string, checked: boolean) => {
    if (question.type === "single") return setAnswer(question.id, checked ? [optionId] : []);
    const next = checked ? [...chosen.filter((id) => id !== optionId), optionId] : chosen.filter((id) => id !== optionId);
    setAnswer(question.id, question.options.map((option) => option.id).filter((id) => next.includes(id)));
  };

  const submit = async () => {
    setSubmitting(true);
    setSubmitError("");
    try {
      await quiz.submit();
    } catch (reason) {
      const message = (reason as Error).message;
      setSubmitError(message === "Failed to fetch" ? "Không kết nối được server của app" : message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3 text-sm">
          <span className="font-medium tabular-nums">
            Câu {index + 1}/{total}
          </span>
          <span className="text-xs text-muted tabular-nums">
            Đã trả lời {total - missing.length}/{total}
          </span>
        </div>
        <ProgressBar percent={((total - missing.length) / total) * 100} label={`Đã trả lời ${total - missing.length} trên ${total} câu`} />
        <QuestionChips questions={questions} current={index} draft={draft} onJump={setCurrent} />
      </div>

      <fieldset key={question.id} className="flex min-w-0 flex-col gap-3">
        <legend className="sr-only">Câu {index + 1}</legend>
        <div className="flex flex-wrap items-center gap-2">
          <span className={badge.neutral}>{KIND_LABEL[question.kind] ?? question.kind}</span>
          <span className="text-xs text-muted">{question.type === "multi" ? "Chọn tất cả đáp án đúng" : "Chọn một đáp án"}</span>
        </div>
        <Markdown className="font-medium [&_p]:m-0">{question.prompt}</Markdown>
        <div className="grid gap-2">
          {question.options.map((option) => (
            <OptionRow key={option.id} question={question} option={option} selected={chosen.includes(option.id)} onToggle={(checked) => toggle(option.id, checked)} />
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={button.outline} disabled={index === 0} onClick={() => setCurrent(index - 1)}>
          <ChevronLeft className="size-4 shrink-0" aria-hidden />
          Câu trước
        </button>
        <span className="flex-1" />
        {isLast ? (
          <button type="button" className={button.primary} disabled={missing.length > 0 || submitting} onClick={() => void submit()} aria-busy={submitting || undefined}>
            {submitting ? <LoaderCircle className="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden /> : <Send className="size-4 shrink-0" aria-hidden />}
            {submitting ? "Đang chấm…" : "Nộp"}
          </button>
        ) : (
          <button type="button" className={button.outline} onClick={() => setCurrent(index + 1)}>
            Câu sau
            <ChevronRight className="size-4 shrink-0" aria-hidden />
          </button>
        )}
      </div>

      {isLast && missing.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-sm text-muted" role="status">
          <span>Còn {missing.length} câu chưa trả lời:</span>
          {missing.map((item) => (
            <button key={item.id} type="button" className="cursor-pointer rounded-md px-1.5 font-medium text-primary tabular-nums underline-offset-2 outline-hidden hover:underline focus-visible:underline" onClick={() => setCurrent(item.number - 1)}>
              Câu {item.number}
            </button>
          ))}
        </div>
      )}
      {submitError && (
        <p role="alert" className="text-sm text-error-text">
          Không chấm được bài: {submitError}
        </p>
      )}
    </div>
  );
}

function QuizReview({ quiz }: { quiz: ReturnType<typeof useQuiz> }) {
  const result = quiz.result!;
  const byId = new Map(result.results.map((item) => [item.id, item]));
  const score = scoreOf(result.results);
  const percent = score.total ? (score.correct / score.total) * 100 : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm">
          Điểm: <strong className="text-lg font-semibold tabular-nums">{score.correct}/{score.total}</strong>
        </p>
        <span className="flex-1" />
        <button type="button" className={button.outline} onClick={quiz.retake}>
          <RotateCcw className="size-4 shrink-0" aria-hidden />
          Làm lại
        </button>
      </div>
      <ProgressBar percent={percent} label={`Đúng ${score.correct} trên ${score.total} câu`} />
      <ol className="grid gap-3">
        {quiz.questions.map((question, index) => {
          const graded = byId.get(question.id);
          const picked = result.answers[question.id] ?? [];
          const correctIds = graded?.answer ?? [];
          const shown = question.options.filter((option) => picked.includes(option.id) || correctIds.includes(option.id));
          const ok = graded?.correct ?? false;
          return (
            <li key={question.id} className="rounded-xl border border-border-strong p-3.5">
              <div className="flex items-start gap-2.5">
                {ok ? <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" aria-label="Đúng" /> : <CircleX className="mt-0.5 size-4 shrink-0 text-error-text" aria-label="Sai" />}
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <div className="flex min-w-0 gap-1.5 text-sm font-medium">
                    <span className="shrink-0 tabular-nums">{index + 1}.</span>
                    <Markdown className={INLINE_MD}>{question.prompt}</Markdown>
                  </div>
                  <ul className="grid gap-1.5">
                    {shown.map((option) => {
                      const isPicked = picked.includes(option.id);
                      const isCorrect = correctIds.includes(option.id);
                      return (
                        <li key={option.id} className={cx("flex min-w-0 flex-wrap items-start gap-x-2 gap-y-1 rounded-lg px-2.5 py-1.5", isCorrect ? "bg-success-bg" : "bg-neutral-bg")}>
                          <Markdown className={cx(INLINE_MD, "flex-1 basis-48 [&_p]:text-sm")}>{option.text}</Markdown>
                          <span className="flex shrink-0 gap-1.5 text-xs font-medium">
                            {isPicked && <span className={isCorrect ? "text-success" : "text-error-text"}>Bạn chọn</span>}
                            {isCorrect && <span className="text-success">Đáp án đúng</span>}
                          </span>
                        </li>
                      );
                    })}
                    {picked.length === 0 && <li className="px-2.5 text-xs text-muted">Bạn không chọn đáp án nào.</li>}
                  </ul>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function QuizCard({ exercise, trackId }: { exercise: Exercise; trackId: string }) {
  const quiz = useQuiz(exercise, trackId);
  if (quiz.status === "none") return null;
  const empty = quiz.status === "ready" && quiz.questions.length === 0;
  const report = writtenReportOf(exercise);

  return (
    <section aria-labelledby="nb-quiz-title" className={cx(card, "p-5")}>
      <div className="mb-4 flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <ClipboardList className="size-4 shrink-0 text-muted" aria-hidden />
          <h2 id="nb-quiz-title" className="text-base font-semibold">
            Báo cáo bài học
          </h2>
          <span className={badge.neutral}>Tuỳ chọn</span>
        </div>
        {report && <p className="text-xs text-muted">Trắc nghiệm tự kiểm tra, không thay cho {report}.</p>}
      </div>
      {quiz.stale && !quiz.result && <p className="mb-4 text-sm text-muted">Bộ câu hỏi đã đổi, kết quả cũ không còn hiệu lực. Làm lại để có điểm mới.</p>}
      {quiz.status === "loading" && <LoadingBlock text="Đang tải câu hỏi…" />}
      {quiz.status === "error" && <ErrorBlock title="Không tải được câu hỏi" reason={quiz.error} />}
      {empty && <p className="text-sm text-muted">Bộ câu hỏi đang trống.</p>}
      {quiz.status === "ready" && !empty && (quiz.result ? <QuizReview quiz={quiz} /> : <QuizForm key={quiz.quizHash} quiz={quiz} />)}
    </section>
  );
}

/** Khung phải của bài notebook: card giới thiệu + chạy test, và card trắc nghiệm (nếu bài có quiz.yaml). */
export function NotebookPanel({ exercise, trackId, done, onMarkDone }: { exercise: Exercise; trackId: string; done: boolean; onMarkDone: () => void }) {
  return (
    <div className="flex flex-col gap-3">
      <ExerciseIntroCard exercise={exercise} done={done} onMarkDone={onMarkDone} />
      <QuizCard exercise={exercise} trackId={trackId} />
    </div>
  );
}
