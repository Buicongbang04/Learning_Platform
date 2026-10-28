import { Link, useParams } from "react-router-dom";
import { Check, Circle, CircleCheck, CircleDot } from "lucide-react";
import { findTrack, LEVEL_LABEL, type Module, type Track } from "../content";
import { currentModule, moduleStats, trackStats, useProgress, type TrackProgress } from "../progress";
import { Shell } from "../components/Shell";
import { badge, card, cx, ErrorBlock, LoadingBlock, PageHeader, ProgressBar } from "../components/ui";
import { milestoneLink, moduleLink } from "../links";
import { NotFound } from "./NotFound";

function TrackHeader({ track, stats }: { track: Track; stats?: ReturnType<typeof trackStats> }) {
  return (
    <PageHeader
      title={track.name}
      description={track.description}
      actions={
        stats && (
          <div className="w-full sm:w-56">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-muted">Hoàn thành</span>
              <span className="text-sm font-medium tabular-nums">{stats.percent}%</span>
            </div>
            <ProgressBar percent={stats.percent} label={`Tiến độ ${track.name}`} className="mt-2" />
            <p className="mt-1.5 text-xs text-muted">
              {stats.exercisesDone} / {stats.exercises} bài tập
            </p>
          </div>
        )
      }
    />
  );
}

function ModuleRow({ track, module, progress, isCurrent, isFresh }: { track: Track; module: Module; progress: TrackProgress; isCurrent: boolean; isFresh: boolean }) {
  const stats = moduleStats(module, progress);
  const status = stats.complete ? "done" : isCurrent ? (isFresh ? "next" : "now") : "todo";
  return (
    <li className="relative">
      <Link
        to={moduleLink(track.id, module.id)}
        className="group flex items-center gap-3 rounded-xl px-3 py-3 outline-hidden transition-colors hover:bg-item-hover focus-visible:bg-item-hover"
      >
        {status === "done" ? (
          <span className="relative z-10 grid size-8 shrink-0 place-items-center rounded-full bg-success-bg text-success">
            <Check className="size-4" aria-label="Đã xong" />
          </span>
        ) : status === "todo" ? (
          <span className="relative z-10 grid size-8 shrink-0 place-items-center rounded-full border border-border-strong bg-surface text-xs font-medium text-muted tabular-nums">
            {module.number}
          </span>
        ) : (
          <span className="relative z-10 grid size-8 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground tabular-nums">
            {module.number}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <p className="min-w-0 truncate text-sm font-medium" title={module.title}>
              <span className="text-muted">{module.number} ·</span> {module.title}
            </p>
            {status === "now" && <span className={badge.now}>Đang học</span>}
            {status === "next" && <span className={badge.now}>Bắt đầu ở đây</span>}
          </div>
          <p className="mt-0.5 truncate text-xs text-muted">{module.hasContent ? module.topics.join(" · ") : "Đang soạn nội dung"}</p>
        </div>
        <p className="hidden shrink-0 items-center gap-x-1.5 self-center text-xs xl:flex">
          {stats.byLevel.map((level, index) => (
            <span key={level.level} className="flex items-center gap-x-1.5 whitespace-nowrap">
              {index > 0 && <span className="text-muted">·</span>}
              <span className="text-muted" title={LEVEL_LABEL[level.level]}>
                {LEVEL_LABEL[level.level][0]}
              </span>
              <span className={cx("tabular-nums", level.total > 0 && level.done === level.total ? "text-foreground" : "text-muted")}>
                {level.done}/{level.total}
              </span>
            </span>
          ))}
        </p>
        <span className={cx("w-14 shrink-0 self-center text-right text-sm tabular-nums", stats.complete ? "font-medium text-success" : "text-muted")}>
          {stats.exercisesDone} / {module.exercises.length}
        </span>
      </Link>
    </li>
  );
}

export function TrackPage() {
  const { trackId } = useParams();
  const track = findTrack(trackId);
  const api = useProgress();
  if (!track || track.status === "soon") return <NotFound />;

  const header = <p className="min-w-0 truncate text-base font-semibold">Lộ trình</p>;
  if (api.status !== "ready") {
    return (
      <Shell header={header}>
        <TrackHeader track={track} />
        <section className={card}>
          {api.status === "loading" ? <LoadingBlock text="Đang tải lộ trình…" /> : <ErrorBlock title="Không đọc được tiến độ học" reason={api.error} onRetry={api.reload} />}
        </section>
      </Shell>
    );
  }

  const progress = api.of(track.id);
  const stats = trackStats(track, progress);
  const current = currentModule(track, progress);
  const fresh = stats.exercisesDone + stats.read === 0;

  return (
    <Shell header={header}>
      <div className="max-w-[1600px]">
        <TrackHeader track={track} stats={stats} />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] 2xl:grid-cols-[minmax(0,1fr)_24rem]">
          <section className={`${card} py-3 lg:self-start`}>
            <ol className="relative flex flex-col gap-1 px-2 before:absolute before:top-7 before:bottom-7 before:left-[1.75rem] before:w-px before:bg-border-strong">
              {track.modules.map((module) => (
                <ModuleRow key={module.id} track={track} module={module} progress={progress} isCurrent={module.id === current?.id} isFresh={fresh} />
              ))}
            </ol>
          </section>
          <div className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
            <section className={`${card} p-5`}>
              <h2 className="mb-4 text-base font-semibold">Tiến độ</h2>
              <dl className="grid gap-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Bài tập</dt>
                  <dd className="font-medium tabular-nums">
                    {stats.exercisesDone} / {stats.exercises}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Lý thuyết đã đọc</dt>
                  <dd className="font-medium tabular-nums">
                    {stats.read} / {stats.sections}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Module hoàn thành</dt>
                  <dd className="font-medium tabular-nums">
                    {stats.modulesDone} / {track.modules.length}
                  </dd>
                </div>
              </dl>
            </section>
            {track.capstone && (
              <section className={`${card} py-5`}>
                <header className="mb-1.5 px-5">
                  <h2 className="text-base font-semibold">Capstone · {track.capstone.title}</h2>
                  <p className="mt-0.5 text-xs text-muted">
                    {stats.milestonesDone} / {stats.milestones} milestone
                  </p>
                </header>
                <ol className="flex flex-col gap-1 px-2">
                  {track.capstone.milestones.map((milestone) => {
                    const done = Boolean(progress.milestones[milestone.id]);
                    const now = !done && current?.id === milestone.after;
                    const after = track.modules.find((module) => module.id === milestone.after);
                    return (
                      <li key={milestone.id}>
                        <Link
                          to={milestoneLink(track.id, milestone.id)}
                          className="flex items-start gap-2.5 rounded-xl px-3 py-2 outline-hidden transition-colors hover:bg-item-hover focus-visible:bg-item-hover"
                        >
                          {done ? (
                            <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" aria-label="Đã xong" />
                          ) : now ? (
                            <CircleDot className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                          ) : (
                            <Circle className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
                          )}
                          <div className="min-w-0 flex-1">
                            <p className={cx("text-sm text-pretty", done && "text-muted", now && "font-medium")}>{milestone.title}</p>
                            <p className="text-xs text-muted">Sau module {after?.number ?? milestone.after}</p>
                          </div>
                        </Link>
                      </li>
                    );
                  })}
                </ol>
              </section>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
