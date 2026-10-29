import { useCallback, useEffect, useMemo, useState } from "react";
import type { Exercise } from "../content";
import { now, useProgress } from "../progress";
import { storedResultFor, type QuizResult } from "./quizResult";

export type { QuizResult } from "./quizResult";
export type QuizQuestion = {
  id: string;
  kind: "data" | "knowledge";
  type: "single" | "multi";
  prompt: string;
  options: { id: string; text: string }[];
};
export type QuestionResult = { id: string; correct: boolean; answer: string[] };
type Answers = Record<string, string[]>;
type GradeResponse = { correct: number; total: number; quizHash: string; results: QuestionResult[] };
type Status = "loading" | "none" | "ready" | "error";

async function request<T>(url: string, body?: unknown): Promise<T> {
  const init = body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.error ?? `Lỗi ${response.status}`), { status: response.status });
  return data as T;
}

/**
 * Trắc nghiệm của một bài. Server không lưu đáp án đúng ở client: kết quả chi tiết (`results`) lấy từ
 * POST /api/quiz/grade. Tiến độ chỉ lưu `QuizResult`; khi mở lại bài, nếu hash còn khớp thì chấm lại
 * đáp án đã lưu để dựng lại phần đáp án đúng.
 */
export function useQuiz(exercise: Exercise, trackId: string) {
  const progress = useProgress();
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [quizHash, setQuizHash] = useState("");
  const [draft, setDraft] = useState<Answers>({});
  const [results, setResults] = useState<QuestionResult[] | null>(null);
  const [retaking, setRetaking] = useState(false);
  const dir = exercise.dir;

  useEffect(() => {
    let live = true;
    setStatus("loading");
    setError("");
    setDraft({});
    setResults(null);
    setRetaking(false);
    request<{ questions: QuizQuestion[]; quizHash: string }>(`/api/quiz?dir=${encodeURIComponent(dir)}`)
      .then((body) => {
        if (!live) return;
        setQuestions(body.questions);
        setQuizHash(body.quizHash);
        setStatus("ready");
      })
      .catch((reason: Error & { status?: number }) => {
        if (!live) return;
        if (reason.status === 404) return setStatus("none");
        setError(reason.message === "Failed to fetch" ? "Không kết nối được server của app" : reason.message);
        setStatus("error");
      });
    return () => {
      live = false;
    };
  }, [dir]);

  const stored = progress.status === "ready" ? storedResultFor(progress.of(trackId).quizzes[exercise.key], quizHash) : null;

  // Mở lại bài đã nộp: chấm lại đáp án đã lưu để có `results` (kèm đáp án đúng).
  useEffect(() => {
    if (!stored || results || retaking) return;
    let live = true;
    request<GradeResponse>("/api/quiz/grade", { dir, answers: stored.answers })
      .then((body) => live && setResults(body.results))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [stored, results, retaking, dir]);

  const setAnswer = useCallback((qid: string, optionIds: string[]) => setDraft((value) => ({ ...value, [qid]: optionIds })), []);

  const submit = useCallback(async () => {
    const body = await request<GradeResponse>("/api/quiz/grade", { dir, answers: draft });
    const saved: QuizResult = { answers: draft, correct: body.correct, total: body.total, submittedAt: now(), quizHash: body.quizHash };
    setResults(body.results);
    setRetaking(false);
    progress.update(trackId, (track) => {
      track.quizzes[exercise.key] = saved;
    });
  }, [dir, draft, exercise.key, trackId, progress]);

  const retake = useCallback(() => {
    setDraft({});
    setRetaking(true); // kết quả cũ vẫn nằm trong tiến độ đến khi nộp lại
  }, []);

  const result = useMemo(() => (stored && results && !retaking ? { ...stored, results } : null), [stored, results, retaking]);

  return { status, error, questions, quizHash, draft, setAnswer, submit, result, retake };
}
