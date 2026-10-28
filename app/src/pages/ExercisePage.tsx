import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Check, ChevronDown, FileCode, Lightbulb, Lock, RotateCcw } from "lucide-react";
import { findTrack, LEVEL_LABEL, loadMarkdown, solutionDir } from "../content";
import { now, useProgress } from "../progress";
import { Crumbs, Shell } from "../components/Shell";
import { ExerciseList, Notes } from "../components/shared";
import { Markdown } from "../components/Markdown";
import { badge, button, card, CodeLine, ErrorBlock, LoadingBlock, PageHeader } from "../components/ui";
import { moduleLink, trackLink } from "../links";
import { NotFound } from "./NotFound";

export function ExercisePage() {
  const { trackId, moduleId, level, slug } = useParams();
  const track = findTrack(trackId);
  const module = track?.modules.find((item) => item.id === moduleId);
  const exercise = module?.exercises.find((item) => item.level === level && item.slug === slug);
  const api = useProgress();
  const [solution, setSolution] = useState<{ status: "hidden" | "loading" | "ready" | "missing"; body: string }>({ status: "hidden", body: "" });

  useEffect(() => setSolution({ status: "hidden", body: "" }), [exercise?.key]);

  if (!track || !module || !exercise) return <NotFound />;

  const progress = api.of(track.id);
  const done = Boolean(progress.exercises[exercise.key]);
  const sameLevel = module.exercises.filter((item) => item.level === exercise.level);
  const position = sameLevel.findIndex((item) => item.key === exercise.key) + 1;
  const isAdvanced = exercise.level === "advanced";

  const showSolution = async () => {
    setSolution({ status: "loading", body: "" });
    const body = await loadMarkdown(`${solutionDir(exercise)}/SOLUTION.md`);
    setSolution(body ? { status: "ready", body } : { status: "missing", body: "" });
    api.update(track.id, (draft) => {
      draft.solutionsViewed[exercise.key] ??= now();
    });
  };
  const toggleDone = () =>
    api.update(track.id, (draft) => {
      if (draft.exercises[exercise.key]) delete draft.exercises[exercise.key];
      else draft.exercises[exercise.key] = now();
    });

  const header = (
    <div className="min-w-0 flex-1">
      <Crumbs
        items={[
          { to: trackLink(track.id), label: track.name },
          { to: moduleLink(track.id, module.id, "bai-tap"), label: `${module.number} · ${module.title}` },
        ]}
      />
    </div>
  );

  const pageHeader = (
    <PageHeader
      kicker={
        <div className="flex flex-wrap items-center gap-2">
          <span className={badge.neutral}>{LEVEL_LABEL[exercise.level]}</span>
          <span className="text-xs text-muted tabular-nums">
            Bài {LEVEL_LABEL[exercise.level][0]}
            {position} · {position} / {sameLevel.length} của mức này
          </span>
        </div>
      }
      title={exercise.title}
      actions={
        api.status === "ready" &&
        (done ? (
          <button type="button" className={button.outline} onClick={toggleDone}>
            <RotateCcw className="size-4 shrink-0" aria-hidden />
            Đánh dấu chưa xong
          </button>
        ) : (
          <button type="button" className={button.primary} onClick={toggleDone}>
            <Check className="size-4 shrink-0" aria-hidden />
            Đánh dấu xong
          </button>
        ))
      }
    />
  );

  if (api.status !== "ready") {
    return (
      <Shell header={header}>
        {pageHeader}
        <section className={card}>
          {api.status === "loading" ? <LoadingBlock text="Đang tải đề bài…" /> : <ErrorBlock title="Không đọc được tiến độ học" reason={api.error} onRetry={api.reload} />}
        </section>
      </Shell>
    );
  }

  return (
    <Shell header={header}>
      <div className="max-w-[1600px]">
        {pageHeader}
        {done && (
          <p className="mb-5 flex items-center gap-2 text-sm text-success">
            <Check className="size-4 shrink-0" aria-hidden />
            Đã xong bài này
          </p>
        )}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex min-w-0 flex-col gap-5">
            <section className={`${card} p-5 sm:p-6`}>
              <h2 className="mb-3 text-base font-semibold">Đề bài</h2>
              {exercise.goal && <Markdown className="mb-4 max-w-[72ch] text-muted">{exercise.goal}</Markdown>}
              <Markdown className="max-w-[72ch]">{exercise.task || "Đề bài chưa có nội dung."}</Markdown>
            </section>

            <section className={`${card} p-5 sm:p-6`}>
              <h2 className="mb-3 text-base font-semibold">Làm bài</h2>
              <p className="text-sm text-muted">Thư mục</p>
              <div className="mt-1.5">
                <CodeLine text={exercise.dir} label="Chép đường dẫn" />
              </div>
              {exercise.files.length > 0 && (
                <ul className="mt-3 grid gap-1 text-sm">
                  {exercise.files.map((file) => (
                    <li key={file.path} className="flex items-center gap-2.5 py-1">
                      <FileCode className="size-4 shrink-0 text-muted" aria-hidden />
                      <code className="min-w-0 flex-1 truncate font-mono text-[13px]">{file.path}</code>
                      {file.note && <span className="shrink-0 text-xs text-muted">{file.note}</span>}
                    </li>
                  ))}
                </ul>
              )}
              {exercise.run.length > 0 && (
                <>
                  <p className="mt-5 text-sm text-muted">Chạy kiểm tra</p>
                  <div className="mt-1.5 grid grid-cols-[minmax(0,1fr)] gap-2">
                    {exercise.run.map((command) => (
                      <CodeLine key={command} text={command} />
                    ))}
                  </div>
                </>
              )}
              {exercise.criteria.length > 0 && (
                <>
                  <h3 className="mt-5 text-sm font-medium">Tiêu chí đạt</h3>
                  <ul className="mt-2 grid gap-1.5 text-sm">
                    {exercise.criteria.map((criterion) => (
                      <li key={criterion} className="flex items-start gap-2.5">
                        <Check className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
                        <Markdown className="min-w-0 [&_p]:m-0 [&_p]:text-sm">{criterion}</Markdown>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>

            <section className={card}>
              {exercise.hints.map((hint) => (
                <details key={hint.title} className="group border-b border-border">
                  <summary className="flex h-14 cursor-pointer list-none items-center gap-3 px-5 text-sm font-medium outline-hidden [&::-webkit-details-marker]:hidden">
                    <Lightbulb className="size-4 shrink-0 text-muted" aria-hidden />
                    <span className="flex-1">{hint.title}</span>
                    <ChevronDown className="size-4 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />
                  </summary>
                  <div className="px-5 pb-4 pl-12">
                    <Markdown className="[&_p]:text-sm">{hint.body}</Markdown>
                  </div>
                </details>
              ))}
              {solution.status === "ready" ? (
                <div className="p-5 sm:p-6">
                  <h2 className="mb-3 text-base font-semibold">{isAdvanced ? "Hướng làm và rubric" : "Lời giải mẫu"}</h2>
                  {!isAdvanced && (
                    <div className="mb-4">
                      <CodeLine text={`SOLUTION=1 uv run pytest ${exercise.dir} -q`} />
                    </div>
                  )}
                  <Markdown className="max-w-[72ch]">{solution.body}</Markdown>
                </div>
              ) : (
                <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Lock className="size-4 shrink-0 text-muted" aria-hidden />
                    <div>
                      <p className="text-sm font-medium">{isAdvanced ? "Hướng làm và rubric" : "Lời giải mẫu"}</p>
                      <p className="text-xs text-muted">
                        {solution.status === "missing" ? "Bài này chưa có lời giải." : "Thử tự làm trước, xem lời giải khi đã chạy test."}
                      </p>
                    </div>
                  </div>
                  {solution.status !== "missing" && (
                    <button type="button" className={`${button.outline} shrink-0`} onClick={showSolution} aria-busy={solution.status === "loading" || undefined}>
                      {isAdvanced ? "Xem hướng làm" : "Xem lời giải"}
                    </button>
                  )}
                </div>
              )}
            </section>
          </div>

          <div className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
            <Notes trackId={track.id} noteKey={exercise.key} />
            <section className={`${card} py-5`}>
              <header className="mb-1.5 px-5">
                <h2 className="text-base font-semibold">Bài trong module</h2>
              </header>
              <div className="px-2">
                <ExerciseList trackId={track.id} module={module} currentKey={exercise.key} />
              </div>
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}
