import { memo, useEffect, useState } from "react";
import { Check, CircleAlert, CircleCheck, CircleX, ExternalLink, FileCode, LoaderCircle, Lock, Play, RotateCcw, SquareTerminal, X } from "lucide-react";
import type { Exercise } from "../content";
import { button, CodeLine, cx, ErrorBlock, LoadingBlock } from "../components/ui";
import { CodeEditor } from "./CodeEditor";
import { useSplit } from "./useSplit";
import { useWorkspace, type RunResult } from "./workspace";

const SAVE_LABEL = { saved: "Đã lưu", dirty: "Chưa lưu", saving: "Đang lưu…", error: "Lưu lỗi" } as const;
const MOD = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";
const HAS_MAIN = /^if\s+__name__\s*==\s*["']__main__["']\s*:/m;

const TONES = {
  pass: { className: "text-success", Icon: CircleCheck },
  warn: { className: "text-muted", Icon: CircleAlert },
  fail: { className: "text-error-text", Icon: CircleX },
} as const;

function verdict(result: RunResult): { tone: keyof typeof TONES; text: string } {
  const { passed = 0, failed = 0, errors = 0, skipped = 0 } = result.counts;
  const exitError = { tone: "fail", text: `Lỗi (mã thoát ${result.code ?? "?"})` } as const;
  if (result.timedOut) return { tone: "fail", text: "Quá thời gian chạy" };
  if (result.kind === "file") {
    if (result.code !== 0) return exitError;
    return result.output.trim() ? { tone: "pass", text: "Chạy xong" } : { tone: "warn", text: "Chạy xong, không in ra gì" };
  }
  if (failed || errors) return { tone: "fail", text: `${failed + errors} lỗi · ${passed} đạt` };
  if (result.code === 0 && passed) return { tone: "pass", text: skipped ? `${passed} đạt · ${skipped} bỏ qua` : `Đạt cả ${passed} test` };
  if (result.code === 0 && skipped) return { tone: "warn", text: `${skipped} test bị bỏ qua` };
  return result.code === 5 ? { tone: "fail", text: "Không tìm thấy test" } : exitError;
}

function lineClass(line: string) {
  if (/^E\s|FAILED|^ERROR|Error:|Traceback/.test(line)) return "text-error-text";
  if (/^SKIPPED/.test(line)) return "text-muted";
  if (/^=+ .* in [\d.]+s/.test(line) || /^\d+ passed/.test(line)) return /failed|error/.test(line) ? "text-error-text font-medium" : "text-success font-medium";
  return "";
}

export const RunOutput = memo(function RunOutput({ output }: { output: string }) {
  return (
    <pre className="px-4 py-3 font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap">
      {output.split("\n").map((line, index) => (
        <span key={index} className={cx("block", lineClass(line))}>
          {line || " "}
        </span>
      ))}
    </pre>
  );
});

/** Dòng tóm tắt một lần chạy: biểu tượng + kết luận + thời gian. */
export function RunSummary({ result }: { result: RunResult }) {
  const outcome = verdict(result);
  const tone = TONES[outcome.tone];
  return (
    <span className={cx("inline-flex min-w-0 items-center gap-1.5 truncate text-sm", tone.className)}>
      <tone.Icon className="size-4 shrink-0" aria-hidden />
      {outcome.text}
      <span className="text-muted tabular-nums">· {(result.durationMs / 1000).toFixed(1)}s</span>
    </span>
  );
}

/** Dải mời đánh dấu xong khi lần chạy test vừa rồi đạt hết. */
export function PassedBanner({ result, onMarkDone, text = "Code của bạn đã qua toàn bộ test." }: { result: RunResult; onMarkDone: () => void; text?: string }) {
  if (result.kind !== "test" || verdict(result).tone !== "pass") return null;
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border-strong bg-success-bg px-4 py-2.5">
      <p className="min-w-0 flex-1 text-sm text-success">{text}</p>
      <button type="button" className={button.primary} onClick={onMarkDone}>
        <Check className="size-4 shrink-0" aria-hidden />
        Đánh dấu xong
      </button>
    </div>
  );
}

