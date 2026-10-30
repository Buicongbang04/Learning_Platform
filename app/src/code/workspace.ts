import { useCallback, useEffect, useRef, useState } from "react";

export type WorkspaceFile = { path: string; content: string; editable: boolean; binary?: false } | { path: string; binary: true };
export type RunResult = {
  kind: "test" | "file";
  code: number | null;
  output: string;
  durationMs: number;
  timedOut: boolean;
  counts: Partial<Record<"passed" | "failed" | "errors" | "skipped", number>>;
};
type SaveState = "saved" | "dirty" | "saving" | "error";
type RunResponse = Omit<RunResult, "kind" | "counts">;

async function request<T>(url: string, body?: unknown): Promise<T> {
  const init = body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error ?? `Lỗi ${response.status}`);
  return data as T;
}

/** Đếm kết quả từ dòng tổng kết của pytest, vd. "2 failed, 3 passed, 1 skipped in 0.41s". */
export function pytestCounts(output: string): RunResult["counts"] {
  const counts: RunResult["counts"] = {};
  const summary = output.trim().split("\n").reverse().find((line) => / in [\d.]+s/.test(line)) ?? "";
  for (const [, value, name] of summary.matchAll(/(\d+) (passed|failed|errors?|skipped)/g)) {
    counts[name.startsWith("error") ? "errors" : (name as "passed" | "failed" | "skipped")] = Number(value);
  }
  return counts;
}

export function useWorkspace(dir: string) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string>();
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [revisions, setRevisions] = useState<Record<string, number>>({});
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [running, setRunning] = useState<RunResult["kind"] | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);

  const saved = useRef<Record<string, string>>({});
  const latest = useRef<Record<string, string>>({});
  const timer = useRef<number | undefined>(undefined);
  const saveChain = useRef<Promise<boolean>>(Promise.resolve(true));
  const busy = useRef(false);

  const isDirty = () => Object.keys(latest.current).some((path) => latest.current[path] !== saved.current[path]);

  const fail = useCallback((reason: unknown) => {
    setError((reason as Error).message);
    setSaveState("error");
  }, []);

  const replace = useCallback((path: string, content: string) => {
    latest.current[path] = content;
    setRevisions((value) => ({ ...value, [path]: (value[path] ?? 0) + 1 }));
  }, []);

  const load = useCallback(
    async (quiet = false) => {
      if (!quiet) setStatus("loading");
      try {
        const { files: list } = await request<{ files: WorkspaceFile[] }>(`/api/workspace/files?dir=${encodeURIComponent(dir)}`);
        if (quiet && isDirty()) return;
        for (const file of list) {
          if (file.binary) continue;
          if (latest.current[file.path] !== file.content) replace(file.path, file.content);
          saved.current[file.path] = file.content;
        }
        setFiles(list);
        setStatus("ready");
      } catch (reason) {
        if (quiet) return;
        setError((reason as Error).message);
        setStatus("error");
      }
    },
    [dir, replace],
  );

  const writeDirty = useCallback(async () => {
    const dirty = Object.keys(latest.current).filter((path) => path.startsWith("starter/") && latest.current[path] !== saved.current[path]);
    if (dirty.length === 0) return true;
    setSaveState("saving");
    try {
      for (const path of dirty) {
        const content = latest.current[path];
        await request("/api/workspace/save", { dir, path, content });
        saved.current[path] = content;
      }
      setSaveState(isDirty() ? "dirty" : "saved");
      return true;
    } catch (reason) {
      fail(reason);
      return false;
    }
  }, [dir, fail]);

  const save = useCallback(() => {
    window.clearTimeout(timer.current);
    saveChain.current = saveChain.current.then(writeDirty, writeDirty);
    return saveChain.current;
  }, [writeDirty]);

  const change = useCallback(
    (path: string, content: string) => {
      latest.current[path] = content;
      setSaveState("dirty");
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => void save(), 800);
    },
    [save],
  );

  const openExternal = useCallback(
    async (path: string): Promise<string | null> => {
      try {
        await request("/api/workspace/open-file", { dir, path });
        return null;
      } catch (reason) {
        return (reason as Error).message;
      }
    },
    [dir],
  );

  const reset = useCallback(
    async (path: string) => {
      try {
        const { content } = await request<{ content: string }>("/api/workspace/reset", { dir, path });
        replace(path, content);
        await save();
      } catch (reason) {
        fail(reason);
      }
    },
    [dir, replace, save, fail],
  );

  const execute = useCallback(
    async (kind: RunResult["kind"], url: string, body: unknown) => {
      if (busy.current) return;
      busy.current = true;
      try {
        if (!(await save())) return;
        setRunning(kind);
        const data = await request<RunResponse>(url, body).catch(
          (reason): RunResponse => ({ code: null, output: (reason as Error).message, durationMs: 0, timedOut: false }),
        );
        setResult({ ...data, kind, counts: kind === "test" ? pytestCounts(data.output) : {} });
      } finally {
        busy.current = false;
        setRunning(null);
      }
    },
    [save],
  );

  const runTests = useCallback(() => void execute("test", "/api/workspace/test", { dir }), [dir, execute]);
  const runFile = useCallback((path: string) => void execute("file", "/api/workspace/exec", { dir, path }), [dir, execute]);
  const contentOf = useCallback((path: string) => latest.current[path] ?? "", []);
  const clearResult = useCallback(() => setResult(null), []);

  useEffect(() => {
    void load();
    const onFocus = () => !isDirty() && void load(true);
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      void save();
    };
  }, [load, save]);

  return { status, error, files, revisions, saveState, running, result, load, change, save, reset, openExternal, runTests, runFile, contentOf, clearResult };
}
