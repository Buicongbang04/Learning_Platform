import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parse } from "yaml";
import { exerciseKind } from "./exerciseKind.ts";

test("notebook DS vẫn là notebook", () => assert.equal(exerciseKind({ files: [{ path: "starter/eda.ipynb" }, { path: "starter/MEMO.md" }] }), "notebook"));
test("bài .py là code", () => assert.equal(exerciseKind({ files: [{ path: "starter/load.py" }, { path: "tests/test_x.py", note: "Không sửa" }] }), "code"));
test("files rỗng là quiz-only", () => assert.equal(exerciseKind({ files: [] }), "quiz-only"));
test("chỉ có tệp ngoài starter/tests vẫn là quiz-only", () => assert.equal(exerciseKind({ files: [{ path: "README.md" }] }), "quiz-only"));

test("frontmatter thật của bài DA 08 basic/01-chart-chooser là quiz-only", () => {
  const readme = readFileSync(
    new URL("../../../tracks/data-analyst/modules/08-visualization-chart-reading/exercises/basic/01-chart-chooser/README.md", import.meta.url),
    "utf-8",
  );
  const match = /^---\n([\s\S]*?)\n---\n?/.exec(readme.replace(/\r\n/g, "\n"));
  assert.ok(match, "README thiếu frontmatter");
  const meta = parse(match[1]) as { files: { path: string }[] };
  assert.deepEqual(meta.files, []);
  assert.equal(exerciseKind(meta), "quiz-only");
});

test("frontmatter thiếu khoá files (parse lỗi) không bị coi là quiz-only", () => {
  assert.equal(exerciseKind({ files: [], filesDeclared: false }), "code");
  assert.equal(exerciseKind({ files: [], filesDeclared: true }), "quiz-only");
});

test("mọi README bài tập có frontmatter parse được và `files` là mảng", async () => {
  const { readdirSync } = await import("node:fs");
  const root = new URL("../../../tracks/", import.meta.url);
  const bad: string[] = [];
  let count = 0;
  const walk = (dir: URL) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const child = new URL(e.name + (e.isDirectory() ? "/" : ""), dir);
      if (e.isDirectory()) walk(child);
      else if (e.name === "README.md" && /\/modules\/[^/]+\/exercises\/[^/]+\/[^/]+\/README\.md$/.test(child.pathname)) {
        count++;
        const m = /^---\n([\s\S]*?)\n---\n?/.exec(readFileSync(child, "utf-8").replace(/\r\n/g, "\n"));
        try {
          const data = m ? (parse(m[1]) as { files?: unknown }) : null;
          if (!Array.isArray(data?.files)) bad.push(child.pathname + " (files không phải mảng)");
        } catch (err) {
          bad.push(child.pathname + " (yaml lỗi: " + (err as Error).message.split("\n")[0] + ")");
        }
      }
    }
  };
  walk(root);
  assert.ok(count > 0);
  assert.deepEqual(bad, []);
});
