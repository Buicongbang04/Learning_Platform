import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";
import { execFile, spawn } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { relative, resolve, sep } from "node:path";

const EXERCISE_DIR = /^tracks\/[\w.-]+\/modules\/[\w.-]+\/exercises\/(basic|intermediate|advanced)\/[\w.-]+$/;
const MAX_FILE_BYTES = 256 * 1024;
const MAX_OUTPUT = 200_000;
const SKIP_DIRS = new Set(["__pycache__", ".pytest_cache", "target", "logs", "dbt_packages", ".terraform"]);

type FileEntry = { path: string; content: string; editable: boolean };

class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function listFiles(root: string, base: string): string[] {
  if (!existsSync(root)) return [];
  const out: string[] = [];
  for (const entry of readdirSync(root, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if (SKIP_DIRS.has(entry.name) || entry.name.endsWith(".pyc")) continue;
    const full = resolve(root, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(full, base));
    else if (entry.isFile() && statSync(full).size <= MAX_FILE_BYTES) out.push(relative(base, full).split(sep).join("/"));
  }
  return out;
}

const isText = (path: string) => !/\.(duckdb|parquet|png|jpe?g|gif|zip|gz|db|sqlite)$/i.test(path);

export function workspaceApi(repoRoot: string): Plugin {
  const exerciseRoot = (dir: unknown) => {
    if (typeof dir !== "string" || !EXERCISE_DIR.test(dir)) throw new HttpError(400, "Đường dẫn bài tập không hợp lệ");
    const full = resolve(repoRoot, dir);
    if (!existsSync(full)) throw new HttpError(404, "Không có thư mục bài tập");
    return full;
  };
  const starterFile = (root: string, path: unknown) => {
    if (typeof path !== "string" || !path.startsWith("starter/")) throw new HttpError(400, "Chỉ sửa được tệp trong starter/");
    const full = resolve(root, path);
    if (!full.startsWith(resolve(root, "starter") + sep)) throw new HttpError(400, "Đường dẫn tệp không hợp lệ");
    return full;
  };

  const pythonFile = (root: string, path: unknown) => {
    const full = starterFile(root, path);
    if (!full.endsWith(".py")) throw new HttpError(400, "Chỉ chạy trực tiếp được tệp .py");
    return full;
  };

  const readFiles = (root: string): FileEntry[] => {
    const starter = listFiles(resolve(root, "starter"), root).filter(isText);
    const tests = listFiles(resolve(root, "tests"), root).filter((path) => path.endsWith(".py"));
    return [
      ...starter.map((path) => ({ path, content: readFileSync(resolve(root, path), "utf-8"), editable: true })),
      ...tests.map((path) => ({ path, content: readFileSync(resolve(root, path), "utf-8"), editable: false })),
    ];
  };

  let running = false;

  const run = (args: string[], timeoutMs: number, res: ServerResponse) =>
    new Promise<{ code: number | null; output: string; durationMs: number; timedOut: boolean }>((resolveRun) => {
      const started = Date.now();
      const env: NodeJS.ProcessEnv = { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1", PYTHONUNBUFFERED: "1" };
      delete env.SOLUTION;
      const child = spawn("uv", args, { cwd: repoRoot, env, stdio: ["ignore", "pipe", "pipe"] });
      let output = "";
      let timedOut = false;
      const append = (chunk: Buffer) => {
        if (output.length < MAX_OUTPUT) output += chunk.toString("utf-8");
      };
      child.stdout.on("data", append);
      child.stderr.on("data", append);
      const timer = setTimeout(() => {
        timedOut = true;
        child.kill("SIGKILL");
      }, timeoutMs);
      const abandon = () => child.exitCode === null && child.kill("SIGKILL");
      res.on("close", abandon);
      child.on("error", (error) => {
        clearTimeout(timer);
        res.off("close", abandon);
        resolveRun({ code: null, output: `Không chạy được uv: ${error.message}`, durationMs: Date.now() - started, timedOut });
      });
      child.on("close", (code) => {
        clearTimeout(timer);
        if (output.length >= MAX_OUTPUT) output = output.slice(0, MAX_OUTPUT) + "\n… (cắt bớt output)";
        res.off("close", abandon);
        resolveRun({ code, output, durationMs: Date.now() - started, timedOut });
      });
    });

  const gitHead = (path: string) =>
    new Promise<string>((resolveContent, reject) =>
      execFile("git", ["show", `HEAD:${path}`], { cwd: repoRoot, maxBuffer: MAX_FILE_BYTES * 2 }, (error, stdout) =>
        error ? reject(new HttpError(404, "Tệp này chưa có trong git, không khôi phục được")) : resolveContent(stdout),
      ),
    );

  const readBody = (req: IncomingMessage) =>
    new Promise<Record<string, unknown>>((resolveBody, reject) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
        if (body.length > MAX_FILE_BYTES * 2) {
          req.removeAllListeners("data");
          reject(new HttpError(413, "Nội dung gửi lên quá lớn"));
        }
      });
      req.on("end", () => {
        try {
          resolveBody(JSON.parse(body || "{}"));
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

  const openInVsCode = (path: unknown, send: (status: number, data: unknown) => void) => {
    if (typeof path !== "string" || !path || path.includes("\0")) throw new HttpError(400, "Đường dẫn không hợp lệ");
    const root = resolve(repoRoot);
    const full = resolve(root, path);
    if (full !== root && !full.startsWith(root + sep)) throw new HttpError(400, "Đường dẫn nằm ngoài repo");
    if (!existsSync(full)) throw new HttpError(400, "Tệp hoặc thư mục không tồn tại");
    return new Promise<void>((done) => {
      const child = spawn("code", [full], { cwd: repoRoot, detached: true, stdio: "ignore" });
      child.once("error", () => {
        send(500, { error: "Không chạy được lệnh `code`. Cài VS Code và bật lệnh `code` trong PATH (xem setup/SETUP.md)." });
        done();
      });
      child.once("spawn", () => {
        child.unref();
        send(200, { ok: true });
        done();
      });
    });
  };

  const handle = async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    if (!url.pathname.startsWith("/api/workspace/")) return next();
    res.setHeader("Content-Type", "application/json");
    const send = (status: number, data: unknown) => {
      res.statusCode = status;
      res.end(JSON.stringify(data));
    };
    try {
      if (url.pathname === "/api/workspace/files" && req.method === "GET") {
        return send(200, { files: readFiles(exerciseRoot(url.searchParams.get("dir"))) });
      }
      if (req.method !== "POST") return send(405, { error: "Phương thức không được hỗ trợ" });
      assertSameOrigin(req);
      const body = await readBody(req);

      if (url.pathname === "/api/workspace/open") return await openInVsCode(body.path, send);
      const root = exerciseRoot(body.dir);

      if (url.pathname === "/api/workspace/save") {
        const full = starterFile(root, body.path);
        if (typeof body.content !== "string") throw new HttpError(400, "Thiếu nội dung tệp");
        if (!existsSync(full)) throw new HttpError(404, "Tệp không tồn tại");
        writeFileSync(full, body.content, "utf-8");
        return send(200, { ok: true });
      }
      if (url.pathname === "/api/workspace/reset") {
        starterFile(root, body.path);
        return send(200, { content: await gitHead(`${body.dir}/${body.path}`) });
      }
      if (url.pathname === "/api/workspace/test" || url.pathname === "/api/workspace/exec") {
        const args =
          url.pathname === "/api/workspace/test"
            ? ["run", "pytest", String(body.dir), "-q", "--no-header", "--tb=short", "-rs", "--color=no"]
            : ["run", "python", relative(repoRoot, pythonFile(root, body.path))];
        if (running) throw new HttpError(409, "Đang có một lần chạy khác, chờ nó xong đã");
        running = true;
        try {
          return send(200, await run(args, url.pathname === "/api/workspace/test" ? 300_000 : 120_000, res));
        } finally {
          running = false;
        }
      }
      return send(404, { error: "Không có API này" });
    } catch (error) {
      send(error instanceof HttpError ? error.status : 500, { error: (error as Error).message });
    }
  };

  const middleware = (req: IncomingMessage, res: ServerResponse, next: () => void) => void handle(req, res, next);
  return {
    name: "workspace-api",
    configureServer: (server) => void server.middlewares.use(middleware),
    configurePreviewServer: (server) => void server.middlewares.use(middleware),
  };
}
