import test from "node:test";
import assert from "node:assert/strict";
import { exerciseKind } from "./exerciseKind.ts";

test("notebook DS vẫn là notebook", () => assert.equal(exerciseKind({ files: [{ path: "starter/eda.ipynb" }, { path: "starter/MEMO.md" }] }), "notebook"));
test("bài .py là code", () => assert.equal(exerciseKind({ files: [{ path: "starter/load.py" }, { path: "tests/test_x.py", note: "Không sửa" }] }), "code"));
test("files rỗng là quiz-only", () => assert.equal(exerciseKind({ files: [] }), "quiz-only"));
test("chỉ có tệp ngoài starter/tests vẫn là quiz-only", () => assert.equal(exerciseKind({ files: [{ path: "README.md" }] }), "quiz-only"));
