import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "yaml";

const EXERCISE_DIR = /^tracks\/[\w.-]+\/modules\/[\w.-]+\/exercises\/(basic|intermediate|advanced)\/[\w.-]+$/;

export type QuizQuestion = {
  id: string;
  kind: "data" | "knowledge";
  type: "single" | "multi";
  prompt: string;
  options: { id: string; text: string }[];
};
export type AnswerKey = Record<string, string[]>;
export type GradeResult = {
  correct: number;
  total: number;
  results: { id: string; correct: boolean; answer: string[] }[];
};

class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const quizHash = (rawYaml: string) => createHash("sha256").update(rawYaml).digest("hex").slice(0, 12);

export function parseQuiz(rawYaml: string): QuizQuestion[] {
  const data = parse(rawYaml) as { questions?: unknown } | null;
  if (!data || !Array.isArray(data.questions) || data.questions.length === 0) throw new Error("quiz.yaml cần mảng questions không rỗng");
  return data.questions.map((q: any) => {
    if (!q || typeof q.id !== "string" || typeof q.prompt !== "string" || !Array.isArray(q.options)) throw new Error(`Câu hỏi sai định dạng: ${q?.id ?? "?"}`);
    if (q.kind !== "data" && q.kind !== "knowledge") throw new Error(`${q.id}: kind không hợp lệ`);
    if (q.type !== "single" && q.type !== "multi") throw new Error(`${q.id}: type không hợp lệ`);
    return {
      id: q.id,
      kind: q.kind,
      type: q.type,
      prompt: q.prompt,
      options: q.options.map((o: any) => ({ id: String(o.id), text: String(o.text) })),
    };
  });
}

const sameSet = (a: string[], b: string[]) => {
  const sa = new Set(a);
  const sb = new Set(b);
  return sa.size === sb.size && [...sa].every((x) => sb.has(x));
};

export function gradeQuiz(questions: QuizQuestion[], key: AnswerKey, answers: Record<string, string[]>): GradeResult {
  const results = questions.map((q) => {
    const answer = key[q.id];
    if (!Array.isArray(answer)) throw new Error(`Thiếu đáp án cho câu ${q.id}`);
    const chosen = Array.isArray(answers[q.id]) ? answers[q.id].map(String) : [];
    return { id: q.id, correct: chosen.length > 0 && sameSet(chosen, answer), answer: [...answer].sort() };
  });
  return { correct: results.filter((r) => r.correct).length, total: results.length, results };
}

const MAX_BODY = 64 * 1024;

export function quizApi(repoRoot: string): Plugin {
  const exerciseDir = (dir: unknown) => {
    if (typeof dir !== "string" || !EXERCISE_DIR.test(dir)) throw new HttpError(400, "Đường dẫn bài tập không hợp lệ");
    return dir;
  };
  const load = (dir: string) => {
    const file = resolve(repoRoot, dir, "quiz.yaml");
    if (!existsSync(file)) throw new HttpError(404, "Bài này chưa có trắc nghiệm");
    const raw = readFileSync(file, "utf-8");
    try {
      return { raw, questions: parseQuiz(raw) };
    } catch (error) {
      throw new HttpError(500, (error as Error).message);
    }
  };
  const readBody = (req: IncomingMessage) =>
    new Promise<Record<string, unknown>>((done, reject) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
        if (body.length > MAX_BODY) {
          req.removeAllListeners("data");
          reject(new HttpError(413, "Nội dung gửi lên quá lớn"));
        }
      });
      req.on("end", () => {
        try {
          done(JSON.parse(body || "{}"));
        } catch {
          reject(new HttpError(400, "Dữ liệu gửi lên không phải JSON"));
        }
      });
      req.on("error", reject);
    });
  const assertSameOrigin = (req: IncomingMessage) => {
    const origin = req.headers.origin;
    const host = req.headers.host;
    if (!origin || !host || new URL(origin).host !== host) throw new HttpError(403, "Chỉ gọi được từ app học tập");
    if (!String(req.headers["content-type"] ?? "").startsWith("application/json")) throw new HttpError(415, "Cần Content-Type application/json");
  };

  const handle = async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    if (url.pathname !== "/api/quiz" && url.pathname !== "/api/quiz/grade") return next();
    res.setHeader("Content-Type", "application/json");
    const send = (status: number, data: unknown) => {
      res.statusCode = status;
      res.end(JSON.stringify(data));
    };
    try {
      if (url.pathname === "/api/quiz") {
        if (req.method !== "GET") return send(405, { error: "Phương thức không được hỗ trợ" });
        const { raw, questions } = load(exerciseDir(url.searchParams.get("dir")));
        return send(200, { questions, quizHash: quizHash(raw) });
      }
      if (req.method !== "POST") return send(405, { error: "Phương thức không được hỗ trợ" });
      assertSameOrigin(req);
      const body = await readBody(req);
      const dir = exerciseDir(body.dir);
      if (!body.answers || typeof body.answers !== "object" || Array.isArray(body.answers)) throw new HttpError(400, "Thiếu answers");
      const { raw, questions } = load(dir);
      const keyFile = resolve(repoRoot, dir.replace("/exercises/", "/solutions/"), "quiz-answers.yaml");
      if (!existsSync(keyFile)) throw new HttpError(404, "Chưa có đáp án cho bài này");
      let result: GradeResult;
      try {
        result = gradeQuiz(questions, parse(readFileSync(keyFile, "utf-8")) as AnswerKey, body.answers as Record<string, string[]>);
      } catch (error) {
        throw new HttpError(500, (error as Error).message);
      }
      return send(200, { ...result, quizHash: quizHash(raw) });
    } catch (error) {
      send(error instanceof HttpError ? error.status : 500, { error: (error as Error).message });
    }
  };
  const middleware = (req: IncomingMessage, res: ServerResponse, next: () => void) => void handle(req, res, next);
  return {
    name: "quiz-api",
    configureServer: (server) => void server.middlewares.use(middleware),
    configurePreviewServer: (server) => void server.middlewares.use(middleware),
  };
}
