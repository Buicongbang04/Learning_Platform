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
