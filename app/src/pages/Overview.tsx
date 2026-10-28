import { Link } from "react-router-dom";
import { Play } from "lucide-react";
import { LEVEL_LABEL, TRACKS, type Track } from "../content";
import { currentModule, moduleStats, nextItems, trackStats, useProgress, type NextItem } from "../progress";
import { Shell } from "../components/Shell";
import { button, card, ErrorBlock, Icon, LoadingBlock, ProgressBar } from "../components/ui";
import { moduleLink, nextItemLink, trackLink } from "../links";

function describe(item: NextItem) {
  const where = `Module ${item.module.number} · ${item.module.title}`;
  if (item.kind === "section") return { title: item.title, meta: `${where} · Lý thuyết` };
  if (item.kind === "exercise") return { title: item.exercise.title, meta: `${where} · ${LEVEL_LABEL[item.exercise.level]}` };
  return { title: item.title, meta: `Capstone · sau Module ${item.module.number}` };
}

function NextUp({ track }: { track: Track }) {
  const progress = useProgress().of(track.id);
  const stats = trackStats(track, progress);
  const [next] = nextItems(track, progress, 1);
  const module = currentModule(track, progress);

  if (!next) {
    return (
      <section className={`${card} p-5 sm:p-6`}>
        <p className="text-sm text-muted">{track.name}</p>
        <h2 className="mt-1 text-lg font-semibold">Bạn đã hoàn thành cả lộ trình</h2>
        <p className="mt-1 text-sm text-muted">Ôn lại câu hỏi phỏng vấn ở từng module, hoặc thêm một track mới trong thư mục tracks/.</p>
      </section>
    );
  }

  const fresh = stats.exercisesDone === 0 && stats.read === 0;
  const { title, meta } = fresh && module ? { title: `Module ${module.number} · ${module.title}`, meta: `${module.sections.length} phần lý thuyết · ${module.exercises.length} bài tập` } : describe(next);
  const modulePercent = module ? Math.round(((moduleStats(module, progress).read + moduleStats(module, progress).exercisesDone) / Math.max(1, module.sections.length + module.exercises.length)) * 100) : 0;

  return (
    <section className={`${card} flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:gap-6 sm:p-6`}>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-muted">
          {fresh ? "Bắt đầu" : "Học tiếp"} · {track.name}
        </p>
        <h2 className="mt-1 text-lg font-semibold text-balance">{title}</h2>
        <p className="mt-1 text-sm text-muted">{meta}</p>
        {!fresh && module && (
          <div className="mt-4 flex max-w-sm items-center gap-3">
            <ProgressBar percent={modulePercent} label={`Tiến độ module ${module.number}`} className="flex-1" />
            <span className="shrink-0 text-xs text-muted tabular-nums">Module {modulePercent}%</span>
          </div>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Link to={fresh && module ? moduleLink(track.id, module.id) : nextItemLink(track.id, next)} className={button.primary}>
          <Play className="size-4 shrink-0" aria-hidden />
          {fresh ? "Bắt đầu học" : "Tiếp tục"}
        </Link>
        {!fresh && module && (
          <Link to={moduleLink(track.id, module.id)} className={button.outline}>
            Xem module
          </Link>
        )}
      </div>
    </section>
  );
}

function StatRow({ tracks }: { tracks: Track[] }) {
  const progress = useProgress();
  const totals = tracks.reduce(
    (sum, track) => {
      const stats = trackStats(track, progress.of(track.id));
      return {
        exercises: sum.exercises + stats.exercises,
        exercisesDone: sum.exercisesDone + stats.exercisesDone,
        modules: sum.modules + track.modules.length,
        modulesDone: sum.modulesDone + stats.modulesDone,
        sections: sum.sections + stats.sections,
        read: sum.read + stats.read,
        milestones: sum.milestones + stats.milestones,
        milestonesDone: sum.milestonesDone + stats.milestonesDone,
      };
    },
    { exercises: 0, exercisesDone: 0, modules: 0, modulesDone: 0, sections: 0, read: 0, milestones: 0, milestonesDone: 0 },
  );
  const stats = [
    ["Bài tập đã xong", `${totals.exercisesDone} / ${totals.exercises}`],
    ["Module hoàn thành", `${totals.modulesDone} / ${totals.modules}`],
    ["Lý thuyết đã đọc", `${totals.read} / ${totals.sections}`],
    ["Milestone capstone", `${totals.milestonesDone} / ${totals.milestones}`],
  ];
  return (
    <section className={`${card} grid grid-cols-2 lg:grid-cols-4`}>
      {stats.map(([label, value], index) => (
        <div
          key={label}
          className={[
            "p-5",
            index % 2 ? "border-l border-border" : "",
            index >= 2 ? "border-t border-border lg:border-t-0" : "",
            index === 2 ? "lg:border-l" : "",
          ].join(" ")}
        >
          <p className="text-sm text-muted">{label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
        </div>
      ))}
    </section>
  );
}

function TrackGrid() {
  const progress = useProgress();
  return (
    <section>
      <h2 className="mb-3 text-base font-semibold">Lộ trình</h2>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {TRACKS.map((track) => {
          if (track.status === "soon") {
            return (
              <div key={track.id} className={`${card} flex flex-col p-5`}>
                <div className="flex items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-background text-muted">
                    <Icon name={track.icon} className="size-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground/70">{track.name}</p>
                    <p className="text-xs text-muted">Sắp có</p>
                  </div>
                </div>
                <p className="mt-4 text-sm text-pretty text-muted">
                  Chưa có nội dung. Thêm module vào <code className="font-mono text-xs">tracks/{track.id}</code> để mở track này.
                </p>
              </div>
            );
          }
          const stats = trackStats(track, progress.of(track.id));
          const module = currentModule(track, progress.of(track.id));
          return (
            <Link key={track.id} to={trackLink(track.id)} className={`${card} group flex flex-col p-5 outline-hidden`}>
              <div className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-background">
                  <Icon name={track.icon} className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium group-hover:underline group-focus-visible:underline">{track.name}</p>
                  <p className="text-xs text-muted">
                    {track.modules.length} module{track.capstone ? ` · capstone ${track.capstone.title}` : ""}
                  </p>
                </div>
                <span className="shrink-0 text-sm font-medium tabular-nums">{stats.percent}%</span>
              </div>
              <ProgressBar percent={stats.percent} label={`Tiến độ ${track.name}`} className="mt-4" />
              <p className="mt-2 text-xs text-muted">
                {stats.exercisesDone} / {stats.exercises} bài tập ·{" "}
                {stats.exercisesDone + stats.read === 0 ? "Chưa bắt đầu" : module ? `Đang học Module ${module.number}` : "Đã xong"}
              </p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export function Overview() {
  const progress = useProgress();
  const active = TRACKS.filter((track) => track.status === "active" && track.modules.length > 0);
  const focus =
    active.find((track) => {
      const stats = trackStats(track, progress.of(track.id));
      return stats.exercisesDone + stats.read > 0 && stats.percent < 100;
    }) ?? active[0];

  return (
    <Shell header={<h1 className="min-w-0 truncate text-base font-semibold">Tổng quan</h1>}>
      {progress.status === "loading" && (
        <section className={card}>
          <LoadingBlock text="Đang tải tiến độ…" />
        </section>
      )}
      {progress.status === "error" && (
        <section className={card}>
          <ErrorBlock title="Không đọc được tiến độ học" reason={progress.error} onRetry={progress.reload} />
        </section>
      )}
      {progress.status === "ready" && (
        <div className="flex flex-col gap-5">
          {focus && <NextUp track={focus} />}
          <StatRow tracks={active} />
          <TrackGrid />
        </div>
      )}
    </Shell>
  );
}
