import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, ChevronDown, FolderOpen, Play } from "lucide-react";
import { findTrack, loadMarkdown, splitSections, type Module, type Section } from "../content";
import { moduleStats, useProgress } from "../progress";
import { Crumbs, Shell } from "../components/Shell";
import { ExerciseList, Notes } from "../components/shared";
import { Markdown } from "../components/Markdown";
import { button, card, Checkbox, cx, ErrorBlock, LoadingBlock, PageHeader, useCopy } from "../components/ui";
import { exerciseLink, moduleLink, trackLink } from "../links";
import { NotFound } from "./NotFound";

const TABS = [
  { id: "ly-thuyet", label: "Lý thuyết" },
  { id: "bai-tap", label: "Bài tập" },
  { id: "phong-van", label: "Phỏng vấn" },
  { id: "ghi-chu", label: "Ghi chú" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function useInterview(module: Module) {
  const [state, setState] = useState<{ status: "loading" | "ready" | "missing"; questions: Section[] }>({ status: "loading", questions: [] });
  useEffect(() => {
    let cancelled = false;
    loadMarkdown(`${module.dir}/interview.md`).then((raw) => {
      if (cancelled) return;
      setState(raw ? { status: "ready", questions: splitSections(raw).sections } : { status: "missing", questions: [] });
    });
    return () => {
      cancelled = true;
    };
  }, [module.dir]);
  return state;
}

function Toc({ trackId, module, activeSlug, onSelect }: { trackId: string; module: Module; activeSlug?: string; onSelect: (slug: string) => void }) {
  const api = useProgress();
  const read = new Set(api.of(trackId).sections[module.id] ?? []);
  const toggle = (slug: string, checked: boolean) =>
    api.update(trackId, (draft) => {
      const set = new Set(draft.sections[module.id] ?? []);
      if (checked) set.add(slug);
      else set.delete(slug);
      draft.sections[module.id] = [...set];
    });
  return (
    <section className={`${card} py-5`}>
      <header className="mb-1.5 px-5">
        <h2 className="text-base font-semibold">Mục lục</h2>
        <p className="mt-0.5 text-xs text-muted">
          Đã đọc {module.sections.filter((section) => read.has(section.slug)).length} / {module.sections.length}
        </p>
      </header>
      <ul className="flex flex-col gap-1 px-2">
        {module.sections.map((section) => {
          const active = section.slug === activeSlug;
          const isRead = read.has(section.slug);
          return (
            <li key={section.slug} className={cx("flex items-center gap-1 rounded-xl pl-1", active && "bg-secondary")}>
              <label className="grid size-9 shrink-0 cursor-pointer place-items-center">
                <Checkbox checked={isRead} onChange={(checked) => toggle(section.slug, checked)} label={`Đã đọc: ${section.title}`} />
              </label>
              <button
                type="button"
                onClick={() => onSelect(section.slug)}
                aria-current={active ? "true" : undefined}
                className={cx(
                  "flex h-10 min-w-0 flex-1 cursor-pointer items-center rounded-xl px-2 text-left text-sm outline-hidden transition-colors",
                  active ? "font-medium" : "hover:bg-item-hover focus-visible:bg-item-hover",
                  !active && isRead && "text-muted",
                )}
              >
                <span className="truncate" title={section.title}>
                  {section.title}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function ModulePage() {
  const { trackId, moduleId } = useParams();
  const [params, setParams] = useSearchParams();
  const track = findTrack(trackId);
  const module = track?.modules.find((item) => item.id === moduleId);
  const api = useProgress();
  const interview = useInterview(module ?? ({ dir: "" } as Module));
  const { copied, copy } = useCopy();

  if (!track || !module) return <NotFound />;

  const header = <div className="min-w-0 flex-1"><Crumbs items={[{ to: trackLink(track.id), label: track.name }]} /></div>;
  const progress = api.of(track.id);
  const stats = moduleStats(module, progress);
  const fresh = !stats.started;
  const nextExercise = module.exercises.find((exercise) => !progress.exercises[exercise.key]);
  const readSet = new Set(progress.sections[module.id] ?? []);
  const tab = (TABS.some((item) => item.id === params.get("tab")) ? params.get("tab") : "ly-thuyet") as TabId;
  const defaultSlug = module.sections.find((section) => !readSet.has(section.slug))?.slug ?? module.sections[0]?.slug;
  const activeIndex = Math.max(0, module.sections.findIndex((section) => section.slug === (params.get("s") ?? defaultSlug)));
  const active = module.sections[activeIndex];
  const nextSection = module.sections[activeIndex + 1];
  const selectSection = (slug: string) => {
    setParams({ s: slug });
    window.scrollTo({ top: 0 });
  };

  const pageHeader = (
    <PageHeader
      title={
        <>
          <span className="text-muted">{module.number} ·</span> {module.title}
        </>
      }
      description={module.summary}
      actions={
        <>
          <button type="button" className={button.outline} onClick={() => copy(module.dir)} title={module.dir}>
            <FolderOpen className="size-4 shrink-0" aria-hidden />
            {copied ? "Đã chép" : "Chép đường dẫn"}
          </button>
          {nextExercise && (
            <Link to={fresh ? moduleLink(track.id, module.id) : exerciseLink(track.id, nextExercise)} className={button.primary}>
              <Play className="size-4 shrink-0" aria-hidden />
              {fresh ? "Bắt đầu" : "Làm bài tiếp"}
            </Link>
          )}
        </>
      }
    />
  );

  if (api.status !== "ready") {
    return (
      <Shell header={header}>
        {pageHeader}
        <section className={card}>
          {api.status === "loading" ? <LoadingBlock text="Đang tải bài học…" /> : <ErrorBlock title="Không đọc được tiến độ học" reason={api.error} onRetry={api.reload} />}
        </section>
      </Shell>
    );
  }

  const counts: Record<TabId, string> = {
    "ly-thuyet": `${stats.read} / ${module.sections.length}`,
    "bai-tap": `${stats.exercisesDone} / ${module.exercises.length}`,
    "phong-van": interview.status === "ready" ? String(interview.questions.length) : "",
    "ghi-chu": "",
  };

  return (
    <Shell header={header}>
      <div className="max-w-[1600px]">
        {pageHeader}
        <div className="mb-5">
          <div className="scrollbar-clean overflow-x-auto">
            <div className="flex min-w-full gap-2 px-2 shadow-[inset_0_-1px_0_var(--border-strong)]" role="tablist">
              {TABS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={item.id === tab}
                  onClick={() => setParams(item.id === "ly-thuyet" ? {} : { tab: item.id })}
                  className={cx(
                    "relative box-content flex h-10 shrink-0 cursor-pointer items-center gap-1.5 rounded-xl px-2 pb-px text-sm font-medium outline-hidden after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full",
                    item.id === tab ? "text-foreground after:bg-foreground" : "text-foreground/70 after:bg-transparent hover:text-foreground focus-visible:text-foreground",
                  )}
                >
                  {item.label}
                  {counts[item.id] && <span className="text-xs text-muted tabular-nums">{counts[item.id]}</span>}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] 2xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex min-w-0 flex-col gap-5">
            {tab === "ly-thuyet" &&
              (active ? (
                <section className={`${card} p-5 sm:p-8`}>
                  {activeIndex === 0 && module.intro && <Markdown className="mb-6 max-w-[72ch] text-muted">{module.intro}</Markdown>}
                  <article className="max-w-[72ch]">
                    <h2 className="mb-2 text-lg font-semibold text-balance">{active.title}</h2>
                    <Markdown>{active.body}</Markdown>
                  </article>
                  <div className="mt-8 flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
                    <label className="flex min-h-10 cursor-pointer items-center gap-3 text-sm">
                      <Checkbox
                        checked={readSet.has(active.slug)}
                        onChange={(checked) =>
                          api.update(track.id, (draft) => {
                            const set = new Set(draft.sections[module.id] ?? []);
                            if (checked) set.add(active.slug);
                            else set.delete(active.slug);
                            draft.sections[module.id] = [...set];
                          })
                        }
                      />
                      Đã đọc xong phần này
                    </label>
                    {nextSection ? (
                      <button
                        type="button"
                        className={button.outline}
                        onClick={() => {
                          api.update(track.id, (draft) => {
                            draft.sections[module.id] = [...new Set([...(draft.sections[module.id] ?? []), active.slug])];
                          });
                          selectSection(nextSection.slug);
                        }}
                      >
                        <span className="truncate">{nextSection.title}</span>
                        <ArrowRight className="size-4 shrink-0" aria-hidden />
                      </button>
                    ) : (
                      <button type="button" className={button.outline} onClick={() => setParams({ tab: "bai-tap" })}>
                        Sang bài tập
                        <ArrowRight className="size-4 shrink-0" aria-hidden />
                      </button>
                    )}
                  </div>
                </section>
              ) : (
                <section className={card}>
                  <LoadingBlock text="Module này chưa có lý thuyết" />
                </section>
              ))}

            {tab === "bai-tap" && (
              <section className={`${card} py-5`}>
                <header className="mb-1.5 px-5">
                  <h2 className="text-base font-semibold">Bài tập</h2>
                </header>
                <div className="px-2">
                  <ExerciseList trackId={track.id} module={module} />
                </div>
              </section>
            )}

            {tab === "phong-van" && (
              <section className={card}>
                {interview.status === "loading" && <LoadingBlock text="Đang tải câu hỏi…" />}
                {interview.status === "missing" && <LoadingBlock text="Module này chưa có câu hỏi phỏng vấn" />}
                {interview.status === "ready" &&
                  interview.questions.map((question, index) => (
                    <details key={question.slug} className="group border-b border-border last:border-b-0">
                      <summary className="flex min-h-14 cursor-pointer list-none items-center gap-3 px-5 py-3 text-sm font-medium outline-hidden [&::-webkit-details-marker]:hidden">
                        <span className="w-6 shrink-0 text-xs text-muted tabular-nums">{index + 1}</span>
                        <span className="min-w-0 flex-1 text-pretty">{question.title}</span>
                        <ChevronDown className="size-4 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />
                      </summary>
                      <div className="px-5 pb-5 sm:pl-14">
                        <Markdown className="max-w-[72ch]">{question.body}</Markdown>
                      </div>
                    </details>
                  ))}
              </section>
            )}

            {tab === "ghi-chu" && <Notes trackId={track.id} noteKey={module.id} rows={14} />}
          </div>

          <div className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
            {module.sections.length > 0 && (
              <Toc
                trackId={track.id}
                module={module}
                activeSlug={tab === "ly-thuyet" ? active?.slug : undefined}
                onSelect={(slug) => {
                  selectSection(slug);
                }}
              />
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}