export function OpenInVsCode({ path, className, showLabel = false }: { path: string; className?: string; showLabel?: boolean }) {
  const [error, setError] = useState<string | null>(null);
  const open = async () => {
    setError(null);
    try {
      const response = await fetch("/api/workspace/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) });
      if (!response.ok) setError(((await response.json().catch(() => null)) as { error?: string } | null)?.error ?? "Không mở được VS Code");
    } catch {
      setError("Không kết nối được server của app");
    }
  };
  return (
    <>
      <button type="button" className={cx(button.outline, className)} onClick={() => void open()} title={`Mở ${path} trong VS Code`}>
        <ExternalLink className="size-4 shrink-0" aria-hidden />
        <span className={showLabel ? undefined : "hidden sm:inline"}>Mở trong VS Code</span>
      </button>
      {error && (
        <span role="alert" className="max-w-64 truncate text-xs text-error-text" title={error}>
          {error}
        </span>
      )}
    </>
  );
}

export function Workspace({ exercise, done, onMarkDone }: { exercise: Exercise; done: boolean; onMarkDone: () => void }) {
  const ws = useWorkspace(exercise.dir);
  const [active, setActive] = useState<string | null>(null);
  const split = useSplit({ storageKey: "split:console", initial: 0.62, axis: "y", min: 0.25, max: 0.85 });

  useEffect(() => {
    if (ws.status !== "ready" || (active && ws.files.some((file) => file.path === active))) return;
    const listed = exercise.files.map((file) => file.path).find((path) => path.startsWith("starter/") && ws.files.some((file) => file.path === path));
    setActive(listed ?? ws.files.find((file) => file.editable)?.path ?? ws.files[0]?.path ?? null);
  }, [ws.status, ws.files, active, exercise.files]);

  if (ws.status === "loading") return <LoadingBlock text="Đang mở tệp bài tập…" />;
  if (ws.status === "error") return <ErrorBlock title="Không mở được tệp bài tập" reason={ws.error} onRetry={() => void ws.load()} />;
  if (ws.files.length === 0) return <ErrorBlock title="Bài này không có tệp trong starter/" />;

  const file = ws.files.find((item) => item.path === active) ?? ws.files[0];
  const result = ws.result;
  const runnable = file.editable && file.path.endsWith(".py") && HAS_MAIN.test(ws.contentOf(file.path));
  const services = exercise.services.filter((service) => service !== "airflow");

  return (
    <div ref={split.container} style={split.style} className="flex h-full min-h-0 flex-col">
      <div className="flex h-11 shrink-0 items-center gap-1 border-b border-border-strong pr-2">
        <div role="tablist" aria-label="Tệp bài tập" className="scrollbar-clean flex min-w-0 flex-1 items-stretch self-stretch overflow-x-auto">
          {ws.files.map((item) => {
            const selected = item.path === file.path;
            return (
              <button
                key={item.path}
                type="button"
                role="tab"
                aria-selected={selected}
                title={item.path}
                onClick={() => setActive(item.path)}
                className={cx(
                  "relative flex shrink-0 cursor-pointer items-center gap-2 px-3.5 text-[13px] outline-hidden transition-colors",
                  selected ? "text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary" : "text-muted hover:text-foreground focus-visible:text-foreground",
                )}
              >
                {item.editable ? <FileCode className="size-3.5 shrink-0" aria-hidden /> : <Lock className="size-3.5 shrink-0" aria-label="Chỉ đọc" />}
                <span className="font-mono">{item.path.replace(/^(starter|tests)\//, "")}</span>
              </button>
            );
          })}
        </div>
        <span className={cx("shrink-0 px-2 text-xs", ws.saveState === "error" ? "text-error-text" : "text-muted")} role="status" title={ws.saveState === "error" ? ws.error : undefined}>
          {file.editable ? SAVE_LABEL[ws.saveState] : "Chỉ đọc"}
        </span>
        {file.path.endsWith(".ipynb") && <OpenInVsCode path={`${exercise.dir}/${file.path}`} className="min-h-8 shrink-0 px-3 py-1" />}
        {file.editable && (
          <button
            type="button"
            className={button.icon}
            aria-label="Khôi phục code ban đầu"
            title="Khôi phục code ban đầu"
            onClick={() => window.confirm(`Khôi phục ${file.path} về bản gốc? Code bạn đã viết trong tệp này sẽ mất.`) && void ws.reset(file.path)}
          >
            <RotateCcw className="size-4" aria-hidden />
          </button>
        )}
      </div>

      <div className="min-h-0 grow-(--split-a) basis-0">
        <CodeEditor
          path={file.path}
          content={ws.contentOf(file.path)}
          revision={ws.revisions[file.path] ?? 0}
          readOnly={!file.editable}
          onChange={ws.change}
          onSave={() => void ws.save()}
          onRun={ws.runTests}
        />
      </div>

      <div
        {...split.handleProps}
        aria-label="Kéo để đổi chiều cao khung kết quả"
        className="group relative z-10 -my-1 h-2 shrink-0 cursor-row-resize outline-hidden"
      >
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border-strong transition-colors group-hover:h-0.5 group-hover:bg-primary group-focus-visible:h-0.5 group-focus-visible:bg-primary group-data-dragging:h-0.5 group-data-dragging:bg-primary" />
      </div>

      <section aria-label="Kết quả chạy" className="flex min-h-0 grow-(--split-b) basis-0 flex-col">
        <div className="flex h-12 shrink-0 items-center gap-2 px-3">
          <SquareTerminal className="size-4 shrink-0 text-muted" aria-hidden />
          <h2 className="text-sm font-medium">Kết quả</h2>
          {result && !ws.running && <RunSummary result={result} />}
          <span className="flex-1" />
          {result && !ws.running && (
            <button type="button" className={button.icon} aria-label="Xoá kết quả" onClick={ws.clearResult}>
              <X className="size-4" aria-hidden />
            </button>
          )}
          {runnable && (
            <button type="button" className={button.outline} disabled={Boolean(ws.running)} onClick={() => ws.runFile(file.path)} title={`uv run python ${exercise.dir}/${file.path}`}>
              {ws.running === "file" ? <LoaderCircle className="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden /> : <Play className="size-4 shrink-0" aria-hidden />}
              Chạy file
            </button>
          )}
          <button type="button" className={button.primary} disabled={Boolean(ws.running)} onClick={ws.runTests} title={`${MOD}+Enter`}>
            {ws.running === "test" ? <LoaderCircle className="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden /> : <Check className="size-4 shrink-0" aria-hidden />}
            {ws.running === "test" ? "Đang chạy…" : "Chạy test"}
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto border-t border-border-strong bg-code-frame" aria-live="polite" aria-busy={Boolean(ws.running) || undefined}>
          {result && !done && <PassedBanner result={result} onMarkDone={onMarkDone} />}
          {result ? (
            <RunOutput output={result.output} />
          ) : (
            <div className="flex flex-col gap-3 px-4 py-4 text-sm text-muted">
              <p>
                Viết code trong <code className="font-mono text-[13px] text-foreground">starter/</code>, tự lưu sau khi gõ. Bấm <strong className="font-medium text-foreground">Chạy test</strong> ({MOD}+Enter) để
                chạy pytest của bài này.
              </p>
              {services.length > 0 && (
                <div>
                  <p className="mb-1.5">Bài cần dịch vụ Docker (chưa bật thì test bị bỏ qua):</p>
                  <CodeLine text={`docker compose -f setup/docker-compose.yml up -d ${services.join(" ")}`} />
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
