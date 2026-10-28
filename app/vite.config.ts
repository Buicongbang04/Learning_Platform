import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";

const repoRoot = resolve(__dirname, "..");
const progressFile = resolve(repoRoot, "progress.json");
const emptyProgress = { version: 1, tracks: {} };

// Tiến độ lưu thẳng vào progress.json ở gốc repo, để commit cùng git.
function progressApi(): Plugin {
  const handle = (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    if (req.url !== "/api/progress") return next();
    res.setHeader("Content-Type", "application/json");
    if (req.method === "GET") {
      const body = existsSync(progressFile) ? readFileSync(progressFile, "utf-8") : JSON.stringify(emptyProgress);
      try {
        JSON.parse(body);
      } catch (error) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: `progress.json sai cú pháp: ${(error as Error).message}` }));
        return;
      }
      res.end(body);
      return;
    }
    if (req.method === "PUT") {
      let body = "";
      req.on("data", (chunk) => (body += chunk));
      req.on("end", () => {
        try {
          const data = JSON.parse(body);
          writeFileSync(progressFile, JSON.stringify(data, null, 2) + "\n", "utf-8");
          res.end(JSON.stringify({ ok: true }));
        } catch (error) {
          res.statusCode = 400;
          res.end(JSON.stringify({ error: (error as Error).message }));
        }
      });
      return;
    }
    res.statusCode = 405;
    res.end();
  };
  return {
    name: "progress-api",
    configureServer(server) {
      server.middlewares.use(handle);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handle);
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), progressApi()],
  server: {
    port: 5173,
    fs: { allow: [repoRoot] },
    watch: { ignored: ["**/.venv/**", "**/data/raw/**", "**/progress.json"] },
  },
});
