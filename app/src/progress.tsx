import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { LEVELS, type Exercise, type Module, type Track } from "./content";

/* Tiến độ lưu ở progress.json (gốc repo) qua API của vite.config.ts. */

export type TrackProgress = {
  sections: Record<string, string[]>; // moduleId → slug các phần đã đọc
  exercises: Record<string, string>; // exercise.key → thời điểm xong
  milestones: Record<string, string>; // milestone.id → thời điểm xong
  notes: Record<string, string>; // moduleId hoặc exercise.key → ghi chú
  notesSavedAt: Record<string, string>;
  solutionsViewed: Record<string, string>;
};
export type ProgressData = { version: 1; tracks: Record<string, TrackProgress> };

const emptyTrack = (): TrackProgress => ({ sections: {}, exercises: {}, milestones: {}, notes: {}, notesSavedAt: {}, solutionsViewed: {} });

type Status = "loading" | "ready" | "error";
type ProgressApi = {
  status: Status;
  error: string;
  reload: () => void;
  of: (trackId: string) => TrackProgress;
  update: (trackId: string, change: (draft: TrackProgress) => void) => void;
};

const ProgressContext = createContext<ProgressApi | null>(null);

export function ProgressProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ProgressData>({ version: 1, tracks: {} });
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const saveTimer = useRef<number | undefined>(undefined);

  const reload = useCallback(() => {
    setStatus("loading");
    fetch("/api/progress")
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
        setData({ version: 1, tracks: body.tracks ?? {} });
        setStatus("ready");
      })
      .catch((reason: Error) => {
        setError(reason.message === "Failed to fetch" ? "Không kết nối được server của app" : reason.message);
        setStatus("error");
      });
  }, []);

  useEffect(reload, [reload]);

  const persist = useCallback((next: ProgressData) => {
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      fetch("/api/progress", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next) }).catch(() => {});
    }, 300);
  }, []);

  const of = useCallback((trackId: string) => ({ ...emptyTrack(), ...data.tracks[trackId] }), [data]);

  const update = useCallback(
    (trackId: string, change: (draft: TrackProgress) => void) => {
      setData((previous) => {
        const draft: TrackProgress = structuredClone({ ...emptyTrack(), ...previous.tracks[trackId] });
        change(draft);
        const next: ProgressData = { version: 1, tracks: { ...previous.tracks, [trackId]: draft } };
        persist(next);
        return next;
      });
    },
    [persist],
  );

  return <ProgressContext.Provider value={{ status, error, reload, of, update }}>{children}</ProgressContext.Provider>;
}

export function useProgress() {
  const api = useContext(ProgressContext);
  if (!api) throw new Error("useProgress phải nằm trong ProgressProvider");
  return api;
}

/* ===== Tính toán từ tiến độ ===== */

export const now = () => new Date().toISOString();

export function moduleStats(module: Module, progress: TrackProgress) {
  const readSet = new Set(progress.sections[module.id] ?? []);
  const read = module.sections.filter((section) => readSet.has(section.slug)).length;
  const exercisesDone = module.exercises.filter((exercise) => progress.exercises[exercise.key]).length;
  const byLevel = LEVELS.map((level) => {
    const items = module.exercises.filter((exercise) => exercise.level === level);
    return { level, done: items.filter((exercise) => progress.exercises[exercise.key]).length, total: items.length };
  });
  const total = module.sections.length + module.exercises.length;
  const complete = module.hasContent && total > 0 && read === module.sections.length && exercisesDone === module.exercises.length;
  const started = read > 0 || exercisesDone > 0;
  return { read, exercisesDone, byLevel, complete, started };
}

export function trackStats(track: Track, progress: TrackProgress) {
  let exercises = 0;
  let exercisesDone = 0;
  let sections = 0;
  let read = 0;
  let modulesDone = 0;
  for (const module of track.modules) {
    const stats = moduleStats(module, progress);
    exercises += module.exercises.length;
    exercisesDone += stats.exercisesDone;
    sections += module.sections.length;
    read += stats.read;
    if (stats.complete) modulesDone += 1;
  }
  const milestones = track.capstone?.milestones.length ?? 0;
  const milestonesDone = track.capstone?.milestones.filter((milestone) => progress.milestones[milestone.id]).length ?? 0;
  const units = exercises + sections;
  const percent = units ? Math.round(((exercisesDone + read) / units) * 100) : 0;
  return { exercises, exercisesDone, sections, read, modulesDone, milestones, milestonesDone, percent };
}

export type NextItem =
  | { kind: "section"; module: Module; slug: string; title: string }
  | { kind: "exercise"; module: Module; exercise: Exercise }
  | { kind: "milestone"; module: Module; id: string; title: string };

/** Hàng đợi học tiếp: từng module theo thứ tự — lý thuyết chưa đọc, rồi bài tập chưa xong, rồi milestone. */
export function nextItems(track: Track, progress: TrackProgress, limit = 6): NextItem[] {
  const items: NextItem[] = [];
  for (const module of track.modules) {
    const readSet = new Set(progress.sections[module.id] ?? []);
    for (const section of module.sections) {
      if (!readSet.has(section.slug)) items.push({ kind: "section", module, slug: section.slug, title: section.title });
    }
    for (const exercise of module.exercises) {
      if (!progress.exercises[exercise.key]) items.push({ kind: "exercise", module, exercise });
    }
    for (const milestone of track.capstone?.milestones.filter((m) => m.after === module.id) ?? []) {
      if (!progress.milestones[milestone.id]) items.push({ kind: "milestone", module, id: milestone.id, title: milestone.title });
    }
    if (items.length >= limit) break;
  }
  return items.slice(0, limit);
}

/** Module đang học: module đầu tiên chưa xong. */
export function currentModule(track: Track, progress: TrackProgress) {
  return track.modules.find((module) => module.hasContent && !moduleStats(module, progress).complete);
}
