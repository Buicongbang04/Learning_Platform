import { Link } from "react-router-dom";
import { Circle, CircleCheck, CircleDot } from "lucide-react";
import { LEVEL_LABEL, LEVELS, type Module } from "../content";
import { now, useProgress } from "../progress";
import { exerciseLink } from "../links";
import { card, cx } from "./ui";

/** Danh sách bài tập của một module, nhóm theo mức. */
export function ExerciseList({ trackId, module, currentKey }: { trackId: string; module: Module; currentKey?: string }) {
  const progress = useProgress().of(trackId);
  const firstOpen = module.exercises.find((exercise) => !progress.exercises[exercise.key])?.key;
  if (module.exercises.length === 0) return <p className="py-6 text-center text-sm text-muted">Module này chưa có bài tập</p>;
  return (
    <>
      {LEVELS.map((level, index) => {
        const items = module.exercises.filter((exercise) => exercise.level === level);
        if (items.length === 0) return null;
        const done = items.filter((exercise) => progress.exercises[exercise.key]).length;
        return (
          <div key={level} className={index ? "mt-4" : ""}>
            <p className="flex h-8 items-center justify-between px-3 text-xs font-medium tracking-wide text-muted uppercase">
              <span>{LEVEL_LABEL[level]}</span>
              <span className="normal-case tabular-nums">
                {done} / {items.length}
              </span>
            </p>
            <ul className="flex flex-col gap-1">
              {items.map((exercise, position) => {
                const isDone = Boolean(progress.exercises[exercise.key]);
                const isNext = exercise.key === firstOpen;
                const isCurrent = exercise.key === currentKey;
                const code = `${LEVEL_LABEL[level][0]}${position + 1}`;
                return (
                  <li key={exercise.key}>
                    <Link
                      to={exerciseLink(trackId, exercise)}
                      aria-current={isCurrent ? "page" : undefined}
                      className={cx(
                        "flex items-start gap-2.5 rounded-xl px-3 py-2.5 outline-hidden transition-colors",
                        isCurrent ? "bg-secondary" : "hover:bg-item-hover focus-visible:bg-item-hover",
                      )}
                    >
                      {isDone ? (
                        <CircleCheck className="size-4 shrink-0 text-success" aria-label="Đã xong" />
                      ) : isNext ? (
                        <CircleDot className="size-4 shrink-0 text-primary" aria-label="Bài tiếp theo" />
                      ) : (
                        <Circle className="size-4 shrink-0 text-muted" aria-hidden />
                      )}
                      <span className={cx("shrink-0 text-xs font-medium tabular-nums", isCurrent ? "text-foreground/70" : "text-muted")}>{code}</span>
                      <span className={cx("line-clamp-2 min-w-0 flex-1 text-sm text-pretty", (isCurrent || isNext) && "font-medium", isDone && !isCurrent && "text-muted")}>
                        {exercise.title}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </>
  );
}

const timeFormat = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });

/** Ô ghi chú, lưu vào progress.json. */
export function Notes({ trackId, noteKey, rows = 5, bare = false }: { trackId: string; noteKey: string; rows?: number; bare?: boolean }) {
  const api = useProgress();
  const progress = api.of(trackId);
  const value = progress.notes[noteKey] ?? "";
  const savedAt = progress.notesSavedAt[noteKey];
  const id = `note-${noteKey.replace(/[^a-z0-9]/gi, "-")}`;
  const body = (
    <>
      <label htmlFor={id} className="mb-2 block text-base font-semibold">
        Ghi chú
      </label>
      <textarea
        id={id}
        rows={rows}
        value={value}
        placeholder="Điều cần nhớ, lỗi đã gặp…"
        onChange={(event) =>
          api.update(trackId, (draft) => {
            draft.notes[noteKey] = event.target.value;
            draft.notesSavedAt[noteKey] = now();
          })
        }
        className="w-full resize-y rounded-xl border border-border-strong bg-surface px-3.5 py-2.5 text-base text-foreground outline-hidden transition-colors placeholder:text-muted focus:border-focus focus:ring-2 focus:ring-focus md:text-sm"
      />
      <p className="mt-1.5 text-xs text-muted">{savedAt ? `Đã lưu lúc ${timeFormat.format(new Date(savedAt))}` : "Lưu tự động vào progress.json"}</p>
    </>
  );
  return bare ? body : <section className={`${card} p-5`}>{body}</section>;
}
