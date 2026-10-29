import { Check } from "lucide-react";
import { LEVEL_LABEL, type Exercise } from "../content";
import { Markdown } from "../components/Markdown";
import { badge, button, card, cx } from "../components/ui";
import { QuizCard } from "./NotebookPanel";

/** Khung phải của bài chỉ có trắc nghiệm (không starter/, không tests/): card giới thiệu + card trắc nghiệm. */
export function QuizOnlyPanel({ exercise, trackId, done, onMarkDone }: { exercise: Exercise; trackId: string; done: boolean; onMarkDone: () => void }) {
  return (
    <div className="flex flex-col gap-3">
      <section aria-labelledby="qo-intro-title" className={cx(card, "overflow-hidden")}>
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
            <h2 id="qo-intro-title" className="mt-1 text-lg font-semibold text-balance">
              {exercise.title}
            </h2>
          </div>
          {exercise.goal && <Markdown className="text-muted [&_p]:text-sm">{exercise.goal}</Markdown>}
          {!done && (
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className={button.primary} onClick={onMarkDone}>
                <Check className="size-4 shrink-0" aria-hidden />
                Đánh dấu hoàn thành
              </button>
            </div>
          )}
        </div>
      </section>
      <QuizCard exercise={exercise} trackId={trackId} noneNotice="Bài này chưa có câu hỏi" />
    </div>
  );
}
