import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronDown, ChevronLeft, ChevronRight, Lightbulb, Lock, RotateCcw } from "lucide-react";
import { findTrack, LEVEL_LABEL, loadMarkdown, solutionDir, type Exercise, type Module } from "../content";
import { now, useProgress } from "../progress";
import { Crumbs, Shell } from "../components/Shell";
import { ExerciseList, Notes } from "../components/shared";
import { Markdown } from "../components/Markdown";
import { badge, button, card, CodeLine, cx, ErrorBlock, LoadingBlock } from "../components/ui";
import { Workspace } from "../code/Workspace";
import { exerciseKind, quizVariantOf } from "../code/exerciseKind";
import { NotebookPanel, QuizCard } from "../code/NotebookPanel";
import { QuizOnlyPanel } from "../code/QuizOnlyPanel";
import { useSplit } from "../code/useSplit";
import { exerciseLink, moduleLink, trackLink } from "../links";
import { NotFound } from "./NotFound";

const TABS = [
  { id: "de-bai", label: "Đề bài" },
  { id: "loi-giai", label: "Gợi ý & lời giải" },
  { id: "ghi-chu", label: "Ghi chú" },
  { id: "cac-bai", label: "Các bài" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function Statement({ exercise, position, total }: { exercise: Exercise; position: number; total: number }) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className={badge.neutral}>{LEVEL_LABEL[exercise.level]}</span>
        <span className="text-xs text-muted tabular-nums">
          Bài {LEVEL_LABEL[exercise.level][0]}
          {position} · {position} / {total} của mức này
        </span>
      </div>
      <h1 className="mt-2 mb-4 text-xl font-semibold text-balance">{exercise.title}</h1>
      {exercise.goal && <Markdown className="mb-4 text-muted">{exercise.goal}</Markdown>}
      <Markdown>{exercise.task || "Đề bài chưa có nội dung."}</Markdown>
      {exercise.criteria.length > 0 && (
        <>
          <h2 className="mt-6 text-base font-semibold">Tiêu chí đạt</h2>
          <ul className="mt-2 grid gap-1.5 text-sm">
            {exercise.criteria.map((criterion) => (
              <li key={criterion} className="flex items-start gap-2.5">
                <Check className="mt-1 size-4 shrink-0 text-muted" aria-hidden />
                <Markdown className="min-w-0 [&_p]:m-0">{criterion}</Markdown>
              </li>
            ))}
          </ul>
        </>
      )}
      {exercise.run.length > 0 && (
        <>
          <h2 className="mt-6 mb-2 text-base font-semibold">Chạy từ terminal</h2>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-2">
            {exercise.run.map((command) => (
              <CodeLine key={command} text={command} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function Solution({ exercise, onViewed }: { exercise: Exercise; onViewed: () => void }) {
  const [solution, setSolution] = useState<{ status: "hidden" | "loading" | "ready" | "missing"; body: string }>({ status: "hidden", body: "" });
  const isAdvanced = exercise.level === "advanced";
  const title = isAdvanced ? "Hướng làm và rubric" : "Lời giải mẫu";

  const show = async () => {
    setSolution({ status: "loading", body: "" });
    const body = await loadMarkdown(`${solutionDir(exercise)}/SOLUTION.md`);
    setSolution(body ? { status: "ready", body } : { status: "missing", body: "" });
    onViewed();
  };

  return (
    <>
      {exercise.hints.length === 0 && <p className="mb-4 text-sm text-muted">Bài này không có gợi ý.</p>}
      {exercise.hints.length > 0 && (
        <div className="mb-5 overflow-hidden rounded-xl border border-border-strong">
          {exercise.hints.map((hint) => (
            <details key={hint.title} className="group border-b border-border-strong last:border-b-0">
              <summary className="flex h-12 cursor-pointer list-none items-center gap-3 px-4 text-sm font-medium outline-hidden focus-visible:bg-item-hover [&::-webkit-details-marker]:hidden">
                <Lightbulb className="size-4 shrink-0 text-muted" aria-hidden />
                <span className="flex-1">{hint.title}</span>
                <ChevronDown className="size-4 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />
              </summary>
              <div className="px-4 pb-4 pl-11">
                <Markdown className="[&_p]:text-sm">{hint.body}</Markdown>
              </div>
            </details>
          ))}
        </div>
      )}
      {solution.status === "ready" ? (
        <>
          <h2 className="mb-3 text-base font-semibold">{title}</h2>
          {!isAdvanced && (
            <div className="mb-4">
              <CodeLine text={`SOLUTION=1 uv run pytest ${exercise.dir} -q`} />
            </div>
          )}
          <Markdown>{solution.body}</Markdown>
        </>
      ) : (
        <div className="flex flex-col gap-3 rounded-xl border border-border-strong p-4 sm:flex-row sm:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Lock className="size-4 shrink-0 text-muted" aria-hidden />
            <div>
              <p className="text-sm font-medium">{title}</p>
              <p className="text-xs text-muted">{solution.status === "missing" ? "Bài này chưa có lời giải." : "Thử tự làm trước, xem lời giải khi đã chạy test."}</p>
            </div>
          </div>
          {solution.status !== "missing" && (
            <button type="button" className={cx(button.outline, "shrink-0")} onClick={show} aria-busy={solution.status === "loading" || undefined}>
              {isAdvanced ? "Xem hướng làm" : "Xem lời giải"}
            </button>
          )}
        </div>
      )}
    </>
  );
}

function ProblemPanel({ trackId, module, exercise }: { trackId: string; module: Module; exercise: Exercise }) {
  const api = useProgress();
  const [tab, setTab] = useState<TabId>("de-bai");
  const sameLevel = module.exercises.filter((item) => item.level === exercise.level);
  const position = sameLevel.findIndex((item) => item.key === exercise.key) + 1;

  useEffect(() => setTab("de-bai"), [exercise.key]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div role="tablist" aria-label="Nội dung bài" className="scrollbar-clean flex h-11 shrink-0 items-stretch overflow-x-auto border-b border-border-strong px-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={cx(
              "relative shrink-0 cursor-pointer px-3 text-sm outline-hidden transition-colors",
              tab === item.id ? "font-medium text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary" : "text-muted hover:text-foreground focus-visible:text-foreground",
            )}
          >
            {item.label}
            {item.id === "loi-giai" && exercise.hints.length > 0 && <span className="ml-1.5 text-xs text-muted tabular-nums">{exercise.hints.length}</span>}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
        {tab === "de-bai" && <Statement exercise={exercise} position={position} total={sameLevel.length} />}
        {tab === "loi-giai" && (
          <Solution
            key={exercise.key}
            exercise={exercise}
            onViewed={() =>
              api.update(trackId, (draft) => {
                draft.solutionsViewed[exercise.key] ??= now();
              })
            }
          />
        )}
        {tab === "ghi-chu" && <Notes trackId={trackId} noteKey={exercise.key} rows={12} bare />}
        {tab === "cac-bai" && (
          <div className="-mx-3">
            <ExerciseList trackId={trackId} module={module} currentKey={exercise.key} />
          </div>
        )}
      </div>
    </div>
  );
}

function StepLink({ trackId, target, label, Icon }: { trackId: string; target?: Exercise; label: string; Icon: typeof ChevronLeft }) {
  if (!target) {
    return (
      <span className={cx(button.icon, "pointer-events-none opacity-40")} aria-hidden>
        <Icon className="size-4" />
      </span>
    );
  }
  return (
    <Link to={exerciseLink(trackId, target)} className={button.icon} aria-label={`${label}: ${target.title}`} title={target.title}>
      <Icon className="size-4" aria-hidden />
    </Link>
  );
}

export function ExercisePage() {
  const { trackId, moduleId, level, slug } = useParams();
  const track = findTrack(trackId);
  const module = track?.modules.find((item) => item.id === moduleId);
  const exercise = module?.exercises.find((item) => item.level === level && item.slug === slug);
  const api = useProgress();
  const split = useSplit({ storageKey: "split:exercise", initial: 0.42, axis: "x", min: 0.25, max: 0.7 });

  if (!track || !module || !exercise) return <NotFound />;

  const progress = api.of(track.id);
  const done = Boolean(progress.exercises[exercise.key]);
  const index = module.exercises.findIndex((item) => item.key === exercise.key);
  const previous = module.exercises[index - 1];
  const next = module.exercises[index + 1];
  const setDone = (value: boolean) =>
    api.update(track.id, (draft) => {
      if (value) draft.exercises[exercise.key] ??= now();
      else delete draft.exercises[exercise.key];
    });

  const header = (
    <>
      <div className="min-w-0 flex-1">
        <Crumbs
          items={[
            { to: trackLink(track.id), label: track.name },
            { to: moduleLink(track.id, module.id, "bai-tap"), label: `${module.number} · ${module.title}` },
          ]}
        />
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <StepLink trackId={track.id} target={previous} label="Bài trước" Icon={ChevronLeft} />
        <StepLink trackId={track.id} target={next} label="Bài sau" Icon={ChevronRight} />
      </div>
      {api.status === "ready" &&
        (done ? (
          <button type="button" className={cx(button.outline, "shrink-0")} onClick={() => setDone(false)} title="Đánh dấu chưa xong" aria-label="Đã xong, bấm để đánh dấu chưa xong">
            <RotateCcw className="size-4 shrink-0" aria-hidden />
            <span className="hidden sm:inline">Đã xong</span>
          </button>
        ) : (
          <button type="button" className={cx(button.primary, "shrink-0")} onClick={() => setDone(true)} aria-label="Đánh dấu xong">
            <Check className="size-4 shrink-0" aria-hidden />
            <span className="hidden sm:inline">Đánh dấu xong</span>
          </button>
        ))}
    </>
  );

  if (api.status !== "ready") {
    return (
      <Shell header={header}>
        <section className={card}>
          {api.status === "loading" ? <LoadingBlock text="Đang tải đề bài…" /> : <ErrorBlock title="Không đọc được tiến độ học" reason={api.error} onRetry={api.reload} />}
        </section>
      </Shell>
    );
  }

  const kind = exerciseKind(exercise);

  return (
    <Shell header={header} fill>
      <div ref={split.container} style={split.style} className="flex flex-col gap-3 lg:h-full lg:flex-row lg:gap-0">
        <section aria-label="Đề bài" className={cx(card, "min-h-0 overflow-hidden max-lg:max-h-[70vh] lg:w-[calc(var(--split-a)*100%)] lg:shrink-0")}>
          <ProblemPanel trackId={track.id} module={module} exercise={exercise} />
        </section>
        <div {...split.handleProps} aria-label="Kéo để đổi độ rộng hai khung" className="group relative hidden w-3 shrink-0 cursor-col-resize outline-hidden lg:block">
          <div className="absolute inset-y-6 left-1/2 w-1 -translate-x-1/2 rounded-full transition-colors group-hover:bg-primary group-focus-visible:bg-primary group-data-dragging:bg-primary" />
        </div>
        {kind === "code" ? (
          <div className={cx("flex min-w-0 flex-col gap-3 lg:min-h-0 lg:flex-1 lg:overflow-y-auto", split.dragging && "select-none")}>
            <section aria-label="Code" className={cx(card, "h-[85vh] shrink-0 overflow-hidden lg:h-full")}>
              <Workspace key={exercise.key} exercise={exercise} done={done} onMarkDone={() => setDone(true)} />
            </section>
            <QuizCard key={exercise.key} exercise={exercise} trackId={track.id} variant={quizVariantOf(exercise)} />
          </div>
        ) : (
          <section aria-label="Làm bài" className={cx("min-w-0 lg:min-h-0 lg:flex-1 lg:overflow-y-auto", split.dragging && "select-none")}>
            {kind === "notebook" ? (
              <NotebookPanel key={exercise.key} exercise={exercise} trackId={track.id} done={done} onMarkDone={() => setDone(true)} />
            ) : (
              <QuizOnlyPanel key={exercise.key} exercise={exercise} trackId={track.id} done={done} onMarkDone={() => setDone(true)} />
            )}
          </section>
        )}
      </div>
    </Shell>
  );
}
