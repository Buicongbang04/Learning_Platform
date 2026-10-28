import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, Circle, CircleCheck, RotateCcw } from "lucide-react";
import { findTrack, loadMarkdown } from "../content";
import { now, useProgress } from "../progress";
import { Crumbs, Shell } from "../components/Shell";
import { Notes } from "../components/shared";
import { Markdown } from "../components/Markdown";
import { button, card, cx, ErrorBlock, LoadingBlock, PageHeader } from "../components/ui";
import { milestoneLink, trackLink } from "../links";
import { NotFound } from "./NotFound";

/* Màn milestone capstone: ngoài phạm vi wireframe, dựng theo khuôn màn Bài tập. */
export function MilestonePage() {
  const { trackId, milestoneId } = useParams();
  const track = findTrack(trackId);
  const milestone = track?.capstone?.milestones.find((item) => item.id === milestoneId);
  const api = useProgress();
  const [doc, setDoc] = useState<{ status: "loading" | "ready" | "missing"; body: string }>({ status: "loading", body: "" });

  useEffect(() => {
    if (!milestone) return;
    let cancelled = false;
    setDoc({ status: "loading", body: "" });
    loadMarkdown(milestone.doc).then((raw) => {
      if (!cancelled) setDoc(raw ? { status: "ready", body: raw.replace(/^# .+\n/, "") } : { status: "missing", body: "" });
    });
    return () => {
      cancelled = true;
    };
  }, [milestone]);

  if (!track || !track.capstone || !milestone) return <NotFound />;

  const progress = api.of(track.id);
  const done = Boolean(progress.milestones[milestone.id]);
  const index = track.capstone.milestones.indexOf(milestone);
  const after = track.modules.find((module) => module.id === milestone.after);
  const toggleDone = () =>
    api.update(track.id, (draft) => {
      if (draft.milestones[milestone.id]) delete draft.milestones[milestone.id];
      else draft.milestones[milestone.id] = now();
    });

  return (
    <Shell header={<div className="min-w-0 flex-1"><Crumbs items={[{ to: trackLink(track.id), label: track.name }]} /></div>}>
      <div className="max-w-[1600px]">
        <PageHeader
          kicker={
            <p className="text-xs text-muted tabular-nums">
              Capstone · Milestone {index + 1} / {track.capstone.milestones.length} · sau Module {after?.number}
            </p>
          }
          title={milestone.title}
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
        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <section className={`${card} p-5 sm:p-6`}>
            {doc.status === "loading" && <LoadingBlock text="Đang tải milestone…" />}
            {doc.status === "missing" && <ErrorBlock title="Chưa có tài liệu cho milestone này" reason={milestone.doc} />}
            {doc.status === "ready" && <Markdown className="max-w-[72ch]">{doc.body}</Markdown>}
          </section>
          <div className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
            {api.status === "ready" && <Notes trackId={track.id} noteKey={`capstone/${milestone.id}`} />}
            <section className={`${card} py-5`}>
              <header className="mb-1.5 px-5">
                <h2 className="text-base font-semibold">Các milestone</h2>
              </header>
              <ol className="flex flex-col gap-1 px-2">
                {track.capstone.milestones.map((item) => {
                  const isDone = Boolean(progress.milestones[item.id]);
                  const isCurrent = item.id === milestone.id;
                  return (
                    <li key={item.id}>
                      <Link
                        to={milestoneLink(track.id, item.id)}
                        aria-current={isCurrent ? "page" : undefined}
                        className={cx(
                          "flex items-start gap-2.5 rounded-xl px-3 py-2.5 outline-hidden transition-colors",
                          isCurrent ? "bg-secondary" : "hover:bg-item-hover focus-visible:bg-item-hover",
                        )}
                      >
                        {isDone ? <CircleCheck className="size-4 shrink-0 text-success" aria-label="Đã xong" /> : <Circle className="size-4 shrink-0 text-muted" aria-hidden />}
                        <span className={cx("min-w-0 flex-1 text-sm text-pretty", isCurrent && "font-medium", isDone && !isCurrent && "text-muted")}>{item.title}</span>
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}
